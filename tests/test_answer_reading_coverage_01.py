"""Mechanical literal-reading coverage for evidence-backed Answer decisions."""

import json
from copy import deepcopy

import pytest
from test_research_loop import answer, decision, multi_search, no_fetch, request, search

from scryraven.research import RunLimits, run
from scryraven.sources import Evidence


class RecordingModel:
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def __call__(self, stage, prompt, packet, schema):
        self.calls.append((stage, prompt, deepcopy(packet), schema))
        return json.dumps(next(self.outputs))


def readings(*items):
    return [{"evidence_ref": ref, "passages": [passage]} for ref, passage in items]


def answer_calls(model):
    return [call for call in model.calls if call[0] == "answer"]


@pytest.mark.parametrize("posture", ["supported", "partial"])
def test_evidence_answer_without_readings_is_corrected_in_same_contract(posture):
    rejected = answer("REJECTED PROSE [E1]", posture, readings=[])
    corrected = answer("The publication states seven. [E1]", posture)
    model = RecordingModel(decision(), decision("answer", ["E1"]), rejected, corrected)

    result = run("What does the publication state?", model=model, search=search, fetch=no_fetch)

    first, second = answer_calls(model)
    assert first[1] == second[1] and first[3] == second[3]
    assert first[2]["evidence"] == second[2]["evidence"]
    assert second[2]["output_correction"]["code"] == "required_source_reading_missing"
    assert "REJECTED PROSE" not in json.dumps(second[2])
    assert result.posture == posture and result.answer == "The publication states seven. [1]"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4


def test_every_cited_source_group_needs_a_validated_reading():
    first = "First exact passage."
    second = "Second source fact."
    rejected = answer("REJECTED PROSE [E1, E2]", readings=readings(("E1", first)))
    corrected = answer("The two facts differ. [E1, E2]",
                       readings=readings(("E1", first), ("E2", second)))
    model = RecordingModel(decision(), decision("answer", ["E1", "E2"]), rejected, corrected)

    result = run("Compare the two facts.", model=model, search=multi_search, fetch=no_fetch)

    correction = answer_calls(model)[1][2]["output_correction"]
    assert correction["code"] == "cited_source_without_reading"
    assert correction["source_ids"] == ["E2"]
    assert "REJECTED PROSE" not in json.dumps(answer_calls(model)[1][2])
    assert [citation.source_id for citation in result.citations] == ["E1", "E2"]
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4


def test_targeted_view_reading_covers_its_canonical_citation_group():
    passage = "The source states a targeted fact."
    content = "Before. " + passage + " After."
    start = content.index(passage)
    end = start + len(passage)
    parent = Evidence("E1", "https://example.org/full", "Full source", content)
    view_ref = f"E1@{start}:{end}"
    route = request("read", query="", target="E1", mode="local")
    route.update(start_char=start, end_char=end)
    final = answer("The targeted fact is documented. [E1]",
                   readings=readings((view_ref, passage)))
    model = RecordingModel(decision(requests=[route]),
                           decision("answer", [view_ref]), final)

    result = run("What fact is documented?", model=model,
                 search=lambda _: pytest.fail("Unexpected search"), fetch=no_fetch,
                 retained_acquisitions=(parent,))

    assert len(answer_calls(model)) == 1
    assert result.citations[0].source_id == "E1"
    assert result.citations[0].materials[0].id == view_ref
    assert result.selected_evidence == result.citations[0].materials


def test_validated_reading_from_uncited_selected_source_is_allowed():
    model = RecordingModel(
        decision(), decision("answer", ["E1", "E2"]),
        answer("Only the first fact is reported. [E1]", readings=readings(
            ("E1", "First exact passage."), ("E2", "Second source fact."))),
    )

    result = run("Report the first fact.", model=model, search=multi_search, fetch=no_fetch)

    assert len(answer_calls(model)) == 1
    assert [citation.source_id for citation in result.citations] == ["E1"]
    assert result.posture == "supported"


@pytest.mark.parametrize("basis", ["none", "evidence"])
def test_unable_answer_is_exempt_from_new_reading_requirement(basis):
    model = RecordingModel(decision(), decision("answer", ["E1"]),
                           answer("The source does not establish the answer.", "unable",
                                  support_basis=basis, readings=[]))

    result = run("What is the answer?", model=model, search=search, fetch=no_fetch)

    assert len(answer_calls(model)) == 1
    assert result.posture == "unable" and result.citations == ()


def test_no_remaining_answer_allowance_uses_operational_fallback():
    invalid = answer("REJECTED PROSE [E1]", readings=[])
    model = RecordingModel(decision(), decision("answer", ["E1"]), invalid, invalid)

    result = run("What does the source say?", model=model, search=search, fetch=no_fetch,
                 limits=RunLimits(semantic_attempts=4))

    assert len(answer_calls(model)) == 2
    assert result.posture == "unable" and result.stop_reason == "research_bound"
    assert result.citations == () and result.selected_evidence == ()
    assert "REJECTED PROSE" not in result.answer
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4
    assert len([event for event in result.trace
                if event.get("code") == "required_source_reading_missing"]) == 2
