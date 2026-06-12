"""Passive AG-49A official-source survival runtime projection.

This module consumes already-computed sanitized runtime trace facts and emits a
compact diagnostic projection. It does not inspect provider payloads, prompts,
logs, DB rows, caches, or raw traces, and it does not participate in retrieval
or final-answer behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.official_source_survival_diagnostics import (
    ACCEPTED_SOURCE_DROPPED_BEFORE_FINAL_EVIDENCE,
    ANSWER_CORRECTLY_CAVEATED_MISSING_SOURCE,
    CANDIDATE_ACCEPTANCE_STAGE,
    CANDIDATE_ACQUISITION_STAGE,
    CANDIDATE_QUERY_GENERATION_STAGE,
    CAVEAT_ABSENT,
    CAVEAT_NOT_APPLICABLE,
    CAVEAT_PRESENT,
    CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED,
    CITED_VALUE_EXTRACTION_STAGE,
    FINAL_CITATION_SURVIVAL_STAGE,
    FINAL_EVIDENCE_SOURCE_NOT_CITED,
    FINAL_EVIDENCE_SURVIVAL_STAGE,
    NO_ACTION_LANE,
    NO_CANDIDATE_QUERY,
    NO_OFFICIAL_CANDIDATES_RETURNED,
    NOT_A_SOURCE_ACQUISITION_FAILURE,
    NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE,
    OBLIGATION_NOT_DETECTED,
    OFFICIAL_CANDIDATE_REJECTED_OR_UNREADABLE,
    SOURCE_ACQUISITION_SURVIVAL_LANE,
    SOURCE_FIT_CITATION_SURVIVAL_LANE,
    SOURCE_OBLIGATION_DETECTION_STAGE,
    SOURCE_SURVIVED_STAGE,
)

OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY = (
    "official_source_survival_projection_trace"
)
OFFICIAL_SOURCE_SURVIVAL_PROJECTION_SCHEMA_VERSION = (
    "official_source_survival_projection_ag49a_v1"
)

UNKNOWN = "unknown"
NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS = (
    "stage_not_observable_from_allowed_artifacts"
)
OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE = (
    "official_source_survival_instrumentation"
)

_OFFICIAL_OR_CANONICAL_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
        "primary_source_documents",
        "archival_primary_text",
    }
)
_OFFICIAL_OR_LEGAL_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
    }
)
_CANONICAL_PRIMARY_CLASSES = frozenset(
    {"primary_source_documents", "archival_primary_text"}
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
class OfficialSourceSurvivalProjectionFacts:
    """Sanitized facts used by the AG-49A projection."""

    question_type: str
    required_classes: tuple[str, ...]
    source_obligation_required: bool | str
    required_source_obligation: str
    obligation_detected: bool | str
    candidate_query_count: int | str
    candidate_official_or_canonical_count: int | str
    accepted_official_or_canonical_count: int | str
    final_evidence_official_or_canonical_count: int | str
    final_citation_official_or_canonical_count: int | str
    caveat_present: bool | str
    numeric_value_mismatch: bool | str
    source_bound_value_present: bool | str

    @classmethod
    def from_runtime_trace(
        cls,
        runtime_trace: Mapping[str, Any] | None,
    ) -> "OfficialSourceSurvivalProjectionFacts":
        trace = _safe_mapping(runtime_trace)
        runtime_required_classes = _runtime_required_classes(trace)
        inferred_required_classes = _inferred_required_classes(trace)
        required_classes = runtime_required_classes or inferred_required_classes
        required = _source_obligation_required(trace, required_classes)
        return cls(
            question_type=_clean_text(
                trace.get("query_type")
                or trace.get("report_type")
                or trace.get("intent")
                or "unspecified",
                limit=80,
            )
            or "unspecified",
            required_classes=required_classes,
            source_obligation_required=required,
            required_source_obligation=_required_source_obligation(
                required_classes, required
            ),
            obligation_detected=_obligation_detected(
                required=required,
                runtime_required_classes=runtime_required_classes,
                inferred_required_classes=inferred_required_classes,
            ),
            candidate_query_count=_candidate_query_count(trace),
            candidate_official_or_canonical_count=UNKNOWN,
            accepted_official_or_canonical_count=_accepted_count(
                trace, required_classes
            ),
            final_evidence_official_or_canonical_count=_final_evidence_count(
                trace, required_classes
            ),
            final_citation_official_or_canonical_count=_final_citation_count(
                trace, required_classes
            ),
            caveat_present=_caveat_present(trace),
            numeric_value_mismatch=_numeric_value_mismatch(trace),
            source_bound_value_present=_source_bound_value_present(trace),
        )


def build_official_source_survival_projection_trace(
    facts: OfficialSourceSurvivalProjectionFacts | Mapping[str, Any] | None = None,
    *,
    runtime_trace: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build passive runtime-visible source survival diagnostics."""
    if isinstance(facts, OfficialSourceSurvivalProjectionFacts):
        active_facts = facts
    elif isinstance(facts, Mapping):
        active_facts = OfficialSourceSurvivalProjectionFacts.from_runtime_trace(facts)
    else:
        active_facts = OfficialSourceSurvivalProjectionFacts.from_runtime_trace(
            runtime_trace
        )

    classification = _classify_projection(active_facts)
    projection = {
        "diagnostic_only": True,
        "aggregate_counts_are_not_custody": True,
        "aggregate_counts_are_not_readiness": True,
        "aggregate_count_custody_interpretation": (
            "aggregate_survival_counts_are_not_custody_or_readiness_proof"
        ),
        "question_type": active_facts.question_type,
        "required_source_obligation": active_facts.required_source_obligation,
        "source_obligation_required": active_facts.source_obligation_required,
        "obligation_detected": active_facts.obligation_detected,
        "candidate_query_count": active_facts.candidate_query_count,
        "candidate_official_or_canonical_count": (
            active_facts.candidate_official_or_canonical_count
        ),
        "accepted_official_or_canonical_count": (
            active_facts.accepted_official_or_canonical_count
        ),
        "final_evidence_official_or_canonical_count": (
            active_facts.final_evidence_official_or_canonical_count
        ),
        "final_citation_official_or_canonical_count": (
            active_facts.final_citation_official_or_canonical_count
        ),
        "caveat_present": active_facts.caveat_present,
        "numeric_value_mismatch": active_facts.numeric_value_mismatch,
        "source_bound_value_present": active_facts.source_bound_value_present,
        "missing_stage": classification["missing_stage"],
        "bottleneck_class": classification["bottleneck_class"],
        "recommended_next_lane": classification["recommended_next_lane"],
        "caveat_status": _caveat_status(active_facts),
        "behavior_changed": False,
        "source_survival_observability_status": classification[
            "source_survival_observability_status"
        ],
        "unknown_fields": _unknown_fields(active_facts),
        "required_source_classes": list(active_facts.required_classes),
        "consumer": [
            "local_output_quality_review_packet",
            "future_official_current_canonical_source_quality_validation",
            "ag48a_ag48b_diagnostic_classifiers",
            "ag48c_next_lane_decision_follow_up",
        ],
        "decision_enabled": [
            "distinguish_source_obligation_not_detected",
            "distinguish_candidate_query_unavailable",
            "distinguish_official_candidate_visibility_gap",
            "distinguish_candidate_acceptance_visibility_gap",
            "distinguish_final_evidence_absence",
            "distinguish_final_evidence_source_not_cited",
            "distinguish_cited_source_value_extraction_visibility_gap",
            "distinguish_stage_not_observable_from_allowed_artifacts",
        ],
        "promotion_or_deletion_criteria": {
            "keep_if": "used_by_ag49_validation_and_future_official_source_quality_phases",
            "collapse_if": "source_survival_diagnostics_move_into_consolidated_controller_handoff",
            "remove_if": "fields_are_redundant_with_existing_safe_handoff",
        },
        "protected_surface": {
            "provider_policy_unchanged": True,
            "depth_policy_unchanged": True,
            "query_generation_unchanged": True,
            "prompt_unchanged": True,
            "source_ranking_unchanged": True,
            "runtime_source_classification_unchanged": True,
            "final_answer_behavior_unchanged": True,
            "raw_provider_payload_visible": False,
            "raw_prompt_visible": False,
            "raw_trace_visible": False,
            "db_rows_visible": False,
            "secrets_visible": False,
        },
    }
    return {
        "schema_version": OFFICIAL_SOURCE_SURVIVAL_PROJECTION_SCHEMA_VERSION,
        "trace_mode": "passive_runtime_visibility",
        "OfficialSourceSurvivalProjection": _safe_value(projection),
    }


