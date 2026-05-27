from __future__ import annotations

import ast
import json
from pathlib import Path

from core.social_signal_controller import (
    SOCIAL_SIGNAL_ACTION_NAME,
    SOCIAL_SIGNAL_EVIDENCE_CLASS,
    SocialSignalControllerInput,
    decide_social_signal_controller,
)
from core.social_signal_schema import AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL
from core.social_signal_scoring import build_social_signal_packet_from_items

_ROOT = Path(__file__).resolve().parents[1]
_CONTROLLER_PATH = _ROOT / "core" / "social_signal_controller.py"


def _fixture_items() -> list[dict[str, object]]:
    return [
        {
            "platform": "fixture_forum",
            "community": "owners",
            "thread_id": "thread-picture",
            "item_id": "item-picture",
            "author_key": "RAW_AUTHOR_A_SHOULD_NOT_REACH_AUTHOR",
            "text": "RAW_COMMENT_A_SHOULD_NOT_REACH_AUTHOR: picture quality looks great.",
            "created_at": "2026-05-10T10:00:00+00:00",
            "topic": "picture_quality",
            "sentiment": "positive",
            "stance": "supportive",
            "upvotes": 8,
        },
        {
            "platform": "fixture_forum",
            "community": "owners",
            "thread_id": "thread-delivery",
            "item_id": "item-delivery",
            "author_key": "RAW_AUTHOR_B_SHOULD_NOT_REACH_AUTHOR",
            "text": "RAW_COMMENT_B_SHOULD_NOT_REACH_AUTHOR: delivery was late.",
            "created_at": "2026-05-11T10:00:00+00:00",
            "topic": "delivery_logistics",
            "sentiment": "negative",
            "stance": "critical",
            "upvotes": 4,
        },
        {
            "platform": "fixture_blog",
            "community": "review-comments",
            "thread_id": "thread-support",
            "item_id": "item-support",
            "author_key": "RAW_AUTHOR_C_SHOULD_NOT_REACH_AUTHOR",
            "text": "RAW_COMMENT_C_SHOULD_NOT_REACH_AUTHOR: support replaced the damaged box.",
            "created_at": "2026-05-12T10:00:00+00:00",
            "topic": "customer_support",
            "sentiment": "positive",
            "stance": "supportive",
            "upvotes": 2,
        },
    ]


def _fixture_packet_dict() -> dict[str, object]:
    return build_social_signal_packet_from_items(
        _fixture_items(),
        query="What are owners saying about this TV?",
        entity="TCL TV",
        topic="owner discussion",
        reference_time="2026-05-15T00:00:00+00:00",
    ).to_dict()


def test_irrelevant_not_explicit_returns_not_applicable_without_packet_or_digest() -> None:
    decision = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="What is the current warranty term?",
            social_signal_relevance="irrelevant",
            explicit_social_signal_requested=False,
        )
    )

    assert decision.action_name == SOCIAL_SIGNAL_ACTION_NAME
    assert decision.status == "not_applicable"
    assert decision.social_signal_status == "not_applicable"
    assert decision.stable_reason_code == "social_relevance_irrelevant"
    assert "social_relevance_irrelevant" in decision.reasons
    assert decision.packet_valid is False
    assert decision.author_digest_or_none is None
    assert decision.provider_call_allowed is False
    assert decision.live_api_call_allowed is False


def test_central_social_query_without_provider_or_packet_returns_provider_unavailable() -> None:
    decision = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="What is Reddit saying about Acme pricing?",
            social_signal_relevance="central",
            social_provider_configured=False,
            packet_or_none=None,
        )
    )

    assert decision.status == "provider_unavailable"
    assert decision.social_signal_status == "provider_unavailable"
    assert decision.social_signal_status != "checked"
    assert decision.stable_reason_code == "social_provider_not_configured"
    assert decision.author_digest_or_none is None


def test_fast_mode_explicit_social_request_is_blocked_without_packet_or_provider() -> None:
    decision = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="Check social reaction to the launch.",
            mode="Fast",
            social_signal_relevance="central",
            explicit_social_signal_requested=True,
        )
    )

    assert decision.status == "blocked"
    assert decision.social_signal_status == "blocked"
    assert decision.stable_reason_code == "fast_mode_blocked"
    assert decision.packet_valid is False
    assert decision.author_digest_or_none is None
    assert decision.provider_call_allowed is False


def test_valid_fixture_packet_returns_checked_author_safe_digest_only() -> None:
    decision = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="What are owners saying about this TV?",
            social_signal_relevance="central",
            explicit_social_signal_requested=True,
            packet_or_none=_fixture_packet_dict(),
        )
    )

    assert decision.status == "checked"
    assert decision.social_signal_status == "checked"
    assert decision.packet_valid is True
    assert decision.side_packet_allowed is True
    assert decision.author_digest_or_none is not None
    assert decision.author_digest_or_none["label"] == AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL
    assert "sampled public discussion signal" in decision.author_digest_or_none["label"].casefold()
    assert "not factual evidence" in decision.author_digest_or_none["label"].casefold()
    assert decision.may_support_factual_claims is False
    assert decision.raw_packet_to_author_allowed is False
    assert decision.raw_comments_to_author_allowed is False

    encoded = json.dumps(decision.to_dict(), sort_keys=True)
    assert "RAW_COMMENT" not in encoded
    assert "RAW_AUTHOR" not in encoded
    assert "thread-picture" not in encoded
    assert "item-picture" not in encoded
    assert "representative_high_engagement_examples" not in encoded
    assert "high_engagement_dissenting_examples" not in encoded


