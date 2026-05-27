"""AnswerContract-compatible projection for authoritative-source obligations.

AG-65B keeps this as a pure compatibility helper. It projects the AG-65A
authoritative-source obligation kernel into the existing answer-contract
fulfillment vocabulary without wiring runtime behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.authoritative_source_obligations import (
    AuthoritativeSourceObligationState,
    AuthorityStatus,
)

ANSWER_CONTRACT_AUTHORITY_PROJECTION_SCHEMA_VERSION = (
    "answer_contract_authority_projection_v1"
)

_PARTIAL_STATUS = "partial"
_FULFILLED_STATUS = "fulfilled"
_UNFULFILLED_STATUS = "unfulfilled"

_SATISFIED_STRONG = "satisfied_strong"
_SECONDARY_ONLY = "expected_but_only_secondary"
_UNSATISFIED = "unsatisfied"

_PROTECTED_MARKERS = (
    "controller_diagnostics",
    "database",
    "db row",
    "economist_v1",
    "full_trace",
    "local packet",
    "private log",
    "provider_payload",
    "quantitative_packet",
    "raw evidence",
    "raw prompt",
    "raw_prompt",
    "raw_provider",
    "secret",
    "source_bound_values",
)


def _copy_string_tuple(values: Sequence[Any] | None) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        text = " ".join(str(value or "").strip().split())
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _safe_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if _contains_protected_marker(key):
                safe[key] = "[redacted protected material]"
            else:
                safe[key] = _safe_value(raw_value)
        return safe
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return "[redacted protected material]" if _contains_protected_marker(value) else value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def _contains_protected_marker(value: str) -> bool:
    folded = value.casefold()
    return any(marker in folded for marker in _PROTECTED_MARKERS)


def _get_field(source: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(field_name, default)
    return getattr(source, field_name, default)


def _source_class_warnings(source_class_gaps: Sequence[str]) -> tuple[str, ...]:
    gaps = {item.casefold() for item in _copy_string_tuple(source_class_gaps)}
    warnings: list[str] = []
    if gaps & {"legal_or_regulatory_text", "official_current_rules"}:
        warnings.append("official/current legal evidence missing or secondary-only")
    if "current_primary_or_official" in gaps:
        warnings.append("official/current primary evidence missing or secondary-only")
    if "primary_or_archival" in gaps:
        warnings.append("primary/archival source not found")
    if "primary_source_documents" in gaps:
        warnings.append("canonical/official documentation missing or secondary-only")
    if "academic_literature" in gaps:
        warnings.append("academic literature evidence missing or secondary-only")
    if "current_specs_or_availability" in gaps:
        warnings.append("current specs/availability evidence missing or secondary-only")
    if "sourced_numeric_values" in gaps:
        warnings.append("source-bound numeric evidence missing or partial")
    if "social_signal" in gaps:
        warnings.append("social signal unavailable/provider_unavailable")
    return _copy_string_tuple(warnings)


@dataclass(frozen=True, slots=True)
class AnswerContractAuthorityProjection:
    """Trace-safe projection into existing AnswerContract fulfillment fields."""

    source_obligation_status: str
    fulfilled_source_classes: tuple[str, ...] = ()
    unfulfilled_source_classes: tuple[str, ...] = ()
    partial_source_classes: tuple[str, ...] = ()
    source_class_satisfaction_status: Mapping[str, str] | None = None
    warnings_to_Analyst_or_Author: tuple[str, ...] = ()
    recovery_posture_summary: Mapping[str, Any] | None = None
    trace_safe_summary: Mapping[str, Any] | None = None
    schema_version: str = ANSWER_CONTRACT_AUTHORITY_PROJECTION_SCHEMA_VERSION
    trace_safe: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _safe_value(
            {
                "schema_version": self.schema_version,
                "trace_safe": self.trace_safe,
                "source_obligation_status": self.source_obligation_status,
                "fulfilled_source_classes": list(self.fulfilled_source_classes),
                "unfulfilled_source_classes": list(self.unfulfilled_source_classes),
                "partial_source_classes": list(self.partial_source_classes),
                "source_class_satisfaction_status": dict(
                    self.source_class_satisfaction_status or {}
                ),
                "warnings_to_Analyst_or_Author": list(
                    self.warnings_to_Analyst_or_Author
                ),
                "recovery_posture_summary": dict(
                    self.recovery_posture_summary or {}
                ),
                "trace_safe_summary": dict(self.trace_safe_summary or {}),
            }
        )


def project_authoritative_source_state_to_answer_contract_fields(
    state: AuthoritativeSourceObligationState,
    *,
    existing_handoff: Any | None = None,
) -> AnswerContractAuthorityProjection:
    """Project kernel state into the stable AnswerContract handoff vocabulary."""

    fulfilled_classes: list[str] = []
    unfulfilled_classes: list[str] = []
    partial_classes: list[str] = []
    satisfaction_status: dict[str, str] = {}

    missing_requirements = {
        requirement.requirement_id
        for requirement in state.missing_authority_requirements()
    }
    for requirement in state.requirements:
        for leaf in requirement.leaf_requirements():
            if not leaf.required_authority_classes:
                continue
            satisfaction = state.satisfaction_for(leaf.requirement_id)
            classes = leaf.required_authority_classes
            if satisfaction.status is AuthorityStatus.FULFILLED:
                satisfied_classes = _satisfying_source_classes(state, leaf.requirement_id)
                fulfilled_classes.extend(satisfied_classes or classes)
                for source_class in satisfied_classes or classes:
                    satisfaction_status[source_class] = _SATISFIED_STRONG
                continue
            if leaf.requirement_id not in missing_requirements:
                continue
            unfulfilled_classes.extend(classes)
            if satisfaction.status is AuthorityStatus.PARTIAL:
                partial_classes.extend(classes)
                for source_class in classes:
                    satisfaction_status[source_class] = _SECONDARY_ONLY
            else:
                for source_class in classes:
                    satisfaction_status[source_class] = _UNSATISFIED

    if missing_requirements:
        scoped_unfulfilled: list[str] = []
        scoped_partial: list[str] = []
        for requirement in state.requirements:
            for leaf in requirement.leaf_requirements():
                if leaf.requirement_id not in missing_requirements:
                    continue
                scoped_unfulfilled.extend(leaf.required_authority_classes)
                if state.satisfaction_for(leaf.requirement_id).status is AuthorityStatus.PARTIAL:
                    scoped_partial.extend(leaf.required_authority_classes)
        unfulfilled_classes = scoped_unfulfilled
        partial_classes = scoped_partial

    unfulfilled = _copy_string_tuple(unfulfilled_classes)
    partial = _copy_string_tuple(partial_classes)
    fulfilled = _copy_string_tuple(
        source_class
        for source_class in fulfilled_classes
        if source_class.casefold() not in {item.casefold() for item in unfulfilled}
    )

    if existing_handoff is not None:
        unfulfilled = _copy_string_tuple(
            tuple(_copy_string_tuple(_get_field(existing_handoff, "unfulfilled_source_classes")))
            + tuple(unfulfilled)
        )
        partial = _copy_string_tuple(
            tuple(_copy_string_tuple(_get_field(existing_handoff, "partial_source_classes")))
            + tuple(partial)
        )

    source_obligation_status = _projection_status(state, unfulfilled, partial)
    warnings = _source_class_warnings(unfulfilled)
    if existing_handoff is not None:
        warnings = _copy_string_tuple(
            tuple(_copy_string_tuple(_get_field(existing_handoff, "warnings_to_Analyst_or_Author")))
            + tuple(warnings)
        )

    return AnswerContractAuthorityProjection(
        source_obligation_status=source_obligation_status,
        fulfilled_source_classes=fulfilled,
        unfulfilled_source_classes=unfulfilled,
        partial_source_classes=partial if source_obligation_status == _PARTIAL_STATUS else (),
        source_class_satisfaction_status=dict(sorted(satisfaction_status.items())),
        warnings_to_Analyst_or_Author=warnings,
        recovery_posture_summary=_recovery_posture_summary(state),
        trace_safe_summary=_trace_safe_summary(state, missing_requirements),
    )


def compare_authoritative_projection_to_answer_contract_handoff(
    projection: AnswerContractAuthorityProjection,
    handoff: Any,
) -> dict[str, Any]:
    """Compare projected fields with an existing AnswerContract handoff."""

    projected = projection.to_dict()
    checks = {
        "source_obligation_status": projected["source_obligation_status"]
        == _get_field(handoff, "source_obligation_status"),
        "unfulfilled_source_classes": projected["unfulfilled_source_classes"]
        == list(_copy_string_tuple(_get_field(handoff, "unfulfilled_source_classes"))),
        "partial_source_classes": projected["partial_source_classes"]
        == list(_copy_string_tuple(_get_field(handoff, "partial_source_classes"))),
        "warnings_to_Analyst_or_Author": projected["warnings_to_Analyst_or_Author"]
        == list(
            _copy_string_tuple(_get_field(handoff, "warnings_to_Analyst_or_Author"))
        ),
    }
    return {
        "schema_version": "answer_contract_authority_projection_parity_v1",
        "matches": all(checks.values()),
        "checks": checks,
    }


def _projection_status(
    state: AuthoritativeSourceObligationState,
    unfulfilled: tuple[str, ...],
    partial: tuple[str, ...],
) -> str:
    if not unfulfilled:
        return _FULFILLED_STATUS
    if partial:
        return _PARTIAL_STATUS
    if any(
        satisfaction.status is AuthorityStatus.FULFILLED
        for satisfaction in state.satisfactions.values()
    ):
        return _PARTIAL_STATUS
    if any(fit.candidate_exists or fit.context_allowed for fit in state.evidence_fits):
        return _PARTIAL_STATUS
    return _UNFULFILLED_STATUS


def _satisfying_source_classes(
    state: AuthoritativeSourceObligationState,
    requirement_id: str,
) -> tuple[str, ...]:
    classes = [
        str(fit.observed_source_class)
        for fit in state.evidence_fits
        if fit.requirement_id in (None, requirement_id)
        and fit.candidate_exists
        and fit.satisfies_authority
        and fit.observed_source_class
    ]
    return _copy_string_tuple(classes)


def _recovery_posture_summary(
    state: AuthoritativeSourceObligationState,
) -> dict[str, Any]:
    plan = state.recovery_plan().to_projection()
    return _safe_value(
        {
            "missing_requirement_ids": plan["missing_requirement_ids"],
            "target_authority_classes": plan["target_authority_classes"],
            "generic_recovery_intents": plan["generic_recovery_intents"],
            "provider_agnostic": plan["provider_agnostic"],
            "execution_free": plan["execution_free"],
        }
    )


def _trace_safe_summary(
    state: AuthoritativeSourceObligationState,
    missing_requirements: set[str],
) -> dict[str, Any]:
    return _safe_value(
        {
            "requirement_count": len(state.requirements),
            "evidence_fit_count": len(state.evidence_fits),
            "missing_requirement_ids": sorted(missing_requirements),
            "projection_source": "authoritative_source_obligation_kernel",
            "runtime_wiring": False,
        }
    )


__all__ = [
    "ANSWER_CONTRACT_AUTHORITY_PROJECTION_SCHEMA_VERSION",
    "AnswerContractAuthorityProjection",
    "compare_authoritative_projection_to_answer_contract_handoff",
    "project_authoritative_source_state_to_answer_contract_fields",
]
