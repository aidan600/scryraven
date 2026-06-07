"""Legacy synthesis-evaluator and Scrutineer runtime stage extraction.

The helper executes an already-authorized stage with injected prompt/model/search
callables; it does not own provider routing, evidence ranking, citation
formatting, or final-answer posture.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableSequence, Sequence

from core.retrieval_dispatch_runtime import (
    execute_scrutineer_remediation_from_scope,
    execute_supplemental_search_from_scope,
)
from core.runtime_prompt_assembly import (
    build_analyst_prompt,
    build_scrutineer_prompt,
    build_scrutineer_remediation_prompt,
    build_synthesis_evaluator_prompt,
)
from core.scrutineer_remediation_runtime_handoff import RuntimeRemediationQueryFact


@dataclass(frozen=True)
class LegacyReviewRuntimeDeps:
    ask_model: Callable[..., str]
    clean_json_response: Callable[[Any], str]
    measure_context_stage: Callable[..., None]
    record_analyst_model_call: Callable[[str], None]
    build_final_evidence_bundle: Callable[..., Any]
    final_evidence_bundle_inputs: Callable[[], Any]
    build_analyst_cached_prefix: Callable[[], str]
    evidence_slice_for_analyst: Callable[[], Any]
    select_providers: Callable[..., Sequence[str]]
    choose_supplemental_search_depth: Callable[[str, str], str]
    execute_supplemental_search: Callable[..., Any] = execute_supplemental_search_from_scope
    execute_scrutineer_remediation: Callable[..., Any] = execute_scrutineer_remediation_from_scope
    monotonic: Callable[[], float] = time.monotonic
    environ_get: Callable[[str], str | None] = os.getenv


@dataclass(frozen=True)
class LegacyReviewRuntimeRequest:
    scope: Mapping[str, Any]; query: str; analysis: str; complexity: str; corpus_weak: bool
    entity_hint_for_retrieval: str | None; utilization_rate_val: float | None; synth_skip_utilization_threshold: float
    post_retrieval_fast_path_used: bool; economist_output_used_as_analysis: bool; status: Any; collector: Any
    default_system: Mapping[str, str]; query_authority: Any; search_depth: str; query_type: str | None; intent: str
    available_keys: Mapping[str, Any]; report_type: str | None; is_academic: bool; suppress_tavily: bool
    local_url: str | None; or_api_key: str | None; use_reasoning: bool; fast_provider: str; fast_model: str
    smart_provider: str; smart_model: str; analyst_effort: str; all_passages: MutableSequence[dict[str, Any]]
    linkup_block: str; current_date: str; core_topic: str; past_searches: Sequence[str]
    final_top_evidence: Sequence[Any]; unique_source_urls: Sequence[str]; run_log: logging.Logger; author_notes: str
    first_synth_sufficient: bool; synth_was_insufficient: bool; synth_deficiency: str | None; supplemental_ran: bool
    delta_urls_supplemental: int; synth_evaluator_seconds: float; analyst_seconds: float; scrutineer_ran: bool
    scrutineer_seconds: float; scrutineer_flags: list[dict[str, Any]] = field(default_factory=list)
    scrutineer_remediation_queries: list[RuntimeRemediationQueryFact] = field(default_factory=list)
    scrutineer_remediation_dispatch_authorized: bool = False; scrutineer_remediation_dispatch_posture: str = "skipped"
    scrutineer_remediation_provider_role: str | None = None; scrutineer_remediation_providers: list[str] = field(default_factory=list)
    scrutineer_remediation_linkup_depth_override: str | None = None; scrutineer_remediation_evidence: list[Any] = field(default_factory=list)
    scrutineer_remediation_resynthesis_triggered: bool = False; scrutineer_pass_flags_directly_to_author: bool = False


@dataclass(frozen=True)
class LegacyReviewRuntimeOutcome:
    analysis: str; author_notes: str; first_synth_sufficient: bool; synth_was_insufficient: bool
    synth_deficiency: str | None; supplemental_ran: bool; delta_urls_supplemental: int
    synth_evaluator_seconds: float; analyst_seconds: float; scrutineer_ran: bool; scrutineer_seconds: float
    scrutineer_flags: list[dict[str, Any]]; scrutineer_high_count: int
    scrutineer_remediation_queries: list[RuntimeRemediationQueryFact]
    scrutineer_remediation_dispatch_authorized: bool; scrutineer_remediation_dispatch_posture: str
    scrutineer_remediation_provider_role: str | None; scrutineer_remediation_providers: list[str]
    scrutineer_remediation_linkup_depth_override: str | None; scrutineer_remediation_evidence: list[Any]
    scrutineer_remediation_resynthesis_triggered: bool; scrutineer_pass_flags_directly_to_author: bool
    final_top_evidence: Any; unique_source_urls: Any; ordered_sources: Any; evidence_block: Any; cached_prefix: Any

    def orchestrator_values(self) -> tuple[Any, ...]:
        """Return legacy orchestrator assignment values in the old local order."""
        return (
            self.analysis, self.author_notes, self.first_synth_sufficient, self.synth_was_insufficient,
            self.synth_deficiency, self.supplemental_ran, self.delta_urls_supplemental, self.synth_evaluator_seconds,
            self.analyst_seconds, self.scrutineer_ran, self.scrutineer_seconds, self.scrutineer_flags,
            self.scrutineer_high_count, self.scrutineer_remediation_queries, self.scrutineer_remediation_dispatch_authorized,
            self.scrutineer_remediation_dispatch_posture, self.scrutineer_remediation_provider_role,
            self.scrutineer_remediation_providers, self.scrutineer_remediation_linkup_depth_override,
            self.scrutineer_remediation_evidence, self.scrutineer_remediation_resynthesis_triggered,
            self.scrutineer_pass_flags_directly_to_author, self.final_top_evidence, self.unique_source_urls,
        )


_DIRECT_SCOPE_FIELD_NAMES = (
    "query", "analysis", "complexity", "corpus_weak", "entity_hint_for_retrieval", "utilization_rate_val",
    "synth_skip_utilization_threshold", "post_retrieval_fast_path_used", "economist_output_used_as_analysis",
    "query_authority", "search_depth", "query_type", "intent", "available_keys", "report_type", "is_academic",
    "suppress_tavily", "local_url", "or_api_key", "use_reasoning", "fast_provider", "fast_model", "smart_provider",
    "smart_model", "analyst_effort", "all_passages", "linkup_block", "current_date", "core_topic", "past_searches",
    "final_top_evidence", "unique_source_urls", "run_log", "author_notes", "first_synth_sufficient",
    "synth_was_insufficient", "synth_deficiency", "supplemental_ran", "delta_urls_supplemental",
    "synth_evaluator_seconds", "analyst_seconds", "scrutineer_ran", "scrutineer_seconds", "scrutineer_flags",
    "scrutineer_remediation_queries", "scrutineer_remediation_dispatch_authorized", "scrutineer_remediation_dispatch_posture",
    "scrutineer_remediation_provider_role", "scrutineer_remediation_providers", "scrutineer_remediation_linkup_depth_override",
    "scrutineer_remediation_evidence", "scrutineer_remediation_resynthesis_triggered", "scrutineer_pass_flags_directly_to_author",
)
_DEFAULTED_SCOPE_FIELDS = {
    "synth_was_insufficient": False, "synth_deficiency": None, "supplemental_ran": False,
    "delta_urls_supplemental": 0, "scrutineer_flags": [], "scrutineer_remediation_queries": [],
    "scrutineer_remediation_dispatch_authorized": False, "scrutineer_remediation_dispatch_posture": "skipped",
    "scrutineer_remediation_provider_role": None, "scrutineer_remediation_providers": [],
    "scrutineer_remediation_linkup_depth_override": None, "scrutineer_remediation_evidence": [],
    "scrutineer_remediation_resynthesis_triggered": False, "scrutineer_pass_flags_directly_to_author": False,
}
_RETRIEVAL_DISPATCH_SCOPE_FIELD_NAMES = (
    "process_search_queries", "query_embedding", "seen_urls", "collected_images", "embed_provider", "embed_model",
    "embed_texts", "deps", "provider_diagnostics", "results_per_query", "include_domains", "exclude_domains",
)
_SCOPE_KEYS = frozenset(_DIRECT_SCOPE_FIELD_NAMES + _RETRIEVAL_DISPATCH_SCOPE_FIELD_NAMES + (
    "status", "synthesis_evaluator_supplemental_search_collector", "ordered_sources", "evidence_block", "cached_prefix",
))
_OUTCOME_LOCAL_NAMES = (
    "analysis", "author_notes", "first_synth_sufficient", "synth_was_insufficient", "synth_deficiency",
    "supplemental_ran", "delta_urls_supplemental", "synth_evaluator_seconds", "analyst_seconds",
    "scrutineer_ran", "scrutineer_seconds", "scrutineer_flags", "scrutineer_high_count",
    "scrutineer_remediation_queries", "scrutineer_remediation_dispatch_authorized",
    "scrutineer_remediation_dispatch_posture", "scrutineer_remediation_provider_role",
    "scrutineer_remediation_providers", "scrutineer_remediation_linkup_depth_override",
    "scrutineer_remediation_evidence", "scrutineer_remediation_resynthesis_triggered",
    "scrutineer_pass_flags_directly_to_author", "final_top_evidence", "unique_source_urls",
    "ordered_sources", "evidence_block", "cached_prefix",
)


def execute_legacy_review_runtime_stage_from_scope(
    scope: Mapping[str, Any],
    *,
    deps: LegacyReviewRuntimeDeps,
    default_system: Mapping[str, str],
) -> LegacyReviewRuntimeOutcome:
    stage_scope = {key: scope[key] for key in _SCOPE_KEYS if key in scope}
    request_kwargs = {
        name: (stage_scope[name] if name in stage_scope else _DEFAULTED_SCOPE_FIELDS[name])
        for name in _DIRECT_SCOPE_FIELD_NAMES if name in stage_scope or name in _DEFAULTED_SCOPE_FIELDS
    }
    request = LegacyReviewRuntimeRequest(
        **request_kwargs, scope=stage_scope, status=stage_scope["status"],
        collector=stage_scope["synthesis_evaluator_supplemental_search_collector"], default_system=default_system,
    )
    return execute_legacy_review_runtime_stage(request, deps)


def _bundle_outputs(bundle: Any) -> tuple[Any, Any, Any, Any, Any]:
    return bundle.final_top_evidence, bundle.unique_source_urls, bundle.ordered_sources, bundle.evidence_block, bundle.cached_prefix


def _rebuild_evidence(request: LegacyReviewRuntimeRequest, deps: LegacyReviewRuntimeDeps) -> tuple[Any, Any, Any, Any, Any]:
    final_evidence_bundle = deps.build_final_evidence_bundle(
        deps.final_evidence_bundle_inputs(),
        linkup_block=(request.linkup_block if request.complexity == "high" and deps.environ_get("LINKUP_API_KEY") and request.linkup_block else ""),
    )
    return _bundle_outputs(final_evidence_bundle)


def execute_legacy_review_runtime_stage(
    request: LegacyReviewRuntimeRequest,
    deps: LegacyReviewRuntimeDeps,
) -> LegacyReviewRuntimeOutcome:
    analysis = request.analysis
    author_notes = request.author_notes
    first_synth_sufficient = request.first_synth_sufficient
    synth_was_insufficient = request.synth_was_insufficient
    synth_deficiency = request.synth_deficiency
    supplemental_ran = request.supplemental_ran
    delta_urls_supplemental = request.delta_urls_supplemental
    synth_evaluator_seconds = request.synth_evaluator_seconds
    analyst_seconds = request.analyst_seconds
    scrutineer_ran = request.scrutineer_ran
    scrutineer_seconds = request.scrutineer_seconds
    scrutineer_flags = list(request.scrutineer_flags)
    scrutineer_high_count = 0
    scrutineer_remediation_queries = list(request.scrutineer_remediation_queries)
    scrutineer_remediation_dispatch_authorized = request.scrutineer_remediation_dispatch_authorized
    scrutineer_remediation_dispatch_posture = request.scrutineer_remediation_dispatch_posture
    scrutineer_remediation_provider_role = request.scrutineer_remediation_provider_role
    scrutineer_remediation_providers = list(request.scrutineer_remediation_providers)
    scrutineer_remediation_linkup_depth_override = request.scrutineer_remediation_linkup_depth_override
    scrutineer_remediation_evidence = list(request.scrutineer_remediation_evidence)
    scrutineer_remediation_resynthesis_triggered = request.scrutineer_remediation_resynthesis_triggered
    scrutineer_pass_flags_directly_to_author = request.scrutineer_pass_flags_directly_to_author
    final_top_evidence = request.final_top_evidence
    unique_source_urls = request.unique_source_urls
    ordered_sources = request.scope.get("ordered_sources")
    evidence_block = request.scope.get("evidence_block")
    cached_prefix = request.scope.get("cached_prefix")

    if (
        request.complexity in ("medium", "high")
        and analysis != "DIRECT_TO_AUTHOR"
        and not request.post_retrieval_fast_path_used
        and not request.economist_output_used_as_analysis
    ):
        request.collector.mark_eligible()
        strong_retrieval = (
            not request.corpus_weak
            and bool(request.entity_hint_for_retrieval)
            and (request.utilization_rate_val is not None)
            and request.utilization_rate_val >= request.synth_skip_utilization_threshold
        )
        if strong_retrieval:
            request.status.step(
                "Retrieval already matches the main subject well; "
                "skipping synthesis completeness re-check and supplemental search."
            )
            request.collector.mark_strong_retrieval_skipped()
            if request.complexity in ("medium", "high"):
                first_synth_sufficient = True
        else:
            request.status.step("Checking synthesis completeness...")
            synth_eval_prompt = build_synthesis_evaluator_prompt(query=request.query, analysis=analysis)
            deps.measure_context_stage("synth_evaluator", prompt=synth_eval_prompt, system_prompt=request.default_system["synth_evaluator"])
            _se_t0 = deps.monotonic()
            synth_eval_text = deps.clean_json_response(
                deps.ask_model(
                    synth_eval_prompt, request.default_system["synth_evaluator"],
                    provider=request.fast_provider, model=request.fast_model, effort="low",
                    base_url=request.local_url, api_key=request.or_api_key, require_json=True, use_reasoning=request.use_reasoning,
                )
            )
            synth_evaluator_seconds += max(0.0, deps.monotonic() - _se_t0)

            synth_is_sufficient = True
            synth_queries: list[str] = []
            deficiency = "Missing key specifics."
            try:
                synth_eval_data = json.loads(synth_eval_text)
                synth_is_sufficient = synth_eval_data.get("is_sufficient", True)
                synth_queries = [
                    str(q)[:300] for q in synth_eval_data.get("supplemental_queries", [])
                ][:2]
                deficiency = synth_eval_data.get("deficiency", "Missing key specifics.")
                if not synth_is_sufficient:
                    synth_was_insufficient = True
                    synth_deficiency = str(deficiency) if deficiency is not None else "Missing key specifics."
            except Exception as e:  # pragma: no cover - covered by orchestrator parity path
                request.collector.mark_parse_failed(e)
                request.run_log.warning("Synth Evaluator JSON parse failed: %s", e)
            else:
                request.collector.mark_completeness(
                    sufficient=bool(synth_is_sufficient),
                    deficiency_text=synth_deficiency,
                )
            if request.complexity in ("medium", "high"):
                first_synth_sufficient = bool(synth_is_sufficient)

            if not synth_is_sufficient and synth_queries:
                synth_queries = request.query_authority.finalize_supplemental(synth_queries, max_len=2)
                request.collector.record_supplemental_queries(synth_queries)
                author_notes = (
                    f"\n\n⚠️ NOTE FOR AUTHOR: Synthesis quality check flagged: '{deficiency}'. "
                    "Hedge appropriately where data is missing."
                )
                request.collector.record_author_hedge_note()
                request.status.step(f"Completeness gap detected: {deficiency}. Running supplemental searches...")
                supp_search_depth = deps.choose_supplemental_search_depth(request.complexity, request.search_depth)
                supp_providers = deps.select_providers(
                    request.query_type, request.intent, request.complexity, request.available_keys,
                    report_type=request.report_type, is_academic=request.is_academic,
                    suppress_tavily=request.suppress_tavily, override=None,
                )
                request.collector.record_dispatch(providers=supp_providers, search_depth=supp_search_depth)
                supplemental_ran = True
                supplemental_outcome = deps.execute_supplemental_search(
                    request.scope, queries=synth_queries, search_depth=supp_search_depth, providers=supp_providers
                )
                supp_passages = supplemental_outcome.passages
                delta_urls_supplemental = supplemental_outcome.seen_url_delta
                request.collector.record_evidence(supp_passages)

                if supp_passages:
                    request.all_passages.extend(supp_passages)
                    final_top_evidence, unique_source_urls, ordered_sources, evidence_block, cached_prefix = _rebuild_evidence(request, deps)
                    request.collector.record_final_evidence_rebuild()
                    request.status.step("Re-analyzing with supplemental evidence...")
                    analyst_cached_prefix = deps.build_analyst_cached_prefix()
                    _an_t0 = deps.monotonic()
                    _analyst_prompt = build_analyst_prompt(analyst_cached_prefix=analyst_cached_prefix, intent=request.intent, analyst_effort=request.analyst_effort)
                    deps.measure_context_stage(
                        "analyst_supplemental",
                        prompt=_analyst_prompt,
                        system_prompt=request.default_system["analyst"],
                        stable_prefix=request.default_system["analyst"],
                        evidence_passages=deps.evidence_slice_for_analyst(),
                    )
                    deps.record_analyst_model_call(_analyst_prompt)
                    request.collector.record_analyst_rerun()
                    analysis = deps.ask_model(
                        _analyst_prompt,
                        request.default_system["analyst"],
                        provider=request.smart_provider, model=request.smart_model, effort=request.analyst_effort,
                        base_url=request.local_url, api_key=request.or_api_key, use_reasoning=request.use_reasoning,
                    )
                    analyst_seconds += max(0.0, deps.monotonic() - _an_t0)
                else:
                    request.status.step("Supplemental search yielded no new results. Passing gap directly to author.")

        if request.complexity == "high":
            scrutineer_ran = True
            request.status.step("Running adversarial review (Scrutineer)...")
            scrutineer_prompt = build_scrutineer_prompt(
                intent=request.intent,
                default_scrutineer_system=request.default_system["scrutineer"],
                final_top_evidence=final_top_evidence,
                unique_source_urls=unique_source_urls,
                analysis=analysis,
            )
            scrutineer_sys_prompt = scrutineer_prompt.system_prompt
            scrutineer_input = scrutineer_prompt.user_prompt
            deps.measure_context_stage("scrutineer", prompt=scrutineer_input, system_prompt=scrutineer_sys_prompt)
            _sc_t0 = deps.monotonic()
            scrutineer_text = deps.clean_json_response(
                deps.ask_model(
                    scrutineer_input, scrutineer_sys_prompt,
                    provider=request.smart_provider, model=request.smart_model, effort="medium",
                    base_url=request.local_url, api_key=request.or_api_key, require_json=True, use_reasoning=False,
                )
            )
            scrutineer_seconds += max(0.0, deps.monotonic() - _sc_t0)
            try:
                scrutineer_data = json.loads(scrutineer_text)
                scrutineer_flags = scrutineer_data.get("flags", [])
                scrutineer_high_count = len(
                    [f for f in scrutineer_flags if str(f.get("severity", "")).lower() == "high"]
                )
                scrutineer_verdict = scrutineer_data.get("verdict", "clean")
                request.run_log.info("Scrutineer verdict: %s | Flags: %d", scrutineer_verdict, len(scrutineer_flags))

                HIGH_FLAG_THRESHOLD = 5
                if scrutineer_flags and len(scrutineer_flags) >= HIGH_FLAG_THRESHOLD:
                    scrutineer_pass_flags_directly_to_author = True
                    request.run_log.warning(
                        "Scrutineer returned %d flags — evidence base too thin for remediation. "
                        "Passing flags as author context instead.",
                        len(scrutineer_flags),
                    )
                    request.status.step(
                        f"Scrutineer raised {len(scrutineer_flags)} issues. "
                        "Evidence base too thin for remediation; passing flags directly to author."
                    )
                else:
                    SEARCHABLE = {"SINGLE-SOURCE", "TEMPORAL DRIFT"}
                    search_flag_pairs = [
                        (i, f) for i, f in enumerate(scrutineer_flags)
                        if f.get("severity", "").lower() == "high" and f.get("category") in SEARCHABLE
                    ]
                    search_flags = [f for _, f in search_flag_pairs]
                    search_flag_ids = tuple(
                        str(f.get("flag_id") or f.get("id") or f"scrutineer-flag-{i + 1}")
                        for i, f in search_flag_pairs
                    )
                    if search_flags:
                        request.status.step(
                            f"Scrutineer raised {len(search_flags)} high-severity issue(s). "
                            "Generating remediation queries..."
                        )
                        remed_prompt = build_scrutineer_remediation_prompt(
                            current_date=request.current_date,
                            core_topic=request.core_topic,
                            past_searches=request.past_searches,
                            search_flags=search_flags,
                        )
                        deps.measure_context_stage(
                            "scrutineer_remediation_researcher", prompt=remed_prompt, system_prompt=request.default_system["researcher"]
                        )
                        _rem_t0 = deps.monotonic()
                        remed_raw = deps.clean_json_response(
                            deps.ask_model(
                                remed_prompt, request.default_system["researcher"],
                                provider=request.fast_provider, model=request.fast_model, effort="low",
                                base_url=request.local_url, api_key=request.or_api_key,
                                require_json=True, use_reasoning=request.use_reasoning,
                            )
                        )
                        scrutineer_seconds += max(0.0, deps.monotonic() - _rem_t0)
                        remed_queries: list[str] = []
                        try:
                            remed_queries = [str(q)[:300] for q in json.loads(remed_raw).get("queries", [])][:2]
                        except Exception as e:
                            request.run_log.warning("Remediation query parse failed: %s", e)

                        if remed_queries:
                            novel_queries = []
                            raw_query_novelty: dict[str, bool] = {}
                            for rq in remed_queries:
                                is_novel = True
                                rq_tokens = set(rq.lower().split())
                                for pq in request.past_searches:
                                    pq_tokens = set(pq.lower().split())
                                    if not rq_tokens or not pq_tokens:
                                        continue
                                    overlap = len(rq_tokens & pq_tokens) / max(len(rq_tokens), 1)
                                    if overlap > 0.6:
                                        is_novel = False
                                        break
                                raw_query_novelty[rq] = is_novel
                                if is_novel:
                                    novel_queries.append(rq)

                            novel_queries = request.query_authority.finalize_remediation(novel_queries, max_len=2)

                            admitted_query_set = set(novel_queries)
                            for _rq_index, _rq in enumerate(remed_queries):
                                _is_novel = raw_query_novelty.get(_rq, False)
                                scrutineer_remediation_queries.append(
                                    RuntimeRemediationQueryFact(
                                        query_id=f"scrutineer-remediation-query-{len(scrutineer_remediation_queries) + 1}",
                                        query_text=_rq,
                                        source_flag_ids=search_flag_ids,
                                        filter_posture=(
                                            "admitted"
                                            if _rq in admitted_query_set
                                            else ("rejected_not_novel" if _is_novel else "rejected_duplicate")
                                        ),
                                        rejection_reason=(
                                            None
                                            if _rq in admitted_query_set
                                            else ("final_query_filter" if _is_novel else "overlap_gt_0_6")
                                        ),
                                    )
                                )

                            if not novel_queries:
                                request.run_log.info("Scrutineer remediation: all generated queries too similar to prior searches. Skipping.")
                                request.status.step("Remediation searches skipped (duplicate queries).")
                            else:
                                request.status.step(f"Remediation searches: {novel_queries}")
                                scrutineer_remediation_dispatch_authorized = True
                                scrutineer_remediation_dispatch_posture = "authorized"
                                scrutineer_remediation_provider_role = "scrutineer_remediation"
                                scrutineer_remediation_linkup_depth_override = "deep"
                                remed_providers = deps.select_providers(
                                    request.query_type, request.intent, request.complexity, request.available_keys,
                                    report_type=request.report_type, is_academic=request.is_academic,
                                    suppress_tavily=request.suppress_tavily, override=None,
                                )
                                scrutineer_remediation_providers = list(remed_providers)
                                remediation_outcome = deps.execute_scrutineer_remediation(
                                    request.scope, queries=novel_queries, providers=remed_providers
                                )
                                remed_passages = remediation_outcome.passages
                                if remed_passages:
                                    scrutineer_remediation_dispatch_posture = "completed"
                                    scrutineer_remediation_evidence = list(remed_passages)
                                    request.all_passages.extend(remed_passages)
                                    final_top_evidence, unique_source_urls, ordered_sources, evidence_block, cached_prefix = _rebuild_evidence(request, deps)
                                    request.status.step("Re-synthesizing with remediation evidence...")
                                    scrutineer_remediation_resynthesis_triggered = True
                                    analyst_cached_prefix = deps.build_analyst_cached_prefix()
                                    _an_t0 = deps.monotonic()
                                    _remed_analyst_prompt = build_analyst_prompt(analyst_cached_prefix=analyst_cached_prefix, intent=request.intent, analyst_effort=request.analyst_effort)
                                    deps.measure_context_stage(
                                        "analyst_scrutineer_remediation",
                                        prompt=_remed_analyst_prompt,
                                        system_prompt=request.default_system["analyst"],
                                        stable_prefix=request.default_system["analyst"],
                                        evidence_passages=deps.evidence_slice_for_analyst(),
                                    )
                                    analysis = deps.ask_model(
                                        _remed_analyst_prompt,
                                        request.default_system["analyst"],
                                        provider=request.smart_provider, model=request.smart_model, effort=request.analyst_effort,
                                        base_url=request.local_url, api_key=request.or_api_key, use_reasoning=request.use_reasoning,
                                    )
                                    analyst_seconds += max(0.0, deps.monotonic() - _an_t0)
                                else:
                                    request.status.step("Remediation search yielded no new results.")
            except Exception as e:
                request.run_log.warning("Scrutineer JSON parse failed: %s", e)
                scrutineer_flags = []

    return LegacyReviewRuntimeOutcome(
        analysis=analysis, author_notes=author_notes, first_synth_sufficient=first_synth_sufficient, synth_was_insufficient=synth_was_insufficient,
        synth_deficiency=synth_deficiency, supplemental_ran=supplemental_ran, delta_urls_supplemental=delta_urls_supplemental, synth_evaluator_seconds=synth_evaluator_seconds, analyst_seconds=analyst_seconds,
        scrutineer_ran=scrutineer_ran, scrutineer_seconds=scrutineer_seconds, scrutineer_flags=scrutineer_flags, scrutineer_high_count=scrutineer_high_count,
        scrutineer_remediation_queries=scrutineer_remediation_queries, scrutineer_remediation_dispatch_authorized=scrutineer_remediation_dispatch_authorized, scrutineer_remediation_dispatch_posture=scrutineer_remediation_dispatch_posture,
        scrutineer_remediation_provider_role=scrutineer_remediation_provider_role, scrutineer_remediation_providers=scrutineer_remediation_providers, scrutineer_remediation_linkup_depth_override=scrutineer_remediation_linkup_depth_override,
        scrutineer_remediation_evidence=scrutineer_remediation_evidence, scrutineer_remediation_resynthesis_triggered=scrutineer_remediation_resynthesis_triggered, scrutineer_pass_flags_directly_to_author=scrutineer_pass_flags_directly_to_author,
        final_top_evidence=final_top_evidence, unique_source_urls=unique_source_urls, ordered_sources=ordered_sources, evidence_block=evidence_block, cached_prefix=cached_prefix,
    )
