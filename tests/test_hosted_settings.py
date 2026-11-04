"""Hosted preferences, exact compatibility and immutable accepted-job settings."""

import json
from dataclasses import replace
from threading import Event, Lock

import pytest
import test_hosted_identity as identity
from reading_room_samples import no_io
from test_reading_room import Form
from test_research_loop import answer, decision

from scryraven.hosted_preferences import HOSTED_MODEL_CHOICES, HostedPreferences, validate_hosted_settings
from scryraven.model import ModelError
from scryraven.reading_room import create_app
from scryraven.session_store import SQLiteSessionStore

config = identity.config
key = identity.key


def test_saved_hosted_defaults_override_environment_and_preserve_local_preferences(config):
    store = SQLiteSessionStore(config.database)
    original = config.run_settings
    store.set_run_settings(replace(original, api_processing="fast"))
    preferences = HostedPreferences(store, original)
    assert preferences.defaults() == original
    saved = replace(original, research_model="gpt-6-luna", research_reasoning="high", api_processing="fast")
    preferences.save_defaults(saved.to_dict())
    preferences.save_processing("alice@example.test", "standard")
    restarted = HostedPreferences(SQLiteSessionStore(config.database), replace(original, research_reasoning="low"))
    assert restarted.defaults() == saved
    assert restarted.for_user("alice@example.test").api_processing == "standard"
    assert restarted.for_user("bob@example.test") == saved
    assert restarted.for_user(config.admin_email, admin=True) == saved
    assert store.get_run_settings() == replace(original, api_processing="fast")


def test_corrupt_saved_defaults_do_not_silently_reroute_to_environment(config):
    store = SQLiteSessionStore(config.database)
    store.set_hosted_preferences({**config.run_settings.to_dict(), "answer_model": "arbitrary-model"})
    with pytest.raises(ValueError, match="invalid_run_settings"):
        HostedPreferences(store, config.run_settings)


@pytest.mark.parametrize("model,effort", [
    (model, effort or None) for model, choice in HOSTED_MODEL_CHOICES.items() for effort in choice["reasoning"]
])
def test_exact_hosted_family_supported_efforts(config, model, effort):
    assert validate_hosted_settings(replace(config.run_settings, research_model=model, research_reasoning=effort))


@pytest.mark.parametrize("change", [
    {"research_model": "gpt-6.1-sol", "research_reasoning": "none"},
    {"answer_model": "gpt-6.1-sol", "answer_reasoning": "none"},
    {"research_model": "gpt-6-luna-latest"}, {"answer_model": "arbitrary-model"},
    {"backend": "chatgpt_plan", "api_processing": None},
])
def test_unsupported_hosted_routing_is_rejected(config, change):
    with pytest.raises(ValueError, match="invalid_run_settings"):
        validate_hosted_settings(replace(config.run_settings, **change))


def hosted_room(config, key, factory):
    store = SQLiteSessionStore(config.database)
    app = create_app(store=store, hosted=config, identity_validator=identity.validator(config, key),
                     run_model_factory=factory,
                     session_options={"model": no_io, "search": no_io, "fetch": no_io})
    app.config["TESTING"] = True

    def get(path="/", email="alice@example.test"):
        return app.test_client().get(path, base_url=config.origin,
                                    headers={"Cf-Access-Jwt-Assertion": identity.token(config, key, email=email)})

    def post(path, fields, email="alice@example.test"):
        return app.test_client().post(path, base_url=config.origin, data=fields,
                                     headers={"Cf-Access-Jwt-Assertion": identity.token(config, key, email=email),
                                              "Origin": config.origin})

    return app, store, get, post


def completed_model(stage, *_):
    return json.dumps(decision("return") if stage == "research" else
                      answer("Eight remain.", support_basis="user_premises"))


