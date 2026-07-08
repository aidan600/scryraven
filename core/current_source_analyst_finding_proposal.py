"""Source-grounded Analyst finding proposal contract for current-source runs.

The proposal records analysis custody over already-triaged candidate refs. It is
not evidence, not a citation, not answer authority, and not product correctness.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

ANALYST_FINDING_PROPOSAL_SCHEMA_VERSION = "analyst_finding_proposal_v1"
ANALYST_SOURCE_SUPPORT_MAP_SCHEMA_VERSION = "analyst_source_support_map_v1"
ANALYST_SAFE_MODEL_INPUT_PACKET_SCHEMA_VERSION = (
    "analyst_finding_safe_model_input_packet_v1"
)
ANALYST_MODEL_OUTPUT_VALIDATION_SCHEMA_VERSION = (
    "analyst_finding_model_output_validation_v1"
)
ANALYST_FINDING_PROPOSAL_PHASE = (
    "CURRENT-SOURCE-ANALYST-FINDING-CONTRACT-CUSTODY-V1-01"
)

FINDING_STATUS_SOURCE_GROUNDED_PROPOSED = "source_grounded_proposed"
FINDING_STATUS_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
FINDING_STATUS_FOLLOWUP_REQUIRED = "followup_required"

ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER = "proposed_answer"
ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION = "evidence_interpretation"
ANALYSIS_CLAIM_KIND_CAVEAT = "caveat"
ANALYSIS_CLAIM_KIND_EXCLUSION = "exclusion"
ANALYSIS_CLAIM_KIND_GAP = "gap"
ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK = "overclaim_risk"
ANALYSIS_CLAIM_KIND_CONFLICT_RISK = "conflict_risk"

SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED = "source_grounded_proposed"
SUPPORT_STATUS_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
SUPPORT_STATUS_ADJACENT_ONLY = "adjacent_only"
SUPPORT_STATUS_UNREADABLE_SOURCE_NEEDED = "unreadable_source_needed"
SUPPORT_STATUS_CONFLICT_OR_OVERCLAIM_RISK = "conflict_or_overclaim_risk"

MODEL_ADAPTER_KIND_FAKE_TEST = "fake_test_adapter"

_RAW_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_source_content_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}
_NON_AUTHORITY_FALSE_FLAGS = {
    "evidence_admitted": False,
    "source_obligation_satisfied": False,
    "citation_eligibility_created": False,
    "final_answer_packet_created": False,
    "author_output_created": False,
    "product_correctness_claimed": False,
    "component_coverage_created": False,
    "sufficiency_readiness_created": False,
    "source_display_opened": False,
}
_NON_AUTHORITY_TRUE_FLAGS = {
    "proposal_only": True,
    "analysis_is_not_evidence": True,
    "analysis_is_not_citation": True,
    "analysis_is_not_answer_authority": True,
    "source_grounding_required": True,
    "dprime_validation_required": True,
}
_CLAIM_KINDS = frozenset(
    {
        ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER,
        ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION,
        ANALYSIS_CLAIM_KIND_CAVEAT,
        ANALYSIS_CLAIM_KIND_EXCLUSION,
        ANALYSIS_CLAIM_KIND_GAP,
        ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK,
        ANALYSIS_CLAIM_KIND_CONFLICT_RISK,
    }
)
_SUPPORT_STATUSES = frozenset(
    {
        SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED,
        SUPPORT_STATUS_INSUFFICIENT_EVIDENCE,
        SUPPORT_STATUS_ADJACENT_ONLY,
        SUPPORT_STATUS_UNREADABLE_SOURCE_NEEDED,
        SUPPORT_STATUS_CONFLICT_OR_OVERCLAIM_RISK,
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "bounded_text",
        "cache_row",
        "cookie",
        "cookies",
        "db_row",
        "env",
        "full_prompt",
        "full_text",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_extracted_text",
        "provider_payload",
        "raw_html",
        "raw_model_response",
        "raw_page",
        "raw_page_content",
        "raw_page_text",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "raw_source_text",
        "raw_text",
        "secret",
        "secrets",
        "token",
        "unbounded_text",
    }
)
_DANGEROUS_TRUE_KEYS = frozenset(_NON_AUTHORITY_FALSE_FLAGS) | {
    "citation_eligible",
    "component_coverage_bound",
    "evidence_claimed",
    "final_answer_packet_ready",
    "source_obligation_authority_claimed",
    "support_admitted",
    "support_claimed",
}
_VALUE_PATTERNS = (
    r"\$\s?\d{1,6}(?:\.\d{2})?",
    r"\b\d{1,3}(?:\.\d+)?%",
    r"\b(?:19|20)\d{2}(?:-\d{1,2}(?:-\d{1,2})?)?\b",
    r"\b\d+(?:\.\d+)?\b",
)


class AnalystFindingProposalError(ValueError):
    """Raised when Analyst finding custody or grounding is invalid."""


FakeAnalystFindingAdapter = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def build_deterministic_analyst_finding_proposal(
    *,
    triage_packet: Mapping[str, Any],
    analysis_gap_search_proposal: Mapping[str, Any],
    fetch_read_content_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic proposal-only Analyst finding."""

    triage = _safe_mapping(triage_packet)
    gap = _safe_mapping(analysis_gap_search_proposal)
    fetch_packet = _safe_mapping(fetch_read_content_packet)
    binding_ref = _safe_mapping(triage.get("component_answer_type_binding_ref"))
    selected_refs = _safe_refs(triage.get("selected_answer_bearing_candidate_refs"))
    adjacent_refs = _safe_refs(triage.get("adjacent_context_candidate_refs"))
    excluded_refs = _safe_refs(triage.get("excluded_scope_candidate_refs"))
    unreadable_refs = _safe_refs(triage.get("unreadable_high_value_candidate_refs"))
    overclaim_refs = _safe_refs(triage.get("overclaim_risk_candidate_refs"))
    triage_summary_ref = _safe_mapping(triage.get("candidate_triage_summary_ref"))
    bounded_content_refs = _bounded_content_refs(
        fetch_packet,
        candidate_refs=selected_refs,
    )
    finding_status = _finding_status(
        selected_refs=selected_refs,
        gap_proposal=gap,
    )
    analysis_summary = _analysis_summary_text(
        finding_status=finding_status,
        selected_refs=selected_refs,
        adjacent_refs=adjacent_refs,
        excluded_refs=excluded_refs,
        unreadable_refs=unreadable_refs,
        overclaim_refs=overclaim_refs,
    )
    analysis_summary_ref = _summary_ref(analysis_summary)
    support_map_seed = _source_support_map(
        component_answer_type_binding_ref=binding_ref,
        candidate_triage_summary_ref=triage_summary_ref,
        selected_answer_bearing_candidate_refs=selected_refs,
        adjacent_context_candidate_refs=adjacent_refs,
        excluded_scope_candidate_refs=excluded_refs,
        unreadable_high_value_candidate_refs=unreadable_refs,
        bounded_content_refs=bounded_content_refs,
        proposed_answer_claim_ref={},
        analysis_claim_refs=[],
    )
    support_map_ref = _source_support_map_ref(support_map_seed)
    proposed_answer_claim = _proposed_answer_claim(
        component_answer_type_binding_ref=binding_ref,
        selected_answer_bearing_candidate_refs=selected_refs,
        bounded_content_refs=bounded_content_refs,
        source_support_map_ref=support_map_ref,
    )
    analysis_claims = _analysis_claims(
        component_answer_type_binding_ref=binding_ref,
        proposed_answer_claim=proposed_answer_claim,
        selected_answer_bearing_candidate_refs=selected_refs,
        adjacent_context_candidate_refs=adjacent_refs,
        excluded_scope_candidate_refs=excluded_refs,
        unreadable_high_value_candidate_refs=unreadable_refs,
        overclaim_risk_candidate_refs=overclaim_refs,
        bounded_content_refs=bounded_content_refs,
        source_support_map_ref=support_map_ref,
        gap_proposal=gap,
    )
    source_support_map = _source_support_map(
        component_answer_type_binding_ref=binding_ref,
        candidate_triage_summary_ref=triage_summary_ref,
        selected_answer_bearing_candidate_refs=selected_refs,
        adjacent_context_candidate_refs=adjacent_refs,
        excluded_scope_candidate_refs=excluded_refs,
        unreadable_high_value_candidate_refs=unreadable_refs,
        bounded_content_refs=bounded_content_refs,
        proposed_answer_claim_ref=_proposed_answer_claim_ref(proposed_answer_claim),
        analysis_claim_refs=[_analysis_claim_ref(item) for item in analysis_claims],
    )
    source_support_map_ref = _source_support_map_ref(source_support_map)
    if proposed_answer_claim:
        proposed_answer_claim = {
            **proposed_answer_claim,
            "source_support_map_ref": source_support_map_ref,
        }
        proposed_answer_claim["proposed_answer_claim_digest"] = _digest_json(
            _without_digest(proposed_answer_claim)
        )
    analysis_claims = [
        _with_claim_support_map_ref(claim, source_support_map_ref)
        for claim in analysis_claims
    ]
    caveat_refs = [
        _analysis_claim_ref(item)
        for item in analysis_claims
        if item.get("analysis_claim_kind") == ANALYSIS_CLAIM_KIND_CAVEAT
    ]
    adjacent_exclusion_refs = [
        _analysis_claim_ref(item)
        for item in analysis_claims
        if item.get("analysis_claim_kind") == ANALYSIS_CLAIM_KIND_EXCLUSION
    ]
    unresolved_gap_refs = [
        _analysis_claim_ref(item)
        for item in analysis_claims
        if item.get("analysis_claim_kind") == ANALYSIS_CLAIM_KIND_GAP
    ]
    risk_refs = [
        _analysis_claim_ref(item)
        for item in analysis_claims
        if item.get("analysis_claim_kind")
        in {
            ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK,
            ANALYSIS_CLAIM_KIND_CONFLICT_RISK,
        }
    ]
    challenge_seed = _scrutineer_challenge_seed(
        proposed_answer_claim=proposed_answer_claim,
        adjacent_context_candidate_refs=adjacent_refs,
        excluded_scope_candidate_refs=excluded_refs,
        unreadable_high_value_candidate_refs=unreadable_refs,
        caveat_refs=caveat_refs,
        adjacent_claim_exclusion_refs=adjacent_exclusion_refs,
        conflict_or_overclaim_risk_refs=risk_refs,
    )
    base = _without_empty(
        {
            "schema_version": ANALYST_FINDING_PROPOSAL_SCHEMA_VERSION,
            "phase": ANALYST_FINDING_PROPOSAL_PHASE,
            "finding_kind": "analyst_finding_proposal",
            "finding_status": finding_status,
            "component_answer_type_binding_ref": binding_ref,
            "candidate_triage_summary_ref": triage_summary_ref,
            "selected_answer_bearing_candidate_refs": selected_refs,
            "adjacent_context_candidate_refs": adjacent_refs,
            "excluded_scope_candidate_refs": excluded_refs,
            "unreadable_high_value_candidate_refs": unreadable_refs,
            "analysis_gap_search_proposal_ref": _gap_proposal_ref(gap),
            "proposed_answer_claim": proposed_answer_claim,
            "proposed_answer_claim_ref": _proposed_answer_claim_ref(
                proposed_answer_claim
            ),
            "analysis_body": {
                "analysis_summary": analysis_summary,
                "analysis_steps": _analysis_steps(finding_status),
                "analysis_claim_refs": [
                    _analysis_claim_ref(item) for item in analysis_claims
                ],
                "caveat_refs": caveat_refs,
                "adjacent_claim_exclusion_refs": adjacent_exclusion_refs,
                "unresolved_gap_refs": unresolved_gap_refs,
                "conflict_or_overclaim_risk_refs": risk_refs,
                "support_map_ref": source_support_map_ref,
                "source_grounding_required": True,
                "dprime_validation_required": True,
                "scrutineer_validation_later": True,
            },
            "analysis_summary_ref": analysis_summary_ref,
            "analysis_claims": analysis_claims,
            "analysis_claim_refs": [
                _analysis_claim_ref(item) for item in analysis_claims
            ],
            "caveat_refs": caveat_refs,
            "adjacent_claim_exclusion_refs": adjacent_exclusion_refs,
            "unresolved_gap_refs": unresolved_gap_refs,
            "conflict_or_overclaim_risk_refs": risk_refs,
            "source_support_map": source_support_map,
            "source_support_map_ref": source_support_map_ref,
            "dprime_handoff_refs": _dprime_handoff_refs(
                analyst_finding_proposal_ref={},
                proposed_answer_claim_ref=_proposed_answer_claim_ref(
                    proposed_answer_claim
                ),
                analysis_claim_refs=[
                    _analysis_claim_ref(item) for item in analysis_claims
                ],
                analysis_summary_ref=analysis_summary_ref,
                source_support_map_ref=source_support_map_ref,
                caveat_refs=caveat_refs,
                adjacent_claim_exclusion_refs=adjacent_exclusion_refs,
                unresolved_gap_refs=unresolved_gap_refs,
                candidate_triage_summary_ref=triage_summary_ref,
                selected_answer_bearing_candidate_refs=selected_refs,
                adjacent_context_candidate_refs=adjacent_refs,
                excluded_scope_candidate_refs=excluded_refs,
                unreadable_high_value_candidate_refs=unreadable_refs,
            ),
            "scrutineer_challenge_seed": challenge_seed,
            "scrutineer_challenge_seed_ref": _scrutineer_challenge_seed_ref(
                challenge_seed
            ),
            "model_assisted_analysis_run": False,
            "model_adapter_kind": "deterministic_grounded_builder",
            "live_model_call_run": False,
            "safe_model_input_packet_ref": {},
            "model_output_validation_ref": {},
            "requires_dprime_validation": True,
            "requires_runkernel_admission": True,
            "source_grounding_required": True,
            "dprime_validation_required": True,
            "scrutineer_validation_later": True,
            **_non_authority_posture(),
        }
    )
    for list_key, list_value in (
        ("selected_answer_bearing_candidate_refs", selected_refs),
        ("adjacent_context_candidate_refs", adjacent_refs),
        ("excluded_scope_candidate_refs", excluded_refs),
        ("unreadable_high_value_candidate_refs", unreadable_refs),
        ("analysis_claim_refs", [_analysis_claim_ref(item) for item in analysis_claims]),
        ("caveat_refs", caveat_refs),
        ("adjacent_claim_exclusion_refs", adjacent_exclusion_refs),
        ("unresolved_gap_refs", unresolved_gap_refs),
        ("conflict_or_overclaim_risk_refs", risk_refs),
    ):
        base[list_key] = list(list_value)
    digest = _digest_json(base)
    proposal = {
        **base,
        "finding_id": f"analyst-finding-proposal:{digest[:20]}",
        "finding_digest": digest,
    }
    proposal["dprime_handoff_refs"] = _dprime_handoff_refs(
        analyst_finding_proposal_ref=analyst_finding_proposal_ref(proposal),
        proposed_answer_claim_ref=_proposed_answer_claim_ref(proposed_answer_claim),
        analysis_claim_refs=[_analysis_claim_ref(item) for item in analysis_claims],
        analysis_summary_ref=analysis_summary_ref,
        source_support_map_ref=source_support_map_ref,
        caveat_refs=caveat_refs,
        adjacent_claim_exclusion_refs=adjacent_exclusion_refs,
        unresolved_gap_refs=unresolved_gap_refs,
        candidate_triage_summary_ref=triage_summary_ref,
        selected_answer_bearing_candidate_refs=selected_refs,
        adjacent_context_candidate_refs=adjacent_refs,
        excluded_scope_candidate_refs=excluded_refs,
        unreadable_high_value_candidate_refs=unreadable_refs,
    )
    proposal["finding_digest"] = _digest_json(_without_digest(proposal))
    return validate_analyst_finding_proposal(proposal)


