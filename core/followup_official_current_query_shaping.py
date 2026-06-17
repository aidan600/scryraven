"""Offline provider-neutral official/current query-shaping diagnostics.

The helper in this module shapes bounded query variants for later diagnostic
use. It does not call providers, fetch/read pages, inspect private payloads,
or change product query generation.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from core.followup_deliberation import ProviderJobKind, clean_text, clean_token

DISCOVERY_UNCONSTRAINED = "discovery_unconstrained"
SOFT_AUTHORITY_HINT = "soft_authority_hint"
HARD_CORRIDOR_DOMAIN_CONSTRAINED = "hard_corridor_domain_constrained"

OFFICIAL_CURRENT_ARTIFACT_DISCOVERY = "official_current_artifact_discovery"
SCOUT_HYPOTHESIS_DISAMBIGUATION = "scout_hypothesis_disambiguation"

ACQUISITION_MODES = frozenset(
    {
        DISCOVERY_UNCONSTRAINED,
        SOFT_AUTHORITY_HINT,
        HARD_CORRIDOR_DOMAIN_CONSTRAINED,
    }
)

SCOUT_JOB_KINDS = frozenset(
    {
        ProviderJobKind.SCOUT_DISAMBIGUATION.value,
        ProviderJobKind.BRIDGE_HINT_DISCOVERY.value,
    }
)

OFFICIAL_CURRENT_JOB_KINDS = frozenset(
    {
        ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        ProviderJobKind.LEGAL_CURRENT_PRIMARY_ACQUISITION.value,
        ProviderJobKind.CANONICAL_DOC_ACQUISITION.value,
    }
)

SOURCE_CLASS_ARTIFACT_TERMS = (
    "official",
    "current",
    "notice",
    "announcement",
    "newsroom",
    "bulletin",
    "rule",
    "guidance",
    "form instructions",
    "fee schedule",
    "filing fee",
    "final rule",
    "release",
    "table",
)

PHRASE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bstandard\s+mileage\s+rates?\b", "standard mileage rates"),
    (r"\bbusiness\s+use\b", "business use"),
    (r"\bmileage\s+rate\b", "mileage rate"),
    (r"\bfiling\s+fee\b", "filing fee"),
    (r"\bfee\s+schedule\b", "fee schedule"),
    (r"\bform\s+[a-z0-9-]+\b", "form"),
    (r"\bfinal\s+rule\b", "final rule"),
    (r"\bfederal\s+register\b", "federal register"),
    (r"\bsafety\s+alert\b", "safety alert"),
    (r"\brecall\s+notice\b", "recall notice"),
    (r"\benforcement\s+report\b", "enforcement report"),
    (r"\bcompany\s+announcement\b", "company announcement"),
    (r"\bpatch\s+notes?\b", "patch notes"),
)

TOPIC_TERMS: tuple[tuple[str, str], ...] = (
    (r"\bcar\b", "car"),
    (r"\bvehicle\b", "vehicle"),
    (r"\bmileage\b", "mileage"),
    (r"\breimbursement\b", "reimbursement"),
    (r"\bfee\b", "fee"),
    (r"\bform\b", "form"),
    (r"\bfiling\b", "filing"),
    (r"\brule\b", "rule"),
    (r"\bguidance\b", "guidance"),
    (r"\bdisclosure\b", "disclosure"),
    (r"\brecall\b", "recall"),
    (r"\bsafety\b", "safety"),
    (r"\bpatch\b", "patch"),
)


def build_official_current_query_shaping_diagnostics(
    *,
    authorized_query: str,
    provider_job_kind: str,
    acquisition_mode: str = DISCOVERY_UNCONSTRAINED,
    source_obligation_hints: Iterable[str] | None = None,
    bridge_hint_terms: Iterable[str] | None = None,
    admitted_context_terms: Iterable[str] | None = None,
    canonical_subject: str | None = None,
    canonical_subject_status: str | None = None,
    max_query_variants: int = 4,
    domain_constraints: Iterable[str] | None = None,
    include_domains: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build a sanitized offline query-shaping diagnostic packet.

    Discovery-unconstrained mode refuses source-specific domain constraints.
    Ambiguous inputs without an explicit canonical subject produce scout
    hypotheses instead of a resolved official/current subject.
    """

    query = clean_text(authorized_query, limit=500) or ""
    job_kind = _provider_job_kind(provider_job_kind)
    mode = _acquisition_mode(acquisition_mode)
    max_variants = _bounded_variant_count(max_query_variants)
    constraints = _clean_domain_tuple(domain_constraints)
    includes = _clean_domain_tuple(include_domains)
    constraint_domains = tuple(dict.fromkeys((*constraints, *includes)))
    domain_constraint_status = _domain_constraint_status(
        acquisition_mode=mode,
        constraint_domains=constraint_domains,
    )
    invalid_domain_constraint = domain_constraint_status.startswith("invalid_")
    canonical_status = _canonical_subject_status(
        canonical_subject_status=canonical_subject_status,
        canonical_subject=canonical_subject,
    )

    if invalid_domain_constraint:
        return _base_packet(
            query=query,
            acquisition_mode=mode,
            provider_job_kind=job_kind,
            query_shape_mode=OFFICIAL_CURRENT_ARTIFACT_DISCOVERY,
            canonical_subject_status=canonical_status,
            domain_constraint_status=domain_constraint_status,
            query_variants=[],
            shaping_reasons=[
                "discovery_unconstrained_refused_source_specific_domain_constraint"
            ],
            preserved_target_terms=[],
            artifact_terms_used=[],
            source_obligation_hints=source_obligation_hints,
            bridge_hint_terms=bridge_hint_terms,
            admitted_context_terms=admitted_context_terms,
            candidate_interpretations=[],
        )

    if _should_build_scout_packet(
        query=query,
        provider_job_kind=job_kind,
        canonical_subject=canonical_subject,
        canonical_subject_status=canonical_status,
    ):
        hypotheses = _candidate_interpretations(query)
        probes = _query_probes_for_hypotheses(query, hypotheses, max_variants)
        return _base_packet(
            query=query,
            acquisition_mode=mode,
            provider_job_kind=job_kind,
            query_shape_mode=SCOUT_HYPOTHESIS_DISAMBIGUATION,
            canonical_subject_status="unresolved",
            domain_constraint_status=domain_constraint_status,
            query_variants=probes,
            shaping_reasons=[
                "ambiguous_input_requires_hypothesis_first_scout",
                "canonical_subject_not_promoted_without_evidence_or_caller_resolution",
            ],
            preserved_target_terms=_preserved_terms(query),
            artifact_terms_used=[],
            source_obligation_hints=source_obligation_hints,
            bridge_hint_terms=bridge_hint_terms,
            admitted_context_terms=admitted_context_terms,
            candidate_interpretations=hypotheses,
        )

    subject_text = clean_text(canonical_subject, limit=300) or query
    preserved_terms = _preserved_terms(subject_text)
    artifact_terms = _artifact_terms(
        subject_text,
        source_obligation_hints=source_obligation_hints,
        bridge_hint_terms=bridge_hint_terms,
    )
    variants = _official_current_variants(
        preserved_terms=preserved_terms,
        artifact_terms=artifact_terms,
        max_query_variants=max_variants,
    )
    return _base_packet(
        query=query,
        acquisition_mode=mode,
        provider_job_kind=job_kind,
        query_shape_mode=OFFICIAL_CURRENT_ARTIFACT_DISCOVERY,
        canonical_subject_status=canonical_status,
        domain_constraint_status=domain_constraint_status,
        query_variants=variants,
        shaping_reasons=[
            "official_current_query_shaping_asks_for_source_artifacts",
            "target_terms_preserved_without_source_domain_corridor",
            "artifact_terms_are_source_class_terms_not_provider_filters",
        ],
        preserved_target_terms=preserved_terms,
        artifact_terms_used=artifact_terms[: max(1, min(len(artifact_terms), 8))],
        source_obligation_hints=source_obligation_hints,
        bridge_hint_terms=bridge_hint_terms,
        admitted_context_terms=admitted_context_terms,
        candidate_interpretations=[],
    )


