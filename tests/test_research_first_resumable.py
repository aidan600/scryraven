"""Research-first handoff and native Answer continuation, using offline transports."""
from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven import research
from scryraven.model import ModelConfig, ModelRole, OpenAIModel
from scryraven.research import RunError, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import Evidence

CONFIG = ModelConfig(ModelRole("research-test", "high"), ModelRole("answer-test", "high"))
QUESTION = "Explain the original value, twice it, and its consequential qualifications."
VALUE = "The stated value is seven."


def understanding():
    return {"interpretation": "Investigate the immutable whole question", "established": [],
            "still_needed": [], "last_route_result": ""}


def request(kind="search", query="requested original value", target="", **changes):
    return {"kind": kind, "query": query, "target": target, "mode": "auto", "focus": "",
            "scope": [], "start_char": None, "end_char": None, **changes}


def initial(action="research", refs=(), requests=()):
    return {"understanding": understanding(), "action": action, "requests": list(requests),
            "retain": list(refs), "answer_evidence_refs": list(refs) if action == "answer" else []}


def delegated(action="research", refs=(), requests=(), selections=None):
    return {"understanding": understanding(), "action": action, "requests": list(requests),
            "retain": list(refs), "evidence_refs": list(refs) if selections is None else selections,
            "assessment": "Fallible navigation; interpret the originals independently."}


def answer(text="Seven. [E1]", posture="supported", basis="evidence", missing=None):
    return {"posture": posture, "support_basis": basis, "answer": text, "missing_information": missing}


def reply(value):
    return [{"type": "message", "role": "assistant", "phase": "final_answer", "content": [
        {"type": "output_text", "text": json.dumps(value)}]}]


def tool(name, arguments, identity):
    return [{"type": "reasoning", "id": f"reason-{identity}", "encrypted_content": f"opaque-{identity}"},
            {"type": "function_call", "name": name, "call_id": identity,
             "arguments": json.dumps(arguments)}]


def packet(payload):
    user = next(item for item in payload["input"] if item.get("role") == "user")
    return json.loads("".join(item["text"] for item in user["content"]))


def results(payload):
    return {item["call_id"]: json.loads(item["output"]) for item in payload["input"]
            if item.get("type") == "function_call_output"}


def scripted(monkeypatch, outputs, backend="api"):
    """Use production OpenAIModel and the actual plan-payload projection, never auth/I/O."""
    payloads, timeouts = [], []
    remaining = iter(outputs)

    def dispatch(payload, timeout):
        payloads.append(deepcopy(payload))
        timeouts.append(timeout)
        output = next(remaining)
        if callable(output):
            output = output(payload)
        if isinstance(output, Exception):
            raise output
        return {"status": "completed", "output": output,
                "usage": {"input_tokens": 11, "output_tokens": 5}}

    if backend == "api":
        monkeypatch.setenv("OPENAI_API_KEY", "synthetic-offline-key")

        class Response:
            def __init__(self, data):
                self.data = data

            def raise_for_status(self):
                pass

            def json(self):
                return self.data

        def post(_url, **kwargs):
            return Response(dispatch(kwargs["json"], kwargs["timeout"].total))

        model = OpenAIModel(CONFIG, post=post)
    else:
        from scryraven.chatgpt_plan.transport import plan_payload

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        model = OpenAIModel(CONFIG, backend="chatgpt_plan")
        def plan_request(payload, *, timeout, before_dispatch):
            body = plan_payload(payload)
            return dispatch(body, min(timeout, before_dispatch()))

        model.plan_transport = SimpleNamespace(request=plan_request)
    return model, payloads, timeouts


def search(_query):
    return [DiscoveryCandidate("Official", "https://example.org/value", VALUE,
                               context_kind="provider_highlights")]


def prohibited(*_args, **_kwargs):
    pytest.fail("unexpected external dispatch")


