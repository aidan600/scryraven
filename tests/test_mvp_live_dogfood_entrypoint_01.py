"""PRODUCT-PATH-REGRESSION: MVP live dogfood entrypoint.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --mvp-live-dogfood-run
Runtime consumer: proplex.__main__ -> proplex.mvp_live_dogfood_run ->
proplex.mvp_friend_shareable_output -> proplex.live_semantic_coverage_status
Why ordinary product-path work cannot be done directly: offline validation must
not make live provider, broker, fetch/read, retrieval, or model calls; injected
provider/fetch runners preserve the same retained-artifact product consumer.
Integration deadline: current phase.
Exit condition: keep while the live dogfood CLI entrypoint exists.
Why this is not a shadow product path: the test invokes the product entrypoint
builder and existing retained-artifact status chain, not a standalone answer
formatter or alternate status implementation.
Forbidden interpretation: this is not live validation, product correctness,
source acquisition quality, arbitrary query support, model-review readiness,
Scrutineer remediation, Economist/Specialist routing, or old Author execution.
"""

from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
from typing import Any

import pytest

from core.product_model_route_config import MVP_LIVE_DOGFOOD_RUN_FLAG
from proplex.live_acquisition_readability_status import (
    FETCH_READ_ARTIFACT_DIR,
    FETCH_READ_CONTENT_PACKET_NAME,
    LIVE_SOURCE_SURVIVAL_SUMMARY_NAME,
    SANITIZED_PROVIDER_RESULTS_NAME,
    SEARCH_ARTIFACT_DIR,
    SEARCH_CANDIDATE_PACKET_NAME,
    SEARCH_RESULT_CANDIDATE_PACKET_NAME,
)
from proplex.mvp_friend_shareable_output import DEFAULT_MVP_QUERY
from proplex.mvp_live_dogfood_run import (
    BLOCKED_MVP_LIVE_CONFIRMATION_REQUIRED,
    BLOCKED_MVP_LIVE_DOGFOOD_QUERY_NOT_SUPPORTED,
    BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING,
    BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
    BLOCKED_MVP_LIVE_TEST_OR_CI_GUARD,
    CONFIRM_LIVE_DOGFOOD_FLAG,
    LiveDogfoodFetchReadResult,
    MvpLiveDogfoodRunError,
    ProviderProxyRunRequest,
    ProviderProxyRunResult,
    build_mvp_live_dogfood_run_output,
    validate_mvp_live_dogfood_packet,
)


def test_live_run_requires_explicit_confirmation(tmp_path: Path) -> None:
    calls: list[ProviderProxyRunRequest] = []

    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="confirmation-required",
        provider_proxy_runner=_recording_proxy_runner(calls),
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_MVP_LIVE_CONFIRMATION_REQUIRED
    assert calls == []
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["fetch_read_attempts"] == 0
    assert result.packet["raw_provider_payload_retained"] is False
    assert CONFIRM_LIVE_DOGFOOD_FLAG in result.output


