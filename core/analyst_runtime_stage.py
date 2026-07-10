"""Bounded Analyst runtime stage extraction.

Executes the pre-Analyst gate, post-Economist handoff, unsupported-retrieval
fallback, and first Analyst model-call seam with injected runtime callables. It
does not select providers, retrieve/search, mutate queries, rank final evidence,
format citations, or assemble Author prose.
"""

from __future__ import annotations

import re
import time
from collections import namedtuple
from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping

from core.corpus_state import CorpusState
from core.economist_handoff_contract import build_economist_handoff_state, execute_economist_handoff
from core.failure_card import failure_card_reason, failure_card_should_show
from core.runtime_prompt_assembly import build_analyst_prompt, build_unsupported_retrieval_prompt_fragments
from core.source_classifier import source_domain_telemetry, source_tier_telemetry
from core.weak_failure_gate_contract import build_analyst_gate_descriptor

GENERIC_NEWS_DOMAINS = frozenset({
    "abcnews.go.com", "apnews.com", "axios.com", "bbc.com", "bbc.co.uk",
    "cbsnews.com", "cnn.com", "forbes.com", "foxnews.com", "msnbc.com",
    "nbcnews.com", "newsweek.com", "nytimes.com", "reuters.com",
    "theguardian.com", "usatoday.com", "washingtonpost.com", "yahoo.com",
})
_SCOPE_FIELD_NAMES = """run_id query report_type query_type complexity corpus_state corpus_weak retrieval_retry_used empty_entity_flag utilization_rate_val utilization_threshold all_passages total_chunks_embedded primary_entity core_topic need_economist economist_ran economist_preflight_allowed economist_preflight_block_reason economist_preflight_missing_entities economist_safety_telemetry economist_pre_analyst_skip_candidate_telemetry analyst_quant_packet_handoff_telemetry author_quant_source_telemetry estimate_from_priors_requested estimate_from_priors_blocked_by_pre_analyst_gate status author_notes analyst_cached_prefix intent analyst_effort smart_provider smart_model local_url or_api_key use_reasoning analyst_seconds""".split()
_SCOPE_KEYS = frozenset(_SCOPE_FIELD_NAMES) | {"DEFAULT_SYSTEM", "status"}


def query_expects_official_evidence(query: str, report_type: str, query_type: str) -> bool:
    text = f"{query} {report_type} {query_type}".casefold()
    primary = bool(re.search(r"\bprimary[-\s]+(?:sources?|documents?|evidence|records?|materials?)\b", text))
    official = bool(
        re.search(r"\b(?:company|corporate|issuer|reported\s+company)[-\s]+(?:filings?|materials?|reports?|records?)\b", text)
        or re.search(r"\beligibility[-\s]+requirements?\b", text)
    )
    if primary or official:
        return True
    return bool(re.search(
        r"\b(official|patch\s*notes?|release\s*notes?|changelog|pricing|prices?|"
        r"policy|policies|terms|rate\s*card|fees?|tariffs?|developer|dev\s*notes?|"
        r"filings?|regulatory|sec|announcement|roadmap)\b",
        text,
    ))


def query_expects_community_evidence(query: str, report_type: str, query_type: str) -> bool:
    text = f"{query} {report_type} {query_type}".casefold()
    return bool(re.search(
        r"\b(community|forum|forums|reddit|users?|players?|reviews?|discussion|"
        r"github|gitlab|stackoverflow|stack\s*overflow|issues?|pull\s*requests?|discord)\b",
        text,
    ))


def query_requires_clinical_trial_comparative_caution(query: str) -> bool:
    text = str(query or "").casefold()
    clinical = bool(re.search(r"\b(clinical|patients?|treatments?|therap(?:y|ies))\b", text))
    randomized = bool(re.search(r"\b(rct|randomi[sz]ed|randomi[sz]ed controlled trial)\b", text))
    comparative = bool(re.search(r"\b(vs\.?|versus|compare[sd]?|comparative|effect|efficacy)\b", text))
    return clinical and randomized and comparative