def stages(payloads):
    return [value["text"]["format"]["name"] for value in payloads]


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_initial_production_research_precedes_independent_answer_without_delegation(monkeypatch, backend):
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("answer", ["E1"])), reply(answer())], backend)
    result = run("What is the original value?", model=model, search=search, fetch=prohibited)
    assert stages(payloads) == ["research", "research", "answer"]
    first = packet(payloads[0])
    assert "delegated_need" not in first and "answer_delivery" not in first
    assert "sole Research decision-maker" in payloads[0]["input"][0]["content"][0]["text"]
    assert packet(payloads[2])["evidence"][0]["content"] == VALUE
    handoff, = [event for event in result.trace if event["action"] == "initial_research_handoff"]
    assert handoff["selected_refs"] == ["E1"]
    assert result.posture == "supported" and result.citations[0].materials[0].content == VALUE
    budget = result.trace[-1]["budget"]
    assert budget["research_episodes"] == 0 and budget["physical_requests"] == 3
    assert budget["role_physical_requests"] == {"answer": 1, "research": 2}


def test_initial_handoff_retains_normal_large_selected_packet(monkeypatch):
    original = Evidence("E1", "https://example.org/large", "Original", "The controlling fact. ".ljust(60_000, "x"),
                        "provider_highlights")
    model, payloads, _ = scripted(monkeypatch, [reply(initial("answer", ["E1"])), reply(answer())])
    result = run("What is established?", model=model, initial_evidence=(original,),
                 retained_acquisitions=(original,), search=prohibited, fetch=prohibited)
    supplied, = packet(payloads[1])["evidence"]
    assert supplied["content"] == original.content
    assert packet(payloads[1])["library"]["text_characters_remaining"] == 68_000
    assert result.selected_evidence == (original,)


def test_premise_control_keeps_initial_research_and_dependent_calculator(monkeypatch):
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial("answer")), tool("calculate", {"expression": "12*7"}, "c1"),
        tool("calculate", {"expression": "84/2"}, "c2"),
        reply(answer("Under your premises, half the total is 42.", basis="user_premises"))])
    result = run("Assume twelve lots of seven; what is half the total?", model=model, search=prohibited)
    assert stages(payloads) == ["research", "answer", "answer", "answer"]
    assert results(payloads[-1])["c1"]["value"] == "84"
    assert results(payloads[-1])["c2"]["value"] == "42"
    assert result.posture == "supported" and not result.citations
    assert result.trace[-1]["budget"]["physical_requests"] == 4


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_multiple_research_calls_resume_one_answer_with_local_and_arithmetic_history(monkeypatch, backend):
    context = {"conversation_context": [{"question": "Use the winter scenario.",
                                         "answer": "Acknowledged, as task context."}]}
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("answer", ["E1"])),
        tool("library_read", {"target": "E1", "focus": "", "start_char": None, "end_char": None}, "l1"),
        tool("calculate", {"expression": "7*2"}, "c1"),
        tool("research", {"need": "Fetch the original's newly consequential winter qualification."}, "r1"),
        reply(delegated(requests=[request("read", query="", target="https://example.org/value")])),
        reply(delegated("return", ["E2"])),
        tool("library_find", {"query": "winter", "scope": ["E2"]}, "l2"),
        tool("research", {"need": "Find whether the documented winter uplift is one."}, "r2"),
        reply(delegated(requests=[request(query="winter uplift original")])),
        reply(delegated("return", ["E3"])),
        tool("calculate", {"expression": "14+1"}, "c2"),
        reply(answer("Twice seven is fourteen; adding the winter uplift gives fifteen. [E1][E2][E3]"))], backend)
    acquisitions = []

    def discover(query):
        acquisitions.append(query)
        if len(acquisitions) == 1:
            return search(query)
        return [DiscoveryCandidate("Winter uplift", "https://example.org/uplift", "The winter uplift is one.",
                                   context_kind="provider_highlights")]

    result = run(QUESTION, model=model, search=discover,
                 fetch=lambda url: FetchedMaterial(url, "The stated value is seven, applicable in winter."), context=context)
    assert stages(payloads) == ["research", "research", "answer", "answer", "answer", "research", "research",
                                "answer", "answer", "research", "research", "answer", "answer"]
    owners = [value for value in payloads if value["text"]["format"]["name"] == "answer"]
    for value in owners[1:]:
        assert value["input"][:2] == owners[0]["input"][:2]
        assert any(item.get("encrypted_content") == "opaque-l1" for item in value["input"])
    assert list(results(owners[-1])) == ["l1", "c1", "r1", "l2", "r2", "c2"]
    assert results(owners[-1])["r1"]["evidence"][0]["content"].endswith("in winter.")
    assert results(owners[-1])["r2"]["evidence"][0]["content"] == "The winter uplift is one."
    assert results(owners[-1])["c1"]["value"] == "14"
    assert results(owners[-1])["c2"]["value"] == "15"
    for value in payloads:
        assert packet(value)["question"] == QUESTION
        assert packet(value)["conversation_context"] == context["conversation_context"]
    for index in (5, 6, 9, 10):
        assert "bounded investigator called by Answer" in payloads[index]["input"][0]["content"][0]["text"]
        assert packet(payloads[index])["prior_research_understanding"]["fallible_navigation_only"]
        assert "opaque-l1" not in json.dumps(payloads[index])
    budget = result.trace[-1]["budget"]
    assert budget["physical_requests"] == 13 and budget["research_episodes"] == 2
    assert budget["role_physical_requests"] == {"answer": 7, "research": 6}
    assert budget["external_attempts"] == 3 and budget["answer_continuations"] == 6
    assert results(owners[-1])["r2"]["library"]["operations_remaining"] < results(owners[-1])["r1"]["library"]["operations_remaining"]
    assert result.posture == "supported" and len(result.citations) == 2