def test_unsupported_query_blocks_before_provider(tmp_path: Path) -> None:
    calls: list[ProviderProxyRunRequest] = []
    unsupported = "What arbitrary question should the live dogfood answer?"

    result = build_mvp_live_dogfood_run_output(
        query=unsupported,
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="unsupported-query",
        confirm_live_dogfood=True,
        provider_proxy_runner=_recording_proxy_runner(calls),
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_MVP_LIVE_DOGFOOD_QUERY_NOT_SUPPORTED
    assert calls == []
    assert result.packet["query"] == "unsupported live dogfood query (not retained)"
    assert result.packet["unsupported_query_retained"] is False
    assert unsupported not in result.output
    assert unsupported not in json.dumps(result.packet, sort_keys=True)


def test_default_live_runner_blocked_under_pytest_or_ci(tmp_path: Path) -> None:
    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="pytest-guard",
        confirm_live_dogfood=True,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_MVP_LIVE_TEST_OR_CI_GUARD
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["mvp_live_status_consumed_retained_artifacts"] is False


def test_fake_broker_and_fetch_feed_existing_status_consumer(tmp_path: Path) -> None:
    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="fake-live-consumer",
        confirm_live_dogfood=True,
        provider_proxy_runner=_official_proxy_runner,
        fetch_read_runner=_official_fetch_runner,
        environ={},
    )

    assert result.return_code == 2
    assert result.decision == BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING
    assert result.packet["status_decision"] == "BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED"
    assert result.packet["mvp_live_status_consumed_retained_artifacts"] is True
    assert result.packet["ordinary_product_path_consumed"] is True
    assert result.packet["runtime_consumer"] == (
        "proplex.live_semantic_coverage_status.build_live_semantic_coverage_status"
    )
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["provider_calls_completed"] == 1
    assert result.packet["provider_results_returned"] == 1
    assert result.packet["search_tasks_attempted"] == 1
    assert result.packet["search_tasks_completed"] == 1
    assert result.packet["fetch_read_attempts"] == 1
    assert result.packet["fetch_read_completed"] == 1
    assert result.packet["evidence_ledger_admissions"] == 1
    assert result.packet["dprime_model_review_call_count"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["dprime_model_review_calls_completed"] == 0
    assert result.packet["model_review_licensed"] is False
    assert result.packet["followup_loop_count"] == 0
    assert result.packet["product_correctness_claimed"] is False
    assert result.packet["raw_provider_payload_retained"] is False
    assert result.packet["raw_search_response_retained"] is False
    assert result.packet["raw_prompt_retained"] is False
    assert result.packet["raw_model_response_retained"] is False
    assert result.packet["private_logs_retained"] is False
    assert "product correctness" in result.packet["explicit_non_proofs"]

    retained = result.retained_artifact_root
    assert retained is not None
    search_dir = retained / SEARCH_ARTIFACT_DIR
    fetch_dir = retained / FETCH_READ_ARTIFACT_DIR
    assert (search_dir / SANITIZED_PROVIDER_RESULTS_NAME).is_file()
    assert (search_dir / SEARCH_CANDIDATE_PACKET_NAME).is_file()
    assert (search_dir / SEARCH_RESULT_CANDIDATE_PACKET_NAME).is_file()
    assert (fetch_dir / FETCH_READ_CONTENT_PACKET_NAME).is_file()
    assert (fetch_dir / LIVE_SOURCE_SURVIVAL_SUMMARY_NAME).is_file()


def test_output_path_confinement(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="output/mvp_live_dogfood_01"):
        build_mvp_live_dogfood_run_output(
            repo_root=tmp_path,
            output_dir=tmp_path / "output" / "not_mvp_live",
            confirm_live_dogfood=True,
            provider_proxy_runner=_official_proxy_runner,
            fetch_read_runner=_official_fetch_runner,
            environ={},
        )


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "api_key",
        "auth",
        "authorization",
        "token",
        "raw_provider_payload",
        "raw_search_response",
        "raw_prompt",
        "raw_model_response",
        "private_log",
        "db",
        "cache",
        "full_trace",
        "unbounded_text",
    ],
)
def test_packet_rejects_forbidden_raw_private_fields(
    tmp_path: Path,
    forbidden_key: str,
) -> None:
    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="forbidden-field",
        confirm_live_dogfood=True,
        provider_proxy_runner=_official_proxy_runner,
        fetch_read_runner=_official_fetch_runner,
        environ={},
    )
    packet = copy.deepcopy(result.packet)
    packet["status_payload"] = {forbidden_key: "private_sentinel"}

    with pytest.raises(MvpLiveDogfoodRunError) as excinfo:
        validate_mvp_live_dogfood_packet(packet)

    assert excinfo.value.blocker == BLOCKED_MVP_LIVE_OUTPUT_HYGIENE


