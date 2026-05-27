from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.social_signal_schema import (
    AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL,
    EVIDENCE_BOUNDARY_REQUIRED_VALUES,
    SOCIAL_SIGNAL_SCHEMA_VERSION,
    SocialSignalPacketValidationError,
    author_boundary_block_reasons,
    build_author_safe_social_signal_digest,
    can_merge_into_ordinary_evidence_registry,
    is_social_signal_factual_evidence,
    parse_social_signal_packet,
    validate_social_signal_packet,
)
from core.social_signal_scoring import build_social_signal_packet_from_items

_ROOT = Path(__file__).resolve().parents[1]
_SOCIAL_MODULE_PATHS = (
    _ROOT / "core" / "social_signal_schema.py",
    _ROOT / "core" / "social_signal_scoring.py",
)


def _schema_items() -> list[dict[str, object]]:
    return [
        {
            "platform": "fixture_forum",
            "community": "display-owners",
            "thread_id": "thread-product",
            "item_id": "item-picture",
            "author_key": "RAW_USER_123_SHOULD_NOT_REACH_AUTHOR",
            "text": "RAW_COMMENT_SHOULD_NOT_REACH_AUTHOR: picture quality is excellent.",
            "created_at": "2026-05-12T10:00:00+00:00",
            "topic": "picture_quality",
            "sentiment": "positive",
            "stance": "supportive",
            "upvotes": 120,
            "likes": 12,
            "replies": 4,
            "source_reference_url": "https://example.invalid/social/thread-product",
        },
        {
            "platform": "fixture_forum",
            "community": "display-owners",
            "thread_id": "thread-delivery",
            "item_id": "item-delivery",
            "author_hash": "RAW_HASH_456_SHOULD_NOT_REACH_AUTHOR",
            "text": "RAW_DELIVERY_COMMENT_SHOULD_NOT_REACH_AUTHOR: delivery was late.",
            "created_at": "2026-05-13T10:00:00+00:00",
            "topic": "delivery_logistics",
            "sentiment": "negative",
            "stance": "critical",
            "upvotes": 1,
            "likes": 0,
            "replies": 0,
        },
        {
            "platform": "fixture_forum",
            "community": "display-owners",
            "thread_id": "thread-support",
            "item_id": "item-support",
            "author_key": "RAW_USER_789_SHOULD_NOT_REACH_AUTHOR",
            "text": "Support chat helped me replace a damaged box.",
            "created_at": "2026-05-14T10:00:00+00:00",
            "topic": "customer_support",
            "sentiment": "positive",
            "stance": "supportive",
            "upvotes": 2,
            "likes": 1,
            "replies": 1,
        },
    ]


def _good_packet_dict() -> dict[str, object]:
    packet = build_social_signal_packet_from_items(
        _schema_items(),
        query="What are owners saying about the TCL TV?",
        entity="TCL QM8",
        topic="TCL TV owner discussion",
        time_window={"start": "2026-05-12", "end": "2026-05-14"},
        reference_time="2026-05-15T00:00:00+00:00",
    )
    return packet.to_dict()


def test_packet_validates_good_fixture() -> None:
    packet_dict = _good_packet_dict()

    result = validate_social_signal_packet(packet_dict)
    packet = parse_social_signal_packet(packet_dict)

    assert result.valid is True
    assert result.status == "completed"
    assert packet.schema_version == SOCIAL_SIGNAL_SCHEMA_VERSION
    assert packet.may_support_factual_claims is False
    assert packet.may_support_claims_about_sampled_sentiment is True
    assert packet.raw_packet_to_author_allowed is False
    assert packet.raw_comments_to_author_allowed is False
    assert packet.raw_storage_allowed is False
    assert packet.source_references == ()
    assert packet.representative_high_engagement_examples
    assert "sanitized_excerpt" in packet.representative_high_engagement_examples[0]
    assert "text" not in packet.representative_high_engagement_examples[0]


def test_packet_rejects_missing_boundary_fields() -> None:
    packet_dict = _good_packet_dict()
    packet_dict.pop("may_support_factual_claims")

    result = validate_social_signal_packet(packet_dict)

    assert result.valid is False
    assert result.status == "invalid"
    assert "packet_validation_failed" in result.reasons
    with pytest.raises(SocialSignalPacketValidationError) as exc:
        parse_social_signal_packet(packet_dict)
    assert "packet_validation_failed" in exc.value.reasons