def build_analyst_finding_safe_model_input_packet(
    *,
    triage_packet: Mapping[str, Any],
    analysis_gap_search_proposal: Mapping[str, Any],
) -> dict[str, Any]:
    """Return safe retained refs for a future model-assisted Analyst call."""

    triage = _safe_mapping(triage_packet)
    gap = _safe_mapping(analysis_gap_search_proposal)
    packet = _without_empty(
        {
            "schema_version": ANALYST_SAFE_MODEL_INPUT_PACKET_SCHEMA_VERSION,
            "phase": ANALYST_FINDING_PROPOSAL_PHASE,
            "packet_kind": "AnalystFindingSafeModelInputPacket",
            "component_answer_type_binding_ref": _safe_mapping(
                triage.get("component_answer_type_binding_ref")
            ),
            "candidate_triage_summary_ref": _safe_mapping(
                triage.get("candidate_triage_summary_ref")
            ),
            "selected_answer_bearing_candidate_refs": _safe_refs(
                triage.get("selected_answer_bearing_candidate_refs")
            ),
            "adjacent_context_candidate_refs": _safe_refs(
                triage.get("adjacent_context_candidate_refs")
            ),
            "excluded_scope_candidate_refs": _safe_refs(
                triage.get("excluded_scope_candidate_refs")
            ),
            "unreadable_high_value_candidate_refs": _safe_refs(
                triage.get("unreadable_high_value_candidate_refs")
            ),
            "analysis_gap_search_proposal_ref": _gap_proposal_ref(gap),
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "live_model_call_run": False,
            **_non_authority_posture(),
        }
    )
    for list_key in (
        "selected_answer_bearing_candidate_refs",
        "adjacent_context_candidate_refs",
        "excluded_scope_candidate_refs",
        "unreadable_high_value_candidate_refs",
    ):
        packet.setdefault(list_key, [])
    _reject_forbidden_or_authority(packet, context="Analyst safe model input packet")
    digest = _digest_json(packet)
    return {
        **packet,
        "safe_model_input_packet_id": f"analyst-finding-model-input:{digest[:20]}",
        "safe_model_input_packet_digest": digest,
    }


