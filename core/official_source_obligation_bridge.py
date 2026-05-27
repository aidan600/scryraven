"""AG-49C bridge from official-source obligations to recovery inputs.

This module is pure glue. It consumes sanitized AG-49B-style obligation facts
and may add generic missing source-class facts to an existing recovery
recommendation. It does not retrieve, route providers, choose depth, generate
queries, classify returned sources, rank/filter sources, or affect final-answer
behavior.
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

OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY = (
    "official_source_obligation_bridge_trace"
)
OFFICIAL_SOURCE_OBLIGATION_BRIDGE_SCHEMA_VERSION = (
    "official_source_obligation_bridge_ag49c_v1"
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
_KERNEL_AUTHORITY_CLASS_BY_LEGACY_CLASS = {
    "official_current_rules": OFFICIAL_CURRENT_RULES,
    "legal_or_regulatory_text": LEGAL_OR_REGULATORY_TEXT,
    "current_primary_or_official": OFFICIAL_CURRENT_RULES,
    "primary_source_documents": PRIMARY_SOURCE_DOCUMENTS,
    "archival_primary_text": PRIMARY_SOURCE_DOCUMENTS,
}
_BLOCKERS_THAT_PRESERVE_EXISTING_OWNERSHIP = frozenset(
    {
        "active_recovery_already_used",
        "already_attempted",
        "blocked_by_author_phase",
        "blocked_by_corpus_weak",
        "blocked_by_iteration_budget",
        "blocked_by_post_analyst_phase",
        "blocked_by_provider_policy_change_required",
        "blocked_by_retrieve_to_anchor_recommendation",
        "blocked_by_search_depth_escalation_required",
        "blocked_by_terminal_stop",
        "blocked_by_weak_corpus_recovery",
        "budget_hard_exhausted",
        "existing_active_recovery_blocked_by_budget",
        "fast_mode_policy_block",
        "terminal_stop_approved",
        "weak_corpus_recovery_owns_path",
    }
)
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
class OfficialSourceObligationBridgeResult:
    """Bridge output plus the recommendation visible to existing consumers."""

    recommendation: dict[str, Any]
    trace: dict[str, Any]


def apply_official_source_obligation_bridge(
    *,
    recommendation: Mapping[str, Any] | None,
    runtime_trace: Mapping[str, Any] | None = None,
    obligation_facts: OfficialSourceObligationCandidateVisibilityFacts
    | Mapping[str, Any]
    | None = None,
    existing_blockers: Iterable[Any] = (),
) -> OfficialSourceObligationBridgeResult:
    """Map required official/current/canonical obligations to recovery inputs."""
    base = _safe_mapping(recommendation)
    facts = _coerce_facts(obligation_facts, runtime_trace=runtime_trace)
    existing_missing = _class_list(base.get("missing_expected_source_classes"))
    required_classes = _class_list(facts.required_source_classes)
    allowed_required = [
        item for item in required_classes if item in _ALLOWED_REQUIRED_SOURCE_CLASSES
    ]
    satisfied, unsatisfied_required = _kernel_satisfaction_for_required_classes(
        allowed_required,
        recommendation=base,
        runtime_trace=runtime_trace,
    )
    blockers = _bridge_blockers(existing_blockers, base, runtime_trace)

    considered = facts.obligation_status != UNKNOWN
    eligible = bool(
        considered
        and facts.obligation_status == REQUIRED
        and unsatisfied_required
        and not blockers
    )
    added_classes = [
        item for item in unsatisfied_required if item not in set(existing_missing)
    ]
    used = bool(eligible and added_classes)
    recommendation_out = dict(base)
    if used:
        missing = [*existing_missing, *added_classes]
        bridge_reason = "official_source_obligation_bridge:" + ",".join(
            added_classes
        )
        recommendation_out.update(
            {
                "source_class_recovery_recommended": True,
                "source_class_recovery_shadow_mode": True,
                "missing_expected_source_classes": missing,
                "source_class_recovery_reason": (
                    base.get("source_class_recovery_reason") or bridge_reason
                ),
                "source_class_recovery_trigger_fields": _append_unique(
                    base.get("source_class_recovery_trigger_fields"),
                    (
                        "official_source_obligation_trace",
                        "official_source_obligation_bridge",
                    ),
                ),
            }
        )
        if "source_class_recovery_queries" in recommendation_out:
            recommendation_out["source_class_recovery_query_count"] = len(
                _string_list(recommendation_out.get("source_class_recovery_queries"))
            )

    trace_payload = {
        "schema_version": OFFICIAL_SOURCE_OBLIGATION_BRIDGE_SCHEMA_VERSION,
        "trace_mode": "runtime_expectation_bridge",
        "bridge_considered": considered,
        "bridge_eligible": eligible,
        "bridge_used": used,
        "bridge_skip_reason": _skip_reason(
            facts=facts,
            considered=considered,
            allowed_required=allowed_required,
            unsatisfied_required=unsatisfied_required,
            added_classes=added_classes,
            blockers=blockers,
        ),
        "bridge_blockers": blockers,
        "bridge_source": facts.obligation_source,
        "bridge_required_source_classes": unsatisfied_required,
        "bridge_candidate_query_available": _candidate_query_available(facts),
        "bridge_candidate_query_count": facts.candidate_query_count,
        "bridge_candidate_query_previews": list(facts.candidate_query_previews),
        "bridge_recovery_recommended": bool(
            recommendation_out.get("source_class_recovery_recommended")
        ),
        "bridge_recovery_reason": recommendation_out.get(
            "source_class_recovery_reason"
        ),
        "bridge_added_missing_source_classes": added_classes,
        "bridge_existing_missing_source_classes": existing_missing,
        "bridge_satisfied_source_classes": satisfied,
        "behavior_changed": used,
        "protected_surface": {
            "provider_policy_unchanged": True,
            "depth_policy_unchanged": True,
            "query_generation_unchanged": True,
            "generated_query_text_unchanged": True,
            "prompt_unchanged": True,
            "source_ranking_unchanged": True,
            "runtime_source_classification_unchanged": True,
            "final_answer_behavior_unchanged": True,
            "retrieve_targeted_promoted": False,
        },
        "consumer": [
            "source_class_recovery_recommendation_input",
            "answer_contract_runtime_handoff",
            "evidence_integration_checkpoint",
            "local_output_quality_review_packet",
        ],
        "decision_enabled": [
            "official_current_canonical_obligation_visible_to_runtime_expectation",
            "preferred_and_unknown_obligations_do_not_force_recovery",
            "existing_blockers_remain_authoritative",
            "candidate_query_visibility_not_backfilled",
        ],
        "promotion_or_deletion_criteria": {
            "keep_if": "ag49c_validates_obligation_to_runtime_expectation_gap",
            "promote_if": "future_controller_lane_consumes_required_source_classes_directly",
            "remove_if": "source_class_expectation_natively_receives_obligation_facts",
        },
    }
    return OfficialSourceObligationBridgeResult(
        recommendation=recommendation_out,
        trace={
            "schema_version": OFFICIAL_SOURCE_OBLIGATION_BRIDGE_SCHEMA_VERSION,
            "trace_mode": "runtime_expectation_bridge",
            "OfficialSourceObligationBridge": _safe_value(trace_payload),
        },
    )


def build_official_source_obligation_bridge_trace(
    runtime_trace: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a trace-only bridge packet from an assembled runtime trace."""
    return apply_official_source_obligation_bridge(
        recommendation=runtime_trace,
        runtime_trace=runtime_trace,
    ).trace


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
    added_classes: list[str],
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
    if not added_classes:
        return "required_source_class_already_visible"
    return None