def _base_packet(
    *,
    query: str,
    acquisition_mode: str,
    provider_job_kind: str,
    query_shape_mode: str,
    canonical_subject_status: str,
    domain_constraint_status: str,
    query_variants: list[str],
    shaping_reasons: list[str],
    preserved_target_terms: list[str],
    artifact_terms_used: list[str],
    source_obligation_hints: Iterable[str] | None,
    bridge_hint_terms: Iterable[str] | None,
    admitted_context_terms: Iterable[str] | None,
    candidate_interpretations: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "ag96i3f_provider_neutral_query_shaping_v1",
        "record_type": "provider_neutral_official_current_query_shaping_diagnostics",
        "owner": "FollowupOfficialCurrentQueryShapingDiagnostics",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "original_authorized_query": query,
        "acquisition_mode": acquisition_mode,
        "provider_job_kind": provider_job_kind,
        "query_shape_mode": query_shape_mode,
        "query_variant_count": len(query_variants),
        "query_variants": query_variants,
        "shaping_reasons": [reason for reason in shaping_reasons if reason],
        "preserved_target_terms": preserved_target_terms,
        "artifact_terms_used": artifact_terms_used,
        "source_obligation_hints": _clean_hint_list(source_obligation_hints),
        "bridge_hint_derived_terms": _clean_hint_list(bridge_hint_terms),
        "admitted_context_terms": _clean_hint_list(admitted_context_terms),
        "candidate_interpretations": candidate_interpretations,
        "prohibited_constraints": {
            "include_domains_used": False,
            "site_filters_used": False,
            "source_domain_filters_used": False,
            "provider_specific_syntax_used": False,
            "hardcoded_source_resolver_used": False,
            "answer_value_invented": False,
        },
        "domain_constraint_status": domain_constraint_status,
        "canonical_subject_status": canonical_subject_status,
        "live_call_authorized": False,
        "provider_called": False,
        "fetch_read_invoked": False,
        "model_called": False,
        "author_executor_invoked": False,
        "evidence_boundary": {
            "query_variants_are_final_evidence": False,
            "query_variants_are_citation_eligible": False,
            "final_evidence_requires_later_fetch_read_admission": True,
        },
        "raw_private_payload_redaction_posture": _redaction_posture(),
    }


