"""PRODUCT-PATH-REGRESSION: MVP supported-query-class boundary metadata.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --mvp-demo and
python -m proplex --mvp-live-dogfood-run
Runtime consumer: proplex.mvp_friend_shareable_output and
proplex.mvp_live_dogfood_run packet builders
Why ordinary product-path work cannot be done directly: the boundary is consumed
by ordinary MVP packet builders, while offline tests avoid live provider,
broker, fetch/read, retrieval, and model calls.
Integration deadline: current phase.
Exit condition: keep while MVP demo/live dogfood packets carry the first
supported-query-class boundary metadata.
Why this is not a shadow product path: the tests call the existing MVP packet
builders and validate their product-visible metadata, not a parallel planner or
alternate answer path.
Forbidden interpretation: this is not arbitrary query support, query planning,
source-authority adjudication, social/review evidence handling, live validation,
friend-level/general MVP readiness, or product correctness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from core.mvp_supported_query_class_boundary import (
    MVP_SUPPORTED_QUERY_CLASS_HARD_EXCLUSIONS,
    MVP_SUPPORTED_QUERY_CLASS_ID,
    MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE,
    build_mvp_supported_query_class_boundary_profile,
    build_mvp_supported_query_class_boundary_status,
    validate_mvp_supported_query_class_boundary_profile,
    validate_mvp_supported_query_class_boundary_status,
)
from proplex.mvp_friend_shareable_output import (
    BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED,
    BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING,
    DEFAULT_MVP_QUERY,
    build_mvp_demo_output,
    build_mvp_live_dogfood_status_output,
)
from proplex.mvp_live_dogfood_run import build_mvp_live_dogfood_run_output


def test_boundary_profile_exists_validates_and_is_not_passport_specific() -> None:
    profile = validate_mvp_supported_query_class_boundary_profile(
        build_mvp_supported_query_class_boundary_profile()
    )

    assert profile["profile_id"] == MVP_SUPPORTED_QUERY_CLASS_ID
    assert profile["profile_version"] == "1"
    assert "source-of-record single-fact" in profile["short_label"]
    assert "passport" not in _non_example_text(profile)
    assert "passport" in json.dumps(
        {
            "conceptual_examples": profile["conceptual_examples"],
            "canonical_fixed_dogfood_example": (
                profile["canonical_fixed_dogfood_example"]
            ),
        },
        sort_keys=True,
    ).casefold()


def test_fixed_query_is_canonical_example_not_the_supported_class() -> None:
    status = validate_mvp_supported_query_class_boundary_status(
        build_mvp_supported_query_class_boundary_status(
            product_path_slice="offline_fixed_fixture_demo",
            product_path_consumed=True,
        )
    )

    assert status["profile_id"] == MVP_SUPPORTED_QUERY_CLASS_ID
    assert status["fixed_query_example"] is True
    assert status["canonical_fixed_dogfood_example"]["query"] == DEFAULT_MVP_QUERY
    assert status["canonical_fixed_dogfood_example"]["example_only"] is True
    assert (
        status["canonical_fixed_dogfood_example"]["architecture_definition"]
        is False
    )
    assert status["arbitrary_query_planning_supported"] is False
    assert status["query_to_relation_planning_supported"] is False
    assert status["next_milestone"] == MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE
    assert status["next_milestone"] != BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING


def test_hard_exclusions_cover_post_boundary_work() -> None:
    joined = "\n".join(MVP_SUPPORTED_QUERY_CLASS_HARD_EXCLUSIONS).casefold()

    for required in (
        "social/review sentiment as authority",
        "broad product comparison/reliability questions",
        "medical, legal, financial, or safety advice",
        "arbitrary query planning",
        "multi-component synthesis",
        "private/personal data",
    ):
        assert required in joined


def test_mvp_demo_packet_consumes_boundary_metadata(tmp_path: Path) -> None:
    result = build_mvp_demo_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_demo_01",
        run_id="boundary-demo",
    )

    packet = json.loads(result.packet_path.read_text(encoding="utf-8"))
    boundary = validate_mvp_supported_query_class_boundary_status(
        packet["supported_query_class_boundary"]
    )

    assert result.decision == "PASS"
    assert boundary["profile_id"] == MVP_SUPPORTED_QUERY_CLASS_ID
    assert boundary["status"] == "fixed_dogfood_example_only"
    assert boundary["product_path_slice"] == "offline_fixed_fixture_demo"
    assert boundary["product_path_consumed"] is True
    assert boundary["fixed_query_example"] is True
    assert boundary["friend_level_mvp_claimed"] is False
    assert boundary["general_supported_query_mvp_claimed"] is False
    assert boundary["product_correctness_claimed"] is False
    assert "Supported-query class:" in result.output
    assert "arbitrary query planning=false" in result.output


def test_unsupported_demo_query_blocks_without_retention_and_keeps_boundary(
    tmp_path: Path,
) -> None:
    unsupported = "How does this Honda compare to competitors?"
    result = build_mvp_demo_output(
        query=unsupported,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_demo_01",
        run_id="boundary-unsupported-demo",
    )

    packet = json.loads(result.packet_path.read_text(encoding="utf-8"))
    boundary = validate_mvp_supported_query_class_boundary_status(
        packet["supported_query_class_boundary"]
    )
    serialized = json.dumps(packet, sort_keys=True)

    assert result.decision == BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED
    assert packet["unsupported_query_retained"] is False
    assert packet["query"] == "unsupported MVP demo query (not retained)"
    assert unsupported not in result.output
    assert unsupported not in serialized
    assert boundary["status"] == "unsupported_query_blocked_before_boundary_entry"
    assert boundary["fixed_query_example"] is False
    assert boundary["product_path_consumed"] is False
    assert boundary["broad_product_comparison_supported"] is False
    assert boundary["next_milestone"] == MVP_SUPPORTED_QUERY_CLASS_NEXT_MILESTONE
    assert boundary["next_milestone"] != BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING


def test_live_status_packet_consumes_boundary_without_live_calls(
    tmp_path: Path,
) -> None:
    result = build_mvp_live_dogfood_status_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="boundary-live-status",
    )

    boundary = validate_mvp_supported_query_class_boundary_status(
        result.packet["supported_query_class_boundary"]
    )

    assert result.return_code == 2
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert boundary["status"] == "fixed_dogfood_example_only"
    assert boundary["product_path_slice"] == "fixed_live_dogfood_status_slice"
    assert boundary["fixed_query_example"] is True
    assert boundary["product_correctness_claimed"] is False


def test_live_run_blocker_packet_carries_boundary_without_broadening_behavior(
    tmp_path: Path,
) -> None:
    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="boundary-live-confirmation",
    )

    boundary = validate_mvp_supported_query_class_boundary_status(
        result.packet["supported_query_class_boundary"]
    )

    assert result.return_code == 2
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["mvp_live_status_consumed_retained_artifacts"] is False
    assert boundary["status"] == "fixed_dogfood_example_only"
    assert boundary["product_path_slice"] == "fixed_live_dogfood_slice"
    assert boundary["fixed_query_example"] is True
    assert boundary["arbitrary_query_planning_supported"] is False
    assert boundary["friend_level_mvp_claimed"] is False
    assert boundary["general_supported_query_mvp_claimed"] is False


def _non_example_text(value: Mapping[str, Any]) -> str:
    example_keys = {"canonical_fixed_dogfood_example", "conceptual_examples"}
    pieces: list[str] = []

    def walk(item: Any, *, key: str = "") -> None:
        if key in example_keys:
            return
        if isinstance(item, Mapping):
            for child_key, child in item.items():
                pieces.append(str(child_key))
                walk(child, key=str(child_key))
        elif isinstance(item, list | tuple):
            for child in item:
                walk(child)
        elif isinstance(item, str):
            pieces.append(item)

    walk(value)
    return " ".join(pieces).casefold()