def _candidate_query_available(
    facts: OfficialSourceObligationCandidateVisibilityFacts,
) -> bool | str:
    if facts.candidate_query_count == UNKNOWN:
        return UNKNOWN
    if isinstance(facts.candidate_query_count, int):
        return facts.candidate_query_count > 0
    return False


def _status_by_class(
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for source in (runtime_trace, recommendation):
        if not isinstance(source, Mapping):
            continue
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
    runtime_trace: Mapping[str, Any] | None,
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
    runtime_trace: Mapping[str, Any] | None,
    source_class: str,
) -> bool:
    for source in (runtime_trace, recommendation):
        if not isinstance(source, Mapping):
            continue
        counts = source.get("source_class_strong_satisfaction_counts")
        if not isinstance(counts, Mapping):
            continue
        try:
            if int(counts.get(source_class, 0) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _bridge_blockers(
    explicit_blockers: Iterable[Any],
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any] | None,
) -> list[str]:
    blockers: list[str] = []
    for source in (
        explicit_blockers,
        recommendation.get("active_source_class_recovery_blockers"),
        recommendation.get("source_class_recovery_candidate_v2_blockers"),
        (runtime_trace or {}).get("active_source_class_recovery_blockers")
        if isinstance(runtime_trace, Mapping)
        else (),
        (runtime_trace or {}).get("source_class_recovery_candidate_v2_blockers")
        if isinstance(runtime_trace, Mapping)
        else (),
    ):
        for item in _string_list(source):
            if item in _BLOCKERS_THAT_PRESERVE_EXISTING_OWNERSHIP:
                _append_one(blockers, item)
    return blockers


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


def _append_unique(value: Any, additions: Iterable[str]) -> list[str]:
    out = _string_list(value)
    for item in additions:
        _append_one(out, item)
    return out


def _append_one(target: list[str], value: str) -> None:
    if value and value not in target:
        target.append(value)


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
    "OFFICIAL_SOURCE_OBLIGATION_BRIDGE_SCHEMA_VERSION",
    "OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY",
    "OfficialSourceObligationBridgeResult",
    "apply_official_source_obligation_bridge",
    "build_official_source_obligation_bridge_trace",
]