def test_initial_and_delegated_research_share_first_deep_eligibility(monkeypatch):
    modes = []

    def exa(query, *, search_type, timeout_seconds):
        modes.append((search_type, timeout_seconds))
        return [DiscoveryCandidate("Original", f"https://example.org/{len(modes)}", VALUE,
                                   context_kind="provider_highlights")]

    monkeypatch.setattr(research, "search_exa", exa)
    model, _, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("answer", ["E1"])),
        tool("research", {"need": "Find an independently acquired qualification."}, "r1"),
        reply(delegated(requests=[request(query="qualification")])), reply(delegated("return", ["E2"])),
        reply(answer("Both originals state seven. [E1][E2]"))])
    result = run("Establish the value and qualification.", model=model, search=exa)
    assert [mode for mode, _ in modes] == ["deep", "auto"]
    assert result.trace[-1]["budget"]["external_attempts"] == 2


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_invalid_final_after_research_corrects_inside_same_native_history(monkeypatch, backend):
    rejected = [{"type": "reasoning", "id": "invalid-reason", "encrypted_content": "opaque-invalid"},
                *reply(answer("REJECTED UNCITED PROSE"))]
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("answer", ["E1"])),
        tool("library_browse", {"offset": 0}, "l1"),
        tool("research", {"need": "Obtain the consequential original qualification."}, "r1"),
        reply(delegated(requests=[request("read", query="", target="https://example.org/value")])),
        reply(delegated("return", ["E2"])), rejected,
        tool("library_browse", {"offset": 0}, "l2"), tool("calculate", {"expression": "7*2"}, "c1"),
        reply(answer("Seven, doubled, is fourteen under the winter qualification. [E1][E2]"))], backend)
    events = []
    result = run(QUESTION, model=model, search=search, context={"conversation_context": [
        {"question": "Use the winter case.", "answer": "Winter is an explicit premise."}]},
        fetch=lambda url: FetchedMaterial(url, "The stated value is seven in winter."), observe=events.append)
    owners = [p for p in payloads if p["text"]["format"]["name"] == "answer"]
    assert len(owners) == 6
    # Initial user/developer items and every prior native item remain byte-exact.
    corrected = owners[3]
    assert corrected["input"][:len(owners[2]["input"])] == owners[2]["input"]
    assert any(item.get("encrypted_content") == "opaque-invalid" for item in corrected["input"])
    assert "REJECTED UNCITED PROSE" not in json.dumps(corrected)
    assert "missing_citation" in json.dumps(corrected["input"][-1])
    resources = json.loads(corrected["input"][-2]["content"][0]["text"].split(": ", 1)[1])
    assert resources["physical_requests"] == 7 and resources["physical_remaining"] == 33
    assert list(results(corrected)) == ["l1", "r1"]
    assert list(results(owners[-1])) == ["l1", "r1", "l2", "c1"]
    assert results(owners[-1])["c1"]["value"] == "14"
    assert packet(corrected) == packet(owners[0])
    assert [item["id"] for item in packet(corrected)["evidence"]] == ["E1"]
    assert results(corrected)["r1"]["evidence"][0]["id"] == "E2"
    before = results(corrected)["r1"]["library"]
    after = results(owners[-1])["l2"]
    assert after["text_characters_remaining"] == before["text_characters_remaining"]
    assert after["operations_remaining"] == before["operations_remaining"] - 1
    assert len([e for e in events if e["action"] == "model_started" and e.get("contract") == "answer"]) == 1
    requests = [e for e in events if e["action"] == "model_request_finished" and e.get("contract") == "answer"]
    assert [e["continuation_index"] for e in requests] == list(range(6))
    assert sum(e["input_tokens"] for e in requests) == 66
    assert sum(e["output_tokens"] for e in requests) == 30
    budget = result.trace[-1]["budget"]
    assert budget["physical_requests"] == 10 and budget["external_attempts"] == 2
    assert budget["role_physical_requests"] == {"answer": 6, "research": 4}
    assert budget["research_episodes"] == 1 and budget["answer_continuations"] == 5
    assert result.posture == "supported" and len(result.citations) == 1


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
@pytest.mark.parametrize("invalid,code", [
    ({"not": "the schema"}, "malformed_model_response"),
    (answer(missing="Missing original"), "supported_with_missing_information"),
    (answer("No conclusion", posture="unable", basis="user_premises"), "basis_user_premises_unable"),
    (answer("A conclusion", basis="none"), "basis_none_requires_unable"),
    (answer("Premises [E1]", basis="user_premises"), "basis_user_premises_has_citations"),
    (answer("Seven without required citation"), "missing_citation"),
])
def test_existing_mechanical_corrections_share_native_context(monkeypatch, backend, invalid, code):
    model, payloads, _ = scripted(monkeypatch, [reply(initial(requests=[request()])),
        reply(initial("answer", ["E1"])), reply(invalid), reply(answer())], backend)
    result = run("What is the original value?", model=model, search=search)
    owners = payloads[-2:]
    # The plan projection inserts its tools before the first response item;
    # without prior tool/opaque items that declaration can move past feedback.
    previous = [item for item in owners[0]["input"] if item.get("type") != "additional_tools"]
    current = [item for item in owners[1]["input"] if item.get("type") != "additional_tools"]
    assert current[:len(previous)] == previous
    assert "output_correction" not in packet(owners[1])
    correction = next(item for item in current if "output_correction" in json.dumps(item))
    expected = "Return a JSON object matching the schema." if code == "malformed_model_response" else code
    assert expected in json.dumps(correction)
    assert [e["code"] for e in result.trace if e["action"] == "response_rejected"] == [code]
    assert result.posture == "supported"
    assert len([e for e in result.trace if e["action"] == "model_started" and e.get("contract") == "answer"]) == 1


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_second_invalid_final_after_research_has_no_third_attempt_or_prose_publication(monkeypatch, backend):
    model, payloads, _ = scripted(monkeypatch, [reply(initial("answer")),
        tool("research", {"need": "Find the original."}, "r1"),
        reply(delegated(requests=[request()])), reply(delegated("return", ["E1"])),
        reply(answer("FIRST REJECTED PROSE")), reply(answer("SECOND REJECTED PROSE"))], backend)
    result = run("What is the original value?", model=model, search=search)
    assert result.answer == research.ANSWER_VALIDATION_FAILURE_MESSAGE
    assert result.posture == "unable" and not result.citations
    assert len(payloads) == 6
    assert "FIRST REJECTED PROSE" not in json.dumps(payloads[-1])
    assert list(results(payloads[-1])) == ["r1"]
    assert len([e for e in result.trace if e["action"] == "answer_validation_exhausted"]) == 1
    assert result.trace[-1]["budget"]["physical_requests"] == 6


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_non_json_final_and_empty_evidence_basis_use_only_one_native_correction(monkeypatch, backend):
    malformed = [{"type": "message", "role": "assistant", "phase": "final_answer",
                  "content": [{"type": "output_text", "text": "not-json-at-all"}]}]
    model, payloads, _ = scripted(monkeypatch, [reply(initial("answer")), malformed,
        reply(answer("A claim without supplied evidence"))], backend)
    result = run("Find the missing original.", model=model, search=prohibited)
    assert result.answer == research.ANSWER_VALIDATION_FAILURE_MESSAGE
    assert [e["code"] for e in result.trace if e["action"] == "response_rejected"] == [
        "malformed_model_response", "basis_evidence_missing_packet"]
    assert len(payloads) == 3
    assert "not-json-at-all" not in json.dumps(payloads[-1])


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_duplicate_tool_id_still_rejected_after_final_correction(monkeypatch, backend):
    model, payloads, _ = scripted(monkeypatch, [reply(initial("answer")),
        tool("research", {"need": "Find the original."}, "same"),
        reply(delegated(requests=[request()])), reply(delegated("return", ["E1"])),
        reply(answer("Uncited rejected prose")),
        tool("calculate", {"expression": "7*2"}, "same")], backend)
    with pytest.raises(RunError, match="malformed_model_response"):
        run("What is the original value?", model=model, search=search)
    assert len(payloads) == 6 and list(results(payloads[-1])) == ["same"]


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
@pytest.mark.parametrize("bound", ["physical", "deadline"])
def test_correction_cannot_renew_exhausted_time_or_physical_allowance(monkeypatch, backend, bound):
    now = [0.0]

    def invalid(_payload):
        if bound == "deadline":
            now[0] = 901
        return reply(answer("Uncited rejected prose"))

    model, payloads, _ = scripted(monkeypatch, [reply(initial(requests=[request()])),
        reply(initial("answer", ["E1"])), invalid], backend)
    result = run("What is the original value?", model=model, search=search,
        limits=research.RunLimits(physical_model_requests=3 if bound == "physical" else 40),
        clock=lambda: now[0])
    assert len(payloads) == 3
    assert result.posture == "unable" and not result.citations
    assert result.stop_reason == "research_bound"
    assert result.trace[-1]["budget"]["physical_requests"] == 3


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_invalid_custody_alias_remains_hard_failure_without_correction(monkeypatch, backend):
    model, payloads, _ = scripted(monkeypatch, [reply(initial(requests=[request()])),
        reply(initial("answer", ["E1"])), reply(answer("Unseen material. [E2]"))], backend)
    with pytest.raises(RunError, match="invalid_citation_reference"):
        run("What is established?", model=model, search=search)
    assert len(payloads) == 3


