from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from core.cost_accounting import CostAccumulator
from core.followup_initial_state_contract import (
    FOLLOWUP_INITIAL_STATE_TRACE_KEY,
    build_followup_initial_controller_state,
    detect_ambiguity_cue,
    detect_contradiction_cue,
    detect_followup_required_source_classes,
    detect_freshness_cue,
    detect_source_constraint_type,
    evaluate_followup_saved_context_authority,
    execute_followup_initial_state_handoff,
    prompt_context_metadata,
    saved_context_satisfies_required_classes,
)
from core.output_validation import enforce_table_width, stream_apply_table_width
from core.pipeline_config import UI_MODES, PipelineConfig
from core.provider_diagnostics import provider_diagnostics_payload, supported_diagnostic_kwargs
from core.run_logging import log_provider_error


def _cost_kw(cost_accumulator: CostAccumulator | None, *, phase: str) -> dict[str, Any]:
    if cost_accumulator is None:
        return {}
    return {"cost_accumulator": cost_accumulator, "cost_phase": phase}

CHAT_FOLLOWUP_FORMAT_RULES = (
    "FOLLOW-UP FORMAT:\n"
    "- Do not produce markdown tables wider than 4 columns.\n"
    "- When comparing two or more entities across many dimensions, use one markdown section per entity "
    "(`## Name - What the Data Shows`) with short bullets instead of wide multi-column grids.\n"
    "- For route-specific CASM / seat-mile cost comparisons: lead with **one compact summary table with at most 3 columns** "
    "(e.g. Aircraft | CASM or unit cost | route/context basis), then a brief caveat paragraph - not the reverse.\n\n"
)

TIER_INSTRUCTIONS = {
    "low": (
        "TIER: FAST. You are working from unanalyzed search snippets. Do not synthesize competing claims into a single "
        "assertion - present them as reported. Cap confidence language. Prefer 'reportedly,' 'according to,' "
        "or 'as of [date]' over declarative present-tense claims. The absence of an analyst pass means unresolved "
        "conflicts in the evidence should remain visible rather than being collapsed into a single verdict. Provide a "
        "direct opening answer followed by no more than 3-4 short supporting sentences. No headers. No sources section "
        "at the end (use inline citations only). Tone: direct answer, not a report."
    ),
    "medium": (
        "TIER: BALANCED. Write a structured brief. Use H3 headers for sections, narrative paragraphs, and a Sources "
        "list at the end when helpful. For comparisons across many dimensions, prefer one section per entity with "
        "bullets - do not use tables wider than 4 columns. Optional: one compact summary table with at most 3 columns "
        "after bullets."
    ),
    "high": (
        "TIER: DEEP. Write a dense intelligence-style answer with H3/H4 subsections and a Sources list. Do not "
        "produce markdown tables wider than 4 columns. For multi-entity comparatives, use one section per entity "
        "with bullets; add at most one compact summary table (<=3 columns) if it clarifies costs or metrics - avoid "
        "wide grids."
    ),
}


@dataclass
class MemorySearchResult:
    sources: dict[str, dict[str, Any]]
    next_source_id: int
    conversation_history: str
    query_embedding: list[float]
    existing_evidence_block: str
    needs_search: bool
    followup_queries: list[str]
    evaluator_parse_status: str = "unknown"
    existing_embeddings: Any = None
    required_source_classes: tuple[str, ...] = ()
    source_obligation_status: str = "not_required"
    source_obligation_reason: str = ""
    source_obligation_note: str = ""
    saved_context_source_sufficient: bool | str = "not_required"
    saved_context_reuse_decision: str = "reuse_as_sufficient_context"
    followup_initial_state_trace: dict[str, Any] = field(default_factory=dict)


@dataclass
class WebRetrievalResult:
    sources: dict[str, dict[str, Any]]
    next_source_id: int
    new_passages: list[dict[str, Any]]
    new_evidence_block: str
    seen_urls: list[str]
    collected_images: list[str]
    search_ran: bool = False
    error: str | None = None
    provider_diagnostics: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SynthesisResult:
    answer: str
    prompt_used: str
    sources: dict[str, dict[str, Any]]
    sources_text: str
    stream: Any | None = None
    error: str | None = None


@dataclass
class FollowUpDeps:
    """Injectables for follow-up: embeddings, search, evaluator model, and synthesis model."""

    embed_texts: Callable[..., list]
    compute_similarities: Callable[..., Any]
    search_fn: Callable[..., list[dict[str, Any]]]
    ask_model: Callable[..., Any]
    clean_json_response: Callable[[str], str]
    synthesis_model_fn: Callable[..., Any]
    cost_accumulator: CostAccumulator | None = None
    execution_log_path: Path | None = None
    logger: Any = None


