"""Offline multi-turn decisions through the ordinary application, faking only I/O."""

import json

import pytest
from test_source_acquisition import use
from test_walking_skeleton import Model, analysis, author, done, orient, read, relevance, search_for

from core import exa_transport
from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven import __main__ as cli
from scryraven import research
from scryraven.model import ModelError
from scryraven.research import RunError, run
from scryraven.session import ResearchSession
from scryraven.sources import PACKET_CHARACTERS

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


class Script(Model):
    def __init__(self, *replies):
        super().__init__(*replies)
        self.prompts = []

    def __call__(self, stage, prompt, material, schema):
        self.prompts.append(prompt)
        if callable(self.replies[0]):
            self.replies[0] = self.replies[0](stage, material)
        return super().__call__(stage, prompt, material, schema)


class Provider:
    def __init__(self, *batches, bodies=None):
        self.batches = iter(batches)
        self.bodies = bodies or {URL_A: BODY, URL_B: FACT_C}
        self.searches = []
        self.fetches = []

    def search(self, query):
        self.searches.append(query)
        return next(self.batches)

    def fetch(self, url):
        self.fetches.append(url)
        return FetchedMaterial(url, self.bodies[url])


def candidate(url=URL_A, context="", *, highlights=False):
    return DiscoveryCandidate("Synthetic standard", url, context,
                              context_kind="provider_highlights" if highlights else "navigation")


def assess(question, text, *refs):
    stage, reply = analysis(refs=refs)
    reply["coverage"][0].update(need=question, findings=[{"text": text, "support_refs": list(refs)}])
    return stage, reply


def inspect(*refs, need=Q2):
    stage, reply = read(*refs)
    reply["context_needed"] = need
    return stage, reply


def first_turn():
    return (orient(Q1), search_for(Q1), inspect("C1", need=Q1), relevance("E1"),
            assess(Q1, FACT_A, "E1"), author(ANSWER_A + " [E1]"))


def completed(trace):
    return next(event for event in trace if event["action"] == "turn_completed")


@pytest.mark.parametrize("highlights", [False, True])
def test_followup_inspects_retained_fact_not_previous_answer_with_zero_provider_calls(highlights):
    opening = (orient(Q1), search_for(Q1), use("C1"),
               assess(Q1, FACT_A, "E1"), author(ANSWER_A + " [E1]")) if highlights else first_turn()
    reuse = (use("C1"),) if highlights else (inspect("C1"), relevance("E1"))
    model = Script(*opening, orient(Q2), *reuse, assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]"))
    provider = Provider([candidate(context=BODY if highlights else "", highlights=highlights)])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)

    first = session.ask(Q1)
    acquisition = session.acquisitions[0]
    counts = len(provider.searches), len(provider.fetches)
    second = session.ask(Q2)

    assert (len(provider.searches), len(provider.fetches)) == counts == (1, 0 if highlights else 1)
    assert first.answer == ANSWER_A + " [1]"
    assert second.answer == FACT_B + " [1]" and second.posture == "supported"
    assert session.acquisitions == first.evidence == second.evidence == (acquisition,)
    assert session.acquisitions[0] is acquisition and acquisition.content == BODY
    assert acquisition.acquisition == ("provider_highlights" if highlights else "fetched_source")
    assert session.source_ids == ("E1",)
    assert second.citations[0].source_id == "E1" and second.citations[0].url == URL_A
    assert second.citations[0].materials == second.selected_evidence
    assert all(second.citations[use.number - 1].source_id == "E1"
               and second.answer[use.start:use.end] == "[1]" for use in second.citation_uses)
    assert [turn.question for turn in session.turns] == [Q1, Q2]
    assert not model.replies

    analyst_inputs = [material for stage, material in model.calls if stage == "analyst"]
    assert len(analyst_inputs) == 2 and second.analysis is not first.analysis
    followup = analyst_inputs[1]
    assert followup["previous_analysis"] is None
    assert followup["conversation_context"] == [{"question": Q1, "answer": first.answer}]
    assert followup["semantic_history"][0]["analysis"] == first.analysis.model_dump()
    assert followup["evidence"][0]["content"] == BODY
    assert first.answer not in json.dumps(followup["evidence"])
    assert FACT_B not in first.answer and FACT_B in second.analysis.findings[0].text
    assert first.answer not in json.dumps(second.trace)
    navigation = next(m for stage, m in model.calls if m.get("phase") == "navigation" and m["question"] == Q2)
    assert navigation["retained_sources"][0]["id"] == "E1"
    assert navigation["retained_sources"][0]["candidate_refs"] == ["C1"]
    assert model.calls[-1][1]["conversation_context"] == followup["conversation_context"]
    assert "semantic_history" not in model.calls[-1][1]
    assert completed(second.trace) == {"stage": "session", "action": "turn_completed", "turn_index": 2,
                                       "new_acquisition_count": 0, "reused_source_ids": ["E1"], "source_count": 1}
    assert second.trace[0]["retained_source_count"] == 1


