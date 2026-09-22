"""Research-selected lexical discovery is navigation, with no provider fallback."""

import json

from test_model_transport import Response
from test_research_loop import Script, answer, decision, request

from core import exa_transport, linkup_transport, serper_transport
from core.exa_transport import DiscoveryCandidate
from core.transport import FetchedMaterial
from scryraven import __main__ as cli
from scryraven import model, reading_room
from scryraven.acquisition import AcquisitionLibrary
from scryraven.research import Request, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore

URL = "https://example.test/public-post"


def test_explicit_capability_dispatch_and_failure_isolation():
    calls = []

    def exa(query):
        calls.append(("exa", query))
        return []

    def serper(query):
        calls.append(("serper", query))
        return []

    library = AcquisitionLibrary(search=exa, lexical_search=serper)
    assert library.execute({"kind": "search", "query": "ordinary"}, before_external=lambda: None)["status"] == "ok"
    assert library.execute({"kind": "search_lexical", "query": "community"}, before_external=lambda: None)["status"] == "ok"
    assert calls == [("exa", "ordinary"), ("serper", "community")]

    def fail(query):
        calls.append(("failed", query))
        raise RuntimeError("private diagnostic")

    library = AcquisitionLibrary(search=exa, lexical_search=fail)
    assert library.execute({"kind": "search_lexical", "query": "post"}, before_external=lambda: None)["code"] == "search_failed"
    library = AcquisitionLibrary(search=fail, lexical_search=serper)
    assert library.execute({"kind": "search", "query": "fact"}, before_external=lambda: None)["code"] == "search_failed"
    assert calls[-2:] == [("failed", "post"), ("failed", "fact")]


def test_serper_candidate_requires_linkup_read_before_evidence():
    calls = []

    def lexical(query):
        calls.append(("serper", query))
        # Even a transport mistake cannot upgrade a Serper snippet to Evidence.
        return [DiscoveryCandidate("Public post", URL, "Snippet claims the answer is seven.",
                                   context_kind="provider_highlights")]

    def fetch(url):
        calls.append(("linkup", url))
        return FetchedMaterial(url, "The actual published source says seven.")

    library = AcquisitionLibrary(search=lambda q: calls.append(("exa", q)) or [],
                                 lexical_search=lexical, fetch=fetch)
    found = library.execute({"kind": "search_lexical", "query": "public post"}, before_external=lambda: None)
    assert found["candidate_refs"] == ["C1"]
    assert found["material_ids"] == found["new_acquisition_ids"] == []
    assert library.acquisitions == []
    assert library.catalog()["candidates"][0]["context"] == "Snippet claims the answer is seven."
    read = library.execute({"kind": "read", "target": "C1"}, before_external=lambda: None)
    assert read["material_ids"] == ["E1"]
    assert library.acquisitions[0].acquisition == "fetched_source"
    assert library.acquisitions[0].content == "The actual published source says seven."
    assert calls == [("serper", "public post"), ("linkup", URL)]
    assert library.execute({"kind": "read", "target": "C1"}, before_external=lambda: (_ for _ in ()).throw(AssertionError("external")))["local"]
    assert library.execute({"kind": "find", "query": "published"}, before_external=lambda: (_ for _ in ()).throw(AssertionError("external")))["local"]


def test_exa_serper_duplicate_url_keeps_candidate_and_source_identity():
    library = AcquisitionLibrary(
        search=lambda q: [DiscoveryCandidate("Exa", URL, "Exact highlight.", context_kind="provider_highlights")],
        lexical_search=lambda q: [DiscoveryCandidate("Serper", URL, "Navigation snippet")],
        fetch=lambda url: FetchedMaterial(url, "Fetched source."),
    )
    exa = library.execute({"kind": "search", "query": "fact"}, before_external=lambda: None)
    lexical = library.execute({"kind": "search_lexical", "query": "post"}, before_external=lambda: None)
    fetched = library.execute({"kind": "read", "target": "C1"}, before_external=lambda: None)
    assert exa["candidate_refs"] == lexical["candidate_refs"] == fetched["candidate_refs"] == ["C1"]
    assert exa["material_ids"] == ["E1"] and lexical["material_ids"] == []
    assert fetched["material_ids"] == ["E2"]
    assert [item.source_id for item in library.acquisitions] == ["E1", "E1"]


