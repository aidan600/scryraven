"""Ordinary follow-ups start Research with the last turn's exact cited text."""

from test_research_loop import Script, answer, decision

from scryraven.presentation import Citation, CitationUse
from scryraven.research import RunLimits
from scryraven.session import ResearchSession
from scryraven.session_store import SessionState, SessionTurn, SQLiteSessionStore
from scryraven.sources import Evidence, exact_view


def no_external(*args, **kwargs):
    raise AssertionError("Unexpected provider I/O")


def saved_cited_turn(material, text="An earlier answer [1]."):
    marker = text.index("[1]")
    return SessionTurn(
        "What did the earlier source establish?", text, None, "supported", "supported",
        (material,),
        (Citation(1, material.source_id, material.title, material.url, (material,)),),
        (CitationUse(1, marker, marker + 3),),
    )


def test_reopened_session_exposes_exact_prior_view_in_first_research_call(tmp_path):
    body = "Unselected preface. The exact retained finding is 17 units. Unselected ending."
    parent = Evidence("E1", "https://example.test/prior", "Prior publication", body)
    start = body.index("The exact retained finding")
    end = body.index(" Unselected ending.")
    view = exact_view(parent, start, end)
    seed_store = SQLiteSessionStore(tmp_path / "seed.sqlite3")
    seed = seed_store.create()
    seed_store.commit(seed.metadata.session_id, 0,
                      SessionState((saved_cited_turn(view),), (parent,)))

    cited_answer = answer(f"The finding is 17 units. [{view.id}]", readings=[
        {"evidence_ref": view.id, "passages": [view.content]},
    ])
    model = Script(decision("answer", [view.id]), cited_answer)
    session = ResearchSession.open(seed.metadata.session_id, store=SQLiteSessionStore(seed_store.path),
                                   model=model, search=no_external, fetch=no_external)
    result = session.ask("What was that exact finding?")

    research = [packet for stage, _, packet, _ in model.calls if stage == "research"]
    assert len(research) == 1
    assert research[0]["evidence"] == [view.material()]
    assert not any(event["action"] == "acquisition_timing" for event in result.trace)
    assert result.selected_evidence == (view,)
    assert [item["id"] for item in model.calls[-1][2]["evidence"]] == [view.id]
    assert session.acquisitions == (parent,)


def test_only_immediately_prior_citations_are_preexposed_and_answer_is_not_selected(tmp_path):
    older = Evidence("E1", "https://example.test/older", "Older publication", "Older source fact.")
    latest_material = Evidence("E2", "https://example.test/latest", "Latest publication", "Latest source fact.")
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = store.create()
    first = saved_cited_turn(older)
    latest = saved_cited_turn(latest_material)
    store.commit(saved.metadata.session_id, 0, SessionState((first,), (older,)))
    store.commit(saved.metadata.session_id, 1,
                 SessionState((first, latest), (older, latest_material)))
    model = Script(decision("answer"), answer("Still unresolved.", "unable"))
    session = ResearchSession.open(saved.metadata.session_id, store=store, model=model,
                                   search=no_external, fetch=no_external)
    session.ask("And now?")
    assert [item["id"] for item in model.calls[0][2]["evidence"]] == [latest_material.id]
    assert model.calls[1][2]["evidence"] == []


def test_uncited_immediate_turn_does_not_reach_back_to_older_citations(tmp_path):
    older = Evidence("E1", "https://example.test/older", "Older publication", "Older source fact.")
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = store.create()
    first = saved_cited_turn(older)
    uncited = SessionTurn("Was more learned?", "That remains unresolved.", None,
                           "unable", "not_established")
    store.commit(saved.metadata.session_id, 0, SessionState((first,), (older,)))
    store.commit(saved.metadata.session_id, 1, SessionState((first, uncited), (older,)))
    model = Script(decision("answer"), answer("Still unresolved.", "unable"))
    session = ResearchSession.open(saved.metadata.session_id, store=store, model=model,
                                   search=no_external, fetch=no_external)
    session.ask("And now?")
    assert model.calls[0][2]["evidence"] == []


def test_prior_cited_exposure_is_all_or_none_at_attention_bound(tmp_path):
    first = Evidence("E1", "https://example.test/first-large", "First large publication", "x" * 35_000)
    second = Evidence("E2", "https://example.test/second-large", "Second large publication", "y" * 35_000)
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = store.create()
    text = "Earlier conclusions [1] and [2]."
    first_use, second_use = text.index("[1]"), text.index("[2]")
    prior = SessionTurn(
        "What did the two publications establish?", text, None, "supported", "supported",
        (first, second),
        (Citation(1, first.source_id, first.title, first.url, (first,)),
         Citation(2, second.source_id, second.title, second.url, (second,))),
        (CitationUse(1, first_use, first_use + 3), CitationUse(2, second_use, second_use + 3)),
    )
    store.commit(saved.metadata.session_id, 0,
                 SessionState((prior,), (first, second)))
    model = Script(decision("answer"), answer("Still unresolved.", "unable"))
    session = ResearchSession.open(
        saved.metadata.session_id, store=store, model=model,
        search=no_external, fetch=no_external,
        limits=RunLimits(attention_characters=65_536),
    )
    session.ask("What can be said now?")
    assert model.calls[0][2]["evidence"] == []
    assert [item["id"] for item in model.calls[0][2]["catalog"]["materials"]] == ["E1", "E2"]
    assert not any(item["exposed"] for item in model.calls[0][2]["catalog"]["materials"])
