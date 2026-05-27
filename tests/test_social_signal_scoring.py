from __future__ import annotations

import json

from core.social_signal_schema import build_author_safe_social_signal_digest
from core.social_signal_scoring import (
    SocialSignalScoringConfig,
    build_social_signal_packet_from_items,
    engagement_raw,
    engagement_weight,
    recency_weight,
)


def _tcl_tv_items() -> list[dict[str, object]]:
    items: list[dict[str, object]] = [
        {
            "platform": "fixture_forum",
            "community": "tcl-tv-owners",
            "thread_id": "picture-thread",
            "item_id": "picture-positive",
            "author_key": "owner-picture",
            "text": "The TCL picture quality is excellent, especially HDR brightness and color.",
            "created_at": "2026-05-10T10:00:00+00:00",
            "topic": "picture_quality",
            "sentiment": "positive",
            "upvotes": 900,
            "likes": 100,
            "replies": 30,
            "shares": 5,
            "source_reference_url": "https://example.invalid/tcl/picture",
        }
    ]
    for index in range(5):
        items.append(
            {
                "platform": "fixture_forum",
                "community": "tcl-tv-owners",
                "thread_id": "delivery-thread",
                "item_id": f"delivery-complaint-{index}",
                "author_key": f"delivery-author-{index}",
                "text": f"Delivery complaint {index}: shipping was late and the box sat in transit.",
                "created_at": f"2026-05-1{index}T10:00:00+00:00",
                "topic": "delivery_logistics",
                "sentiment": "negative",
                "upvotes": 1,
                "likes": 0,
                "replies": 0,
                "shares": 0,
            }
        )
    return items


def test_tcl_tv_fixture_preserves_product_quality_and_delivery_as_separate_clusters() -> None:
    packet = build_social_signal_packet_from_items(
        _tcl_tv_items(),
        query="What are people saying about this TCL TV?",
        entity="TCL TV",
        reference_time="2026-05-20T00:00:00+00:00",
    )

    topics = {cluster["topic"] for cluster in packet.topic_clusters}

    assert {"picture_quality", "delivery_logistics"} <= topics
    assert "tcl_sentiment" not in topics
    assert packet.raw_sentiment_counts_by_topic["picture_quality"] == {"positive": 1}
    assert packet.raw_sentiment_counts_by_topic["delivery_logistics"] == {"negative": 5}
    assert packet.engagement_weighted_sentiment_by_topic["picture_quality"]["label"] == "positive"
    assert packet.engagement_weighted_sentiment_by_topic["delivery_logistics"]["label"] == "negative"
    assert packet.recency_weighted_sentiment_by_topic["picture_quality"]["model"] == "recency_weight"
    assert packet.may_support_factual_claims is False

    picture_examples = [
        example
        for example in packet.representative_high_engagement_examples
        if example["topic"] == "picture_quality"
    ]
    assert picture_examples
    assert picture_examples[0]["engagement_raw"] > 1000
    assert "picture quality" in picture_examples[0]["sanitized_excerpt"]
    assert "text" not in picture_examples[0]
    assert "author_key" not in picture_examples[0]
    assert "thread_id" not in picture_examples[0]
    assert "item_id" not in picture_examples[0]

    delivery_complaints = [
        cluster for cluster in packet.complaint_clusters if cluster["topic"] == "delivery_logistics"
    ]
    assert delivery_complaints[0]["count"] == 5


def test_topic_separation_product_quality_delivery_and_customer_support() -> None:
    packet = build_social_signal_packet_from_items(
        [
            {
                "platform": "forum_a",
                "community": "owners-a",
                "thread_id": "p",
                "item_id": "p1",
                "author_key": "a",
                "text": "The panel contrast looks good.",
                "topic": "picture_quality",
                "sentiment": "positive",
                "upvotes": 3,
            },
            {
                "platform": "forum_b",
                "community": "owners-b",
                "thread_id": "d",
                "item_id": "d1",
                "author_key": "b",
                "text": "Delivery was delayed.",
                "topic": "delivery_logistics",
                "sentiment": "negative",
                "upvotes": 2,
            },
            {
                "platform": "forum_c",
                "community": "owners-c",
                "thread_id": "s",
                "item_id": "s1",
                "author_key": "c",
                "text": "Customer support solved the setup issue.",
                "topic": "customer_support",
                "sentiment": "positive",
                "upvotes": 1,
            },
        ],
        query="Summarize owner discussion by aspect.",
        entity="TCL TV",
        reference_time="2026-05-20T00:00:00+00:00",
    )

    assert {cluster["topic"] for cluster in packet.topic_clusters} == {
        "customer_support",
        "delivery_logistics",
        "picture_quality",
    }
    assert set(packet.engagement_weighted_sentiment_by_topic) == {
        "customer_support",
        "delivery_logistics",
        "picture_quality",
    }


