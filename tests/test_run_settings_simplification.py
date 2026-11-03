"""Offline authorization, bounded requests and historical-settings protection."""

import re
import sqlite3
from contextlib import closing
from dataclasses import replace
from threading import Event, Lock

import pytest
from reading_room_samples import no_io
from test_model_dispatch_accounting import OfflineAuth, Response, completed
from test_persistent_sessions import tmp_path as external_tmp_path
from test_reading_room import token
from test_research_loop import decision
from test_run_settings_integration import response, selected_fields
from test_run_settings_store import settings
from werkzeug.datastructures import MultiDict

from scryraven.model import ModelError, OpenAIModel
from scryraven.reading_room import create_app
from scryraven.research import _Bound, _Budget
from scryraven.run_settings import RunSettings, settings_from_form
from scryraven.session_store import SessionStoreError, SQLiteSessionStore

tmp_path = external_tmp_path


def billing_fields(client, backend="openai", authorized="1"):
    page = client.get("/").get_data(as_text=True)
    return {"form_token": re.search(r'data-billing-token="([^"]+)"', page).group(1),
            "backend": backend, "authorized": authorized}


@pytest.fixture
def app(tmp_path):
    store = SQLiteSessionStore(tmp_path / "simplification.sqlite3")
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    app.testing = True
    yield app, store, app.test_client()
    app.extensions["research_jobs"].shutdown()


@pytest.mark.parametrize("backend", ["chatgpt_plan", "openai", "openrouter"])
def test_new_submissions_own_40_requests_without_changing_other_limits(backend):
    initial = replace(settings(), external_attempt_limit=7, seconds_limit=123,
                      attention_character_limit=80_000)
    prefix = "vendor/" if backend == "openrouter" else ""
    form = MultiDict({"backend": backend, "research_model": prefix + "exact.model-v2",
                      "answer_model": prefix + "exact.other-v3", "research_reasoning": "",
                      "answer_reasoning": "high"})
    if backend == "openai":
        form["api_processing"] = "fast"
    parsed = settings_from_form(form, initial)
    assert parsed.physical_request_limit == 40
    assert (parsed.external_attempt_limit, parsed.seconds_limit, parsed.attention_character_limit) == (7, 123, 80_000)
    assert parsed.research_model == prefix + "exact.model-v2"
    assert parsed.answer_model == prefix + "exact.other-v3"
    assert parsed.model_config().research.service_tier == ("fast" if backend == "openai" else None)


@pytest.mark.parametrize("name,value", [
    ("physical_request_limit", "6"), ("physical_request_limit", "40"),
    ("physical_request_limit", "4000"), ("paid_inference_confirmed", "1"),
    ("external_attempt_limit", "0"), ("seconds_limit", "1"), ("attention_character_limit", "65536"),
    ("api_processing", "fast"),
])
def test_hidden_or_removed_controls_cannot_change_submissions(app, name, value):
    app, store, client = app
    fields = token(client.get("/"), "/ask") | {"question": "Offline question", name: value}
    assert client.post("/ask", data=fields).status_code == 400
    assert store.list_jobs() == ()


@pytest.mark.parametrize("name", ["backend", "research_model", "answer_model", "research_reasoning",
                                  "answer_reasoning", "api_processing"])
@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_missing_or_duplicate_run_fields_are_rejected(app, name, mutation):
    app, store, client = app
    fields = MultiDict(selected_fields(client))
    if mutation == "missing":
        fields.pop(name)
    else:
        fields.add(name, fields[name])
    assert client.post("/ask", data=fields).status_code == 400
    assert store.list_jobs() == ()


@pytest.mark.parametrize("model", ["", "gpt-6.1-sol", "openrouter/auto", "vendor/model:online",
                                  "https://example.test/model", "vendor/model/extra", "vendor/model?route=fast"])
