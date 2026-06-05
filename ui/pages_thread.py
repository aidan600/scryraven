"""Active thread view: report, review mode, evidence, follow-up."""

import re
from datetime import datetime, timezone

from core.corpus_state import CorpusState
from core.failure_card import (
    failure_card_show_estimate,
    failure_card_show_force_keyword,
)
from core.pipeline import kb_review_agent_hybrid, kb_review_agent_positive
from core.review_flags import (
    feedback_overall_numeric,
    feedback_saved_fingerprint,
    load_feedback_for_session,
)
from ui.context import UIContext
from ui.pages_followup import render_followup_chat
from ui.pages_projects import render_thread_report_project_save_section
from ui.shared import (
    append_jsonl_record,
    flatten_providers_used,
    read_jsonl_records,
)
from ui.source_display import (
    _evidence_provenance_rows,
    _evidence_sort_key,
    _render_source_chip_strip,
    _safe_display_value,
    _short_preview,
)


def render_active_thread_report_section(context: UIContext, session: dict) -> None:
    """Render the active-thread report save entrypoint with the live session."""

    st = context.st
    with st.expander("🧾 Generate / Save Thread Report to Project", expanded=False):
        render_thread_report_project_save_section(st, context, session)


def render_thread_page(context: UIContext) -> None:
    st = context.st
    os = context.os
    json = context.json
    current_date = context.current_date
    logger = context.logger
    OUTPUT_DIR = context.OUTPUT_DIR
    execution_log_path = OUTPUT_DIR / "execution_log.jsonl"
    feedback_log_path = OUTPUT_DIR / "feedback_log.jsonl"
    kb_triggers_path = OUTPUT_DIR / "kb_triggers.jsonl"
    ask_model = context.ask_model
    clean_json_response = context.clean_json_response

    def _append_jsonl(path, payload: dict) -> None:
        append_jsonl_record(path, payload, logger=logger)

    def _read_jsonl(path) -> list[dict]:
        return read_jsonl_records(path, json_module=json, logger=logger)

    # --- RENDER EXISTING SESSION ---
    lkb = st.session_state.pop("last_kb_instrumentation", None)
    if lkb is not None:
        agent_note = (
            "quality review agent finished a KB entry"
            if lkb.get("agent_ran")
            else "quality review agent not invoked (auto-review not triggered or failed)"
        )
        st.info(
            f"**Run instrumentation (KB line always logged):** score **{lkb.get('score')}** — "
            f"auto-review **{'yes' if lkb.get('fired') else 'no'}** — {agent_note}."
        )
    session = st.session_state.current_session

    st.header(session["query"])
    _title_slug = re.sub(
        r"[^\w\s-]",
        "",
        (session.get("title") or session.get("query") or "thread"),
    )[:80]
    _title_slug = re.sub(r"[\s_]+", "-", _title_slug.strip()).strip("-") or "thread"
    _export_md = (
        f"# {session.get('title') or 'Research'}\n\n"
        f"**Query:** {session.get('query', '')}\n\n"
        f"*{session.get('timestamp', '')}*\n\n---\n\n"
        f"{session.get('report', '') or ''}\n"
    )
    st.download_button(
        label="Export Markdown",
        data=_export_md,
        file_name=f"{_title_slug}.md",
        mime="text/markdown",
        key="thread_export_markdown",
    )

    if st.session_state.get("review_mode", False):
        st.caption("Review Mode — ratings are appended to output/feedback_log.jsonl.")
        _rkey = (session.get("run_id") or session.get("id") or "na")[:12]
        _sid = session.get("id") or ""
        saved_fb = load_feedback_for_session(feedback_log_path, _sid) if _sid else {}
        _fp_now = feedback_saved_fingerprint(saved_fb)
        _fp_key = f"_fb_disk_fp_{_sid}"
        if st.session_state.get(_fp_key) != _fp_now:
            if saved_fb:
                _leg = feedback_overall_numeric(saved_fb)
                _def = int(_leg) if _leg is not None else 4
                st.session_state[f"fb_ac_{_rkey}"] = int(
                    saved_fb.get("answer_completeness") if saved_fb.get("answer_completeness") is not None else _def
                )
                st.session_state[f"fb_evq_{_rkey}"] = int(
                    saved_fb.get("evidence_quality") if saved_fb.get("evidence_quality") is not None else _def
                )
                st.session_state[f"fb_op_{_rkey}"] = int(
                    saved_fb.get("output_precision") if saved_fb.get("output_precision") is not None else _def
                )
                st.session_state[f"fb_overall_{_rkey}"] = int(
                    saved_fb.get("overall") if saved_fb.get("overall") is not None else _def
                )
                if saved_fb.get("scout_contribution") is not None:
                    st.session_state[f"fb_scout_{_rkey}"] = int(saved_fb["scout_contribution"])
                st.session_state[f"fb_notes_{_rkey}"] = saved_fb.get("user_notes") or ""
            st.session_state[_fp_key] = _fp_now
        with st.form(key=f"review_form_{session.get('run_id', session.get('id', 'current'))}"):
            dims = [1, 2, 3, 4, 5]
            ac = st.select_slider("Did it answer what was asked?", options=dims, value=4, key=f"fb_ac_{_rkey}")
            evq = st.select_slider("Were sources good and specific?", options=dims, value=4, key=f"fb_evq_{_rkey}")
            op_ = st.select_slider(
                "Specific numbers and facts vs vague summary?", options=dims, value=4, key=f"fb_op_{_rkey}"
            )
            sc_val = 4
            latest_exec: dict | None = None
            if session.get("run_id"):
                for item in reversed(_read_jsonl(execution_log_path)):
                    if item.get("run_id") == session.get("run_id") and item.get("event") == "execution":
                        latest_exec = item
                        break
            if latest_exec and latest_exec.get("scout_fired"):
                sc_val = st.select_slider(
                    "Did scout queries add real value?", options=dims, value=4, key=f"fb_scout_{_rkey}"
                )
            overall = st.select_slider("Overall", options=dims, value=4, key=f"fb_overall_{_rkey}")
            notes = st.text_input(
                "Notes (optional)", placeholder="What worked or what to improve?", key=f"fb_notes_{_rkey}"
            )
            submitted = st.form_submit_button("Log Feedback")
            if submitted:
                parts = [ac, evq, op_]
                if latest_exec and latest_exec.get("scout_fired"):
                    parts.append(sc_val)
                try:
                    overall_auto = round(sum(parts) / len(parts), 2) if parts else None
                except TypeError:
                    overall_auto = None
                # Legacy label for any code still expecting user_rating
                o = overall
                u_rating = (
                    "Excellent"
                    if o == 5
                    else "Good"
                    if o >= 4
                    else "Fair"
                    if o in (2, 3)
                    else "Poor"
                    if o == 1
                    else "Good"
                )
                fb_time = datetime.now(timezone.utc).isoformat()
                _append_jsonl(
                    feedback_log_path,
                    {
                        "event": "feedback",
                        "timestamp": current_date,
                        "timestamp_utc": fb_time,
                        "run_id": session.get("run_id"),
                        "session_id": session.get("id"),
                        "user_rating": u_rating,
                        "user_notes": notes or None,
                        "answer_completeness": ac,
                        "evidence_quality": evq,
                        "output_precision": op_,
                        "overall": overall,
                        "overall_auto": overall_auto,
                    }
                    | ({"scout_contribution": sc_val} if latest_exec and latest_exec.get("scout_fired") else {}),
                )
                st.success("Feedback logged.")
                exec_for_run: dict = latest_exec or {}
                if not exec_for_run and session.get("run_id"):
                    for it in reversed(_read_jsonl(execution_log_path)):
                        if it.get("run_id") == session.get("run_id") and it.get("event") == "execution":
                            exec_for_run = it
                            break
                try:
                    o_int = int(overall)
                except (TypeError, ValueError):
                    o_int = 0
                positive_eligible = o_int >= 4 and (
                    not exec_for_run.get("scout_fired") or (exec_for_run.get("scout_fired") and int(sc_val) >= 4)
                )
                low_feedback_eligible = o_int <= 2
                if positive_eligible and exec_for_run:
                    fb_sl = {
                        "answer_completeness": ac,
                        "evidence_quality": evq,
                        "output_precision": op_,
                        "overall": overall,
                        "overall_auto": overall_auto,
                    }
                    if exec_for_run.get("scout_fired"):
                        fb_sl["scout_contribution"] = sc_val
                    try:
                        or_api_key = st.session_state.get("or_key", os.getenv("OPENROUTER_API_KEY", ""))
                        local_url_fb = st.session_state.get("local_url", "http://localhost:1234/v1")
                        fast_provider_fb = st.session_state.get("fp", "OpenAI")
                        if fast_provider_fb == "OpenAI":
                            fast_model_fb = st.session_state.get("fm_oa", "gpt-5.4-mini")
                        elif fast_provider_fb == "OpenRouter":
                            fast_model_fb = st.session_state.get("fm_or", "anthropic/claude-haiku-4.5")
                        else:
                            fast_model_fb = st.session_state.get("fm_ls", "local-model")
                        rpt = session.get("report", "") or ""
                        kb_p = kb_review_agent_positive(
                            ask_model,
                            clean_json_response,
                            exec_for_run,
                            rpt,
                            fb_sl,
                            fast_provider_fb,
                            fast_model_fb,
                            local_url_fb,
                            or_api_key,
                        )
                        if kb_p:
                            _append_jsonl(
                                kb_triggers_path,
                                {
                                    "event": "kb_trigger",
                                    "review_type": "positive",
                                    "fired": False,
                                    "run_id": session.get("run_id"),
                                    "session_id": session.get("id"),
                                    "query": (session.get("query") or "")[:200],
                                    "mode": exec_for_run.get("mode", ""),
                                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                    "retrieval_yield_chunks": int(exec_for_run.get("total_chunks_embedded") or 0),
                                    "providers_used": flatten_providers_used(
                                        exec_for_run.get("providers_by_iteration")
                                    ),
                                    "timing": dict(exec_for_run.get("timing") or {}),
                                    "kb_review": kb_p,
                                },
                            )
                    except Exception as e:
                        logger.warning(f"Positive KB review skipped: {e}")
                elif low_feedback_eligible and exec_for_run:
                    fb_sl = {
                        "answer_completeness": ac,
                        "evidence_quality": evq,
                        "output_precision": op_,
                        "overall": overall,
                        "overall_auto": overall_auto,
                        "user_notes": notes or None,
                    }
                    if exec_for_run.get("scout_fired"):
                        fb_sl["scout_contribution"] = sc_val
                    try:
                        or_api_key = st.session_state.get("or_key", os.getenv("OPENROUTER_API_KEY", ""))
                        local_url_fb = st.session_state.get("local_url", "http://localhost:1234/v1")
                        fast_provider_fb = st.session_state.get("fp", "OpenAI")
                        if fast_provider_fb == "OpenAI":
                            fast_model_fb = st.session_state.get("fm_oa", "gpt-5.4-mini")
                        elif fast_provider_fb == "OpenRouter":
                            fast_model_fb = st.session_state.get("fm_or", "anthropic/claude-haiku-4.5")
                        else:
                            fast_model_fb = st.session_state.get("fm_ls", "local-model")
                        rpt = session.get("report", "") or ""
                        kb_n = kb_review_agent_hybrid(
                            ask_model,
                            clean_json_response,
                            exec_for_run,
                            rpt,
                            fb_sl,
                            fast_provider_fb,
                            fast_model_fb,
                            local_url_fb,
                            or_api_key,
                        )
                        if kb_n:
                            _append_jsonl(
                                kb_triggers_path,
                                {
                                    "event": "kb_trigger",
                                    "review_type": "user_negative",
                                    "fired": True,
                                    "run_id": session.get("run_id"),
                                    "session_id": session.get("id"),
                                    "query": (session.get("query") or "")[:200],
                                    "mode": exec_for_run.get("mode", ""),
                                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                    "retrieval_yield_chunks": int(exec_for_run.get("total_chunks_embedded") or 0),
                                    "providers_used": flatten_providers_used(
                                        exec_for_run.get("providers_by_iteration")
                                    ),
                                    "timing": dict(exec_for_run.get("timing") or {}),
                                    "kb_review": kb_n,
                                },
                            )
                    except Exception as e:
                        logger.warning(f"Negative hybrid KB review skipped: {e}")
    fc = session.get("failure_card") or {}
    if fc.get("show"):
        with st.expander("Quality and retrieval note", expanded=True):
            st.markdown(fc.get("reason") or "")
            prefer = [
                p
                for p in ("tavily", "linkup", "exa")
                if os.getenv({"tavily": "TAVILY_API_KEY", "linkup": "LINKUP_API_KEY", "exa": "EXA_API_KEY"}[p])
            ] or ["tavily"]
            _fc_sid = session.get("id") or "thread"
            if failure_card_show_force_keyword(
                corpus_state=str(fc.get("corpus_state") or ""),
                first_pass_providers=list(fc.get("first_pass_providers") or []),
            ):
                if st.button(
                    "Retry with keyword search",
                    key=f"fc_kw_{_fc_sid}",
                    use_container_width=True,
                    disabled=st.session_state.is_running,
                ):
                    st.session_state["next_run_provider_override"] = prefer
                    st.session_state.pop("next_run_force_state", None)
                    st.session_state["proplex_seed_query"] = session.get("query") or ""
                    st.session_state["proplex_append_meta"] = {
                        "session_id": session.get("id"),
                        "title": session.get("title"),
                        "query": session.get("query"),
                    }
                    st.session_state["proplex_auto_run"] = True
                    st.session_state.current_session = None
                    st.session_state.current_page = "home"
                    st.rerun()
            if failure_card_show_estimate(corpus_state=str(fc.get("corpus_state") or "")):
                if st.button(
                    "Allow estimate from priors",
                    key=f"fc_est_{_fc_sid}",
                    use_container_width=True,
                    disabled=st.session_state.is_running,
                ):
                    st.session_state["next_run_force_state"] = CorpusState.ESTIMATE_FROM_PRIORS.value
                    st.session_state.pop("next_run_provider_override", None)
                    st.session_state["proplex_seed_query"] = session.get("query") or ""
                    st.session_state["proplex_append_meta"] = {
                        "session_id": session.get("id"),
                        "title": session.get("title"),
                        "query": session.get("query"),
                    }
                    st.session_state["proplex_auto_run"] = True
                    st.session_state.current_session = None
                    st.session_state.current_page = "home"
                    st.rerun()
            if st.button(
                "Broaden query (new thread)",
                key=f"fc_br_{_fc_sid}",
                use_container_width=True,
                disabled=st.session_state.is_running,
            ):
                st.session_state.pop("next_run_provider_override", None)
                st.session_state.pop("next_run_force_state", None)
                st.session_state.pop("proplex_append_meta", None)
                st.session_state.pop("proplex_auto_run", None)
                st.session_state["proplex_seed_query"] = (session.get("query") or "").strip() + "\n\n"
                st.session_state.current_session = None
                st.session_state.current_page = "home"
                st.rerun()
    st.markdown(session["report"].replace("$", "\\$"))
    _render_source_chip_strip(st, session.get("top_passages", []))
    render_active_thread_report_section(context, session)

    with st.expander(f"🔍 View Retrieved Evidence ({len(session.get('top_passages', []))} chunks)"):
        top_list = session.get("top_passages", [])
        provenance_rows = _evidence_provenance_rows(top_list)
        if provenance_rows:
            st.dataframe(provenance_rows, use_container_width=True, hide_index=True)
            st.divider()
        else:
            st.caption("No retrieved evidence is available for this thread.")

        for _, p in sorted(enumerate(top_list if isinstance(top_list, list) else []), key=_evidence_sort_key):
            if not isinstance(p, dict):
                continue
            sid = _safe_display_value(p.get("source_id")) or _safe_display_value(p.get("url")) or "?"
            title = _safe_display_value(p.get("title")) or "Untitled"
            domain = _safe_display_value(p.get("domain"))
            text = _short_preview(p, max_chars=600)
            st.markdown(f"**[{sid}] {title}**")
            details = []
            if domain:
                details.append(f"Domain: {domain}")
            if details:
                st.caption(" | ".join(details))
            st.markdown(f"> *{text[:600]}{'...' if len(text) > 600 else ''}*")
            st.write("---")

    render_followup_chat(context, session)