@pytest.mark.parametrize(
    ("field_name", "expected_reason"),
    [
        ("may_support_factual_claims", "factual_claim_boundary_violation"),
        ("may_support_claims_about_sampled_sentiment", "packet_validation_failed"),
        ("raw_packet_to_author_allowed", "raw_packet_author_blocked"),
        ("raw_comments_to_author_allowed", "raw_packet_author_blocked"),
        ("ordinary_evidence_registry_merge_allowed", "ordinary_evidence_merge_blocked"),
        ("analyst_review_required_before_author", "packet_validation_failed"),
    ],
)
def test_packet_rejects_boundary_value_drift(field_name: str, expected_reason: str) -> None:
    packet_dict = _good_packet_dict()
    packet_dict[field_name] = not EVIDENCE_BOUNDARY_REQUIRED_VALUES[field_name]

    result = validate_social_signal_packet(packet_dict)

    assert result.valid is False
    assert expected_reason in result.reasons


def test_packet_rejects_factual_claim_supporting_boundary_values() -> None:
    packet_dict = _good_packet_dict()
    packet_dict["may_support_factual_claims"] = True

    result = validate_social_signal_packet(packet_dict)

    assert result.valid is False
    assert "factual_claim_boundary_violation" in result.reasons
    with pytest.raises(SocialSignalPacketValidationError):
        parse_social_signal_packet(packet_dict)


@pytest.mark.parametrize("field_name", ["item_counts", "topic_clusters"])
def test_completed_packet_requires_included_items_and_topic_clusters(field_name: str) -> None:
    packet_dict = _good_packet_dict()
    if field_name == "item_counts":
        packet_dict["item_counts"] = {
            **packet_dict["item_counts"],
            "included_items": 0,
        }
    else:
        packet_dict["topic_clusters"] = []

    result = validate_social_signal_packet(packet_dict)

    assert result.valid is False
    assert "packet_validation_failed" in result.reasons


@pytest.mark.parametrize("status", ["blocked", "invalid"])
def test_non_completed_packet_cannot_claim_social_signal_available(status: str) -> None:
    packet_dict = _good_packet_dict()
    packet_dict["status"] = status
    packet_dict["social_signal_available"] = True

    result = validate_social_signal_packet(packet_dict)

    assert result.valid is False
    assert "packet_validation_failed" in result.reasons


def test_raw_example_fields_require_raw_storage_allowed() -> None:
    packet_dict = _good_packet_dict()
    packet_dict["representative_high_engagement_examples"] = [
        {
            "topic": "picture_quality",
            "text": "RAW_COMMENT_SHOULD_NOT_BE_STORED",
            "author_key": "RAW_AUTHOR_SHOULD_NOT_BE_STORED",
            "thread_id": "thread-product",
            "item_id": "item-picture",
            "source_reference_url": "https://example.invalid/raw",
        }
    ]

    result = validate_social_signal_packet(packet_dict)

    assert result.valid is False
    assert "raw_storage_not_allowed" in result.reasons


def test_source_references_require_raw_storage_allowed() -> None:
    packet_dict = _good_packet_dict()
    packet_dict["source_references"] = ["https://example.invalid/social/thread-product"]

    result = validate_social_signal_packet(packet_dict)

    assert result.valid is False
    assert "raw_storage_not_allowed" in result.reasons


def test_social_signal_is_not_factual_evidence() -> None:
    packet = parse_social_signal_packet(_good_packet_dict())

    assert is_social_signal_factual_evidence(packet) is False
    assert packet.may_support_factual_claims is False
    assert packet.may_support_claims_about_sampled_sentiment is True


def test_social_signal_packet_is_not_ordinary_evidence_registry_material() -> None:
    packet = parse_social_signal_packet(_good_packet_dict())

    assert can_merge_into_ordinary_evidence_registry(packet) is False
    assert packet.ordinary_evidence_registry_merge_allowed is False
    assert "ordinary_evidence_merge_blocked" in author_boundary_block_reasons(packet)


def test_sanitized_digest_removes_raw_comments_user_ids_and_packet_internals() -> None:
    packet = parse_social_signal_packet(_good_packet_dict())

    digest = build_author_safe_social_signal_digest(packet)
    encoded = json.dumps(digest, sort_keys=True)

    assert digest["label"] == AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL
    assert "RAW_COMMENT_SHOULD_NOT_REACH_AUTHOR" not in encoded
    assert "RAW_DELIVERY_COMMENT_SHOULD_NOT_REACH_AUTHOR" not in encoded
    assert "RAW_USER_123_SHOULD_NOT_REACH_AUTHOR" not in encoded
    assert "RAW_HASH_456_SHOULD_NOT_REACH_AUTHOR" not in encoded
    assert "thread-product" not in encoded
    assert "item-picture" not in encoded
    assert "parent_id" not in encoded
    assert "source_tool" not in encoded
    assert "source_references" not in encoded
    assert "source_reference_url" not in encoded
    assert "text" not in encoded
    assert "author_key" not in encoded
    assert "author_hash" not in encoded