def test_initial_research_follows_source_discovered_dependency_before_handoff(monkeypatch):
    fetched = []
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])),
        reply(initial(refs=["E1"], requests=[request("read", query="", target="https://example.org/controlling")])),
        reply(initial("answer", ["E1", "E2"])), reply(answer("The original identifies seven under the controlling rule. [E1][E2]"))])

    def fetch(url):
        fetched.append(url)
        return FetchedMaterial(url, "The controlling rule establishes applicability to this case.")

    result = run("What controls the original result?", model=model,
                 search=lambda _: [DiscoveryCandidate("Dependency", "https://example.org/lead",
                     "The result is seven; the controlling original is https://example.org/controlling .",
                     context_kind="provider_highlights")], fetch=fetch)
    assert stages(payloads) == ["research"] * 3 + ["answer"]
    assert fetched == ["https://example.org/controlling"]
    assert result.trace[-1]["budget"]["research_episodes"] == 0 and result.posture == "supported"


def test_denied_seventeenth_attempt_returns_exact_local_passage_into_same_answer(monkeypatch):
    passage = "The company reported 2018 revenue of $1.8 billion and losses of $1.9 billion."
    body = ("Earlier source context. " * 12 + passage + " Later context.").ljust(916, ".")
    known = (Evidence("E1", "https://example.org/one", "One", "Known context. ".ljust(64_000, "x"), "provider_highlights"),
             Evidence("E2", "https://example.org/two", "Two", "Known qualification. ".ljust(63_776, "y"), "provider_highlights"))
    dispatched = []

    def discover(query):
        dispatched.append(query)
        return [DiscoveryCandidate("Report", "https://example.org/new", body, context_kind="provider_highlights")]

    def return_after_denial(payload):
        state = packet(payload)
        assert state["budget"]["external_attempts"] == 16 and state["budget"]["external_remaining"] == 0
        assert state["last_route"][0]["code"] == "external_attempts"
        assert state["answer_delivery"]["text_characters_remaining"] == 224
        assert "Local Read/Find" in state["output_correction"]
        assert next(item for item in state["evidence"] if item["id"] == "E3")["content"] == body
        return reply(delegated("return", ["E3"], selections=[{"ref": "E3", "text": passage}]))

    sequence = [reply(initial("answer", ["E1", "E2"])),
                tool("research", {"need": "Obtain the exact original revenue/loss benchmark."}, "r1")]
    sequence += [reply(delegated(refs=[] if index == 0 else ["E3"], requests=[request(query=f"report {index}")]))
                 for index in range(16)]
    sequence += [reply(delegated(refs=["E3"], requests=[request(query="unavailable extra")])),
                 return_after_denial, reply(answer("The original reports both financial figures. [E3]"))]
    model, payloads, _ = scripted(monkeypatch, sequence)
    result = run("What are the original revenue and loss?", model=model, search=discover, fetch=prohibited,
                 retained_acquisitions=known, initial_evidence=known)
    returned = results(payloads[-1])["r1"]
    assert len(dispatched) == 16 and returned["text_characters_returned"] == len(passage)
    assert returned["text_characters_remaining"] == 224 - len(passage)
    assert returned["omitted_material_ids"] == returned["selection_limitations"] == []
    view, = result.selected_evidence
    assert view.content == passage and view.range_basis == "acquired_highlight" and view.parent_id == "E3"
    assert result.posture == "supported" and result.stop_reason == "research_bound"
    assert result.trace[-1]["budget"]["physical_requests"] == 21
    assert result.trace[-1]["budget"]["external_attempts"] == 16
    assert payloads[-1]["input"][:2] == payloads[1]["input"][:2]
    assert any(item.get("encrypted_content") == "opaque-r1" for item in payloads[-1]["input"])


