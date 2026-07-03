"""PRODUCT-PATH-REGRESSION: MVP live D-prime review entrypoint.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --mvp-live-dogfood-run
Runtime consumer: proplex.__main__ -> proplex.mvp_live_dogfood_run ->
proplex.live_semantic_coverage_status -> D-prime product answer path
Why ordinary product-path work cannot be done directly: offline validation must
not make live provider, broker, fetch/read, retrieval, or model calls; injected
provider/fetch/model-review callables preserve the same product consumer.
Integration deadline: current phase.
Exit condition: keep while the fixed live dogfood D-prime review flag exists.
Why this is not a shadow product path: the test invokes the product entrypoint
builder and existing D-prime status/RunKernel/answer-path reducers.
Forbidden interpretation: fake model-review success is not live success,
product correctness, arbitrary query support, provider quality, Scrutineer
expansion, Economist/Specialist routing, or old Author execution.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from core.product_model_route_config import (
    CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
    MVP_LIVE_DOGFOOD_RUN_FLAG,
    initialize_product_model_route_config,
)
from proplex.mvp_friend_shareable_output import MVP_COMPONENT_ID
from proplex.mvp_live_dogfood_run import (
    BLOCKED_MVP_LIVE_DOGFOOD_QUERY_NOT_SUPPORTED,
    BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING,
    BLOCKED_MVP_LIVE_DPRIME_REVIEW_OUTPUT_INVALID,
    BLOCKED_MVP_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE,
    BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
    CONFIRM_LIVE_DOGFOOD_FLAG,
    MvpLiveDogfoodRunError,
    build_mvp_live_dogfood_run_output,
    validate_mvp_live_dogfood_packet,
)
from tests.test_dprime_model_review_assessment_slice_01 import _assessment_payload
from tests.test_mvp_live_dogfood_entrypoint_01 import (
    _official_fetch_runner,
    _official_proxy_runner,
)


def test_live_dprime_review_requires_separate_confirmation(
    tmp_path: Path,
) -> None:
    calls = 0

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _mvp_assessment_payload()

    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="dprime-confirmation-missing",
        confirm_live_dogfood=True,
        provider_proxy_runner=_official_proxy_runner,
        fetch_read_runner=_official_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={},
    )

    assert calls == 0
    assert result.decision == BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING
    assert result.packet["status_decision"] == "BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED"
    assert result.packet["model_review_licensed"] is False
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["dprime_model_review_calls_completed"] == 0
    assert CONFIRM_LIVE_DPRIME_REVIEW_FLAG in result.packet["blocker_detail"]


def test_unsupported_query_blocks_before_dprime_and_is_not_retained(
    tmp_path: Path,
) -> None:
    calls = 0
    unsupported = "What arbitrary question should this live dogfood answer?"

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _mvp_assessment_payload()

    result = build_mvp_live_dogfood_run_output(
        query=unsupported,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="unsupported-query-dprime",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_official_proxy_runner,
        fetch_read_runner=_official_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={},
    )

    assert calls == 0
    assert result.decision == BLOCKED_MVP_LIVE_DOGFOOD_QUERY_NOT_SUPPORTED
    assert result.packet["query"] == "unsupported live dogfood query (not retained)"
    assert result.packet["unsupported_query_retained"] is False
    assert unsupported not in result.output
    assert unsupported not in json.dumps(result.packet, sort_keys=True)


def test_real_dprime_route_disabled_under_pytest_without_fake_injection(
    tmp_path: Path,
) -> None:
    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="pytest-real-route-disabled",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_official_proxy_runner,
        fetch_read_runner=_official_fetch_runner,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert result.decision == BLOCKED_MVP_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["model_review_licensed"] is False
    assert result.packet["dprime_model_review_calls_attempted"] == 0


def test_fake_dprime_review_is_consumed_by_existing_product_path(
    tmp_path: Path,
) -> None:
    calls = 0

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _mvp_assessment_payload()

    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="fake-dprime-product-path",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_official_proxy_runner,
        fetch_read_runner=_official_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert calls == 1
    assert result.decision == "PASS", result.packet.get("blocker_detail")
    assert result.packet["model_review_licensed"] is True
    assert result.packet["dprime_model_review_call_count"] == 1
    assert result.packet["dprime_model_review_calls_attempted"] == 1
    assert result.packet["dprime_model_review_calls_completed"] == 1
    assert result.packet["followup_loop_count"] == 0
    assert result.packet["caps_exhausted"] is False
    assert result.packet["answer_text_present"] is True
    assert result.packet["source_display_entries"]
    assert result.packet["product_correctness_claimed"] is False
    assert result.packet["raw_prompt_retained"] is False
    assert result.packet["raw_model_response_retained"] is False
    assert CONFIRM_LIVE_DPRIME_REVIEW_FLAG in result.packet["command_harness_used"]
    assert (
        result.packet["provider_broker_posture"]
        == "private_broker_sanitized_provider_proxy_to_retained_artifacts_"
        "with_explicit_dprime_review"
    )


def test_invalid_fake_dprime_output_fails_closed_without_retry(
    tmp_path: Path,
) -> None:
    calls = 0

    def fake_invalid(*_args: Any, **_kwargs: Any) -> str:
        nonlocal calls
        calls += 1
        return "not json"

    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="invalid-dprime-output",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_official_proxy_runner,
        fetch_read_runner=_official_fetch_runner,
        dprime_model_review_callable=fake_invalid,
        environ={},
    )

    assert calls == 1
    assert result.decision == BLOCKED_MVP_LIVE_DPRIME_REVIEW_OUTPUT_INVALID
    assert result.packet["status_decision"] == "BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID"
    assert result.packet["model_review_licensed"] is True
    assert result.packet["dprime_model_review_calls_attempted"] == 1
    assert result.packet["dprime_model_review_calls_completed"] == 0
    assert result.packet["source_display_entries"] == []


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "raw_prompt",
        "raw_model_response",
        "provider_payload",
        "raw_provider_payload",
        "raw_search_response",
        "api_key",
        "token",
        "auth",
        "secret",
        "private_logs",
        "db",
        "cache",
        "full_trace",
    ],
)
def test_live_dprime_packet_rejects_raw_private_fields(
    tmp_path: Path,
    forbidden_key: str,
) -> None:
    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="dprime-packet-hygiene",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_official_proxy_runner,
        fetch_read_runner=_official_fetch_runner,
        dprime_model_review_callable=lambda *_args, **_kwargs: _mvp_assessment_payload(),
        environ={},
    )
    packet = copy.deepcopy(result.packet)
    packet["status_payload"] = {forbidden_key: "private_sentinel"}

    with pytest.raises(MvpLiveDogfoodRunError) as excinfo:
        validate_mvp_live_dogfood_packet(packet)

    assert excinfo.value.blocker == BLOCKED_MVP_LIVE_OUTPUT_HYGIENE


def test_dprime_confirming_live_run_uses_product_config_boundary() -> None:
    calls = 0

    def fake_dotenv() -> bool:
        nonlocal calls
        calls += 1
        return True

    no_review = initialize_product_model_route_config(
        [MVP_LIVE_DOGFOOD_RUN_FLAG, CONFIRM_LIVE_DOGFOOD_FLAG],
        load_dotenv_func=fake_dotenv,
        environ={},
    )
    with_review = initialize_product_model_route_config(
        [
            MVP_LIVE_DOGFOOD_RUN_FLAG,
            CONFIRM_LIVE_DOGFOOD_FLAG,
            CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
        ],
        load_dotenv_func=fake_dotenv,
        environ={},
    )

    assert no_review.dotenv_skipped_for_status_dry_run is True
    assert no_review.dotenv_helper_invoked is False
    assert with_review.dotenv_skipped_for_status_dry_run is False
    assert with_review.dotenv_helper_invoked is True
    assert calls == 1


def _mvp_assessment_payload() -> dict[str, Any]:
    payload = _assessment_payload()
    payload["answer_component_claim"]["component_id"] = MVP_COMPONENT_ID
    return payload
