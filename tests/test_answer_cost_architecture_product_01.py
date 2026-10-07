"""Semantic Answer, non-authoritative localization, and legacy fallback."""
import hashlib
import json
import sqlite3

import pytest
from test_model_transport import Response
from test_research_loop import (
    Script,
    answer,
    decision,
    failed_localization,
    multi_search,
    no_fetch,
    request,
    search,
    synthetic_localization,
)

from core.exa_transport import DiscoveryCandidate
from scryraven.model import ModelConfig, ModelError, ModelRole, OpenAIModel
from scryraven.research import (
    ANSWER_PROMPT,
    LOCALIZATION_PROMPT,
    SEMANTIC_ANSWER_PROMPT,
    AnswerDecision,
    SemanticAnswerDecision,
    literal_passage_span,
    run,
)
from scryraven.session import ResearchSession
from scryraven.session_store import SessionTurn, SQLiteSessionStore

_LEGACY_PROMPT_HASH = "b5bd95717485690e130a6c8060ba168b510862cd27ec5b617598d4992b4eabd9"
_PASSAGE = "The stated value is seven."
_TURN_KEYS = {
    "question", "answer", "analysis", "posture", "stop_reason",
    "selected_evidence", "citations", "citation_uses",
}


def stages(model):
    return [call[0] for call in model.calls]


def packets(model, stage):
    return [call[2] for call in model.calls if call[0] == stage]


def legacy_answer(text="The stated value is seven. [E1]"):
    return answer(text, readings=[{"evidence_ref": "E1", "passages": [_PASSAGE]}])


def test_primary_semantic_schema_and_prompt_drop_only_reading_output():
    assert "source_readings" not in SemanticAnswerDecision.model_fields
    assert "source_readings" not in SemanticAnswerDecision.model_json_schema()["properties"]
    assert "source_readings" in AnswerDecision.model_fields
    assert set(ModelConfig.__dataclass_fields__) == {"research", "answer"}
    assert hashlib.sha256(ANSWER_PROMPT.encode()).hexdigest() == _LEGACY_PROMPT_HASH
    assert "source_reading" not in SEMANTIC_ANSWER_PROMPT
    assert "Read the supplied Evidence yourself before composing." in SEMANTIC_ANSWER_PROMPT
    assert "Do not output copied support passages" in SEMANTIC_ANSWER_PROMPT
    assert "non-authoritative localization step may run" in SEMANTIC_ANSWER_PROMPT
    assert "No separate verifier or polisher" in SEMANTIC_ANSWER_PROMPT
    assert "No separate verifier or polisher" in ANSWER_PROMPT
    folded = " ".join(LOCALIZATION_PROMPT.split())
    assert "citations are frozen" in folded
    assert "Do not rewrite, approve, reject or reinterpret" in folded
    assert "insufficient_source_ids" in folded
    assert "No calculator." in folded


def test_consequential_missing_information_returns_to_research_without_localization():
    model = Script(
        decision(), decision("answer", ["E1"]),
        answer("Only seven is established. [E1]", "partial", "What condition applies?"),
        decision("answer", ["E1"]),
    )

    result = run("What is the value?", model=model, search=search, fetch=no_fetch)

    assert stages(model) == ["research", "research", "answer", "research"]
    assert packets(model, "research")[-1]["answer_missing_information"] == "What condition applies?"
    assert "Only seven is established" not in json.dumps(packets(model, "research")[-1])
    assert result.posture == "partial"
    assert "Only seven is established" in result.answer
    assert any(event["action"] == "answer_returned_to_research" for event in result.trace)
    assert any(event["action"] == "answer_committed_no_progress" for event in result.trace)
    assert not any(event["action"].startswith("support_localization") for event in result.trace)
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4


