"""Local Streamlit UI for reviewed source-first knowledge maintenance."""
from __future__ import annotations

from datetime import datetime, timezone
from difflib import unified_diff
import json
from pathlib import Path

from triage_knowledge.contracts import KnowledgeError, TableSource, canonical_bytes, strict_json
from triage_knowledge.source import SourceDocument, extract_code
from triage_knowledge.source_cli import DEFAULT_DOMAIN, DEFAULT_STORE
from triage_knowledge.source_store import SourceKnowledgeStore
from triage_knowledge.retrieval import binding_from_tables, get_triage_knowledge, strategy_binding


def main() -> None:
    """Render the local editor; publication remains an unauthenticated declaration."""
    import streamlit as st

    st.set_page_config(page_title="Source-first Knowledge", layout="wide")
    st.title("Source-first Knowledge")
    st.caption("Exact user sources, reviewed active knowledge. Workflow owns L/I assessment and urgency.")
    root = st.sidebar.text_input("Source-first store", str(DEFAULT_STORE))
    domain = st.sidebar.text_input("Initial domain path", str(DEFAULT_DOMAIN))
    if st.session_state.get("source_store_identity") != root:
        for key in list(st.session_state):
            if key.startswith("source_"):
                del st.session_state[key]
        st.session_state["source_store_identity"] = root
    store = SourceKnowledgeStore(Path(root))
    st.warning("Local, unauthenticated review declarations. Publish does not deploy or approve maintenance.")
    st.caption("Workflow deployment status: unknown. An operator must separately pin a compatible release.")
    st.info("Code extraction is the default. Copilot extraction is experimental and unqualified; "
            "there is no automatic paid extraction or scoring in this editor.")
    with st.sidebar.expander("Storage and saved releases"):
        st.caption("Only the configured source-first store is read or modified.")
        st.code(str(store.root.resolve()), language=None)
        try:
            releases = store.list_releases()
            if releases:
                st.json(releases)
            else:
                st.caption("No immutable release yet. A draft cannot be used for triage.")
        except (ValueError, OSError) as error:
            st.error(str(error))

    def show_error(error: Exception) -> None:
        code = error.code if isinstance(error, KnowledgeError) else type(error).__name__
        st.error(f"{code}: {error}")

    def reload_draft() -> None:
        candidate, digest = store.load_draft()
        st.session_state["source_candidate"] = canonical_bytes(candidate)
        st.session_state["source_digest"] = digest

    def updated() -> None:
        reload_draft()
        st.rerun()

    with st.expander("Import user knowledge", expanded=not store.draft_path.exists()):
        st.caption("Supplied domain only for the initial exercise; amendments need explicit user "
                   "source lineage and review. Synthetic evaluation documents never belong here.")
        name = st.text_input("User source name", "User amendment")
        upload = st.file_uploader("UTF-8 Markdown or plain text", type=["md", "txt"])
        submitted = st.text_area("Or submit exact source text", key="source_submitted_text")
        initial = st.button("Import initial domain")
        addition = st.button("Import submitted source", disabled=upload is None and not submitted)
        if initial or addition:
            try:
                if initial:
                    document = SourceDocument.from_bytes(Path(domain).read_bytes(),
                                                         name="Supplied domain", source_id="domain")
                else:
                    raw = upload.getvalue() if upload is not None else submitted.encode("utf-8")
                    document = SourceDocument.from_bytes(raw, name=name)
                extraction = extract_code(document)
                if store.draft_path.exists():
                    if "source_digest" not in st.session_state:
                        reload_draft()
                    store.add_source(extraction, expected_digest=st.session_state["source_digest"])
                else:
                    store.create_draft([extraction])
                updated()
            except (ValueError, OSError) as error:
                show_error(error)

    fork_version = st.sidebar.text_input("Reviewed release to open for editing")
    st.sidebar.caption("Opening replaces the saved draft; immutable releases remain unchanged.")
    if st.sidebar.button("Open release as editable draft"):
        try:
            if store.draft_path.exists() and "source_digest" not in st.session_state:
                reload_draft()
            store.fork_release(fork_version, expected_digest=st.session_state.get("source_digest"))
            updated()
        except (KnowledgeError, OSError) as error:
            show_error(error)

    if not store.draft_path.exists():
        st.info("No source-first draft. Import creates pending knowledge, not a release.")
        return
    if st.sidebar.button("Reload saved draft"):
        try:
            reload_draft()
            st.rerun()
        except (KnowledgeError, OSError) as error:
            show_error(error)
    try:
        if "source_candidate" not in st.session_state:
            reload_draft()
        candidate = strict_json(st.session_state["source_candidate"])
        digest = st.session_state["source_digest"]
    except (KnowledgeError, OSError) as error:
        show_error(error)
        return

    st.caption("Loaded candidate: " + digest)
    st.dataframe([{
        "Item": item_id,
        "Source": candidate["sources"][entry["revision"]["source_id"]]["name"],
        "Review": entry["review_state"],
        "Lifecycle": entry["revision"]["status"],
        "Text": entry["revision"]["text"][:160].replace("\n", " "),
    } for item_id, entry in sorted(candidate["items"].items())], hide_index=True)
    inspect, relationships, publication, preview = st.tabs(
        ["Cases and edits", "Context and replacement", "Review and publish", "Active retrieval preview"])
    with inspect:
        identifiers = sorted(candidate["items"])
        if not identifiers:
            st.info("No items in the draft.")
        else:
            selected = st.selectbox("Knowledge item", identifiers)
            item = candidate["items"][selected]["revision"]
            st.json(item)
            with st.expander("Exact source units and original bytes"):
                try:
                    document = store.source_document(item["source_id"])
                    st.code(document.raw.decode("utf-8"), language="markdown")
                    st.json(document.units)
                except (KnowledgeError, OSError) as error:
                    show_error(error)
            with st.form("source_edit_" + selected + digest):
                revised = st.text_area("Revised source text", item["text"], height=200)
                reason = st.text_input("Edit reason")
                st.caption("Saving re-extracts scope, aliases and source evidence from this text. "
                           "Structural multi-item changes must be imported as a new source.")
                if st.form_submit_button("Preview source edit diff"):
                    difference = "".join(unified_diff(
                        item["text"].splitlines(keepends=True), revised.splitlines(keepends=True),
                        fromfile="Current revision", tofile="Proposed user revision"))
                    st.code(difference or "No text changes.", language="diff")
                if st.form_submit_button("Save as new user revision"):
                    try:
                        store.edit_item(selected, revised, reason=reason, expected_digest=digest)
                        updated()
                    except (KnowledgeError, OSError) as error:
                        show_error(error)
            with st.form("source_metadata_" + selected + digest):
                scopes = st.text_area("Literal equipment-type scopes (one per line; blank is general)",
                                      "\n".join(item["scopes"]))
                aliases = st.text_area("Source-written aliases (one per line)", "\n".join(item["aliases"]))
                evidence = st.text_area("Evidence JSON: unit_id and exact quote",
                                       "[]")
                st.caption("Literal evidence proves location, not entailment. Unit-ID extraction "
                           "uses a code-expanded unit, not a model-selected phrase. "
                           "Read conditions and exceptions.")
                if st.form_submit_button("Save metadata for review"):
                    try:
                        store.update_metadata(
                            selected, scopes=[v.strip() for v in scopes.splitlines() if v.strip()],
                            aliases=[v.strip() for v in aliases.splitlines() if v.strip()],
                            evidence=strict_json(evidence), expected_digest=digest)
                        updated()
                    except (KnowledgeError, OSError) as error:
                        show_error(error)
            with st.form("source_lifecycle_" + selected + digest):
                state = st.selectbox("Desired lifecycle", ["active", "retired"])
                lower = st.text_input("Effective from (inclusive ISO time; blank is unbounded)")
                upper = st.text_input("Effective until (exclusive ISO time; blank is unbounded)")
                reason = st.text_input("Lifecycle or rejection reason")
                save = st.form_submit_button("Save lifecycle for review")
                reject = st.form_submit_button("Reject pending intake with reason")
                restore = st.form_submit_button("Restore rejected intake for fresh review")
                if save or reject or restore:
                    try:
                        if reject:
                            store.reject_item(selected, reason=reason, expected_digest=digest)
                        elif restore:
                            store.restore_item(selected, reason=reason, expected_digest=digest)
                        else:
                            store.set_lifecycle(
                                selected, status=state, effective_from=lower or None,
                                effective_until=upper or None, reason=reason, expected_digest=digest)
                        updated()
                    except (KnowledgeError, OSError) as error:
                        show_error(error)

    with relationships:
        st.caption("Edges bind exact item/revision endpoints. Editing an endpoint requires reviewed rebinding.")
        with st.expander("Complete candidate, including context and replacement edges"):
            st.json(candidate)
        links = st.text_area("Replace context links with JSON (empty array explicitly clears all links)", "[]")
        if st.button("Save context links for review"):
            try:
                store.set_context_links(strict_json(links), expected_digest=digest)
                updated()
            except (KnowledgeError, OSError) as error:
                show_error(error)
        with st.form("source_replacement_" + digest):
            predecessor = st.text_input("Predecessor item ID")
            successor = st.text_input("Successor item ID")
            start = st.text_input("Replacement starts (inclusive ISO time)")
            reason = st.text_input("Replacement reason")
            st.caption("Retiring or expiring a successor does not resurrect its predecessor. "
                       "Check future gaps before publishing.")
            replace = st.form_submit_button("Save replacement for review")
            cancel = st.form_submit_button("Cancel replacement deliberately")
            if replace or cancel:
                try:
                    if cancel:
                        store.cancel_replacement(predecessor, reason=reason, expected_digest=digest)
                    else:
                        store.replace_item(predecessor, successor, effective_from=start,
                                           reason=reason, expected_digest=digest)
                    updated()
                except (KnowledgeError, OSError) as error:
                    show_error(error)

    with publication:
        reviewer = st.text_input("Reviewer")
        reason = st.text_area("Review justification")
        if candidate["items"]:
            item_id = st.selectbox("Item reviewed with its source and linked context", sorted(candidate["items"]))
            if st.button("Record item review"):
                try:
                    store.review_item(item_id, reviewer=reviewer, reason=reason, expected_digest=digest)
                    updated()
                except (KnowledgeError, OSError) as error:
                    show_error(error)
        author = st.text_input("Author")
        confirm = st.checkbox("I reviewed this exact candidate, all cases, scope, conflicts and context",
                              key="source_publish_confirm_" + digest)
        if st.button("Publish exact reviewed candidate", disabled=not confirm):
            try:
                version = store.publish(expected_digest=digest, author=author, reviewer=reviewer,
                                        reason=reason, reviewed_at=datetime.now(timezone.utc).isoformat())
                st.success("Published immutable release; workflow pin is unchanged.")
                st.code(version, language=None)
            except (KnowledgeError, OSError) as error:
                show_error(error)

    with preview:
        version = st.text_input("Pinned release ID")
        cutoff = st.text_input("Assessment time (explicit timezone-aware ISO value)")
        findings_path = st.text_input("Selected findings CSV path")
        registry_path = st.text_input("Registry CSV path")
        limit = st.number_input("Maximum provider knowledge bytes", min_value=1, value=64_000)
        st.caption("This preview uses the same retrieval API and current displayed strategy. No model call.")
        st.json(strategy_binding())
        if st.button("Preview eligible relevant knowledge"):
            try:
                findings = TableSource.from_bytes(Path(findings_path).read_bytes(),
                                                  source_id="findings", kind="finding_input")
                registry = TableSource.from_bytes(Path(registry_path).read_bytes(),
                                                  source_id="registry", kind="registry_input")
                query = {"findings": {r["finding_id"]: r for r in findings.rows},
                         "registry": {r["equipment_id"]: r for r in registry.rows}}
                result = get_triage_knowledge(
                    store, query, knowledge_version=version, assessment_time=cutoff,
                    expected_strategy=strategy_binding(),
                    allowed_input_binding=binding_from_tables(findings, registry), max_bytes=int(limit))
                st.json(result.to_dict())
            except (KnowledgeError, OSError) as error:
                show_error(error)


if __name__ == "__main__":
    main()
