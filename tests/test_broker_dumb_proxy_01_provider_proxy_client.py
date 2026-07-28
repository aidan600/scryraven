from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from scripts import request_provider_proxy_broker as client
from scripts.provider_execution_contract import (
    MODEL_GENERATE_OPERATION,
    REQUEST_KIND,
    SCHEMA_VERSION,
    SEARCH_QUERY_OPERATION,
    ProviderExecutionContractError,
    build_model_request,
    build_search_request,
    build_success_response,
    normalize_search_provider_result,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "request_provider_proxy_broker.py"


def _request(provider: str = "serper") -> dict[str, Any]:
    return build_search_request(
        provider=provider,
        query="current official example",
        max_results=5,
        timeout_seconds=30,
        retry_cap=0,
    )


def _sample_broker_response(provider: str = "serper") -> dict[str, Any]:
    return build_success_response(
        _request(provider),
        physical_attempt_count=1,
        provider_elapsed_milliseconds_total=5,
        results=[
            {
                "title": "Example Result",
                "url": "https://example.gov/current",
                "domain": "example.gov",
                "snippet": "Sanitized result snippet.",
                "published_or_observed_date": "2026-06-28",
                "result_rank": 1,
                "provider_call_index": 1,
                "provider": provider,
                "operation": SEARCH_QUERY_OPERATION,
            }
        ],
    )


def _client_args(output: str, *, broker_url: str = client.DEFAULT_BROKER_URL) -> list[str]:
    return [
        "--broker-url",
        broker_url,
        "--provider",
        "serper",
        "--operation",
        SEARCH_QUERY_OPERATION,
        "--query",
        "current official example",
        "--max-results",
        "5",
        "--timeout-seconds",
        "30",
        "--retry-cap",
        "0",
        "--cost-ceiling-usd",
        "0.05",
        "--output",
        output,
        "--confirm-provider-call",
    ]


def _model_client_args(output: str) -> list[str]:
    return [
        "--provider",
        "openai",
        "--operation",
        MODEL_GENERATE_OPERATION,
        "--model",
        "gpt-5.4-2026-03-05",
        "--input-prompt",
        "Return one status object.",
        "--reasoning-effort",
        "medium",
        "--max-output-tokens",
        "128",
        "--maximum-input-tokens",
        "1000",
        "--timeout-seconds",
        "120",
        "--retry-cap",
        "0",
        "--ordinary-input-price-usd-per-million",
        "2.50",
        "--cached-input-price-usd-per-million",
        "0.25",
        "--output-price-usd-per-million",
        "15.00",
        "--cost-ceiling-usd",
        "0.01",
        "--expected-json-status",
        "BROKER_MODEL_OK",
        "--output",
        output,
        "--confirm-provider-call",
    ]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def test_request_shape_is_generic_provider_proxy_not_phase_job_policy() -> None:
    payload = client.build_provider_proxy_request(
        provider="serper",
        operation=SEARCH_QUERY_OPERATION,
        query="current official example",
        max_results=5,
    )
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["request_kind"] == REQUEST_KIND
    assert payload["provider"] == "serper"
    assert payload["operation"] == SEARCH_QUERY_OPERATION
    assert payload["timeout_seconds"] == 30.0
    assert payload["retry_cap"] == 0
    assert all(
        payload[key] is False
        for key in (
            "raw_provider_payload_retained",
            "raw_request_material_retained",
            "raw_response_material_retained",
            "raw_search_response_retained",
        )
    )
    rendered = json.dumps(payload).casefold()
    for forbidden in ("job_id", "validation_profile", "runkernel", "evidenceledger"):
        assert forbidden not in rendered


@pytest.mark.parametrize("max_results", [0, 11])
def test_request_rejects_unbounded_max_results(max_results: int) -> None:
    with pytest.raises(
        (client.ProviderProxyClientError, ProviderExecutionContractError),
        match="max_results",
    ):
        client.build_provider_proxy_request(
            provider="serper",
            operation=SEARCH_QUERY_OPERATION,
            query="current official example",
            max_results=max_results,
        )


def test_client_refuses_non_loopback_urls_and_requires_token_and_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(client.TOKEN_ENV_VAR, raising=False)
    assert client.main(_client_args("output/missing-token.json")) == 2
    monkeypatch.setenv(client.TOKEN_ENV_VAR, "temporary-session")
    assert (
        client.main(
            _client_args(
                "output/nonloopback.json",
                broker_url="https://broker.example.com/run",
            )
        )
        == 2
    )
    args = _client_args("output/no-confirm.json")
    args.remove("--confirm-provider-call")
    assert client.main(args) == 2
    with pytest.raises(SystemExit):
        client._parser().parse_args([*_client_args("output/no-argv-token.json"), "--token", "blocked"])


def test_client_writes_only_sanitized_results_under_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(client, "ROOT", tmp_path)
    monkeypatch.setattr(client, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setenv(client.TOKEN_ENV_VAR, "temporary-session")
    captured: dict[str, Any] = {}

    def fake_post(
        broker_url: str,
        token: str,
        payload: Mapping[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        captured.update(url=broker_url, token=token, payload=dict(payload))
        return 200, _sample_broker_response()

    monkeypatch.setattr(client, "_post_broker_json", fake_post)
    assert client.main(_client_args("output/sanitized.json")) == 0
    durable = json.loads((tmp_path / "output" / "sanitized.json").read_text())
    assert durable["proof_kind"] == client.SEARCH_PROOF_KIND
    assert durable["results"][0]["provider"] == "serper"
    assert durable["results"][0]["operation"] == SEARCH_QUERY_OPERATION
    assert captured["token"] == "temporary-session"
    assert "token" not in json.dumps(captured["payload"]).casefold()


def test_model_client_never_prints_or_persists_transient_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(client, "ROOT", tmp_path)
    monkeypatch.setattr(client, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setenv(client.TOKEN_ENV_VAR, "temporary-session")
    output_text = '{"status":"BROKER_MODEL_OK"}'

    def fake_post(
        _broker_url: str,
        _token: str,
        payload: Mapping[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        expected_request = build_model_request(
            provider="openai",
            model="gpt-5.4-2026-03-05",
            system_instructions="",
            input_prompt="Return one status object.",
            reasoning_effort="medium",
            max_output_tokens=128,
            timeout_seconds=120,
            retry_cap=0,
        )
        assert payload == expected_request
        return 200, build_success_response(
            payload,
            physical_attempt_count=1,
            provider_elapsed_milliseconds_total=5,
            output_text=output_text,
            generation_status="completed",
            usage_observed=True,
            input_tokens=20,
            cached_input_tokens=0,
            output_tokens=8,
            reasoning_tokens=0,
            total_tokens=28,
        )

    monkeypatch.setattr(client, "_post_broker_json", fake_post)
    assert client.main(_model_client_args("output/model-proof.json")) == 0
    rendered = (tmp_path / "output" / "model-proof.json").read_text()
    captured = capsys.readouterr()
    assert output_text not in rendered
    assert output_text not in captured.out + captured.err
    proof = json.loads(rendered)
    assert proof["parsed_status"] == "BROKER_MODEL_OK"
    assert proof["output_text_retained"] is False


def test_client_preflights_nested_output_before_broker_post(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(client, "ROOT", tmp_path)
    monkeypatch.setattr(client, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setenv(client.TOKEN_ENV_VAR, "temporary-session")
    target = tmp_path / "output" / "nested" / "response.json"

    def fake_post(
        _broker_url: str,
        _token: str,
        _payload: Mapping[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        assert target.parent.is_dir()
        assert not (target.parent / client.OUTPUT_PREFLIGHT_SENTINEL).exists()
        return 200, _sample_broker_response()

    monkeypatch.setattr(client, "_post_broker_json", fake_post)
    assert client.main(_client_args("output/nested/response.json")) == 0


def test_client_output_directory_file_collision_blocks_before_broker_post(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(client, "ROOT", tmp_path)
    monkeypatch.setattr(client, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setenv(client.TOKEN_ENV_VAR, "temporary-session")
    blocked = tmp_path / "output" / "blocked"
    blocked.parent.mkdir()
    blocked.write_text("collision", encoding="utf-8")
    called = False

    def fake_post(*_args: Any, **_kwargs: Any) -> tuple[int, dict[str, Any]]:
        nonlocal called
        called = True
        return 200, _sample_broker_response()

    monkeypatch.setattr(client, "_post_broker_json", fake_post)
    assert client.main(_client_args("output/blocked/response.json")) == 2
    assert called is False
    assert client.OUTPUT_HYGIENE_DECISION in capsys.readouterr().err


def test_client_refuses_output_outside_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(client, "ROOT", tmp_path)
    monkeypatch.setattr(client, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setenv(client.TOKEN_ENV_VAR, "temporary-session")
    assert client.main(_client_args(str(tmp_path / "outside.json"))) == 2


@pytest.mark.parametrize(
    "forbidden",
    [
        "raw_provider_payload",
        "raw_search_response",
        "raw_content",
        "auth",
        "token",
        "secret",
        "prompt",
        "full_trace",
        "db_row",
    ],
)
def test_sanitizer_rejects_raw_or_private_fields(forbidden: str) -> None:
    response = _sample_broker_response()
    response["results"][0][forbidden] = "private"
    with pytest.raises(ProviderExecutionContractError):
        client.sanitize_broker_response(
            response,
            provider="serper",
            operation=SEARCH_QUERY_OPERATION,
            request_payload=_request(),
        )


def test_sanitizer_converts_tavily_result_raw_content_to_extracted_text() -> None:
    normalized = normalize_search_provider_result(
        {
            "title": "Official",
            "url": "https://example.gov/current",
            "content": "Snippet",
            "raw_content": "Official source text. " * 200,
        },
        provider="tavily",
        result_rank=1,
        provider_call_index=1,
    )
    assert "raw_content" not in normalized
    assert normalized["provider_extracted_text_sanitized"] is True
    assert normalized["provider_extracted_text_bounded"] is True
    assert normalized["provider_extracted_text_char_count"] <= 2_000
    assert normalized["provider"] == "tavily"


def test_sanitizer_rejects_tavily_envelope_raw_content() -> None:
    response = _sample_broker_response("tavily")
    response["raw_content"] = "blocked"
    with pytest.raises(ProviderExecutionContractError):
        client.sanitize_broker_response(
            response,
            provider="tavily",
            operation=SEARCH_QUERY_OPERATION,
            request_payload=_request("tavily"),
        )


def test_sanitizer_rejects_raw_retention_true() -> None:
    response = _sample_broker_response()
    response["raw_provider_payload_retained"] = True
    with pytest.raises(ProviderExecutionContractError, match="must_be_false"):
        client.sanitize_broker_response(
            response,
            provider="serper",
            operation=SEARCH_QUERY_OPERATION,
            request_payload=_request(),
        )


def test_static_boundary_has_no_dotenv_provider_or_scry_authority_imports() -> None:
    imported = _imports(SCRIPT)
    source = SCRIPT.read_text(encoding="utf-8")
    assert "dotenv" not in imported
    assert "scripts.provider_execution_broker" not in imported
    assert "core.search_providers" not in imported
    assert "core.validation_profiles" not in imported
    for token in (
        "load_dotenv",
        "OPENAI_API_KEY",
        "SERPER_API_KEY",
        "TAVILY_API_KEY",
        "ALLOWLISTED_JOBS",
        "validation_profile",
        "EvidenceLedger",
        "RunKernel",
        "subprocess",
    ):
        assert token not in source
