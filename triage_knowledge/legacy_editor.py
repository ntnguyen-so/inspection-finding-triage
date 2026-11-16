from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from triage_knowledge.__main__ import DOMAIN_PATH
from triage_knowledge.contracts import KnowledgeError, Review, canonical_bytes, identifier, sha256, strict_json
from triage_knowledge.knowledge import (
    KnowledgeStore, _lifecycle, candidate_diff, domain_sections, effective_guidance, starter_candidate,
)


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Triage Knowledge Editor", layout="wide")
    st.title("Triage Knowledge Editor")
    st.caption("Local knowledge maintenance. No model calls, ticket editing or operational approval.")
    root = st.sidebar.text_input("Knowledge store directory", "knowledge")
    domain = st.sidebar.text_input("Configured domain source (read-only)", DOMAIN_PATH)
    store = KnowledgeStore(Path(root), Path(domain))
    identity = (root, domain)
    if st.session_state.get("store_identity") != identity:
        for key in list(st.session_state):
            if key not in {"store_identity"} and key.startswith(("editor_", "guidance_", "rubric_", "review_")):
                del st.session_state[key]
        st.session_state["store_identity"] = identity

    def show_error(error: Exception) -> None:
        if isinstance(error, KnowledgeError):
            st.error(f"{error.code}: {error.field}: {error}")
        else:
            st.error("Could not read or write the configured artifact. Check the local paths and permissions.")

    def load() -> None:
        candidate, digest = store.load_draft()
        st.session_state["editor_candidate"] = canonical_bytes(candidate)
        st.session_state["editor_digest"] = digest

    def reset_form_state() -> None:
        for key in list(st.session_state):
            if key.startswith(("guidance_", "rubric_", "review_")):
                del st.session_state[key]

    def offer_recovery() -> None:
        try:
            raw_digest = sha256(store.draft_path.read_bytes())
            st.code(raw_digest, language=None)
            confirmed = st.checkbox("Archive the invalid draft and reset to an unapproved initial draft",
                                     key="editor_recovery_" + raw_digest)
            if st.button("Archive invalid draft and reset", disabled=not confirmed):
                replacement = starter_candidate(store.domain_path.read_bytes(), store.domain_locator)
                store.recover_draft(replacement, expected_raw_sha256=raw_digest)
                reset_form_state()
                load()
                st.rerun()
        except (KnowledgeError, OSError) as error:
            show_error(error)

    if not store.draft_path.exists():
        st.info("No draft exists. Creating a draft does not publish or approve any knowledge.")
        if st.button("Create initial draft"):
            try:
                candidate = starter_candidate(store.domain_path.read_bytes(), store.domain_locator)
                store.save_draft(candidate, expected_digest=None)
                load()
                st.rerun()
            except (KnowledgeError, OSError) as error:
                show_error(error)
        return
    try:
        store.load_draft()
        if "editor_candidate" not in st.session_state:
            load()
        candidate = strict_json(st.session_state["editor_candidate"])
        domain_raw = store.domain_path.read_bytes()
        sections = domain_sections(domain_raw)
    except (KnowledgeError, OSError) as error:
        show_error(error)
        offer_recovery()
        return
    if st.sidebar.button("Reload saved draft (discard unsaved edits)"):
        try:
            load()
            reset_form_state()
            st.rerun()
        except (KnowledgeError, OSError) as error:
            show_error(error)
            offer_recovery()
            return
    st.caption(f"Loaded candidate: {st.session_state['editor_digest']}")
    if candidate["schema_version"] == 1:
        st.info("This legacy draft needs an explicit schema-2 upgrade. Original guidance and "
                "release files are preserved; previous review confirmation will not apply.")
        if st.button("Upgrade saved draft and reload (discard unsaved edits)"):
            try:
                store.upgrade_draft(expected_digest=st.session_state["editor_digest"])
                reset_form_state()
                load()
                st.rerun()
            except (KnowledgeError, OSError) as error:
                show_error(error)
        return
    st.warning("Review declarations are local and unauthenticated. Every maintenance draft still needs human approval.")
    st.caption("Editing or retiring affects only the next reviewed release. Workflow must pin its new ID; "
               "older pinned releases are not globally revoked.")
    st.caption("One active editor writer only. Saving validates the whole draft; "
               "use Reload to explicitly discard an incomplete unsaved topic.")
    with st.expander("Original domain source (unchanged)"):
        st.code(domain_raw.decode("utf-8"), language="markdown")
    guidance_tab, rubric_tab, review_tab = st.tabs(["Guidance", "L/I rubric", "Review and publish"])

    def save(updated: dict) -> None:
        st.session_state["editor_candidate"] = canonical_bytes(updated)
        try:
            digest = store.save_draft(updated, expected_digest=st.session_state["editor_digest"])
            st.session_state["editor_digest"] = digest
            st.success("Draft saved and validated. It is not published.")
        except (KnowledgeError, OSError) as error:
            show_error(error)

    with guidance_tab:
        new_id = st.text_input("New guidance ID", key="editor_new_id")
        if st.button("Add guidance to unsaved draft"):
            if not identifier(new_id) or new_id in candidate["guidance"]:
                st.error("Use a new lowercase guidance ID with letters, digits, hyphens or underscores.")
            else:
                candidate["guidance"][new_id] = {
                    "title": "", "scope": "all", "dimension": "evidence", "guidance": "",
                    "evidence_requirements": [], "uncertainty_guidance": "",
                    "source_refs": [], "supersedes": [], "change_reason": "",
                    "lifecycle": _lifecycle({}),
                }
                st.session_state["editor_candidate"] = canonical_bytes(candidate)
                st.session_state["editor_selected"] = new_id
                st.rerun()
        names = sorted(candidate["guidance"])
        if names:
            if st.session_state.get("editor_selected") not in names:
                st.session_state["editor_selected"] = names[0]
            name = st.selectbox("Guidance topic", names, key="editor_selected")
            entry = candidate["guidance"][name]
            key = "guidance_" + name + "_"
            with st.form("guidance_form_" + name):
                title = st.text_input("Title", entry["title"], key=key + "title")
                all_types = st.checkbox("Apply to all equipment types", entry["scope"] == "all", key=key + "all")
                scope = st.text_area("Equipment types (one per line)",
                                     "" if entry["scope"] == "all" else "\n".join(entry["scope"]), key=key + "scope")
                dimensions = ["likelihood", "impact", "evidence", "uncertainty"]
                dimension = st.selectbox("Assessment dimension", dimensions,
                                          index=dimensions.index(entry["dimension"]), key=key + "dimension")
                guidance = st.text_area("Assessment guidance", entry["guidance"], key=key + "text", height=150)
                evidence = st.text_area("Evidence requirements (one per line)",
                                        "\n".join(entry["evidence_requirements"]), key=key + "evidence")
                uncertainty = st.text_area("Uncertainty guidance", entry["uncertainty_guidance"], key=key + "uncertainty")
                st.caption("Source headings: " + "; ".join("domain:" + heading for heading in sections))
                refs = st.text_area("Source references (one per line)",
                                    "\n".join(entry["source_refs"]), key=key + "refs")
                supersedes = st.multiselect("Superseded managed entries (same scope and dimension)",
                                             [value for value in names if value != name],
                                             default=entry["supersedes"], key=key + "supersedes")
                reason = st.text_area("Reason for change", entry["change_reason"], key=key + "reason")
                lifecycle = entry["lifecycle"]
                st.caption("To remove guidance, retire it, give a reason, save, then review/publish. "
                           "Times are inclusive-from / exclusive-until at the run's explicit assessment time.")
                retired = st.checkbox("Retire guidance (remove from workflow context)",
                                      lifecycle["status"] == "retired", key=key + "retired")
                lower = st.text_input("Effective from (timezone-aware ISO timestamp; blank is unbounded)",
                                      lifecycle["effective_from"] or "", key=key + "from")
                upper = st.text_input("Effective until (timezone-aware ISO timestamp; blank is unbounded)",
                                      lifecycle["effective_until"] or "", key=key + "until")
                retirement_reason = st.text_area("Retirement reason (clear when restoring active guidance)",
                                                 lifecycle["retirement_reason"] or "", key=key + "retirement")
                if st.form_submit_button("Validate and save guidance"):
                    candidate["guidance"][name] = {
                        "title": title, "scope": "all" if all_types else sorted(set(_lines(scope))),
                        "dimension": dimension, "guidance": guidance,
                        "evidence_requirements": _lines(evidence), "uncertainty_guidance": uncertainty,
                        "source_refs": sorted(set(_lines(refs))), "supersedes": sorted(supersedes),
                        "change_reason": reason,
                        "lifecycle": {
                            "status": "retired" if retired else "active",
                            "effective_from": lower if lower.strip() else None,
                            "effective_until": upper if upper.strip() else None,
                            "retirement_reason": retirement_reason if retirement_reason.strip() else None,
                        },
                    }
                    save(candidate)
    with rubric_tab:
        st.info("Ordinal prototype anchors, not calibrated failure probabilities. Workflow owns executable invariants.")
        dimension = st.selectbox("Rubric dimension", ["likelihood", "impact"], key="editor_rubric_dimension")
        with st.form("rubric_form_" + dimension):
            edited = []
            for band in candidate["rubric"][dimension]:
                st.subheader(band["band_id"])
                key = "rubric_" + band["band_id"] + "_"
                minimum = st.number_input("Minimum", min_value=1, max_value=10,
                                           value=band["minimum"], step=1, key=key + "minimum")
                maximum = st.number_input("Maximum", min_value=1, max_value=10,
                                           value=band["maximum"], step=1, key=key + "maximum")
                description = st.text_area("Band description", band["description"], key=key + "description")
                refs = st.text_area("Band source references (one per line)",
                                    "\n".join(band["source_refs"]), key=key + "refs")
                edited.append({**band, "minimum": minimum, "maximum": maximum,
                               "description": description, "source_refs": sorted(set(_lines(refs)))})
            if st.form_submit_button("Validate and save rubric"):
                candidate["rubric"][dimension] = edited
                save(candidate)
        st.caption("Confirmed required-function failure compatibility band: "
                   + str(candidate["rubric"]["confirmed_required_function_failure_band"])
                   + ". Changing the workflow invariant requires a coordinated code-policy change.")
    with review_tab:
        st.caption("Preview and diff refer to the saved draft, not unsubmitted form fields.")
        try:
            saved, digest = store.load_draft()
            stale = digest != st.session_state["editor_digest"]
            unsaved = st.session_state["editor_candidate"] != canonical_bytes(saved)
            if stale:
                st.error("The saved draft changed in another tab. Reload before reviewing or publishing.")
            if unsaved:
                st.error("Submitted edits are not saved and validated. Correct them or explicitly Reload before publishing.")
            base_id = saved["base_release_id"]
            base = store.resolve_knowledge(base_id).candidate if base_id else None
            st.subheader("Changes against base release")
            st.json(candidate_diff(base, saved))
            st.subheader("Time-specific eligibility preview")
            preview_time = st.text_input("Preview assessment time", datetime.now(timezone.utc).isoformat(),
                                         key="review_preview_time")
            st.caption("Local audit preview, not provider payload. Excluded text and maintenance metadata "
                       "are not sent to workflow assessment. Runtime uses its own explicit configured time.")
            preview_valid = True
            try:
                included, excluded = effective_guidance(saved, preview_time)
                st.json({"active_guidance_ids": included, "excluded_guidance": excluded,
                         "rubric": saved["rubric"],
                         "guidance": {key: saved["guidance"][key] for key in included}})
            except KnowledgeError as error:
                preview_valid = False
                show_error(error)
            author = st.text_input("Declared author", key="review_author")
            reviewer = st.text_input("Declared reviewer", key="review_reviewer")
            rationale = st.text_area("Review rationale", key="review_rationale")
            confirmed = st.checkbox("I reviewed this exact saved candidate and its source references",
                                     key="review_confirmation_" + digest)
            if st.button("Publish reviewed release",
                         disabled=stale or unsaved or not preview_valid
                         or not (confirmed and author.strip() and reviewer.strip() and rationale.strip())):
                now = datetime.now(timezone.utc).isoformat()
                version = store.publish(Review(digest, author, reviewer, rationale, now), published_at=now)
                st.session_state["editor_last_release"] = version
                st.success("Published an immutable release. Existing workflow configurations are unchanged.")
            version = st.session_state.get("editor_last_release")
            if version:
                st.code(version, language=None)
                if st.button("Start next draft from this release"):
                    store.fork_release(version, expected_digest=st.session_state["editor_digest"])
                    reset_form_state()
                    load()
                    st.rerun()
        except (KnowledgeError, OSError) as error:
            show_error(error)


if __name__ == "__main__":
    main()