def _classify_projection(
    facts: OfficialSourceSurvivalProjectionFacts,
) -> dict[str, str]:
    if facts.source_obligation_required is False:
        return _projection_result(
            NOT_A_SOURCE_ACQUISITION_FAILURE,
            SOURCE_SURVIVED_STAGE,
            NO_ACTION_LANE,
            "source_obligation_not_required",
        )
    if facts.source_obligation_required == UNKNOWN:
        return _projection_result(
            NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS,
            SOURCE_OBLIGATION_DETECTION_STAGE,
            OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE,
            "source_obligation_not_observable",
        )
    if facts.obligation_detected is False:
        return _projection_result(
            OBLIGATION_NOT_DETECTED,
            SOURCE_OBLIGATION_DETECTION_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            "source_obligation_required_but_not_detected",
        )

    downstream_candidate_survived = any(
        _positive_known(value)
        for value in (
            facts.candidate_official_or_canonical_count,
            facts.accepted_official_or_canonical_count,
            facts.final_evidence_official_or_canonical_count,
            facts.final_citation_official_or_canonical_count,
        )
    )
    if facts.candidate_query_count == UNKNOWN and not downstream_candidate_survived:
        return _projection_result(
            NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS,
            CANDIDATE_QUERY_GENERATION_STAGE,
            OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE,
            "candidate_query_availability_not_observable",
        )
    if facts.candidate_query_count == 0 and not downstream_candidate_survived:
        return _projection_result(
            NO_CANDIDATE_QUERY,
            CANDIDATE_QUERY_GENERATION_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            "source_obligation_detected_but_no_candidate_query_visible",
        )

    downstream_accepted = any(
        _positive_known(value)
        for value in (
            facts.accepted_official_or_canonical_count,
            facts.final_evidence_official_or_canonical_count,
            facts.final_citation_official_or_canonical_count,
        )
    )
    if (
        facts.candidate_official_or_canonical_count == UNKNOWN
        and not downstream_accepted
    ):
        return _projection_result(
            NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS,
            CANDIDATE_ACQUISITION_STAGE,
            OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE,
            "official_or_canonical_candidate_visibility_not_observable",
        )
    if (
        facts.candidate_official_or_canonical_count == 0
        and not downstream_accepted
    ):
        if facts.caveat_present is True and facts.numeric_value_mismatch is not True:
            return _projection_result(
                ANSWER_CORRECTLY_CAVEATED_MISSING_SOURCE,
                CANDIDATE_ACQUISITION_STAGE,
                SOURCE_ACQUISITION_SURVIVAL_LANE,
                "no_official_candidate_visible_and_answer_caveated",
            )
        return _projection_result(
            NO_OFFICIAL_CANDIDATES_RETURNED,
            CANDIDATE_ACQUISITION_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            "no_official_or_canonical_candidate_visible",
        )

    downstream_final_evidence = any(
        _positive_known(value)
        for value in (
            facts.final_evidence_official_or_canonical_count,
            facts.final_citation_official_or_canonical_count,
        )
    )
    if (
        facts.accepted_official_or_canonical_count == UNKNOWN
        and not downstream_final_evidence
    ):
        return _projection_result(
            NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS,
            CANDIDATE_ACCEPTANCE_STAGE,
            OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE,
            "candidate_acceptance_or_readability_not_observable",
        )
    if facts.accepted_official_or_canonical_count == 0 and not downstream_final_evidence:
        return _projection_result(
            OFFICIAL_CANDIDATE_REJECTED_OR_UNREADABLE,
            CANDIDATE_ACCEPTANCE_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            "official_or_canonical_candidate_not_accepted_or_readable",
        )

    if facts.final_evidence_official_or_canonical_count == UNKNOWN:
        if _positive_known(facts.final_citation_official_or_canonical_count):
            return _cited_source_result(facts)
        return _projection_result(
            NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS,
            FINAL_EVIDENCE_SURVIVAL_STAGE,
            OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE,
            "final_evidence_survival_not_observable",
        )
    if facts.final_evidence_official_or_canonical_count == 0:
        return _projection_result(
            ACCEPTED_SOURCE_DROPPED_BEFORE_FINAL_EVIDENCE
            if _positive_known(facts.accepted_official_or_canonical_count)
            else NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS,
            FINAL_EVIDENCE_SURVIVAL_STAGE,
            SOURCE_ACQUISITION_SURVIVAL_LANE,
            "official_or_canonical_source_absent_from_final_evidence",
        )

    if facts.final_citation_official_or_canonical_count == UNKNOWN:
        return _projection_result(
            NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS,
            FINAL_CITATION_SURVIVAL_STAGE,
            OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE,
            "final_citation_survival_not_observable",
        )
    if facts.final_citation_official_or_canonical_count == 0:
        return _projection_result(
            FINAL_EVIDENCE_SOURCE_NOT_CITED,
            FINAL_CITATION_SURVIVAL_STAGE,
            SOURCE_FIT_CITATION_SURVIVAL_LANE,
            "final_evidence_source_not_cited",
        )

    return _cited_source_result(facts)


