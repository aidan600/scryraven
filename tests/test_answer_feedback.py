"""Hosted answer comments use real signed identity, HTTP, SQLite and ZIP custody.

Only research/provider I/O is scripted; feedback always uses ordinary HTTP forms.
"""

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from io import BytesIO
from threading import Event
from urllib.parse import urlsplit
from zipfile import ZipFile

import pytest
import test_hosted_identity as identity
import test_hosted_reading_room as hosted_room
from reading_room_samples import no_io
from test_reading_room import Form
from test_research_loop import answer, decision
from werkzeug.datastructures import MultiDict

from scryraven.reading_room import create_app
from scryraven.session_store import SQLiteSessionStore, _encode

config = hosted_room.config
key = hosted_room.key
room = hosted_room.room
tmp_path = hosted_room.tmp_path
get = hosted_room.get
post = hosted_room.post


def feedback_path(session_id, turn=1):
    return f"/sessions/{session_id}/turns/{turn}/feedback"


def feedback_form(room, config, key, session_id, turn=1):
    page = get(room, config, key, f"/sessions/{session_id}")
    fields = Form(page.text, feedback_path(session_id, turn)).fields
    assert fields.get("form_token"), page.text
    return fields


def send(room, config, key, session_id, text, turn=1):
    fields = feedback_form(room, config, key, session_id, turn)
    response = post(room, config, key, feedback_path(session_id, turn), {**fields, "text": text})
    assert response.status_code == 303, response.text
    assert urlsplit(response.location).fragment == f"feedback-{turn}"
    return response


def delete_path(entry):
    return f"{feedback_path(entry.session_id, entry.turn_index)}/{entry.feedback_id}/delete"


def test_comments_persist_without_changing_session_sources_jobs_or_quota(room, config, key):
    app, store, session_id, _ = room
    before = store.load(session_id)
    with closing(sqlite3.connect(store.path)) as connection:
        original_payload = connection.execute("SELECT payload FROM sessions WHERE session_id=?", (session_id,)).fetchone()[0]
        original_quota = connection.execute("SELECT * FROM user_submissions").fetchall()
    send(room, config, key, session_id, "First comment about this answer.")
    send(room, config, key, session_id, "Second comment, same answer.")
    entries = store.list_feedback(session_id)
    assert [entry.text for entry in entries] == ["First comment about this answer.", "Second comment, same answer."]
    assert all(entry.session_id == session_id and entry.turn_index == 1 and entry.author_id == "alice@example.test" for entry in entries)
    assert all(entry.created_at for entry in entries)
    assert store.load(session_id) == before
    assert store.list_jobs() == ()
    with closing(sqlite3.connect(store.path)) as connection:
        assert connection.execute("SELECT payload FROM sessions WHERE session_id=?", (session_id,)).fetchone()[0] == original_payload
        assert connection.execute("SELECT * FROM user_submissions").fetchall() == original_quota
    page = get(room, config, key, f"/sessions/{session_id}")
    assert page.text.index(entries[0].text) < page.text.index(entries[1].text)
    app.extensions["research_jobs"].shutdown()
    assert app.extensions["research_jobs"].wait_idle(10)
    reopened = create_app(store=SQLiteSessionStore(store.path), hosted=config,
                          identity_validator=identity.validator(config, key),
                          session_options={"model": no_io, "search": no_io, "fetch": no_io})
    response = reopened.test_client().get(f"/sessions/{session_id}", base_url=config.origin,
                                          headers=hosted_room.headers(config, key))
    assert response.status_code == 200
    assert all(entry.text in response.text for entry in entries)
    assert SQLiteSessionStore(store.path).list_feedback(session_id) == entries


