"""Validation helpers for passive AG-96I1 follow-up deliberation records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from core.followup_deliberation import (
    FollowupDecision,
    FollowupDeliberationCheckpoint,
    FollowupMode,
    GapType,
    ProviderJobKind,
    ReasoningHopType,
    clean_token,
    safe_json,
)

_FALSE_CAPABILITY_FIELDS = frozenset(
    {
        "may_directly_browse",
        "direct_browsing",
        "browsing_claimed",
        "may_directly_fetch",
        "direct_fetching",
        "fetching_claimed",
        "may_run_code",
        "arbitrary_code_execution_used",
        "may_select_citations",
        "citation_selection_claimed",
        "may_override_final_sufficiency",
        "final_sufficiency_override_claimed",
        "bridge_only_provider_outputs_satisfy_final_evidence",
    }
)
_FORBIDDEN_IMPORT_TOKENS = (
    "core." + "search_providers",
    "core." + "search_web",
    "core." + "retrieval_dispatch_runtime",
    "core." + "retrieval_scheduler",
    "core." + "pipeline_orchestrator",
)
_FORBIDDEN_CALL_TOKENS = (
    "ask_" + "model",
    "ev" + "al(",
    "ex" + "ec(",
    "sub" + "process",
    "format_" + "citation",
)


@dataclass(frozen=True, slots=True)
class FollowupDeliberationValidationResult:
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            raise ValueError("; ".join(self.errors))

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": list(self.errors)}


def validate_followup_deliberation_checkpoint(
    checkpoint: FollowupDeliberationCheckpoint | Mapping[str, Any],
) -> FollowupDeliberationValidationResult:
    payload = checkpoint.to_dict() if hasattr(checkpoint, "to_dict") else safe_json(checkpoint)
    payload = dict(payload if isinstance(payload, Mapping) else {})
    records = dict(payload.get("records") or {})
    errors: list[str] = []

    gaps = {
        clean_token(item.get("gap_id")): item
        for item in _mappings(records.get("gap_assessments"))
        if clean_token(item.get("gap_id"))
    }
    recommendations = list(_mappings(records.get("followup_recommendations")))
    candidates = list(_mappings(records.get("followup_authorization_candidates")))
    mode = clean_token(payload.get("mode")) or FollowupMode.BALANCED.value

    for item in recommendations:
        rec_id = clean_token(item.get("recommendation_id")) or "recommendation"
        gap_type = clean_token(item.get("gap_type"))
        gap_id = clean_token(item.get("gap_id"))
        if gap_type not in {gap.value for gap in GapType}:
            errors.append(f"{rec_id} must name a canonical gap_type")
        if not gap_id or gap_id not in gaps:
            errors.append(f"{rec_id} must reference a known gap_id")
        if not clean_token(item.get("component_id")):
            errors.append(f"{rec_id} must name component_id")
        if not clean_token(item.get("source_obligation_id")):
            errors.append(f"{rec_id} must name source_obligation_id")
        if _decision_can_execute(item) and not clean_token(item.get("provider_job_kind")):
            errors.append(f"{rec_id} must name provider_job_kind")
        if _decision_can_execute(item) and not item.get("expected_custody_update"):
            errors.append(f"{rec_id} must define expected EvidenceLedger custody update")
        if not clean_token(item.get("fallback_posture")):
            errors.append(f"{rec_id} must define fallback stop/caveat/refuse posture")

    for item in candidates:
        auth_id = clean_token(item.get("authorization_id")) or "authorization_candidate"
        job_kind = clean_token(item.get("provider_job_kind"))
        if job_kind not in {job.value for job in ProviderJobKind}:
            errors.append(f"{auth_id} must name provider_job_kind")
        if not item.get("expected_evidence_ledger_custody_update"):
            errors.append(
                f"{auth_id} must define expected EvidenceLedger custody update"
            )
        if not clean_token(item.get("fallback_stop_posture")):
            errors.append(f"{auth_id} must define fallback stop posture")
        if not clean_token(item.get("fallback_caveat_refuse_posture")):
            errors.append(f"{auth_id} must define fallback caveat/refuse posture")
        if (
            mode == FollowupMode.BALANCED.value
            and clean_token(item.get("hop_type"))
            == ReasoningHopType.MACRO_RUN_DIAGNOSIS.value
        ):
            errors.append(f"{auth_id} Balanced cannot authorize macro_run_diagnosis")
        if (
            mode == FollowupMode.BALANCED.value
            and job_kind == ProviderJobKind.RECONCILIATION_SUPPORT.value
        ):
            errors.append(f"{auth_id} Balanced cannot authorize Deep-only reconciliation")
        if clean_token(item.get("decision")) != FollowupDecision.AUTHORIZE_CANDIDATE.value:
            errors.append(f"{auth_id} candidate decision must be authorize_candidate")

    handoff = dict(records.get("sufficiency_handoff") or {})
    if handoff.get("bridge_only_provider_outputs_satisfy_final_evidence"):
        errors.append("bridge-only provider output cannot satisfy final evidence")
    errors.extend(_forbidden_capability_errors(payload))
    return FollowupDeliberationValidationResult(errors=tuple(dict.fromkeys(errors)))


def passive_module_static_guard(source_text: str, *, module_name: str) -> tuple[str, ...]:
    """Return static-boundary errors for an AG-96I1 passive module source."""

    errors: list[str] = []
    for token in _FORBIDDEN_IMPORT_TOKENS:
        if token in source_text:
            errors.append(f"{module_name} must not import {token}")
    for token in _FORBIDDEN_CALL_TOKENS:
        if token in source_text:
            errors.append(f"{module_name} must not contain {token}")
    return tuple(errors)


def _decision_can_execute(item: Mapping[str, Any]) -> bool:
    decision = clean_token(item.get("decision"))
    return decision in {
        FollowupDecision.RECOMMEND.value,
        FollowupDecision.AUTHORIZE_CANDIDATE.value,
    }


def _forbidden_capability_errors(value: Any, *, path: str = "checkpoint") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = clean_token(key) or ""
            next_path = f"{path}.{key_text or 'unknown'}"
            if key_text in _FALSE_CAPABILITY_FIELDS and item is True:
                errors.append(f"{next_path} must be false in AG-96I1")
            errors.extend(_forbidden_capability_errors(item, path=next_path))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for index, item in enumerate(value):
            errors.extend(_forbidden_capability_errors(item, path=f"{path}[{index}]"))
    elif isinstance(value, Enum):
        pass
    return errors


def _mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if value is None or isinstance(value, str | bytes):
        return ()
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


__all__ = [
    "FollowupDeliberationValidationResult",
    "passive_module_static_guard",
    "validate_followup_deliberation_checkpoint",
]