def _cited_source_result(
    facts: OfficialSourceSurvivalProjectionFacts,
) -> dict[str, str]:
    if facts.numeric_value_mismatch is True:
        return _projection_result(
            CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED,
            CITED_VALUE_EXTRACTION_STAGE,
            NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE,
            "official_or_canonical_citation_survived_but_value_mismatch_visible",
        )
    if facts.source_bound_value_present == UNKNOWN:
        return _projection_result(
            NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS,
            CITED_VALUE_EXTRACTION_STAGE,
            OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE,
            "cited_source_present_but_source_bound_value_visibility_unknown",
        )
    if facts.source_bound_value_present is False:
        return _projection_result(
            CITATION_SURVIVED_BUT_VALUE_EXTRACTION_FAILED,
            CITED_VALUE_EXTRACTION_STAGE,
            NUMERIC_EXTRACTION_SOURCE_BOUND_VALUE_LANE,
            "official_or_canonical_citation_survived_but_source_bound_value_missing",
        )
    return _projection_result(
        NOT_A_SOURCE_ACQUISITION_FAILURE,
        SOURCE_SURVIVED_STAGE,
        NO_ACTION_LANE,
        "required_source_survived_through_final_citation",
    )


def _projection_result(
    bottleneck_class: str,
    missing_stage: str,
    recommended_next_lane: str,
    status: str,
) -> dict[str, str]:
    return {
        "bottleneck_class": bottleneck_class,
        "missing_stage": missing_stage,
        "recommended_next_lane": recommended_next_lane,
        "source_survival_observability_status": status,
    }


