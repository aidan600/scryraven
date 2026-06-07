"""Post-Analyst handoff packaging helpers.

Packages already-computed Analyst/Economist/gate outputs for downstream legacy
handoffs. It does not build prompts, call providers, retrieve/search, choose
evidence, format citations, or change FinalAnswerPacket semantics.
"""

from __future__ import annotations

import re
from collections import namedtuple
from typing import Any, Callable, Mapping, Sequence

from core.analyst_author_handoff_contract import build_analyst_author_handoff_state, execute_analyst_author_handoff

_SCOPE_FIELD_NAMES = """run_id analyst_skipped analyst_skip_reason post_retrieval_fast_path_used pre_analyst_gate_signals analyst_skipped_after_economist analyst_after_economist_skip_reason economist_output_used_as_analysis analyst_cached_prefix linkup_block analyst_quant_packet_handoff_telemetry missing_target_metric_directive_emitted corpus_weak _pre_gate_failure_card_show _pre_gate_failure_card_reason author_notes author_evidence final_top_evidence ordered_sources unique_source_urls author_evidence_block author_prompt complexity author_system_prompt_key _author_effort recency_notes image_context pre_analyst_gate_contract retrieval_loop_contract_state router_query_preparation_contract report_type strategy economist_safety_telemetry quant_retrieval_sufficiency_telemetry economist_pre_analyst_skip_candidate_telemetry pre_analyst_gate analysis _efp_author _relevance_low""".split()
_SCOPE_KEYS = frozenset(_SCOPE_FIELD_NAMES)
class PostAnalystHandoffPackagingOutcome(
    namedtuple(
        "PostAnalystHandoffPackagingOutcome",
        "analyst_author_handoff_state analyst_author_handoff author_system_prompt_key author_effort author_quant_source_telemetry economist_skip_eligibility_shadow_telemetry economist_skip_shadow_alignment",
    )
):
    __slots__ = ()

    def orchestrator_values(self) -> tuple[Any, ...]:
        return tuple(self)


def _mapping_or_none(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, Mapping) else None


def _author_quant_source_telemetry_defaults() -> dict[str, Any]:
    return {
        "author_quant_content_source": "none",
        "author_received_raw_quant_packet": False,
        "author_received_economist_framework": False,
        "author_received_analyst_packet_marker": False,
        "author_quant_handoff_gate_reason": "no_quantitative_author_handoff_detected",
    }


def _economist_skip_eligibility_shadow_defaults() -> dict[str, Any]:
    return {
        "economist_skip_eligible_shadow": False,
        "economist_skip_eligibility_reasons": [],
        "economist_skip_eligibility_blockers": [],
        "economist_skip_eligibility_gate_reason": "not_evaluated",
        "economist_skip_eligibility_shadow_mode": True,
    }


def _author_prompt_contains_raw_economist_framework(prompt: str) -> bool:
    text = str(prompt or "")
    heading_pattern = re.compile(r"(?im)^\s*(?:#{1,6}\s*)?(?:LEGACY\s+)?QUANTITATIVE FRAMEWORK\b[^\n]*")
    payload_markers = (
        "MODEL-DERIVED", "Normalization approach", "Computed results",
        "computed value", "Numeric rendering", "central", "range",
    )
    for match in heading_pattern.finditer(text):
        normalized_heading = match.group(0).casefold()
        if re.search(r"\bnot\s+(?:run|shown)\b", normalized_heading):
            continue
        window = text[match.end(): match.end() + 1200]
        if any(marker in window for marker in payload_markers):
            return True
    return False


