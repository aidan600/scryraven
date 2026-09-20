"""Ordinary follow-ups: fresh decisions, retained actual Evidence, atomic history."""
import json

import pytest
from test_research_loop import Script, answer, decision, request

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.model import ModelError
from scryraven.research import RunError, run
from scryraven.session import ResearchSession

URL_A = "https://example.test/pressure-standard"
URL_B = "https://example.test/temperature-standard"
Q1 = "What pressure setpoint does the standard specify?"
Q2 = "And what is its inspection interval?"
Q3 = "What temperature does the separate temperature standard specify?"
FACT_A = "The pressure setpoint is 12 kPa while idle."
FACT_B = "The inspection interval is eight cycles."
FACT_C = "The temperature setpoint is 40 degrees Celsius."
BODY = FACT_A + "\n\n" + FACT_B
ANSWER_A = "For idle operation, the standard specifies 12 kPa."


class Provider:
    def __init__(self, *batches, bodies=None):
        self.batches = iter(batches)
        self.bodies = bodies or {URL_A: BODY, URL_B: FACT_C}
        self.searches, self.fetches = [], []

    def search(self, query):
        self.searches.append(query)
        return next(self.batches)

    def fetch(self, url):
        self.fetches.append(url)
        return FetchedMaterial(url, self.bodies[url])


def candidate(url=URL_A, context="", *, highlights=False):
    return DiscoveryCandidate("Synthetic standard", url, context,
                              context_kind="provider_highlights" if highlights else "navigation")


def local_turn(text=FACT_B + " [E1]", refs=("E1",)):
    return (decision(requests=[request("read", query="", target=ref, mode="local") for ref in refs]),
            decision("answer", refs), answer(text))


def first_turn(*, highlights=False):
    reading = () if highlights else (decision(requests=[request("read", query="", target="C1")]),)
    return (decision(), *reading, decision("answer", ["E1"]), answer(ANSWER_A + " [E1]"))


def no_io(*args, **kwargs):
    raise AssertionError("Unexpected model/provider I/O")


@pytest.mark.parametrize("highlights", [False, True])
def test_followup_reads_retained_fact_with_fresh_research_and_answer(highlights):
    model = Script(*first_turn(highlights=highlights), *local_turn())
    provider = Provider([candidate(context=BODY if highlights else "", highlights=highlights)])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    first, second = session.ask(Q1), session.ask(Q2)
    assert len(provider.searches) == 1 and len(provider.fetches) == (0 if highlights else 1)
    assert session.acquisitions == first.evidence == second.evidence
    assert second.answer == FACT_B + " [1]" and FACT_B not in first.answer
    assert session.source_ids == ("E1",)
    assert all(turn.analysis is None for turn in session.turns)
    calls = [m for _, _, m, _ in model.calls if m["question"] == Q2]
    assert calls[0]["working_understanding"] is None and calls[0]["evidence"] == []
    assert calls[-1]["conversation_context"] == [{"question": Q1, "answer": first.answer}]
    assert calls[-1]["evidence"][0]["content"] == BODY
    assert first.answer not in json.dumps(calls[-1]["evidence"])
    assert all("analysis" not in m and "semantic_history" not in m for m in calls)
    assert [s for s, _, _, _ in model.calls[-3:]] == ["research", "research", "answer"]
    assert second.trace[-1]["budget"]["external_attempts"] == 0
    assert first.citations == session.turns[0].citations


def test_new_source_and_comparison_keep_canonical_identity_and_per_answer_numbers():
    provider = Provider([candidate(context=BODY, highlights=True)], [candidate(URL_B, FACT_C, highlights=True)])
    model = Script(*first_turn(highlights=True), decision(), decision("answer", ["E2"]),
                   answer(FACT_C + " [E2]"), *local_turn(FACT_C + " [E2] " + FACT_A + " [E1]", ["E1", "E2"]))
    session = ResearchSession(model=model, search=provider.search, fetch=no_io)
    first, second, third = [session.ask(q) for q in [Q1, Q3, "Compare them."]]
    assert session.source_ids == ("E1", "E2") and len(provider.searches) == 2
    assert second.citations[0].source_id == "E2" and second.citations[0].number == 1
    assert [c.source_id for c in third.citations] == ["E2", "E1"]
    assert session.turns[0].selected_evidence == first.selected_evidence


@pytest.mark.parametrize("failure", [ModelError("model_transport_failed"), answer("Invalid [E99]")])
def test_failed_turn_leaves_in_memory_evidence_and_history_unchanged(failure):
    provider = Provider([candidate(context=BODY, highlights=True)], [candidate(URL_B, FACT_C, highlights=True)])
    model = Script(*first_turn(highlights=True), decision(), decision("answer", ["E2"]), failure)
    session = ResearchSession(model=model, search=provider.search, fetch=no_io)
    session.ask(Q1)
    before = session.turns, session.acquisitions
    with pytest.raises(RunError):
        session.ask(Q3)
    assert (session.turns, session.acquisitions) == before


def test_isolated_run_has_no_session_evidence_and_only_two_semantic_roles():
    model = Script(*first_turn(highlights=True))
    result = run(Q1, model=model, search=lambda q: [candidate(context=BODY, highlights=True)], fetch=no_io)
    assert {stage for stage, _, _, _ in model.calls} == {"research", "answer"}
    assert not hasattr(result, "analysis")
    assert model.calls[0][2]["catalog"]["materials"] == []