def _official_current_variants(
    *,
    preserved_terms: list[str],
    artifact_terms: list[str],
    max_query_variants: int,
) -> list[str]:
    anchor = _join_terms(preserved_terms)
    if not anchor:
        anchor = "official current source artifact"
    artifact_pairs = [
        artifact_terms[:2],
        artifact_terms[2:4],
        artifact_terms[4:6],
        artifact_terms[6:8],
    ]
    variants: list[str] = []
    for pair in artifact_pairs:
        terms = [anchor, *pair]
        variant = _sanitize_query_variant(" ".join(term for term in terms if term))
        if variant and variant not in variants:
            variants.append(variant)
        if len(variants) >= max_query_variants:
            break
    if not variants:
        variants.append(_sanitize_query_variant(f"{anchor} official current notice"))
    return variants[:max_query_variants]


def _artifact_terms(
    text: str,
    *,
    source_obligation_hints: Iterable[str] | None,
    bridge_hint_terms: Iterable[str] | None,
) -> list[str]:
    folded = text.casefold()
    terms = ["official", "current"]
    if "disclosure" in folded or "securities" in folded:
        terms.extend(["final rule", "release", "filing", "disclosure"])
    if "mileage" in folded or "reimbursement" in folded:
        terms.extend(["notice", "announcement", "newsroom", "table", "guidance"])
    if "fee" in folded or "form" in folded or "filing" in folded:
        terms.extend(["fee schedule", "form", "filing fee", "instructions"])
    if "rule" in folded or "regulation" in folded or "standard" in folded:
        terms.extend(["rule", "guidance", "federal register", "final rule"])
    if "recall" in folded or "safety" in folded:
        terms.extend(
            [
                "recall notice",
                "safety alert",
                "enforcement report",
                "company announcement",
            ]
        )
    if "patch" in folded or "release" in folded:
        terms.extend(["patch notes", "release notes", "announcement"])
    terms.extend(_clean_hint_list(source_obligation_hints))
    terms.extend(_clean_hint_list(bridge_hint_terms))
    terms.extend(SOURCE_CLASS_ARTIFACT_TERMS)
    return list(dict.fromkeys(term for term in terms if not _looks_like_domain(term)))


