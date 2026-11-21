"""Isolated source-first JSON store; declarations are not authenticated approvals."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import time
import uuid

from .contracts import (KnowledgeError, canonical_bytes, fields, identifier, nonblank,
                        release_identifier, require, sha256, strict_json, timestamp)
from .source import SourceDocument, Extraction, metadata_supported, validate_proposal


def _copy(value):
    return strict_json(canonical_bytes(value))


def _hash(value):
    return "sha256-" + sha256(canonical_bytes(value))


def _strings(values):
    return (isinstance(values, list) and all(nonblank(x) for x in values)
            and len(values) == len(set(values)))


REVISION_FIELDS = {
    "item_id", "source_id", "source_sha256", "spans", "text", "scopes", "aliases",
    "evidence", "status", "effective_from", "effective_until", "ancestry", "reason",
}
ITEM_FIELDS = {"revision_id", "revision", "review_state", "review", "decision_reason"}


class SourceKnowledgeStore:
    """Single-writer store for mutable candidates and immutable reviewed releases."""

    def __init__(self, root=r"knowledge\source-first", *, experimental_profile=None):
        self.root = Path(root)
        if experimental_profile is not None:
            require(isinstance(experimental_profile, dict)
                    and nonblank(experimental_profile.get("experiment_id")),
                    "experimental_profile", "An explicit unqualified experiment ID is required.")
        self._experimental_profile = _copy(experimental_profile)

    @property
    def working_candidate_path(self):
        return self.root / "working-candidate.json"

    @property
    def legacy_draft_path(self):
        return self.root / "draft.json"

    @property
    def draft_path(self):
        if self.working_candidate_path.exists() or not self.legacy_draft_path.exists():
            return self.working_candidate_path
        return self.legacy_draft_path

    @property
    def legacy_draft_used(self):
        return self.draft_path == self.legacy_draft_path

    def _path(self, kind, digest):
        require(release_identifier(digest), "store_hash", "A hash-safe identifier is required.")
        return self.root / kind / (digest + (".bin" if kind == "sources" else ".json"))

    @contextmanager
    def _writer(self):
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / ".writer.lock"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as error:
            raise KnowledgeError("store_busy", "Another writer holds the store lock.") from error
        try:
            os.close(fd)
            yield
        finally:
            path.unlink()

    def _immutable(self, path, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            require(path.read_bytes() == raw, "immutable_conflict", "Immutable record differs.")
            return
        staging = path.with_name(".writing-" + uuid.uuid4().hex)
        try:
            with staging.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(staging, path)
            except FileExistsError:
                require(path.read_bytes() == raw, "immutable_conflict", "Immutable record differs.")
        finally:
            staging.unlink(missing_ok=True)

    def _save(self, candidate):
        self._validate(candidate)
        for item in candidate["items"].values():
            self._immutable(self._path("revisions", item["revision_id"]),
                            canonical_bytes(item["revision"]))
        raw = canonical_bytes(candidate)
        staging = self.root / ".working-candidate-writing.json"
        created = False
        try:
            with staging.open("xb") as stream:
                created = True
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            for attempt in range(10):
                try:
                    os.replace(staging, self.working_candidate_path)
                    break
                except PermissionError:
                    # Windows readers/indexers may briefly deny replacement of a closed file.
                    if attempt == 9:
                        raise
                    time.sleep(0.02 * (attempt + 1))
        finally:
            if created and staging.exists():
                staging.unlink()
        if self.legacy_draft_path.exists():
            self.legacy_draft_path.unlink()
        return sha256(raw)

    def _source(self, source_hash):
        require(isinstance(source_hash, str) and release_identifier("sha256-" + source_hash),
                "source_hash", "A source hash is required.")
        raw = self._path("sources", "sha256-" + source_hash).read_bytes()
        require(sha256(raw) == source_hash, "source_hash", "Source blob integrity failed.")
        return raw

    def _validate(self, candidate, *, immutable=False):
        fields(candidate, {"schema_version", "sources", "items", "context_links", "replacements"},
               "candidate")
        require(candidate["schema_version"] == 3, "unsupported_contract", "Source schema 3 required.")
        require(isinstance(candidate["sources"], dict) and isinstance(candidate["items"], dict),
                "schema", "Source and item maps required.")
        for sid, source in candidate["sources"].items():
            require(identifier(sid), "source_identity", "Invalid source ID.")
            fields(source, {"name", "source_sha256", "ancestry", "extraction_profile"}, "source")
            require(nonblank(source["name"]) and isinstance(source["ancestry"], list),
                    "source_identity", "Invalid source metadata.")
            profile = source["extraction_profile"]
            require(profile in ("c0", "user-amendment") or (
                isinstance(profile, dict) and self._experimental_profile is not None
                and profile == self._experimental_profile),
                "experimental_profile", "Unqualified extraction requires its explicit experiment binding.")
            raw = self._source(source["source_sha256"])
            SourceDocument.from_bytes(raw, name=source["name"], source_id=sid)
            for ancestor in source["ancestry"]:
                fields(ancestor, {"item_id", "revision_id", "source_id", "source_sha256"}, "ancestry")
                require(identifier(ancestor["item_id"]) and release_identifier(ancestor["revision_id"])
                        and ancestor["source_id"] in candidate["sources"]
                        and candidate["sources"][ancestor["source_id"]]["source_sha256"]
                        == ancestor["source_sha256"], "ancestry", "Invalid source ancestry.")
                prior = strict_json(self._path("revisions", ancestor["revision_id"]).read_bytes())
                require(_hash(prior) == ancestor["revision_id"]
                        and all(prior[key] == ancestor[key] for key in
                                ("item_id", "source_id", "source_sha256")),
                        "ancestry", "Source ancestry differs from the original revision.")
        for item_id, item in candidate["items"].items():
            require(identifier(item_id), "item_id", "Invalid item ID.")
            fields(item, ITEM_FIELDS, "item")
            revision = fields(item["revision"], REVISION_FIELDS, "revision")
            require(revision["item_id"] == item_id and item["revision_id"] == _hash(revision),
                    "revision_hash", "Revision identity mismatch.")
            if immutable:
                require(self._path("revisions", item["revision_id"]).read_bytes()
                        == canonical_bytes(revision), "revision_hash", "Revision file mismatch.")
            sid = revision["source_id"]
            require(sid in candidate["sources"]
                    and revision["source_sha256"] == candidate["sources"][sid]["source_sha256"],
                    "source_hash", "Unknown or mismatched source.")
            raw = self._source(revision["source_sha256"])
            spans, previous, pieces = revision["spans"], -1, []
            require(isinstance(spans, list) and spans, "spans", "Source spans required.")
            doc = SourceDocument.from_bytes(raw, name=candidate["sources"][sid]["name"], source_id=sid)
            boundaries = {(u["start"], u["end"]) for u in doc.units}
            for span in spans:
                fields(span, {"start", "end"}, "span")
                start, end = span["start"], span["end"]
                require(type(start) is int and type(end) is int
                        and (start, end) in boundaries and start >= previous,
                        "spans", "Spans must be ascending complete source units.")
                pieces.append(raw[start:end].decode("utf-8"))
                previous = end
            require(isinstance(revision["text"], str) and revision["text"]
                    and revision["text"] == "".join(pieces),
                    "source_text", "Text differs from exact source spans.")
            require(_strings(revision["scopes"]) and _strings(revision["aliases"]),
                    "metadata", "Unique scope and alias literals required.")
            require(isinstance(revision["evidence"], list), "evidence", "Evidence list required.")
            quotes = []
            for ev in revision["evidence"]:
                fields(ev, {"unit_id", "quote"}, "evidence")
                unit = next((u for u in doc.units if u["unit_id"] == ev["unit_id"]), None)
                require(unit is not None and isinstance(ev["quote"], str) and ev["quote"]
                        and ev["quote"] in unit["text"], "evidence", "Invalid source quote.")
                if {"start": unit["start"], "end": unit["end"]} in spans:
                    quotes.append((ev["quote"], unit["text"]))
            for label in revision["scopes"] + revision["aliases"]:
                require(any(metadata_supported(label, q, unit_text) for q, unit_text in quotes),
                        "metadata_evidence", "Literal metadata evidence is required.")
            require(revision["status"] in ("active", "retired"), "lifecycle", "Invalid status.")
            start, end = revision["effective_from"], revision["effective_until"]
            if start is not None:
                timestamp(start, "effective_from")
            if end is not None:
                timestamp(end, "effective_until")
            require(start is None or end is None or timestamp(start, "") < timestamp(end, ""),
                    "lifecycle", "Effective window must be nonempty.")
            require(isinstance(revision["ancestry"], list) and nonblank(revision["reason"]),
                    "revision", "Revision reason and ancestry required.")
            state = item["review_state"]
            require(state in ("pending", "reviewed", "rejected"), "review", "Invalid review state.")
            if state == "reviewed":
                review = fields(item["review"], {"revision_id", "reviewer", "reason"}, "review")
                require(review["revision_id"] == item["revision_id"]
                        and nonblank(review["reviewer"]) and nonblank(review["reason"]),
                        "review", "Review must bind this revision.")
            else:
                require(item["review"] is None, "review", "Unreviewed item cannot carry approval.")
            require((state == "rejected" and nonblank(item["decision_reason"]))
                    or (state != "rejected" and item["decision_reason"] is None),
                    "review", "Rejection requires an explicit coverage reason.")
        self._coverage(candidate)
        require(isinstance(candidate["context_links"], list)
                and isinstance(candidate["replacements"], list), "schema", "Edge lists required.")
        for edge in candidate["context_links"]:
            edge_fields = {"from", "to", "evidence"}
            if isinstance(edge, dict) and "kind" in edge:
                edge_fields.add("kind")
                require(edge["kind"] in ("required_context", "conservative_source_context"),
                        "context_kind", "Unsupported context relationship kind.")
            fields(edge, edge_fields, "context_link")
            require(isinstance(edge["evidence"], list) and edge["evidence"],
                    "context_evidence", "Context evidence required.")
            for ev in edge["evidence"]:
                fields(ev, {"item_id", "revision_id", "start", "end", "quote"}, "context_evidence")
                endpoint = ev["item_id"] + "@" + ev["revision_id"]
                require(endpoint in (edge["from"], edge["to"]), "context_evidence",
                        "Evidence must cite an endpoint.")
                item = self._endpoint(candidate, endpoint, exact=False)
                rev = item["revision"]
                raw = self._source(rev["source_sha256"])
                require(type(ev["start"]) is int and type(ev["end"]) is int
                        and 0 <= ev["start"] < ev["end"] <= len(raw)
                        and raw[ev["start"]:ev["end"]].decode("utf-8") == ev["quote"]
                        and any(s["start"] <= ev["start"] < ev["end"] <= s["end"]
                                for s in rev["spans"]), "context_evidence",
                        "Context quote must be inside endpoint source spans.")
            require({e["item_id"] + "@" + e["revision_id"] for e in edge["evidence"]}
                    == {edge["from"], edge["to"]}, "context_evidence",
                    "Both endpoints require evidence.")
            if edge.get("kind") == "conservative_source_context":
                require(len({self._endpoint(candidate, edge[key], exact=False)["revision"]["source_id"]
                             for key in ("from", "to")}) == 1,
                        "context_evidence", "Conservative source coupling requires one actual source.")
        for edge in candidate["replacements"]:
            fields(edge, {"predecessor_id", "successor_id", "effective_from", "reason"}, "replacement")
            require(edge["predecessor_id"] in candidate["items"]
                    and edge["successor_id"] in candidate["items"]
                    and edge["predecessor_id"] != edge["successor_id"]
                    and nonblank(edge["reason"]), "replacement", "Invalid replacement.")
            timestamp(edge["effective_from"], "effective_from")
        self._replacement_cycles(candidate)

    def _coverage(self, candidate):
        # Rejected originals remain explicit per-span coverage decisions; edited descendants
        # add a new source rather than pretending to cover their original bytes.
        covered = {sid: [] for sid in candidate["sources"]}
        direct = {sid: set() for sid in candidate["sources"]}
        for item in candidate["items"].values():
            rev = item["revision"]
            if rev["source_id"] in covered:
                spans = {(s["start"], s["end"]) for s in rev["spans"]}
                require(not direct[rev["source_id"]].intersection(spans),
                        "source_coverage", "Current items duplicate source units.")
                direct[rev["source_id"]].update(spans)
                covered[rev["source_id"]].extend(spans)
            for ancestor in rev["ancestry"]:
                old = self._path("revisions", ancestor).read_bytes()
                prior = strict_json(old)
                require(_hash(prior) == ancestor, "ancestry", "Ancestor revision hash mismatch.")
                if prior["source_id"] in covered:
                    covered[prior["source_id"]].extend((s["start"], s["end"]) for s in prior["spans"])
        for sid, spans in covered.items():
            # Ancestry can intentionally account for the same original passage in later edits.
            ordered, end = sorted(set(spans)), 0
            for start, stop in ordered:
                require(start == end, "source_coverage", "Source has missing or overlapping coverage.")
                end = stop
            require(end == len(self._source(candidate["sources"][sid]["source_sha256"])),
                    "source_coverage", "Source has uncovered bytes.")

    def _replacement_cycles(self, candidate):
        graph, incoming = {}, {}
        for edge in candidate["replacements"]:
            left, right = edge["predecessor_id"], edge["successor_id"]
            require(right not in graph.setdefault(left, set()),
                    "replacement", "Duplicate replacement edge.")
            graph[left].add(right)
            incoming.setdefault(left, 0)
            incoming[right] = incoming.get(right, 0) + 1
        ready = [node for node, count in incoming.items() if count == 0]
        visited = 0
        while ready:
            node = ready.pop()
            visited += 1
            for successor in graph.get(node, ()):
                incoming[successor] -= 1
                if incoming[successor] == 0:
                    ready.append(successor)
        require(visited == len(incoming), "replacement_cycle", "Replacement cycle is invalid.")

    def _endpoint(self, candidate, endpoint, *, exact=True):
        require(isinstance(endpoint, str) and endpoint.count("@") == 1,
                "invalid_dependency", "Expected exact item@revision endpoint.")
        item_id, revision_id = endpoint.split("@")
        require(identifier(item_id) and release_identifier(revision_id)
                and item_id in candidate["items"], "invalid_dependency", "Unknown endpoint.")
        item = candidate["items"][item_id]
        if exact:
            require(item["revision_id"] == revision_id and item["review_state"] == "reviewed",
                    "invalid_dependency", "Context endpoint changed or is not reviewed.")
            return item
        if item["revision_id"] == revision_id:
            return item
        prior = strict_json(self._path("revisions", revision_id).read_bytes())
        require(_hash(prior) == revision_id and prior["item_id"] == item_id,
                "invalid_dependency", "Invalid archived context endpoint.")
        return {"revision": prior}

    def validate_dependencies(self, candidate, assessment_time=None):
        cutoff = timestamp(assessment_time, "assessment_time") if assessment_time else None
        for edge in candidate["context_links"]:
            require(edge["from"] != edge["to"], "invalid_dependency", "Self context edge.")
            left = self._endpoint(candidate, edge["from"])["revision"]
            right = self._endpoint(candidate, edge["to"])["revision"]
            if cutoff:
                require(self.eligible(candidate, left["item_id"], assessment_time)
                        and self.eligible(candidate, right["item_id"], assessment_time),
                        "invalid_dependency", "Known context endpoint is inactive.")
            else:
                require(left["status"] == right["status"] == "active"
                        and left["effective_from"] == right["effective_from"]
                        and left["effective_until"] == right["effective_until"],
                        "invalid_dependency", "Context endpoint lifecycle windows conflict.")

    def eligible(self, candidate, item_id, assessment_time):
        cutoff = timestamp(assessment_time, "assessment_time")
        item = candidate["items"][item_id]
        rev = item["revision"]
        return (item["review_state"] == "reviewed" and rev["status"] == "active"
                and (rev["effective_from"] is None
                     or timestamp(rev["effective_from"], "") <= cutoff)
                and (rev["effective_until"] is None
                     or cutoff < timestamp(rev["effective_until"], ""))
                and not any(e["predecessor_id"] == item_id
                            and timestamp(e["effective_from"], "") <= cutoff
                            for e in candidate["replacements"]))

    def _append(self, candidate, extraction):
        require(isinstance(extraction, Extraction), "extraction", "An extraction is required.")
        profile = "c0" if extraction.strategy == "c0" else self._experimental_profile
        require(profile is not None, "experimental_profile",
                "C1 is unqualified; supply an explicit experimental store profile.")
        if extraction.strategy == "c0":
            # A strategy label cannot turn a different proposal into code-baseline output.
            from .source import extract_code
            require(extraction.proposal == extract_code(extraction.document).proposal,
                    "extraction_profile", "C0 proposal differs from deterministic extraction.")
        extraction = validate_proposal(extraction.document, extraction.proposal)
        doc, mapping = extraction.document, {}
        require(doc.source_id not in candidate["sources"], "source_identity", "Duplicate source ID.")
        self._immutable(self._path("sources", "sha256-" + doc.source_sha256), doc.raw)
        candidate["sources"][doc.source_id] = {
            "name": doc.name, "source_sha256": doc.source_sha256,
            "ancestry": [], "extraction_profile": profile}
        for group in extraction.groups:
            item_id = "item-" + sha256(canonical_bytes([doc.source_id, group["group_id"]]))[:32]
            rev = {key: group[key] for key in
                   ("source_id", "source_sha256", "spans", "text", "scopes", "aliases", "evidence")}
            rev.update(item_id=item_id, status="active", effective_from=None,
                       effective_until=None, ancestry=[], reason="Source intake")
            candidate["items"][item_id] = self._pending(rev)
            mapping[group["group_id"]] = item_id
        for group in extraction.groups:
            for target in group["required_with"]:
                left, right = mapping[group["group_id"]], mapping[target]
                def endpoint(i):
                    return i + "@" + candidate["items"][i]["revision_id"]
                evidence = []
                for item_id in (left, right):
                    rev = candidate["items"][item_id]["revision"]
                    endpoint_units = {u["unit_id"]: u for u in doc.units
                                      if {"start": u["start"], "end": u["end"]} in rev["spans"]}
                    ev = next(e for e in group["evidence"] if e["unit_id"] in endpoint_units)
                    unit = endpoint_units[ev["unit_id"]]
                    start = unit["start"] + len(unit["text"][:unit["text"].index(ev["quote"])].encode("utf-8"))
                    evidence.append({"item_id": item_id,
                                     "revision_id": candidate["items"][item_id]["revision_id"],
                                     "start": start, "end": start + len(ev["quote"].encode("utf-8")),
                                     "quote": ev["quote"]})
                candidate["context_links"].append({
                    "from": endpoint(left), "to": endpoint(right), "evidence": evidence,
                    "kind": ("conservative_source_context" if profile == "c0" else "required_context")})

    def create_draft(self, extractions, expected_digest=None):
        with self._writer():
            require(not self.draft_path.exists() and expected_digest is None,
                    "draft_exists", "A draft already exists; no implicit replacement.")
            extractions = list(extractions)
            require(extractions, "extraction", "Validated extractions required.")
            candidate = {"schema_version": 3, "sources": {}, "items": {},
                         "context_links": [], "replacements": []}
            for extraction in extractions:
                self._append(candidate, extraction)
            return self._save(candidate)

    def add_source(self, extraction, *, expected_digest):
        return self._change(expected_digest, lambda candidate: self._append(candidate, extraction))

    def fork_release(self, release_id, *, expected_digest):
        with self._writer():
            if self.draft_path.exists():
                _, digest = self.load_draft()
                require(expected_digest == digest, "stale_draft", "Candidate changed before fork.")
            else:
                require(expected_digest is None, "stale_draft", "No current draft exists.")
            candidate = self.resolve_release(release_id)["candidate"]
            return self._save(candidate)

    def list_releases(self):
        releases = []
        for path in sorted((self.root / "releases").glob("*.json")):
            release = self.resolve_release(path.stem)
            releases.append({
                "knowledge_version": path.stem,
                "item_count": len(release["candidate"]["items"]),
                "source_count": len(release["candidate"]["sources"]),
                "publication": _copy(release["publication"]),
            })
        return releases

    def source_document(self, source_id):
        candidate, _ = self.load_draft()
        require(isinstance(source_id, str) and source_id in candidate["sources"],
                "source_identity", "Unknown candidate source.")
        source = candidate["sources"][source_id]
        return SourceDocument.from_bytes(self._source(source["source_sha256"]),
                                         name=source["name"], source_id=source_id)

    def item_record(self, item_id):
        """A flat safe copy for editors; persisted items keep revision and review separate."""
        candidate, _ = self.load_draft()
        item = self._item(candidate, item_id)
        return {**item["revision"], **{key: value for key, value in item.items() if key != "revision"}}

    def _pending(self, revision):
        return {"revision_id": _hash(revision), "revision": revision,
                "review_state": "pending", "review": None, "decision_reason": None}

    def load_draft(self):
        raw = self.draft_path.read_bytes()
        candidate = strict_json(raw)
        require(canonical_bytes(candidate) == raw, "draft_encoding", "Draft must use canonical JSON.")
        self._validate(candidate, immutable=True)
        return candidate, sha256(raw)

    def _change(self, expected_digest, operation):
        with self._writer():
            candidate, digest = self.load_draft()
            require(digest == expected_digest, "stale_draft", "Candidate changed; reload before writing.")
            operation(candidate)
            return self._save(candidate)

    def _item(self, candidate, item_id):
        require(isinstance(item_id, str) and item_id in candidate["items"],
                "item_id", "Unknown candidate item.")
        return candidate["items"][item_id]

    def _editable_item(self, candidate, item_id):
        item = self._item(candidate, item_id)
        require(item["review_state"] != "rejected", "rejected_item",
                "Restore this rejected item explicitly before making amendments.")
        return item

    def review_item(self, item_id, *, reviewer, reason, expected_digest):
        require(nonblank(reviewer) and nonblank(reason), "review", "Reviewer and reason required.")
        def change(candidate):
            item = self._item(candidate, item_id)
            require(item["review_state"] != "rejected", "review", "Restore rejected item before review.")
            item.update(review_state="reviewed", decision_reason=None, review={
                "revision_id": item["revision_id"], "reviewer": reviewer, "reason": reason})
        return self._change(expected_digest, change)

    def _published_item_ids(self):
        # Immutable releases are the durable proof, including directly published drafts
        # that were never forked and therefore have no base-release pointer.
        published = set()
        for path in sorted((self.root / "releases").glob("*.json")):
            release = self.resolve_release(path.stem)
            published.update(item_id for item_id, item in release["candidate"]["items"].items()
                             if item["review_state"] == "reviewed")
        return published

    def reject_item(self, item_id, *, reason, expected_digest):
        require(nonblank(reason), "review", "Explicit source-span rejection reason required.")
        def change(candidate):
            item = self._item(candidate, item_id)
            require(item["review_state"] == "pending", "review",
                    "Only pending intake may be rejected; withdraw reviewed content by retiring.")
            require(item_id not in self._published_item_ids(), "published_item",
                    "This logical item was published; use explicit retirement or restoration, not intake rejection.")
            item.update(review_state="rejected", review=None, decision_reason=reason)
        return self._change(expected_digest, change)

    def restore_item(self, item_id, *, reason, expected_digest):
        require(nonblank(reason), "review", "Restoration reason required.")
        def change(candidate):
            item = self._item(candidate, item_id)
            rev = item["revision"]
            rev["reason"] = reason
            rev["status"] = "active"
            rev["effective_from"] = None
            rev["effective_until"] = None
            # Restoration deliberately cancels suppression, never as an incidental expiry.
            candidate["replacements"] = [e for e in candidate["replacements"]
                                         if e["predecessor_id"] != item_id]
            candidate["items"][item_id] = self._pending(rev)
        return self._change(expected_digest, change)

    def edit_item(self, item_id, text, *, reason, expected_digest):
        require(nonblank(text) and nonblank(reason), "edit", "Text and edit reason required.")
        raw = text.encode("utf-8")
        def change(candidate):
            item = self._editable_item(candidate, item_id)
            old = item["revision"]
            sid = "user-" + sha256(canonical_bytes([item_id, item["revision_id"], text, reason]))[:32]
            doc = SourceDocument.from_bytes(raw, name="User amendment", source_id=sid)
            from .source import extract_code
            extraction = extract_code(doc)
            require(len(extraction.groups) == 1, "edit_shape",
                    "One item edit must extract to exactly one item; import a source for structural changes.")
            group = extraction.groups[0]
            self._immutable(self._path("sources", "sha256-" + doc.source_sha256), raw)
            candidate["sources"][sid] = {"name": doc.name, "source_sha256": doc.source_sha256,
                "extraction_profile": "user-amendment",
                "ancestry": [{"item_id": item_id, "revision_id": item["revision_id"],
                              "source_id": old["source_id"], "source_sha256": old["source_sha256"]}]}
            rev = {**old, "source_id": sid, "source_sha256": doc.source_sha256,
                   **{key: group[key] for key in
                      ("spans", "text", "scopes", "aliases", "evidence")},
                   "ancestry": old["ancestry"] + [item["revision_id"]], "reason": reason}
            candidate["items"][item_id] = self._pending(rev)
        return self._change(expected_digest, change)

    def set_lifecycle(self, item_id, *, status="active", effective_from=None,
                      effective_until=None, reason, expected_digest):
        require(nonblank(reason), "lifecycle", "Lifecycle reason required.")
        def change(candidate):
            rev = self._editable_item(candidate, item_id)["revision"]
            rev.update(status=status, effective_from=effective_from,
                       effective_until=effective_until, reason=reason)
            candidate["items"][item_id] = self._pending(rev)
        return self._change(expected_digest, change)

    def update_metadata(self, item_id, *, scopes, aliases, evidence, expected_digest):
        def change(candidate):
            rev = self._editable_item(candidate, item_id)["revision"]
            rev.update(scopes=_copy(scopes), aliases=_copy(aliases), evidence=_copy(evidence),
                       reason="Explicit metadata amendment")
            candidate["items"][item_id] = self._pending(rev)
        return self._change(expected_digest, change)

    def set_context_links(self, links, *, expected_digest):
        def change(candidate):
            candidate["context_links"] = _copy(links)
            # Context interpretation affects the whole candidate's scope safety.
            for item in candidate["items"].values():
                if item["review_state"] != "rejected":
                    item.update(review_state="pending", review=None)
        return self._change(expected_digest, change)

    def replace_item(self, predecessor_id, successor_id, *, effective_from, reason, expected_digest):
        require(nonblank(reason), "replacement", "Replacement reason required.")
        def change(candidate):
            self._editable_item(candidate, predecessor_id)
            self._editable_item(candidate, successor_id)
            require(not any(e["predecessor_id"] == predecessor_id for e in candidate["replacements"]),
                    "replacement", "Cancel an existing replacement explicitly first.")
            candidate["replacements"].append({
                "predecessor_id": predecessor_id, "successor_id": successor_id,
                "effective_from": effective_from, "reason": reason})
            for item_id in (predecessor_id, successor_id):
                item = candidate["items"][item_id]
                item.update(review_state="pending", review=None)
        return self._change(expected_digest, change)

    def cancel_replacement(self, predecessor_id, *, reason, expected_digest):
        require(nonblank(reason), "replacement", "Cancellation reason required.")
        def change(candidate):
            require(any(e["predecessor_id"] == predecessor_id for e in candidate["replacements"]),
                    "replacement", "No replacement to cancel.")
            rev = self._editable_item(candidate, predecessor_id)["revision"]
            candidate["replacements"] = [e for e in candidate["replacements"]
                                         if e["predecessor_id"] != predecessor_id]
            rev["reason"] = reason
            candidate["items"][predecessor_id] = self._pending(rev)
        return self._change(expected_digest, change)

    def publish(self, *, expected_digest, author, reviewer, reason, reviewed_at):
        require(all(nonblank(x) for x in (author, reviewer, reason)),
                "publication", "Explicit author, reviewer and reason required.")
        timestamp(reviewed_at, "reviewed_at")
        with self._writer():
            candidate, digest = self.load_draft()
            require(digest == expected_digest, "stale_draft", "Candidate changed before publication.")
            require(all(i["review_state"] in ("reviewed", "rejected")
                        for i in candidate["items"].values()), "pending_review", "Pending items block release.")
            rejected = {item_id for item_id, item in candidate["items"].items()
                        if item["review_state"] == "rejected"}
            require(not rejected.intersection(self._published_item_ids()), "published_item",
                    "Published logical items cannot be withdrawn through intake rejection.")
            require(all(candidate["items"][e[key]]["review_state"] == "reviewed"
                        for e in candidate["replacements"] for key in ("predecessor_id", "successor_id")),
                    "replacement", "Replacement endpoints must be explicitly reviewed.")
            self.validate_dependencies(candidate)
            record = {"contract": "source-knowledge-release-v1", "candidate": candidate,
                      "candidate_digest": digest, "publication": {
                          "author": author, "reviewer": reviewer, "reason": reason,
                          "reviewed_at": reviewed_at}}
            release_id = _hash(record)
            self._immutable(self._path("releases", release_id), canonical_bytes(record))
            return release_id

    def resolve_release(self, releaseid):
        record = strict_json(self._path("releases", releaseid).read_bytes())
        fields(record, {"contract", "candidate", "candidate_digest", "publication"}, "release")
        require(_hash(record) == releaseid, "release_hash", "Release identity mismatch.")
        require(record["contract"] == "source-knowledge-release-v1", "unsupported_contract",
                "Unsupported release contract.")
        require(sha256(canonical_bytes(record["candidate"])) == record["candidate_digest"],
                "release_hash", "Candidate digest mismatch.")
        publication = fields(record["publication"],
                             {"author", "reviewer", "reason", "reviewed_at"}, "publication")
        require(all(nonblank(publication[x]) for x in ("author", "reviewer", "reason")),
                "publication", "Incomplete publication.")
        timestamp(publication["reviewed_at"], "reviewed_at")
        self._validate(record["candidate"], immutable=True)
        require(all(i["review_state"] in ("reviewed", "rejected")
                    for i in record["candidate"]["items"].values()),
                "pending_review", "Release contains unresolved intake.")
        self.validate_dependencies(record["candidate"])
        return record