def test_new_information_gets_new_source_and_only_current_selection_supports_answer():
    model = Script(*first_turn(), orient(Q3), search_for(Q3), inspect("C2", need=Q3), relevance("E2"),
                   assess(Q3, FACT_C, "E2"), author(FACT_C + " [E2]"),
                   orient("Compare the two standards."), inspect("C1", "C2"), relevance("E1", "E2"),
                   assess("Compare the two standards.", FACT_A + " " + FACT_C, "E1", "E2"),
                   author(FACT_C + " [E2] " + FACT_A + " [E1]"))
    provider = Provider([candidate()], [candidate(URL_B)])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    second = session.ask(Q3)
    assert provider.fetches == [URL_A, URL_B] and len(provider.searches) == 2
    assert session.acquisitions[0] is first.evidence[0]
    assert [(e.id, e.source_id) for e in session.acquisitions] == [("E1", "E1"), ("E2", "E2")]
    assert [e.id for e in second.selected_evidence] == ["E2"]
    assert [e["id"] for stage, m in model.calls if stage == "analyst" for e in m["evidence"]] == ["E1", "E2"]
    assert second.citations[0].source_id == "E2" and second.citations[0].number == 1
    assert completed(second.trace)["new_acquisition_count"] == 1
    third = session.ask("Compare the two standards.")
    assert [(c.source_id, c.number) for c in third.citations] == [("E2", 1), ("E1", 2)]
    assert provider.fetches == [URL_A, URL_B] and len(provider.searches) == 2
    assert session.source_ids == ("E1", "E2")


def test_omitted_retained_inspection_continues_navigation_before_first_analyst_call():
    model = Script(*first_turn(), orient(Q3), inspect("C1", need=Q3), relevance(),
                   search_for(Q3), inspect("C2", need=Q3), relevance("E2"),
                   assess(Q3, FACT_C, "E2"), author(FACT_C + " [E2]"))
    provider = Provider([candidate()], [candidate(URL_B)])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    session.ask(Q1)
    result = session.ask(Q3)
    inputs = [m for stage, m in model.calls if stage == "analyst"]
    assert len(inputs) == 2 and inputs[-1]["evidence"][0]["id"] == "E2"
    assert len(result.selected_evidence) == 1 and result.selected_evidence[0].url == URL_B


def test_full_read_after_retained_highlights_preserves_source_identity_then_reuses_parent():
    model = Script(orient(Q1), search_for(Q1), use("C1"), assess(Q1, FACT_A, "E1"), author(ANSWER_A + " [E1]"),
                   orient(Q2), inspect("C1"), relevance("E2"), assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]"),
                   orient(Q2), inspect("C2"), relevance("E2"), assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]"))
    provider = Provider([candidate(context=FACT_A, highlights=True)])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    session.ask(Q1)
    assert not provider.fetches
    second = session.ask(Q2)
    third = session.ask(Q2)
    assert provider.fetches == [URL_A] and len(provider.searches) == 1
    assert [(e.id, e.source_id, e.acquisition) for e in session.acquisitions] == [
        ("E1", "E1", "provider_highlights"), ("E2", "E1", "fetched_source")]
    assert third.selected_evidence == second.selected_evidence == (session.acquisitions[1],)
    assert third.citations[0].source_id == "E1" and third.citations[0].materials[0].id == "E2"
    assert completed(third.trace)["new_acquisition_count"] == 0
    assert next(t for t in second.trace if t["action"] == "read_succeeded")["source_identity"] == "reused"