def test_admin_and_tester_controls_are_identity_bound_and_strict(config, key):
    _, store, get, post = hosted_room(config, key, lambda _: completed_model)
    admin = Form(get(email=config.admin_email).text, "/settings/hosted").fields
    assert admin["research_model"] == config.run_settings.research_model
    assert post("/settings/hosted", admin).status_code == 403
    for change in ({"backend": "openrouter"}, {"api_key": "synthetic-not-a-key"},  # pragma: allowlist secret
                   {"physical_request_limit": "100"}, {"owner_id": config.admin_email},
                   {"answer_reasoning": "none"}, {"research_model": "gpt-6-luna-latest"}):
        fields = Form(get(email=config.admin_email).text, "/settings/hosted").fields
        assert post("/settings/hosted", {**fields, **change}, config.admin_email).status_code == 400
    processing = Form(get().text, "/settings/processing").fields
    assert post("/settings/processing", processing, "bob@example.test").status_code == 409
    assert post("/settings/processing", {**processing, "research_model": "gpt-6-luna"}).status_code == 400
    assert post("/settings/processing", {**processing, "api_processing": "priority"}).status_code == 400
    processing = Form(get().text, "/settings/processing").fields
    assert post("/settings/processing", {**processing, "api_processing": "fast"}).status_code == 303
    assert store.get_hosted_processing("alice@example.test") == "fast"
    assert store.get_hosted_processing("bob@example.test") is None
    assert store.get_hosted_preferences() is None


def test_changes_leave_four_active_and_fifth_queued_snapshots_unchanged(config, key):
    release, four_started = Event(), Event()
    captured, lock = [], Lock()

    def factory(settings):
        with lock:
            captured.append(settings)
            if len(captured) == 4:
                four_started.set()

        def model(stage, *args):
            assert release.wait(10)
            return completed_model(stage, *args)
        return model

    app, store, get, post = hosted_room(config, key, factory)
    try:
        for number in range(5):
            fields = Form(get().text, "/ask").fields
            assert post("/ask", {**fields, "question": f"Given 10 apples and 2 removed, how many remain? {number}"}).status_code == 303
        assert four_started.wait(5)
        jobs = store.list_jobs()
        assert sum(job.state == "researching" for job in jobs) == 4
        assert sum(job.state == "queued" for job in jobs) == 1
        admin = Form(get(email=config.admin_email).text, "/settings/hosted").fields
        admin.update(research_model="gpt-6-luna", research_reasoning="high", api_processing="fast")
        assert post("/settings/hosted", admin, config.admin_email).status_code == 303
        assert all(job.run_settings == config.run_settings for job in store.list_jobs())
        release.set()
        assert app.extensions["research_jobs"].wait_idle(15)
        assert captured == [config.run_settings] * 5
        fields = Form(get().text, "/ask").fields
        assert post("/ask", {**fields, "question": "New default question"}).status_code == 303
        assert app.extensions["research_jobs"].wait_idle(10)
        latest = store.list_jobs()[0]
        assert latest.run_settings.research_model == "gpt-6-luna"
        assert latest.run_settings.research_reasoning == "high" and latest.run_settings.api_processing == "fast"
        assert latest.state == "completed"
        assert all(job.state == "completed" for job in store.list_jobs())
    finally:
        release.set()


@pytest.mark.parametrize("explicit_processing", [False, True])
def test_exact_submission_replay_keeps_snapshot_after_defaults_change(config, key, explicit_processing):
    app, store, get, post = hosted_room(config, key, lambda _: completed_model)
    fields = Form(get().text, "/ask").fields
    fields.update(question="Given ten apples and two removed, how many remain?", idempotency_key="replayed-admission")
    if explicit_processing:
        fields["api_processing"] = "standard"
    first = post("/ask", fields)
    assert first.status_code == 303
    assert app.extensions["research_jobs"].wait_idle(10)
    original = store.list_jobs()[0]
    admin = Form(get(email=config.admin_email).text, "/settings/hosted").fields
    admin.update(research_model="gpt-6-luna", research_reasoning="high", api_processing="fast")
    assert post("/settings/hosted", admin, config.admin_email).status_code == 303
    repeated = post("/ask", fields)
    assert repeated.status_code == 303 and repeated.location == first.location
    assert store.list_jobs() == (original,)
    assert post("/ask", {**fields, "question": "An edited question"}).status_code == 409
    assert post("/ask", {**fields, "api_processing": "fast"}).status_code == 409
    assert store.list_jobs() == (original,)


