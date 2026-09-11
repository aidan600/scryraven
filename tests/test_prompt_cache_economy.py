"""Transport economics without live calls, semantic compression or fake cache hits."""

import json
from copy import deepcopy
from dataclasses import asdict

import pytest
import requests
from test_model_transport import Response
from test_research_session import (
    ANSWER_A,
    BODY,
    FACT_A,
    FACT_B,
    FACT_C,
    Q1,
    Q2,
    Q3,
    URL_A,
    URL_B,
    Provider,
    assess,
    candidate,
)
from test_source_acquisition import use
from test_walking_skeleton import author, orient, search_for

from scryraven import research
from scryraven.model import ModelConfig, ModelRole, OpenAIModel
from scryraven.session import ResearchSession

SUFFIX = "\nReturn only JSON matching the response schema, with no Markdown or commentary."
FAMILIES = [
    ("research", "orientation", research.ORIENTATION_PROMPT, research.SESSION_CONTEXT_PROMPT, research.Orientation),
    ("research", "navigation", research.RESEARCH_PROMPT, research.SESSION_RESEARCH_PROMPT, research.ResearchAction),
    ("research", "relevance", research.RELEVANCE_PROMPT, research.SESSION_CONTEXT_PROMPT, research.RelevantEvidence),
    ("analyst", "analyst", research.ANALYST_PROMPT, research.SESSION_CONTEXT_PROMPT, research.Analysis),
    ("author", "author", research.AUTHOR_PROMPT, research.SESSION_AUTHOR_PROMPT, research.Draft),
]


def response(reply='{"answer":"ok"}', **extra):
    return Response({"status": "completed", "output": [
        {"type": "message", "phase": "final_answer", "content": [{"type": "output_text", "text": reply}]},
    ], **extra})


def material_of(payload):
    return json.loads("".join(block["text"] for block in payload["input"][1]["content"]))


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls, usage = [], []

    def post(_url, **kwargs):
        calls.append(kwargs["json"])
        return response()

    return OpenAIModel(ModelConfig(), post=post, usage_observer=usage.append), calls, usage


def rich_material():
    return {
        "current_date": "2026-09-11", "phase": "navigation", "question": Q2,
        "conversation_context": [{"question": Q1, "answer": ANSWER_A}],
        "semantic_history": [{"question": Q1, "analysis": assess(Q1, FACT_A, "E1")[1],
                              "posture": "supported", "stop_reason": "supported"}],
        "need": "Resolve the follow-up", "answer_needs": orient(Q2)[1]["answer_needs"],
        "candidates": [{"id": "C1", "url": URL_A, "context": BODY + '\nUnicode ± – \\ " [E1]'}],
        "evidence": [{"id": "E1", "content": BODY}], "new_evidence": [{"id": "E2", "content": FACT_C}],
        "retained_sources": [{"id": "E1", "candidate_refs": ["C1"]}],
        "previous_analysis": None, "retrieval_allowance": {"remaining": 2}, "attempts": [],
        "output_correction": {"rejected_response": '{"answer":'},
        "selection_correction": {"cause": "unknown_alias"},
        "unrecognized_future_field": {"qualification": "only while idle", "order": [3, 1, 2]},
    }


@pytest.mark.parametrize("stage,phase,prompt,session_prompt,shape", FAMILIES)
@pytest.mark.parametrize("session", [False, True])
def test_lossless_layout_unchanged_instructions_schema_defaults_and_stateless_contract(
    transport, stage, phase, prompt, session_prompt, shape, session,
):
    model, calls, usage = transport
    material = rich_material()
    material["phase"] = phase
    if not session:
        material.pop("semantic_history")
        material.pop("conversation_context")
    original = deepcopy(material)
    instructions = prompt + (session_prompt if session else "")
    schema = shape.model_json_schema()
    assert model(stage, instructions, material, schema) == '{"answer":"ok"}'
    payload = calls[0]
    assert material == original == material_of(payload)
    assert payload["input"][0] == {"role": "developer", "content": [{
        "type": "input_text", "text": instructions + SUFFIX,
        "prompt_cache_breakpoint": {"mode": "explicit"},
    }]}
    assert payload["input"][1]["role"] == "user"
    assert payload["model"] == "gpt-5.6-luna"
    assert payload["reasoning"] == {"effort": "medium"}
    assert payload["text"] == {"format": {"type": "json_schema", "name": stage, "strict": True, "schema": schema}}
    assert payload["store"] is False and payload["max_output_tokens"] == 12000
    assert not {"previous_response_id", "conversation", "prompt_cache_retention", "tools"} & payload.keys()
    # Current GPT-5.6 contract: explicit markers on input_text, explicit-only
    # mode suppresses automatic end-of-input writes; 30m is the supported TTL.
    assert payload["prompt_cache_options"] == {"mode": "explicit", "ttl": "30m"}
    markers = [block for message in payload["input"] for block in message["content"]
               if "prompt_cache_breakpoint" in block]
    assert 1 <= len(markers) <= 4
    assert all(block["prompt_cache_breakpoint"] == {"mode": "explicit"} for block in markers)
    assert len(markers) == len(usage[0].breakpoints)
    assert not any(key in json.dumps(asdict(usage[0])) for key in (BODY, ANSWER_A, "rejected_response"))


