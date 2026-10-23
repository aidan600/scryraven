"""Exact local exposure, continuation, and durable citation boundaries."""
import json
from copy import deepcopy

import pytest
from pdf_fixtures import text_pdf
from test_answer_calculator_runtime_01 import ScriptedResponses, model_reply, tool_reply
from test_pdf_documents import owned
from test_production_plan_transport import ENCRYPTED, FrozenAuth, Reply, Stream
from test_research_loop import answer, decision

from scryraven.acquisition import AcquisitionLibrary
from scryraven.answer_library import MAX_OPERATIONS, AnswerLibrary
from scryraven.model import OpenAIModel, built_in_model_config
from scryraven.research import RunError, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import Evidence


def forbidden(*args, **kwargs):
    pytest.fail("Local Answer inspection dispatched external I/O")


def corpus():
    return (Evidence("E1", "https://example.org/a", "Selected", "The initial result was seven.", "provider_highlights"),
            Evidence("E2", "https://example.org/b", "Unselected", "The qualifying condition is winter.", "provider_highlights"))


def adapter(items=None, refs=None, **kwargs):
    lib = AcquisitionLibrary(items or corpus(), search=forbidden, fetch=forbidden, lexical_search=forbidden)
    return AnswerLibrary(lib, refs if refs is not None else ["E1"], **kwargs)


def read_args(target, **kwargs):
    return {"target": target, "focus": "", "start_char": None, "end_char": None, **kwargs}


def call(local, name, args):
    return local(name, json.dumps(args))


def function_reply(name, arguments, call_id="lib1"):
    reply = model_reply({})
    reply["output"] = [
        {"type": "reasoning", "encrypted_content": ENCRYPTED},
        {"type": "function_call", "name": name, "arguments": json.dumps(arguments), "call_id": call_id}]
    return reply


def test_catalog_is_navigation_and_find_exposes_unselected_exact_text():
    events, refs = [], ["E1"]
    local = adapter(refs=refs, emit=lambda action, **fields: events.append({"action": action, **fields}))
    original = deepcopy(local.library.acquisitions)
    assert [r["id"] for r in local.catalog()["entries"]] == ["E1", "E2"]
    assert "winter" not in json.dumps(local.catalog()) and refs == ["E1"]
    result = call(local, "library_find", {"query": "qualifying winter", "scope": []})
    assert result["evidence"] == [corpus()[1].material()]
    assert refs == ["E1", "E2"] and local.library.acquisitions == original
    safe = events[0]
    assert safe["exposed"][0]["id"] == "E2" and len(safe["exposed"][0]["sha256"]) == 64
    assert "winter" not in json.dumps(safe) and not safe["external"]


@pytest.mark.parametrize("name,args", [
    ("library_read", read_args("E99")), ("library_read", read_args("C99")),
    ("library_read", read_args("https://unrelated.example/")),
    ("library_read", read_args("C:/private/file")),
    ("library_read", {**read_args("E1"), "mode": "refresh"}),
    ("library_read", read_args("E1", start_char=True, end_char=8)),
    ("library_read", read_args("E1", start_char=0, end_char=None)),
    ("library_find", {"query": "winter", "scope": [1]}),
    ("library_browse", {"offset": -1}), ("search", {"query": "test"}),
])
def test_invalid_arguments_and_references_are_local_errors(name, args):
    local = adapter()
    assert "error" in call(local, name, args)
    assert local.refs == ["E1"]


def test_paging_versions_and_highlights_do_not_grant_full_webpage():
    items = [Evidence(f"E{i}", "https://example.org/same", f"Version {i}", f"Excerpt {i}",
                      "provider_highlights", "E1") for i in range(1, 29)]
    local = adapter(items)
    page = local.catalog()
    assert page["total"] == 28 and page["next_offset"] == 24 and len(page["entries"]) == 24
    tail = call(local, "library_browse", {"offset": 24})
    assert tail["entries"][0]["id"] == "E25" and tail["next_offset"] is None
    result = call(local, "library_read", read_args("E2"))
    assert result["evidence"] == [items[1].material()]
    view = call(local, "library_read", read_args("E2", start_char=0, end_char=5))["evidence"][0]
    assert view["content"] == "Excer" and view["range_basis"] == "acquired_highlight"
    local.library._candidate("https://example.org/navigation-only", "Navigation fact")
    assert call(local, "library_read", read_args("C2")) == {"error": "local_material_unavailable"}


def test_large_body_exact_views_and_attention_are_bounded():
    body = "Ordinary filler. " * 20_000 + "\nOperative provision: winter applies.\n" + "Tail. " * 5000
    item = Evidence("E1", "https://example.org/large", "Regulation", body)
    local = adapter([item], refs=[], attention_characters=40_000)
    result = call(local, "library_find", {"query": "operative provision winter", "scope": ["E1"]})
    assert 0 < result["text_characters_returned"] <= 32_000
    for row in result["evidence"]:
        assert row["content"] == body[row["start_char"]:row["end_char"]]
        assert row["parent_id"] == "E1"
    first = result["evidence"][0]
    again = call(local, "library_read", read_args(first["id"], focus="other"))
    assert again["evidence"] == [first]
    assert local.library.acquisitions == [item]
    assert "error" in call(local, "library_read", read_args("E1", start_char=0, end_char=len(body)))
    for _ in range(MAX_OPERATIONS):
        call(local, "library_browse", {"offset": 0})
    assert call(local, "library_read", read_args("E1"))["error"] == "library_operation_limit"


