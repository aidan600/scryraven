from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.social_signal_controller import (
    SOCIAL_SIGNAL_EVIDENCE_CLASS,
    SocialSignalControllerInput,
    decide_social_signal_controller,
)
from core.social_signal_schema import (
    AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL,
    EVIDENCE_BOUNDARY_REQUIRED_VALUES,
    SocialSignalPacket,
    SocialSignalPacketValidationError,
    build_author_safe_social_signal_digest,
    can_merge_into_ordinary_evidence_registry,
    is_social_signal_factual_evidence,
    parse_social_signal_packet,
    validate_social_signal_packet,
)
from core.social_signal_scoring import build_social_signal_packet_from_items

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "social_signal"

_EXPECTED_FIXTURE_FILES = (
    "brigading_duplicate_noise.json",
    "minority_high_engagement_dissent.json",
    "missing_engagement_metadata.json",
    "platform_dominated_sample.json",
    "political_current_event_perception.json",
    "product_recommendation_optional_social.json",
    "provider_unavailable_central_social.json",
    "raw_storage_policy_fixture.json",
    "social_only_public_reaction.json",
    "tcl_tv_weighted_topic_split.json",
)

_DIGEST_INTERNAL_KEYS = frozenset(
    {
        "access_method",
        "author",
        "author_hash",
        "author_id",
        "author_key",
        "high_engagement_dissenting_examples",
        "item_id",
        "packet",
        "parent_id",
        "policy_basis",
        "raw_comments",
        "raw_text",
        "representative_high_engagement_examples",
        "source_reference_url",
        "source_references",
        "source_tool",
        "source_url",
        "text",
        "thread_id",
        "url",
        "user_id",
        "username",
    }
)

_ITEM_RAW_KEYS = (
    "author_hash",
    "author_id",
    "author_key",
    "item_id",
    "parent_id",
    "source_reference_url",
    "source_url",
    "thread_id",
    "url",
    "user_id",
    "username",
)


def _fixture_paths() -> tuple[Path, ...]:
    return tuple(sorted(_FIXTURE_DIR.glob("*.json")))


def _load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_packet(fixture: Mapping[str, Any]) -> SocialSignalPacket:
    return build_social_signal_packet_from_items(
        fixture["items"],
        query=str(fixture["query"]),
        entity=fixture.get("entity"),
        topic=fixture.get("topic"),
        reference_time=fixture.get("reference_time"),
        raw_storage_allowed=bool(fixture.get("raw_storage_allowed", False)),
    )


@pytest.mark.parametrize("fixture_path", _fixture_paths(), ids=lambda path: path.stem)
def test_social_signal_offline_fixture_harness(fixture_path: Path) -> None:
    fixture = _load_fixture(fixture_path)
    expected = fixture["expected"]

    packet = _build_packet(fixture)
    packet_dict = packet.to_dict()
    validation = validate_social_signal_packet(packet_dict)

    assert validation.valid is True
    assert validation.status == expected.get("packet_status", "completed")
    parsed_packet = parse_social_signal_packet(packet_dict)

    _assert_packet_boundary(parsed_packet)
    digest = build_author_safe_social_signal_digest(parsed_packet)
    _assert_author_digest_safe(digest, fixture)
    _assert_fixture_expectations(parsed_packet, digest, expected)

    if "unsafe_packet_overrides" in expected:
        unsafe_packet = _unsafe_packet(packet_dict, expected)
        unsafe_validation = validate_social_signal_packet(unsafe_packet)
        assert unsafe_validation.valid is False
        for reason in expected["unsafe_validation_reasons"]:
            assert reason in unsafe_validation.reasons
        with pytest.raises(SocialSignalPacketValidationError):
            parse_social_signal_packet(unsafe_packet)
        unsafe_digest = build_author_safe_social_signal_digest(unsafe_packet)
        assert unsafe_digest["status"] == "blocked"
        _assert_author_digest_safe(unsafe_digest, fixture)

    _assert_controller_cases(fixture, packet_dict)


