"""Offline regressions for one bounded Answer correction per selected packet."""

import json
from copy import deepcopy
from dataclasses import asdict

import pytest
from test_research_loop import (
    answer,
    decision,
    next_scripted,
    no_fetch,
    request,
    search,
)

from core.exa_transport import DiscoveryCandidate
from scryraven.model import ModelError, OpenAIModel
from scryraven.research import ANSWER_PROMPT, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore

OPERATIONAL_MESSAGE = "I couldn't complete a source-validated answer for this request."
SOURCE_TEXT = "The stated value is seven."


class RecordingModel:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def __call__(self, stage, prompt, packet, schema):
        self.calls.append((stage, prompt, deepcopy(packet), schema))
        output = next_scripted(self.outputs, stage, packet)
        return output if isinstance(output, str) else json.dumps(output)


class TimedModel(OpenAIModel):
    """Capture the real-model timeout seam without making a transport request."""

    def __init__(self, now, *steps, timeout_seconds=120):
        super().__init__(timeout_seconds=timeout_seconds)
        self.now = now
        self.steps = iter(steps)
        self.calls = []

    def __call__(self, stage, prompt, packet, schema):
        self.calls.append((stage, self.timeout_seconds, deepcopy(packet)))
        advance, output = next(self.steps)
        self.now[0] += advance
        if isinstance(output, Exception):
            raise output
        return output if isinstance(output, str) else json.dumps(output)


def answer_calls(model):
    return [call for call in model.calls if call[0] == "answer"]


def assert_operational_inability(result):
    assert result.posture == "unable"
    assert result.stop_reason == "not_established"
    assert result.answer == OPERATIONAL_MESSAGE
    assert result.citations == result.citation_uses == result.selected_evidence == ()
    assert not any(event["action"] == "answer_decision" for event in result.trace)
    assert any(event["action"] == "answer_validation_exhausted"
               and event["code"] == "answer_validation_exhausted" for event in result.trace)


def test_no_op_research_after_valid_corrected_need_does_not_start_new_answer():
    model = RecordingModel(
        decision(), decision("answer", ["E1"]), answer("REJECTED_CITELESS"),
        answer("Only an initial fact is established. [E1]", "partial", "What condition applies?"),
        decision("answer", ["E1"]),
    )

    result = run("What is the value?", model=model, search=search, fetch=no_fetch)

    assert [call[0] for call in model.calls] == [
        "research", "research", "answer", "answer", "research",
    ]
    assert len(answer_calls(model)) == 2
    assert result.posture == "partial" and result.answer.endswith("[1]")
    assert any(event["action"] == "answer_committed_no_progress" for event in result.trace)
    assert not any(event["action"] == "answer_validation_exhausted" for event in result.trace)


def test_answer_prompt_distinguishes_developed_analysis_from_compact_lookup():
    prompt = " ".join(ANSWER_PROMPT.lower().split())
    assert "for non-lookup questions" in prompt
    assert "substantially develop" in prompt
    assert "lookups direct and compact" in prompt
    assert "soft editorial ceiling" in prompt


def test_correction_request_receives_only_remaining_answer_stage_seconds():
    now = [0.0]
    model = TimedModel(now, (0, decision()), (0, decision("answer", ["E1"])),
                       (118, answer("REJECTED_MODEL_PROSE")), (0, answer()))

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 clock=lambda: now[0])

    assert [call[1] for call in answer_calls(model)] == pytest.approx([120, 2])
    assert result.posture == "supported" and result.answer.endswith("[1]")


def test_no_correction_starts_when_answer_stage_has_no_meaningful_time():
    now = [0.0]
    model = TimedModel(now, (0, decision()), (0, decision("answer", ["E1"])),
                       (119.5, answer("REJECTED_MODEL_PROSE")))

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 clock=lambda: now[0])

    assert len(answer_calls(model)) == 1
    assert_operational_inability(result)