def test_minority_dissent_is_preserved_but_not_over_weighted() -> None:
    items: list[dict[str, object]] = []
    for index in range(6):
        items.append(
            {
                "platform": f"forum_{index % 3}",
                "community": f"owners_{index % 3}",
                "thread_id": f"positive-thread-{index}",
                "item_id": f"positive-{index}",
                "author_key": f"positive-author-{index}",
                "text": f"Picture quality looks strong after calibration from owner {index}.",
                "topic": "picture_quality",
                "sentiment": "positive",
                "upvotes": 20,
            }
        )
    items.append(
        {
            "platform": "forum_dissent",
            "community": "owners_dissent",
            "thread_id": "dissent-thread",
            "item_id": "negative-dissent",
            "author_key": "negative-author",
            "text": "Minority dissent: motion handling still looks bad to me.",
            "topic": "picture_quality",
            "sentiment": "negative",
            "upvotes": 500,
            "replies": 60,
        }
    )

    packet = build_social_signal_packet_from_items(
        items,
        query="What is the picture-quality sentiment?",
        entity="TCL TV",
        reference_time="2026-05-20T00:00:00+00:00",
    )

    weighted = packet.engagement_weighted_sentiment_by_topic["picture_quality"]

    assert packet.raw_sentiment_counts_by_topic["picture_quality"] == {
        "negative": 1,
        "positive": 6,
    }
    assert weighted["label"] == "positive"
    assert 0 < weighted["score"] < 1
    assert packet.high_engagement_dissenting_examples[0]["sentiment"] == "negative"
    assert packet.high_engagement_dissenting_examples[0]["sanitized_excerpt"] == (
        "Sampled negative discussion about picture quality."
    )
    assert "item_id" not in packet.high_engagement_dissenting_examples[0]


def test_platform_bias_caveat_required_for_one_platform_dominance() -> None:
    packet = build_social_signal_packet_from_items(
        _tcl_tv_items(),
        query="What are people saying about this TCL TV?",
        entity="TCL TV",
        reference_time="2026-05-20T00:00:00+00:00",
    )

    assert "platform_bias_too_high" in packet.confidence_reasons
    assert "platform_bias_too_high" in packet.platform_sample_bias_caveats
    assert any("platform" in caveat for caveat in packet.platform_sample_bias_caveats)


def test_missing_engagement_metadata_degrades_confidence() -> None:
    packet = build_social_signal_packet_from_items(
        [
            {
                "platform": "forum_a",
                "community": "owners-a",
                "thread_id": "a",
                "item_id": "a1",
                "author_key": "a",
                "text": "Picture looks good.",
                "topic": "picture_quality",
                "sentiment": "positive",
            },
            {
                "platform": "forum_b",
                "community": "owners-b",
                "thread_id": "b",
                "item_id": "b1",
                "author_key": "b",
                "text": "Delivery was slow.",
                "topic": "delivery_logistics",
                "sentiment": "negative",
            },
            {
                "platform": "forum_c",
                "community": "owners-c",
                "thread_id": "c",
                "item_id": "c1",
                "author_key": "c",
                "text": "Support was fine.",
                "topic": "customer_support",
                "sentiment": "neutral",
            },
        ],
        query="Summarize owner discussion.",
        entity="TCL TV",
        reference_time="2026-05-20T00:00:00+00:00",
    )

    assert packet.missing_metadata_counts["items_missing_any_engagement"] == 3
    assert "missing_engagement_metadata" in packet.confidence_reasons
    assert packet.confidence_level in {"medium", "low"}