def test_author_digest_recursively_excludes_raw_nested_packet_internals() -> None:
    packet = build_social_signal_packet_from_items(
        _schema_items(),
        query="What are owners saying about the TCL TV?",
        entity="TCL QM8",
        topic="TCL TV owner discussion",
        reference_time="2026-05-15T00:00:00+00:00",
        raw_storage_allowed=True,
    ).to_dict()
    packet["complaint_clusters"] = [
        {
            "topic": "delivery_logistics",
            "count": 1,
            "sentiment": "negative",
            "summary": "RAW_COMMENT_SHOULD_NOT_REACH_AUTHOR",
            "raw_comments": ["RAW_NESTED_COMMENT_SHOULD_NOT_REACH_AUTHOR"],
            "source_reference_url": "https://example.invalid/raw-thread",
        }
    ]
    packet["confidence_reasons"] = [
        "missing_engagement_metadata",
        "RAW_USER_ID_SHOULD_NOT_REACH_AUTHOR",
    ]

    digest = build_author_safe_social_signal_digest(packet)
    encoded = json.dumps(digest, sort_keys=True)

    assert digest["author_safe"] is True
    assert "RAW_COMMENT_SHOULD_NOT_REACH_AUTHOR" not in encoded
    assert "RAW_NESTED_COMMENT_SHOULD_NOT_REACH_AUTHOR" not in encoded
    assert "RAW_USER_ID_SHOULD_NOT_REACH_AUTHOR" not in encoded
    assert '"raw_comments"' not in encoded
    assert "source_reference_url" not in encoded
    assert "representative_high_engagement_examples" not in encoded


def test_raw_packet_and_comments_are_not_allowed_to_author() -> None:
    packet = parse_social_signal_packet(_good_packet_dict())
    digest = build_author_safe_social_signal_digest(packet)

    assert packet.raw_packet_to_author_allowed is False
    assert packet.raw_comments_to_author_allowed is False
    assert digest["raw_packet_to_author_allowed"] is False
    assert digest["raw_comments_to_author_allowed"] is False
    assert "raw_packet_author_blocked" in author_boundary_block_reasons(packet)


def test_political_perception_packet_does_not_become_truth_or_polling_claim() -> None:
    packet = build_social_signal_packet_from_items(
        [
            {
                "platform": "fixture_forum",
                "community": "current-events",
                "thread_id": "debate-thread",
                "item_id": "debate-1",
                "author_key": "author-a",
                "text": "People in this thread say Candidate A sounded more prepared.",
                "created_at": "2026-05-16T10:00:00+00:00",
                "topic": "debate_reaction",
                "sentiment": "positive",
                "stance": "supports_candidate_a",
                "upvotes": 3,
            },
            {
                "platform": "fixture_forum",
                "community": "current-events",
                "thread_id": "debate-thread",
                "item_id": "debate-2",
                "author_key": "author-b",
                "text": "Others say Candidate B had the better answer.",
                "created_at": "2026-05-16T11:00:00+00:00",
                "topic": "debate_reaction",
                "sentiment": "positive",
                "stance": "supports_candidate_b",
                "upvotes": 2,
            },
            {
                "platform": "fixture_forum",
                "community": "current-events",
                "thread_id": "debate-thread",
                "item_id": "debate-3",
                "author_key": "author-c",
                "text": "A third commenter thought neither answer changed their mind.",
                "created_at": "2026-05-16T12:00:00+00:00",
                "topic": "debate_reaction",
                "sentiment": "neutral",
                "stance": "undecided",
                "upvotes": 1,
            },
        ],
        query="Who won the debate on social media?",
        entity="Candidate debate",
        topic="debate reaction",
        reference_time="2026-05-17T00:00:00+00:00",
    )

    digest = build_author_safe_social_signal_digest(packet)

    assert packet.may_support_factual_claims is False
    assert digest["may_support_factual_claims"] is False
    assert "Not a statistically representative poll." in digest["caveats"]
    assert digest["topics"][0]["raw_stance_counts"] == {
        "supports_candidate_a": 1,
        "supports_candidate_b": 1,
        "undecided": 1,
    }


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_social_signal_modules_static_import_guard() -> None:
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.llm",
        "core.prompts",
        "core.search_providers",
        "core.db",
        "core.storage",
        "core.run_logging",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.routing",
        "core.scout",
        "core.source_class_recovery",
        "core.weak_corpus_recovery",
    )
    forbidden_terms = (
        "ask_model",
        "process_search_queries",
        "select_providers",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "run_source_class_recovery",
        "run_weak_corpus_recovery",
        "choose_retrieval_search_depth",
    )

    for path in _SOCIAL_MODULE_PATHS:
        violations = [
            name
            for name in _imported_names(path)
            for prefix in forbidden_import_prefixes
            if name == prefix or name.startswith(prefix + ".")
        ]
        source = path.read_text(encoding="utf-8")

        assert violations == []
        assert all(term not in source for term in forbidden_terms)
