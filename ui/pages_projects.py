"""Streamlit UI seam for local Projects and Project Sources.

AG-84B-R1 intentionally keeps this module as a thin UI wrapper over
``core.project_sources``. It creates/lists local manifests and promotes an
already-built session-local ``DocumentReviewContext`` into compact Project Source
manifests without adding public validation, provider/model calls, prompt changes,
connectors, caches, source indexes, or pipeline/orchestrator hooks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.document_review import DocumentReviewContext
from core.project_sources import (
    DEFAULT_PROJECT_SOURCE_STORAGE_ROOT,
    Project,
    ProjectSource,
    ProjectSourcePromotionResult,
    add_project_source_from_document_review,
    create_project,
    list_project_sources,
    list_projects,
    load_project,
    remove_project_source,
)
from ui.context import UIContext

_PROJECTS_SELECTED_KEY = "projects_selected_project_id"
_DOC_REVIEW_TARGET_KEY = "document_review_save_project_id"
_DOC_REVIEW_INLINE_NAME_KEY = "document_review_save_new_project_name"
_DOC_REVIEW_INLINE_DESCRIPTION_KEY = "document_review_save_new_project_description"
_DOC_REVIEW_TITLE_KEY = "document_review_project_source_title"
_BOUNDARY_ITEMS = (
    "Local/private manifests under output/project_sources/.",
    "Raw source files are not copied by default.",
    "Raw normalized document text is not persisted by default.",
    "Saved Project Sources are not public validation.",
    "No retrieval integration yet; Project Sources are not automatically injected into answers.",
    "No connectors, Project Instructions, snapshots, saved reports, or thread report generator yet.",
)


def project_source_boundary_caption() -> str:
    """Return the user-facing storage/privacy boundary caption."""

    return " ".join(_BOUNDARY_ITEMS)


def summarize_source_obligations(project_source: ProjectSource) -> str:
    """Return a compact, stable summary of source-obligation counts."""

    summary = project_source.source_obligation_summary or {}
    ordered_fields = (
        ("findings", summary.get("finding_count")),
        ("labels", summary.get("label_counts")),
        ("claim types", summary.get("claim_type_counts")),
        ("obligations", summary.get("obligation_counts")),
        ("evidence roles", summary.get("evidence_role_counts")),
        ("validation needs", summary.get("validation_need_counts")),
        ("risk levels", summary.get("risk_level_counts")),
    )
    parts: list[str] = []
    for label, value in ordered_fields:
        if isinstance(value, dict):
            total = sum(int(count) for count in value.values() if isinstance(count, int))
            unique = len(value)
            parts.append(f"{label}: {total} across {unique}")
        elif value is not None:
            parts.append(f"{label}: {value}")
    if summary.get("validation_posture"):
        parts.append(f"validation posture: {summary['validation_posture']}")
    return "; ".join(parts) if parts else "No source-obligation counts recorded."


def format_project_row(project: Project) -> dict[str, object]:
    """Format a Project manifest for display/test assertions."""

    return {
        "Name": project.name,
        "Project ID": project.project_id,
        "Description": project.description or "—",
        "Sources": len(project.project_source_ids),
        "Privacy": project.privacy_class,
        "Retention": project.retention_state,
        "Created": project.created_at,
        "Updated": project.updated_at,
    }


def format_project_source_row(project_source: ProjectSource) -> dict[str, object]:
    """Format a ProjectSource membership edge for display/test assertions."""

    parser_metadata = project_source.parser_metadata or {}
    parser_notes = parser_metadata.get("parser_notes") or parser_metadata.get("notes") or []
    if isinstance(parser_notes, (list, tuple)):
        parser_notes_text = "; ".join(str(note) for note in parser_notes)
    else:
        parser_notes_text = str(parser_notes) if parser_notes else "—"
    source_identity = project_source.source_identity or {}
    return {
        "Title": project_source.title,
        "Project Source ID": project_source.project_source_id,
        "Source kind": project_source.source_kind,
        "Evidence role": project_source.evidence_role,
        "Validation posture": project_source.validation_posture,
        "Source-obligation summary": summarize_source_obligations(project_source),
        "Parser": parser_metadata.get("parser_name", "—"),
        "Parser version": parser_metadata.get("parser_version", "—"),
        "Parser confidence": parser_metadata.get(
            "parser_confidence", parser_metadata.get("extraction_confidence", "—")
        ),
        "Parser notes": parser_notes_text or "—",
        "Input format": source_identity.get("input_format", "—"),
        "Retention": project_source.retention_state,
        "Raw text persisted": project_source.raw_text_persisted,
        "Privacy": project_source.privacy_class,
        "Added": project_source.added_at,
        "Updated": project_source.updated_at,
    }


def project_select_options(projects: tuple[Project, ...] | list[Project]) -> dict[str, str]:
    """Return stable select labels mapped to Project IDs."""

    return {f"{project.name} ({project.project_id})": project.project_id for project in projects}


def save_document_review_to_project(
    project: Project | str,
    context: DocumentReviewContext,
    *,
    storage_root: str | Path | None = None,
    title: str | None = None,
) -> ProjectSourcePromotionResult:
    """Promote a session-local document review context using AG-84B helpers only."""

    return add_project_source_from_document_review(
        project,
        context,
        storage_root=storage_root,
        title=title,
    )


def render_projects_page(context: UIContext) -> None:
    """Render the minimal local Projects / Project Sources page."""

    st = context.st
    st.header("Projects / Project Sources")
    st.info(project_source_boundary_caption())
    st.caption(f"Default local manifest root: `{DEFAULT_PROJECT_SOURCE_STORAGE_ROOT}`")

    with st.form("create_project_form", clear_on_submit=True):
        st.subheader("Create Project")
        name = st.text_input("Project name")
        description = st.text_area("Description (optional)", height=80)
        submitted = st.form_submit_button("Create local Project", type="primary")
    if submitted:
        try:
            created = create_project(name, description=description)
        except ValueError as exc:
            st.warning(str(exc))
        else:
            st.session_state[_PROJECTS_SELECTED_KEY] = created.project_id
            st.success(f"Created local Project '{created.name}' ({created.project_id}).")
            st.rerun()

    projects = list_projects()
    st.subheader("Local Projects")
    if not projects:
        st.caption("No local Projects yet. Create one above to start saving Project Sources.")
        return

    st.dataframe([format_project_row(project) for project in projects], use_container_width=True, hide_index=True)
    selected_project = _render_project_selector(st, projects, key="projects_selected_project_label")
    if selected_project is None:
        return
    _render_selected_project(st, selected_project)


def render_document_review_project_save_section(st: Any, context_obj: DocumentReviewContext) -> None:
    """Render the Document Review save/promote action for an existing context."""

    st.subheader("Save to Project")
    st.caption(project_source_boundary_caption())
    projects = list_projects()
    if not projects:
        st.caption("No local Projects exist yet. Create one here or open Projects / Project Sources from the sidebar.")

    with st.form("document_review_save_to_project_form"):
        options = project_select_options(projects)
        labels = list(options)
        selected_label = st.selectbox("Existing Project", labels, index=0) if labels else None
        st.markdown("**Or create a new Project for this source**")
        new_project_name = st.text_input("New Project name", key=_DOC_REVIEW_INLINE_NAME_KEY)
        new_project_description = st.text_area(
            "New Project description (optional)",
            height=70,
            key=_DOC_REVIEW_INLINE_DESCRIPTION_KEY,
        )
        source_title = st.text_input(
            "Project Source title (optional)",
            value=context_obj.metadata.title,
            key=_DOC_REVIEW_TITLE_KEY,
        )
        submitted = st.form_submit_button("Save document review as Project Source", type="primary")

    if not submitted:
        return

    try:
        if str(new_project_name or "").strip():
            project = create_project(new_project_name, description=new_project_description)
        elif selected_label:
            project = load_project(options[selected_label])
        else:
            st.warning("Create or select a Project before saving this document review.")
            return
        result = save_document_review_to_project(project, context_obj, title=source_title)
    except ValueError as exc:
        st.warning(str(exc))
        return

    st.success(
        f"Saved '{result.project_source.title}' to Project '{result.project.name}' "
        f"as ProjectSource {result.project_source.project_source_id}."
    )
    st.caption(
        "Raw normalized document text was not persisted by default; compact manifests and bounded previews were saved locally only."
    )
    st.session_state[_PROJECTS_SELECTED_KEY] = result.project.project_id
    st.session_state[_DOC_REVIEW_TARGET_KEY] = result.project.project_id


def _render_project_selector(st: Any, projects: tuple[Project, ...], *, key: str) -> Project | None:
    options = project_select_options(projects)
    if not options:
        return None
    labels = list(options)
    current_project_id = st.session_state.get(_PROJECTS_SELECTED_KEY)
    selected_index = 0
    if current_project_id in options.values():
        selected_index = next(index for index, label in enumerate(labels) if options[label] == current_project_id)
    default_label = labels[selected_index]
    if st.session_state.get(key) not in options:
        st.session_state[key] = default_label
    selected_label = st.selectbox("Select Project", labels, index=selected_index, key=key)
    selected_project_id = options[selected_label]
    st.session_state[_PROJECTS_SELECTED_KEY] = selected_project_id
    return load_project(selected_project_id)


def _render_selected_project(st: Any, project: Project) -> None:
    st.subheader(f"Project: {project.name}")
    st.write(format_project_row(project))
    st.caption(project_source_boundary_caption())

    sources = list_project_sources(project)
    st.markdown("### Project Sources")
    if not sources:
        st.caption("No active Project Sources linked to this Project yet.")
        return

    rows = [format_project_source_row(source) for source in sources]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    for source in sources:
        with st.expander(f"{source.title} — {source.project_source_id}", expanded=False):
            st.write(format_project_source_row(source))
            st.caption(
                "Remove from Project only removes the membership edge. SourceRecord and SourceRevision manifests remain active. "
                "This is not deletion, tombstoning, secure erase, snapshot removal, or managed-copy deletion."
            )
            if st.button(
                "Remove from this Project",
                key=f"remove_project_source_{source.project_source_id}",
                use_container_width=True,
            ):
                updated = remove_project_source(project, source.project_source_id)
                st.session_state[_PROJECTS_SELECTED_KEY] = updated.project_id
                st.success(
                    f"Removed ProjectSource {source.project_source_id} from Project '{updated.name}'. "
                    "SourceRecord and SourceRevision manifests remain active."
                )
                st.rerun()
