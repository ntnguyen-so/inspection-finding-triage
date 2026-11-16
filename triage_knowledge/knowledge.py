from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path, PureWindowsPath
import re
import tempfile

from .contracts import (
    KnowledgeError, KnowledgeSnapshot, Review, canonical_bytes, fields, identifier,
    nonblank, release_identifier, require, sha256, strict_json, timestamp,
)

CANDIDATE_FIELDS = {"schema_version", "base_release_id", "domain_source", "rubric", "guidance"}
GUIDANCE_FIELDS = {
    "title", "scope", "dimension", "guidance", "evidence_requirements",
    "uncertainty_guidance", "source_refs", "supersedes", "change_reason",
}
DEFAULT_DOMAIN_LOCATOR = r"docs\candidate-pack\candidate-pack\reference\domain_knowledge.md"


def _lifecycle(entry: dict) -> dict:
    return entry.get("lifecycle", {
        "status": "active", "effective_from": None, "effective_until": None,
        "retirement_reason": None,
    })


def _window(entry: dict) -> tuple:
    lifecycle = _lifecycle(entry)
    return tuple(timestamp(lifecycle[field], field) if lifecycle[field] is not None else None
                 for field in ("effective_from", "effective_until"))


def _upgraded(candidate: dict) -> dict:
    result = strict_json(canonical_bytes(candidate))
    if result["schema_version"] == 1:
        for entry in result["guidance"].values():
            entry["lifecycle"] = _lifecycle(entry)
        result["schema_version"] = 2
    return result


def _references(value: object, field: str, owner: str) -> list:
    refs = _strings(value, field)
    require(any(ref.startswith("domain:") for ref in refs)
            and not any(ref.startswith(f"knowledge:{owner}:") for ref in refs),
            "source_ref", "Guidance must cite supplied domain material and cannot cite itself.", field)
    require(refs == sorted(refs), "source_ref", "Source references must be sorted.", field)
    return refs


