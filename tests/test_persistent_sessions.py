"""Durable-session promises through the existing engine, with only external I/O faked."""

import json
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

import pytest
from test_research_session import (
    ANSWER_A,
    BODY,
    FACT_A,
    FACT_B,
    FACT_C,
    Q1,
    Q2,
    Q3,
    URL_A,
    URL_B,
    Provider,
    Script,
    assess,
    candidate,
    first_turn,
    inspect,
    select_packet,
)
from test_source_acquisition import use
from test_walking_skeleton import analysis, author, done, orient, relevance, search_for

from scryraven import __main__ as cli
from scryraven import research
from scryraven.model import ModelError
from scryraven.presentation import render_cli, render_html
from scryraven.research import RunError, run
from scryraven.session import ResearchSession
from scryraven.session_store import (
    SessionConflictError,
    SessionStoreError,
    SQLiteSessionStore,
    default_session_path,
)
from scryraven.sources import PACKET_CHARACTERS


@pytest.fixture
def tmp_path():
    # The repository's general pytest basetemp can live inside the checkout.
    # Session databases must stay external even when pytest runs without flags.
    root = Path(tempfile.gettempdir()).resolve()
    assert not root.is_relative_to(Path(__file__).resolve().parents[1])
    with tempfile.TemporaryDirectory(prefix="scryraven-session-test-", dir=root) as directory:
        yield Path(directory)


def no_io(*args, **kwargs):
    raise AssertionError("Unexpected model/provider I/O")