def test_duplicate_and_spam_comments_do_not_dominate() -> None:
    items: list[dict[str, object]] = [
        {
            "platform": "forum_a",
            "community": "owners-a",
            "thread_id": "genuine-positive",
            "item_id": "genuine-positive",
            "author_key": "author-positive",
            "text": "Picture quality looks great.",
            "topic": "picture_quality",
            "sentiment": "positive",
            "upvotes": 4,
        },
        {
            "platform": "forum_b",
            "community": "owners-b",
            "thread_id": "genuine-negative",
            "item_id": "genuine-negative",
            "author_key": "author-negative",
            "text": "Motion processing is not good.",
            "topic": "picture_quality",
            "sentiment": "negative",
            "upvotes": 2,
        },
    ]
    for index in range(8):
        items.append(
            {
                "platform": "forum_b",
                "community": "owners-b",
                "thread_id": "spam-thread",
                "item_id": f"spam-{index}",
                "author_key": f"spam-author-{index}",
                "text": "Copy paste complaint about picture quality.",
                "topic": "picture_quality",
                "sentiment": "negative",
                "upvotes": 99,
                "is_spam": True,
            }
        )

    packet = build_social_signal_packet_from_items(
        items,
        query="What are people saying about picture quality?",
        entity="TCL TV",
        reference_time="2026-05-20T00:00:00+00:00",
    )

    assert packet.item_counts["excluded_duplicate_or_spam"] == 8
    assert packet.raw_sentiment_counts_by_topic["picture_quality"] == {
        "negative": 1,
        "positive": 1,
    }
    assert "duplicate_or_spam_dominance" in packet.confidence_reasons
    assert any("suppressed" in caveat for caveat in packet.spam_duplicate_brigading_caveats)


def test_default_packet_examples_are_sanitized_when_raw_storage_is_false() -> None:
    packet = build_social_signal_packet_from_items(
        [
            {
                "platform": "reddit_api_fixture",
                "community": "r/tclowners",
                "thread_id": "raw-thread-1",
                "item_id": "raw-item-1",
                "parent_id": "raw-parent-1",
                "author_key": "RAW_USER_1_SHOULD_NOT_BE_STORED",
                "text": "RAW_COMMENT_1_SHOULD_NOT_BE_STORED: HDR looks great.",
                "topic": "picture_quality",
                "sentiment": "positive",
                "upvotes": 11,
                "source_reference_url": "https://example.invalid/raw-thread-1",
            },
            {
                "platform": "reddit_api_fixture",
                "community": "r/tclowners",
                "thread_id": "raw-thread-2",
                "item_id": "raw-item-2",
                "parent_id": "raw-parent-2",
                "author_key": "RAW_USER_2_SHOULD_NOT_BE_STORED",
                "text": "RAW_COMMENT_2_SHOULD_NOT_BE_STORED: shipping was late.",
                "topic": "delivery_logistics",
                "sentiment": "negative",
                "upvotes": 7,
                "source_reference_url": "https://example.invalid/raw-thread-2",
            },
            {
                "platform": "reddit_api_fixture",
                "community": "r/tclowners",
                "thread_id": "raw-thread-3",
                "item_id": "raw-item-3",
                "parent_id": "raw-parent-3",
                "author_key": "RAW_USER_3_SHOULD_NOT_BE_STORED",
                "text": "RAW_COMMENT_3_SHOULD_NOT_BE_STORED: support fixed my issue.",
                "topic": "customer_support",
                "sentiment": "positive",
                "upvotes": 5,
                "source_reference_url": "https://example.invalid/raw-thread-3",
            },
        ],
        query="What are owners saying?",
        entity="TCL TV",
        source_tool="live_like_fixture",
        access_method="official_api_fixture",
        raw_storage_allowed=False,
    )

    packet_json = json.dumps(packet.to_dict(), sort_keys=True)
    first_example = packet.representative_high_engagement_examples[0]
    digest_json = json.dumps(build_author_safe_social_signal_digest(packet), sort_keys=True)

    assert packet.raw_storage_allowed is False
    assert packet.source_references == ()
    assert "sanitized_excerpt" in first_example
    assert "text" not in first_example
    assert "author_key" not in first_example
    assert "thread_id" not in first_example
    assert "item_id" not in first_example
    assert "parent_id" not in first_example
    assert "source_reference_url" not in first_example
    assert "RAW_COMMENT" not in packet_json
    assert "RAW_USER" not in packet_json
    assert "example.invalid/raw-thread" not in packet_json
    assert "RAW_COMMENT" not in digest_json
    assert "RAW_USER" not in digest_json