@dataclass
class FollowUpRunResult:
    memory_result: MemorySearchResult
    web_result: WebRetrievalResult
    synthesis_result: SynthesisResult


def resolve_followup_mode(session: dict[str, Any]) -> str:
    """Research strategy for chat follow-ups: inherit the parent run, not sidebar defaults."""
    mode = session.get("last_report_mode")
    if mode in UI_MODES:
        return str(mode)
    pc = PipelineConfig.from_mapping(session.get("pipeline_config"))
    if pc.mode in UI_MODES:
        return str(pc.mode)
    complexity = str(pc.complexity or "medium").lower()
    return {"low": "Fast", "medium": "Balanced", "high": "Deep"}.get(complexity, "Balanced")


def complexity_for_ui_mode(mode: str) -> str:
    return {"Fast": "low", "Balanced": "medium", "Deep": "high"}.get(mode, "medium")


def build_source_map(passages: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], int]:
    sources: dict[str, dict[str, Any]] = {}
    current_id = 1
    for passage in passages:
        url = passage.get("url") or ""
        if not url or url in sources:
            continue
        sources[url] = {"title": passage.get("title", "Untitled"), "id": current_id}
        current_id += 1
    return sources, current_id


def build_sources_text(
    sources: dict[str, dict[str, Any]],
    is_plausible_domain: Callable[[str], bool],
) -> str:
    return "\n".join(
        f"[{info['id']}] {info.get('title', 'Untitled')} - {url}"
        for url, info in sources.items()
        if is_plausible_domain(url)
    )


def build_conversation_history(
    *,
    chat_messages: list[dict[str, Any]],
    current_date: str,
    ask_model: Callable[..., str],
    fast_provider: str,
    fast_model: str,
    local_url: str,
    api_key: str,
    use_reasoning: bool,
    cost_accumulator: CostAccumulator | None = None,
) -> str:
    if len(chat_messages) <= 12:
        return "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_messages[:-1]])

    older_msgs = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_messages[:-6]])
    summary_prompt = (
        f"Today is {current_date}.\n"
        f"Summarize this conversation history concisely to retain critical context for the assistant:\n{older_msgs}"
    )
    summary = ask_model(
        summary_prompt,
        "You are a concise summarizer.",
        provider=fast_provider,
        model=fast_model,
        effort="low",
        base_url=local_url,
        api_key=api_key,
        use_reasoning=use_reasoning,
        **_cost_kw(cost_accumulator, phase="model"),
    )
    recent = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_messages[-6:-1]])
    return f"Summary of older conversation:\n{summary}\n\nRecent Conversation:\n{recent}"