def test_feedback_during_research_and_after_followup_keeps_exact_answer_identity(room, config, key):
    original_app, store, session_id, _ = room
    original_app.extensions["research_jobs"].shutdown()
    assert original_app.extensions["research_jobs"].wait_idle(10)
    entered, release = Event(), Event()
    received = []

    def model(stage, prompt, material, schema):
        received.append(json.dumps({"prompt": prompt, "material": material}, default=str))
        if stage == "research":
            entered.set()
            assert release.wait(10)
            return json.dumps(decision("return"))
        return json.dumps(answer("Given your premises, eight apples remain.", support_basis="user_premises"))

    app = create_app(store=store, hosted=config, identity_validator=identity.validator(config, key),
                     session_options={"model": model, "search": no_io, "fetch": no_io})
    active_room = (app, store, session_id, room[3])
    manager = app.extensions["research_jobs"]
    sentinel = "FEEDBACK_ONLY_SENTINEL_never_research_context"
    before = store.load(session_id)
    stale = feedback_form(active_room, config, key, session_id)
    page = get(active_room, config, key, f"/sessions/{session_id}")
    fields = Form(page.text, f"/sessions/{session_id}/ask").fields
    try:
        accepted = post(active_room, config, key, f"/sessions/{session_id}/ask",
                        {**fields, "question": "Given ten apples and two removed, how many remain?"})
        assert accepted.status_code == 303
        assert entered.wait(5)
        send(active_room, config, key, session_id, sentinel)
        assert store.list_jobs()[0].state == "researching"
        assert store.load(session_id).state == before.state
        release.set()
        assert manager.wait_idle(10)
        assert all(sentinel not in packet for packet in received)
        assert len(received) == 2
        assert store.load(session_id).metadata.revision == before.metadata.revision + 1
        assert store.load(session_id).state.turns[0] == before.state.turns[0]
        # A comment form does not become stale when a research revision commits.
        late = post(active_room, config, key, feedback_path(session_id), {**stale, "text": "On the first answer, after follow-up."})
        assert late.status_code == 303
        send(active_room, config, key, session_id, "On the second answer.", turn=2)
        entries = store.list_feedback(session_id)
        assert [(entry.turn_index, entry.text) for entry in entries] == [
            (1, sentinel), (1, "On the first answer, after follow-up."), (2, "On the second answer.")]
        assert sentinel not in _encode(store.load(session_id).state)
        assert len(store.list_jobs()) == 1
        with closing(sqlite3.connect(store.path)) as connection:
            assert connection.execute("SELECT submission_count FROM user_submissions").fetchall() == [(1,)]
        # The research quota is exhausted; comments still succeeded without using it.
        latest = get(active_room, config, key, f"/sessions/{session_id}")
        ask = Form(latest.text, f"/sessions/{session_id}/ask").fields
        assert post(active_room, config, key, f"/sessions/{session_id}/ask", {**ask, "question": "One more?"}).status_code == 429
    finally:
        release.set()
        manager.shutdown()
        assert manager.wait_idle(10)


def test_feedback_and_remove_enforce_identity_ownership_and_admin_readonly(room, config, key):
    app, store, session_id, other = room
    send(room, config, key, session_id, "Owner-only comment")
    entry = store.list_feedback(session_id)[0]
    paths = (feedback_path(session_id), delete_path(entry))
    for path in paths:
        assert app.test_client().post(path, base_url=config.origin, data={}).status_code == 401
        for email in ("bob@example.test", config.admin_email):
            assert post(room, config, key, path, {}, email=email).status_code == 404
    assert get(room, config, key, f"/sessions/{session_id}", email="bob@example.test").status_code == 404
    admin = get(room, config, key, f"/sessions/{session_id}", email=config.admin_email)
    assert "Owner-only comment" in admin.text
    assert Form(admin.text, feedback_path(session_id)).fields == {}
    assert Form(admin.text, delete_path(entry)).fields == {}
    assert store.list_feedback(other) == ()


