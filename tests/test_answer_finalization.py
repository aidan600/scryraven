"""Publish primary work with exact custody and generic saved-material inspection."""

import json
from dataclasses import replace

import pytest
from test_research_loop import Script, answer, decision, no_fetch, search

from scryraven import reading_room
from scryraven.research import SemanticAnswerDecision, run
from scryraven.results import resolve_citations
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import Evidence, exact_view


@pytest.mark.parametrize("posture", ["supported", "partial"])
def test_valid_primary_answer_is_final_and_reader_opens_saved_material(tmp_path, posture):
    primary = answer("The stated value is seven. [E1]", posture)
    model = Script(decision(), decision("answer", ["E1"]), primary)
    store = SQLiteSessionStore(tmp_path / "answers.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=search, fetch=no_fetch)
    result = session.ask("What value is stated?")

    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert result.answer == primary["answer"].replace("[E1]", "[1]")
    assert result.posture == posture
    assert result.citations[0].materials == result.selected_evidence
    assert all(not use.support for use in result.citation_uses)
    reopened = ResearchSession.open(session.session_id, store=store)
    assert reopened.turns == session.turns
    html = reading_room.create_app(store=store).test_client().get(
        f"/sessions/{session.session_id}").get_data(as_text=True)
    assert 'data-citation-start="' in html
    assert "The stated value is seven." in html
    assert "Material ScryRaven used from this source" in html
    assert "Open original publication" in html
    assert "Support for this citation" not in html
    assert '<mark class="support-text"' not in html


def test_retired_reading_output_is_not_a_second_answer_contract():
    with pytest.raises(ValueError):
        SemanticAnswerDecision.model_validate({**answer(), "source_readings": []})
    assert set(SemanticAnswerDecision.model_fields) == {
        "posture", "support_basis", "answer", "missing_information"}


@pytest.mark.parametrize("draft", ["Fact [E2]", "Fact [E1@0:5]"])
def test_unknown_alias_or_unsupplied_version_still_fails_custody(draft):
    parent = Evidence("E1", "https://example.org/source", "Source", "First fact. Later fact.")
    selected = exact_view(parent, 0, 11)
    from scryraven.errors import RunError

    with pytest.raises(RunError, match="invalid_citation_reference"):
        resolve_citations(draft, [selected], [parent], [])
    with pytest.raises(RunError, match="invalid_selected_material"):
        resolve_citations("Fact [E1]", [replace(selected, content="Wrong text.")], [parent], [])


@pytest.mark.parametrize("first,second", [
    ('{"posture":', answer("Still missing a required citation.")),
    (json.dumps(answer("No citation.")), {**answer(), "posture": "invalid"}),
])
def test_shape_and_citation_errors_share_the_existing_single_correction(first, second):
    model = Script(decision(), decision("answer", ["E1"]), first, second)
    result = run("What value is stated?", model=model, search=search, fetch=no_fetch)
    assert [call[0] for call in model.calls] == ["research", "research", "answer", "answer"]
    assert result.posture == "unable" and result.citations == result.selected_evidence == ()
    assert result.answer == "I couldn't complete a source-validated answer for this request."
    assert model.calls[-2][2]["evidence"] == model.calls[-1][2]["evidence"]