def test_invalid_settings_return_target_cannot_save_preferences(config, key):
    _, store, get, post = hosted_room(config, key, lambda _: completed_model)
    other = store.create("Other owner's conversation", owner_id="bob@example.test")
    fields = Form(get().text, "/settings/processing").fields
    fields.update(api_processing="fast", return_session_id=other.metadata.session_id)
    assert post("/settings/processing", fields).status_code == 404
    assert store.get_hosted_processing("alice@example.test") is None
    admin = Form(get(email=config.admin_email).text, "/settings/hosted").fields
    admin.update(api_processing="fast", return_session_id=other.metadata.session_id)
    assert post("/settings/hosted", admin, config.admin_email).status_code == 404
    assert store.get_hosted_preferences() is None


def test_shutdown_without_restart_does_not_invent_interruption_cause(config, key):
    started, release = Event(), Event()

    def model(stage, *args):
        started.set()
        assert release.wait(10)
        return completed_model(stage, *args)

    app, store, get, post = hosted_room(config, key, lambda _: model)
    try:
        fields = Form(get().text, "/ask").fields
        assert post("/ask", {**fields, "question": "Given ten apples and two removed, how many remain?"}).status_code == 303
        assert started.wait(5)
        app.extensions["research_jobs"].shutdown()
        job = store.list_jobs()[0]
        assert job.state == "interrupted" and job.error_code == "server_interrupted"
        message = get("/jobs/status").get_json()["jobs"][0]["error"]
        assert message == ("The server interrupted this run. Your question and attachments are saved; "
                           "retry explicitly to start again.")
        assert "restart" not in message
        assert not store.load(job.session_id).state.turns
    finally:
        release.set()
        assert app.extensions["research_jobs"].wait_idle(10)


def test_retry_preserves_original_snapshot_after_admin_changes_and_restart(config, key):
    calls = []

    def factory(settings):
        calls.append(settings)
        if len(calls) == 1:
            def fail(*_):
                raise ModelError("model_request_rejected")
            return fail
        return completed_model

    app, store, get, post = hosted_room(config, key, factory)
    fields = Form(get().text, "/ask").fields
    assert post("/ask", {**fields, "question": "Given 10 apples and 2 removed, how many remain?"}).status_code == 303
    assert app.extensions["research_jobs"].wait_idle(10)
    old = store.list_jobs()[0]
    assert old.state == "failed"
    admin = Form(get(email=config.admin_email).text, "/settings/hosted").fields
    admin.update(research_model="gpt-6-luna", research_reasoning="high", api_processing="fast")
    assert post("/settings/hosted", admin, config.admin_email).status_code == 303
    app.extensions["research_jobs"].shutdown()
    app, store, get, post = hosted_room(config, key, factory)
    assert len(calls) == 1  # Restart does not replay the failed question.
    path = f"/sessions/{old.session_id}/jobs/{old.job_id}/retry"
    retry = Form(get(f"/sessions/{old.session_id}").text, path).fields
    assert post(path, retry).status_code == 303
    assert app.extensions["research_jobs"].wait_idle(10)
    assert calls == [config.run_settings, config.run_settings]
    assert store.list_jobs()[0].state == "completed"
    app.extensions["research_jobs"].shutdown()
    restarted, reopened, get, _ = hosted_room(config, key, factory)
    assert "gpt-6-luna" in get(email=config.admin_email).text
    assert reopened.get_hosted_preferences()["research_reasoning"] == "high"
    assert reopened.load(old.session_id).state.turns[0].answer == "Eight remain."
    assert restarted.extensions["research_jobs"].wait_idle(10)
