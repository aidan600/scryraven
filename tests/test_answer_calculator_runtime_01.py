"""Offline Responses function-call paths through the ordinary Answer owner."""

import json
from copy import deepcopy

import pytest
import requests
from test_research_loop import answer, decision, no_fetch

from core.exa_transport import DiscoveryCandidate
from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.forensic_log import ForensicLog
from scryraven.model import OpenAIModel
from scryraven.research import ANSWER_PROMPT, RunLimits, run


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def model_reply(value, *, tokens=10):
    return {
        "status": "completed",
        "output": [{"type": "message", "phase": "final_answer", "content": [
            {"type": "output_text", "text": json.dumps(value)},
        ]}],
        "usage": {"input_tokens": tokens,
                  "input_tokens_details": {"cached_tokens": 2, "cache_write_tokens": 0},
                  "output_tokens": 5, "output_tokens_details": {"reasoning_tokens": 1}},
    }


def tool_reply(expression, call_id, *, tokens=10):
    reply = model_reply({}, tokens=tokens)
    reply["output"] = [{"type": "function_call", "name": "calculate", "call_id": call_id,
                        "arguments": json.dumps({"expression": expression})}]
    return reply


class ScriptedResponses:
    def __init__(self, *steps, now=None):
        self.steps = iter(steps)
        self.calls = []
        self.now = now

    def post(self, _url, **kwargs):
        self.calls.append(deepcopy(kwargs))
        expected_stage, reply, advance = next(self.steps)
        assert kwargs["json"]["text"]["format"]["name"] == expected_stage
        if self.now is not None:
            self.now[0] += advance
        if isinstance(reply, Exception):
            raise reply
        return Response(reply)


def run_offline(monkeypatch, transport, question, *, search=None, **kwargs):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    model = OpenAIModel(post=transport.post)
    result = run(question, model=model,
                 search=search or (lambda _query: pytest.fail("Unexpected search")),
                 fetch=no_fetch, **kwargs)
    return result, model


def calculations_in(payload):
    return [item for item in payload["input"] if item.get("type") == "function_call_output"]


def test_basic_user_premise_calculation_is_one_answer_attempt(monkeypatch):
    valid = answer("25 units from the stipulated 100 units.", support_basis="user_premises",
                   readings=[])
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0),
        ("answer", tool_reply("100 * 0.25", "calc_1"), 0),
        ("answer", model_reply(valid), 0),
    )
    observed = []
    result, _ = run_offline(
        monkeypatch, transport, "If the amount is 100 units, what is 25%?",
        limits=RunLimits(semantic_attempts=2), observe=observed.append,
    )

    assert result.posture == "supported" and result.answer == valid["answer"]
    assert result.evidence == result.selected_evidence == result.citations == ()
    assert result.trace[-1]["budget"]["semantic_attempts"] == 2
    assert [event["contract"] for event in result.trace if event["action"] == "model_started"] == [
        "research", "answer",
    ]
    assert "tools" not in transport.calls[0]["json"]
    assert transport.calls[1]["json"]["store"] is False
    assert len(transport.calls[1]["json"]["tools"]) == 1
    assert json.loads(calculations_in(transport.calls[2]["json"])[0]["output"]) == {"value": "25"}
    receipts = [event for event in observed if event["action"] == "calculator_result"]
    assert [(item["sequence"], item["expression"], item["result"])
            for item in receipts] == [(1, "100 * 0.25", {"value": "25"})]
    assert not any(event["action"] == "calculator_result" for event in result.trace)
    assert all("expression" not in event and "result" not in event for event in result.trace)


def test_chained_calculations_reuse_prior_result_and_aggregate_usage(monkeypatch):
    valid = answer("The stipulated result is 35.", support_basis="user_premises", readings=[])
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0),
        ("answer", tool_reply("100 * 1.2", "calc_a"), 0),
        ("answer", tool_reply("120 / 4", "calc_b"), 0),
        ("answer", tool_reply("30 + 5", "calc_c"), 0),
        ("answer", model_reply(valid), 0),
    )
    usage = []
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    model = OpenAIModel(post=transport.post, usage_observer=usage.append)
    result = run("Given 100 units, raise it by 20%, divide by 4, and add 5.", model=model,
                 search=lambda _q: pytest.fail("Unexpected search"), fetch=no_fetch,
                 limits=RunLimits(semantic_attempts=2))

    assert result.posture == "supported" and result.answer == valid["answer"]
    assert result.trace[-1]["budget"]["semantic_attempts"] == 2
    assert len([event for event in result.trace if event["action"] == "calculator_used"]) == 3
    assert [json.loads(item["output"]) for item in calculations_in(transport.calls[4]["json"])] == [
        {"value": "120"}, {"value": "30"}, {"value": "35"},
    ]
    answer_return = next(event for event in result.trace
                         if event["action"] == "model_returned" and event["contract"] == "answer")
    assert answer_return["usage"]["input_tokens"] == 40
    assert answer_return["usage"]["output_tokens"] == 20
    assert answer_return["usage"]["reasoning_tokens"] == 4
    assert answer_return["usage"]["cached_input_tokens"] == 8
    assert answer_return["usage"]["ordinary_uncached_tokens"] == 32
    assert [(item.stage, item.input_tokens) for item in usage] == [
        ("research", 10), ("answer", 10), ("answer", 10), ("answer", 10),
        ("answer", 10),
    ]


