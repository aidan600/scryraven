"""No-network smoke tests through the production plan streaming adapter."""
from __future__ import annotations

import json
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from test_production_plan_transport import ENCRYPTED, Reply, forbidden
from test_research_loop import answer, decision, request

from scripts import aid10_plan_smoke as pilot
from scryraven.acquisition import AcquisitionError
from scryraven.chatgpt_plan.http import JWKS, RESPONSES, TOKEN, PlanError, PublicHTTP


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


def auth(http):
    def access(account, *, timeout):
        assert account == "personal" and 0 < timeout <= 45
        return {"access_token": "synthetic-private-plan-token"}

    return SimpleNamespace(access=access, http=http)


def mock_streams(monkeypatch, replies, *, wrong_model=False, tier=None):
    requested = []
    remaining = iter(replies)

    def send(_session, prepared, **kwargs):
        assert (prepared.method, prepared.url) == ("POST", RESPONSES)
        assert prepared.headers["Authorization"] == "Bearer synthetic-private-plan-token"
        assert kwargs["allow_redirects"] is False
        payload = json.loads(prepared.body)
        requested.append(payload)
        stream = next(remaining).stream(payload)
        if tier is not None:
            stream.events[-1]["response"]["service_tier"] = tier
        if wrong_model:
            stream.events[-1]["response"]["model"] = "gpt-6.1-terra"
        return stream

    monkeypatch.setattr(requests.Session, "send", send)
    return requested


@pytest.mark.parametrize("arm,tier", [("control", None), ("hardened", "priority")])
def test_frozen_search_read_and_native_plan_continuation(monkeypatch, tmp_path, arm, tier):
    requested = mock_streams(monkeypatch, [
        Reply("research", decision(requests=[request(query="2024 Honda Passport vs GE Passport aircraft engine")])),
        Reply("research", decision(requests=[request("read", target=f"C{n}") for n in range(1, 4)])),
        Reply("research", decision("return", refs=("E1", "E2", "E3"))),
        Reply("answer", tool="3471 / 1000"),
        Reply("answer", answer("Honda uses a 3.5-litre V6. [E1] [E2] The GE Passport is a turbofan. [E3]")),
    ], tier=tier)
    pilot.run_arm(arm, tmp_path, auth_factory=auth)
    observed = pilot.summary(arm, tmp_path, "finished")
    assert observed["processing"] == "plan-default"
    assert observed["exact_models_observed"] is True
    assert observed["responses_dispatched"] == 5
    assert observed["posture"] == "supported" and observed["citation_count"] == 3
    assert observed["blocked_transport"] == []
    assert {row["returned_tier"] for row in observed["receipts"]} == {tier}
    assert [row["model"] for row in requested] == ["gpt-6-luna"] * 3 + ["gpt-6.2-sol"] * 2
    assert [row["reasoning"]["effort"] for row in requested] == ["high"] * 3 + ["medium"] * 2
    assert all(row["stream"] and row["store"] is False for row in requested)
    assert all("service_tier" not in row and "max_output_tokens" not in row for row in requested)
    assert any(row.get("type") == "function_call_output" for row in requested[-1]["input"])
    assert (tmp_path / "session.sqlite3").is_file()
    fixture = pilot.load_fixture()
    retained = pilot.read_rows(tmp_path / "outcome.jsonl")[0]["outcome"]["citations"]
    assert {citation["url"]: citation["materials"][0]["content"] for citation in retained} == {
        row["url"]: row["text"] for row in fixture["sources"]
    }
    first_instruction = requested[0]["input"][0]["content"][0]["text"]
    assert ("Before handing off" in first_instruction) == (arm == "hardened")
    assert "Before finalizing" not in requested[-1]["input"][0]["content"][0]["text"]
    for path in tmp_path.glob("*.jsonl"):
        data = path.read_text(encoding="utf-8")
        assert "synthetic-private-plan-token" not in data and ENCRYPTED not in data


def test_mismatched_plan_model_fails_without_fallback(monkeypatch, tmp_path):
    requested = mock_streams(monkeypatch, [Reply("research", decision("return"))], wrong_model=True)
    pilot.run_arm("control", tmp_path, auth_factory=auth)
    observed = pilot.summary("control", tmp_path, "finished")
    assert observed["exact_models_observed"] is False and observed["posture"] is None
    assert observed["failure"] == {"stage": "research", "code": "malformed_model_response"}
    assert len(requested) == observed["responses_dispatched"] == 1


