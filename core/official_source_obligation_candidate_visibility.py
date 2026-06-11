"""Passive AG-49B official-source obligation and candidate visibility diagnostics.

This module consumes already-computed sanitized runtime facts and emits compact
review diagnostics. It does not call providers, inspect prompts, read logs, alter
retrieval, or participate in final-answer behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from core.official_source_survival_projection import (
    OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY,
    UNKNOWN,
)

OFFICIAL_SOURCE_OBLIGATION_TRACE_KEY = "official_source_obligation_trace"
OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY = (
    "official_source_candidate_visibility_trace"
)
OFFICIAL_SOURCE_OBLIGATION_CANDIDATE_SCHEMA_VERSION = (
    "official_source_obligation_candidate_visibility_ag49b_v1"
)

REQUIRED = "required"
PREFERRED = "preferred"
NOT_REQUIRED = "not_required"

_VISIBLE = "visible"
_NOT_VISIBLE = "not_visible"
_NONE_VISIBLE = "none_visible"
_ABSENT = "absent"

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

_REQUIRED_TRIGGER_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "exact_numeric_status_date_threshold_eligibility_compliance_claim",
        (
            "amount",
            "benefit",
            "cola",
            "compliance",
            "date",
            "deadline",
            "earnings test",
            "earnings-test",
            "effective",
            "eligibility",
            "federal payment",
            "limit",
            "maximum",
            "payment",
            "rule",
            "status",
            "taxable maximum",
            "threshold",
        ),
    ),
    (
        "current_rule_status_request",
        (
            "current",
            "latest",
            "now",
            "operative",
            "this year",
            "today",
            "updated",
        ),
    ),
    (
        "legal_regulatory_current_primary_request",
        (
            "agency",
            "federal",
            "government",
            "legal",
            "official",
            "regulation",
            "regulatory",
            "statute",
            "statutory",
        ),
    ),
)

_CANONICAL_TECHNICAL_TERMS = (
    "api",
    "database",
    "documentation",
    "framework",
    "how",
    "library",
    "mode",
    "protocol",
    "reference",
    "software",
    "standard",
    "tradeoff",
    "wal",
    "write-ahead",
    "works",
)

_PREFERRED_CONTEXT_TERMS = (
    "breaking",
    "current",
    "latest",
    "news",
    "recent",
    "this month",
    "this week",
    "today",
    "what happened",
)

_OFFICIAL_QUERY_INTENT_TERMS = (
    ".gov",
    "agency",
    "canonical",
    "docs",
    "documentation",
    "federal",
    "fact sheet",
    "government",
    "official",
    "primary",
    "regulation",
    "source",
    "statute",
)


@dataclass(frozen=True)
class OfficialSourceObligationCandidateVisibilityFacts:
    """Sanitized facts used by the AG-49B projection."""

    question_type: str
    obligation_status: str
    obligation_reason: str
    obligation_source: str
    obligation_required_or_preferred: str
    obligation_detected_by_runtime: bool | str
    obligation_trigger_terms: tuple[str, ...]
    required_source_classes: tuple[str, ...]
    candidate_query_visibility_status: str
    candidate_query_count: int | str
    candidate_query_previews: tuple[str, ...]
    candidate_query_official_intent_status: str
    candidate_official_source_visibility_status: str
    candidate_official_source_count: int | str
    candidate_official_source_domain_previews: tuple[str, ...]
    accepted_or_readable_visibility_status: str
    accepted_or_readable_official_source_count: int | str
    final_evidence_survival_status: str
    final_citation_survival_status: str
    final_evidence_official_or_canonical_count: int | str
    final_citation_official_or_canonical_count: int | str
    likely_visibility_gap: str

    @classmethod
    def from_runtime_trace(
        cls,
        runtime_trace: Mapping[str, Any] | None,
    ) -> "OfficialSourceObligationCandidateVisibilityFacts":
        trace = _safe_mapping(runtime_trace)
        survival = _survival_projection_payload(trace)
        obligation = _obligation(trace, survival)
        query_previews = _candidate_query_previews(trace)
        candidate_query_count = _candidate_query_count(trace, query_previews)
        candidate_source_count = _candidate_official_source_count(trace)
        candidate_domains = _candidate_official_source_domains(trace)
        accepted_count = _accepted_or_readable_official_count(trace)
        final_evidence_count = _final_count(
            trace,
            survival,
            "source_survival_final_evidence_official_or_canonical_count",
            "final_evidence_official_or_canonical_count",
        )
        final_citation_count = _final_count(
            trace,
            survival,
            "source_survival_final_citation_official_or_canonical_count",
            "final_citation_official_or_canonical_count",
        )
        values = {
            "obligation_status": obligation["status"],
            "obligation_detected_by_runtime": obligation[
                "detected_by_runtime"
            ],
            "candidate_query_count": candidate_query_count,
            "candidate_official_source_count": candidate_source_count,
            "accepted_or_readable_official_source_count": accepted_count,
            "final_evidence_official_or_canonical_count": final_evidence_count,
            "final_citation_official_or_canonical_count": final_citation_count,
        }
        return cls(
            question_type=_question_type(trace),
            obligation_status=str(obligation["status"]),
            obligation_reason=str(obligation["reason"]),
            obligation_source=str(obligation["source"]),
            obligation_required_or_preferred=str(obligation["required_or_preferred"]),
            obligation_detected_by_runtime=obligation["detected_by_runtime"],
            obligation_trigger_terms=tuple(obligation["trigger_terms"]),
            required_source_classes=tuple(obligation["required_classes"]),
            candidate_query_visibility_status=_query_visibility_status(
                candidate_query_count,
                query_previews,
            ),
            candidate_query_count=candidate_query_count,
            candidate_query_previews=query_previews,
            candidate_query_official_intent_status=_query_intent_status(
                candidate_query_count,
                query_previews,
            ),
            candidate_official_source_visibility_status=_count_visibility_status(
                candidate_source_count
            ),
            candidate_official_source_count=candidate_source_count,
            candidate_official_source_domain_previews=candidate_domains,
            accepted_or_readable_visibility_status=_count_visibility_status(
                accepted_count
            ),
            accepted_or_readable_official_source_count=accepted_count,
            final_evidence_survival_status=_count_visibility_status(
                final_evidence_count
            ),
            final_citation_survival_status=_count_visibility_status(
                final_citation_count
            ),
            final_evidence_official_or_canonical_count=final_evidence_count,
            final_citation_official_or_canonical_count=final_citation_count,
            likely_visibility_gap=_likely_visibility_gap(values),
        )


def build_official_source_obligation_candidate_visibility_traces(
    facts: OfficialSourceObligationCandidateVisibilityFacts
    | Mapping[str, Any]
    | None = None,
    *,
    runtime_trace: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build passive runtime-visible AG-49B diagnostic traces."""
    if isinstance(facts, OfficialSourceObligationCandidateVisibilityFacts):
        active_facts = facts
    elif isinstance(facts, Mapping):
        active_facts = OfficialSourceObligationCandidateVisibilityFacts.from_runtime_trace(
            facts
        )
    else:
        active_facts = OfficialSourceObligationCandidateVisibilityFacts.from_runtime_trace(
            runtime_trace
        )

    obligation_payload = {
        "question_type": active_facts.question_type,
        "obligation_status": active_facts.obligation_status,
        "obligation_reason": active_facts.obligation_reason,
        "obligation_source": active_facts.obligation_source,
        "obligation_required_or_preferred": (
            active_facts.obligation_required_or_preferred
        ),
        "obligation_detected_by_runtime": (
            active_facts.obligation_detected_by_runtime
        ),
        "obligation_trigger_terms": list(active_facts.obligation_trigger_terms),
        "required_source_classes": list(active_facts.required_source_classes),
        "unknown_fields": _unknown_fields(active_facts),
        "behavior_changed": False,
    }
    candidate_payload = {
        **obligation_payload,
        "candidate_query_visibility_status": (
            active_facts.candidate_query_visibility_status
        ),
        "candidate_query_count": active_facts.candidate_query_count,
        "candidate_query_previews": list(active_facts.candidate_query_previews),
        "candidate_query_official_intent_status": (
            active_facts.candidate_query_official_intent_status
        ),
        "candidate_official_source_visibility_status": (
            active_facts.candidate_official_source_visibility_status
        ),
        "candidate_official_source_count": (
            active_facts.candidate_official_source_count
        ),
        "candidate_official_source_domain_previews": list(
            active_facts.candidate_official_source_domain_previews
        ),
        "accepted_or_readable_visibility_status": (
            active_facts.accepted_or_readable_visibility_status
        ),
        "accepted_or_readable_official_source_count": (
            active_facts.accepted_or_readable_official_source_count
        ),
        "final_evidence_survival_status": (
            active_facts.final_evidence_survival_status
        ),
        "final_citation_survival_status": (
            active_facts.final_citation_survival_status
        ),
        "final_evidence_official_or_canonical_count": (
            active_facts.final_evidence_official_or_canonical_count
        ),
        "final_citation_official_or_canonical_count": (
            active_facts.final_citation_official_or_canonical_count
        ),
        "likely_visibility_gap": active_facts.likely_visibility_gap,
        "consumer": [
            "local_output_quality_review_packet",
            "future_official_current_canonical_source_quality_validation",
            "ag48a_ag48b_classifiers",
            "ag49a_ag49b_source_survival_projection_follow_up",
            "future_repair_lane_selection",
        ],
        "decision_enabled": [
            "distinguish_required_preferred_not_required_unknown_obligation",
            "distinguish_obligation_detection_gap_from_candidate_visibility_gap",
            "distinguish_candidate_query_unavailable_from_official_candidate_unavailable",
            "distinguish_accepted_readable_visibility_gap_from_final_survival_gap",
            "preserve_unknown_when_candidate_stage_is_not_observable",
        ],
        "promotion_or_deletion_criteria": {
            "keep_if": "used_by_ag49_validation_and_future_official_source_repair_lanes",
            "collapse_if": "consolidated_controller_handoff_becomes_primary_review_artifact",
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
        OFFICIAL_SOURCE_OBLIGATION_TRACE_KEY: {
            "schema_version": OFFICIAL_SOURCE_OBLIGATION_CANDIDATE_SCHEMA_VERSION,
            "trace_mode": "passive_runtime_visibility",
            "OfficialSourceObligation": _safe_value(obligation_payload),
        },
        OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY: {
            "schema_version": OFFICIAL_SOURCE_OBLIGATION_CANDIDATE_SCHEMA_VERSION,
            "trace_mode": "passive_runtime_visibility",
            "OfficialSourceCandidateVisibility": _safe_value(candidate_payload),
        },
    }


def _question_type(trace: Mapping[str, Any]) -> str:
    return (
        _clean_text(
            trace.get("query_type")
            or trace.get("report_type")
            or trace.get("intent")
            or "unspecified",
            limit=80,
        )
        or "unspecified"
    )


def _obligation(
    trace: Mapping[str, Any],
    survival: Mapping[str, Any],
) -> dict[str, Any]:
    runtime_classes = _runtime_required_classes(trace)
    survival_classes = tuple(
        item
        for item in _compact_tokens(survival.get("required_source_classes"))
        if item in _OFFICIAL_OR_CANONICAL_CLASSES
    )
    classes = runtime_classes or survival_classes
    if classes:
        reason = (
            "official_agency_or_canonical_technical_behavior_request"
            if any(item in _CANONICAL_PRIMARY_CLASSES for item in classes)
            else "legal_regulatory_current_primary_request"
        )
        return {
            "status": REQUIRED,
            "reason": reason,
            "source": "runtime_source_class_expectation",
            "required_or_preferred": REQUIRED,
            "detected_by_runtime": True,
            "trigger_terms": classes,
            "required_classes": classes,
        }

    inferred = _inferred_obligation(trace)
    if inferred["status"] != UNKNOWN:
        return inferred

    expected = trace.get("expected_source_classes_raw")
    if isinstance(expected, (list, tuple, set)):
        return {
            "status": NOT_REQUIRED,
            "reason": "unclear_no_obligation_detected",
            "source": "runtime_source_class_expectation",
            "required_or_preferred": NOT_REQUIRED,
            "detected_by_runtime": False,
            "trigger_terms": (),
            "required_classes": (),
        }
    if _clean_text(trace.get("query_preview"), limit=300):
        return {
            "status": NOT_REQUIRED,
            "reason": "unclear_no_obligation_detected",
            "source": "sanitized_query_preview_inference",
            "required_or_preferred": NOT_REQUIRED,
            "detected_by_runtime": False,
            "trigger_terms": (),
            "required_classes": (),
        }
    return {
        "status": UNKNOWN,
        "reason": UNKNOWN,
        "source": UNKNOWN,
        "required_or_preferred": UNKNOWN,
        "detected_by_runtime": UNKNOWN,
        "trigger_terms": (),
        "required_classes": (),
    }


def _runtime_required_classes(trace: Mapping[str, Any]) -> tuple[str, ...]:
    classes: list[str] = []
    for key in (
        "expected_source_classes_raw",
        "source_class_gap_candidates",
        "active_source_class_recovery_missing_classes",
        "missing_expected_source_classes",
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


def _inferred_obligation(trace: Mapping[str, Any]) -> dict[str, Any]:
    text = _trace_text(trace)
    if not text:
        return {
            "status": UNKNOWN,
            "reason": UNKNOWN,
            "source": UNKNOWN,
            "required_or_preferred": UNKNOWN,
            "detected_by_runtime": UNKNOWN,
            "trigger_terms": (),
            "required_classes": (),
        }

    trigger_terms: list[str] = []
    group_hits: set[str] = set()
    for reason, terms in _REQUIRED_TRIGGER_GROUPS:
        hits = [term for term in terms if term in text]
        if hits:
            group_hits.add(reason)
            trigger_terms.extend(hits[:4])
    has_year_or_current = bool(
        group_hits & {"current_rule_status_request"}
    ) or any(year in text for year in ("2024", "2025", "2026", "2027"))
    has_exact_or_rule = bool(
        group_hits
        & {
            "exact_numeric_status_date_threshold_eligibility_compliance_claim",
            "legal_regulatory_current_primary_request",
        }
    )
    if has_year_or_current and has_exact_or_rule:
        reason = (
            "legal_regulatory_current_primary_request"
            if "legal_regulatory_current_primary_request" in group_hits
            else "exact_numeric_status_date_threshold_eligibility_compliance_claim"
        )
        return {
            "status": REQUIRED,
            "reason": reason,
            "source": "sanitized_query_preview_inference",
            "required_or_preferred": REQUIRED,
            "detected_by_runtime": False,
            "trigger_terms": tuple(_dedupe(trigger_terms)),
            "required_classes": ("official_current_rules",),
        }

    canonical_hits = [term for term in _CANONICAL_TECHNICAL_TERMS if term in text]
    if (
        len(canonical_hits) >= 3
        and any(term in text for term in ("how", "works", "mode", "reference"))
        and any(term in text for term in ("database", "api", "protocol", "software", "wal"))
    ):
        return {
            "status": REQUIRED,
            "reason": "official_agency_or_canonical_technical_behavior_request",
            "source": "sanitized_query_preview_inference",
            "required_or_preferred": REQUIRED,
            "detected_by_runtime": False,
            "trigger_terms": tuple(canonical_hits[:8]),
            "required_classes": ("primary_source_documents",),
        }

    if _government_access_identity_rule_request(
        text
    ) or _government_enforcement_date_rule_request(text):
        return {
            "status": REQUIRED,
            "reason": "government_access_identity_enforcement_rule_request",
            "source": "sanitized_query_preview_inference",
            "required_or_preferred": REQUIRED,
            "detected_by_runtime": False,
            "trigger_terms": (
                "government_access_identity_rule",
                "enforcement_date_rule",
            ),
            "required_classes": ("official_current_rules",),
        }

    preferred_hits = [term for term in _PREFERRED_CONTEXT_TERMS if term in text]
    if preferred_hits:
        return {
            "status": PREFERRED,
            "reason": "reputable_current_context_preferred",
            "source": "sanitized_query_preview_inference",
            "required_or_preferred": PREFERRED,
            "detected_by_runtime": False,
            "trigger_terms": tuple(preferred_hits[:6]),
            "required_classes": (),
        }

    return {
        "status": NOT_REQUIRED,
        "reason": "unclear_no_obligation_detected",
        "source": "sanitized_query_preview_inference",
        "required_or_preferred": NOT_REQUIRED,
        "detected_by_runtime": False,
        "trigger_terms": (),
        "required_classes": (),
    }


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _government_access_identity_rule_request(text: str) -> bool:
    identity_document_context = _has_any(
        text,
        (
            r"\b(?:identification|identity\s+documents?|id\s+documents?|"
            r"acceptable\s+ids?|accepted\s+ids?|valid\s+ids?)\b",
            r"\b(?:credentials?|proof\s+of\s+(?:identity|identification)|"
            r"identity\s+proof|documentary\s+proof)\b",
            r"\b(?:documents?|proof|credentials?)\s+"
            r"(?:accepted|required|needed|valid|acceptable)\b",
            r"\b(?:accepted|acceptable|required|valid)\s+"
            r"(?:documents?|proof|credentials?)\b",
        ),
    )
    if not identity_document_context:
        return False

    requirement_context = _has_any(
        text,
        (
            r"\b(?:need|needs|needed|require|required|requires|must|have\s+to)\b",
            r"\b(?:accepted|acceptable|valid|allowed|recognized|recognised)\b",
            r"\bwhat\s+(?:identification|documents?|credentials?|proof)\s+"
            r"(?:is|are)\s+(?:accepted|required|valid|needed)\b",
        ),
    )
    access_context = _has_any(
        text,
        (
            r"\b(?:access|entry|enter|admission|admitted|screening|"
            r"security\s+checkpoint|checkpoint|travel|flight|flights|"
            r"domestic\s+travel|domestic\s+flights?|air\s+travel|"
            r"board|boarding|service|services|benefits?|eligibility)\b",
        ),
    )
    if not (requirement_context and access_context):
        return False

    official_or_government_context = _has_any(
        text,
        (
            r"\b(?:official|government|public\s+authority|agency|"
            r"federal|state|county|municipal|local|provincial)\b",
            r"\b(?:regulatory|compliance|enforcement|effective\s+date|"
            r"official\s+requirements?)\b",
        ),
    )
    administered_access_context = _has_any(
        text,
        (
            r"\b(?:screening|security\s+checkpoint|checkpoint|border|customs|"
            r"airport|air\s+travel|domestic\s+travel|domestic\s+flights?|"
            r"flights?|public\s+services?|public\s+benefits?|courts?|"
            r"courthouse|government\s+building|voting|election|"
            r"immigration|licens(?:e|ing)|permits?)\b",
        ),
    )
    current_or_enforcement_context = _has_any(
        text,
        (
            r"\b(?:current|currently|now|today|latest|as\s+of)\b",
            r"\b(?:enforcement|effective|compliance)\s+(?:date|dates?|"
            r"start(?:ed)?|begin|began|status)\b",
            r"\bwhen\s+(?:did|does|do)\s+"
            r"(?:enforcement|the\s+rule|the\s+requirement)\s+"
            r"(?:start|begin|go\s+into\s+effect|take\s+effect)\b",
        ),
    )

    return bool(
        official_or_government_context
        or (administered_access_context and current_or_enforcement_context)
    )


def _government_enforcement_date_rule_request(text: str) -> bool:
    enforcement_date_context = _has_any(
        text,
        (
            r"\bwhen\s+(?:did|does|do)\s+"
            r"(?:enforcement|the\s+rule|the\s+requirement|requirements?)\s+"
            r"(?:start|begin|go\s+into\s+effect|take\s+effect)\b",
            r"\b(?:enforcement|effective|compliance)\s+(?:date|dates?)\b",
            r"\b(?:rule|requirement|requirements?)\s+"
            r"(?:start(?:ed)?|began|begin|effective|in\s+effect)\b",
        ),
    )
    if not enforcement_date_context:
        return False

    rule_context = _has_any(
        text,
        (
            r"\b(?:rules?|requirements?|guidance|eligibility|access|entry|"
            r"screening|compliance|enforcement|accepted|acceptable|valid)\b",
            r"\b(?:identification|id|credentials?|documents?|proof)\b",
        ),
    )
    government_context = _has_any(
        text,
        (
            r"\b(?:official|government|public\s+authority|agency|"
            r"federal|state|county|municipal|local|provincial|regulatory|"
            r"compliance)\b",
            r"\b(?:public\s+services?|public\s+benefits?|courts?|courthouse|"
            r"government\s+building|screening|security\s+checkpoint|"
            r"border|customs|airport|air\s+travel|domestic\s+travel|"
            r"domestic\s+flights?|immigration|licens(?:e|ing)|permits?)\b",
        ),
    )
    return bool(rule_context and government_context)


def _candidate_query_previews(trace: Mapping[str, Any]) -> tuple[str, ...]:
    for key in (
        "active_source_class_recovery_queries",
        "source_class_recovery_queries",
        "candidate_query_previews",
    ):
        if key in trace:
            previews = _compact_strings(trace.get(key), limit=160, max_items=5)
            if previews:
                return previews
    packet = trace.get("source_class_recovery_validation_packet")
    if isinstance(packet, Mapping) and "recovery_query_previews" in packet:
        return _compact_strings(
            packet.get("recovery_query_previews"),
            limit=160,
            max_items=5,
        )
    return ()


def _candidate_query_count(
    trace: Mapping[str, Any],
    query_previews: tuple[str, ...],
) -> int | str:
    for key in (
        "active_source_class_recovery_queries",
        "source_class_recovery_queries",
        "candidate_query_previews",
    ):
        if key in trace:
            count = len(_compact_strings(trace.get(key), limit=160, max_items=100))
            if count:
                return count
    if query_previews:
        return len(query_previews)
    return UNKNOWN


def _candidate_official_source_count(trace: Mapping[str, Any]) -> int | str:
    for key in (
        "candidate_official_source_count",
        "candidate_official_or_canonical_count",
        "official_candidate_source_count",
    ):
        if key in trace:
            return _non_negative_int(trace.get(key))
    return UNKNOWN


def _candidate_official_source_domains(trace: Mapping[str, Any]) -> tuple[str, ...]:
    for key in (
        "candidate_official_source_domain_previews",
        "candidate_official_source_domains",
        "candidate_official_or_canonical_domains",
        "official_candidate_domain_previews",
    ):
        if key in trace:
            return _compact_domains(trace.get(key), max_items=5)
    return ()


def _accepted_or_readable_official_count(trace: Mapping[str, Any]) -> int | str:
    for key in (
        "accepted_or_readable_official_source_count",
        "accepted_official_or_canonical_count",
    ):
        if key in trace:
            return _non_negative_int(trace.get(key))
    if trace.get("active_source_class_recovery_used") is True:
        if "recovered_official_or_primary_count" in trace:
            return _non_negative_int(trace.get("recovered_official_or_primary_count"))
        counts = trace.get("recovered_source_class_counts")
        if isinstance(counts, Mapping):
            count = _class_count(counts)
            if count != UNKNOWN:
                return count
    return UNKNOWN


def _final_count(
    trace: Mapping[str, Any],
    survival: Mapping[str, Any],
    trace_key: str,
    survival_key: str,
) -> int | str:
    if trace_key in trace:
        return _non_negative_int(trace.get(trace_key))
    if survival_key in survival:
        return _non_negative_int(survival.get(survival_key))
    return UNKNOWN


def _query_visibility_status(
    count: int | str,
    previews: tuple[str, ...],
) -> str:
    if count == UNKNOWN:
        return UNKNOWN
    if _positive_known(count) or previews:
        return _VISIBLE
    return _NONE_VISIBLE


def _query_intent_status(
    count: int | str,
    previews: tuple[str, ...],
) -> str:
    if count == UNKNOWN:
        return UNKNOWN
    if any(
        term in " ".join(previews).casefold()
        for term in _OFFICIAL_QUERY_INTENT_TERMS
    ):
        return _VISIBLE
    return _ABSENT


def _count_visibility_status(count: int | str) -> str:
    if count == UNKNOWN:
        return UNKNOWN
    if _positive_known(count):
        return _VISIBLE
    return _NOT_VISIBLE


def _likely_visibility_gap(values: Mapping[str, Any]) -> str:
    status = values.get("obligation_status")
    if status == UNKNOWN:
        return "obligation_visibility_unknown"
    if status == NOT_REQUIRED:
        return "no_official_current_canonical_obligation_visible"
    if values.get("obligation_detected_by_runtime") is False and status == REQUIRED:
        return "obligation_detection_gap"
    if values.get("candidate_query_count") == UNKNOWN:
        return "candidate_query_visibility_unknown"
    if values.get("candidate_query_count") == 0:
        return "no_candidate_query_visible"
    if values.get("candidate_official_source_count") == UNKNOWN:
        return "official_candidate_visibility_unknown"
    if values.get("candidate_official_source_count") == 0:
        return "no_official_candidate_visible"
    if values.get("accepted_or_readable_official_source_count") == UNKNOWN:
        return "accepted_or_readable_visibility_unknown"
    if values.get("accepted_or_readable_official_source_count") == 0:
        return "no_accepted_or_readable_official_source_visible"
    if values.get("final_evidence_official_or_canonical_count") == UNKNOWN:
        return "final_evidence_survival_unknown"
    if values.get("final_evidence_official_or_canonical_count") == 0:
        return "final_evidence_survival_gap"
    if values.get("final_citation_official_or_canonical_count") == UNKNOWN:
        return "final_citation_survival_unknown"
    if values.get("final_citation_official_or_canonical_count") == 0:
        return "final_citation_survival_gap"
    return "no_visibility_gap_visible"


def _survival_projection_payload(trace: Mapping[str, Any]) -> Mapping[str, Any]:
    projection_trace = trace.get(OFFICIAL_SOURCE_SURVIVAL_PROJECTION_TRACE_KEY)
    if not isinstance(projection_trace, Mapping):
        return {}
    projection = projection_trace.get("OfficialSourceSurvivalProjection")
    return projection if isinstance(projection, Mapping) else {}


def _trace_text(trace: Mapping[str, Any]) -> str:
    return " ".join(
        str(part or "")
        for part in (
            trace.get("query_preview"),
            trace.get("query_type"),
            trace.get("report_type"),
            trace.get("intent"),
        )
    ).strip().casefold()


def _unknown_fields(
    facts: OfficialSourceObligationCandidateVisibilityFacts,
) -> list[str]:
    fields = (
        "obligation_status",
        "obligation_source",
        "obligation_detected_by_runtime",
        "candidate_query_count",
        "candidate_query_official_intent_status",
        "candidate_official_source_count",
        "accepted_or_readable_official_source_count",
        "final_evidence_official_or_canonical_count",
        "final_citation_official_or_canonical_count",
    )
    return [field for field in fields if getattr(facts, field) == UNKNOWN]


def _class_count(counts: Mapping[str, Any]) -> int | str:
    values = [
        _non_negative_int(counts.get(key))
        for key in _OFFICIAL_OR_CANONICAL_CLASSES
        if key in counts
    ]
    if not values:
        return UNKNOWN
    return max(values)


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


def _compact_strings(
    value: Any,
    *,
    limit: int,
    max_items: int,
) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for item in _iterable_values(value):
        text = _clean_text(item, limit=limit)
        key = (text or "").casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
        if len(out) >= max_items:
            break
    return tuple(out)


def _compact_domains(value: Any, *, max_items: int) -> tuple[str, ...]:
    domains: list[str] = []
    seen: set[str] = set()
    for item in _iterable_values(value):
        domain = _clean_text(item, limit=120)
        if not domain:
            continue
        domain = domain.casefold()
        domain = domain.removeprefix("https://").removeprefix("http://")
        domain = domain.split("/", 1)[0].rstrip(".")
        if domain.startswith("www."):
            domain = domain[4:]
        if "." not in domain or " " in domain:
            continue
        if domain not in seen:
            seen.add(domain)
            domains.append(domain)
        if len(domains) >= max_items:
            break
    return tuple(domains)


def _iterable_values(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Mapping):
        return tuple(value.values())
    if value is None or isinstance(value, (str, bytes)):
        return ()
    try:
        return tuple(value)
    except TypeError:
        return ()


def _dedupe(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return tuple(out)


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _positive_known(value: int | str | bool) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


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
    "NOT_REQUIRED",
    "OFFICIAL_SOURCE_CANDIDATE_VISIBILITY_TRACE_KEY",
    "OFFICIAL_SOURCE_OBLIGATION_CANDIDATE_SCHEMA_VERSION",
    "OFFICIAL_SOURCE_OBLIGATION_TRACE_KEY",
    "PREFERRED",
    "REQUIRED",
    "OfficialSourceObligationCandidateVisibilityFacts",
    "build_official_source_obligation_candidate_visibility_traces",
]