def run_memory_search_and_evaluator(
    *,
    prompt: str,
    session: dict[str, Any],
    current_date: str,
    fu_params: dict[str, Any],
    fast_provider: str,
    fast_model: str,
    local_url: str,
    api_key: str,
    use_reasoning: bool,
    embed_provider: str,
    embed_model: str,
    embed_texts: Callable[..., list],
    compute_similarities: Callable[..., Any],
    ask_model: Callable[..., str],
    clean_json_response: Callable[[str], str],
    chat_evaluator_prompt: str,
    existing_embeddings: Any = None,
    logger: Any = None,
    cost_accumulator: CostAccumulator | None = None,
) -> MemorySearchResult:
    """Search original evidence memory and decide whether web follow-up retrieval is needed."""
    top_passages = session.get("top_passages", []) or []
    sources, next_source_id = build_source_map(top_passages)
    conversation_history = build_conversation_history(
        chat_messages=session.get("chat_messages", []) or [],
        current_date=current_date,
        ask_model=ask_model,
        fast_provider=fast_provider,
        fast_model=fast_model,
        local_url=local_url,
        api_key=api_key,
        use_reasoning=use_reasoning,
        cost_accumulator=cost_accumulator,
    )

    query_embedding = embed_texts(
        [prompt],
        provider=embed_provider,
        model=embed_model,
        base_url=local_url,
        **_cost_kw(cost_accumulator, phase="embedding"),
    )[0]

    existing_evidence_block = ""
    if top_passages:
        if existing_embeddings is None:
            existing_embeddings = embed_texts(
                [p.get("text", "") for p in top_passages],
                provider=embed_provider,
                model=embed_model,
                base_url=local_url,
                **_cost_kw(cost_accumulator, phase="embedding"),
            )

        sim_scores = compute_similarities(query_embedding, existing_embeddings)
        score_values = sim_scores.tolist() if hasattr(sim_scores, "tolist") else list(sim_scores)
        scored_existing = list(zip(score_values, top_passages))
        scored_existing.sort(key=lambda x: x[0], reverse=True)
        relevant_existing = [p for _, p in scored_existing[:5]]
        existing_evidence_block = "\n\n".join(
            f"[Memory Source {sources[p.get('url', '')]['id']}] {p.get('title', 'Untitled')}: {(p.get('text') or '')[:800]}"
            for p in relevant_existing
            if p.get("url") in sources
        )

    eval_prompt = (
        f"Today is {current_date}.\n"
        f"Existing Report:\n{session.get('report', '')}\n\n"
        f"Raw Source Excerpts (from memory):\n{existing_evidence_block}\n\n"
        f"Conversation History:\n{conversation_history}\n\n"
        f"User's Follow-up Question: {prompt}\n\n"
        "Execute the chat evaluator instructions."
    )

    eval_res = clean_json_response(
        ask_model(
            eval_prompt,
            chat_evaluator_prompt,
            provider=fast_provider,
            model=fast_model,
            effort="low",
            base_url=local_url,
            api_key=api_key,
            require_json=True,
            use_reasoning=use_reasoning,
            **_cost_kw(cost_accumulator, phase="model"),
        )
    )

    needs_search = False
    followup_queries: list[str] = []
    evaluator_parse_status = "unknown"
    try:
        eval_data = json.loads(eval_res)
        evaluator_parse_status = "parsed"
        if not eval_data.get("can_answer", True):
            needs_search = True
            followup_queries = eval_data.get("search_queries", [prompt])[: int(fu_params["max_queries"])]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        evaluator_parse_status = "parse_failed"
        if logger is not None:
            logger.warning(f"Evaluator JSON parse failed in chat fallback: {e}")

    followup_initial_state = build_followup_initial_controller_state(
        query=prompt,
        session=session,
    )
    followup_handoff = execute_followup_initial_state_handoff(
        state=followup_initial_state,
        prompt=prompt,
        needs_search=needs_search,
        followup_queries=followup_queries,
        max_queries=int(fu_params["max_queries"]),
    )
    needs_search = followup_handoff.needs_search
    followup_queries = list(followup_handoff.followup_queries)
    required_source_classes = followup_handoff.required_source_classes
    source_obligation_status = followup_handoff.source_obligation_status
    source_obligation_reason = followup_handoff.source_obligation_reason
    source_obligation_note = followup_handoff.source_obligation_note
    saved_context_source_sufficient = followup_handoff.saved_context_source_sufficient
    saved_context_reuse_decision = followup_handoff.saved_context_reuse_decision
    followup_initial_state_trace = followup_initial_state.to_trace()

    return MemorySearchResult(
        sources=sources,
        next_source_id=next_source_id,
        conversation_history=conversation_history,
        query_embedding=query_embedding,
        existing_evidence_block=existing_evidence_block,
        needs_search=needs_search,
        followup_queries=followup_queries,
        evaluator_parse_status=evaluator_parse_status,
        existing_embeddings=existing_embeddings,
        required_source_classes=required_source_classes,
        source_obligation_status=source_obligation_status,
        source_obligation_reason=source_obligation_reason,
        source_obligation_note=source_obligation_note,
        saved_context_source_sufficient=saved_context_source_sufficient,
        saved_context_reuse_decision=saved_context_reuse_decision,
        followup_initial_state_trace=followup_initial_state_trace,
    )


_CITATION_ID_RE = re.compile(r"\[\[(\d{1,4})\]\]|\[(\d{1,4})\]")

_PROTECTED_FOLLOWUP_MARKERS = (
    "raw prompt",
    "raw_prompt",
    "raw provider payload",
    "raw_provider_payload",
    "provider_payload",
    "full_trace",
    "db_row",
    "database row",
    "cache_path",
    "cache path",
    "local packet",
    "output packet",
    "private log",
    "private logs",
    "raw diagnostics",
    "quantitative_packet",
    "economist_v1",
    "source_bound_values",
    "unsupported_values",
    ".env",
    "secret",
    "token",
)