def test_openrouter_submissions_reject_nonexplicit_or_routing_identifiers(app, model):
    app, store, client = app
    fields = selected_fields(client, "openrouter") | {"research_model": model}
    assert client.post("/ask", data=fields).status_code == 400
    assert store.list_jobs() == ()


@pytest.mark.parametrize("backend", ["openai", "openrouter"])
def test_authorization_is_persistent_backend_specific_revocable_and_csrf_bound(app, backend):
    app, store, client = app
    assert store.get_billing_authorizations() == {"openai": False, "openrouter": False}
    fields = billing_fields(client, backend)
    assert client.post("/settings/billing", data=fields, headers={"Origin": "https://elsewhere.test"}).status_code == 403
    assert not store.get_billing_authorizations()[backend]
    saved = client.post("/settings/billing", data=fields, headers={"Accept": "application/json"})
    assert saved.status_code == 200
    data = saved.get_json()
    assert data["billing_authorizations"][backend]
    other = "openrouter" if backend == "openai" else "openai"
    assert not data["billing_authorizations"][other]
    assert SQLiteSessionStore(store.path).get_billing_authorizations() == data["billing_authorizations"]
    assert client.post("/settings/billing", data=fields).status_code == 409
    revoked = client.post("/settings/billing", data={"form_token": data["form_token"],
        "backend": backend, "authorized": "0"}, headers={"Accept": "application/json"})
    assert revoked.status_code == 200
    assert not SQLiteSessionStore(store.path).get_billing_authorizations()[backend]
    assert store.list_jobs() == ()


@pytest.mark.parametrize("alteration", [
    {"backend": "chatgpt_plan"}, {"backend": "unknown"}, {"authorized": "true"},
    {"authorized": ""}, {"form_token": ""}, {"unexpected": "1"},
    {"backend": ["openai", "openrouter"]}, {"authorized": ["1", "0"]},
    {"form_token": ["first", "second"]},
])
def test_malformed_authorization_never_grants_permission(app, alteration):
    app, store, client = app
    fields = billing_fields(client) | alteration
    assert client.post("/settings/billing", data=fields).status_code in {400, 409}
    assert store.get_billing_authorizations() == {"openai": False, "openrouter": False}


@pytest.mark.parametrize("backend", ["openai", "openrouter"])
def test_paid_admission_and_retry_require_current_authorization(app, backend):
    app, store, client = app
    fields = selected_fields(client, backend)
    store.set_billing_authorization(backend, False)
    assert client.post("/ask", data=fields).status_code == 400
    assert store.list_jobs() == ()
    store.set_billing_authorization(backend, True)
    accepted = client.post("/ask", data=fields)
    assert accepted.status_code == 303 and app.extensions["research_jobs"].wait_idle()
    original, = store.list_jobs()
    assert original.state == "failed"  # no_io never performs model I/O.
    store.set_billing_authorization(backend, False)
    retry_url = f"/sessions/{original.session_id}/jobs/{original.job_id}/retry"
    blocked = client.post(retry_url, data=token(client.get(accepted.location), retry_url))
    assert blocked.status_code == 400 and len(store.list_jobs()) == 1
    assert store.get_job(original.job_id).run_settings == original.run_settings


@pytest.mark.parametrize("backend", ["api", "openrouter", "chatgpt_plan"])
def test_40th_physical_request_is_allowed_and_41st_denied_for_each_backend(monkeypatch, backend):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-only")
    selected = replace(settings(), research_model="vendor/research" if backend == "openrouter" else "research",
                       answer_model="vendor/answer" if backend == "openrouter" else "answer",
                       backend="openai" if backend == "api" else backend,
                       api_processing="standard" if backend == "api" else None,
                       physical_request_limit=40)
    shared = _Budget(selected.limits(), lambda: 0)
    posts, usage = [], []
    def post(url, **kwargs):
        posts.append(kwargs["json"])
        return Response(completed(kwargs["json"]))
    auth = OfflineAuth() if backend == "chatgpt_plan" else None
    model = OpenAIModel(selected.model_config(), backend=backend, post=post, plan_auth=auth,
                        usage_observer=usage.append)
    for _ in range(40):
        assert model("answer", "Offline", {}, {}, before_request=shared.before_model) == "{}"
    with pytest.raises(_Bound):
        model("answer", "Offline", {}, {}, before_request=shared.before_model)
    assert shared.physical == len(usage) == 40
    assert len(auth.posts if auth else posts) == 40