def test_feedback_csrf_is_identity_action_answer_bound_and_replay_protected(room, config, key):
    _, store, session_id, _ = room
    path = feedback_path(session_id)
    initial = feedback_form(room, config, key, session_id)
    ask = Form(get(room, config, key, f"/sessions/{session_id}").text, f"/sessions/{session_id}/ask").fields
    for token in ("", "malformed", ask["form_token"]):
        assert post(room, config, key, path, {"form_token": token, "text": "no"}).status_code == 403
    # Bob's valid sessionless form cannot authorize Alice's feedback action.
    bob_ask = Form(get(room, config, key, email="bob@example.test").text, "/ask").fields
    assert post(room, config, key, path, {"form_token": bob_ask["form_token"], "text": "no"}).status_code == 403
    accepted = post(room, config, key, path, {**initial, "text": "Exactly once"})
    assert accepted.status_code == 303
    assert post(room, config, key, path, {**initial, "text": "Exactly once"}).status_code == 409
    entry = store.list_feedback(session_id)[0]
    # A submission token cannot authorize deletion, even for its own author.
    assert post(room, config, key, delete_path(entry), initial).status_code == 403
    assert len(store.list_feedback(session_id)) == 1


@pytest.mark.parametrize("forged_headers", [
    {"Origin": "https://attacker.example.test"}, {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"},
])
def test_feedback_preserves_csrf_origin_checks(room, config, key, forged_headers):
    app, store, session_id, _ = room
    fields = feedback_form(room, config, key, session_id)
    result = app.test_client().post(feedback_path(session_id), base_url=config.origin,
        headers={**hosted_room.headers(config, key), **forged_headers}, data={**fields, "text": "Cross-site"})
    assert result.status_code == 403
    assert not store.list_feedback(session_id)


@pytest.mark.parametrize("text", ["", " \r\n\t ", "x" * 2001, "bad\x00comment", "bad\x01comment"])
def test_feedback_rejects_empty_oversize_and_control_text(room, config, key, text):
    _, store, session_id, _ = room
    fields = feedback_form(room, config, key, session_id)
    result = post(room, config, key, feedback_path(session_id), {**fields, "text": text})
    assert result.status_code == 400
    assert not store.list_feedback(session_id)


@pytest.mark.parametrize("extra", [
    {"owner_id": "bob@example.test"}, {"author_id": "bob@example.test"}, {"turn_index": "2"},
    {"question": "Must not research"}, {"rating": "5"}, {"created_at": "forged-time"},
])
def test_feedback_rejects_forged_fields(room, config, key, extra):
    _, store, session_id, _ = room
    fields = feedback_form(room, config, key, session_id)
    assert post(room, config, key, feedback_path(session_id), {**fields, "text": "Text", **extra}).status_code == 400
    assert not store.list_feedback(session_id)
    assert not store.list_jobs()


def test_feedback_rejects_duplicate_fields_and_nonform_body(room, config, key):
    _, store, session_id, _ = room
    for duplicate in ("text", "form_token"):
        fields = feedback_form(room, config, key, session_id)
        data = MultiDict([*fields.items(), ("text", "First")])
        data.add(duplicate, "Second")
        assert post(room, config, key, feedback_path(session_id), data).status_code == 400
    assert post(room, config, key, feedback_path(session_id), json.dumps({"text": "JSON"}), content_type="application/json").status_code == 415
    assert not store.list_feedback(session_id)


def test_feedback_plain_text_limit_and_html_escaping(room, config, key):
    _, store, session_id, _ = room
    literal = '<script>window.feedbackExecuted=true</script> <img src=x onerror="alert(1)">\n**plain text**'
    send(room, config, key, session_id, literal)
    send(room, config, key, session_id, "x" * 2000)
    page = get(room, config, key, f"/sessions/{session_id}")
    assert "&lt;script&gt;window.feedbackExecuted=true&lt;/script&gt;" in page.text
    assert '<script>window.feedbackExecuted' not in page.text
    assert '<img src=x onerror=' not in page.text
    assert "**plain text**" in page.text
    assert [entry.text for entry in store.list_feedback(session_id)] == [literal, "x" * 2000]


def test_comment_removal_and_session_deletion_remove_only_ordinary_feedback(room, config, key):
    _, store, session_id, _ = room
    send(room, config, key, session_id, "Remove this one")
    send(room, config, key, session_id, "Keep this one")
    first, second = store.list_feedback(session_id)
    before = store.load(session_id)
    fields = Form(get(room, config, key, f"/sessions/{session_id}").text, delete_path(first)).fields
    assert fields.get("form_token")
    # Forged fields do not bypass a narrowly scoped removal form.
    assert post(room, config, key, delete_path(first), {**fields, "text": "tampered"}).status_code == 400
    fields = Form(get(room, config, key, f"/sessions/{session_id}").text, delete_path(first)).fields
    removed = post(room, config, key, delete_path(first), fields)
    assert removed.status_code == 303
    assert urlsplit(removed.location).fragment == "feedback-1"
    assert store.list_feedback(session_id) == (second,)
    assert store.load(session_id) == before
    confirmation = get(room, config, key, f"/sessions/{session_id}/delete")
    delete = Form(confirmation.text, f"/sessions/{session_id}/delete").fields
    assert post(room, config, key, f"/sessions/{session_id}/delete", {**delete, "confirm": "delete"}).status_code == 303
    with closing(sqlite3.connect(store.path)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM answer_feedback WHERE session_id=?", (session_id,)).fetchone()[0] == 0


def test_feedback_rejects_nonexistent_answers_and_comment_identity(room, config, key):
    _, store, session_id, _ = room
    for turn in (0, 2, 999):
        # The action's CSRF token is not sufficient to invent a completed answer.
        fields = feedback_form(room, config, key, session_id)
        assert post(room, config, key, feedback_path(session_id, turn), {**fields, "text": "No answer"}).status_code in {403, 404}
    send(room, config, key, session_id, "Existing")
    entry = store.list_feedback(session_id)[0]
    fields = Form(get(room, config, key, f"/sessions/{session_id}").text, delete_path(entry)).fields
    false_id = f"{feedback_path(session_id)}/{'a' * 32}/delete"
    assert post(room, config, key, false_id, fields).status_code in {403, 404}
    assert len(store.list_feedback(session_id)) == 1


def test_admin_export_adds_feedback_with_provenance_and_preserves_exact_sources(room, config, key):
    _, store, session_id, _ = room
    before = store.load(session_id)
    empty = get(room, config, key, f"/admin/sessions/{session_id}/export", email=config.admin_email)
    with ZipFile(BytesIO(empty.data)) as archive:
        old_record = json.loads(archive.read("session.json"))
        old_attachments = {name: archive.read(name) for name in archive.namelist() if name.startswith("attachments/")}
    assert old_record["format"] == "scryraven-session-export-1"
    assert old_record["answer_feedback"] == []
    send(room, config, key, session_id, "For the administrator's forensic review")
    entry = store.list_feedback(session_id)[0]
    response = get(room, config, key, f"/admin/sessions/{session_id}/export", email=config.admin_email)
    with ZipFile(BytesIO(response.data)) as archive:
        record = json.loads(archive.read("session.json"))
        assert {name: archive.read(name) for name in old_attachments} == old_attachments
    assert record["state"] == old_record["state"]
    assert record["documents"] == old_record["documents"]
    assert record["images"] == old_record["images"]
    assert record["metadata"] == old_record["metadata"]
    assert record["answer_feedback"] == [{**asdict(entry), "provenance": "authenticated_participant"}]
    assert "Cloudflare" in json.dumps(record["answer_feedback_provenance"])
    assert "turn_index" in json.dumps(record["answer_feedback_provenance"])
    assert "answer_feedback" not in record["state"]
    assert record["state"]["turns"][entry.turn_index - 1]["answer"] == before.state.turns[0].answer
    assert store.load(session_id) == before


def test_trusted_local_reading_room_has_no_feedback_interface_or_mutations(tmp_path):
    store = SQLiteSessionStore(tmp_path / "local.sqlite3")
    saved = store.create("Trusted local research")
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    client = app.test_client()
    response = client.get(f"/sessions/{saved.metadata.session_id}")
    assert "Feedback on this answer" not in response.text
    assert client.post(feedback_path(saved.metadata.session_id), data={"text": "local"}).status_code == 404
    assert client.post(f"{feedback_path(saved.metadata.session_id)}/{'a' * 32}/delete", data={},
                       content_type="application/x-www-form-urlencoded").status_code == 404
    assert store.list_feedback(saved.metadata.session_id) == ()
