"""Forensic Reading Room uses the ordinary engine and isolates sensitive events."""

import json
from pathlib import Path

import pytest
from test_reading_room import submit
from test_research_loop import Script, answer, decision, no_fetch, search

from scryraven import reading_room
from scryraven.forensic_log import ForensicLog
from scryraven.presentation import render_cli
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _client(store, *, model, dogfood_log=None, forensic_log=None, search_provider=search):
    return reading_room.create_app(
        store=store, dogfood_log=dogfood_log, forensic_log=forensic_log,
        session_options={"model": model, "search": search_provider, "fetch": no_fetch},
    ).test_client()


def test_forensic_events_capture_exposure_rejection_and_stay_out_of_product_records(
    tmp_path, monkeypatch,
):
    rejected = "SYNTHETIC_REJECTED_PASSAGE_837_ONLY_FOR_FORENSICS"
    source_body = "The stated value is seven."
    bad = answer(readings=[{"evidence_ref": "E1", "passages": [rejected]}])
    model = Script(decision(), decision("answer", ["E1"]), bad, answer())
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    dogfood = tmp_path / "turns.jsonl"
    forensic = tmp_path / "observer.jsonl"
    completed = []
    original_ask = ResearchSession.ask

    def capture_answer(self, question):
        result = original_ask(self, question)
        completed.append(result)
        return result

    monkeypatch.setattr(ResearchSession, "ask", capture_answer)
    client = _client(store, model=model, dogfood_log=dogfood, forensic_log=forensic)
    response = submit(client, question="What is the value?")
    assert response.status_code == 303
    records = _events(forensic)
    actions = [row["event"]["action"] for row in records]
    assert {"started", "research_decision", "acquired_material", "answer_reading_rejected_detail",
            "answer_reading", "answer_decision", "completed"} <= set(actions)
    exposures = [row["event"] for row in records if row["event"]["action"] == "exposure"]
    assert [event["contract"] for event in exposures] == ["research", "research", "answer", "answer"]
    assert exposures[1]["evidence"][0]["content"] == source_body
    assert exposures[2]["evidence"][0]["content"] == source_body
    detail = next(row["event"] for row in records
                  if row["event"]["action"] == "answer_reading_rejected_detail")
    assert detail["attempted_passage"] == rejected
    assert [row["event_sequence"] for row in records] == list(range(1, len(records) + 1))
    session_id = store.list_sessions()[0].session_id
    assert all(row["session_id"] == session_id and row["attempted_turn"] == 1
               and row["revision_before"] == 0 for row in records)
    assert len({row["run_id"] for row in records}) == 1
    assert all(row["logged_at_utc"] for row in records)
    assert any(row["event"]["action"] == "model_returned" for row in records)

    assert rejected in forensic.read_text(encoding="utf-8")
    assert rejected not in dogfood.read_text(encoding="utf-8")
    assert source_body not in dogfood.read_text(encoding="utf-8")
    assert rejected not in json.dumps(completed[0].trace)
    assert rejected not in repr(store.load(session_id).state)
    assert rejected not in client.get(response.location).get_data(as_text=True)
    assert rejected not in render_cli(completed[0])
    assert store.load(session_id).metadata.revision == 1
    assert completed[0].posture == "supported"