def test_answer_correction_allows_calculations_in_both_attempts(monkeypatch):
    invalid = answer("A rejected provisional number.", support_basis="user_premises",
                     readings=[], missing="A consequential need")
    valid = answer("The stipulated result is 30.", support_basis="user_premises", readings=[])
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0),
        ("answer", tool_reply("100 * 1.2", "calc_a"), 0),
        ("answer", tool_reply("120 / 4", "calc_b"), 0),
        ("answer", model_reply(invalid), 0),
        ("answer", tool_reply("120 / 4", "calc_c"), 0),
        ("answer", model_reply(valid), 0),
    )
    result, _ = run_offline(
        monkeypatch, transport, "Given 100 units, increase by 20%, divide by 4.",
        limits=RunLimits(semantic_attempts=3),
    )

    assert result.answer == valid["answer"]
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3
    assert len([event for event in result.trace if event["action"] == "calculator_used"]) == 3
    assert [(event["action"], event.get("attempt")) for event in result.trace
            if event["action"] in {"model_started", "model_returned"}
            and event.get("contract") == "answer"] == [
        ("model_started", 2), ("model_returned", 2),
        ("model_started", 3), ("model_returned", 3),
    ]
    assert [event["code"] for event in result.trace if event["action"] == "response_rejected"] == [
        "supported_with_missing_information",
    ]
    second_attempt_input = transport.calls[4]["json"]["input"]
    assert not calculations_in(transport.calls[4]["json"])
    assert "output_correction" in "".join(
        item.get("text", "") for block in second_attempt_input
        for item in block.get("content", [])
    )


@pytest.mark.parametrize("run_seconds,advance", [(300, 120.1), (5, 5.1)])
def test_tool_continuation_obeys_answer_and_whole_run_deadlines(
    monkeypatch, run_seconds, advance,
):
    now = [0.0]
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0),
        ("answer", tool_reply("100 / 4", "calc_a"), advance),
        now=now,
    )
    result, _ = run_offline(
        monkeypatch, transport, "Given 100, divide by 4.",
        limits=RunLimits(semantic_attempts=2, seconds=run_seconds), clock=lambda: now[0],
    )
    assert len(transport.calls) == 2
    assert result.posture == "unable"
    assert result.answer == "I couldn't complete a source-validated answer for this request."
    assert result.trace[-1]["budget"]["semantic_attempts"] == 2


def test_evidence_derived_result_cites_inputs_not_calculator(monkeypatch):
    source = "Capacity is 100 Ah and voltage is 12 V under the stated conditions."
    valid = answer("The derived energy is 1200 Wh. [E1]", readings=[
        {"evidence_ref": "E1", "passages": [source]},
    ])
    transport = ScriptedResponses(
        ("research", model_reply(decision()), 0),
        ("research", model_reply(decision("answer", ["E1"])), 0),
        ("answer", tool_reply("100 * 12", "calc_a"), 0),
        ("answer", model_reply(valid), 0),
    )
    result, _ = run_offline(
        monkeypatch, transport, "What is the energy?",
        search=lambda _q: [DiscoveryCandidate(
            "Specification", "https://example.org/spec", source,
            context_kind="provider_highlights",
        )],
    )

    assert result.posture == "supported" and result.answer == "The derived energy is 1200 Wh. [1]"
    assert [item.id for item in result.selected_evidence] == ["E1"]
    assert [citation.source_id for citation in result.citations] == ["E1"]
    assert [item.id for item in result.evidence] == ["E1"]
    assert next(event for event in result.trace if event["action"] == "answer_decision")[
        "decision"]["support_basis"] == "evidence"