def _scan_author_quant_source_telemetry(
    author_prompt: str, *, analyst_quant_packet_reviewed_by_model: bool, analysis: str | None
) -> dict[str, Any]:
    telemetry = _author_quant_source_telemetry_defaults()
    prompt = str(author_prompt or "")
    has_raw_packet = "quantitative_packet" in prompt or "quantitative_packet_v1" in prompt
    has_analyst_packet_marker = "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY" in prompt
    has_economist_framework = _author_prompt_contains_raw_economist_framework(prompt)
    telemetry.update({
        "author_received_raw_quant_packet": has_raw_packet,
        "author_received_analyst_packet_marker": has_analyst_packet_marker,
        "author_received_economist_framework": has_economist_framework,
    })
    if has_raw_packet:
        telemetry["author_quant_content_source"] = "raw_quant_packet_detected"
        telemetry["author_quant_handoff_gate_reason"] = "author_prompt_contains_raw_quant_packet"
    elif has_analyst_packet_marker:
        telemetry["author_quant_content_source"] = "analyst_packet_marker_detected"
        telemetry["author_quant_handoff_gate_reason"] = "author_prompt_contains_analyst_packet_marker"
    elif has_economist_framework:
        telemetry["author_quant_content_source"] = "raw_economist_block_detected"
        telemetry["author_quant_handoff_gate_reason"] = "author_prompt_contains_economist_framework"
    elif analyst_quant_packet_reviewed_by_model and str(analysis or "").strip():
        telemetry["author_quant_content_source"] = "analyst_reviewed"
        telemetry["author_quant_handoff_gate_reason"] = "author_received_analyst_reviewed_quantitative_synthesis"
    return telemetry


def _economist_skip_shadow_alignment(
    *, pre_analyst_candidate_telemetry: dict[str, Any] | None, posthoc_skip_eligibility_telemetry: dict[str, Any] | None
) -> str:
    """Compare shadow candidate signals without changing runtime behavior."""
    if not isinstance(pre_analyst_candidate_telemetry, dict) or not isinstance(posthoc_skip_eligibility_telemetry, dict):
        return "not_evaluated"
    pre_candidate = bool(pre_analyst_candidate_telemetry.get("economist_pre_analyst_skip_candidate_shadow"))
    posthoc_eligible = bool(posthoc_skip_eligibility_telemetry.get("economist_skip_eligible_shadow"))
    if pre_candidate and posthoc_eligible:
        return "candidate_and_posthoc_eligible"
    if pre_candidate:
        return "candidate_only"
    if posthoc_eligible:
        return "posthoc_only"
    return "neither"


