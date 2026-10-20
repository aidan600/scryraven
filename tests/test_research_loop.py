"""Synthetic contracts test mechanics only; they cannot establish research skill."""
import json

import pytest

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.model import ModelError, OpenAIModel
from scryraven.presentation import RESEARCH_BOUND_DISCLOSURE, render_cli
from scryraven.research import (
    TERMINAL_ANSWER_RESERVE_SECONDS,
    ResearchDecision,
    RunError,
    RunLimits,
    run,
)
from scryraven.sources import Evidence


def request(kind="search", query="public fact", target="", mode="auto", focus=""):
    return dict(kind=kind, query=query, target=target, mode=mode, focus=focus,
                scope=[], start_char=None, end_char=None)


def decision(action="research", refs=(), requests=None, interpretation="Find the requested fact"):
    return dict(understanding=dict(interpretation=interpretation, established=[],
                                  still_needed=[] if action == "answer" else ["What is the fact?"],
                                  last_route_result=""), action=action,
                requests=([request()] if requests is None and action == "research" else requests or []),
                retain=list(refs), answer_evidence_refs=list(refs) if action == "answer" else [])


def test_research_decision_schema_has_no_purpose_and_rejects_legacy_output():
    expected = decision()
    parsed = ResearchDecision.model_validate(expected)
    assert parsed.model_dump() == expected
    assert "purpose" not in ResearchDecision.model_fields
    assert "purpose" not in ResearchDecision.model_json_schema()["properties"]
    with pytest.raises(ValueError):
        ResearchDecision.model_validate({**expected, "purpose": "Legacy route prose"})


def test_legacy_purpose_output_uses_bounded_malformed_response_correction():
    legacy = {**decision("answer"), "purpose": "Legacy route prose"}
    model = Script(legacy, decision("answer"),
                   answer("No source establishes this.", "unable"))
    result = run("Value?", model=model, search=search, fetch=no_fetch)
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert model.calls[1][2]["output_correction"]
    assert "Legacy route prose" not in json.dumps(model.calls[1][2])
    assert [event["code"] for event in result.trace
            if event["action"] == "response_rejected"] == ["malformed_model_response"]
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3
    assert result.posture == "unable"


def answer(text="The stated value is seven. [E1]", posture="supported", missing=None,
           support_basis=None):
    support_basis = support_basis or ("none" if posture == "unable" else "evidence")
    result = dict(answer=text, posture=posture, support_basis=support_basis,
                  missing_information=missing)
    return result


def next_scripted(outputs, stage, material):
    """Play only explicitly scripted production model outputs."""
    if not outputs:
        raise StopIteration
    value = outputs.pop(0)
    if callable(value):
        value = value(material)
    if isinstance(value, Exception):
        raise value
    return value


class Script:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def __call__(self, stage, prompt, material, schema):
        self.calls.append((stage, prompt, material, schema))
        value = next_scripted(self.outputs, stage, material)
        if isinstance(value, dict):
            assert stage == ("research" if "understanding" in value else "answer")
        return value if isinstance(value, str) else json.dumps(value)


def search(query):
    return [DiscoveryCandidate("Official fact", "https://example.org/fact", "The stated value is seven.", context_kind="provider_highlights")]


def multi_search(query):
    return [
        DiscoveryCandidate("First source", "https://example.org/first",
                           "First exact passage. A material qualification applies. Final first-source fact.",
                           context_kind="provider_highlights"),
        DiscoveryCandidate("Second source", "https://example.org/second",
                           "Second source fact. A second qualification applies.", context_kind="provider_highlights"),
    ]


def no_fetch(url):
    pytest.fail("Unexpected external read")


def test_fresh_source_first_answer_and_exact_exposure():
    model = Script(decision(), decision("answer", ["E1"]), answer())
    observations = []
    result = run("What is the value?", model=model, search=search, fetch=no_fetch, observe=observations.append)
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    packet = next(call[2] for call in model.calls if call[0] == "answer")
    assert not {"working_understanding", "analysis", "draft", "verdict", "research_cautions"} & packet.keys()
    assert packet["evidence"][0]["content"] == "The stated value is seven."
    assert result.answer.endswith("[1]")
    assert result.selected_evidence == result.citations[0].materials
    assert result.evidence == result.selected_evidence
    starts = [e for e in result.trace if e["action"] == "model_started"]
    assert starts[0]["exposed"] == []
    assert starts[1]["exposed"][0]["id"] == "E1"
    assert not any("content" in str(e) for e in result.trace if e["action"] == "model_started")
    assert any(e["action"] == "exposure" and e["evidence"] for e in observations)


