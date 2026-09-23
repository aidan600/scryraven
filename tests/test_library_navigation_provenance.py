"""Prior answer citation navigation stays derived and Research-only."""

import json

from test_research_loop import Script, answer, decision, request

from scryraven.presentation import Citation, CitationUse
from scryraven.session import ResearchSession
from scryraven.session_store import SessionState, SessionTurn, SQLiteSessionStore
from scryraven.sources import Evidence, exact_view


def no_io(*args, **kwargs):
    raise AssertionError("Unexpected provider I/O")


def test_saved_citations_project_exact_research_navigation_without_answer_leakage(tmp_path):
    first = Evidence("E1", "https://example.org/first", "Publication one",
                     "Private source body: the measured value is 14 units.")
    second = Evidence("E2", "https://example.org/second", "Publication two",
                      "Private second source body: the limit is 20 units.")
    view = exact_view(first, 21, 43)
    historical_answer = "Earlier result [1] and [2]."
    cited_turn = SessionTurn(
        "What did the publications say?", historical_answer, None, "supported", "supported",
        (view, second),
        (Citation(1, "E1", first.title, first.url, (view,)),
         Citation(2, "E2", second.title, second.url, (second,))),
        (CitationUse(1, historical_answer.index("[1]"), historical_answer.index("[1]") + 3),
         CitationUse(2, historical_answer.index("[2]"), historical_answer.index("[2]") + 3)),
    )
    premise_turn = SessionTurn("Suppose x is 2.", "Then x plus one is 3.", None,
                               "supported", "supported")
    unable_turn = SessionTurn("Was a third publication found?", "Not established.", None,
                              "unable", "not_established")
    saved_state = SessionState((cited_turn, premise_turn, unable_turn), (first, second))
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = store.create()
    for count in range(1, len(saved_state.turns) + 1):
        store.commit(saved.metadata.session_id, count - 1,
                     SessionState(saved_state.turns[:count], saved_state.acquisitions))

    model = Script(
        decision(requests=[request("read", query="", target="E1", mode="local")]),
        decision("answer"),
        answer("The current task remains unresolved.", "unable"),
    )
    session = ResearchSession.open(saved.metadata.session_id, store=store, model=model,
                                   search=no_io, fetch=no_io)
    question = "Can we revisit citation [1]?"
    result = session.ask(question)
    research_calls = [packet for stage, _, packet, _ in model.calls if stage == "research"]
    answer_packet = next(packet for stage, _, packet, _ in model.calls if stage == "answer")
    assert len(research_calls) == 2
    ordinary = [{"question": turn.question, "answer": turn.answer} for turn in saved_state.turns]
    assert all([{key: entry[key] for key in ("question", "answer")}
                for entry in packet["conversation_context"]] == ordinary
               for packet in research_calls)
    assert answer_packet["conversation_context"] == ordinary
    assert "research_conversation_context" not in answer_packet
    assert "E1@21:43" not in json.dumps(answer_packet)

    provenance = research_calls[0]["conversation_context"][0]["provenance"]
    assert provenance == {
        "posture": "supported", "stop_reason": "supported",
        "citations": [
            {"number": 1, "source_id": "E1", "title": first.title,
             "material_ids": ["E1@21:43"]},
            {"number": 2, "source_id": "E2", "title": second.title,
             "material_ids": ["E2"]},
        ],
    }
    use = cited_turn.citation_uses[0]
    assert historical_answer[use.start:use.end] == f"[{provenance['citations'][0]['number']}]"
    assert provenance["citations"][0]["material_ids"] == [view.id]
    assert research_calls[1]["conversation_context"] == research_calls[0]["conversation_context"]
    assert research_calls[0]["conversation_context"][1]["provenance"] == {
        "posture": "supported", "stop_reason": "supported", "citations": [],
    }
    assert research_calls[0]["conversation_context"][2]["provenance"] == {
        "posture": "unable", "stop_reason": "not_established", "citations": [],
    }
    assert set(provenance) == {"posture", "stop_reason", "citations"}
    assert set(provenance["citations"][0]) == {"number", "source_id", "title", "material_ids"}
    assert "Private source body" not in json.dumps(provenance)
    assert "measured value" not in json.dumps(provenance)
    assert result.trace[-1]["budget"]["external_attempts"] == 0

    started = next(event for event in result.trace if event["action"] == "started")
    assert started["prior_conversation_turns"] == 3
    assert started["conversation_characters"] == sum(len(turn.question) + len(turn.answer)
                                                     for turn in saved_state.turns)
    assert started["current_question_characters"] == len(question)
    assert started["retained_acquisition_count"] == 2
    assert started["total_retained_source_characters"] == len(first.content) + len(second.content)
    assert started["prior_provenance_citations"] == 2
    assert "question" not in started
    model_starts = [event for event in result.trace if event["action"] == "model_started"]
    assert [event["current_evidence_characters"] for event in model_starts] == [0, len(first.content), 0]
    assert all(event["conversation_characters"] == started["conversation_characters"]
               for event in model_starts)
    assert model_starts[0]["conversation_packet_characters"] == len(json.dumps(
        research_calls[0]["conversation_context"], ensure_ascii=False, sort_keys=True))
    assert model_starts[0]["conversation_packet_characters"] > model_starts[-1][
        "conversation_packet_characters"]
    assert all(event["catalog_characters"] > 0 for event in model_starts[:2])
    assert model_starts[-1]["catalog_characters"] == 0
    safe_counts = json.dumps([started, *model_starts])
    assert question not in safe_counts
    assert historical_answer not in safe_counts
    assert first.content not in safe_counts and second.content not in safe_counts
    answer_decision = next(event for event in result.trace if event["action"] == "answer_decision")
    assert "answer" not in answer_decision["decision"]