def test_new_evidence_after_missing_information_localizes_only_the_terminal_answer():
    def varied(query):
        if query == "condition":
            return [DiscoveryCandidate(
                "Condition", "https://example.org/condition", "The condition is daylight.",
                context_kind="provider_highlights")]
        return search(query)

    model = Script(
        decision(requests=[request(query="public fact")]),
        decision("answer", ["E1"]),
        answer("Seven is stated. [E1]", "partial", "What condition applies?"),
        decision(requests=[request(query="condition")]),
        decision("answer", ["E1", "E2"]),
        answer("Seven applies in daylight. [E1, E2]"),
    )

    result = run("What is the value?", model=model, search=varied, fetch=no_fetch)

    assert stages(model) == [
        "research", "research", "answer", "research", "research", "answer", "localize"]
    assert packets(model, "research")[2]["answer_missing_information"] == "What condition applies?"
    assert "Seven is stated" not in json.dumps(packets(model, "research")[2])
    assert [event["action"] for event in result.trace].count("support_localization_started") == 1
    assert result.posture == "supported"
    assert [citation.source_id for citation in result.citations] == ["E1", "E2"]
    assert result.trace[-1]["budget"]["semantic_attempts"] == 6


@pytest.mark.parametrize("posture", ["supported", "partial"])
def test_terminal_evidence_answer_localizes_after_the_semantic_decision(posture):
    model = Script(decision(), decision("answer", ["E1"]),
                   answer("The stated value is seven. [E1]", posture))
    observed = []

    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 observe=observed.append)

    assert stages(model) == ["research", "research", "answer", "localize"]
    actions = [event["action"] for event in result.trace]
    assert actions.index("answer_semantic_decision") < actions.index("support_localization_started")
    assert actions.index("support_localization_completed") < actions.index("answer_decision")
    assert "answer_legacy_fallback" not in actions
    localize = packets(model, "localize")[0]
    assert set(localize) == {
        "question", "current_date", "conversation_context", "phase", "posture",
        "support_basis", "answer", "missing_information", "cited_source_ids", "evidence",
    }
    assert localize["phase"] == "localize" and localize["posture"] == posture
    assert result.answer.endswith("[1]") and result.citations[0].source_id == "E1"
    completion = next(index for index, event in enumerate(result.trace)
                      if event["action"] == "answer_source_completion")
    semantic = next(index for index, event in enumerate(result.trace)
                    if event["action"] == "model_started" and event["contract"] == "answer")
    assert completion < semantic
    assert any(event["action"] == "answer_reading" for event in observed)
    assert not any(event["action"] == "answer_reading" for event in result.trace)
    assert _PASSAGE not in json.dumps(result.trace)


def test_localizer_borrows_research_model_settings_under_localize_telemetry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    config = ModelConfig(
        research=ModelRole("gpt-6-luna", "high", "fast"),
        answer=ModelRole("gpt-6.1-sol", "high", "fast"),
    )
    scripted = [decision(), decision("answer", ["E1"]), answer()]
    seen = []

    def post(_url, **kwargs):
        body = kwargs["json"]
        name = body["text"]["format"]["name"]
        seen.append((name, body["model"], body["reasoning"]["effort"], body.get("service_tier")))
        material = json.loads("".join(block["text"] for block in body["input"][1]["content"]))
        if name == "localize":
            text = json.dumps(synthetic_localization(material))
        else:
            text = json.dumps(scripted.pop(0))
        return Response({"status": "completed", "output": [{"type": "message", "phase": "final_answer",
                         "content": [{"type": "output_text", "text": text}]}]})

    result = run("What is the value?", model=OpenAIModel(config, post=post),
                 search=search, fetch=no_fetch)

    assert [item[0] for item in seen] == ["research", "research", "answer", "localize"]
    assert seen[2][1:] == ("gpt-6.1-sol", "high", "fast")
    assert seen[3][1:] == ("gpt-6-luna", "high", "fast")
    started = [event for event in result.trace if event["action"] == "model_started"]
    assert started[-1]["contract"] == "localize"
    assert started[-1]["model"] == "gpt-6-luna"
    assert started[-1]["attempt"] == started[-2]["attempt"]
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3


@pytest.mark.parametrize(("outputs", "posture"), [
    ([decision("answer"), answer(
        "Under your assumptions, the figure is conditional.", support_basis="user_premises")],
     "supported"),
    ([decision(), decision("answer", ["E1"]),
      answer("The source does not establish the answer.", "unable", support_basis="none")],
     "unable"),
])
def test_user_premise_and_unable_answers_skip_localization(outputs, posture):
    model = Script(*outputs)

    result = run("What follows?", model=model, search=search, fetch=no_fetch)

    assert "localize" not in stages(model)
    assert not any(event["action"].startswith("support_localization") for event in result.trace)
    assert result.posture == posture
    assert result.citations == ()


