"""Ordinary Research routing, attempt accounting and selected-source custody."""

import json

import pytest
from test_research_loop import Script, answer, decision, no_fetch, request

from core.dual_read import DualReadResult, ReadAttempt
from core.transport import FetchedMaterial
from scryraven import research
from scryraven.dogfood_diagnostics import TurnDiagnostics

URL = "https://example.test/original"
TEXT = "The original article establishes the exact threshold of seven."


def dual_result(url, providers, *, winner="exa"):
    attempts = tuple(ReadAttempt(provider, True, True, "usable" if provider == winner else "cancelled",
                                 None, 0.01, 0.25) for provider in providers)
    return DualReadResult(winner, FetchedMaterial(url, TEXT), attempts, winner, "first_usable")


def test_dual_read_accounts_for_both_arms_and_publishes_only_the_selected_original(monkeypatch):
    calls = []
    diagnostic = TurnDiagnostics()
    monkeypatch.setattr(research, "configured_read_providers", lambda: ("linkup", "exa"))

    def retrieve(url, *, providers, timeout_seconds):
        calls.append((url, providers, timeout_seconds))
        return dual_result(url, providers)

    monkeypatch.setattr(research, "fetch_dual", retrieve)
    model = Script(decision(requests=[request("read", target=URL, mode="full"),
                                      request("read", target=URL, mode="local")]),
                   decision("return", refs=["E1"]),
                   answer("The threshold is seven. [E1]"))
    result = research.run(f"Read the original at {URL}", model=model, observe=diagnostic.observe)

    assert len(calls) == 1 and calls[0] == (URL, ("linkup", "exa"), 300)
    assert len(result.evidence) == 1 and result.evidence[0].content == TEXT
    assert result.citations[0].url == URL
    reads = diagnostic.acquisitions
    assert [row["provider"] for row in reads] == ["exa", "local"]
    assert reads[0]["first_usable_provider"] == "exa"
    assert [row["status"] for row in reads[0]["read_provider_attempts"]] == ["cancelled", "usable"]
    assert TEXT not in json.dumps(reads)
    assert result.trace[-1]["budget"]["external_attempts"] == 1
    assert result.trace[-1]["budget"]["physical_acquisition_dispatches"] == 2
    assert diagnostic.physical_acquisition_dispatches == 2
    assert "physical_acquisition_dispatches" not in model.calls[1][2]["budget"]


@pytest.mark.parametrize("provider", ["linkup", "exa"])
def test_only_configured_provider_uses_one_slot(monkeypatch, provider):
    monkeypatch.setattr(research, "configured_read_providers", lambda: (provider,))

    def retrieve(url, *, providers, **_kwargs):
        assert providers == (provider,)
        return dual_result(url, providers, winner=provider)

    monkeypatch.setattr(research, "fetch_dual", retrieve)
    model = Script(decision(requests=[request("read", target=URL)]), decision("return", refs=["E1"]),
                   answer("The threshold is seven. [E1]"))
    result = research.run(f"Read {URL}", model=model)
    assert result.trace[-1]["budget"]["physical_acquisition_dispatches"] == 1
    assert result.trace[-1]["budget"]["external_attempts"] == 1


def test_failed_and_undispatched_arms_charge_only_required_physical_allowance(monkeypatch):
    monkeypatch.setattr(research, "configured_read_providers", lambda: ("linkup", "exa"))
    outcomes = [ReadAttempt("linkup", False, False, "error", "read_worker_failed", None, None),
                ReadAttempt("exa", True, True, "error", "exa_transport_failed", 0.01, 0.2)]
    monkeypatch.setattr(research, "fetch_dual", lambda *args, **kwargs:
                        DualReadResult(None, None, tuple(outcomes), None, "no_usable_material"))
    model = Script(decision(requests=[request("read", target=URL)]), decision("return"),
                   answer("The source could not be read.", "unable", missing="No original was retrieved."))
    result = research.run(f"Read {URL}", model=model)
    assert not result.evidence
    assert result.trace[-1]["budget"]["external_attempts"] == 1
    assert result.trace[-1]["budget"]["physical_acquisition_dispatches"] == 1


def test_physical_reservation_preserves_single_read_and_prevents_search_overspend(monkeypatch):
    monkeypatch.setattr(research, "PHYSICAL_ACQUISITION_DISPATCH_LIMIT", 2)
    monkeypatch.setattr(research, "configured_read_providers", lambda: ("linkup", "exa"))
    calls = []

    def search(query):
        calls.append(query)
        return []

    def retrieve(url, *, providers, **_kwargs):
        calls.append(providers)
        return dual_result(url, providers, winner="linkup")

    monkeypatch.setattr(research, "fetch_dual", retrieve)
    model = Script(decision(requests=[request("search", query="first"), request("read", target=URL),
                                      request("search", query="over budget")]),
                   decision("return", refs=["E1"]), answer("Seven. [E1]"))
    result = research.run(f"Read {URL}", model=model, search=search)
    assert calls == ["first", ("linkup",)]
    assert result.trace[-1]["budget"]["external_attempts"] == 2
    assert result.trace[-1]["budget"]["physical_acquisition_remaining"] == 0


def test_missing_configuration_spends_logical_attempt_but_not_dispatch(monkeypatch):
    monkeypatch.setattr(research, "configured_read_providers", lambda: ())
    monkeypatch.delenv("LINKUP_API_KEY", raising=False)
    model = Script(decision(requests=[request("read", target=URL)]), decision("return"),
                   answer("The source is unavailable.", "unable", missing="No configured Read transport."))
    result = research.run(f"Read {URL}", model=model)
    assert result.trace[-1]["budget"]["external_attempts"] == 1
    assert result.trace[-1]["budget"]["physical_acquisition_dispatches"] == 0


def test_no_dispatch_when_logical_allowance_is_exhausted(monkeypatch):
    monkeypatch.setattr(research, "configured_read_providers", lambda: ("linkup", "exa"))
    monkeypatch.setattr(research, "fetch_dual", no_fetch)
    model = Script(decision(requests=[request("read", target=URL)]), decision("return"),
                   answer("No original was retrieved.", "unable", missing="Acquisition allowance exhausted."))
    result = research.run(f"Read {URL}", model=model, limits=research.RunLimits(external_attempts=0))
    assert result.trace[-1]["budget"]["external_attempts"] == 0
    assert result.trace[-1]["budget"]["physical_acquisition_dispatches"] == 0