def test_correction_timeout_stops_without_another_answer_attempt():
    now = [0.0]
    model = TimedModel(now, (0, decision()), (0, decision("answer", ["E1"])),
                       (118, answer("REJECTED_MODEL_PROSE")),
                       (2, ModelError("model_request_timed_out")))

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 clock=lambda: now[0])

    assert [call[1] for call in answer_calls(model)] == pytest.approx([120, 2])
    assert len(answer_calls(model)) == 2
    assert model.timeout_seconds == 120
    assert_operational_inability(result)
    assert not any(event["action"] == "answer_returned_to_research" for event in result.trace)


def test_non_timeout_model_failure_after_answer_stage_deadline_is_operational_inability():
    now = [0.0]
    model = TimedModel(now, (0, decision()), (0, decision("answer", ["E1"])),
                       (118, answer("REJECTED_MODEL_PROSE")),
                       (3, ModelError("model_request_rejected")))

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 clock=lambda: now[0])

    assert [call[1] for call in answer_calls(model)] == pytest.approx([120, 2])
    assert len(answer_calls(model)) == 2
    assert now[0] == 121
    assert_operational_inability(result)
    assert not any(event["action"] == "answer_returned_to_research" for event in result.trace)


def test_explicit_smaller_model_timeout_is_preserved_across_turns():
    now = [0.0]
    unable = answer("The requested fact remains unestablished.", "unable")
    model = TimedModel(now, (0, decision("answer")), (0, unable),
                       (0, decision("answer")), (0, unable), timeout_seconds=17)

    first = run("First question?", model=model, search=search, fetch=no_fetch,
                clock=lambda: now[0])
    second = run("Second question?", model=model, search=search, fetch=no_fetch,
                 clock=lambda: now[0])

    assert first.posture == second.posture == "unable"
    assert [call[1] for call in model.calls] == [17, 17, 17, 17]
    assert model.timeout_seconds == 17


def test_materially_new_answer_evidence_after_valid_need_resets_stage_allowance():
    now = [0.0]
    model = TimedModel(
        now,
        (0, decision()),
        (0, decision("answer", ["E1"])),
        (119, answer("An initial fact is known. [E1]", "partial", "What is the new fact?")),
        (0, decision(requests=[request(query="new fact")], refs=["E1"])),
        (0, decision("answer", ["E1", "E2"])),
        (0, answer("The new fact is documented. [E2]")),
    )

    def staged_search(query):
        if query == "new fact":
            return [DiscoveryCandidate("New source", "https://example.org/new", "New exact fact.",
                                       context_kind="provider_highlights")]
        return search(query)

    result = run("What is the new fact?", model=model, search=staged_search,
                 fetch=no_fetch, clock=lambda: now[0])

    first, second = answer_calls(model)
    assert [call[1] for call in (first, second)] == pytest.approx([120, 120])
    assert [item["id"] for item in first[2]["evidence"]] == ["E1"]
    assert [item["id"] for item in second[2]["evidence"]] == ["E1", "E2"]
    assert result.posture == "supported" and result.answer.endswith("[1]")
    assert any(event["action"] == "answer_returned_to_research" for event in result.trace)


def test_operational_inability_round_trips_through_existing_session_schema(tmp_path):
    rejected = "SURROGATE_FAILED_SESSION_PASSAGE"
    model = RecordingModel(decision(), decision("answer", ["E1"]),
                           answer(rejected), answer(rejected))
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=search, fetch=no_fetch)

    result = session.ask("What is the value?")
    restored = ResearchSession.open(session.session_id, store=SQLiteSessionStore(store.path),
                                    model=lambda *args: pytest.fail("Unexpected model call"),
                                    search=lambda *args: pytest.fail("Unexpected search"),
                                    fetch=no_fetch)

    assert_operational_inability(result)
    assert len(restored.turns) == 1
    turn = restored.turns[0]
    assert turn.answer == OPERATIONAL_MESSAGE
    assert turn.posture == "unable" and turn.stop_reason == "not_established"
    assert turn.selected_evidence == turn.citations == turn.citation_uses == ()
    assert set(asdict(turn)) == {"question", "answer", "analysis", "posture", "stop_reason",
                                 "selected_evidence", "citations", "citation_uses"}
    assert rejected not in repr(turn)