def test_unexposed_retained_reference_is_rejected_then_local_read():
    retained = Evidence("E1", "https://example.org/fact", "Fact", "The stated value is seven.")
    model = Script(decision("answer", ["E1"]),
                   decision(requests=[request("read", query="", target="E1", mode="local")]),
                   decision("answer", ["E1"]), answer())
    result = run("What is the value?", model=model, search=lambda q: pytest.fail("Unexpected search"),
                 fetch=no_fetch, retained_acquisitions=(retained,))
    assert any(e["action"] == "decision_rejected" for e in result.trace)
    correction = model.calls[1][2]["output_correction"]
    assert correction["issues"]["unexposed_answer_refs"] == ["E1"]
    assert correction["exposed_refs"] == []
    assert result.evidence == (retained,)
    assert result.trace[-1]["budget"]["external_attempts"] == 0


def test_missing_need_returns_to_same_loop_without_draft_or_budget_reset():
    model = Script(decision(), decision("answer", ["E1"]),
                   answer("A provisional fragment. [E1]", "partial", "What conditions apply?"),
                   decision(requests=[request("read", query="", target="E1", mode="full", focus="conditions")], refs=["E1"]),
                   decision("answer", ["E2"]),
                   answer("Seven under the stated condition. [E2]"))
    result = run("What is the value?", model=model, search=search,
                 fetch=lambda url: FetchedMaterial(url, "Seven under the stated condition."))
    continuation = model.calls[3][2]
    assert continuation["answer_missing_information"] == "What conditions apply?"
    assert "provisional fragment" not in json.dumps(continuation)
    assert continuation["evidence"][0]["id"] == "E1"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 6
    assert result.trace[-1]["budget"]["external_attempts"] == 2
    assert not any(event["action"] == "answer_committed_no_progress" for event in result.trace)


def test_terminal_unable_answer_without_a_need_commits_immediately():
    model = Script(decision("answer"), answer("The material does not establish this.", "unable"))
    result = run("What is the value?", model=model, search=search, fetch=no_fetch)
    assert [call[0] for call in model.calls] == ["research", "answer"]
    assert result.posture == "unable"
    assert not any(event["action"] == "answer_returned_to_research" for event in result.trace)


def test_terminal_partial_answer_without_a_need_commits_immediately():
    model = Script(decision(), decision("answer", ["E1"]),
                   answer("The material establishes only this fragment. [E1]", "partial"))
    result = run("What is the value?", model=model, search=search, fetch=no_fetch)
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert result.posture == "partial"
    assert not any(event["action"] == "answer_returned_to_research" for event in result.trace)


def test_partial_answer_with_no_new_selected_material_commits_without_a_second_answer():
    model = Script(decision(), decision("answer", ["E1"]),
                   answer("A supported fragment. [E1]", "partial", "What condition applies?"),
                   decision("answer", ["E1"]))
    result = run("What is the value?", model=model, search=search, fetch=no_fetch)
    assert [call[0] for call in model.calls] == ["research", "research", "answer", "research"]
    assert result.answer.startswith("A supported fragment.")
    assert result.posture == "partial"
    committed = [event for event in result.trace if event["action"] == "answer_committed_no_progress"]
    assert committed == [
        {"stage": "research", "action": "answer_committed_no_progress", "posture": "partial",
         "missing_information": "What condition applies?", "prior_selected_refs": ["E1"],
         "selected_refs": ["E1"]},
    ]