def test_retained_followup_reopens_and_still_runs_initial_research_without_reacquisition(monkeypatch, tmp_path):
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("answer", ["E1"])), reply(answer()),
        reply(initial("answer", ["E1"])), reply(answer("The retained original says seven. [E1]"))])
    store = SQLiteSessionStore(tmp_path / "hybrid.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=search, fetch=prohibited)
    session.ask("What is the original value?")
    first = session.turns[0]
    reopened = ResearchSession.open(session.session_id, store=store, model=model, search=prohibited, fetch=prohibited)
    result = reopened.ask("What value did that original state?")
    assert first == reopened.turns[0]
    assert stages(payloads) == ["research", "research", "answer", "research", "answer"]
    assert result.trace[-1]["budget"]["external_attempts"] == 0
    assert result.trace[-1]["budget"]["research_episodes"] == 0
    assert ResearchSession.open(session.session_id, store=store).turns == reopened.turns


def test_interruption_after_delegated_return_preserves_prior_durable_turn(monkeypatch, tmp_path):
    def interrupted(_payload):
        raise KeyboardInterrupt

    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("answer", ["E1"])), reply(answer()),
        reply(initial("answer", ["E1"])), tool("research", {"need": "Find the new qualification"}, "interrupt-r1"),
        reply(delegated(requests=[request(query="new qualification")])),
        reply(delegated("return", ["E2"])), interrupted,
    ])
    store = SQLiteSessionStore(tmp_path / "interrupted.sqlite3")
    searches = []

    def acquiring(query):
        searches.append(query)
        if query == "new qualification":
            return [DiscoveryCandidate("Qualification", "https://example.org/qualification", "Winter applies.",
                                       context_kind="provider_highlights")]
        return search(query)

    session = ResearchSession.create(store=store, model=model, search=acquiring, fetch=prohibited)
    session.ask("What is the original value?")
    before = store.load(session.session_id)
    with pytest.raises(KeyboardInterrupt):
        session.ask("What new qualification applies to that value?")
    assert "new qualification" in searches
    assert results(payloads[-1])["interrupt-r1"]["evidence"][0]["content"] == "Winter applies."
    assert store.load(session.session_id) == before
    assert session.turns == before.state.turns and session.acquisitions == before.state.acquisitions
    assert session.metadata == before.metadata


