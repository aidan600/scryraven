"""Durable ordinary turns and backward reading of actual pre-supersession records."""
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import pytest
from test_research_loop import Script, answer, decision, request
from test_research_session import BODY, FACT_B, Q1, Q2, Provider, candidate, first_turn, local_turn, no_io

from scryraven import __main__ as cli
from scryraven import research
from scryraven.presentation import render_cli, render_html
from scryraven.research import run
from scryraven.session import ResearchSession
from scryraven.session_store import (
    SessionConflictError,
    SessionStoreError,
    SQLiteSessionStore,
    _decode,
    default_session_path,
)


@pytest.fixture
def tmp_path():
    # The repository's general pytest basetemp can live inside the checkout.
    # Session databases must stay external even when pytest runs without flags.
    root = Path(tempfile.gettempdir()).resolve()
    assert not root.is_relative_to(Path(__file__).resolve().parents[1])
    with tempfile.TemporaryDirectory(prefix="scryraven-session-test-", dir=root) as directory:
        yield Path(directory)



def reopen(path, session_id, **kwargs):
    return ResearchSession.open(session_id, store=SQLiteSessionStore(path),
                                **({"model": no_io, "search": no_io, "fetch": no_io} | kwargs))



def opening(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    store = SQLiteSessionStore(path)
    saved = store.create()
    payload = (Path(__file__).parent / "fixtures/historical_session_v1.json").read_text(encoding="utf-8")
    store.commit(saved.metadata.session_id, 0, _decode(payload, 1))
    session = reopen(path, saved.metadata.session_id)
    return path, session, session.turns[0]


def install_model(monkeypatch, script):
    class OfflineModel:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, *args):
            return script(*args)
    monkeypatch.setattr(research, "OpenAIModel", OfflineModel)


def test_historical_reopen_keeps_records_and_fresh_followup_never_sees_analyst(tmp_path):
    path, session, old = opening(tmp_path)
    raw_before = path.read_bytes()
    original = session.turns
    html = render_html(Q1, old)
    assert old.analysis is not None
    assert reopen(path, session.session_id).turns == original
    assert path.read_bytes() == raw_before
    session.turns[0].analysis.coverage.clear()
    assert session.turns == original
    model = Script(*local_turn())
    session = reopen(path, session.session_id, model=model)
    current = session.ask(Q2)
    assert session.turns[0] == old and session.turns[1].analysis is None
    assert current.answer == FACT_B + " [1]" and current.trace[-1]["budget"]["external_attempts"] == 0
    assert all("semantic_history" not in m and "analysis" not in m for _, _, m, _ in model.calls)
    assert model.calls[0][2]["working_understanding"] is None
    assert model.calls[-1][2]["evidence"][0]["content"] == BODY
    restored = reopen(path, session.session_id)
    assert restored.turns[0] == old and render_html(Q1, restored.turns[0]) == html
    assert render_cli(restored.turns[1]) == render_cli(current)
    with closing(sqlite3.connect(path)) as connection:
        payload = json.loads(connection.execute("SELECT payload FROM sessions").fetchone()[0])
    frozen = json.loads((Path(__file__).parent / "fixtures/historical_session_v1.json").read_text())
    assert payload["turns"][0] == frozen["turns"][0]
    assert payload["turns"][1]["analysis"] is None
    assert set(payload) == {"turns", "acquisitions"}


