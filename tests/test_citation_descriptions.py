"""Optional generated previews stay separate from custody and final validity."""

import json

import pytest
from pdf_fixtures import text_pdf
from test_research_first_resumable import (
    answer as native_answer,
)
from test_research_first_resumable import (
    delegated,
    initial,
    reply,
    request,
    scripted,
    stages,
    tool,
)
from test_research_loop import Script, answer, decision, multi_search, no_fetch, search
from test_research_loop import request as local_request

from core.exa_transport import DiscoveryCandidate
from scryraven.errors import RunError
from scryraven.research import SemanticAnswerDecision, run
from scryraven.results import resolve_citations
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore, _decode, _encode
from scryraven.sources import Evidence, exact_view


def preview(ref, text):
    return {"source_ref": ref, "description": text}


def test_grouped_and_repeated_citations_match_source_specific_descriptions():
    model = Script(decision(), decision("return", ["E1", "E2"]), {
        **answer("The first and second findings agree. [E2,E1] The first adds context. [E1]"),
        "citation_descriptions": [preview("E1", "The first source provides the main finding."),
                                  preview("E2", "The second source corroborates it.")],
    })
    result = run("Compare the findings.", model=model, search=multi_search, fetch=no_fetch)
    assert result.answer == "The first and second findings agree. [1] [2] The first adds context. [2]"
    assert [(c.source_id, c.description) for c in result.citations] == [
        ("E2", "The second source corroborates it."),
        ("E1", "The first source provides the main finding."),
    ]
    assert [use.number for use in result.citation_uses] == [1, 2, 2]
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert all("citation_descriptions" not in event.get("decision", {}) for event in result.trace)
    assert all("description" not in item.material() for item in result.evidence)


def test_multiple_actual_versions_and_excerpts_share_one_preview_without_changing_custody():
    first = Evidence("E1", "https://example.org/report?version=original#part", "Report", "First exact finding.")
    later = Evidence("E2", first.url, "Report updated", "Later exact finding.", source_id="E1")
    views = [exact_view(first, 0, 12), exact_view(later, 0, 12)]
    result, citations, uses = resolve_citations(
        "Two versions. [E1@0:12,E2@0:12] Repeated. [E2@0:12]", views, [first, later], [],
        descriptions=[preview("E2@0:12", "These saved versions contain the two findings."),
                      preview("E1", "A duplicate description is unnecessary.")],
    )
    citation, = citations
    assert result == "Two versions. [1] Repeated. [1]"
    assert citation.materials == tuple(views)
    assert citation.description == "These saved versions contain the two findings."
    assert citation.url == first.url and citation.title == first.title
    assert len(uses) == 2


def test_uncited_unavailable_invalid_and_unsupplied_description_aliases_are_ignored():
    first = Evidence("E1", "https://example.org/one", "One", "First fact. More context.")
    second = Evidence("E2", "https://example.org/two", "Two", "Second fact.")
    view = exact_view(first, 0, 11)
    _, citations, _ = resolve_citations(
        "First fact. [E1]", [view, second], [first, second], [],
        descriptions=[preview(ref, "This must not be displayed.") for ref in
                      ("E2", "E99", "C1", "E1@11:24", "E1@0:5", "1", "e1")],
    )
    assert len(citations) == 1 and citations[0].description is None
    with pytest.raises(RunError, match="invalid_citation_reference"):
        resolve_citations("Unseen. [E99]", [view], [first], [],
                          descriptions=[preview("E99", "Metadata cannot create membership.")])


@pytest.mark.parametrize("metadata", [
    None, "invalid", {}, [None, 4, []],
    [{"source_ref": "E1"}], [{"description": "Missing reference."}],
    [preview("E1", None)], [preview(1, "Wrong identity type.")],
    [preview("E1", "   \n ")], [preview("E1", "x" * 1201)],
    [{**preview("E1", "Extra shape."), "unsupported": True}],
])
@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_malformed_optional_metadata_cannot_invalidate_native_answer_or_request_correction(
    monkeypatch, metadata, backend,
):
    value = {**native_answer(), "citation_descriptions": metadata}
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("return", ["E1"])), reply(value)], backend)
    result = run("What value is stated?", model=model, search=search, fetch=no_fetch)
    assert result.answer == "Seven. [1]" and result.posture == "supported"
    assert result.citations[0].description is None
    assert stages(payloads) == ["research", "research", "answer"]
    assert not any(event["action"] == "response_rejected" for event in result.trace)


def test_preview_parser_keeps_valid_neighbors_and_strict_primary_contract():
    parsed = SemanticAnswerDecision.model_validate({
        **answer(), "citation_descriptions": [None, preview("E1", "  A specific\ncontribution.  "),
                                               preview("E2", ""), preview("E3", 8)],
    })
    assert [item.model_dump() for item in parsed.citation_descriptions] == [
        preview("E1", "A specific contribution.")]
    assert SemanticAnswerDecision.model_validate(answer()).citation_descriptions is None
    schema = SemanticAnswerDecision.model_json_schema()
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
    for changed in ({"posture": "invalid"}, {"answer": 6}, {"new_primary_field": True}):
        with pytest.raises(ValueError):
            SemanticAnswerDecision.model_validate({**answer(), **changed})
    with pytest.raises(ValueError):
        SemanticAnswerDecision.model_validate({"posture": "supported", "answer": "Missing basis."})


