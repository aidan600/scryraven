"""Neutral completed-answer custody and citation mechanics; no live cognition claims."""

import json
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest

from scryraven import __main__ as cli
from scryraven.presentation import render_html
from scryraven.research import RunError
from scryraven.results import CompletedAnswer, resolve_citations
from scryraven.session import ResearchSession
from scryraven.session_store import SessionConflictError, SessionStoreError, SQLiteSessionStore
from scryraven.sources import Evidence, exact_view


@pytest.fixture
def tmp_path():
    with tempfile.TemporaryDirectory(prefix="scryraven-v2-session-") as directory:
        yield Path(directory)


def completed(draft, selected, acquisitions, posture="supported"):
    trace = []
    answer, citations, uses = resolve_citations(draft, selected, acquisitions, trace,
                                               require_citation=posture != "unable")
    return CompletedAnswer(answer, posture, "supported" if posture == "supported" else "not_established",
                           tuple(acquisitions), tuple(trace), tuple(selected), citations, uses)


def test_exact_aliases_share_canonical_number_and_only_supplied_material():
    original = Evidence("E1", "https://example.org/source", "Original", "first version")
    updated = Evidence("E2", original.url, "Updated title", "prefix first second suffix", source_id="E1")
    other = Evidence("E3", "https://example.org/other", "Other", "other material")
    first, second = exact_view(updated, 7, 12), exact_view(updated, 13, 19)
    answer = completed("Other [E3]. Both [[E2@7:12], [E2@13:19]]. Again [E1].",
                       [first, second, other], [original, updated, other])
    assert answer.answer == "Other [1]. Both [2]. Again [2]."
    assert [c.source_id for c in answer.citations] == ["E3", "E1"]
    assert answer.citations[1].materials == (first, second)
    assert answer.citations[1].title == "Original"
    assert all(answer.answer[use.start:use.end] == f"[{use.number}]" for use in answer.citation_uses)
    assert "prefix" not in render_html("Question", answer)


@pytest.mark.parametrize("draft", [
    "No citation", "Numeric [1]", "Unseen parent [E2]", "Unseen view [E2@0:6]",
    "Unknown [E9]", "Malformed [E2@7:12", "Nested [[[E1]]]", r"Escaped \[E1]",
    "Code `[E1]`", "Link [source](https://example.org/source)",
])
def test_unsupplied_or_noninspectable_citations_fail(draft):
    original = Evidence("E1", "https://example.org/source", "Original", "old")
    parent = Evidence("E2", original.url, "Updated", "prefix first suffix", source_id="E1")
    with pytest.raises(RunError) as caught:
        completed(draft, [exact_view(parent, 7, 12)], [original, parent])
    assert caught.value.stage == "citations"
    assert draft not in json.dumps(caught.value.trace)


def test_fabricated_view_cannot_become_cited_material():
    parent = Evidence("E1", "https://example.org/source", "Source", "actual exact text")
    forged = replace(exact_view(parent, 0, 6), content="forged")
    with pytest.raises(RunError, match="invalid_selected_material"):
        completed("Assertion [E1@0:6]", [forged], [parent])