@pytest.mark.parametrize("highlights", [False, True])
def test_native_create_reopen_and_followup_retain_evidence_and_citations(tmp_path, highlights):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    provider = Provider([candidate(context=BODY if highlights else "", highlights=highlights)])
    session = ResearchSession.create(store=store, model=Script(*first_turn(highlights=highlights)), search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    assert session.metadata.title == Q1 and session.metadata.revision == 1
    session = reopen(store.path, session.session_id, model=Script(*local_turn()))
    second = session.ask(Q2)
    assert first.evidence == second.evidence == session.acquisitions
    assert first.citations == session.turns[0].citations
    assert all(t.analysis is None for t in session.turns)
    assert reopen(store.path, session.session_id).turns == session.turns


def test_new_exact_view_after_reopen_preserves_historical_selected_text(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    body = "first exact fact " + "unselected background " * 5000 + "last exact fact"
    def read_range(start, end):
        req = request("read", query="", target="C1")
        req.update(start_char=start, end_char=end)
        ref = f"E1@{start}:{end}"
        return decision(requests=[req]), decision("answer", [ref]), answer("Selected [" + ref + "]")
    provider = Provider([candidate()], bodies={"https://example.test/pressure-standard": body})
    session = ResearchSession.create(store=store, model=Script(decision(), *read_range(0, 16)), search=provider.search, fetch=provider.fetch)
    first = session.ask(Q1)
    session = reopen(store.path, session.session_id, model=Script(*read_range(len(body)-15, len(body))))
    second = session.ask(Q2)
    assert len(provider.fetches) == 1 and session.acquisitions == first.evidence == second.evidence
    restored = reopen(store.path, session.session_id)
    assert restored.turns[0].citations == first.citations
    assert restored.turns[1].selected_evidence[0].content == "last exact fact"
    assert "last exact fact" not in render_html(Q1, restored.turns[0])


def test_cli_create_list_reopen_and_native_followup(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sessions.sqlite3"
    install_model(monkeypatch, Script(decision("answer"), answer("Evidence unavailable.", "unable")))
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert cli.main([Q1, "--create-session", "--database", str(path)]) == 0
    session_id = SQLiteSessionStore(path).list_sessions()[0].session_id
    assert "Evidence unavailable." in capsys.readouterr().out
    install_model(monkeypatch, no_io)
    assert cli.main(["--list-sessions", "--database", str(path)]) == 0
    assert session_id in capsys.readouterr().out
    assert cli.main(["--resume", session_id, "--database", str(path)]) == 0
    assert Q1 in capsys.readouterr().out
    install_model(monkeypatch, Script(decision("answer"), answer("Still unavailable.", "unable")))
    assert cli.main([Q2, "--resume", session_id, "--database", str(path)]) == 0
    assert reopen(path, session_id).metadata.revision == 2


def test_cli_store_errors_do_not_print_unsaved_answers(tmp_path, monkeypatch, capsys):
    path = tmp_path / "sessions.sqlite3"
    assert cli.main(["--resume", "missing", "--database", str(path)]) == 1
    assert capsys.readouterr().err == "ScryRaven session error: session_not_found\n"
    install_model(monkeypatch, Script(decision("answer"), answer("UNSAVED_ANSWER", "unable")))
    def failed(*args):
        raise SessionStoreError()
    monkeypatch.setattr(SQLiteSessionStore, "commit", failed)
    assert cli.main([Q1, "--create-session", "--database", str(path)]) == 1
    output = capsys.readouterr()
    assert "UNSAVED_ANSWER" not in output.out + output.err
    assert "session_store_unavailable" in output.err



def test_sqlite_commit_failure_rolls_back_completed_result_and_memory(tmp_path, monkeypatch):
    path, original, _ = opening(tmp_path)
    before = SQLiteSessionStore(path).load(original.session_id)
    session = reopen(path, original.session_id, model=Script(*local_turn()))
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
    winner = reopen(path, original.session_id, model=Script(*local_turn()))
    stale = reopen(path, original.session_id, model=Script(*local_turn()))
    winner.ask(Q2)
    with pytest.raises(SessionConflictError):
        stale.ask(Q2)
    assert stale.turns == original.turns and stale.metadata.revision == 1
    assert reopen(path, original.session_id).turns == winner.turns



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



@pytest.mark.parametrize("args", [[], [Q1, "--database", "unused"], [Q1, "--list-sessions"],
                                  [Q1, "--create-session", "--html", "unused"],
                                  [Q1, "--create-session", "--session"]])
def test_invalid_cli_combinations_fail_before_io(args):
    with pytest.raises(SystemExit) as caught:
        cli.main(args)
    assert caught.value.code == 2