def pre_analyst_retrieval_gate(
    *, query: str, report_type: str, query_type: str, corpus_state: str,
    corpus_weak: bool, failure_card_show: bool, utilization_rate_val: float | None,
    utilization_threshold: float, source_tier_counts: dict[str, int],
    source_domain_counts: dict[str, int], top_source_domains: list[dict[str, Any]],
    on_domain_source_count: int, official_evidence_found: bool,
    community_signal_found: bool,
) -> dict[str, Any]:
    """Decide whether post-retrieval evidence is too weak for Analyst spend."""
    signals: list[str] = []
    total_sources = max(0, sum(int(v or 0) for v in source_domain_counts.values()))
    total_tiered = max(0, sum(int(v or 0) for v in source_tier_counts.values()))
    unknown_count = int(source_tier_counts.get("unknown", 0) or 0)
    unknown_ratio = (unknown_count / max(1, total_tiered)) if total_tiered else 0.0
    generic_count = sum(int(c or 0) for d, c in source_domain_counts.items() if str(d).lower() in GENERIC_NEWS_DOMAINS)
    generic_ratio = (generic_count / max(1, total_sources)) if total_sources else 0.0
    top_domain = str(top_source_domains[0].get("domain") or "").lower() if top_source_domains else ""
    top_count = int(top_source_domains[0].get("count") or 0) if top_source_domains else 0
    top_generic_dominates = top_domain in GENERIC_NEWS_DOMAINS and total_sources > 0 and (top_count / max(1, total_sources)) >= 0.5
    generic_news_dominated = generic_ratio >= 0.6 or top_generic_dominates
    mostly_unknown = total_tiered > 0 and unknown_ratio >= 0.8
    all_unknown = total_tiered > 0 and unknown_count == total_tiered
    low_utilization = utilization_rate_val is not None and float(utilization_rate_val) <= max(float(utilization_threshold) + 0.10, 0.35)
    no_domain_relevant = total_sources > 0 and int(on_domain_source_count or 0) <= 0

    if generic_news_dominated:
        signals.append("generic_news_dominated")
    if mostly_unknown:
        signals.append("mostly_unknown_sources")
    if all_unknown:
        signals.append("all_unknown_sources")
    if query_expects_official_evidence(query, report_type, query_type) and not official_evidence_found:
        signals.append("missing_expected_official_evidence")
    if query_expects_community_evidence(query, report_type, query_type) and not community_signal_found:
        signals.append("missing_expected_community_signal")
    if low_utilization:
        signals.append("low_utilization_near_threshold")
    if no_domain_relevant:
        signals.append("no_domain_relevant_source")

    reason: str | None = None
    if corpus_state == CorpusState.OFF_TOPIC.value:
        reason = "corpus_off_topic"
    elif corpus_weak:
        reason = "corpus_weak"
    elif failure_card_show:
        reason = "failure_card_shown"
    elif "missing_expected_official_evidence" in signals and mostly_unknown and (generic_news_dominated or no_domain_relevant or low_utilization):
        reason = "missing_expected_official_evidence"
    elif mostly_unknown and low_utilization and (generic_news_dominated or no_domain_relevant):
        reason = "low_utilization_unknown_sources"
    elif generic_news_dominated and no_domain_relevant and len(signals) >= 3:
        reason = "unsupported_off_domain_retrieval"
    return {
        "analyst_skipped": bool(reason),
        "analyst_skip_reason": reason,
        "post_retrieval_fast_path_used": bool(reason),
        "pre_analyst_gate_signals": signals,
    }


def post_economist_analyst_gate(
    *, query: str, report_type: str, complexity: str, economist_ran: bool,
    economist_block: str, corpus_state: str, corpus_weak: bool,
    failure_card_show: bool, pre_analyst_gate_skipped: bool,
    economist_schema_valid: bool = False,
) -> dict[str, Any]:
    """Return telemetry-only skip labels; Economist output never skips Analyst."""
    normalized_report_type = str(report_type or "").strip().lower()
    normalized_complexity = str(complexity or "").strip().lower()
    block = str(economist_block or "").strip()
    if normalized_report_type not in {"quantitative_comparison", "benchmark"}:
        reason = "report_type_not_bounded_quant"
    elif economist_schema_valid:
        reason = "economist_shadow_mode_no_framework"
    elif not economist_ran or not block:
        reason = "economist_empty_or_failed"
    elif corpus_state == CorpusState.OFF_TOPIC.value:
        reason = "corpus_off_topic"
    elif corpus_weak:
        reason = "corpus_weak"
    elif failure_card_show:
        reason = "failure_card_shown"
    elif pre_analyst_gate_skipped:
        reason = "pre_analyst_gate_skipped"
    elif normalized_complexity == "high":
        reason = "deep_mode_requires_scrutineer_path"
    elif query_requires_clinical_trial_comparative_caution(query):
        reason = "clinical_randomized_trial_comparative_effect_guardrail"
    else:
        reason = "economist_shadow_mode_no_framework"
    return {
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": reason,
        "economist_output_used_as_analysis": False,
    }


