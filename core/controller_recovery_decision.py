"""AG-74D Controller-owned official/current recovery retry/stop decision table.

The helper is pure decision glue. It observes ledger/source-obligation facts and
returns the Controller-owned retry/stop posture for the existing recovery
executor; it does not route providers, change search depth, alter queries, rank
sources, classify sources, or affect final answer behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from core.controller_evidence_ledger import CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY

CONTROLLER_RECOVERY_DECISION_TRACE_KEY = "controller_recovery_decision_trace"
CONTROLLER_RECOVERY_DECISION_SCHEMA_VERSION = (
    "controller_recovery_retry_stop_decision_ag74d_v1"
)

STOP_SUFFICIENT = "stop_sufficient"
STOP_INSUFFICIENT = "stop_insufficient"
STOP_LEGACY_CUSTODY_GAP = "stop_legacy_custody_gap"
RETRY_RECOVERY = "retry_recovery"
REQUEST_PROVIDER_SEARCH_REVIEW = "request_provider_search_review"
CONTINUE_DOWNSTREAM = "continue_downstream"
STOP_FOR_ARCHITECTURE_DECISION = "stop_for_architecture_decision"

_UNKNOWN = "unknown"
_NOT_OBSERVABLE = "not_observable"
_OFFICIAL_CURRENT_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)
_DECISIONS = frozenset(
    {
        STOP_SUFFICIENT,
        STOP_INSUFFICIENT,
        STOP_LEGACY_CUSTODY_GAP,
        RETRY_RECOVERY,
        REQUEST_PROVIDER_SEARCH_REVIEW,
        CONTINUE_DOWNSTREAM,
        STOP_FOR_ARCHITECTURE_DECISION,
    }
)


@dataclass(frozen=True)
class ControllerRecoveryDecision:
    """Controller-owned recovery decision record."""

    payload: dict[str, Any]

    @property
    def decision(self) -> str:
        return str(self.payload["decision"])

    @property
    def retry_allowed(self) -> bool:
        return bool(self.payload["retry_allowed"])

    @property
    def provider_search_review_requested(self) -> bool:
        return bool(self.payload["provider_search_review_requested"])

    def to_trace(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLER_RECOVERY_DECISION_SCHEMA_VERSION,
            "trace_mode": "controller_owned_recovery_retry_stop_decision",
            "ControllerRecoveryDecision": dict(self.payload),
        }

    def to_trace_fields(self) -> dict[str, Any]:
        return {
            CONTROLLER_RECOVERY_DECISION_TRACE_KEY: self.to_trace(),
            "controller_recovery_decision": self.decision,
            "controller_recovery_decision_reason": self.payload[
                "decision_reason"
            ],
            "controller_recovery_retry_allowed": self.retry_allowed,
            "controller_recovery_allowed_executor_action": self.payload[
                "allowed_executor_action"
            ],
            "controller_recovery_provider_search_review_requested": (
                self.provider_search_review_requested
            ),
            "controller_recovery_old_path_subordinated": self.payload[
                "old_path_subordinated"
            ],
        }

    def to_executor_trace_fields(self) -> dict[str, Any]:
        return {
            "recovery_decision_trace": self.to_trace(),
            "recovery_decision": self.decision,
            "recovery_decision_reason": self.payload["decision_reason"],
            "recovery_retry_allowed": self.retry_allowed,
            "recovery_allowed_executor_action": self.payload[
                "allowed_executor_action"
            ],
            "recovery_provider_search_review_requested": (
                self.provider_search_review_requested
            ),
            "recovery_old_path_subordinated": self.payload[
                "old_path_subordinated"
            ],
        }


def build_controller_recovery_decision(
    runtime_trace: Mapping[str, Any] | None,
) -> ControllerRecoveryDecision:
    """Map ledger/source-obligation facts to one Controller recovery decision."""

    trace = _safe_mapping(runtime_trace)
    ledger_custody = _ledger_custody(trace)
    ledger_status = _text(
        _first_present(
            trace.get("final_evidence_citation_custody_status"),
            ledger_custody.get("status"),
        )
    )
    custody_complete = _bool_or_unknown(
        _first_present(
            trace.get("final_evidence_citation_custody_complete"),
            ledger_custody.get("custody_complete"),
        )
    )
    legacy_gap_types = _string_list(
        _first_present(
            trace.get("ledger_legacy_gap_types"),
            ledger_custody.get("legacy_gap_types"),
        )
    )
    source_classes = _source_classes(trace)
    source_obligation_status = _source_obligation_status(trace, source_classes)
    budget_state = _recovery_budget_state(trace)
    candidate_state = _candidate_state_summary(trace)
    gate_authoritative = _controller_gate_authoritative(
        trace=trace,
        ledger_status=ledger_status,
        source_classes=source_classes,
        source_obligation_status=source_obligation_status,
    )

    decision, reason = _decide(
        ledger_status=ledger_status,
        custody_complete=custody_complete,
        legacy_gap_types=legacy_gap_types,
        source_obligation_status=source_obligation_status,
        budget_state=budget_state,
        candidate_state=candidate_state,
        gate_authoritative=gate_authoritative,
    )
    if decision not in _DECISIONS:
        decision = STOP_FOR_ARCHITECTURE_DECISION
        reason = "decision_table_returned_unknown_decision"

    payload = {
        "schema_version": CONTROLLER_RECOVERY_DECISION_SCHEMA_VERSION,
        "decision_owner": "ControllerEvidenceLedger",
        "requirement_id": _text(trace.get("requirement_id")),
        "required_source_class": source_classes,
        "ledger_custody_status": ledger_status,
        "source_obligation_status": source_obligation_status,
        "candidate_state_summary": candidate_state,
        "recovery_budget_state": budget_state,
        "decision": decision,
        "decision_reason": reason,
        "allowed_executor_action": _allowed_executor_action(decision, reason),
        "provider_search_review_requested": (
            decision == REQUEST_PROVIDER_SEARCH_REVIEW
        ),
        "retry_allowed": decision == RETRY_RECOVERY,
        "retry_reason": reason if decision == RETRY_RECOVERY else None,
        "stop_reason": reason if decision.startswith("stop_") else None,
        "architecture_stop_reason": (
            reason if decision == STOP_FOR_ARCHITECTURE_DECISION else None
        ),
        "legacy_gap_types": legacy_gap_types,
        "old_path_subordinated": [
            "source_class_recovery_executor_action_gate",
            "official_canonical_recovery_visibility_export",
        ],
        "controller_gate_authoritative": gate_authoritative,
        "diagnostic_only": False,
        "behavior_changed": False,
        "provider_policy_unchanged": True,
        "provider_selection_unchanged": True,
        "depth_policy_unchanged": True,
        "query_strategy_unchanged": True,
        "source_classification_unchanged": True,
        "candidate_fit_unchanged": True,
        "final_answer_behavior_unchanged": True,
    }
    return ControllerRecoveryDecision(payload=payload)


def controller_recovery_executor_allows_attempt(
    decision: ControllerRecoveryDecision,
) -> bool:
    """Return whether the mechanical executor may spend the recovery action."""

    payload = decision.payload
    if payload.get("controller_gate_authoritative") is not True:
        return True
    return decision.retry_allowed


def _decide(
    *,
    ledger_status: str,
    custody_complete: Any,
    legacy_gap_types: list[str],
    source_obligation_status: str,
    budget_state: str,
    candidate_state: str,
    gate_authoritative: bool,
) -> tuple[str, str]:
    if ledger_status == "controller_complete" and custody_complete is True:
        return CONTINUE_DOWNSTREAM, "controller_complete_custody_no_retry"
    if custody_complete is True and ledger_status != "controller_complete":
        return (
            STOP_FOR_ARCHITECTURE_DECISION,
            "contradictory_ledger_custody_status",
        )
    if ledger_status == "legacy_gap_observed" or legacy_gap_types:
        return STOP_LEGACY_CUSTODY_GAP, "legacy_gap_observed_not_success"
    if ledger_status == "missing_controller_disposition":
        return (
            STOP_FOR_ARCHITECTURE_DECISION,
            "missing_controller_disposition_not_aggregate_success",
        )
    if candidate_state == "selected_complete_official_current_evidence_exists":
        return CONTINUE_DOWNSTREAM, "selected_official_current_evidence_exists"
    if candidate_state == "candidate_acquired_but_unreadable":
        return STOP_INSUFFICIENT, "readability_post_provider_issue"
    if candidate_state == "candidate_readable_but_misclassified":
        return STOP_INSUFFICIENT, "classification_issue"
    if candidate_state == "candidate_classified_but_fit_rejected":
        return STOP_INSUFFICIENT, "fit_currentness_issue"
    if candidate_state == "no_plausible_official_current_candidate_acquired":
        if budget_state == "available":
            return RETRY_RECOVERY, "no_candidate_acquired_retry_within_budget"
        return (
            REQUEST_PROVIDER_SEARCH_REVIEW,
            "no_candidate_acquired_provider_search_review_needed",
        )
    if budget_state == "exhausted" and source_obligation_status.endswith("_unmet"):
        return STOP_INSUFFICIENT, "recovery_budget_exhausted_obligation_unmet"
    if (
        source_obligation_status.endswith("_unmet")
        and budget_state == "available"
        and gate_authoritative
    ):
        return RETRY_RECOVERY, "official_current_obligation_unmet_retry_available"
    if source_obligation_status == "not_required_or_satisfied":
        return STOP_SUFFICIENT, "official_current_obligation_satisfied_no_retry"
    return STOP_FOR_ARCHITECTURE_DECISION, "unknown_or_contradictory_recovery_state"


def _allowed_executor_action(decision: str, reason: str) -> str:
    if decision == RETRY_RECOVERY:
        return "execute_existing_recovery_action"
    if reason == "readability_post_provider_issue":
        return "record_readability_post_provider_issue"
    if reason == "classification_issue":
        return "record_classification_issue"
    if reason == "fit_currentness_issue":
        return "record_fit_currentness_issue"
    if decision == REQUEST_PROVIDER_SEARCH_REVIEW:
        return "record_provider_search_review_request"
    return "no_recovery_executor_action"


def _controller_gate_authoritative(
    *,
    trace: Mapping[str, Any],
    ledger_status: str,
    source_classes: list[str],
    source_obligation_status: str,
) -> bool:
    if ledger_status not in {"", _UNKNOWN, _NOT_OBSERVABLE}:
        return True
    if source_obligation_status.endswith("_unmet"):
        return True
    if any(item in _OFFICIAL_CURRENT_CLASSES for item in source_classes):
        return True
    return trace.get("active_source_class_recovery_official_canonical_admitted") is True


def _candidate_state_summary(trace: Mapping[str, Any]) -> str:
    final_selected = _int_or_unknown(
        trace.get("final_selected_authority_evidence_count")
    )
    final_evidence = _int_or_unknown(
        trace.get("final_evidence_official_or_canonical_count")
    )
    final_citation = _int_or_unknown(
        trace.get("final_citation_official_or_canonical_count")
    )
    if _positive(final_selected) or (_positive(final_evidence) and _positive(final_citation)):
        return "selected_complete_official_current_evidence_exists"

    recovered_result = _int_or_unknown(
        _first_present(
            trace.get("recovered_result_count"),
            trace.get("active_source_class_recovery_result_count"),
        )
    )
    official_candidate = _int_or_unknown(
        trace.get("candidate_official_or_canonical_count")
    )
    accepted_readable = _int_or_unknown(
        trace.get("accepted_or_readable_official_or_canonical_count")
    )
    selected_readable = _int_or_unknown(
        trace.get("recovered_candidate_selected_readable_count")
    )
    rejection_reasons = " ".join(
        item.casefold()
        for item in _string_list(trace.get("recovered_candidate_rejection_reasons"))
    )
    fit_status = _text(trace.get("recovered_candidate_source_fit_status")).casefold()
    candidate_status = _text(trace.get("candidate_return_status"))

    if _zero(recovered_result) or candidate_status == "zero_candidates":
        return "no_plausible_official_current_candidate_acquired"
    if _positive(recovered_result) and _zero(official_candidate):
        return "candidate_readable_but_misclassified"
    if _positive(official_candidate) and (
        _zero(accepted_readable)
        or "unreadable" in rejection_reasons
        or "readability" in rejection_reasons
        or "unreadable" in fit_status
    ):
        return "candidate_acquired_but_unreadable"
    if _positive(official_candidate) and (
        _zero(selected_readable)
        or "fit" in rejection_reasons
        or "currentness" in rejection_reasons
        or "fit_rejected" in fit_status
    ):
        return "candidate_classified_but_fit_rejected"
    if _positive(official_candidate):
        return "official_current_candidate_acquired"
    return _UNKNOWN


def _recovery_budget_state(trace: Mapping[str, Any]) -> str:
    slot_available = _bool_or_unknown(trace.get("recovery_slot_available"))
    if slot_available is True:
        return "available"
    if slot_available is False:
        return "exhausted"
    prior = _int_or_unknown(
        _first_present(
            trace.get("prior_recovery_attempt_count"),
            trace.get("active_source_class_recovery_attempt_count"),
        )
    )
    maximum = _int_or_unknown(trace.get("max_recovery_attempts"))
    if isinstance(prior, int) and isinstance(maximum, int):
        return "available" if prior < maximum else "exhausted"
    if (
        trace.get("active_source_class_recovery_eligible") is True
        or trace.get("source_class_recovery_eligible") is True
    ):
        return "available"
    skip_reason = _text(
        _first_present(
            trace.get("admission_skip_reason"),
            trace.get("active_source_class_recovery_skip_reason"),
        )
    )
    if "exhausted" in skip_reason or "hard_recovery_attempt_cap" in skip_reason:
        return "exhausted"
    return _UNKNOWN


def _source_obligation_status(
    trace: Mapping[str, Any],
    source_classes: list[str],
) -> str:
    direct = _text(trace.get("source_obligation_status"))
    if direct not in {"", _UNKNOWN, _NOT_OBSERVABLE}:
        return direct
    unsatisfied = _string_list(trace.get("unsatisfied_required_source_classes"))
    if not unsatisfied:
        unsatisfied = _string_list(
            trace.get("active_source_class_recovery_missing_classes")
        )
    if any(item in _OFFICIAL_CURRENT_CLASSES for item in unsatisfied):
        return "official_current_required_unmet"
    if any(item in _OFFICIAL_CURRENT_CLASSES for item in source_classes):
        if trace.get("active_source_class_recovery_eligible") is True:
            return "official_current_required_unmet"
        if trace.get("active_source_class_recovery_official_canonical_admitted") is True:
            return "official_current_required_unmet"
    if trace.get("admission_used") is False:
        return "not_required_or_satisfied"
    return _UNKNOWN


def _source_classes(trace: Mapping[str, Any]) -> list[str]:
    classes = []
    for key in (
        "required_source_class",
        "required_source_classes",
        "unsatisfied_required_source_classes",
        "active_source_class_recovery_missing_classes",
    ):
        classes.extend(_string_list(trace.get(key)))
    seen: set[str] = set()
    out: list[str] = []
    for item in classes:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _ledger_custody(trace: Mapping[str, Any]) -> dict[str, Any]:
    direct = trace.get("final_evidence_citation_custody")
    if isinstance(direct, Mapping):
        return dict(direct)
    packet = trace.get(CONTROLLER_EVIDENCE_LEDGER_TRACE_KEY)
    if isinstance(packet, Mapping):
        ledger = packet.get("ControllerEvidenceLedger")
        if isinstance(ledger, Mapping):
            custody = ledger.get("final_evidence_citation_custody")
            if isinstance(custody, Mapping):
                return dict(custody)
    ledger = trace.get("ControllerEvidenceLedger")
    if isinstance(ledger, Mapping):
        custody = ledger.get("final_evidence_citation_custody")
        if isinstance(custody, Mapping):
            return dict(custody)
    return {}


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _text(value: Any) -> str:
    if value is None:
        return _UNKNOWN
    text = str(value).strip()
    return text or _UNKNOWN


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = list(value)
    else:
        values = []
    out: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if text and text not in {_UNKNOWN, _NOT_OBSERVABLE}:
            out.append(text)
    return out


def _int_or_unknown(value: Any) -> int | str:
    if isinstance(value, bool):
        return _UNKNOWN
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    if isinstance(value, str) and value.strip().isdigit():
        return max(0, int(value.strip()))
    return _UNKNOWN


def _bool_or_unknown(value: Any) -> bool | str:
    if isinstance(value, bool):
        return value
    return _UNKNOWN


def _positive(value: Any) -> bool:
    return isinstance(value, int) and value > 0


def _zero(value: Any) -> bool:
    return isinstance(value, int) and value == 0


__all__ = [
    "CONTINUE_DOWNSTREAM",
    "CONTROLLER_RECOVERY_DECISION_SCHEMA_VERSION",
    "CONTROLLER_RECOVERY_DECISION_TRACE_KEY",
    "ControllerRecoveryDecision",
    "REQUEST_PROVIDER_SEARCH_REVIEW",
    "RETRY_RECOVERY",
    "STOP_FOR_ARCHITECTURE_DECISION",
    "STOP_INSUFFICIENT",
    "STOP_LEGACY_CUSTODY_GAP",
    "STOP_SUFFICIENT",
    "build_controller_recovery_decision",
    "controller_recovery_executor_allows_attempt",
]