def _economist_skip_eligibility_shadow_telemetry(
    *, report_type: str, complexity: str, mode: str,
    economist_safety_telemetry: dict[str, Any], analyst_quant_packet_handoff_telemetry: dict[str, Any],
    author_quant_source_telemetry: dict[str, Any], analyst_skipped_after_economist: bool,
    economist_output_used_as_analysis: bool, pre_analyst_gate_skipped: bool | None = None,
    quant_retrieval_sufficiency_telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Diagnostic-only posthoc skip eligibility telemetry."""
    telemetry = _economist_skip_eligibility_shadow_defaults()
    reasons: list[str] = []
    blockers: list[str] = []
    bounded_quantitative = str(report_type).lower() in {"quantitative_comparison", "benchmark"}
    (reasons if bounded_quantitative else blockers).append(
        "bounded_quantitative_report" if bounded_quantitative else "non_bounded_quantitative_report"
    )
    if bounded_quantitative:
        quant_retrieval_sufficiency_telemetry = quant_retrieval_sufficiency_telemetry or {}
        target = bool(quant_retrieval_sufficiency_telemetry.get("quant_retrieval_target_detected"))
        valid = bool(quant_retrieval_sufficiency_telemetry.get("quant_retrieval_sufficiency_valid"))
        if target and valid:
            reasons.append("retrieval_sufficiency_valid")
        else:
            blockers.append("retrieval_sufficiency_missing" if not target else "retrieval_sufficiency_failed")
    (reasons if str(complexity).lower() == "medium" else blockers).append(
        "medium_complexity" if str(complexity).lower() == "medium" else "non_medium_complexity"
    )
    packet_valid = bool(economist_safety_telemetry.get("quantitative_packet_valid"))
    packet_direct = bool(economist_safety_telemetry.get("quantitative_packet_direct_use_eligible"))
    packet_requires_analyst = bool(economist_safety_telemetry.get("quantitative_packet_requires_analyst"))
    if packet_valid and packet_direct and not packet_requires_analyst:
        reasons.append("valid_direct_use_packet")
    else:
        if not packet_valid:
            blockers.append("packet_invalid_or_missing")
        if not packet_direct:
            blockers.append("packet_not_direct_use_eligible")
        if packet_requires_analyst:
            blockers.append("packet_requires_analyst")
    if bool(economist_safety_telemetry.get("high_stakes_quant_detected")):
        blockers.append("high_stakes_requires_analyst")
    else:
        reasons.append("non_high_stakes")
    if bool(economist_safety_telemetry.get("economist_code_execution_requested")):
        blockers.append("economist_code_execution_requested")
    analyst_reviewed = bool(analyst_quant_packet_handoff_telemetry.get("analyst_quant_packet_reviewed_by_model"))
    analyst_model_called = bool(analyst_quant_packet_handoff_telemetry.get("analyst_model_called"))
    if analyst_reviewed and analyst_model_called:
        reasons.append("analyst_reviewed_packet")
    else:
        if not analyst_reviewed:
            blockers.append("packet_not_reviewed_by_analyst")
        if not analyst_model_called:
            blockers.append("analyst_model_not_called")
    if author_quant_source_telemetry.get("author_quant_content_source") == "analyst_reviewed":
        reasons.append("author_received_analyst_reviewed_synthesis")
    else:
        blockers.append("author_not_analyst_reviewed")
    marker_blockers = (
        ("author_received_raw_quant_packet", "author_raw_packet_marker_detected"),
        ("author_received_economist_framework", "author_framework_marker_detected"),
        ("author_received_analyst_packet_marker", "author_analyst_packet_marker_detected"),
    )
    marker_leak = False
    for source_key, blocker in marker_blockers:
        if bool(author_quant_source_telemetry.get(source_key)):
            marker_leak = True
            blockers.append(blocker)
    if not marker_leak:
        reasons.append("no_author_marker_leak")
    if economist_output_used_as_analysis:
        blockers.append("economist_output_used_as_analysis")
    else:
        reasons.append("economist_not_used_as_analysis")
    if analyst_skipped_after_economist:
        blockers.append("analyst_already_skipped")
    else:
        reasons.append("analyst_not_skipped")
    if pre_analyst_gate_skipped is True:
        blockers.append("pre_analyst_gate_skipped")
    gate_reason = _economist_skip_gate_reason(blockers)
    telemetry.update({
        "economist_skip_eligible_shadow": not blockers,
        "economist_skip_eligibility_reasons": reasons,
        "economist_skip_eligibility_blockers": blockers,
        "economist_skip_eligibility_gate_reason": gate_reason,
        "economist_skip_eligibility_shadow_mode": True,
    })
    return telemetry


def _economist_skip_gate_reason(blockers: Sequence[str]) -> str:
    if not blockers:
        return "eligible_shadow_only"
    ordered = (
        ("high_stakes_requires_analyst", "blocked_by_high_stakes"),
        ("packet_invalid_or_missing", "blocked_by_invalid_packet"),
        (("packet_not_reviewed_by_analyst", "analyst_model_not_called"), "blocked_by_missing_analyst_review"),
        (("author_raw_packet_marker_detected", "author_framework_marker_detected", "author_analyst_packet_marker_detected"), "blocked_by_author_marker_leak"),
        (("retrieval_sufficiency_failed", "retrieval_sufficiency_missing"), "blocked_by_retrieval_sufficiency"),
        ("non_bounded_quantitative_report", "blocked_by_report_type"),
        ("non_medium_complexity", "blocked_by_complexity"),
        ("economist_code_execution_requested", "blocked_by_code_request"),
        ("pre_analyst_gate_skipped", "blocked_by_pre_analyst_gate"),
    )
    for keys, reason in ordered:
        if isinstance(keys, str):
            keys = (keys,)
        if any(key in blockers for key in keys):
            return reason
    return "blocked_by_multiple_reasons"


def build_post_analyst_handoff_packaging(
    *, run_id: str, analyst_skipped: bool, analyst_skip_reason: str | None,
    post_retrieval_fast_path_used: bool, pre_analyst_gate_signals: Sequence[str],
    analyst_skipped_after_economist: bool, analyst_after_economist_skip_reason: str | None,
    economist_output_used_as_analysis: bool, analyst_evidence: Sequence[Any], analyst_context_prefix: str,
    linkup_block_included: bool, quantitative_packet_injected: bool, missing_target_metric_directive_emitted: bool,
    corpus_weak: bool, failure_card_payload: Mapping[str, Any], author_notes: str,
    author_evidence: Sequence[Any], selected_evidence: Sequence[Any], final_evidence: Sequence[Any], ordered_sources: Sequence[Any],
    unique_source_urls: Sequence[str], author_evidence_block: str, author_prompt: str, complexity: str,
    author_system_prompt_key: str, author_effort: str, includes_analysis: bool, includes_recency_notes: bool,
    includes_author_notes: bool, image_context_active: bool, pre_analyst_gate_ref: Any, retrieval_loop_state: Any,
    router_query_preparation_state: Any, report_type: str, mode: str, economist_safety_telemetry: Mapping[str, Any],
    analyst_quant_packet_handoff_telemetry: Mapping[str, Any], author_quant_source_telemetry: Mapping[str, Any],
    quant_retrieval_sufficiency_telemetry: Mapping[str, Any] | None,
    economist_pre_analyst_skip_candidate_telemetry: Mapping[str, Any] | None, pre_analyst_gate_skipped: bool | None,
) -> PostAnalystHandoffPackagingOutcome:
    """Package already-computed post-Analyst values for legacy handoff consumers."""
    skip_telemetry = _economist_skip_eligibility_shadow_telemetry(
        report_type=report_type, complexity=complexity, mode=mode,
        economist_safety_telemetry=dict(economist_safety_telemetry),
        analyst_quant_packet_handoff_telemetry=dict(analyst_quant_packet_handoff_telemetry),
        author_quant_source_telemetry=dict(author_quant_source_telemetry),
        quant_retrieval_sufficiency_telemetry=_mapping_or_none(quant_retrieval_sufficiency_telemetry),
        analyst_skipped_after_economist=analyst_skipped_after_economist,
        economist_output_used_as_analysis=economist_output_used_as_analysis,
        pre_analyst_gate_skipped=pre_analyst_gate_skipped,
    )
    handoff_state = build_analyst_author_handoff_state(
        run_id=run_id, analyst_skipped=analyst_skipped, analyst_skip_reason=analyst_skip_reason,
        post_retrieval_fast_path_used=post_retrieval_fast_path_used, pre_analyst_gate_signals=pre_analyst_gate_signals,
        analyst_skipped_after_economist=analyst_skipped_after_economist,
        analyst_after_economist_skip_reason=analyst_after_economist_skip_reason,
        economist_output_used_as_analysis=economist_output_used_as_analysis, analyst_evidence=analyst_evidence,
        analyst_context_prefix=analyst_context_prefix, linkup_block_included=linkup_block_included,
        quantitative_packet_injected=quantitative_packet_injected,
        missing_target_metric_directive_emitted=missing_target_metric_directive_emitted,
        corpus_weak=corpus_weak, failure_card_payload=failure_card_payload, author_notes=author_notes,
        author_evidence=author_evidence, selected_evidence=selected_evidence, final_evidence=final_evidence,
        ordered_sources=ordered_sources, unique_source_urls=unique_source_urls, author_evidence_block=author_evidence_block,
        author_prompt=author_prompt, complexity=complexity, author_system_prompt_key=author_system_prompt_key,
        author_effort=author_effort, includes_analysis=includes_analysis, includes_recency_notes=includes_recency_notes,
        includes_author_notes=includes_author_notes, image_context_active=image_context_active,
        pre_analyst_gate_ref=pre_analyst_gate_ref, retrieval_loop_state=retrieval_loop_state,
        router_query_preparation_state=router_query_preparation_state,
    )
    handoff = execute_analyst_author_handoff(handoff_state)
    return PostAnalystHandoffPackagingOutcome(
        handoff_state, handoff, handoff.author_system_prompt_key, handoff.author_effort,
        dict(author_quant_source_telemetry), skip_telemetry,
        _economist_skip_shadow_alignment(
            pre_analyst_candidate_telemetry=_mapping_or_none(economist_pre_analyst_skip_candidate_telemetry),
            posthoc_skip_eligibility_telemetry=skip_telemetry,
        ),
    )


def build_post_analyst_handoff_packaging_from_scope(
    scope: Mapping[str, Any], *, evidence_slice_for_analyst: Callable[[], Sequence[Any]]
) -> PostAnalystHandoffPackagingOutcome:
    """Orchestrator adapter using a strict whitelist of local names."""
    v = {name: scope[name] for name in _SCOPE_KEYS}
    author_quant = _scan_author_quant_source_telemetry(
        v["author_prompt"],
        analyst_quant_packet_reviewed_by_model=bool(v["analyst_quant_packet_handoff_telemetry"].get("analyst_quant_packet_reviewed_by_model")),
        analysis=v["analysis"],
    )
    return build_post_analyst_handoff_packaging(
        run_id=v["run_id"], analyst_skipped=v["analyst_skipped"], analyst_skip_reason=v["analyst_skip_reason"],
        post_retrieval_fast_path_used=v["post_retrieval_fast_path_used"], pre_analyst_gate_signals=v["pre_analyst_gate_signals"],
        analyst_skipped_after_economist=v["analyst_skipped_after_economist"],
        analyst_after_economist_skip_reason=v["analyst_after_economist_skip_reason"],
        economist_output_used_as_analysis=v["economist_output_used_as_analysis"], analyst_evidence=evidence_slice_for_analyst(),
        analyst_context_prefix=v["analyst_cached_prefix"], linkup_block_included=bool(v["linkup_block"]),
        quantitative_packet_injected=bool(v["analyst_quant_packet_handoff_telemetry"].get("analyst_quant_packet_injected")),
        missing_target_metric_directive_emitted=v["missing_target_metric_directive_emitted"], corpus_weak=v["corpus_weak"],
        failure_card_payload={"show": v["_pre_gate_failure_card_show"], "reason": v["_pre_gate_failure_card_reason"]},
        author_notes=v["author_notes"], author_evidence=v["author_evidence"], selected_evidence=v["final_top_evidence"],
        final_evidence=v["final_top_evidence"], ordered_sources=v["ordered_sources"], unique_source_urls=v["unique_source_urls"],
        author_evidence_block=v["author_evidence_block"], author_prompt=v["author_prompt"], complexity=v["complexity"],
        author_system_prompt_key=v["author_system_prompt_key"], author_effort=v["_author_effort"],
        includes_analysis=v["complexity"] != "low" and (not v["corpus_weak"] or v["_efp_author"]) and not v["_relevance_low"],
        includes_recency_notes=bool(v["recency_notes"]), includes_author_notes=bool(v["author_notes"]),
        image_context_active=bool(v["image_context"]), pre_analyst_gate_ref=v["pre_analyst_gate_contract"],
        retrieval_loop_state=v["retrieval_loop_contract_state"], router_query_preparation_state=v["router_query_preparation_contract"],
        report_type=v["report_type"], mode=v["strategy"], economist_safety_telemetry=v["economist_safety_telemetry"],
        analyst_quant_packet_handoff_telemetry=v["analyst_quant_packet_handoff_telemetry"], author_quant_source_telemetry=author_quant,
        quant_retrieval_sufficiency_telemetry=v["quant_retrieval_sufficiency_telemetry"],
        economist_pre_analyst_skip_candidate_telemetry=v["economist_pre_analyst_skip_candidate_telemetry"],
        pre_analyst_gate_skipped=bool(v["pre_analyst_gate"]["analyst_skipped"]),
    )
