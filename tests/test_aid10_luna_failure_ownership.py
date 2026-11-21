"""Development questions with invented source packets and scripted Responses."""
from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from test_aid10_luna_harness import final, prohibited

from core.exa_transport import DiscoveryCandidate
from scripts import aid10_luna as harness
from scripts import aid10_luna_review as review

SCOPE = "These are typical distances under dry-road conditions."
DISTANCES = "50 mph: thinking 15 m; braking 38 m; total 53 m."
TABLE = f"{SCOPE}\n{DISTANCES}"
VALUES_REF = f"E1@{len(SCOPE) + 1}:{len(TABLE)}"
SCOPE_REF = f"E1@0:{len(SCOPE)}"

PERMISSION = "This example license allows distributing and selling modified copies."
NOTICE = "Copies or substantial portions must retain the copyright and permission notices."
LICENSE = f"{PERMISSION}\n{NOTICE}"


@pytest.fixture
def development_questions():
    manifest = os.environ.get("SCRYRAVEN_AID10_DEVELOPMENT_MANIFEST")
    if manifest:
        cases = harness.phase_cases(harness.load_cases(Path(manifest)), "diagnostic-development")
        return {case["id"]: case["question"] for case in cases}
    return {
        "D03": "Does this example license allow sales of modified copies, and which notices are required?",
        "D04": "From the dry-road stopping table, give the typical thinking and braking distances at 50 mph.",
    }


def research_decision(action, *, requests=(), refs=(), briefing=None):
    return final({"action": action, "briefing": briefing, "requests": list(requests),
                  "retain": [], "evidence_refs": list(refs)})


def draft(answer, *, posture="supported", missing=None, passages=None):
    return final({"answer": answer, "support_basis": "evidence", "posture": posture,
                  "missing_information": missing, "citation_passages": passages})


def call(name, arguments):
    return [{"type": "function_call", "name": name, "call_id": f"{name}-1",
             "arguments": json.dumps(arguments)}]


def run_fixture(monkeypatch, arm, question, sources, selection, answer_steps):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")
    monkeypatch.setattr(requests.Session, "request", prohibited)
    candidates = [
        DiscoveryCandidate(f"Synthetic source {index}", f"https://example.org/{index}", content,
                           context_kind="provider_highlights")
        for index, content in enumerate(sources, start=1)
    ]
    outputs = [
        research_decision("research", requests=[
            {"kind": "search", "query": question, "objective": "Locate source material."}
        ]),
        selection,
        *answer_steps,
    ]
    remaining = iter(outputs)
    sent = []

    def post(_url, **kwargs):
        payload = kwargs["json"]
        sent.append(payload)
        data = {"status": "completed", "model": payload["model"],
                "service_tier": payload["service_tier"], "output": next(remaining)}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: data)

    # Exercise the Luna-only role profile against development questions and invented materials.
    result = harness.run_case(
        question, "luna-reserved", arm, post=post, search=lambda *_args, **_kwargs: candidates,
        fetch=prohibited, lexical_search=prohibited, scholarly_search=prohibited,
        scholarly_fetch=prohibited, venue_lookup=prohibited,
    )
    assert len(sent) == len(outputs)
    assert result["failure"] is None
    return result


@pytest.mark.parametrize("arm", harness.ARMS)
def test_wrong_quantity_with_valid_citation_remains_an_answer_failure(monkeypatch, arm, development_questions):
    result = run_fixture(monkeypatch, arm, development_questions["D04"], [TABLE], research_decision("return", refs=["E1"]), [
        draft("Typical at 50 mph on a dry road: thinking 25 m and braking 28 m, totaling 53 m. [E1]",
              passages=[{"ref": "E1", "occurrence": 1, "text": DISTANCES}]),
    ])
    assert result["gate_issues"] == []
    assert result["outcome"]["posture"] == "supported"
    assert result["outcome"]["citation_uses"][0]["support"]
    assert "thinking 25 m" in result["outcome"]["answer"]
    anchor = review.trace_reviewed_passage(result, "E1", DISTANCES)
    assert anchor["answer_finalized"]
    assert anchor["research_packets"] and anchor["answer_packets"]
    assert anchor["passage_sha256"] == sha256(DISTANCES.encode()).hexdigest()


