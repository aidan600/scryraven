"""Analyst-owned source-authority posture packet contract.

This module is vocabulary/schema/contract only. It validates an Analyst-declared
source-authority posture; it does not rank sources, score authority, apply
domain allow/block lists, classify arbitrary queries, call providers, call
models, fetch/read content, run Scrutineer, or wire D-prime/FAP/Author behavior.
"""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping, Sequence

SOURCE_AUTHORITY_POSTURE_PHASE = "ANALYST-SOURCE-AUTHORITY-POSTURE-PACKET-01"
SOURCE_AUTHORITY_POSTURE_SCHEMA_VERSION = "source_authority_posture_packet_v1"
SOURCE_AUTHORITY_POSTURE_OWNER_ANALYST = "Analyst"

SOURCE_AUTHORITY_RECOMMENDED_USE_AUTHORITY = "authority"
SOURCE_AUTHORITY_RECOMMENDED_USE_CORROBORATION = "corroboration"
SOURCE_AUTHORITY_RECOMMENDED_USE_CONTEXT = "context"
SOURCE_AUTHORITY_RECOMMENDED_USE_DIRECTIONALITY = "directionality"
SOURCE_AUTHORITY_RECOMMENDED_USE_IGNORE = "ignore"

SOURCE_AUTHORITY_RECOMMENDED_USES = (
    SOURCE_AUTHORITY_RECOMMENDED_USE_AUTHORITY,
    SOURCE_AUTHORITY_RECOMMENDED_USE_CORROBORATION,
    SOURCE_AUTHORITY_RECOMMENDED_USE_CONTEXT,
    SOURCE_AUTHORITY_RECOMMENDED_USE_DIRECTIONALITY,
    SOURCE_AUTHORITY_RECOMMENDED_USE_IGNORE,
)

SOURCE_AUTHORITY_SOURCE_CLASS_OFFICIAL_OR_SOURCE_OF_RECORD = (
    "official_or_source_of_record"
)
SOURCE_AUTHORITY_SOURCE_CLASS_GOVERNMENT_OR_PUBLIC_AGENCY = (
    "government_or_public_agency"
)
SOURCE_AUTHORITY_SOURCE_CLASS_LEGAL_OR_REGULATORY = "legal_or_regulatory"
SOURCE_AUTHORITY_SOURCE_CLASS_ACADEMIC_OR_RESEARCH = "academic_or_research"
SOURCE_AUTHORITY_SOURCE_CLASS_NEWS_OR_REPORTING = "news_or_reporting"
SOURCE_AUTHORITY_SOURCE_CLASS_VENDOR_OR_PRODUCT_DOCUMENTATION = (
    "vendor_or_product_documentation"
)
SOURCE_AUTHORITY_SOURCE_CLASS_DATA_TABLE_OR_STATISTICAL_SOURCE = (
    "data_table_or_statistical_source"
)
SOURCE_AUTHORITY_SOURCE_CLASS_SOCIAL_OR_FORUM_DISCUSSION = (
    "social_or_forum_discussion"
)
SOURCE_AUTHORITY_SOURCE_CLASS_USER_REVIEW = "user_review"
SOURCE_AUTHORITY_SOURCE_CLASS_UNKNOWN_OR_UNCLASSIFIED = "unknown_or_unclassified"

SOURCE_AUTHORITY_SOURCE_CLASSES = (
    SOURCE_AUTHORITY_SOURCE_CLASS_OFFICIAL_OR_SOURCE_OF_RECORD,
    SOURCE_AUTHORITY_SOURCE_CLASS_GOVERNMENT_OR_PUBLIC_AGENCY,
    SOURCE_AUTHORITY_SOURCE_CLASS_LEGAL_OR_REGULATORY,
    SOURCE_AUTHORITY_SOURCE_CLASS_ACADEMIC_OR_RESEARCH,
    SOURCE_AUTHORITY_SOURCE_CLASS_NEWS_OR_REPORTING,
    SOURCE_AUTHORITY_SOURCE_CLASS_VENDOR_OR_PRODUCT_DOCUMENTATION,
    SOURCE_AUTHORITY_SOURCE_CLASS_DATA_TABLE_OR_STATISTICAL_SOURCE,
    SOURCE_AUTHORITY_SOURCE_CLASS_SOCIAL_OR_FORUM_DISCUSSION,
    SOURCE_AUTHORITY_SOURCE_CLASS_USER_REVIEW,
    SOURCE_AUTHORITY_SOURCE_CLASS_UNKNOWN_OR_UNCLASSIFIED,
)

SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_NONE = "none"
SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_FUTURE = "future"
SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_VALUES = (
    SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_NONE,
    SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_FUTURE,
)

