"""Offline social-signal packet schema and Author-safe digest helpers.

Social signal is discussion/perception signal only. This module validates that
boundary explicitly and keeps raw discussion packets out of factual-evidence
and Author handoff surfaces.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

SOCIAL_SIGNAL_SCHEMA_VERSION = "social_signal_packet_v1"
SOCIAL_SIGNAL_DIGEST_SCHEMA_VERSION = "social_signal_author_digest_v1"

AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL = "Sampled public discussion signal, not factual evidence."

SOCIAL_SIGNAL_STATUSES = frozenset(
    {
        "completed",
        "blocked",
        "skipped",
        "invalid",
        "not_requested",
    }
)

SOCIAL_SIGNAL_REASON_CODES = frozenset(
    {
        "fast_mode_blocked",
        "social_relevance_irrelevant",
        "social_provider_not_configured",
        "api_disabled",
        "tos_review_required",
        "platform_not_allowed",
        "commercial_use_not_allowed",
        "retention_policy_unresolved",
        "raw_storage_not_allowed",
        "missing_engagement_metadata",
        "insufficient_sample",
        "platform_bias_too_high",
        "duplicate_or_spam_dominance",
        "packet_validation_failed",
        "factual_claim_boundary_violation",
        "raw_packet_author_blocked",
        "ordinary_evidence_merge_blocked",
    }
)

SOCIAL_SIGNAL_STABLE_CODES = SOCIAL_SIGNAL_STATUSES | SOCIAL_SIGNAL_REASON_CODES

COMPLIANCE_FIELDS = (
    "source_tool",
    "official_access",
    "access_method",
    "retention_deadline",
    "deletion_check_due",
    "redistribution_allowed",
    "attribution_required",
    "policy_basis",
    "raw_storage_allowed",
    "commercial_use_allowed",
)

EVIDENCE_BOUNDARY_FIELDS = (
    "may_support_factual_claims",
    "may_support_claims_about_sampled_sentiment",
    "raw_packet_to_author_allowed",
    "raw_comments_to_author_allowed",
    "ordinary_evidence_registry_merge_allowed",
    "analyst_review_required_before_author",
)

EVIDENCE_BOUNDARY_REQUIRED_VALUES = {
    "may_support_factual_claims": False,
    "may_support_claims_about_sampled_sentiment": True,
    "raw_packet_to_author_allowed": False,
    "raw_comments_to_author_allowed": False,
    "ordinary_evidence_registry_merge_allowed": False,
    "analyst_review_required_before_author": True,
}

_REQUIRED_PACKET_FIELDS = (
    "schema_version",
    "status",
    "query",
    "entity",
    "topic",
    "time_window",
    "platforms_sampled",
    "communities_sampled",
    "item_counts",
    "topic_clusters",
    "raw_sentiment_counts_by_topic",
    "raw_stance_counts_by_topic",
    "engagement_weighted_sentiment_by_topic",
    "recency_weighted_sentiment_by_topic",
    "representative_high_engagement_examples",
    "high_engagement_dissenting_examples",
    "complaint_clusters",
    "praise_clusters",
    "missing_metadata_counts",
    "spam_duplicate_brigading_caveats",
    "platform_sample_bias_caveats",
    "confidence_level",
    "confidence_reasons",
    "source_references",
) + COMPLIANCE_FIELDS + EVIDENCE_BOUNDARY_FIELDS

_RAW_DIGEST_BLOCKLIST_KEYS = frozenset(
    {
        "text",
        "comment",
        "comments",
        "raw_comment",
        "raw_comments",
        "raw_text",
        "author",
        "author_id",
        "author_key",
        "author_hash",
        "user",
        "user_id",
        "username",
        "item_id",
        "parent_id",
        "thread_id",
        "raw_packet",
        "packet",
        "packet_dict",
        "representative_high_engagement_examples",
        "high_engagement_dissenting_examples",
        "source_tool",
        "access_method",
        "source_reference",
        "source_reference_url",
        "source_references",
        "source_url",
        "url",
    }
)

_RAW_STORAGE_EXAMPLE_FIELDS = frozenset(
    {
        "text",
        "comment",
        "comments",
        "raw_comment",
        "raw_comments",
        "raw_text",
        "author",
        "author_id",
        "author_key",
        "author_hash",
        "user",
        "user_id",
        "username",
        "item_id",
        "parent_id",
        "thread_id",
        "source_reference",
        "source_reference_url",
        "source_references",
        "source_url",
        "url",
    }
)

_RAW_STORAGE_EXAMPLE_CONTAINERS = (
    "representative_high_engagement_examples",
    "high_engagement_dissenting_examples",
)

_NORMALIZED_RAW_DIGEST_BLOCKLIST_KEYS = frozenset(
    "".join(char for char in key.casefold() if char.isalnum())
    for key in _RAW_DIGEST_BLOCKLIST_KEYS
)
_NORMALIZED_RAW_STORAGE_EXAMPLE_FIELDS = frozenset(
    "".join(char for char in key.casefold() if char.isalnum())
    for key in _RAW_STORAGE_EXAMPLE_FIELDS
)


@dataclass(frozen=True)
class SocialSignalPacket:
    """Validated offline social-signal packet.

    Raw examples may exist here for Analyst review, but this object is not an
    ordinary factual-evidence record and is never Author-safe by itself.
    """

    schema_version: str
    status: str
    query: str
    entity: str | None
    topic: str
    time_window: Mapping[str, Any] | str | None
    platforms_sampled: tuple[str, ...] = ()
    communities_sampled: tuple[str, ...] = ()
    item_counts: Mapping[str, Any] = field(default_factory=dict)
    topic_clusters: tuple[Mapping[str, Any], ...] = ()
    raw_sentiment_counts_by_topic: Mapping[str, Mapping[str, int]] = field(default_factory=dict)
    raw_stance_counts_by_topic: Mapping[str, Mapping[str, int]] = field(default_factory=dict)
    engagement_weighted_sentiment_by_topic: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    recency_weighted_sentiment_by_topic: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    representative_high_engagement_examples: tuple[Mapping[str, Any], ...] = ()
    high_engagement_dissenting_examples: tuple[Mapping[str, Any], ...] = ()
    complaint_clusters: tuple[Mapping[str, Any], ...] = ()
    praise_clusters: tuple[Mapping[str, Any], ...] = ()
    missing_metadata_counts: Mapping[str, int] = field(default_factory=dict)
    spam_duplicate_brigading_caveats: tuple[str, ...] = ()
    platform_sample_bias_caveats: tuple[str, ...] = ()
    confidence_level: str = "low"
    confidence_reasons: tuple[str, ...] = ()
    source_references: tuple[str, ...] = ()
    source_tool: str = "offline_fixture"
    official_access: bool = False
    access_method: str = "offline_fixture"
    retention_deadline: str = "not_retained"
    deletion_check_due: str = "not_applicable"
    redistribution_allowed: bool = False
    attribution_required: bool = True
    policy_basis: str = "offline_fixture"
    raw_storage_allowed: bool = False
    commercial_use_allowed: bool = False
    may_support_factual_claims: bool = False
    may_support_claims_about_sampled_sentiment: bool = True
    raw_packet_to_author_allowed: bool = False
    raw_comments_to_author_allowed: bool = False
    ordinary_evidence_registry_merge_allowed: bool = False
    analyst_review_required_before_author: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class SocialSignalValidationResult:
    valid: bool
    status: str
    reasons: tuple[str, ...] = ()
    packet: SocialSignalPacket | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "status": self.status,
            "reasons": list(self.reasons),
            "packet": self.packet.to_dict() if self.packet else None,
        }


class SocialSignalPacketValidationError(ValueError):
    """Raised when a social-signal packet violates the schema boundary."""

    def __init__(self, reasons: tuple[str, ...]):
        self.reasons = reasons
        super().__init__("SocialSignalPacket invalid: " + ", ".join(reasons))


def evidence_boundary_defaults() -> dict[str, bool]:
    return dict(EVIDENCE_BOUNDARY_REQUIRED_VALUES)


def is_social_signal_factual_evidence(packet: SocialSignalPacket | Mapping[str, Any]) -> bool:
    result = validate_social_signal_packet(packet)
    if not result.valid:
        return False
    return bool(result.packet and result.packet.may_support_factual_claims)


def can_merge_into_ordinary_evidence_registry(
    packet: SocialSignalPacket | Mapping[str, Any],
) -> bool:
    result = validate_social_signal_packet(packet)
    if not result.valid:
        return False
    return bool(result.packet and result.packet.ordinary_evidence_registry_merge_allowed)


def author_boundary_block_reasons(packet: SocialSignalPacket | Mapping[str, Any]) -> tuple[str, ...]:
    result = validate_social_signal_packet(packet)
    if not result.valid:
        return result.reasons

    reasons = ["raw_packet_author_blocked", "ordinary_evidence_merge_blocked"]
    if result.packet and result.packet.may_support_factual_claims:
        reasons.append("factual_claim_boundary_violation")
    return tuple(_dedupe_strings(reasons))


def parse_social_signal_packet(packet: SocialSignalPacket | Mapping[str, Any]) -> SocialSignalPacket:
    result = validate_social_signal_packet(packet)
    if not result.valid:
        raise SocialSignalPacketValidationError(result.reasons)
    assert result.packet is not None
    return result.packet


def validate_social_signal_packet(
    packet: SocialSignalPacket | Mapping[str, Any],
) -> SocialSignalValidationResult:
    data = _packet_mapping(packet)
    reasons: list[str] = []

    if not data:
        reasons.append("packet_validation_failed")
        return _invalid_result(reasons)

    missing_fields = [field_name for field_name in _REQUIRED_PACKET_FIELDS if field_name not in data]
    if missing_fields:
        reasons.append("packet_validation_failed")

    if data.get("schema_version") != SOCIAL_SIGNAL_SCHEMA_VERSION:
        reasons.append("packet_validation_failed")

    status = data.get("status")
    if status not in SOCIAL_SIGNAL_STATUSES:
        reasons.append("packet_validation_failed")

    for field_name in COMPLIANCE_FIELDS:
        if field_name not in data:
            continue
        if field_name in {
            "official_access",
            "redistribution_allowed",
            "attribution_required",
            "raw_storage_allowed",
            "commercial_use_allowed",
        } and not isinstance(data.get(field_name), bool):
            reasons.append("packet_validation_failed")
        elif field_name not in {
            "official_access",
            "redistribution_allowed",
            "attribution_required",
            "raw_storage_allowed",
            "commercial_use_allowed",
        } and data.get(field_name) in (None, ""):
            reasons.append("packet_validation_failed")

    reasons.extend(_status_consistency_reasons(data))
    reasons.extend(_raw_storage_policy_reasons(data))
    reasons.extend(_boundary_violation_reasons(data))

    stable_reasons = tuple(_dedupe_strings(reason for reason in reasons if reason in SOCIAL_SIGNAL_STABLE_CODES))
    if stable_reasons:
        return SocialSignalValidationResult(
            valid=False,
            status="invalid",
            reasons=stable_reasons or ("packet_validation_failed",),
            packet=None,
        )

    return SocialSignalValidationResult(
        valid=True,
        status=str(status),
        reasons=(),
        packet=_packet_from_mapping(data),
    )


def build_author_safe_social_signal_digest(
    packet: SocialSignalPacket | Mapping[str, Any],
) -> dict[str, Any]:
    """Return the only packet-derived shape intended for Author handoff."""

    result = validate_social_signal_packet(packet)
    if not result.valid or result.packet is None:
        return _strip_blocked_keys(
            {
                "schema_version": SOCIAL_SIGNAL_DIGEST_SCHEMA_VERSION,
                "status": "blocked",
                "reason_codes": list(result.reasons or ("packet_validation_failed",)),
                "label": AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL,
                "author_safe": True,
                "social_signal_available": False,
                "may_support_factual_claims": False,
                "may_support_claims_about_sampled_sentiment": True,
                "raw_packet_to_author_allowed": False,
                "raw_comments_to_author_allowed": False,
                "ordinary_evidence_registry_merge_allowed": False,
                "analyst_review_required_before_author": True,
                "topics": [],
                "caveats": ["Social-signal packet was blocked before Author handoff."],
            }
        )

    packet_obj = result.packet
    packet_data = packet_obj.to_dict()
    topics = _digest_topics(packet_data)
    caveats = _dedupe_strings(
        [
            AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL,
            "This digest describes sampled discussion only and cannot verify factual claims.",
            "Not a statistically representative poll.",
            *packet_obj.platform_sample_bias_caveats,
            *packet_obj.spam_duplicate_brigading_caveats,
            *packet_obj.confidence_reasons,
        ]
    )

    digest = {
        "schema_version": SOCIAL_SIGNAL_DIGEST_SCHEMA_VERSION,
        "status": packet_obj.status,
        "reason_codes": [],
        "label": AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL,
        "author_safe": True,
        "social_signal_available": packet_obj.status == "completed",
        "query": _compact_string(packet_obj.query),
        "entity": _compact_string(packet_obj.entity),
        "topic": _compact_string(packet_obj.topic),
        "time_window": _jsonable(packet_obj.time_window),
        "sampled_item_count": _safe_count(packet_obj.item_counts.get("included_items")),
        "topics": topics,
        "caveats": caveats,
        "confidence": {
            "level": packet_obj.confidence_level,
            "reasons": list(packet_obj.confidence_reasons),
        },
        "may_support_factual_claims": False,
        "may_support_claims_about_sampled_sentiment": True,
        "raw_packet_to_author_allowed": False,
        "raw_comments_to_author_allowed": False,
        "ordinary_evidence_registry_merge_allowed": False,
        "analyst_review_required_before_author": True,
    }
    return _strip_blocked_keys(digest)


def _status_consistency_reasons(data: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    status = data.get("status")
    item_counts = _mapping(data.get("item_counts"))
    included_items = _safe_count(item_counts.get("included_items"))
    topic_clusters = _as_list(data.get("topic_clusters"))

    if status == "completed" and (included_items <= 0 or not topic_clusters):
        reasons.append("packet_validation_failed")

    if "social_signal_available" in data:
        social_signal_available = data.get("social_signal_available")
        if not isinstance(social_signal_available, bool):
            reasons.append("packet_validation_failed")
        elif status != "completed" and social_signal_available:
            reasons.append("packet_validation_failed")

    return tuple(reasons)


def _raw_storage_policy_reasons(data: Mapping[str, Any]) -> tuple[str, ...]:
    if data.get("raw_storage_allowed") is not False:
        return ()

    reasons: list[str] = []
    if _as_list(data.get("source_references")):
        reasons.append("raw_storage_not_allowed")

    for container_name in _RAW_STORAGE_EXAMPLE_CONTAINERS:
        if _contains_raw_storage_example_field(data.get(container_name)):
            reasons.append("raw_storage_not_allowed")
            break

    return tuple(reasons)


def _boundary_violation_reasons(data: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    missing = [field_name for field_name in EVIDENCE_BOUNDARY_FIELDS if field_name not in data]
    if missing:
        reasons.append("packet_validation_failed")
        return tuple(reasons)

    for field_name, expected in EVIDENCE_BOUNDARY_REQUIRED_VALUES.items():
        if data.get(field_name) is expected:
            continue
        if field_name == "may_support_factual_claims":
            reasons.append("factual_claim_boundary_violation")
        elif field_name in {"raw_packet_to_author_allowed", "raw_comments_to_author_allowed"}:
            reasons.append("raw_packet_author_blocked")
        elif field_name == "ordinary_evidence_registry_merge_allowed":
            reasons.append("ordinary_evidence_merge_blocked")
        else:
            reasons.append("packet_validation_failed")
    return tuple(reasons)


def _packet_from_mapping(data: Mapping[str, Any]) -> SocialSignalPacket:
    clean = deepcopy(dict(data))
    return SocialSignalPacket(
        schema_version=str(clean["schema_version"]),
        status=str(clean["status"]),
        query=str(clean["query"]),
        entity=_optional_string(clean.get("entity")),
        topic=str(clean["topic"]),
        time_window=_jsonable(clean.get("time_window")),
        platforms_sampled=_string_tuple(clean.get("platforms_sampled")),
        communities_sampled=_string_tuple(clean.get("communities_sampled")),
        item_counts=_mapping(clean.get("item_counts")),
        topic_clusters=_mapping_tuple(clean.get("topic_clusters")),
        raw_sentiment_counts_by_topic=_nested_mapping(clean.get("raw_sentiment_counts_by_topic")),
        raw_stance_counts_by_topic=_nested_mapping(clean.get("raw_stance_counts_by_topic")),
        engagement_weighted_sentiment_by_topic=_nested_mapping(
            clean.get("engagement_weighted_sentiment_by_topic")
        ),
        recency_weighted_sentiment_by_topic=_nested_mapping(clean.get("recency_weighted_sentiment_by_topic")),
        representative_high_engagement_examples=_mapping_tuple(
            clean.get("representative_high_engagement_examples")
        ),
        high_engagement_dissenting_examples=_mapping_tuple(clean.get("high_engagement_dissenting_examples")),
        complaint_clusters=_mapping_tuple(clean.get("complaint_clusters")),
        praise_clusters=_mapping_tuple(clean.get("praise_clusters")),
        missing_metadata_counts=_int_mapping(clean.get("missing_metadata_counts")),
        spam_duplicate_brigading_caveats=_string_tuple(clean.get("spam_duplicate_brigading_caveats")),
        platform_sample_bias_caveats=_string_tuple(clean.get("platform_sample_bias_caveats")),
        confidence_level=str(clean.get("confidence_level") or "low"),
        confidence_reasons=_string_tuple(clean.get("confidence_reasons")),
        source_references=_string_tuple(clean.get("source_references")),
        source_tool=str(clean["source_tool"]),
        official_access=bool(clean["official_access"]),
        access_method=str(clean["access_method"]),
        retention_deadline=str(clean["retention_deadline"]),
        deletion_check_due=str(clean["deletion_check_due"]),
        redistribution_allowed=bool(clean["redistribution_allowed"]),
        attribution_required=bool(clean["attribution_required"]),
        policy_basis=str(clean["policy_basis"]),
        raw_storage_allowed=bool(clean["raw_storage_allowed"]),
        commercial_use_allowed=bool(clean["commercial_use_allowed"]),
        may_support_factual_claims=bool(clean["may_support_factual_claims"]),
        may_support_claims_about_sampled_sentiment=bool(
            clean["may_support_claims_about_sampled_sentiment"]
        ),
        raw_packet_to_author_allowed=bool(clean["raw_packet_to_author_allowed"]),
        raw_comments_to_author_allowed=bool(clean["raw_comments_to_author_allowed"]),
        ordinary_evidence_registry_merge_allowed=bool(
            clean["ordinary_evidence_registry_merge_allowed"]
        ),
        analyst_review_required_before_author=bool(clean["analyst_review_required_before_author"]),
    )


def _digest_topics(packet_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    topic_names = _topic_order(packet_data)
    complaints_by_topic = _cluster_lookup(packet_data.get("complaint_clusters"))
    praise_by_topic = _cluster_lookup(packet_data.get("praise_clusters"))
    dissent_by_topic = _example_topic_counts(packet_data.get("high_engagement_dissenting_examples"))

    topics: list[dict[str, Any]] = []
    for topic_name in topic_names:
        topics.append(
            _strip_blocked_keys(
                {
                    "topic": topic_name,
                    "item_count": _topic_item_count(packet_data, topic_name),
                    "raw_sentiment_counts": _jsonable(
                        _mapping(packet_data.get("raw_sentiment_counts_by_topic", {}).get(topic_name))
                    ),
                    "raw_stance_counts": _jsonable(
                        _mapping(packet_data.get("raw_stance_counts_by_topic", {}).get(topic_name))
                    ),
                    "engagement_weighted_sentiment": _jsonable(
                        _mapping(packet_data.get("engagement_weighted_sentiment_by_topic", {}).get(topic_name))
                    ),
                    "recency_weighted_sentiment": _jsonable(
                        _mapping(packet_data.get("recency_weighted_sentiment_by_topic", {}).get(topic_name))
                    ),
                    "complaint_cluster": complaints_by_topic.get(topic_name),
                    "praise_cluster": praise_by_topic.get(topic_name),
                    "dissenting_examples_preserved": dissent_by_topic.get(topic_name, 0),
                }
            )
        )
    return topics


def _topic_order(packet_data: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for cluster in _as_list(packet_data.get("topic_clusters")):
        if isinstance(cluster, Mapping):
            topic = _compact_string(cluster.get("topic"))
            if topic and topic not in out:
                out.append(topic)
    for mapping_name in (
        "raw_sentiment_counts_by_topic",
        "engagement_weighted_sentiment_by_topic",
        "recency_weighted_sentiment_by_topic",
    ):
        mapping = packet_data.get(mapping_name)
        if isinstance(mapping, Mapping):
            for topic in mapping:
                topic_text = _compact_string(topic)
                if topic_text and topic_text not in out:
                    out.append(topic_text)
    return out


def _topic_item_count(packet_data: Mapping[str, Any], topic_name: str) -> int:
    for cluster in _as_list(packet_data.get("topic_clusters")):
        if isinstance(cluster, Mapping) and cluster.get("topic") == topic_name:
            return _safe_count(cluster.get("item_count"))
    sentiment_counts = _mapping(packet_data.get("raw_sentiment_counts_by_topic", {}).get(topic_name))
    return sum(_safe_count(value) for value in sentiment_counts.values())


def _cluster_lookup(value: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for cluster in _as_list(value):
        if not isinstance(cluster, Mapping):
            continue
        topic = _compact_string(cluster.get("topic"))
        if not topic:
            continue
        count = _safe_count(cluster.get("count"))
        sentiment = _compact_string(cluster.get("sentiment"))
        out[topic] = _strip_blocked_keys(
            {
                "topic": topic,
                "count": count,
                "sentiment": sentiment,
                "summary": _safe_cluster_summary(
                    topic=topic,
                    count=count,
                    sentiment=sentiment,
                ),
            }
        )
    return out


def _example_topic_counts(value: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for example in _as_list(value):
        if not isinstance(example, Mapping):
            continue
        topic = _compact_string(example.get("topic"))
        if topic:
            out[topic] = out.get(topic, 0) + 1
    return out


def _contains_raw_storage_example_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalized_key(key) in _NORMALIZED_RAW_STORAGE_EXAMPLE_FIELDS:
                return True
            if _contains_raw_storage_example_field(item):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_raw_storage_example_field(item) for item in value)
    return False


def _strip_blocked_keys(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _strip_blocked_keys(item)
            for key, item in value.items()
            if not _is_blocked_digest_key(key) and item not in ({}, [], (), None)
        }
    if isinstance(value, (list, tuple)):
        return [_strip_blocked_keys(item) for item in value if item not in ({}, [], (), None)]
    if isinstance(value, str):
        return _redact_digest_string(value)
    return value


def _safe_cluster_summary(*, topic: str, count: int, sentiment: str) -> str:
    sentiment_text = sentiment or "sampled"
    return f"{count} sampled {sentiment_text} signal(s) about {topic}."


def _is_blocked_digest_key(key: Any) -> bool:
    normalized = _normalized_key(key)
    return normalized in _NORMALIZED_RAW_DIGEST_BLOCKLIST_KEYS or normalized.startswith("sourcereference")


def _normalized_key(key: Any) -> str:
    return "".join(char for char in str(key).casefold() if char.isalnum())


def _redact_digest_string(value: str) -> str:
    text = _compact_string(value)
    if "RAW_" in text or "SHOULD_NOT_REACH_AUTHOR" in text:
        return "[redacted]"
    return text


def _packet_mapping(packet: SocialSignalPacket | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(packet, SocialSignalPacket):
        return packet.to_dict()
    if isinstance(packet, Mapping):
        return deepcopy(dict(packet))
    return {}


def _invalid_result(reasons: list[str]) -> SocialSignalValidationResult:
    return SocialSignalValidationResult(
        valid=False,
        status="invalid",
        reasons=tuple(_dedupe_strings(reasons or ["packet_validation_failed"])),
        packet=None,
    )


def _mapping(value: Any) -> dict[str, Any]:
    return deepcopy(dict(value)) if isinstance(value, Mapping) else {}


def _nested_mapping(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, item in value.items():
        out[str(key)] = _mapping(item)
    return out


def _int_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): _safe_count(item) for key, item in value.items()}


def _mapping_tuple(value: Any) -> tuple[dict[str, Any], ...]:
    return tuple(_mapping(item) for item in _as_list(value) if isinstance(item, Mapping))


def _string_tuple(value: Any) -> tuple[str, ...]:
    return tuple(_dedupe_strings(_compact_string(item) for item in _as_list(value)))


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _optional_string(value: Any) -> str | None:
    text = _compact_string(value)
    return text if text else None


def _compact_string(value: Any, *, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def _safe_count(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _dedupe_strings(values: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _compact_string(value)
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return out


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
