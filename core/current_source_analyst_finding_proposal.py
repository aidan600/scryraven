"""Source-grounded Analyst finding proposal contract for current-source runs.

The proposal records analysis custody over already-triaged candidate refs. It is
not evidence, not a citation, not answer authority, and not product correctness.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from core.fetch_read_content_reference import FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS

ANALYST_FINDING_PROPOSAL_SCHEMA_VERSION = "analyst_finding_proposal_v1"
ANALYST_SOURCE_SUPPORT_MAP_SCHEMA_VERSION = "analyst_source_support_map_v1"
ANALYST_SAFE_MODEL_INPUT_PACKET_SCHEMA_VERSION = (
    "analyst_finding_safe_model_input_packet_v1"
)
ANALYST_MODEL_OUTPUT_VALIDATION_SCHEMA_VERSION = (
    "analyst_finding_model_output_validation_v1"
)
ANALYST_FINDING_MODEL_ROUTE_SCHEMA_VERSION = "analyst_finding_model_route_v1"
ANALYST_FINDING_PROPOSAL_PHASE = (
    "CURRENT-SOURCE-ANALYST-FINDING-CONTRACT-CUSTODY-V1-01"
)
ANALYST_FINDING_PROMPT_SCHEMA_VERSION = "analyst_finding_prompt_v1"

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
MODEL_ADAPTER_KIND_REAL_SMART = "real_smart_model_route"
MODEL_ADAPTER_KIND_DETERMINISTIC = "deterministic_grounded_builder"
ANALYST_MODEL_ROLE_SMART = "smart"
ANALYST_ROLE_SURFACE = "analyst_finding_proposal"
ANALYST_RUNTIME_CONSUMER = "AnalystWorkbench / AnalystFindingProposal"
ANALYST_ROUTE_AUTHORITY = "licensed model-assisted Analyst call"
ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS = (
    FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS
)
FINDING_GENERATION_MODE_DETERMINISTIC = "deterministic_scaffold"
FINDING_GENERATION_MODE_MODEL_ASSISTED = "model_assisted_smart"
MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE = "missing_license"
MODEL_ASSISTED_NOT_RUN_MISSING_ADAPTER = "missing_adapter_or_route"
MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE_AND_ADAPTER = "missing_license_and_adapter"
MODEL_INPUT_EVIDENCE_DEPTH_BOUNDED_EXCERPT = "bounded_excerpt"
MODEL_INPUT_EVIDENCE_DEPTH_LIMITED_NO_EXCERPT = "limited_no_excerpt"
MODEL_INPUT_EVIDENCE_DEPTH_REFS_ONLY = "refs_only"
MODEL_INPUT_EVIDENCE_LIMITATION_NO_SAFE_BOUNDED_EXCERPT = (
    "no_safe_bounded_excerpt_text_available"
)
DETERMINISTIC_FALLBACK_ROLE_DIAGNOSTIC = "offline_test_diagnostic_fallback"
PRODUCT_PROOF_STATUS_BLOCKED_ANALYST_NOT_RUN = (
    "blocked_model_assisted_analyst_required_but_not_run"
)
PRODUCT_PROOF_STATUS_PENDING_DPRIME_VALIDATION = (
    "not_claimed_pending_dprime_validation"
)

ANALYST_FINDING_SYSTEM_PROMPT = (
    "You are the ScryRaven Analyst for a proposal-only "
    "AnalystFindingProposal. Use only the provided safe refs, triage roles, "
    "bounded evidence excerpts, bounded-content refs, caveats, exclusions, and "
    "gaps. If bounded_evidence_excerpt_available is false, report only limited "
    "refs-only analysis and do not imply source-grounded model analysis over "
    "source text. Return only one JSON object containing "
    "analyst_finding_proposal. Do not write final user prose, do not cite "
    "sources directly, do not make D-prime decisions, do not run Scrutineer, "
    "and do not claim evidence admission, source-obligation satisfaction, "
    "citation eligibility, ComponentCoverage, Sufficiency, FinalAnswerPacket, "
    "Author output, source display, or product correctness."
)

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


@dataclass(frozen=True, slots=True)
class AnalystFindingModelAssistedLicense:
    """Explicit license for one model-assisted Analyst attempt."""

    license_id: str = "analyst-finding-proposal-model-assisted-v1:not-enabled"
    enabled: bool = False
    test_only: bool = True
    adapter_kind: str = MODEL_ADAPTER_KIND_FAKE_TEST
    max_model_calls: int = 1
    retry_policy: str = "forbidden"
    timeout_policy: str = "fail_closed"
    model_role: str = ANALYST_MODEL_ROLE_SMART
    role_surface: str = ANALYST_ROLE_SURFACE
    runtime_consumer: str = ANALYST_RUNTIME_CONSUMER
    route_authority: str = ANALYST_ROUTE_AUTHORITY

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any] | None,
    ) -> "AnalystFindingModelAssistedLicense":
        safe = _safe_mapping(value)
        if not safe:
            return cls()
        test_only = safe.get("test_only", True) is True
        adapter_kind = (
            _clean_text(safe.get("adapter_kind") or safe.get("callable_kind"), limit=80)
            or (MODEL_ADAPTER_KIND_FAKE_TEST if test_only else MODEL_ADAPTER_KIND_REAL_SMART)
        )
        return cls(
            license_id=(
                _clean_text(safe.get("license_id"), limit=260) or cls().license_id
            ),
            enabled=safe.get("enabled") is True,
            test_only=test_only,
            adapter_kind=adapter_kind,
            max_model_calls=_bounded_int(safe.get("max_model_calls"), default=1),
            retry_policy=_normalize_key(safe.get("retry_policy")) or "forbidden",
            timeout_policy=_normalize_key(safe.get("timeout_policy")) or "fail_closed",
            model_role=_normalize_key(safe.get("model_role")) or ANALYST_MODEL_ROLE_SMART,
            role_surface=(
                _normalize_key(safe.get("role_surface")) or ANALYST_ROLE_SURFACE
            ),
            runtime_consumer=(
                _clean_text(safe.get("runtime_consumer"), limit=260)
                or ANALYST_RUNTIME_CONSUMER
            ),
            route_authority=(
                _clean_text(safe.get("route_authority"), limit=260)
                or ANALYST_ROUTE_AUTHORITY
            ),
        )

    @property
    def is_fake_test(self) -> bool:
        return (
            self.test_only is True
            and _normalize_key(self.adapter_kind) == MODEL_ADAPTER_KIND_FAKE_TEST
        )

    @property
    def is_real_smart_route(self) -> bool:
        return (
            self.test_only is not True
            or _normalize_key(self.adapter_kind) == MODEL_ADAPTER_KIND_REAL_SMART
        )

    def to_ref(self) -> dict[str, Any]:
        return {
            "license_id": self.license_id,
            "phase": ANALYST_FINDING_PROPOSAL_PHASE,
            "enabled": self.enabled,
            "test_only": self.test_only,
            "adapter_kind": self.adapter_kind,
            "max_model_calls": self.max_model_calls,
            "retry_policy": self.retry_policy,
            "timeout_policy": self.timeout_policy,
            "model_role": self.model_role,
            "role_surface": self.role_surface,
            "runtime_consumer": self.runtime_consumer,
            "route_authority": self.route_authority,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
        }


@dataclass(slots=True)
class AnalystFindingSmartModelAdapter:
    """One-shot adapter for the configured SmartModel Analyst route."""

    transport: Callable[..., Any] = field(repr=False, compare=False)
    adapter_ref: str = "analyst-finding-smart-model-adapter:configured:v1"
    configured_smart_provider: str | None = None
    configured_smart_model: str | None = None
    configured_endpoint_kind: str | None = None
    adapter_kind: str = MODEL_ADAPTER_KIND_REAL_SMART
    model_role: str = ANALYST_MODEL_ROLE_SMART
    role_surface: str = ANALYST_ROLE_SURFACE
    runtime_consumer: str = ANALYST_RUNTIME_CONSUMER
    route_authority: str = ANALYST_ROUTE_AUTHORITY
    max_model_calls: int = 1
    retry_policy: str = "forbidden"
    fallback_policy: str = "forbidden"
    timeout_policy: str = "fail_closed"
    provider_switching_allowed: bool = False
    endpoint_switching_allowed: bool = False
    raw_prompt_retained: bool = False
    raw_model_response_retained: bool = False
    raw_provider_payload_retained: bool = False
    _call_count: int = field(default=0, init=False, repr=False)

    def to_ref(self) -> dict[str, Any]:
        return _without_empty(
            {
                "schema_version": ANALYST_FINDING_MODEL_ROUTE_SCHEMA_VERSION,
                "phase": ANALYST_FINDING_PROPOSAL_PHASE,
                "adapter_ref": self.adapter_ref,
                "model_adapter_kind": self.adapter_kind,
                "model_role": self.model_role,
                "role_surface": self.role_surface,
                "runtime_consumer": self.runtime_consumer,
                "route_authority": self.route_authority,
                "configured_smart_provider": _safe_route_text(
                    self.configured_smart_provider,
                    limit=120,
                ),
                "configured_smart_model": _safe_route_text(
                    self.configured_smart_model,
                    limit=160,
                ),
                "configured_endpoint_kind": _clean_text(
                    self.configured_endpoint_kind,
                    limit=120,
                ),
                "max_model_calls": self.max_model_calls,
                "retry_policy": self.retry_policy,
                "fallback_policy": self.fallback_policy,
                "timeout_policy": self.timeout_policy,
                "provider_switching_allowed": self.provider_switching_allowed,
                "endpoint_switching_allowed": self.endpoint_switching_allowed,
                "call_count": self._call_count,
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "raw_provider_payload_retained": False,
                "provider_payload_retained": False,
                "live_model_call_run": False,
            }
        )

    def invoke_once(
        self,
        *,
        prompt: str,
        input_packet: Mapping[str, Any],
        system_prompt: str,
        license_ref: Mapping[str, Any],
        route_ref: Mapping[str, Any],
    ) -> Any:
        if self._call_count != 0 or self.max_model_calls != 1:
            raise AnalystFindingProposalError(
                "Analyst SmartModel route must execute at most once"
            )
        if self.model_role != ANALYST_MODEL_ROLE_SMART:
            raise AnalystFindingProposalError(
                "AnalystFindingProposal requires SmartModel role"
            )
        if self.role_surface != ANALYST_ROLE_SURFACE:
            raise AnalystFindingProposalError(
                "AnalystFindingProposal route surface mismatch"
            )
        if self.retry_policy != "forbidden" or self.fallback_policy != "forbidden":
            raise AnalystFindingProposalError(
                "Analyst SmartModel route must forbid retry and fallback"
            )
        if self.provider_switching_allowed or self.endpoint_switching_allowed:
            raise AnalystFindingProposalError(
                "Analyst SmartModel route must not allow provider switching"
            )
        if self.raw_prompt_retained or self.raw_model_response_retained:
            raise AnalystFindingProposalError(
                "Analyst SmartModel route must not retain raw prompts or responses"
            )
        self._call_count += 1
        return self.transport(
            prompt,
            system_prompt=system_prompt,
            input_packet=input_packet,
            license_ref=license_ref,
            route_ref=route_ref,
            require_json=True,
        )


def build_model_assisted_analyst_license(
    *,
    license_id: str,
    test_only: bool = True,
    adapter_kind: str | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    """Return an explicit license packet for a gated Analyst model attempt."""

    return AnalystFindingModelAssistedLicense(
        license_id=license_id,
        enabled=enabled,
        test_only=test_only,
        adapter_kind=(
            adapter_kind
            or (MODEL_ADAPTER_KIND_FAKE_TEST if test_only else MODEL_ADAPTER_KIND_REAL_SMART)
        ),
    ).to_ref()


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
    model_input_candidate_refs = _model_input_candidate_refs(
        selected_refs=selected_refs,
        adjacent_refs=adjacent_refs,
        excluded_refs=excluded_refs,
        unreadable_refs=unreadable_refs,
        overclaim_refs=overclaim_refs,
    )
    _reject_unsafe_fetch_read_packet_material(fetch_packet)
    bounded_content_refs = _bounded_content_refs(
        fetch_packet,
        candidate_refs=selected_refs,
    )
    evidence_profile = _model_input_evidence_profile(
        fetch_packet,
        candidate_refs=model_input_candidate_refs,
        bounded_content_refs=bounded_content_refs,
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
            "finding_generation_mode": FINDING_GENERATION_MODE_DETERMINISTIC,
            "model_adapter_kind": MODEL_ADAPTER_KIND_DETERMINISTIC,
            "model_role": ANALYST_MODEL_ROLE_SMART,
            "role_surface": ANALYST_ROLE_SURFACE,
            "runtime_consumer": ANALYST_RUNTIME_CONSUMER,
            "route_authority": ANALYST_ROUTE_AUTHORITY,
            "model_assisted_analysis_license_present": False,
            "model_assisted_analysis_adapter_present": False,
            "model_calls_attempted": 0,
            "model_calls_completed": 0,
            "live_model_call_run": False,
            "safe_model_input_packet_ref": {},
            "model_output_validation_ref": {},
            **_analyst_product_policy_fields(model_assisted_run=False),
            **evidence_profile,
            "model_route_diagnostics": _analyst_model_route_diagnostics(
                license_obj=AnalystFindingModelAssistedLicense(),
                adapter_ref={},
                adapter_present=False,
                attempted=0,
                completed=0,
                live_model_call_run=False,
                not_run_reason=MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE_AND_ADAPTER,
            ),
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
    fetch_read_content_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return safe retained refs for a future model-assisted Analyst call."""

    triage = _safe_mapping(triage_packet)
    gap = _safe_mapping(analysis_gap_search_proposal)
    binding_ref = _safe_mapping(triage.get("component_answer_type_binding_ref"))
    selected_refs = _safe_refs(triage.get("selected_answer_bearing_candidate_refs"))
    adjacent_refs = _safe_refs(triage.get("adjacent_context_candidate_refs"))
    excluded_refs = _safe_refs(triage.get("excluded_scope_candidate_refs"))
    unreadable_refs = _safe_refs(triage.get("unreadable_high_value_candidate_refs"))
    overclaim_refs = _safe_refs(triage.get("overclaim_risk_candidate_refs"))
    fetch_packet = _safe_mapping(fetch_read_content_packet)
    model_input_candidate_refs = _model_input_candidate_refs(
        selected_refs=selected_refs,
        adjacent_refs=adjacent_refs,
        excluded_refs=excluded_refs,
        unreadable_refs=unreadable_refs,
        overclaim_refs=overclaim_refs,
    )
    _reject_unsafe_fetch_read_packet_material(fetch_packet)
    bounded_content_refs = _bounded_content_refs(
        fetch_packet,
        candidate_refs=selected_refs,
    )
    bounded_evidence_excerpts = _bounded_evidence_excerpts(
        fetch_packet,
        candidate_refs=model_input_candidate_refs,
    )
    evidence_profile = _model_input_evidence_profile_from_excerpts(
        bounded_evidence_excerpts=bounded_evidence_excerpts,
        bounded_content_refs=bounded_content_refs,
    )
    packet = _without_empty(
        {
            "schema_version": ANALYST_SAFE_MODEL_INPUT_PACKET_SCHEMA_VERSION,
            "phase": ANALYST_FINDING_PROPOSAL_PHASE,
            "packet_kind": "AnalystFindingSafeModelInputPacket",
            "model_role": ANALYST_MODEL_ROLE_SMART,
            "role_surface": ANALYST_ROLE_SURFACE,
            "runtime_consumer": ANALYST_RUNTIME_CONSUMER,
            "route_authority": ANALYST_ROUTE_AUTHORITY,
            "component_answer_type_binding_ref": binding_ref,
            "claim_under_test": binding_ref.get("claim_under_test"),
            "requested_answer_type": binding_ref.get("requested_answer_type"),
            "expected_value_shape": binding_ref.get("expected_value_shape"),
            "adjacent_claim_exclusions": list(
                _safe_sequence(binding_ref.get("adjacent_claim_exclusions"))
            ),
            "candidate_triage_summary_ref": _safe_mapping(
                triage.get("candidate_triage_summary_ref")
            ),
            "candidate_triage_records": _safe_candidate_triage_records(
                triage.get("candidate_triage_records")
            ),
            "selected_answer_bearing_candidate_refs": selected_refs,
            "adjacent_context_candidate_refs": adjacent_refs,
            "excluded_scope_candidate_refs": excluded_refs,
            "unreadable_high_value_candidate_refs": unreadable_refs,
            "overclaim_risk_candidate_refs": overclaim_refs,
            "bounded_content_refs": bounded_content_refs,
            "bounded_evidence_excerpts": bounded_evidence_excerpts,
            **evidence_profile,
            "analysis_gap_search_proposal_ref": _gap_proposal_ref(gap),
            "non_authority_posture_flags": _non_authority_posture(),
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
            "provider_payload_retained": False,
            "live_model_call_run": False,
            **_non_authority_posture(),
        }
    )
    for list_key in (
        "selected_answer_bearing_candidate_refs",
        "adjacent_context_candidate_refs",
        "excluded_scope_candidate_refs",
        "unreadable_high_value_candidate_refs",
        "overclaim_risk_candidate_refs",
        "bounded_content_refs",
        "bounded_evidence_excerpts",
        "candidate_triage_records",
    ):
        packet.setdefault(list_key, [])
    validate_analyst_finding_safe_model_input_packet(packet)
    digest = _digest_json(packet)
    return {
        **packet,
        "safe_model_input_packet_id": f"analyst-finding-model-input:{digest[:20]}",
        "safe_model_input_packet_digest": digest,
    }