def test_missing_external_premise_remains_unestablished(monkeypatch):
    source = "Capacity is 100 Ah. No voltage is stated."
    partial = answer("The source gives 100 Ah [E1], but no voltage needed for Wh.",
                     posture="partial", readings=[
                         {"evidence_ref": "E1", "passages": [source]},
                     ])
    transport = ScriptedResponses(
        ("research", model_reply(decision()), 0),
        ("research", model_reply(decision("answer", ["E1"])), 0),
        ("answer", model_reply(partial), 0),
    )
    result, _ = run_offline(
        monkeypatch, transport, "What is the energy in Wh?",
        search=lambda _q: [DiscoveryCandidate(
            "Specification", "https://example.org/spec", source,
            context_kind="provider_highlights",
        )],
    )
    assert result.posture == "partial" and result.answer.endswith("Wh.")
    assert len(result.citations) == 1
    assert not any(event["action"] == "calculator_used" for event in result.trace)
    assert "do not invent" in ANSWER_PROMPT.lower()
    assert "missing contingent external input" in ANSWER_PROMPT.lower()


def test_failed_continuation_preserves_known_usage_as_incomplete(monkeypatch):
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0),
        ("answer", tool_reply("100 / 4", "calc_a"), 0),
        ("answer", requests.Timeout("private transport detail"), 0),
    )
    diagnostics = TurnDiagnostics(started_at=0, clock=lambda: 0)
    result, _ = run_offline(
        monkeypatch, transport, "Given 100, divide by 4.",
        observe=diagnostics.observe,
    )
    failed = next(event for event in result.trace if event["action"] == "model_failed")
    assert failed["usage"]["input_tokens"] == 10
    assert failed["usage"]["output_tokens"] == 5
    assert failed["usage"]["usage_incomplete"] is True
    assert failed["code"] == "model_request_timed_out"
    record = diagnostics.record(session_id=None, revision_before=0, revision_after=1,
                                result=result)
    answer_call = next(row for row in record["model_calls"] if row["contract"] == "answer")
    assert answer_call["input_tokens"] == 10
    assert answer_call["output_tokens"] == 5
    assert answer_call["usage_incomplete"] is True
    assert "private transport detail" not in json.dumps(result.trace)


def test_real_tool_round_trip_reaches_forensic_log_without_safe_body_leak(
    monkeypatch, tmp_path,
):
    valid = answer("The stipulated 25% is 25 units.", support_basis="user_premises",
                   readings=[])
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0),
        ("answer", tool_reply("100 * 0.25", "calc_a"), 0),
        ("answer", tool_reply("PRIVATE_SOURCE_MARKER + 2", "calc_b"), 0),
        ("answer", model_reply(valid), 0),
    )
    forensic_path = tmp_path / "forensic.jsonl"
    forensic = ForensicLog(forensic_path)
    diagnostics = TurnDiagnostics(started_at=0, clock=lambda: 0)

    def observe(event):
        forensic.append(event, session_id="a" * 32, revision_before=0)
        diagnostics.observe(event)

    result, _ = run_offline(monkeypatch, transport,
                            "If the amount is 100 units, what is 25%?",
                            observe=observe)
    records = [json.loads(line) for line in forensic_path.read_text(encoding="utf-8").splitlines()]
    receipts = [row for row in records if row["event"]["action"] == "calculator_result"]
    assert [(row["event"]["attempt"], row["event"]["sequence"],
             row["event"]["expression"], row["event"]["result"])
            for row in receipts] == [
        (2, 1, "100 * 0.25", {"value": "25"}),
        (2, 2, "PRIVATE_SOURCE_MARKER + 2", {"error": "invalid_expression"}),
    ]
    assert receipts[0]["event_sequence"] < receipts[1]["event_sequence"]
    assert "PRIVATE_SOURCE_MARKER" not in json.dumps(result.trace)
    record = diagnostics.record(session_id="a" * 32, revision_before=0,
                                revision_after=1, result=result)
    assert record["calculator"]["calls"] == 2
    assert record["calculator"]["failures"] == 1
    assert "PRIVATE_SOURCE_MARKER" not in json.dumps(record)


def test_invalid_tool_arguments_do_not_reuse_previous_calculation_timing(monkeypatch):
    now = [0.0]
    malformed = tool_reply("unused", "calc_b")
    malformed["output"][0]["arguments"] = "not-json"
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0),
        ("answer", tool_reply("1 + 1", "calc_a"), 0),
        ("answer", malformed, 0),
        ("answer", model_reply(answer("Two units.", support_basis="user_premises",
                                      readings=[])), 0),
        now=now,
    )

    def timed_calculate(_expression):
        now[0] += 0.25
        return {"value": "2"}

    monkeypatch.setattr("scryraven.research.calculate", timed_calculate)
    result, _ = run_offline(monkeypatch, transport, "Given one unit, what is one plus one?",
                            clock=lambda: now[0])
    used = [event for event in result.trace if event["action"] == "calculator_used"]
    assert [(event["success"], event["duration_seconds"]) for event in used] == [
        (True, 0.25), (False, None),
    ]