@pytest.mark.parametrize("backend", ["openai", "openrouter"])
@pytest.mark.parametrize("boundary", ["next_role", "continuation"])
def test_revocation_blocks_the_next_physical_request_without_rewriting_snapshot(tmp_path, monkeypatch, backend, boundary):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-only")
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-only")
    store = SQLiteSessionStore(tmp_path / "revoked.sqlite3")
    calls = []
    def post(url, **kwargs):
        calls.append(kwargs["json"])
        if boundary == "continuation" and len(calls) == 1:
            return response(kwargs["json"], decision("return"))
        store.set_billing_authorization(backend, False)
        return response(kwargs["json"], decision("return") if boundary == "next_role" else [{
            "type": "function_call", "name": "calculate", "call_id": "revoked-calculation",
            "arguments": '{"expression":"12 - 4"}'}])
    app = create_app(store=store, session_options={"search": no_io, "fetch": no_io},
                     run_model_factory=lambda selected: OpenAIModel(selected.model_config(),
                         backend="api" if backend == "openai" else backend, post=post))
    manager, client = app.extensions["research_jobs"], app.test_client()
    try:
        accepted = client.post("/ask", data=selected_fields(client, backend))
        assert accepted.status_code == 303 and manager.wait_idle()
        job, = store.list_jobs()
        assert job.state == "failed" and job.error_code == "paid_inference_authorization_required"
        assert job.run_settings.physical_request_limit == 40
        assert len(calls) == len(job.run_receipt["requests"]) == (1 if boundary == "next_role" else 2)
        assert store.load(job.session_id).state.turns == ()
    finally:
        manager.shutdown()


