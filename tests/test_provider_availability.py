"""Turn-local operational availability, using scripted models and offline transports."""

import json

import pytest
from pdf_fixtures import text_pdf
from test_research_first_resumable import (
    delegated,
    initial,
    reply,
    request,
    results,
    scripted,
    stages,
    tool,
)
from test_research_loop import Script, answer, decision
from test_research_passage_locators import owned

from core.exa_transport import DiscoveryCandidate, ExaTransportError
from core.linkup_transport import LinkupTransportError
from core.serper_transport import SerperTransportError
from core.transport import FetchedMaterial
from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.forensic_log import ForensicLog
from scryraven.research import run
from scryraven.session import ResearchSession
from scryraven.sources import Evidence

URL = "https://example.test/original"
VALUE = "The exact synthetic value is seven."


def prohibited(*_args, **_kwargs):
    pytest.fail("unexpected external transport")


class Missing:
    def __init__(self, provider):
        self.provider, self.calls = provider, []

    def __call__(self, value):
        self.calls.append(value)
        error = {"exa": ExaTransportError, "serper": SerperTransportError,
                 "linkup": LinkupTransportError}[self.provider]
        raise error(f"{self.provider}_configuration_missing")


class RepeatingResearch:
    """Repeat the historical impossible routes; accept an early operational handoff."""

    def __init__(self, kinds):
        self.kinds, self.calls = kinds, []

    def __call__(self, stage, _prompt, packet, _schema):
        self.calls.append((stage, packet))
        if stage == "answer":
            return json.dumps(answer("The external fact is not established: search is not configured.",
                                     "unable", missing="Search configuration is missing."))
        number = sum(call[0] == "research" for call in self.calls)
        if number > len(self.kinds):
            return json.dumps(decision("return"))
        return json.dumps(decision(requests=[request(self.kinds[number - 1],
                                                     query=f"synthetic fact wording {number}")]))


def highlights(_query):
    return [DiscoveryCandidate("Synthetic original", URL, VALUE,
                               context_kind="provider_highlights")]


def budget(result):
    return result.trace[-1]["budget"]


def test_original_twelve_exa_four_serper_pattern_stops_before_seventeen_research_calls():
    exa, serper = Missing("exa"), Missing("serper")
    model = RepeatingResearch(["search"] * 12 + ["search_lexical"] * 4)
    result = run("Find a synthetic public fact.", model=model, search=exa,
                 lexical_search=serper, fetch=prohibited)
    assert len(exa.calls) == 1
    assert not serper.calls
    assert [stage for stage, _ in model.calls] == ["research", "research", "answer"]
    assert budget(result)["external_attempts"] == 1
    assert not result.evidence and not result.citations
    assert result.posture == "unable"
    limitations = model.calls[-1][1]["acquisition_limitations"]
    assert any(item.get("provider") == "exa" and item["code"] == "exa_configuration_missing"
               for item in limitations)


def test_exa_then_serper_configuration_failure_hands_off_without_another_luna_call():
    exa, serper = Missing("exa"), Missing("serper")
    model = RepeatingResearch(["search", "search_lexical"] + ["search"] * 14)
    result = run("Find a synthetic public fact.", model=model, search=exa,
                 lexical_search=serper, fetch=prohibited)
    assert len(exa.calls) == len(serper.calls) == 1
    assert [stage for stage, _ in model.calls] == ["research", "research", "answer"]
    assert budget(result)["external_attempts"] == 2
    limitations = model.calls[-1][1]["acquisition_limitations"]
    assert {(item.get("provider"), item["code"]) for item in limitations
            if item.get("provider")} == {
                ("exa", "exa_configuration_missing"), ("serper", "serper_configuration_missing")}
    assert not model.calls[-1][1]["evidence"]
    assert result.posture == "unable" and not result.citations


def test_missing_serper_does_not_block_working_exa():
    serper = Missing("serper")
    model = Script(decision(requests=[request("search_lexical")]), decision(),
                   decision("return", ["E1"]), answer(VALUE + " [E1]"))
    result = run("Find the value.", model=model, search=highlights,
                 lexical_search=serper, fetch=prohibited)
    assert len(serper.calls) == 1 and result.posture == "supported"
    assert result.citations[0].materials[0].content == VALUE
    assert budget(result)["external_attempts"] == 2


def test_missing_exa_keeps_configured_known_url_read_available():
    exa, fetched = Missing("exa"), []
    model = Script(decision(), decision(requests=[request("read", query="", target="C1")]),
                   decision("return", ["E1"]), answer(VALUE + " [E1]"))

    def fetch(url):
        fetched.append(url)
        return FetchedMaterial(url, VALUE)

    result = run(f"Find the value in {URL}", model=model, search=exa, fetch=fetch)
    assert len(exa.calls) == 1 and fetched == [URL]
    assert result.posture == "supported" and result.evidence[0].content == VALUE
    assert budget(result)["external_attempts"] == 2