def test_final_missing_information_is_a_limitation_without_stage_restart(monkeypatch):
    model, payloads, _ = scripted(monkeypatch, [reply(initial("answer")),
        reply(answer("The requested evidence was not obtained.", "unable", "none", "Obtain the missing original"))])
    result = run("What does the absent original establish?", model=model, search=prohibited)
    assert stages(payloads) == ["research", "answer"] and result.posture == "unable"
    final, = [event for event in result.trace if event["action"] == "answer_decision"]
    assert final["decision"]["missing_information"] == "Obtain the missing original"


def test_unreturned_worker_original_cannot_be_cited_by_answer(monkeypatch):
    model, _, _ = scripted(monkeypatch, [reply(initial("answer")),
        tool("research", {"need": "Find actual originals."}, "r1"),
        reply(delegated(requests=[request()])), reply(delegated("return", ["E1"])),
        reply(answer("The unseen second source says two. [E2]"))])
    with pytest.raises(RunError, match="invalid_citation_reference"):
        run("What do the originals establish?", model=model, search=lambda _: [
            DiscoveryCandidate("First", "https://example.org/first", "One.", context_kind="provider_highlights"),
            DiscoveryCandidate("Second", "https://example.org/second", "Two.", context_kind="provider_highlights")])


def test_invalid_research_arguments_continue_without_dispatching_worker(monkeypatch):
    model, payloads, _ = scripted(monkeypatch, [reply(initial("answer")),
        tool("research", {"need": " "}, "bad"),
        reply(answer("No source was acquired.", "unable", "none", "Actual original missing"))])
    result = run("Find the original.", model=model, search=prohibited)
    assert stages(payloads) == ["research", "answer", "answer"]
    assert results(payloads[-1])["bad"] == {"error": "invalid_tool_arguments"}
    assert result.trace[-1]["budget"]["research_episodes"] == 0


