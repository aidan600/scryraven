"""Opt-in scripted pairs through Reading Room, native Responses and SQLite."""

import json
import socket

import pytest
from test_answer_calculator_runtime_01 import ScriptedResponses, model_reply, tool_reply
from test_reading_room import app_for, submit
from test_research_loop import answer, decision, request

from core.exa_transport import DiscoveryCandidate
from core.transport import FetchedMaterial
from experiments.aid12.stopping import STOPPING_INSTRUCTION, ordinary_research_prompt
from experiments.aid12.timing import profile_turn
from scryraven import research
from scryraven.model import ModelConfig, ModelRole, OpenAIModel
from scryraven.session_store import SQLiteSessionStore

STANDARD = ModelConfig(
    research=ModelRole("gpt-6.1-terra", "medium", "default"),
    answer=ModelRole("gpt-6.2-sol", "medium", "default"),
)
REGISTER = "https://example.org/register"
NOTICE = "https://example.org/notice"
DIRECT = "The 2024 North district permit fee is 7 credits."


def respond(stage, output):
    return stage, model_reply(output) | {"service_tier": "default"}, 0


def find(query):
    return respond("research", decision(requests=[request(query=query, objective=query)]))


def read_register(mode="full"):
    operation = request(kind="read", target="E1", mode=mode, focus="permit fee")
    return respond("research", decision(refs=["E1"], requests=[operation]))


def handoff(*refs):
    return respond("research", decision("return", refs, briefing="Use the selected source material."))


def delegate(need):
    return "answer", model_reply({}) | {"service_tier": "default", "output": [{
        "type": "function_call", "name": "research", "call_id": "resolve-scope",
        "arguments": json.dumps({"need": need}),
    }]}, 0


def cited_answer(text, ref, excerpt):
    return respond("answer", answer(f"{text} [{ref}]") | {
        "citation_passages": [{"ref": ref, "occurrence": 1, "text": excerpt}],
    })


def saved_passage(turn):
    region, = turn.citation_uses[0].support
    material = next(item for item in turn.citations[0].materials if item.id == region.evidence_ref)
    return material, material.content[region.start_char:region.end_char]


def no_network(*args, **kwargs):
    pytest.fail("An opt-in replay attempted network I/O")


@pytest.fixture(params=["baseline", "candidate"])
def replay(request, monkeypatch, tmp_path):
    candidate = request.param == "candidate"
    original = research.RESEARCH_PROMPT
    if candidate:
        monkeypatch.setattr(research, "RESEARCH_PROMPT", ordinary_research_prompt(original))
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", no_network)
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture")
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    store.set_billing_authorization("openai", True)  # Fixture DB, injected Responses only.
    log = tmp_path / "diagnostics.jsonl"

    def run(question, steps, *, highlights=None, full=None, first_answer_evidence=None):
        transport = ScriptedResponses(*steps)

        def search(query):
            return [
                DiscoveryCandidate("Synthetic official record", url, content, context_kind="provider_highlights")
                for url, content in (highlights or {})[query]
            ]

        def fetch(url):
            return FetchedMaterial(url, (full or {})[url])

        app = app_for(
            store, dogfood_log=log, model=OpenAIModel(STANDARD, post=transport.post), search=search,
            fetch=fetch, lexical_search=no_network, scholarly_search=no_network,
            scholarly_fetch=no_network, venue_lookup=no_network,
        )
        client = app.test_client()
        try:
            submitted = submit(client, question=question)
            assert submitted.status_code == 303
            assert client.get(submitted.location).status_code == 200
        finally:
            app.extensions["research_jobs"].shutdown()
        assert len(transport.calls) == len(steps)
        for call, (stage, _, _) in zip(transport.calls, steps, strict=True):
            payload = call["json"]
            assert payload["model"] == getattr(STANDARD, stage).model
            assert payload["reasoning"] == {"effort": "medium"}
            assert payload["service_tier"] == "default"
            prompt = payload["input"][0]["content"][0]["text"]
            assert (STOPPING_INSTRUCTION in prompt) == (
                candidate and stage == "research" and "Answer has requested delegated_need." not in prompt)
        if first_answer_evidence is not None:
            payload = next(call["json"] for call in transport.calls if call["json"]["text"]["format"]["name"] == "answer")
            packet = json.loads("".join(block["text"] for block in payload["input"][1]["content"]))
            assert [(item["id"], item["content"]) for item in packet["evidence"]] == first_answer_evidence
        receipt = json.loads(log.read_text(encoding="utf-8"))
        assert receipt["physical_requests"] == len(steps)
        assert all(call["returned_service_tier"] == "default" for call in receipt["model_calls"])
        profile_turn(receipt)
        session_id = store.list_sessions()[0].session_id
        turns = SQLiteSessionStore(store.path).load(session_id).state.turns
        return receipt, turns

    return candidate, run