def test_both_search_lanes_missing_still_allow_known_url_read():
    exa, serper = Missing("exa"), Missing("serper")
    model = Script(decision(), decision(requests=[request("search_lexical")]),
                   decision(requests=[request("read", query="", target="C1")]),
                   decision("return", ["E1"]), answer(VALUE + " [E1]"))
    result = run(f"Find the value in {URL}", model=model, search=exa, lexical_search=serper,
                 fetch=lambda url: FetchedMaterial(url, VALUE))
    assert result.posture == "supported" and result.evidence[0].content == VALUE
    assert budget(result)["external_attempts"] == 3


@pytest.mark.parametrize("source", ["retained", "pdf"])
def test_missing_linkup_keeps_retained_local_find_and_read_usable(source):
    linkup = Missing("linkup")
    original = Evidence("E1", URL, "Retained original", VALUE)
    document = owned(text_pdf([VALUE]))
    ref = "E1" if source == "retained" else f"D1@0:{len(document.extracted_text)}"
    local_target = "E1" if source == "retained" else "D1"
    model = Script(
        decision(requests=[request("read", query="", target="C1", mode="refresh")]),
        decision(requests=[request("find", query="seven", scope=[local_target]),
                           request("read", query="", target=local_target, mode="local")]),
        decision("return", [ref]), answer(VALUE + f" [{ref}]"),
    )
    result = run(f"Read {URL}", model=model, search=prohibited, fetch=linkup,
                 retained_acquisitions=(original,) if source == "retained" else (),
                 documents=(document,) if source == "pdf" else ())
    assert len(linkup.calls) == 1
    assert result.posture == "supported" and result.citations
    assert budget(result)["external_attempts"] == 1
    assert VALUE in result.citations[0].materials[0].content


def test_working_configured_paths_keep_normal_behavior():
    searches, lexical, reads = [], [], []

    def search(query):
        searches.append(query)
        return highlights(query)

    def serper(query):
        lexical.append(query)
        return [DiscoveryCandidate("Other original", URL + "/other", "navigation only")]

    def fetch(url):
        reads.append(url)
        return FetchedMaterial(url, "The independently acquired qualification applies.")

    model = Script(decision(), decision(requests=[request("search_lexical")]),
                   decision(requests=[request("read", query="", target="C2")]),
                   decision("return", ["E2"]),
                   answer("The independently acquired qualification applies. [E2]"))
    result = run("Find the qualification.", model=model, search=search,
                 lexical_search=serper, fetch=fetch)
    assert len(searches) == len(lexical) == len(reads) == 1
    assert reads == [URL + "/other"]
    assert budget(result)["external_attempts"] == 3
    assert result.posture == "supported"


def test_next_turn_in_same_session_retries_provider_after_configuration_is_corrected():
    calls = []

    def search(query):
        calls.append(query)
        if len(calls) == 1:
            raise ExaTransportError("exa_configuration_missing")
        return highlights(query)

    model = Script(decision(), decision("return"), answer("Search is unavailable.", "unable"),
                   decision(), decision("return", ["E1"]), answer(VALUE + " [E1]"))
    session = ResearchSession(model=model, search=search, fetch=prohibited)
    first = session.ask("Find the value.")
    second = session.ask("Try the corrected configuration.")
    assert len(calls) == 2
    assert first.posture == "unable" and second.posture == "supported"
    assert budget(first)["external_attempts"] == budget(second)["external_attempts"] == 1
    second_initial = next(packet for stage, _, packet, _ in model.calls
                          if stage == "research" and packet["question"] == "Try the corrected configuration.")
    assert not second_initial.get("unavailable_providers")


def test_explicit_user_premise_answer_needs_no_provider_configuration(monkeypatch):
    for name in ("EXA_API_KEY", "SERPER_API_KEY", "LINKUP_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    model = Script(decision("return"), answer("Under your premise, the value is seven.",
                                               support_basis="user_premises"))
    result = run("Assume the value is seven. What is the assumed value?", model=model,
                 search=prohibited, lexical_search=prohibited, fetch=prohibited)
    assert result.posture == "supported" and not result.citations
    assert budget(result)["external_attempts"] == 0