@dataclass(frozen=True)
class AnalystRuntimeDeps:
    ask_model: Callable[..., str]
    measure_context_stage: Callable[..., None]
    record_analyst_model_call: Callable[[str], None]
    evidence_slice_for_analyst: Callable[[], Any]
    pre_analyst_retrieval_gate: Callable[..., Mapping[str, Any]] = pre_analyst_retrieval_gate
    post_economist_analyst_gate: Callable[..., Mapping[str, Any]] = post_economist_analyst_gate
    monotonic: Callable[[], float] = time.monotonic


@dataclass(frozen=True)
class AnalystRuntimeRequest:
    values: Mapping[str, Any]

    def __getattr__(self, name: str) -> Any:
        try:
            return self.values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


_OUTCOME_NAMES = """analysis author_notes analyst_seconds pre_analyst_gate post_economist_gate pre_gate_failure_card_show pre_gate_failure_card_reason pre_analyst_gate_contract pre_analyst_gate_handoff analyst_skipped analyst_skip_reason post_retrieval_fast_path_used pre_analyst_gate_signals estimate_from_priors_blocked_by_pre_analyst_gate economist_ran economist_preflight_allowed economist_preflight_block_reason economist_preflight_missing_entities analyst_skipped_after_economist analyst_after_economist_skip_reason economist_output_used_as_analysis""".split()
_AnalystRuntimeOutcomeBase = namedtuple("AnalystRuntimeOutcome", _OUTCOME_NAMES)


class AnalystRuntimeOutcome(_AnalystRuntimeOutcomeBase):
    __slots__ = ()

    def orchestrator_values(self) -> tuple[Any, ...]:
        """Return values in the assignment order used by pipeline_orchestrator."""
        return tuple(self)


def multicomponent_analyst_bypass_outcome_from_scope(
    scope: Mapping[str, Any],
) -> AnalystRuntimeOutcome:
    """Keep the legacy Analyst lane closed after Graph V1 has completed."""

    reason = "ordinary_multicomponent_graph_v1_completed"
    pre_analyst_gate = {
        "analyst_skipped": True,
        "analyst_skip_reason": reason,
        "post_retrieval_fast_path_used": True,
        "pre_analyst_gate_signals": [reason],
    }
    post_economist_gate = {
        "analyst_skipped_after_economist": True,
        "analyst_after_economist_skip_reason": reason,
        "economist_output_used_as_analysis": False,
    }
    pre_analyst_gate_contract = build_analyst_gate_descriptor(
        pre_analyst_gate=pre_analyst_gate,
        post_economist_gate=post_economist_gate,
    )
    return AnalystRuntimeOutcome(
        analysis="",
        author_notes=str(scope.get("author_notes") or ""),
        analyst_seconds=float(scope.get("analyst_seconds") or 0.0),
        pre_analyst_gate=pre_analyst_gate,
        post_economist_gate=post_economist_gate,
        pre_gate_failure_card_show=False,
        pre_gate_failure_card_reason=None,
        pre_analyst_gate_contract=pre_analyst_gate_contract,
        pre_analyst_gate_handoff=pre_analyst_gate_contract.to_trace(),
        analyst_skipped=True,
        analyst_skip_reason=reason,
        post_retrieval_fast_path_used=True,
        pre_analyst_gate_signals=[reason],
        estimate_from_priors_blocked_by_pre_analyst_gate=False,
        economist_ran=bool(scope.get("economist_ran")),
        economist_preflight_allowed=bool(
            scope.get("economist_preflight_allowed")
        ),
        economist_preflight_block_reason=scope.get(
            "economist_preflight_block_reason"
        ),
        economist_preflight_missing_entities=list(
            scope.get("economist_preflight_missing_entities") or ()
        ),
        analyst_skipped_after_economist=True,
        analyst_after_economist_skip_reason=reason,
        economist_output_used_as_analysis=False,
    )


def build_analyst_model_call_recorder(telemetry: MutableMapping[str, Any]) -> Callable[[str], None]:
    """Create the legacy Analyst model-call telemetry mutator."""
    def _record_analyst_model_call(prompt: str) -> None:
        telemetry["analyst_model_called"] = True
        if telemetry.get("analyst_quant_packet_injected") is True and "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY" in str(prompt or ""):
            telemetry["analyst_quant_packet_reviewed_by_model"] = True
    return _record_analyst_model_call