def _redact_followup_protected_text(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text:
        return ""
    redacted_lines: list[str] = []
    for line in text.splitlines():
        folded = line.casefold()
        if any(marker in folded for marker in _PROTECTED_FOLLOWUP_MARKERS):
            redacted_lines.append("[redacted protected material]")
        else:
            redacted_lines.append(line)
    return "\n".join(redacted_lines)


def _apply_followup_source_obligation_refresh(
    *,
    prompt: str,
    top_passages: list[dict[str, Any]],
    needs_search: bool,
    followup_queries: list[str],
    max_queries: int,
) -> tuple[bool, list[str], tuple[str, ...], str, str, str, bool | str]:
    """Legacy-compatible wrapper around Controller-owned follow-up state.

    Kept for existing offline tests and callers; the sufficiency decision is made
    by ``core.followup_initial_state_contract`` rather than this follow-up
    runtime adapter.
    """
    state = build_followup_initial_controller_state(
        query=prompt,
        session={"top_passages": list(top_passages or [])},
    )
    handoff = execute_followup_initial_state_handoff(
        state=state,
        prompt=prompt,
        needs_search=needs_search,
        followup_queries=followup_queries,
        max_queries=max_queries,
    )
    return (
        handoff.needs_search,
        list(handoff.followup_queries),
        handoff.required_source_classes,
        handoff.source_obligation_status,
        handoff.source_obligation_reason,
        handoff.source_obligation_note,
        handoff.saved_context_source_sufficient,
    )


def _detect_followup_required_source_classes(prompt: str | None) -> tuple[str, ...]:
    return detect_followup_required_source_classes(prompt)


def _saved_context_satisfies_required_classes(
    passages: list[dict[str, Any]],
    required_classes: tuple[str, ...],
) -> bool:
    return saved_context_satisfies_required_classes(passages, required_classes)


def _evaluate_followup_saved_context_authority(
    *,
    passages: list[dict[str, Any]],
    required_classes: tuple[str, ...],
):
    return evaluate_followup_saved_context_authority(
        passages=passages,
        required_classes=required_classes,
    )


def _diagnostic_id(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    text = str(value).strip()
    if not text or text == "?":
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _sort_ids(values: set[str]) -> list[str]:
    return sorted(values, key=lambda value: (0, int(value)) if value.isdigit() else (1, value))


def _extract_answer_citation_ids(answer_text: Any) -> list[str]:
    if not isinstance(answer_text, str) or not answer_text:
        return []
    ids: set[str] = set()
    for match in _CITATION_ID_RE.finditer(answer_text):
        citation_id = _diagnostic_id(match.group(1) or match.group(2))
        if citation_id:
            ids.add(citation_id)
    return _sort_ids(ids)


def _extract_available_source_ids(sources: Any) -> list[str]:
    if not isinstance(sources, dict):
        return []
    ids: set[str] = set()
    for info in sources.values():
        if not isinstance(info, dict):
            continue
        source_id = _diagnostic_id(info.get("id"))
        if source_id:
            ids.add(source_id)
    return _sort_ids(ids)


def _extract_source_card_ids(source_cards: Any) -> list[str]:
    if not isinstance(source_cards, list):
        return []
    ids: set[str] = set()
    for card in source_cards:
        if not isinstance(card, dict):
            continue
        source_id = _diagnostic_id(card.get("source_id"))
        if source_id:
            ids.add(source_id)
    return _sort_ids(ids)


def build_source_card_parity_diagnostics(
    *,
    answer_text: Any,
    source_cards: Any,
    available_sources: Any,
    synthesis_error: bool = False,
) -> dict[str, Any]:
    """Diagnostic-only citation/card parity telemetry; never filters or mutates cards."""
    answer_citation_ids = _extract_answer_citation_ids(answer_text)
    source_card_ids = _extract_source_card_ids(source_cards)
    available_source_ids = _extract_available_source_ids(available_sources)

    cited_ids = set(answer_citation_ids)
    card_ids = set(source_card_ids)
    available_ids = set(available_source_ids)
    cited_ids_without_cards = _sort_ids(cited_ids - card_ids)
    card_ids_not_cited = _sort_ids(card_ids - cited_ids) if answer_citation_ids else []
    card_ids_without_available_sources = _sort_ids(card_ids - available_ids) if available_source_ids else []

    if not (answer_citation_ids or source_card_ids or available_source_ids):
        parity_status = "unavailable"
    elif cited_ids_without_cards:
        parity_status = "cited_ids_without_cards"
    elif card_ids_without_available_sources:
        parity_status = "card_ids_without_available_sources"
    elif card_ids_not_cited:
        parity_status = "card_ids_not_cited"
    else:
        parity_status = "ok"

    return {
        "source_card_parity_status": parity_status,
        "answer_citation_ids": answer_citation_ids,
        "source_card_ids": source_card_ids,
        "available_source_ids": available_source_ids,
        "cited_ids_without_cards": cited_ids_without_cards,
        "card_ids_not_cited": card_ids_not_cited,
        "cards_from_error_response": bool(synthesis_error and source_card_ids),
    }


def _observed_followup_route(
    *,
    memory_result: MemorySearchResult,
    web_result: WebRetrievalResult,
    evaluator_parse_status: str,
    followup_queries: list[str],
) -> str:
    if evaluator_parse_status == "parse_failed":
        return "parse_failure_fallback"
    if web_result.error:
        return "retrieval_error_fallback"
    if web_result.search_ran and not web_result.new_passages:
        return "no_results_fallback"
    if web_result.search_ran:
        return "fresh_retrieval"
    if not memory_result.needs_search:
        return "saved_context"
    if memory_result.needs_search and not followup_queries:
        return "missing_followup_queries_fallback"
    return "unknown"


def _shadow_followup_route(
    *,
    observed_route: str,
    evaluator_parse_status: str,
    freshness_cue_type: str,
    source_constraint_type: str,
    contradiction_cue_detected: bool,
    ambiguity_cue_detected: bool,
    no_results: bool,
    retrieval_error: bool,
) -> tuple[str, str]:
    if evaluator_parse_status == "parse_failed":
        return "parse_failure_fallback", "evaluator_parse_failed"
    if ambiguity_cue_detected:
        return "clarification", "ambiguity_cue_detected"
    if source_constraint_type != "none":
        return "source_constrained_retrieval", f"source_constraint:{source_constraint_type}"
    if contradiction_cue_detected:
        return "contradiction_retrieval", "contradiction_cue_detected"
    if freshness_cue_type != "none":
        return "fresh_retrieval", f"freshness_cue:{freshness_cue_type}"
    if retrieval_error:
        return "retrieval_error_fallback", "retrieval_error"
    if no_results:
        return "weak_no_answer", "no_results"
    return observed_route, "observed_current_behavior"


def build_followup_diagnostics(
    *,
    memory_result: MemorySearchResult,
    web_result: WebRetrievalResult,
    synthesis_result: SynthesisResult,
    source_cards: Any,
    prompt: str | None = None,
    answer_text: str | None = None,
) -> dict[str, Any]:
    """Diagnostic-only route/search telemetry for chat follow-up completion logs."""
    followup_queries = list(memory_result.followup_queries or [])
    source_card_count = len(source_cards) if isinstance(source_cards, list) else 0
    retrieval_error_preview = web_result.error[:300] if web_result.error else None
    evaluator_parse_status = memory_result.evaluator_parse_status
    if evaluator_parse_status not in ("parsed", "parse_failed", "unknown"):
        evaluator_parse_status = "unknown"
    search_skip_reason = None
    if not web_result.search_ran:
        if not memory_result.needs_search:
            search_skip_reason = "existing_context_sufficient"
        elif not followup_queries:
            search_skip_reason = "missing_followup_queries"
    freshness_cue_type = detect_freshness_cue(prompt)
    freshness_cue_detected = freshness_cue_type != "none"
    source_constraint_type = detect_source_constraint_type(prompt)
    source_constraint_detected = source_constraint_type != "none"
    contradiction_cue_detected = detect_contradiction_cue(prompt)
    ambiguity_cue_detected = detect_ambiguity_cue(prompt)
    no_results = bool(web_result.search_ran and not web_result.error and not web_result.new_passages)
    retrieval_error = bool(web_result.error)
    observed_route = _observed_followup_route(
        memory_result=memory_result,
        web_result=web_result,
        evaluator_parse_status=evaluator_parse_status,
        followup_queries=followup_queries,
    )
    shadow_route, shadow_reason = _shadow_followup_route(
        observed_route=observed_route,
        evaluator_parse_status=evaluator_parse_status,
        freshness_cue_type=freshness_cue_type,
        source_constraint_type=source_constraint_type,
        contradiction_cue_detected=contradiction_cue_detected,
        ambiguity_cue_detected=ambiguity_cue_detected,
        no_results=no_results,
        retrieval_error=retrieval_error,
    )
    saved_context_sufficient: bool | str
    if evaluator_parse_status == "parsed":
        saved_context_sufficient = not bool(memory_result.needs_search)
    else:
        saved_context_sufficient = "unknown"
    parity_diagnostics = build_source_card_parity_diagnostics(
        answer_text=answer_text if answer_text is not None else synthesis_result.answer,
        source_cards=source_cards,
        available_sources=synthesis_result.sources,
        synthesis_error=bool(synthesis_result.error),
    )

    return {
        "followup_route_observed": observed_route,
        "followup_route_shadow": shadow_route,
        "followup_route_reason": shadow_reason,
        "evaluator_parse_status": evaluator_parse_status,
        "saved_context_sufficient": saved_context_sufficient,
        "freshness_cue_detected": freshness_cue_detected,
        "freshness_cue_type": freshness_cue_type,
        "would_require_fresh_retrieval": bool(
            freshness_cue_detected or source_constraint_detected or contradiction_cue_detected
        ),
        "required_source_classes": list(memory_result.required_source_classes),
        "source_obligation_status": memory_result.source_obligation_status,
        "source_obligation_reason": memory_result.source_obligation_reason,
        "saved_context_source_sufficient": memory_result.saved_context_source_sufficient,
        "saved_context_reuse_decision": memory_result.saved_context_reuse_decision,
        FOLLOWUP_INITIAL_STATE_TRACE_KEY: memory_result.followup_initial_state_trace,
        "source_constraint_detected": source_constraint_detected,
        "source_constraint_type": source_constraint_type,
        "contradiction_cue_detected": contradiction_cue_detected,
        "ambiguity_cue_detected": ambiguity_cue_detected,
        "needs_search": bool(memory_result.needs_search),
        "followup_query_count": len(followup_queries),
        "query_count": len(followup_queries),
        "queries_preview": [str(query)[:200] for query in followup_queries[:5]],
        "search_ran": bool(web_result.search_ran),
        "search_skip_reason": search_skip_reason,
        "new_passage_count": len(web_result.new_passages or []),
        "retrieval_error": retrieval_error,
        "retrieval_error_preview": retrieval_error_preview,
        "no_results": no_results,
        "source_card_count": source_card_count,
        "synthesis_error": bool(synthesis_result.error),
        **provider_diagnostics_payload(web_result.provider_diagnostics),
        **parity_diagnostics,
    }


def add_passages_to_source_map(
    sources: dict[str, dict[str, Any]],
    current_id: int,
    passages: list[dict[str, Any]],
) -> int:
    for passage in passages:
        url = passage.get("url") or ""
        if not url or url in sources:
            continue
        sources[url] = {"title": passage.get("title", "Untitled"), "id": current_id}
        current_id += 1
    return current_id


def build_new_evidence_block(
    passages: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    max_chars: int = 1000,
) -> str:
    lines: list[str] = []
    for passage in passages:
        url = passage.get("url") or ""
        if url not in sources:
            continue
        sid = sources[url]["id"]
        title = passage.get("title", "Untitled")
        text = (passage.get("text") or "")[:max_chars]
        lines.append(f"[New Source {sid}] {title}\nURL: {url}\nExcerpt: {text}")
    return "\n\n".join(lines)


def run_web_retrieval(
    *,
    memory_result: MemorySearchResult,
    session: dict[str, Any],
    intent: str,
    complexity: str,
    fu_params: dict[str, Any],
    include_domains: list[str],
    exclude_domains: list[str],
    embed_provider: str,
    embed_model: str,
    local_url: str,
    embed_texts: Callable[..., list],
    compute_similarities: Callable[..., Any],
    search_fn: Callable[..., list[dict[str, Any]]],
    status_container: Any = None,
    on_progress: Callable[[str], None] | None = None,
    entity_hint: str | None = None,
    logger: Any = None,
    run_id: str | None = None,
    session_id: str | None = None,
    execution_log_path: Path | None = None,
    cost_accumulator: CostAccumulator | None = None,
) -> WebRetrievalResult:
    sources = {url: dict(info) for url, info in memory_result.sources.items()}
    next_source_id = memory_result.next_source_id
    seen_urls = set(session.get("seen_urls", []) or [])
    collected_images: set[str] = set()
    provider_diagnostics: list[dict[str, Any]] = []

    if not memory_result.needs_search or not memory_result.followup_queries:
        if on_progress:
            on_progress("Existing context sufficient; skipping web search.")
        return WebRetrievalResult(
            sources=sources,
            next_source_id=next_source_id,
            new_passages=[],
            new_evidence_block="",
            seen_urls=list(seen_urls),
            collected_images=[],
            search_ran=False,
            provider_diagnostics=provider_diagnostics,
        )

    if on_progress:
        on_progress(f"Searching the web: {memory_result.followup_queries}")

    kwargs: dict[str, Any] = {
        "status_container": status_container,
        "linkup_depth_override": fu_params.get("linkup_depth_override"),
        "entity_hint": entity_hint,
    }
    if status_container is None:
        kwargs.pop("status_container")
    kwargs.update(
        supported_diagnostic_kwargs(
            search_fn,
            {
                "provider_diagnostics": provider_diagnostics,
                "provider_role": "chat_followup_search",
            },
        )
    )

    try:
        passages = search_fn(
            memory_result.followup_queries,
            intent,
            complexity,
            str(fu_params["search_depth"]),
            int(fu_params["max_results"]),
            include_domains,
            exclude_domains,
            memory_result.query_embedding,
            seen_urls,
            collected_images,
            embed_provider,
            embed_model,
            local_url,
            embed_texts,
            compute_similarities,
            **_cost_kw(cost_accumulator, phase="retrieval"),
            **kwargs,
        )
    except Exception as e:
        if logger is not None:
            logger.warning(f"Follow-up web retrieval failed: {e}")
        log_provider_error(
            provider="followup_web_retrieval",
            error=str(e),
            query_preview=str(memory_result.followup_queries)[:200],
            run_id=run_id,
            session_id=session_id,
            phase="chat_followup",
            path=execution_log_path,
            logger=logger,
        )
        if on_progress:
            on_progress("Follow-up web retrieval failed; continuing with existing context.")
        return WebRetrievalResult(
            sources=sources,
            next_source_id=next_source_id,
            new_passages=[],
            new_evidence_block="",
            seen_urls=list(seen_urls),
            collected_images=list(collected_images),
            search_ran=True,
            error=str(e)[:1000],
            provider_diagnostics=provider_diagnostics,
        )

    passages = list(passages or [])
    if not passages:
        if on_progress:
            on_progress("No new readable text found.")
        return WebRetrievalResult(
            sources=sources,
            next_source_id=next_source_id,
            new_passages=[],
            new_evidence_block="",
            seen_urls=list(seen_urls),
            collected_images=list(collected_images),
            search_ran=True,
            provider_diagnostics=provider_diagnostics,
        )

    passages.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_passages = passages[: int(fu_params["top_passage_count"])]
    next_source_id = add_passages_to_source_map(sources, next_source_id, top_passages)
    evidence_block = build_new_evidence_block(top_passages, sources)
    if on_progress:
        on_progress(f"Integrated {len(top_passages)} new evidence passages.")

    return WebRetrievalResult(
        sources=sources,
        next_source_id=next_source_id,
        new_passages=top_passages,
        new_evidence_block=evidence_block,
        seen_urls=list(seen_urls),
        collected_images=list(collected_images),
        search_ran=True,
        provider_diagnostics=provider_diagnostics,
    )


def build_image_context(image_urls: list[str] | set[str]) -> str:
    valid_images = [
        url
        for url in image_urls
        if url.startswith("http")
        and any(
            ext in url.lower()
            for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", "images?", "format=jpg", "format=png")
        )
        and len(url) < 600
    ]
    if not valid_images:
        return ""
    image_block = "\n".join(list(valid_images)[:5])
    return (
        f"\n\nAVAILABLE IMAGES:\n{image_block}\n\n"
        "IMAGE RULES: If highly relevant to the follow-up question, you may embed 1-2 images using markdown: "
        "![description](url)."
    )


def tier_instruction(complexity: str) -> str:
    return TIER_INSTRUCTIONS.get(complexity, TIER_INSTRUCTIONS["low"])


def build_followup_prompt(
    *,
    current_date: str,
    report: str,
    existing_evidence_block: str,
    new_evidence_block: str,
    sources_text: str,
    conversation_history: str,
    prompt: str,
    complexity: str,
    image_context: str = "",
    source_obligation_note: str = "",
) -> str:
    parts = [
        "Today is "
        f"{current_date}.\nOriginal Report Context:\n"
        f"{_redact_followup_protected_text(report)}\n",
    ]
    safe_source_obligation_note = _redact_followup_protected_text(source_obligation_note)
    if safe_source_obligation_note:
        parts.append(f"{safe_source_obligation_note}\n")
    if existing_evidence_block:
        parts.append(
            "Raw Source Excerpts for Precision (contains details omitted from report):\n"
            f"{_redact_followup_protected_text(existing_evidence_block)}\n"
        )
    if new_evidence_block:
        parts.append(
            "Newly Gathered Evidence for Follow-up:\n"
            f"{_redact_followup_protected_text(new_evidence_block)}\n"
        )
    parts.append(f"AVAILABLE SOURCES:\n{_redact_followup_protected_text(sources_text)}\n")
    parts.append(
        "Conversation History:\n"
        f"{_redact_followup_protected_text(conversation_history)}\n\n"
        f"USER FOLLOW-UP: {_redact_followup_protected_text(prompt)}\n\n"
        f"{CHAT_FOLLOWUP_FORMAT_RULES}{tier_instruction(complexity)}{image_context}"
    )
    return "\n".join(parts)


def run_followup_synthesis(
    *,
    query: str,
    memory_result: MemorySearchResult,
    web_result: WebRetrievalResult,
    session: dict[str, Any],
    current_date: str,
    follow_complexity: str,
    image_context: str,
    is_plausible_domain: Callable[[str], bool],
    model_fn: Callable[..., Any],
    on_progress: Callable[[str], None] | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    execution_log_path: Path | None = None,
    logger: Any = None,
) -> SynthesisResult:
    sources = {url: dict(info) for url, info in web_result.sources.items()}
    sources_text = build_sources_text(sources, is_plausible_domain)
    prompt_used = build_followup_prompt(
        current_date=current_date,
        report=str(session.get("report") or ""),
        existing_evidence_block=memory_result.existing_evidence_block,
        new_evidence_block=web_result.new_evidence_block,
        sources_text=sources_text,
        conversation_history=memory_result.conversation_history,
        prompt=query,
        complexity=follow_complexity,
        image_context=image_context,
        source_obligation_note=memory_result.source_obligation_note,
    )
    if memory_result.followup_initial_state_trace:
        state = build_followup_initial_controller_state(
            query=query,
            session=session,
            run_id=run_id,
            session_id=session_id,
        )
        memory_result.followup_initial_state_trace = prompt_context_metadata(
            state=state,
            prompt_context=prompt_used,
        ).to_trace()
    if on_progress:
        on_progress("Synthesizing answer")
    try:
        raw = model_fn(prompt_used)
    except Exception as exc:
        log_provider_error(
            provider="followup_synthesis",
            error=str(exc),
            query_preview=query[:200],
            run_id=run_id,
            session_id=session_id,
            phase="chat_followup",
            path=execution_log_path,
            logger=logger,
        )
        return SynthesisResult(
            answer="I encountered an error generating a response. Please try again.",
            prompt_used=prompt_used,
            sources=sources,
            sources_text=sources_text,
            error=str(exc)[:500],
        )
    if isinstance(raw, str):
        return SynthesisResult(
            answer=enforce_table_width(raw),
            prompt_used=prompt_used,
            sources=sources,
            sources_text=sources_text,
        )
    return SynthesisResult(
        answer="",
        prompt_used=prompt_used,
        sources=sources,
        sources_text=sources_text,
        stream=stream_apply_table_width(raw),
    )


def run_followup(
    *,
    query: str,
    session: dict[str, Any],
    deps: FollowUpDeps,
    current_date: str,
    follow_complexity: str,
    fu_params: dict[str, Any],
    intent: str,
    include_domains: list[str],
    exclude_domains: list[str],
    embed_provider: str,
    embed_model: str,
    fast_provider: str,
    fast_model: str,
    local_url: str,
    api_key: str,
    use_reasoning: bool,
    chat_evaluator_prompt: str,
    is_plausible_domain: Callable[[str], bool],
    existing_embeddings: Any = None,
    run_id: str | None = None,
    session_id: str | None = None,
    status_container: Any = None,
    on_progress: Callable[[str], None] | None = None,
    entity_hint: str | None = None,
) -> FollowUpRunResult:
    """Memory search → web retrieval → synthesis. Session passage/image merges stay at the UI layer."""
    if on_progress:
        on_progress("Searching existing memory...")
    memory_result = run_memory_search_and_evaluator(
        prompt=query,
        session=session,
        current_date=current_date,
        fu_params=fu_params,
        fast_provider=fast_provider,
        fast_model=fast_model,
        local_url=local_url,
        api_key=api_key,
        use_reasoning=use_reasoning,
        embed_provider=embed_provider,
        embed_model=embed_model,
        embed_texts=deps.embed_texts,
        compute_similarities=deps.compute_similarities,
        ask_model=deps.ask_model,
        clean_json_response=deps.clean_json_response,
        chat_evaluator_prompt=chat_evaluator_prompt,
        existing_embeddings=existing_embeddings,
        logger=deps.logger,
        cost_accumulator=deps.cost_accumulator,
    )
    web_result = run_web_retrieval(
        memory_result=memory_result,
        session=session,
        intent=intent,
        complexity=follow_complexity,
        fu_params=fu_params,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        embed_provider=embed_provider,
        embed_model=embed_model,
        local_url=local_url,
        embed_texts=deps.embed_texts,
        compute_similarities=deps.compute_similarities,
        search_fn=deps.search_fn,
        status_container=status_container,
        on_progress=on_progress,
        entity_hint=entity_hint,
        logger=deps.logger,
        run_id=run_id,
        session_id=session_id,
        execution_log_path=deps.execution_log_path,
        cost_accumulator=deps.cost_accumulator,
    )
    merged_images = list(set(session.get("collected_images") or []) | set(web_result.collected_images))
    image_context = build_image_context(merged_images)
    synthesis_result = run_followup_synthesis(
        query=query,
        memory_result=memory_result,
        web_result=web_result,
        session=session,
        current_date=current_date,
        follow_complexity=follow_complexity,
        image_context=image_context,
        is_plausible_domain=is_plausible_domain,
        model_fn=deps.synthesis_model_fn,
        on_progress=on_progress,
        run_id=run_id,
        session_id=session_id,
        execution_log_path=deps.execution_log_path,
        logger=deps.logger,
    )
    return FollowUpRunResult(
        memory_result=memory_result,
        web_result=web_result,
        synthesis_result=synthesis_result,
    )