@pytest.mark.parametrize("failure", [None, "exa_transport_failed", "exa_response_invalid"])
def test_empty_and_nonconfiguration_search_failures_do_not_disable_provider(failure):
    calls = []

    def search(query):
        calls.append(query)
        if failure:
            raise ExaTransportError(failure)
        return []

    model = Script(decision(), decision(), decision("return"), answer("Not established.", "unable"))
    result = run("Find the value.", model=model, search=search, fetch=prohibited)
    assert len(calls) == 2 and budget(result)["external_attempts"] == 2
    assert not model.calls[2][2].get("unavailable_providers")


@pytest.mark.parametrize("failure", ["linkup_timeout", "linkup_connection_failed",
                                     "linkup_endpoint_access_rejected", "linkup_endpoint_rate_limited",
                                     "linkup_endpoint_server_failed", "linkup_material_unavailable"])
def test_ordinary_read_failures_do_not_disable_or_reclassify_provider(failure):
    calls = []

    def fetch(url):
        calls.append(url)
        raise LinkupTransportError(failure)

    model = Script(decision(requests=[request("read", query="", target="C1")]),
                   decision(requests=[request("read", query="", target="C1", focus="new scope")]),
                   decision("return"), answer("Not established.", "unable"))
    result = run(f"Read {URL}", model=model, search=prohibited, fetch=fetch)
    assert len(calls) == 2 and budget(result)["external_attempts"] == 2
    assert [row["code"] for row in model.calls[2][2]["acquisition_history"]] == [failure, failure]
    assert not model.calls[2][2].get("unavailable_providers")


def test_body_free_and_forensic_receipts_distinguish_dispatch_and_local_suppression(tmp_path):
    exa = Missing("exa")
    model = Script(decision(), decision(), answer("Search is not configured.", "unable"))
    diagnostics = TurnDiagnostics()
    forensic = ForensicLog(tmp_path / "observer.jsonl")

    def observe(event):
        diagnostics.observe(event)
        forensic.append(event, session_id="a" * 32, revision_before=0)

    result = run("Find private-query-fragment.", model=model, search=exa,
                 lexical_search=prohibited, fetch=prohibited, observe=observe)
    record = diagnostics.record(session_id="a" * 32, revision_before=0, revision_after=1, result=result)
    first, suppressed = record["acquisitions"]
    assert (first["provider"], first["code"], first["provider_dispatched"], first["suppressed"],
            first["external"]) == ("exa", "exa_configuration_missing", False, False, True)
    assert (suppressed["provider"], suppressed["code"], suppressed["provider_dispatched"],
            suppressed["suppressed"], suppressed["external"]) == (
                "exa", "exa_configuration_missing", False, True, False)
    assert record["external_attempts"] == 1 and len(exa.calls) == 1
    for omitted in ("private-query-fragment", "synthetic fact", "public fact", "https://"):
        assert omitted not in json.dumps(record)
    events = [json.loads(line)["event"] for line in forensic.path.read_text().splitlines()]
    timings = [row for row in events if row["action"] == "acquisition_timing"]
    assert [row["provider_dispatched"] for row in timings] == [False, False]
    assert [row["suppressed"] for row in timings] == [False, True]

    working = TurnDiagnostics()
    good = Script(decision(), decision("return", ["E1"]), answer(VALUE + " [E1]"))
    run("Find the value.", model=good, search=highlights, observe=working.observe)
    assert working.acquisitions[0]["provider_dispatched"] is True
    assert working.acquisitions[0]["suppressed"] is False


def test_known_unavailable_exa_is_suppressed_before_concurrent_group_reservation():
    exa, serper = Missing("exa"), []

    def lexical(query):
        serper.append(query)
        return []

    model = Script(decision(),
                   decision(requests=[request(query="different one"), request(query="different two"),
                                      request("search_lexical")]),
                   decision("return"), answer("Not established.", "unable"))
    result = run("Find a synthetic fact.", model=model, search=exa, lexical_search=lexical)
    assert len(exa.calls) == len(serper) == 1
    assert budget(result)["external_attempts"] == 2


