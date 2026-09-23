"""Offline regressions for bounded citation omission correction in Answer."""

import json
from copy import deepcopy

import pytest
from test_research_loop import answer, decision, no_fetch, request, search

from scryraven.research import RunError, RunLimits, run
from scryraven.session import ResearchSession

QUESTION = "What value does the publication state?"
SOURCE_TEXT = "The stated value is seven."


class RecordingModel:
    """Keep the packet as it existed at each call, before correction mutates it."""

    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def __call__(self, stage, prompt, packet, schema):
        self.calls.append((stage, prompt, deepcopy(packet), schema))
        output = next(self.outputs)
        return output if isinstance(output, str) else json.dumps(output)


def with_reading(text, posture="supported"):
    output = answer(text, posture)
    output["source_readings"] = [{"evidence_ref": "E1", "passages": [SOURCE_TEXT]}]
    return output


def answer_calls(model):
    return [call for call in model.calls if call[0] == "answer"]


@pytest.mark.parametrize("posture", ["supported", "partial"])
def test_citationless_answer_is_corrected_with_same_contract_and_exact_inputs(posture):
    rejected_prose = "REJECTED PRIVATE PROSE: the publication states seven."
    model = RecordingModel(
        decision(), decision("answer", ["E1"]),
        with_reading(rejected_prose, posture),
        with_reading("The publication states seven. [E1]", posture),
    )

    result = run(QUESTION, model=model, search=search, fetch=no_fetch)

    first, corrected = answer_calls(model)
    assert first[1] == corrected[1]
    assert first[3] == corrected[3]
    assert first[2]["question"] == corrected[2]["question"] == QUESTION
    assert first[2]["evidence"] == corrected[2]["evidence"]
    assert first[2]["evidence"][0]["content"] == SOURCE_TEXT
    assert corrected[2]["output_correction"]["code"] == "missing_citation"
    assert "[E1]" in corrected[2]["output_correction"]["instruction"]
    assert rejected_prose not in json.dumps(corrected[2])
    assert rejected_prose not in json.dumps(result.trace)
    assert [call[0] for call in model.calls] == ["research", "research", "answer", "answer"]
    assert result.posture == posture
    assert result.answer == "The publication states seven. [1]"
    assert result.citations[0].materials == result.selected_evidence
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4
    assert len([event for event in result.trace if event["action"] == "answer_decision"]) == 1
    assert any(event.get("code") == "missing_citation" for event in result.trace)


def test_repeated_citation_omission_ends_at_existing_semantic_bound():
    model = RecordingModel(
        decision(), decision("answer", ["E1"]),
        with_reading("Citation omitted on first attempt."),
        with_reading("Citation omitted on second attempt."),
    )

    result = run(QUESTION, model=model, search=search, fetch=no_fetch,
                 limits=RunLimits(semantic_attempts=4))

    assert [call[0] for call in model.calls] == ["research", "research", "answer", "answer"]
    assert len(answer_calls(model)) == 2
    assert result.posture == "unable"
    assert result.stop_reason == "research_bound"
    assert result.citations == ()
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4
    assert len([event for event in result.trace if event.get("code") == "missing_citation"]) == 2
    assert not any(event["action"] == "answer_decision" for event in result.trace)


def test_unable_answer_without_citation_needs_no_correction():
    model = RecordingModel(decision("answer"), answer("The available material does not establish it.", "unable"))

    result = run(QUESTION, model=model, search=search, fetch=no_fetch)

    assert len(answer_calls(model)) == 1
    assert result.posture == "unable"
    assert result.citations == ()
    assert not any(event.get("code") == "missing_citation" for event in result.trace)


@pytest.mark.parametrize("posture", ["supported", "partial"])
def test_already_cited_answer_needs_no_additional_model_call(posture):
    model = RecordingModel(decision(), decision("answer", ["E1"]),
                           with_reading("The publication states seven. [E1]", posture))

    result = run(QUESTION, model=model, search=search, fetch=no_fetch)

    assert len(answer_calls(model)) == 1
    assert result.posture == posture
    assert result.answer == "The publication states seven. [1]"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3


@pytest.mark.parametrize(("bad_answer", "code"), [
    ("An unsupported alias. [E99]", "invalid_citation_reference"),
    ("A malformed alias. [E1", "malformed_citation_reference"),
])
def test_other_invalid_citation_syntax_keeps_existing_failure(bad_answer, code):
    model = RecordingModel(decision(), decision("answer", ["E1"]), with_reading(bad_answer))

    with pytest.raises(RunError) as caught:
        run(QUESTION, model=model, search=search, fetch=no_fetch)

    assert caught.value.stage == "citations"
    assert caught.value.code == code
    assert len(answer_calls(model)) == 1
    assert not any(event.get("code") == "missing_citation" for event in caught.value.trace)


def test_source_reading_correction_remains_separate_from_citation_correction():
    invalid_reading = answer("An invalid reading was selected. [E1]")
    invalid_reading["source_readings"] = [
        {"evidence_ref": "E1", "passages": ["An invented value is eight."]},
    ]
    model = RecordingModel(
        decision(), decision("answer", ["E1"]), invalid_reading,
        with_reading("Correct literal reading, but no citation."),
        with_reading("The publication states seven. [E1]"),
    )

    result = run(QUESTION, model=model, search=search, fetch=no_fetch)

    first, second, third = answer_calls(model)
    assert second[2]["output_correction"]["code"] == "reading_passage_not_in_source"
    assert third[2]["output_correction"]["code"] == "missing_citation"
    assert first[2]["evidence"] == second[2]["evidence"] == third[2]["evidence"]
    assert result.answer == "The publication states seven. [1]"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 5
    assert len([event for event in result.trace if event["action"] == "answer_decision"]) == 1


def test_followup_over_retained_evidence_can_use_citation_correction():
    model = RecordingModel(
        decision(), decision("answer", ["E1"]), with_reading("Seven. [E1]"),
        decision(requests=[request("read", query="", target="E1", mode="local")]),
        decision("answer", ["E1"]),
        with_reading("The retained publication still states seven."),
        with_reading("The retained publication still states seven. [E1]"),
    )
    session = ResearchSession(model=model, search=search, fetch=no_fetch)

    first = session.ask(QUESTION)
    second = session.ask("What does that same publication say now?")

    followup_first, followup_corrected = answer_calls(model)[1:]
    assert followup_first[2]["question"] == followup_corrected[2]["question"]
    assert followup_first[2]["evidence"] == followup_corrected[2]["evidence"]
    assert followup_first[2]["evidence"][0]["content"] == SOURCE_TEXT
    assert followup_corrected[2]["output_correction"]["code"] == "missing_citation"
    assert second.evidence == first.evidence
    assert second.answer == "The retained publication still states seven. [1]"
    assert second.trace[-1]["budget"]["external_attempts"] == 0
    assert len(session.turns) == 2
