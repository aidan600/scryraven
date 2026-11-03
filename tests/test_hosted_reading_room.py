"""Offline hosted HTTP security boundaries with signed identities and synthetic custody."""

import json
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from time import time
from zipfile import ZipFile

import pytest
import test_hosted_identity as identity
from pdf_fixtures import text_pdf
from PIL import Image
from reading_room_samples import first_script, no_io, source_search
from test_persistent_sessions import tmp_path as external_tmp_path
from test_research_loop import Script

from scryraven.reading_room import create_app
from scryraven.session_store import SQLiteSessionStore, _decode

tmp_path = external_tmp_path
key = identity.key


@pytest.fixture
def config(tmp_path):
    return replace(identity.config.__wrapped__(tmp_path), submissions_per_day=1)


@pytest.fixture
def room(config, key):
    store = SQLiteSessionStore(config.database)
    saved = store.create("Alice private title", owner_id="alice@example.test")
    payload = (Path(__file__).parent / "fixtures/historical_session_v1.json").read_text()
    store.commit(saved.metadata.session_id, 0, _decode(payload, 1))
    store.attach_document(saved.metadata.session_id, 1, "synthetic.pdf", "application/pdf", text_pdf(["SYNTHETIC_PDF_BODY"]))
    other = store.create("Bob private title", owner_id="bob@example.test")
    app = create_app(store=store, hosted=config, identity_validator=identity.validator(config, key),
                     session_options={"model": no_io, "search": source_search, "fetch": no_io},
                     run_model_factory=lambda settings: Script(*first_script()))
    app.config["TESTING"] = True
    return app, store, saved.metadata.session_id, other.metadata.session_id


def headers(config, key, email="alice@example.test"):
    return {"Cf-Access-Jwt-Assertion": identity.token(config, key, email=email)}


def get(room, config, key, path="/", email="alice@example.test", **kwargs):
    return room[0].test_client().get(path, base_url=config.origin, headers=headers(config, key, email), **kwargs)


def form(response, action="ask"):
    import re

    if action == "ask":
        area = response.text.split('class="ask-form"', 1)[1]
    else:
        area = response.text.split(f'/{action}"', 1)[1]
    return re.search(r'name="form_token" value="([^"]+)"', area)[1]


def post(room, config, key, path, data, email="alice@example.test", **kwargs):
    return room[0].test_client().post(path, base_url=config.origin, headers=headers(config, key, email),
                                    data=data, **kwargs)


def test_every_data_route_rejects_unauthenticated_and_forged_identity(room, config):
    app, _, alice, _ = room
    paths = ["/", "/jobs/status", "/admin", f"/sessions/{alice}",
             f"/sessions/{alice}/documents/D1/original", f"/sessions/{alice}/images/I1/preview",
             f"/sessions/{alice}/images/I1/original", f"/sessions/{alice}/delete",
             f"/admin/sessions/{alice}/export"]
    for path in paths:
        for forged in ({}, {"Cf-Access-Authenticated-User-Email": config.admin_email},
                       {"X-Forwarded-User": config.admin_email, "X-Forwarded-Host": config.hostname},
                       {"Cf-Access-Jwt-Assertion": "bogus"}):
            response = app.test_client().get(path, base_url=config.origin, headers=forged)
            assert response.status_code == 401, path
            assert "Alice private" not in response.text
    for path in ("/ask", "/settings/billing", f"/sessions/{alice}/ask",
                 f"/sessions/{alice}/rename", f"/sessions/{alice}/delete",
                 f"/sessions/{alice}/jobs/{'c' * 32}/retry"):
        assert app.test_client().post(path, base_url=config.origin, data={}).status_code == 401