def test_without_forensic_log_ordinary_turn_has_no_sensitive_observer_file(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    dogfood = tmp_path / "turns.jsonl"
    client = _client(store, model=Script(decision(), decision("answer", ["E1"]), answer()),
                     dogfood_log=dogfood)
    assert submit(client).status_code == 303
    assert store.list_sessions()[0].revision == 1
    assert not (tmp_path / "observer.jsonl").exists()
    assert "The stated value is seven." not in dogfood.read_text(encoding="utf-8")


def test_forensic_cli_option_wires_distinct_logs_without_running_a_turn(tmp_path, monkeypatch):
    database = tmp_path / "sessions.sqlite3"
    dogfood = tmp_path / "turns.jsonl"
    forensic = tmp_path / "observer.jsonl"
    served = []
    monkeypatch.setattr(reading_room, "serve", lambda app, *, port: served.append((app, port)))
    assert reading_room.main([
        "--database", str(database), "--dogfood-log", str(dogfood),
        "--forensic-log", str(forensic), "--port", "7332",
    ]) == 0
    assert len(served) == 1 and served[0][1] == 7332
    assert dogfood.read_text(encoding="utf-8") == ""
    assert forensic.read_text(encoding="utf-8") == ""
    assert not database.exists()  # Creating the app does not open a session.


def test_forensic_write_failure_disables_sink_and_preserves_subsequent_turns(
    tmp_path, monkeypatch, capsys,
):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    forensic = tmp_path / "observer.jsonl"
    unable = answer("No source establishes this.", posture="unable")
    client = _client(store, model=Script(decision("answer"), unable,
                                         decision("answer"), unable),
                     forensic_log=forensic, search_provider=lambda _: pytest.fail("Unexpected search"))
    original_open = Path.open
    attempts = []

    def denied(path, *args, **kwargs):
        if path == forensic:
            attempts.append(path)
            raise OSError("PRIVATE_LOG_FAILURE")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    assert submit(client, question="First?").status_code == 303
    assert submit(client, question="Second?").status_code == 303
    assert len(attempts) == 1
    assert len(store.list_sessions()) == 2
    assert all(item.revision == 1 for item in store.list_sessions())
    warning = capsys.readouterr().err
    assert warning.count("forensic diagnostics stopped") == 1
    assert "PRIVATE_LOG_FAILURE" not in warning
    monkeypatch.undo()
    assert forensic.read_text(encoding="utf-8") == ""


def test_forensic_rejects_database_and_dogfood_aliases_before_opening(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    dogfood = tmp_path / "turns.jsonl"
    forensic = tmp_path / "observer.jsonl"
    with pytest.raises(OSError, match="forensic_log_matches_session_database"):
        reading_room.create_app(store=store, forensic_log=store.path)
    with pytest.raises(OSError, match="dogfood_log_matches_session_database"):
        reading_room.create_app(store=store, dogfood_log=store.path, forensic_log=forensic)
    with pytest.raises(OSError, match="forensic_log_matches_dogfood_log"):
        reading_room.create_app(store=store, dogfood_log=dogfood, forensic_log=dogfood)
    assert not forensic.exists() and not dogfood.exists()
    store.list_sessions()  # Create the real SQLite file for hard-link checks.
    try:
        forensic.hardlink_to(store.path)
    except OSError:
        pytest.skip("Hard links unavailable on this filesystem")
    with pytest.raises(OSError, match="forensic_log_matches_session_database"):
        reading_room.create_app(store=store, forensic_log=forensic)
    assert store.list_sessions() == ()


def test_forensic_append_preserves_existing_model_telemetry_and_runtime_alias_is_safe(
    tmp_path, capsys,
):
    db = tmp_path / "sessions.sqlite3"
    db.write_bytes(b"DATABASE_SENTINEL")
    forensic = tmp_path / "observer.jsonl"
    sink = ForensicLog(forensic, session_database=db)
    event = {"stage": "research", "action": "model_returned", "contract": "answer",
             "duration_seconds": 1.25, "usage": {"input_tokens": 17,
                                                 "output_tokens": 8,
                                                 "reasoning_tokens": 3,
                                                 "returned_service_tier": "fast"}}
    sink.append(event, session_id="a" * 32, revision_before=2)
    assert _events(forensic)[0]["event"] == event
    assert _events(forensic)[0]["attempted_turn"] == 3
    forensic.unlink()
    try:
        forensic.hardlink_to(db)
    except OSError:
        pytest.skip("Hard links unavailable on this filesystem")
    sink.append(event, session_id="a" * 32, revision_before=2)
    assert db.read_bytes() == b"DATABASE_SENTINEL"
    assert "forensic diagnostics stopped" in capsys.readouterr().err