def test_revocation_prevents_a_queued_paid_job_from_starting(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-only")
    store = SQLiteSessionStore(tmp_path / "queued.sqlite3")
    started, release, lock, calls = Event(), Event(), Lock(), []
    def post(url, **kwargs):
        with lock:
            calls.append(kwargs["json"])
            if len(calls) == 2:
                started.set()
        assert release.wait(10)
        return response(kwargs["json"], decision("return"))
    app = create_app(store=store, session_options={"search": no_io, "fetch": no_io},
                     run_model_factory=lambda selected: OpenAIModel(selected.model_config(), post=post))
    manager, client = app.extensions["research_jobs"], app.test_client()
    try:
        assert client.post("/ask", data=selected_fields(client)).status_code == 303
        assert client.post("/ask", data=selected_fields(client)).status_code == 303
        assert started.wait(5)
        assert client.post("/ask", data=selected_fields(client)).status_code == 303
        assert sum(job.state == "queued" for job in store.list_jobs()) == 1
        store.set_billing_authorization("openai", False)
        release.set()
        assert manager.wait_idle()
        assert len(calls) == 2
        for job in store.list_jobs():
            assert job.state == "failed" and job.error_code == "paid_inference_authorization_required"
            assert job.run_settings.physical_request_limit == 40
    finally:
        release.set()
        manager.shutdown()


def test_billing_authorization_can_be_changed_from_a_saved_session(app):
    app, store, client = app
    saved = store.create("Offline session")
    page = client.get("/sessions/" + saved.metadata.session_id).get_data(as_text=True)
    fields = {"form_token": re.search(r'data-billing-token="([^"]+)"', page).group(1),
              "backend": "openai", "authorized": "1"}
    assert client.post("/settings/billing", data=fields).status_code == 303
    assert store.get_billing_authorizations()["openai"]


@pytest.mark.parametrize("backend,processing", [("openai", "standard"), ("openai", "fast"),
                                               ("openrouter", None), ("chatgpt_plan", None)])
@pytest.mark.parametrize("legacy_limit", [6, 12])
def test_http_retry_retains_historical_allowance_tier_and_newer_preferences(tmp_path, processing, backend, legacy_limit):
    store = SQLiteSessionStore(tmp_path / "historical-retry.sqlite3")
    original = replace(settings("vendor/exact-model" if backend == "openrouter" else "exact-model", backend),
                       api_processing=processing, physical_request_limit=legacy_limit)
    old = store.accept_job("Original question", idempotency_key="historical-http-retry-01", run_settings=original)
    store.fail_job(old.job_id)
    newer = replace(original, research_model="vendor/new-model" if backend == "openrouter" else "new-model",
                    physical_request_limit=40)
    store.set_run_settings(newer)
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    manager, client = app.extensions["research_jobs"], app.test_client()
    try:
        if backend != "chatgpt_plan":
            fields = billing_fields(client, backend)
            assert client.post("/settings/billing", data=fields).status_code == 303
        retry_url = f"/sessions/{old.session_id}/jobs/{old.job_id}/retry"
        assert client.post(retry_url, data=token(client.get("/sessions/" + old.session_id), retry_url)).status_code == 303
        assert manager.wait_idle()
        assert len(store.list_jobs()) == 2
        assert all(job.run_settings == original for job in store.list_jobs())
        assert store.get_run_settings() == newer
        reopened = SQLiteSessionStore(store.path)
        assert all(job.run_settings.physical_request_limit == legacy_limit for job in reopened.list_jobs())
        assert all(job.run_settings.api_processing == processing for job in reopened.list_jobs())
    finally:
        manager.shutdown()


def test_authorizer_survives_cloning_and_denied_requests_have_no_usage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-only")
    usage = []
    def denied():
        raise ModelError("paid_inference_authorization_required")
    model = OpenAIModel(settings().model_config(), post=no_io, request_authorizer=denied,
                        usage_observer=usage.append).with_config(settings().model_config())
    with pytest.raises(ModelError, match="^paid_inference_authorization_required$"):
        model("answer", "Offline", {}, {}, before_request=no_io)
    assert usage == []


def test_authorization_time_cannot_renew_the_request_deadline(monkeypatch):
    from scryraven import model as model_module

    monkeypatch.setenv("OPENAI_API_KEY", "offline-only")
    now, usage = [0], []
    monkeypatch.setattr(model_module, "monotonic", lambda: now[0])
    def slow_authorization():
        now[0] = 6
    model = OpenAIModel(settings().model_config(), post=no_io, request_authorizer=slow_authorization,
                        timeout_seconds=5, usage_observer=usage.append)
    with pytest.raises(ModelError, match="^model_request_timed_out$"):
        model("answer", "Offline", {}, {}, before_request=no_io)
    assert usage == []


def test_authorization_store_fails_closed_on_malformed_values(app):
    app, store, client = app
    with closing(sqlite3.connect(store.path)) as connection:
        connection.execute("INSERT INTO app_preferences VALUES (?,?)", ("billing_authorized:openai", '"true"'))
        connection.commit()
    assert not store.get_billing_authorizations()["openai"]
    for backend, value in (([], True), ("openai", 1), ("chatgpt_plan", True)):
        with pytest.raises(SessionStoreError, match="invalid_billing_authorization"):
            store.set_billing_authorization(backend, value)


@pytest.mark.parametrize("field,value", [("backend", []), ("research_reasoning", []),
    ("api_processing", []), ("physical_request_limit", True), ("seconds_limit", float("nan")),
    ("research_model", True)])
def test_malformed_saved_settings_fail_as_validation_errors(field, value):
    with pytest.raises(ValueError, match="invalid_run_settings"):
        RunSettings.from_dict(settings().to_dict() | {field: value})
