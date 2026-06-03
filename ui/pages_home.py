"""Home page: new research run, deduplication, and ``run_pipeline`` wiring."""

import re

from core.cost_accounting import CostAccumulator
from core.failure_card import normalize_force_corpus_state
from core.pipeline_orchestrator import PipelineError, run_pipeline
from core.provider_validation import missing_required_api_keys
from core.retrieval import ensure_passage_source_ids
from core.run_config import RunConfig, RunDeps
from core.run_dedup import (
    RUN_DEDUP_TTL_SEC,
    build_run_dedup_key,
    lookup_recent_run,
    lookup_semantic_similar_run,
    normalize_query_for_dedup,
    remember_run_for_dedup,
    routing_key_from_full_dedup_key,
)
from ui.context import UIContext
from ui.pages_demo import render_demo_home_notice
from ui.status import StreamlitStatusWriter


def render_home_page(context: UIContext) -> None:
    st = context.st
    os = context.os
    json = context.json
    time = context.time
    uuid = context.uuid

    OUTPUT_DIR = context.OUTPUT_DIR
    current_date = context.current_date
    DEFAULT_SYSTEM = context.DEFAULT_SYSTEM
    NEWS_PREFERRED_DOMAINS = context.NEWS_PREFERRED_DOMAINS
    ACADEMIC_DOMAINS = context.ACADEMIC_DOMAINS
    QUANT_REPORT_TYPES = context.QUANT_REPORT_TYPES

    logger = context.logger

    load_history = context.load_history
    save_session = context.save_session

    parse_domain_list = context.parse_domain_list
    clean_json_response = context.clean_json_response
    ask_model = context.ask_model
    embed_texts = context.embed_texts
    compute_similarities = context.compute_similarities
    process_search_queries = context.process_search_queries
    filter_top_evidence = context.filter_top_evidence
    is_plausible_domain = context.is_plausible_domain
    anchor_query_to_topic = context.anchor_query_to_topic
    fetch_linkup_precision_block = context.fetch_linkup_precision_block
    run_economist_step = context.run_economist_step
    run_scout = context.run_scout
    should_skip_quant_scout = context.should_skip_quant_scout

    execution_log_path = OUTPUT_DIR / "execution_log.jsonl"
    feedback_log_path = OUTPUT_DIR / "feedback_log.jsonl"
    kb_triggers_path = OUTPUT_DIR / "kb_triggers.jsonl"
    policy_state_path = OUTPUT_DIR / "policy_state.json"
    policy_journal_path = OUTPUT_DIR / "policy_journal.jsonl"

    def _clean_query(q: str) -> str:
        """Normalize query text and drop likely trailing token truncation."""
        q2 = " ".join((q or "").strip().split())
        if not q2:
            return ""
        words = q2.split(" ")
        last = words[-1]
        if len(last) < 3 and last.isalpha() and "." not in last:
            words = words[:-1]
        return " ".join(words)[:300]

    def _extract_year(text: str) -> str:
        m = re.search(r"\b(19|20)\d{2}\b", text or "")
        return m.group(0) if m else "2026"

    def _acc_iter_time(iter_idx: int, started_at: float, acc: dict[int, float]) -> None:
        elapsed = max(0.0, time.monotonic() - started_at)
        acc[iter_idx] = float(acc.get(iter_idx, 0.0)) + elapsed

    st.markdown(
        "<h1 style='text-align: center; font-size: 3rem; font-weight: 400; margin-bottom: 2rem; "
        "letter-spacing: -0.03em; color: #111827;'>ScryRaven</h1>",
        unsafe_allow_html=True,
    )

    _seed_q = st.session_state.pop("proplex_seed_query", None)
    if _seed_q is not None:
        st.session_state["research_topic_ta"] = _seed_q

    render_demo_home_notice(context)

    query = st.text_area("Research topic", placeholder="Ask anything...", height=120, label_visibility="collapsed", key="research_topic_ta")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run = st.button("Start Research", type="primary", use_container_width=True)

    append_meta_pending = st.session_state.get("proplex_append_meta")
    auto_run = bool(st.session_state.get("proplex_auto_run", False))
    run = run or append_meta_pending is not None or auto_run

    if run:
        append_meta = st.session_state.pop("proplex_append_meta", None)
        st.session_state.pop("proplex_auto_run", None)
        try:
            raw_provider_override = st.session_state.get("next_run_provider_override")
            if isinstance(raw_provider_override, str):
                active_search_providers = [raw_provider_override]
            else:
                active_search_providers = list(raw_provider_override or [])
            env_for_validation = dict(os.environ)
            if st.session_state.get("linkup_key"):
                env_for_validation["LINKUP_API_KEY"] = st.session_state.get("linkup_key", "")
            if st.session_state.get("exa_key"):
                env_for_validation["EXA_API_KEY"] = st.session_state.get("exa_key", "")
            missing_keys = missing_required_api_keys(
                fast_provider=st.session_state.get("fp", "OpenAI"),
                smart_provider=st.session_state.get("sp", "OpenAI"),
                embed_provider=st.session_state.get("ep", "OpenAI"),
                active_search_providers=active_search_providers,
                env=env_for_validation,
            )
            if missing_keys:
                for key_name in missing_keys:
                    provider_name = key_name.removesuffix("_API_KEY").lower()
                    if provider_name == "openai":
                        st.error("Provide an OpenAI API key to continue.")
                    else:
                        label = provider_name.title()
                        st.error(f"Provide a {label} API key to continue.")
                st.stop()
            if not query.strip():
                st.warning("Enter a research question before starting.")
                st.stop()

            strategy = st.session_state.get("strategy", "Balanced")
            focus_academic = bool(st.session_state.get("focus_academic", False))
            force_intent_news = bool(st.session_state.get("force_intent_news", False))
            skip_run_dedup = bool(st.session_state.pop("proplex_skip_run_dedup", False))
            dedup_key_this_run: str | None = None

            raw_ov_pre = st.session_state.get("next_run_provider_override")
            pov_tuple: tuple[str, ...] | None = None
            if raw_ov_pre:
                if isinstance(raw_ov_pre, str):
                    s = raw_ov_pre.strip().lower()
                    pov_tuple = (s,) if s else None
                else:
                    pov_tuple = tuple(
                        sorted({str(x).strip().lower() for x in raw_ov_pre if str(x).strip()})
                    ) or None
            force_pre = st.session_state.get("next_run_force_state")
            forced_cs_pre = normalize_force_corpus_state(force_pre) if force_pre else None
            dedup_key_this_run = build_run_dedup_key(
                query=query,
                strategy=strategy,
                focus_academic=focus_academic,
                force_intent_news=force_intent_news,
                provider_override=pov_tuple,
                forced_corpus_state=str(forced_cs_pre or "").strip() or None,
            )

            if not skip_run_dedup and append_meta is None and dedup_key_this_run:
                dedup_cache: dict[str, dict] = st.session_state.setdefault("proplex_run_dedup_cache", {})
                now_ts = time.time()
                hit = lookup_recent_run(
                    dedup_cache, dedup_key_this_run, now=now_ts, ttl_sec=RUN_DEDUP_TTL_SEC
                )
                if hit:
                    sid_hit = str(hit.get("session_id") or "").strip()
                    ago_s = max(0, int(now_ts - float(hit.get("ts") or 0.0)))
                    mins = ago_s // 60
                    ago_human = f"{mins}m ago" if mins else f"{ago_s}s ago"
                    st.warning(
                        f"Same query and routing profile ran recently ({ago_human}, TTL {RUN_DEDUP_TTL_SEC // 60} min). "
                        "Open the existing thread or re-run to start another full pipeline pass."
                    )
                    c_open, c_rerun = st.columns(2)
                    if c_open.button("Open recent thread", key="proplex_dedup_open"):
                        if sid_hit:
                            hist_d = load_history()
                            row = next((x for x in hist_d if x.get("id") == sid_hit), None)
                            if row:
                                passages_file = OUTPUT_DIR / f"{sid_hit}_passages.json"
                                if passages_file.exists():
                                    try:
                                        with open(passages_file, encoding="utf-8") as pf:
                                            row["top_passages"] = json.load(pf)
                                            ensure_passage_source_ids(row["top_passages"])
                                    except Exception:
                                        row["top_passages"] = []
                                else:
                                    row["top_passages"] = []
                                st.session_state.current_session = row
                                st.session_state.current_page = "thread"
                                st.rerun()
                        st.info("That thread is no longer in the library. Use **Re-run anyway**.")
                    if c_rerun.button("Re-run anyway", key="proplex_dedup_force"):
                        st.session_state["proplex_skip_run_dedup"] = True
                        st.rerun()
                    st.warning("Use **Open recent thread** or **Re-run anyway** above to continue.")
                    st.stop()

                skip_semantic_notice = bool(
                    st.session_state.pop("proplex_skip_semantic_similar_notice", False)
                )
                routing_only = routing_key_from_full_dedup_key(dedup_key_this_run)
                embed_provider_pre = st.session_state.get("ep", "OpenAI")
                embed_model_pre = (
                    st.session_state.get("em_ls", "text-embedding-3-small")
                    if embed_provider_pre != "OpenAI"
                    else "text-embedding-3-small"
                )
                local_url_pre = st.session_state.get("local_url", "http://localhost:1234/v1")
                semantic_hit = None
                if not skip_semantic_notice:
                    try:
                        q_emb_pre = embed_texts(
                            [normalize_query_for_dedup(query)],
                            provider=embed_provider_pre,
                            model=embed_model_pre,
                            base_url=local_url_pre,
                        )[0]
                    except Exception as e:
                        logger.warning("Semantic dedup embedding skipped: %s", e)
                        q_emb_pre = []
                    if q_emb_pre:
                        semantic_hit = lookup_semantic_similar_run(
                            dedup_cache,
                            routing_key=routing_only,
                            query_embedding=q_emb_pre,
                            exclude_full_key=dedup_key_this_run,
                            now=now_ts,
                            ttl_sec=RUN_DEDUP_TTL_SEC,
                        )
                if semantic_hit:
                    sid_sem = str(semantic_hit.get("session_id") or "").strip()
                    title_sem = str(semantic_hit.get("title") or "Recent thread").strip()
                    ago_s = max(0, int(now_ts - float(semantic_hit.get("ts") or 0.0)))
                    mins_sem = ago_s // 60
                    ago_human_sem = f"{mins_sem}m ago" if mins_sem else f"{ago_s}s ago"
                    sim_pct = int(round(float(semantic_hit.get("similarity", 0)) * 100))
                    st.warning(
                        f"Your prompt is very similar (~{sim_pct}% embedding match) to a recent run "
                        f"**{title_sem}** ({ago_human_sem}, same routing profile). "
                        "Opening that thread may be faster. This run will still execute unless you navigate away."
                    )
                    c_so, c_sr = st.columns(2)
                    if c_so.button("Open similar thread", key="proplex_semantic_dedup_open"):
                        if sid_sem:
                            hist_sem = load_history()
                            row_sem = next((x for x in hist_sem if x.get("id") == sid_sem), None)
                            if row_sem:
                                passages_file_sem = OUTPUT_DIR / f"{sid_sem}_passages.json"
                                if passages_file_sem.exists():
                                    try:
                                        with open(passages_file_sem, encoding="utf-8") as pf:
                                            row_sem["top_passages"] = json.load(pf)
                                            ensure_passage_source_ids(row_sem["top_passages"])
                                    except Exception:
                                        row_sem["top_passages"] = []
                                else:
                                    row_sem["top_passages"] = []
                                st.session_state.current_session = row_sem
                                st.session_state.current_page = "thread"
                                st.rerun()
                        st.info("That thread is no longer in the library. Use **Run anyway** to suppress this hint.")
                    if c_sr.button("Run anyway", key="proplex_semantic_dedup_force"):
                        st.session_state["proplex_skip_semantic_similar_notice"] = True
                        st.session_state["proplex_auto_run"] = True
                        st.rerun()

            st.session_state.is_running = True

            # --- Build model settings from sidebar ---
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

            # Populate env vars explicitly for APIs that use them from env directly
            if st.session_state.get("linkup_key"):
                os.environ["LINKUP_API_KEY"] = st.session_state.get("linkup_key")
            if st.session_state.get("exa_key"):
                os.environ["EXA_API_KEY"] = st.session_state.get("exa_key")

            use_reasoning = st.session_state.get("use_reasoning", True)
            include_domains = parse_domain_list(st.session_state.get("include_domains_text", ""))
            exclude_domains = parse_domain_list(st.session_state.get("exclude_domains_text", ""))
            cost_accumulator = CostAccumulator()

            base_ask_model = ask_model
            base_embed_texts = embed_texts
            base_process_search_queries = process_search_queries
            base_fetch_linkup_precision_block = fetch_linkup_precision_block

            def ask_model_tracked(*args, **kwargs):
                kwargs.setdefault("cost_accumulator", cost_accumulator)
                kwargs.setdefault("cost_phase", "model")
                return base_ask_model(*args, **kwargs)

            def embed_texts_tracked(*args, **kwargs):
                kwargs.setdefault("cost_accumulator", cost_accumulator)
                kwargs.setdefault("cost_phase", "embedding")
                return base_embed_texts(*args, **kwargs)

            def process_search_queries_tracked(*args, **kwargs):
                kwargs.setdefault("cost_accumulator", cost_accumulator)
                kwargs.setdefault("cost_phase", "retrieval")
                return base_process_search_queries(*args, **kwargs)

            def fetch_linkup_precision_block_tracked(*args, **kwargs):
                kwargs.setdefault("cost_accumulator", cost_accumulator)
                kwargs.setdefault("cost_phase", "retrieval")
                return base_fetch_linkup_precision_block(*args, **kwargs)

            ask_model = ask_model_tracked
            embed_texts = embed_texts_tracked
            process_search_queries = process_search_queries_tracked
            fetch_linkup_precision_block = fetch_linkup_precision_block_tracked

            prior_run_history: list[dict] = []
            prior_snapshot_for_history: dict | None = None
            prior_title_for_thread: str | None = None

            if append_meta:
                sid_am = str(append_meta.get("session_id") or "").strip()
                if sid_am:
                    session_id = sid_am
                    hist0 = load_history()
                    prow = next((x for x in hist0 if x.get("id") == session_id), None)
                    if prow:
                        prior_run_history = list(prow.get("run_history") or [])
                        am_title = str(append_meta.get("title") or "").strip()
                        prior_title_for_thread = am_title or prow.get("title") or (str(prow.get("query") or "")[:40])
                        prid = prow.get("run_id")
                        if prid:
                            prior_snapshot_for_history = {
                                "run_id": prid,
                                "query": prow.get("query"),
                                "report": prow.get("report"),
                                "timestamp": prow.get("timestamp"),
                                "failure_card": prow.get("failure_card"),
                                "core_topic": prow.get("core_topic"),
                                "execution_trace": prow.get("execution_trace"),
                            }
                    else:
                        prior_title_for_thread = str(append_meta.get("title") or "").strip() or None
                else:
                    session_id = str(uuid.uuid4())
            else:
                session_id = str(uuid.uuid4())
            # --- RunConfig: all per-run settings ---
            _raw_ov = st.session_state.pop("next_run_provider_override", None)
            _pov: list[str] | None = None
            if _raw_ov:
                _raw_list = [_raw_ov] if isinstance(_raw_ov, str) else list(_raw_ov)
                _pov = [str(x).strip().lower() for x in _raw_list if str(x).strip()] or None

            run_config = RunConfig(
                query=query,
                mode=strategy,
                current_date=current_date,
                session_id=session_id,
                focus_academic=focus_academic,
                force_intent_news=force_intent_news,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                fast_provider=fast_provider,
                fast_model=fast_model,
                smart_provider=smart_provider,
                smart_model=smart_model,
                embed_provider=embed_provider,
                embed_model=embed_model,
                local_url=local_url,
                or_api_key=or_api_key,
                use_reasoning=use_reasoning,
                provider_override=_pov,
                forced_corpus_state=st.session_state.pop("next_run_force_state", None),
                prior_run_history=prior_run_history,
                prior_snapshot_for_history=prior_snapshot_for_history,
                prior_title=prior_title_for_thread,
            )

            # --- RunDeps: injected callables and paths ---
            run_deps = RunDeps(
                ask_model=ask_model,
                embed_texts=embed_texts,
                compute_similarities=compute_similarities,
                process_search_queries=process_search_queries,
                filter_top_evidence=filter_top_evidence,
                is_plausible_domain=is_plausible_domain,
                anchor_query_to_topic=anchor_query_to_topic,
                fetch_linkup_precision_block=fetch_linkup_precision_block,
                run_economist_step=run_economist_step,
                run_scout=run_scout,
                should_skip_quant_scout=should_skip_quant_scout,
                clean_json_response=clean_json_response,
                DEFAULT_SYSTEM=DEFAULT_SYSTEM,
                NEWS_PREFERRED_DOMAINS=NEWS_PREFERRED_DOMAINS,
                ACADEMIC_DOMAINS=ACADEMIC_DOMAINS,
                QUANT_REPORT_TYPES=QUANT_REPORT_TYPES,
                logger=logger,
                execution_log_path=execution_log_path,
                feedback_log_path=feedback_log_path,
                kb_triggers_path=kb_triggers_path,
                policy_state_path=policy_state_path,
                policy_journal_path=policy_journal_path,
            )

            cost_accumulator = CostAccumulator()
            with st.status("Running pipeline...", expanded=True) as _st_status:
                _status_writer = StreamlitStatusWriter(_st_status)
                _stream_box = st.container()

                def _author_stream_display(chunks):
                    with _stream_box:
                        st.write_stream(chunks)

                run_config.author_stream_display = _author_stream_display
                outcome = run_pipeline(run_config, run_deps, _status_writer, cost_accumulator)

            if not outcome.author_streamed:
                st.subheader("Report")
                st.markdown(outcome.report)

            # KB warning (only surfaces when KB agent found a likely-recurring issue)
            if outcome.kb_warning:
                st.warning(f"KB: {outcome.kb_warning[:500]}")

            # Stash instrumentation for the thread view
            st.session_state["last_kb_instrumentation"] = outcome.kb_instrumentation or {}

            # Update run-dedup cache (in-session only; CLI has no cache)
            if append_meta is None and dedup_key_this_run:
                _dedup_cache_post = st.session_state.setdefault("proplex_run_dedup_cache", {})
                _rk_post = routing_key_from_full_dedup_key(dedup_key_this_run)
                _dedup_emb_post: list[float] | None = None
                try:
                    _dedup_emb_post = embed_texts(
                        [normalize_query_for_dedup(query)],
                        provider=embed_provider,
                        model=embed_model,
                        base_url=local_url,
                    )[0]
                except Exception as _e:
                    logger.warning("Semantic dedup post-run embedding skipped: %s", _e)
                remember_run_for_dedup(
                    _dedup_cache_post,
                    dedup_key_this_run,
                    session_id=outcome.session_id,
                    title=str(outcome.new_session.get("title") or "")[:200],
                    ts=time.time(),
                    routing_key=_rk_post,
                    query_embedding=_dedup_emb_post,
                )

            # Save session and navigate to thread view
            new_session = outcome.new_session
            save_session(new_session)
            st.session_state.current_session = new_session
            st.session_state.current_page = "thread"
            st.rerun()

        except (PipelineError, Exception):
            # run_pipeline() logs run_failed internally; re-raise for Streamlit.
            raise
        finally:
            st.session_state.is_running = False