def _runtime_required_classes(trace: Mapping[str, Any]) -> tuple[str, ...]:
    classes = []
    for key in (
        "expected_source_classes_raw",
        "source_class_gap_candidates",
        "active_source_class_recovery_missing_classes",
    ):
        classes.extend(_compact_tokens(trace.get(key)))
    status = trace.get("source_class_satisfaction_status")
    if isinstance(status, Mapping):
        classes.extend(_clean_token(key) for key in status if _clean_token(key))
    return tuple(
        item
        for item in _dedupe(classes)
        if item and item != "none" and item in _OFFICIAL_OR_CANONICAL_CLASSES
    )


def _inferred_required_classes(trace: Mapping[str, Any]) -> tuple[str, ...]:
    text = " ".join(
        str(part or "")
        for part in (
            trace.get("query_preview"),
            trace.get("query_type"),
            trace.get("report_type"),
            trace.get("intent"),
        )
    ).casefold()
    current_numeric = any(year in text for year in ("2024", "2025", "2026", "2027"))
    public_program_amount = any(
        marker in text
        for marker in (
            "benefit",
            "cola",
            "cost-of-living",
            "earnings test",
            "earnings-test",
            "eligibility",
            "federal payment",
            "limit",
            "payment amount",
            "tax credit",
            "taxable maximum",
            "threshold",
        )
    )
    government_or_current = any(
        marker in text
        for marker in (
            "current",
            "federal",
            "government",
            "legal",
            "official",
            "program",
            "regulatory",
            "statutory",
        )
    )
    if current_numeric and public_program_amount and government_or_current:
        return ("official_current_rules",)
    return ()


