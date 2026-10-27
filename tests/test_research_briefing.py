"""Briefing communication through ordinary sessions and injected native transports.

These tests establish runtime behavior, not live model judgment or answer quality.
"""
from __future__ import annotations

import json

import pytest
from test_research_first_resumable import (
    answer,
    packet,
    reply,
    request,
    results,
    scripted,
    stages,
    tool,
)

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.errors import RunError
from scryraven.presentation import source_body_html
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore


def decision(*, briefing=None, action="research", requests=(), refs=(), retain=()):
    return {"briefing": briefing, "action": action, "requests": list(requests),
            "retain": list(retain), "evidence_refs": list(refs)}


def forbidden(*_args, **_kwargs):
    pytest.fail("This integration must not call an external provider")


def candidate(url, text):
    return DiscoveryCandidate("Synthetic publication", url, text,
                              context_kind="provider_highlights")


def test_source_discovered_relationship_reaches_answer_with_originals(monkeypatch):
    question = "Which engine was modified, and what rating applies to it?"
    lead = ("The modified engine is the Finch, not the aircraft's Heron engine. "
            "Finch specifications: https://example.org/finch .")
    specifications = "Finch rating: 12 units in normal operation; 9 units in winter."
    provisional = "The modified engine is Finch [E1]; its applicable rating remains to be read."
    briefing = ("Finch, not Heron, is the modified engine [E1]. Its rating is 12 units normally "
                "and 9 in winter [E2]; preserve the operating-condition distinction.")

    def follow_dependency(payload):
        state = packet(payload)
        assert state["evidence"][0]["content"] == lead
        return reply(decision(briefing=provisional, retain=["E1"], requests=[
            request("read", query="", target="https://example.org/finch")]))

    def finish_research(payload):
        state = packet(payload)
        assert state["research_briefing"] == provisional
        assert {row["id"]: row["content"] for row in state["evidence"]} == {
            "E1": lead, "E2": specifications}
        return reply(decision(briefing=briefing, action="return", refs=["E1", "E2"]))

    def synthesize(payload):
        state = packet(payload)
        originals = {row["id"]: row["content"] for row in state["evidence"]}
        assert state["research_briefing"] == briefing
        assert originals == {"E1": lead, "E2": specifications}
        assert all(row["id"] == row["source_id"] for row in state["evidence"])
        # The injected writer consumes both communication channels. A missing
        # briefing cannot silently produce the same successful canned output.
        if "not Heron" in state["research_briefing"] and "9 units in winter" in originals["E2"]:
            return reply(answer("The modified engine is Finch. [E1] Its rating is 12 units normally, "
                                "or 9 in winter. [E2]"))
        return reply(answer("The applicable relationship remains unresolved.", "unable", "none"))

    model, payloads, _ = scripted(monkeypatch, [
        reply(decision(requests=[request(query="modified engine original specification")])),
        follow_dependency, finish_research, synthesize])
    fetched = []

    def fetch(url):
        fetched.append(url)
        return FetchedMaterial(url, specifications)

    session = ResearchSession(model=model, search=lambda _: [candidate("https://example.org/project", lead)],
                              fetch=fetch, lexical_search=forbidden)
    result = session.ask(question)
    assert stages(payloads) == ["research", "research", "research", "answer"]
    assert fetched == ["https://example.org/finch"]
    assert result.posture == "supported" and "Finch" in result.answer
    assert [citation.materials[0].content for citation in result.citations] == [lead, specifications]
    assert result.trace[-1]["budget"]["research_episodes"] == 0


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
@pytest.mark.parametrize("need_resolved", [True, False], ids=["resolved", "still-unresolved"])
def test_new_evidence_preserves_or_resolves_stated_need_in_answer_briefing(monkeypatch, backend, need_resolved):
    """Scripted judgments prove replacement/null plumbing, not live prompt compliance."""
    revenue = ("The 2025 report states revenue of 12 units. "
               "Separate profit statement: https://example.org/profit .")
    profit = ("The final 2025 statement reports profit of 3 units." if need_resolved else
              "The 2025 profit statement is not yet published; this notice supplies no profit figure.")
    provisional = "Revenue is 12 units [E1]. The 2025 profit figure remains unresolved."
    updated = "Revenue is 12 units [E1]; the final 2025 statement establishes profit of 3 units [E2]."
    expected_briefing = updated if need_resolved else provisional

    def investigate_stated_need(payload):
        state = packet(payload)
        assert state["evidence"][0]["content"] == revenue
        return reply(decision(briefing=provisional, retain=["E1"], requests=[
            request("read", target="https://example.org/profit")]))

    def handoff_after_acquisition(payload):
        state = packet(payload)
        assert state["research_briefing"] == provisional
        assert {row["id"]: row["content"] for row in state["evidence"]} == {
            "E1": revenue, "E2": profit}
        # Resolved work replaces the old need; a genuinely unchanged open need
        # remains available without rewriting the same account.
        return reply(decision(briefing=updated if need_resolved else None,
                              action="return", refs=["E1", "E2"]))

    def finish(payload):
        state = packet(payload)
        assert state["research_briefing"] == expected_briefing
        assert {row["id"]: row["content"] for row in state["evidence"]} == {
            "E1": revenue, "E2": profit}
        if need_resolved:
            assert "remains unresolved" not in state["research_briefing"]
            return reply(answer("Revenue was 12 units [E1] and profit was 3 units. [E2]"))
        assert "profit figure remains unresolved" in state["research_briefing"]
        return reply(answer("Revenue was 12 units. [E1] The available notice supplies no profit figure. [E2]",
                            "partial", missing="The 2025 profit figure"))

    model, payloads, _ = scripted(monkeypatch, [
        reply(decision(requests=[request(query="2025 report revenue and profit")])),
        investigate_stated_need, handoff_after_acquisition, finish], backend)
    observed = []
    session = ResearchSession(
        model=model, search=lambda _: [candidate("https://example.org/revenue", revenue)],
        fetch=lambda url: FetchedMaterial(url, profit), lexical_search=forbidden, observe=observed.append)
    result = session.ask("What were the 2025 revenue and profit?")

    assert stages(payloads) == ["research", "research", "research", "answer"]
    assert result.posture == ("supported" if need_resolved else "partial")
    assert [citation.materials[0].content for citation in result.citations] == [revenue, profit]
    exposure, = [event for event in observed
                 if event["action"] == "exposure" and event["contract"] == "answer"]
    assert exposure["research_briefing"] == expected_briefing
    final, = [event for event in result.trace if event["action"] == "answer_decision"]
    assert final["decision"]["missing_information"] == (None if need_resolved else "The 2025 profit figure")
    assert not any(event["action"] == "response_rejected" for event in result.trace)


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_delegated_revision_survives_native_continuation_and_durable_followup(monkeypatch, tmp_path, backend):
    question = "What is twice the winter limit currently in force?"
    url = "https://example.org/winter-limit"
    old = "The 2024 winter limit is 7 units."
    new = "From January 2026 the winter limit is 9 units, replacing the 2024 limit of 7."
    provisional = "The winter limit appears to be 7 units [E1]; current applicability needs confirmation."
    revised = "E2 supersedes E1 from January 2026: use 9 units, not 7, for the current winter limit."

    def request_update(payload):
        state = packet(payload)
        assert state["research_briefing"] == provisional
        assert state["evidence"][0]["content"] == old
        return tool("research", {"need": "Check whether a later rule supersedes the 2024 winter limit."}, "update")

    def delegated_route(payload):
        state = packet(payload)
        assert state["research_briefing"] == provisional
        assert "later rule" in state["delegated_need"]
        return reply(decision(briefing=None, requests=[request("read", query="", target="E1", mode="refresh")]))

    def revise(payload):
        state = packet(payload)
        assert state["research_briefing"] == provisional  # null did not erase it
        assert next(row for row in state["evidence"] if row["id"] == "E2")["content"] == new
        return reply(decision(briefing=revised, action="return", refs=["E2"]))

    def request_retained_clarification(payload):
        returned = results(payload)["update"]
        assert returned["research_briefing"] == revised
        assert returned["evidence"][0]["content"] == new
        assert returned["evidence"][0]["id"] == "E2"
        assert returned["evidence"][0]["source_id"] == "E1"
        return tool("research", {"need": "Confirm the effective date from the retained replacement rule."}, "date")

    def confirm_retained_date(payload):
        state = packet(payload)
        assert state["research_briefing"] == revised  # latest episode, not the initial interpretation
        assert "effective date" in state["delegated_need"]
        return reply(decision(briefing=None, action="return", refs=["E2"]))

    def calculate_revised_value(payload):
        returned = results(payload)["date"]
        assert returned["research_briefing"] == revised
        assert returned["evidence"] == []  # previously supplied original is not retransmitted
        value = 9 if "use 9 units" in returned["research_briefing"] else 7
        return tool("calculate", {"expression": f"{value}*2"}, "double")

    def final(payload):
        returned = results(payload)
        assert returned["double"]["value"] == "18"
        assert returned["update"]["research_briefing"] == revised
        return reply(answer(f"The current winter limit is 9 units, so twice it is {returned['double']['value']} units. [E2]"))

    model, payloads, _ = scripted(monkeypatch, [
        reply(decision(requests=[request()])),
        reply(decision(briefing=provisional, action="return", refs=["E1"])),
        request_update, delegated_route, revise, request_retained_clarification,
        confirm_retained_date, calculate_revised_value, final], backend)
    store = SQLiteSessionStore(tmp_path / "briefing.sqlite3")
    fetched = []

    def fetch(target):
        fetched.append(target)
        return FetchedMaterial(target, new)

    session = ResearchSession.create(store=store, model=model, search=lambda _: [candidate(url, old)],
                                     fetch=fetch, lexical_search=forbidden)
    result = session.ask(question)
    assert result.posture == "supported" and "18 units" in result.answer
    assert fetched == [url]
    owners = [payload for payload in payloads if payload["text"]["format"]["name"] == "answer"]
    assert len(owners) == 4
    assert all(owner["input"][:2] == owners[0]["input"][:2] for owner in owners)
    assert any(item.get("encrypted_content") == "opaque-update" for item in owners[-1]["input"])
    assert [item.content for item in session.acquisitions] == [old, new]
    assert result.citations[0].source_id == "E1"
    historical = session.turns[0]
    historical_html = source_body_html(historical.citations[0])
    assert new in historical_html

    followup_briefing = "The earlier 7-unit rule [E1] was replaced by the 9-unit rule [E2]."

    def fresh_followup(payload):
        state = packet(payload)
        assert state["research_briefing"] is None
        assert {row["id"]: row["content"] for row in state["evidence"]} == {"E1": old, "E2": new}
        assert state["conversation_context"][0]["answer"] == result.answer
        return reply(decision(requests=[request("read", query="", target="E1", mode="local")], retain=["E2"]))

    def compare(payload):
        state = packet(payload)
        assert state["research_briefing"] == followup_briefing
        assert {row["id"]: row["content"] for row in state["evidence"]} == {"E1": old, "E2": new}
        return reply(answer("The earlier limit was 7 units; from January 2026 it is 9. [E1][E2]"))

    followup, followup_payloads, _ = scripted(monkeypatch, [fresh_followup,
        reply(decision(briefing=followup_briefing, action="return", refs=["E1", "E2"])), compare], backend)
    reopened = ResearchSession.open(session.session_id, store=store, model=followup,
                                    search=forbidden, fetch=forbidden, lexical_search=forbidden)
    comparison = reopened.ask("What changed from the earlier rule?")
    assert stages(followup_payloads) == ["research", "research", "answer"]
    assert comparison.posture == "supported"
    assert comparison.trace[-1]["budget"]["external_attempts"] == 0
    assert reopened.turns[0] == historical
    restored = ResearchSession.open(session.session_id, store=store, model=forbidden,
                                    search=forbidden, fetch=forbidden, lexical_search=forbidden)
    assert restored.metadata.revision == 2 and restored.turns == reopened.turns
    assert source_body_html(restored.turns[0].citations[0]) == historical_html
    # Source-level compact numbering retains both supplied versions of the same
    # publication, not just the last material alias used in prose.
    assert [item.content for item in restored.turns[0].citations[0].materials] == [old, new]


