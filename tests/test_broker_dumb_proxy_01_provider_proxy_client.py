from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from scripts import request_provider_proxy_broker as client

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "request_provider_proxy_broker.py"


def _output_path(name: str) -> Path:
    return ROOT / "output" / name


def _sample_broker_response() -> dict[str, Any]:
    return {
        "results": [
            {
                "title": "Example Result",
                "link": "https://example.gov/current",
                "domain": "example.gov",
                "snippet": "Sanitized result snippet.",
                "date": "2026-06-28",
                "rank": 1,
                "call_index": 1,
            }
        ],
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _normalized_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key).strip().casefold() for key in value}
        for item in value.values():
            keys.update(_normalized_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_normalized_keys(item))
        return keys
    return set()


def _assert_no_custody_evidence_or_citation_keys(payload: Mapping[str, Any]) -> None:
    keys = _normalized_keys(payload)
    assert not keys.intersection(
        {
            "broker_output_is_evidence",
            "broker_output_satisfies_source_obligation",
            "citation",
            "citation_eligible",
            "evidence",
            "evidence_id",
            "evidenceledger",
            "source_custody",
            "source_obligation",
            "source_obligation_satisfied",
            "satisfies_source_obligation",
        }
    )


def test_request_shape_is_generic_provider_proxy_not_phase_job_policy() -> None:
    payload = client.build_provider_proxy_request(
        provider="serper",
        operation="search",
        query="current official example",
        max_results=5,
    )

    assert payload == {
        "request_kind": client.REQUEST_KIND,
        "provider": "serper",
        "operation": "search",
        "query": "current official example",
        "max_results": 5,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    rendered = json.dumps(payload).casefold()
    assert "job_id" not in rendered
    assert "validation_profile" not in rendered
    assert "runkernel" not in rendered
    assert "evidenceledger" not in rendered


@pytest.mark.parametrize("max_results", [0, 11])
def test_request_rejects_unbounded_max_results(max_results: int) -> None:
    with pytest.raises(client.ProviderProxyClientError, match="max_results"):
        client.build_provider_proxy_request(
            provider="serper",
            operation="search",
            query="current official example",
            max_results=max_results,
        )


def test_client_refuses_non_loopback_urls_and_requires_token_and_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(client.TOKEN_ENV_VAR, raising=False)
    assert client.main(
        [
            "--broker-url",
            "http://127.0.0.1:8765/run",
            "--provider",
            "serper",
            "--query",
            "current official example",
            "--output",
            "output/broker_dumb_proxy_missing_token.json",
            "--confirm-provider-call",
        ]
    ) == 2

    assert client.main(
        [
            "--broker-url",
            "https://broker.example.com/run",
            "--provider",
            "serper",
            "--query",
            "current official example",
            "--output",
            "output/broker_dumb_proxy_nonlocal.json",
            "--token",
            "local-token",
            "--confirm-provider-call",
        ]
    ) == 2

    assert client.main(
        [
            "--broker-url",
            "http://127.0.0.1:8765/run",
            "--provider",
            "serper",
            "--query",
            "current official example",
            "--output",
            "output/broker_dumb_proxy_no_confirm.json",
            "--token",
            "local-token",
        ]
    ) == 2


def test_client_writes_only_sanitized_results_under_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = _output_path("broker_dumb_proxy_sanitized_response.json")
    captured: dict[str, Any] = {}

    def fake_post(
        broker_url: str,
        token: str,
        payload: Mapping[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        captured["broker_url"] = broker_url
        captured["token"] = token
        captured["payload"] = dict(payload)
        return 200, _sample_broker_response()

    monkeypatch.setattr(client, "_post_broker_json", fake_post)

    rc = client.main(
        [
            "--broker-url",
            "http://127.0.0.1:8765/run",
            "--provider",
            "serper",
            "--operation",
            "search",
            "--query",
            "current official example",
            "--max-results",
            "5",
            "--output",
            str(output_path),
            "--token",
            "local-token",
            "--confirm-provider-call",
        ]
    )

    assert rc == 0
    assert captured["broker_url"] == "http://127.0.0.1:8765/run"
    assert captured["token"] == "local-token"
    assert captured["payload"]["provider"] == "serper"
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["request_kind"] == client.REQUEST_KIND
    assert written["result_count"] == 1
    assert written["raw_provider_payload_retained"] is False
    assert written["raw_search_response_retained"] is False
    assert written["results"] == [
        {
            "title": "Example Result",
            "url": "https://example.gov/current",
            "domain": "example.gov",
            "snippet": "Sanitized result snippet.",
            "published_or_observed_date": "2026-06-28",
            "result_rank": 1,
            "provider_call_index": 1,
        }
    ]


def test_client_preflights_nested_output_before_broker_post(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(client, "ROOT", tmp_path)
    monkeypatch.setattr(client, "OUTPUT_DIR", tmp_path / "output")
    output_path = tmp_path / "output" / "nested" / "broker_response.json"
    captured: dict[str, Any] = {}

    def fake_post(
        broker_url: str,
        token: str,
        payload: Mapping[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        captured["broker_url"] = broker_url
        captured["token"] = token
        captured["payload"] = dict(payload)
        assert output_path.parent.is_dir()
        assert not (output_path.parent / client.OUTPUT_PREFLIGHT_SENTINEL).exists()
        return 200, _sample_broker_response()

    monkeypatch.setattr(client, "_post_broker_json", fake_post)

    rc = client.main(
        [
            "--broker-url",
            "http://127.0.0.1:8765/run",
            "--provider",
            "serper",
            "--operation",
            "search",
            "--query",
            "current official example",
            "--max-results",
            "5",
            "--output",
            "output/nested/broker_response.json",
            "--token",
            "local-token",
            "--confirm-provider-call",
        ]
    )

    assert rc == 0
    assert captured["broker_url"] == "http://127.0.0.1:8765/run"
    assert output_path.is_file()


def test_client_output_directory_file_collision_blocks_before_broker_post(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(client, "ROOT", tmp_path)
    monkeypatch.setattr(client, "OUTPUT_DIR", tmp_path / "output")
    blocked_dir = tmp_path / "output" / "blocked"
    blocked_dir.parent.mkdir(parents=True)
    blocked_dir.write_text("not a directory\n", encoding="utf-8")
    captured: dict[str, Any] = {}

    def fake_post(
        broker_url: str,
        token: str,
        payload: Mapping[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        captured["called"] = True
        return 200, _sample_broker_response()

    monkeypatch.setattr(client, "_post_broker_json", fake_post)

    rc = client.main(
        [
            "--broker-url",
            "http://127.0.0.1:8765/run",
            "--provider",
            "serper",
            "--operation",
            "search",
            "--query",
            "current official example",
            "--max-results",
            "5",
            "--output",
            "output/blocked/broker_response.json",
            "--token",
            "local-token",
            "--confirm-provider-call",
        ]
    )

    err = capsys.readouterr().err
    assert rc == 2
    assert captured == {}
    assert client.OUTPUT_HYGIENE_DECISION in err
    assert "could_not_create_output_directory" in err
    assert "local-token" not in err
    assert ".env" not in err
    assert "api_key" not in err.casefold()
    assert "raw_provider_payload\":" not in err
    assert "raw_search_response\":" not in err
    assert "full_trace" not in err


def test_client_refuses_output_outside_output() -> None:
    assert client.main(
        [
            "--broker-url",
            "http://127.0.0.1:8765/run",
            "--provider",
            "serper",
            "--query",
            "current official example",
            "--output",
            str(ROOT / "not-output" / "broker_response.json"),
            "--token",
            "local-token",
            "--confirm-provider-call",
        ]
    ) == 2


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

    with pytest.raises(client.ProviderProxyClientError):
        client.sanitize_broker_response(
            response,
            provider="serper",
            operation="search",
        )


def test_sanitizer_converts_tavily_result_raw_content_to_extracted_text() -> None:
    response = _sample_broker_response()
    response["results"][0]["raw_content"] = "Official source text. " * 20

    sanitized = client.sanitize_broker_response(
        response,
        provider="tavily",
        operation="search",
    )

    result = sanitized["results"][0]
    assert "raw_content" not in result
    assert result["provider_extracted_text"].startswith("Official source text.")
    assert result["provider_extracted_text_sanitized"] is True
    assert result["provider_extracted_text_bounded"] is True
    assert result["provider_extracted_text_char_count"] == len(
        result["provider_extracted_text"]
    )
    assert result["provider_extracted_content_type"] == "text/html"
    _assert_no_custody_evidence_or_citation_keys(sanitized)


def test_sanitizer_rejects_tavily_envelope_raw_content() -> None:
    response = _sample_broker_response()
    response["raw_content"] = "raw envelope content must not be accepted"

    with pytest.raises(client.ProviderProxyClientError, match="raw/private"):
        client.sanitize_broker_response(
            response,
            provider="tavily",
            operation="search",
        )


def test_sanitizer_rejects_raw_retention_true() -> None:
    response = _sample_broker_response()
    response["raw_provider_payload_retained"] = True

    with pytest.raises(client.ProviderProxyClientError, match="raw provider"):
        client.sanitize_broker_response(
            response,
            provider="serper",
            operation="search",
        )


def test_static_boundary_has_no_dotenv_provider_or_scry_authority_imports() -> None:
    imported = _imports(SCRIPT)
    source = SCRIPT.read_text(encoding="utf-8")

    assert "dotenv" not in imported
    assert "core.search_providers" not in imported
    assert "core.validation_profiles" not in imported
    assert "core.run_kernel" not in imported
    for token in (
        "load_dotenv",
        "SERPER_API_KEY",
        "ALLOWLISTED_JOBS",
        "validation_profile",
        "EvidenceLedger",
        "RunKernel",
        "subprocess",
    ):
        assert token not in source