@pytest.mark.parametrize("lookalike", [False, True])
def test_scope_was_seen_by_research_but_dropped_from_the_handoff(
    monkeypatch, tmp_path, capsys, development_questions, lookalike,
):
    sources = [TABLE, SCOPE] if lookalike else [TABLE]
    selected = [{"ref": "E1", "text": DISTANCES}]
    if lookalike:
        # Identical wording from another source does not prove this passage was delivered.
        selected.append("E2")
    result = run_fixture(monkeypatch, "hardened", development_questions["D04"], sources,
                         research_decision("return", refs=selected), [
        draft(f"At 50 mph, the thinking distance is 15 m and braking distance is 38 m. [{VALUES_REF}]"),
    ])
    assert result["gate_issues"] == []
    assert "typical" not in result["outcome"]["answer"]
    scope_anchor = review.trace_reviewed_passage(result, "E1", SCOPE)
    values_anchor = review.trace_reviewed_passage(result, "E1", DISTANCES)
    assert scope_anchor["answer_finalized"]
    assert scope_anchor["research_packets"] and not scope_anchor["answer_packets"]
    assert values_anchor["answer_packets"][0]["material_id"] == VALUES_REF

    # Exercise the offline CLI on a completed development turn.
    log = tmp_path / "development.jsonl"
    passage = tmp_path / "scope.txt"
    log.write_text(json.dumps({
        "kind": "turn_finished", "case_id": "D04", "arm": "hardened", **result,
    }) + "\n", encoding="utf-8")
    passage.write_text(SCOPE, encoding="utf-8")
    assert review.main(["trace-passage", "--log", str(log), "--case-id", "D04", "--arm", "hardened",
                        "--material-id", "E1", "--passage-file", str(passage)]) == 0
    assert json.loads(capsys.readouterr().out) == scope_anchor


@pytest.mark.parametrize("route,tool_result", [
    ("library_read", "answer_library_result"),
    ("research", "research_tool_result"),
])
def test_correct_scope_recovered_in_native_answer_continuation(monkeypatch, route, tool_result, development_questions):
    if route == "library_read":
        steps = [call("library_read", {"target": "E1", "focus": "dry-road conditions",
                                      "start_char": 0, "end_char": len(SCOPE)})]
    else:
        steps = [call("research", {"need": "Retrieve the literal qualification for the table."}),
                 research_decision("return", refs=[{"ref": "E1", "text": SCOPE}])]
    steps.append(draft(f"On a dry road the typical estimate is 53 m: 15 m while reacting and "
                       f"38 m while braking. [{SCOPE_REF}] [{VALUES_REF}]"))
    result = run_fixture(monkeypatch, "hardened", development_questions["D04"], [TABLE],
                         research_decision("return", refs=[{"ref": "E1", "text": DISTANCES}]), steps)
    assert result["gate_issues"] == []
    assert "while reacting" in result["outcome"]["answer"]
    scope_anchor = review.trace_reviewed_passage(result, "E1", SCOPE)
    assert scope_anchor["answer_finalized"]
    assert [(entry["action"], entry["material_id"]) for entry in scope_anchor["answer_packets"]] == [
        (tool_result, SCOPE_REF)
    ]


@pytest.mark.parametrize("arm", harness.ARMS)
def test_notice_subanswer_can_be_dropped_even_when_it_reached_answer(monkeypatch, arm, development_questions):
    result = run_fixture(monkeypatch, arm, development_questions["D03"], [LICENSE], research_decision("return", refs=["E1"]), [
        draft("Yes, modified versions can be sold. [E1]"),
    ])
    assert result["gate_issues"] == []
    assert "notice" not in result["outcome"]["answer"]
    assert review.trace_reviewed_passage(result, "E1", NOTICE)["answer_packets"]


def test_honest_partial_keeps_its_slot_and_cannot_invent_a_notice(monkeypatch, development_questions):
    result = run_fixture(monkeypatch, "hardened", development_questions["D03"], [PERMISSION], research_decision("return", refs=["E1"]), [
        draft("Yes, modified versions can be sold. [E1] The material supplied does not specify the required notices.",
              posture="partial", missing="The notice requirement"),
    ])
    assert result["gate_issues"] == ["partial"]
    assert result["outcome"]["posture"] == "partial"
    with pytest.raises(ValueError, match="passage_not_found"):
        review.trace_reviewed_passage(result, "E1", NOTICE)


def test_correct_compact_paraphrase_with_both_subanswers_passes_mechanical_checks(monkeypatch, development_questions):
    result = run_fixture(monkeypatch, "hardened", development_questions["D03"], [LICENSE], research_decision("return", refs=["E1"]), [
        draft("Yes. Keep the copyright and permission statements with redistributed copies and substantial parts. [E1]"),
    ])
    assert result["gate_issues"] == []
    assert "substantial portions" not in result["outcome"]["answer"]
    assert review.trace_reviewed_passage(result, "E1", NOTICE)["answer_packets"]
