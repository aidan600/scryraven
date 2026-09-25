"""The operator screen invokes real Answer mechanics, with no live provider I/O."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_answer_calculator_runtime_01 import ScriptedResponses, model_reply, tool_reply
from test_research_loop import answer

from scripts import answer_development_screen as screen
from scryraven import research
from scryraven.sources import Evidence, exact_view


def envelope(*, with_evidence=False):
    items = [Evidence("E1", "https://example.org/value", "Synthetic value",
                      "The stated value is seven.").material()] if with_evidence else []
    return {
        "schema_version": 1, "packet_id": "SYNTHETIC",
        "packet": {"question": "Assume 120 units. Divide it by four.",
                   "current_date": "2026-09-24", "conversation_context": [],
                   "phase": "answer", "evidence": items, "acquisition_limitations": [],
                   "budget": {"semantic_attempts": 11, "external_attempts": 16,
                              "semantic_remaining": 1, "seconds_remaining": 3}},
        "acquisitions": deepcopy(items),
        "provenance": {"not_model_input": "SECRET_EVALUATOR_SENTINEL"},
        "obligations": ["RUBRIC_SENTINEL"],
    }


def invoke(monkeypatch, tmp_path, source, *replies, journal=None):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    transport = ScriptedResponses(*[("answer", reply, 0) for reply in replies])
    journal = journal or screen.Journal(tmp_path / "ledger.jsonl", "offline")
    result = screen.execute(source, journal, post=transport.post)
    return result, transport, journal


def packet_from_request(request):
    return json.loads("".join(item["text"] for message in request["json"]["input"]
                             if message.get("role") == "user" for item in message["content"]))


def test_real_calculator_continuation_and_exact_packet_no_envelope_leak(monkeypatch, tmp_path):
    source = envelope()
    original = deepcopy(source)
    final = answer("Under your stipulated 120 units, the result is 30.",
                   support_basis="user_premises", readings=[])
    result, transport, journal = invoke(monkeypatch, tmp_path, source,
                                       tool_reply("120 / 4", "calc1"), model_reply(final))
    assert result["status"] == "completed"
    assert result["decision"] == final
    assert source == original and result["packet_unchanged"]
    assert packet_from_request(transport.calls[0]) == source["packet"]
    serialized = json.dumps(transport.calls)
    assert "SECRET_EVALUATOR_SENTINEL" not in serialized and "RUBRIC_SENTINEL" not in serialized
    assert all(call["json"]["text"]["format"]["name"] == "answer" for call in transport.calls)
    assert journal.counts == {"semantic_submitted": 1, "provider_submitted": 2}
    outputs = [item for item in transport.calls[1]["json"]["input"]
               if item.get("type") == "function_call_output"]
    assert json.loads(outputs[0]["output"]) == {"value": "30"}
    assert len(result["usage"]) == 2
    assert any(event["action"] == "calculator_result" and event["result"] == {"value": "30"}
               for event in result["events"])
    assert not any(event.get("contract") == "research" for event in result["events"])


def test_actual_reading_validation_correction_and_citations(monkeypatch, tmp_path):
    source = envelope(with_evidence=True)
    invalid = answer("The stated value is seven. [E1]", readings=[{
        "evidence_ref": "E1", "passages": ["The value is eight."]}])
    result, transport, journal = invoke(monkeypatch, tmp_path, source,
                                       model_reply(invalid), model_reply(answer()))
    assert result["status"] == "completed"
    assert journal.counts == {"semantic_submitted": 2, "provider_submitted": 2}
    assert len(result["structured_attempts"]) == 2
    assert result["structured_attempts"][0]["decision"] == invalid
    corrected_packet = packet_from_request(transport.calls[1])
    correction = corrected_packet.pop("output_correction")
    assert corrected_packet == source["packet"]
    assert correction["code"] == "reading_passage_not_in_source"
    assert "The value is eight." not in json.dumps(correction)
    assert result["result"]["answer"] == "The stated value is seven. [1]"
    assert result["result"]["citations"][0]["materials"][0]["content"] == "The stated value is seven."


def test_invalid_corrected_answer_exhausts_same_production_allowance(monkeypatch, tmp_path):
    invalid = answer("No literal reading. [E1]", readings=[])
    result, transport, _ = invoke(monkeypatch, tmp_path, envelope(with_evidence=True),
                                  model_reply(invalid), model_reply(invalid))
    assert result["status"] == "validation_exhausted"
    assert len(transport.calls) == 2
    assert result["result"]["answer"] == research.ANSWER_VALIDATION_FAILURE_MESSAGE
    assert result["result"]["citations"] == ()


@pytest.mark.parametrize("kind,cap", [("semantic_submitted", 24), ("provider_submitted", 40)])
def test_durable_phase_cap_stops_before_dispatch(monkeypatch, tmp_path, kind, cap):
    journal = screen.Journal(tmp_path / "ledger.jsonl", "previous")
    for _ in range(cap):
        journal.reserve(kind)
    reloaded = screen.Journal(journal.path, "offline")
    result, transport, ledger = invoke(monkeypatch, tmp_path, envelope(),
        model_reply(answer("30.", support_basis="user_premises", readings=[])), journal=reloaded)
    assert result["status"] == "screen_stopped"
    assert result["code"] == kind + "_cap_reached"
    assert transport.calls == []
    assert ledger.counts[kind] == cap


def test_continuation_cap_is_not_swallowed_by_transport_or_observer(monkeypatch, tmp_path):
    journal = screen.Journal(tmp_path / "ledger.jsonl", "previous")
    for _ in range(39):
        journal.reserve("provider_submitted")
    result, transport, ledger = invoke(monkeypatch, tmp_path, envelope(),
        tool_reply("120 / 4", "calc1"), model_reply(answer()), journal=journal)
    assert len(transport.calls) == 1
    assert result["status"] == "screen_stopped"
    assert result["code"] == "provider_submitted_cap_reached"
    assert ledger.counts["provider_submitted"] == 40


def test_sparse_original_identity_and_targeted_view_custody(monkeypatch, tmp_path):
    source = envelope(with_evidence=True)
    canonical = Evidence("E4", "https://example.org/value", "Original", "First acquisition.")
    parent = Evidence("E9", canonical.url, "Later exact parent", "Prefix. The value is seven. Suffix.",
                      source_id="E4")
    selected = exact_view(parent, 8, 27)
    source["packet"]["evidence"] = [selected.material()]
    source["acquisitions"] = [canonical.material(), parent.material()]
    final = answer("The value is seven. [E9@8:27]", readings=[{
        "evidence_ref": selected.id, "passages": ["The value is seven."]}])
    result, transport, _ = invoke(monkeypatch, tmp_path, source, model_reply(final))
    assert result["status"] == "completed"
    assert packet_from_request(transport.calls[0])["evidence"] == source["packet"]["evidence"]
    assert result["result"]["citations"][0]["source_id"] == "E4"


def test_extraction_fails_closed_when_production_packet_shape_changes(monkeypatch, tmp_path):
    source = Path(research.__file__).read_text(encoding="utf-8")
    changed = tmp_path / "changed_research.py"
    changed.write_text(source.replace('packet = {**common, "phase": "answer",',
                                     'packet = dict(phase="answer")\n        other = {**common, "phase": "answer",'),
                       encoding="utf-8")
    monkeypatch.setattr(research, "__file__", str(changed))
    with pytest.raises(ValueError, match="answer_packet_constructor_changed"):
        screen.extracted_functions()
