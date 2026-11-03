"""The real production process starts and rejects unauthenticated origin access."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from threading import Thread
from time import monotonic, sleep

import jwt
import pytest
import requests
import test_hosted_identity as identity
import waitress
from test_hosted_identity import environment, token, validator
from test_reading_room import Form
from test_research_loop import answer, decision
from test_run_settings_integration import response

from scryraven.hosted import HostedConfig
from scryraven.model import OpenAIModel
from scryraven.session_store import SQLiteSessionStore

_ROOT = Path(__file__).resolve().parents[1]
config = identity.config
key = identity.key


def child_environment(folder, port):
    # Never copy the developer's credential-bearing environment into this proof.
    env = {name: os.environ[name] for name in ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP")
           if name in os.environ}
    env.update(environment(folder))
    env.update({"PORT": str(port), "SCRYRAVEN_BIND_HOST": "127.0.0.1",
                "OPENAI_API_KEY": "synthetic-offline-placeholder",  # pragma: allowlist secret
                "PYTHONPATH": os.pathsep.join([str(_ROOT), str(Path(jwt.__file__).resolve().parents[1]),
                                               str(Path(waitress.__file__).resolve().parents[1])]),
                "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"})
    return env


def available_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def start(folder):
    port = available_port()
    process = subprocess.Popen([sys.executable, "-m", "scryraven.wsgi"], cwd=_ROOT,
                               env=child_environment(folder, port),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    client = requests.Session()
    client.trust_env = False
    url = f"http://127.0.0.1:{port}"
    deadline = monotonic() + 15
    while monotonic() < deadline:
        if process.poll() is not None:
            out, err = process.communicate()
            pytest.fail(f"Hosted startup failed: {out} {err}")
        try:
            response = client.get(url + "/healthz", headers={"Host": "healthcheck.railway.app"}, timeout=1)
            if response.status_code == 200:
                return process, client, url
        except requests.ConnectionError:
            pass
        sleep(0.05)
    process.terminate()
    process.communicate(timeout=10)
    pytest.fail("Production server did not become healthy")


def stop(process, client):
    client.close()
    process.terminate()
    process.communicate(timeout=10)


def test_actual_waitress_entrypoint_origin_auth_and_restart(tmp_path):
    env = child_environment(tmp_path, 8080)
    config = HostedConfig.from_env(env)
    store = SQLiteSessionStore(config.database)
    queued = store.accept_job("Synthetic restart question", idempotency_key="synthetic-startup",
                              owner_id="alice@example.test", submission_quota=20,
                              run_settings=config.run_settings)
    for _ in range(2):
        process, client, url = start(tmp_path)
        try:
            for path in ["/", f"/sessions/{queued.session_id}", "/jobs", "/admin"]:
                headers = {"Host": config.hostname,
                           "Cf-Access-Authenticated-User-Email": "owner@example.test",
                           "X-Forwarded-User": "owner@example.test", "X-Forwarded-Proto": "https"}
                response = client.get(url + path, headers=headers, timeout=2)
                assert response.status_code == 401
                assert "Synthetic restart question" not in response.text
            headers = {"Host": config.hostname, "Cf-Access-Jwt-Assertion": "bogus"}
            assert client.get(url + "/", headers=headers, timeout=2).status_code == 401
            assert client.get(url + "/", headers={"Host": "healthcheck.railway.app"}, timeout=2).status_code == 400
            assert client.get(url + "/", headers={"Host": "untrusted-origin.example.test"}, timeout=2).status_code == 400
            health = client.get(url + "/healthz", headers={"Host": config.hostname}, timeout=2)
            assert health.status_code == 200
            assert "session" not in health.text.lower() and "alice" not in health.text.lower()
        finally:
            stop(process, client)
        assert store.get_job(queued.job_id).state == "interrupted"
        assert store.load(queued.session_id).metadata.owner_id == "alice@example.test"


def test_production_entrypoint_missing_security_configuration_fails_without_values(tmp_path):
    env = child_environment(tmp_path, available_port())
    env["CF_ACCESS_ISSUER"] = "synthetic-sensitive-invalid-configuration"
    result = subprocess.run([sys.executable, "-m", "scryraven.wsgi"], cwd=_ROOT,
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert "could not start" in result.stderr
    assert env["CF_ACCESS_ISSUER"] not in result.stdout + result.stderr
    assert not (tmp_path / "sessions.sqlite3").exists()


def test_production_factory_signed_identity_and_ordinary_turn_over_waitress(config, key, monkeypatch):
    from waitress import server as waitress_server
    from waitress import wasyncore

    from scryraven.wsgi import create_application

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-offline-api-key")
    outputs = iter([decision("return"), answer("Eight apples remain.", support_basis="user_premises")])
    calls = []

    def post(url, **kwargs):
        calls.append((url, deepcopy(kwargs["json"])))
        return response(kwargs["json"], next(outputs))

    def forbidden(*_args, **_kwargs):
        pytest.fail("Synthetic premise turn contacted an acquisition service")

    path = None
    for opening in range(2):
        app = create_application(
            config=config, identity_validator=validator(config, key),
            run_model_factory=lambda settings: OpenAIModel(settings.model_config(), backend="api", post=post),
            session_options={"search": forbidden, "fetch": forbidden, "lexical_search": forbidden},
        )
        manager = app.extensions["research_jobs"]
        diagnostics = app.extensions["hosted_diagnostics"]
        assert diagnostics._maintenance_thread.is_alive()
        server = waitress_server.create_server(app, host="127.0.0.1", port=0, threads=4,
            url_scheme="https", clear_untrusted_proxy_headers=True, expose_tracebacks=False,
            asyncore_loop_timeout=0.1, map={})
        thread = Thread(target=server.run, daemon=True)
        thread.start()
        client = requests.Session()
        client.trust_env = False
        url = "http://127.0.0.1:" + str(server.effective_port)
        headers = {"Host": config.hostname, "Cf-Access-Jwt-Assertion": token(config, key)}
        try:
            assert client.get(url + "/healthz", headers={"Host": "healthcheck.railway.app"}, timeout=3).status_code == 200
            assert client.get(url + "/", headers={"Host": config.hostname,
                "Cf-Access-Authenticated-User-Email": "owner@example.test"}, timeout=3).status_code == 401
            page = client.get(url + (path or "/"), headers=headers, timeout=3)
            assert page.status_code == 200
            if opening == 0:
                fields = Form(page.text, "/ask").fields
                fields["question"] = "Given 12 apples with four removed, how many remain?"
                accepted = client.post(url + "/ask", headers={**headers, "Origin": config.origin},
                                       data=fields, timeout=3, allow_redirects=False)
                assert accepted.status_code == 303
                assert manager.wait_idle(10)
                path = accepted.headers["Location"]
                page = client.get(url + path, headers=headers, timeout=3)
            assert "Eight apples remain." in page.text
            job, = manager.list()
            assert job.state == "completed" and job.run_settings == config.run_settings
            saved = SQLiteSessionStore(config.database).load(job.session_id)
            assert saved.metadata.owner_id == "alice@example.test"
            assert saved.state.turns[0].answer == "Eight apples remain."
            assert len(calls) == 2
            assert all(item[0] == "https://api.openai.com/v1/responses" for item in calls)
            assert [item[1]["model"] for item in calls] == [config.run_settings.research_model,
                                                            config.run_settings.answer_model]
        finally:
            client.close()
            manager.shutdown()
            diagnostics.close()
            assert not diagnostics._maintenance_thread.is_alive()
            assert manager.wait_idle(10)
            server.task_dispatcher.shutdown()
            server.close()
            wasyncore.close_all(map=server._map)
            thread.join(5)
            assert not thread.is_alive()
