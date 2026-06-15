"""RunKernel-authorized query production and QueryPlan admission boundaries.

AG-91I moves initial router-posture overrides, recon/researcher candidate
production, and candidate-source selection behind a RunKernel action. QueryPlan
admission still owns final query identity/order/finalization.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable, Mapping, MutableSequence, Sequence
from dataclasses import dataclass
from typing import Any

from core.anchor_resolution import (
    build_shadow_anchor_packet,
    format_anchor_context_for_researcher,
)
from core.nutrition_lookup import detect_nutrition_lookup_telemetry
from core.provider_diagnostics import build_provider_attempt_diagnostic
from core.query_plan import QUERY_PLAN_TRACE_KEY, QueryPlanRole
from core.query_plan_runtime_adapter import QueryPlanRuntimeAdapter
from core.retrieval_quality import (
    extract_recon_context,
    official_bias_phrase,
    wants_official_source_bias,
)
from core.router_query_preparation_contract import (
    RouterQueryPreparationState,
    with_router_query_runtime_posture,
)
from core.run_authority_contract import contract_query_hints_from_projection
from core.run_kernel import (
    QUERY_PLAN_ADMISSION_STAGE,
    QUERY_PRODUCTION_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)


def brave_reconnaissance(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    """Import the live provider boundary only when recon actually uses it."""

    from core.search_providers import brave_reconnaissance as _brave_reconnaissance

    return _brave_reconnaissance(*args, **kwargs)

_RECON_QUERY_TYPES = frozenset({"person", "news", "current_events", "event"})


@dataclass(frozen=True, slots=True)
class QueryProductionAdmissionInputs:
    """Reduced query-production projection consumed by QueryPlan admission."""

    candidate_queries: list[str]
    candidate_source: str
    effective_route_posture: dict[str, Any]
    contract_source_requirement_hints: list[dict[str, Any]]

    @property
    def query_type(self) -> str:
        return str(self.effective_route_posture["query_type"])

    @property
    def max_queries(self) -> int:
        return int(self.effective_route_posture["max_queries"])


@dataclass(frozen=True, slots=True)
class QueryProductionResult:
    """Query-production output plus the kernel observation to reduce."""

    candidate_queries: list[str]
    candidate_source: str
    effective_route_posture: dict[str, Any]
    include_domains: list[str]
    anchor_packet_telemetry: dict[str, Any]
    nutrition_lookup_telemetry: dict[str, Any]
    waste_flags: list[str]
    recon_fired: bool
    recon_confidence: str | None
    canonical_subject_resolved: str | None
    recon_seconds: float
    researcher_fallback_status: str
    empty_entity_flag: bool
    contract_source_requirement_hints: list[dict[str, Any]]
    observation: Observation

    @property
    def intent(self) -> str:
        return str(self.effective_route_posture["intent"])

    @property
    def report_type(self) -> str:
        return str(self.effective_route_posture["report_type"])

    @property
    def image_mode(self) -> str:
        return str(self.effective_route_posture["image_mode"])

    @property
    def core_topic(self) -> str:
        return str(self.effective_route_posture["core_topic"])

    @property
    def query_type(self) -> str:
        return str(self.effective_route_posture["query_type"])

    @property
    def primary_entity(self) -> str:
        return str(self.effective_route_posture["primary_entity"])

    @property
    def entities_list(self) -> list[str]:
        return list(self.effective_route_posture["entities_list"])

    @property
    def is_academic(self) -> bool:
        return bool(self.effective_route_posture["is_academic"])

    @property
    def routing_override_applied(self) -> bool:
        return bool(self.effective_route_posture["routing_override_applied"])

    @property
    def routing_override_reason(self) -> str | None:
        reason = self.effective_route_posture["routing_override_reason"]
        return None if reason is None else str(reason)

    @property
    def complexity(self) -> str:
        return str(self.effective_route_posture["complexity"])

    @property
    def max_queries(self) -> int:
        return int(self.effective_route_posture["max_queries"])

    @property
    def results_per_query(self) -> int:
        return int(self.effective_route_posture["results_per_query"])

    @property
    def search_depth(self) -> str:
        return str(self.effective_route_posture["search_depth"])

    @property
    def top_chunks(self) -> int:
        return int(self.effective_route_posture["top_chunks"])

    @property
    def max_iterations(self) -> int:
        return int(self.effective_route_posture["max_iterations"])


def _clean_query_projection(queries: Sequence[str]) -> list[str]:
    return [" ".join(str(query or "").split())[:300] for query in queries if str(query or "").strip()]


def _status_step(status: Any, message: str) -> None:
    if status is not None and hasattr(status, "step"):
        status.step(message)


def _warning(logger: Any, message: str, error: Exception) -> None:
    if logger is not None and hasattr(logger, "warning"):
        logger.warning(message, error)


def _complexity_for_strategy(strategy: str) -> str:
    if strategy == "Fast":
        return "low"
    if strategy == "Balanced":
        return "medium"
    return "high"


def _budget_for_complexity(complexity: str) -> dict[str, int | str]:
    if complexity == "high":
        return {
            "max_queries": 3,
            "results_per_query": 8,
            "search_depth": "advanced",
            "top_chunks": 40,
            "max_iterations": 3,
        }
    if complexity == "medium":
        return {
            "max_queries": 2,
            "results_per_query": 6,
            "search_depth": "basic",
            "top_chunks": 20,
            "max_iterations": 2,
        }
    return {
        "max_queries": 2,
        "results_per_query": 5,
        "search_depth": "basic",
        "top_chunks": 8,
        "max_iterations": 1,
    }


def _build_recon_rewriter_prompt(
    *,
    current_date: str,
    query: str,
    recon_context: Mapping[str, Any],
) -> str:
    return (
        f"Today is {current_date}.\n"
        f"Original query: {query}\n"
        f"Recon titles: {recon_context.get('recon_titles', '')}\n"
        f"Recon snippets: {recon_context.get('recon_snippets', '')}\n"
    )


def _build_researcher_prompt(
    *,
    current_date: str,
    query: str,
    core_topic: str,
    intent: str,
    query_type: str,
    entities_list: Sequence[str],
    primary_entity: str,
    anchor_packet_telemetry: Mapping[str, Any],
    strategy: str,
) -> str:
    anchor_context_for_researcher = (
        format_anchor_context_for_researcher(dict(anchor_packet_telemetry))
        if strategy == "Balanced"
        else ""
    )
    anchor_context_section = (
        f"{anchor_context_for_researcher}\n" if anchor_context_for_researcher else ""
    )
    return (
        f"Today is {current_date}.\n"
        f"Original Prompt: {query}\n"
        f"Core Topic: {core_topic}\n"
        f"Intent: {intent}\n"
        f"query_type: {query_type}\n"
        f"entities: {list(entities_list)}\n"
        f"primary_entity: {primary_entity}\n"
        f"{anchor_context_section}"
        "If query_type is person, each search query must include a disambiguating term "
        "(role, employer, 'NYU', podcast, etc.) so results are not confused with other people. "
        "Return JSON with a queries array."
    )


def _effective_route_posture(
    *,
    intent: str,
    report_type: str,
    image_mode: str,
    core_topic: str,
    primary_entity: str,
    entities_list: Sequence[str],
    is_academic: bool,
    query_type: str,
    routing_override_applied: bool,
    routing_override_reason: str | None,
    focus_academic: bool,
    force_intent_news: bool,
    complexity: str,
    max_queries: int,
    results_per_query: int,
    search_depth: str,
    top_chunks: int,
    max_iterations: int,
    run_contract_ref: Mapping[str, Any] | None = None,
    contract_source_requirement_hints: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "report_type": report_type,
        "query_type": query_type,
        "image_mode": image_mode,
        "core_topic": core_topic,
        "primary_entity": primary_entity,
        "entities_list": list(entities_list),
        "is_academic": bool(is_academic),
        "routing_override_applied": bool(routing_override_applied),
        "routing_override_reason": routing_override_reason,
        "focus_academic": bool(focus_academic),
        "force_intent_news": bool(force_intent_news),
        "complexity": complexity,
        "max_queries": int(max_queries),
        "results_per_query": int(results_per_query),
        "search_depth": search_depth,
        "top_chunks": int(top_chunks),
        "max_iterations": int(max_iterations),
        "run_contract_ref": dict(run_contract_ref or {}),
        "contract_source_requirement_hints": [
            dict(item)
            for item in (contract_source_requirement_hints or ())
            if isinstance(item, Mapping)
        ],
        "contract_consumed_by_query_production": bool(run_contract_ref),
    }


def _build_query_production_payload(
    *,
    action: AuthorizedAction,
    effective_route_posture: Mapping[str, Any],
    candidate_source: str,
    candidate_queries: Sequence[str],
    recon_fired: bool,
    recon_status: str,
    recon_confidence: str | None,
    canonical_subject_resolved: str | None,
    entity_update_projection: Mapping[str, Any],
    researcher_fallback_status: str,
    anchor_packet_telemetry: Mapping[str, Any],
    nutrition_lookup_telemetry: Mapping[str, Any],
    include_domains: Sequence[str],
    provider_diagnostics: Sequence[Mapping[str, Any]],
    contract_source_requirement_hints: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "action_id": action.action_id,
        "run_id": action.run_id,
        "stage": action.stage,
        "observation_type": ObservationType.QUERY_CANDIDATES_PRODUCED.value,
        "status": RunStageStatus.COMPLETED.value,
        "effective_route_posture": dict(effective_route_posture),
        "candidate_source": candidate_source,
        "candidate_query_count": len(list(candidate_queries)),
        "candidate_query_projection": _clean_query_projection(candidate_queries),
        "recon": {
            "fired": bool(recon_fired),
            "status": recon_status,
            "confidence": recon_confidence,
        },
        "canonical_subject_projection": canonical_subject_resolved,
        "entity_update_projection": dict(entity_update_projection),
        "researcher_fallback_status": researcher_fallback_status,
        "contract_source_requirement_hints": [
            dict(item)
            for item in contract_source_requirement_hints
            if isinstance(item, Mapping)
        ],
        "diagnostics": {
            "anchor_packet_present": bool(anchor_packet_telemetry.get("anchor_packet_present")),
            "nutrition_lookup_detected": bool(
                nutrition_lookup_telemetry.get("nutrition_lookup_detected")
            ),
            "news_domain_augmentation_applied": (
                str(effective_route_posture.get("intent") or "") == "news"
            ),
            "include_domain_count": len(list(include_domains)),
            "provider_diagnostic_count": len(list(provider_diagnostics)),
        },
        "provenance": {
            "query_production_owner": "RunKernel",
            "executor": "core.query_production_runtime.execute_query_production_action",
            "query_order_owner": "QueryPlan",
            "raw_prompts_retained": False,
            "raw_model_responses_retained": False,
            "raw_provider_payloads_retained": False,
        },
    }


def query_plan_admission_inputs_from_query_production_projection(
    projection: Mapping[str, Any],
) -> QueryProductionAdmissionInputs:
    """Return the reduced query-production facts that QueryPlan admission consumes."""

    candidate_queries = list(projection.get("candidate_query_projection") or [])
    candidate_source = str(projection.get("candidate_source") or "").strip()
    effective_route_posture = dict(projection.get("effective_route_posture") or {})
    if not candidate_source:
        raise ValueError("query production projection missing candidate_source")
    if candidate_source not in {"recon", "researcher", "fallback"}:
        raise ValueError(f"unsupported query production candidate source: {candidate_source}")
    if not candidate_queries:
        raise ValueError("query production projection missing candidate queries")
    if not effective_route_posture:
        raise ValueError("query production projection missing effective route posture")
    return QueryProductionAdmissionInputs(
        candidate_queries=[str(query) for query in candidate_queries],
        candidate_source=candidate_source,
        effective_route_posture=effective_route_posture,
        contract_source_requirement_hints=[
            dict(item)
            for item in projection.get("contract_source_requirement_hints", [])
            if isinstance(item, Mapping)
        ],
    )


def execute_query_production_action(
    action: AuthorizedAction,
    *,
    router_query_preparation_contract: RouterQueryPreparationState,
    query: str,
    strategy: str,
    current_date: str,
    focus_academic: bool,
    force_intent_news: bool,
    include_domains: Sequence[str],
    news_preferred_domains: Sequence[str],
    ask_model: Callable[..., str],
    clean_json_response: Callable[[str], str],
    default_system: Mapping[str, str],
    fast_provider: str,
    fast_model: str,
    local_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    measure_context_stage: Callable[..., Any],
    clean_query: Callable[[str], str],
    cost_accumulator: Any,
    status: Any,
    provider_diagnostics: MutableSequence[dict[str, Any]],
    run_log: Any,
    waste_flags: Sequence[str] | None = None,
    brave_api_key_available: bool | None = None,
    brave_reconnaissance_func: Callable[..., list[dict[str, Any]]] = brave_reconnaissance,
    run_contract_projection: Mapping[str, Any] | None = None,
) -> QueryProductionResult:
    """Execute old initial candidate production after RunKernel authorization."""

    validate_authorized_action(
        action,
        action_type=ActionType.QUERY_PRODUCTION,
        stage=QUERY_PRODUCTION_STAGE,
        expected_observation_type=ObservationType.QUERY_CANDIDATES_PRODUCED,
    )

    intent = router_query_preparation_contract.intent
    report_type = router_query_preparation_contract.report_type
    image_mode = router_query_preparation_contract.image_mode
    core_topic = router_query_preparation_contract.core_topic
    is_academic = router_query_preparation_contract.is_academic
    query_type = router_query_preparation_contract.query_type
    primary_entity = router_query_preparation_contract.primary_entity
    entities_list = router_query_preparation_contract.entities_list
    router_entity_retry_used = router_query_preparation_contract.router_entity_retry_used
    router_original_report_type = router_query_preparation_contract.router_original_report_type
    router_original_query_type = router_query_preparation_contract.router_original_query_type
    routing_override_applied = False
    routing_override_reason: str | None = None
    active_waste_flags = list(waste_flags or [])
    contract_source_requirement_hints = contract_query_hints_from_projection(
        run_contract_projection
    )
    run_contract_ref = {}
    if isinstance(run_contract_projection, Mapping) and run_contract_projection:
        run_contract_ref = {
            "owner": run_contract_projection.get("owner"),
            "contract_id": run_contract_projection.get("contract_id"),
            "synthesis_mode": run_contract_projection.get("synthesis_mode"),
            "selected_template_ids": run_contract_projection.get(
                "selected_template_ids",
                [],
            ),
            "source_requirement_count": run_contract_projection.get(
                "source_requirement_count",
                0,
            ),
        }

    nutrition_lookup_telemetry = detect_nutrition_lookup_telemetry(query)
    if nutrition_lookup_telemetry["nutrition_lookup_detected"]:
        report_type = "quantitative_comparison"
        routing_override_applied = True
        routing_override_reason = "nutrition_macro_per_100g_lookup"

    if focus_academic:
        is_academic = True
    if force_intent_news:
        intent = "news"

    anchor_packet_telemetry: dict[str, Any] = {}
    if strategy == "Balanced":
        anchor_packet_telemetry = build_shadow_anchor_packet(
            mode=strategy,
            query=query,
            current_date=current_date,
            intent=intent,
            report_type=report_type,
            router_original_report_type=router_original_report_type,
            query_type=query_type,
            router_original_query_type=router_original_query_type,
            core_topic=core_topic,
            primary_entity=primary_entity,
            entities=entities_list,
            router_entity_retry_used=router_entity_retry_used,
        )

    active_include_domains = list(include_domains)
    if intent == "news":
        active_include_domains = list(set(active_include_domains + list(news_preferred_domains)))

    complexity = _complexity_for_strategy(strategy)
    budget = _budget_for_complexity(complexity)
    max_queries = int(budget["max_queries"])
    results_per_query = int(budget["results_per_query"])
    search_depth = str(budget["search_depth"])
    top_chunks = int(budget["top_chunks"])
    max_iterations = int(budget["max_iterations"])

    recon_fired = False
    recon_confidence: str | None = None
    canonical_subject_resolved: str | None = None
    recon_status = "not_eligible"
    pre_retrieval_query_candidates: list[str] = []
    recon_t0 = time.monotonic()
    recon_query_type = (query_type or "").lower()
    if recon_query_type in _RECON_QUERY_TYPES:
        recon_status = "eligible"
        well_scoped = bool(re.search(r"\b(19|20)\d{2}\b", query or "")) and len(
            (primary_entity or core_topic or "").split()
        ) >= 4
        if well_scoped:
            recon_confidence = "low"
            recon_status = "skipped_well_scoped"
            active_waste_flags.append("recon_skipped")
        else:
            has_brave_key = (
                bool(os.getenv("BRAVE_API_KEY"))
                if brave_api_key_available is None
                else bool(brave_api_key_available)
            )
            if not has_brave_key:
                recon_status = "skipped_missing_brave_api_key"
                active_waste_flags.append("recon_skipped")
            else:
                brave_call_completed = False
                try:
                    _status_step(status, "Reconnaissance search (resolving entities and terms)\u2026")
                    brave_query = (query or core_topic)[:500]
                    brave_results = brave_reconnaissance_func(
                        brave_query,
                        num_results=5,
                        cost_accumulator=cost_accumulator,
                        cost_phase="recon",
                    )
                    brave_call_completed = True
                    recon_url_count = len(
                        {
                            str(item.get("url") or "")
                            for item in brave_results
                            if item.get("url")
                        }
                    )
                    provider_diagnostics.append(
                        build_provider_attempt_diagnostic(
                            provider="brave",
                            provider_role="recon",
                            cost_phase="recon",
                            query=brave_query,
                            max_results=5,
                            output_type="searchResults",
                            success=True,
                            result_count=len(brave_results),
                            new_url_count=recon_url_count,
                            accepted_url_count=recon_url_count,
                        )
                    )
                    recon_context = extract_recon_context(brave_results)
                    if (
                        (recon_context.get("recon_titles") or "").strip()
                        or (recon_context.get("recon_snippets") or "").strip()
                    ):
                        recon_rewriter_prompt = _build_recon_rewriter_prompt(
                            current_date=current_date,
                            query=query,
                            recon_context=recon_context,
                        )
                        measure_context_stage(
                            "recon_rewriter",
                            prompt=recon_rewriter_prompt,
                            system_prompt=default_system["recon_query_rewriter"],
                        )
                        rewriter_text = clean_json_response(
                            ask_model(
                                recon_rewriter_prompt,
                                default_system["recon_query_rewriter"],
                                provider=fast_provider,
                                model=fast_model,
                                effort="low",
                                base_url=local_url,
                                api_key=api_key,
                                require_json=True,
                                use_reasoning=use_reasoning,
                            )
                        )
                        rewriter_data = json.loads(rewriter_text)
                        rewritten_queries = [
                            clean_query(str(item))
                            for item in (rewriter_data.get("rewritten_queries") or [])
                            if clean_query(str(item))
                        ]
                        if rewritten_queries:
                            pre_retrieval_query_candidates = rewritten_queries
                            recon_fired = True
                            recon_status = "fired"
                            recon_confidence = (
                                (rewriter_data.get("recon_confidence") or "").strip()
                                or None
                            )
                            canonical_subject = (
                                rewriter_data.get("canonical_subject") or ""
                            ).strip()
                            if canonical_subject:
                                canonical_subject_resolved = canonical_subject[:200]
                            if (
                                canonical_subject
                                and canonical_subject.lower()
                                == (core_topic or "").strip().lower()
                            ):
                                recon_confidence = "low"
                            if (
                                (recon_confidence or "") in ("high", "medium")
                                and canonical_subject
                            ):
                                primary_entity = canonical_subject[:200]
                        else:
                            recon_status = "no_rewritten_queries"
                    else:
                        recon_status = "no_context"
                except Exception as exc:
                    if not brave_call_completed:
                        provider_diagnostics.append(
                            build_provider_attempt_diagnostic(
                                provider="brave",
                                provider_role="recon",
                                cost_phase="recon",
                                query=(query or core_topic)[:500],
                                max_results=5,
                                output_type="searchResults",
                                success=False,
                                failure_type=type(exc).__name__,
                            )
                        )
                    _warning(run_log, "Reconnaissance skipped: %s", exc)
                    active_waste_flags.append("recon_skipped")
                    recon_status = "failed"
    recon_seconds = max(0.0, time.monotonic() - recon_t0)

    entity_count_before = len(entities_list)
    canonical_entity = (canonical_subject_resolved or "").strip()[:200]
    canonical_inserted = False
    if canonical_entity:
        lows = {entity.casefold() for entity in entities_list}
        if canonical_entity.casefold() not in lows:
            entities_list = [canonical_entity] + entities_list
            canonical_inserted = True
    if entities_list:
        primary_entity = entities_list[0][:200]
    elif primary_entity.strip():
        entities_list = [primary_entity.strip()[:200]]
        primary_entity = entities_list[0][:200]
    empty_entity_flag = len(entities_list) == 0

    if not pre_retrieval_query_candidates:
        _status_step(status, "Generating initial search plan...")
        researcher_prompt = _build_researcher_prompt(
            current_date=current_date,
            query=query,
            core_topic=core_topic,
            intent=intent,
            query_type=query_type,
            entities_list=entities_list,
            primary_entity=primary_entity,
            anchor_packet_telemetry=anchor_packet_telemetry,
            strategy=strategy,
        )
        measure_context_stage(
            "researcher",
            prompt=researcher_prompt,
            system_prompt=default_system["researcher"],
        )
        researcher_text = clean_json_response(
            ask_model(
                researcher_prompt,
                default_system["researcher"],
                provider=fast_provider,
                model=fast_model,
                effort="low",
                base_url=local_url,
                api_key=api_key,
                require_json=True,
                use_reasoning=use_reasoning,
            )
        )
        try:
            queries_dict = json.loads(researcher_text)
            queries_raw = (
                queries_dict.get("queries", [])
                if isinstance(queries_dict, dict)
                else queries_dict
            )
            researcher_query_candidates = [
                clean_query(str(item)) for item in queries_raw if clean_query(str(item))
            ]
            if not researcher_query_candidates:
                researcher_query_candidates = [core_topic[:300]]
                candidate_source = "fallback"
                researcher_fallback_status = "empty_researcher_output"
            else:
                candidate_source = "researcher"
                researcher_fallback_status = "not_used"
        except Exception:
            researcher_query_candidates = [core_topic[:300]]
            candidate_source = "fallback"
            researcher_fallback_status = "invalid_researcher_output"
        candidate_queries = researcher_query_candidates
    else:
        _status_step(
            status,
            "Using recon-informed search queries (research planner skipped for pass 1).",
        )
        candidate_queries = pre_retrieval_query_candidates
        candidate_source = "recon"
        researcher_fallback_status = "not_needed_recon"

    route_posture = _effective_route_posture(
        intent=intent,
        report_type=report_type,
        image_mode=image_mode,
        core_topic=core_topic,
        primary_entity=primary_entity,
        entities_list=entities_list,
        is_academic=is_academic,
        query_type=query_type,
        routing_override_applied=routing_override_applied,
        routing_override_reason=routing_override_reason,
        focus_academic=focus_academic,
        force_intent_news=force_intent_news,
        complexity=complexity,
        max_queries=max_queries,
        results_per_query=results_per_query,
        search_depth=search_depth,
        top_chunks=top_chunks,
        max_iterations=max_iterations,
        run_contract_ref=run_contract_ref,
        contract_source_requirement_hints=contract_source_requirement_hints,
    )
    entity_update_projection = {
        "entity_count_before": entity_count_before,
        "entity_count_after": len(entities_list),
        "canonical_subject_inserted": canonical_inserted,
        "primary_entity": primary_entity,
    }
    payload = _build_query_production_payload(
        action=action,
        effective_route_posture=route_posture,
        candidate_source=candidate_source,
        candidate_queries=candidate_queries,
        recon_fired=recon_fired,
        recon_status=recon_status,
        recon_confidence=recon_confidence,
        canonical_subject_resolved=canonical_subject_resolved,
        entity_update_projection=entity_update_projection,
        researcher_fallback_status=researcher_fallback_status,
        anchor_packet_telemetry=anchor_packet_telemetry,
        nutrition_lookup_telemetry=nutrition_lookup_telemetry,
        include_domains=active_include_domains,
        provider_diagnostics=provider_diagnostics,
        contract_source_requirement_hints=contract_source_requirement_hints,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.QUERY_CANDIDATES_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    return QueryProductionResult(
        candidate_queries=list(candidate_queries),
        candidate_source=candidate_source,
        effective_route_posture=route_posture,
        include_domains=active_include_domains,
        anchor_packet_telemetry=anchor_packet_telemetry,
        nutrition_lookup_telemetry=dict(nutrition_lookup_telemetry),
        waste_flags=active_waste_flags,
        recon_fired=recon_fired,
        recon_confidence=recon_confidence,
        canonical_subject_resolved=canonical_subject_resolved,
        recon_seconds=recon_seconds,
        researcher_fallback_status=researcher_fallback_status,
        empty_entity_flag=empty_entity_flag,
        contract_source_requirement_hints=list(contract_source_requirement_hints),
        observation=observation,
    )


@dataclass(frozen=True, slots=True)
class QueryPlanAdmissionResult:
    """QueryPlan admission output plus the kernel observation to reduce."""

    queries: list[str]
    current_queries: list[str]
    recency_merge_used: bool
    recency_merge_query: str | None
    router_query_preparation_contract: RouterQueryPreparationState
    observation: Observation


def _query_plan_projection(
    query_authority: QueryPlanRuntimeAdapter,
    *,
    query_source: str,
    recency_merge_used: bool,
    recency_merge_query: str | None,
    current_queries: Sequence[str],
    contract_source_requirement_hints: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    query_plan = query_authority.to_trace_fragment().get(QUERY_PLAN_TRACE_KEY, {})
    return {
        "query_plan_ref": query_plan,
        "query_source": query_source,
        "recency_merge_used": bool(recency_merge_used),
        "recency_merge_query": recency_merge_query,
        "current_query_count": len(list(current_queries)),
        "query_order_owner": "QueryPlan",
        "contract_source_requirement_hints": [
            dict(item)
            for item in (contract_source_requirement_hints or ())
            if isinstance(item, Mapping)
        ],
    }


def execute_query_plan_admission_action(
    action: AuthorizedAction,
    *,
    query_authority: QueryPlanRuntimeAdapter,
    router_query_preparation_contract: RouterQueryPreparationState,
    candidate_queries: Sequence[str],
    candidate_source: str,
    query_type: str,
    current_date: str,
    max_queries: int,
    route_runtime_posture: Mapping[str, Any],
    search_work_projection: Mapping[str, Any] | None = None,
) -> QueryPlanAdmissionResult:
    """Admit existing candidates into QueryPlan after RunKernel authorization."""

    validate_authorized_action(
        action,
        action_type=ActionType.QUERY_PLAN_ADMISSION,
        stage=QUERY_PLAN_ADMISSION_STAGE,
        expected_observation_type=ObservationType.QUERY_PLAN_ADMITTED,
    )
    if candidate_source == "recon":
        queries = query_authority.admit_recon_candidates(candidate_queries)
    elif candidate_source in {"researcher", "fallback"}:
        queries = query_authority.admit_researcher_candidates(candidate_queries)
    else:
        raise ValueError(f"unsupported query admission candidate source: {candidate_source}")

    queries = query_authority.consume_search_work_for_existing_queries(
        queries,
        search_work_projection=search_work_projection,
        max_len=max_queries,
        origin=f"{candidate_source}_search_work_consumption",
        role=QueryPlanRole.INITIAL,
    )
    recency_projection = query_authority.apply_initial_recency_merge(
        queries,
        query_type=query_type,
        current_date=current_date,
        max_queries=max_queries,
    )
    current_queries = query_authority.finalize(
        recency_projection.current_queries,
        max_len=max_queries,
        include_official_bias=False,
    )
    contract_source_requirement_hints = [
        dict(item)
        for item in route_runtime_posture.get("contract_source_requirement_hints", [])
        if isinstance(item, Mapping)
    ]
    run_contract_ref = (
        dict(route_runtime_posture.get("run_contract_ref") or {})
        if isinstance(route_runtime_posture.get("run_contract_ref"), Mapping)
        else {}
    )
    if run_contract_ref or contract_source_requirement_hints:
        query_authority.plan = query_authority.plan.append(
            origin="run_authority_contract",
            role="initial",
            status="admitted",
            phase="run_contract_source_requirements",
            admission_reason="source_requirement_hints_consumed",
            metadata={
                "contract_ref": run_contract_ref,
                "contract_source_requirement_hints": contract_source_requirement_hints,
                "contract_changed_query_order": False,
            },
        )

    intent = str(route_runtime_posture["intent"])
    route_entities = route_runtime_posture.get(
        "entities_list",
        route_runtime_posture.get("entities"),
    )
    route_query_type = str(route_runtime_posture.get("query_type", query_type))
    router_query_preparation_contract = with_router_query_runtime_posture(
        router_query_preparation_contract,
        intent=intent,
        report_type=str(route_runtime_posture["report_type"]),
        query_type=route_query_type,
        primary_entity=str(route_runtime_posture["primary_entity"]),
        entities=route_entities,
        is_academic=bool(route_runtime_posture["is_academic"]),
        routing_override_applied=bool(route_runtime_posture["routing_override_applied"]),
        routing_override_reason=route_runtime_posture["routing_override_reason"],
        focus_academic=bool(route_runtime_posture["focus_academic"]),
        force_intent_news=bool(route_runtime_posture["force_intent_news"]),
        complexity=str(route_runtime_posture["complexity"]),
        max_queries=max_queries,
        results_per_query=int(route_runtime_posture["results_per_query"]),
        search_depth=str(route_runtime_posture["search_depth"]),
        top_chunks=int(route_runtime_posture["top_chunks"]),
        max_iterations=int(route_runtime_posture["max_iterations"]),
        recency_merge_used=recency_projection.recency_merge_used,
        recency_query=recency_projection.recency_merge_query,
        official_bias_requested=wants_official_source_bias(
            query_authority.user_query,
            intent,
        ),
        official_bias_phrase=(
            official_bias_phrase(query_authority.user_query)
            if wants_official_source_bias(query_authority.user_query, intent)
            else None
        ),
        finalized_queries=queries,
        current_queries=current_queries,
        query_source=candidate_source,
        run_contract_ref=run_contract_ref,
        contract_source_requirement_hints=contract_source_requirement_hints,
    )
    payload = _query_plan_projection(
        query_authority,
        query_source=candidate_source,
        recency_merge_used=recency_projection.recency_merge_used,
        recency_merge_query=recency_projection.recency_merge_query,
        current_queries=current_queries,
        contract_source_requirement_hints=contract_source_requirement_hints,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.QUERY_PLAN_ADMITTED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    return QueryPlanAdmissionResult(
        queries=list(queries),
        current_queries=list(current_queries),
        recency_merge_used=recency_projection.recency_merge_used,
        recency_merge_query=recency_projection.recency_merge_query,
        router_query_preparation_contract=router_query_preparation_contract,
        observation=observation,
    )


__all__ = [
    "QueryProductionAdmissionInputs",
    "QueryProductionResult",
    "QueryPlanAdmissionResult",
    "execute_query_production_action",
    "execute_query_plan_admission_action",
    "query_plan_admission_inputs_from_query_production_projection",
]
