"""Pure diagnostics for source-class recovery recommendations.

This module does not call retrieval, providers, ranking, prompts, models, or
pipeline orchestration. It only describes whether a first-pass corpus appears
to be missing an expected source class and suggests generic follow-up queries.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse

from core.authoritative_source_obligations import (
    ACADEMIC_LITERATURE,
    LEGAL_OR_REGULATORY_TEXT,
    OFFICIAL_CURRENT_RULES,
    PRIMARY_SOURCE_DOCUMENTS,
    REPUTABLE_SECONDARY,
    SOURCED_NUMERIC_VALUES,
    AuthoritativeSourceObligationState,
    AuthorityEvidenceFit,
    AuthorityRequirement,
    AuthorityStatus,
)
from core.canonical_technical_docs_policy import (
    is_canonical_technical_documentation_context,
)

SOURCE_CLASS_BUCKETS = (
    "official_current_rules",
    "issuer_filings_or_company_materials",
    "polling_data_or_aggregator",
    "primary_source_documents",
    "none",
)

SOURCE_CLASS_OBSERVABILITY_BUCKETS = (
    "official_current_rules",
    "legal_or_regulatory_text",
    "parliamentary_or_legislative_material",
    "primary_source_documents",
    "archival_primary_text",
    "historical_legal_text",
    "issuer_filings_or_company_materials",
    "polling_data_or_aggregator",
    "none",
)

SOURCE_CLASS_SATISFACTION_STATUSES = (
    "satisfied_strong",
    "satisfied_weak",
    "expected_but_only_secondary",
    "unsatisfied",
)

SOURCE_CLASS_RECOVERY_CANDIDATE_V2_SCHEMA_VERSION = (
    "source_class_recovery_candidate_v2"
)

SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS = (
    "expected_source_class_unsatisfied",
    "expected_source_class_secondary_only",
    "expected_source_class_weakly_satisfied",
    "final_answer_lacks_official_source",
    "final_answer_lacks_primary_source",
    "final_answer_lacks_archival_source",
    "final_answer_lacks_legal_or_regulatory_source",
    "answer_class_partial_or_no_evidence",
    "corpus_off_topic_with_expected_source_class",
    "at_cap_with_source_class_underfire",
    "budget_exhausted_with_source_class_underfire",
)

SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS = (
    "all_expected_source_classes_satisfied_strong",
    "no_expected_source_class",
    "weak_corpus_recovery_owns_path",
    "active_recovery_already_used",
    "no_recovery_query_available",
    "budget_hard_exhausted",
    "fast_mode_policy_block",
    "existing_active_recovery_blocked_by_budget",
    "unsupported_off_domain_retrieval",
)

SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BUDGET_CONTEXTS = (
    "exhausted",
    "at_cap",
    "near_cap",
    "room_remaining",
    "unknown",
)

RECOVERY_SOURCE_QUALITY_STATUSES = (
    "official_or_primary_found",
    "secondary_only",
    "no_relevant_sources",
    "classification_mismatch",
    "promoted_but_not_final",
    "unknown",
)

_CAP_TEXT = 160
_CAP_QUERY = 180
_MAX_RECOVERY_QUERIES = 2
_MAX_SHADOW_CLASS_INTENT_QUERIES = 2
_MAX_EVIDENCE_CLASS_TEXT = 2000
ANSWER_CONTRACT_SOURCE_CLASS_RECOVERY_CLASSES = (
    "legal_or_regulatory_text",
    "official_current_rules",
    "current_primary_or_official",
)
ANSWER_CONTRACT_SOURCE_CLASS_RECOVERY_REASON_BY_CLASS = {
    "official_current_rules": "answer_contract_official_gap",
    "legal_or_regulatory_text": "answer_contract_legal_text_gap",
    "current_primary_or_official": "answer_contract_current_primary_gap",
}
OFFICIAL_SOURCE_DOMAIN_CONSTRAINT_CLASSES = frozenset(
    {
        "official_current_rules",
        "legal_or_regulatory_text",
        "current_primary_or_official",
    }
)
OFFICIAL_SOURCE_US_AUTHORITY_DOMAINS = (
    "federalregister.gov",
    "ecfr.gov",
    "govinfo.gov",
    "regulations.gov",
)
OFFICIAL_SOURCE_EU_AUTHORITY_DOMAINS = (
    "eur-lex.europa.eu",
)
OFFICIAL_SOURCE_UK_AUTHORITY_DOMAINS = (
    "legislation.gov.uk",
)
_ANSWER_CONTRACT_OFFICIAL_OR_LEGAL_FAMILIES = {
    "current_official_rules",
    "legal_or_regulatory_primary_text",
}
_ANSWER_CONTRACT_CURRENT_PRIMARY_FAMILIES = {
    "current_official_rules",
    "legal_or_regulatory_primary_text",
    "developing_event_orientation",
}
_KERNEL_SOURCE_CLASS_MAP = {
    "official_current_rules": OFFICIAL_CURRENT_RULES,
    "primary_source_documents": PRIMARY_SOURCE_DOCUMENTS,
    "archival_primary_text": PRIMARY_SOURCE_DOCUMENTS,
    "legal_or_regulatory_text": LEGAL_OR_REGULATORY_TEXT,
    "historical_legal_text": LEGAL_OR_REGULATORY_TEXT,
    "current_primary_or_official": OFFICIAL_CURRENT_RULES,
    "academic_literature": ACADEMIC_LITERATURE,
    "sourced_numeric_values": SOURCED_NUMERIC_VALUES,
}


def _compact_text(value: Any, *, limit: int = _CAP_TEXT) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return text[:limit]


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _anchor_payload(anchor_packet: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(anchor_packet, dict):
        return {}
    nested = anchor_packet.get("anchor_packet")
    if isinstance(nested, dict):
        return nested
    return anchor_packet


def _anchor_text(anchor_packet: dict[str, Any] | None) -> str:
    packet = _anchor_payload(anchor_packet)
    if not packet:
        return ""
    hints = packet.get("decomposition_hints")
    if isinstance(hints, (list, tuple)):
        hint_text = " ".join(_compact_text(item, limit=60) for item in hints)
    else:
        hint_text = _compact_text(hints, limit=120)
    return " ".join(
        part
        for part in (
            _compact_text(packet.get("source_class_expectation"), limit=80),
            _compact_text(packet.get("claim_or_metric_type"), limit=80),
            _compact_text(packet.get("freshness_requirement"), limit=80),
            _compact_text(packet.get("answerability_forecast"), limit=80),
            hint_text,
        )
        if part
    )


def _combined_text(
    *,
    query: str,
    intent: str,
    report_type: str,
    query_type: str,
    core_topic: str,
    primary_entity: str,
    anchor_packet: dict[str, Any] | None,
) -> str:
    return " ".join(
        part
        for part in (
            query,
            intent,
            report_type,
            query_type,
            core_topic,
            primary_entity,
            _anchor_text(anchor_packet),
        )
        if str(part or "").strip()
    ).casefold()


def _negative_primary_context(text: str) -> bool:
    return _has_any(
        text,
        (
            r"\bprimary\s+(?:election|system|school|care|color|colour|reason)\b",
            r"\btop[-\s]+two\s+primary\b",
        ),
    )


def _historical_or_conceptual_rule_context(text: str) -> bool:
    return _has_any(
        text,
        (
            r"\b(?:historical|history|background|conceptual|concept|explain\s+the\s+concept)\b",
            r"\brather\s+than\s+(?:summariz(?:e|ing)|identify(?:ing)?|find(?:ing)?)\s+"
            r"(?:the\s+)?current\b",
            r"\bnot\s+(?:the\s+)?current\s+(?:rule|rules|requirement|requirements)\b",
        ),
    )


def _anchor_source_class(anchor_packet: dict[str, Any] | None) -> str:
    return _compact_text(_anchor_payload(anchor_packet).get("source_class_expectation"), limit=80).casefold()


def _anchor_claim_type(anchor_packet: dict[str, Any] | None) -> str:
    return _compact_text(_anchor_payload(anchor_packet).get("claim_or_metric_type"), limit=80).casefold()


def _expected_source_classes(
    *,
    text: str,
    anchor_packet: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    expected: list[str] = []
    trigger_fields: list[str] = []

    def add(bucket: str, field: str) -> None:
        if bucket not in expected:
            expected.append(bucket)
        if field not in trigger_fields:
            trigger_fields.append(field)

    source_class = _anchor_source_class(anchor_packet)
    claim_type = _anchor_claim_type(anchor_packet)
    historical_rule_context = _historical_or_conceptual_rule_context(text)

    primary_source_request = _has_any(
        text,
        (
            r"\bprimary[-\s]+(?:sources?|documents?|evidence|records?|materials?)\b",
            r"\bprimary[-\s]+source[-\s]+documents?\b",
        ),
    )
    if primary_source_request and not _negative_primary_context(text):
        add("primary_source_documents", "query")
    elif source_class == "primary" and not _negative_primary_context(text):
        add("primary_source_documents", "anchor_packet")
    elif is_canonical_technical_documentation_context(
        text,
        required_source_classes=("primary_source_documents",),
    ):
        add("primary_source_documents", "canonical_technical_docs_policy")

    official_current_request = _has_any(
        text,
        (
            r"\bcurrent\s+(?:official\s+)?(?:eligibility\s+)?(?:rules?|requirements?)\b",
            r"\b(?:eligibility|regulatory|compliance)\s+requirements?\b",
            r"\bofficial\s+(?:current\s+)?(?:rules?|requirements?)\b",
            r"\bgovernment\s+(?:program\s+)?(?:rules?|requirements?)\b",
            r"\bcurrent\s+(?:program|government|regulatory|compliance)\s+(?:rules?|requirements?)\b",
        ),
    )
    official_current_numeric_rule_request = _has_any(
        text,
        (
            r"\b(?:current|latest|2024|2025|2026|2027)\b",
        ),
    ) and _has_any(
        text,
        (
            r"\b(?:irs|ssa|social\s+security|dol|department\s+of\s+labor|uscis|federal)\b",
            r"\b(?:official|agency|government|source)\b",
        ),
    ) and _has_any(
        text,
        (
            r"\b(?:standard\s+mileage\s+rate|mileage\s+rate|taxable\s+maximum|wage\s+base)\b",
            r"\b(?:federal\s+minimum\s+wage|n-400|naturalization|filing\s+fee)\b",
            r"\b(?:rate|rates|fee|fees|threshold|limit|maximum|eligibility|status)\b",
        ),
    )
    if (
        official_current_request or official_current_numeric_rule_request
    ) and not historical_rule_context:
        add("official_current_rules", "query")
    elif source_class == "official" and claim_type == "rule" and not historical_rule_context:
        add("official_current_rules", "anchor_packet")

    issuer_request = _has_any(
        text,
        (
            r"\b(?:company|corporate|issuer|reported\s+company)[-\s]+"
            r"(?:filings?|materials?|reports?|records?|metrics?)\b",
            r"\b(?:company|issuer)[-\s]+reported[-\s]+(?:metric|metrics|results?|figures?)\b",
            r"\b(?:earnings\s+release|quarterly\s+results?|quarterly\s+reports?)\b",
            r"\b(?:10[-\s]?q|10[-\s]?k|form\s+10[-\s]?[qk]|sec\s+filings?)\b",
            r"\binvestor\s+relations?\b",
        ),
    )
    if issuer_request:
        add("issuer_filings_or_company_materials", "query")

    polling_request = _has_any(
        text,
        (
            r"\bpolling?\s+averages?\b",
            r"\blatest\s+polls?\b",
            r"\bpolling\s+toplines?\b",
            r"\bcrosstabs?\b",
            r"\bbroader\s+polling\s+averages?\b",
            r"\bcandidate\s+polling\s+hierarchy\b",
            r"\bpolling?\s+(?:data|survey|surveys|aggregator)\b",
        ),
    )
    if polling_request:
        add("polling_data_or_aggregator", "query")

    if not expected:
        expected.append("none")

    return expected, trigger_fields


def _positive_count(counts: dict[str, int], key: str) -> bool:
    return int(counts.get(key, 0) or 0) > 0


def _domain_entries(
    source_domain_counts: dict[str, int],
    top_source_domains: list[dict[str, Any]],
) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    for domain in source_domain_counts:
        clean = _compact_text(domain, limit=120).casefold()
        if clean and clean not in seen:
            domains.append(clean)
            seen.add(clean)
    for row in top_source_domains or []:
        if not isinstance(row, dict):
            continue
        clean = _compact_text(row.get("domain"), limit=120).casefold()
        if clean and clean not in seen:
            domains.append(clean)
            seen.add(clean)
    return domains


def _domain_has_any(domains: list[str], patterns: tuple[str, ...]) -> bool:
    return any(_has_any(domain, patterns) for domain in domains)


def _official_domain_signal(domains: list[str]) -> bool:
    return _domain_has_any(
        domains,
        (
            r"(^|\.)gov(?:\.|$)",
            r"(^|\.)mil(?:\.|$)",
            r"(^|\.)edu(?:\.|$)",
            r"(^|\.)int(?:\.|$)",
            r"\b(?:official|regulator|government|agency)\b",
        ),
    )


def _polling_domain_signal(domains: list[str]) -> bool:
    return _domain_has_any(
        domains,
        (
            r"\b(?:poll|polling|survey|surveys|crosstab|topline|aggregator)s?\b",
            r"\b(?:election|campaign)\s*(?:data|polls?|survey)\b",
        ),
    )


def _issuer_materials_domain_signal(domains: list[str]) -> bool:
    return _domain_has_any(
        domains,
        (
            r"(^|[.\-])(?:ir|investor|investors)([.\-]|$)",
            r"\b(?:filings?|earnings|quarterly|annualreports?|sec)\b",
        ),
    )


def _primary_document_domain_signal(domains: list[str]) -> bool:
    return _domain_has_any(
        domains,
        (
            r"\b(?:archive|archives|records?|documents?|repository|library)\b",
        ),
    )


def _source_domain_from_url(url: Any) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").casefold().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _source_path_from_url(url: Any) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    return (parsed.path or "").casefold()


def _evidence_classification_text(source: Mapping[str, Any]) -> str:
    return " ".join(
        _compact_text(source.get(field), limit=_MAX_EVIDENCE_CLASS_TEXT)
        for field in ("url", "title", "text", "snippet")
        if str(source.get(field) or "").strip()
    ).casefold()


def _declared_source_classes(source: Mapping[str, Any]) -> tuple[str, ...]:
    raw_values: list[Any] = [
        source.get("source_class"),
        source.get("source_class_bucket"),
    ]
    classes = source.get("source_classes")
    if isinstance(classes, (list, tuple, set)):
        raw_values.extend(classes)
    else:
        raw_values.append(classes)
    allowed = set(SOURCE_CLASS_OBSERVABILITY_BUCKETS) - {"none"}
    out: list[str] = []
    for value in raw_values:
        cleaned = _compact_text(value, limit=80).casefold().replace("-", "_").replace(" ", "_")
        if cleaned in allowed:
            _append_unique(out, cleaned)
    return tuple(out)


def _canonical_documentation_signal(
    *,
    source: Mapping[str, Any],
    text: str,
    domain: str,
    tier: str,
    secondary_signal: bool,
) -> bool:
    if secondary_signal:
        return False
    combined = f"{text} {_source_path_from_url(source.get('url'))} {domain}"
    if _has_any(
        combined,
        (
            r"\b(?:mirror|unofficial|copy\s+of|scraped|rehosted)\b",
        ),
    ):
        return False
    documentation_signal = _has_any(
        combined,
        (
            r"\b(?:documentation|docs|manual|reference)\b",
            r"/docs(?:/|$)",
            r"(^|\.)docs\.",
        ),
    )
    technical_signal = _has_any(
        combined,
        (
            r"\b(?:api|database|framework|library|protocol|software|"
            r"concurrency|configuration|reference|manual)\b",
        ),
    )
    canonical_tier = tier in {"canonical", "primary"}
    canonical_text = _has_any(
        combined,
        (
            r"\b(?:canonical|official|primary)\s+"
            r"(?:documentation|docs|manual|reference)\b",
            r"\b(?:documentation|docs|manual|reference)\s+"
            r"(?:canonical|official|primary)\b",
        ),
    )
    docs_surface = bool(
        domain
        and documentation_signal
        and (
            _source_path_from_url(source.get("url")).startswith("/docs")
            or ".docs." in f".{domain}."
            or domain.startswith("docs.")
        )
    )
    return bool(documentation_signal and technical_signal and (canonical_tier or canonical_text or docs_surface))


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _authority_requirement_for_source_class(
    source_class: str,
) -> AuthorityRequirement | None:
    requirement_id = _compact_text(source_class, limit=80).casefold()
    if requirement_id == "official_current_rules":
        return AuthorityRequirement.official_current(requirement_id)
    if requirement_id in {"primary_source_documents", "archival_primary_text"}:
        return AuthorityRequirement.canonical_project_doc(requirement_id)
    if requirement_id in {
        "legal_or_regulatory_text",
        "historical_legal_text",
        "current_primary_or_official",
    }:
        return AuthorityRequirement.legal_current_primary(requirement_id)
    if requirement_id == "academic_literature":
        return AuthorityRequirement.academic_literature(requirement_id)
    if requirement_id == "sourced_numeric_values":
        return AuthorityRequirement.source_bound_numeric(requirement_id)
    return None


def _authority_evidence_fits_for_source_class(
    source_class: str,
    *,
    strong_count: int,
    weak_count: int,
    secondary_only_count: int,
) -> tuple[AuthorityEvidenceFit, ...]:
    source_class_key = _compact_text(source_class, limit=80).casefold()
    requirement = _authority_requirement_for_source_class(source_class_key)
    authority_class = _KERNEL_SOURCE_CLASS_MAP.get(source_class_key)
    if requirement is None or authority_class is None:
        return ()
    fits: list[AuthorityEvidenceFit] = []
    for index in range(max(0, int(strong_count or 0))):
        fits.append(
            AuthorityEvidenceFit.authoritative(
                requirement.requirement_id,
                f"{source_class}:strong:{index}",
                authority_class,
            )
        )
    for index in range(max(0, int(weak_count or 0))):
        fits.append(
            AuthorityEvidenceFit(
                requirement_id=requirement.requirement_id,
                evidence_id=f"{source_class}:weak:{index}",
                candidate_exists=True,
                observed_source_class=authority_class,
                context_allowed=True,
                satisfies_authority=False,
                mismatch_reason="expected_source_class_weakly_satisfied",
            )
        )
    for index in range(max(0, int(secondary_only_count or 0))):
        fits.append(
            AuthorityEvidenceFit.lower_tier_context(
                requirement.requirement_id,
                f"{source_class}:secondary_only:{index}",
                REPUTABLE_SECONDARY,
                mismatch_reason="expected_source_class_secondary_only",
            )
        )
    return tuple(fits)


def _evaluate_source_class_satisfaction_with_authority_kernel(
    expected_source_classes: Iterable[str],
    *,
    strong_counts: Mapping[str, int],
    weak_counts: Mapping[str, int],
    secondary_only_counts: Mapping[str, int],
) -> tuple[dict[str, str], list[str]]:
    satisfaction_status: dict[str, str] = {}
    gap_candidates: list[str] = []
    for bucket in expected_source_classes:
        bucket_key = _compact_text(bucket, limit=80).casefold()
        requirement = _authority_requirement_for_source_class(bucket_key)
        if requirement is not None:
            state = AuthoritativeSourceObligationState.evaluate(
                [requirement],
                _authority_evidence_fits_for_source_class(
                    bucket,
                    strong_count=int(strong_counts.get(bucket, 0) or 0),
                    weak_count=int(weak_counts.get(bucket, 0) or 0),
                    secondary_only_count=int(secondary_only_counts.get(bucket, 0) or 0),
                ),
            )
            satisfaction = state.satisfaction_for(requirement.requirement_id)
            if satisfaction.status is AuthorityStatus.FULFILLED:
                status = "satisfied_strong"
            elif int(secondary_only_counts.get(bucket, 0) or 0) > 0:
                status = "expected_but_only_secondary"
            elif int(weak_counts.get(bucket, 0) or 0) > 0:
                status = "satisfied_weak"
            else:
                status = "unsatisfied"
        elif int(strong_counts.get(bucket, 0) or 0) > 0:
            status = "satisfied_strong"
        elif int(secondary_only_counts.get(bucket, 0) or 0) > 0:
            status = "expected_but_only_secondary"
        elif int(weak_counts.get(bucket, 0) or 0) > 0:
            status = "satisfied_weak"
        else:
            status = "unsatisfied"
        satisfaction_status[bucket] = status
        if status != "satisfied_strong":
            gap_candidates.append(bucket)
    return satisfaction_status, gap_candidates


def _public_program_official_current_request(text: str) -> bool:
    public_program_context = _has_any(
        text,
        (
            r"\b(?:government|public)\s+"
            r"(?:benefits?|assistance|aid|programs?|subsid(?:y|ies)|"
            r"services?|support|agency|authority)\b",
            r"\b(?:state|county|federal|municipal|local|provincial)\s+"
            r"[a-z0-9'.\-\s]{0,60}"
            r"(?:benefits?|assistance|aid|programs?|subsid(?:y|ies)|"
            r"services?|support|courts?|agenc(?:y|ies)|authorit(?:y|ies))\b",
            r"\b(?:benefits?|assistance|aid|subsid(?:y|ies))\s+programs?\b",
            r"\b(?:public\s+authority|government\s+authority|state\s+agency|"
            r"county\s+agency|federal\s+agency|municipal\s+agency)\b",
        ),
    )
    if not public_program_context:
        return False

    official_context = _has_any(
        text,
        (
            r"\bofficial\b",
            r"\b(?:agency|government|public\s+authority|state\s+agency|"
            r"county\s+agency|federal\s+agency|municipal\s+agency)\s+guidance\b",
        ),
    )
    if not official_context:
        return False

    current_or_guidance_context = _has_any(
        text,
        (
            r"\bcurrent\b",
            r"\b(?:agency|official|government|public\s+authority)\s+guidance\b",
            r"\bguidance\s+(?:controls?|governs?|sets?|explains?)\b",
        ),
    )
    if not current_or_guidance_context:
        return False

    eligibility_context = _has_any(
        text,
        (
            r"\b(?:eligible|eligibility|qualif(?:y|ies|ication|ications))\b",
            r"\bwho\s+(?:is\s+)?(?:eligible|qualifies?)\b",
        ),
    )
    application_context = _has_any(
        text,
        (
            r"\bapplications?\s+(?:rules?|process|work|requirements?)\b",
            r"\bhow\s+(?:to\s+apply|applications?\s+work)\b",
            r"\bapply\s+(?:for|under)\b",
        ),
    )
    guidance_controls_rule_context = _has_any(
        text,
        (
            r"\bguidance\s+(?:controls?|governs?|sets?|explains?)\s+"
            r"[a-z0-9'.\-\s]{0,50}"
            r"(?:eligibility|applications?|rules?|requirements?)\b",
        ),
    )

    return bool(
        (eligibility_context and application_context)
        or (guidance_controls_rule_context and eligibility_context)
        or (
            current_or_guidance_context
            and (eligibility_context or application_context)
            and _has_any(text, (r"\b(?:rules?|requirements?|guidance)\b",))
        )
    )


def _observability_expected_source_classes(
    *,
    text: str,
    anchor_packet: dict[str, Any] | None,
) -> list[str]:
    active_expected, _trigger_fields = _expected_source_classes(
        text=text,
        anchor_packet=anchor_packet,
    )
    expected: list[str] = []
    for bucket in active_expected:
        if bucket != "none":
            _append_unique(expected, bucket)

    source_class = _anchor_source_class(anchor_packet)
    claim_type = _anchor_claim_type(anchor_packet)
    historical_rule_context = _historical_or_conceptual_rule_context(text)

    legal_or_regulatory_request = _has_any(
        text,
        (
            r"\b(?:legal|regulatory|statutory)\s+"
            r"(?:texts?|sources?|materials?|requirements?|obligations?|rules?)\b",
            r"\b(?:requirements?|obligations?|provisions?|rules?)\s+under\s+"
            r"(?:the\s+)?[a-z0-9'.\-\s]{0,80}"
            r"(?:act|law|regulation|directive|statute|code)\b",
            r"\b(?:what|how)\s+(?:does|do|did)\s+(?:the\s+)?"
            r"[a-z0-9'.\-\s]{0,80}"
            r"(?:act|law|regulation|directive|statute|code)\s+"
            r"(?:say|require|define|provide)\b",
            r"\b(?:articles?|sections?|clauses?|chapters?)\s+\d+[a-z]?\b",
            r"\b(?:act|law|regulation|directive|statute)\s+"
            r"(?:texts?|sources?|requirements?|obligations?|provisions?)\b",
            r"\b(?:law[-\s]+codes?|legal[-\s]+codes?|statutory[-\s]+codes?)\b",
            r"\b(?:legal|statutory|regulatory|compliance)\s+duties\b",
            r"\b(?:obligations?|duties)\s+(?:are\s+)?(?:already\s+)?in\s+force\b",
            r"\benforcement\s+dates?\b",
            r"\bcode\s+of\s+practice\b",
            r"\bcompliance\s+uncertainty\b",
        ),
    )
    if legal_or_regulatory_request or source_class in {"legal", "regulatory"}:
        _append_unique(expected, "legal_or_regulatory_text")

    official_legal_request = _has_any(
        text,
        (
            r"\bofficial\s+(?:legal|regulatory|statutory)\s+"
            r"(?:texts?|sources?|materials?|requirements?|obligations?|rules?)\b",
            r"\b(?:regulatory|compliance)\s+"
            r"(?:requirements?|obligations?|rules?|guidance)\b",
            r"\b(?:legal|statutory|regulatory|compliance)\s+duties\b",
            r"\b(?:obligations?|duties)\s+(?:are\s+)?(?:already\s+)?in\s+force\b",
            r"\benforcement\s+dates?\b",
        ),
    )
    if official_legal_request and not historical_rule_context:
        _append_unique(expected, "official_current_rules")
    elif source_class == "official" and claim_type in {"legal", "regulatory"}:
        _append_unique(expected, "official_current_rules")

    agency_official_request = _has_any(
        text,
        (
            r"\bofficially\s+"
            r"(?:says?|said|states?|stated|reports?|reported|announc(?:e|es|ed))\b",
            r"\bofficial\s+"
            r"(?:notice|recall|guidance|position|statement|advisory|warning|"
            r"determination|bulletin)\b",
            r"\b(?:agency|regulator|public\s+authority|government\s+authority)\b"
            r".{0,80}\bofficial\b",
        ),
    )
    if agency_official_request and not historical_rule_context:
        _append_unique(expected, "official_current_rules")

    if (
        not historical_rule_context
        and _public_program_official_current_request(text)
    ):
        _append_unique(expected, "official_current_rules")

    parliamentary_request = _has_any(
        text,
        (
            r"\b(?:parliamentary|parliament|legislative|legislature|"
            r"congressional|congress|hansard)\b",
            r"\b(?:bill|committee\s+report|legislative\s+history|"
            r"house\s+of\s+(?:commons|lords)|senate\s+committee)\b",
        ),
    )
    if parliamentary_request:
        _append_unique(expected, "parliamentary_or_legislative_material")

    historical_context = _has_any(
        text,
        (
            r"\b(?:historical|history|medieval|ancient|early[-\s]+modern)\b",
            r"\b(?:archive|archives|archival|primary[-\s]+source|"
            r"source[-\s]+text|original[-\s]+text|translated?|translation|"
            r"transcribed?|transcription)\b",
        ),
    )
    historical_primary_request = (
        historical_context
        and _has_any(
            text,
            (
                r"\b(?:orders?|records?|documents?|texts?|sources?|"
                r"proclamations?|edicts?|ordinances?)\b",
            ),
        )
    )
    if historical_primary_request:
        _append_unique(expected, "primary_source_documents")
        _append_unique(expected, "archival_primary_text")

    historical_legal_request = (
        legal_or_regulatory_request
        and (
            historical_context
            or _has_any(
                text,
                (
                    r"\b(?:charters?|law[-\s]+codes?|legal[-\s]+codes?|"
                    r"ordinances?|decrees?|edicts?)\b",
                    r"\b(?:translated?|translation|direct)\s+"
                    r"(?:law|legal|statutory|source|text)\b",
                ),
            )
        )
    )
    if historical_legal_request:
        _append_unique(expected, "historical_legal_text")
        _append_unique(expected, "primary_source_documents")

    if not expected:
        return ["none"]
    return expected


def _public_authority_domain_signal(domain: str) -> bool:
    return _domain_has_any(
        [domain],
        (
            r"(^|\.)gov(?:\.|$)",
            r"(^|\.)mil(?:\.|$)",
            r"(^|\.)int(?:\.|$)",
            r"(^|\.)europa\.eu$",
            r"\b(?:regulator|government|agency|authority)\b",
        ),
    )


def _legal_authority_domain_signal(domain: str) -> bool:
    return _public_authority_domain_signal(domain) or _domain_has_any(
        [domain],
        (
            r"(^|\.)eur-lex\.europa\.eu$",
            r"(^|\.)(?:commission|ec|digital-strategy|ai-office)\.europa\.eu$",
            r"(^|\.)legislation\.gov\.uk$",
            r"(^|\.)federalregister\.gov$",
            r"(^|\.)ecfr\.gov$",
            r"(^|\.)govinfo\.gov$",
            r"(^|\.)regulations\.gov$",
            r"(^|\.)congress\.gov$",
            r"(^|\.)law\.cornell\.edu$",
            r"(^|\.)avalon\.law\.yale\.edu$",
            r"(^|\.)sourcebooks\.fordham\.edu$",
            r"(^|\.)archives?\.gov$",
            r"(^|\.)nationalarchives\.gov\.uk$",
            r"(^|\.)loc\.gov$",
        ),
    )


def _legislative_authority_domain_signal(domain: str) -> bool:
    return _domain_has_any(
        [domain],
        (
            r"(^|\.)parliament\.uk$",
            r"(^|\.)hansard\.parliament\.uk$",
            r"(^|\.)bills\.parliament\.uk$",
            r"(^|\.)committees\.parliament\.uk$",
            r"(^|\.)legislation\.gov\.uk$",
            r"(^|\.)congress\.gov$",
            r"(^|\.)senate\.gov$",
            r"(^|\.)house\.gov$",
            r"(^|\.)govinfo\.gov$",
            r"(^|\.)congressionalrecord\.gov$",
        ),
    )


def _archival_authority_domain_signal(domain: str) -> bool:
    return _domain_has_any(
        [domain],
        (
            r"\b(?:archive|archives|archival|library|repository|sourcebooks?)\b",
            r"(^|\.)archive\.org$",
            r"(^|\.)archives?\.gov$",
            r"(^|\.)nationalarchives\.gov\.uk$",
            r"(^|\.)loc\.gov$",
            r"(^|\.)bl\.uk$",
            r"(^|\.)avalon\.law\.yale\.edu$",
            r"(^|\.)sourcebooks\.fordham\.edu$",
            r"(^|\.)law\.cornell\.edu$",
        ),
    )


def _secondary_source_signal(domain: str, tier: str) -> bool:
    return tier in {
        "secondary",
        "trusted_community",
        "social_or_forum",
        "low_trust_commercial",
        "content_mill",
    } or _domain_has_any(
        [domain],
        (
            r"(^|\.)arxiv\.org$",
            r"(^|\.)nature\.com$",
            r"(^|\.)jstor\.org$",
            r"(^|[.\-])news([.\-]|$)",
            r"(^|\.)"
            r"(?:apnews|bbc|bloomberg|cnn|forbes|nytimes|politico|reuters|"
            r"theguardian|theverge|washingtonpost)\.com$",
        ),
    )


def _empty_signal_map() -> dict[str, dict[str, list[str]]]:
    return {
        bucket: {"strong": [], "weak": [], "secondary_only": []}
        for bucket in SOURCE_CLASS_OBSERVABILITY_BUCKETS
        if bucket != "none"
    }


def _append_signal(
    signals: dict[str, dict[str, list[str]]],
    bucket: str,
    strength: str,
    basis: str,
) -> None:
    _append_unique(signals[bucket][strength], basis)


def _evidence_source_class_strengths(
    source: Mapping[str, Any],
) -> dict[str, dict[str, list[str]]]:
    text = _evidence_classification_text(source)
    domain = _source_domain_from_url(source.get("url"))
    tier = str(source.get("source_tier") or "").strip().casefold()
    signals = _empty_signal_map()

    official_signal = tier == "official" or _public_authority_domain_signal(domain)
    legal_authority_signal = official_signal or _legal_authority_domain_signal(domain)
    legislative_authority_signal = _legislative_authority_domain_signal(domain) or (
        official_signal
        and _has_any(
            text,
            (
                r"\b(?:parliament|parliamentary|legislation|legislative|"
                r"legislature|congress|hansard|bill|committee|senate)\b",
            ),
        )
    )
    archival_authority_signal = _archival_authority_domain_signal(domain)
    secondary_signal = _secondary_source_signal(domain, tier)
    for source_class in _declared_source_classes(source):
        _append_signal(
            signals,
            source_class,
            "secondary_only" if secondary_signal else "strong",
            "secondary_declared_source_class"
            if secondary_signal
            else "declared_source_class",
        )

    official_reference_signal = _has_any(
        text,
        (
            r"\bofficial(?:ly)?\b",
            r"\b(?:agency|regulator|government|public\s+authority|authority)\b",
            r"\b(?:recall|notice|guidance|statement|position|advisory)\b",
        ),
    )
    legal_discussion_signal = _has_any(
        text,
        (
            r"\b(?:legal|law|legislation|regulation|regulatory|statute|"
            r"statutory|directive|ordinance|decree)\b",
            r"\b(?:cfr|ecfr|code\s+of\s+federal\s+regulations|"
            r"federal\s+register|govinfo)\b",
            r"\b(?:articles?|sections?|clauses?|chapters?)\s+\d+[a-z]?\b",
            r"\b(?:articles?|sections?|clauses?|chapters?|obligations?|duties)\b",
            r"\b(?:official\s+journal|eur-lex|code\s+of\s+practice)\b",
            r"\b(?:requirements?|provisions?)\s+under\s+"
            r"(?:the\s+)?[a-z0-9'.\-\s]{0,80}"
            r"(?:act|law|regulation|directive|statute|code)\b",
            r"\b(?:law[-\s]+codes?|legal[-\s]+codes?|charters?)\b",
        ),
    )
    direct_legal_text_signal = _has_any(
        text,
        (
            r"\b(?:full\s+text|text\s+of|original\s+text|translated?\s+text|"
            r"translation|source\s+text)\b",
            r"\b(?:official\s+journal|eur-lex|ecfr|cfr|federal\s+register|"
            r"govinfo|code\s+of\s+federal\s+regulations)\b",
            r"\b(?:articles?|sections?|clauses?|chapters?)\s+\d+[a-z]?\b",
            r"\b(?:law[-\s]+codes?|legal[-\s]+codes?|charters?)\b",
        ),
    )
    official_current_rule_signal = (
        legal_discussion_signal
        or direct_legal_text_signal
        or _has_any(
            text,
            (
                r"\b(?:current|effective|as\s+of|latest|202[0-9])\b"
                r".{0,80}"
                r"\b(?:rules?|requirements?|guidance|notice|advisory|"
                r"warning|statement|position|determination|bulletin|"
                r"enforcement|compliance|obligations?|duties)\b",
                r"\b(?:rules?|requirements?|guidance|notice|advisory|"
                r"warning|statement|position|determination|bulletin|"
                r"enforcement|compliance|obligations?|duties)\b"
                r".{0,80}"
                r"\b(?:current|effective|as\s+of|latest|202[0-9])\b",
                r"\b(?:final\s+rule|compliance\s+date|enforcement\s+status|"
                r"official\s+requirements?|agency\s+guidance|agency\s+rule)\b",
                r"\b(?:recall|notice|guidance|advisory|warning|statement|"
                r"position|determination|bulletin)\b",
            ),
        )
    )
    legislative_signal = _has_any(
        text,
        (
            r"\b(?:parliament|parliamentary|legislation|legislative|"
            r"legislature|congress|hansard|bill|committee|senate)\b",
        ),
    )
    direct_primary_text_signal = _has_any(
        text,
        (
            r"\b(?:primary[-\s]+source|source[-\s]+text|original[-\s]+text|"
            r"full\s+text|transcript|transcription|translated?\s+text|"
            r"translation|text\s+of)\b",
        ),
    )
    document_signal = _has_any(
        text,
        (
            r"\b(?:records?|documents?|manuscripts?|collection|sourcebooks?)\b",
        ),
    )
    archival_reference_signal = archival_authority_signal or _has_any(
        text,
        (
            r"\b(?:archive|archives|archival|library|repository|sourcebooks?)\b",
        ),
    )
    primary_reference_signal = direct_primary_text_signal or document_signal
    historical_signal = _has_any(
        text,
        (
            r"\b(?:historical|history|medieval|ancient|early[-\s]+modern|"
            r"charters?|translated?|translation|source[-\s]+text|"
            r"original[-\s]+text)\b",
        ),
    )
    historical_legal_signal = legal_discussion_signal and (
        historical_signal
        or _has_any(
            text,
            (
                r"\b(?:charters?|law[-\s]+codes?|legal[-\s]+codes?|"
                r"ordinances?|decrees?|edicts?)\b",
            ),
        )
    )
    issuer_signal = _issuer_materials_domain_signal([domain]) or _has_any(
        text,
        (
            r"\b(?:investor\s+relations?|earnings\s+release|quarterly\s+"
            r"(?:results?|reports?)|annual\s+reports?|10[-\s]?[qk]|"
            r"sec\s+filings?)\b",
        ),
    )
    polling_signal = _polling_domain_signal([domain]) or _has_any(
        text,
        (
            r"\b(?:polling?\s+average|polling?\s+data|toplines?|"
            r"crosstabs?|survey\s+aggregator)\b",
        ),
    )

    if official_signal and official_current_rule_signal:
        _append_signal(
            signals,
            "official_current_rules",
            "strong",
            "official_current_rule_authority",
        )
    elif official_reference_signal:
        _append_signal(
            signals,
            "official_current_rules",
            "secondary_only" if secondary_signal else "weak",
            "secondary_official_discussion"
            if secondary_signal
            else "official_reference_signal",
        )

    if legal_discussion_signal:
        if legal_authority_signal or (
            archival_authority_signal and direct_legal_text_signal
        ):
            _append_signal(
                signals,
                "legal_or_regulatory_text",
                "strong",
                "legal_or_regulatory_authority",
            )
        else:
            _append_signal(
                signals,
                "legal_or_regulatory_text",
                "secondary_only" if secondary_signal else "weak",
                "secondary_legal_discussion"
                if secondary_signal
                else "legal_discussion_signal",
            )

    if legislative_signal:
        if legislative_authority_signal:
            _append_signal(
                signals,
                "parliamentary_or_legislative_material",
                "strong",
                "legislative_authority",
            )
        else:
            _append_signal(
                signals,
                "parliamentary_or_legislative_material",
                "secondary_only" if secondary_signal else "weak",
                "secondary_legislative_discussion"
                if secondary_signal
                else "legislative_material_signal",
            )

    if primary_reference_signal:
        if direct_primary_text_signal and (
            archival_authority_signal or legal_authority_signal or official_signal
        ):
            _append_signal(
                signals,
                "primary_source_documents",
                "strong",
                "primary_text_authority",
            )
        else:
            _append_signal(
                signals,
                "primary_source_documents",
                "secondary_only" if secondary_signal else "weak",
                "secondary_primary_text_discussion"
                if secondary_signal
                else "primary_text_signal",
            )

    if _canonical_documentation_signal(
        source=source,
        text=text,
        domain=domain,
        tier=tier,
        secondary_signal=secondary_signal,
    ):
        _append_signal(
            signals,
            "primary_source_documents",
            "strong",
            "canonical_documentation_source_fit",
        )
    elif secondary_signal and is_canonical_technical_documentation_context(
        text,
        required_source_classes=("primary_source_documents",),
    ):
        _append_signal(
            signals,
            "primary_source_documents",
            "secondary_only",
            "secondary_canonical_documentation_discussion",
        )

    if archival_reference_signal:
        if archival_authority_signal and (
            direct_primary_text_signal
            or document_signal
            or historical_signal
            or direct_legal_text_signal
        ):
            _append_signal(
                signals,
                "archival_primary_text",
                "strong",
                "archival_primary_authority",
            )
        elif primary_reference_signal or historical_signal:
            _append_signal(
                signals,
                "archival_primary_text",
                "secondary_only" if secondary_signal else "weak",
                "secondary_archival_discussion"
                if secondary_signal
                else "archival_reference_signal",
            )

    if historical_legal_signal:
        if (
            archival_authority_signal or legal_authority_signal or official_signal
        ) and (direct_legal_text_signal or direct_primary_text_signal):
            _append_signal(
                signals,
                "historical_legal_text",
                "strong",
                "historical_legal_authority_text",
            )
        else:
            _append_signal(
                signals,
                "historical_legal_text",
                "secondary_only" if secondary_signal else "weak",
                "secondary_historical_legal_discussion"
                if secondary_signal
                else "historical_legal_text_signal",
            )

    if issuer_signal or (official_signal and _issuer_materials_domain_signal([domain])):
        _append_signal(
            signals,
            "issuer_filings_or_company_materials",
            "strong",
            "issuer_materials_signal",
        )
    if polling_signal:
        _append_signal(
            signals,
            "polling_data_or_aggregator",
            "strong",
            "polling_signal",
        )
    return signals


def _evidence_source_class_bases(source: Mapping[str, Any]) -> dict[str, list[str]]:
    signals = _evidence_source_class_strengths(source)
    bases: dict[str, list[str]] = {}
    for bucket, bucket_signals in signals.items():
        bases[bucket] = []
        for strength in ("strong", "weak", "secondary_only"):
            for basis in bucket_signals[strength]:
                _append_unique(bases[bucket], basis)
    return bases


def _selected_final_sources(
    final_top_evidence: Iterable[Mapping[str, Any]] | None,
    final_answer_source_ids: Iterable[Any] | None,
) -> list[Mapping[str, Any]]:
    sources = [source for source in final_top_evidence or [] if isinstance(source, Mapping)]
    cited_ids = {
        str(source_id).strip()
        for source_id in (final_answer_source_ids or [])
        if str(source_id).strip()
    }
    if not cited_ids:
        return sources
    cited_sources = [
        source
        for source in sources
        if str(source.get("source_id") or "").strip() in cited_ids
    ]
    return cited_sources or sources


def build_source_class_observability_telemetry(
    *,
    query: str,
    intent: str,
    report_type: str,
    query_type: str,
    core_topic: str,
    primary_entity: str,
    anchor_packet: dict[str, Any] | None,
    final_top_evidence: Iterable[Mapping[str, Any]] | None,
    final_answer_source_ids: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Build source-class underfire observability without changing recovery."""
    text = _combined_text(
        query=query,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        anchor_packet=anchor_packet,
    )
    expected = _observability_expected_source_classes(
        text=text,
        anchor_packet=anchor_packet,
    )
    expected_without_none = [bucket for bucket in expected if bucket != "none"]
    sources = _selected_final_sources(final_top_evidence, final_answer_source_ids)

    strong_counts = {
        bucket: 0
        for bucket in SOURCE_CLASS_OBSERVABILITY_BUCKETS
        if bucket != "none"
    }
    weak_counts = {
        bucket: 0
        for bucket in SOURCE_CLASS_OBSERVABILITY_BUCKETS
        if bucket != "none"
    }
    secondary_only_counts = {
        bucket: 0
        for bucket in SOURCE_CLASS_OBSERVABILITY_BUCKETS
        if bucket != "none"
    }
    satisfaction_basis = {
        bucket: []
        for bucket in SOURCE_CLASS_OBSERVABILITY_BUCKETS
        if bucket != "none"
    }
    for source in sources:
        signals = _evidence_source_class_strengths(source)
        for bucket, bucket_signals in signals.items():
            if bucket_signals["strong"]:
                strong_counts[bucket] += 1
            elif bucket_signals["secondary_only"]:
                secondary_only_counts[bucket] += 1
            elif bucket_signals["weak"]:
                weak_counts[bucket] += 1
            for strength in ("strong", "weak", "secondary_only"):
                for basis in bucket_signals[strength]:
                    _append_unique(satisfaction_basis[bucket], basis)

    satisfaction_status, gap_candidates = (
        _evaluate_source_class_satisfaction_with_authority_kernel(
            expected_without_none,
            strong_counts=strong_counts,
            weak_counts=weak_counts,
            secondary_only_counts=secondary_only_counts,
        )
    )

    strength_counts = {status: 0 for status in SOURCE_CLASS_SATISFACTION_STATUSES}
    for status in satisfaction_status.values():
        strength_counts[status] += 1

    underfire = bool(gap_candidates)
    reasons: list[str] = []
    blockers: list[str] = []
    if underfire:
        reasons.append("missing_expected_source_class")
        if not sources:
            reasons.append("no_final_evidence")
    elif not expected_without_none:
        blockers.append("no_expected_source_class")
    else:
        blockers.append("all_expected_source_classes_satisfied")

    return {
        "expected_source_classes_raw": expected,
        "source_class_gap_candidates": gap_candidates,
        "source_class_satisfaction_basis": {
            bucket: satisfaction_basis[bucket]
            for bucket in expected_without_none
        },
        "source_class_satisfaction_status": satisfaction_status,
        "source_class_satisfaction_strength_counts": strength_counts,
        "source_class_underfire_shadow": underfire,
        "source_class_underfire_reasons": reasons,
        "source_class_underfire_blockers": blockers,
        "final_official_source_count": strong_counts["official_current_rules"],
        "final_primary_source_count": strong_counts["primary_source_documents"],
        "final_archival_source_count": strong_counts["archival_primary_text"],
        "final_legal_or_regulatory_source_count": strong_counts[
            "legal_or_regulatory_text"
        ],
        "source_class_satisfaction_counts": strong_counts,
        "source_class_strong_satisfaction_counts": strong_counts,
        "source_class_weak_satisfaction_counts": weak_counts,
        "source_class_secondary_only_counts": secondary_only_counts,
    }