SOURCE_AUTHORITY_REQUIRED_PACKET_FIELDS = (
    "schema_version",
    "phase",
    "owner",
    "source_authority_posture_id",
    "source_class",
    "issuer_or_source_owner",
    "document_type",
    "primary_derivative_posture",
    "officialness_canonicality_posture",
    "directness_to_answer_component",
    "recency_currentness",
    "publication_date",
    "revision_date",
    "observed_date",
    "scope_match",
    "claim_specificity",
    "source_contains_exact_claim",
    "conflict_qualification_posture",
    "recommended_source_use",
    "recommended_source_use_rationale",
    "recommended_source_use_supporting_fields",
    "limitations",
    "required_caveats",
    "source_class_adapter_used",
    "analyst_rationale",
    "nonclaims",
    "raw_private_retention_flags",
    "closed_surface_flags",
    "anti_laundering_flags",
)

SOURCE_AUTHORITY_AUTHORITY_REQUIRED_SUPPORTING_FIELDS = (
    "source_class",
    "issuer_or_source_owner",
    "document_type",
    "primary_derivative_posture",
    "officialness_canonicality_posture",
    "directness_to_answer_component",
    "recency_currentness",
    "scope_match",
    "claim_specificity",
    "source_contains_exact_claim",
    "conflict_qualification_posture",
    "analyst_rationale",
)

SOURCE_AUTHORITY_SOCIAL_REVIEW_SOURCE_CLASSES = (
    SOURCE_AUTHORITY_SOURCE_CLASS_SOCIAL_OR_FORUM_DISCUSSION,
    SOURCE_AUTHORITY_SOURCE_CLASS_USER_REVIEW,
)

SOURCE_AUTHORITY_SOCIAL_REVIEW_RECOMMENDED_USES = (
    SOURCE_AUTHORITY_RECOMMENDED_USE_DIRECTIONALITY,
    SOURCE_AUTHORITY_RECOMMENDED_USE_IGNORE,
)

SOURCE_AUTHORITY_REQUIRED_NONCLAIMS = (
    "product correctness remains unclaimed",
    "recommended_source_use is Analyst-declared posture, not an algorithmic ranking",
    "source class alone does not determine recommended_source_use",
    "document type alone does not determine recommended_source_use",
    "domain membership does not determine recommended_source_use",
    "single social/forum/review item is not consensus",
    "single social/forum/review item is not reliability evidence",
    "single social/forum/review item is not authority-bearing support",
    "source-class adapters remain future work and cannot bypass Analyst",
    "query-to-relation planning remains future work",
)

SOURCE_AUTHORITY_RAW_PRIVATE_RETENTION_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_source_content_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}

SOURCE_AUTHORITY_CLOSED_SURFACE_FLAGS = {
    "query_to_relation_planning_opened": False,
    "source_class_adapter_implemented": False,
    "source_ranking_algorithm_created": False,
    "authority_score_created": False,
    "domain_allowlist_created": False,
    "domain_blocklist_created": False,
    "planner_policy_created": False,
    "scrutineer_behavior_changed": False,
    "dprime_review_behavior_changed": False,
    "fap_behavior_changed": False,
    "author_behavior_changed": False,
    "live_dogfood_behavior_changed": False,
    "provider_call_made": False,
    "model_call_made": False,
    "fetch_read_call_made": False,
    "product_correctness_claimed": False,
}

SOURCE_AUTHORITY_ANTI_LAUNDERING_FLAGS = {
    "single_item_consensus_claimed": False,
    "single_item_reliability_evidence_claimed": False,
    "single_item_authority_bearing_support_claimed": False,
    "social_review_upgraded_to_authority": False,
    "social_review_upgraded_to_consensus": False,
}

_RECOMMENDED_USE_DEFINITIONS = {
    SOURCE_AUTHORITY_RECOMMENDED_USE_AUTHORITY: (
        "Source may bear authority for the claim only when the Analyst-declared "
        "posture fields and rationale support that use."
    ),
    SOURCE_AUTHORITY_RECOMMENDED_USE_CORROBORATION: (
        "Source may support consistency but should not be treated as the source "
        "of authority."
    ),
    SOURCE_AUTHORITY_RECOMMENDED_USE_CONTEXT: (
        "Source may help explain background but should not authorize the answer "
        "component."
    ),
    SOURCE_AUTHORITY_RECOMMENDED_USE_DIRECTIONALITY: (
        "Source may indicate user experience, sentiment, or lead direction, but "
        "not factual truth or authority."
    ),
    SOURCE_AUTHORITY_RECOMMENDED_USE_IGNORE: (
        "Source should not be used for this answer component."
    ),
}