def test_native_citation_correction_and_delegation_remain_in_same_answer(monkeypatch):
    outputs = [
        reply(initial(requests=[request()])), reply(initial("return", ["E1"])),
        tool("research", {"need": "Establish the second finding."}, "need-second"),
        reply(delegated(requests=[request(query="second finding")])),
        reply(delegated("return", ["E2"])),
        reply({**native_answer("The findings are seven and nine."), "citation_descriptions": "bad"}),
        reply({**native_answer("The findings are seven [E1] and nine [E2]."),
               "citation_descriptions": [preview("E1", "States seven."), preview("E2", "States nine.")]}),
    ]
    model, payloads, _ = scripted(monkeypatch, outputs)

    def provider(query):
        if query == "second finding":
            return [DiscoveryCandidate("Second", "https://example.org/second", "Nine.",
                                       context_kind="provider_highlights")]
        return search(query)

    result = run("What are both findings?", model=model, search=provider, fetch=no_fetch)
    assert result.posture == "supported" and result.answer == "The findings are seven [1] and nine [2]."
    assert [c.description for c in result.citations] == ["States seven.", "States nine."]
    assert stages(payloads) == ["research", "research", "answer", "research", "research", "answer", "answer"]
    assert [event["code"] for event in result.trace if event["action"] == "response_rejected"] == ["missing_citation"]
    assert payloads[-1]["input"][:len(payloads[-2]["input"])] == payloads[-2]["input"]


@pytest.mark.parametrize("posture", ["supported", "partial", "unable"])
def test_source_free_answers_ignore_all_preview_metadata(posture):
    primary = answer("Only the stipulated premise is available.", posture,
                     missing="No external value is established." if posture == "partial" else None,
                     support_basis="none" if posture == "unable" else "user_premises")
    model = Script(decision("return"), {**primary, "citation_descriptions": [preview("E1", "Invented.")]})
    result = run("Assume seven as the stipulated value.", model=model, search=no_fetch, fetch=no_fetch)
    assert result.answer == primary["answer"] and result.posture == posture
    assert result.citations == result.selected_evidence == ()
    assert len(model.calls) == 2


def test_partial_previews_survive_storage_and_reopening_without_entering_research_context(tmp_path):
    store = SQLiteSessionStore(tmp_path / "previews.sqlite3")
    description = 'The source states seven, with <literal> & "quoted" wording.'
    model = Script(decision(), decision("return", ["E1"]), {
        **answer("Seven is established. [E1] The second value remains unverified.", "partial", missing="Second value"),
        "citation_descriptions": [preview("E1", description)],
    })
    session = ResearchSession.create(store=store, model=model, search=search, fetch=no_fetch)
    result = session.ask("What are the first and second values?")
    restored = ResearchSession.open(session.session_id, store=store, model=Script(
        decision("return"), answer("No further conclusion is available.", "unable")),
        search=no_fetch, fetch=no_fetch)
    assert restored.turns == session.turns
    assert restored.turns[0].citations[0].description == description
    assert restored.turns[0].citations[0].url == result.citations[0].url == "https://example.org/fact"
    assert restored.turns[0].selected_evidence == result.selected_evidence
    restored.ask("What remains unresolved?")
    assert all(description not in json.dumps(call[2]) for call in restored._model.calls)
    assert store.load(session.session_id).state.turns[0] == session.turns[0]


def test_historical_records_without_previews_decode_and_reencode_without_backfill():
    from pathlib import Path

    raw = (Path(__file__).parent / "fixtures/historical_session_v1.json").read_text(encoding="utf-8")
    state = _decode(raw, 1)
    assert all(c.description is None for t in state.turns for c in t.citations)
    assert json.loads(_encode(state)) == json.loads(raw)


def test_document_preview_keeps_exact_extracted_material_and_original_pdf(tmp_path):
    store = SQLiteSessionStore(tmp_path / "document-previews.sqlite3")
    saved = store.create()
    pdf = text_pdf(["The crane count is fourteen."])
    attached = store.attach_document(saved.metadata.session_id, 0, "cranes.pdf", "application/pdf", pdf)
    view_id = f"D1@0:{len(attached.document.extracted_text)}"
    model = Script(
        decision(requests=[local_request("read", target="D1", mode="local")]),
        decision("return", [view_id]),
        {**answer("The document reports fourteen cranes. [D1]"),
         "citation_descriptions": [preview(view_id, "Reports a count of fourteen cranes.")]},
    )
    session = ResearchSession.open(saved.metadata.session_id, store=store, model=model,
                                   search=no_fetch, fetch=no_fetch)
    result = session.ask("What crane count does the attached document report?")
    citation, = result.citations
    assert citation.source_id == citation.document_id == "D1"
    assert citation.description == "Reports a count of fourteen cranes."
    assert citation.url == "" and citation.filename == "cranes.pdf"
    assert citation.page_start == citation.page_end == 1
    assert citation.materials[0].content == attached.document.extracted_text
    reopened = ResearchSession.open(session.session_id, store=store)
    assert reopened.turns[0].citations == result.citations
    assert reopened.documents[0].original_pdf == pdf