def test_invalid_selection_preserves_useful_partial_without_research_retry(monkeypatch):
    text = "The report states revenue of 12 units, but contains no profit figure."
    briefing = "Revenue is 12 [E1]. Profit remains unresolved; the proposed E99 reference is not available."

    def partial(payload):
        state = packet(payload)
        assert state["research_briefing"] == briefing
        assert [row["id"] for row in state["evidence"]] == ["E1"]
        assert state["evidence"][0]["content"] == text
        assert len(state["selection_limitations"]) == 2
        return reply(answer("Revenue is 12 units. [E1] The available report does not establish profit.",
                            "partial", missing="Profit figure"))

    model, payloads, _ = scripted(monkeypatch, [
        reply(decision(requests=[request()])),
        reply(decision(briefing=briefing, action="return", refs=["E1", "C1", "E99"])), partial])
    session = ResearchSession(model=model, search=lambda _: [candidate("https://example.org/report", text)],
                              fetch=forbidden, lexical_search=forbidden)
    result = session.ask("What were revenue and profit?")
    assert stages(payloads) == ["research", "research", "answer"]
    assert result.posture == "partial" and result.citations[0].materials[0].content == text
    assert not any(event["action"] == "response_rejected" for event in result.trace)


def test_briefing_reference_cannot_create_citation_authority(monkeypatch):
    text = "The only acquired source states seven."
    model, payloads, _ = scripted(monkeypatch, [
        reply(decision(requests=[request()])),
        reply(decision(briefing="Unsupported proposed finding [E99].", action="return", refs=["E1", "E99"])),
        reply(answer("A claim purportedly established by the briefing. [E99]"))])
    session = ResearchSession(model=model, search=lambda _: [candidate("https://example.org/only", text)],
                              fetch=forbidden, lexical_search=forbidden)
    with pytest.raises(RunError, match="invalid_citation_reference"):
        session.ask("What is externally established?")
    assert stages(payloads) == ["research", "research", "answer"]
    assert session.turns == () and session.acquisitions == ()
    assert [row["id"] for row in packet(payloads[-1])["evidence"]] == ["E1"]


def test_premise_briefing_and_calculation_need_no_external_evidence(monkeypatch):
    briefing = "User stipulates 12 lots of 7 units; doubling the total is a conditional calculation, not an external fact."

    def calculate(payload):
        state = packet(payload)
        assert state["research_briefing"] == briefing and state["evidence"] == []
        return tool("calculate", {"expression": "12*7*2"}, "premise")

    def finish(payload):
        value = results(payload)["premise"]["value"]
        assert value == "168"
        return reply(answer(f"Under your stated assumptions, twice the total is {value} units.", basis="user_premises"))

    model, payloads, _ = scripted(monkeypatch, [
        reply(decision(briefing=briefing, action="return")), calculate, finish])
    session = ResearchSession(model=model, search=forbidden, fetch=forbidden, lexical_search=forbidden)
    result = session.ask("Assume 12 lots of 7 units; what is twice their total?")
    assert result.posture == "supported" and result.citations == () and result.evidence == ()
    assert stages(payloads) == ["research", "answer", "answer"]
    assert result.trace[-1]["budget"]["external_attempts"] == 0
    assert "research_briefing" not in json.dumps(session.turns[0].__dict__)
