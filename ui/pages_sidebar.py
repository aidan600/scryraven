"""Sidebar: review state, navigation, settings, and internal diagnostics."""

from core.retrieval import ensure_passage_source_ids
from core.review_flags import (
    feedback_overall_numeric,
    kb_insights_data,
    performance_insights,
)
from ui.context import UIContext
from ui.shared import read_jsonl_records

RECENT_THREAD_LIMIT = 7
SIDEBAR_TITLE_LIMIT = 72


def render_review_mode_toggle(context: UIContext) -> None:
    st = context.st
    # Keep the state initialized before main content reads it; render the visible
    # toggle later with the rest of the sidebar so navigation stays first.
    if "review_mode" not in st.session_state:
        st.session_state["review_mode"] = False


def _compact_sidebar_title(value: object) -> str:
    title = " ".join(str(value or "Untitled").split())
    if len(title) <= SIDEBAR_TITLE_LIMIT:
        return title
    return title[: SIDEBAR_TITLE_LIMIT - 3].rstrip() + "..."


def render_main_sidebar(context: UIContext) -> None:
    st = context.st
    os = context.os
    json = context.json

    OUTPUT_DIR = context.OUTPUT_DIR

    logger = context.logger

    load_history = context.load_history
    rename_session = context.rename_session
    delete_session = context.delete_session

    execution_log_path = OUTPUT_DIR / "execution_log.jsonl"
    feedback_log_path = OUTPUT_DIR / "feedback_log.jsonl"
    kb_triggers_path = OUTPUT_DIR / "kb_triggers.jsonl"

    def _read_jsonl(path) -> list[dict]:
        return read_jsonl_records(path, json_module=json, logger=logger)

    # Rendered at the end to allow for dynamic disabling during execution.
    with st.sidebar:
        st.markdown(
            "<h2 style='font-size: 1.4rem; font-weight: 700; margin-bottom: 1rem; color: #111827;'>ScryRaven</h2>",
            unsafe_allow_html=True,
        )

        if st.button("New Thread", use_container_width=True, disabled=st.session_state.is_running):
            st.session_state.current_session = None
            st.session_state.current_page = "home"
            st.rerun()

        if st.button("Library", use_container_width=True, disabled=st.session_state.is_running):
            st.session_state.current_session = None
            st.session_state.current_page = "history"
            st.rerun()

        st.caption("RECENT THREADS")
        history_list = load_history()

        if not history_list:
            st.caption("No recent threads yet.")
        else:
            for s in history_list[:RECENT_THREAD_LIMIT]:
                raw_title = " ".join(str(s.get("title", s.get("query", "Untitled"))).split())
                compact_title = _compact_sidebar_title(raw_title)
                is_active = st.session_state.get("current_session") and st.session_state.current_session["id"] == s["id"]
                btn_type = "primary" if is_active else "secondary"

                col1, col2 = st.columns([6, 1])
                with col1:
                    if st.button(
                        compact_title,
                        key=f"hist_{s['id']}",
                        use_container_width=True,
                        type=btn_type,
                        disabled=st.session_state.is_running,
                    ):
                        passages_file = OUTPUT_DIR / f"{s['id']}_passages.json"
                        if passages_file.exists():
                            try:
                                with open(passages_file, "r", encoding="utf-8") as pf:
                                    s["top_passages"] = json.load(pf)
                                    ensure_passage_source_ids(s["top_passages"])
                            except Exception:
                                s["top_passages"] = []
                        else:
                            s["top_passages"] = []

                        st.session_state.current_session = s
                        st.session_state.current_page = "thread"
                        st.rerun()
                with col2:
                    with st.popover("...", disabled=st.session_state.is_running):
                        new_title = st.text_input(
                            "Rename",
                            value=raw_title,
                            key=f"ren_val_{s['id']}",
                            label_visibility="collapsed",
                        )
                        if st.button("Rename", key=f"ren_btn_{s['id']}", use_container_width=True):
                            rename_session(s["id"], new_title)
                            if is_active:
                                st.session_state.current_session["title"] = new_title
                            st.rerun()
                        if st.button("Delete", key=f"del_btn_{s['id']}", use_container_width=True):
                            delete_session(s["id"])
                            if is_active:
                                st.session_state.current_session = None
                                st.session_state.current_page = "home"
                            st.rerun()

        with st.expander("Advanced", expanded=False):
            use_reasoning = st.toggle(
                "Enable Reasoning Models",
                value=True,
                help="Disable to fall back to standard generation and increase speed.",
            )
            st.session_state["use_reasoning"] = use_reasoning

            st.write("**Model Selection**")
            st.selectbox("Fast Provider", ["OpenAI", "OpenRouter", "Local (LM Studio)"], key="fp")
            if st.session_state.get("fp", "OpenAI") == "OpenAI":
                st.selectbox("Model", ["gpt-5.4-mini"], key="fm_oa")
            elif st.session_state.get("fp") == "OpenRouter":
                st.caption("Fast model")
                st.radio(
                    "fm_or_model",
                    ["anthropic/claude-haiku-4.5", "google/gemini-3.1-flash-lite-preview"],
                    key="fm_or",
                    label_visibility="collapsed",
                )
            else:
                st.text_input("LM Studio Model ID", "local-model", key="fm_ls")

            st.selectbox("Smart Provider", ["OpenAI", "OpenRouter", "Local (LM Studio)"], key="sp")
            if st.session_state.get("sp", "OpenAI") == "OpenAI":
                st.selectbox("Model", ["gpt-5.4", "gpt-5.4-mini"], key="sm_oa")
            elif st.session_state.get("sp") == "OpenRouter":
                st.caption("Smart model")
                st.radio(
                    "sm_or_model",
                    [
                        "anthropic/claude-sonnet-4.6",
                        "google/gemini-3.1-pro-preview",
                        "google/gemini-3-flash-preview",
                    ],
                    key="sm_or",
                    label_visibility="collapsed",
                )
            else:
                st.text_input("LM Studio Model ID", "local-model", key="sm_ls")

            st.selectbox("Embedding Provider", ["OpenAI", "Local (LM Studio)"], key="ep")
            if st.session_state.get("ep", "OpenAI") == "OpenAI":
                pass
            else:
                st.text_input("LM Studio Embedding ID", "nomic-embed-text-v1.5", key="em_ls")

            if "Local (LM Studio)" in [
                st.session_state.get("fp"),
                st.session_state.get("sp"),
                st.session_state.get("ep"),
            ]:
                st.text_input("LM Studio Base URL", value="http://localhost:1234/v1", key="local_url")

            if "OpenRouter" in [st.session_state.get("fp"), st.session_state.get("sp")]:
                st.text_input(
                    "OpenRouter API Key",
                    value=os.getenv("OPENROUTER_API_KEY", ""),
                    type="password",
                    key="or_key",
                )

            st.text_input("Linkup API Key", value=os.getenv("LINKUP_API_KEY", ""), type="password", key="linkup_key")
            st.text_input("Exa API Key", value=os.getenv("EXA_API_KEY", ""), type="password", key="exa_key")

            st.write("**Research Strategy**")
            st.radio(
                "Pipeline Mode:",
                ["Fast", "Balanced", "Deep"],
                index=1,
                captions=[
                    "~20s - Direct answer with key sources",
                    "~90s - Structured brief across multiple sources",
                    "~3min - Full research report with gap analysis",
                ],
                key="strategy",
            )

            st.markdown("---")
            st.markdown("**Focus**")
            focus_options = {
                "Web": "web",
                "Academic": "academic",
                "News": "news",
            }
            legacy_focus_labels = {
                "🌐 Web": "Web",
                "🎓 Academic": "Academic",
                "📰 News": "News",
            }
            current_focus_label = st.session_state.get("focus_radio")
            if current_focus_label in legacy_focus_labels:
                st.session_state["focus_radio"] = legacy_focus_labels[current_focus_label]
            elif current_focus_label not in focus_options:
                st.session_state["focus_radio"] = "Web"
            selected_focus = st.radio(
                "Focus mode",
                options=list(focus_options.keys()),
                index=0,
                label_visibility="collapsed",
                key="focus_radio",
            )
            focus_value = focus_options[selected_focus]
            st.session_state["focus_academic"] = focus_value == "academic"
            st.session_state["force_intent_news"] = focus_value == "news"

        st.divider()
        st.caption("INTERNAL REVIEW")
        st.toggle(
            "QA Review Mode",
            key="review_mode",
            help="Shows reviewer-only ratings, summaries, and instrumentation.",
        )

        if st.session_state.get("review_mode", False):
            with st.expander("Feedback Summary", expanded=False):
                exec_logs = _read_jsonl(execution_log_path)
                feedback_logs = _read_jsonl(feedback_log_path)
                feedback_by_run = {
                    f.get("run_id"): f
                    for f in feedback_logs
                    if f.get("run_id")
                }
                total_queries = len([e for e in exec_logs if e.get("event") == "execution"])
                rated = [
                    f
                    for f in feedback_logs
                    if f.get("event") == "feedback"
                    and (feedback_overall_numeric(f) is not None or f.get("user_rating"))
                ]
                st.write(f"Total runs in execution log: **{total_queries}** | Feedback forms submitted: **{len(rated)}**")
                last_five = []
                for e in [x for x in exec_logs if x.get("event") == "execution"][-5:]:
                    fb = feedback_by_run.get(e.get("run_id"), {})
                    last_five.append(
                        {
                            "timestamp": e.get("timestamp"),
                            "query": e.get("query"),
                            "mode": e.get("mode"),
                            "report_type": e.get("report_type"),
                            "scout_fired": e.get("scout_fired"),
                            "overall_1_5": feedback_overall_numeric(fb),
                            "legacy": fb.get("user_rating"),
                        }
                    )
                if last_five:
                    st.dataframe(last_five, use_container_width=True)

            with st.expander("KB Insights", expanded=False):
                perf = performance_insights(execution_log_path, feedback_log_path)
                st.caption("Performance (rated runs + recent execution traces)")
                st.write(
                    f"**Runs (execution log):** {perf.get('total_runs', 0)}  "
                    f"**Rated:** {perf.get('with_rating', 0)}  "
                    f"**Overall >=4:** {perf.get('pct_overall_at_least_4') or 'N/A'}%"
                )
                sfp = perf.get("pct_synth_sufficient_first_pass")
                st.caption("First synthesis pass sufficient (completeness check) - of runs with this field logged")
                st.write(
                    f"**% synth sufficient on first pass:** {sfp if sfp is not None else 'N/A'}"
                    f" (n with field: {perf.get('executions_with_synth_flag', 0)})"
                )
                srate = perf.get("pct_scout_contrib_at_least_4")
                st.caption("Scout value: runs with scout that also have a scout_contribution score in feedback")
                st.write(
                    f"**% runs with scout_contribution >=4 (among those rated):** "
                    f"{srate if srate is not None else 'N/A'}"
                    f" (n={perf.get('scout_fired_rated', 0)})"
                )
                lbm = perf.get("latency_by_mode") or {}
                if lbm:
                    st.caption("Mean latency (seconds) by research strategy")
                    st.dataframe(
                        [{"Strategy": m, "Mean latency (s)": v} for m, v in lbm.items()],
                        use_container_width=True,
                    )
                ol0 = perf.get("overall_last_10") or []
                if len(ol0) >= 2:
                    st.caption("Last rated runs: overall 1-5 (chronological)")
                    st.line_chart({"Overall": ol0})
                st.divider()
                kbd = kb_insights_data(kb_triggers_path, execution_log_path)
                st.caption("Failure-oriented KB (auto review)")
                tr = kbd.get("total_runs") or 0
                tf = kbd.get("total_flagged", 0)
                tp = kbd.get("total_positive_review", 0)
                ratio = round(100.0 * tf / tr, 1) if tr else 0.0
                st.write(
                    f"**Auto-review flagged** {tf} / {tr} runs ({ratio}%). **Positive-capture** lines: **{tp}**"
                )
                fcc = kbd.get("failure_class_counts")
                sacc = kbd.get("suggested_action_type_counts")
                st.caption("Top failure classes (from KB reviews)")
                if fcc and len(fcc) > 0:
                    for k, c in fcc.most_common(3):
                        st.caption(f"- {k}: {c}")
                else:
                    st.caption("- none yet")
                st.caption("Top suggested action types")
                if sacc and len(sacc) > 0:
                    for k, c in sacc.most_common(3):
                        st.caption(f"- {k}: {c}")
                else:
                    st.caption("- none yet")
                for i, r in enumerate(kbd.get("last_recurring", []) or []):
                    with st.expander(f"Likely-recurring {i + 1}", expanded=False):
                        st.caption(f"**Query:** {r.get('query', '')}")
                        st.write(r.get("detail", ""))
                        st.caption((r.get("summary") or "")[:500])