def test_exact_localization_covers_every_cited_source_group():
    located = {"readings": [
        {"evidence_ref": "E1", "passages": ["First exact passage."]},
        {"evidence_ref": "E2", "passages": ["Second source fact."]},
    ], "insufficient_source_ids": []}
    model = Script(
        decision(), decision("answer", ["E1", "E2"]),
        answer("The two facts differ. [E1, E2]"), located,
    )
    observed = []

    result = run("Compare the facts.", model=model, search=multi_search, fetch=no_fetch,
                 observe=observed.append)

    assert "answer_legacy_fallback" not in [event["action"] for event in result.trace]
    completed = next(event for event in result.trace if event["action"] == "support_localization_completed")
    assert completed["covered_source_ids"] == ["E1", "E2"]
    assert completed["rejected_passage_count"] == 0
    assert [citation.source_id for citation in result.citations] == ["E1", "E2"]
    forensic = next(event for event in observed if event["action"] == "answer_reading")
    assert {item["source_id"] for item in forensic["readings"]} == {"E1", "E2"}
    assert "First exact passage." not in json.dumps(result.trace)


def test_one_invalid_passage_is_dropped_when_the_same_group_stays_covered():
    content = "A joint-\neffort program states seven."
    assert literal_passage_span("joint-effort", content) is None
    assert literal_passage_span("program states seven.", content) is not None

    def hyphenated(_query):
        return [DiscoveryCandidate(
            "Program", "https://example.org/program", content, context_kind="provider_highlights")]

    located = {"readings": [{"evidence_ref": "E1", "passages": [
        "joint-effort", "program states seven."]}], "insufficient_source_ids": []}
    model = Script(
        decision(), decision("answer", ["E1"]),
        answer("The program states seven. [E1]"), located,
    )
    observed = []

    result = run("What does the program state?", model=model, search=hyphenated, fetch=no_fetch,
                 observe=observed.append)

    rejected = [event for event in result.trace if event["action"] == "support_localization_passage_rejected"]
    assert len(rejected) == 1 and rejected[0]["code"] == "reading_passage_not_in_source"
    assert "joint-effort" not in json.dumps(result.trace)
    assert any(event["action"] == "support_localization_passage_rejected_detail"
               and event["attempted_passage"] == "joint-effort" for event in observed)
    completed = next(event for event in result.trace if event["action"] == "support_localization_completed")
    assert completed["rejected_passage_count"] == 1 and completed["valid_passage_count"] == 1
    assert "answer_legacy_fallback" not in [event["action"] for event in result.trace]
    assert result.answer == "The program states seven. [1]"
    assert result.posture == "supported"


def _fallback_run(localization, legacy_outputs):
    model = Script(
        decision(), decision("answer", ["E1"]),
        answer("DISCARDED_SEMANTIC_SENTENCE_ZX is not for publication. [E1]"),
        localization, *legacy_outputs,
    )
    result = run("What is the value?", model=model, search=search, fetch=no_fetch)
    return model, result


@pytest.mark.parametrize(("localization", "code"), [
    ({"readings": [{"evidence_ref": "E1", "passages": ["NOT_IN_SOURCE_ZX"]}],
      "insufficient_source_ids": []}, "cited_source_without_localized_support"),
    ({"readings": [{"evidence_ref": "E1", "passages": [_PASSAGE]}],
      "insufficient_source_ids": ["E1"]}, "insufficient_source_ids"),
    ({"readings": "not-a-list", "insufficient_source_ids": []}, "malformed_localization"),
    (ModelError("model_transport_failed"), "model_transport_failed"),
])
def test_localization_failure_falls_back_to_the_legacy_answer_contract(localization, code):
    model, result = _fallback_run(localization, [legacy_answer()])

    assert stages(model) == ["research", "research", "answer", "localize", "answer"]
    assert next(event["code"] for event in result.trace
                if event["action"] == "answer_legacy_fallback") == code
    semantic, legacy = packets(model, "answer")
    assert semantic["evidence"] == legacy["evidence"]
    assert legacy["evidence"][0]["content"] == _PASSAGE
    assert model.calls[-1][1] == ANSWER_PROMPT
    assert "source_readings" in model.calls[-1][3]["properties"]
    dumped = json.dumps(legacy)
    assert "DISCARDED_SEMANTIC_SENTENCE_ZX" not in dumped
    assert "NOT_IN_SOURCE_ZX" not in dumped
    assert "not-a-list" not in dumped
    assert result.answer == "The stated value is seven. [1]"
    assert "DISCARDED_SEMANTIC_SENTENCE_ZX" not in result.answer
    started = [event for event in result.trace if event["action"] == "model_started"]
    assert started[-2]["contract"] == "localize"
    assert started[-2]["attempt"] == started[-3]["attempt"]
    assert started[-1]["contract"] == "answer" and started[-1]["attempt"] == started[-3]["attempt"] + 1
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4