def test_invalid_packet_returns_invalid_packet_without_checked_status_or_digest() -> None:
    packet = _fixture_packet_dict()
    packet["schema_version"] = "not_the_schema"

    decision = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="What are owners saying about this TV?",
            social_signal_relevance="central",
            explicit_social_signal_requested=True,
            packet_or_none=packet,
        )
    )

    assert decision.status == "invalid_packet"
    assert decision.social_signal_status == "invalid_packet"
    assert decision.social_signal_status != "checked"
    assert decision.stable_reason_code == "packet_validation_failed"
    assert "packet_validation_failed" in decision.reasons
    assert decision.packet_valid is False
    assert decision.author_digest_or_none is None


def test_platform_denylist_and_allowlist_reject_disallowed_sampled_platforms() -> None:
    packet = _fixture_packet_dict()

    denied = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="What are owners saying about this TV?",
            social_signal_relevance="central",
            explicit_social_signal_requested=True,
            packet_or_none=packet,
            platform_denylist=("fixture_forum",),
        )
    )
    not_allowed = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="What are owners saying about this TV?",
            social_signal_relevance="central",
            explicit_social_signal_requested=True,
            packet_or_none=packet,
            platform_allowlist=("approved_fixture_only",),
        )
    )

    for decision in (denied, not_allowed):
        assert decision.status == "blocked"
        assert decision.social_signal_status == "blocked"
        assert decision.stable_reason_code == "platform_not_allowed"
        assert "platform_not_allowed" in decision.reasons
        assert decision.packet_valid is True
        assert decision.author_digest_or_none is None


def test_optional_recommendation_social_signal_is_not_requested_unless_explicit_or_packeted() -> None:
    skipped = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="Which TV is the better buy?",
            social_signal_relevance="relevant_optional",
            explicit_social_signal_requested=False,
            social_provider_configured=False,
            packet_or_none=None,
        )
    )
    checked = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="Which TV is the better buy?",
            social_signal_relevance="relevant_optional",
            explicit_social_signal_requested=True,
            packet_or_none=_fixture_packet_dict(),
        )
    )

    assert skipped.status == "not_requested"
    assert skipped.social_signal_status == "not_applicable"
    assert skipped.stable_reason_code == "social_signal_not_requested"
    assert skipped.author_digest_or_none is None
    assert checked.status == "checked"
    assert checked.social_signal_status == "checked"
    assert checked.author_digest_or_none is not None


def test_decision_does_not_create_ordinary_evidence() -> None:
    decision = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="What are owners saying about this TV?",
            social_signal_relevance="central",
            explicit_social_signal_requested=True,
            packet_or_none=_fixture_packet_dict(),
        )
    )

    assert decision.evidence_class == SOCIAL_SIGNAL_EVIDENCE_CLASS
    assert decision.evidence_class == "social_signal_perception"
    assert decision.ordinary_evidence_registry_merge_allowed is False
    assert decision.may_support_factual_claims is False
    assert decision.factual_evidence_sufficiency_changed is False


def test_decision_does_not_satisfy_official_or_weak_factual_evidence_paths() -> None:
    decision = decide_social_signal_controller(
        SocialSignalControllerInput(
            query="What are owners saying about this TV?",
            social_signal_relevance="central",
            explicit_social_signal_requested=True,
            packet_or_none=_fixture_packet_dict(),
        )
    )

    assert decision.official_or_primary_evidence_satisfied is False
    assert decision.official_source_repair_interaction_allowed is False
    assert decision.weak_evidence_repair_interaction_allowed is False
    assert decision.may_support_factual_claims is False
    assert decision.ordinary_evidence_registry_merge_allowed is False


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_social_signal_controller_static_import_guard() -> None:
    forbidden_import_prefixes = (
        "streamlit",
        "requests",
        "httpx",
        "openai",
        "anthropic",
        "sqlite3",
        "core.prompts",
        "core.search_providers",
        "core.provider_validation",
        "core.provider_diagnostics",
        "core.pipeline_orchestrator",
        "core.routing",
        "core.retrieval",
        "core.retrieval_quality",
        "core.retrieval_budget_pressure",
        "core.db",
        "core.storage",
        "core.run_logging",
        "core.source_class_recovery",
        "core.weak_corpus_recovery",
        "core.answer_contract_runtime_handoff",
        "core.answer_contract_pipeline_adapter",
        "core.answer_contract_loop_harness",
        "core.run_controller",
        "core.run_plan",
        "core.nutrition_author_notes",
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

    violations = [
        name
        for name in _imported_names(_CONTROLLER_PATH)
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    source = _CONTROLLER_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