def domain_sections(raw: bytes) -> dict[str, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise KnowledgeError("domain_encoding", "Domain source must be UTF-8.") from error
    headings = list(re.finditer(r"(?m)^#{1,6}[ \t]+([^\r\n]+)\r?$", text))
    require(bool(headings), "domain_heading", "Domain source has no addressable headings.")
    result = {}
    for position, match in enumerate(headings):
        name = match[1]
        require(name not in result, "domain_heading", "Ambiguous duplicate domain heading.", name)
        end = headings[position + 1].start() if position + 1 < len(headings) else len(text)
        result[name] = text[match.start():end]
    return result


def _strings(value: object, field: str, *, empty: bool = False) -> list:
    require(isinstance(value, list) and (empty or bool(value))
            and all(nonblank(x) for x in value) and len(value) == len(set(value)),
            "schema", "A unique array of nonblank strings is required.", field)
    return value


def validate_candidate(candidate: object, domain_raw: bytes, domain_locator: str) -> dict:
    data = fields(candidate, CANDIDATE_FIELDS, "candidate")
    require(type(data["schema_version"]) is int and data["schema_version"] in {1, 2},
            "schema_version", "Unsupported knowledge schema.", "schema_version")
    require(data["base_release_id"] is None or release_identifier(data["base_release_id"]),
            "release_id", "Invalid base release identity.", "base_release_id")
    source = fields(data["domain_source"], {"source_id", "path", "sha256"}, "domain_source")
    require(source == {"source_id": "domain", "path": domain_locator, "sha256": sha256(domain_raw)},
            "domain_hash", "Domain source does not match the fixed configured source.", "domain_source")
    sections = domain_sections(domain_raw)
    refs = {f"domain:{name}" for name in sections}
    rubric = fields(data["rubric"], {
        "likelihood", "impact", "confirmed_required_function_failure_band",
    }, "rubric")
    declaration = rubric["confirmed_required_function_failure_band"]
    require(isinstance(declaration, list) and len(declaration) == 2
            and all(type(v) is int and 1 <= v <= 10 for v in declaration)
            and declaration[0] <= declaration[1], "rubric",
            "An integer failure-band compatibility declaration is required.", "rubric")
    band_ids = set()
    referenced = []
    for dimension in ("likelihood", "impact"):
        bands = rubric[dimension]
        require(isinstance(bands, list) and bool(bands), "rubric", "Rubric bands are required.", dimension)
        next_minimum = 1
        for item in bands:
            band = fields(item, {"band_id", "minimum", "maximum", "description", "source_refs"},
                          f"rubric.{dimension}")
            name = band["band_id"]
            require(identifier(name) and name not in band_ids, "rubric", "Unique band ID required.", dimension)
            band_ids.add(name)
            require(type(band["minimum"]) is int and type(band["maximum"]) is int
                    and band["minimum"] == next_minimum <= band["maximum"] <= 10,
                    "rubric", "Ordered bands must cover 1-10 without overlap or gaps.", dimension)
            require(nonblank(band["description"]), "rubric", "Band description required.", name)
            next_minimum = band["maximum"] + 1
            refs.add(f"knowledge:{name}:description")
            referenced.extend(_references(band["source_refs"], f"rubric.{name}.source_refs", name))
        require(next_minimum == 11, "rubric", "Rubric must cover 1-10.", dimension)
    require(declaration == [rubric["likelihood"][-1]["minimum"], 10],
            "rubric", "The failure-band declaration must identify the top likelihood band.", "rubric")
    guidance = data["guidance"]
    require(isinstance(guidance, dict), "schema", "Guidance must be an ID-keyed object.", "guidance")
    replaced = {}
    entry_fields = GUIDANCE_FIELDS | ({"lifecycle"} if data["schema_version"] == 2 else set())
    for name, item in guidance.items():
        fields(item, entry_fields, f"guidance.{name}")
    for name, item in guidance.items():
        require(identifier(name) and name not in band_ids, "guidance_id",
                "Guidance ID must be stable and distinct from band IDs.", name)
        entry = fields(item, entry_fields, f"guidance.{name}")
        if data["schema_version"] == 2:
            lifecycle = fields(entry["lifecycle"], {
                "status", "effective_from", "effective_until", "retirement_reason",
            }, f"{name}.lifecycle")
            require(isinstance(lifecycle["status"], str) and lifecycle["status"] in {"active", "retired"},
                    "lifecycle", "Guidance status must be active or retired.", name)
            require((lifecycle["status"] == "active" and lifecycle["retirement_reason"] is None)
                    or (lifecycle["status"] == "retired" and nonblank(lifecycle["retirement_reason"])),
                    "lifecycle", "Retired guidance needs a reason; active guidance must clear it.", name)
            lower, upper = _window(entry)
            require(lower is None or upper is None or lower < upper,
                    "lifecycle_window", "Effective-from must precede effective-until.", name)
        for field in ("title", "guidance", "uncertainty_guidance", "change_reason"):
            require(nonblank(entry[field]), "schema", "A nonblank value is required.", f"{name}.{field}")
        scope = entry["scope"]
        require(scope == "all" or isinstance(scope, list), "scope",
                "Scope must be all or an equipment-type array.", name)
        if scope != "all":
            require(_strings(scope, f"{name}.scope") == sorted(scope), "scope",
                    "Equipment-type scope must be sorted.", name)
        require(isinstance(entry["dimension"], str)
                and entry["dimension"] in {"likelihood", "impact", "evidence", "uncertainty"},
                "dimension", "Only assessment guidance dimensions are supported.", name)
        _strings(entry["evidence_requirements"], f"{name}.evidence_requirements")
        referenced.extend(_references(entry["source_refs"], f"{name}.source_refs", name))
        refs.add(f"knowledge:{name}:guidance")
        for field in ("title", "uncertainty_guidance", "change_reason", "dimension"):
            if field == "change_reason" and data["schema_version"] == 2:
                continue
            refs.add(f"knowledge:{name}:{field}")
        for number, _ in enumerate(entry["evidence_requirements"]):
            refs.add(f"knowledge:{name}:evidence_requirements/{number}")
        for old in _strings(entry["supersedes"], f"{name}.supersedes", empty=True):
            require(old in guidance and old != name, "supersession",
                    "Only another managed entry may be superseded.", f"{name}.supersedes")
            require(guidance[old].get("scope") == scope
                    and guidance[old].get("dimension") == entry["dimension"],
                    "supersession", "Replacement scope and dimension must match.", name)
            require(old not in replaced, "supersession", "Two entries replace the same guidance.", old)
            replaced[old] = name
    require(all(ref in refs for ref in referenced), "source_ref", "Unresolved knowledge source reference.")
    for start in guidance:
        seen = set()
        current = start
        while current in replaced:
            require(current not in seen, "supersession", "Cyclic guidance supersession.", start)
            seen.add(current)
            current = replaced[current]
    live_refs = [ref for bands in (rubric["likelihood"], rubric["impact"])
                 for band in bands for ref in band["source_refs"]]
    live_refs.extend(ref for name, entry in guidance.items()
                     if name not in replaced and _lifecycle(entry)["status"] == "active"
                     for ref in entry["source_refs"])
    unavailable = set(guidance) - set(active_guidance(data))
    require(not any(ref.startswith(f"knowledge:{old}:") for old in unavailable for ref in live_refs),
            "source_ref", "Active knowledge cannot cite retired/superseded guidance; cite its source instead.")
    owners = [(None, band["source_refs"]) for dimension in ("likelihood", "impact")
              for band in rubric[dimension]]
    owners.extend((guidance[name], guidance[name]["source_refs"]) for name in active_guidance(data))
    for owner, source_refs in owners:
        lower, upper = _window(owner) if owner is not None else (None, None)
        for ref in source_refs:
            target = guidance.get(ref.split(":")[1]) if ref.startswith("knowledge:") else None
            if target is not None:
                target_lower, target_upper = _window(target)
                require((target_lower is None or lower is not None and target_lower <= lower)
                        and (target_upper is None or upper is not None and target_upper >= upper),
                        "source_ref_window", "Referenced guidance must cover the citing rule's whole interval.", ref)
    canonical_bytes(data)
    return data


def candidate_digest(candidate: dict) -> str:
    return sha256(canonical_bytes(candidate))


def validate_snapshot(snapshot: KnowledgeSnapshot) -> None:
    require(isinstance(snapshot, KnowledgeSnapshot)
            and type(snapshot.release_bytes) is bytes and type(snapshot.domain_bytes) is bytes,
            "snapshot", "An immutable materialized knowledge snapshot is required.")
    release = fields(strict_json(snapshot.release_bytes),
                     {"release_id", "candidate", "review", "published_at"}, "release")
    require(snapshot.release_bytes == canonical_bytes(release)
            and release_identifier(release["release_id"])
            and "sha256-" + snapshot.content_hash == release["release_id"],
            "release_hash", "Release serialization or content identity differs.")
    candidate = release["candidate"]
    require(isinstance(candidate, dict) and isinstance(candidate.get("domain_source"), dict),
            "schema", "Release candidate and fixed domain source are required.")
    locator = candidate["domain_source"].get("path")
    require(nonblank(locator), "domain_source", "A domain source locator is required.")
    validate_candidate(candidate, snapshot.domain_bytes, locator)
    review = fields(release["review"],
                    {"candidate_digest", "author", "reviewer", "rationale", "reviewed_at"}, "review")
    require(review["candidate_digest"] == candidate_digest(candidate)
            and all(nonblank(review[name]) for name in ("author", "reviewer", "rationale")),
            "review", "Release review does not bind to this candidate.")
    require(timestamp(release["published_at"], "published_at")
            >= timestamp(review["reviewed_at"], "review.reviewed_at"),
            "review", "Publication cannot precede review.")


def active_guidance(candidate: dict) -> tuple[str, ...]:
    replaced = {old for entry in candidate["guidance"].values() for old in entry["supersedes"]}
    return tuple(sorted(name for name, entry in candidate["guidance"].items()
                        if name not in replaced and _lifecycle(entry)["status"] == "active"))


def effective_guidance(candidate: dict, assessment_time: str) -> tuple[tuple[str, ...], dict[str, str]]:
    when = timestamp(assessment_time, "assessment_time")
    guidance = candidate["guidance"]
    excluded = {}
    for name, entry in guidance.items():
        lower, upper = _window(entry)
        if _lifecycle(entry)["status"] == "retired":
            excluded[name] = "retired"
        elif lower is not None and when < lower:
            excluded[name] = "not_yet_effective"
        elif upper is not None and when >= upper:
            excluded[name] = "expired"
    for entry in guidance.values():
        lower, _ = _window(entry)
        if lower is None or when >= lower:
            ancestors = list(entry["supersedes"])
            seen = set()
            while ancestors:
                old = ancestors.pop()
                if old in seen:
                    continue
                seen.add(old)
                excluded.setdefault(old, "superseded")
                ancestors.extend(guidance[old]["supersedes"])
    included = tuple(sorted(set(guidance) - set(excluded)))
    refs = [ref for dimension in ("likelihood", "impact")
            for band in candidate["rubric"][dimension] for ref in band["source_refs"]]
    refs.extend(ref for name in included for ref in guidance[name]["source_refs"])
    require(not any(ref.startswith(f"knowledge:{name}:") for name in excluded for ref in refs),
            "inactive_source_ref", "Effective knowledge cites excluded guidance.")
    return included, dict(sorted(excluded.items()))


def candidate_diff(before: dict | None, after: dict) -> list[dict]:
    result = []

    def walk(left: object, right: object, path: str) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(left.keys() | right.keys()):
                address = path + "/" + key.replace("~", "~0").replace("/", "~1")
                if key not in left:
                    result.append({"field": address, "change": "added", "after": right[key]})
                elif key not in right:
                    result.append({"field": address, "change": "removed", "before": left[key]})
                else:
                    walk(left[key], right[key], address)
        elif left != right:
            result.append({"field": path, "change": "changed", "before": left, "after": right})

    walk({} if before is None else before, after, "")
    return result


def starter_candidate(domain_raw: bytes, domain_locator: str) -> dict:
    descriptions = {
        "likelihood": [
            "Little supported indication of near-term function loss; assess supported margin and service state.",
            "Credible limited degradation with supported margin and no strong progression evidence.",
            "Active degradation or meaningful precursor; near-term progression is uncertain.",
            "Strong progression, advanced damage or recurrent functional interruption.",
            "Direct evidence of imminent loss; a confirmed failed required function is at this top end.",
        ],
        "impact": [
            "Appearance, housekeeping or similarly limited low-energy consequence.",
            "Localized recoverable consequence with justified functional alternatives.",
            "Material operational consequence or moderate protection degradation with remaining capability.",
            "Severe operational, delayed integrity or major-accident exposure considering actual protection.",
            "Extreme consequences supported by the actual scenario, not merely an SCE label or repair cost.",
        ],
    }
    rubric = {"confirmed_required_function_failure_band": [9, 10]}
    for dimension, texts in descriptions.items():
        rubric[dimension] = [{
            "band_id": f"{dimension}-{2 * index + 1}-{2 * index + 2}",
            "minimum": 2 * index + 1, "maximum": 2 * index + 2,
            "description": text, "source_refs": [f"domain:What moves {dimension}"],
        } for index, text in enumerate(texts)]
    candidate = {
        "schema_version": 2, "base_release_id": None,
        "domain_source": {"source_id": "domain", "path": domain_locator, "sha256": sha256(domain_raw)},
        "rubric": rubric,
        "guidance": {"psv-assessment": {
            "title": "PSV evidence and functional assessment", "scope": ["Pressure Safety Valve"],
            "dimension": "evidence",
            "guidance": "Assess the observed mechanism and evidence of the required relief function. "
                        "A documentation defect alone does not establish a functional failure. "
                        "Use the equipment-specific engineer comment and distinguish confirmed facts "
                        "from suspected mechanisms or missing evidence.",
            "evidence_requirements": [
                "Inspection observations and any stated functional-test or certification evidence.",
                "The primary equipment comment and relevant selected observations.",
            ],
            "uncertainty_guidance": "State missing evidence explicitly; do not infer a healthy "
                                    "protection function or absence of a deviation from silence.",
            "source_refs": ["domain:Output expectations", "domain:The two questions"],
            "supersedes": [],
            "lifecycle": _lifecycle({}),
            "change_reason": "Initial prototype guidance and ordinal rubric require explicit content review; "
                             "they are not calibrated probabilities or expert-certified scores.",
        }},
    }
    return validate_candidate(candidate, domain_raw, domain_locator)


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise KnowledgeError("storage_read", "Could not read the configured knowledge artifact.",
                             str(path)) from error


def _write(path: Path, raw: bytes, *, replace: bool) -> None:
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".knowledge-", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    except FileExistsError as error:
        raise KnowledgeError("already_exists", "The destination already exists.", str(path)) from error
    except OSError as error:
        raise KnowledgeError("storage_write", "Could not persist the knowledge artifact.",
                             str(path)) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as error:
                raise KnowledgeError(
                    "storage_cleanup", "Temporary-file cleanup failed; the destination may exist. "
                    "Inspect its identity before retrying.", str(path),
                ) from error


class KnowledgeStore:
    def __init__(self, root: Path, domain_path: Path, *, domain_locator: str | None = None):
        self.root = Path(root)
        self.domain_path = Path(domain_path)
        locator = DEFAULT_DOMAIN_LOCATOR if domain_locator is None else domain_locator
        require(nonblank(locator), "domain_locator", "A stable logical domain locator is required.")
        logical = PureWindowsPath(locator)
        require(not logical.drive and not logical.is_absolute() and ".." not in logical.parts,
                "domain_locator", "The logical domain locator must be repository-relative.")
        self.domain_locator = str(logical)

    @property
    def draft_path(self) -> Path:
        return self.root / "drafts" / "working.json"

    def validate(self, candidate: dict) -> dict:
        return validate_candidate(candidate, _read(self.domain_path), self.domain_locator)

    def load_draft(self) -> tuple[dict, str]:
        candidate = self.validate(strict_json(_read(self.draft_path)))
        return candidate, candidate_digest(candidate)

    def save_draft(self, candidate: dict, *, expected_digest: str | None) -> str:
        raw = canonical_bytes(self.validate(candidate))
        if self.draft_path.exists():
            _, actual = self.load_draft()
            require(expected_digest == actual, "stale_draft",
                    "The saved draft changed; reload before saving.", "candidate_digest")
            _write(self.draft_path, raw, replace=True)
        else:
            require(expected_digest is None, "stale_draft", "The expected draft no longer exists.")
            _write(self.draft_path, raw, replace=False)
        return sha256(raw)

    def resolve_knowledge(self, knowledge_version: str) -> KnowledgeSnapshot:
        require(release_identifier(knowledge_version), "release_id",
                "An exact immutable release ID is required.", "knowledge_version")
        raw = _read(self.root / "releases" / f"{knowledge_version}.json")
        domain_raw = _read(self.domain_path)
        snapshot = KnowledgeSnapshot(raw, domain_raw)
        validate_snapshot(snapshot)
        require(snapshot.knowledge_version == knowledge_version, "release_hash",
                "Release differs from the requested identity.")
        self.validate(snapshot.candidate)
        return snapshot

    def publish(self, review: Review, *, published_at: str) -> str:
        require(isinstance(review, Review), "review", "An explicit candidate-bound review is required.")
        candidate, digest = self.load_draft()
        require(candidate["schema_version"] == 2, "schema_upgrade",
                "Explicitly upgrade the legacy draft before publishing a new release.")
        require(review.candidate_digest == digest, "stale_review",
                "Review confirmation does not match the saved candidate.", "candidate_digest")
        require(all(nonblank(value) for value in (review.author, review.reviewer, review.rationale)),
                "review", "Declared author, reviewer and review rationale are required.")
        reviewed = timestamp(review.reviewed_at, "reviewed_at")
        require(timestamp(published_at, "published_at") >= reviewed,
                "review", "Publication cannot precede review.")
        if candidate["base_release_id"] is not None:
            base = self.resolve_knowledge(candidate["base_release_id"])
            require(set(base.candidate["guidance"]) <= set(candidate["guidance"]),
                    "guidance_removal", "Retire published guidance instead of deleting its ID.")
        body = {"candidate": candidate, "review": asdict(review), "published_at": published_at}
        version = "sha256-" + sha256(canonical_bytes(body))
        raw = canonical_bytes({**body, "release_id": version})
        path = self.root / "releases" / f"{version}.json"
        if path.exists():
            require(_read(path) == raw, "release_hash", "Existing release has different bytes.")
            raise KnowledgeError("already_exists", "This exact release artifact is already published.", version)
        _write(path, raw, replace=False)
        return version

    def fork_release(self, version: str, *, expected_digest: str | None) -> str:
        candidate = _upgraded(self.resolve_knowledge(version).candidate)
        candidate["base_release_id"] = version
        return self.save_draft(candidate, expected_digest=expected_digest)

    def upgrade_draft(self, *, expected_digest: str) -> str:
        candidate, _ = self.load_draft()
        require(candidate["schema_version"] == 1, "schema_upgrade", "The draft already uses schema 2.")
        return self.save_draft(_upgraded(candidate), expected_digest=expected_digest)

    def retire_guidance(self, name: str, reason: str, *, expected_digest: str) -> str:
        candidate, _ = self.load_draft()
        require(candidate["schema_version"] == 2, "schema_upgrade", "Upgrade the draft before retiring guidance.")
        require(identifier(name) and name in candidate["guidance"] and nonblank(reason),
                "lifecycle", "An existing guidance ID and nonblank retirement reason are required.", str(name))
        entry = candidate["guidance"][name]
        require(entry["lifecycle"]["status"] == "active", "lifecycle", "Guidance is already retired.", name)
        entry["lifecycle"].update(status="retired", retirement_reason=reason)
        return self.save_draft(candidate, expected_digest=expected_digest)

    def recover_draft(self, replacement: dict, *, expected_raw_sha256: str) -> str:
        raw = _read(self.draft_path)
        require(sha256(raw) == expected_raw_sha256, "stale_draft",
                "The invalid draft changed before recovery.")
        try:
            self.load_draft()
        except KnowledgeError:
            pass
        else:
            raise KnowledgeError("draft_recovery", "The saved draft is valid; use ordinary editing.")
        replacement_raw = canonical_bytes(self.validate(replacement))
        archive = self.root / "drafts" / "archive" / f"{expected_raw_sha256}.json"
        if archive.exists():
            require(_read(archive) == raw, "draft_recovery", "The recovery archive has different bytes.")
        else:
            _write(archive, raw, replace=False)
        _write(self.draft_path, replacement_raw, replace=True)
        return sha256(replacement_raw)