def recovery_source_quality_defaults() -> dict[str, Any]:
    """Return compact defaults for source-class recovery quality diagnostics."""
    return {
        "recovered_source_tier_counts": {},
        "recovered_source_class_counts": {},
        "recovered_candidate_domain_preview": [],
        "recovered_official_or_primary_count": 0,
        "recovered_accepted_url_count": 0,
        "recovered_promoted_source_count": 0,
        "recovery_source_quality_status": "unknown",
    }


def _source_identity(source: Mapping[str, Any]) -> str:
    for key in ("url", "source_id", "title"):
        value = str(source.get(key) or "").strip()
        if value:
            return value
    return ""


def _quality_source_keys(
    sources: Iterable[Mapping[str, Any]],
) -> set[str]:
    quality_buckets = {
        "official_current_rules",
        "legal_or_regulatory_text",
        "primary_source_documents",
        "archival_primary_text",
        "historical_legal_text",
        "issuer_filings_or_company_materials",
    }
    keys: set[str] = set()
    for source in sources:
        signals = _evidence_source_class_strengths(source)
        if any(signals.get(bucket, {}).get("strong") for bucket in quality_buckets):
            identity = _source_identity(source)
            if identity:
                keys.add(identity)
    return keys


def build_recovery_source_quality_diagnostics(
    recovered_passages: Iterable[Mapping[str, Any]],
    *,
    final_top_evidence: Iterable[Mapping[str, Any]] | None = None,
    final_source_class_counts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize recovered result quality without ranking, filtering, or promotion."""
    recovered = [
        source for source in recovered_passages if isinstance(source, Mapping)
    ]
    if not recovered:
        out = recovery_source_quality_defaults()
        out["recovery_source_quality_status"] = "no_relevant_sources"
        return out

    tier_counts: dict[str, int] = {}
    class_counts: dict[str, int] = {
        bucket: 0
        for bucket in SOURCE_CLASS_OBSERVABILITY_BUCKETS
        if bucket != "none"
    }
    accepted_urls: set[str] = set()
    candidate_domains: list[str] = []
    seen_candidate_domains: set[str] = set()
    secondary_like_count = 0
    authority_without_class_count = 0

    for source in recovered:
        url = str(source.get("url") or "").strip()
        if url:
            accepted_urls.add(url)
        tier = str(source.get("source_tier") or "unknown").strip() or "unknown"
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        domain = _source_domain_from_url(url)
        if domain and domain not in seen_candidate_domains:
            candidate_domains.append(domain)
            seen_candidate_domains.add(domain)
        signals = _evidence_source_class_strengths(source)
        strong_hit = False
        for bucket, bucket_signals in signals.items():
            if bucket_signals["strong"]:
                class_counts[bucket] += 1
                strong_hit = True
        if _secondary_source_signal(domain, tier.casefold()):
            secondary_like_count += 1
        if (
            not strong_hit
            and (
                _public_authority_domain_signal(domain)
                or _legal_authority_domain_signal(domain)
                or _archival_authority_domain_signal(domain)
            )
        ):
            authority_without_class_count += 1

    recovered_keys = {
        _source_identity(source)
        for source in recovered
        if _source_identity(source)
    }
    quality_keys = _quality_source_keys(recovered)
    promoted_count = 0
    quality_promoted_count = 0
    if final_top_evidence is not None:
        final_keys = {
            _source_identity(source)
            for source in final_top_evidence
            if isinstance(source, Mapping)
        }
        promoted_count = len(recovered_keys & final_keys)
        quality_promoted_count = len(quality_keys & final_keys)

    quality_count = len(quality_keys)
    final_quality_count = 0
    if final_source_class_counts is not None:
        for bucket in (
            "official_current_rules",
            "legal_or_regulatory_text",
            "primary_source_documents",
            "archival_primary_text",
            "historical_legal_text",
            "issuer_filings_or_company_materials",
        ):
            try:
                final_quality_count += int(final_source_class_counts.get(bucket, 0) or 0)
            except (TypeError, ValueError):
                continue

    status = "unknown"
    if quality_count > 0:
        status = "official_or_primary_found"
        if (
            quality_promoted_count > 0
            and final_source_class_counts is not None
            and final_quality_count == 0
        ):
            status = "promoted_but_not_final"
    elif authority_without_class_count > 0:
        status = "classification_mismatch"
    elif secondary_like_count == len(recovered):
        status = "secondary_only"
    elif accepted_urls:
        status = "no_relevant_sources"

    return {
        "recovered_source_tier_counts": {
            key: tier_counts[key] for key in sorted(tier_counts)
        },
        "recovered_source_class_counts": {
            key: value for key, value in class_counts.items() if value
        },
        "recovered_candidate_domain_preview": candidate_domains[:8],
        "recovered_official_or_primary_count": quality_count,
        "recovered_accepted_url_count": len(accepted_urls),
        "recovered_promoted_source_count": promoted_count,
        "recovery_source_quality_status": status,
    }


def _source_class_present(
    bucket: str,
    *,
    source_tier_counts: dict[str, int],
    domains: list[str],
    official_evidence_found: bool,
) -> bool:
    official_present = bool(official_evidence_found) or _positive_count(source_tier_counts, "official")

    if bucket in {
        "official_current_rules",
    }:
        present = official_present or _official_domain_signal(domains)
    elif bucket == "issuer_filings_or_company_materials":
        return official_present or _official_domain_signal(domains) or _issuer_materials_domain_signal(domains)
    elif bucket == "polling_data_or_aggregator":
        return _polling_domain_signal(domains)
    elif bucket == "primary_source_documents":
        present = official_present or _primary_document_domain_signal(domains)
    else:
        return True

    requirement = _authority_requirement_for_source_class(bucket)
    authority_class = _KERNEL_SOURCE_CLASS_MAP.get(
        _compact_text(bucket, limit=80).casefold()
    )
    if requirement is None or authority_class is None:
        return bool(present)
    state = AuthoritativeSourceObligationState.evaluate(
        [requirement],
        (
            AuthorityEvidenceFit.authoritative(
                requirement.requirement_id,
                f"{bucket}:present",
                authority_class,
            ),
        )
        if present
        else (),
    )
    return state.satisfaction_for(requirement.requirement_id).status is (
        AuthorityStatus.FULFILLED
    )


def _query_subject(*, primary_entity: str, core_topic: str, query: str) -> str:
    for value in (primary_entity, core_topic, query):
        clean = _compact_text(value, limit=100)
        if clean:
            return clean
    return "source topic"


def _official_source_target_hints(*texts: str) -> list[str]:
    """Return deterministic public-authority hints as ordinary search terms."""
    text = " ".join(_compact_text(value, limit=240) for value in texts).casefold()
    hints: list[str] = []

    def add(*values: str) -> None:
        for value in values:
            _append_unique(hints, value)

    dot_context = _has_any(
        text,
        (
            r"\b(?:department\s+of\s+transportation|transportation\s+department)\b",
            r"\bair\s+carrier\s+access\s+act\b",
            r"\b(?:airlines?|airline\s+passengers?|passengers?\s+with\s+disabilities)\b",
        ),
    ) or (
        _has_any(text, (r"\bdot\b",))
        and _has_any(
            text,
            (
                r"\b(?:airlines?|transportation|carrier|passengers?|"
                r"wheelchairs?|regulations?|rules?)\b",
            ),
        )
    )
    if dot_context:
        add("transportation.gov", "DOT", "14 CFR Part 382", "Air Carrier Access Act")

    if _has_any(
        text,
        (
            r"\b(?:ftc|federal\s+trade\s+commission)\b",
            r"\bnon[-\s]?competes?\b",
            r"\b(?:negative\s+option|click[-\s]?to[-\s]?cancel)\b",
        ),
    ):
        add("ftc.gov", "Federal Register", "final rule", "court status")

    if _has_any(
        text,
        (
            r"\b(?:fda|food\s+and\s+drug\s+administration)\b",
            r"\blaboratory\s+developed\s+tests?\b",
            r"\bldts?\b",
            r"\bmedical\s+devices?\b",
            r"\benforcement\s+discretion\b",
        ),
    ):
        add("fda.gov", "Federal Register", "enforcement discretion", "final rule")

    if _has_any(
        text,
        (
            r"\b(?:osha|occupational\s+safety\s+and\s+health)\b",
            r"\bhazard\s+communication\b",
            r"\b29\s+cfr\s+1910\.1200\b",
        ),
    ):
        add("osha.gov", "29 CFR 1910.1200", "Federal Register")

    if _has_any(
        text,
        (
            r"\b(?:irs|internal\s+revenue\s+service)\b",
            r"\btax\s+credits?\b",
            r"\b(?:forms?|instructions?)\b",
        ),
    ):
        add("irs.gov", "form", "instructions", "Internal Revenue Bulletin")

    if _has_any(
        text,
        (
            r"\b(?:cfpb|consumer\s+financial\s+protection\s+bureau)\b",
            r"\bconsumer\s+finance\b",
        ),
    ):
        add("consumerfinance.gov", "rule", "guidance")

    sec_context = _has_any(
        text,
        (
            r"\b(?:securities\s+and\s+exchange\s+commission|issuer\s+filings?|"
            r"edgar|10[-\s]?[qk]|form\s+10[-\s]?[qk])\b",
        ),
    ) or (
        _has_any(text, (r"\bsec\b",))
        and _has_any(text, (r"\b(?:filings?|issuer|edgar|securities)\b",))
    )
    if sec_context:
        add("sec.gov", "EDGAR", "issuer filing")

    return hints


def _normalize_recovery_domain(value: Any) -> str:
    raw = _compact_text(value, limit=120).casefold()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or raw.split("/", 1)[0]).strip().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host):
        return ""
    if "." not in host:
        return ""
    return host


def _append_domain(target: list[str], value: str) -> None:
    domain = _normalize_recovery_domain(value)
    if domain and domain not in target:
        target.append(domain)


def build_official_source_recovery_domain_constraints(
    *,
    missing_expected_source_classes: Iterable[Any],
    query: str,
    core_topic: str = "",
    primary_entity: str = "",
    recovery_queries: Iterable[Any] = (),
) -> list[str]:
    """Return deterministic official-domain constraints for source recovery."""
    missing = {
        str(item or "").strip()
        for item in missing_expected_source_classes or ()
        if str(item or "").strip()
    }
    if not (missing & OFFICIAL_SOURCE_DOMAIN_CONSTRAINT_CLASSES):
        return []

    text = " ".join(
        _compact_text(value, limit=240)
        for value in (
            query,
            core_topic,
            primary_entity,
            " ".join(
                _compact_text(item, limit=120)
                for item in (recovery_queries or ())
                if str(item or "").strip()
            ),
        )
        if str(value or "").strip()
    ).casefold()

    domains: list[str] = []
    official_or_legal_missing = bool(
        missing & {"official_current_rules", "legal_or_regulatory_text"}
    )

    dot_context = _has_any(
        text,
        (
            r"\b(?:department\s+of\s+transportation|transportation\s+department)\b",
            r"\bair\s+carrier\s+access\s+act\b",
            r"\b(?:airlines?|airline\s+passengers?|passengers?\s+with\s+disabilities)\b",
        ),
    ) or (
        _has_any(text, (r"\bdot\b",))
        and _has_any(
            text,
            (
                r"\b(?:airlines?|transportation|carrier|passengers?|"
                r"wheelchairs?|regulations?|rules?)\b",
            ),
        )
    )

    agency_targets: tuple[tuple[tuple[str, ...], str], ...] = (
        (
            (
                r"\b(?:ftc|federal\s+trade\s+commission)\b",
                r"\bnon[-\s]?competes?\b",
                r"\b(?:negative\s+option|click[-\s]?to[-\s]?cancel)\b",
            ),
            "ftc.gov",
        ),
        (
            (
                r"\b(?:fda|food\s+and\s+drug\s+administration)\b",
                r"\blaboratory\s+developed\s+tests?\b",
                r"\bldts?\b",
                r"\bmedical\s+devices?\b",
                r"\benforcement\s+discretion\b",
            ),
            "fda.gov",
        ),
        (
            (
                r"\b(?:osha|occupational\s+safety\s+and\s+health)\b",
                r"\bhazard\s+communication\b",
                r"\b29\s+cfr\s+1910\.1200\b",
            ),
            "osha.gov",
        ),
        (
            (
                r"\b(?:irs|internal\s+revenue\s+service)\b",
                r"\btax\s+credits?\b",
                r"\bstandard\s+mileage\s+rate\b",
                r"\bmileage\s+rate\b",
            ),
            "irs.gov",
        ),
        (
            (
                r"\b(?:ssa|social\s+security\s+administration)\b",
                r"\bsocial\s+security\b",
                r"\btaxable\s+maximum\b",
                r"\bwage\s+base\b",
                r"\bcontribution\s+and\s+benefit\s+base\b",
            ),
            "ssa.gov",
        ),
        (
            (
                r"\b(?:dol|department\s+of\s+labor)\b",
                r"\bfederal\s+minimum\s+wage\b",
                r"\bminimum\s+wage\b",
            ),
            "dol.gov",
        ),
        (
            (
                r"\buscis\b",
                r"\bn-400\b",
                r"\bnaturalization\b",
                r"\bfiling\s+fee\b",
            ),
            "uscis.gov",
        ),
        (
            (
                r"\b(?:cfpb|consumer\s+financial\s+protection\s+bureau)\b",
                r"\bconsumer\s+finance\b",
            ),
            "consumerfinance.gov",
        ),
        (
            (
                r"\b(?:sec|securities\s+and\s+exchange\s+commission)\b",
                r"\b(?:issuer\s+filings?|edgar|10[-\s]?[qk]|form\s+10[-\s]?[qk])\b",
            ),
            "sec.gov",
        ),
    )
    us_agency_domains: list[str] = []
    if dot_context:
        _append_domain(us_agency_domains, "transportation.gov")
    for patterns, domain in agency_targets:
        if _has_any(text, patterns):
            _append_domain(us_agency_domains, domain)

    us_legal_context = (
        bool(us_agency_domains)
        or _has_any(
            text,
            (
                r"\b(?:u\.s\.|us|united\s+states|american)\b"
                r".{0,100}"
                r"\b(?:law|legal|regulation|regulatory|rule|rules|"
                r"statute|agency|federal)\b",
                r"\b(?:cfr|ecfr|code\s+of\s+federal\s+regulations|"
                r"federal\s+register|govinfo|regulations\.gov)\b",
            ),
        )
    )
    eu_legal_context = _has_any(
        text,
        (
            r"\b(?:eu|e\.u\.|european\s+union|eur[-\s]?lex|eurlex)\b"
            r".{0,120}"
            r"\b(?:law|legal|regulation|regulatory|directive|act|"
            r"obligations?|duties|text|requirements?)\b",
            r"\b(?:law|legal|regulation|regulatory|directive|act|"
            r"obligations?|duties|text|requirements?)\b"
            r".{0,120}"
            r"\b(?:eu|e\.u\.|european\s+union|eur[-\s]?lex|eurlex)\b",
            r"\b(?:ai\s+act|gdpr|eprivacy|digital\s+services\s+act|"
            r"digital\s+markets\s+act)\b",
            r"\bregulation\s+\(eu\)\b",
        ),
    )
    uk_legal_context = _has_any(
        text,
        (
            r"\b(?:uk|u\.k\.|united\s+kingdom|british|legislation\.gov\.uk)\b"
            r".{0,120}"
            r"\b(?:law|legal|regulation|regulatory|act|statute|statutory|"
            r"instrument|obligations?|duties|text|requirements?)\b",
            r"\b(?:law|legal|regulation|regulatory|act|statute|statutory|"
            r"instrument|obligations?|duties|text|requirements?)\b"
            r".{0,120}"
            r"\b(?:uk|u\.k\.|united\s+kingdom|british|legislation\.gov\.uk)\b",
            r"\b(?:online\s+safety\s+act|data\s+protection\s+act|"
            r"companies\s+act\s+2006)\b",
        ),
    )

    if official_or_legal_missing and us_legal_context:
        for domain in OFFICIAL_SOURCE_US_AUTHORITY_DOMAINS:
            _append_domain(domains, domain)
    for domain in us_agency_domains:
        _append_domain(domains, domain)
    if official_or_legal_missing and eu_legal_context:
        for domain in OFFICIAL_SOURCE_EU_AUTHORITY_DOMAINS:
            _append_domain(domains, domain)
    if official_or_legal_missing and uk_legal_context:
        for domain in OFFICIAL_SOURCE_UK_AUTHORITY_DOMAINS:
            _append_domain(domains, domain)

    return domains


def _hint_text(hints: list[str]) -> str:
    return _compact_text(" ".join(hints), limit=80)


def _append_hint(base: str, hint_text: str) -> str:
    if not hint_text:
        return base
    return f"{base} {hint_text}"


def _candidate_queries_for_bucket(
    bucket: str,
    subject: str,
    *,
    context_text: str = "",
) -> list[str]:
    hints = _hint_text(_official_source_target_hints(subject, context_text))
    if bucket == "official_current_rules":
        return [
            _append_hint(
                f"{subject} official source current rules government agency guidance "
                "Federal Register CFR eCFR GovInfo",
                hints,
            ),
            _append_hint(
                f"{subject} final rule compliance date enforcement status "
                "agency guidance official requirements",
                hints,
            ),
        ]
    if bucket == "legal_or_regulatory_text":
        return [
            _append_hint(
                f"{subject} legal regulatory text statute regulation CFR eCFR "
                "Code of Federal Regulations",
                hints,
            ),
            _append_hint(
                f"{subject} Federal Register GovInfo final rule docket "
                "compliance date regulation text",
                hints,
            ),
        ]
    if bucket == "current_primary_or_official":
        return [
            _append_hint(
                f"{subject} current official primary source agency guidance "
                "Federal Register enforcement status",
                hints,
            ),
            _append_hint(
                f"{subject} official source current status final rule "
                "court status compliance date",
                hints,
            ),
        ]
    if bucket == "issuer_filings_or_company_materials":
        return [
            f"{subject} investor relations quarterly results earnings release SEC",
            f"{subject} SEC 10-Q 10-K quarterly results company filings",
        ]
    if bucket == "polling_data_or_aggregator":
        return [
            f"{subject} polling average poll toplines crosstabs survey aggregator",
            f"{subject} latest poll broader polling averages survey",
        ]
    if bucket == "primary_source_documents":
        if is_canonical_technical_documentation_context(
            subject,
            context_text,
            required_source_classes=("primary_source_documents",),
        ):
            return [
                f"{subject} official documentation reference manual",
                f"{subject} reference documentation official docs",
            ]
        return [
            f"{subject} primary sources documents records archive",
            f"{subject} primary evidence records materials documents",
        ]
    return []


def _dedupe_cap_queries(queries: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for query in queries:
        clean = _compact_text(query, limit=_CAP_QUERY)
        key = clean.casefold()
        if clean and key not in seen:
            out.append(clean)
            seen.add(key)
        if len(out) >= _MAX_RECOVERY_QUERIES:
            break
    return out


def _copy_compact_list(value: Any, *, limit: int = 80) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    values = value if isinstance(value, (list, tuple, set)) else []
    for item in values:
        text = _compact_text(item, limit=limit)
        key = text.casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return out


def _answer_contract_gap_classes(
    *values: Any,
) -> list[str]:
    haystack: list[str] = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            haystack.extend(_compact_text(item, limit=120) for item in value)
        else:
            haystack.append(_compact_text(value, limit=120))

    found: list[str] = []
    for source_class in ANSWER_CONTRACT_SOURCE_CLASS_RECOVERY_CLASSES:
        source_text = source_class.casefold()
        source_words = source_class.replace("_", " ").casefold()
        if any(
            source_text in item.casefold() or source_words in item.casefold()
            for item in haystack
        ):
            _append_unique(found, source_class)
    return found


def _answer_contract_goal_allows_gap(
    *,
    family: str | None,
    source_class: str,
) -> bool:
    normalized_family = str(family or "").strip().casefold()
    normalized_class = source_class.casefold()
    if normalized_class == "legal_or_regulatory_text":
        return normalized_family == "legal_or_regulatory_primary_text"
    if normalized_class == "official_current_rules":
        return normalized_family in _ANSWER_CONTRACT_OFFICIAL_OR_LEGAL_FAMILIES
    if normalized_class == "current_primary_or_official":
        return normalized_family in _ANSWER_CONTRACT_CURRENT_PRIMARY_FAMILIES
    return False


def _answer_contract_gap_reason(gaps: list[str]) -> str | None:
    for source_class in ANSWER_CONTRACT_SOURCE_CLASS_RECOVERY_CLASSES:
        if source_class in gaps:
            return ANSWER_CONTRACT_SOURCE_CLASS_RECOVERY_REASON_BY_CLASS[source_class]
    return None


def apply_answer_contract_source_class_recovery_gap_trigger(
    *,
    recommendation: Mapping[str, Any] | None,
    answer_contract_family: str | None,
    answer_contract_source_classes_missing: Iterable[Any] = (),
    answer_contract_unfulfilled_items: Iterable[Any] = (),
    answer_contract_partial_items: Iterable[Any] = (),
    query: str,
    core_topic: str,
    primary_entity: str,
) -> dict[str, Any]:
    """Merge a bounded answer-contract source-class gap into the recommendation."""
    base = dict(recommendation or {})
    missing = _copy_compact_list(base.get("missing_expected_source_classes"))
    explicit_missing_gaps = _answer_contract_gap_classes(
        answer_contract_source_classes_missing,
    )
    handoff_item_gaps = [
        source_class
        for source_class in _answer_contract_gap_classes(
            answer_contract_unfulfilled_items,
            answer_contract_partial_items,
        )
        if source_class != "current_primary_or_official"
    ]
    gap_candidates = list(explicit_missing_gaps)
    for source_class in handoff_item_gaps:
        _append_unique(gap_candidates, source_class)
    allowed_gaps = [
        source_class
        for source_class in gap_candidates
        if _answer_contract_goal_allows_gap(
            family=answer_contract_family,
            source_class=source_class,
        )
    ]

    added_gaps: list[str] = []
    for source_class in allowed_gaps:
        if source_class not in missing:
            missing.append(source_class)
            added_gaps.append(source_class)

    if not added_gaps:
        return base

    queries = _copy_compact_list(
        base.get("source_class_recovery_queries"),
        limit=_CAP_QUERY,
    )
    subject = _query_subject(
        primary_entity=primary_entity,
        core_topic=core_topic,
        query=query,
    )
    context_text = " ".join(
        part
        for part in (query, core_topic, primary_entity)
        if str(part or "").strip()
    )
    for source_class in added_gaps:
        queries.extend(
            _candidate_queries_for_bucket(
                source_class,
                subject,
                context_text=context_text,
            )
        )
    recovery_queries = _dedupe_cap_queries(queries)
    official_domains = build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=missing,
        query=query,
        core_topic=core_topic,
        primary_entity=primary_entity,
        recovery_queries=recovery_queries,
    )

    trigger_fields = _copy_compact_list(
        base.get("source_class_recovery_trigger_fields")
    )
    for field in (
        "answer_contract_fulfillment_handoff",
        "answer_contract_source_class_gap",
    ):
        if field not in trigger_fields:
            trigger_fields.append(field)

    reason_code = _answer_contract_gap_reason(added_gaps)
    reason = (
        f"{reason_code}:{','.join(added_gaps)}"
        if reason_code is not None
        else base.get("source_class_recovery_reason")
    )

    base.update(
        {
            "source_class_recovery_recommended": bool(missing),
            "source_class_recovery_shadow_mode": True,
            "missing_expected_source_classes": missing,
            "source_class_recovery_reason": reason,
            "source_class_recovery_queries": recovery_queries,
            "source_class_recovery_query_count": len(recovery_queries),
            "source_class_recovery_trigger_fields": trigger_fields,
        }
    )
    if official_domains:
        base["source_class_recovery_official_domains"] = official_domains
        base["source_class_recovery_domain_constraint_source"] = (
            "official_source_recovery_lane"
        )
    else:
        base.pop("source_class_recovery_official_domains", None)
        base.pop("source_class_recovery_domain_constraint_source", None)
    return base


def _candidate_v2_bool(value: Any) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _candidate_v2_count(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _candidate_v2_class_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed = set(SOURCE_CLASS_OBSERVABILITY_BUCKETS) - {"none"}
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item in allowed:
            _append_unique(out, item)
    return out


def _candidate_v2_status_by_class(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    allowed_classes = set(SOURCE_CLASS_OBSERVABILITY_BUCKETS) - {"none"}
    allowed_statuses = set(SOURCE_CLASS_SATISFACTION_STATUSES)
    out: dict[str, str] = {}
    for bucket in SOURCE_CLASS_OBSERVABILITY_BUCKETS:
        if bucket == "none" or bucket not in value:
            continue
        status = value.get(bucket)
        if isinstance(status, str) and status in allowed_statuses:
            out[bucket] = status
    for raw_bucket, raw_status in value.items():
        if not (
            isinstance(raw_bucket, str)
            and raw_bucket in allowed_classes
            and raw_bucket not in out
            and isinstance(raw_status, str)
            and raw_status in allowed_statuses
        ):
            continue
        out[raw_bucket] = raw_status
    return out


def _candidate_v2_order_classes(values: Iterable[str]) -> list[str]:
    present = {
        value
        for value in values
        if value in set(SOURCE_CLASS_OBSERVABILITY_BUCKETS)
    }
    return [
        bucket
        for bucket in SOURCE_CLASS_OBSERVABILITY_BUCKETS
        if bucket != "none" and bucket in present
    ]


def _candidate_v2_append_allowed(
    target: list[str],
    value: str,
    allowed: tuple[str, ...],
) -> None:
    if value in allowed:
        _append_unique(target, value)


def _candidate_v2_budget_context(trace: Mapping[str, Any]) -> str:
    payload = trace.get("retrieval_budget_pressure_shadow")
    if not isinstance(payload, Mapping):
        return "unknown"
    hard_budget = payload.get("hard_mode_budget")
    if not isinstance(hard_budget, Mapping):
        return "unknown"
    bucket = hard_budget.get("budget_pressure_bucket")
    if (
        isinstance(bucket, str)
        and bucket in SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BUDGET_CONTEXTS
    ):
        return bucket
    return "unknown"


def _candidate_v2_has_active_budget_blocker(trace: Mapping[str, Any]) -> bool:
    blockers = trace.get("active_source_class_recovery_blockers")
    if isinstance(blockers, list) and "blocked_by_iteration_budget" in blockers:
        return True
    return trace.get("active_source_class_recovery_skip_reason") == (
        "blocked_by_iteration_budget"
    )


def _candidate_v2_has_fast_policy_block(trace: Mapping[str, Any]) -> bool:
    blockers = trace.get("weak_corpus_recovery_blockers")
    return isinstance(blockers, list) and "max_iterations_1" in blockers


def _candidate_v2_has_unsupported_retrieval_blocker(
    trace: Mapping[str, Any],
) -> bool:
    blockers = trace.get("active_source_class_recovery_blockers")
    if not isinstance(blockers, list):
        blockers = []
    blocker_set = {item for item in blockers if isinstance(item, str)}
    return bool(
        blocker_set
        & {
            "blocked_by_provider_policy_change_required",
            "blocked_by_search_depth_escalation_required",
            "blocked_by_retrieve_to_anchor_recommendation",
        }
    )


def build_source_class_recovery_candidate_v2(
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    """Build shadow-only candidate-v2 telemetry from existing trace facts."""
    status_by_class = _candidate_v2_status_by_class(
        trace.get("source_class_satisfaction_status")
    )
    gap_classes = _candidate_v2_class_list(trace.get("source_class_gap_candidates"))
    for bucket in gap_classes:
        status_by_class.setdefault(bucket, "unsatisfied")

    expected_classes = _candidate_v2_order_classes(status_by_class.keys())
    underfire = _candidate_v2_bool(trace.get("source_class_underfire_shadow")) is True
    candidate_classes = _candidate_v2_order_classes(
        bucket
        for bucket in expected_classes + gap_classes
        if status_by_class.get(bucket) != "satisfied_strong"
    )
    all_expected_strong = bool(expected_classes) and all(
        status_by_class.get(bucket) == "satisfied_strong"
        for bucket in expected_classes
    )
    candidate = bool(candidate_classes and (underfire or not all_expected_strong))

    reasons: list[str] = []
    if candidate:
        statuses = {status_by_class.get(bucket) for bucket in candidate_classes}
        if "unsatisfied" in statuses:
            _candidate_v2_append_allowed(
                reasons,
                "expected_source_class_unsatisfied",
                SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS,
            )
        if "expected_but_only_secondary" in statuses:
            _candidate_v2_append_allowed(
                reasons,
                "expected_source_class_secondary_only",
                SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS,
            )
        if "satisfied_weak" in statuses:
            _candidate_v2_append_allowed(
                reasons,
                "expected_source_class_weakly_satisfied",
                SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS,
            )

        class_count_reasons = (
            (
                "official_current_rules",
                "final_official_source_count",
                "final_answer_lacks_official_source",
            ),
            (
                "primary_source_documents",
                "final_primary_source_count",
                "final_answer_lacks_primary_source",
            ),
            (
                "archival_primary_text",
                "final_archival_source_count",
                "final_answer_lacks_archival_source",
            ),
            (
                "legal_or_regulatory_text",
                "final_legal_or_regulatory_source_count",
                "final_answer_lacks_legal_or_regulatory_source",
            ),
        )
        for bucket, count_field, reason in class_count_reasons:
            if (
                bucket in candidate_classes
                and _candidate_v2_count(trace.get(count_field)) == 0
            ):
                _candidate_v2_append_allowed(
                    reasons,
                    reason,
                    SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS,
                )

        answer_class = str(trace.get("answer_class") or "")
        if trace.get("evidence_sufficient") is False or answer_class in {
            "partial_answer",
            "no_evidence_found",
            "off_topic_retrieval",
        }:
            _candidate_v2_append_allowed(
                reasons,
                "answer_class_partial_or_no_evidence",
                SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS,
            )
        if str(trace.get("corpus_state") or "") == "OFF_TOPIC":
            _candidate_v2_append_allowed(
                reasons,
                "corpus_off_topic_with_expected_source_class",
                SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS,
            )

    budget_context = _candidate_v2_budget_context(trace)
    if candidate and budget_context == "at_cap":
        _candidate_v2_append_allowed(
            reasons,
            "at_cap_with_source_class_underfire",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS,
        )
    elif candidate and budget_context == "exhausted":
        _candidate_v2_append_allowed(
            reasons,
            "budget_exhausted_with_source_class_underfire",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_REASONS,
        )

    weak_corpus_owns_path = (
        trace.get("weak_corpus_recovery_decision") == "run_weak_corpus_recovery"
    )
    active_budget_blocked = _candidate_v2_has_active_budget_blocker(trace)
    blocked_by_weak_corpus = bool(candidate and weak_corpus_owns_path)
    blocked_by_budget = candidate and (
        budget_context in {"exhausted", "at_cap"} or active_budget_blocked
    )

    blockers: list[str] = []
    if not expected_classes and not gap_classes:
        _candidate_v2_append_allowed(
            blockers,
            "no_expected_source_class",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
        )
    elif all_expected_strong and not candidate:
        _candidate_v2_append_allowed(
            blockers,
            "all_expected_source_classes_satisfied_strong",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
        )
    if blocked_by_weak_corpus:
        _candidate_v2_append_allowed(
            blockers,
            "weak_corpus_recovery_owns_path",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
        )
    if trace.get("active_source_class_recovery_used") is True:
        _candidate_v2_append_allowed(
            blockers,
            "active_recovery_already_used",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
        )
    query_count = (
        min(len(candidate_classes), _MAX_SHADOW_CLASS_INTENT_QUERIES)
        if candidate
        else 0
    )
    if candidate and query_count <= 0:
        _candidate_v2_append_allowed(
            blockers,
            "no_recovery_query_available",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
        )
    if candidate and budget_context == "exhausted":
        _candidate_v2_append_allowed(
            blockers,
            "budget_hard_exhausted",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
        )
    if candidate and _candidate_v2_has_fast_policy_block(trace):
        _candidate_v2_append_allowed(
            blockers,
            "fast_mode_policy_block",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
        )
    if candidate and active_budget_blocked:
        _candidate_v2_append_allowed(
            blockers,
            "existing_active_recovery_blocked_by_budget",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
        )
    if candidate and _candidate_v2_has_unsupported_retrieval_blocker(trace):
        _candidate_v2_append_allowed(
            blockers,
            "unsupported_off_domain_retrieval",
            SOURCE_CLASS_RECOVERY_CANDIDATE_V2_BLOCKERS,
        )

    return {
        "schema_version": SOURCE_CLASS_RECOVERY_CANDIDATE_V2_SCHEMA_VERSION,
        "shadow_mode": True,
        "source_class_recovery_candidate_v2_shadow": candidate,
        "source_class_recovery_candidate_v2_classes": candidate_classes,
        "source_class_recovery_candidate_v2_reasons": reasons,
        "source_class_recovery_candidate_v2_blockers": blockers,
        "source_class_recovery_candidate_v2_status_by_class": {
            bucket: status_by_class[bucket] for bucket in expected_classes
        },
        "source_class_recovery_candidate_v2_query_count": query_count,
        "source_class_recovery_candidate_v2_query_source": (
            "class_intent_catalog" if candidate else "none"
        ),
        "source_class_recovery_candidate_v2_budget_context": budget_context,
        "source_class_recovery_candidate_v2_blocked_by_weak_corpus": (
            blocked_by_weak_corpus
        ),
        "source_class_recovery_candidate_v2_blocked_by_budget": blocked_by_budget,
    }


def build_source_class_recovery_recommendation(
    *,
    query: str,
    current_date: str,
    intent: str,
    report_type: str,
    query_type: str,
    core_topic: str,
    primary_entity: str,
    anchor_packet: dict[str, Any] | None,
    source_tier_counts: dict[str, int],
    source_domain_counts: dict[str, int],
    top_source_domains: list[dict[str, Any]],
    official_evidence_found: bool,
) -> dict[str, Any]:
    """Build a source-class recovery recommendation without executing retrieval."""
    del current_date
    text = _combined_text(
        query=query,
        intent=intent,
        report_type=report_type,
        query_type=query_type,
        core_topic=core_topic,
        primary_entity=primary_entity,
        anchor_packet=anchor_packet,
    )
    expected, expectation_triggers = _expected_source_classes(text=text, anchor_packet=anchor_packet)
    domains = _domain_entries(source_domain_counts, top_source_domains)

    missing = [
        bucket
        for bucket in expected
        if bucket != "none"
        and not _source_class_present(
            bucket,
            source_tier_counts=source_tier_counts,
            domains=domains,
            official_evidence_found=official_evidence_found,
        )
    ]

    subject = _query_subject(
        primary_entity=primary_entity,
        core_topic=core_topic,
        query=query,
    )
    context_text = " ".join(
        part
        for part in (query, core_topic, primary_entity)
        if str(part or "").strip()
    )
    query_candidates: list[str] = []
    for bucket in missing:
        query_candidates.extend(
            _candidate_queries_for_bucket(
                bucket,
                subject,
                context_text=context_text,
            )
        )
    recovery_queries = _dedupe_cap_queries(query_candidates)
    official_domains = build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=missing,
        query=query,
        core_topic=core_topic,
        primary_entity=primary_entity,
        recovery_queries=recovery_queries,
    )

    trigger_fields: list[str] = []
    if missing:
        trigger_fields.extend(expectation_triggers)
        for field in ("source_tier_counts", "source_domain_counts", "official_evidence_found"):
            if field not in trigger_fields:
                trigger_fields.append(field)

    reason = None
    if missing:
        reason = "missing_expected_source_class:" + ",".join(missing)

    payload = {
        "source_class_recovery_recommended": bool(missing),
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": missing,
        "source_class_recovery_reason": reason,
        "source_class_recovery_queries": recovery_queries,
        "source_class_recovery_query_count": len(recovery_queries),
        "source_class_recovery_trigger_fields": trigger_fields,
    }
    if official_domains:
        payload["source_class_recovery_official_domains"] = official_domains
        payload["source_class_recovery_domain_constraint_source"] = (
            "official_source_recovery_lane"
        )
    return payload