def test_partial_answer_at_a_semantic_bound_is_not_promoted_to_support():
    model = Script(decision(), decision("answer", ["E1"]),
                   answer("A supported fragment. [E1]", "partial", "What condition applies?"),
                   decision(refs=["E1"]))
    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 limits=RunLimits(semantic_attempts=5, external_attempts=1))
    assert [call[0] for call in model.calls] == ["research", "research", "answer", "research"]
    assert result.posture == "partial"
    assert result.stop_reason == "research_bound"
    assert any(event["action"] == "research_bound" for event in result.trace)
    assert RESEARCH_BOUND_DISCLOSURE in render_cli(result)
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4


def test_malformed_call_consumes_attempt_and_final_reserve_is_source_first():
    model = Script("invalid", decision(), answer())
    result = run("Value?", model=model, search=search, fetch=no_fetch, limits=RunLimits(semantic_attempts=3))
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert result.stop_reason == "research_bound"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3
    assert next(call[2] for call in model.calls if call[0] == "answer")["evidence"][0]["id"] == "E1"


def test_external_budget_blocks_second_independent_request_without_hiding_first_material():
    model = Script(decision(requests=[request(query="one"), request(query="two")]),
                   decision("answer", ["E1"]), answer())
    calls = []
    result = run("Value?", model=model, search=lambda q: calls.append(q) or search(q), fetch=no_fetch,
                 limits=RunLimits(external_attempts=1))
    assert calls == ["one"]
    assert model.calls[1][2]["last_route"][1]["code"] == "external_attempts"
    assert result.trace[-1]["budget"]["external_attempts"] == 1


def test_deadline_prevents_additional_io_and_produces_honest_operational_result():
    now = [0.0]
    def delayed(q):
        now[0] = 10
        return search(q)
    model = Script(decision())
    result = run("Value?", model=model, search=delayed, fetch=no_fetch,
                 limits=RunLimits(seconds=5), clock=lambda: now[0])
    assert len(model.calls) == 1
    assert result.posture == "unable"
    assert result.citations == ()
    assert len(result.evidence) == 1
    assert not any(e["action"] == "model_started" and e["exposed"] for e in result.trace)


def test_run_headroom_defaults_and_model_trace_use_one_monotonic_clock():
    assert RunLimits() == RunLimits(semantic_attempts=12, external_attempts=16,
                                     seconds=300, attention_characters=128_000)
    assert TERMINAL_ANSWER_RESERVE_SECONDS == 180
    now = [10.0]

    def research_after_transport(_material):
        now[0] = 11.25
        return decision("answer")

    def answer_after_transport(_material):
        now[0] = 13.5
        return answer("No source establishes this.", "unable")

    result = run("Value?", model=Script(research_after_transport, answer_after_transport),
                 search=search, fetch=no_fetch, clock=lambda: now[0])
    events = [event for event in result.trace if event["action"].startswith("model_")]
    assert [(event["action"], event["contract"], event["attempt"],
             event["budget"]["elapsed_seconds"], event["budget"]["seconds_remaining"])
            for event in events] == [
                ("model_started", "research", 1, 0.0, 300.0),
                ("model_returned", "research", 1, 1.25, 298.75),
                ("model_started", "answer", 2, 1.25, 298.75),
                ("model_returned", "answer", 2, 3.5, 296.5),
            ]


def test_model_failure_trace_has_later_time_and_only_safe_code():
    now = [0.0]

    def failed(_material):
        now[0] = 2.5
        return ModelError("model_response_incomplete_content_filter")

    with pytest.raises(RunError) as caught:
        run("Value?", model=Script(failed), search=search, fetch=no_fetch,
            clock=lambda: now[0])
    events = [event for event in caught.value.trace if event["action"].startswith("model_")]
    assert [(event["action"], event["budget"]["elapsed_seconds"]) for event in events] == [
        ("model_started", 0.0), ("model_failed", 2.5),
    ]
    assert events[-1]["code"] == "model_response_incomplete_content_filter"
    assert events[-1]["ended_elapsed_seconds"] == 2.5
    assert events[-1]["duration_seconds"] == 2.5
    assert all(value is None for value in events[-1]["usage"].values())
    assert set(events[-1]) == {"stage", "action", "contract", "attempt", "code", "budget",
                               "ended_elapsed_seconds", "duration_seconds", "usage"}


