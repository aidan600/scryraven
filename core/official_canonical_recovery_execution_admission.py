"""AG-50B official/canonical recovery execution admission.

This module decides whether a required official/current/canonical recovery
query may spend one bounded source-class recovery execution slot. It is pure
admission glue: it does not retrieve, route providers, choose depth, rank or
filter sources, classify returned sources, alter prompts, or affect final
answer behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from core.authoritative_source_obligations import (
    LEGAL_OR_REGULATORY_TEXT,
    OFFICIAL_CURRENT_RULES,
    PRIMARY_SOURCE_DOCUMENTS,
    REPUTABLE_SECONDARY,
    AuthoritativeSourceObligationState,
    AuthorityEvidenceFit,
    AuthorityRequirement,
    AuthorityStatus,
)
from core.official_source_obligation_candidate_visibility import (
    NOT_REQUIRED,
    PREFERRED,
    REQUIRED,
    UNKNOWN,
    OfficialSourceObligationCandidateVisibilityFacts,
)

OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY = (
    "official_canonical_recovery_execution_admission_trace"
)
OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_SCHEMA_VERSION = (
    "official_canonical_recovery_execution_admission_ag50b_v1"
)

_ALLOWED_REQUIRED_SOURCE_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)
_HARD_BLOCKERS = frozenset(
    {
        "active_recovery_already_used",
        "already_attempted",
        "blocked_by_conflict_resolution",
        "blocked_by_corpus_weak",
        "blocked_by_provider_policy_change_required",
        "blocked_by_retrieve_to_anchor_recommendation",
        "blocked_by_search_depth_escalation_required",
        "blocked_by_terminal_stop",
        "blocked_by_weak_corpus_recovery",
        "authority_lifecycle_execution_blocked",
        "budget_hard_exhausted",
        "conflict_resolution_owns_path",
        "terminal_stop_approved",
        "weak_corpus_recovery_owns_path",
    }
)
_TERMINAL_BLOCKERS = frozenset(
    {
        "blocked_by_terminal_stop",
        "terminal_stop_approved",
    }
)
_WEAK_CORPUS_BLOCKERS = frozenset(
    {
        "blocked_by_corpus_weak",
        "blocked_by_weak_corpus_recovery",
        "weak_corpus_recovery_owns_path",
    }
)
_SUPPORTED_STRONG_AUTHORITY_RECOVERY_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
    }
)
_VISIBLE_STRONG_AUTHORITY_RECOVERY_CLASSES = (
    _SUPPORTED_STRONG_AUTHORITY_RECOVERY_CLASSES
    | {"primary_source_documents", "archival_primary_text"}
)
_KERNEL_AUTHORITY_CLASS_BY_LEGACY_CLASS = {
    "official_current_rules": OFFICIAL_CURRENT_RULES,
    "legal_or_regulatory_text": LEGAL_OR_REGULATORY_TEXT,
    "current_primary_or_official": OFFICIAL_CURRENT_RULES,
    "primary_source_documents": PRIMARY_SOURCE_DOCUMENTS,
    "archival_primary_text": PRIMARY_SOURCE_DOCUMENTS,
}
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "output",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "secret",
        "secrets",
        "token",
    }
)
_PROTECTED_MARKERS = (
    "raw prompt",
    "raw_provider",
    "provider_payload",
    "secret",
)


@dataclass(frozen=True)
class OfficialCanonicalRecoveryExecutionAdmissionResult:
    """Admission trace plus the bounded slot decision."""

    source_class_recovery_execution_admitted: bool
    trace: dict[str, Any]


def build_official_canonical_recovery_execution_admission(
    *,
    recommendation: Mapping[str, Any] | None,
    runtime_trace: Mapping[str, Any] | None = None,
    obligation_facts: OfficialSourceObligationCandidateVisibilityFacts
    | Mapping[str, Any]
    | None = None,
    existing_blockers: Iterable[Any] = (),
    prior_recovery_attempt_count: int | None = None,
    max_recovery_attempts: int = 1,
    ordinary_iteration_budget_remaining: int = 0,
) -> OfficialCanonicalRecoveryExecutionAdmissionResult:
    """Return whether the official/canonical path may spend one recovery slot."""

    base = _safe_mapping(recommendation)
    trace = _safe_mapping(runtime_trace)
    facts = _coerce_facts(obligation_facts, runtime_trace={**trace, **base})
    required_classes = _class_list(facts.required_source_classes)
    allowed_required = [
        item for item in required_classes if item in _ALLOWED_REQUIRED_SOURCE_CLASSES
    ]
    _satisfied, unsatisfied_required = _kernel_satisfaction_for_required_classes(
        allowed_required,
        recommendation=base,
        runtime_trace=trace,
    )
    recovery_queries = _recovery_queries(base, trace, facts)
    prior_attempts = _non_negative_int(
        _first_present(
            prior_recovery_attempt_count,
            trace.get("active_source_class_recovery_attempt_count"),
        )
    )
    max_attempts = max(0, _non_negative_int(max_recovery_attempts))
    ordinary_remaining = _non_negative_int(ordinary_iteration_budget_remaining)
    blockers = _admission_blockers(
        existing_blockers=existing_blockers,
        recommendation=base,
        runtime_trace=trace,
        unsatisfied_required_source_classes=unsatisfied_required,
        recovery_queries=recovery_queries,
        prior_attempts=prior_attempts,
        max_attempts=max_attempts,
    )
    weak_corpus_can_coexist = _official_or_legal_gap_can_coexist_with_weak_corpus(
        unsatisfied_required_source_classes=unsatisfied_required,
        recovery_queries=recovery_queries,
    )
    weak_corpus_coexistence_reason = _weak_corpus_coexistence_reason(
        runtime_trace=trace,
        blockers=blockers,
        weak_corpus_can_coexist=weak_corpus_can_coexist,
    )
    acquisition_path_visible = _official_canonical_acquisition_path_visible(
        base,
        trace,
    )
    considered = facts.obligation_status != UNKNOWN
    recovery_query_available = bool(recovery_queries)
    recovery_slot_available = prior_attempts < max_attempts
    eligible = bool(
        considered
        and facts.obligation_status == REQUIRED
        and unsatisfied_required
        and acquisition_path_visible
        and recovery_query_available
        and recovery_slot_available
        and not blockers
    )
    used = eligible

    payload = {
        "schema_version": (
            OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_SCHEMA_VERSION
        ),
        "trace_mode": "recovery_execution_admission",
        "admission_considered": considered,
        "admission_eligible": eligible,
        "admission_used": used,
        "admission_skip_reason": _skip_reason(
            facts=facts,
            considered=considered,
            allowed_required=allowed_required,
            unsatisfied_required=unsatisfied_required,
            acquisition_path_visible=acquisition_path_visible,
            recovery_query_available=recovery_query_available,
            recovery_slot_available=recovery_slot_available,
            blockers=blockers,
        ),
        "admission_blockers": blockers,
        "weak_corpus_coexistence_reason": weak_corpus_coexistence_reason,
        "admission_source": facts.obligation_source,
        "admission_acquisition_path_visible": acquisition_path_visible,
        "required_source_classes": allowed_required,
        "unsatisfied_required_source_classes": unsatisfied_required,
        "recovery_query_available": recovery_query_available,
        "recovery_query_count": len(recovery_queries),
        "recovery_query_previews": list(recovery_queries[:3]),
        "prior_recovery_attempt_count": prior_attempts,
        "max_recovery_attempts": max_attempts,
        "ordinary_iteration_budget_remaining": ordinary_remaining,
        "recovery_slot_available": recovery_slot_available,
        "source_class_recovery_execution_admitted": used,
        "source_class_recovery_attempt_expected": used,
        "provider_policy_unchanged": True,
        "depth_policy_unchanged": True,
        "ranking_unchanged": True,
        "final_answer_behavior_unchanged": True,
        "behavior_changed": used,
        "protected_surface": {
            "provider_policy_unchanged": True,
            "provider_selection_unchanged": True,
            "depth_policy_unchanged": True,
            "ranking_unchanged": True,
            "returned_source_classification_unchanged": True,
            "prompt_unchanged": True,
            "economist_behavior_unchanged": True,
            "author_behavior_unchanged": True,
            "final_answer_behavior_unchanged": True,
            "retrieve_targeted_promoted": False,
        },
        "consumer": [
            "source_class_recovery_lifecycle",
            "controller_loop_spine",
            "local_output_quality_review_packet",
        ],
        "decision_enabled": [
            "required_official_current_canonical_query_can_spend_one_recovery_slot",
            "preferred_and_unknown_obligations_do_not_admit_execution",
            "terminal_weak_corpus_conflict_and_hard_cap_blockers_remain_authoritative",
            "ordinary_iteration_budget_exhaustion_can_be_distinguished_from_hard_cap",
        ],
    }
    return OfficialCanonicalRecoveryExecutionAdmissionResult(
        source_class_recovery_execution_admitted=used,
        trace={
            "schema_version": (
                OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_SCHEMA_VERSION
            ),
            "trace_mode": "recovery_execution_admission",
            "OfficialCanonicalRecoveryExecutionAdmission": _safe_value(payload),
        },
    )


def _coerce_facts(
    facts: OfficialSourceObligationCandidateVisibilityFacts | Mapping[str, Any] | None,
    *,
    runtime_trace: Mapping[str, Any] | None,
) -> OfficialSourceObligationCandidateVisibilityFacts:
    if isinstance(facts, OfficialSourceObligationCandidateVisibilityFacts):
        return facts
    if isinstance(facts, Mapping):
        return OfficialSourceObligationCandidateVisibilityFacts.from_runtime_trace(facts)
    return OfficialSourceObligationCandidateVisibilityFacts.from_runtime_trace(
        runtime_trace
    )


def _skip_reason(
    *,
    facts: OfficialSourceObligationCandidateVisibilityFacts,
    considered: bool,
    allowed_required: list[str],
    unsatisfied_required: list[str],
    acquisition_path_visible: bool,
    recovery_query_available: bool,
    recovery_slot_available: bool,
    blockers: list[str],
) -> str | None:
    if not considered:
        return "obligation_unknown"
    if facts.obligation_status == PREFERRED:
        return "preferred_obligation_advisory_only"
    if facts.obligation_status == NOT_REQUIRED:
        return "obligation_not_required"
    if facts.obligation_status == UNKNOWN:
        return "obligation_unknown"
    if facts.obligation_status != REQUIRED:
        return "obligation_status_not_required"
    if not allowed_required:
        return "no_required_source_classes"
    if blockers:
        return "existing_runtime_blocker"
    if not unsatisfied_required:
        return "existing_source_class_satisfied"
    if not acquisition_path_visible:
        return "official_canonical_acquisition_path_not_visible"
    if not recovery_query_available:
        return "no_recovery_query_available"
    if not recovery_slot_available:
        return "hard_recovery_attempt_cap_exhausted"
    return None


def _admission_blockers(
    *,
    existing_blockers: Iterable[Any],
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
    unsatisfied_required_source_classes: Iterable[str],
    recovery_queries: Iterable[str],
    prior_attempts: int,
    max_attempts: int,
) -> list[str]:
    blockers: list[str] = []
    authority_lifecycle_preserves_recovery = bool(
        runtime_trace.get("authority_lifecycle_required_recovery_allowed")
    )
    weak_corpus_can_coexist = _official_or_legal_gap_can_coexist_with_weak_corpus(
        unsatisfied_required_source_classes=unsatisfied_required_source_classes,
        recovery_queries=recovery_queries,
    )
    for source in (
        existing_blockers,
        recommendation.get("active_source_class_recovery_blockers"),
        recommendation.get("source_class_recovery_candidate_v2_blockers"),
        runtime_trace.get("active_source_class_recovery_blockers"),
        runtime_trace.get("source_class_recovery_candidate_v2_blockers"),
    ):
        for item in _string_list(source):
            if item in _WEAK_CORPUS_BLOCKERS and weak_corpus_can_coexist:
                continue
            if (
                item in _WEAK_CORPUS_BLOCKERS
                and authority_lifecycle_preserves_recovery
            ):
                continue
            if item in _HARD_BLOCKERS:
                _append_one(blockers, item)
    if (
        runtime_trace.get("terminal_stop_approved") is True
    ):
        _append_one(blockers, "terminal_stop_approved")
    if (
        runtime_trace.get("weak_corpus_recovery_used") is True
        and not weak_corpus_can_coexist
        and not authority_lifecycle_preserves_recovery
    ):
        _append_one(blockers, "weak_corpus_recovery_owns_path")
    if (
        runtime_trace.get("corpus_weak") is True
        and not weak_corpus_can_coexist
        and not authority_lifecycle_preserves_recovery
    ):
        _append_one(blockers, "blocked_by_corpus_weak")
    if runtime_trace.get("conflict_resolution_owns_path") is True:
        _append_one(blockers, "conflict_resolution_owns_path")
    _append_authority_lifecycle_execution_blocker(blockers, runtime_trace)
    if max_attempts <= 0 or prior_attempts >= max_attempts:
        _append_one(blockers, "budget_hard_exhausted")
    return blockers


def _append_authority_lifecycle_execution_blocker(
    blockers: list[str],
    runtime_trace: Mapping[str, Any],
) -> None:
    if runtime_trace.get("authority_lifecycle_execution_blocked") is not True:
        return
    blocker = runtime_trace.get("authority_lifecycle_execution_blocker")
    if isinstance(blocker, Mapping):
        for key in ("kind", "reason"):
            text = _clean_token(blocker.get(key))
            if text in _HARD_BLOCKERS:
                _append_one(blockers, text)
                return
    _append_one(blockers, "authority_lifecycle_execution_blocked")


def _official_or_legal_gap_can_coexist_with_weak_corpus(
    *,
    unsatisfied_required_source_classes: Iterable[str],
    recovery_queries: Iterable[str],
) -> bool:
    required = set(unsatisfied_required_source_classes)
    if not required & _SUPPORTED_STRONG_AUTHORITY_RECOVERY_CLASSES:
        return False
    return bool(tuple(recovery_queries))


def _weak_corpus_coexistence_reason(
    *,
    runtime_trace: Mapping[str, Any],
    blockers: Iterable[str],
    weak_corpus_can_coexist: bool,
) -> str | None:
    if not weak_corpus_can_coexist:
        return None
    if not (
        runtime_trace.get("corpus_weak") is True
        or runtime_trace.get("weak_corpus_recovery_used") is True
    ):
        return None
    if any(item in _WEAK_CORPUS_BLOCKERS for item in blockers):
        return None
    return "unsatisfied_official_current_recovery_lane"


def _recovery_queries(
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
    facts: OfficialSourceObligationCandidateVisibilityFacts,
) -> tuple[str, ...]:
    return tuple(
        _dedupe(
            [
                *_string_list(recommendation.get("source_class_recovery_queries")),
                *_string_list(runtime_trace.get("active_source_class_recovery_queries")),
                *_string_list(runtime_trace.get("source_class_recovery_queries")),
            ]
        )
    )


def _official_canonical_acquisition_path_visible(
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
) -> bool:
    if recommendation.get("official_canonical_acquisition_path_visible") is True:
        return True
    reason = str(recommendation.get("source_class_recovery_reason") or "")
    if reason.startswith("official_canonical_recovery_query_acquisition:"):
        return True
    trigger_fields = set(_string_list(recommendation.get("source_class_recovery_trigger_fields")))
    if "official_canonical_recovery_query_acquisition" in trigger_fields:
        return True
    trace_packet = runtime_trace.get(
        "official_canonical_recovery_query_acquisition_trace"
    )
    if isinstance(trace_packet, Mapping):
        payload = trace_packet.get("OfficialCanonicalRecoveryQueryAcquisition")
        if isinstance(payload, Mapping):
            return bool(payload.get("acquisition_repair_used"))
    if _source_class_recovery_recommendation_path_visible(
        recommendation,
        runtime_trace,
    ):
        return True
    return False


def _source_class_recovery_recommendation_path_visible(
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
) -> bool:
    if not (
        recommendation.get("source_class_recovery_recommended")
        or runtime_trace.get("source_class_recovery_recommended")
    ):
        return False
    if not _recovery_queries(recommendation, runtime_trace, _empty_facts()):
        return False
    visible_classes: set[str] = set()
    for source in (recommendation, runtime_trace):
        for key in (
            "missing_expected_source_classes",
            "required_source_classes",
            "source_class_gap_candidates",
            "active_source_class_recovery_missing_classes",
            "unsatisfied_required_source_classes",
        ):
            visible_classes.update(_class_list(source.get(key)))
        status = source.get("source_class_satisfaction_status")
        if isinstance(status, Mapping):
            visible_classes.update(_class_list(status.keys()))
    if not (visible_classes & _VISIBLE_STRONG_AUTHORITY_RECOVERY_CLASSES):
        return False
    reason = " ".join(
        item
        for item in (
            _clean_text(recommendation.get("source_class_recovery_reason"), limit=180),
            _clean_text(runtime_trace.get("source_class_recovery_reason"), limit=180),
        )
        if item
    )
    trigger_fields = {
        *_string_list(recommendation.get("source_class_recovery_trigger_fields")),
        *_string_list(runtime_trace.get("source_class_recovery_trigger_fields")),
    }
    if reason.startswith(
        (
            "missing_expected_source_class:",
            "answer_contract_",
            "official_source_obligation_bridge:",
            "run_authority_search_judgment:",
        )
    ):
        return True
    return bool(
        trigger_fields
        & {
            "answer_contract_source_class_gap",
            "official_canonical_acquisition_path_visibility",
            "official_source_obligation_bridge",
            "official_source_obligation_trace",
            "run_authority_search_judgment",
            "source_domain_counts",
            "source_tier_counts",
            "official_evidence_found",
        }
    )


def _empty_facts() -> OfficialSourceObligationCandidateVisibilityFacts:
    return OfficialSourceObligationCandidateVisibilityFacts.from_runtime_trace({})


def _status_by_class(
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for source in (runtime_trace, recommendation):
        status = source.get("source_class_satisfaction_status")
        if not isinstance(status, Mapping):
            continue
        for key, value in status.items():
            clean_key = _clean_token(key)
            clean_value = _clean_text(value, limit=80)
            if clean_key and clean_value:
                out[clean_key] = clean_value
    return out


def _kernel_satisfaction_for_required_classes(
    source_classes: Iterable[str],
    *,
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    requirements: list[tuple[str, AuthorityRequirement]] = []
    evidence_fits: list[AuthorityEvidenceFit] = []
    status_by_class = _status_by_class(recommendation, runtime_trace)
    for source_class in source_classes:
        requirement = _authority_requirement_for_source_class(source_class)
        authority_class = _KERNEL_AUTHORITY_CLASS_BY_LEGACY_CLASS.get(source_class)
        if requirement is None or authority_class is None:
            continue
        requirements.append((source_class, requirement))
        evidence_fits.extend(
            _authority_evidence_fits_for_source_class(
                source_class,
                requirement=requirement,
                authority_class=authority_class,
                legacy_status=status_by_class.get(source_class),
                strong_count_positive=_strong_count_positive(
                    recommendation,
                    runtime_trace,
                    source_class,
                ),
            )
        )
    state = AuthoritativeSourceObligationState.evaluate(
        [requirement for _source_class, requirement in requirements],
        evidence_fits,
    )
    satisfied: list[str] = []
    unsatisfied: list[str] = []
    for source_class, requirement in requirements:
        target = (
            satisfied
            if state.satisfaction_for(requirement.requirement_id).status
            is AuthorityStatus.FULFILLED
            else unsatisfied
        )
        _append_one(target, source_class)
    return satisfied, unsatisfied


def _authority_requirement_for_source_class(
    source_class: str,
) -> AuthorityRequirement | None:
    if source_class == "official_current_rules":
        return AuthorityRequirement.official_current(source_class)
    if source_class in {"legal_or_regulatory_text", "current_primary_or_official"}:
        return AuthorityRequirement.legal_current_primary(source_class)
    if source_class in {"primary_source_documents", "archival_primary_text"}:
        return AuthorityRequirement.canonical_project_doc(source_class)
    return None


def _authority_evidence_fits_for_source_class(
    source_class: str,
    *,
    requirement: AuthorityRequirement,
    authority_class: str,
    legacy_status: str | None,
    strong_count_positive: bool,
) -> tuple[AuthorityEvidenceFit, ...]:
    if strong_count_positive or legacy_status == "satisfied_strong":
        return (
            AuthorityEvidenceFit.authoritative(
                requirement.requirement_id,
                f"{source_class}:satisfied_strong",
                authority_class,
            ),
        )
    if legacy_status == "satisfied_weak":
        return (
            AuthorityEvidenceFit(
                requirement_id=requirement.requirement_id,
                evidence_id=f"{source_class}:satisfied_weak",
                candidate_exists=True,
                observed_source_class=authority_class,
                context_allowed=True,
                satisfies_authority=False,
                mismatch_reason="expected_source_class_weakly_satisfied",
            ),
        )
    if legacy_status == "expected_but_only_secondary":
        return (
            AuthorityEvidenceFit.lower_tier_context(
                requirement.requirement_id,
                f"{source_class}:secondary_only",
                REPUTABLE_SECONDARY,
                mismatch_reason="expected_source_class_secondary_only",
            ),
        )
    return ()


def _strong_count_positive(
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
    source_class: str,
) -> bool:
    for source in (runtime_trace, recommendation):
        counts = source.get("source_class_strong_satisfaction_counts")
        if not isinstance(counts, Mapping):
            continue
        try:
            if int(counts.get(source_class, 0) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _class_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _iter_values(value):
        token = _clean_token(item)
        if token and token in _ALLOWED_REQUIRED_SOURCE_CLASSES:
            _append_one(out, token)
    return out


def _string_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _iter_values(value):
        text = _clean_text(item, limit=180)
        if text:
            _append_one(out, text)
    return out


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if value and key not in seen:
            out.append(value)
            seen.add(key)
    return out


def _append_one(target: list[str], value: str) -> None:
    if value and value not in target:
        target.append(value)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return 0


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key, item in value.items():
        if _is_sensitive_key(key):
            continue
        out[str(key)] = _safe_value(item)
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=300)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value[:20]]
    if isinstance(value, (set, frozenset)):
        return [_safe_value(item) for item in sorted(value, key=str)[:20]]
    return _clean_text(value, limit=300)


def _iter_values(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Mapping):
        return tuple(value.values())
    if value is None or isinstance(value, (str, bytes)):
        return ()
    try:
        return tuple(value)
    except TypeError:
        return ()


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    return text[:limit]


def _clean_token(value: Any) -> str | None:
    text = _clean_text(value, limit=100)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


__all__ = [
    "OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_SCHEMA_VERSION",
    "OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY",
    "OfficialCanonicalRecoveryExecutionAdmissionResult",
    "build_official_canonical_recovery_execution_admission",
]
