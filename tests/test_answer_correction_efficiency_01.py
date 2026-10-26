"""Answer shape and literal-reading corrections stay inside the Answer contract."""

import json
from copy import deepcopy

from test_research_loop import (
    answer,
    decision,
    next_scripted,
    no_fetch,
    search,
)

from scryraven.research import RunLimits, run


class RecordingModel:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def __call__(self, stage, prompt, packet, schema):
        self.calls.append((stage, prompt, deepcopy(packet), schema))
        return json.dumps(next_scripted(self.outputs, stage, packet))


def answer_calls(model):
    return [call for call in model.calls if call[0] == "answer"]


def test_supported_answer_with_missing_need_gets_fresh_answer_correction():
    rejected_prose = "REJECTED_PRIVATE_ANSWER_MARKER"
    rejected = answer(rejected_prose + " [E1]", missing="What else is needed?")
    corrected = answer("The publication states seven. [E1]")
    model = RecordingModel(decision(), decision("return", ["E1"]), rejected, corrected)

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
    model = RecordingModel(decision(), decision("return", ["E1"]), rejected)

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 limits=RunLimits(physical_model_requests=3))

    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert result.posture == "unable" and result.stop_reason == "research_bound"
    assert "operating limit" in result.answer
    assert result.citations == ()
    assert not any(event["action"] == "answer_decision" for event in result.trace)
    assert any(event.get("code") == "supported_with_missing_information"
               for event in result.trace)
