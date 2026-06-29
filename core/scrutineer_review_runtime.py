"""RunKernel-reduced Scrutineer review posture for Analyst work product.

The Scrutineer is a supervisory review/sign-off layer over Analyst work,
admitted SemanticObservation support, ComponentCoverage posture, and follow-up
remediation state. It reviews and records posture only. It does not authorize
search, run remediation, admit SemanticObservation, reduce ComponentCoverage,
decide Sufficiency, create FinalAnswerPacket state, create Author input, create
citations, satisfy source obligations, mutate current_answer_contract, call
providers/brokers/retrieval/models, or claim product correctness.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from core.analysis_gap_followup_search_packet import (
    followup_search_intent_packet_ref_from_packet,
    validate_followup_search_intent_packet,
)
from core.evidence_relative_analysis_packet import (
    evidence_relative_analysis_packet_ref_from_packet,
    validate_evidence_relative_analysis_packet,
)

SCRUTINEER_REVIEW_SCHEMA_VERSION = "scrutineer_review_ag_scrutineer_review_01_v1"
SCRUTINEER_REVIEW_ACTION_SCHEMA_VERSION = (
    "scrutineer_review_action_ag_scrutineer_review_01_v1"
)
SCRUTINEER_REVIEW_STAGE = "scrutineer_review"
SCRUTINEER_REVIEW_REASON = "scrutineer_review_from_runkernel_reduced_record"
SCRUTINEER_REVIEW_TRACE_KEY = "scrutineer_review"
SCRUTINEER_REVIEW_OWNER = "RunKernel.ScrutineerReview"
SCRUTINEER_REVIEW_HELPER = "scrutineer_review_runtime_ag_scrutineer_review_01"

REVIEW_OUTCOMES = frozenset(
    {
        "signed_off",
        "remediation_required",
        "contested",
        "blocked",
        "not_applicable",
    }
)
REVIEW_PASS_KINDS = frozenset({"initial", "final_verification"})
ISSUE_KINDS = frozenset(
    {
        "unsupported_analyst_claim",
        "missing_semantic_observation_admission",
        "coverage_overclaim",
        "weak_source_class",
        "currentness_unresolved",
        "contradiction_unresolved",
        "scope_mismatch",
        "missing_component_coverage",
        "followup_required",
        "followup_attempt_unresolved",
        "closed_surface_violation",
        "lineage_mismatch",
    }
)

_MODE_LABELS = {
    "fast": "Fast",
    "balanced": "Balanced",
    "deep": "Deep",
}
_SUPPORT_FINDING_KIND = "possible_support_proposal"
_GOOD_COVERAGE_STATES = frozenset({"supported_with_caveats", "satisfied"})
_OVERCLAIM_COVERAGE_STATES = frozenset({"partial", "supported_with_caveats", "satisfied"})
_BAD_COVERAGE_STATES = frozenset(
    {"blocked", "conflicted", "stale", "unassessed", "unsupported"}
)
_GOOD_CURRENTNESS = frozenset({"current", "not_time_sensitive", None, ""})
_BAD_CURRENTNESS = frozenset({"stale", "stale_or_unknown", "unknown"})
_BAD_CONFLICT = frozenset({"present"})
_GOOD_CONFLICT = frozenset({"none", "resolved", "unknown", None, ""})
_WEAK_SOURCE_CLASSES = frozenset(
    {
        "blog",
        "forum",
        "social_media",
        "unknown",
        "unvetted_secondary",
        "weak_secondary",
    }
)
_CLOSED_SURFACE_FLAGS = {
    "search_authorization_created": False,
    "followup_search_authorized": False,
    "query_bundle_created": False,
    "search_result_candidate_packet_created": False,
    "fetch_read_content_packet_created": False,
    "evidence_ledger_custody_created": False,
    "semantic_observation_admitted": False,
    "component_coverage_created": False,
    "component_coverage_reduced": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "citation_created": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "author_called": False,
    "current_answer_contract_mutated": False,
    "provider_called": False,
    "live_provider_called": False,
    "broker_called": False,
    "retrieval_executed": False,
    "live_fetch_read_executed": False,
    "model_called": False,
    "product_correctness_claimed": False,
}
_RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "body",
        "bounded_text",
        "cache",
        "cookie",
        "db",
        "env",
        "full_prompt",
        "full_text",
        "full_trace",
        "headers",
        "html",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "snippet",
        "source_text",
        "text",
        "token",
        "unbounded_content",
        "unbounded_text",
    }
)
_SAFE_FALSE_RAW_RETENTION_KEYS = frozenset(
    {
        "raw_content_retained",
        "raw_headers_retained",
        "raw_model_response_retained",
        "raw_page_content_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)
_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_CLOSED_SURFACE_FLAGS,
        "answer_ready",
        "author_input_ready",
        "authorized",
        "authorized_for_search",
        "broker_invoked",
        "citation_rendered",
        "component_satisfied",
        "content_citation_eligible",
        "coverage_decision",
        "evidence_admitted",
        "evidence_created",
        "evidence_ledger_custody_created",
        "final_answer_ready",
        "final_evidence_eligible",
        "live_search_executed",
        "provider_execution_licensed",
        "query_plan_activated",
        "readiness_decided",
        "search_dispatched",
        "search_executed",
        "semantic_observation_created",
        "semantic_support_created",
        "source_obligation_support_created",
    }
)


class ScrutineerReviewRuntimeError(ValueError):
    """Raised when Scrutineer review state would exceed its authority."""


@dataclass(frozen=True, slots=True)
class ScrutineerReviewResult:
    """Compact runtime result for a RunKernel-reduced Scrutineer review."""

    review_record: Mapping[str, Any]
    review_projection: Mapping[str, Any]
    authorization_action_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_kind": "scrutineer_review_result",
            "durable_packet": False,
            "helper": SCRUTINEER_REVIEW_HELPER,
            "authorization_action_id": self.authorization_action_id,
            "review_record_ref": _review_ref(self.review_record),
            "review_projection": dict(self.review_projection),
            "search_authorized": False,
            "semantic_observation_admitted": False,
            "component_coverage_reduced": False,
            "sufficiency_decided": False,
            "final_answer_packet_created": False,
            "author_input_created": False,
        }


def build_scrutineer_review_record(
    *,
    evidence_relative_analysis_packet: Mapping[str, Any],
    mode: str = "Balanced",
    review_pass_kind: str = "initial",
    run_id: str | None = None,
    request_id: str | None = None,
    semantic_observation_admission_projection: Mapping[str, Any] | None = None,
    semantic_observation_admission_history: Sequence[Mapping[str, Any]] = (),
    component_coverage_projection: Mapping[str, Any] | None = None,
    component_coverage_history: Sequence[Mapping[str, Any]] = (),
    followup_search_intent_packet: Mapping[str, Any] | None = None,
    followup_authorization_projection: Mapping[str, Any] | None = None,
    followup_reentry_refs: Mapping[str, Any] | None = None,
    unresolved_component_posture: Mapping[str, Any] | None = None,
    red_flag_context: bool = False,
    explicit_mode_override: bool = False,
    analyst_scrutineer_disagreement: bool = False,
) -> dict[str, Any]:
    """Build a bounded Scrutineer review record from existing projections."""

    analysis_packet = validate_evidence_relative_analysis_packet(
        evidence_relative_analysis_packet
    )
    _reject_raw_private_or_dangerous(analysis_packet, context="analysis packet")
    followup_packet = _validated_followup_packet(followup_search_intent_packet)
    mode_label = _mode_label(mode)
    pass_kind = _review_pass_kind(review_pass_kind)
    clean_run_id = _required_token(
        run_id or analysis_packet.get("run_id"),
        "Scrutineer review requires run_id",
    )
    clean_request_id = _required_token(
        request_id or analysis_packet.get("request_id"),
        "Scrutineer review requires request_id",
    )
    if analysis_packet.get("run_id") != clean_run_id:
        raise ScrutineerReviewRuntimeError(
            "Scrutineer review run_id does not match analysis packet"
        )
    if analysis_packet.get("request_id") != clean_request_id:
        raise ScrutineerReviewRuntimeError(
            "Scrutineer review request_id does not match analysis packet"
        )

    admissions = _admission_refs(
        semantic_observation_admission_projection,
        semantic_observation_admission_history,
    )
    coverage_refs = _coverage_refs(
        component_coverage_projection,
        component_coverage_history,
    )
    followup_proposals = _followup_proposals(followup_packet)
    reviewed_refs = _reviewed_artifact_refs(
        analysis_packet=analysis_packet,
        admissions=admissions,
        coverage_refs=coverage_refs,
        followup_packet=followup_packet,
        followup_authorization_projection=followup_authorization_projection,
        followup_reentry_refs=followup_reentry_refs,
        unresolved_component_posture=unresolved_component_posture,
    )
    issues = _review_issues(
        analysis_packet=analysis_packet,
        admissions=admissions,
        component_coverage_projection=_safe_mapping(component_coverage_projection),
        followup_proposals=followup_proposals,
        unresolved_component_posture=_safe_mapping(unresolved_component_posture),
        review_pass_kind=pass_kind,
        analyst_scrutineer_disagreement=analyst_scrutineer_disagreement,
    )
    red_flag_triggered = bool(red_flag_context or issues)
    outcome = _review_outcome(
        mode=mode_label,
        review_pass_kind=pass_kind,
        issues=issues,
        explicit_mode_override=explicit_mode_override,
        red_flag_triggered=red_flag_triggered,
        analyst_scrutineer_disagreement=analyst_scrutineer_disagreement,
        unresolved_component_posture=_safe_mapping(unresolved_component_posture),
    )
    if outcome == "not_applicable":
        issues = ()
    contested = outcome == "contested"
    contested_reason = _contested_reason(
        issues=issues,
        analyst_scrutineer_disagreement=analyst_scrutineer_disagreement,
        unresolved_component_posture=_safe_mapping(unresolved_component_posture),
    )
    if not contested:
        contested_reason = None
    remediation_budget_recommended = outcome in {
        "remediation_required",
        "contested",
        "blocked",
    }
    record_base = _without_empty(
        {
            "schema_version": SCRUTINEER_REVIEW_SCHEMA_VERSION,
            "record_kind": "scrutineer_review_record",
            "trace_key": SCRUTINEER_REVIEW_TRACE_KEY,
            "owner": SCRUTINEER_REVIEW_OWNER,
            "helper": SCRUTINEER_REVIEW_HELPER,
            "canonical_state": False,
            "reduced_state": False,
            "proposal_packet": False,
            "run_id": clean_run_id,
            "request_id": clean_request_id,
            "mode": mode_label,
            "review_pass_kind": pass_kind,
            "red_flag_context": bool(red_flag_context),
            "red_flag_triggered": red_flag_triggered,
            "explicit_mode_override": bool(explicit_mode_override),
            "reviewed_artifact_refs": reviewed_refs,
            "review_outcome": outcome,
            "issue_count": len(issues),
            "issues": [dict(issue) for issue in issues],
            "signoff": {
                "analyst_work_signed_off": outcome == "signed_off",
                "final_answer_signed_off": False,
                "product_correctness_claimed": False,
            },
            "contested": contested,
            "contested_reason": contested_reason,
            "remediation_budget_recommended": remediation_budget_recommended,
            "balanced_remediation_loop_reserved_if_budget_permits": (
                mode_label == "Balanced" and remediation_budget_recommended
            ),
            "mode_policy": _mode_policy(
                mode=mode_label,
                red_flag_triggered=red_flag_triggered,
                explicit_mode_override=explicit_mode_override,
                remediation_budget_recommended=remediation_budget_recommended,
            ),
            "scrutineer_is_product_authority": False,
            "review_only": True,
            "authorizes_search": False,
            "runs_remediation": False,
            "admits_semantic_observation": False,
            "reduces_component_coverage": False,
            "decides_sufficiency": False,
            "creates_final_answer_packet": False,
            "creates_author_input": False,
            **_CLOSED_SURFACE_FLAGS,
            "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
        }
    )
    review_digest = _digest_json(_record_digest_payload(record_base))
    review_id = (
        "scrutineer-review:"
        f"{clean_request_id}:{pass_kind}:{review_digest[:16]}"
    )
    record = {
        **record_base,
        "review_id": review_id,
        "review_digest": review_digest,
    }
    return validate_scrutineer_review_record(record)


def reduce_scrutineer_review(
    *,
    run_kernel: Any,
    scrutineer_review_record: Mapping[str, Any],
) -> ScrutineerReviewResult:
    """Authorize and reduce one Scrutineer review record through RunKernel."""

    record = validate_scrutineer_review_record(scrutineer_review_record)
    try:
        action = run_kernel.authorize_scrutineer_review(
            scrutineer_review_record=record,
        )
        from core.run_kernel import Observation, ObservationType, RunStageStatus

        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.SCRUTINEER_REVIEW_REDUCED,
                status=RunStageStatus.COMPLETED,
                payload={"scrutineer_review_record": record},
            )
        )
    except Exception as exc:  # pragma: no cover - translated for callers/tests.
        if exc.__class__.__name__ == "RunKernelTransitionError":
            raise ScrutineerReviewRuntimeError(str(exc)) from exc
        raise
    return ScrutineerReviewResult(
        review_record=record,
        review_projection=dict(run_kernel.state.scrutineer_review_projection),
        authorization_action_id=action.action_id,
    )


def build_scrutineer_review_action_inputs(
    *,
    run_id: str,
    request_id: str,
    scrutineer_review_record: Mapping[str, Any],
) -> dict[str, Any]:
    """Build RunKernel action inputs for reducing a review record."""

    record = validate_scrutineer_review_record(scrutineer_review_record)
    clean_run_id = _required_token(run_id, "Scrutineer review action requires run_id")
    clean_request_id = _required_token(
        request_id,
        "Scrutineer review action requires request_id",
    )
    if record.get("run_id") != clean_run_id or record.get("request_id") != clean_request_id:
        raise ScrutineerReviewRuntimeError(
            "Scrutineer review record run/request lineage does not match RunKernel"
        )
    return {
        "schema_version": SCRUTINEER_REVIEW_ACTION_SCHEMA_VERSION,
        "owner": SCRUTINEER_REVIEW_OWNER,
        "trace_key": SCRUTINEER_REVIEW_TRACE_KEY,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "review_id": record["review_id"],
        "review_digest": record["review_digest"],
        "mode": record["mode"],
        "review_pass_kind": record["review_pass_kind"],
        "review_outcome": record["review_outcome"],
        "issue_count": record["issue_count"],
        "review_only": True,
        "authorizes_search": False,
        "runs_remediation": False,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def build_scrutineer_review_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    existing_review_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate reducer observation and build canonical Scrutineer state."""

    clean_action_id = _required_token(
        action_id,
        "Scrutineer review reduction requires action_id",
        limit=200,
    )
    clean_run_id = _required_token(run_id, "Scrutineer review reduction requires run_id")
    clean_request_id = _required_token(
        request_id,
        "Scrutineer review reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    if inputs.get("schema_version") != SCRUTINEER_REVIEW_ACTION_SCHEMA_VERSION:
        raise ScrutineerReviewRuntimeError("Scrutineer review action schema mismatch")
    payload = _safe_mapping(observation_payload)
    record = validate_scrutineer_review_record(
        _safe_mapping(payload.get("scrutineer_review_record"))
    )
    if record.get("run_id") != clean_run_id or record.get("request_id") != clean_request_id:
        raise ScrutineerReviewRuntimeError(
            "Scrutineer review observation run/request binding mismatch"
        )
    for key in (
        "review_id",
        "review_digest",
        "mode",
        "review_pass_kind",
        "review_outcome",
        "issue_count",
    ):
        if inputs.get(key) != record.get(key):
            raise ScrutineerReviewRuntimeError(
                f"Scrutineer review action binding mismatch for {key}"
            )
    _validate_closed_flags(inputs, context="Scrutineer review action inputs")
    existing = _safe_mapping(existing_review_projection)
    prior_history = [
        _safe_mapping(item) for item in _safe_list(existing.get("review_history"))
    ]
    if record["review_digest"] in {
        item.get("review_digest") for item in prior_history if isinstance(item, Mapping)
    }:
        raise ScrutineerReviewRuntimeError(
            "Scrutineer review record was already reduced"
        )
    history = [*prior_history, _history_entry(record, clean_action_id)]
    return {
        **record,
        "canonical_state": True,
        "reduced_state": True,
        "authorized_action_id": clean_action_id,
        "review_history": history,
        "review_count": len(history),
    }


def build_scrutineer_review_projection(
    *,
    scrutineer_review_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project canonical Scrutineer state without downstream authority."""

    state = validate_scrutineer_review_record(scrutineer_review_state)
    history = [
        _safe_mapping(item) for item in _safe_list(scrutineer_review_state.get("review_history"))
    ]
    if not history:
        history = [_history_entry(state, state.get("authorized_action_id"))]
    return {
        "owner": SCRUTINEER_REVIEW_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": SCRUTINEER_REVIEW_TRACE_KEY,
        "canonical_state": True,
        "reduced_state": True,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "review_id": state.get("review_id"),
        "review_digest": state.get("review_digest"),
        "mode": state.get("mode"),
        "review_pass_kind": state.get("review_pass_kind"),
        "review_outcome": state.get("review_outcome"),
        "issue_count": state.get("issue_count"),
        "issues": [dict(item) for item in state.get("issues") or ()],
        "reviewed_artifact_refs": _safe_mapping(state.get("reviewed_artifact_refs")),
        "latest_review": _history_entry(state, state.get("authorized_action_id")),
        "review_history": history,
        "review_count": len(history),
        "signoff": _safe_mapping(state.get("signoff")),
        "contested": state.get("contested") is True,
        "contested_reason": state.get("contested_reason"),
        "remediation_budget_recommended": (
            state.get("remediation_budget_recommended") is True
        ),
        "balanced_remediation_loop_reserved_if_budget_permits": (
            state.get("balanced_remediation_loop_reserved_if_budget_permits") is True
        ),
        "mode_policy": _safe_mapping(state.get("mode_policy")),
        "scrutineer_is_product_authority": False,
        "review_only": True,
        "authorizes_search": False,
        "runs_remediation": False,
        "admits_semantic_observation": False,
        "reduces_component_coverage": False,
        "decides_sufficiency": False,
        "creates_final_answer_packet": False,
        "creates_author_input": False,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def validate_scrutineer_review_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a Scrutineer review record and return a sanitized copy."""

    safe = _safe_mapping(record)
    if not safe:
        raise ScrutineerReviewRuntimeError("Scrutineer review record is required")
    _reject_raw_private_or_dangerous(safe, context="Scrutineer review record")
    if safe.get("schema_version") != SCRUTINEER_REVIEW_SCHEMA_VERSION:
        raise ScrutineerReviewRuntimeError("Scrutineer review schema mismatch")
    if safe.get("record_kind") != "scrutineer_review_record":
        raise ScrutineerReviewRuntimeError("Scrutineer review record kind mismatch")
    if safe.get("owner") != SCRUTINEER_REVIEW_OWNER:
        raise ScrutineerReviewRuntimeError("Scrutineer review owner mismatch")
    if safe.get("review_outcome") not in REVIEW_OUTCOMES:
        raise ScrutineerReviewRuntimeError("Scrutineer review outcome mismatch")
    if safe.get("review_pass_kind") not in REVIEW_PASS_KINDS:
        raise ScrutineerReviewRuntimeError("Scrutineer review pass kind mismatch")
    if safe.get("scrutineer_is_product_authority") is not False:
        raise ScrutineerReviewRuntimeError("Scrutineer must not be product authority")
    for key in (
        "review_only",
        "authorizes_search",
        "runs_remediation",
        "admits_semantic_observation",
        "reduces_component_coverage",
        "decides_sufficiency",
        "creates_final_answer_packet",
        "creates_author_input",
    ):
        expected = key == "review_only"
        if safe.get(key) is not expected:
            raise ScrutineerReviewRuntimeError(
                f"Scrutineer review must keep {key}={expected}"
            )
    _validate_closed_flags(safe, context="Scrutineer review record")
    signoff = _safe_mapping(safe.get("signoff"))
    if signoff.get("final_answer_signed_off") is not False:
        raise ScrutineerReviewRuntimeError("Scrutineer cannot sign off final answers")
    if signoff.get("product_correctness_claimed") is not False:
        raise ScrutineerReviewRuntimeError("Scrutineer cannot claim product correctness")
    issues = [_safe_mapping(item) for item in _safe_list(safe.get("issues"))]
    if int(safe.get("issue_count") or 0) != len(issues):
        raise ScrutineerReviewRuntimeError("Scrutineer review issue count mismatch")
    for issue in issues:
        if issue.get("issue_kind") not in ISSUE_KINDS:
            raise ScrutineerReviewRuntimeError("Scrutineer review issue kind mismatch")
    if safe.get("review_outcome") == "signed_off":
        if issues:
            raise ScrutineerReviewRuntimeError("signed-off review cannot carry issues")
        if signoff.get("analyst_work_signed_off") is not True:
            raise ScrutineerReviewRuntimeError("signed-off review must sign off Analyst work")
        if safe.get("contested") is not False:
            raise ScrutineerReviewRuntimeError("signed-off review cannot be contested")
    if safe.get("review_outcome") == "contested" and safe.get("contested") is not True:
        raise ScrutineerReviewRuntimeError("contested review must preserve contested posture")
    declared_digest = _required_token(
        safe.get("review_digest"),
        "Scrutineer review requires review_digest",
        limit=128,
    )
    if declared_digest != _digest_json(_record_digest_payload(safe)):
        raise ScrutineerReviewRuntimeError("Scrutineer review digest mismatch")
    expected_id = (
        "scrutineer-review:"
        f"{_clean_token(safe.get('request_id'), limit=120)}:"
        f"{safe.get('review_pass_kind')}:{declared_digest[:16]}"
    )
    if safe.get("review_id") != expected_id:
        raise ScrutineerReviewRuntimeError("Scrutineer review id mismatch")
    return safe


def _review_issues(
    *,
    analysis_packet: Mapping[str, Any],
    admissions: Sequence[Mapping[str, Any]],
    component_coverage_projection: Mapping[str, Any],
    followup_proposals: Sequence[Mapping[str, Any]],
    unresolved_component_posture: Mapping[str, Any],
    review_pass_kind: str,
    analyst_scrutineer_disagreement: bool,
) -> tuple[dict[str, Any], ...]:
    report = _safe_mapping(analysis_packet.get("analyst_report"))
    findings = [_safe_mapping(item) for item in _safe_list(report.get("findings"))]
    gaps = [
        _safe_mapping(item)
        for item in _safe_list(report.get("analysis_gap_proposals"))
    ]
    support_findings = [
        finding
        for finding in findings
        if finding.get("proposal_kind") == _SUPPORT_FINDING_KIND
    ]
    issues: list[dict[str, Any]] = []
    admission_components = {
        item.get("answer_component_id")
        for item in admissions
        if item.get("answer_component_id")
    }
    admission_ids = {
        item.get("observation_id")
        for item in admissions
        if item.get("observation_id")
    }
    for finding in support_findings:
        component_id = _clean_token(finding.get("component_id"), limit=260)
        if component_id not in admission_components:
            issues.append(
                _issue(
                    "missing_semantic_observation_admission",
                    severity="high",
                    component_id=component_id,
                    finding_ref=_finding_ref(finding),
                    recommended_remediation=(
                        "Admit eligible support through the existing "
                        "SemanticObservation admission bridge before coverage review."
                    ),
                )
            )
            issues.append(
                _issue(
                    "unsupported_analyst_claim",
                    severity="high",
                    component_id=component_id,
                    finding_ref=_finding_ref(finding),
                    recommended_remediation=(
                        "Keep Analyst support proposal contested until admitted "
                        "SemanticObservation and custody lineage exist."
                    ),
                )
            )

    coverage = _safe_mapping(component_coverage_projection)
    if coverage:
        issues.extend(
            _coverage_issues(
                coverage=coverage,
                admission_ids=admission_ids,
                admission_components=admission_components,
                support_findings=support_findings,
            )
        )
    elif support_findings or admissions:
        component_id = _first_component_id(support_findings, admissions)
        issues.append(
            _issue(
                "missing_component_coverage",
                severity="high",
                component_id=component_id,
                recommended_remediation=(
                    "Reduce ComponentCoverage through the existing reducer "
                    "after SemanticObservation admission."
                ),
            )
        )

    for gap in gaps:
        followup_ref = _matching_followup_proposal_ref(gap, followup_proposals)
        issues.append(_issue_for_gap(gap, followup_ref=followup_ref))
    for proposal in followup_proposals:
        source_class = _clean_token(
            proposal.get("required_source_class_hint"),
            limit=260,
        )
        if source_class in _WEAK_SOURCE_CLASSES:
            issues.append(
                _issue(
                    "weak_source_class",
                    severity="medium",
                    component_id=_clean_token(proposal.get("component_id"), limit=260),
                    followup_proposal_ref=_proposal_ref(proposal),
                    recommended_remediation=(
                        "Use the existing follow-up intent packet to propose a "
                        "stronger official/current source class; Scrutineer "
                        "does not authorize that search."
                    ),
                )
            )
    if unresolved_component_posture:
        issues.extend(
            _unresolved_posture_issues(
                unresolved_component_posture,
                review_pass_kind=review_pass_kind,
            )
        )
    if analyst_scrutineer_disagreement:
        issues.append(
            _issue(
                "contradiction_unresolved",
                severity="high",
                recommended_remediation=(
                    "Preserve contested posture until Analyst/Scrutineer "
                    "disagreement is resolved by admitted support."
                ),
            )
        )
    return _dedupe_issues(issues)


def _coverage_issues(
    *,
    coverage: Mapping[str, Any],
    admission_ids: set[str],
    admission_components: set[str],
    support_findings: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    coverage_state = _clean_token(coverage.get("coverage_state"), limit=80)
    semantic_status = _clean_token(coverage.get("semantic_support_status"), limit=80)
    component_id = _clean_token(coverage.get("answer_component_id"), limit=260)
    accepted_refs = [
        _safe_mapping(item)
        for item in _safe_list(coverage.get("accepted_observation_refs"))
    ]
    if coverage_state in _OVERCLAIM_COVERAGE_STATES or semantic_status == "supported":
        if not accepted_refs or not admission_ids:
            issues.append(
                _issue(
                    "coverage_overclaim",
                    severity="high",
                    component_id=component_id,
                    coverage_ref=_coverage_ref(coverage),
                    recommended_remediation=(
                        "Do not present ComponentCoverage as supported until "
                        "admitted SemanticObservation refs are present."
                    ),
                )
            )
        for ref in accepted_refs:
            if ref.get("observation_id") not in admission_ids:
                issues.append(
                    _issue(
                        "lineage_mismatch",
                        severity="high",
                        component_id=component_id,
                        coverage_ref=_coverage_ref(coverage),
                        source_ref={"observation_id": ref.get("observation_id")},
                        recommended_remediation=(
                            "Align ComponentCoverage accepted_observation_refs "
                            "with RunKernel-admitted SemanticObservation history."
                        ),
                    )
                )
    if component_id and admission_components and component_id not in admission_components:
        issues.append(
            _issue(
                "lineage_mismatch",
                severity="high",
                component_id=component_id,
                coverage_ref=_coverage_ref(coverage),
                recommended_remediation=(
                    "Coverage component lineage must match admitted "
                    "SemanticObservation component lineage."
                ),
            )
        )
    if coverage_state == "satisfied" and coverage.get("source_obligation_status") not in {
        "satisfied",
        "not_applicable",
    }:
        issues.append(
            _issue(
                "coverage_overclaim",
                severity="high",
                component_id=component_id,
                coverage_ref=_coverage_ref(coverage),
                recommended_remediation=(
                    "Do not upgrade ComponentCoverage to satisfied while source "
                    "obligations remain partial, unknown, or unsatisfied."
                ),
            )
        )
    if coverage_state in _BAD_COVERAGE_STATES and (support_findings or admission_ids):
        issues.append(
            _issue(
                "missing_component_coverage",
                severity="medium",
                component_id=component_id,
                coverage_ref=_coverage_ref(coverage),
                recommended_remediation=(
                    "Preserve blocker posture or reduce a supported coverage "
                    "record after admitted support is available."
                ),
            )
        )
    if coverage.get("followup_need") in {"required", "blocked"}:
        issues.append(
            _issue(
                "followup_required",
                severity="medium",
                component_id=component_id,
                coverage_ref=_coverage_ref(coverage),
                recommended_remediation=(
                    "If a matching FollowupSearchIntent exists, route it through "
                    "RunKernel follow-up authorization; Scrutineer only points "
                    "to the need."
                ),
            )
        )
    if coverage.get("currentness_posture") in _BAD_CURRENTNESS:
        issues.append(
            _issue(
                "currentness_unresolved",
                severity="high",
                component_id=component_id,
                coverage_ref=_coverage_ref(coverage),
                recommended_remediation=(
                    "Resolve currentness through admitted current support or "
                    "preserve stale/blocked posture."
                ),
            )
        )
    if coverage.get("conflict_posture") not in _GOOD_CONFLICT:
        issues.append(
            _issue(
                "contradiction_unresolved",
                severity="high",
                component_id=component_id,
                coverage_ref=_coverage_ref(coverage),
                recommended_remediation=(
                    "Preserve contested posture until contradiction is resolved."
                ),
            )
        )
    return issues


def _issue_for_gap(
    gap: Mapping[str, Any],
    *,
    followup_ref: Mapping[str, Any],
) -> dict[str, Any]:
    kind = _clean_token(gap.get("gap_kind") or gap.get("source_gap_kind"), limit=120)
    issue_kind = {
        "currentness_concern": "currentness_unresolved",
        "possible_contradiction": "contradiction_unresolved",
        "scope_mismatch": "scope_mismatch",
    }.get(kind or "", "followup_required")
    return _issue(
        issue_kind,
        severity="high" if issue_kind != "followup_required" else "medium",
        component_id=_clean_token(gap.get("component_id"), limit=260),
        finding_ref=_gap_ref(gap),
        followup_proposal_ref=followup_ref,
        recommended_remediation=(
            "Reference the matching FollowupSearchIntent proposal and use the "
            "existing RunKernel follow-up authorization/reentry path if budget "
            "permits. Scrutineer does not authorize search."
        )
        if followup_ref
        else "Create or preserve an Analyst follow-up gap; Scrutineer does not authorize search.",
    )


def _unresolved_posture_issues(
    posture: Mapping[str, Any],
    *,
    review_pass_kind: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if (
        posture.get("support_admitted") is False
        or posture.get("coverage_reduced") is False
        or posture.get("followup_need") in {"required", "blocked"}
    ):
        issues.append(
            _issue(
                "followup_attempt_unresolved",
                severity="high" if review_pass_kind == "final_verification" else "medium",
                component_id=_clean_token(posture.get("component_id"), limit=260),
                recommended_remediation=(
                    "Preserve unresolved follow-up posture; do not create false "
                    "support or coverage from a failed remediation attempt."
                ),
            )
        )
    if posture.get("currentness_posture") in _BAD_CURRENTNESS:
        issues.append(
            _issue(
                "currentness_unresolved",
                severity="high",
                component_id=_clean_token(posture.get("component_id"), limit=260),
                recommended_remediation="Keep stale/currentness posture contested or blocked.",
            )
        )
    if posture.get("posture") == "contested" or posture.get("coverage_state") == "contested":
        issues.append(
            _issue(
                "contradiction_unresolved",
                severity="high",
                component_id=_clean_token(posture.get("component_id"), limit=260),
                recommended_remediation="Preserve contested posture after failed remediation.",
            )
        )
    return issues


def _review_outcome(
    *,
    mode: str,
    review_pass_kind: str,
    issues: Sequence[Mapping[str, Any]],
    explicit_mode_override: bool,
    red_flag_triggered: bool,
    analyst_scrutineer_disagreement: bool,
    unresolved_component_posture: Mapping[str, Any],
) -> str:
    if mode == "Fast" and not explicit_mode_override:
        return "not_applicable"
    if mode == "Balanced" and not red_flag_triggered and not explicit_mode_override:
        return "not_applicable"
    if not issues:
        return "signed_off"
    issue_kinds = {issue.get("issue_kind") for issue in issues}
    if (
        analyst_scrutineer_disagreement
        or unresolved_component_posture.get("posture") == "contested"
        or unresolved_component_posture.get("coverage_state") == "contested"
        or (
            review_pass_kind == "final_verification"
            and issue_kinds
            & {
                "followup_attempt_unresolved",
                "unsupported_analyst_claim",
                "missing_semantic_observation_admission",
                "contradiction_unresolved",
            }
        )
    ):
        return "contested"
    if issue_kinds == {"closed_surface_violation"}:
        return "blocked"
    return "remediation_required"


def _contested_reason(
    *,
    issues: Sequence[Mapping[str, Any]],
    analyst_scrutineer_disagreement: bool,
    unresolved_component_posture: Mapping[str, Any],
) -> str | None:
    if analyst_scrutineer_disagreement:
        return "Analyst and Scrutineer disagreement remains unresolved."
    if unresolved_component_posture.get("posture") == "contested":
        return "Follow-up remediation remains contested."
    kinds = {issue.get("issue_kind") for issue in issues}
    if "contradiction_unresolved" in kinds:
        return "Contradiction remains unresolved."
    if "followup_attempt_unresolved" in kinds:
        return "Follow-up attempt did not resolve support."
    return "Scrutineer review preserves contested posture."


def _reviewed_artifact_refs(
    *,
    analysis_packet: Mapping[str, Any],
    admissions: Sequence[Mapping[str, Any]],
    coverage_refs: Sequence[Mapping[str, Any]],
    followup_packet: Mapping[str, Any],
    followup_authorization_projection: Mapping[str, Any] | None,
    followup_reentry_refs: Mapping[str, Any] | None,
    unresolved_component_posture: Mapping[str, Any] | None,
) -> dict[str, Any]:
    report = _safe_mapping(analysis_packet.get("analyst_report"))
    return _without_empty(
        {
            "analysis_packet_ref": evidence_relative_analysis_packet_ref_from_packet(
                analysis_packet
            ),
            "analyst_report_ref": _without_empty(
                {
                    "report_id": report.get("report_id"),
                    "report_digest": report.get("report_digest"),
                    "schema_version": report.get("schema_version"),
                    "finding_count": report.get("finding_count"),
                    "analysis_gap_proposal_count": report.get(
                        "analysis_gap_proposal_count"
                    ),
                }
            ),
            "semantic_observation_admission_refs": [dict(item) for item in admissions],
            "component_coverage_refs": [dict(item) for item in coverage_refs],
            "followup_search_intent_ref": followup_search_intent_packet_ref_from_packet(
                followup_packet
            )
            if followup_packet
            else {},
            "followup_authorization_refs": _followup_authorization_refs(
                followup_authorization_projection
            ),
            "followup_reentry_refs": _safe_mapping(followup_reentry_refs),
            "unresolved_component_posture_ref": _posture_ref(
                unresolved_component_posture
            ),
        }
    )


def _admission_refs(
    projection: Mapping[str, Any] | None,
    history: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    refs: list[dict[str, Any]] = []
    for item in [*list(history or ()), projection or {}]:
        mapped = _safe_mapping(item)
        if not mapped:
            continue
        ref = _without_empty(
            {
                "authorized_action_id": mapped.get("authorized_action_id"),
                "observation_id": mapped.get("observation_id"),
                "observation_digest": mapped.get("observation_digest"),
                "answer_component_id": mapped.get("answer_component_id"),
                "component_revision": mapped.get("component_revision"),
                "component_digest": mapped.get("component_digest"),
                "content_refs": list(mapped.get("content_refs") or []),
                "evidence_refs": list(mapped.get("evidence_refs") or []),
            }
        )
        if ref:
            refs.append(ref)
    return tuple(_dedupe_by_digest(refs, "observation_digest"))


def _coverage_refs(
    projection: Mapping[str, Any] | None,
    history: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    refs: list[dict[str, Any]] = []
    for item in [*list(history or ()), projection or {}]:
        mapped = _safe_mapping(item)
        if not mapped:
            continue
        refs.append(_coverage_ref(mapped))
    return tuple(_dedupe_by_digest(refs, "coverage_record_digest"))


def _followup_proposals(packet: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(
        _safe_mapping(item)
        for item in _safe_list(packet.get("analysis_gap_search_proposals"))
        if _safe_mapping(item)
    )


def _validated_followup_packet(packet: Mapping[str, Any] | None) -> dict[str, Any]:
    if not packet:
        return {}
    safe = validate_followup_search_intent_packet(packet)
    _reject_raw_private_or_dangerous(safe, context="follow-up intent packet")
    return safe


def _followup_authorization_refs(
    projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    mapped = _safe_mapping(projection)
    if not mapped:
        return {}
    latest = _safe_mapping(mapped.get("latest_authorization"))
    return _without_empty(
        {
            "owner": mapped.get("owner"),
            "authorized_loop_count": mapped.get("authorized_loop_count"),
            "latest_authorization": {
                "authorization_id": latest.get("authorization_id"),
                "authorization_digest": latest.get("authorization_digest"),
                "query_count": latest.get("query_count"),
                "handoff_id": latest.get("handoff_id"),
                "handoff_digest": latest.get("handoff_digest"),
                "fixture_reentry_only": True,
                "live_dispatch_allowed": False,
            },
        }
    )


def _matching_followup_proposal_ref(
    gap: Mapping[str, Any],
    proposals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    gap_id = _clean_token(gap.get("gap_id") or gap.get("source_gap_id"), limit=320)
    gap_digest = _clean_token(
        gap.get("gap_digest") or gap.get("source_gap_digest"),
        limit=128,
    )
    component_id = _clean_token(gap.get("component_id"), limit=260)
    kind = _clean_token(gap.get("gap_kind") or gap.get("source_gap_kind"), limit=120)
    for proposal in proposals:
        if (
            (gap_id and proposal.get("source_gap_id") == gap_id)
            or (gap_digest and proposal.get("source_gap_digest") == gap_digest)
            or (
                component_id
                and kind
                and proposal.get("component_id") == component_id
                and proposal.get("source_gap_kind") == kind
            )
        ):
            return _proposal_ref(proposal)
    return {}


def _proposal_ref(proposal: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "proposal_id": proposal.get("proposal_id"),
            "proposal_digest": proposal.get("proposal_digest"),
            "source_gap_id": proposal.get("source_gap_id"),
            "source_gap_kind": proposal.get("source_gap_kind"),
            "component_id": proposal.get("component_id"),
            "ready_for_authorization_review": proposal.get(
                "ready_for_authorization_review"
            ),
            "authorized": False,
            "search_dispatched": False,
        }
    )


def _finding_ref(finding: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "finding_id": finding.get("finding_id"),
            "finding_digest": finding.get("finding_digest"),
            "proposal_kind": finding.get("proposal_kind"),
            "component_id": finding.get("component_id"),
            "candidate_id": finding.get("candidate_id"),
            "candidate_digest": finding.get("candidate_digest"),
            "reference_id": finding.get("reference_id"),
            "reference_digest": finding.get("reference_digest"),
        }
    )


def _gap_ref(gap: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "gap_id": gap.get("gap_id") or gap.get("source_gap_id"),
            "gap_digest": gap.get("gap_digest") or gap.get("source_gap_digest"),
            "gap_kind": gap.get("gap_kind") or gap.get("source_gap_kind"),
            "component_id": gap.get("component_id"),
            "trigger_reference_id": gap.get("trigger_reference_id")
            or gap.get("reference_id"),
            "trigger_reference_digest": gap.get("trigger_reference_digest")
            or gap.get("reference_digest"),
        }
    )


def _coverage_ref(coverage: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "coverage_record_id": coverage.get("coverage_record_id")
            or coverage.get("record_id"),
            "coverage_record_digest": coverage.get("coverage_record_digest")
            or coverage.get("record_digest"),
            "coverage_reduction_digest": coverage.get("coverage_reduction_digest"),
            "answer_component_id": coverage.get("answer_component_id"),
            "component_revision": coverage.get("component_revision"),
            "component_digest": coverage.get("component_digest"),
            "coverage_state": coverage.get("coverage_state"),
            "semantic_support_status": coverage.get("semantic_support_status"),
            "currentness_posture": coverage.get("currentness_posture"),
            "followup_need": coverage.get("followup_need"),
        }
    )


def _posture_ref(posture: Mapping[str, Any] | None) -> dict[str, Any]:
    mapped = _safe_mapping(posture)
    if not mapped:
        return {}
    return _without_empty(
        {
            "posture": mapped.get("posture"),
            "coverage_state": mapped.get("coverage_state"),
            "semantic_support_status": mapped.get("semantic_support_status"),
            "followup_need": mapped.get("followup_need"),
            "currentness_posture": mapped.get("currentness_posture"),
            "analysis_gap_count": mapped.get("analysis_gap_count"),
            "gap_kinds": list(mapped.get("gap_kinds") or []),
            "support_admitted": mapped.get("support_admitted"),
            "coverage_reduced": mapped.get("coverage_reduced"),
            "posture_digest": _digest_json(mapped),
        }
    )


def _issue(
    issue_kind: str,
    *,
    severity: str,
    component_id: str | None = None,
    source_ref: Mapping[str, Any] | None = None,
    custody_ref: Mapping[str, Any] | None = None,
    finding_ref: Mapping[str, Any] | None = None,
    coverage_ref: Mapping[str, Any] | None = None,
    recommended_remediation: str | None = None,
    followup_proposal_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if issue_kind not in ISSUE_KINDS:
        raise ScrutineerReviewRuntimeError(f"unsupported Scrutineer issue kind: {issue_kind}")
    issue_base = _without_empty(
        {
            "issue_kind": issue_kind,
            "severity": severity,
            "component_id": component_id,
            "source_ref": _safe_mapping(source_ref),
            "custody_ref": _safe_mapping(custody_ref),
            "finding_ref": _safe_mapping(finding_ref),
            "coverage_ref": _safe_mapping(coverage_ref),
            "recommended_remediation": _clean_text(
                recommended_remediation,
                limit=500,
            ),
            "followup_proposal_ref": _safe_mapping(followup_proposal_ref),
            "scrutineer_authorizes_followup": False,
        }
    )
    issue_digest = _digest_json(issue_base)
    issue_id = (
        "scrutineer-issue:"
        f"{issue_kind}:{_clean_token(component_id, limit=80) or 'run'}:{issue_digest[:16]}"
    )
    return {
        **issue_base,
        "issue_id": issue_id,
        "issue_digest": issue_digest,
    }


def _dedupe_issues(issues: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for issue in issues:
        digest = _clean_token(issue.get("issue_digest"), limit=128)
        if digest and digest in seen:
            continue
        if digest:
            seen.add(digest)
        out.append(dict(issue))
    return tuple(out)


def _dedupe_by_digest(
    records: Sequence[Mapping[str, Any]],
    digest_key: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in records:
        digest = _clean_token(item.get(digest_key), limit=128)
        fallback = _digest_json(item)
        key = digest or fallback
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(item))
    return out


def _first_component_id(
    support_findings: Sequence[Mapping[str, Any]],
    admissions: Sequence[Mapping[str, Any]],
) -> str | None:
    for finding in support_findings:
        component_id = _clean_token(finding.get("component_id"), limit=260)
        if component_id:
            return component_id
    for admission in admissions:
        component_id = _clean_token(admission.get("answer_component_id"), limit=260)
        if component_id:
            return component_id
    return None


def _history_entry(record: Mapping[str, Any], action_id: Any) -> dict[str, Any]:
    return {
        "review_id": record.get("review_id"),
        "review_digest": record.get("review_digest"),
        "authorized_action_id": action_id,
        "mode": record.get("mode"),
        "review_pass_kind": record.get("review_pass_kind"),
        "review_outcome": record.get("review_outcome"),
        "issue_count": record.get("issue_count"),
        "contested": record.get("contested") is True,
        "remediation_budget_recommended": (
            record.get("remediation_budget_recommended") is True
        ),
        "analyst_work_signed_off": _safe_mapping(record.get("signoff")).get(
            "analyst_work_signed_off"
        )
        is True,
        "final_answer_signed_off": False,
        "product_correctness_claimed": False,
    }


def _review_ref(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "review_id": record.get("review_id"),
        "review_digest": record.get("review_digest"),
        "review_outcome": record.get("review_outcome"),
        "issue_count": record.get("issue_count"),
    }


def _mode_policy(
    *,
    mode: str,
    red_flag_triggered: bool,
    explicit_mode_override: bool,
    remediation_budget_recommended: bool,
) -> dict[str, Any]:
    return {
        "fast_scrutineer_default_enabled": False,
        "fast_invocation_requires_explicit_override": True,
        "balanced_red_flag_triggered": mode == "Balanced" and red_flag_triggered,
        "balanced_requires_red_flag_context": True,
        "balanced_remediation_loop_reserved_if_budget_permits": (
            mode == "Balanced" and remediation_budget_recommended
        ),
        "deep_scrutineer_required_later": mode == "Deep",
        "deep_orchestration_implemented": False,
        "explicit_mode_override": bool(explicit_mode_override),
    }


def _review_pass_kind(value: Any) -> str:
    text = _clean_token(value, limit=80)
    if text not in REVIEW_PASS_KINDS:
        raise ScrutineerReviewRuntimeError(
            "Scrutineer review_pass_kind must be initial or final_verification"
        )
    return text


def _mode_label(mode: Any) -> str:
    label = _MODE_LABELS.get(str(_clean_token(mode, limit=40) or "").casefold())
    if not label:
        raise ScrutineerReviewRuntimeError(
            "Scrutineer review mode must be Fast, Balanced, or Deep"
        )
    return label


def _validate_closed_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if value.get(key) is not expected:
            raise ScrutineerReviewRuntimeError(f"{context} must keep {key}=False")
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if flags.get(key) is not expected:
            raise ScrutineerReviewRuntimeError(
                f"{context} closed_surface_flags must keep {key}=False"
            )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise ScrutineerReviewRuntimeError(
            f"{context} opens closed surfaces: " + ", ".join(dangerous)
        )


def _reject_raw_private_or_dangerous(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    raw_or_private = sorted(key for key in keys if _is_raw_or_private_key(key))
    if raw_or_private:
        raise ScrutineerReviewRuntimeError(
            f"{context} contains raw/private fields: " + ", ".join(raw_or_private)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise ScrutineerReviewRuntimeError(
            f"{context} opens closed runtime surfaces: " + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _normalize_key(key)
            if token in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(token)
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


def _is_raw_or_private_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in _SAFE_FALSE_RAW_RETENTION_KEYS:
        return False
    return normalized.startswith("raw_") or normalized in _RAW_OR_PRIVATE_KEYS


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    safe = _json_safe(list(value))
    return list(safe) if isinstance(safe, list) else []


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=1_000)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key:
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=300)


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise ScrutineerReviewRuntimeError(message)
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def _record_digest_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(record)
    for key in (
        "review_id",
        "review_digest",
        "authorized_action_id",
        "review_history",
        "review_count",
    ):
        payload.pop(key, None)
    payload["canonical_state"] = False
    payload["reduced_state"] = False
    return payload


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ISSUE_KINDS",
    "REVIEW_OUTCOMES",
    "SCRUTINEER_REVIEW_ACTION_SCHEMA_VERSION",
    "SCRUTINEER_REVIEW_HELPER",
    "SCRUTINEER_REVIEW_OWNER",
    "SCRUTINEER_REVIEW_REASON",
    "SCRUTINEER_REVIEW_SCHEMA_VERSION",
    "SCRUTINEER_REVIEW_STAGE",
    "SCRUTINEER_REVIEW_TRACE_KEY",
    "ScrutineerReviewResult",
    "ScrutineerReviewRuntimeError",
    "build_scrutineer_review_action_inputs",
    "build_scrutineer_review_projection",
    "build_scrutineer_review_record",
    "build_scrutineer_review_state",
    "reduce_scrutineer_review",
    "validate_scrutineer_review_record",
]
