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
    search,
)

from scryraven.model import OpenAIModel
from scryraven.research import run
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




def test_explicit_smaller_model_timeout_is_preserved_across_turns():
    now = [0.0]
    unable = answer("The requested fact remains unestablished.", "unable")
    model = TimedModel(now, (0, decision("return")), (0, unable),
                       (0, decision("return")), (0, unable), timeout_seconds=17)

    first = run("First question?", model=model, search=search, fetch=no_fetch,
                clock=lambda: now[0])
    second = run("Second question?", model=model, search=search, fetch=no_fetch,
                 clock=lambda: now[0])

    assert first.posture == second.posture == "unable"
    assert [call[1] for call in model.calls] == [17, 17, 17, 17]
    assert model.timeout_seconds == 17




def test_operational_inability_round_trips_through_existing_session_schema(tmp_path):
    rejected = "SURROGATE_FAILED_SESSION_PASSAGE"
    model = RecordingModel(decision(), decision("return", ["E1"]),
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
                                 "selected_evidence", "citations", "citation_uses", "image_ids"}
    assert rejected not in repr(turn)
