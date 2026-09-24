"""Offline regressions for one bounded Answer correction per selected packet."""

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict

import pytest
from test_research_loop import answer, decision, multi_search, no_fetch, request, search

from core.exa_transport import DiscoveryCandidate
from scryraven.dogfood_diagnostics import DogfoodLog, TurnDiagnostics
from scryraven.model import ModelError, OpenAIModel
from scryraven.presentation import render_cli, render_html
from scryraven.research import ANSWER_PROMPT, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore

OPERATIONAL_MESSAGE = "I couldn't complete a source-validated answer for this request."
SOURCE_TEXT = "The stated value is seven."


class RecordingModel:
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def __call__(self, stage, prompt, packet, schema):
        self.calls.append((stage, prompt, deepcopy(packet), schema))
        output = next(self.outputs)
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


def rejected_reading(ref="E1", passage="SURROGATE_NONLITERAL_PASSAGE"):
    return answer("REJECTED_MODEL_PROSE [" + ref + "]", readings=[
        {"evidence_ref": ref, "passages": [passage]},
    ])


def assert_operational_inability(result):
    assert result.posture == "unable"
    assert result.stop_reason == "not_established"
    assert result.answer == OPERATIONAL_MESSAGE
    assert result.citations == result.citation_uses == result.selected_evidence == ()
    assert not any(event["action"] == "answer_decision" for event in result.trace)
    assert any(event["action"] == "answer_validation_exhausted"
               and event["code"] == "answer_validation_exhausted" for event in result.trace)


def f2_surrogate_search(_query):
    # Public failure structure: a ten-item selected packet ending in E13.
    # Passage strings are synthetic, not reconstructed historical F2 output.
    return [DiscoveryCandidate(f"Public source {i}", f"https://example.org/{i}",
                               f"Exact public material {i}.", context_kind="provider_highlights")
            for i in range(1, 14)]


def test_f2_surrogate_e13_repeated_invalid_reading_stops_on_same_packet():
    refs = [f"E{i}" for i in range(4, 14)]
    first = rejected_reading("E13", "F2_SURROGATE_INVALID_E13_PASSAGE_ONE")
    second = rejected_reading("E13", "F2_SURROGATE_INVALID_E13_PASSAGE_TWO")
    model = RecordingModel(decision(), decision("answer", refs), first, second)

    result = run("What does the selected publication establish?", model=model,
                 search=f2_surrogate_search, fetch=no_fetch)

    assert [call[0] for call in model.calls] == ["research", "research", "answer", "answer"]
    initial, correction = answer_calls(model)
    assert [item["id"] for item in initial[2]["evidence"]] == refs
    assert initial[2]["evidence"] == correction[2]["evidence"]
    assert correction[2]["output_correction"]["code"] == "reading_passage_not_in_source"
    assert [event["code"] for event in result.trace if event["action"] == "answer_reading_rejected"] == [
        "reading_passage_not_in_source", "reading_passage_not_in_source",
    ]
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4
    assert_operational_inability(result)
    assert "REJECTED_MODEL_PROSE" not in json.dumps(result.trace)
    assert "F2_SURROGATE_INVALID" not in json.dumps(result.trace)


def test_f2_surrogate_e13_exact_corrected_reading_completes_normally():
    refs = [f"E{i}" for i in range(4, 14)]
    model = RecordingModel(
        decision(), decision("answer", refs), rejected_reading("E13"),
        answer("The selected publication says thirteen. [E13]", readings=[
            {"evidence_ref": "E13", "passages": ["Exact public material 13."]},
        ]),
    )

    result = run("What does the selected publication establish?", model=model,
                 search=f2_surrogate_search, fetch=no_fetch)

    assert len(answer_calls(model)) == 2
    assert result.posture == "supported" and result.stop_reason == "supported"
    assert result.answer == "The selected publication says thirteen. [1]"
    assert [item.id for item in result.selected_evidence] == ["E13"]
    assert [citation.source_id for citation in result.citations] == ["E13"]


def test_malformed_response_then_nonliteral_reading_uses_one_shared_correction():
    model = RecordingModel(decision(), decision("answer", ["E1"]),
                           "not valid JSON", rejected_reading())

    result = run("What is the value?", model=model, search=search, fetch=no_fetch)

    assert [call[0] for call in model.calls] == ["research", "research", "answer", "answer"]
    assert answer_calls(model)[1][2]["output_correction"]
    assert [event["code"] for event in result.trace if event["action"] == "response_rejected"] == [
        "malformed_model_response", "reading_passage_not_in_source",
    ]
    assert_operational_inability(result)


