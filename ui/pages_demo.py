"""Offline fixture/demo presentation for UX review."""

from __future__ import annotations

from typing import Any

from ui.context import UIContext
from ui.demo_fixtures import build_demo_session, is_demo_session, list_demo_scenarios
from ui.pages_thread import _evidence_provenance_rows, _render_source_chip_strip

_POSTURE_LABELS = {
    "direct": "Directly sourced",
    "inferred": "Inferred from sourced premises",
    "unsupported": "Unsupported by fixture evidence",
}

_STATE_ICONS = {
    "complete": "✅",
    "warning": "⚠️",
    "error": "❌",
    "running": "▶️",
}


def render_demo_sidebar(context: UIContext) -> None:
    """Render sidebar controls that load canned offline sessions."""

    st = context.st
    scenarios = list_demo_scenarios()
    labels = {
        f"{item['title']} · {item['state_label']}": item["id"] for item in scenarios
    }
    if not labels:
        return

    st.divider()
    st.caption("OFFLINE UX DEMO")
    st.info("Fixture-backed product demo. No API keys or live retrieval required.")
    selected_label = st.selectbox(
        "Demo scenario",
        options=list(labels.keys()),
        key="offline_demo_scenario_label",
        disabled=st.session_state.is_running,
    )
    if st.button(
        "Open offline demo",
        key="open_offline_demo",
        use_container_width=True,
        disabled=st.session_state.is_running,
    ):
        st.session_state.current_session = build_demo_session(labels[selected_label])
        st.session_state.current_page = "thread"
        st.session_state["review_mode"] = False
        st.rerun()


def render_demo_home_notice(context: UIContext) -> None:
    """Make the demo entrypoint visible on the empty home page."""

    st = context.st
    with st.expander("Offline UX demo mode", expanded=False):
        st.markdown(
            "Use **Offline UX Demo** in the sidebar to open fixture-backed "
            "ScryRaven product flows. Demo mode uses canned source cards, "
            "citations, progress states, and answer states; it does not run "
            "providers, model APIs, search, retrieval, or live validation."
        )


def render_demo_thread_page(context: UIContext) -> None:
    """Render a demo fixture session without live follow-up or review actions."""

    st = context.st
    session = st.session_state.current_session
    if not is_demo_session(session):
        return

    demo = session["demo_fixture"]
    scenario: dict[str, Any] = demo["scenario"]

    st.caption("OFFLINE DEMO / FIXTURE MODE")
    st.warning(demo.get("offline_notice") or "Offline demo fixture only.")
    st.header(session.get("query") or scenario.get("title") or "Offline demo")

    cols = st.columns(3)
    cols[0].metric("Scenario", scenario.get("state_label") or "Offline demo")
    cols[1].metric("Mode", scenario.get("mode") or "Fixture")
    cols[2].metric("Confidence", scenario.get("confidence_label") or "Demo only")

    _render_progress(st, scenario.get("progress_steps") or [])
    _render_document_preview(st, scenario.get("document_preview"))
    _render_mode_comparison(st, scenario.get("mode_comparison"))

    st.subheader("Fixture answer")
    st.markdown((session.get("report") or "").replace("$", "\\$"))

    _render_claim_cards(st, scenario.get("claim_cards") or [])
    _render_export_preview(st, scenario.get("export_preview"))

    _render_source_chip_strip(st, session.get("top_passages", []))
    with st.expander(
        f"🔍 View fixture evidence ({len(session.get('top_passages', []))} chunks)",
        expanded=False,
    ):
        rows = _evidence_provenance_rows(session.get("top_passages", []))
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("This demo scenario intentionally has no usable source cards.")

    st.info(
        "Demo sessions are not saved to history and follow-up chat is disabled "
        "so fixture review cannot be mistaken for live run telemetry."
    )


def _render_progress(st: Any, steps: list[dict[str, Any]]) -> None:
    if not steps:
        return
    with st.expander("Pipeline progress preview", expanded=True):
        for step in steps:
            state = str(step.get("state") or "complete").lower()
            icon = _STATE_ICONS.get(state, "•")
            st.markdown(f"{icon} **{step.get('label') or 'Step'}** — {step.get('detail') or ''}")


def _render_claim_cards(st: Any, claim_cards: list[dict[str, Any]]) -> None:
    if not claim_cards:
        return
    st.subheader("Claim/evidence posture")
    for card in claim_cards:
        posture = str(card.get("evidence_posture") or "direct").lower()
        label = _POSTURE_LABELS.get(posture, posture.replace("_", " ").title())
        source_ids = card.get("source_ids") or []
        suffix = f" Sources: {', '.join(str(x) for x in source_ids)}." if source_ids else " No source card."
        st.markdown(f"**{label}:** {card.get('claim') or ''}{suffix}")
        if card.get("note"):
            st.caption(str(card["note"]))


def _render_document_preview(st: Any, document_preview: Any) -> None:
    if not isinstance(document_preview, dict):
        return
    with st.expander("Document-review preview (mock only)", expanded=True):
        st.markdown(f"**Document:** {document_preview.get('document_name') or 'Mock document'}")
        rows = [
            {
                "Section": section.get("heading"),
                "Status": section.get("status"),
                "Preview note": section.get("note"),
            }
            for section in document_preview.get("sections") or []
            if isinstance(section, dict)
        ]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("Preview only: no upload, parsing, storage, or document-ingestion behavior is implemented.")


def _render_mode_comparison(st: Any, comparison: Any) -> None:
    if not isinstance(comparison, list) or not comparison:
        return
    with st.expander("Fast / Balanced / Deep fixture illustration", expanded=True):
        st.dataframe(
            [
                {"Mode": item.get("mode"), "Fixture UI summary": item.get("summary")}
                for item in comparison
                if isinstance(item, dict)
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Illustrative UX copy only; this is not AG-81B answer-quality policy.")


def _render_export_preview(st: Any, export_preview: Any) -> None:
    if not export_preview:
        return
    with st.expander("Export preview", expanded=False):
        st.write(str(export_preview))
