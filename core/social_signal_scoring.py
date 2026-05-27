"""Deterministic offline social-signal scoring helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import log1p
from typing import Any, Mapping, Sequence

from core.social_signal_schema import (
    EVIDENCE_BOUNDARY_REQUIRED_VALUES,
    SOCIAL_SIGNAL_SCHEMA_VERSION,
    SocialSignalPacket,
    parse_social_signal_packet,
)

ENGAGEMENT_FIELDS = ("upvotes", "likes", "replies", "reposts", "shares", "views")
POSITIVE_ENGAGEMENT_FIELDS = ("upvotes", "likes", "replies", "reposts", "shares")

SENTIMENT_SCORES = {
    "positive": 1.0,
    "praise": 1.0,
    "supportive": 1.0,
    "negative": -1.0,
    "complaint": -1.0,
    "critical": -1.0,
    "opposed": -1.0,
    "neutral": 0.0,
    "mixed": 0.0,
    "unclear": 0.0,
    "unknown": 0.0,
}

DEFAULT_ENGAGEMENT_CAP = 100
DEFAULT_HALF_LIFE_DAYS = 30.0
DEFAULT_PER_AUTHOR_TOPIC_CAP = 3
DEFAULT_PER_THREAD_TOPIC_CAP = 5


@dataclass(frozen=True)
class SocialSignalScoringConfig:
    engagement_cap: int = DEFAULT_ENGAGEMENT_CAP
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS
    per_author_topic_cap: int = DEFAULT_PER_AUTHOR_TOPIC_CAP
    per_thread_topic_cap: int = DEFAULT_PER_THREAD_TOPIC_CAP
    platform_dominance_threshold: float = 0.75
    community_dominance_threshold: float = 0.75
    duplicate_spam_dominance_threshold: float = 0.40
    minimum_included_items: int = 3


@dataclass(frozen=True)
class _PreparedSocialItem:
    original: Mapping[str, Any]
    index: int
    platform: str
    community: str
    topic: str
    sentiment: str
    stance: str | None
    text: str
    created_at: datetime | None
    author_key: str | None
    thread_id: str | None
    item_id: str | None
    parent_id: str | None
    source_reference: str | None
    engagement_raw: int
    engagement_capped: int
    engagement_weight: float
    recency_weight: float
    missing_any_engagement: bool
    duplicate_or_spam: bool
    duplicate_or_spam_reason: str | None


def build_social_signal_packet_from_items(
    items: Sequence[Mapping[str, Any]],
    *,
    query: str,
    entity: str | None = None,
    topic: str | None = None,
    time_window: Mapping[str, Any] | str | None = None,
    reference_time: datetime | str | None = None,
    config: SocialSignalScoringConfig | None = None,
    source_tool: str = "offline_fixture",
    official_access: bool = False,
    access_method: str = "offline_fixture",
    retention_deadline: str = "not_retained",
    deletion_check_due: str = "not_applicable",
    redistribution_allowed: bool = False,
    attribution_required: bool = True,
    policy_basis: str = "offline_fixture",
    raw_storage_allowed: bool = False,
    commercial_use_allowed: bool = False,
) -> SocialSignalPacket:
    """Build a validated offline packet from fixture-like social items."""

    scoring_config = config or SocialSignalScoringConfig()
    now = _parse_datetime(reference_time) or datetime.now(timezone.utc)
    prepared = _prepare_items(items, reference_time=now, config=scoring_config)
    included, excluded_by_cap = _apply_caps(prepared, scoring_config)
    grouped = _group_by_topic(included)

    confidence_reasons = _confidence_reasons(prepared, included, scoring_config, excluded_by_cap)
    packet_dict: dict[str, Any] = {
        "schema_version": SOCIAL_SIGNAL_SCHEMA_VERSION,
        "status": "completed" if included else "blocked",
        "query": _compact_string(query),
        "entity": _compact_string(entity) or None,
        "topic": _compact_string(topic) or _infer_packet_topic(included, prepared),
        "time_window": time_window if time_window is not None else _time_window_from_items(prepared),
        "platforms_sampled": sorted(_unique_strings(item.platform for item in prepared)),
        "communities_sampled": sorted(_unique_strings(item.community for item in prepared)),
        "item_counts": _item_counts(prepared, included, excluded_by_cap),
        "topic_clusters": _topic_clusters(grouped),
        "raw_sentiment_counts_by_topic": _raw_sentiment_counts(grouped),
        "raw_stance_counts_by_topic": _raw_stance_counts(grouped),
        "engagement_weighted_sentiment_by_topic": _weighted_sentiment_by_topic(
            grouped,
            weight_name="engagement_weight",
        ),
        "recency_weighted_sentiment_by_topic": _weighted_sentiment_by_topic(
            grouped,
            weight_name="recency_weight",
        ),
        "representative_high_engagement_examples": _representative_examples(
            grouped,
            raw_storage_allowed=raw_storage_allowed,
        ),
        "high_engagement_dissenting_examples": _dissenting_examples(
            grouped,
            raw_storage_allowed=raw_storage_allowed,
        ),
        "complaint_clusters": _polarity_clusters(grouped, polarity="complaint"),
        "praise_clusters": _polarity_clusters(grouped, polarity="praise"),
        "missing_metadata_counts": _missing_metadata_counts(prepared),
        "spam_duplicate_brigading_caveats": _spam_duplicate_caveats(prepared, scoring_config),
        "platform_sample_bias_caveats": _platform_bias_caveats(prepared, scoring_config),
        "confidence_level": _confidence_level(confidence_reasons, len(included)),
        "confidence_reasons": confidence_reasons,
        "source_references": _source_references(included) if raw_storage_allowed else [],
        "source_tool": source_tool,
        "official_access": official_access,
        "access_method": access_method,
        "retention_deadline": retention_deadline,
        "deletion_check_due": deletion_check_due,
        "redistribution_allowed": redistribution_allowed,
        "attribution_required": attribution_required,
        "policy_basis": policy_basis,
        "raw_storage_allowed": raw_storage_allowed,
        "commercial_use_allowed": commercial_use_allowed,
        **EVIDENCE_BOUNDARY_REQUIRED_VALUES,
    }
    return parse_social_signal_packet(packet_dict)


def engagement_raw(item: Mapping[str, Any]) -> int:
    total = 0
    for field_name in POSITIVE_ENGAGEMENT_FIELDS:
        total += _nonnegative_int(item.get(field_name)) or 0
    return total


def engagement_weight(raw_engagement: int, *, cap: int = DEFAULT_ENGAGEMENT_CAP) -> float:
    capped = max(0, min(_nonnegative_int(raw_engagement) or 0, max(0, cap)))
    return 1.0 + log1p(capped)


def recency_weight(
    created_at: datetime | str | None,
    *,
    reference_time: datetime | str | None = None,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    created = _parse_datetime(created_at)
    reference = _parse_datetime(reference_time) or datetime.now(timezone.utc)
    if created is None or half_life_days <= 0:
        return 1.0
    age_seconds = max(0.0, (reference - created).total_seconds())
    age_days = age_seconds / 86400.0
    return 0.5 ** (age_days / half_life_days)


def assign_topic(item: Mapping[str, Any]) -> str:
    fixture_label = (
        item.get("topic")
        or item.get("aspect")
        or item.get("topic_label")
        or item.get("aspect_label")
    )
    label = _slug(fixture_label)
    if label:
        return label

    text = " ".join(
        str(item.get(key) or "")
        for key in ("text", "title", "community", "channel", "forum")
    ).casefold()
    keyword_topics = (
        (
            "delivery_logistics",
            (
                "delivery",
                "shipping",
                "ship",
                "arrived",
                "arrival",
                "box",
                "damaged",
                "fedex",
                "ups",
                "logistics",
            ),
        ),
        (
            "customer_support",
            (
                "support",
                "service",
                "warranty",
                "refund",
                "return",
                "chat",
                "phone",
                "customer",
            ),
        ),
        (
            "picture_quality",
            (
                "picture",
                "panel",
                "brightness",
                "color",
                "contrast",
                "hdr",
                "black level",
                "image",
                "motion",
            ),
        ),
        (
            "price_value",
            (
                "price",
                "value",
                "deal",
                "cheap",
                "expensive",
                "worth",
            ),
        ),
        (
            "adoption_momentum",
            (
                "switched",
                "adopted",
                "using",
                "installed",
                "everyone",
                "popular",
            ),
        ),
    )
    for topic_name, keywords in keyword_topics:
        if any(keyword in text for keyword in keywords):
            return topic_name
    return "general_discussion"


def normalize_sentiment(item: Mapping[str, Any]) -> str:
    fixture_label = item.get("sentiment") or item.get("sentiment_label")
    label = _slug(fixture_label)
    if label in SENTIMENT_SCORES:
        if label == "praise":
            return "positive"
        if label in {"complaint", "critical", "opposed"}:
            return "negative"
        return label

    text = str(item.get("text") or "").casefold()
    negative_terms = (
        "bad",
        "awful",
        "terrible",
        "broken",
        "complaint",
        "late",
        "delayed",
        "damaged",
        "refund",
        "angry",
        "hate",
    )
    positive_terms = (
        "good",
        "great",
        "excellent",
        "love",
        "bright",
        "impressed",
        "recommend",
        "happy",
        "praise",
    )
    negative = any(term in text for term in negative_terms)
    positive = any(term in text for term in positive_terms)
    if positive and not negative:
        return "positive"
    if negative and not positive:
        return "negative"
    if positive and negative:
        return "mixed"
    return "unknown"


def sentiment_score(sentiment: str | None) -> float:
    return SENTIMENT_SCORES.get(_slug(sentiment) or "unknown", 0.0)


def _prepare_items(
    items: Sequence[Mapping[str, Any]],
    *,
    reference_time: datetime,
    config: SocialSignalScoringConfig,
) -> list[_PreparedSocialItem]:
    prepared: list[_PreparedSocialItem] = []
    seen_text: set[str] = set()
    for index, item in enumerate(items):
        text = _compact_string(item.get("text"), limit=600)
        normalized_text = " ".join(text.casefold().split())
        explicit_duplicate = _truthy_marker(item, "duplicate", "is_duplicate") or bool(
            item.get("duplicate_of")
        )
        explicit_spam = _truthy_marker(
            item,
            "spam",
            "is_spam",
            "brigading",
            "brigaded",
            "brigading_marker",
        )
        text_duplicate = bool(normalized_text and normalized_text in seen_text)
        if normalized_text:
            seen_text.add(normalized_text)

        raw = engagement_raw(item)
        capped = min(raw, max(0, config.engagement_cap))
        created_at = _parse_datetime(item.get("created_at"))
        missing_any_engagement = not any(_nonnegative_int(item.get(field_name)) is not None for field_name in ENGAGEMENT_FIELDS)
        duplicate_or_spam = explicit_duplicate or explicit_spam or text_duplicate
        duplicate_or_spam_reason = None
        if duplicate_or_spam:
            if explicit_spam:
                duplicate_or_spam_reason = "spam_or_brigading_marker"
            else:
                duplicate_or_spam_reason = "duplicate_marker_or_duplicate_text"

        prepared.append(
            _PreparedSocialItem(
                original=item,
                index=index,
                platform=_compact_string(item.get("platform")) or "unknown_platform",
                community=_compact_string(
                    item.get("community") or item.get("channel") or item.get("forum")
                )
                or "unknown_community",
                topic=assign_topic(item),
                sentiment=normalize_sentiment(item),
                stance=_optional_slug(item.get("stance") or item.get("stance_label")),
                text=text,
                created_at=created_at,
                author_key=_compact_string(item.get("author_key") or item.get("author_hash")) or None,
                thread_id=_compact_string(item.get("thread_id")) or None,
                item_id=_compact_string(item.get("item_id")) or None,
                parent_id=_compact_string(item.get("parent_id")) or None,
                source_reference=_source_reference(item),
                engagement_raw=raw,
                engagement_capped=capped,
                engagement_weight=1.0 + log1p(capped),
                recency_weight=recency_weight(
                    created_at,
                    reference_time=reference_time,
                    half_life_days=config.half_life_days,
                ),
                missing_any_engagement=missing_any_engagement,
                duplicate_or_spam=duplicate_or_spam,
                duplicate_or_spam_reason=duplicate_or_spam_reason,
            )
        )
    return prepared


def _apply_caps(
    prepared: Sequence[_PreparedSocialItem],
    config: SocialSignalScoringConfig,
) -> tuple[list[_PreparedSocialItem], Counter[str]]:
    included: list[_PreparedSocialItem] = []
    excluded = Counter()
    author_topic_counts: Counter[tuple[str, str]] = Counter()
    thread_topic_counts: Counter[tuple[str, str]] = Counter()

    ordered = sorted(
        prepared,
        key=lambda item: (item.topic, -item.engagement_capped, item.index),
    )
    for item in ordered:
        if item.duplicate_or_spam:
            excluded["duplicate_or_spam"] += 1
            continue
        if item.author_key:
            author_key = (item.topic, item.author_key)
            if author_topic_counts[author_key] >= config.per_author_topic_cap:
                excluded["per_author_cap"] += 1
                continue
            author_topic_counts[author_key] += 1
        if item.thread_id:
            thread_key = (item.topic, item.thread_id)
            if thread_topic_counts[thread_key] >= config.per_thread_topic_cap:
                excluded["per_thread_cap"] += 1
                continue
            thread_topic_counts[thread_key] += 1
        included.append(item)
    included.sort(key=lambda item: item.index)
    return included, excluded


def _group_by_topic(items: Sequence[_PreparedSocialItem]) -> dict[str, list[_PreparedSocialItem]]:
    grouped: dict[str, list[_PreparedSocialItem]] = defaultdict(list)
    for item in items:
        grouped[item.topic].append(item)
    return dict(sorted(grouped.items()))


def _topic_clusters(grouped: Mapping[str, Sequence[_PreparedSocialItem]]) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    for topic, items in grouped.items():
        sentiment_counts = Counter(item.sentiment for item in items)
        top_sentiment = sentiment_counts.most_common(1)[0][0] if sentiment_counts else "unknown"
        clusters.append(
            {
                "topic": topic,
                "item_count": len(items),
                "dominant_sentiment": top_sentiment,
                "raw_sentiment_counts": dict(sorted(sentiment_counts.items())),
                "summary": _topic_summary(topic, sentiment_counts),
            }
        )
    return clusters


def _raw_sentiment_counts(
    grouped: Mapping[str, Sequence[_PreparedSocialItem]],
) -> dict[str, dict[str, int]]:
    return {
        topic: dict(sorted(Counter(item.sentiment for item in items).items()))
        for topic, items in grouped.items()
    }


def _raw_stance_counts(
    grouped: Mapping[str, Sequence[_PreparedSocialItem]],
) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for topic, items in grouped.items():
        counts = Counter(item.stance for item in items if item.stance)
        out[topic] = dict(sorted(counts.items()))
    return out


def _weighted_sentiment_by_topic(
    grouped: Mapping[str, Sequence[_PreparedSocialItem]],
    *,
    weight_name: str,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for topic, items in grouped.items():
        total_weight = 0.0
        weighted_sum = 0.0
        for item in items:
            weight = getattr(item, weight_name)
            total_weight += weight
            weighted_sum += sentiment_score(item.sentiment) * weight
        score = weighted_sum / total_weight if total_weight else 0.0
        out[topic] = {
            "score": round(score, 4),
            "label": _score_label(score),
            "weighted_item_count": round(total_weight, 4),
            "model": weight_name,
        }
    return out


def _representative_examples(
    grouped: Mapping[str, Sequence[_PreparedSocialItem]],
    *,
    per_topic: int = 2,
    raw_storage_allowed: bool = False,
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for topic, items in grouped.items():
        top_items = sorted(items, key=lambda item: (-item.engagement_capped, item.index))[:per_topic]
        examples.extend(
            _example(item, topic=topic, raw_storage_allowed=raw_storage_allowed)
            for item in top_items
        )
    return examples


def _dissenting_examples(
    grouped: Mapping[str, Sequence[_PreparedSocialItem]],
    *,
    per_topic: int = 1,
    raw_storage_allowed: bool = False,
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for topic, items in grouped.items():
        sentiment_counts = Counter(item.sentiment for item in items)
        if len(sentiment_counts) <= 1:
            continue
        majority = sentiment_counts.most_common(1)[0][0]
        dissent = [item for item in items if item.sentiment != majority]
        dissent.sort(key=lambda item: (-item.engagement_capped, item.index))
        examples.extend(
            _example(item, topic=topic, raw_storage_allowed=raw_storage_allowed)
            for item in dissent[:per_topic]
        )
    return examples


def _polarity_clusters(
    grouped: Mapping[str, Sequence[_PreparedSocialItem]],
    *,
    polarity: str,
) -> list[dict[str, Any]]:
    target_sentiments = {"negative"} if polarity == "complaint" else {"positive"}
    clusters: list[dict[str, Any]] = []
    for topic, items in grouped.items():
        matching = [item for item in items if item.sentiment in target_sentiments]
        if not matching:
            continue
        clusters.append(
            {
                "topic": topic,
                "count": len(matching),
                "sentiment": "negative" if polarity == "complaint" else "positive",
                "summary": f"{len(matching)} sampled {polarity} signal(s) about {topic}.",
            }
        )
    return clusters


def _example(
    item: _PreparedSocialItem,
    *,
    topic: str,
    raw_storage_allowed: bool,
) -> dict[str, Any]:
    example = {
        "topic": topic,
        "platform": item.platform,
        "community": item.community,
        "sanitized_excerpt": _sanitized_excerpt(item),
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "sentiment": item.sentiment,
        "stance": item.stance,
        "engagement_raw": item.engagement_raw,
        "engagement_capped": item.engagement_capped,
        "engagement_weight": round(item.engagement_weight, 4),
        "recency_weight": round(item.recency_weight, 4),
    }
    if raw_storage_allowed:
        example.update(
            {
                "thread_id": item.thread_id,
                "item_id": item.item_id,
                "parent_id": item.parent_id,
                "author_key": item.author_key,
                "text": item.text,
                "source_reference_url": item.source_reference,
            }
        )
    return example


def _sanitized_excerpt(item: _PreparedSocialItem) -> str:
    topic_text = item.topic.replace("_", " ")
    sentiment_text = item.sentiment or "sampled"
    return f"Sampled {sentiment_text} discussion about {topic_text}."


def _item_counts(
    prepared: Sequence[_PreparedSocialItem],
    included: Sequence[_PreparedSocialItem],
    excluded_by_cap: Counter[str],
) -> dict[str, int]:
    duplicate_or_spam = sum(1 for item in prepared if item.duplicate_or_spam)
    return {
        "input_items": len(prepared),
        "included_items": len(included),
        "excluded_duplicate_or_spam": duplicate_or_spam,
        "excluded_by_per_author_cap": excluded_by_cap.get("per_author_cap", 0),
        "excluded_by_per_thread_cap": excluded_by_cap.get("per_thread_cap", 0),
    }


def _missing_metadata_counts(prepared: Sequence[_PreparedSocialItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for field_name in ENGAGEMENT_FIELDS:
        counts[f"missing_{field_name}"] = sum(
            1 for item in prepared if _nonnegative_int(item.original.get(field_name)) is None
        )
    counts["items_missing_any_engagement"] = sum(1 for item in prepared if item.missing_any_engagement)
    counts["missing_author_key"] = sum(1 for item in prepared if not item.author_key)
    counts["missing_thread_id"] = sum(1 for item in prepared if not item.thread_id)
    counts["missing_created_at"] = sum(1 for item in prepared if item.created_at is None)
    return counts


def _confidence_reasons(
    prepared: Sequence[_PreparedSocialItem],
    included: Sequence[_PreparedSocialItem],
    config: SocialSignalScoringConfig,
    excluded_by_cap: Counter[str],
) -> list[str]:
    reasons: list[str] = []
    if len(included) < config.minimum_included_items:
        reasons.append("insufficient_sample")
    if any(item.missing_any_engagement for item in prepared):
        reasons.append("missing_engagement_metadata")
    if _dominance_ratio(item.platform for item in prepared) > config.platform_dominance_threshold:
        reasons.append("platform_bias_too_high")
    if _dominance_ratio(item.community for item in prepared) > config.community_dominance_threshold:
        reasons.append("platform_bias_too_high")
    duplicate_or_spam_count = sum(1 for item in prepared if item.duplicate_or_spam)
    if prepared and duplicate_or_spam_count / len(prepared) > config.duplicate_spam_dominance_threshold:
        reasons.append("duplicate_or_spam_dominance")
    if excluded_by_cap.get("per_author_cap"):
        reasons.append("per_author_cap_applied")
    if excluded_by_cap.get("per_thread_cap"):
        reasons.append("per_thread_cap_applied")
    return _unique_strings(reasons)


def _confidence_level(reasons: Sequence[str], included_count: int) -> str:
    severe = {"insufficient_sample", "duplicate_or_spam_dominance"}
    if included_count == 0 or any(reason in severe for reason in reasons) or len(reasons) >= 3:
        return "low"
    if reasons:
        return "medium"
    return "high"


def _spam_duplicate_caveats(
    prepared: Sequence[_PreparedSocialItem],
    config: SocialSignalScoringConfig,
) -> list[str]:
    duplicate_or_spam_count = sum(1 for item in prepared if item.duplicate_or_spam)
    if not duplicate_or_spam_count:
        return []
    ratio = duplicate_or_spam_count / len(prepared) if prepared else 0.0
    caveats = [
        f"{duplicate_or_spam_count} duplicate/spam-marked item(s) suppressed before aggregation.",
    ]
    if ratio > config.duplicate_spam_dominance_threshold:
        caveats.append("duplicate_or_spam_dominance")
    return caveats


def _platform_bias_caveats(
    prepared: Sequence[_PreparedSocialItem],
    config: SocialSignalScoringConfig,
) -> list[str]:
    caveats: list[str] = []
    platform_ratio = _dominance_ratio(item.platform for item in prepared)
    community_ratio = _dominance_ratio(item.community for item in prepared)
    if platform_ratio > config.platform_dominance_threshold:
        caveats.append("platform_bias_too_high")
        caveats.append("One sampled platform dominates the packet.")
    if community_ratio > config.community_dominance_threshold:
        caveats.append("One sampled community/channel dominates the packet.")
    return _unique_strings(caveats)


def _source_references(items: Sequence[_PreparedSocialItem]) -> list[str]:
    return sorted(_unique_strings(item.source_reference for item in items if item.source_reference))


def _source_reference(item: Mapping[str, Any]) -> str | None:
    if item.get("source_reference_allowed") is False:
        return None
    return _compact_string(
        item.get("source_reference_url")
        or item.get("source_url")
        or item.get("url"),
        limit=400,
    ) or None


def _time_window_from_items(prepared: Sequence[_PreparedSocialItem]) -> dict[str, str | None]:
    dates = sorted(item.created_at for item in prepared if item.created_at is not None)
    return {
        "start": dates[0].date().isoformat() if dates else None,
        "end": dates[-1].date().isoformat() if dates else None,
    }


def _infer_packet_topic(
    included: Sequence[_PreparedSocialItem],
    prepared: Sequence[_PreparedSocialItem],
) -> str:
    topic_counts = Counter(item.topic for item in included or prepared)
    if not topic_counts:
        return "social_signal"
    if len(topic_counts) == 1:
        return topic_counts.most_common(1)[0][0]
    return "multi_topic_social_signal"


def _topic_summary(topic: str, sentiment_counts: Counter[str]) -> str:
    if not sentiment_counts:
        return f"No included sampled discussion about {topic}."
    pieces = ", ".join(f"{sentiment}={count}" for sentiment, count in sorted(sentiment_counts.items()))
    return f"Sampled discussion about {topic}: {pieces}."


def _score_label(score: float) -> str:
    if score >= 0.2:
        return "positive"
    if score <= -0.2:
        return "negative"
    return "mixed_or_neutral"


def _dominance_ratio(values: Sequence[str] | Any) -> float:
    items = [value for value in values if value]
    if not items:
        return 0.0
    counts = Counter(items)
    return counts.most_common(1)[0][1] / len(items)


def _truthy_marker(item: Mapping[str, Any], *field_names: str) -> bool:
    return any(item.get(field_name) is True for field_name in field_names)


def _parse_datetime(value: datetime | str | None) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _optional_slug(value: Any) -> str | None:
    slug = _slug(value)
    return slug or None


def _slug(value: Any) -> str:
    text = _compact_string(value).casefold()
    if not text:
        return ""
    out = []
    last_was_sep = False
    for char in text:
        if char.isalnum():
            out.append(char)
            last_was_sep = False
        elif not last_was_sep:
            out.append("_")
            last_was_sep = True
    return "".join(out).strip("_")


def _compact_string(value: Any, *, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def _unique_strings(values: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _compact_string(value)
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return out
