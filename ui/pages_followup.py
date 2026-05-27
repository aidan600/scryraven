"""Thread follow-up chat UI (discuss this research)."""

from typing import Any

from core.cost_accounting import CostAccumulator
from core.followup import (
    FollowUpDeps,
    build_followup_diagnostics,
    run_followup,
)
from core.followup import (
    complexity_for_ui_mode as _complexity_for_ui_mode,
)
from core.followup import (
    resolve_followup_mode as _resolve_followup_mode,
)
from core.retrieval import ensure_passage_source_ids
from core.run_logging import (
    log_chat_followup_completed,
    log_run_completed,
    log_run_failed,
    log_run_started,
)
from ui.context import UIContext
from ui.shared import pipeline_timing_payload


def _safe_display_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        return " ".join(str(value).split())
    except Exception:
        return ""


def _source_preview(passage: dict[str, Any], *, max_chars: int = 240) -> str:
    raw = passage.get("text") or passage.get("snippet") or passage.get("raw_content") or ""
    text = _safe_display_value(raw)
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)].rstrip() + "..."


def _source_sort_key(item: tuple[str, Any]) -> tuple[int, float, str]:
    url, info = item
    if isinstance(info, dict):
        source_id = info.get("id")
        if isinstance(source_id, (int, float)):
            return (0, float(source_id), url)
        source_id_text = _safe_display_value(source_id)
        if source_id_text.isdigit():
            return (0, float(source_id_text), url)
    return (1, 0.0, url)


def build_followup_source_cards(
    synthesis_sources: Any,
    passages: Any,
) -> list[dict[str, str]]:
    """Build display-only per-message source cards from the exact synthesis source map."""
    if not isinstance(synthesis_sources, dict):
        return []

    passage_by_url: dict[str, dict[str, Any]] = {}
    if isinstance(passages, list):
        for passage in passages:
            if not isinstance(passage, dict):
                continue
            url = _safe_display_value(passage.get("url"))
            if url and url not in passage_by_url:
                passage_by_url[url] = passage

    cards: list[dict[str, str]] = []
    for url, info in sorted(synthesis_sources.items(), key=_source_sort_key):
        if not isinstance(info, dict):
            info = {}
        url_text = _safe_display_value(url)
        passage = passage_by_url.get(url_text, {})
        title = _safe_display_value(info.get("title")) or _safe_display_value(passage.get("title")) or "Untitled"
        card = {
            "source_id": _safe_display_value(info.get("id")) or "?",
            "title": title,
            "domain": _safe_display_value(passage.get("domain")),
            "url": url_text,
            "preview": _source_preview(passage) if passage else "",
        }
        cards.append(card)
    return cards


def build_followup_assistant_message(
    *,
    content: str,
    steps: list[dict[str, Any]],
    source_cards: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content, "steps": steps}
    if source_cards:
        message["source_cards"] = source_cards
    return message


def followup_progress_label(label: str) -> str:
    replacements = {
        "Checking follow-up search need...": "Reviewing thread context...",
        "Existing context sufficient; skipping web search.": "Using saved context...",
        "Existing context sufficient.": "Using saved context.",
    }
    return replacements.get(label, label)


def _render_followup_source_card_details(st: Any, card: dict[str, str]) -> None:
    st.markdown(f"**{card.get('title') or 'Untitled'}**")
    st.caption(f"Source: {card.get('source_id') or '?'}")
    if card.get("domain"):
        st.caption(f"Domain: {card['domain']}")
    if card.get("url"):
        st.caption(f"URL: {card['url']}")
    if card.get("preview"):
        st.write(card["preview"])


def render_followup_source_cards(st: Any, source_cards: Any) -> None:
    if not isinstance(source_cards, list) or not source_cards:
        return

    cards = [card for card in source_cards if isinstance(card, dict)]
    if not cards:
        return

    st.caption("Sources")
    for card in cards:
        source_id = _safe_display_value(card.get("source_id")) or "?"
        title = _safe_display_value(card.get("title")) or "Untitled"
        domain = _safe_display_value(card.get("domain"))
        label_text = domain or title
        label = f"[{source_id}] {label_text}"
        if len(label) > 44:
            label = label[:41].rstrip() + "..."
        if hasattr(st, "popover"):
            with st.popover(label):
                _render_followup_source_card_details(st, card)
        else:
            with st.expander(label, expanded=False):
                _render_followup_source_card_details(st, card)