def _source_obligation_required(
    trace: Mapping[str, Any],
    required_classes: tuple[str, ...],
) -> bool | str:
    if required_classes:
        return True
    expected = trace.get("expected_source_classes_raw")
    if isinstance(expected, (list, tuple, set)):
        return False
    if isinstance(trace.get("source_class_satisfaction_status"), Mapping):
        return False
    return UNKNOWN


def _required_source_obligation(
    required_classes: tuple[str, ...],
    required: bool | str,
) -> str:
    if required is False:
        return "not_required"
    if required == UNKNOWN:
        return UNKNOWN
    if any(item in _OFFICIAL_OR_LEGAL_CLASSES for item in required_classes):
        return "official/current government or legal source"
    if any(item in _CANONICAL_PRIMARY_CLASSES for item in required_classes):
        return "canonical or primary source"
    return "official/current/canonical source"


def _obligation_detected(
    *,
    required: bool | str,
    runtime_required_classes: tuple[str, ...],
    inferred_required_classes: tuple[str, ...],
) -> bool | str:
    if required is True and runtime_required_classes:
        return True
    if required is True and inferred_required_classes:
        return False
    if required is False:
        return False
    return UNKNOWN


def _candidate_query_count(trace: Mapping[str, Any]) -> int | str:
    for key in ("active_source_class_recovery_queries", "source_class_recovery_queries"):
        if key in trace:
            return len(_compact_strings(trace.get(key)))
    return UNKNOWN


def _accepted_count(
    trace: Mapping[str, Any],
    required_classes: tuple[str, ...],
) -> int | str:
    counts = trace.get("source_tier_counts")
    if not isinstance(counts, Mapping):
        return UNKNOWN
    if any(item in _OFFICIAL_OR_LEGAL_CLASSES for item in required_classes):
        return _non_negative_int(counts.get("official"))
    return UNKNOWN


def _final_evidence_count(
    trace: Mapping[str, Any],
    required_classes: tuple[str, ...],
) -> int | str:
    value = trace.get("source_survival_final_evidence_official_or_canonical_count")
    if value is not None:
        return _non_negative_int(value)
    packet = trace.get("source_class_recovery_validation_packet")
    if isinstance(packet, Mapping):
        counts = packet.get("evidence_bundle_official_legal_current_primary_counts")
        count = _class_count(counts, required_classes)
        if count != UNKNOWN:
            return count
    return UNKNOWN