def opening(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    provider = Provider([candidate()])
    session = ResearchSession.create(store=SQLiteSessionStore(path), model=Script(*first_turn()),
                                     search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    return path, session, first


def reopen(path, session_id, **kwargs):
    return ResearchSession.open(session_id, store=SQLiteSessionStore(path),
                                **({"model": no_io, "search": no_io, "fetch": no_io} | kwargs))


@pytest.mark.parametrize("highlights", [True, False])
def test_create_reopen_followup_new_source_and_exact_history(tmp_path, highlights):
    path = tmp_path / "sessions.sqlite3"
    store = SQLiteSessionStore(path)
    provider = Provider([candidate(context=BODY, highlights=True)] if highlights else [candidate()])
    first_script = (orient(Q1), search_for(Q1), use("C1"), assess(Q1, FACT_A, "E1"),
                    author(ANSWER_A + " [E1]")) if highlights else first_turn()
    session = ResearchSession.create(store=store, model=Script(*first_script),
                                     search=provider.search, fetch=provider.fetch)
    session_id = session.session_id
    assert session.metadata.revision == 0 and session.turns == ()
    first = session.ask(Q1)
    history, corpus, metadata = session.turns, session.acquisitions, session.metadata
    assert metadata.title == Q1 and metadata.revision == 1
    del session, store, provider

    reuse = (use("C1"),) if highlights else (inspect("C1"), relevance("E1"))
    model = Script(orient(Q2), *reuse, assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]"))
    session = reopen(path, session_id, model=model)
    assert session.turns == history and session.acquisitions == corpus and session.metadata == metadata
    old = session.turns[0]
    assert old.answer == first.answer and old.analysis == first.analysis
    assert old.selected_evidence == first.selected_evidence and old.citations == first.citations
    assert old.citation_uses == first.citation_uses
    assert render_cli(old) == render_cli(first) and render_html(Q1, old) == render_html(Q1, first)
    second = session.ask(Q2)
    assert second.evidence == corpus and session.source_ids == ("E1",)
    analyst_input = next(m for stage, m in model.calls if stage == "analyst")
    assert analyst_input["previous_analysis"] is None
    assert analyst_input["conversation_context"] == [{"question": Q1, "answer": first.answer}]
    assert analyst_input["semantic_history"][0]["analysis"] == first.analysis.model_dump()
    assert analyst_input["evidence"][0]["content"] == BODY
    assert first.answer not in json.dumps(analyst_input["evidence"])
    assert [stage for stage, _ in model.calls].count("analyst") == 1
    assert [stage for stage, _ in model.calls].count("author") == 1
    history = session.turns
    del session, model

    provider = Provider([candidate(URL_B, FACT_C, highlights=True)])
    model = Script(orient(Q3), search_for(Q3), use("C2"), assess(Q3, FACT_C, "E2"), author(FACT_C + " [E2]"))
    session = reopen(path, session_id, model=model, search=provider.search)
    third = session.ask(Q3)
    assert session.source_ids == ("E1", "E2") and session.acquisitions[0] == corpus[0]
    assert third.selected_evidence == (session.acquisitions[1],)
    assert third.citations[0].source_id == "E2" and third.citations[0].number == 1
    assert len(provider.searches) == 1 and not provider.fetches
    del session, model, provider
    restored = reopen(path, session_id)
    assert restored.turns[:2] == history and restored.metadata.revision == 3
    assert SQLiteSessionStore(path).list_sessions() == (restored.metadata,)


def test_same_url_versions_keep_source_identity_and_new_source_does_not_collide(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    provider = Provider([candidate(context=FACT_A, highlights=True)])
    session = ResearchSession.create(store=SQLiteSessionStore(path), search=provider.search, fetch=no_io,
                                     model=Script(orient(Q1), search_for(Q1), use("C1"),
                                                  assess(Q1, FACT_A, "E1"), author(ANSWER_A + " [E1]")))
    session.ask(Q1)
    session_id = session.session_id
    del session
    session = reopen(path, session_id, fetch=provider.fetch,
                     model=Script(orient(Q2), inspect("C1"), relevance("E2"),
                                  assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]")))
    second = session.ask(Q2)
    assert [(item.id, item.source_id) for item in session.acquisitions] == [("E1", "E1"), ("E2", "E1")]
    assert second.citations[0].source_id == "E1" and second.citations[0].materials[0].id == "E2"
    del session
    provider = Provider([candidate(URL_B, FACT_C, highlights=True)])
    session = reopen(path, session_id, search=provider.search,
                     model=Script(orient(Q3), search_for(Q3), use("C3"), assess(Q3, FACT_C, "E3"),
                                  author(FACT_C + " [E3]")))
    session.ask(Q3)
    assert session.source_ids == ("E1", "E3")
    assert [(item.id, item.source_id) for item in session.acquisitions] == [("E1", "E1"), ("E2", "E1"), ("E3", "E3")]
    assert reopen(path, session_id).turns[1].citations == second.citations


def test_historical_multiple_citation_order_and_repeated_uses_are_exact(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    question = "Compare the standards."
    provider = Provider([candidate(context=FACT_A, highlights=True), candidate(URL_B, FACT_C, highlights=True)])
    model = Script(orient(question), search_for(question), use("C1", "C2"),
                   assess(question, FACT_A + FACT_C, "E1", "E2"),
                   author(FACT_C + " [E2] " + FACT_A + " [E1] Both. [E2, E1]"))
    session = ResearchSession.create(store=SQLiteSessionStore(path), model=model, search=provider.search, fetch=no_io)
    result = session.ask(question)
    session_id = session.session_id
    del session
    turn = reopen(path, session_id).turns[0]
    assert [(c.number, c.source_id) for c in turn.citations] == [(1, "E2"), (2, "E1")]
    assert [use.number for use in turn.citation_uses] == [1, 2, 1, 2]
    assert turn.citations == result.citations and turn.citation_uses == result.citation_uses
    assert turn.selected_evidence == result.selected_evidence and turn.answer == result.answer


def test_exact_large_view_history_survives_and_new_packet_uses_persisted_parent(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    filler = ("# Machinery archive\n" + "Unrelated engineering background. " * 240 + "\n\n") * 30
    body = "# Standard\nScope: pressure equipment.\n\n" + FACT_A + "\n\n" + filler + "# Inspection\n" + FACT_B + "\n\n" + filler
    provider = Provider([candidate()], bodies={URL_A: body})
    model = Script(orient(Q1), search_for(Q1), inspect("C1", need=Q1), select_packet,
                   assess(Q1, FACT_A, "E1"), author(ANSWER_A + " [E1]"))
    session = ResearchSession.create(store=SQLiteSessionStore(path), model=model,
                                     search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    session_id = session.session_id
    assert provider.fetches == [URL_A] and len(provider.searches) == 1
    del session, model, provider
    session = reopen(path, session_id, model=Script(orient(Q2), inspect("C1"), select_packet,
                                                   assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]")))
    assert session.turns[0].selected_evidence == first.selected_evidence
    second = session.ask(Q2)
    assert session.acquisitions == first.evidence == second.evidence
    assert session.acquisitions[0].content == body
    assert FACT_B not in "".join(item.content for item in first.selected_evidence)
    assert FACT_B in "".join(item.content for item in second.selected_evidence)
    assert set(item.id for item in first.selected_evidence) != set(item.id for item in second.selected_evidence)
    assert sum(len(item.content) for item in second.selected_evidence) <= PACKET_CHARACTERS
    for turn in reopen(path, session_id).turns:
        assert turn.citations[0].materials == turn.selected_evidence
        for item in turn.selected_evidence:
            assert item.acquisition == "targeted_view" and item.parent_id == item.source_id == "E1"
            assert item.content == body[item.start_char:item.end_char]
    assert reopen(path, session_id).turns[0].citations == first.citations


@pytest.mark.parametrize("failure", ["model", "provider", "citations"])
def test_failed_attempt_does_not_write_any_part_of_turn(tmp_path, failure):
    path, original, _ = opening(tmp_path)
    before = SQLiteSessionStore(path).load(original.session_id)
    provider = Provider([candidate(URL_B, FACT_C, highlights=True)])
    tail = ("author", ModelError("synthetic failure")) if failure == "model" else author(FACT_C + " [E99]")
    model = Script(orient(Q3), search_for(Q3), use("C2"), assess(Q3, FACT_C, "E2"), tail)

    def failed_search(query):
        raise RuntimeError("synthetic provider failure")

    session = reopen(path, original.session_id, model=model,
                     search=failed_search if failure == "provider" else provider.search)
    with pytest.raises((RunError, RuntimeError)):
        session.ask(Q3)
    assert session.turns == before.state.turns and session.acquisitions == before.state.acquisitions
    assert session.metadata == before.metadata
    assert SQLiteSessionStore(path).load(original.session_id) == before


def test_sqlite_commit_failure_rolls_back_completed_result_and_memory(tmp_path, monkeypatch):
    path, original, _ = opening(tmp_path)
    before = SQLiteSessionStore(path).load(original.session_id)
    session = reopen(path, original.session_id, model=Script(orient(Q2), inspect("C1"), relevance("E1"),
                                                             assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]")))
    connect = sqlite3.connect

    class FailedCommit(sqlite3.Connection):
        def commit(self):
            # Verify failure is injected after the UPDATE, before COMMIT.
            assert self.execute("SELECT revision FROM sessions").fetchone()[0] == 2
            raise sqlite3.OperationalError("PRIVATE_DATABASE_FAILURE_DETAILS")

    monkeypatch.setattr(sqlite3, "connect", lambda *a, **kw: connect(*a, **kw, factory=FailedCommit))
    with pytest.raises(SessionStoreError) as caught:
        session.ask(Q2)
    assert str(caught.value) == "session_store_unavailable" and caught.value.__suppress_context__
    assert session.metadata == before.metadata and session.turns == before.state.turns
    assert session.acquisitions == before.state.acquisitions
    monkeypatch.undo()
    assert SQLiteSessionStore(path).load(original.session_id) == before


def test_stale_writer_cannot_overwrite_winner_or_advance_its_own_memory(tmp_path):
    path, original, _ = opening(tmp_path)
    winner = reopen(path, original.session_id, model=Script(orient(Q2), inspect("C1"), relevance("E1"),
                                                           assess(Q2, FACT_B, "E1"), author(FACT_B + " [E1]")))
    provider = Provider([candidate(URL_B, FACT_C, highlights=True)])
    stale = reopen(path, original.session_id, search=provider.search,
                   model=Script(orient(Q3), search_for(Q3), use("C2"), assess(Q3, FACT_C, "E2"), author(FACT_C + " [E2]")))
    winner.ask(Q2)
    with pytest.raises(SessionConflictError, match="^session_conflict$"):
        stale.ask(Q3)
    assert stale.metadata.revision == 1 and stale.acquisitions == original.acquisitions
    assert stale.turns == original.turns
    restored = reopen(path, original.session_id)
    assert restored.turns == winner.turns and restored.metadata == winner.metadata
    assert restored.acquisitions == original.acquisitions


def mutate_payload(path, mutate):
    with closing(sqlite3.connect(path)) as connection, connection:
        payload = json.loads(connection.execute("SELECT payload FROM sessions").fetchone()[0])
        mutate(payload)
        connection.execute("UPDATE sessions SET payload = ?", (json.dumps(payload),))


@pytest.mark.parametrize("mutate", [
    lambda p: p["acquisitions"][0].update(content=123),
    lambda p: p["acquisitions"][0].update(id="E7"),
    lambda p: p["acquisitions"][0].update(source_id=""),
    lambda p: p["acquisitions"][0].update(acquisition="generated_answer"),
    lambda p: p["acquisitions"][0].update(start_char=0),
    lambda p: p["turns"][0]["analysis"].update(decision="invalid"),
    lambda p: p["turns"][0]["analysis"].update(coverage=[]),
    lambda p: p["turns"][0]["analysis"].update(active_evidence_refs=["E7"]),
    lambda p: p["turns"][0]["selected_evidence"][0].update(content="Changed source material"),
    lambda p: p["turns"][0]["citations"][0].update(number=2),
    lambda p: p["turns"][0]["citations"][0].update(material_ids=["E7"]),
    lambda p: p["turns"][0]["citations"][0].update(url="https://example.test/wrong"),
    lambda p: p["turns"][0]["citation_uses"][0].update(start=0),
    lambda p: p["turns"][0].update(posture="unable"),
    lambda p: p["turns"][0].update(stop_reason="research_bound"),
    lambda p: p["turns"][0].update(question=" "),
    lambda p: p.update(turns=[]),
    lambda p: p.update(trace=["not product state"]),
])
def test_corrupt_product_state_fails_before_research_without_rewriting_data(tmp_path, mutate):
    path, session, _ = opening(tmp_path)
    mutate_payload(path, mutate)
    before = path.read_bytes()
    with pytest.raises(SessionStoreError, match="^invalid_session_data$"):
        reopen(path, session.session_id)
    assert path.read_bytes() == before


@pytest.mark.parametrize("statement", [
    "UPDATE sessions SET revision = 8",
    "UPDATE sessions SET created_at = 'invalid'",
    "UPDATE sessions SET updated_at = '2001-01-01T00:00:00+00:00'",
    "UPDATE sessions SET payload = '{broken json'",
])
def test_invalid_metadata_and_json_are_safe(tmp_path, statement):
    path, session, _ = opening(tmp_path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(statement)
    with pytest.raises(SessionStoreError, match="^invalid_session_data$"):
        reopen(path, session.session_id)


@pytest.mark.parametrize("statement", ["PRAGMA user_version = 99", "CREATE TABLE unrelated (value TEXT)"])
def test_unknown_schema_is_not_migrated_or_overwritten(tmp_path, statement):
    path = tmp_path / "incompatible.sqlite3"
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(statement)
    before = path.read_bytes()
    with pytest.raises(SessionStoreError, match="^incompatible_session_store$"):
        SQLiteSessionStore(path).list_sessions()
    assert path.read_bytes() == before


def test_missing_store_id_and_unreadable_database_return_fixed_errors(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    assert store.list_sessions() == ()
    with pytest.raises(SessionStoreError, match="^session_not_found$"):
        store.load("missing")
    invalid = tmp_path / "invalid.sqlite3"
    invalid.write_bytes(b"This is not SQLite")
    with pytest.raises(SessionStoreError, match="^session_store_unavailable$"):
        SQLiteSessionStore(invalid).list_sessions()
    with pytest.raises(SessionStoreError, match="^session_store_unavailable$"):
        SQLiteSessionStore(tmp_path).create()


def test_public_snapshots_are_copied_and_storage_is_a_product_field_allowlist(tmp_path):
    path, session, result = opening(tmp_path)
    result.analysis.coverage.clear()
    session.turns[0].analysis.coverage.clear()
    assert session.turns[0].analysis.findings[0].text == FACT_A
    restored = reopen(path, session.session_id)
    assert restored.turns == session.turns
    with closing(sqlite3.connect(path)) as connection, connection:
        record = json.loads(connection.execute("SELECT payload FROM sessions").fetchone()[0])
    assert set(record) == {"turns", "acquisitions"}
    assert set(record["turns"][0]) == {
        "question", "answer", "analysis", "posture", "stop_reason", "selected_evidence", "citations", "citation_uses"}
    assert record["acquisitions"] == [asdict(item) for item in session.acquisitions]
    assert record["turns"][0]["analysis"] == session.turns[0].analysis.model_dump()


@pytest.mark.parametrize("decision, refs, gap", [("unable", (), None), ("unable", ("E1",), None),
                                               ("research_needed", ("E1",), "Missing exception")])
def test_valid_partial_unable_and_bound_results_commit(tmp_path, decision, refs, gap):
    path = tmp_path / "sessions.sqlite3"
    provider = Provider([candidate(context=FACT_A, highlights=True)])
    start = (search_for(Q1), use("C1")) if refs else (done(),)
    model = Script(orient(Q1), *start, analysis(decision, refs=refs, next_need=gap),
                   author(FACT_A + " [E1]" if refs else "The evidence did not establish the answer."))
    session = ResearchSession.create(store=SQLiteSessionStore(path), model=model, search=provider.search, fetch=no_io,
                                     limits=research.RunLimits(research_passes=1))
    result = session.ask(Q1)
    assert reopen(path, session.session_id).turns[0].posture == result.posture
    before = session.metadata
    with pytest.raises(RunError, match="input: empty_question"):
        session.ask(" ")
    assert session.metadata == before


def test_default_path_is_external_and_ephemeral_run_never_opens_store(tmp_path, monkeypatch):
    repository = Path(__file__).resolve().parents[1]
    assert not default_session_path().resolve().is_relative_to(repository)
    monkeypatch.setattr(SQLiteSessionStore, "_transaction", no_io)
    monkeypatch.chdir(tmp_path)
    provider = Provider([candidate()], [candidate()])
    session = ResearchSession(model=Script(*first_turn()), search=provider.search, fetch=provider.fetch)
    session.ask(Q1)
    isolated = run(Q1, model=Script(*first_turn()), search=provider.search, fetch=provider.fetch)
    assert session.session_id is None and session.metadata is None
    assert len(isolated.evidence) == 1 and isolated.evidence[0].id == "E1"
    assert not list(tmp_path.iterdir())


def test_cli_create_list_resume_and_provider_free_history(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sessions.sqlite3"
    # The real session/SQLite path is exercised; the ordinary transport factory is fake.
    monkeypatch.setattr(research, "OpenAIModel", lambda: Script(orient(Q1), done(), analysis("unable", refs=()),
                                                              author("Evidence unavailable.")))
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert cli.main([Q1, "--create-session", "--database", str(path)]) == 0
    output = capsys.readouterr()
    session_id = output.err.strip().removeprefix("Session: ")
    assert "Evidence unavailable." in output.out
    monkeypatch.setattr(research, "OpenAIModel", no_io)
    assert cli.main(["--list-sessions", "--database", str(path)]) == 0
    assert session_id in capsys.readouterr().out
    assert cli.main(["--resume", session_id, "--database", str(path)]) == 0
    assert Q1 in capsys.readouterr().out
    monkeypatch.setattr(research, "OpenAIModel", lambda: Script(orient(Q2), done(), analysis("unable", refs=()),
                                                              author("Still unavailable.")))
    assert cli.main([Q2, "--resume", session_id, "--database", str(path)]) == 0
    assert "Still unavailable." in capsys.readouterr().out
    assert reopen(path, session_id).metadata.revision == 2


def test_cli_store_errors_do_not_print_unsaved_answers(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sessions.sqlite3"
    assert cli.main(["--resume", "missing", "--database", str(path)]) == 1
    assert capsys.readouterr().err == "ScryRaven session error: session_not_found\n"
    monkeypatch.setattr(research, "OpenAIModel", lambda: Script(orient(Q1), done(), analysis("unable", refs=()),
                                                              author("UNSAVED_ANSWER")))

    def fail_commit(*args):
        raise SessionStoreError()

    monkeypatch.setattr(SQLiteSessionStore, "commit", fail_commit)
    assert cli.main([Q1, "--create-session", "--database", str(path)]) == 1
    output = capsys.readouterr()
    assert "UNSAVED_ANSWER" not in output.out + output.err
    assert "session_store_unavailable" in output.err


@pytest.mark.parametrize("args", [[], [Q1, "--database", "unused"], [Q1, "--list-sessions"],
                                  [Q1, "--create-session", "--html", "unused"],
                                  [Q1, "--create-session", "--session"]])
def test_invalid_cli_combinations_fail_before_io(args):
    with pytest.raises(SystemExit) as caught:
        cli.main(args)
    assert caught.value.code == 2
