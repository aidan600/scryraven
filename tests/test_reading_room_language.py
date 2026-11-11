"""Conversation source-language settings keep identity and accepted-turn custody."""

from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest
import test_hosted_identity as identity
from reading_room_samples import no_io, prepared_session
from test_persistent_sessions import tmp_path as external_tmp_path
from test_reading_room import Form
from test_research_jobs import result
from werkzeug.datastructures import MultiDict

from scryraven.reading_room import create_app
from scryraven.session_store import SQLiteSessionStore, _decode

tmp_path = external_tmp_path
config = identity.config
key = identity.key


@pytest.fixture
def hosted_room(config, key):
    store = SQLiteSessionStore(config.database)
    alice = store.create("Alice's conversation", owner_id="alice@example.test")
    historical = (Path(__file__).parent / "fixtures/historical_session_v1.json").read_text(encoding="utf-8")
    store.commit(alice.metadata.session_id, 0, _decode(historical, 1))
    bob = store.create("Bob's conversation", owner_id="bob@example.test")
    app = create_app(store=store, hosted=config, identity_validator=identity.validator(config, key),
                     session_options={"model": no_io, "search": no_io, "fetch": no_io})
    client = app.test_client()

    def get(path="/", email="alice@example.test"):
        return client.get(path, base_url=config.origin,
                          headers={"Cf-Access-Jwt-Assertion": identity.token(config, key, email=email)})

    def post(path, fields, email="alice@example.test", **headers):
        return client.post(path, data=fields, base_url=config.origin, headers={
            "Cf-Access-Jwt-Assertion": identity.token(config, key, email=email),
            "Origin": config.origin, **headers,
        })

    try:
        yield app, store, "/sessions/" + alice.metadata.session_id, "/sessions/" + bob.metadata.session_id, get, post
    finally:
        app.extensions["research_jobs"].shutdown()
        app.extensions["hosted_diagnostics"].close()


