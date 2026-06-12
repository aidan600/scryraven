"""AG-50A generic recovery-query acquisition repair.

This module consumes sanitized official/current/canonical obligation facts and
may append a generic source-seeking recovery query to an existing source-class
recovery recommendation. It does not retrieve, route providers, choose depth,
rank/filter sources, classify returned sources, alter prompts, or affect final
answer behavior.
"""

from __future__ import annotations

import re
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
from core.authority_custody_satisfaction import (
    authority_custody_satisfaction_for_source_class,
)
from core.official_source_obligation_candidate_visibility import (
    NOT_REQUIRED,
    PREFERRED,
    REQUIRED,
    UNKNOWN,
    OfficialSourceObligationCandidateVisibilityFacts,
)
from core.source_class_recovery import (
    _infer_official_authority_venue,
    build_official_authority_acquisition_plan,
    build_official_source_recovery_domain_constraints,
)

OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY = (
    "official_canonical_recovery_query_acquisition_trace"
)
OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_SCHEMA_VERSION = (
    "official_canonical_recovery_query_acquisition_ag50a_v1"
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
_OFFICIAL_CURRENT_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
    }
)
_CANONICAL_PRIMARY_CLASSES = frozenset(
    {"primary_source_documents", "archival_primary_text"}
)
_KERNEL_AUTHORITY_CLASS_BY_LEGACY_CLASS = {
    "official_current_rules": OFFICIAL_CURRENT_RULES,
    "legal_or_regulatory_text": LEGAL_OR_REGULATORY_TEXT,
    "current_primary_or_official": OFFICIAL_CURRENT_RULES,
    "primary_source_documents": PRIMARY_SOURCE_DOCUMENTS,
    "archival_primary_text": PRIMARY_SOURCE_DOCUMENTS,
}
_CANONICAL_TECHNICAL_CONTEXT_TERMS = (
    "api",
    "concurrency",
    "database",
    "documentation",
    "framework",
    "library",
    "mode",
    "mvcc",
    "protocol",
    "read write",
    "read/write",
    "reference",
    "software",
    "standard",
    "technical",
    "tradeoff",
    "wal",
    "works",
    "write-ahead",
)
_CANONICAL_TECHNICAL_HARD_TERMS = (
    "api",
    "concurrency",
    "database",
    "documentation",
    "library",
    "mode",
    "mvcc",
    "protocol",
    "read write",
    "read/write",
    "software",
    "standard",
    "wal",
    "write-ahead",
)
_BLOCKERS_THAT_PRESERVE_EXISTING_OWNERSHIP = frozenset(
    {
        "active_recovery_already_used",
        "already_attempted",
        "blocked_by_author_phase",
        "blocked_by_conflict_resolution",
        "blocked_by_corpus_weak",
        "blocked_by_iteration_budget",
        "blocked_by_post_analyst_phase",
        "blocked_by_provider_policy_change_required",
        "blocked_by_redundant_query",
        "blocked_by_retrieve_to_anchor_recommendation",
        "blocked_by_search_depth_escalation_required",
        "blocked_by_terminal_stop",
        "blocked_by_weak_corpus_recovery",
        "budget_hard_exhausted",
        "conflict_resolution_owns_path",
        "existing_active_recovery_blocked_by_budget",
        "fast_mode_policy_block",
        "no_useful_query",
        "no_useful_recovery_query",
        "terminal_stop_approved",
        "weak_corpus_recovery_owns_path",
    }
)
_WEAK_CORPUS_BLOCKERS = frozenset(
    {
        "blocked_by_corpus_weak",
        "blocked_by_weak_corpus_recovery",
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
_DOMAIN_LIKE_RE = re.compile(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+\b", re.IGNORECASE)
_CAP_TEXT = 180
_CAP_QUERY = 180
_MAX_ADDED_QUERIES = 3

_CANONICAL_DOCUMENTATION_QUERY_VARIANTS = (
    (
        "official_documentation",
        "official documentation {subject}",
        (
            "official documentation",
            "official docs",
            "official manual",
            "official reference",
        ),
    ),
    (
        "reference_documentation",
        "reference documentation {subject}",
        (
            "reference documentation",
            "reference docs",
            "reference manual",
            "technical manual",
            "project documentation",
        ),
    ),
)


@dataclass(frozen=True)
class OfficialCanonicalRecoveryQueryAcquisitionResult:
    """Recovery recommendation plus AG-50A acquisition trace."""

    recommendation: dict[str, Any]
    trace: dict[str, Any]


def apply_official_canonical_recovery_query_acquisition(
    *,
    recommendation: Mapping[str, Any] | None,
    runtime_trace: Mapping[str, Any] | None = None,
    obligation_facts: OfficialSourceObligationCandidateVisibilityFacts
    | Mapping[str, Any]
    | None = None,
    existing_blockers: Iterable[Any] = (),
) -> OfficialCanonicalRecoveryQueryAcquisitionResult:
    """Append a generic source-seeking recovery query when safely eligible."""
    base = _safe_mapping(recommendation)
    trace = _safe_mapping(runtime_trace)
    facts = _coerce_facts(obligation_facts, runtime_trace={**trace, **base})

    existing_queries = _string_list(base.get("source_class_recovery_queries"))
    upstream_query_candidates = _dedupe(_string_list(facts.candidate_query_previews))
    visible_queries = _dedupe(
        [
            *existing_queries,
            *_string_list(trace.get("active_source_class_recovery_queries")),
            *_string_list(trace.get("source_class_recovery_queries")),
            *upstream_query_candidates,
        ]
    )
    required_classes = _class_list(facts.required_source_classes)
    allowed_required = [
        item for item in required_classes if item in _ALLOWED_REQUIRED_SOURCE_CLASSES
    ]
    _satisfied, unsatisfied_required = _kernel_satisfaction_for_required_classes(
        allowed_required,
        recommendation=base,
        runtime_trace=trace,
    )
    visible_missing = _class_list(base.get("missing_expected_source_classes"))
    acquisition_classes = [
        item
        for item in unsatisfied_required
        if item in set(visible_missing)
        and _source_class_has_supported_context(item, base=base, trace=trace)
    ]
    considered = facts.obligation_status != UNKNOWN

    subject = _query_subject(base=base, trace=trace)
    context_text = _context_text(base=base, trace=trace)
    official_plan = build_official_authority_acquisition_plan(
        source_classes=acquisition_classes,
        subject=subject,
        context_text=context_text,
        max_query_variants=_MAX_ADDED_QUERIES,
    )
    needed_intents = _needed_intents(
        source_classes=acquisition_classes,
        existing_queries=visible_queries,
        subject=subject,
    )
    promoted_queries = _promotable_upstream_queries(
        upstream_query_candidates,
        source_classes=acquisition_classes,
        subject=subject,
        existing_queries=existing_queries,
    )
    generation_intents = () if promoted_queries else needed_intents
    added_queries = _generic_queries_for_intents(
        generation_intents,
        subject,
        existing_queries=[*visible_queries, *promoted_queries],
        context_text=context_text,
        source_classes=acquisition_classes,
    )
    executable_queries = _dedupe([*promoted_queries, *added_queries])
    source_specific_terms_present = _source_specific_terms_present(executable_queries)
    source_specific_terms_allowed = bool(
        official_plan.get("hard_domains")
        or official_plan.get("soft_candidate_domains")
    )
    source_specific_terms_blocking = (
        source_specific_terms_present and not source_specific_terms_allowed
    )
    blockers = _acquisition_blockers(
        existing_blockers,
        base,
        trace,
        weak_corpus_can_coexist=bool(
            set(acquisition_classes) & _OFFICIAL_CURRENT_CLASSES
        ),
    )
    weak_corpus_coexistence_reason = _weak_corpus_coexistence_reason(
        runtime_trace=trace,
        acquisition_classes=acquisition_classes,
        recovery_queries=executable_queries,
        blockers=blockers,
    )
    eligible = bool(
        considered
        and facts.obligation_status == REQUIRED
        and acquisition_classes
        and (needed_intents or promoted_queries)
        and not blockers
        and not source_specific_terms_blocking
    )
    used = bool(eligible and executable_queries)

    recommendation_out = dict(base)
    if used:
        merged_queries = _dedupe([*existing_queries, *executable_queries])
        recommendation_out.update(
            {
                "source_class_recovery_recommended": True,
                "source_class_recovery_shadow_mode": True,
                "source_class_recovery_queries": merged_queries,
                "source_class_recovery_query_count": len(merged_queries),
                "source_class_recovery_reason": (
                    base.get("source_class_recovery_reason")
                    or "official_canonical_recovery_query_acquisition:"
                    + ",".join(acquisition_classes)
                ),
                "source_class_recovery_trigger_fields": _append_unique(
                    base.get("source_class_recovery_trigger_fields"),
                    _trigger_field_additions(promoted_queries=promoted_queries),
                ),
            }
        )
        official_domains = _official_domain_constraints_for_acquired_queries(
            source_classes=acquisition_classes,
            base=base,
            trace=trace,
            subject=subject,
            recovery_queries=merged_queries,
        )
        if official_domains:
            recommendation_out["source_class_recovery_official_domains"] = (
                official_domains
            )
            recommendation_out["source_class_recovery_domain_constraint_source"] = (
                "official_source_recovery_lane"
            )
    trace_payload = {
        "schema_version": (
            OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_SCHEMA_VERSION
        ),
        "trace_mode": "recovery_query_acquisition_repair",
        "acquisition_repair_considered": considered,
        "acquisition_repair_eligible": eligible,
        "acquisition_repair_used": used,
        "acquisition_repair_skip_reason": _skip_reason(
            facts=facts,
            considered=considered,
            allowed_required=allowed_required,
            unsatisfied_required=unsatisfied_required,
            visible_missing=visible_missing,
            acquisition_classes=acquisition_classes,
            needed_intents=needed_intents,
            promoted_queries=promoted_queries,
            blockers=blockers,
            source_specific_terms_present=source_specific_terms_blocking,
            added_queries=added_queries,
        ),
        "acquisition_repair_blockers": blockers,
        "acquisition_repair_source": facts.obligation_source,
        "required_source_classes": acquisition_classes,
        "existing_recovery_query_count": len(visible_queries),
        "promoted_recovery_query_count": len(promoted_queries) if used else 0,
        "promoted_recovery_query_previews": list(promoted_queries if used else ()),
        "added_recovery_query_count": len(added_queries) if used else 0,
        "added_recovery_query_previews": list(added_queries if used else ()),
        "executable_recovery_query_count": len(executable_queries) if used else 0,
        "generic_query_intent": _generic_query_intent_label(
            _trace_intents(
                needed_intents=needed_intents,
                promoted_queries=promoted_queries,
                used=used,
            )
        ),
        "official_authority_acquisition_plan": official_plan,
        "weak_corpus_coexistence_reason": weak_corpus_coexistence_reason,
        "source_specific_terms_present": source_specific_terms_present,
        "source_specific_terms_allowed_by_official_authority_plan": (
            source_specific_terms_allowed
        ),
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
            "source_class_recovery_recommendation_input",
            "source_class_recovery_lifecycle",
            "local_output_quality_review_packet",
        ],
        "decision_enabled": [
            "required_official_current_canonical_obligation_can_add_generic_query",
            "preferred_and_unknown_obligations_do_not_force_query_acquisition",
            "existing_recovery_queries_are_preserved",
            "existing_blockers_remain_authoritative",
        ],
        "promotion_or_deletion_criteria": {
            "keep_if": "ag50a_validates_query_acquisition_gap",
            "promote_if": "source_class_recovery_natively_generates_obligation_queries",
            "remove_if": "native_recovery_query_generation_covers_required_obligations",
        },
    }
    return OfficialCanonicalRecoveryQueryAcquisitionResult(
        recommendation=recommendation_out,
        trace={
            "schema_version": (
                OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_SCHEMA_VERSION
            ),
            "trace_mode": "recovery_query_acquisition_repair",
            "OfficialCanonicalRecoveryQueryAcquisition": _safe_value(trace_payload),
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
    visible_missing: list[str],
    acquisition_classes: list[str],
    needed_intents: tuple[str, ...],
    promoted_queries: list[str],
    blockers: list[str],
    source_specific_terms_present: bool,
    added_queries: tuple[str, ...],
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
    if not visible_missing or not acquisition_classes:
        return "required_source_class_not_visible_or_supported_for_query"
    if not needed_intents and not promoted_queries:
        return "existing_query_satisfies_intent"
    if source_specific_terms_present:
        return "source_specific_terms_present"
    if not added_queries and not promoted_queries:
        return "no_generic_query_available"
    return None


def _needed_intents(
    *,
    source_classes: list[str],
    existing_queries: list[str],
    subject: str,
) -> tuple[str, ...]:
    intents = _dedupe(
        [
            _intent_for_class(source_class)
            for source_class in source_classes
            if _intent_for_class(source_class)
        ]
    )
    return tuple(
        intent
        for intent in intents
        if not _existing_query_satisfies_intent(
            existing_queries,
            intent,
            subject=subject,
        )
    )


def _promotable_upstream_queries(
    candidates: Iterable[str],
    *,
    source_classes: list[str],
    subject: str,
    existing_queries: Iterable[str],
) -> list[str]:
    existing_keys = {query.casefold() for query in existing_queries}
    promoted: list[str] = []
    intents = tuple(
        intent
        for intent in (
            _intent_for_class(source_class) for source_class in source_classes
        )
        if intent
    )
    for query in candidates:
        clean = _compact_text(query, limit=_CAP_QUERY)
        key = clean.casefold()
        if not clean or key in existing_keys:
            continue
        if _source_specific_terms_present((clean,)):
            continue
        if any(
            _query_satisfies_promotable_intent(clean, intent, subject=subject)
            for intent in intents
        ):
            _append_one(promoted, clean)
        if len(promoted) >= _MAX_ADDED_QUERIES:
            break
    return promoted


def _query_satisfies_promotable_intent(
    query: str,
    intent: str,
    *,
    subject: str,
) -> bool:
    text = query.casefold()
    if intent == "canonical_documentation":
        return any(
            marker in text
            for marker in (
                "documentation",
                "docs",
                "manual",
                "reference",
            )
        )
    if intent == "official_current_source":
        official_marker = any(
            marker in text
            for marker in (
                "agency",
                "current",
                "federal",
                "government",
                "official",
                "source",
            )
        )
        return official_marker and _subject_overlap_present(query, subject)
    return False


def _subject_overlap_present(query: str, subject: str) -> bool:
    subject_tokens = {
        token
        for token in re.findall(r"[a-z0-9]{3,}", subject.casefold())
        if token
        not in {
            "and",
            "for",
            "official",
            "source",
            "the",
            "what",
            "with",
        }
    }
    query_text = query.casefold()
    return not subject_tokens or any(token in query_text for token in subject_tokens)


def _intent_for_class(source_class: str) -> str | None:
    if source_class in _CANONICAL_PRIMARY_CLASSES:
        return "canonical_documentation"
    if source_class in _OFFICIAL_CURRENT_CLASSES:
        return "official_current_source"
    return None


def _source_class_has_supported_context(
    source_class: str,
    *,
    base: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> bool:
    if source_class not in _CANONICAL_PRIMARY_CLASSES:
        return True
    text = _context_text(base=base, trace=trace)
    hits = [term for term in _CANONICAL_TECHNICAL_CONTEXT_TERMS if term in text]
    return len(hits) >= 2 and any(
        term in text for term in _CANONICAL_TECHNICAL_HARD_TERMS
    )


def _weak_corpus_coexistence_reason(
    *,
    runtime_trace: Mapping[str, Any],
    acquisition_classes: Iterable[str],
    recovery_queries: Iterable[str],
    blockers: Iterable[str],
) -> str | None:
    if not (
        runtime_trace.get("corpus_weak") is True
        or runtime_trace.get("weak_corpus_recovery_used") is True
    ):
        return None
    if any(item in _WEAK_CORPUS_BLOCKERS for item in blockers):
        return None
    if not (set(acquisition_classes) & _OFFICIAL_CURRENT_CLASSES):
        return None
    if not recovery_queries:
        return None
    return "unsatisfied_official_current_recovery_lane"


def _context_text(
    *,
    base: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> str:
    parts: list[str] = []
    for source in (trace, base):
        for key in ("query_preview", "query", "core_topic", "primary_entity"):
            text = _compact_text(source.get(key), limit=220)
            if text:
                parts.append(text)
    return " ".join(parts).casefold().replace("-", " ")


def _existing_query_satisfies_intent(
    existing_queries: Iterable[str],
    intent: str,
    *,
    subject: str = "",
) -> bool:
    text = " ".join(existing_queries).casefold()
    if not text:
        return False
    if intent == "canonical_documentation":
        return not _missing_canonical_documentation_variants(existing_queries)
    if intent == "official_current_source":
        return _official_current_specific_query_present(
            existing_queries,
            subject=subject,
        )
    return False


def _generic_queries_for_intents(
    intents: tuple[str, ...],
    subject: str,
    *,
    existing_queries: Iterable[str] = (),
    context_text: str = "",
    source_classes: Iterable[str] = (),
) -> tuple[str, ...]:
    queries: list[str] = []
    for intent in intents:
        if intent == "canonical_documentation":
            for _variant, template, _markers in (
                _missing_canonical_documentation_variants(existing_queries)
            ):
                queries.append(template.format(subject=subject))
                if len(queries) >= _MAX_ADDED_QUERIES:
                    break
        elif intent == "official_current_source":
            queries.extend(
                _official_current_queries(
                    subject,
                    context_text=context_text,
                    source_classes=source_classes,
                )
            )
        if len(queries) >= _MAX_ADDED_QUERIES:
            break
    return tuple(_dedupe(_compact_text(query, limit=_CAP_QUERY) for query in queries))


def _official_domain_constraints_for_acquired_queries(
    *,
    source_classes: Iterable[str],
    base: Mapping[str, Any],
    trace: Mapping[str, Any],
    subject: str,
    recovery_queries: Iterable[str],
) -> list[str]:
    official_classes = [
        source_class
        for source_class in source_classes
        if source_class in _OFFICIAL_CURRENT_CLASSES
    ]
    if not official_classes:
        return []
    return build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=official_classes,
        query=_context_value("query_preview", base=base, trace=trace) or subject,
        core_topic=_context_value("core_topic", base=base, trace=trace),
        primary_entity=_context_value("primary_entity", base=base, trace=trace),
        recovery_queries=recovery_queries,
    )


def _year_terms(text: str) -> str:
    years = re.findall(r"\b20\d{2}\b", text)
    return " ".join(dict.fromkeys(years))


def _official_current_queries(
    subject: str,
    *,
    context_text: str = "",
    source_classes: Iterable[str] = (),
) -> list[str]:
    """Return deterministic official/current query variants for numeric rules."""
    text = subject.casefold()
    year_text = _year_terms(subject)
    plan = build_official_authority_acquisition_plan(
        source_classes=source_classes or ("official_current_rules",),
        subject=subject,
        context_text=context_text,
        max_query_variants=_MAX_ADDED_QUERIES,
    )
    role_only_hints = _official_current_role_only_venue_hints(
        subject,
        context_text,
    )
    queries: list[str] = []

    def add(query: str) -> None:
        if query not in queries and len(queries) < _MAX_ADDED_QUERIES:
            queries.append(query)

    if (
        plan.get("venue_families")
        or plan.get("hard_domains")
        or plan.get("soft_candidate_domains")
    ):
        for query in plan.get("query_variants", ()):
            add(query)
    if role_only_hints:
        add(" ".join(("official current source", *role_only_hints, subject)))
    if "irs" in text or "internal revenue service" in text:
        if "mileage" in text or "standard mileage" in text:
            add(
                " ".join(
                    part
                    for part in (
                        "IRS",
                        year_text,
                        "standard mileage rate business official notice revenue procedure",
                    )
                    if part
                )
            )
        else:
            add(
                " ".join(
                    part
                    for part in (
                        "IRS",
                        year_text,
                        "official current tax threshold eligibility rule notice",
                    )
                    if part
                )
            )
    if (
        "ssa" in text
        or "social security" in text
        or "taxable maximum" in text
        or "wage base" in text
    ):
        add(
            " ".join(
                part
                for part in (
                    "SSA",
                    year_text,
                    "Social Security taxable maximum wage base official contribution benefit base",
                )
                if part
            )
        )
    if "uscis" in text or "n-400" in text or "naturalization" in text:
        add("USCIS Form N-400 online filing fee official current fee schedule")
    if "federal minimum wage" in text or "minimum wage" in text:
        add("Department of Labor current federal minimum wage official")
    if not queries and any(
        term in text
        for term in (
            "eligibility",
            "fee",
            "rate",
            "status",
            "threshold",
            "wage base",
        )
    ):
        add(f"federal agency official current eligibility threshold status rule {subject}")
    add(f"official current source {subject}")
    return queries


def _official_current_role_only_venue_hints(*texts: str) -> tuple[str, ...]:
    inferred = _infer_official_authority_venue(*texts)
    text = " ".join(str(value or "") for value in texts).casefold()
    hints: list[str] = []
    priority = (
        "airport screening",
        "accepted-ID guidance",
        "enforcement-date notice",
        "official agency",
        "official program guidance",
        "agency FAQ",
        "eligibility requirements",
        "application instructions",
        "access rules",
        "checkpoint requirements",
        "regulatory text",
    )
    available: list[str] = []
    for candidate in inferred.candidates:
        if candidate.constraint_strength != "role_only":
            continue
        if candidate.family_id == "government_program_eligibility_access_rule":
            if not _has_access_identity_terms(text):
                continue
        elif candidate.family_id != "airport_screening_identity_access_rule":
            continue
        available.extend(candidate.search_hints)
    for value in priority:
        if value in available:
            _append_one(hints, value)
    for value in available:
        _append_one(hints, value)
    return tuple(hints[:4])


def _has_access_identity_terms(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:credentials?|identification|identity|id\s+documents?|"
            r"documents?|proof|access|entry|screening|checkpoint)\b",
            text,
        )
    )


def _official_current_specific_query_present(
    existing_queries: Iterable[str],
    *,
    subject: str,
) -> bool:
    text = " ".join(existing_queries).casefold()
    subject_text = subject.casefold()
    if "irs" in subject_text or "internal revenue service" in subject_text:
        if "mileage" in subject_text or "standard mileage" in subject_text:
            return (
                "irs" in text
                and "standard mileage rate" in text
                and (
                    "revenue procedure" in text
                    or "official notice" in text
                    or "notice revenue procedure" in text
                )
            )
    if (
        "ssa" in subject_text
        or "social security" in subject_text
        or "taxable maximum" in subject_text
        or "wage base" in subject_text
    ):
        return (
            "ssa" in text
            and (
                "contribution benefit base" in text
                or "contribution and benefit base" in text
            )
        )
    if "uscis" in subject_text or "n-400" in subject_text or "naturalization" in subject_text:
        return "uscis" in text and "n-400" in text and "fee" in text
    if "federal minimum wage" in subject_text or "minimum wage" in subject_text:
        return (
            "department of labor" in text
            and "federal minimum wage" in text
            and "official" in text
        )
    if any(
        term in subject_text
        for term in (
            "eligibility",
            "fee",
            "rate",
            "status",
            "threshold",
            "wage base",
        )
    ):
        return "federal agency official current eligibility threshold status rule" in text
    return any(
        marker in text
        for marker in (
            "official agency source",
            "official current source",
            "official fact sheet",
            "government agency source",
            "primary source",
        )
    )


def _missing_canonical_documentation_variants(
    existing_queries: Iterable[str],
) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    text = " ".join(existing_queries).casefold()
    if not text:
        return _CANONICAL_DOCUMENTATION_QUERY_VARIANTS[:2]
    return tuple(
        variant
        for variant in _CANONICAL_DOCUMENTATION_QUERY_VARIANTS
        if not any(marker in text for marker in variant[2])
    )


def _generic_query_intent_label(intents: Iterable[str]) -> str:
    values = [intent for intent in intents if intent]
    if not values:
        return "none"
    return ",".join(values)


def _trace_intents(
    *,
    needed_intents: tuple[str, ...],
    promoted_queries: list[str],
    used: bool,
) -> tuple[str, ...]:
    if not used:
        return ()
    if promoted_queries:
        return (*needed_intents, "upstream_candidate")
    return needed_intents


def _trigger_field_additions(*, promoted_queries: list[str]) -> tuple[str, ...]:
    fields = [
        "official_source_obligation_bridge",
        "official_canonical_recovery_query_acquisition",
    ]
    if promoted_queries:
        fields.append("upstream_recovery_query_candidate")
    return tuple(fields)


def _query_subject(
    *,
    base: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> str:
    for source in (trace, base):
        combined = _combined_entity_topic_subject(source)
        if combined:
            return combined
    for source in (trace, base):
        for key in ("core_topic", "primary_entity", "query_preview", "query"):
            subject = _compact_text(source.get(key), limit=110)
            if subject:
                return subject
    return "source topic"


def _context_value(
    key: str,
    *,
    base: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> str:
    for source in (trace, base):
        text = _compact_text(source.get(key), limit=160)
        if text:
            return text
    return ""


def _combined_entity_topic_subject(source: Mapping[str, Any]) -> str:
    primary_entity = _compact_text(source.get("primary_entity"), limit=80)
    core_topic = _compact_text(source.get("core_topic"), limit=110)
    if primary_entity and core_topic:
        primary_key = primary_entity.casefold()
        topic_key = core_topic.casefold()
        if primary_key in topic_key:
            return core_topic
        if topic_key in primary_key:
            return primary_entity
        return _compact_text(f"{primary_entity} {core_topic}", limit=110)
    return ""


def _source_specific_terms_present(queries: Iterable[str]) -> bool:
    return any(_DOMAIN_LIKE_RE.search(str(query or "")) for query in queries)


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
                recommendation=recommendation,
                runtime_trace=runtime_trace,
                legacy_status=status_by_class.get(source_class),
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
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
    legacy_status: str | None,
) -> tuple[AuthorityEvidenceFit, ...]:
    custody = authority_custody_satisfaction_for_source_class(
        source_class,
        runtime_trace,
        recommendation,
        authority_class=authority_class,
    )
    if custody.authority_satisfied:
        return (
            AuthorityEvidenceFit.authoritative(
                requirement.requirement_id,
                custody.evidence_id or f"{source_class}:{custody.reason}",
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


def _acquisition_blockers(
    explicit_blockers: Iterable[Any],
    recommendation: Mapping[str, Any],
    runtime_trace: Mapping[str, Any],
    *,
    weak_corpus_can_coexist: bool = False,
) -> list[str]:
    blockers: list[str] = []
    authority_lifecycle_preserves_recovery = bool(
        runtime_trace.get("authority_lifecycle_required_recovery_allowed")
    )
    for source in (
        explicit_blockers,
        recommendation.get("active_source_class_recovery_blockers"),
        recommendation.get("source_class_recovery_candidate_v2_blockers"),
        runtime_trace.get("active_source_class_recovery_blockers"),
        runtime_trace.get("source_class_recovery_candidate_v2_blockers"),
    ):
        for item in _string_list(source):
            if (
                item in {
                    "blocked_by_corpus_weak",
                    "blocked_by_weak_corpus_recovery",
                    "weak_corpus_recovery_owns_path",
                }
                and (
                    authority_lifecycle_preserves_recovery
                    or weak_corpus_can_coexist
                )
            ):
                continue
            if item in _BLOCKERS_THAT_PRESERVE_EXISTING_OWNERSHIP:
                _append_one(blockers, item)
    if runtime_trace.get("query_redundancy_skipped") is True:
        _append_one(blockers, "blocked_by_redundant_query")
    if runtime_trace.get("next_query_redundant") is True:
        _append_one(blockers, "blocked_by_redundant_query")
    if (
        runtime_trace.get("weak_corpus_recovery_used") is True
        and not authority_lifecycle_preserves_recovery
        and not weak_corpus_can_coexist
    ):
        _append_one(blockers, "weak_corpus_recovery_owns_path")
    if (
        runtime_trace.get("corpus_weak") is True
        and not authority_lifecycle_preserves_recovery
        and not weak_corpus_can_coexist
    ):
        _append_one(blockers, "blocked_by_corpus_weak")
    if runtime_trace.get("active_source_class_recovery_used") is True:
        _append_one(blockers, "active_recovery_already_used")
    if _positive_int(runtime_trace.get("active_source_class_recovery_attempt_count")):
        _append_one(blockers, "already_attempted")
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
        text = _clean_text(item, limit=_CAP_QUERY)
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


def _dedupe(values: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = _compact_text(value, limit=_CAP_QUERY)
        key = clean.casefold()
        if clean and key not in seen:
            out.append(clean)
            seen.add(key)
    return out


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


def _compact_text(value: Any, *, limit: int = _CAP_TEXT) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return text[:limit]


def _clean_text(value: Any, *, limit: int) -> str | None:
    text = _compact_text(value, limit=limit)
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PROTECTED_MARKERS):
        return "[redacted protected material]"
    return text


def _clean_token(value: Any) -> str | None:
    text = _clean_text(value, limit=100)
    if not text:
        return None
    return text.casefold().replace("-", "_").replace(" ", "_")


def _positive_int(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return int(value or 0) > 0
    except (TypeError, ValueError):
        return False


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


__all__ = [
    "OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_SCHEMA_VERSION",
    "OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY",
    "OfficialCanonicalRecoveryQueryAcquisitionResult",
    "apply_official_canonical_recovery_query_acquisition",
]