_FORBIDDEN_DECISION_MECHANIC_KEYS = frozenset(
    {
        "approved_domain",
        "approved_domains",
        "authority_score",
        "blocked_domain",
        "blocked_domains",
        "denylist",
        "domain_allowlist",
        "domain_blocklist",
        "numeric_threshold",
        "rank",
        "ranking_score",
        "score",
        "threshold",
    }
)

_RAW_PRIVATE_CONTENT_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "bounded_text",
        "cache_row",
        "cookie",
        "cookies",
        "db_row",
        "env",
        "full_prompt",
        "full_text",
        "header",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_html",
        "raw_model_response",
        "raw_page",
        "raw_page_content",
        "raw_page_text",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "raw_text",
        "secret",
        "secrets",
        "token",
        "unbounded_text",
    }
)

_AUTHORITY_CONFLICT_BLOCKERS = frozenset(
    {
        "conflicted",
        "contradicted",
        "known_conflict",
        "unresolved",
        "unresolved_conflict",
        "unknown",
    }
)


class SourceAuthorityPosturePacketError(ValueError):
    """Raised when an Analyst source-authority posture packet is invalid."""


def build_source_authority_posture_profile() -> dict[str, Any]:
    """Return the durable Analyst-owned source-authority posture profile."""

    profile = {
        "schema_version": SOURCE_AUTHORITY_POSTURE_SCHEMA_VERSION,
        "phase": SOURCE_AUTHORITY_POSTURE_PHASE,
        "owner": SOURCE_AUTHORITY_POSTURE_OWNER_ANALYST,
        "profile_id": "source-authority-posture-profile:v1",
        "profile_is_contract_only": True,
        "source_authority_is_analyst_owned": True,
        "source_authority_is_not_domain_allowlist": True,
        "source_authority_is_not_source_ranking": True,
        "source_authority_is_not_numeric_scoring": True,
        "planner_may_reference_requirements_later": True,
        "planner_must_not_invent_source_authority_policy": True,
        "scrutineer_role": (
            "Scrutineer audits Analyst posture; it does not perform first-pass "
            "source synthesis."
        ),
        "evidence_class_adapter_extension_point": {
            "allowed_values": list(SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_VALUES),
            "current_value": SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_NONE,
            "future_adapter_role": (
                "Adapters may feed Analyst posture later; they do not bypass "
                "Analyst or become source authority."
            ),
        },
        "source_class_labels": list(SOURCE_AUTHORITY_SOURCE_CLASSES),
        "recommended_source_use_definitions": dict(_RECOMMENDED_USE_DEFINITIONS),
        "required_packet_fields": list(SOURCE_AUTHORITY_REQUIRED_PACKET_FIELDS),
        "authority_required_supporting_fields": list(
            SOURCE_AUTHORITY_AUTHORITY_REQUIRED_SUPPORTING_FIELDS
        ),
        "social_review_source_classes": list(
            SOURCE_AUTHORITY_SOCIAL_REVIEW_SOURCE_CLASSES
        ),
        "social_review_allowed_recommended_uses": list(
            SOURCE_AUTHORITY_SOCIAL_REVIEW_RECOMMENDED_USES
        ),
        "hard_anti_laundering_rule": (
            "A single social/forum/review item must not validate as consensus, "
            "reliability evidence, or authority-bearing support."
        ),
        "nonclaims": list(SOURCE_AUTHORITY_REQUIRED_NONCLAIMS),
        "raw_private_retention_flags": dict(
            SOURCE_AUTHORITY_RAW_PRIVATE_RETENTION_FLAGS
        ),
        "closed_surface_flags": dict(SOURCE_AUTHORITY_CLOSED_SURFACE_FLAGS),
        "anti_laundering_flags": dict(SOURCE_AUTHORITY_ANTI_LAUNDERING_FLAGS),
    }
    return validate_source_authority_posture_profile(profile)