def test_repeated_tool_identity_is_rejected_after_initial_research(monkeypatch):
    model, payloads, _ = scripted(monkeypatch, [reply(initial("answer")),
        tool("calculate", {"expression": "7*2"}, "same"), tool("calculate", {"expression": "14+1"}, "same")])
    with pytest.raises(RunError, match="malformed_model_response"):
        run("Assume seven; double it and add one.", model=model, search=prohibited)
    assert len(payloads) == 3


def test_expired_initial_research_never_dispatches_unbudgeted_answer(monkeypatch):
    now = [0.0]

    def expire(_payload):
        now[0] = 901
        return reply(initial("answer"))

    model, payloads, _ = scripted(monkeypatch, [expire])
    result = run("Find the original.", model=model, search=prohibited, clock=lambda: now[0])
    assert stages(payloads) == ["research"]
    assert result.posture == "unable" and result.stop_reason == "research_bound" and not result.citations


@pytest.mark.parametrize("delay", [125, 725])
def test_tool_research_uses_whole_turn_time_past_retired_stage_clocks(monkeypatch, delay):
    now = [0.0]

    def delayed(_payload):
        now[0] = delay
        return tool("research", {"need": "Establish the missing original value."}, "r1")

    model, payloads, timeouts = scripted(monkeypatch, [reply(initial("answer")), delayed,
        reply(delegated(requests=[request()])), reply(delegated("return", ["E1"])), reply(answer())])
    result = run("What is the value?", model=model, search=search, clock=lambda: now[0])
    assert result.posture == "supported" and stages(payloads) == ["research", "answer", "research", "research", "answer"]
    assert result.trace[-1]["budget"]["seconds_remaining"] == 900 - delay
    assert all(timeout <= min(300, 900 - delay) for timeout in timeouts[2:])