def test_terminal_answer_reserve_preserves_a_source_first_answer_window():
    now = [0.0]

    def delayed(q):
        now[0] = 120
        return search(q)

    model = Script(decision(), answer())
    result = run("Value?", model=model, search=delayed, fetch=no_fetch, clock=lambda: now[0])
    assert [call[0] for call in model.calls] == ["research", "answer"]
    assert result.stop_reason == "research_bound"
    assert any(event["action"] == "research_bound" and event["code"] == "answer_deadline_reserve"
               for event in result.trace)
    assert next(call[2] for call in model.calls if call[0] == "answer")["evidence"][0]["id"] == "E1"


def test_individual_model_call_stays_capped_at_120_seconds():
    now = [0.0]

    class TimedModel(OpenAIModel):
        def __init__(self):
            super().__init__()
            self.timeouts = []

        def __call__(self, stage, prompt, material, schema):
            self.timeouts.append(self.timeout_seconds)
            if stage == "research":
                now[0] = 200
                return json.dumps(decision("answer"))
            return json.dumps(answer("No source establishes this.", "unable"))

    model = TimedModel()
    run("Value?", model=model, search=search, fetch=no_fetch, clock=lambda: now[0])
    assert model.timeouts == [120, 100]


def test_pending_new_material_at_deadline_preserves_partial_with_bound_disclosure():
    now = [0.0]

    def staged_search(query):
        if query == "new material":
            now[0] = 301
            return [DiscoveryCandidate("New fact", "https://example.org/new", "A new fact.",
                                       context_kind="provider_highlights")]
        return search(query)

    model = Script(
        decision(),
        decision("answer", ["E1"]),
        answer("A provisional fragment. [E1]", "partial", "What changed?"),
        decision(requests=[request(query="new material")], refs=["E1"]),
    )
    result = run("Value?", model=model, search=staged_search, fetch=no_fetch,
                 clock=lambda: now[0])
    assert [call[0] for call in model.calls] == ["research", "research", "answer", "research"]
    assert result.posture == "partial"
    assert result.answer == "A provisional fragment. [1]"
    assert result.stop_reason == "research_bound"
    assert [item.id for item in result.selected_evidence] == ["E1"]
    assert any(event["action"] == "answer_prior_partial_preserved" for event in result.trace)
    assert not any(event["action"] == "answer_committed_no_progress" for event in result.trace)
    assert {item.id for item in result.evidence} == {"E1", "E2"}


def test_unknown_final_citation_fails_without_a_hidden_polisher():
    model = Script(decision(), decision("answer", ["E1"]), answer("Seven. [E99]"))
    with pytest.raises(RunError):
        run("Value?", model=model, search=search, fetch=no_fetch)
    assert len(model.calls) == 3


def test_followup_does_not_inherit_semantic_history_or_generated_support():
    model = Script(decision("answer"), answer("The retained material does not establish this.", "unable"))
    result = run("What about that?", model=model, search=search, fetch=no_fetch,
                 context={"conversation_context": [{"question": "Earlier?", "answer": "A referent"}],
                          "semantic_history": [{"analysis": "FAKE FACT"}]})
    assert all("FAKE FACT" not in json.dumps(call[2]) for call in model.calls)
    assert model.calls[-1][2]["conversation_context"][0]["answer"] == "A referent"
    assert result.posture == "unable"


def test_pending_requested_reading_precedes_new_external_work():
    # Three independent returned materials exceed attention. The next request is
    # deferred mechanically until the exact remaining text has been supplied.
    def large_search(q):
        return [DiscoveryCandidate(str(i), f"https://example.org/{i}", str(i) * 40000,
                                   context_kind="provider_highlights") for i in range(3)]
    model = Script(decision(), decision(), decision(), decision("answer", ["E3"]),
                   answer("A selected observation. [E3]"))
    result = run("Inspect", model=model, search=large_search, fetch=no_fetch,
                 limits=RunLimits(attention_characters=65536))
    # The packet is intentionally one material wide; all three are delivered.
    assert [call[2]["evidence"][0]["id"] for call in model.calls[1:4]] == ["E1", "E2", "E3"]
    assert any(e["action"] == "reading_pending" for e in result.trace)
    assert result.trace[-1]["budget"]["external_attempts"] == 1
