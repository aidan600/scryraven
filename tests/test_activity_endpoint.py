"""Exercise owner-scoped activity through the Reading Room's ordinary job path."""

import json
from io import BytesIO
from threading import Event
from zipfile import ZipFile

from test_hosted_identity import validator
from test_hosted_reading_room import config as hosted_config
from test_hosted_reading_room import form, get, post
from test_hosted_reading_room import key as hosted_key
from test_persistent_sessions import tmp_path as external_tmp_path
from test_reading_room_jobs import form as local_form
from test_research_loop import Script, answer, decision, request, search

from scryraven.model import ModelError
from scryraven.reading_room import create_app
from scryraven.research_activity import QUERY_CHARACTERS
from scryraven.session_store import SQLiteSessionStore

tmp_path = external_tmp_path
config = hosted_config
key = hosted_key


def test_activity_is_available_only_to_exact_owner_and_stays_out_of_other_surfaces(config, key):
    query = "<owner-only-search> " + "z" * QUERY_CHARACTERS
    model = Script(decision(requests=[request(query=query)], briefing="private briefing"),
                   decision("return", ["E1"]), answer())
    store = SQLiteSessionStore(config.database)
    other = store.create("Other", owner_id="bob@example.test")
    app = create_app(store=store, hosted=config,
                     identity_validator=validator(config, key),
                     run_model_factory=lambda _: model, session_options={"search": search})
    room = (app,)
    manager = app.extensions["research_jobs"]
    try:
        response = post(room, config, key, "/ask", {
            "form_token": form(get(room, config, key)), "question": "An ordinary lookup",
            "idempotency_key": "owner-activity-example",
        })
        assert response.status_code == 303 and manager.wait_idle()
        job, = store.list_jobs()
        url = f"/sessions/{job.session_id}/jobs/{job.job_id}/activity"
        owned = get(room, config, key, url)
        assert owned.status_code == 200 and owned.headers["Cache-Control"] == "no-store"
        activity = owned.json
        assert activity["state"] == "completed"
        assert activity["current"]["label"] == "Answer saved"
        actual = [operation for item in activity["events"] for operation in item.get("operations", [])
                  if operation.get("query")]
        assert actual[-1]["query"] == query[:QUERY_CHARACTERS] and actual[-1]["query_truncated"]
        assert actual[-1]["candidates"] == actual[-1]["highlights"] == 1
        assert "private briefing" not in owned.text and "The stated value is seven" not in owned.text
        assert get(room, config, key, url + f"?after={activity['cursor']}").json["events"] == []
        assert get(room, config, key, url + "?after=99999").json["reset"]
        assert get(room, config, key, url + "?after=0&after=0").status_code == 400
        assert get(room, config, key, url, email="bob@example.test").status_code == 404
        assert get(room, config, key, url, email=config.admin_email).status_code == 404
        mismatch = f"/sessions/{other.metadata.session_id}/jobs/{job.job_id}/activity"
        assert get(room, config, key, mismatch, email="bob@example.test").status_code == 404
        assert app.test_client().get(url, base_url=config.origin).status_code == 401

        page = get(room, config, key, f"/sessions/{job.session_id}", email=config.admin_email)
        assert page.status_code == 200 and url not in page.text and "owner-only-search" not in page.text
        assert "owner-only-search" not in get(room, config, key, "/jobs/status").text
        exported = get(room, config, key, f"/admin/sessions/{job.session_id}/export", email=config.admin_email)
        with ZipFile(BytesIO(exported.data)) as archive:
            exported_session = json.loads(archive.read("session.json"))
        assert "owner-only-search" not in json.dumps(exported_session["jobs"])

        page = get(room, config, key, f"/sessions/{job.session_id}/delete")
        submitted = post(room, config, key, f"/sessions/{job.session_id}/delete", {
            "form_token": page.text.split('id="delete-confirmation"', 1)[1]
            .split('name="form_token" value="', 1)[1].split('"', 1)[0],
            "confirm": "delete",
        })
        assert submitted.status_code == 303
        assert get(room, config, key, url).status_code == 404
    finally:
        manager.shutdown()
        app.extensions["research_activity"].close()


def test_activity_does_not_report_saved_answer_before_commit_or_after_failed_job(tmp_path, monkeypatch):
    waiting = Event()
    release = Event()
    store = SQLiteSessionStore(tmp_path / "activity.sqlite3")
    commit = store.commit_job

    def pause_commit(*args, **kwargs):
        waiting.set()
        assert release.wait(5)
        return commit(*args, **kwargs)

    monkeypatch.setattr(store, "commit_job", pause_commit)
    model = Script(decision(), decision("return", ["E1"]), answer(),
                   ModelError("model_transport_failed"))
    app = create_app(store=store, session_options={"model": model, "search": search})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    try:
        action, fields = local_form(client)
        assert client.post(action, data=fields | {"question": "Lookup"}).status_code == 303
        assert waiting.wait(5)
        job, = store.list_jobs()
        url = f"/sessions/{job.session_id}/jobs/{job.job_id}/activity"
        intermediate = client.get(url).json
        assert intermediate["state"] == "researching"
        assert intermediate["current"]["label"] == "Checking citation references"
        assert "Answer saved" not in str(intermediate)
        release.set()
        assert manager.wait_idle()
        assert client.get(url).json["current"]["label"] == "Answer saved"

        action, fields = local_form(client)
        assert client.post(action, data=fields | {"question": "A separate lookup"}).status_code == 303
        assert manager.wait_idle()
        failed = next(item for item in store.list_jobs() if item.state == "failed")
        page = client.get(f"/sessions/{failed.session_id}")
        failed_url = f"/sessions/{failed.session_id}/jobs/{failed.job_id}/activity"
        assert f'data-activity-archive="{failed_url}"' in page.text
        activity = client.get(failed_url).json
        assert activity["state"] == "failed" and activity["current"]["label"] == "Research failed"
        assert activity["available"]
    finally:
        release.set()
        manager.shutdown()
        app.extensions["research_activity"].close()