def execute_analyst_runtime_stage_from_scope(scope: Mapping[str, Any], *, deps: AnalystRuntimeDeps) -> AnalystRuntimeOutcome:
    """Build a request from an explicit local-scope whitelist and execute it."""
    stage_scope = {key: scope[key] for key in _SCOPE_KEYS if key in scope}
    stage_scope["default_system"] = stage_scope["DEFAULT_SYSTEM"]
    return execute_analyst_runtime_stage(AnalystRuntimeRequest(stage_scope), deps)


def _run_analyst_model(request: AnalystRuntimeRequest, deps: AnalystRuntimeDeps, *, stage: str, system_key: str, estimate_from_priors: bool = False) -> tuple[str, float]:
    started = deps.monotonic()
    analyst_prompt = build_analyst_prompt(
        analyst_cached_prefix=request.analyst_cached_prefix,
        intent=request.intent,
        analyst_effort=request.analyst_effort,
        estimate_from_priors=estimate_from_priors,
    )
    system_prompt = request.default_system[system_key]
    deps.measure_context_stage(
        stage,
        prompt=analyst_prompt,
        system_prompt=system_prompt,
        stable_prefix=system_prompt,
        evidence_passages=deps.evidence_slice_for_analyst(),
    )
    deps.record_analyst_model_call(analyst_prompt)
    analysis = deps.ask_model(
        analyst_prompt,
        system_prompt,
        provider=request.smart_provider,
        model=request.smart_model,
        effort=request.analyst_effort,
        base_url=request.local_url,
        api_key=request.or_api_key,
        use_reasoning=request.use_reasoning,
    )
    return analysis, max(0.0, deps.monotonic() - started)


def _pre_gate_failure_card_inputs(request: AnalystRuntimeRequest) -> tuple[bool, str]:
    total_chunks = max(0, int(request.total_chunks_embedded))
    utilization = float(request.utilization_rate_val or 0.0)
    chunks_with_entity = min(total_chunks, max(0, int(round(utilization * max(1, total_chunks))))) if total_chunks else 0
    show = failure_card_should_show(
        corpus_state=request.corpus_state,
        retrieval_retry_used=request.retrieval_retry_used,
        empty_entity=request.empty_entity_flag,
        scrutineer_high_count=0,
        useful_content=True,
    )
    reason = failure_card_reason(
        corpus_state=request.corpus_state,
        retrieval_retry_used=request.retrieval_retry_used,
        empty_entity=request.empty_entity_flag,
        scrutineer_high_count=0,
        useful_content=True,
        chunks_with_entity=chunks_with_entity,
        total_chunks_embedded=total_chunks,
    )
    return show, reason


