"""HTTP admission/navigation runs through real durable local job execution."""

from io import BytesIO
from threading import Event
from urllib.parse import urlencode

import pytest
from pdf_fixtures import text_pdf
from PIL import Image
from test_persistent_sessions import tmp_path as external_tmp_path
from test_reading_room import token
from test_research_jobs import Workers, engine

from scryraven.reading_room import create_app
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore

tmp_path = external_tmp_path


def form(client, location="/"):
    action = "/ask" if location == "/" else location + "/ask"
    return action, token(client.get(location), action)


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("known_length", [False, True])
def test_oversized_urlencoded_question_is_rejected_before_admission(tmp_path, existing, known_length):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = store.create("Existing conversation") if existing else None
    calls = []
    app = create_app(store=store, session_options={"engine": lambda *a, **k: calls.append(a)})
    client = app.test_client()
    action, fields = form(client, f"/sessions/{saved.metadata.session_id}" if saved else "/")
    before = store.list_sessions()
    body = urlencode(fields | {"question": "q" * (300 * 1024)}).encode()
    overrides = {} if known_length else {"CONTENT_LENGTH": None, "wsgi.input_terminated": True}
    response = client.post(action, data=body, content_type="application/x-www-form-urlencoded",
                           environ_overrides=overrides)
    assert response.status_code == 413 and b"too large" in response.data
    assert calls == [] and store.list_jobs() == () and store.list_sessions() == before


@pytest.mark.parametrize("known_length", [False, True])
def test_urlencoded_question_accepts_exact_text_form_limit(tmp_path, known_length):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    app = create_app(store=store, session_options={"engine": engine})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    action, fields = form(client)
    body = urlencode(fields | {"question": "Inspect this question"}).encode() + b"&padding="
    body += b"x" * (256 * 1024 - len(body))
    overrides = {} if known_length else {"CONTENT_LENGTH": None, "wsgi.input_terminated": True}
    response = client.post(action, data=body, content_type="application/x-www-form-urlencoded",
                           environ_overrides=overrides)
    assert response.status_code == 303 and manager.wait_idle(10)
    job, = store.list_jobs()
    assert job.state == "completed" and store.load(job.session_id).metadata.revision == 1


@pytest.mark.parametrize("known_length", [False, True])
def test_multipart_question_accepts_pdf_larger_than_text_form_limit(tmp_path, known_length):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    app = create_app(store=store, session_options={"engine": engine})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    action, fields = form(client)
    pdf = text_pdf(["Public synthetic document. " + "x" * (300 * 1024)])
    assert len(pdf) > 256 * 1024
    overrides = {} if known_length else {"CONTENT_LENGTH": None, "wsgi.input_terminated": True}
    response = client.post(action, data=fields | {
        "question": "Inspect this PDF", "files": (BytesIO(pdf), "notes.pdf", "application/pdf")},
        environ_overrides=overrides)
    assert response.status_code == 303 and manager.wait_idle(10)
    job, = store.list_jobs()
    saved = store.load(job.session_id)
    assert job.state == "completed" and saved.metadata.revision == 1
    assert saved.documents[0].original_pdf == pdf and saved.state.turns[0].question == "Inspect this PDF"