@pytest.mark.parametrize("ref", ["previous_answer", "E1"])
def test_history_and_unselected_retained_evidence_cannot_supply_current_support(ref):
    model = Script(*first_turn(), orient(Q2), done(), assess(Q2, FACT_B, ref))
    provider = Provider([candidate()])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    with pytest.raises(RunError, match="analyst: invalid_evidence_reference"):
        session.ask(Q2)
    assert session.acquisitions == first.evidence and len(session.turns) == 1
    assert model.calls[-1][1]["evidence"] == []
    assert model.calls[-1][1]["conversation_context"][0]["answer"] == first.answer


def test_author_cannot_cite_a_prior_source_excluded_from_current_findings():
    model = Script(*first_turn(), orient(Q3), search_for(Q3), inspect("C2", need=Q3), relevance("E2"),
                   assess(Q3, FACT_C, "E2"), author(FACT_C + " [E2] " + ANSWER_A + " [E1]"))
    provider = Provider([candidate()], [candidate(URL_B)])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    with pytest.raises(RunError) as caught:
        session.ask(Q3)
    assert caught.value.stage == "citations"
    assert session.acquisitions == first.evidence and len(session.turns) == 1
    assert [e["id"] for e in model.calls[-1][1]["evidence"]] == ["E2"]


@pytest.mark.parametrize("failure", [ModelError("offline_model_failure"), ValueError("offline_failure")])
def test_failed_turn_discards_new_acquisition_and_analysis_without_corrupting_prior_state(failure):
    second = (orient(Q3), search_for(Q3), inspect("C2", need=Q3), relevance("E2"), assess(Q3, FACT_C, "E2"))
    model = Script(*first_turn(), *second, ("author", failure), *second, author(FACT_C + " [E2]"))
    provider = Provider([candidate()], [candidate(URL_B)], [candidate(URL_B)])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    before = session.turns
    with pytest.raises((RunError, ValueError)):
        session.ask(Q3)
    assert session.turns == before and session.acquisitions == first.evidence and session.source_ids == ("E1",)
    result = session.ask(Q3)
    assert len(session.turns) == 2 and result.trace[0]["turn_index"] == 2
    assert session.source_ids == ("E1", "E2") and provider.fetches == [URL_A, URL_B, URL_B]
    assert len(model.calls[-1][1]["conversation_context"]) == 1


def test_returned_analysis_and_history_snapshots_cannot_mutate_committed_history():
    model = Script(*first_turn(), orient(Q2), inspect("C1"), relevance("E1"),
                   assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]"))
    provider = Provider([candidate()])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    first.analysis.coverage[0].findings[0].text = "Caller mutation"
    session.turns[0].analysis.coverage.clear()
    assert session.turns[0].analysis.findings[0].text == FACT_A
    session.ask(Q2)
    second_analyst = [m for stage, m in model.calls if stage == "analyst"][-1]
    assert second_analyst["semantic_history"][0]["analysis"]["coverage"][0]["findings"][0]["text"] == FACT_A


def select_packet(_stage, material):
    assert material["phase"] == "relevance"
    return relevance(*(item["id"] for item in material["new_evidence"]))


def test_large_parent_yields_different_exact_followup_view_without_provider_io():
    filler = ("# Machinery archive\n" + "Unrelated engineering background. " * 240 + "\n\n") * 30
    body = "# Standard\nScope: pressure equipment.\n\n" + FACT_A + "\n\n" + filler + "# Inspection\n" + FACT_B + "\n\n" + filler
    model = Script(orient(Q1), search_for(Q1), inspect("C1", need=Q1), select_packet,
                   assess(Q1, FACT_A, "E1"), author(ANSWER_A + " [E1]"),
                   orient(Q2), inspect("C1"), select_packet, assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]"))
    provider = Provider([candidate()], bodies={URL_A: body})
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    second = session.ask(Q2)
    parent = session.acquisitions[0]
    assert parent.content == body and len(body) > PACKET_CHARACTERS
    assert FACT_B not in "".join(e.content for e in first.selected_evidence)
    assert FACT_B in "".join(e.content for e in second.selected_evidence)
    assert set(e.id for e in second.selected_evidence) != set(e.id for e in first.selected_evidence)
    for item in (*first.selected_evidence, *second.selected_evidence):
        assert item.acquisition == "targeted_view" and item.source_id == item.parent_id == "E1"
        assert item.content == body[item.start_char:item.end_char]
    assert sum(len(e.content) for e in second.selected_evidence) <= PACKET_CHARACTERS
    assert provider.fetches == [URL_A] and len(provider.searches) == 1
    assert body not in json.dumps(second.trace)
    assert second.citations[0].materials == second.selected_evidence