def execute_analyst_runtime_stage(request: AnalystRuntimeRequest, deps: AnalystRuntimeDeps) -> AnalystRuntimeOutcome:
    """Execute the bounded first Analyst runtime seam without owning policy."""
    tier = source_tier_telemetry(request.all_passages)
    domain = source_domain_telemetry(request.all_passages, domain_anchor=request.primary_entity or request.core_topic)
    pre_gate_failure_card_show, pre_gate_failure_card_reason = _pre_gate_failure_card_inputs(request)
    pre_analyst_gate = deps.pre_analyst_retrieval_gate(
        query=request.query,
        report_type=request.report_type,
        query_type=request.query_type,
        corpus_state=request.corpus_state,
        corpus_weak=request.corpus_weak,
        failure_card_show=pre_gate_failure_card_show,
        utilization_rate_val=request.utilization_rate_val,
        utilization_threshold=request.utilization_threshold,
        source_tier_counts=tier["source_tier_counts"],
        source_domain_counts=domain["source_domain_counts"],
        top_source_domains=domain["top_source_domains"],
        on_domain_source_count=domain["on_domain_source_count"],
        official_evidence_found=tier["official_evidence_found"],
        community_signal_found=tier["community_signal_found"],
    )
    post_economist_gate = deps.post_economist_analyst_gate(
        query=request.query,
        report_type=request.report_type,
        complexity=request.complexity,
        economist_ran=request.economist_ran,
        economist_block="",
        economist_schema_valid=bool(request.economist_safety_telemetry.get("economist_schema_valid")),
        corpus_state=request.corpus_state,
        corpus_weak=request.corpus_weak,
        failure_card_show=pre_gate_failure_card_show,
        pre_analyst_gate_skipped=bool(pre_analyst_gate["analyst_skipped"]),
    )
    analyst_skipped_after_economist = bool(post_economist_gate["analyst_skipped_after_economist"])
    analyst_after_economist_skip_reason = post_economist_gate["analyst_after_economist_skip_reason"]
    economist_output_used_as_analysis = bool(post_economist_gate["economist_output_used_as_analysis"])
    economist_handoff = execute_economist_handoff(build_economist_handoff_state(
        run_id=request.run_id,
        need_economist=request.need_economist,
        economist_ran=request.economist_ran,
        economist_preflight_allowed=request.economist_preflight_allowed,
        economist_preflight_block_reason=request.economist_preflight_block_reason,
        economist_preflight_missing_entities=request.economist_preflight_missing_entities,
        economist_safety_telemetry=request.economist_safety_telemetry,
        economist_pre_analyst_skip_candidate_telemetry=request.economist_pre_analyst_skip_candidate_telemetry,
        analyst_quant_packet_handoff_telemetry=request.analyst_quant_packet_handoff_telemetry,
        author_quant_source_telemetry=request.author_quant_source_telemetry,
        analyst_skipped_after_economist=analyst_skipped_after_economist,
        analyst_after_economist_skip_reason=analyst_after_economist_skip_reason,
        economist_output_used_as_analysis=economist_output_used_as_analysis,
        estimate_from_priors_requested=request.estimate_from_priors_requested,
        estimate_from_priors_blocked_by_pre_analyst_gate=request.estimate_from_priors_blocked_by_pre_analyst_gate,
        answer_contract_ref=None,
    ))
    pre_analyst_gate_contract = build_analyst_gate_descriptor(pre_analyst_gate=pre_analyst_gate, post_economist_gate=post_economist_gate)
    pre_analyst_gate_handoff = pre_analyst_gate_contract.to_trace()
    analyst_skipped = bool(pre_analyst_gate_handoff["analyst_skipped"])
    analyst_skip_reason = pre_analyst_gate_handoff["analyst_skip_reason"]
    post_retrieval_fast_path_used = bool(pre_analyst_gate_handoff["post_retrieval_fast_path_used"])
    pre_analyst_gate_signals = list(pre_analyst_gate_handoff["pre_analyst_gate_signals"])
    estimate_blocked = bool(request.estimate_from_priors_requested and analyst_skipped and post_retrieval_fast_path_used and analyst_skip_reason == "corpus_weak")

    author_notes = request.author_notes
    analyst_seconds = request.analyst_seconds
    if analyst_skipped:
        request.status.step("Retrieval quality gate skipped Analyst; sending unsupported-evidence directive to Author.")
        unsupported_prompt = build_unsupported_retrieval_prompt_fragments(
            analyst_skip_reason=analyst_skip_reason,
            pre_analyst_gate_signals=pre_analyst_gate_signals,
            pre_gate_failure_card_reason=pre_gate_failure_card_reason,
        )
        analysis = unsupported_prompt.analysis
        author_notes += unsupported_prompt.author_note_append
    elif request.complexity == "low":
        request.status.step("Skipping deep analysis (Fast mode)...")
        analysis = "DIRECT_TO_AUTHOR"
    elif request.corpus_weak and request.complexity in ("medium", "high"):
        if request.corpus_state == CorpusState.ESTIMATE_FROM_PRIORS.value:
            request.status.step("Thin corpus vs anchors — running analyst pass with estimation framing…")
            analysis, elapsed = _run_analyst_model(request, deps, stage="analyst_estimate_from_priors", system_key="analyst_estimate_from_priors", estimate_from_priors=True)
            analyst_seconds += elapsed
        else:
            request.status.step("Source match is low for the main subject; keeping the answer short.")
            analysis = "DIRECT_TO_AUTHOR"
    else:
        request.status.step(f"Analyzing and compressing evidence (Effort: {request.analyst_effort})...")
        analysis, elapsed = _run_analyst_model(request, deps, stage="analyst", system_key="analyst")
        analyst_seconds += elapsed

    return AnalystRuntimeOutcome(
        analysis,
        author_notes,
        analyst_seconds,
        pre_analyst_gate,
        post_economist_gate,
        pre_gate_failure_card_show,
        pre_gate_failure_card_reason,
        pre_analyst_gate_contract,
        pre_analyst_gate_handoff,
        analyst_skipped,
        analyst_skip_reason,
        post_retrieval_fast_path_used,
        pre_analyst_gate_signals,
        estimate_blocked,
        economist_handoff.economist_ran,
        economist_handoff.economist_preflight_allowed,
        economist_handoff.economist_preflight_block_reason,
        list(economist_handoff.economist_preflight_missing_entities),
        economist_handoff.analyst_skipped_after_economist,
        economist_handoff.analyst_after_economist_skip_reason,
        economist_handoff.economist_output_used_as_analysis,
    )