def test_missing_citation_then_unread_cited_group_uses_one_shared_correction():
    first = answer("REJECTED_CITELESS_PROSE", readings=[
        {"evidence_ref": "E1", "passages": ["First exact passage."]},
    ])
    second = answer("REJECTED_UNREAD_GROUP_PROSE [E2]", readings=[
        {"evidence_ref": "E1", "passages": ["First exact passage."]},
    ])
    model = RecordingModel(decision(), decision("answer", ["E1", "E2"]), first, second)

    result = run("Compare the publications.", model=model, search=multi_search, fetch=no_fetch)

    assert [call[0] for call in model.calls] == ["research", "research", "answer", "answer"]
    assert answer_calls(model)[1][2]["output_correction"]["code"] == "missing_citation"
    assert [event["code"] for event in result.trace if event["action"] == "response_rejected"] == [
        "missing_citation", "cited_source_without_reading",
    ]
    assert_operational_inability(result)
    assert "REJECTED_" not in json.dumps(result.trace)


def test_no_op_research_after_valid_corrected_need_does_not_start_new_answer():
    model = RecordingModel(
        decision(), decision("answer", ["E1"]), rejected_reading(),
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


def test_answer_prompt_states_existing_cited_source_reading_coverage_rule():
    assert "every canonical source group" in ANSWER_PROMPT.lower()
    assert "source_reading" in ANSWER_PROMPT
    assert "selected material" in ANSWER_PROMPT.lower()


def test_correction_request_receives_only_remaining_answer_stage_seconds():
    now = [0.0]
    model = TimedModel(now, (0, decision()), (0, decision("answer", ["E1"])),
                       (118, rejected_reading()), (0, answer()))

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 clock=lambda: now[0])

    assert [call[1] for call in answer_calls(model)] == pytest.approx([120, 2])
    assert result.posture == "supported" and result.answer.endswith("[1]")


def test_no_correction_starts_when_answer_stage_has_no_meaningful_time():
    now = [0.0]
    model = TimedModel(now, (0, decision()), (0, decision("answer", ["E1"])),
                       (119.5, rejected_reading()))

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 clock=lambda: now[0])

    assert len(answer_calls(model)) == 1
    assert_operational_inability(result)


def test_correction_timeout_stops_without_another_answer_attempt():
    now = [0.0]
    model = TimedModel(now, (0, decision()), (0, decision("answer", ["E1"])),
                       (118, rejected_reading()),
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
                       (118, rejected_reading()),
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
        (0, answer("The new fact is documented. [E2]", readings=[
            {"evidence_ref": "E2", "passages": ["New exact fact."]},
        ])),
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


def test_rejected_reading_detail_is_observer_only_and_success_is_not_reported_as_rejected(tmp_path):
    rejected = "SURROGATE_REJECTED_PASSAGE_FOR_FORENSICS"
    first = rejected_reading(passage=rejected)
    corrected = answer("The stated value is seven. [E1]")
    model = RecordingModel(decision(), decision("answer", ["E1"]), first, corrected)
    observed = []
    diagnostic = TurnDiagnostics(started_at=0.0, clock=lambda: 0.0)

    def observe(event):
        observed.append(event)
        diagnostic.observe(event)

    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=search,
                                     fetch=no_fetch, observe=observe)
    result = session.ask("What is the value?")

    details = [event for event in observed if event["action"] == "answer_reading_rejected_detail"]
    assert len(details) == 1
    detail = details[0]
    assert detail["attempted_passage"] == rejected
    assert detail["evidence_ref"] == detail["source_id"] == "E1"
    assert detail["reading_index"] == detail["passage_index"] == 0
    assert detail["selected_content_sha256"] == hashlib.sha256(SOURCE_TEXT.encode()).hexdigest()
    assert detail["selected_content_characters"] == len(SOURCE_TEXT)
    safe = [event for event in result.trace if event["action"] == "answer_reading_rejected"]
    assert len(safe) == 1 and safe[0]["code"] == "reading_passage_not_in_source"
    assert "attempted_passage" not in safe[0]
    assert not any(event["action"] == "answer_reading_rejected_detail" for event in result.trace)
    assert rejected not in json.dumps(result.trace)
    record = diagnostic.record(session_id=session.session_id, revision_before=0,
                               revision_after=1, result=result)
    log_path = tmp_path / "dogfood.jsonl"
    DogfoodLog(log_path, session_database=store.path).append(record)
    assert rejected not in log_path.read_text(encoding="utf-8")
    restored = store.load(session.session_id).state.turns[0]
    assert set(asdict(restored)) == {"question", "answer", "analysis", "posture", "stop_reason",
                                     "selected_evidence", "citations", "citation_uses"}
    assert rejected not in repr(restored)
    assert rejected not in render_cli(result)
    assert rejected not in render_html("What is the value?", result)
    assert len([event for event in observed if event["action"] == "answer_reading"]) == 1


def test_successful_reading_emits_no_rejected_detail():
    observed = []
    model = RecordingModel(decision(), decision("answer", ["E1"]), answer())

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 observe=observed.append)

    assert result.posture == "supported"
    assert not any(event["action"] == "answer_reading_rejected_detail" for event in observed)


def test_operational_inability_round_trips_through_existing_session_schema(tmp_path):
    rejected = "SURROGATE_FAILED_SESSION_PASSAGE"
    model = RecordingModel(decision(), decision("answer", ["E1"]),
                           rejected_reading(passage=rejected),
                           rejected_reading(passage=rejected))
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