def test_social_signal_fixture_inventory_is_intentional() -> None:
    assert tuple(path.name for path in _fixture_paths()) == _EXPECTED_FIXTURE_FILES


def _assert_packet_boundary(packet: SocialSignalPacket) -> None:
    for field_name, expected_value in EVIDENCE_BOUNDARY_REQUIRED_VALUES.items():
        assert getattr(packet, field_name) is expected_value

    assert is_social_signal_factual_evidence(packet) is False
    assert can_merge_into_ordinary_evidence_registry(packet) is False
    assert packet.raw_packet_to_author_allowed is False
    assert packet.raw_comments_to_author_allowed is False
    assert packet.ordinary_evidence_registry_merge_allowed is False
    assert packet.may_support_factual_claims is False


def _assert_fixture_expectations(
    packet: SocialSignalPacket,
    digest: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    topics = {str(cluster["topic"]) for cluster in packet.topic_clusters}
    for topic in expected.get("topics_present", []):
        assert topic in topics
    for topic in expected.get("topics_absent", []):
        assert topic not in topics

    for topic, counts in expected.get("raw_sentiment_counts", {}).items():
        assert packet.raw_sentiment_counts_by_topic[topic] == counts
    for topic, counts in expected.get("raw_stance_counts", {}).items():
        assert packet.raw_stance_counts_by_topic[topic] == counts
    for topic, label in expected.get("weighted_labels", {}).items():
        assert packet.engagement_weighted_sentiment_by_topic[topic]["label"] == label
    for topic, bounds in expected.get("weighted_score_bounds", {}).items():
        score = packet.engagement_weighted_sentiment_by_topic[topic]["score"]
        _assert_numeric_bounds(score, bounds)
    for key, value in expected.get("item_counts", {}).items():
        assert packet.item_counts[key] == value
    for key, value in expected.get("missing_metadata_counts", {}).items():
        assert packet.missing_metadata_counts[key] == value
    for reason in expected.get("confidence_reasons_include", []):
        assert reason in packet.confidence_reasons
    if expected.get("confidence_level_in"):
        assert packet.confidence_level in expected["confidence_level_in"]
    for topic, count in expected.get("dissenting_examples_by_topic", {}).items():
        matching = [
            example for example in packet.high_engagement_dissenting_examples if example["topic"] == topic
        ]
        assert len(matching) == count

    for caveat in expected.get("digest_caveats_include", []):
        assert any(caveat.casefold() in str(item).casefold() for item in digest["caveats"])
    for topic, topic_expected in expected.get("digest_topic_expectations", {}).items():
        digest_topic = _digest_topic(digest, topic)
        for key, value in topic_expected.items():
            assert digest_topic[key] == value


def _assert_controller_cases(fixture: Mapping[str, Any], packet_dict: Mapping[str, Any]) -> None:
    expected = fixture["expected"]
    for case in expected.get("controller_cases", []):
        packet_source = case.get("packet_source", "built")
        if packet_source == "built":
            packet_or_none = packet_dict
        elif packet_source == "unsafe_override":
            packet_or_none = _unsafe_packet(packet_dict, expected)
        elif packet_source == "none":
            packet_or_none = None
        else:
            raise AssertionError(f"Unsupported packet_source: {packet_source}")

        decision = decide_social_signal_controller(
            SocialSignalControllerInput(
                query=str(fixture["query"]),
                mode=str(case.get("mode", fixture.get("mode", "Balanced"))),
                social_signal_relevance=case.get(
                    "social_signal_relevance",
                    fixture.get("social_signal_relevance"),
                ),
                explicit_social_signal_requested=bool(
                    case.get(
                        "explicit_social_signal_requested",
                        fixture.get("explicit_social_signal_requested", False),
                    )
                ),
                social_provider_configured=bool(
                    case.get(
                        "social_provider_configured",
                        fixture.get("social_provider_configured", False),
                    )
                ),
                api_enabled=bool(case.get("api_enabled", fixture.get("api_enabled", False))),
                packet_or_none=packet_or_none,
                platform_allowlist=tuple(case.get("platform_allowlist", ())),
                platform_denylist=tuple(case.get("platform_denylist", ())),
            )
        )

        assert decision.status == case["expected_status"], case["name"]
        assert decision.social_signal_status == case["expected_social_signal_status"], case["name"]
        assert decision.stable_reason_code == case["expected_reason"], case["name"]
        assert case["expected_reason"] in decision.reasons
        assert decision.packet_valid is bool(case.get("packet_valid", decision.status == "checked"))
        _assert_decision_boundary(decision.to_dict())

        if case.get("expect_author_digest", False):
            assert decision.author_digest_or_none is not None
            assert decision.author_digest_or_none["label"] == AUTHOR_SAFE_SOCIAL_SIGNAL_LABEL
            _assert_author_digest_safe(decision.author_digest_or_none, fixture)
        else:
            assert decision.author_digest_or_none is None


def _assert_decision_boundary(decision: Mapping[str, Any]) -> None:
    assert decision["evidence_class"] == SOCIAL_SIGNAL_EVIDENCE_CLASS
    assert decision["may_support_factual_claims"] is False
    assert decision["ordinary_evidence_registry_merge_allowed"] is False
    assert decision["raw_packet_to_author_allowed"] is False
    assert decision["raw_comments_to_author_allowed"] is False
    assert decision["provider_call_allowed"] is False
    assert decision["live_api_call_allowed"] is False
    assert decision["factual_evidence_sufficiency_changed"] is False
    assert decision["official_or_primary_evidence_satisfied"] is False
    assert decision["official_source_repair_interaction_allowed"] is False
    assert decision["weak_evidence_repair_interaction_allowed"] is False


def _assert_author_digest_safe(digest: Mapping[str, Any], fixture: Mapping[str, Any]) -> None:
    encoded = json.dumps(digest, sort_keys=True)

    assert digest["author_safe"] is True
    assert digest["may_support_factual_claims"] is False
    assert digest["ordinary_evidence_registry_merge_allowed"] is False
    assert digest["raw_packet_to_author_allowed"] is False
    assert digest["raw_comments_to_author_allowed"] is False
    assert "http://" not in encoded
    assert "https://" not in encoded

    for sentinel in fixture["expected"].get("raw_sentinels", []):
        assert sentinel not in encoded
    for item in fixture.get("items", []):
        for key in _ITEM_RAW_KEYS:
            value = item.get(key)
            if isinstance(value, str) and len(value) >= 6:
                assert value not in encoded

    digest_keys = _collect_keys(digest)
    assert digest_keys.isdisjoint(_DIGEST_INTERNAL_KEYS)


def _assert_numeric_bounds(value: float, bounds: Mapping[str, float]) -> None:
    if "gt" in bounds:
        assert value > bounds["gt"]
    if "ge" in bounds:
        assert value >= bounds["ge"]
    if "lt" in bounds:
        assert value < bounds["lt"]
    if "le" in bounds:
        assert value <= bounds["le"]


def _digest_topic(digest: Mapping[str, Any], topic: str) -> Mapping[str, Any]:
    for item in digest["topics"]:
        if item["topic"] == topic:
            return item
    raise AssertionError(f"Missing digest topic: {topic}")


def _unsafe_packet(packet_dict: Mapping[str, Any], expected: Mapping[str, Any]) -> dict[str, Any]:
    unsafe_packet = copy.deepcopy(dict(packet_dict))
    unsafe_packet.update(copy.deepcopy(expected["unsafe_packet_overrides"]))
    return unsafe_packet


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        out = {str(key) for key in value}
        for item in value.values():
            out.update(_collect_keys(item))
        return out
    if isinstance(value, list | tuple):
        out: set[str] = set()
        for item in value:
            out.update(_collect_keys(item))
        return out
    return set()
