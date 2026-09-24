"""Answer shape and literal-reading corrections stay inside the Answer contract."""

import json
from copy import deepcopy

import pytest
from test_research_loop import answer, decision, multi_search, no_fetch, search

from scryraven.research import RunLimits, run


class RecordingModel:
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def __call__(self, stage, prompt, packet, schema):
        self.calls.append((stage, prompt, deepcopy(packet), schema))
        return json.dumps(next(self.outputs))


def answer_calls(model):
    return [call for call in model.calls if call[0] == "answer"]


def test_supported_answer_with_missing_need_gets_fresh_answer_correction():
    rejected_prose = "REJECTED_PRIVATE_ANSWER_MARKER"
    rejected = answer(rejected_prose + " [E1]", missing="What else is needed?")
    corrected = answer("The publication states seven. [E1]")
    model = RecordingModel(decision(), decision("answer", ["E1"]), rejected, corrected)

    result = run("What is the value?", model=model, search=search, fetch=no_fetch)

    first, second = answer_calls(model)
    assert [call[0] for call in model.calls] == ["research", "research", "answer", "answer"]
    assert first[1] == second[1] and first[3] == second[3]
    assert first[2]["evidence"] == second[2]["evidence"]
    assert second[2]["output_correction"]["code"] == "supported_with_missing_information"
    assert rejected_prose not in json.dumps(second[2])
    assert rejected_prose not in json.dumps(result.trace)
    assert result.posture == "supported"
    assert result.answer == "The publication states seven. [1]"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4
    assert not any(event["action"] == "answer_returned_to_research" for event in result.trace)
    assert len([event for event in result.trace if event["action"] == "answer_decision"]) == 1


def test_inconsistent_supported_answer_at_bound_is_not_downgraded_into_a_result():
    rejected = answer("REJECTED_PRIVATE_ANSWER_MARKER [E1]",
                      missing="A consequential missing need")
    model = RecordingModel(decision(), decision("answer", ["E1"]), rejected)

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 limits=RunLimits(semantic_attempts=3))

    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert result.posture == "unable" and result.stop_reason == "research_bound"
    assert result.citations == ()
    assert not any(event["action"] == "answer_decision" for event in result.trace)
    assert any(event.get("code") == "supported_with_missing_information"
               for event in result.trace)


@pytest.mark.parametrize("posture", ["partial", "unable"])
def test_valid_missing_need_still_returns_from_answer_to_research(posture):
    provisional = answer("The material leaves a consequential gap. [E1]" if posture == "partial"
                         else "The material leaves a consequential gap.",
                         posture, "What condition applies?")
    model = RecordingModel(decision(), decision("answer", ["E1"]), provisional,
                           decision("answer", ["E1"]))

    result = run("What is the value?", model=model, search=search, fetch=no_fetch)

    assert [call[0] for call in model.calls] == ["research", "research", "answer", "research"]
    assert len(answer_calls(model)) == 1
    assert model.calls[-1][2]["answer_missing_information"] == "What condition applies?"
    assert result.posture == posture
    assert any(event["action"] == "answer_returned_to_research" for event in result.trace)
    assert any(event["action"] == "answer_committed_no_progress" for event in result.trace)


def test_nonliteral_passage_correction_identifies_exact_reading_and_passage():
    rejected_passage = "REJECTED_PRIVATE_PASSAGE_MARKER"
    invalid = answer("Rejected answer prose. [E1]", readings=[
        {"evidence_ref": "E1", "passages": ["The stated value is seven."]},
        {"evidence_ref": "E1", "passages": ["The stated value is seven.", rejected_passage]},
    ])
    model = RecordingModel(decision(), decision("answer", ["E1"]), invalid, answer())

    result = run("What is the value?", model=model, search=search, fetch=no_fetch)

    correction = answer_calls(model)[1][2]["output_correction"]
    assert correction["code"] == "reading_passage_not_in_source"
    assert correction["evidence_ref"] == "E1"
    assert correction["reading_index"] == 1
    assert correction["passage_index"] == 1
    assert rejected_passage not in json.dumps(correction)
    assert rejected_passage not in json.dumps(result.trace)
    assert "The stated value is seven." not in json.dumps(correction)
    assert result.posture == "supported"


@pytest.mark.parametrize("bad_ref, safe_ref", [
    ("E2", "E2"), ("E99", "E99"), ("PRIVATE_SOURCE_BODY_MARKER", None),
])
def test_unselected_or_unknown_reading_reference_gets_safe_location(bad_ref, safe_ref):
    rejected_passage = "REJECTED_PRIVATE_PASSAGE_MARKER"
    invalid = answer("Rejected answer prose. [E1]", readings=[
        {"evidence_ref": bad_ref, "passages": [rejected_passage]},
    ])
    corrected = answer("First fact. [E1]", readings=[
        {"evidence_ref": "E1", "passages": ["First exact passage."]},
    ])
    model = RecordingModel(decision(), decision("answer", ["E1"]), invalid, corrected)

    result = run("What is the first fact?", model=model, search=multi_search,
                 fetch=no_fetch)

    correction = answer_calls(model)[1][2]["output_correction"]
    assert correction["code"] == "unselected_reading_reference"
    assert correction["evidence_ref"] == safe_ref
    assert correction["reading_index"] == 0
    assert correction["passage_index"] == 0
    assert rejected_passage not in json.dumps(correction)
    assert rejected_passage not in json.dumps(result.trace)
    assert "PRIVATE_SOURCE_BODY_MARKER" not in json.dumps(correction)
    assert "PRIVATE_SOURCE_BODY_MARKER" not in json.dumps(result.trace)
    assert result.answer == "First fact. [1]"