def validate_analyst_finding_safe_model_input_packet(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the ref-addressable safe packet before any model call."""

    packet = _safe_mapping(value)
    if packet.get("schema_version") != ANALYST_SAFE_MODEL_INPUT_PACKET_SCHEMA_VERSION:
        raise AnalystFindingProposalError("safe model input packet schema mismatch")
    if packet.get("model_role") != ANALYST_MODEL_ROLE_SMART:
        raise AnalystFindingProposalError("Analyst safe input must use SmartModel role")
    if packet.get("role_surface") != ANALYST_ROLE_SURFACE:
        raise AnalystFindingProposalError("Analyst safe input route surface mismatch")
    if not _safe_mapping(packet.get("component_answer_type_binding_ref")):
        raise AnalystFindingProposalError(
            "safe model input requires component answer-type binding ref"
        )
    _validate_bounded_evidence_excerpts(
        packet.get("bounded_evidence_excerpts"),
        context="Analyst safe model input bounded evidence excerpts",
    )
    _reject_forbidden_or_authority(packet, context="Analyst safe model input packet")
    return _json_safe(packet)


def build_analyst_finding_prompt(
    input_packet: Mapping[str, Any],
) -> str:
    """Build a transient prompt from a validated safe packet."""

    safe_input = validate_analyst_finding_safe_model_input_packet(input_packet)
    prompt_payload = {
        "schema_version": ANALYST_FINDING_PROMPT_SCHEMA_VERSION,
        "task": "produce_analyst_finding_proposal",
        "instructions": [
            "Stay within the requested answer type and expected value shape.",
            "Use candidate triage roles to separate answer-bearing, adjacent, excluded, unreadable, gap, caveat, and risk material.",
            "Tie every substantive analysis claim to candidate/source refs or mark it as a gap, risk, or exclusion.",
            "Do not produce a proposed answer claim when only adjacent, excluded, or unreadable refs are present.",
            "Use bounded_evidence_excerpts when present; if they are absent, keep analysis limited to refs and report the limitation.",
            "Preserve analysis custody separately from source custody.",
            "Return only the required structured JSON object.",
        ],
        "forbidden_claims": [
            "evidence admission",
            "source-obligation satisfaction",
            "citation eligibility",
            "ComponentCoverage",
            "SufficiencyReadiness",
            "FinalAnswerPacket",
            "Author output",
            "source display",
            "product correctness",
            "D-prime decision",
            "Scrutineer validation",
        ],
        "safe_model_input_packet": safe_input,
        "required_output": {
            "analyst_finding_proposal": {
                "schema_version": ANALYST_FINDING_PROPOSAL_SCHEMA_VERSION,
                "finding_kind": "analyst_finding_proposal",
                "analysis_claims": "array",
                "source_support_map": "AnalystSourceSupportMap",
                "dprime_handoff_refs": "proposal refs only",
            }
        },
    }
    return json.dumps(prompt_payload, sort_keys=True, separators=(",", ":"))


def build_model_assisted_analyst_finding_proposal(
    *,
    triage_packet: Mapping[str, Any],
    analysis_gap_search_proposal: Mapping[str, Any],
    fetch_read_content_packet: Mapping[str, Any] | None = None,
    model_assisted_analyst_license: Mapping[str, Any]
    | AnalystFindingModelAssistedLicense
    | None = None,
    model_assisted_analyst_adapter: Any | None = None,
) -> dict[str, Any]:
    """Run a gated Analyst model route, or deterministically fall back."""

    deterministic = build_deterministic_analyst_finding_proposal(
        triage_packet=triage_packet,
        analysis_gap_search_proposal=analysis_gap_search_proposal,
        fetch_read_content_packet=fetch_read_content_packet,
    )
    license_obj = _coerce_model_assisted_license(model_assisted_analyst_license)
    adapter_ref = _model_adapter_ref(model_assisted_analyst_adapter)
    adapter_present = bool(model_assisted_analyst_adapter)
    if not license_obj.enabled or not adapter_present:
        if not license_obj.enabled and not adapter_present:
            reason = MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE_AND_ADAPTER
        elif not license_obj.enabled:
            reason = MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE
        else:
            reason = MODEL_ASSISTED_NOT_RUN_MISSING_ADAPTER
        return _annotated_deterministic_fallback(
            deterministic,
            license_obj=license_obj,
            adapter_ref=adapter_ref,
            adapter_present=adapter_present,
            not_run_reason=reason,
        )

    input_packet = build_analyst_finding_safe_model_input_packet(
        triage_packet=triage_packet,
        analysis_gap_search_proposal=analysis_gap_search_proposal,
        fetch_read_content_packet=fetch_read_content_packet,
    )
    prompt = build_analyst_finding_prompt(input_packet)
    license_ref = license_obj.to_ref()
    attempted = 1
    completed = 0
    if license_obj.is_fake_test:
        try:
            structured_output = model_assisted_analyst_adapter(input_packet)
        except Exception as exc:  # noqa: BLE001 - fail closed with safe detail.
            raise AnalystFindingProposalError(
                "Analyst fake model adapter failed closed: "
                f"{type(exc).__name__}"
            ) from None
        completed = 1
        return validate_model_assisted_analyst_output(
            safe_model_input_packet=input_packet,
            structured_output=structured_output,
            adapter_kind=MODEL_ADAPTER_KIND_FAKE_TEST,
            license_ref=license_ref,
            adapter_ref=adapter_ref,
            model_calls_attempted=attempted,
            model_calls_completed=completed,
            live_model_call_run=False,
        )

    try:
        raw_output = _invoke_real_model_adapter(
            model_assisted_analyst_adapter,
            prompt=prompt,
            input_packet=input_packet,
            system_prompt=ANALYST_FINDING_SYSTEM_PROMPT,
            license_ref=license_ref,
            route_ref=adapter_ref,
        )
    except Exception as exc:  # noqa: BLE001 - fail closed with safe detail.
        raise AnalystFindingProposalError(
            "Analyst SmartModel adapter failed closed: "
            f"{type(exc).__name__}"
        ) from None
    completed = 1
    structured_output = _parse_structured_output(raw_output)
    return validate_model_assisted_analyst_output(
        safe_model_input_packet=input_packet,
        structured_output=structured_output,
        adapter_kind=MODEL_ADAPTER_KIND_REAL_SMART,
        license_ref=license_ref,
        adapter_ref=adapter_ref,
        model_calls_attempted=attempted,
        model_calls_completed=completed,
        live_model_call_run=True,
    )


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

    return validate_model_assisted_analyst_output(
        safe_model_input_packet=safe_model_input_packet,
        structured_output=structured_output,
        adapter_kind=MODEL_ADAPTER_KIND_FAKE_TEST,
        license_ref=AnalystFindingModelAssistedLicense(
            license_id="analyst-finding-fake-adapter-validation:test-only",
            enabled=True,
            test_only=True,
            adapter_kind=MODEL_ADAPTER_KIND_FAKE_TEST,
        ).to_ref(),
        adapter_ref={"model_adapter_kind": MODEL_ADAPTER_KIND_FAKE_TEST},
        model_calls_attempted=1,
        model_calls_completed=1,
        live_model_call_run=False,
    )


def validate_model_assisted_analyst_output(
    *,
    safe_model_input_packet: Mapping[str, Any],
    structured_output: Mapping[str, Any],
    adapter_kind: str,
    license_ref: Mapping[str, Any],
    adapter_ref: Mapping[str, Any],
    model_calls_attempted: int,
    model_calls_completed: int,
    live_model_call_run: bool,
) -> dict[str, Any]:
    """Validate structured model output into AnalystFindingProposal."""

    input_packet = validate_analyst_finding_safe_model_input_packet(
        safe_model_input_packet
    )
    normalized_adapter_kind = _normalize_key(adapter_kind)
    if normalized_adapter_kind not in {
        MODEL_ADAPTER_KIND_FAKE_TEST,
        MODEL_ADAPTER_KIND_REAL_SMART,
    }:
        raise AnalystFindingProposalError("Analyst model adapter kind invalid")
    output = _safe_mapping(structured_output)
    proposal = _safe_mapping(output.get("analyst_finding_proposal")) or output
    _reject_forbidden_or_authority(
        output,
        context="Analyst model structured output",
    )
    validation_ref = _model_output_validation_ref(
        input_packet=input_packet,
        adapter_kind=normalized_adapter_kind,
        live_model_call_run=live_model_call_run,
    )
    proposal = {
        **proposal,
        "model_assisted_analysis_run": True,
        "finding_generation_mode": FINDING_GENERATION_MODE_MODEL_ASSISTED,
        "model_adapter_kind": normalized_adapter_kind,
        "model_role": ANALYST_MODEL_ROLE_SMART,
        "role_surface": ANALYST_ROLE_SURFACE,
        "runtime_consumer": ANALYST_RUNTIME_CONSUMER,
        "route_authority": ANALYST_ROUTE_AUTHORITY,
        "model_assisted_analysis_license_present": True,
        "model_assisted_analysis_adapter_present": True,
        "model_calls_attempted": _bounded_int(model_calls_attempted),
        "model_calls_completed": _bounded_int(model_calls_completed),
        "live_model_call_run": bool(live_model_call_run),
        "safe_model_input_packet_ref": _safe_model_input_packet_ref(input_packet),
        "model_output_validation_ref": validation_ref,
        **_analyst_product_policy_fields(model_assisted_run=True),
        **_model_input_evidence_profile_from_input(input_packet),
        "model_route_diagnostics": _analyst_model_route_diagnostics(
            license_obj=_coerce_model_assisted_license(license_ref),
            adapter_ref=_safe_mapping(adapter_ref),
            adapter_present=True,
            attempted=_bounded_int(model_calls_attempted),
            completed=_bounded_int(model_calls_completed),
            live_model_call_run=bool(live_model_call_run),
            not_run_reason=None,
        ),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "provider_payload_retained": False,
    }
    _validate_model_output_against_safe_input(proposal, input_packet)
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
    model_role = _normalize_key(proposal.get("model_role"))
    if model_role and model_role != ANALYST_MODEL_ROLE_SMART:
        raise AnalystFindingProposalError(
            "AnalystFindingProposal model role must be smart"
        )
    role_surface = _normalize_key(proposal.get("role_surface"))
    if role_surface and role_surface != ANALYST_ROLE_SURFACE:
        raise AnalystFindingProposalError(
            "AnalystFindingProposal role surface mismatch"
        )
    adapter_kind = _normalize_key(proposal.get("model_adapter_kind"))
    if proposal.get("model_assisted_analysis_run") is True:
        if adapter_kind not in {
            MODEL_ADAPTER_KIND_FAKE_TEST,
            MODEL_ADAPTER_KIND_REAL_SMART,
        }:
            raise AnalystFindingProposalError(
                "AnalystFindingProposal model adapter kind invalid"
            )
        if adapter_kind == MODEL_ADAPTER_KIND_FAKE_TEST and proposal.get(
            "live_model_call_run"
        ) is not False:
            raise AnalystFindingProposalError("fake Analyst adapter must not run live")
        if adapter_kind == MODEL_ADAPTER_KIND_REAL_SMART and proposal.get(
            "live_model_call_run"
        ) is not True:
            raise AnalystFindingProposalError(
                "real Analyst SmartModel route must mark the live model call fact"
            )
    elif proposal.get("live_model_call_run") is not False:
        raise AnalystFindingProposalError(
            "deterministic Analyst proposal must not run live model"
        )
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
            "finding_generation_mode": proposal.get("finding_generation_mode"),
            "model_assisted_analysis_run": (
                proposal.get("model_assisted_analysis_run") is True
            ),
            "model_assisted_analysis_not_run_reason": proposal.get(
                "model_assisted_analysis_not_run_reason"
            ),
            "model_adapter_kind": proposal.get("model_adapter_kind"),
            "model_role": proposal.get("model_role"),
            "role_surface": proposal.get("role_surface"),
            "model_calls_attempted": _bounded_int(
                proposal.get("model_calls_attempted")
            ),
            "model_calls_completed": _bounded_int(
                proposal.get("model_calls_completed")
            ),
            "live_model_call_run": proposal.get("live_model_call_run") is True,
            "model_assisted_analyst_required_for_product_path": (
                proposal.get("model_assisted_analyst_required_for_product_path") is True
            ),
            "model_assisted_analyst_required_for_product_pass": (
                proposal.get("model_assisted_analyst_required_for_product_pass") is True
            ),
            "analyst_finding_generation_required_mode": proposal.get(
                "analyst_finding_generation_required_mode"
            ),
            "model_assisted_analyst_requirement_satisfied": (
                proposal.get("model_assisted_analyst_requirement_satisfied") is True
            ),
            "model_assisted_analyst_product_grade_analysis": (
                proposal.get("model_assisted_analyst_product_grade_analysis") is True
            ),
            "deterministic_fallback_role": proposal.get(
                "deterministic_fallback_role"
            ),
            "product_proof_status": proposal.get("product_proof_status"),
            "product_proof_blocker": proposal.get("product_proof_blocker"),
            "bounded_evidence_excerpt_available": (
                proposal.get("bounded_evidence_excerpt_available") is True
            ),
            "bounded_evidence_excerpt_count": _bounded_int(
                proposal.get("bounded_evidence_excerpt_count")
            ),
            "model_assisted_analysis_evidence_depth": proposal.get(
                "model_assisted_analysis_evidence_depth"
            ),
            "model_input_evidence_limitation": proposal.get(
                "model_input_evidence_limitation"
            ),
            "safe_model_input_packet_ref": _safe_mapping(
                proposal.get("safe_model_input_packet_ref")
            ),
            "model_output_validation_ref": _safe_mapping(
                proposal.get("model_output_validation_ref")
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


def _model_input_candidate_refs(
    *,
    selected_refs: Sequence[Mapping[str, Any]],
    adjacent_refs: Sequence[Mapping[str, Any]],
    excluded_refs: Sequence[Mapping[str, Any]],
    unreadable_refs: Sequence[Mapping[str, Any]],
    overclaim_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in (
        *selected_refs,
        *adjacent_refs,
        *excluded_refs,
        *unreadable_refs,
        *overclaim_refs,
    ):
        ref = _safe_mapping(item)
        candidate_id = _clean_text(ref.get("candidate_id"), limit=320)
        if candidate_id and candidate_id not in seen:
            refs.append(ref)
            seen.add(candidate_id)
    return refs


def _analyst_product_policy_fields(*, model_assisted_run: bool) -> dict[str, Any]:
    return {
        "model_assisted_analyst_required_for_product_path": True,
        "model_assisted_analyst_required_for_product_pass": True,
        "analyst_finding_generation_required_mode": (
            FINDING_GENERATION_MODE_MODEL_ASSISTED
        ),
        "model_assisted_analyst_requirement_satisfied": bool(model_assisted_run),
        "model_assisted_analyst_product_grade_analysis": bool(model_assisted_run),
        "deterministic_fallback_role": None
        if model_assisted_run
        else DETERMINISTIC_FALLBACK_ROLE_DIAGNOSTIC,
        "product_proof_status": PRODUCT_PROOF_STATUS_PENDING_DPRIME_VALIDATION
        if model_assisted_run
        else PRODUCT_PROOF_STATUS_BLOCKED_ANALYST_NOT_RUN,
        "product_proof_blocker": None
        if model_assisted_run
        else PRODUCT_PROOF_STATUS_BLOCKED_ANALYST_NOT_RUN,
        "product_correctness_claimed": False,
    }


def _model_input_evidence_profile(
    fetch_read_content_packet: Mapping[str, Any],
    *,
    candidate_refs: Sequence[Mapping[str, Any]],
    bounded_content_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return _model_input_evidence_profile_from_excerpts(
        bounded_evidence_excerpts=_bounded_evidence_excerpts(
            fetch_read_content_packet,
            candidate_refs=candidate_refs,
        ),
        bounded_content_refs=bounded_content_refs,
    )


def _model_input_evidence_profile_from_input(
    input_packet: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _safe_mapping(input_packet)
    return {
        "bounded_evidence_excerpt_available": (
            safe.get("bounded_evidence_excerpt_available") is True
        ),
        "bounded_evidence_excerpt_count": _bounded_int(
            safe.get("bounded_evidence_excerpt_count")
        ),
        "bounded_evidence_excerpt_max_chars": _bounded_int(
            safe.get("bounded_evidence_excerpt_max_chars"),
            default=ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS,
        ),
        "model_assisted_analysis_evidence_depth": safe.get(
            "model_assisted_analysis_evidence_depth"
        ),
        "model_input_evidence_limitation": safe.get(
            "model_input_evidence_limitation"
        ),
    }


def _model_input_evidence_profile_from_excerpts(
    *,
    bounded_evidence_excerpts: Sequence[Mapping[str, Any]],
    bounded_content_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    excerpts = [_safe_mapping(item) for item in bounded_evidence_excerpts if item]
    if excerpts:
        return {
            "bounded_evidence_excerpt_available": True,
            "bounded_evidence_excerpt_count": len(excerpts),
            "bounded_evidence_excerpt_max_chars": (
                ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS
            ),
            "model_assisted_analysis_evidence_depth": (
                MODEL_INPUT_EVIDENCE_DEPTH_BOUNDED_EXCERPT
            ),
            "model_input_evidence_limitation": None,
        }
    return {
        "bounded_evidence_excerpt_available": False,
        "bounded_evidence_excerpt_count": 0,
        "bounded_evidence_excerpt_max_chars": (
            ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS
        ),
        "model_assisted_analysis_evidence_depth": (
            MODEL_INPUT_EVIDENCE_DEPTH_LIMITED_NO_EXCERPT
            if bounded_content_refs
            else MODEL_INPUT_EVIDENCE_DEPTH_REFS_ONLY
        ),
        "model_input_evidence_limitation": (
            MODEL_INPUT_EVIDENCE_LIMITATION_NO_SAFE_BOUNDED_EXCERPT
        ),
    }


def _reject_unsafe_fetch_read_packet_material(
    fetch_read_content_packet: Mapping[str, Any],
) -> None:
    packet = _safe_mapping(fetch_read_content_packet)
    if not packet:
        return
    packet_without_references = {
        key: value for key, value in packet.items() if key != "reference_records"
    }
    _reject_forbidden_or_authority(
        packet_without_references,
        context="Analyst model fetch/read packet",
    )
    _reject_nonfalse_raw_retention_flags(
        packet_without_references,
        context="Analyst model fetch/read packet",
    )
    allowed_text_keys = {"bounded_text", "bounded_excerpt"}
    for raw in _safe_sequence(packet.get("reference_records")):
        ref = _safe_mapping(raw)
        keys = _collect_keys(ref)
        forbidden = sorted(keys & (_FORBIDDEN_KEYS - allowed_text_keys))
        if forbidden:
            raise AnalystFindingProposalError(
                "Analyst model fetch/read reference includes forbidden material"
            )
        dangerous = sorted(_dangerous_true_claims(ref))
        if dangerous:
            raise AnalystFindingProposalError(
                "Analyst model fetch/read reference attempts authority upgrade"
            )
        _reject_nonfalse_raw_retention_flags(
            ref,
            context="Analyst model fetch/read reference",
        )
        if "bounded_text" in ref or "bounded_excerpt" in ref:
            _safe_bounded_excerpt_text(ref)


def _reject_nonfalse_raw_retention_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key in _collect_keys(value):
        if not key.startswith("raw_") or not key.endswith("_retained"):
            continue
        for item in _all_normalized_key_values(value, key):
            if item is not False:
                raise AnalystFindingProposalError(
                    f"{context} raw/private retention flag must remain false"
                )


def _bounded_evidence_excerpts(
    fetch_read_content_packet: Mapping[str, Any],
    *,
    candidate_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    packet = _safe_mapping(fetch_read_content_packet)
    candidate_ids = _candidate_ids(candidate_refs)
    excerpts: list[dict[str, Any]] = []
    for raw in _safe_sequence(packet.get("reference_records")):
        ref = _safe_mapping(raw)
        if not ref or ref.get("candidate_id") not in candidate_ids:
            continue
        bounded_text = _safe_bounded_excerpt_text(ref)
        if not bounded_text:
            continue
        excerpt_digest = _bounded_excerpt_digest(ref, bounded_text)
        excerpt = _without_empty(
            {
                "candidate_id": ref.get("candidate_id"),
                "candidate_digest": ref.get("candidate_digest"),
                "reference_id": ref.get("reference_id"),
                "reference_digest": ref.get("reference_digest"),
                "excerpt_digest": excerpt_digest,
                "bounded_content_digest": excerpt_digest,
                "bounded_excerpt_text": bounded_text,
                "bounded_character_count": len(bounded_text),
                "fetch_read_status": ref.get("fetch_read_status"),
                "content_type": ref.get("content_type"),
                "bounded_evidence_excerpt_source": (
                    "existing_fetch_read_content_packet.reference_records.bounded_text"
                ),
                "bounded_text_sanitized": True,
                "bounded_text_bounded": True,
                "not_semantic_support": True,
                "not_citation_eligible": True,
                "not_source_obligation_satisfaction": True,
                "raw_prompt_retained": False,
                "raw_model_response_retained": False,
                "raw_provider_payload_retained": False,
                "raw_source_content_retained": False,
            }
        )
        _reject_forbidden_or_authority(
            excerpt,
            context="Analyst bounded evidence excerpt",
        )
        excerpts.append(excerpt)
    return excerpts


def _validate_bounded_evidence_excerpts(value: Any, *, context: str) -> None:
    for item in _safe_sequence(value):
        excerpt = _safe_mapping(item)
        text = _clean_text(
            excerpt.get("bounded_excerpt_text"),
            limit=ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS + 1,
        )
        if not text:
            raise AnalystFindingProposalError(f"{context} requires bounded text")
        if len(text) > ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS:
            raise AnalystFindingProposalError(f"{context} exceeds excerpt cap")
        if excerpt.get("bounded_character_count") != len(text):
            raise AnalystFindingProposalError(
                f"{context} character count mismatch"
            )
        declared_digest = _clean_text(excerpt.get("excerpt_digest"), limit=128)
        if declared_digest and declared_digest != _digest_json({"bounded_text": text}):
            raise AnalystFindingProposalError(f"{context} digest mismatch")
        _reject_forbidden_or_authority(excerpt, context=context)
        _reject_nonfalse_raw_retention_flags(excerpt, context=context)


def _safe_bounded_excerpt_text(ref: Mapping[str, Any]) -> str | None:
    safe = _safe_mapping(ref)
    has_text = safe.get("bounded_text") not in (None, "")
    has_excerpt = safe.get("bounded_excerpt") not in (None, "")
    if not has_text and not has_excerpt:
        return None
    if safe.get("bounded_text_sanitized") is not True or safe.get(
        "bounded_text_bounded"
    ) is not True:
        raise AnalystFindingProposalError(
            "Analyst model bounded excerpt requires sanitized/bounded flags"
        )
    text = _clean_text(
        safe.get("bounded_text") if has_text else safe.get("bounded_excerpt"),
        limit=ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS + 1,
    )
    if not text:
        return None
    if len(text) > ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS:
        raise AnalystFindingProposalError(
            "Analyst model bounded excerpt exceeds cap"
        )
    for key in (
        "bounded_character_count",
        "bounded_text_char_count",
        "bounded_excerpt_char_count",
    ):
        if key in safe and safe.get(key) not in (None, ""):
            if _bounded_int(safe.get(key)) != len(text):
                raise AnalystFindingProposalError(
                    "Analyst model bounded excerpt character count mismatch"
                )
    _bounded_excerpt_digest(safe, text)
    return text


def _bounded_excerpt_digest(ref: Mapping[str, Any], text: str) -> str:
    digest = _digest_json({"bounded_text": text})
    for key in ("excerpt_digest", "bounded_content_digest", "bounded_text_digest"):
        declared = _clean_text(_safe_mapping(ref).get(key), limit=128)
        if declared and declared != digest:
            raise AnalystFindingProposalError(
                "Analyst model bounded excerpt digest mismatch"
            )
    return digest


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
                    "bounded_content_digest": ref.get("excerpt_digest")
                    or ref.get("bounded_content_digest")
                    or ref.get("bounded_text_digest"),
                    "bounded_character_count": ref.get("bounded_character_count")
                    or ref.get("bounded_content_char_count")
                    or ref.get("bounded_text_char_count"),
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


def _all_normalized_key_values(value: Any, normalized_key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_key(key) == normalized_key:
                found.append(item)
            found.extend(_all_normalized_key_values(item, normalized_key))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.extend(_all_normalized_key_values(item, normalized_key))
    return found


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
            "raw_provider_payload_retained": False,
            "bounded_evidence_excerpt_available": (
                safe.get("bounded_evidence_excerpt_available") is True
            ),
            "bounded_evidence_excerpt_count": _bounded_int(
                safe.get("bounded_evidence_excerpt_count")
            ),
            "bounded_evidence_excerpt_max_chars": _bounded_int(
                safe.get("bounded_evidence_excerpt_max_chars"),
                default=ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS,
            ),
            "model_assisted_analysis_evidence_depth": safe.get(
                "model_assisted_analysis_evidence_depth"
            ),
            "model_input_evidence_limitation": safe.get(
                "model_input_evidence_limitation"
            ),
            "live_model_call_run": False,
        }
    )


def _model_output_validation_ref(
    *,
    input_packet: Mapping[str, Any],
    adapter_kind: str,
    live_model_call_run: bool = False,
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
        "raw_provider_payload_retained": False,
        "bounded_evidence_excerpt_available": (
            input_packet.get("bounded_evidence_excerpt_available") is True
        ),
        "bounded_evidence_excerpt_count": _bounded_int(
            input_packet.get("bounded_evidence_excerpt_count")
        ),
        "model_assisted_analysis_evidence_depth": input_packet.get(
            "model_assisted_analysis_evidence_depth"
        ),
        "model_input_evidence_limitation": input_packet.get(
            "model_input_evidence_limitation"
        ),
        "live_model_call_run": bool(live_model_call_run),
    }
    digest = _digest_json(base)
    return {
        **base,
        "model_output_validation_id": (
            f"analyst-finding-model-output-validation:{digest[:20]}"
        ),
        "model_output_validation_digest": digest,
    }


def _annotated_deterministic_fallback(
    proposal: Mapping[str, Any],
    *,
    license_obj: AnalystFindingModelAssistedLicense,
    adapter_ref: Mapping[str, Any],
    adapter_present: bool,
    not_run_reason: str,
) -> dict[str, Any]:
    updated = {
        **_safe_mapping(proposal),
        "model_assisted_analysis_run": False,
        "finding_generation_mode": FINDING_GENERATION_MODE_DETERMINISTIC,
        "model_adapter_kind": MODEL_ADAPTER_KIND_DETERMINISTIC,
        "model_role": ANALYST_MODEL_ROLE_SMART,
        "role_surface": ANALYST_ROLE_SURFACE,
        "runtime_consumer": ANALYST_RUNTIME_CONSUMER,
        "route_authority": ANALYST_ROUTE_AUTHORITY,
        "model_assisted_analysis_license_present": license_obj.enabled,
        "model_assisted_analysis_adapter_present": bool(adapter_present),
        "model_assisted_analysis_not_run_reason": not_run_reason,
        "model_calls_attempted": 0,
        "model_calls_completed": 0,
        "live_model_call_run": False,
        "model_route_diagnostics": _analyst_model_route_diagnostics(
            license_obj=license_obj,
            adapter_ref=adapter_ref,
            adapter_present=adapter_present,
            attempted=0,
            completed=0,
            live_model_call_run=False,
            not_run_reason=not_run_reason,
        ),
        "safe_model_input_packet_ref": {},
        "model_output_validation_ref": {},
        **_analyst_product_policy_fields(model_assisted_run=False),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "provider_payload_retained": False,
    }
    updated["finding_digest"] = _digest_json(_without_digest(updated))
    return validate_analyst_finding_proposal(updated)


def _analyst_model_route_diagnostics(
    *,
    license_obj: AnalystFindingModelAssistedLicense,
    adapter_ref: Mapping[str, Any],
    adapter_present: bool,
    attempted: int,
    completed: int,
    live_model_call_run: bool,
    not_run_reason: str | None,
) -> dict[str, Any]:
    ref = _safe_mapping(adapter_ref)
    diagnostics = _without_empty(
        {
            "schema_version": ANALYST_FINDING_MODEL_ROUTE_SCHEMA_VERSION,
            "phase": ANALYST_FINDING_PROPOSAL_PHASE,
            "model_role": ANALYST_MODEL_ROLE_SMART,
            "role_surface": ANALYST_ROLE_SURFACE,
            "runtime_consumer": ANALYST_RUNTIME_CONSUMER,
            "route_authority": ANALYST_ROUTE_AUTHORITY,
            "model_assisted_analyst_license_present": license_obj.enabled,
            "model_assisted_analyst_adapter_present": bool(adapter_present),
            "model_assisted_analysis_not_run_reason": not_run_reason,
            "model_adapter_kind": ref.get("model_adapter_kind")
            or ref.get("adapter_kind"),
            "model_calls_attempted": _bounded_int(attempted),
            "model_calls_completed": _bounded_int(completed),
            "configured_smart_provider": _safe_route_text(
                ref.get("configured_smart_provider")
                or ref.get("configured_provider"),
                limit=120,
            ),
            "configured_smart_model": _safe_route_text(
                ref.get("configured_smart_model") or ref.get("configured_model"),
                limit=160,
            ),
            "endpoint_kind": _clean_text(
                ref.get("configured_endpoint_kind") or ref.get("endpoint_kind"),
                limit=120,
            ),
            "retry_policy": _normalize_key(
                ref.get("retry_policy") or license_obj.retry_policy
            )
            or "forbidden",
            "fallback_policy": _normalize_key(ref.get("fallback_policy"))
            or "forbidden",
            "timeout_policy": _normalize_key(
                ref.get("timeout_policy") or license_obj.timeout_policy
            )
            or "fail_closed",
            "provider_model_switching_allowed": ref.get(
                "provider_switching_allowed"
            )
            is True,
            "endpoint_switching_allowed": ref.get("endpoint_switching_allowed")
            is True,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
            "live_model_call_run": bool(live_model_call_run),
        }
    )
    diagnostics["route_diagnostics_digest"] = _digest_json(diagnostics)
    return diagnostics


def _coerce_model_assisted_license(
    value: Mapping[str, Any] | AnalystFindingModelAssistedLicense | None,
) -> AnalystFindingModelAssistedLicense:
    if isinstance(value, AnalystFindingModelAssistedLicense):
        return value
    return AnalystFindingModelAssistedLicense.from_mapping(value)


def _model_adapter_ref(adapter: Any) -> dict[str, Any]:
    if adapter is None:
        return {}
    if hasattr(adapter, "to_ref"):
        try:
            ref = _safe_mapping(adapter.to_ref())
        except Exception as exc:  # noqa: BLE001 - fail closed safely.
            raise AnalystFindingProposalError(
                "Analyst model adapter ref failed closed: "
                f"{type(exc).__name__}"
            ) from None
    elif isinstance(adapter, Mapping):
        ref = _safe_mapping(adapter)
    else:
        ref = {
            "schema_version": ANALYST_FINDING_MODEL_ROUTE_SCHEMA_VERSION,
            "phase": ANALYST_FINDING_PROPOSAL_PHASE,
            "model_adapter_kind": MODEL_ADAPTER_KIND_FAKE_TEST,
            "model_role": ANALYST_MODEL_ROLE_SMART,
            "role_surface": ANALYST_ROLE_SURFACE,
            "runtime_consumer": ANALYST_RUNTIME_CONSUMER,
            "route_authority": ANALYST_ROUTE_AUTHORITY,
            "retry_policy": "forbidden",
            "fallback_policy": "forbidden",
            "timeout_policy": "fail_closed",
            "provider_switching_allowed": False,
            "endpoint_switching_allowed": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
        }
    _reject_forbidden_or_authority(ref, context="Analyst model adapter ref")
    return _json_safe(ref)


def _invoke_real_model_adapter(
    adapter: Any,
    *,
    prompt: str,
    input_packet: Mapping[str, Any],
    system_prompt: str,
    license_ref: Mapping[str, Any],
    route_ref: Mapping[str, Any],
) -> Any:
    if hasattr(adapter, "invoke_once"):
        return adapter.invoke_once(
            prompt=prompt,
            input_packet=input_packet,
            system_prompt=system_prompt,
            license_ref=license_ref,
            route_ref=route_ref,
        )
    if callable(adapter):
        return adapter(
            prompt,
            system_prompt=system_prompt,
            input_packet=input_packet,
            license_ref=license_ref,
            route_ref=route_ref,
            require_json=True,
        )
    raise AnalystFindingProposalError(
        "Analyst model adapter must be callable or expose invoke_once"
    )


def _parse_structured_output(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if hasattr(value, "output_text"):
        return _parse_structured_output(getattr(value, "output_text"))
    if hasattr(value, "to_safe_diagnostic"):
        diagnostic = _safe_mapping(value.to_safe_diagnostic())
        if _bounded_int(diagnostic.get("return_code"), default=2) != 0:
            raise AnalystFindingProposalError("Analyst model route failed closed")
        return _parse_structured_output(getattr(value, "output_text", ""))
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise AnalystFindingProposalError(
                "Analyst model output was not structured JSON"
            ) from exc
        return _safe_mapping(parsed)
    raise AnalystFindingProposalError("Analyst model output type invalid")


def _validate_model_output_against_safe_input(
    proposal: Mapping[str, Any],
    input_packet: Mapping[str, Any],
) -> None:
    safe = _safe_mapping(input_packet)
    selected_ids = _candidate_ids(
        _safe_refs(safe.get("selected_answer_bearing_candidate_refs"))
    )
    adjacent_or_excluded_ids = _candidate_ids(
        [
            *_safe_refs(safe.get("adjacent_context_candidate_refs")),
            *_safe_refs(safe.get("excluded_scope_candidate_refs")),
            *_safe_refs(safe.get("unreadable_high_value_candidate_refs")),
            *_safe_refs(safe.get("overclaim_risk_candidate_refs")),
        ]
    )
    proposed_selected_ids = _candidate_ids(
        _safe_refs(proposal.get("selected_answer_bearing_candidate_refs"))
    )
    if proposed_selected_ids - selected_ids:
        raise AnalystFindingProposalError(
            "model output treated adjacent/excluded refs as answer-bearing"
        )
    proposed_answer = _safe_mapping(proposal.get("proposed_answer_claim"))
    if proposed_answer:
        if not selected_ids:
            raise AnalystFindingProposalError(
                "model output created answer claim without answer-bearing refs"
            )
        claim_ids = _candidate_ids(
            _safe_refs(proposed_answer.get("selected_answer_bearing_candidate_refs"))
        )
        if claim_ids - selected_ids:
            raise AnalystFindingProposalError(
                "model output answer claim uses non-answer-bearing refs"
            )
        binding_ref = _safe_mapping(safe.get("component_answer_type_binding_ref"))
        if proposed_answer.get("requested_answer_type") != binding_ref.get(
            "requested_answer_type"
        ):
            raise AnalystFindingProposalError(
                "model output answer claim changed requested answer type"
            )
        if proposed_answer.get("expected_value_shape") != binding_ref.get(
            "expected_value_shape"
        ):
            raise AnalystFindingProposalError(
                "model output answer claim changed expected value shape"
            )
    for claim in _safe_sequence(proposal.get("analysis_claims")):
        claim_safe = _safe_mapping(claim)
        kind = _normalize_key(claim_safe.get("analysis_claim_kind"))
        support_ids = _candidate_ids(
            _safe_refs(claim_safe.get("supporting_candidate_refs"))
        )
        adjacent_ids = _candidate_ids(
            _safe_refs(claim_safe.get("adjacent_or_excluded_candidate_refs"))
        )
        if kind in {
            ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER,
            ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION,
        } and support_ids - selected_ids:
            raise AnalystFindingProposalError(
                "model output source-grounded claim uses non-answer-bearing refs"
            )
        if kind in {
            ANALYSIS_CLAIM_KIND_CAVEAT,
            ANALYSIS_CLAIM_KIND_EXCLUSION,
            ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK,
            ANALYSIS_CLAIM_KIND_CONFLICT_RISK,
        } and adjacent_ids - adjacent_or_excluded_ids:
            raise AnalystFindingProposalError(
                "model output caveat/exclusion/risk refs are outside triage roles"
            )


def _safe_candidate_triage_records(value: Any) -> list[dict[str, Any]]:
    allowed_keys = {
        "candidate_id",
        "candidate_digest",
        "candidate_title",
        "candidate_domain",
        "candidate_url",
        "official_source_record_looking_posture",
        "readable_bounded_content_posture",
        "requested_answer_type_match_status",
        "expected_value_shape_match_status",
        "adjacent_scope_match_status",
        "excluded_adjacent_scope_hits",
        "proposed_candidate_role",
        "triage_reason_codes",
        "selected_for_dprime_review",
        "dprime_review_selection_kind",
        "dprime_review_candidate_answer_bearing",
        "dprime_review_selection_is_diagnostic_only",
        "selected_window_digest",
        "selected_window_char_count",
        "bounded_content_digest",
        "bounded_content_char_count",
        "raw_private_retention_flags",
    }
    records: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        record = _safe_mapping(item)
        safe_record = {
            key: _json_safe(record.get(key))
            for key in allowed_keys
            if key in record and record.get(key) not in (None, "", [], {}, ())
        }
        if safe_record:
            _reject_forbidden_or_authority(
                safe_record,
                context="Analyst safe candidate triage record",
            )
            records.append(safe_record)
    return records


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


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _safe_route_text(value: Any, *, limit: int) -> str | None:
    text = _clean_text(value, limit=limit)
    if not text:
        return None
    lowered = text.casefold()
    private_markers = (
        "api_key",
        "authorization:",
        "bearer ",
        "private_sentinel",
        "provider_payload",
        "raw_prompt",
        "raw_provider",
        "secret",
        "sk-",
        "token",
    )
    if any(marker in lowered for marker in private_markers):
        return "private_looking_value_not_retained"
    return text


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
    "ANALYST_FINDING_PROMPT_SCHEMA_VERSION",
    "ANALYST_FINDING_MODEL_ROUTE_SCHEMA_VERSION",
    "ANALYST_MODEL_OUTPUT_VALIDATION_SCHEMA_VERSION",
    "ANALYST_MODEL_ROLE_SMART",
    "ANALYST_SAFE_MODEL_INPUT_PACKET_SCHEMA_VERSION",
    "ANALYST_SOURCE_SUPPORT_MAP_SCHEMA_VERSION",
    "ANALYST_ROLE_SURFACE",
    "ANALYST_RUNTIME_CONSUMER",
    "ANALYST_ROUTE_AUTHORITY",
    "ANALYST_SAFE_BOUNDED_EVIDENCE_EXCERPT_MAX_CHARS",
    "ANALYSIS_CLAIM_KIND_CAVEAT",
    "ANALYSIS_CLAIM_KIND_CONFLICT_RISK",
    "ANALYSIS_CLAIM_KIND_EVIDENCE_INTERPRETATION",
    "ANALYSIS_CLAIM_KIND_EXCLUSION",
    "ANALYSIS_CLAIM_KIND_GAP",
    "ANALYSIS_CLAIM_KIND_OVERCLAIM_RISK",
    "ANALYSIS_CLAIM_KIND_PROPOSED_ANSWER",
    "AnalystFindingProposalError",
    "AnalystFindingModelAssistedLicense",
    "AnalystFindingSmartModelAdapter",
    "FINDING_STATUS_FOLLOWUP_REQUIRED",
    "FINDING_STATUS_INSUFFICIENT_EVIDENCE",
    "FINDING_STATUS_SOURCE_GROUNDED_PROPOSED",
    "FINDING_GENERATION_MODE_DETERMINISTIC",
    "FINDING_GENERATION_MODE_MODEL_ASSISTED",
    "MODEL_ADAPTER_KIND_DETERMINISTIC",
    "MODEL_ADAPTER_KIND_FAKE_TEST",
    "MODEL_ADAPTER_KIND_REAL_SMART",
    "MODEL_ASSISTED_NOT_RUN_MISSING_ADAPTER",
    "MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE",
    "MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE_AND_ADAPTER",
    "MODEL_INPUT_EVIDENCE_DEPTH_BOUNDED_EXCERPT",
    "MODEL_INPUT_EVIDENCE_DEPTH_LIMITED_NO_EXCERPT",
    "MODEL_INPUT_EVIDENCE_DEPTH_REFS_ONLY",
    "MODEL_INPUT_EVIDENCE_LIMITATION_NO_SAFE_BOUNDED_EXCERPT",
    "DETERMINISTIC_FALLBACK_ROLE_DIAGNOSTIC",
    "PRODUCT_PROOF_STATUS_BLOCKED_ANALYST_NOT_RUN",
    "PRODUCT_PROOF_STATUS_PENDING_DPRIME_VALIDATION",
    "SUPPORT_STATUS_ADJACENT_ONLY",
    "SUPPORT_STATUS_CONFLICT_OR_OVERCLAIM_RISK",
    "SUPPORT_STATUS_INSUFFICIENT_EVIDENCE",
    "SUPPORT_STATUS_SOURCE_GROUNDED_PROPOSED",
    "SUPPORT_STATUS_UNREADABLE_SOURCE_NEEDED",
    "analyst_finding_proposal_ref",
    "build_analyst_finding_safe_model_input_packet",
    "build_deterministic_analyst_finding_proposal",
    "build_fake_model_assisted_analyst_finding_proposal",
    "build_model_assisted_analyst_finding_proposal",
    "build_model_assisted_analyst_license",
    "build_analyst_finding_prompt",
    "validate_analyst_finding_proposal",
    "validate_analyst_finding_safe_model_input_packet",
    "validate_fake_model_assisted_analyst_output",
    "validate_model_assisted_analyst_output",
]