def _final_citation_count(
    trace: Mapping[str, Any],
    required_classes: tuple[str, ...],
) -> int | str:
    value = trace.get("source_survival_final_citation_official_or_canonical_count")
    if value is not None:
        return _non_negative_int(value)
    packet = trace.get("source_class_recovery_validation_packet")
    if isinstance(packet, Mapping):
        counts = packet.get("final_cited_official_legal_current_primary_counts")
        count = _class_count(counts, required_classes)
        if count != UNKNOWN:
            return count
    return _class_count(trace.get("source_class_strong_satisfaction_counts"), required_classes)


def _class_count(
    counts: Any,
    required_classes: tuple[str, ...],
) -> int | str:
    if not isinstance(counts, Mapping):
        return UNKNOWN
    keys = required_classes or tuple(_OFFICIAL_OR_CANONICAL_CLASSES)
    values = [_non_negative_int(counts.get(key)) for key in keys if key in counts]
    if not values:
        return UNKNOWN
    return max(values)


def _caveat_present(trace: Mapping[str, Any]) -> bool | str:
    answer_class = _clean_token(trace.get("answer_class"))
    if answer_class in {"insufficient_answer", "partial_answer", "data_unavailable"}:
        return True
    if answer_class in {"answer", "direct_answer", "complete_answer"}:
        return False
    return UNKNOWN


def _numeric_value_mismatch(trace: Mapping[str, Any]) -> bool | str:
    for key in (
        "numeric_value_mismatch",
        "quantitative_consistency_mismatch_detected",
        "quant_retrieval_value_mismatch",
    ):
        if key in trace:
            return bool(trace.get(key))
    return UNKNOWN


def _source_bound_value_present(trace: Mapping[str, Any]) -> bool | str:
    if "source_bound_value_count" in trace:
        return _non_negative_int(trace.get("source_bound_value_count")) > 0
    if "quant_retrieval_exact_value_binding_valid" in trace:
        return bool(trace.get("quant_retrieval_exact_value_binding_valid"))
    return UNKNOWN


def _caveat_status(facts: OfficialSourceSurvivalProjectionFacts) -> str:
    if facts.source_obligation_required is False:
        return CAVEAT_NOT_APPLICABLE
    if facts.caveat_present is True:
        return CAVEAT_PRESENT
    if facts.caveat_present is False:
        return CAVEAT_ABSENT
    return UNKNOWN


def _unknown_fields(facts: OfficialSourceSurvivalProjectionFacts) -> list[str]:
    out = []
    for field_name in (
        "source_obligation_required",
        "obligation_detected",
        "candidate_query_count",
        "candidate_official_or_canonical_count",
        "accepted_official_or_canonical_count",
        "final_evidence_official_or_canonical_count",
        "final_citation_official_or_canonical_count",
        "caveat_present",
        "numeric_value_mismatch",
        "source_bound_value_present",
    ):
        if getattr(facts, field_name) == UNKNOWN:
            out.append(field_name)
    return out


def _positive_known(value: int | str | bool) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _safe_mapping(value: Any) -> dict[str, Any]:
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


def _compact_tokens(value: Any) -> tuple[str, ...]:
    return tuple(
        item
        for item in (_clean_token(part) for part in _iterable_values(value))
        if item
    )


def _compact_strings(value: Any) -> tuple[str, ...]:
    return tuple(
        item
        for item in (_clean_text(part, limit=160) for part in _iterable_values(value))
        if item
    )


def _iterable_values(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Mapping):
        return tuple(value.values())
    if value is None or isinstance(value, (str, bytes)):
        return ()
    try:
        return tuple(value)
    except TypeError:
        return ()


def _dedupe(values: list[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return out


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


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
    "NOT_OBSERVABLE_FROM_ALLOWED_ARTIFACTS",
    "OFFICIAL_SOURCE_SURVIVAL_INSTRUMENTATION_LANE",
    "OFFICIAL_SOURCE_SURVIVAL_PROJECTION_SCHEMA_VERSION",
    "OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY",
    "UNKNOWN",
    "OfficialSourceSurvivalProjectionFacts",
    "build_official_source_survival_projection_trace",
]