@pytest.mark.parametrize("avoidable_read", [None, "local", "full"])
def test_direct_lookup_keeps_exact_citation(replay, avoidable_read):
    candidate, run = replay
    repeated = [read_register(avoidable_read)] if avoidable_read and not candidate else []
    receipt, (saved,) = run(
        "What was the North district's 2024 permit fee?",
        [find("fee"), *repeated, handoff("E1"), respond("answer", answer("7 credits. [E1]"))],
        highlights={"fee": [(REGISTER, DIRECT)]}, full={REGISTER: DIRECT},
    )
    assert receipt["outcome"] == "completed"
    assert receipt["role_physical_requests"] == {"research": 2 + len(repeated), "answer": 1}
    assert receipt["physical_acquisition_dispatches"] == 1 + int(bool(repeated and avoidable_read == "full"))
    assert saved.posture == "supported" and saved.answer == "7 credits. [1]"
    assert [(citation.url, citation.materials[0].content) for citation in saved.citations] == [(REGISTER, DIRECT)]


@pytest.mark.parametrize(
    ("question", "first", "competing", "full", "phrase"),
    [
        ("What was the 2024 North district permit fee?",
         "The permit fee is 7 credits.", [], DIRECT, "7 credits."),
        ("What was the 2024 North district permit fee?",
         "The South district's 2024 fee is 7 credits.", [],
         "The 2024 North district permit fee is 9 credits.", "9 credits."),
        ("What was the 2024 North district permit fee?", DIRECT,
         [(NOTICE, "The 2024 North district permit fee is 9 credits.")],
         "Restated 2024 North district fee: 9 credits. This revision supersedes the 7-credit fee.",
         "9 credits after the revision."),
    ],
    ids=["weak", "ambiguous-identity", "conflict"],
)
def test_incomplete_or_conflicting_highlights_keep_the_read(replay, question, first, competing, full, phrase):
    _, run = replay
    ref = f"E{2 + len(competing)}"
    receipt, (saved,) = run(
        question,
        [find("fee"), read_register(), handoff(ref), respond("answer", answer(f"{phrase} [{ref}]"))],
        highlights={"fee": [(REGISTER, first), *competing]}, full={REGISTER: full},
    )
    assert receipt["outcome"] == "completed" and receipt["physical_acquisition_dispatches"] == 2
    assert saved.answer == f"{phrase} [1]"
    assert saved.citations[0].materials[0].content == full


def test_multipart_and_required_second_citation_keep_second_search(replay):
    _, run = replay
    deadline = "The North district notice says permit applications close 30 June 2024."
    receipt, (saved,) = run(
        "What was the 2024 fee and deadline for North district permits? Cite the register and the notice.",
        [find("fee"), find("deadline"), handoff("E1", "E2"),
         respond("answer", answer("The fee was 7 credits [E1], and the deadline was 30 June 2024 [E2]."))],
        highlights={"fee": [(REGISTER, DIRECT)], "deadline": [(NOTICE, deadline)]},
    )
    assert receipt["outcome"] == "completed" and receipt["physical_acquisition_dispatches"] == 2
    assert [citation.url for citation in saved.citations] == [REGISTER, NOTICE]
    assert [citation.materials[0].content for citation in saved.citations] == [DIRECT, deadline]


def test_native_calculation_keeps_answer_continuation(replay):
    _, run = replay
    receipt, (saved,) = run(
        "The stipulated fee is 7 credits per permit. What do 3 permits cost?",
        [handoff(), ("answer", tool_reply("7 * 3", "calculate-fee") | {"service_tier": "default"}, 0),
         respond("answer", answer("21 credits.", support_basis="user_premises"))],
    )
    assert receipt["outcome"] == "completed" and receipt["physical_acquisition_dispatches"] == 0
    assert receipt["calculator"]["calls"] == 1 and receipt["calculator"]["failures"] == 0
    assert receipt["role_physical_requests"] == {"research": 1, "answer": 2}
    assert saved.answer == "21 credits." and not saved.citations


