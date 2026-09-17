"""Independent integration regressions for the real V2 loop with offline I/O."""

import json
import tempfile
from pathlib import Path

import pytest
from test_v2 import Script, answer, decision, request, search

from core.exa_transport import DiscoveryCandidate
from scryraven.presentation import render_html
from scryraven.research import RunError
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import Evidence
from scryraven.v2 import V2Limits, _run_turn, run


def no_io(*args, **kwargs):
    pytest.fail("Unexpected provider acquisition")


def test_actual_v2_engine_reopens_and_rereads_retained_material_without_acquisition():
    with tempfile.TemporaryDirectory(prefix="scryraven-v2-real-session-") as directory:
        store = SQLiteSessionStore(Path(directory) / "sessions.sqlite3")
        first_model = Script(decision(), decision("answer", ["E1"]), answer())
        session = ResearchSession.create(store=store, engine=_run_turn, limits=V2Limits(),
                                         model=first_model, search=search, fetch=no_io)
        first = session.ask("What is the value?")
        first_turn = session.turns[0]
        first_html = render_html(first_turn.question, first_turn)
        session_id = session.session_id
        del session

        followup_model = Script(
            decision(requests=[request("read", query="", target="E1", mode="local")]),
            decision("answer", ["E1"]), answer("The retained publication states seven. [E1]"),
        )
        reopened = ResearchSession.open(session_id, store=SQLiteSessionStore(store.path),
                                        engine=_run_turn, limits=V2Limits(), model=followup_model,
                                        search=no_io, fetch=no_io)
        second = reopened.ask("What does that source say?")
        assert second.evidence == first.evidence
        assert second.citations[0].materials == first.citations[0].materials
        assert second.trace[-1]["budget"]["external_attempts"] == 0
        assert [call[0] for call in followup_model.calls] == ["research", "research", "answer"]
        initial_packet, final_packet = followup_model.calls[0][2], followup_model.calls[-1][2]
        assert initial_packet["working_understanding"] is None and initial_packet["evidence"] == []
        assert initial_packet["conversation_context"] == [{"question": "What is the value?", "answer": first.answer}]
        assert final_packet["evidence"][0]["content"] == first.evidence[0].content
        assert not {"analysis", "semantic_history", "working_understanding", "draft"} & final_packet.keys()

        restored = ResearchSession.open(session_id, store=SQLiteSessionStore(store.path))
        assert restored.metadata.revision == 2
        assert all(turn.analysis is None for turn in restored.turns)
        assert restored.turns[0] == first_turn
        assert render_html(restored.turns[0].question, restored.turns[0]) == first_html


def test_supported_answer_without_actual_supplied_evidence_cannot_complete():
    model = Script(decision("answer"), answer("A factual answer from memory."))
    with pytest.raises(RunError, match="missing_citation"):
        run("What is the fact?", model=model, search=no_io, fetch=no_io)


def test_oversized_exact_read_can_be_delivered_or_revised_without_pending_deadlock():
    parent = Evidence("E1", "https://example.org/long", "Long text", "A documented observation. " * 5000)
    calls = []

    def model(stage, prompt, packet, schema):
        calls.append((stage, packet))
        if stage == "answer":
            evidence = packet["evidence"]
            output = (answer(f"A documented observation. [{evidence[0]['id']}]") if evidence
                      else answer("No actual material was delivered.", "unable"))
        elif packet["evidence"]:
            output = decision("answer", [packet["evidence"][0]["id"]])
        else:
            reading = request("read", query="", target="E1", mode="local")
            reading.update(start_char=0, end_char=len(parent.content) if len(calls) == 1 else 100)
            output = decision(requests=[reading])
        return json.dumps(output)

    result = run("Read the observation", model=model, search=no_io, fetch=no_io,
                 retained_acquisitions=(parent,), limits=V2Limits(attention_characters=65536))
    assert result.posture == "supported"
    assert result.citations and result.trace[-1]["budget"]["external_attempts"] == 0
    assert len(calls) < 12


def test_final_selection_of_shelved_material_is_bounded_and_revisable():
    def several_sources(query):
        return [DiscoveryCandidate(str(index), f"https://example.org/{index}", "Text " * 8000,
                                   context_kind="provider_highlights") for index in range(3)]

    model = Script(
        decision(), decision(), decision(),
        decision("answer", ["E1", "E2", "E3"]),
        decision("answer", ["E1"]), answer("A limited source-based answer. [E1]"),
    )
    result = run("Read the sources", model=model, search=several_sources, fetch=no_io,
                 limits=V2Limits(attention_characters=65536))
    assert any(event.get("code") == "attention_packet_too_large" for event in result.trace)
    final_packet = model.calls[-1][2]
    assert sum(len(item["content"]) for item in final_packet["evidence"]) <= 65536
    assert [item["id"] for item in final_packet["evidence"]] == ["E1"]
    assert len(result.evidence) == 3 and result.selected_evidence[0].id == "E1"


@pytest.mark.parametrize("observer_raises", [False, True])
def test_observer_cannot_change_model_evidence_execution_or_returned_trace(observer_raises):
    notifications = []

    def observer(event):
        notifications.append(event)
        if event.get("evidence"):
            event["evidence"][0]["content"] = "FORGED OBSERVER TEXT"
            event["evidence"].clear()
        if "result" in event:
            event["result"]["material_ids"].clear()
        if "budget" in event:
            event["budget"]["semantic_attempts"] = 999
        event["action"] = "observer_changed"
        if observer_raises:
            raise RuntimeError("OBSERVER PRIVATE ERROR")

    model = Script(decision(), decision("answer", ["E1"]), answer())
    result = run("What is the value?", model=model, search=search, fetch=no_io, observe=observer)
    assert notifications and result.posture == "supported"
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    for call in model.calls[1:]:
        assert call[2]["evidence"][0]["content"] == "The stated value is seven."
    assert model.calls[1][2]["last_route"][0]["material_ids"] == ["E1"]
    assert result.evidence[0].content == "The stated value is seven."
    snapshot = json.dumps(result.trace, sort_keys=True)
    assert "observer_changed" not in snapshot and "OBSERVER" not in snapshot
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3
    for event in notifications:
        event.clear()
    assert json.dumps(result.trace, sort_keys=True) == snapshot