def test_neutral_reopen_retained_followup_and_same_source_refresh_preserve_history(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    source = Evidence("E1", "https://example.org/source", "Original", "first fact; second fact")
    view = exact_view(source, 0, 10)

    def first_engine(question, **kwargs):
        assert kwargs["retained_acquisitions"] == ()
        return completed("First fact [E1@0:10].", [view], [source])

    session = ResearchSession.create(store=SQLiteSessionStore(path), engine=first_engine)
    first = session.ask("What is the first fact?")
    session_id = session.session_id
    historical_html = render_html(session.turns[0].question, session.turns[0])
    assert not hasattr(first, "analysis")
    assert session.turns[0].analysis is None
    del session

    def followup(question, **kwargs):
        assert kwargs["retained_acquisitions"] == (source,)
        assert "semantic_history" not in kwargs["context"]
        assert kwargs["context"]["conversation_context"] == [
            {"question": "What is the first fact?", "answer": first.answer}]
        return completed("Second fact [E1@12:23].", [exact_view(source, 12, 23)], [source])

    session = ResearchSession.open(session_id, store=SQLiteSessionStore(path), engine=followup)
    session.ask("And the second?")
    assert session.acquisitions == (source,)
    assert session.turns[0].selected_evidence == (view,)
    refreshed = Evidence("E2", source.url, "Later title", "updated fact", source_id="E1")
    session = ResearchSession.open(session_id, store=SQLiteSessionStore(path),
        engine=lambda question, **kwargs: completed("Updated [E2].", [refreshed], [source, refreshed]))
    session.ask("What changed?")
    restored = ResearchSession.open(session_id, store=SQLiteSessionStore(path))
    assert restored.turns[0].citations[0].materials == (view,)
    assert render_html(restored.turns[0].question, restored.turns[0]) == historical_html
    assert restored.turns[2].citations[0].materials == (refreshed,)
    assert restored.metadata.revision == 3
    with closing(sqlite3.connect(path)) as connection:
        payload = json.loads(connection.execute("SELECT payload FROM sessions").fetchone()[0])
    assert all(turn["analysis"] is None for turn in payload["turns"])
    assert set(payload["turns"][0]) == {
        "question", "answer", "analysis", "posture", "stop_reason", "selected_evidence", "citations", "citation_uses"}


def test_neutral_failure_and_commit_failure_leave_completed_state_unchanged(tmp_path, monkeypatch):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    source = Evidence("E1", "https://example.org/source", "Source", "fact")
    session = ResearchSession.create(store=store,
        engine=lambda question, **kwargs: completed("Fact [E1]", [source], [source]))
    session.ask("Question")
    before = store.load(session.session_id)
    memory = session.turns, session.acquisitions, session.metadata

    def failure(question, **kwargs):
        raise RunError("answer", "invalid_output", [])

    session._engine = failure
    with pytest.raises(RunError):
        session.ask("Failed research")
    assert (session.turns, session.acquisitions, session.metadata) == memory
    assert store.load(session.session_id) == before
    session._engine = lambda question, **kwargs: completed("Fact [E1]", [source], [source])

    def failed_commit(*args):
        raise SessionStoreError()

    monkeypatch.setattr(store, "commit", failed_commit)
    with pytest.raises(SessionStoreError):
        session.ask("Failed commit")
    assert (session.turns, session.acquisitions, session.metadata) == memory
    assert store.load(session.session_id) == before


def test_neutral_stale_writer_does_not_advance_memory(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    engine = lambda question, **kwargs: completed("Unable to establish this.", [], [], "unable")
    first = ResearchSession.create(store=store, engine=engine)
    second = ResearchSession.open(first.session_id, store=store, engine=engine)
    first.ask("Winner")
    with pytest.raises(SessionConflictError):
        second.ask("Stale")
    assert second.turns == () and second.metadata.revision == 0
    assert store.load(first.session_id).metadata.revision == 1


def test_unable_can_preserve_read_packet_without_invented_citation(tmp_path):
    source = Evidence("E1", "https://example.org/source", "Source", "related but insufficient text")
    result = completed("The supplied material does not establish this.", [source], [source], "unable")
    session = ResearchSession.create(store=SQLiteSessionStore(tmp_path / "sessions.sqlite3"),
                                    engine=lambda question, **kwargs: result)
    session.ask("Question")
    saved = ResearchSession.open(session.session_id, store=SQLiteSessionStore(tmp_path / "sessions.sqlite3"))
    assert saved.turns[0].selected_evidence == (source,) and saved.turns[0].citations == ()


def test_neutral_partial_requires_citation_for_selected_material_before_session_commit(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    source = Evidence("E1", "https://example.org/source", "Source", "A documented part of the answer.")
    uncited = CompletedAnswer("An unsupported partial assertion.", "partial", "not_established",
                              (source,), (), (source,), (), ())
    session = ResearchSession.create(store=store, engine=lambda question, **kwargs: uncited)
    with pytest.raises(SessionStoreError, match="invalid_session_data"):
        session.ask("Question")
    assert session.turns == () and session.metadata.revision == 0
    assert store.load(session.session_id).state.turns == ()

    cited = completed("A documented part. [E1] The remainder is unresolved.", [source], [source], "partial")
    session._engine = lambda question, **kwargs: cited
    session.ask("Question")
    reopened = ResearchSession.open(session.session_id, store=store)
    assert reopened.turns[0].posture == "partial"
    assert reopened.turns[0].citations[0].materials == (source,)


def test_cli_routes_isolated_and_durable_calls_through_ordinary_engine(tmp_path, monkeypatch, capsys):
    from scryraven import session
    from scryraven.research import RunLimits

    calls = []
    result = completed("Unable to establish this.", [], [], "unable")

    def engine(question, **kwargs):
        calls.append((question, kwargs))
        return result

    monkeypatch.setattr(cli, "run", engine)
    monkeypatch.setattr(session, "_run_turn", engine)
    assert cli.main(["Isolated question"]) == 0
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    path = tmp_path / "sessions.sqlite3"
    assert cli.main(["--create-session", "--database", str(path), "Saved question"]) == 0
    assert len(calls) == 2 and isinstance(calls[1][1]["limits"], RunLimits)
    session_id = SQLiteSessionStore(path).list_sessions()[0].session_id
    assert cli.main(["--resume", session_id, "--database", str(path)]) == 0
    assert len(calls) == 2
    assert "Saved question" in capsys.readouterr().out
