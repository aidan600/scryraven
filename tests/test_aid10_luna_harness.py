"""Scripted receipts and review bookkeeping for the opt-in Luna experiment."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import requests

from core.exa_transport import DiscoveryCandidate
from scripts import aid10_luna as harness
from scripts import aid10_luna_review as review
from scryraven import research
from scryraven.model import built_in_model_config

QUESTION = "What is the published limit and when does it apply?"
SOURCE = "The published limit is seven units for the trial period."


def final(value):
    return [{"type": "message", "role": "assistant", "phase": "final_answer",
             "content": [{"type": "output_text", "text": json.dumps(value)}]}]


def investigate(action, *, requests=(), refs=()):
    return final({"action": action, "requests": list(requests), "briefing": "Trial period only.",
                  "retain": list(refs), "evidence_refs": list(refs)})


def answer(posture):
    return final({"answer": "Seven units for the trial period. [E1]", "support_basis": "evidence",
                  "posture": posture, "missing_information": None if posture == "supported" else "Later limit"})


def search(*_args, **_kwargs):
    return [DiscoveryCandidate("Public guideline", "https://example.org/guideline", SOURCE,
                               context_kind="provider_highlights")]


def prohibited(*_args, **_kwargs):
    pytest.fail("unexpected external provider dispatch")


def scripted_turn(monkeypatch, phase, arm, *, result_posture="supported", receipt_problem=None):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    sent = []
    outputs = iter([
        investigate("research", requests=[{"kind": "search", "query": QUESTION, "objective": "Find originals."}]),
        investigate("return", refs=["E1"]),
        [{"type": "function_call", "name": "research", "call_id": "check",
          "arguments": '{"need":"Check when the published limits apply."}'}],
        investigate("return", refs=["E1"]),
        answer(result_posture),
    ])

    def post(_url, **kwargs):
        payload = kwargs["json"]
        sent.append(payload)
        output = next(outputs)
        if len(sent) == 4 and receipt_problem == "timeout":
            raise requests.Timeout()
        data = {"status": "completed", "model": payload["model"],
                "service_tier": "default", "output": output}
        if len(sent) == 5:
            if receipt_problem == "model":
                data["model"] = "gpt-6.2-terra"
            elif receipt_problem == "tier":
                data["service_tier"] = "fast"
            elif receipt_problem == "unreported":
                del data["service_tier"]
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: data)

    result = harness.run_case(QUESTION, phase, arm, post=post, search=search, fetch=prohibited,
                              lexical_search=prohibited, scholarly_search=prohibited,
                              scholarly_fetch=prohibited, venue_lookup=prohibited)
    return result, sent


@pytest.mark.parametrize("arm", harness.ARMS)
@pytest.mark.parametrize("phase,answer_model", [
    ("diagnostic-development", "gpt-6.2-sol"), ("luna-reserved", "gpt-6-luna"),
])
def test_native_session_preserves_role_pins_and_delivers_exact_citations(monkeypatch, phase, arm, answer_model):
    original_prompts = harness.prompts(phase, "control")
    defaults = built_in_model_config()
    result, sent = scripted_turn(monkeypatch, phase, arm)
    assert [item["model"] for item in sent] == [
        "gpt-6-luna", "gpt-6-luna", answer_model, "gpt-6-luna", answer_model,
    ]
    assert [item["reasoning"]["effort"] for item in sent] == ["high", "high", "medium", "high", "medium"]
    assert {item["service_tier"] for item in sent} == {"default"}
    assert result["gate_issues"] == []
    assert result["outcome"]["citations"][0]["materials"][0]["content"] == SOURCE
    assert result["outcome"]["answer"].endswith("[1]")
    names = ("RESEARCH_PROMPT", "RESEARCH_PROMPT", "ANSWER_PROMPT", "DELEGATED_RESEARCH_PROMPT", "ANSWER_PROMPT")
    for payload, name in zip(sent, names, strict=True):
        developer = next(item for item in payload["input"] if item.get("role") == "developer")
        guidance = ""
        if arm == "hardened":
            if name != "ANSWER_PROMPT":
                guidance = harness.RESEARCH_GUIDANCE
            elif phase == "luna-reserved":
                guidance = harness.ANSWER_GUIDANCE
        prompt_body = original_prompts[name] + guidance
        assert developer["content"][0]["text"].startswith(prompt_body)
        suffix = developer["content"][0]["text"][len(prompt_body):]
        assert "matching the response schema" in suffix
        assert harness.RESEARCH_GUIDANCE not in suffix and harness.ANSWER_GUIDANCE not in suffix
    assert any(row["action"] == "research_tool_result" for row in result["events"])
    assert any(row["action"] == "exposure" and row["contract"] == "answer"
               and row["evidence"][0]["content"] == SOURCE for row in result["events"])
    assert {name: getattr(research, name) for name in original_prompts} == original_prompts
    assert built_in_model_config() == defaults


@pytest.mark.parametrize("posture,problem,gate,stop", [
    ("partial", None, "partial", False),
    ("supported", "model", "returned_model_mismatch", True),
    ("supported", "tier", "standard_tier_mismatch", True),
    ("supported", "unreported", "missing_model_or_tier_receipt", True),
    ("supported", "timeout", "timeout", False),
])
def test_partial_timeout_and_bad_receipts_cannot_pass(monkeypatch, posture, problem, gate, stop):
    result, _ = scripted_turn(monkeypatch, "luna-reserved", "hardened",
                              result_posture=posture, receipt_problem=problem)
    assert gate in result["gate_issues"]
    assert result["configuration_stop"] is stop


def test_review_retains_interrupted_slot_and_requires_adjudication(monkeypatch, tmp_path):
    case = {"id": "fixture", "category": "citation", "question": QUESTION,
            "obligation": "Keep the trial qualification.", "primary_targets": "Public guideline"}
    phase = "luna-reserved"
    run, _ = scripted_turn(monkeypatch, phase, "control")
    header = {"kind": "block_started", "case_ids": ["fixture"], "phase": phase, "mode": "live_standard",
              "baseline": harness.BASELINE, "corpus_sha256": harness.CASE_DIGEST, "revision": "fixture-revision"}
    slot = {"case_id": "fixture", "phase": phase, "arm": "control"}
    started = {"kind": "turn_started", **slot}
    completed = {"kind": "turn_finished", **slot, **run}
    revision, turns = review.collect([case], phase, [[header, started, completed]])
    assert revision == "fixture-revision"
    log = tmp_path / "interrupted.jsonl"
    log.write_text(json.dumps(header) + "\n" + json.dumps(started) + '\n{"kind":"turn_finished"')
    _, interrupted = review.collect([case], phase, [review.read_block(log)])
    assert interrupted == {("fixture", "control"): None}
    with pytest.raises(ValueError, match="duplicate"):
        review.collect([case], phase, [[header, started, completed, started]])
    with pytest.raises(ValueError, match="provenance"):
        review.collect([case], phase, [[header, started, {**completed, "prompt_hashes": {}}]])
    packet, key = review.blind([case], turns)
    row, = packet
    assert set(row) == {"review_id", "question", "obligation", "primary_targets",
                        "answer", "posture", "citations", "citation_uses"}
    identity = row["review_id"]

    def verdict(name, defects):
        return {"reviewer": name, "verdicts": {identity: {
            "acceptable": not defects, "defects": defects, "rationale": "Synthetic verdict."
        }}}

    reviews = [verdict("one", []), verdict("two", ["unsupported_claim"])]
    with pytest.raises(ValueError, match="third blinded verdict"):
        review.score(key, reviews, {})
    adjudicated = review.score(key, [*reviews, verdict("three", [])], {})
    assert adjudicated["overall"]["arms"]["control"]["accepted"] == 1
    assert adjudicated["overall"]["arms"]["hardened"]["execution_issues"] == {"interrupted_pair": 1}
    assert adjudicated["overall"]["regressed"] == ["fixture"]
    assert adjudicated["disputed_outcomes"] == 1
    rejected = review.score(key, [*reviews, verdict("three", ["unsupported_claim"])], {})
    assert rejected["overall"]["arms"]["control"]["accepted"] == 0
    assert rejected["overall"]["arms"]["control"]["defects"] == {"unsupported_claim": 1}
    assert review.interval(36, 40) == [0.769482, 0.96042]


def test_live_command_requires_explicit_authorization_before_loading_cases():
    with pytest.raises(SystemExit) as exit_info:
        harness.main(["--phase", "luna-reserved", "--manifest", "unread.json", "--count", "1"])
    assert exit_info.value.code == 2
