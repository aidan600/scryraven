"""Synthetic contracts test mechanics only; they cannot establish research skill."""
import json

import pytest

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.research import RunError
from scryraven.sources import Evidence
from scryraven.v2 import AnswerDecision, V2Limits, run


def request(kind="search", query="public fact", target="", mode="auto", focus=""):
    return dict(kind=kind, query=query, target=target, mode=mode, focus=focus,
                scope=[], start_char=None, end_char=None)


def decision(action="research", refs=(), requests=None, interpretation="Find the requested fact"):
    return dict(understanding=dict(interpretation=interpretation, observed=[], inferred=[],
                                  still_needed=[] if action == "answer" else ["What is the fact?"],
                                  last_route_result=""), action=action, purpose="Resolve the fact",
                answer_scope="requested" if action == "answer" else None, scope_limit=None,
                requests=([request()] if requests is None and action == "research" else requests or []),
                retain=list(refs), answer_evidence_refs=list(refs) if action == "answer" else [])


def answer(text="The stated value is seven. [E1]", posture="supported", missing=None):
    return dict(source_readings=[], answer=text, posture=posture, missing_information=missing)


class Script:
    def __init__(self, *outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def __call__(self, stage, prompt, material, schema):
        self.calls.append((stage, prompt, material, schema))
        value = next(self.outputs)
        if callable(value):
            value = value(material)
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
    packet = model.calls[-1][2]
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
                   decision("answer", ["E2"]), answer("Seven under the stated condition. [E2]"))
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
        {"stage": "v2", "action": "answer_committed_no_progress", "posture": "partial",
         "missing_information": "What condition applies?", "prior_selected_refs": ["E1"],
         "selected_refs": ["E1"]},
    ]


def test_partial_answer_at_a_semantic_bound_is_not_promoted_to_support():
    model = Script(decision(), decision("answer", ["E1"]),
                   answer("A supported fragment. [E1]", "partial", "What condition applies?"),
                   decision(refs=["E1"]))
    result = run("What is the value?", model=model, search=search, fetch=no_fetch,
                 limits=V2Limits(semantic_attempts=5, external_attempts=1))
    assert [call[0] for call in model.calls] == ["research", "research", "answer", "research"]
    assert result.posture == "partial"
    assert result.stop_reason == "not_established"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4


def test_malformed_call_consumes_attempt_and_final_reserve_is_source_first():
    model = Script("invalid", decision(), answer())
    result = run("Value?", model=model, search=search, fetch=no_fetch, limits=V2Limits(semantic_attempts=3))
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert result.stop_reason == "research_bound"
    assert result.trace[-1]["budget"]["semantic_attempts"] == 3
    assert model.calls[-1][2]["evidence"][0]["id"] == "E1"


def test_external_budget_blocks_second_independent_request_without_hiding_first_material():
    model = Script(decision(requests=[request(query="one"), request(query="two")]),
                   decision("answer", ["E1"]), answer())
    calls = []
    result = run("Value?", model=model, search=lambda q: calls.append(q) or search(q), fetch=no_fetch,
                 limits=V2Limits(external_attempts=1))
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
                 limits=V2Limits(seconds=5), clock=lambda: now[0])
    assert len(model.calls) == 1
    assert result.posture == "unable"
    assert result.citations == ()
    assert len(result.evidence) == 1
    assert not any(e["action"] == "model_started" and e["exposed"] for e in result.trace)


def test_terminal_answer_reserve_preserves_a_source_first_answer_window():
    now = [0.0]

    def delayed(q):
        now[0] = 66
        return search(q)

    model = Script(decision(), answer())
    result = run("Value?", model=model, search=delayed, fetch=no_fetch, clock=lambda: now[0])
    assert [call[0] for call in model.calls] == ["research", "answer"]
    assert result.stop_reason == "research_bound"
    assert any(event["action"] == "research_bound" and event["code"] == "answer_deadline_reserve"
               for event in result.trace)
    assert model.calls[-1][2]["evidence"][0]["id"] == "E1"


def test_pending_new_material_at_deadline_does_not_commit_a_stale_partial_answer():
    now = [0.0]

    def staged_search(query):
        if query == "new material":
            now[0] = 121
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
    assert result.posture == "unable"
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
    model = Script(decision(), decision(), decision(), decision("answer", ["E3"]), answer("A selected observation. [E3]"))
    result = run("Inspect", model=model, search=large_search, fetch=no_fetch,
                 limits=V2Limits(attention_characters=65536))
    # The packet is intentionally one material wide; all three are delivered.
    assert [call[2]["evidence"][0]["id"] for call in model.calls[1:4]] == ["E1", "E2", "E3"]
    assert any(e["action"] == "reading_pending" for e in result.trace)
    assert result.trace[-1]["budget"]["external_attempts"] == 1


def test_answer_reading_is_exact_source_text_and_invalid_reading_uses_same_budget():
    invalid = answer()
    invalid["source_readings"] = [{"evidence_ref": "E1", "passages": ["The invented value is eight."]}]
    valid = answer()
    valid["source_readings"] = [{"evidence_ref": "E1", "passages": ["The stated\nvalue is seven."]}]
    model = Script(decision(), decision("answer", ["E1"]), invalid, valid)
    events = []
    result = run("Value?", model=model, search=search, fetch=no_fetch, observe=events.append)
    assert [call[0] for call in model.calls] == ["research", "research", "answer", "answer"]
    assert result.trace[-1]["budget"]["semantic_attempts"] == 4
    assert model.calls[-1][2]["output_correction"]["code"] == "reading_passage_not_in_source"
    assert "invented value" not in json.dumps(model.calls[-1][2])
    readings = [event for event in events if event["action"] == "answer_reading"]
    assert readings[0]["readings"][0]["passage"] == "The stated value is seven."
    rejected = [event for event in events if event["action"] == "answer_reading_rejected"]
    assert rejected == [{"stage": "v2", "action": "answer_reading_rejected", "contract": "answer",
                         "code": "reading_passage_not_in_source", "evidence_ref": "E1",
                         "passage": "The invented value is eight.", "reading_index": 0,
                         "passage_index": 0}]
    assert not any(event["action"] == "answer_reading_rejected" for event in result.trace)
    trace_answer = next(event for event in result.trace if event["action"] == "answer_decision")
    assert "source_readings" not in trace_answer["decision"]
    assert trace_answer["source_reading_refs"] == ["E1"]