def test_search_allowance_is_fresh_after_previous_turn_exhausted_its_round():
    model = Script(orient(Q1), search_for(Q1), search_for("A second route"), use("C1"),
                   assess(Q1, FACT_A, "E1"), author(ANSWER_A + " [E1]"),
                   orient(Q3), search_for(Q3), use("C2"), assess(Q3, FACT_C, "E2"), author(FACT_C + " [E2]"))
    provider = Provider([candidate(context=FACT_A, highlights=True)], [],
                        [candidate(URL_B, FACT_C, highlights=True)])
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    session.ask(Q1)
    session.ask(Q3)
    navigation = next(m for _, m in model.calls if m.get("phase") == "navigation" and m["question"] == Q3)
    assert navigation["retrieval_allowance"]["discover_remaining"] == 2
    assert navigation["retrieval_allowance"]["research_round"] == 1
    assert len(provider.searches) == 3 and not provider.fetches


def test_valid_unable_result_is_committed_but_empty_input_is_not():
    model = Script(orient(Q1), done(), analysis("unable", refs=()), author("The evidence did not establish this."))
    provider = Provider()
    session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
    result = session.ask(Q1)
    assert result.posture == "unable" and len(session.turns) == 1 and not session.acquisitions
    with pytest.raises(RunError, match="input: empty_question"):
        session.ask("  ")
    assert len(session.turns) == 1 and not provider.searches and not provider.fetches


def test_run_stays_isolated_and_has_no_session_context_or_inherited_corpus():
    provider = Provider([candidate()], [candidate(URL_B)])
    session = ResearchSession(model=Script(*first_turn()), search=provider.search, fetch=provider.fetch)
    session.ask(Q1)
    model = Script(orient(Q3), search_for(Q3), inspect("C1", need=Q3), relevance("E1"),
                   assess(Q3, FACT_C, "E1"), author(FACT_C + " [E1]"))
    result = run(Q3, model=model, search=provider.search, fetch=provider.fetch)
    assert result.evidence[0].id == "E1" and result.evidence[0].url == URL_B and len(result.evidence) == 1
    assert session.acquisitions[0].url == URL_A and len(session.turns) == 1
    assert all("conversation_context" not in m and "semantic_history" not in m for _, m in model.calls)
    assert not any(event["stage"] == "session" for event in result.trace)


def test_session_cli_answers_before_followup_uses_real_adapters_and_writes_no_files(monkeypatch, capsys, tmp_path):
    model = Script(*first_turn(), orient(Q2), inspect("C1"), relevance("E1"),
                   assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]"))
    requests = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    def post(url, **kwargs):
        requests.append(url)
        if url == exa_transport.EXA_SEARCH_URL:
            return Response({"results": [{"url": URL_A, "title": "Synthetic standard"}]})
        assert url == exa_transport.EXA_CONTENTS_URL
        return Response({"results": [{"url": URL_A, "id": URL_A, "text": BODY}]})

    outputs = []

    def input_after_answer(_prompt):
        outputs.append(capsys.readouterr())
        assert (ANSWER_A if len(outputs) == 1 else FACT_B) in outputs[-1].out
        return Q2 if len(outputs) == 1 else ""

    monkeypatch.setenv("EXA_API_KEY", "offline-test-value")
    monkeypatch.setattr(exa_transport.requests, "post", post)
    monkeypatch.setattr(research, "OpenAIModel", lambda: model)
    monkeypatch.setattr("builtins.input", input_after_answer)
    monkeypatch.chdir(tmp_path)
    assert cli.main([Q1, "--session", "--trace", "--trace-evidence"]) == 0
    assert len(outputs) == 2 and not model.replies
    assert requests == [exa_transport.EXA_SEARCH_URL, exa_transport.EXA_CONTENTS_URL]
    assert all("[1] Synthetic standard" in output.out for output in outputs)
    followup_trace = json.loads(outputs[1].err)
    assert completed(followup_trace["trace"])["new_acquisition_count"] == 0
    assert followup_trace["selected_evidence"][0]["content"] == BODY
    assert ANSWER_A not in outputs[1].err
    assert list(tmp_path.iterdir()) == []


def test_cli_session_html_limit_is_explicit_before_execution():
    with pytest.raises(SystemExit) as caught:
        cli.main([Q1, "--session", "--html", "unused.html"])
    assert caught.value.code == 2