def test_research_and_session_can_choose_lexical_then_read():
    assert Request.model_validate(request("search_lexical", query="public post"))
    for kind, kwargs in (("search", {"query": "general"}),
                         ("read", {"query": "", "target": "C1"}),
                         ("find", {"query": "phrase"})):
        assert AcquisitionLibrary._request({"kind": kind, **kwargs})["kind"] == kind
    model = Script(
        decision(requests=[request("search_lexical", query="public post")]),
        decision(requests=[request("read", query="", target="C1")]),
        decision("answer", ["E1"]),
        answer("The source says seven. [E1]"),
    )
    calls = []
    kwargs = dict(model=model,
                  search=lambda q: calls.append(("exa", q)) or [],
                  lexical_search=lambda q: calls.append(("serper", q)) or [DiscoveryCandidate("Post", URL, "Answer seven")],
                  fetch=lambda url: calls.append(("linkup", url)) or FetchedMaterial(url, "The source says seven."))
    result = run("What does this public post say?", **kwargs)
    assert result.posture == "supported"
    assert [(event["result"]["kind"], event["result"]["material_ids"])
            for event in result.trace if event["action"] == "acquisition_result"] == [
                ("search_lexical", []), ("read", ["E1"])]
    assert calls == [("serper", "public post"), ("linkup", URL)]
    assert model.calls[1][2]["evidence"] == []
    assert model.calls[1][2]["catalog"]["candidates"][0]["context"] == "Answer seven"
    assert model.calls[2][2]["evidence"][0]["content"] == "The source says seven."

    model = Script(
        decision(requests=[request("search_lexical", query="public post")]),
        decision(requests=[request("read", query="", target="C1")]),
        decision("answer", ["E1"]), answer("The source says seven. [E1]"),
    )
    session = ResearchSession(**{**kwargs, "model": model})
    assert session.ask("What does this public post say?").posture == "supported"
    assert session.acquisitions[0].acquisition == "fetched_source"


def test_cli_uses_serper_then_linkup_through_ordinary_run(monkeypatch, capsys):
    for key in ("OPENAI_API_KEY", "SERPER_API_KEY", "LINKUP_API_KEY"):
        monkeypatch.setenv(key, "offline-test-value")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    outputs = iter([
        decision(requests=[request("search_lexical", query="public post")]),
        decision(requests=[request("read", query="", target="C1")]),
        decision("answer", ["E1"]), answer("The source says seven. [E1]"),
    ])
    providers = []

    def post(url, **kwargs):
        if url.endswith("/v1/responses"):
            return Response({"status": "completed", "output": [{"type": "message", "phase": "final_answer",
                             "content": [{"type": "output_text", "text": json.dumps(next(outputs))}]}]})
        providers.append(url)
        if url == serper_transport.SERPER_SEARCH_URL:
            return Response({"organic": [{"title": "Post", "link": URL, "snippet": "A claim"}]})
        if url == linkup_transport.LINKUP_FETCH_URL:
            return Response({"markdown": "The source says seven."})
        raise AssertionError("unexpected provider")

    monkeypatch.setattr(model.requests, "post", post)
    monkeypatch.setattr(serper_transport.requests, "post", post)
    monkeypatch.setattr(linkup_transport.requests, "post", post)
    monkeypatch.setattr(exa_transport.requests, "post", post)
    assert cli.main(["What does this public post say?"]) == 0
    assert "The source says seven. [1]" in capsys.readouterr().out
    assert providers == [serper_transport.SERPER_SEARCH_URL, linkup_transport.LINKUP_FETCH_URL]


def test_reading_room_uses_same_lexical_capability(tmp_path):
    from test_reading_room import submit

    model_script = Script(
        decision(requests=[request("search_lexical", query="public post")]),
        decision(requests=[request("read", query="", target="C1")]),
        decision("answer", ["E1"]), answer("The source says seven. [E1]"),
    )
    calls = []
    app = reading_room.create_app(
        store=SQLiteSessionStore(tmp_path / "sessions.sqlite3"),
        session_options={
            "model": model_script,
            "search": lambda q: calls.append(("exa", q)) or [],
            "lexical_search": lambda q: calls.append(("serper", q)) or [DiscoveryCandidate("Post", URL, "Claim")],
            "fetch": lambda url: calls.append(("linkup", url)) or FetchedMaterial(url, "The source says seven."),
        },
    )
    response = submit(app.test_client(), question="What does this public post say?")
    assert response.status_code == 303
    assert calls == [("serper", "public post"), ("linkup", URL)]