def test_serial_and_concurrent_provider_timeouts_obey_300_and_remaining_turn(monkeypatch):
    now, external = [0.0], []

    def exa(query, *, search_type, timeout_seconds):
        external.append(("exa", query, search_type, timeout_seconds))
        return [DiscoveryCandidate("Original", f"https://example.org/{query}", VALUE,
                                   context_kind="provider_highlights")]

    def lexical(query, *, timeout_seconds):
        external.append(("serper", query, None, timeout_seconds))
        return [DiscoveryCandidate("Lexical original", "https://example.org/lexical", VALUE,
                                   context_kind="navigation")]

    def fetch(url, *, timeout_seconds):
        external.append(("linkup", url, None, timeout_seconds))
        return FetchedMaterial(url, "The full original establishes seven.")

    monkeypatch.setattr(research, "search_exa", exa)
    monkeypatch.setattr(research, "search_serper", lexical)
    monkeypatch.setattr(research, "fetch_linkup", fetch)

    def lexical_later(_payload):
        now[0] = 725
        return reply(initial(refs=["E1", "E2"], requests=[request("search_lexical", query="literal")]))

    def fetch_later(_payload):
        now[0] = 780
        return reply(initial(refs=["E1", "E2"], requests=[request("read", query="", target="https://example.org/first")]))

    def serial_later(_payload):
        now[0] = 850
        return reply(initial(refs=["E3"], requests=[request(query="last")]))

    model, _, _ = scripted(monkeypatch, [
        reply(initial(requests=[request(query="first"), request(query="second")])),
        lexical_later, fetch_later, serial_later,
        reply(initial("answer", ["E3", "E4"])), reply(answer("Both originals establish seven. [E3][E4]"))])
    result = run("What do these originals establish?", model=model, search=exa,
                 lexical_search=lexical, fetch=fetch, clock=lambda: now[0])
    first_group = {query: (mode, timeout) for provider, query, mode, timeout in external[:2] if provider == "exa"}
    assert first_group == {"first": ("deep", 300), "second": ("auto", 300)}
    assert [(provider, timeout) for provider, _query, _mode, timeout in external[2:]] == [
        ("serper", 175), ("linkup", 120), ("exa", 50)]
    assert result.posture == "supported" and result.trace[-1]["budget"]["external_attempts"] == 5


def test_delegated_worker_receives_earlier_failed_route_after_intervening_success(monkeypatch):
    calls = []

    def discover(query):
        calls.append(query)
        if len(calls) == 1:
            raise OSError("UNEXPOSED_PROVIDER_EXCEPTION_BODY")
        return search(query)

    def inspect_history(payload):
        state = packet(payload)
        assert state["last_route"][0]["status"] == "ok"
        history = state["prior_acquisition_history"]
        assert len(history) == 2
        assert history[0]["kind"] == "search" and history[0]["status"] == "error"
        assert history[0]["code"] == "search_failed" and history[0]["material_ids"] == []
        assert history[1]["status"] == "ok" and history[1]["material_ids"] == ["E1"]
        assert state["budget"]["external_attempts"] == 2
        return reply(delegated("return", ["E1"]))

    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request(query="first unsuccessful route")])),
        reply(initial(requests=[request(query="changed reason succeeds")])),
        reply(initial("answer", ["E1"])),
        tool("research", {"need": "Assess the retained original with its acquisition limitations."}, "r1"),
        inspect_history, reply(answer())])
    result = run("Establish the actual original value.", model=model, search=discover, fetch=prohibited)
    assert stages(payloads) == ["research", "research", "research", "answer", "research", "answer"]
    assert "UNEXPOSED_PROVIDER_EXCEPTION_BODY" not in json.dumps(payloads)
    assert result.posture == "supported" and result.trace[-1]["budget"]["external_attempts"] == 2