@pytest.mark.parametrize("filename,media_type,data", [
    ("bad.png", "image/png", b"malformed image"),
    ("active.svg", "image/svg+xml", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"),
    ("", "image/png", None),
])
def test_invalid_attachment_never_dispatches_question_or_partial_files(tmp_path, filename, media_type, data):
    if data is None:
        output = BytesIO()
        Image.new("RGB", (16, 16), "white").save(output, format="PNG")
        data = output.getvalue()
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    calls = []
    app = create_app(store=store, session_options={"engine": lambda *a, **k: calls.append(a)})
    client = app.test_client()
    action, fields = form(client)
    response = client.post(action, data=fields | {
        "question": "Keep my question together with these files",
        "files": [(BytesIO(text_pdf(["Harmless notes"])), "notes.pdf", "application/pdf"),
                  (BytesIO(data), filename, media_type)],
    })
    manager = app.extensions["research_jobs"]
    assert manager.wait_idle()
    assert response.status_code == 400
    assert b"Keep my question together with these files" in response.data
    assert calls == [] and store.list_sessions() == store.list_jobs() == ()
    manager.shutdown()


def test_http_navigation_refresh_and_two_sessions_continue_with_exact_commits(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    first = ResearchSession.create(store=store, title="Existing A", engine=engine)
    first.ask("An older saved question")
    older = first.turns
    second = store.create("Existing B")
    a_path, b_path = f"/sessions/{first.session_id}", f"/sessions/{second.metadata.session_id}"
    workers = Workers()
    app = create_app(store=store, session_options={"engine": workers})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    try:
        action, fields = form(client, a_path)
        fields["question"] = "A"
        accepted = client.post(action, data=fields)
        assert accepted.status_code == 303 and a_path in accepted.location
        a_job = manager.list(first.session_id)[0]
        assert a_job.question == "A" and a_job.revision == 1
        assert workers.started["A"].wait(5)
        # This response returns while the ordinary ask() is still at its barrier.
        assert manager.get(a_job.job_id).state == "researching"
        assert store.load(first.session_id).state.turns == older
        b_page = client.get(b_path)
        assert b_page.status_code == 200 and "Existing B" in b_page.get_data(as_text=True)
        b_action, b_fields = form(client, b_path)
        b_fields["question"] = "B"
        accepted_b = client.post(b_action, data=b_fields)
        assert accepted_b.status_code == 303 and workers.started["B"].wait(5)
        b_job = manager.list(second.metadata.session_id)[0]
        refreshed = client.get(a_path)
        assert refreshed.status_code == 200
        assert b"Researching" in refreshed.data and a_job.job_id.encode() in refreshed.data
        statuses = client.get("/jobs/status").json["jobs"]
        assert {j["session_id"]: j["state"] for j in statuses} == {
            first.session_id: "researching", second.metadata.session_id: "researching"}
        duplicate = client.post(action, data=fields)
        assert duplicate.status_code == 303 and duplicate.location == accepted.location
        assert len(manager.list(first.session_id)) == 1
        another_action, another_fields = form(client, a_path)
        refused = client.post(another_action, data=another_fields | {"question": "My unsent follow-up"})
        assert refused.status_code == 409 and b"My unsent follow-up" in refused.data
        assert b"already has an active question" in refused.data
        rename_path = a_path + "/rename"
        renamed = client.post(rename_path, data=token(client.get(a_path + "?edit=rename"), rename_path)
                              | {"title": "A renamed during research"})
        assert renamed.status_code == 303
        delete_path = a_path + "/delete"
        rejected = client.post(delete_path, data=token(client.get(delete_path), delete_path) | {"confirm": "delete"})
        assert rejected.status_code == 409 and b"Research is active" in rejected.data
        workers.release["A"].set()
        workers.release["B"].set()
        assert manager.wait_idle(10)
        returned = client.get(a_path)
        assert returned.status_code == 200 and b"A conditional result for A" in returned.data
        assert b"An older saved question" in returned.data and b"A renamed during research" in returned.data
        assert store.load(first.session_id).state.turns[:1] == older
        assert store.load(first.session_id).metadata.revision == 2
        assert store.load(second.metadata.session_id).metadata.revision == 1
        assert manager.get(a_job.job_id).state == manager.get(b_job.job_id).state == "completed"
        assert sorted(workers.calls) == ["A", "B"]
        replay_after_completion = client.post(action, data=fields)
        assert replay_after_completion.status_code == 303
        assert store.load(first.session_id).metadata.revision == 2
    finally:
        workers.finish()
        manager.wait_idle(10)
        manager.shutdown()


def test_http_failure_keeps_question_and_explicit_retry_commits_once(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    calls = []
    def fail_once(question, **kwargs):
        calls.append(question)
        if len(calls) == 1:
            raise RuntimeError("PRIVATE_EXCEPTION_PATH")
        return engine(question, **kwargs)
    app = create_app(store=store, session_options={"engine": fail_once})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    try:
        action, fields = form(client)
        accepted = client.post(action, data=fields | {"question": "Retain this failed question"})
        assert accepted.status_code == 303 and manager.wait_idle()
        job = manager.list()[0]
        location = f"/sessions/{job.session_id}"
        failed_page = client.get(location)
        assert failed_page.status_code == 200 and b"Retain this failed question" in failed_page.data
        assert b"Research failed" in failed_page.data and b"Retry this question" in failed_page.data
        assert b"PRIVATE_EXCEPTION_PATH" not in failed_page.data
        retry_path = location + f"/jobs/{job.job_id}/retry"
        retry_fields = token(failed_page, retry_path)
        retried = client.post(retry_path, data=retry_fields)
        assert retried.status_code == 303 and manager.wait_idle()
        assert store.load(job.session_id).metadata.revision == 1
        assert len(manager.list(job.session_id)) == 2
        assert calls == ["Retain this failed question"] * 2
        # A replayed retry form cannot create another execution.
        assert client.post(retry_path, data=retry_fields).status_code == 409
        assert len(manager.list(job.session_id)) == 2
    finally:
        manager.shutdown()


def test_http_restart_shows_interrupted_run_and_requires_user_retry(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    entered, release = Event(), Event()
    calls = []
    def blocked(question, **kwargs):
        calls.append(question)
        entered.set()
        assert release.wait(10)
        return engine(question, **kwargs)
    app = create_app(store=store, session_options={"engine": blocked})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    action, fields = form(client)
    accepted = client.post(action, data=fields | {"question": "Question interrupted by shutdown"})
    assert accepted.status_code == 303 and entered.wait(5)
    job = manager.list()[0]
    manager.shutdown()
    release.set()
    assert manager.wait_idle()
    restarted = create_app(store=SQLiteSessionStore(store.path), session_options={"engine": engine})
    new_manager = restarted.extensions["research_jobs"]
    try:
        new_client = restarted.test_client()
        location = f"/sessions/{job.session_id}"
        reopened = new_client.get(location)
        assert reopened.status_code == 200 and b"Research interrupted" in reopened.data
        assert b"Question interrupted by shutdown" in reopened.data
        assert new_manager.wait_idle() and calls == ["Question interrupted by shutdown"]
        assert store.load(job.session_id).metadata.revision == 0
        status = new_client.get("/jobs/status").json["jobs"][0]
        assert status["state"] == "interrupted"
        retry_path = location + f"/jobs/{job.job_id}/retry"
        retried = new_client.post(retry_path, data=token(reopened, retry_path))
        assert retried.status_code == 303 and new_manager.wait_idle()
        assert store.load(job.session_id).metadata.revision == 1
        assert new_manager.list(job.session_id)[0].state == "completed"
    finally:
        new_manager.shutdown()