def test_navigation_prefix_stable_and_volatile_material_after_last_breakpoint(transport):
    model, calls, _ = transport
    original = rich_material()
    changed = deepcopy(original)
    for field in ("candidates", "evidence", "new_evidence", "previous_analysis", "retained_sources",
                  "attempts", "retrieval_allowance", "output_correction", "selection_correction"):
        changed[field] = {"changed": "volatile"}
    for material in (original, changed):
        model("research", research.RESEARCH_PROMPT, material, research.ResearchAction.model_json_schema())
    before, after = [call["input"][1]["content"] for call in calls]
    assert before[:-1] == after[:-1]
    assert before[-1] != after[-1]
    assert before[-2]["prompt_cache_breakpoint"] == {"mode": "explicit"}
    assert "prompt_cache_breakpoint" not in before[-1]
    prefix = "".join(block["text"] for block in before[:-1]).encode("utf-8")
    assert prefix == "".join(block["text"] for block in after[:-1]).encode("utf-8")
    assert b'"candidates"' not in prefix and b'"output_correction"' not in prefix
    tail = before[-1]["text"]
    assert tail.index('"candidates"') < tail.index('"selection_correction"') < tail.index('"output_correction"')
    assert calls[0]["prompt_cache_key"] == calls[1]["prompt_cache_key"]


@pytest.mark.parametrize("stage,history_field", [("analyst", "semantic_history"), ("author", "conversation_context")])
def test_history_append_keeps_exact_previous_endpoint_without_truncating_history(transport, stage, history_field):
    model, calls, _ = transport
    history = []
    for turn in range(1, 7):
        history.append({"question": f"Question {turn}", "answer": "Complete unchanged history" * turn})
        material = {history_field: deepcopy(history), "question": f"New question {turn}"}
        model(stage, "instructions", material, {})
        assert material_of(calls[-1]) == material
        assert len([b for m in calls[-1]["input"] for b in m["content"] if "prompt_cache_breakpoint" in b]) <= 4
        if len(calls) > 1:
            old = calls[-2]["input"][1]["content"][:-1]
            new = calls[-1]["input"][1]["content"]
            # Marker metadata may retire, but every byte and content boundary
            # remains, and the preceding turn's final endpoint is still marked.
            assert [b["text"] for b in old] == [b["text"] for b in new[:len(old)]]
            assert "prompt_cache_breakpoint" in new[len(old) - 1]


def test_family_separates_contracts_and_namespace_but_not_questions_or_corrections(transport):
    model, calls, _ = transport
    for stage, phase, prompt, session_prompt, shape in FAMILIES:
        for instructions in (prompt, prompt + session_prompt):
            model(stage, instructions, {"phase": phase, "question": Q1}, shape.model_json_schema())
    assert len({call["prompt_cache_key"] for call in calls}) == 10
    for instructions, schema in [("prompt", {}), ("changed prompt", {}), ("prompt", {"type": "object"})]:
        model("author", instructions, {"question": Q1}, schema)
    assert len({call["prompt_cache_key"] for call in calls[-3:]}) == 3
    for material in ({"question": Q1}, {"question": Q2}, {"question": Q2, "output_correction": {"issues": []}}):
        model("author", "prompt", material, {})
    assert len({call["prompt_cache_key"] for call in calls[-3:]}) == 1
    base = calls[-1]["prompt_cache_key"]
    for kwargs in ({"cache_namespace": "cold-validation-2"},
                   {"config": ModelConfig(fast=ModelRole("gpt-5.6-sol", "medium"))},
                   {"config": ModelConfig(fast=ModelRole("gpt-5.6-luna", "high"))}):
        other = OpenAIModel(post=model.post, **kwargs)
        other("author", "prompt", {"question": Q1}, {})
        assert calls[-1]["prompt_cache_key"] != base
    assert all(len(call["prompt_cache_key"]) <= 64 for call in calls)