def build_fake_model_assisted_analyst_finding_proposal(
    *,
    triage_packet: Mapping[str, Any],
    analysis_gap_search_proposal: Mapping[str, Any],
    fake_model_adapter: FakeAnalystFindingAdapter,
) -> dict[str, Any]:
    """Validate structured fake-adapter output into the proposal contract."""

    input_packet = build_analyst_finding_safe_model_input_packet(
        triage_packet=triage_packet,
        analysis_gap_search_proposal=analysis_gap_search_proposal,
    )
    structured_output = fake_model_adapter(input_packet)
    return validate_fake_model_assisted_analyst_output(
        safe_model_input_packet=input_packet,
        structured_output=structured_output,
    )


def validate_fake_model_assisted_analyst_output(
    *,
    safe_model_input_packet: Mapping[str, Any],
    structured_output: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate fake model output without retaining raw prompts or responses."""

    input_packet = _safe_mapping(safe_model_input_packet)
    if (
        input_packet.get("schema_version")
        != ANALYST_SAFE_MODEL_INPUT_PACKET_SCHEMA_VERSION
    ):
        raise AnalystFindingProposalError("safe model input packet schema mismatch")
    output = _safe_mapping(structured_output)
    proposal = _safe_mapping(output.get("analyst_finding_proposal")) or output
    _reject_forbidden_or_authority(
        output,
        context="Analyst fake model structured output",
    )
    validation_ref = _model_output_validation_ref(
        input_packet=input_packet,
        adapter_kind=MODEL_ADAPTER_KIND_FAKE_TEST,
    )
    proposal = {
        **proposal,
        "model_assisted_analysis_run": True,
        "model_adapter_kind": MODEL_ADAPTER_KIND_FAKE_TEST,
        "live_model_call_run": False,
        "safe_model_input_packet_ref": _safe_model_input_packet_ref(input_packet),
        "model_output_validation_ref": validation_ref,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
    }
    proposal["finding_digest"] = _digest_json(_without_digest(proposal))
    return validate_analyst_finding_proposal(proposal)


def validate_analyst_finding_proposal(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate grounding, custody, and non-authority posture."""

    proposal = _safe_mapping(value)
    _reject_forbidden_or_authority(proposal, context="Analyst finding proposal")
    if proposal.get("schema_version") != ANALYST_FINDING_PROPOSAL_SCHEMA_VERSION:
        raise AnalystFindingProposalError("AnalystFindingProposal schema mismatch")
    if not _safe_mapping(proposal.get("component_answer_type_binding_ref")):
        raise AnalystFindingProposalError(
            "AnalystFindingProposal requires component answer-type binding ref"
        )
    finding_status = _clean_text(proposal.get("finding_status"), limit=120)
    if finding_status not in {
        FINDING_STATUS_SOURCE_GROUNDED_PROPOSED,
        FINDING_STATUS_INSUFFICIENT_EVIDENCE,
        FINDING_STATUS_FOLLOWUP_REQUIRED,
    }:
        raise AnalystFindingProposalError("AnalystFindingProposal status invalid")
    selected_refs = _safe_refs(proposal.get("selected_answer_bearing_candidate_refs"))
    proposed_answer = _safe_mapping(proposal.get("proposed_answer_claim"))
    if proposed_answer and not selected_refs:
        raise AnalystFindingProposalError(
            "proposed answer claim requires answer-bearing candidate refs"
        )
    if selected_refs and not proposed_answer:
        raise AnalystFindingProposalError(
            "answer-bearing evidence requires proposed answer claim"
        )
    if proposed_answer:
        _validate_proposed_answer_claim(proposed_answer, selected_refs=selected_refs)
    analysis_body = _safe_mapping(proposal.get("analysis_body"))
    if not analysis_body:
        raise AnalystFindingProposalError("analysis body missing")
    for key in (
        "analysis_summary",
        "analysis_steps",
        "analysis_claim_refs",
        "support_map_ref",
    ):
        if key not in analysis_body:
            raise AnalystFindingProposalError(f"analysis body requires {key}")
    analysis_claims = [_safe_mapping(item) for item in _safe_sequence(proposal.get("analysis_claims"))]
    if not analysis_claims:
        raise AnalystFindingProposalError("analysis claims missing")
    for claim in analysis_claims:
        _validate_analysis_claim(claim)
    support_map = _safe_mapping(proposal.get("source_support_map"))
    if support_map.get("schema_version") != ANALYST_SOURCE_SUPPORT_MAP_SCHEMA_VERSION:
        raise AnalystFindingProposalError("source support map schema mismatch")
    if not _safe_sequence(support_map.get("analysis_claim_support_edges")):
        raise AnalystFindingProposalError("source support map requires support edges")
    handoff = _safe_mapping(proposal.get("dprime_handoff_refs"))
    for key in (
        "analyst_finding_proposal_ref",
        "analysis_claim_refs",
        "source_support_map_ref",
        "candidate_triage_summary_ref",
    ):
        if key not in handoff:
            raise AnalystFindingProposalError(f"D-prime handoff missing {key}")
    if proposed_answer and not _safe_mapping(handoff.get("proposed_answer_claim_ref")):
        raise AnalystFindingProposalError("D-prime handoff missing answer claim ref")
    if (
        proposal.get("model_assisted_analysis_run") is True
        and proposal.get("model_adapter_kind") != MODEL_ADAPTER_KIND_FAKE_TEST
    ):
        raise AnalystFindingProposalError(
            "this phase only permits fake model-assisted Analyst output"
        )
    if proposal.get("live_model_call_run") is not False:
        raise AnalystFindingProposalError("Analyst proposal must not run live model")
    _validate_non_authority_flags(proposal, "AnalystFindingProposal")
    normalized = _json_safe(proposal)
    normalized["finding_digest"] = _digest_json(_without_digest(normalized))
    normalized.setdefault(
        "finding_id",
        f"analyst-finding-proposal:{normalized['finding_digest'][:20]}",
    )
    return normalized


def analyst_finding_proposal_ref(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return compact safe ref for Workbench, D-prime, and reports."""

    proposal = _safe_mapping(value)
    if not proposal:
        return {}
    return _without_empty(
        {
            "schema_version": proposal.get("schema_version"),
            "phase": proposal.get("phase"),
            "finding_id": proposal.get("finding_id"),
            "finding_digest": proposal.get("finding_digest"),
            "finding_kind": proposal.get("finding_kind"),
            "finding_status": proposal.get("finding_status"),
            "proposed_answer_claim_ref": _safe_mapping(
                proposal.get("proposed_answer_claim_ref")
            ),
            "analysis_summary_ref": _safe_mapping(
                proposal.get("analysis_summary_ref")
            ),
            "analysis_claim_refs": _safe_refs(proposal.get("analysis_claim_refs")),
            "source_support_map_ref": _safe_mapping(
                proposal.get("source_support_map_ref")
            ),
            "scrutineer_challenge_seed_ref": _safe_mapping(
                proposal.get("scrutineer_challenge_seed_ref")
            ),
            "requires_dprime_validation": True,
            "requires_runkernel_admission": True,
            "evidence_admitted": False,
            "source_obligation_satisfied": False,
            "citation_eligibility_created": False,
            "final_answer_packet_created": False,
            "author_output_created": False,
            "product_correctness_claimed": False,
        }
    )


def _proposed_answer_claim(
    *,
    component_answer_type_binding_ref: Mapping[str, Any],
    selected_answer_bearing_candidate_refs: Sequence[Mapping[str, Any]],
    bounded_content_refs: Sequence[Mapping[str, Any]],
    source_support_map_ref: Mapping[str, Any],
) -> dict[str, Any]:
    if not selected_answer_bearing_candidate_refs:
        return {}
    binding = _safe_mapping(component_answer_type_binding_ref)
    text = (
        _clean_text(binding.get("claim_under_test"), limit=700)
        or "Proposed answer claim remains under test."
    )
    base = _without_empty(
        {
            "proposed_answer_claim_id": _stable_id(
                "proposed-answer-claim",
                [text, selected_answer_bearing_candidate_refs],
            ),
            "proposed_answer_claim_text": text,
            "requested_answer_type": binding.get("requested_answer_type"),
            "expected_value_shape": binding.get("expected_value_shape"),
            "claim_under_test": binding.get("claim_under_test"),
            "answer_value_candidate": _safe_answer_value_candidate(
                selected_answer_bearing_candidate_refs
            ),
            "answer_value_shape": binding.get("expected_value_shape"),
            "selected_answer_bearing_candidate_refs": [
                _safe_mapping(item) for item in selected_answer_bearing_candidate_refs
            ],
            "source_support_map_ref": _safe_mapping(source_support_map_ref),
            "requires_dprime_validation": True,
            "requires_runkernel_admission": True,
            **_non_authority_posture(),
        }
    )
    base["proposed_answer_claim_digest"] = _digest_json(base)
    return base


def _analysis_claims(
    *,
    component_answer_type_binding_ref: Mapping[str, Any],
    proposed_answer_claim: Mapping[str, Any],
    selected_answer_bearing_candidate_refs: Sequence[Mapping[str, Any]],
    adjacent_context_candidate_refs: Sequence[Mapping[str, Any]],
    excluded_scope_candidate_refs: Sequence[Mapping[str, Any]],
    unreadable_high_value_candidate_refs: Sequence[Mapping[str, Any]],
    overclaim_risk_candidate_refs: Sequence[Mapping[str, Any]],
    bounded_content_refs: Sequence[Mapping[str, Any]],
    source_support_map_ref: Mapping[str, Any],
    gap_proposal: Mapping[str, Any],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if proposed_answer_claim:
        claims.append(
            _analysis_claim(
                kind=ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER,
                text=_clean_text(
                    proposed_answer_claim.get("proposed_answer_claim_text"),
                    limit=700,
                )
                or "Proposed answer claim under test.",
                component_answer_type_binding_ref=component_answer_type_binding_ref,
                supporting_candidate_refs=selected_answer_bearing_candidate_refs,
                supporting_source_excerpt_refs=bounded_content_refs,
                adjacent_or_excluded_candidate_refs=(),
                support_status=SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED,
                unsupported=False,
                source_support_map_ref=source_support_map_ref,
            )
        )
        claims.append(
            _analysis_claim(
                kind=ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION,
                text=(
                    "Selected candidate refs are proposed as matching the "
                    "requested answer type and expected value shape."
                ),
                component_answer_type_binding_ref=component_answer_type_binding_ref,
                supporting_candidate_refs=selected_answer_bearing_candidate_refs,
                supporting_source_excerpt_refs=bounded_content_refs,
                adjacent_or_excluded_candidate_refs=(),
                support_status=SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED,
                unsupported=False,
                source_support_map_ref=source_support_map_ref,
            )
        )
    if adjacent_context_candidate_refs:
        claims.append(
            _analysis_claim(
                kind=ANALYSIS_CLAIM_KIND_CAVEAT,
                text=(
                    "Adjacent context candidates are preserved for caveat review "
                    "but do not satisfy the requested answer type."
                ),
                component_answer_type_binding_ref=component_answer_type_binding_ref,
                supporting_candidate_refs=(),
                supporting_source_excerpt_refs=(),
                adjacent_or_excluded_candidate_refs=adjacent_context_candidate_refs,
                support_status=SUPPORT_STATUS_ADJACENT_ONLY,
                unsupported=False,
                requires_scrutineer=True,
                source_support_map_ref=source_support_map_ref,
            )
        )
    if excluded_scope_candidate_refs:
        claims.append(
            _analysis_claim(
                kind=ANALYSIS_CLAIM_KIND_EXCLUSION,
                text=(
                    "Excluded-scope candidate refs are not allowed to satisfy "
                    "the proposed answer claim."
                ),
                component_answer_type_binding_ref=component_answer_type_binding_ref,
                supporting_candidate_refs=(),
                supporting_source_excerpt_refs=(),
                adjacent_or_excluded_candidate_refs=excluded_scope_candidate_refs,
                support_status=SUPPORT_STATUS_ADJACENT_ONLY,
                unsupported=False,
                requires_scrutineer=True,
                source_support_map_ref=source_support_map_ref,
            )
        )
    if unreadable_high_value_candidate_refs:
        claims.append(
            _analysis_claim(
                kind=ANALYSIS_CLAIM_KIND_GAP,
                text=(
                    "Unreadable high-value candidate refs remain a read-support "
                    "gap before answer authority can open."
                ),
                component_answer_type_binding_ref=component_answer_type_binding_ref,
                supporting_candidate_refs=(),
                supporting_source_excerpt_refs=(),
                adjacent_or_excluded_candidate_refs=unreadable_high_value_candidate_refs,
                support_status=SUPPORT_STATUS_UNREADABLE_SOURCE_NEEDED,
                unsupported=True,
                requires_scrutineer=True,
                source_support_map_ref=source_support_map_ref,
            )
        )
    if overclaim_risk_candidate_refs:
        claims.append(
            _analysis_claim(
                kind=ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK,
                text=(
                    "Overclaim-risk candidate refs require downstream validation "
                    "before any broader answer can be admitted."
                ),
                component_answer_type_binding_ref=component_answer_type_binding_ref,
                supporting_candidate_refs=(),
                supporting_source_excerpt_refs=(),
                adjacent_or_excluded_candidate_refs=overclaim_risk_candidate_refs,
                support_status=SUPPORT_STATUS_CONFLICT_OR_OVERCLAIM_RISK,
                unsupported=True,
                requires_scrutineer=True,
                source_support_map_ref=source_support_map_ref,
            )
        )
    if not claims:
        gap_kind = _clean_text(gap_proposal.get("gap_kind"), limit=160)
        claims.append(
            _analysis_claim(
                kind=ANALYSIS_CLAIM_KIND_GAP,
                text=(
                    "No answer-bearing candidate ref is available; Analyst "
                    f"finding remains {gap_kind or 'insufficient_evidence'}."
                ),
                component_answer_type_binding_ref=component_answer_type_binding_ref,
                supporting_candidate_refs=(),
                supporting_source_excerpt_refs=(),
                adjacent_or_excluded_candidate_refs=(),
                support_status=SUPPORT_STATUS_INSUFFICIENT_EVIDENCE,
                unsupported=True,
                requires_scrutineer=True,
                source_support_map_ref=source_support_map_ref,
            )
        )
    return claims


def _analysis_claim(
    *,
    kind: str,
    text: str,
    component_answer_type_binding_ref: Mapping[str, Any],
    supporting_candidate_refs: Sequence[Mapping[str, Any]],
    supporting_source_excerpt_refs: Sequence[Mapping[str, Any]],
    adjacent_or_excluded_candidate_refs: Sequence[Mapping[str, Any]],
    support_status: str,
    unsupported: bool,
    source_support_map_ref: Mapping[str, Any],
    requires_scrutineer: bool = False,
) -> dict[str, Any]:
    base = _without_empty(
        {
            "analysis_claim_kind": kind,
            "analysis_claim_text": _clean_text(text, limit=700),
            "related_component_answer_type_binding_ref": _safe_mapping(
                component_answer_type_binding_ref
            ),
            "supporting_candidate_refs": [
                _safe_mapping(item) for item in supporting_candidate_refs
            ],
            "supporting_source_excerpt_refs": [
                _safe_mapping(item) for item in supporting_source_excerpt_refs
            ],
            "bounded_content_refs": [
                _safe_mapping(item) for item in supporting_source_excerpt_refs
            ],
            "adjacent_or_excluded_candidate_refs": [
                _safe_mapping(item) for item in adjacent_or_excluded_candidate_refs
            ],
            "unsupported_if_any": bool(unsupported),
            "support_status_proposed": support_status,
            "source_support_map_ref": _safe_mapping(source_support_map_ref),
            "requires_dprime_validation": True,
            "requires_scrutineer_validation": bool(requires_scrutineer),
            **_non_authority_posture(),
        }
    )
    base["analysis_claim_id"] = _stable_id(
        "analysis-claim",
        [kind, text, supporting_candidate_refs, adjacent_or_excluded_candidate_refs],
    )
    base["analysis_claim_digest"] = _digest_json(base)
    return base


def _source_support_map(
    *,
    component_answer_type_binding_ref: Mapping[str, Any],
    candidate_triage_summary_ref: Mapping[str, Any],
    selected_answer_bearing_candidate_refs: Sequence[Mapping[str, Any]],
    adjacent_context_candidate_refs: Sequence[Mapping[str, Any]],
    excluded_scope_candidate_refs: Sequence[Mapping[str, Any]],
    unreadable_high_value_candidate_refs: Sequence[Mapping[str, Any]],
    bounded_content_refs: Sequence[Mapping[str, Any]],
    proposed_answer_claim_ref: Mapping[str, Any],
    analysis_claim_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    base = _without_empty(
        {
            "schema_version": ANALYST_SOURCE_SUPPORT_MAP_SCHEMA_VERSION,
            "phase": ANALYST_FINDING_PROPOSAL_PHASE,
            "map_kind": "AnalystSourceSupportMap",
            "component_answer_type_binding_ref": _safe_mapping(
                component_answer_type_binding_ref
            ),
            "candidate_triage_summary_ref": _safe_mapping(candidate_triage_summary_ref),
            "source_refs": [dict(item) for item in bounded_content_refs],
            "bounded_content_refs": [dict(item) for item in bounded_content_refs],
            "selected_answer_bearing_candidate_refs": [
                _safe_mapping(item) for item in selected_answer_bearing_candidate_refs
            ],
            "adjacent_context_candidate_refs": [
                _safe_mapping(item) for item in adjacent_context_candidate_refs
            ],
            "excluded_scope_candidate_refs": [
                _safe_mapping(item) for item in excluded_scope_candidate_refs
            ],
            "unreadable_high_value_candidate_refs": [
                _safe_mapping(item) for item in unreadable_high_value_candidate_refs
            ],
            "proposed_answer_claim_ref": _safe_mapping(proposed_answer_claim_ref),
            "analysis_claim_refs": [_safe_mapping(item) for item in analysis_claim_refs],
            "analysis_claim_support_edges": _support_edges(
                analysis_claim_refs=analysis_claim_refs,
                selected_answer_bearing_candidate_refs=(
                    selected_answer_bearing_candidate_refs
                ),
                adjacent_context_candidate_refs=adjacent_context_candidate_refs,
                excluded_scope_candidate_refs=excluded_scope_candidate_refs,
                unreadable_high_value_candidate_refs=unreadable_high_value_candidate_refs,
            ),
            "unsupported_gap_refs": [
                _safe_mapping(item) for item in unreadable_high_value_candidate_refs
            ],
            "candidate_role_legend": {
                "source_grounded_answer_support": (
                    "candidate proposed to support an analysis claim"
                ),
                "adjacent_context": (
                    "candidate preserved as caveat/context, not answer support"
                ),
                "excluded_scope": (
                    "candidate excluded from satisfying requested answer type"
                ),
                "unreadable_high_value": (
                    "candidate may matter but needs readable support"
                ),
            },
            "safe_to_forward_to_dprime": True,
            **_non_authority_posture(),
        }
    )
    digest = _digest_json(base)
    return {
        **base,
        "source_support_map_id": f"analyst-source-support-map:{digest[:20]}",
        "source_support_map_digest": digest,
    }


def _support_edges(
    *,
    analysis_claim_refs: Sequence[Mapping[str, Any]],
    selected_answer_bearing_candidate_refs: Sequence[Mapping[str, Any]],
    adjacent_context_candidate_refs: Sequence[Mapping[str, Any]],
    excluded_scope_candidate_refs: Sequence[Mapping[str, Any]],
    unreadable_high_value_candidate_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    proposed_answer_claim_ids = [
        _safe_mapping(item).get("analysis_claim_id")
        for item in analysis_claim_refs
        if _safe_mapping(item).get("analysis_claim_kind")
        in {
            ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER,
            ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION,
        }
    ]
    for claim_id in proposed_answer_claim_ids or ["proposed_answer_claim"]:
        for candidate_ref in selected_answer_bearing_candidate_refs:
            edges.append(
                {
                    "edge_kind": "candidate_supports_analysis_claim",
                    "analysis_claim_id": claim_id,
                    "candidate_ref": _safe_mapping(candidate_ref),
                    "candidate_triage_role": "answer_bearing",
                    "support_status_proposed": (
                        SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED
                    ),
                }
            )
    for candidate_ref in adjacent_context_candidate_refs:
        edges.append(
            {
                "edge_kind": "candidate_is_adjacent_context",
                "candidate_ref": _safe_mapping(candidate_ref),
                "candidate_triage_role": "adjacent_context",
                "support_status_proposed": SUPPORT_STATUS_ADJACENT_ONLY,
            }
        )
    for candidate_ref in excluded_scope_candidate_refs:
        edges.append(
            {
                "edge_kind": "candidate_is_excluded_scope",
                "candidate_ref": _safe_mapping(candidate_ref),
                "candidate_triage_role": "excluded_scope",
                "support_status_proposed": SUPPORT_STATUS_ADJACENT_ONLY,
            }
        )
    for candidate_ref in unreadable_high_value_candidate_refs:
        edges.append(
            {
                "edge_kind": "candidate_is_unreadable_gap",
                "candidate_ref": _safe_mapping(candidate_ref),
                "candidate_triage_role": "unreadable_high_value",
                "support_status_proposed": SUPPORT_STATUS_UNREADABLE_SOURCE_NEEDED,
            }
        )
    if not edges:
        edges.append(
            {
                "edge_kind": "unsupported_analysis_gap",
                "support_status_proposed": SUPPORT_STATUS_INSUFFICIENT_EVIDENCE,
            }
        )
    return edges


def _scrutineer_challenge_seed(
    *,
    proposed_answer_claim: Mapping[str, Any],
    adjacent_context_candidate_refs: Sequence[Mapping[str, Any]],
    excluded_scope_candidate_refs: Sequence[Mapping[str, Any]],
    unreadable_high_value_candidate_refs: Sequence[Mapping[str, Any]],
    caveat_refs: Sequence[Mapping[str, Any]],
    adjacent_claim_exclusion_refs: Sequence[Mapping[str, Any]],
    conflict_or_overclaim_risk_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    targets: list[dict[str, Any]] = []
    if proposed_answer_claim and not _safe_mapping(proposed_answer_claim).get(
        "answer_value_candidate"
    ):
        targets.append(
            {
                "challenge_kind": "weak_value_shape_match",
                "target_ref": _proposed_answer_claim_ref(proposed_answer_claim),
            }
        )
    if adjacent_context_candidate_refs or excluded_scope_candidate_refs:
        targets.append(
            {
                "challenge_kind": "adjacent_or_excluded_scope",
                "candidate_refs": [
                    *[_safe_mapping(item) for item in adjacent_context_candidate_refs],
                    *[_safe_mapping(item) for item in excluded_scope_candidate_refs],
                ],
            }
        )
    if unreadable_high_value_candidate_refs:
        targets.append(
            {
                "challenge_kind": "unreadable_high_value_source",
                "candidate_refs": [
                    _safe_mapping(item) for item in unreadable_high_value_candidate_refs
                ],
            }
        )
    if caveat_refs or adjacent_claim_exclusion_refs:
        targets.append(
            {
                "challenge_kind": "caveat_or_exclusion_validation",
                "caveat_refs": [_safe_mapping(item) for item in caveat_refs],
                "adjacent_claim_exclusion_refs": [
                    _safe_mapping(item) for item in adjacent_claim_exclusion_refs
                ],
            }
        )
    if conflict_or_overclaim_risk_refs:
        targets.append(
            {
                "challenge_kind": "conflict_or_overclaim_risk",
                "risk_refs": [
                    _safe_mapping(item) for item in conflict_or_overclaim_risk_refs
                ],
            }
        )
    if not targets:
        return {}
    base = {
        "schema_version": "analyst_scrutineer_challenge_seed_v1",
        "phase": ANALYST_FINDING_PROPOSAL_PHASE,
        "seed_kind": "ScrutineerChallengeSeed",
        "challenge_targets": targets,
        "scrutineer_lane_placeholder": True,
        "scrutineer_validation_run": False,
        "scrutineer_admission_created": False,
        **_non_authority_posture(),
    }
    digest = _digest_json(base)
    return {
        **base,
        "scrutineer_challenge_seed_id": (
            f"scrutineer-challenge-seed:{digest[:20]}"
        ),
        "scrutineer_challenge_seed_digest": digest,
    }


def _dprime_handoff_refs(
    *,
    analyst_finding_proposal_ref: Mapping[str, Any],
    proposed_answer_claim_ref: Mapping[str, Any],
    analysis_claim_refs: Sequence[Mapping[str, Any]],
    analysis_summary_ref: Mapping[str, Any],
    source_support_map_ref: Mapping[str, Any],
    caveat_refs: Sequence[Mapping[str, Any]],
    adjacent_claim_exclusion_refs: Sequence[Mapping[str, Any]],
    unresolved_gap_refs: Sequence[Mapping[str, Any]],
    candidate_triage_summary_ref: Mapping[str, Any],
    selected_answer_bearing_candidate_refs: Sequence[Mapping[str, Any]],
    adjacent_context_candidate_refs: Sequence[Mapping[str, Any]],
    excluded_scope_candidate_refs: Sequence[Mapping[str, Any]],
    unreadable_high_value_candidate_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return _without_empty(
        {
            "analyst_finding_proposal_ref": _safe_mapping(
                analyst_finding_proposal_ref
            ),
            "proposed_answer_claim_ref": _safe_mapping(proposed_answer_claim_ref),
            "analysis_claim_refs": [_safe_mapping(item) for item in analysis_claim_refs],
            "analysis_summary_ref": _safe_mapping(analysis_summary_ref),
            "source_support_map_ref": _safe_mapping(source_support_map_ref),
            "caveat_refs": [_safe_mapping(item) for item in caveat_refs],
            "adjacent_claim_exclusion_refs": [
                _safe_mapping(item) for item in adjacent_claim_exclusion_refs
            ],
            "unresolved_gap_refs": [_safe_mapping(item) for item in unresolved_gap_refs],
            "candidate_triage_summary_ref": _safe_mapping(candidate_triage_summary_ref),
            "selected_answer_bearing_candidate_refs": [
                _safe_mapping(item) for item in selected_answer_bearing_candidate_refs
            ],
            "adjacent_context_candidate_refs": [
                _safe_mapping(item) for item in adjacent_context_candidate_refs
            ],
            "excluded_scope_candidate_refs": [
                _safe_mapping(item) for item in excluded_scope_candidate_refs
            ],
            "unreadable_high_value_candidate_refs": [
                _safe_mapping(item) for item in unreadable_high_value_candidate_refs
            ],
            "dprime_validation_required": True,
            "dprime_validation_run": False,
            **_non_authority_posture(),
        }
    )


def _finding_status(
    *,
    selected_refs: Sequence[Mapping[str, Any]],
    gap_proposal: Mapping[str, Any],
) -> str:
    if selected_refs:
        return FINDING_STATUS_SOURCE_GROUNDED_PROPOSED
    if gap_proposal.get("live_followup_required") is True:
        return FINDING_STATUS_FOLLOWUP_REQUIRED
    return FINDING_STATUS_INSUFFICIENT_EVIDENCE


def _analysis_summary_text(
    *,
    finding_status: str,
    selected_refs: Sequence[Mapping[str, Any]],
    adjacent_refs: Sequence[Mapping[str, Any]],
    excluded_refs: Sequence[Mapping[str, Any]],
    unreadable_refs: Sequence[Mapping[str, Any]],
    overclaim_refs: Sequence[Mapping[str, Any]],
) -> str:
    if finding_status == FINDING_STATUS_SOURCE_GROUNDED_PROPOSED:
        lead = (
            "Answer-bearing candidate refs support a proposed claim for "
            "D-prime validation."
        )
    else:
        lead = (
            "No answer-bearing candidate refs support a proposed answer claim; "
            "the finding remains gap or follow-up posture."
        )
    return (
        f"{lead} Counts: answer_bearing={len(selected_refs)}, "
        f"adjacent={len(adjacent_refs)}, excluded={len(excluded_refs)}, "
        f"unreadable={len(unreadable_refs)}, overclaim_risk={len(overclaim_refs)}."
    )


def _analysis_steps(finding_status: str) -> list[str]:
    steps = [
        "Read component answer-type binding.",
        "Separate answer-bearing candidate refs from adjacent and excluded refs.",
        "Map candidate refs to proposed analysis claims.",
        "Preserve gaps and risks for D-prime and future Scrutineer review.",
    ]
    if finding_status != FINDING_STATUS_SOURCE_GROUNDED_PROPOSED:
        steps.append("Do not create a proposed answer claim without answer-bearing refs.")
    return steps


def _bounded_content_refs(
    fetch_read_content_packet: Mapping[str, Any],
    *,
    candidate_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    packet = _safe_mapping(fetch_read_content_packet)
    candidate_ids = {
        _clean_text(_safe_mapping(item).get("candidate_id"), limit=320)
        for item in candidate_refs
    }
    refs: list[dict[str, Any]] = []
    for raw in _safe_sequence(packet.get("reference_records")):
        ref = _safe_mapping(raw)
        if not ref or ref.get("candidate_id") not in candidate_ids:
            continue
        refs.append(
            _without_empty(
                {
                    "fetch_read_content_packet_id": packet.get("packet_id"),
                    "fetch_read_content_packet_digest": packet.get("packet_digest"),
                    "candidate_id": ref.get("candidate_id"),
                    "candidate_digest": ref.get("candidate_digest"),
                    "reference_id": ref.get("reference_id"),
                    "reference_digest": ref.get("reference_digest"),
                    "bounded_content_digest": ref.get("excerpt_digest"),
                    "bounded_character_count": ref.get("bounded_character_count"),
                    "fetch_read_status": ref.get("fetch_read_status"),
                    "bounded_content_text_retained": False,
                }
            )
        )
    return refs


def _safe_answer_value_candidate(
    candidate_refs: Sequence[Mapping[str, Any]],
) -> str | None:
    for ref in candidate_refs:
        value = _clean_text(_safe_mapping(ref).get("answer_value_candidate"), limit=120)
        if value and any(re.search(pattern, value) for pattern in _VALUE_PATTERNS):
            return value
    return None


def _validate_proposed_answer_claim(
    claim: Mapping[str, Any],
    *,
    selected_refs: Sequence[Mapping[str, Any]],
) -> None:
    for key in (
        "proposed_answer_claim_id",
        "proposed_answer_claim_text",
        "requested_answer_type",
        "expected_value_shape",
        "claim_under_test",
        "answer_value_shape",
        "selected_answer_bearing_candidate_refs",
        "source_support_map_ref",
    ):
        if key not in claim:
            raise AnalystFindingProposalError(f"proposed answer claim requires {key}")
    if not _safe_refs(claim.get("selected_answer_bearing_candidate_refs")):
        raise AnalystFindingProposalError("proposed answer claim requires support refs")
    selected_ids = _candidate_ids(selected_refs)
    claim_ids = _candidate_ids(_safe_refs(claim.get("selected_answer_bearing_candidate_refs")))
    if not claim_ids <= selected_ids:
        raise AnalystFindingProposalError(
            "proposed answer claim support must come from answer-bearing refs"
        )
    _validate_non_authority_flags(claim, "proposed answer claim")


def _validate_analysis_claim(claim: Mapping[str, Any]) -> None:
    kind = _clean_text(claim.get("analysis_claim_kind"), limit=120)
    status = _clean_text(claim.get("support_status_proposed"), limit=120)
    if kind not in _CLAIM_KINDS:
        raise AnalystFindingProposalError("analysis claim kind invalid")
    if status not in _SUPPORT_STATUSES:
        raise AnalystFindingProposalError("analysis claim support status invalid")
    for key in (
        "analysis_claim_id",
        "analysis_claim_text",
        "related_component_answer_type_binding_ref",
        "requires_dprime_validation",
    ):
        if key not in claim:
            raise AnalystFindingProposalError(f"analysis claim requires {key}")
    supporting_refs = _safe_refs(claim.get("supporting_candidate_refs"))
    bounded_refs = _safe_refs(claim.get("supporting_source_excerpt_refs")) or _safe_refs(
        claim.get("bounded_content_refs")
    )
    adjacent_refs = _safe_refs(claim.get("adjacent_or_excluded_candidate_refs"))
    unsupported = claim.get("unsupported_if_any") is True
    if kind in {
        ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER,
        ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION,
    }:
        if status != SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED:
            raise AnalystFindingProposalError(
                "answer/evidence interpretation claims must be source-grounded"
            )
        if not supporting_refs:
            raise AnalystFindingProposalError(
                "source-grounded claims require supporting candidate refs"
            )
        if unsupported:
            raise AnalystFindingProposalError(
                "source-grounded answer claims cannot be marked unsupported"
            )
    elif kind in {
        ANALYSIS_CLAIM_KIND_CAVEAT,
        ANALYSIS_CLAIM_KIND_EXCLUSION,
        ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK,
        ANALYSIS_CLAIM_KIND_CONFLICT_RISK,
    }:
        if not adjacent_refs:
            raise AnalystFindingProposalError(
                "caveat/exclusion/risk claims require adjacent or excluded refs"
            )
    elif kind == ANALYSIS_CLAIM_KIND_GAP and not unsupported:
        raise AnalystFindingProposalError("gap claims must be marked unsupported")
    if status == SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED and not (
        supporting_refs or bounded_refs
    ):
        raise AnalystFindingProposalError("source-grounded claim lacks support refs")
    _validate_non_authority_flags(claim, "analysis claim")


def _validate_non_authority_flags(value: Mapping[str, Any], context: str) -> None:
    for key, expected in _NON_AUTHORITY_FALSE_FLAGS.items():
        if value.get(key) is not expected:
            raise AnalystFindingProposalError(
                f"{context} authority flag must remain false: {key}"
            )
    flags = _safe_mapping(value.get("raw_private_retention_flags"))
    if flags != _RAW_FALSE_FLAGS:
        raise AnalystFindingProposalError(
            f"{context} raw/private retention flags invalid"
        )
    for key, expected in _RAW_FALSE_FLAGS.items():
        if value.get(key) is not expected:
            raise AnalystFindingProposalError(
                f"{context} raw/private flag must remain false: {key}"
            )


def _reject_forbidden_or_authority(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & _FORBIDDEN_KEYS)
    if forbidden:
        raise AnalystFindingProposalError(f"{context} includes forbidden material")
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise AnalystFindingProposalError(
            f"{context} attempts forbidden authority upgrade: "
            + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(normalized)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _proposed_answer_claim_ref(value: Mapping[str, Any] | None) -> dict[str, Any]:
    claim = _safe_mapping(value)
    if not claim:
        return {}
    return _without_empty(
        {
            "proposed_answer_claim_id": claim.get("proposed_answer_claim_id"),
            "proposed_answer_claim_digest": claim.get(
                "proposed_answer_claim_digest"
            ),
            "requested_answer_type": claim.get("requested_answer_type"),
            "expected_value_shape": claim.get("expected_value_shape"),
            "requires_dprime_validation": True,
            "requires_runkernel_admission": True,
            "evidence_admitted": False,
            "source_obligation_satisfied": False,
            "citation_eligibility_created": False,
            "final_answer_packet_created": False,
            "author_output_created": False,
            "product_correctness_claimed": False,
        }
    )


def _analysis_claim_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    claim = _safe_mapping(value)
    return _without_empty(
        {
            "analysis_claim_id": claim.get("analysis_claim_id"),
            "analysis_claim_digest": claim.get("analysis_claim_digest"),
            "analysis_claim_kind": claim.get("analysis_claim_kind"),
            "support_status_proposed": claim.get("support_status_proposed"),
            "requires_dprime_validation": True,
            "requires_scrutineer_validation": (
                claim.get("requires_scrutineer_validation") is True
            ),
            "evidence_admitted": False,
            "source_obligation_satisfied": False,
            "citation_eligibility_created": False,
            "final_answer_packet_created": False,
            "author_output_created": False,
            "product_correctness_claimed": False,
        }
    )


def _source_support_map_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    support_map = _safe_mapping(value)
    return _without_empty(
        {
            "schema_version": support_map.get("schema_version"),
            "source_support_map_id": support_map.get("source_support_map_id"),
            "source_support_map_digest": support_map.get("source_support_map_digest"),
            "safe_to_forward_to_dprime": (
                support_map.get("safe_to_forward_to_dprime") is True
            ),
            "evidence_admitted": False,
            "source_obligation_satisfied": False,
            "citation_eligibility_created": False,
            "final_answer_packet_created": False,
            "author_output_created": False,
            "product_correctness_claimed": False,
        }
    )


def _scrutineer_challenge_seed_ref(value: Mapping[str, Any] | None) -> dict[str, Any]:
    seed = _safe_mapping(value)
    if not seed:
        return {}
    return _without_empty(
        {
            "schema_version": seed.get("schema_version"),
            "scrutineer_challenge_seed_id": seed.get(
                "scrutineer_challenge_seed_id"
            ),
            "scrutineer_challenge_seed_digest": seed.get(
                "scrutineer_challenge_seed_digest"
            ),
            "challenge_target_count": len(_safe_sequence(seed.get("challenge_targets"))),
            "scrutineer_validation_run": False,
            "scrutineer_admission_created": False,
            "evidence_admitted": False,
            "source_obligation_satisfied": False,
            "citation_eligibility_created": False,
            "final_answer_packet_created": False,
            "author_output_created": False,
            "product_correctness_claimed": False,
        }
    )


def _summary_ref(text: str) -> dict[str, Any]:
    digest = _digest_json({"analysis_summary": text})
    return {
        "analysis_summary_id": f"analysis-summary:{digest[:20]}",
        "analysis_summary_digest": digest,
    }


def _gap_proposal_ref(gap: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "proposal_id": gap.get("proposal_id"),
            "proposal_digest": gap.get("proposal_digest"),
            "gap_status": gap.get("gap_status"),
            "gap_kind": gap.get("gap_kind"),
            "live_followup_required": gap.get("live_followup_required"),
            "live_followup_licensed": gap.get("live_followup_licensed"),
        }
    )


def _with_claim_support_map_ref(
    claim: Mapping[str, Any],
    source_support_map_ref: Mapping[str, Any],
) -> dict[str, Any]:
    out = {**_safe_mapping(claim), "source_support_map_ref": dict(source_support_map_ref)}
    out["analysis_claim_digest"] = _digest_json(_without_digest(out))
    return out


def _safe_model_input_packet_ref(input_packet: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(input_packet)
    return _without_empty(
        {
            "schema_version": safe.get("schema_version"),
            "safe_model_input_packet_id": safe.get("safe_model_input_packet_id"),
            "safe_model_input_packet_digest": safe.get(
                "safe_model_input_packet_digest"
            ),
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "live_model_call_run": False,
        }
    )


def _model_output_validation_ref(
    *,
    input_packet: Mapping[str, Any],
    adapter_kind: str,
) -> dict[str, Any]:
    base = {
        "schema_version": ANALYST_MODEL_OUTPUT_VALIDATION_SCHEMA_VERSION,
        "phase": ANALYST_FINDING_PROPOSAL_PHASE,
        "adapter_kind": adapter_kind,
        "safe_model_input_packet_digest": input_packet.get(
            "safe_model_input_packet_digest"
        ),
        "output_validated_into_analyst_finding_proposal": True,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "live_model_call_run": False,
    }
    digest = _digest_json(base)
    return {
        **base,
        "model_output_validation_id": (
            f"analyst-finding-model-output-validation:{digest[:20]}"
        ),
        "model_output_validation_digest": digest,
    }


def _non_authority_posture() -> dict[str, Any]:
    return {
        **_NON_AUTHORITY_TRUE_FLAGS,
        **_NON_AUTHORITY_FALSE_FLAGS,
        "raw_private_retention_flags": dict(_RAW_FALSE_FLAGS),
        **_RAW_FALSE_FLAGS,
    }


def _candidate_ids(refs: Sequence[Mapping[str, Any]]) -> set[str]:
    return {
        candidate_id
        for candidate_id in (
            _clean_text(_safe_mapping(item).get("candidate_id"), limit=320)
            for item in refs
        )
        if candidate_id
    }


def _safe_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if ref:
            refs.append(ref)
    return refs


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _stable_id(prefix: str, parts: Sequence[Any]) -> str:
    return f"{prefix}:{_digest_json(list(parts))[:20]}"


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {}, ())
    }


def _without_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key
        not in {
            "finding_digest",
            "proposed_answer_claim_digest",
            "analysis_claim_digest",
        }
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ANALYST_FINDING_PROPOSAL_SCHEMA_VERSION",
    "ANALYST_FINDING_PROPOSAL_PHASE",
    "ANALYST_MODEL_OUTPUT_VALIDATION_SCHEMA_VERSION",
    "ANALYST_SAFE_MODEL_INPUT_PACKET_SCHEMA_VERSION",
    "ANALYST_SOURCE_SUPPORT_MAP_SCHEMA_VERSION",
    "ANALYSIS_CLAIM_KIND_CAVEAT",
    "ANALYSIS_CLAIM_KIND_CONFLICT_RISK",
    "ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION",
    "ANALYSIS_CLAIM_KIND_EXCLUSION",
    "ANALYSIS_CLAIM_KIND_GAP",
    "ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK",
    "ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER",
    "AnalystFindingProposalError",
    "FINDING_STATUS_FOLLOWUP_REQUIRED",
    "FINDING_STATUS_INSUFFICIENT_EVIDENCE",
    "FINDING_STATUS_SOURCE_GROUNDED_PROPOSED",
    "MODEL_ADAPTER_KIND_FAKE_TEST",
    "SUPPORT_STATUS_ADJACENT_ONLY",
    "SUPPORT_STATUS_CONFLICT_OR_OVERCLAIM_RISK",
    "SUPPORT_STATUS_INSUFFICIENT_EVIDENCE",
    "SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED",
    "SUPPORT_STATUS_UNREADABLE_SOURCE_NEEDED",
    "analyst_finding_proposal_ref",
    "build_analyst_finding_safe_model_input_packet",
    "build_deterministic_analyst_finding_proposal",
    "build_fake_model_assisted_analyst_finding_proposal",
    "validate_analyst_finding_proposal",
    "validate_fake_model_assisted_analyst_output",
]