def test_large_admitted_highlight_is_read_whole_without_invented_coordinates():
    item = Evidence("E1", "https://example.org/highlight", "Large highlight",
                    "Exact acquired excerpt. " * 2200, "provider_highlights")
    local = adapter([item], refs=[])
    result = call(local, "library_read", read_args("E1"))
    assert result["evidence"] == [item.material()]
    assert result["text_characters_returned"] == len(item.content)
    assert result["evidence"][0]["start_char"] is None
    assert local.remaining == 128_000 - len(item.content)


def test_session_documents_remain_local_and_unrelated_session_is_empty():
    doc = owned(text_pdf(["Document's qualifying condition is winter."]))
    lib = AcquisitionLibrary(documents=(doc,), search=forbidden, fetch=forbidden)
    local = AnswerLibrary(lib, [])
    result = call(local, "library_read", read_args("D1"))
    assert result["evidence"] and result["evidence"][0]["source_kind"] == "user_document"
    assert result["evidence"][0]["page_start"] == 1
    other = AnswerLibrary(AcquisitionLibrary(), [])
    assert other.catalog()["total"] == 0
    assert call(other, "library_read", read_args("D1"))["error"] == "unknown_target"


def test_api_multiple_tools_correction_and_durable_reopen(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic")
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0),
        ("answer", function_reply("library_find", {"query": "winter", "scope": []}), 0),
        ("answer", tool_reply("7 * 2", "calc"), 0),
        ("answer", function_reply("library_read", read_args("E1"), "lib2"), 0),
        ("answer", model_reply(answer("Winter applies, with fourteen units.")), 0),
        ("answer", model_reply(answer("Winter applies [E2], with fourteen derived units [E1].")), 0),
    )
    model = OpenAIModel(post=transport.post, config=built_in_model_config())
    store = SQLiteSessionStore(tmp_path / "session.sqlite3")
    saved = store.create()
    from scryraven.results import resolve_citations
    from scryraven.session_store import SessionState, SessionTurn
    text, citations, uses = resolve_citations("Seven [E1].", [corpus()[0]], list(corpus()), [])
    prior = SessionTurn("Initial?", text, None, "supported", "supported", (corpus()[0],), citations, uses)
    store.commit(saved.metadata.session_id, saved.metadata.revision, SessionState((prior,), corpus()))
    session = ResearchSession.open(saved.metadata.session_id, store=store, model=model,
                                   search=forbidden, fetch=forbidden)
    result = session.ask("What conditions govern the result?")
    assert {i.id for i in result.selected_evidence} == {"E1", "E2"}
    assert result.trace[-1]["budget"]["external_attempts"] == 0
    assert len([e for e in result.trace if e["action"] == "model_request_finished"]) == 6
    assert ENCRYPTED in json.dumps(transport.calls[3]["json"]["input"])
    reopened = ResearchSession.open(session.session_id, store=store, model=forbidden)
    assert reopened.turns == session.turns
    assert reopened.turns[-1].selected_evidence == result.selected_evidence
    correction_input = json.dumps(transport.calls[-1]["json"])
    assert "winter" in correction_input and "missing_citation" in correction_input


def test_catalog_only_citation_is_rejected(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic")
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0),
        ("answer", model_reply(answer("Winter applies [E2].")), 0))
    with pytest.raises(RunError):
        run("Conditions?", model=OpenAIModel(post=transport.post), retained_acquisitions=corpus(),
            search=forbidden, fetch=forbidden)


class LocalReply:
    def __init__(self, name, args):
        self.name, self.args = name, args

    def stream(self, payload):
        output = function_reply(self.name, self.args)["output"]
        for index, item in enumerate(output):
            item["id"] = f"item{index}"
        return Stream([{"type": "response.completed", "response": {
            "status": "completed", "model": payload["model"], "output": output}}])


def test_plan_declared_library_tools_and_opaque_continuation():
    auth = FrozenAuth(Reply("research", decision("answer")),
                      LocalReply("library_read", read_args("E2")),
                      Reply("answer", answer("Winter applies [E2].")))
    model = OpenAIModel(built_in_model_config(), backend="chatgpt_plan", plan_auth=auth)
    result = run("Conditions?", model=model, retained_acquisitions=corpus(), search=forbidden, fetch=forbidden)
    assert result.selected_evidence == (corpus()[1],)
    assert ENCRYPTED in json.dumps(auth.calls[-1])
    assert ENCRYPTED not in json.dumps(result.trace)


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_undeclared_function_rejected_in_both_transports(monkeypatch, backend):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic")
    if backend == "api":
        transport = ScriptedResponses(("research", model_reply(decision("answer")), 0),
                                      ("answer", function_reply("fetch_web", {}), 0))
        model = OpenAIModel(post=transport.post)
    else:
        auth = FrozenAuth(Reply("research", decision("answer")), LocalReply("fetch_web", {}))
        model = OpenAIModel(backend=backend, plan_auth=auth)
    with pytest.raises(RunError, match="malformed_model_response"):
        run("Conditions?", model=model, retained_acquisitions=corpus(), search=forbidden, fetch=forbidden)








def test_multiple_local_calls_and_calculator_in_one_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic")
    batch = function_reply("library_read", read_args("E2"))
    batch["output"].extend(tool_reply("7 * 2", "calc")["output"])
    transport = ScriptedResponses(
        ("research", model_reply(decision("answer")), 0), ("answer", batch, 0),
        ("answer", model_reply(answer("Winter applies [E2].")), 0))
    result = run("Conditions?", model=OpenAIModel(post=transport.post), retained_acquisitions=corpus(),
                 search=forbidden, fetch=forbidden)
    outputs = [i for i in transport.calls[-1]["json"]["input"] if i.get("type") == "function_call_output"]
    assert [i["call_id"] for i in outputs] == ["lib1", "calc"]
    assert json.loads(outputs[1]["output"]) == {"value": "14"}
    assert result.selected_evidence == (corpus()[1],)