def test_raw_storage_allowed_preserves_raw_examples_for_analyst_review_only() -> None:
    packet = build_social_signal_packet_from_items(
        [
            {
                "platform": "fixture_forum",
                "community": "owners",
                "thread_id": "raw-thread",
                "item_id": "raw-item",
                "author_key": "RAW_AUTHOR_ALLOWED_IN_PACKET_ONLY",
                "text": "RAW_COMMENT_ALLOWED_IN_PACKET_ONLY: picture looks great.",
                "topic": "picture_quality",
                "sentiment": "positive",
                "upvotes": 3,
                "source_reference_url": "https://example.invalid/raw-thread",
            }
        ],
        query="What are owners saying?",
        entity="TCL TV",
        raw_storage_allowed=True,
    )

    example = packet.representative_high_engagement_examples[0]
    digest_json = json.dumps(build_author_safe_social_signal_digest(packet), sort_keys=True)

    assert packet.raw_storage_allowed is True
    assert packet.source_references == ("https://example.invalid/raw-thread",)
    assert example["text"] == "RAW_COMMENT_ALLOWED_IN_PACKET_ONLY: picture looks great."
    assert example["author_key"] == "RAW_AUTHOR_ALLOWED_IN_PACKET_ONLY"
    assert example["thread_id"] == "raw-thread"
    assert example["item_id"] == "raw-item"
    assert "RAW_COMMENT_ALLOWED_IN_PACKET_ONLY" not in digest_json
    assert "RAW_AUTHOR_ALLOWED_IN_PACKET_ONLY" not in digest_json
    assert "source_reference_url" not in digest_json


def test_engagement_and_recency_helpers_are_bounded_and_deterministic() -> None:
    high_raw = engagement_raw(
        {
            "upvotes": 1000,
            "likes": 50,
            "replies": 10,
            "reposts": 5,
            "shares": 5,
            "views": 1_000_000,
        }
    )

    assert high_raw == 1070
    assert engagement_weight(high_raw, cap=100) == engagement_weight(100, cap=100)
    assert engagement_weight(0) == 1.0
    assert recency_weight(
        "2026-05-20T00:00:00+00:00",
        reference_time="2026-05-20T00:00:00+00:00",
    ) == 1.0
    assert recency_weight(
        "2026-04-20T00:00:00+00:00",
        reference_time="2026-05-20T00:00:00+00:00",
    ) < 1.0


def test_author_digest_keeps_counts_and_boundary_without_raw_examples() -> None:
    packet = build_social_signal_packet_from_items(
        _tcl_tv_items(),
        query="What are people saying about this TCL TV?",
        entity="TCL TV",
        reference_time="2026-05-20T00:00:00+00:00",
    )

    digest = build_author_safe_social_signal_digest(packet)
    topic_names = {topic["topic"] for topic in digest["topics"]}

    assert {"picture_quality", "delivery_logistics"} <= topic_names
    assert digest["may_support_factual_claims"] is False
    assert digest["ordinary_evidence_registry_merge_allowed"] is False
    assert digest["raw_packet_to_author_allowed"] is False
    assert digest["raw_comments_to_author_allowed"] is False


def test_per_author_and_thread_caps_are_applied() -> None:
    items = [
        {
            "platform": "forum_a",
            "community": "owners-a",
            "thread_id": "same-thread",
            "item_id": f"same-author-{index}",
            "author_key": "same-author",
            "text": f"Repeated praise {index}.",
            "topic": "picture_quality",
            "sentiment": "positive",
            "upvotes": 10 - index,
        }
        for index in range(5)
    ]
    packet = build_social_signal_packet_from_items(
        items,
        query="What are people saying about picture quality?",
        config=SocialSignalScoringConfig(per_author_topic_cap=2, per_thread_topic_cap=4),
    )

    assert packet.item_counts["included_items"] == 2
    assert packet.item_counts["excluded_by_per_author_cap"] == 3
    assert "per_author_cap_applied" in packet.confidence_reasons