def test_foreign_session_routes_and_jobs_are_undiscoverable(room, config, key):
    _, _, alice, bob = room
    for suffix in ("", "/delete", "/documents/D1/original", "/images/I1/preview", "/images/I1/original"):
        assert get(room, config, key, f"/sessions/{alice}{suffix}", email="bob@example.test").status_code == 404
    for suffix in ("/ask", "/rename", "/delete", f"/jobs/{'c' * 32}/retry"):
        assert post(room, config, key, f"/sessions/{alice}{suffix}", {}, email="bob@example.test").status_code == 404
    response = get(room, config, key, email="bob@example.test")
    assert bob in response.text and alice not in response.text and "Alice private" not in response.text
    assert get(room, config, key, "/admin").status_code == 404
    assert get(room, config, key, f"/admin/sessions/{bob}/export").status_code == 404


def test_admin_readonly_historical_citations_pdf_and_selected_export(room, config, key):
    _, store, alice, bob = room
    page = get(room, config, key, f"/sessions/{alice}", email=config.admin_email)
    assert page.status_code == 200 and "read only" in page.text
    assert "citation" in page.text and "View saved excerpt" in page.text
    assert 'class="ask-form"' not in page.text and 'class="session-actions"' not in page.text
    for suffix in ("/ask", "/rename", "/delete", f"/jobs/{'c' * 32}/retry"):
        assert post(room, config, key, f"/sessions/{alice}{suffix}", {}, email=config.admin_email).status_code == 404
    assert get(room, config, key, f"/sessions/{alice}/delete", email=config.admin_email).status_code == 404
    pdf = get(room, config, key, f"/sessions/{alice}/documents/D1/original", email=config.admin_email)
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF-")
    admin = get(room, config, key, "/admin", email=config.admin_email)
    assert alice in admin.text and bob in admin.text and "bytes" in admin.text
    response = get(room, config, key, f"/admin/sessions/{alice}/export", email=config.admin_email)
    assert response.status_code == 200 and response.mimetype == "application/zip"
    with ZipFile(BytesIO(response.data)) as archive:
        record = json.loads(archive.read("session.json"))
        assert record["metadata"]["owner_id"] == "alice@example.test"
        assert record["state"]["turns"][0]["citations"]
        assert record["documents"][0]["pages"] == ["SYNTHETIC_PDF_BODY"]
        assert archive.read("attachments/D1.pdf") == pdf.data
        assert bob not in " ".join(archive.namelist())
    assert store.load(alice).metadata.revision == 1


def test_hosted_forms_bind_identity_origin_and_fixed_operator_policy(room, config, key):
    _, store, _, _ = room
    initial = get(room, config, key)
    token = form(initial)
    # Even a valid form copied between identities cannot authorize a new owner.
    assert post(room, config, key, "/ask", {"form_token": token, "question": "copied"},
                email="bob@example.test").status_code == 409
    for data in ({"backend": "openrouter"}, {"research_model": "unauthorized"},
                 {"owner_id": config.admin_email}, {"session_id": "a" * 32},
                 {"physical_request_limit": "900"}, {"paid_inference_confirmed": "1"},
                 {"api_key": "synthetic-should-never-be-accepted"}):  # pragma: allowlist secret
        assert post(room, config, key, "/ask", {"form_token": token, "question": "tampered", **data}).status_code == 400
    response = room[0].test_client().post("/ask", base_url=config.origin,
        headers={**headers(config, key), "Origin": "https://attacker.example.test"},
        data={"form_token": token, "question": "cross site"})
    assert response.status_code == 403
    assert post(room, config, key, "/settings/billing", {"authorized": "1"}).status_code == 403
    assert not store.list_jobs()
    assert "Configured by the operator" in initial.text
    assert 'id="run-settings-dialog"' not in initial.text