def test_provider_gate_blocks_paid_endpoints_same_url_api_and_extra_requests(monkeypatch):
    delivered = []
    monkeypatch.setattr(requests.Session, "send", lambda _session, request, **_kwargs: delivered.append(request.url))
    recorded = []
    with requests.Session() as session:
        http = PublicHTTP(session)
        with pilot.plan_only_http(http, recorded.append):
            for url in ("https://api.exa.ai/search", "https://api.linkup.so/v1/search",
                        "https://api.openrouter.ai/api/v1/responses", RESPONSES):
                # Third-party routes and the same Responses URL through a separate session.
                with pytest.raises(PlanError, match="model_request_rejected"):
                    requests.post(url, allow_redirects=False)
            # Bypass PublicHTTP's own URL validation to test the additional boundary.
            with pytest.raises(PlanError, match="model_request_rejected"):
                session.post("https://api.linkup.so/v1/fetch", allow_redirects=False)
            for _ in range(pilot.SETTINGS.physical_request_limit):
                http.request("POST", RESPONSES, timeout=1)
            with pytest.raises(PlanError, match="model_request_rejected"):
                http.request("POST", RESPONSES, timeout=1)
            for method, url in (("POST", TOKEN), ("GET", JWKS)):
                http.request(method, url, timeout=1)
                with pytest.raises(PlanError, match="model_request_rejected"):
                    http.request(method, url, timeout=1)
    assert delivered == [RESPONSES] * pilot.SETTINGS.physical_request_limit + [TOKEN, JWKS]
    assert sum(row.get("reason") == "network_route_denied" for row in recorded) == 5
    assert sum(row.get("reason") == "request_limit" for row in recorded) == 3


def test_unknown_queries_urls_and_unsupported_provider_routes_fail_closed():
    providers = pilot.FrozenProviders(pilot.load_fixture()["sources"])
    for route in ("search", "lexical_search"):
        for query in ("unrelated airline fleet statistics", "2024 passport renewal", "2025 Honda Passport engine"):
            with pytest.raises(AcquisitionError, match="fixture_search_outside_case"):
                providers.session_options()[route](query)
    with pytest.raises(AcquisitionError, match="fixture_read_unknown_url"):
        providers.read("https://www.honda.ca/en/passport?different-year")
    for route in ("scholarly_search", "scholarly_fetch", "venue_lookup"):
        with pytest.raises(AcquisitionError, match="fixture_provider_disabled"):
            providers.session_options()[route]("passport")
    assert len(providers.search("2024 Honda Passport engine")) == 2
    assert len(providers.search("GE Passport turbofan")) == 1
    assert not any(lead.context for lead in providers.search("Passport engine"))


@pytest.mark.parametrize("blocked", [False, True])
def test_pair_uses_isolated_processes_and_no_paid_environment(monkeypatch, tmp_path, capsys, blocked):
    starts = []
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-api-key")
    monkeypatch.setenv("EXA_API_KEY", "synthetic-exa-key")
    monkeypatch.setenv("LINKUP_API_KEY", "synthetic-linkup-key")

    def start(argv, **options):
        arm, destination = argv[-2:]
        starts.append((arm, destination))
        assert argv[1] == "-I"
        assert options["timeout"] == pilot.PROCESS_SECONDS
        assert not {"OPENAI_API_KEY", "EXA_API_KEY", "LINKUP_API_KEY"} & options["env"].keys()
        assert options["stderr"] == options["stdout"] == pilot.subprocess.DEVNULL
        directory = Path(destination)
        assert not any(directory.iterdir())
        pilot.append_json(directory / "outcome.jsonl", {"outcome": None, "failure": {"code": "scripted"}})
        if blocked:
            pilot.append_json(directory / "dispatch.jsonl", {"status": "blocked", "reason": "network_route_denied"})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(pilot.subprocess, "run", start)
    assert pilot.run_pair(tmp_path) == 1
    expected = pilot.ARMS[:1] if blocked else pilot.ARMS
    assert starts == [(arm, str(tmp_path / arm)) for arm in expected]
    assert [json.loads(line)["arm"] for line in capsys.readouterr().out.splitlines()] == list(expected)