def test_reading_cannot_borrow_exact_text_from_unsupplied_material():
    invalid = answer()
    invalid["source_readings"] = [{"evidence_ref": "E2", "passages": ["The stated value is seven."]}]
    model = Script(decision(), decision("answer", ["E1"]), invalid, answer())
    result = run("Value?", model=model, search=search, fetch=no_fetch)
    assert any(event.get("code") == "unselected_reading_reference" for event in result.trace)


def test_answer_reading_accepts_discontinuous_literal_passages_from_one_material():
    valid = answer("First exact passage with the qualification. [E1]")
    valid["source_readings"] = [{"evidence_ref": "E1", "passages": [
        "First exact passage.", "A material\nqualification applies.",
    ]}]
    model = Script(decision(), decision("answer", ["E1"]), valid)
    events = []
    result = run("What is the qualified fact?", model=model,
                 search=lambda query: multi_search(query)[:1], fetch=no_fetch, observe=events.append)
    reading = next(event for event in events if event["action"] == "answer_reading")
    assert [item["passage"] for item in reading["readings"]] == [
        "First exact passage.", "A material qualification applies.",
    ]
    trace_answer = next(event for event in result.trace if event["action"] == "answer_decision")
    assert trace_answer["source_reading_refs"] == ["E1"]
    assert result.selected_evidence == result.citations[0].materials


def test_answer_readings_accept_multiple_materials_without_duplicate_source_identity():
    valid = answer("First qualified fact [E1]. Second qualified fact [E2].")
    valid["source_readings"] = [
        {"evidence_ref": "E1", "passages": [
            "First exact passage.", "A material qualification applies.", "First exact passage.",
        ]},
        {"evidence_ref": "E2", "passages": [
            "Second source fact.", "A second qualification applies.",
        ]},
    ]
    model = Script(decision(), decision("answer", ["E1", "E2"]), valid)
    events = []
    result = run("What are the qualified facts?", model=model, search=multi_search, fetch=no_fetch,
                 observe=events.append)
    reading = next(event for event in events if event["action"] == "answer_reading")
    assert [item["evidence_ref"] for item in reading["readings"]] == ["E1", "E1", "E2", "E2"]
    trace_answer = next(event for event in result.trace if event["action"] == "answer_decision")
    assert trace_answer["source_reading_refs"] == ["E1", "E2"]
    assert [citation.materials[0].id for citation in result.citations] == ["E1", "E2"]
    assert [item.id for item in result.selected_evidence] == ["E1", "E2"]


def test_answer_reading_schema_replaces_the_obsolete_single_passage_shape():
    with pytest.raises(ValueError):
        AnswerDecision.model_validate({
            "source_readings": [{"evidence_ref": "E1", "passage": "Old shape."}],
            "posture": "unable", "answer": "Unable.", "missing_information": None,
        })
    with pytest.raises(ValueError):
        AnswerDecision.model_validate({
            "source_readings": [{"evidence_ref": "E1", "passages": []}],
            "posture": "unable", "answer": "Unable.", "missing_information": None,
        })


@pytest.mark.parametrize(("invalid_reading", "code", "passage_index"), [
    ({"evidence_ref": "E2", "passages": ["First exact passage.", "First paraphrased value."]},
     "reading_passage_not_in_source", 1),
    ({"evidence_ref": "E2", "passages": ["First exact passage!"]},
     "reading_passage_not_in_source", 0),
    ({"evidence_ref": "E2", "passages": ["Second source fact."]},
     "reading_passage_not_in_source", 0),
    ({"evidence_ref": "E2", "passages": ["Retained but unsupplied text."]},
     "reading_passage_not_in_source", 0),
    ({"evidence_ref": "E2", "passages": ["Fabricated text."]},
     "reading_passage_not_in_source", 0),
    ({"evidence_ref": "E2", "passages": ["First exact passage. ... A material qualification applies."]},
     "reading_passage_not_in_source", 0),
    ({"evidence_ref": "E99", "passages": ["First exact passage."]}, "unselected_reading_reference", 0),
])
def test_answer_reading_rejects_nonliteral_or_wrong_custody_passages(invalid_reading, code, passage_index):
    invalid = answer()
    invalid["source_readings"] = [invalid_reading]
    model = Script(decision(), decision("answer", ["E2", "E3"]), invalid,
                   answer("First exact passage. [E2]"))
    retained = Evidence("E1", "https://example.org/retained", "Retained", "Retained but unsupplied text.")
    events = []
    result = run("What are the facts?", model=model, search=multi_search, fetch=no_fetch,
                 retained_acquisitions=(retained,), observe=events.append)
    assert result.posture == "supported"
    assert model.calls[-1][2]["output_correction"]["code"] == code
    assert all(item["id"] != "E1" for item in model.calls[-1][2]["evidence"])
    rejected = [event for event in events if event["action"] == "answer_reading_rejected"]
    assert rejected[0]["code"] == code
    assert rejected[0]["evidence_ref"] == invalid_reading["evidence_ref"]
    assert rejected[0]["passage"] == invalid_reading["passages"][passage_index]
    assert rejected[0]["passage_index"] == passage_index