def test_owned_submission_attachments_quota_replay_diagnostics_and_reopen(room, config, key):
    app, store, _, bob = room
    # Use one accepted question per user while retaining the existing synthetic sessions.
    token = form(get(room, config, key))
    png = BytesIO()
    Image.new("RGB", (2, 2), "red").save(png, format="PNG")
    body = {"form_token": token, "idempotency_key": "synthetic-submission-000001", "question": "Synthetic canopy",
            "files": (BytesIO(png.getvalue()), "red.png", "image/png")}
    response = post(room, config, key, "/ask", body)
    assert response.status_code == 303
    assert app.extensions["research_jobs"].wait_idle()
    job = store.list_jobs()[0]
    assert job.run_settings == config.run_settings and job.state == "completed"
    saved = store.load(job.session_id)
    assert saved.metadata.owner_id == "alice@example.test" and saved.state.turns[0].citations
    image = get(room, config, key, f"/sessions/{job.session_id}/images/I1/original")
    assert image.status_code == 200 and image.data == png.getvalue()
    assert get(room, config, key, f"/sessions/{job.session_id}/images/I1/original", email="bob@example.test").status_code == 404
    assert job.session_id not in get(room, config, key, "/jobs/status", email="bob@example.test").text
    assert bob not in get(room, config, key, "/jobs/status").text
    repeated = post(room, config, key, "/ask", {**body, "files": (BytesIO(png.getvalue()), "red.png", "image/png")})
    assert repeated.status_code == 303 and len(store.list_jobs()) == 1
    quota = post(room, config, key, "/ask", {"form_token": token, "question": "Second", "idempotency_key": "synthetic-000002"})
    assert quota.status_code == 429 and "daily submission limit" in quota.text
    exported = get(room, config, key, f"/admin/sessions/{job.session_id}/export", email=config.admin_email)
    with ZipFile(BytesIO(exported.data)) as archive:
        files = [name for name in archive.namelist() if name.startswith("diagnostics/")]
        assert len(files) == 2
        for name in files:
            records = [json.loads(line) for line in archive.read(name).splitlines()]
            assert all(record["owner_id"] == "alice@example.test" for record in records)
            assert all(record["session_id"] == job.session_id for record in records)
    sink = app.extensions["hosted_diagnostics"]
    sink.clock = lambda: time() + 31 * 86400
    sink.maintenance()
    assert sink.export(job.session_id) == {}
    assert store.load(job.session_id) == saved
    assert get(room, config, key, f"/sessions/{job.session_id}/images/I1/original").data == png.getvalue()
    app.extensions["research_jobs"].shutdown()
    reopened = create_app(store=SQLiteSessionStore(store.path), hosted=config,
                          identity_validator=identity.validator(config, key),
                          session_options={"model": no_io, "search": no_io, "fetch": no_io})
    assert reopened.test_client().get(f"/sessions/{job.session_id}", base_url=config.origin,
                                      headers=headers(config, key)).status_code == 200
    assert store.load(job.session_id) == saved


def test_missing_or_unowned_database_is_not_imported(config, key):
    store = SQLiteSessionStore(config.database)
    old = store.create("Synthetic personal database")
    with pytest.raises(ValueError, match="hosted_database_contains_unowned_sessions"):
        create_app(store=store, hosted=config, identity_validator=identity.validator(config, key))
    assert store.load(old.metadata.session_id).metadata.owner_id is None


def test_hosted_factory_never_selects_or_opens_personal_default(config, key, monkeypatch):
    from scryraven import session_store

    monkeypatch.setattr(session_store, "default_session_path", lambda: pytest.fail("Personal database selected"))
    app = create_app(hosted=config, identity_validator=identity.validator(config, key),
                     session_options={"model": no_io})
    app.extensions["research_jobs"].shutdown()
    assert config.database.is_file()
    unrelated = config.data_dir / "unrelated-personal.sqlite3"
    with pytest.raises(ValueError, match="hosted_database_location_required"):
        create_app(database=unrelated, hosted=config, session_options={"model": no_io})
    assert not unrelated.exists()


def test_hosted_health_does_not_expose_data_or_trust_proxy_headers(room, config, key):
    app, _, alice, _ = room
    assert app.test_client().get("/healthz", base_url="http://healthcheck.railway.app").json == {"status": "ok"}
    for origin in ("http://healthcheck.railway.app", "http://origin.up.railway.app", "http://127.0.0.1"):
        response = app.test_client().get(f"/sessions/{alice}", base_url=origin,
            headers={**headers(config, key), "X-Forwarded-Host": config.hostname, "X-Forwarded-Proto": "https"})
        assert response.status_code == 400
    page = get(room, config, key)
    assert page.headers["Cache-Control"] == "no-store"
    assert page.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