def _preserved_terms(text: str) -> list[str]:
    cleaned = clean_text(text, limit=300) or ""
    folded = cleaned.casefold()
    terms: list[str] = []
    terms.extend(match.group(0) for match in re.finditer(r"\b[A-Z]{2,6}\b", cleaned))
    terms.extend(match.group(0) for match in re.finditer(r"\b20\d{2}\b", cleaned))
    title_words = [
        word
        for word in re.findall(r"\b[A-Z][a-z][A-Za-z0-9-]*\b", cleaned)
        if word.casefold() not in _STOPWORDS
    ]
    terms.extend(title_words[:4])
    for pattern, label in PHRASE_PATTERNS:
        if re.search(pattern, folded):
            terms.append(label)
    for pattern, label in TOPIC_TERMS:
        if re.search(pattern, folded):
            terms.append(label)
    if not terms:
        words = [
            word
            for word in re.findall(r"[A-Za-z0-9]+", cleaned)[:8]
            if word.casefold() not in _STOPWORDS
        ]
        terms.extend(words)
    return list(dict.fromkeys(_strip_domain_like_terms(terms)))


def _should_build_scout_packet(
    *,
    query: str,
    provider_job_kind: str,
    canonical_subject: str | None,
    canonical_subject_status: str,
) -> bool:
    if canonical_subject and canonical_subject_status == "resolved_by_caller":
        return False
    if provider_job_kind in SCOUT_JOB_KINDS:
        return True
    if provider_job_kind in OFFICIAL_CURRENT_JOB_KINDS and _looks_scoped(query):
        return False
    return _looks_ambiguous(query)


def _looks_scoped(query: str) -> bool:
    folded = query.casefold()
    has_year = bool(re.search(r"\b20\d{2}\b", query))
    has_uppercase_entity = bool(re.search(r"\b[A-Z]{2,6}\b", query))
    has_official_current_language = any(
        term in folded for term in ("official", "current", "rule", "fee", "rate")
    )
    return has_uppercase_entity and (has_year or has_official_current_language)


def _looks_ambiguous(query: str) -> bool:
    folded = query.casefold()
    if re.search(r"\bpoe\b", folded):
        return True
    vague_terms = ("thing", "funny", "latest", "patch")
    if any(term in folded for term in vague_terms) and not _looks_scoped(query):
        return True
    if "reimbursement" in folded and "driving" in folded and not _looks_scoped(query):
        return True
    return False


def _candidate_interpretations(query: str) -> list[str]:
    folded = query.casefold()
    if re.search(r"\bpoe\b", folded):
        return [
            "Path of Exile game patch",
            "Power over Ethernet firmware or standard patch",
            "Pillars of Eternity game patch",
            "port of entry policy update",
            "proof of eligibility policy change",
        ]
    if "reimbursement" in folded or "driving" in folded:
        return [
            "employer mileage reimbursement",
            "tax mileage deduction",
            "government standard mileage rate",
            "vehicle reimbursement rate",
            "business expense policy",
        ]
    return [
        "official current artifact for the stated topic",
        "policy or rule update",
        "agency or organization announcement",
        "form instructions or guidance",
    ]


def _query_probes_for_hypotheses(
    query: str,
    hypotheses: list[str],
    max_query_variants: int,
) -> list[str]:
    folded = query.casefold()
    if re.search(r"\bpoe\b", folded):
        probes = [
            "Path of Exile latest patch notes",
            "Power over Ethernet firmware patch",
            "Pillars of Eternity latest patch notes",
            "port of entry policy update",
        ]
    elif "reimbursement" in folded or "driving" in folded:
        probes = [
            "driving reimbursement mileage rate",
            "business driving reimbursement standard mileage rate",
            "employer mileage reimbursement accountable plan",
            "tax mileage deduction business driving",
            "vehicle reimbursement rate business use",
        ]
    else:
        probes = [f"{item} official current" for item in hypotheses]
    return [_sanitize_query_variant(item) for item in probes[:max_query_variants]]