@pytest.mark.parametrize("usage,expected", [
    ({"input_tokens": 12000, "input_tokens_details": {"cached_tokens": 8000, "cache_write_tokens": 2000},
      "output_tokens": 500, "output_tokens_details": {"reasoning_tokens": 90}}, (12000, 8000, 2000, 2000, 500, 90)),
    ({"input_tokens": 20, "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
      "output_tokens": 3, "output_tokens_details": {"reasoning_tokens": 0}}, (20, 0, 0, 20, 3, 0)),
    ({"input_tokens": 20, "input_tokens_details": {"cached_tokens": 10}}, (20, 10, None, None, None, None)),
    ({"input_tokens": 20, "input_tokens_details": {"cached_tokens": 15, "cache_write_tokens": 10}},
     (20, 15, 10, None, None, None)),
    ({"input_tokens": True, "input_tokens_details": {"cached_tokens": "5", "cache_write_tokens": -1},
      "output_tokens": 4.2, "output_tokens_details": []}, (None,) * 6),
    ({}, (None,) * 6), (None, (None,) * 6), ("malformed", (None,) * 6),
])
def test_usage_is_optional_safe_and_does_not_invent_missing_classes(transport, usage, expected):
    model, _, records = transport
    model.post = lambda *a, **k: response(usage=usage)
    assert model("author", "private prompt", {}, {}) == '{"answer":"ok"}'
    record = records[0]
    assert (record.input_tokens, record.cached_input_tokens, record.cache_write_tokens,
            record.ordinary_uncached_tokens, record.output_tokens, record.reasoning_tokens) == expected


def test_http_failure_counted_and_observer_failure_cannot_change_model_execution(transport):
    model, _, records = transport

    def failed(*args, **kwargs):
        raise requests.ConnectionError("private transport detail")

    model.post = failed
    with pytest.raises(research.ModelError, match="^model_transport_failed$"):
        model("research", "prompt", {}, {})
    assert len(records) == 1 and records[0].input_tokens is None
    model.post = lambda *a, **k: response()
    model.usage_observer = failed
    assert model("author", "prompt", {}, {}) == '{"answer":"ok"}'


@pytest.mark.parametrize("session_mode", [False, True])
def test_real_model_transport_through_ordinary_run_and_session_with_fake_responses(transport, session_mode):
    model, calls, records = transport
    opening = [orient(Q1), search_for(Q1), use("C1"), assess(Q1, FACT_A, "E1"), author(ANSWER_A + " [E1]")]
    replies = opening + ([orient(Q2), use("C1"), assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]"),
                          orient(Q3), search_for(Q3), use("C2"), assess(Q3, FACT_C, "E2"), author(FACT_C + " [E2]")]
                         if session_mode else [])
    # Exercise the actual Structured Outputs retry, retaining the same prefix.
    replies.insert(0, ("research", '{"answer_needs":'))

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        stage, reply = replies.pop(0)
        assert kwargs["json"]["text"]["format"]["name"] == stage
        return response(reply if isinstance(reply, str) else json.dumps(reply), usage={
            "input_tokens": 100, "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens": 20, "output_tokens_details": {"reasoning_tokens": 5},
        })

    model.post = post
    provider = Provider([candidate(context=BODY, highlights=True)], [candidate(URL_B, FACT_C, highlights=True)])
    if session_mode:
        session = ResearchSession(model=model, search=provider.search, fetch=provider.fetch)
        first, second, third = [session.ask(question) for question in (Q1, Q2, Q3)]
        assert second.evidence == first.evidence
        assert second.citations[0].source_id == "E1"
        assert third.citations[0].source_id == "E2" and third.selected_evidence[0].content == FACT_C
        assert session.source_ids == ("E1", "E2") and len(provider.searches) == 2
        later_analyst = [material_of(call) for call in calls if call["text"]["format"]["name"] == "analyst"][1]
        assert later_analyst["conversation_context"] == [{"question": Q1, "answer": first.answer}]
        assert later_analyst["evidence"][0]["content"] == BODY
        assert later_analyst["previous_analysis"] is None
    else:
        first = research.run(Q1, model=model, search=provider.search, fetch=provider.fetch)
        assert len(provider.searches) == 1
    assert first.answer == ANSWER_A + " [1]" and first.citations[0].url == URL_A
    assert not replies and not provider.fetches
    assert "output_correction" not in material_of(calls[0])
    assert "output_correction" in material_of(calls[1])
    assert calls[0]["prompt_cache_key"] == calls[1]["prompt_cache_key"]
    assert calls[0]["input"][0] == calls[1]["input"][0]
    assert len(records) == len(calls) == (15 if session_mode else 6)
    assert sum(record.ordinary_uncached_tokens for record in records) == 100 * len(calls)