def test_legacy_fallback_keeps_one_correction_on_the_same_evidence_packet():
    invalid = answer("REJECTED_LEGACY_PROSE [E1]", readings=[
        {"evidence_ref": "E1", "passages": ["NOT_A_SOURCE_PASSAGE"]}])
    model, result = _fallback_run(
        failed_localization(), [invalid, legacy_answer("The corrected legacy value is seven. [E1]")])

    assert stages(model) == ["research", "research", "answer", "localize", "answer", "answer"]
    legacy = packets(model, "answer")[1:]
    assert legacy[0]["evidence"] == legacy[1]["evidence"]
    assert legacy[1]["output_correction"]["code"] == "reading_passage_not_in_source"
    assert "DISCARDED_SEMANTIC_SENTENCE_ZX" not in json.dumps(legacy)
    assert "REJECTED_LEGACY_PROSE" not in json.dumps(legacy[1])
    assert result.answer == "The corrected legacy value is seven. [1]"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 5


def test_legacy_fallback_still_runs_after_localization_uses_most_of_the_old_stage_window():
    now = [0.0]
    steps = [decision(), decision("answer", ["E1"]),
             answer("DISCARDED_SEMANTIC_SENTENCE_ZX [E1]")]

    class ClockModel:
        def __init__(self):
            self.calls = []

        def __call__(self, stage, prompt, packet, schema):
            self.calls.append((stage, prompt, packet, schema))
            if stage == "localize":
                now[0] += 119
                return json.dumps(failed_localization())
            value = steps.pop(0) if steps else legacy_answer()
            return json.dumps(value)

    model = ClockModel()
    result = run("What is the value?", model=model, search=search, fetch=no_fetch, clock=lambda: now[0])

    assert stages(model) == ["research", "research", "answer", "localize", "answer"]
    assert result.answer == "The stated value is seven. [1]"
    assert result.posture == "supported"


def test_localization_receives_only_cited_source_groups():
    model = Script(
        decision(), decision("answer", ["E1", "E2"]),
        answer("Only the first fact is reported. [E1]"),
    )

    result = run("Report the first fact.", model=model, search=multi_search, fetch=no_fetch)

    localize = packets(model, "localize")[0]
    assert localize["cited_source_ids"] == ["E1"]
    assert [item["id"] for item in localize["evidence"]] == ["E1"]
    assert [item["id"] for item in packets(model, "answer")[0]["evidence"]] == ["E1", "E2"]
    assert [citation.source_id for citation in result.citations] == ["E1"]
    assert result.selected_evidence[0].id == "E1"


def test_published_answer_persists_without_support_spans(tmp_path):
    model = Script(decision(), decision("answer", ["E1"]), answer())
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=search, fetch=no_fetch)

    result = session.ask("What is the value?")

    assert set(SessionTurn.__dataclass_fields__) == _TURN_KEYS
    assert result.answer == session.turns[0].answer
    assert session.turns[0].citations == result.citations
    payload = json.loads(sqlite3.connect(store.path).execute("select payload from sessions").fetchone()[0])
    assert set(payload["turns"][0]) == _TURN_KEYS
    assert "support_span" not in json.dumps(payload)
    assert "source_readings" not in json.dumps(payload)
    reopened = ResearchSession.open(session.session_id, store=SQLiteSessionStore(store.path))
    assert reopened.turns[0].answer == result.answer
    assert reopened.turns[0].selected_evidence == result.selected_evidence