def test_false_raw_retention_posture_is_allowed_but_true_is_rejected(
    tmp_path: Path,
) -> None:
    result = build_mvp_live_dogfood_run_output(
        repo_root=tmp_path,
        output_dir=tmp_path / "output" / "mvp_live_dogfood_01",
        run_id="raw-retention-posture",
        confirm_live_dogfood=True,
        provider_proxy_runner=_official_proxy_runner,
        fetch_read_runner=_official_fetch_runner,
        environ={},
    )
    packet = validate_mvp_live_dogfood_packet(result.packet)
    assert packet["status_payload"]["raw_private_retention"] is False

    packet["status_payload"]["raw_private_retention"] = True
    with pytest.raises(MvpLiveDogfoodRunError) as excinfo:
        validate_mvp_live_dogfood_packet(packet)

    assert excinfo.value.blocker == BLOCKED_MVP_LIVE_OUTPUT_HYGIENE


def test_live_flag_uses_default_query_and_skips_model_key_validation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    cli = importlib.import_module("proplex.__main__")

    captured: dict[str, Any] = {}

    def fail_key_validation(**_kwargs: Any) -> list[str]:
        raise AssertionError("live dogfood run must not validate model keys")

    def fake_live_run(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return type(
            "FakeResult",
            (),
            {
                "return_code": 2,
                "output": "fake live dogfood blocker",
            },
        )()

    monkeypatch.setattr(cli, "_build_logger", lambda _verbose: None)
    monkeypatch.setattr(cli, "missing_required_api_keys", fail_key_validation)
    monkeypatch.setattr(cli, "build_mvp_live_dogfood_run_output", fake_live_run)

    rc = cli.main([MVP_LIVE_DOGFOOD_RUN_FLAG, CONFIRM_LIVE_DOGFOOD_FLAG])

    assert rc == 2
    assert captured["query"] == DEFAULT_MVP_QUERY
    assert captured["confirm_live_dogfood"] is True
    assert captured["confirm_live_dprime_review"] is False
    assert "fake live dogfood blocker" in capsys.readouterr().out


def _recording_proxy_runner(
    calls: list[ProviderProxyRunRequest],
) -> Any:
    def runner(request: ProviderProxyRunRequest) -> ProviderProxyRunResult:
        calls.append(request)
        return _official_proxy_runner(request)

    return runner


def _official_proxy_runner(request: ProviderProxyRunRequest) -> ProviderProxyRunResult:
    payload = {
        "request_kind": "provider_proxy_search",
        "provider": "serper",
        "operation": "search",
        "result_count": 1,
        "results": [
            {
                "title": "Passport Fees",
                "url": (
                    "https://travel.state.gov/content/travel/en/passports/"
                    "how-apply/fees.html"
                ),
                "domain": "travel.state.gov",
                "snippet": (
                    "Official U.S. passport fees for adult passport book "
                    "renewal by mail."
                ),
                "published_or_observed_date": "2026-07-03",
                "result_rank": 1,
                "provider_call_index": 1,
                "raw_provider_payload_retained": False,
                "raw_search_response_retained": False,
            }
        ],
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    request.output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ProviderProxyRunResult(
        return_code=0,
        output_path=request.output_path,
        provider_calls_attempted=1,
        provider_calls_completed=1,
    )


def _official_fetch_runner(url: str) -> LiveDogfoodFetchReadResult:
    return LiveDogfoodFetchReadResult(
        attempted_url=url,
        final_url=url,
        final_domain="travel.state.gov",
        status_code=200,
        status_class="2xx",
        content_type="text/html",
        fetched_byte_count=512,
        sanitized_text=(
            "Passport Fees. Adult applicants age 16 and older renewing a "
            "passport book by mail pay the current renewal fee listed by the "
            "U.S. Department of State for a passport book. The renewal by mail "
            "fee for an adult passport book is $130."
        ),
        content_title="Passport Fees",
        redirect_count=0,
        retrieved_or_observed_at="2026-07-03T00:00:00+00:00",
    )
