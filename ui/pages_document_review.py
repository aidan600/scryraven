"""Streamlit page for local document review with bounded PDF/DOCX parsing."""

from __future__ import annotations

from core.document_review import (
    BOUNDARY_NOTICE,
    PRIVACY_WARNING,
    DocumentInput,
    build_document_review_context,
    build_document_review_context_from_input,
    retrieve_document_followup,
)
from ui.context import UIContext
from ui.pages_projects import render_document_review_project_save_section

_SESSION_KEY = "document_review_context"
_INPUT_KEY = "document_review_input"
_TITLE_KEY = "document_review_title"
_FOLLOWUP_KEY = "document_review_followup"


def render_document_review_page(context: UIContext) -> None:
    """Render the isolated document-review MVP page.

    This page intentionally uses only deterministic document-review helpers. It does
    not call search, retrieval, providers, model helpers, storage, caches, or the
    pipeline/orchestrator.
    """

    st = context.st
    st.header("Document Review (local MVP)")
    st.info(BOUNDARY_NOTICE)
    st.caption(
        "Pasted text / Markdown remains supported. Optional PDF/DOCX upload uses local text extraction only. "
        "No OCR, public web validation, provider/model/search calls, persistent corpus, or document library storage."
    )

    title = st.text_input("Document title (optional)", key=_TITLE_KEY)
    uploaded_file = st.file_uploader(
        "Optional PDF/DOCX upload (local text extraction only; no OCR)",
        type=["pdf", "docx"],
        accept_multiple_files=False,
    )
    if uploaded_file is not None:
        st.caption(
            "Uploaded files are parsed locally into session-local retained context. PDF anchors are page-only when text is extractable; "
            "DOCX anchors are structural block order only, not rendered page numbers."
        )
    raw_text = st.text_area(
        "Paste text or Markdown",
        height=260,
        key=_INPUT_KEY,
        placeholder="# Decision memo\n\nPaste Markdown or plain text here...",
    )

    col_build, col_clear = st.columns(2)
    with col_build:
        build = st.button("Build local review", type="primary", use_container_width=True)
    with col_clear:
        clear = st.button("Clear document session", use_container_width=True)

    if clear:
        st.session_state.pop(_SESSION_KEY, None)
        st.session_state.pop(_INPUT_KEY, None)
        st.session_state.pop(_TITLE_KEY, None)
        st.session_state.pop(_FOLLOWUP_KEY, None)
        st.rerun()

    if build:
        if uploaded_file is not None:
            suffix = uploaded_file.name.rsplit(".", 1)[-1].casefold()
            input_format = "pdf" if suffix == "pdf" else "docx"
            try:
                context_obj = build_document_review_context_from_input(
                    DocumentInput(
                        content=uploaded_file.getvalue(),
                        input_format=input_format,
                        title=str(title or "") or uploaded_file.name,
                        filename=uploaded_file.name,
                    )
                )
            except (RuntimeError, ValueError) as exc:
                st.warning(f"Could not parse uploaded document locally: {exc}")
            else:
                st.session_state[_SESSION_KEY] = context_obj.snapshot()
                st.success("Built a session-local document review context from a locally parsed file.")
        elif not str(raw_text or "").strip():
            st.warning("Paste text/Markdown or upload a text-based PDF/DOCX before building a local review.")
        else:
            context_obj = build_document_review_context(str(raw_text), title=str(title or "") or None)
            st.session_state[_SESSION_KEY] = context_obj.snapshot()
            st.success("Built a session-local document review context.")

    context_obj = st.session_state.get(_SESSION_KEY)
    if not context_obj:
        st.warning("No document retained yet. Paste text or Markdown and build a local review.")
        return

    st.subheader("Retained session-local context")
    meta = context_obj.metadata
    st.write(
        {
            "title": meta.title,
            "document_id": meta.document_id,
            "version": meta.version,
            "input_format": meta.input_format,
            "parser": meta.parser_name,
            "parser_version": meta.parser_version,
            "parser_confidence": meta.parser_confidence,
            "parser_notes": "; ".join(meta.parser_notes),
            "privacy_marker": meta.privacy_marker,
            "sections": len(context_obj.sections),
            "anchors": len(context_obj.anchors),
            "chunks": len(context_obj.chunks),
            "findings": len(context_obj.findings),
        }
    )
    st.caption(PRIVACY_WARNING)
    render_document_review_project_save_section(st, context_obj)

    st.subheader("Document-local summary")
    st.markdown(context_obj.export_markdown.split("## Document-local summary\n", 1)[-1].split("\n\n##", 1)[0])

    st.subheader("Anchored chunks")
    chunk_rows = [
        {
            "Chunk": chunk.chunk_id,
            "Section": chunk.section_heading,
            "Anchors": ", ".join(chunk.anchor_ids),
            "Label": chunk.evidence_label,
            "Scope": chunk.source_scope,
            "Mode": chunk.retrieval_mode,
            "Confidence": chunk.extraction_confidence,
            "Preview": chunk.preview,
        }
        for chunk in context_obj.chunks
    ]
    if chunk_rows:
        st.dataframe(chunk_rows, use_container_width=True, hide_index=True)

    st.subheader("Claim candidates / review labels")
    st.caption("Deterministic document-local labels only; these do not validate outside-world truth.")
    if not context_obj.findings:
        st.caption("No deterministic claim candidates were detected.")
    for finding in context_obj.findings:
        st.markdown(
            f"**{finding.finding_id}** — `{', '.join(finding.labels)}` anchors: `{', '.join(finding.anchor_ids)}`"
        )
        st.write(finding.text)
        st.write(
            {
                "claim_type": finding.claim_type,
                "source_obligation": finding.source_obligation,
                "evidence_role": finding.evidence_role,
                "validation_need": finding.validation_need,
                "risk_level": finding.risk_level,
            }
        )
        st.caption(finding.note)

    st.subheader("Follow-up retrieval (deterministic retained chunks)")
    followup = st.text_input(
        "Retrieve retained document-local chunks by heading or keyword tokens",
        key=_FOLLOWUP_KEY,
        placeholder="e.g., deadline renewal legal",
    )
    if followup.strip():
        hits = retrieve_document_followup(context_obj, followup)
        if not hits:
            st.caption("No retained document-local chunks matched deterministically; this is not model answering.")
        for hit in hits:
            st.markdown(
                f"**{hit.chunk_id}** score `{hit.score}` — {hit.section_heading} — "
                f"anchors: `{', '.join(hit.anchor_ids)}`"
            )
            st.write(hit.snippet)
            st.caption(f"{', '.join(hit.labels)} · mode: {hit.retrieval_mode}")

    st.subheader("Markdown export")
    st.download_button(
        "Download document-local review Markdown",
        data=context_obj.export_markdown,
        file_name=f"{context_obj.metadata.document_id}_document_review.md",
        mime="text/markdown",
        use_container_width=True,
    )
    with st.expander("Preview export", expanded=False):
        st.markdown(context_obj.export_markdown)