def render_followup_chat(context: UIContext, session: dict) -> None:
    st = context.st
    os = context.os
    time = context.time
    uuid = context.uuid

    current_date = context.current_date
    DEFAULT_SYSTEM = context.DEFAULT_SYSTEM

    logger = context.logger

    save_session = context.save_session

    parse_domain_list = context.parse_domain_list
    clean_json_response = context.clean_json_response
    safe_stream = context.safe_stream
    ask_model = context.ask_model
    embed_texts = context.embed_texts
    compute_similarities = context.compute_similarities
    process_search_queries = context.process_search_queries
    get_followup_search_params = context.get_followup_search_params
    filter_top_evidence = context.filter_top_evidence
    is_plausible_domain = context.is_plausible_domain

    execution_log_path = context.OUTPUT_DIR / "execution_log.jsonl"

    st.divider()
    st.subheader("💬 Discuss this Research")

    chat_msgs = session.get("chat_messages", [])

    if chat_msgs:
        for msg in chat_msgs:
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant" and msg.get("steps"):
                    with st.expander(f"Completed {len(msg['steps'])} steps", expanded=False):
                        for step in msg["steps"]:
                            st.markdown(f"**{step['action']}**")
                            if step.get("details"):
                                for d in step["details"]:
                                    st.caption(f"• {d}")
                st.markdown(msg["content"].replace("$", "\\$"))
                if msg["role"] == "assistant":
                    render_followup_source_cards(st, msg.get("source_cards"))

    if prompt := st.chat_input("Ask a follow-up question based on this report..."):
        follow_mode = _resolve_followup_mode(session)
        if os.getenv("PROPLEX_DEBUG_FOLLOWUP") == "1":
            assert follow_mode in ("Fast", "Balanced", "Deep"), f"mode missing or invalid: {follow_mode!r}"
        st.session_state.is_running = True
        chat_followup_run_id = str(uuid.uuid4())
        fu_cost_accumulator = CostAccumulator()
        t_follow_start = time.time()
        try:
            log_run_started(
                run_id=chat_followup_run_id,
                session_id=session.get("id"),
                phase="chat_followup",
                query=prompt,
                mode=follow_mode,
                parent_run_id=session.get("run_id"),
                path=execution_log_path,
                logger=logger,
            )
            session["chat_messages"].append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                chat_steps = [
                    {
                        "action": "Searching existing memory",
                        "details": ["Scanning original research report and top evidence passages."],
                    }
                ]
                pconf = session.get("pipeline_config", {}) or {}
                follow_complexity = _complexity_for_ui_mode(follow_mode)
                fu_params = get_followup_search_params(
                    follow_complexity,
                    pconf.get("search_depth"),
                )

                fast_provider = st.session_state.get("fp", "OpenAI")
                if fast_provider == "OpenAI":
                    fast_model = st.session_state.get("fm_oa", "gpt-5.4-mini")
                elif fast_provider == "OpenRouter":
                    fast_model = st.session_state.get("fm_or", "anthropic/claude-haiku-4.5")
                else:
                    fast_model = st.session_state.get("fm_ls", "local-model")

                smart_provider = st.session_state.get("sp", "OpenAI")
                if smart_provider == "OpenAI":
                    smart_model = st.session_state.get("sm_oa", "gpt-5.4")
                elif smart_provider == "OpenRouter":
                    smart_model = st.session_state.get("sm_or", "anthropic/claude-sonnet-4.6")
                else:
                    smart_model = st.session_state.get("sm_ls", "local-model")

                embed_provider = st.session_state.get("ep", "OpenAI")
                embed_model = (
                    st.session_state.get("em_ls", "text-embedding-3-small")
                    if embed_provider != "OpenAI"
                    else "text-embedding-3-small"
                )

                local_url = st.session_state.get("local_url", "http://localhost:1234/v1")
                or_api_key = st.session_state.get("or_key", os.getenv("OPENROUTER_API_KEY", ""))
                use_reasoning = st.session_state.get("use_reasoning", True)
                include_domains = parse_domain_list(st.session_state.get("include_domains_text", ""))
                exclude_domains = parse_domain_list(st.session_state.get("exclude_domains_text", ""))

                existing_passages = session.get("top_passages", [])
                cache_key = f"embs_{session['id']}" if existing_passages else None
                chat_effort = "medium"

                with st.status(followup_progress_label("Checking follow-up search need..."), expanded=True) as chat_status:
                    def write_followup_progress(label: str) -> None:
                        chat_status.write(followup_progress_label(label))

                    outcome = run_followup(
                        query=prompt,
                        session=session,
                        deps=FollowUpDeps(
                            embed_texts=embed_texts,
                            compute_similarities=compute_similarities,
                            search_fn=process_search_queries,
                            ask_model=ask_model,
                            clean_json_response=clean_json_response,
                            synthesis_model_fn=lambda p: ask_model(
                                prompt=p,
                                system_prompt=DEFAULT_SYSTEM["chat_assistant"],
                                provider=smart_provider,
                                model=smart_model,
                                effort=chat_effort,
                                base_url=local_url,
                                api_key=or_api_key,
                                stream=True,
                                use_reasoning=use_reasoning,
                                cost_accumulator=fu_cost_accumulator,
                                cost_phase="model",
                            ),
                            cost_accumulator=fu_cost_accumulator,
                            execution_log_path=execution_log_path,
                            logger=logger,
                        ),
                        current_date=current_date,
                        follow_complexity=follow_complexity,
                        fu_params=fu_params,
                        intent=pconf.get("intent", "general"),
                        include_domains=include_domains,
                        exclude_domains=exclude_domains,
                        embed_provider=embed_provider,
                        embed_model=embed_model,
                        fast_provider=fast_provider,
                        fast_model=fast_model,
                        local_url=local_url,
                        api_key=or_api_key,
                        use_reasoning=use_reasoning,
                        chat_evaluator_prompt=DEFAULT_SYSTEM["chat_evaluator"],
                        is_plausible_domain=is_plausible_domain,
                        existing_embeddings=st.session_state.get(cache_key) if cache_key else None,
                        run_id=chat_followup_run_id,
                        session_id=session.get("id"),
                        status_container=chat_status,
                        on_progress=write_followup_progress,
                        entity_hint=(session.get("core_topic") or session.get("query") or "").strip() or None,
                    )
                    if cache_key and cache_key not in st.session_state and outcome.memory_result.existing_embeddings is not None:
                        st.session_state[cache_key] = outcome.memory_result.existing_embeddings

                    web_result = outcome.web_result
                    if web_result.search_ran:
                        chat_steps.append(
                            {"action": "Searching the web", "details": outcome.memory_result.followup_queries}
                        )
                        session["seen_urls"] = web_result.seen_urls
                        if web_result.collected_images:
                            session.setdefault("collected_images", []).extend(web_result.collected_images)
                            session["collected_images"] = list(set(session["collected_images"]))

                    if web_result.new_passages:
                        chat_status.update(label="Follow-up search complete", state="complete")
                        chat_steps.append(
                            {
                                "action": "Reading new sources",
                                "details": [f"Integrated {len(web_result.new_passages)} new evidence passages."],
                            }
                        )
                        session["top_passages"].extend(web_result.new_passages)
                        session["top_passages"].sort(key=lambda x: x.get("score", 0), reverse=True)
                        max_domain_chunks = (
                            4 if follow_complexity == "high" else (3 if follow_complexity == "medium" else 2)
                        )
                        session["top_passages"] = filter_top_evidence(session["top_passages"], 60, max_domain_chunks)
                        ensure_passage_source_ids(session["top_passages"])
                        st.session_state.pop(f"embs_{session['id']}", None)
                    elif web_result.search_ran:
                        chat_status.update(label="No new readable text found.", state="error")
                    else:
                        chat_status.update(label=followup_progress_label("Existing context sufficient."), state="complete")

                synthesis_result = outcome.synthesis_result

                if chat_steps:
                    with st.expander(f"Completed {len(chat_steps)} steps", expanded=False):
                        for step in chat_steps:
                            st.markdown(f"**{step['action']}**")
                            if step.get("details"):
                                for d in step["details"]:
                                    st.caption(f"• {d}")

                if synthesis_result.error:
                    response = synthesis_result.answer
                    st.markdown(response.replace("$", "\\$"))
                elif synthesis_result.stream is not None:
                    response = st.write_stream(safe_stream(synthesis_result.stream))
                else:
                    response = synthesis_result.answer
                    st.markdown(response.replace("$", "\\$"))

                source_cards = build_followup_source_cards(
                    synthesis_result.sources,
                    list(session.get("top_passages", []) or []) + list(web_result.new_passages or []),
                )
                followup_diagnostics = build_followup_diagnostics(
                    memory_result=outcome.memory_result,
                    web_result=web_result,
                    synthesis_result=synthesis_result,
                    source_cards=source_cards,
                    prompt=prompt,
                    answer_text=response if isinstance(response, str) else None,
                )
                render_followup_source_cards(st, source_cards)
                session["chat_messages"].append(
                    build_followup_assistant_message(
                        content=response,
                        steps=chat_steps,
                        source_cards=source_cards,
                    )
                )
                save_session(session)

            latency_follow = round(time.time() - t_follow_start, 2)
            log_run_completed(
                run_id=chat_followup_run_id,
                session_id=session.get("id"),
                phase="chat_followup",
                latency_seconds=latency_follow,
                mode=follow_mode,
                parent_run_id=session.get("run_id"),
                timing=dict(
                    pipeline_timing_payload(
                        latency_seconds=latency_follow,
                        pre_retrieval_seconds=0.0,
                        recon_seconds=0.0,
                        iter_timing_seconds={},
                        scout_llm_seconds=0.0,
                        expander_llm_seconds=0.0,
                        gap_evaluator_llm_seconds=0.0,
                        economist_seconds=0.0,
                        analyst_seconds=0.0,
                        synth_evaluator_seconds=0.0,
                        scrutineer_seconds=0.0,
                        author_seconds=latency_follow,
                    )
                ),
                path=execution_log_path,
                logger=logger,
            )
            log_chat_followup_completed(
                run_id=chat_followup_run_id,
                session_id=session.get("id"),
                parent_run_id=session.get("run_id"),
                query_preview=prompt,
                mode=follow_mode,
                latency_seconds=latency_follow,
                cost=fu_cost_accumulator.snapshot(),
                timing=dict(
                    pipeline_timing_payload(
                        latency_seconds=latency_follow,
                        pre_retrieval_seconds=0.0,
                        recon_seconds=0.0,
                        iter_timing_seconds={},
                        scout_llm_seconds=0.0,
                        expander_llm_seconds=0.0,
                        gap_evaluator_llm_seconds=0.0,
                        economist_seconds=0.0,
                        analyst_seconds=0.0,
                        synth_evaluator_seconds=0.0,
                        scrutineer_seconds=0.0,
                        author_seconds=latency_follow,
                    )
                ),
                followup_diagnostics=followup_diagnostics,
                path=execution_log_path,
                logger=logger,
            )
        except Exception as chat_exc:
            logger.exception("Chat follow-up failed")
            latency_fail = round(time.time() - t_follow_start, 2)
            log_run_failed(
                run_id=chat_followup_run_id,
                session_id=session.get("id"),
                phase="chat_followup",
                latency_seconds=latency_fail,
                error=chat_exc,
                mode=follow_mode,
                parent_run_id=session.get("run_id"),
                path=execution_log_path,
                logger=logger,
            )
            log_chat_followup_completed(
                run_id=chat_followup_run_id,
                session_id=session.get("id"),
                parent_run_id=session.get("run_id"),
                query_preview=prompt,
                mode=follow_mode,
                latency_seconds=latency_fail,
                cost=fu_cost_accumulator.snapshot(),
                path=execution_log_path,
                logger=logger,
            )
            st.error(f"Follow-up failed: {chat_exc}")
        finally:
            st.session_state.is_running = False