def test_answer_can_delegate_to_ordinary_research_when_evidence_is_weak(replay):
    _, run = replay
    delegated = delegate("Verify the place and year of the value in the register.")
    receipt, (saved,) = run(
        "What was the 2024 North district permit fee?",
        [find("fee"), handoff(), delegated, read_register(), handoff("E2"),
         respond("answer", answer("7 credits. [E2]"))],
        highlights={"fee": [(REGISTER, "The permit fee is 7 credits.")]}, full={REGISTER: DIRECT},
    )
    assert receipt["outcome"] == "completed" and receipt["research_episodes"] == 1
    assert receipt["role_physical_requests"] == {"research": 4, "answer": 2}
    assert saved.answer == "7 credits. [1]" and saved.citations[0].materials[0].content == DIRECT


@pytest.mark.parametrize(
    ("question", "highlights", "refs"),
    [
        ("What was the 2024 North district permit fee?",
         [(REGISTER, "The 2024 South district permit fee is 7 credits.")], ["E1"]),
        ("What was the 2024 North district permit fee?",
         [(REGISTER, "Lake City's North district charges 7 credits in 2024."),
          (NOTICE, "River City's North district charges 9 credits in 2024.")], ["E1", "E2"]),
        ("What was the 2024 North district fee for a new permit?",
         [(REGISTER, "The 2024 North district permit fee is 7 credits for")], ["E1"]),
        ("What was the 2024 North district permit fee?",
         [(REGISTER, DIRECT),
          (NOTICE, "The North District Permit Board sets the 2024 permit fee at 9 credits.")], ["E1", "E2"]),
    ],
    ids=["wrong-identity", "ambiguous-identity", "truncated-highlight", "unresolved-authority-conflict"],
)
def test_valid_citation_can_publish_an_unsupported_early_stop_in_either_arm(replay, question, highlights, refs):
    _, run = replay
    first_url, first_excerpt = highlights[0]
    receipt, (saved,) = run(
        question,
        [find("fee"), handoff(*refs), cited_answer("The 2024 North district fee was 7 credits.", "E1", first_excerpt)],
        highlights={"fee": highlights},
        first_answer_evidence=[(ref, text) for ref, (_, text) in zip(refs, highlights, strict=True)],
    )
    assert receipt["outcome"] == "completed" and receipt["corrections"]["answer"] == {}
    assert receipt["physical_acquisition_dispatches"] == 1
    assert saved.posture == "supported" and saved.answer == "The 2024 North district fee was 7 credits. [1]"
    citation, = saved.citations
    assert citation.url == first_url
    assert saved_passage(saved)[1] == first_excerpt


@pytest.mark.parametrize("path", ["early-stop", "ordinary-read", "answer-recovery"])
def test_hidden_correction_on_same_highlight_in_either_arm(replay, path):
    _, run = replay
    # Each path starts with one unqualified highlight. Only the full source
    # supplies the retroactive correction.
    correction = "November 2024 correction: The fee is 9 credits, retroactive to the start of 2024."
    full_text = DIRECT + "\n" + correction
    read_and_return = [read_register(), handoff("E2")]
    if path == "early-stop":
        steps = [handoff("E1"), cited_answer("7 credits.", "E1", DIRECT)]
        expected_passage = DIRECT
        expected = ("7 credits. [1]", DIRECT, 2, 1, 1, 0)
    else:
        if path == "ordinary-read":
            steps = read_and_return.copy()
            expected = ("9 credits. [1]", full_text, 3, 1, 2, 0)
        else:
            steps = [handoff("E1"), delegate("Check whether the register has a later correction."), *read_and_return]
            expected = ("9 credits. [1]", full_text, 4, 2, 2, 1)
        steps.append(cited_answer("9 credits.", "E2", correction))
        expected_passage = correction
    receipt, (saved,) = run(
        "What was the North district's 2024 permit fee?",
        [find("fee"), *steps],
        highlights={"fee": [(REGISTER, DIRECT)]}, full={REGISTER: full_text},
    )
    assert receipt["outcome"] == "completed" and saved.posture == "supported"
    assert saved.citations[0].url == REGISTER
    material, passage = saved_passage(saved)
    assert passage == expected_passage
    assert (
        saved.answer, material.content,
        receipt["role_physical_requests"]["research"], receipt["role_physical_requests"]["answer"],
        receipt["physical_acquisition_dispatches"], receipt["research_episodes"],
    ) == expected


def test_invalid_citation_cannot_publish(replay):
    _, run = replay
    receipt, turns = run(
        "What was the 2024 North district permit fee?",
        [find("fee"), handoff("E1"), respond("answer", answer("7 credits. [E999]"))],
        highlights={"fee": [(REGISTER, DIRECT)]},
    )
    assert receipt["failure"] == {"stage": "citations", "code": "invalid_citation_reference"}
    assert receipt["outcome"] == "failed" and not turns