def test_source_language_settings_require_owner_action_token_and_origin(hosted_room, config):
    _, store, alice_path, bob_path, get, post = hosted_room
    action = alice_path + "/settings/source-language"
    page = get(alice_path)
    fields = Form(page.text, action).fields
    fields["citation_language"] = "pl"
    before = store.load(alice_path.rsplit("/", 1)[1])
    assert post(action, {**fields, "form_token": ""}).status_code == 403
    assert post(action, {**fields, "form_token": Form(page.text, alice_path + "/ask").fields["form_token"]}).status_code == 403
    assert post(action, fields, Origin="https://foreign.example").status_code == 403
    assert post(action, fields, **{"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert post(action, fields, email="bob@example.test").status_code == 404
    assert post(action, fields, email=config.admin_email).status_code == 404
    assert not Form(get(alice_path, email=config.admin_email).text, action).fields
    assert post(bob_path + "/settings/source-language", fields, email="bob@example.test").status_code == 403
    same_owner = store.create("Alice's other conversation", owner_id="alice@example.test")
    assert post(f"/sessions/{same_owner.metadata.session_id}/settings/source-language", fields).status_code == 403
    assert store.load(before.metadata.session_id) == before

    response = post(action, fields, Accept="application/json")
    assert response.status_code == 200 and response.json["form_token"] != fields["form_token"]
    assert post(action, fields).status_code == 403
    after = store.load(before.metadata.session_id)
    assert after.metadata.citation_language == "pl" and after.metadata.revision == before.metadata.revision
    assert after.state == before.state and after.documents == before.documents
    assert store.load(bob_path.rsplit("/", 1)[1]).metadata.citation_language == "en"
    assert store.get_hosted_preferences() is None


@pytest.mark.parametrize("invalid", [
    {}, {"citation_language": ""}, {"citation_language": "invented"},
    {"citation_language": ["en", "fr"]}, {"form_token": ["copied", "duplicate"]},
    {"backend": "openai"}, {"owner_id": "bob@example.test"},
])
def test_invalid_or_duplicate_source_settings_do_not_mutate_preference(hosted_room, invalid):
    _, store, alice_path, _, get, post = hosted_room
    action = alice_path + "/settings/source-language"
    fields = Form(get(alice_path).text, action).fields
    fields.update(invalid)
    if not invalid:
        fields.pop("citation_language")
    body = MultiDict()
    for name, value in fields.items():
        body.setlist(name, value if isinstance(value, list) else [value])
    before = store.load(alice_path.rsplit("/", 1)[1])
    assert post(action, body).status_code == 400
    assert store.load(before.metadata.session_id) == before


def test_administrator_global_settings_leave_each_conversation_language_independent(hosted_room, config):
    _, store, alice_path, bob_path, get, post = hosted_room
    alice_id, bob_id = alice_path.rsplit("/", 1)[1], bob_path.rsplit("/", 1)[1]
    store.set_citation_language(alice_id, "fr", owner_id="alice@example.test")
    store.set_citation_language(bob_id, "ja", owner_id="bob@example.test")
    own = store.create("Administrator's conversation", owner_id=config.admin_email)
    own_path = "/sessions/" + own.metadata.session_id
    store.set_citation_language(own.metadata.session_id, "pl", owner_id=config.admin_email)
    fields = Form(get(own_path, email=config.admin_email).text, "/settings/hosted").fields
    fields.update(research_model="gpt-6-luna", research_reasoning="high", api_processing="fast")
    assert post("/settings/hosted", fields, email=config.admin_email).status_code == 303
    assert store.get_hosted_preferences()["research_model"] == "gpt-6-luna"
    assert [store.load(session_id).metadata.citation_language for session_id in
            (alice_id, bob_id, own.metadata.session_id)] == ["fr", "ja", "pl"]
    fields = Form(get(email=config.admin_email).text, "/settings/hosted").fields
    assert post("/settings/hosted", {**fields, "citation_language": "en"}, email=config.admin_email).status_code == 400


def test_settings_can_change_during_and_after_answer_without_rewriting_accepted_snapshot(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = prepared_session(store)
    path = "/sessions/" + session.session_id
    initial = store.load(session.session_id)
    started, release = Event(), Event()
    languages = []

    def engine(question, *, context, **options):
        languages.append(context["citation_description_language"])
        started.set()
        assert release.wait(10)
        return replace(result(question), evidence=options["retained_acquisitions"])

    app = create_app(store=store, session_options={"engine": engine, "model": no_io, "search": no_io, "fetch": no_io})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    language_action, ask_action = path + "/settings/source-language", path + "/ask"
    try:
        page = client.get(path)
        settings = Form(page.text, language_action).fields
        assert client.post(language_action, data={**settings, "citation_language": "fr"}).status_code == 303
        assert store.load(session.session_id).metadata.revision == initial.metadata.revision
        page = client.get(path)
        stale_settings = Form(page.text, language_action).fields
        ask_fields = {**Form(page.text, ask_action).fields, "question": "A follow-up with accepted French explanations."}
        assert "citation_language" not in ask_fields
        first = client.post(ask_action, data=ask_fields)
        assert first.status_code == 303 and started.wait(5)
        job = manager.list(session.session_id)[0]
        assert job.citation_language == "fr"
        changed = client.post(language_action, data={**stale_settings, "citation_language": "ja"},
                              headers={"Accept": "application/json"})
        assert changed.status_code == 200
        release.set()
        assert manager.wait_idle(10)
        completed = manager.get(job.job_id)
        assert completed.state == "completed" and completed.citation_language == "fr" and languages == ["fr"]
        assert store.load(session.session_id).metadata.citation_language == "ja"
        assert client.post(language_action, data={"form_token": changed.json["form_token"],
                                                "citation_language": "pl"}).status_code == 303
        assert store.load(session.session_id).metadata.revision == initial.metadata.revision + 1
        assert client.post(ask_action, data=ask_fields).location == first.location
        assert len(manager.list(session.session_id)) == 1
        next_fields = {**Form(client.get(path).text, ask_action).fields, "question": "The next accepted explanation language."}
        assert client.post(ask_action, data=next_fields).status_code == 303 and manager.wait_idle(10)
        assert languages == ["fr", "pl"]
        final = store.load(session.session_id)
        assert final.state.turns[:len(initial.state.turns)] == initial.state.turns
        assert final.documents == initial.documents and final.images == initial.images
    finally:
        release.set()
        manager.wait_idle(10)
        manager.shutdown()


def test_retry_uses_accepted_language_and_preserves_newer_conversation_preference(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = store.create("A conversation with a failed question")
    path = "/sessions/" + session.metadata.session_id
    languages = []

    def engine(question, *, context, **options):
        languages.append(context["citation_description_language"])
        if len(languages) == 1:
            raise ValueError("synthetic first-attempt failure")
        return result(question)

    app = create_app(store=store, session_options={"engine": engine, "model": no_io, "search": no_io, "fetch": no_io})
    manager = app.extensions["research_jobs"]
    client = app.test_client()
    action = path + "/ask"
    try:
        fields = {**Form(client.get(path).text, action).fields, "question": "Keep the accepted language on retry."}
        assert client.post(action, data=fields).status_code == 303 and manager.wait_idle(10)
        failed = manager.list(session.metadata.session_id)[0]
        assert failed.state == "failed" and failed.citation_language == "en"

        language_action = path + "/settings/source-language"
        settings = Form(client.get(path).text, language_action).fields
        assert client.post(language_action, data={**settings, "citation_language": "ja"}).status_code == 303
        retry_action = path + f"/jobs/{failed.job_id}/retry"
        retry_fields = Form(client.get(path).text, retry_action).fields
        assert client.post(retry_action, data=retry_fields).status_code == 303 and manager.wait_idle(10)
        retried = manager.list(session.metadata.session_id)[0]
        assert retried.state == "completed" and retried.citation_language == "en"
        assert store.load(session.metadata.session_id).metadata.citation_language == "ja"

        next_fields = {**Form(client.get(path).text, action).fields, "question": "Use the saved preference on a new question."}
        assert client.post(action, data=next_fields).status_code == 303 and manager.wait_idle(10)
        assert manager.list(session.metadata.session_id)[0].citation_language == "ja"
        assert languages == ["en", "en", "ja"]
    finally:
        manager.wait_idle(10)
        manager.shutdown()