def _domain_constraint_status(
    *,
    acquisition_mode: str,
    constraint_domains: tuple[str, ...],
) -> str:
    if acquisition_mode == DISCOVERY_UNCONSTRAINED and constraint_domains:
        return "invalid_unearned_domain_constraint"
    if acquisition_mode == HARD_CORRIDOR_DOMAIN_CONSTRAINED and constraint_domains:
        return "hard_corridor_not_query_shaping_mode"
    if constraint_domains:
        return "soft_hint_not_provider_filter"
    return "not_present"


def _canonical_subject_status(
    *,
    canonical_subject_status: str | None,
    canonical_subject: str | None,
) -> str:
    cleaned_status = clean_token(canonical_subject_status, limit=120)
    if canonical_subject and cleaned_status in {"resolved", "resolved_by_caller"}:
        return "resolved_by_caller"
    if canonical_subject:
        return "resolved_by_caller"
    if cleaned_status == "unresolved":
        return "unresolved"
    return "scoped_from_authorized_query"


def _clean_hint_list(value: Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    cleaned: list[str] = []
    for item in value:
        text = clean_text(item, limit=80)
        if text and not _looks_like_domain(text) and not _contains_provider_syntax(text):
            cleaned.append(text)
    return list(dict.fromkeys(cleaned))


def _clean_domain_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = [value]
    else:
        try:
            items = list(value)
        except TypeError:
            items = []
    cleaned = []
    for item in items:
        domain = clean_text(item, limit=160)
        if domain:
            cleaned.append(domain.casefold())
    return tuple(dict.fromkeys(cleaned))


def _provider_job_kind(value: Any) -> str:
    cleaned = clean_token(value, limit=120)
    valid = {item.value for item in ProviderJobKind}
    if cleaned in valid:
        return cleaned
    return ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value


def _acquisition_mode(value: Any) -> str:
    cleaned = clean_token(value, limit=120)
    return cleaned if cleaned in ACQUISITION_MODES else DISCOVERY_UNCONSTRAINED


def _bounded_variant_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 4
    return min(6, max(1, count))


def _join_terms(terms: list[str]) -> str:
    return " ".join(dict.fromkeys(term for term in terms if term))


def _sanitize_query_variant(value: str) -> str:
    text = clean_text(value, limit=220) or ""
    terms = _strip_domain_like_terms(text.split())
    text = " ".join(terms)
    text = re.sub(r"\bsite:\S+", "", text, flags=re.IGNORECASE)
    text = text.replace("includeDomains", "")
    return clean_text(text, limit=220) or ""


def _strip_domain_like_terms(terms: Iterable[str]) -> list[str]:
    return [term for term in terms if not _looks_like_domain(term)]


def _looks_like_domain(value: str) -> bool:
    return bool(re.search(r"\b[a-z0-9-]+\.(gov|com|org|edu|net|mil)\b", value.casefold()))


def _contains_provider_syntax(value: str) -> bool:
    folded = value.casefold()
    return "site:" in folded or "includedomains" in folded


def _redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_query_variants_only": True,
        "raw_provider_payloads_retained": False,
        "raw_provider_payload_retained": False,
        "raw_snippets_retained": False,
        "raw_page_text_retained": False,
        "raw_text_retained": False,
        "raw_prompts_retained": False,
        "raw_prompt_retained": False,
        "model_outputs_retained": False,
        "model_response_text_retained": False,
        "api_keys_retained": False,
        "env_values_retained": False,
        "db_rows_retained": False,
        "cache_rows_retained": False,
        "private_logs_retained": False,
        "full_traces_retained": False,
        "full_trace_retained": False,
    }


_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "for",
        "find",
        "is",
        "of",
        "the",
        "to",
        "what",
        "which",
        "with",
    }
)


__all__ = [
    "DISCOVERY_UNCONSTRAINED",
    "OFFICIAL_CURRENT_ARTIFACT_DISCOVERY",
    "SCOUT_HYPOTHESIS_DISAMBIGUATION",
    "build_official_current_query_shaping_diagnostics",
]