def test_suppressed_search_in_mixed_route_does_not_skip_usable_retained_read():
    exa = Missing("exa")
    original = Evidence("E1", URL, "Retained original", VALUE)
    model = Script(decision(),
                   decision(requests=[request(query="reworded impossible route"),
                                      request("read", query="", target="E1", mode="local")]),
                   decision("return", ["E1"]), answer(VALUE + " [E1]"))
    result = run("Find the value.", model=model, search=exa, fetch=prohibited,
                 retained_acquisitions=(original,))
    assert len(exa.calls) == 1 and budget(result)["external_attempts"] == 1
    assert result.posture == "supported"
    assert result.citations[0].materials == (original,)
    assert model.calls[2][2]["acquisition_history"][-2]["suppressed"] is True
    assert model.calls[2][2]["acquisition_history"][-1]["status"] == "ok"


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_initial_unavailable_state_is_shared_with_delegated_research(monkeypatch, backend):
    exa = Missing("exa")
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("return")),
        tool("research", {"need": "Find the still missing fact."}, "r1"),
        reply(delegated(requests=[request(query="reworded delegated attempt")])),
        reply(answer("Search configuration is missing; the external fact is not established.", "unable")),
    ], backend)
    result = run("Find the external fact.", model=model, search=exa, fetch=prohibited)
    assert len(exa.calls) == 1
    assert stages(payloads) == ["research", "research", "answer", "research", "answer"]
    returned = results(payloads[-1])["r1"]
    assert not returned["evidence"]
    route = next(row for row in returned["acquisition_limitations"] if row.get("provider") == "exa")
    assert route["provider"] == "exa" and route["code"] == "exa_configuration_missing"
    assert budget(result)["external_attempts"] == 1
    assert result.posture == "unable" and not result.citations


def test_delegated_research_hands_back_both_missing_discovery_codes(monkeypatch):
    exa, serper = Missing("exa"), Missing("serper")
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial("return")), tool("research", {"need": "Find an external fact."}, "r1"),
        reply(delegated(requests=[request()])),
        reply(delegated(requests=[request("search_lexical")])),
        reply(answer("Search is not configured, so the fact is not established.", "unable")),
    ])
    result = run("Find an external fact.", model=model, search=exa, lexical_search=serper,
                 fetch=prohibited)
    assert len(exa.calls) == len(serper.calls) == 1
    assert stages(payloads) == ["research", "answer", "research", "research", "answer"]
    returned = results(payloads[-1])["r1"]
    assert not returned["evidence"] and budget(result)["external_attempts"] == 2
    assert {row["code"] for row in returned["acquisition_limitations"] if row.get("provider")} == {
        "exa_configuration_missing", "serper_configuration_missing"}


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_repeated_delegation_after_established_impossibility_spends_no_more_luna_calls(monkeypatch, backend):
    exa, serper = Missing("exa"), Missing("serper")
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])),
        reply(initial(requests=[request("search_lexical")])),
        tool("research", {"need": "Find the missing fact."}, "r1"),
        tool("research", {"need": "Try a different wording of that missing fact."}, "r2"),
        reply(answer("Search configuration is missing, so the fact is not established.", "unable")),
    ], backend)
    result = run("Find an external fact.", model=model, search=exa, lexical_search=serper,
                 fetch=prohibited)
    assert len(exa.calls) == len(serper.calls) == 1
    assert stages(payloads) == ["research", "research", "answer", "answer", "answer"]
    for returned in results(payloads[-1]).values():
        assert not returned["evidence"]
        assert {row["code"] for row in returned["acquisition_limitations"] if row.get("provider")} == {
            "exa_configuration_missing", "serper_configuration_missing"}
    assert budget(result)["external_attempts"] == 2
    assert result.posture == "unable" and not result.citations


def test_delegated_missing_serper_allows_working_exa_and_exact_return(monkeypatch):
    serper = Missing("serper")
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial("return")), tool("research", {"need": "Find the exact original value."}, "r1"),
        reply(delegated(requests=[request("search_lexical")])),
        reply(delegated(requests=[request()])), reply(delegated("return", ["E1"])),
        reply(answer(VALUE + " [E1]")),
    ])
    result = run("Find the external value.", model=model, search=highlights,
                 lexical_search=serper, fetch=prohibited)
    assert len(serper.calls) == 1 and result.posture == "supported"
    assert results(payloads[-1])["r1"]["evidence"][0]["content"] == VALUE
    assert result.citations[0].materials[0].content == VALUE
    assert budget(result)["external_attempts"] == 2


def test_delegated_missing_linkup_retains_local_read_and_find(monkeypatch):
    original = Evidence("E1", URL, "Retained original", VALUE)
    linkup = Missing("linkup")
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial("return")), tool("research", {"need": "Inspect the retained original."}, "r1"),
        reply(delegated(requests=[request("read", query="", target="C1", mode="refresh")])),
        reply(delegated(requests=[request("find", query="seven", scope=["E1"]),
                                  request("read", query="", target="E1", mode="local")])),
        reply(delegated("return", ["E1"])), reply(answer(VALUE + " [E1]")),
    ])
    result = run("Inspect the retained value.", model=model, retained_acquisitions=(original,),
                 search=prohibited, fetch=linkup)
    assert len(linkup.calls) == 1 and result.posture == "supported"
    assert results(payloads[-1])["r1"]["evidence"][0]["content"] == VALUE
    assert budget(result)["external_attempts"] == 1
