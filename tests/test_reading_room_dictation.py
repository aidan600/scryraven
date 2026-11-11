"""The ordinary dictation endpoint with synthetic audio and no external calls."""

import json
import sqlite3
import wave
from contextlib import closing
from io import BytesIO

import pytest
import requests
import test_hosted_identity as identity
from flask import template_rendered
from reading_room_samples import no_io
from test_persistent_sessions import tmp_path as external_tmp_path

from scryraven import dictation
from scryraven.reading_room import create_app
from scryraven.run_settings import RunSettings
from scryraven.session_store import SQLiteSessionStore

tmp_path = external_tmp_path


def recording(frames=4_000):
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setparams((1, 2, 16_000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\x07\x01" * frames)
    return output.getvalue()


def page_context(client, path="/", **options):
    contexts = []

    def collect(sender, template, context, **extras):
        contexts.append(context)

    with template_rendered.connected_to(collect, client.application):
        assert client.get(path, **options).status_code == 200
    return contexts[0]


def post_audio(client, token, path="/transcribe", *, audio=None, headers=None, **options):
    return client.post(path, data=recording() if audio is None else audio,
                       content_type="audio/wav", headers={"X-Form-Token": token, **(headers or {})}, **options)


@pytest.fixture
def local_room(tmp_path, monkeypatch):
    monkeypatch.setattr(dictation, "available", lambda: True)
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    settings = RunSettings("chatgpt_plan", "gpt-6.1-terra", "medium", "gpt-6.1-sol", "medium", None, 40)
    store.set_run_settings(settings)
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    try:
        yield app.test_client(), store
    finally:
        app.extensions["research_jobs"].shutdown()


def test_dictation_requires_local_billing_without_switching_research_or_saving_audio(local_room, monkeypatch):
    client, store = local_room
    submitted = []

    def transcribe(audio):
        submitted.append(audio)
        return "A synthetic transcript."

    monkeypatch.setattr(dictation, "transcribe", transcribe)
    saved = store.create("An existing draft conversation")
    session_path = "/sessions/" + saved.metadata.session_id
    context = page_context(client, session_path)
    assert context["dictation_configured"] and not context["dictation_enabled"]
    token = context["dictation_token"]
    assert post_audio(client, token, session_path + "/transcribe").status_code == 403
    assert submitted == []

    store.set_billing_authorization("openai", True)
    assert page_context(client, session_path)["dictation_enabled"]
    files = set(store.path.parent.iterdir())
    database = store.path.read_bytes()
    assert post_audio(client, token, session_path + "/transcribe").json == {"text": "A synthetic transcript."}
    assert submitted == [recording()]
    assert set(store.path.parent.iterdir()) == files
    assert store.path.read_bytes() == database
    assert store.get_run_settings().backend == "chatgpt_plan"
    assert client.application.extensions["research_jobs"].list() == ()

    store.set_billing_authorization("openai", False)
    assert post_audio(client, token, session_path + "/transcribe").status_code == 403
    assert len(submitted) == 1


def test_dictation_bounds_actual_wav_and_keeps_errors_local(local_room, monkeypatch):
    client, store = local_room
    store.set_billing_authorization("openai", True)
    called = []

    def transcribe(audio):
        called.append(len(audio))
        return ""

    monkeypatch.setattr(dictation, "transcribe", transcribe)
    token = page_context(client)["dictation_token"]
    assert post_audio(client, "").status_code == 403
    assert post_audio(client, token, headers={"Origin": "https://foreign.example"}).status_code == 403
    assert post_audio(client, token, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.post("/transcribe", data=recording(), content_type="audio/mp4").status_code == 415
    assert post_audio(client, token, audio=recording(3_999)).status_code == 400
    assert post_audio(client, token, audio=b"FAKE" + recording()[4:]).status_code == 400
    maximum = recording(60 * 16_000)
    assert post_audio(client, token, audio=maximum + b"\x00").status_code == 413
    stream = {"CONTENT_LENGTH": "", "wsgi.input_terminated": True}
    assert post_audio(client, token, audio=maximum + b"\x00", environ_overrides=stream).status_code == 413
    assert called == []
    assert post_audio(client, token, audio=maximum, environ_overrides=stream).status_code == 422
    assert called == [len(maximum)]
    assert store.list_sessions() == ()


def test_hosted_dictation_checks_identity_owner_and_does_not_charge_question_quota(tmp_path, monkeypatch):
    config = identity.config.__wrapped__(tmp_path)
    key = identity.key.__wrapped__()
    store = SQLiteSessionStore(config.database)
    alice = store.create("Alice's room", owner_id="alice@example.test").metadata.session_id
    bob = store.create("Bob's room", owner_id="bob@example.test").metadata.session_id
    app = create_app(store=store, hosted=config, identity_validator=identity.validator(config, key),
                     session_options={"model": no_io, "search": no_io, "fetch": no_io})
    calls = []

    def transcribe(audio):
        calls.append(len(audio))
        return "Spoken text."

    monkeypatch.setattr(dictation, "available", lambda: True)
    monkeypatch.setattr(dictation, "transcribe", transcribe)
    try:
        client = app.test_client()
        alice_path, bob_path = f"/sessions/{alice}", f"/sessions/{bob}"

        def auth(email):
            return {"Cf-Access-Jwt-Assertion": identity.token(config, key, email=email)}

        alice_headers, bob_headers = auth("alice@example.test"), auth("bob@example.test")
        alice_token = page_context(client, alice_path, headers=alice_headers,
                                   base_url=config.origin)["dictation_token"]
        assert post_audio(client, alice_token, alice_path + "/transcribe", base_url=config.origin).status_code == 401
        assert post_audio(client, alice_token, alice_path + "/transcribe", headers=bob_headers,
                          base_url=config.origin).status_code == 404
        assert post_audio(client, alice_token, alice_path + "/transcribe", headers=auth(config.admin_email),
                          base_url=config.origin).status_code == 404
        assert post_audio(client, alice_token, bob_path + "/transcribe", headers=bob_headers,
                          base_url=config.origin).status_code == 403
        new_token = page_context(client, headers=alice_headers, base_url=config.origin)["dictation_token"]
        assert post_audio(client, new_token, headers=bob_headers, base_url=config.origin).status_code == 403
        assert calls == []
        assert post_audio(client, alice_token, alice_path + "/transcribe", headers=alice_headers,
                          base_url=config.origin).json == {"text": "Spoken text."}
        assert calls == [len(recording())]
        assert app.extensions["research_jobs"].list() == ()
        with closing(sqlite3.connect(store.path)) as connection:
            assert connection.execute("SELECT count(*) FROM user_submissions").fetchone() == (0,)
    finally:
        app.extensions["research_jobs"].shutdown()
        app.extensions["hosted_diagnostics"].close()


def test_dictation_rate_and_concurrency_bounds_release_failed_slots(monkeypatch):
    now = 0
    monkeypatch.setattr(dictation, "monotonic", lambda: now)
    monkeypatch.setattr(dictation, "_MAX_ATTEMPTS", 1)
    slots = dictation.TranscriptionSlots()
    with pytest.raises(RuntimeError, match="synthetic failure"), slots.reserve("alice"):
        with pytest.raises(dictation.TranscriptionError, match="busy"):
            with slots.reserve("alice"):
                pytest.fail("a second request ran for the same owner")
        with slots.reserve("bob"):
            with pytest.raises(dictation.TranscriptionError, match="busy"):
                with slots.reserve("carol"):
                    pytest.fail("a third provider request ran concurrently")
        raise RuntimeError("synthetic failure")
    with pytest.raises(dictation.TranscriptionError, match="reached the dictation limit"), slots.reserve("alice"):
        pytest.fail("a second attempt ran within the window")
    now += 24 * 60 * 60
    with slots.reserve("alice"):
        assert slots.active == {"alice"}


def test_openai_transcription_multipart_uses_fixed_model_and_never_retries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-fixture-only")  # pragma: allowlist secret
    audio = recording()
    calls = []
    replies = ["  Editable speech.  ", requests.Timeout("private timeout detail")]

    class Response:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def iter_content(self, chunk_size):
            yield json.dumps({"text": replies.pop(0)}).encode()

    def post(session, url, **kwargs):
        calls.append(url)
        assert not session.trust_env
        assert kwargs["headers"] == {"Authorization": "Bearer synthetic-fixture-only"}
        assert kwargs["data"] == {"model": "gpt-transcribe"}
        assert kwargs["files"] == {"file": ("dictation.wav", audio, "audio/wav")}
        assert kwargs["stream"] and not kwargs["allow_redirects"]
        assert kwargs["timeout"].total == 35
        if isinstance(replies[0], Exception):
            raise replies.pop(0)
        return Response()

    monkeypatch.setattr(requests.Session, "post", post)
    assert dictation.transcribe(audio) == "Editable speech."
    with pytest.raises(dictation.TranscriptionError, match="^Dictation timed out") as result:
        dictation.transcribe(audio)
    assert result.value.status == 504
    assert calls == ["https://api.openai.com/v1/audio/transcriptions"] * 2