def validate_source_authority_posture_profile(
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the source-authority posture profile shape."""

    safe = _required_mapping(profile, "source authority posture profile")
    if safe.get("schema_version") != SOURCE_AUTHORITY_POSTURE_SCHEMA_VERSION:
        _blocked("source-authority posture profile schema version mismatch")
    if safe.get("phase") != SOURCE_AUTHORITY_POSTURE_PHASE:
        _blocked("source-authority posture profile phase mismatch")
    if safe.get("owner") != SOURCE_AUTHORITY_POSTURE_OWNER_ANALYST:
        _blocked("source-authority posture profile owner must be Analyst")
    if safe.get("source_authority_is_analyst_owned") is not True:
        _blocked("source authority must be Analyst-owned")
    if safe.get("source_authority_is_not_domain_allowlist") is not True:
        _blocked("source authority must not be a domain allowlist")
    if safe.get("source_authority_is_not_source_ranking") is not True:
        _blocked("source authority must not be source ranking")
    if safe.get("source_authority_is_not_numeric_scoring") is not True:
        _blocked("source authority must not be numeric scoring")
    _require_contains_all(
        _string_tuple(safe.get("source_class_labels")),
        SOURCE_AUTHORITY_SOURCE_CLASSES,
        label="source class labels",
    )
    definitions = _safe_mapping(safe.get("recommended_source_use_definitions"))
    _require_contains_all(
        tuple(definitions),
        SOURCE_AUTHORITY_RECOMMENDED_USES,
        label="recommended source-use definitions",
    )
    _require_contains_all(
        _string_tuple(safe.get("required_packet_fields")),
        SOURCE_AUTHORITY_REQUIRED_PACKET_FIELDS,
        label="required packet fields",
    )
    _require_contains_all(
        _string_tuple(safe.get("authority_required_supporting_fields")),
        SOURCE_AUTHORITY_AUTHORITY_REQUIRED_SUPPORTING_FIELDS,
        label="authority supporting fields",
    )
    _require_contains_all(
        _string_tuple(safe.get("nonclaims")),
        SOURCE_AUTHORITY_REQUIRED_NONCLAIMS,
        label="source-authority posture nonclaims",
    )
    _require_false_flags(
        _safe_mapping(safe.get("raw_private_retention_flags")),
        SOURCE_AUTHORITY_RAW_PRIVATE_RETENTION_FLAGS,
        label="profile raw/private retention flags",
    )
    _require_false_flags(
        _safe_mapping(safe.get("closed_surface_flags")),
        SOURCE_AUTHORITY_CLOSED_SURFACE_FLAGS,
        label="profile closed-surface flags",
    )
    _require_false_flags(
        _safe_mapping(safe.get("anti_laundering_flags")),
        SOURCE_AUTHORITY_ANTI_LAUNDERING_FLAGS,
        label="profile anti-laundering flags",
    )
    _reject_forbidden_payload(safe, context="source-authority posture profile")
    return deepcopy(safe)


def build_source_authority_posture_packet(
    *,
    source_authority_posture_id: str,
    source_class: str,
    issuer_or_source_owner: str,
    document_type: str,
    primary_derivative_posture: str,
    officialness_canonicality_posture: str,
    directness_to_answer_component: str,
    recency_currentness: str,
    scope_match: str,
    claim_specificity: str,
    source_contains_exact_claim: bool,
    conflict_qualification_posture: str,
    recommended_source_use: str,
    recommended_source_use_rationale: str,
    recommended_source_use_supporting_fields: Sequence[str],
    limitations: Sequence[str],
    required_caveats: Sequence[str],
    analyst_rationale: str,
    source_ref: Mapping[str, Any] | None = None,
    source_candidate_ref: Mapping[str, Any] | None = None,
    evidence_content_ref: Mapping[str, Any] | None = None,
    publication_date: str | None = None,
    revision_date: str | None = None,
    observed_date: str | None = None,
    source_class_adapter_used: str = SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_NONE,
    nonclaims: Sequence[str] = SOURCE_AUTHORITY_REQUIRED_NONCLAIMS,
    raw_private_retention_flags: Mapping[str, bool] | None = None,
    closed_surface_flags: Mapping[str, bool] | None = None,
    anti_laundering_flags: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Build a concrete Analyst-declared source-authority posture packet."""

    packet = {
        "schema_version": SOURCE_AUTHORITY_POSTURE_SCHEMA_VERSION,
        "phase": SOURCE_AUTHORITY_POSTURE_PHASE,
        "owner": SOURCE_AUTHORITY_POSTURE_OWNER_ANALYST,
        "source_authority_posture_id": _required_text(
            source_authority_posture_id,
            "source-authority posture id is required",
            limit=320,
        ),
        "source_ref": _safe_mapping(source_ref),
        "source_candidate_ref": _safe_mapping(source_candidate_ref),
        "evidence_content_ref": _safe_mapping(evidence_content_ref),
        "source_class": _clean_token(source_class),
        "issuer_or_source_owner": _required_text(
            issuer_or_source_owner,
            "issuer/source owner is required",
        ),
        "document_type": _required_text(document_type, "document type is required"),
        "primary_derivative_posture": _required_text(
            primary_derivative_posture,
            "primary/derivative posture is required",
        ),
        "officialness_canonicality_posture": _required_text(
            officialness_canonicality_posture,
            "officialness/canonicality posture is required",
        ),
        "directness_to_answer_component": _required_text(
            directness_to_answer_component,
            "directness to answer component is required",
        ),
        "recency_currentness": _required_text(
            recency_currentness,
            "recency/currentness posture is required",
        ),
        "publication_date": _clean_text(publication_date, limit=80),
        "revision_date": _clean_text(revision_date, limit=80),
        "observed_date": _clean_text(observed_date, limit=80),
        "scope_match": _required_text(scope_match, "scope match is required"),
        "claim_specificity": _required_text(
            claim_specificity,
            "claim specificity is required",
        ),
        "source_contains_exact_claim": source_contains_exact_claim,
        "conflict_qualification_posture": _required_text(
            conflict_qualification_posture,
            "conflict/qualification posture is required",
        ),
        "recommended_source_use": _clean_token(recommended_source_use),
        "recommended_source_use_rationale": _required_text(
            recommended_source_use_rationale,
            "recommended source-use rationale is required",
            limit=1000,
        ),
        "recommended_source_use_supporting_fields": list(
            _string_tuple(recommended_source_use_supporting_fields)
        ),
        "limitations": list(_string_tuple(limitations, limit=400)),
        "required_caveats": list(_string_tuple(required_caveats, limit=400)),
        "source_class_adapter_used": _clean_token(source_class_adapter_used),
        "analyst_rationale": _required_text(
            analyst_rationale,
            "Analyst rationale is required",
            limit=1000,
        ),
        "nonclaims": list(_string_tuple(nonclaims, limit=400)),
        "raw_private_retention_flags": dict(
            raw_private_retention_flags
            if raw_private_retention_flags is not None
            else SOURCE_AUTHORITY_RAW_PRIVATE_RETENTION_FLAGS
        ),
        "closed_surface_flags": dict(
            closed_surface_flags
            if closed_surface_flags is not None
            else SOURCE_AUTHORITY_CLOSED_SURFACE_FLAGS
        ),
        "anti_laundering_flags": dict(
            anti_laundering_flags
            if anti_laundering_flags is not None
            else SOURCE_AUTHORITY_ANTI_LAUNDERING_FLAGS
        ),
    }
    packet["source_authority_posture_digest"] = _digest_packet(packet)
    return validate_source_authority_posture_packet(packet)


def validate_source_authority_posture_packet(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a concrete Analyst source-authority posture packet."""

    safe = _required_mapping(packet, "source authority posture packet")
    for field_name in SOURCE_AUTHORITY_REQUIRED_PACKET_FIELDS:
        if field_name not in safe:
            _blocked(f"source-authority posture packet missing {field_name}")
    if safe.get("schema_version") != SOURCE_AUTHORITY_POSTURE_SCHEMA_VERSION:
        _blocked("source-authority posture packet schema version mismatch")
    if safe.get("phase") != SOURCE_AUTHORITY_POSTURE_PHASE:
        _blocked("source-authority posture packet phase mismatch")
    if safe.get("owner") != SOURCE_AUTHORITY_POSTURE_OWNER_ANALYST:
        _blocked("source-authority posture packet owner must be Analyst")
    if not _clean_text(safe.get("source_authority_posture_id"), limit=320):
        _blocked("source-authority posture id is required")
    if not _safe_mapping(safe.get("source_ref")) and not _safe_mapping(
        safe.get("source_candidate_ref")
    ):
        _blocked("source-authority posture requires source_ref or source_candidate_ref")

    source_class = _clean_token(safe.get("source_class"))
    if source_class not in SOURCE_AUTHORITY_SOURCE_CLASSES:
        _blocked(f"unsupported source class: {safe.get('source_class')!s}")
    safe["source_class"] = source_class

    recommended_use = _clean_token(safe.get("recommended_source_use"))
    if recommended_use not in SOURCE_AUTHORITY_RECOMMENDED_USES:
        _blocked(f"unsupported recommended source use: {recommended_use!s}")
    safe["recommended_source_use"] = recommended_use

    adapter_used = _clean_token(safe.get("source_class_adapter_used"))
    if adapter_used not in SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_VALUES:
        _blocked("source-class adapter used must be none or future")
    safe["source_class_adapter_used"] = adapter_used

    for field_name in (
        "issuer_or_source_owner",
        "document_type",
        "primary_derivative_posture",
        "officialness_canonicality_posture",
        "directness_to_answer_component",
        "recency_currentness",
        "scope_match",
        "claim_specificity",
        "conflict_qualification_posture",
        "recommended_source_use_rationale",
        "analyst_rationale",
    ):
        if not _clean_text(safe.get(field_name), limit=1000):
            _blocked(f"source-authority posture field {field_name} is required")
    if not isinstance(safe.get("source_contains_exact_claim"), bool):
        _blocked("source_contains_exact_claim must be bool")
    if not _string_tuple(safe.get("limitations"), limit=400):
        _blocked("source-authority posture requires limitations")
    if not _string_tuple(safe.get("required_caveats"), limit=400):
        _blocked("source-authority posture requires caveats")

    supporting_fields = _string_tuple(
        safe.get("recommended_source_use_supporting_fields")
    )
    if not supporting_fields:
        _blocked("recommended_source_use requires supporting posture fields")
    non_source_supporting_fields = {
        field for field in supporting_fields if field != "source_class"
    }
    if len(non_source_supporting_fields) < 2:
        _blocked(
            "recommended_source_use cannot be justified by source class alone"
        )
    safe["recommended_source_use_supporting_fields"] = list(supporting_fields)

    _require_contains_all(
        _string_tuple(safe.get("nonclaims"), limit=400),
        SOURCE_AUTHORITY_REQUIRED_NONCLAIMS,
        label="source-authority posture nonclaims",
    )
    _require_false_flags(
        _safe_mapping(safe.get("raw_private_retention_flags")),
        SOURCE_AUTHORITY_RAW_PRIVATE_RETENTION_FLAGS,
        label="packet raw/private retention flags",
    )
    _require_false_flags(
        _safe_mapping(safe.get("closed_surface_flags")),
        SOURCE_AUTHORITY_CLOSED_SURFACE_FLAGS,
        label="packet closed-surface flags",
    )
    _require_false_flags(
        _safe_mapping(safe.get("anti_laundering_flags")),
        SOURCE_AUTHORITY_ANTI_LAUNDERING_FLAGS,
        label="packet anti-laundering flags",
    )
    _reject_forbidden_payload(safe, context="source-authority posture packet")

    if source_class in SOURCE_AUTHORITY_SOCIAL_REVIEW_SOURCE_CLASSES:
        _validate_social_or_review_packet(safe)
    if recommended_use == SOURCE_AUTHORITY_RECOMMENDED_USE_AUTHORITY:
        _validate_authority_packet(safe)

    existing_digest = _clean_text(
        safe.get("source_authority_posture_digest"),
        limit=128,
    )
    expected_digest = _digest_packet(safe)
    if existing_digest and existing_digest != expected_digest:
        _blocked("source-authority posture digest mismatch")
    safe["source_authority_posture_digest"] = existing_digest or expected_digest
    return deepcopy(safe)


def build_official_source_of_record_example_posture_packet() -> dict[str, Any]:
    """Return a generic official/source-of-record authority posture example."""

    return build_source_authority_posture_packet(
        source_authority_posture_id=(
            "source-authority-posture:example-county-clerk-fee-schedule"
        ),
        source_ref={
            "source_id": "source:example-county-clerk-fee-schedule",
            "title": "Example County Clerk Official Fee Schedule",
            "lineage_only": True,
        },
        evidence_content_ref={
            "content_ref_id": "content:example-county-clerk-fee-schedule",
            "bounded_content_retained": False,
        },
        source_class=SOURCE_AUTHORITY_SOURCE_CLASS_OFFICIAL_OR_SOURCE_OF_RECORD,
        issuer_or_source_owner="Example County Clerk",
        document_type="official fee schedule",
        primary_derivative_posture="primary",
        officialness_canonicality_posture="official source-of-record",
        directness_to_answer_component="direct",
        recency_currentness="current_or_observed_current",
        revision_date="2026-07-01",
        observed_date="2026-07-03",
        scope_match="exact",
        claim_specificity="exact claim present",
        source_contains_exact_claim=True,
        conflict_qualification_posture="no known conflict",
        recommended_source_use=SOURCE_AUTHORITY_RECOMMENDED_USE_AUTHORITY,
        recommended_source_use_rationale=(
            "Analyst posture recommends authority because the declared source "
            "class, owner, document type, primary posture, official posture, "
            "directness, currentness, exact scope, exact claim, and conflict "
            "posture all support authority use for the answer component."
        ),
        recommended_source_use_supporting_fields=(
            SOURCE_AUTHORITY_AUTHORITY_REQUIRED_SUPPORTING_FIELDS
        ),
        limitations=("product correctness remains unclaimed",),
        required_caveats=(
            "Treat this as an example posture, not a live factual verification.",
        ),
        analyst_rationale=(
            "The Analyst has determined that this example official fee schedule "
            "is primary, direct, current/observed-current, exact in scope, and "
            "contains the exact claim needed for the answer component."
        ),
    )


def build_social_review_directionality_example_posture_packet() -> dict[str, Any]:
    """Return a generic social/forum posture that is not authority."""

    return build_source_authority_posture_packet(
        source_authority_posture_id=(
            "source-authority-posture:example-forum-user-comment"
        ),
        source_candidate_ref={
            "source_candidate_id": "source-candidate:example-forum-user-comment",
            "title": "Example Forum User Comment",
            "lineage_only": True,
        },
        evidence_content_ref={
            "content_ref_id": "content:example-forum-user-comment",
            "bounded_content_retained": False,
        },
        source_class=SOURCE_AUTHORITY_SOURCE_CLASS_SOCIAL_OR_FORUM_DISCUSSION,
        issuer_or_source_owner="forum participant",
        document_type="user comment",
        primary_derivative_posture="anecdotal first-person or unknown",
        officialness_canonicality_posture="not official or canonical",
        directness_to_answer_component="user-experience report",
        recency_currentness="observed date only",
        observed_date="2026-07-03",
        scope_match="limited",
        claim_specificity="anecdotal or disputed",
        source_contains_exact_claim=False,
        conflict_qualification_posture=(
            "representativeness, dissent, and aggregation not established"
        ),
        recommended_source_use=SOURCE_AUTHORITY_RECOMMENDED_USE_DIRECTIONALITY,
        recommended_source_use_rationale=(
            "Analyst posture recommends directionality only because the item is "
            "a single social/forum report with limited scope and no established "
            "aggregation, representativeness, reliability, or authority."
        ),
        recommended_source_use_supporting_fields=(
            "source_class",
            "document_type",
            "primary_derivative_posture",
            "officialness_canonicality_posture",
            "scope_match",
            "claim_specificity",
            "conflict_qualification_posture",
            "limitations",
            "analyst_rationale",
        ),
        limitations=(
            "not authority for factual truth",
            "not consensus unless separately aggregated by a future adapter",
            "single comment/review must not be upgraded into community consensus",
            "social/review analysis remains future adapter work",
        ),
        required_caveats=(
            "Use only as directionality unless a future adapter establishes "
            "aggregation, representativeness, and dissent posture.",
        ),
        analyst_rationale=(
            "The Analyst has determined that this single forum item may indicate "
            "a possible user-experience lead, but it cannot authorize the answer "
            "component or stand in for consensus."
        ),
    )


def _validate_authority_packet(packet: Mapping[str, Any]) -> None:
    source_class = _clean_token(packet.get("source_class"))
    if source_class in SOURCE_AUTHORITY_SOCIAL_REVIEW_SOURCE_CLASSES:
        _blocked("social/forum/review posture cannot validate as authority")
    if packet.get("source_contains_exact_claim") is not True:
        _blocked("authority recommended use requires exact claim present")
    date_fields = (
        packet.get("publication_date"),
        packet.get("revision_date"),
        packet.get("observed_date"),
    )
    if not any(_clean_text(item, limit=80) for item in date_fields):
        _blocked("authority recommended use requires a date posture field")
    conflict_posture = _clean_token(packet.get("conflict_qualification_posture"))
    if conflict_posture in _AUTHORITY_CONFLICT_BLOCKERS:
        _blocked("authority recommended use requires resolved conflict posture")
    _require_contains_all(
        _string_tuple(packet.get("recommended_source_use_supporting_fields")),
        SOURCE_AUTHORITY_AUTHORITY_REQUIRED_SUPPORTING_FIELDS,
        label="authority recommended-use supporting fields",
    )


def _validate_social_or_review_packet(packet: Mapping[str, Any]) -> None:
    recommended_use = _clean_token(packet.get("recommended_source_use"))
    if recommended_use not in SOURCE_AUTHORITY_SOCIAL_REVIEW_RECOMMENDED_USES:
        _blocked(
            "social/forum/review posture must validate as directionality or ignore"
        )
    flags = _safe_mapping(packet.get("anti_laundering_flags"))
    if any(flags.get(key) is not False for key in SOURCE_AUTHORITY_ANTI_LAUNDERING_FLAGS):
        _blocked("social/forum/review anti-laundering flags must remain false")


def _digest_packet(packet: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in packet.items()
        if key != "source_authority_posture_digest"
    }
    encoded = json.dumps(_json_safe(payload), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _require_contains_all(
    values: Sequence[str],
    required: Sequence[str],
    *,
    label: str,
) -> None:
    available = {str(value) for value in values}
    missing = [value for value in required if value not in available]
    if missing:
        _blocked(f"{label} missing required values: {', '.join(missing)}")


def _require_false_flags(
    flags: Mapping[str, Any],
    required: Mapping[str, bool],
    *,
    label: str,
) -> None:
    for key, expected in required.items():
        if expected is not False:
            _blocked(f"{label} expected false baseline for {key}")
        if flags.get(key) is not False:
            _blocked(f"{label} must keep {key}=false")


def _reject_forbidden_payload(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden_decision = sorted(keys & _FORBIDDEN_DECISION_MECHANIC_KEYS)
    if forbidden_decision:
        _blocked(
            f"{context} includes forbidden decision mechanics: "
            + ", ".join(forbidden_decision)
        )
    raw_private = sorted(keys & _RAW_PRIVATE_CONTENT_KEYS)
    if raw_private:
        _blocked(f"{context} includes raw/private fields: " + ", ".join(raw_private))


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _required_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _blocked(f"{label} must be a mapping")
    return dict(value)


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_tuple(value: Any, *, limit: int = 220) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return (text,) if text else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _required_text(value: Any, message: str, *, limit: int = 500) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        _blocked(message)
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    text = _clean_text(value, limit=limit)
    return text.casefold().replace("-", "_").replace(" ", "_") if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_json_safe(item) for item in value]
    return value


def _blocked(message: str) -> None:
    raise SourceAuthorityPosturePacketError(message)


__all__ = [
    "SOURCE_AUTHORITY_ANTI_LAUNDERING_FLAGS",
    "SOURCE_AUTHORITY_AUTHORITY_REQUIRED_SUPPORTING_FIELDS",
    "SOURCE_AUTHORITY_CLOSED_SURFACE_FLAGS",
    "SOURCE_AUTHORITY_POSTURE_OWNER_ANALYST",
    "SOURCE_AUTHORITY_POSTURE_PHASE",
    "SOURCE_AUTHORITY_POSTURE_SCHEMA_VERSION",
    "SOURCE_AUTHORITY_RAW_PRIVATE_RETENTION_FLAGS",
    "SOURCE_AUTHORITY_RECOMMENDED_USE_AUTHORITY",
    "SOURCE_AUTHORITY_RECOMMENDED_USE_CORROBORATION",
    "SOURCE_AUTHORITY_RECOMMENDED_USE_CONTEXT",
    "SOURCE_AUTHORITY_RECOMMENDED_USE_DIRECTIONALITY",
    "SOURCE_AUTHORITY_RECOMMENDED_USE_IGNORE",
    "SOURCE_AUTHORITY_RECOMMENDED_USES",
    "SOURCE_AUTHORITY_REQUIRED_NONCLAIMS",
    "SOURCE_AUTHORITY_REQUIRED_PACKET_FIELDS",
    "SOURCE_AUTHORITY_SOCIAL_REVIEW_RECOMMENDED_USES",
    "SOURCE_AUTHORITY_SOCIAL_REVIEW_SOURCE_CLASSES",
    "SOURCE_AUTHORITY_SOURCE_CLASS_ACADEMIC_OR_RESEARCH",
    "SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_FUTURE",
    "SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_NONE",
    "SOURCE_AUTHORITY_SOURCE_CLASS_ADAPTER_VALUES",
    "SOURCE_AUTHORITY_SOURCE_CLASS_DATA_TABLE_OR_STATISTICAL_SOURCE",
    "SOURCE_AUTHORITY_SOURCE_CLASS_GOVERNMENT_OR_PUBLIC_AGENCY",
    "SOURCE_AUTHORITY_SOURCE_CLASS_LEGAL_OR_REGULATORY",
    "SOURCE_AUTHORITY_SOURCE_CLASS_NEWS_OR_REPORTING",
    "SOURCE_AUTHORITY_SOURCE_CLASS_OFFICIAL_OR_SOURCE_OF_RECORD",
    "SOURCE_AUTHORITY_SOURCE_CLASS_SOCIAL_OR_FORUM_DISCUSSION",
    "SOURCE_AUTHORITY_SOURCE_CLASS_UNKNOWN_OR_UNCLASSIFIED",
    "SOURCE_AUTHORITY_SOURCE_CLASS_USER_REVIEW",
    "SOURCE_AUTHORITY_SOURCE_CLASS_VENDOR_OR_PRODUCT_DOCUMENTATION",
    "SOURCE_AUTHORITY_SOURCE_CLASSES",
    "SourceAuthorityPosturePacketError",
    "build_official_source_of_record_example_posture_packet",
    "build_social_review_directionality_example_posture_packet",
    "build_source_authority_posture_packet",
    "build_source_authority_posture_profile",
    "validate_source_authority_posture_packet",
    "validate_source_authority_posture_profile",
]
