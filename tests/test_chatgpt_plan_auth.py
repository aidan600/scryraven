"""Ported custody and SSE checks; synthetic loopback services and temporary vaults only."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa

from scryraven.chatgpt_plan import storage
from scryraven.chatgpt_plan.__main__ import main
from scryraven.chatgpt_plan.auth import Auth, Deadline
from scryraven.chatgpt_plan.http import (
    AUTHORIZE,
    ISSUER,
    JWKS,
    MODELS,
    RESOURCE,
    RESPONSES,
    SCOPES,
    TOKEN,
    PlanError,
    PublicHTTP,
)
from scryraven.chatgpt_plan.storage import Vault
from scryraven.chatgpt_plan.streaming import events

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI and file-lock integration")


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    original = socket.socket.connect

    def connect(sock, address):
        if address[0] not in {"127.0.0.1", "::1"}:
            raise AssertionError("Offline test attempted a non-loopback connection")
        return original(sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(storage, "default_directory", lambda: pytest.fail("Real operator vault accessed"))
    # Never use the real user's ordinary model configuration in this test module.
    from scryraven import model
    monkeypatch.setattr(model, "user_model_config_path", lambda: Path("does-not-exist-test-model-config.json"))


def response_body(text=None):
    return {
        "status": "completed", "output": [{"type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": text if text is not None else "{}"}]}],
        "usage": {"input_tokens": 100, "output_tokens": 40, "input_tokens_details": {"cached_tokens": 20},
                  "output_tokens_details": {"reasoning_tokens": 10}}, "service_tier": "default",
    }


def sse(body=None):
    return (": heartbeat\r\n\r\nevent: response.completed\r\ndata: "
            + json.dumps({"type": "response.completed", "response": body or response_body()})
            + "\r\n\r\n").encode()


@pytest.fixture
def service(tmp_path):
    state = SimpleNamespace(
        private=rsa.generate_private_key(public_exponent=65537, key_size=2048),
        requests=[], authorizations=[], browser_threads=[], codes={}, scope=SCOPES,
        claim_updates={}, signing_key=None, token_updates={}, deny=False, code_error_once=False,
        refresh_error=None, api_error=None, redirect_status=None, hang_stream=0, catalog={"models": [
            {"slug": "gpt-6-luna", "display_name": "Luna", "visibility": "list"},
            {"slug": "hidden", "display_name": "Hidden", "visibility": "hide"},
            {"slug": "gpt-6.1-sol", "display_name": "Sol", "visibility": "list"},
        ]}, streams=[], stream_type="text/event-stream", refreshes=0,
    )
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(state.private.public_key()))
    jwk.update(kid="fixture", alg="RS256", use="sig")
    state.jwks = {"keys": [jwk]}

    def tokens(nonce, client, *, refresh=False):
        now = int(time.time())
        claims = {"iss": ISSUER, "aud": client, "sub": "fixture-subject", "iat": now,
                  "exp": now + 3600, "nonce": nonce, "email": "fixture@example.invalid"}
        claims.update(state.claim_updates)
        encoded = jwt.encode(claims, state.signing_key or state.private, algorithm="RS256", headers={"kid": "fixture"})
        suffix = "rotated" if refresh else "initial"
        result = {"access_token": "fixture-access-PRIVATE-" + suffix, "refresh_token": "fixture-refresh-PRIVATE-" + suffix,
                  "id_token": encoded, "token_type": "Bearer", "expires_in": 3600, "scope": state.scope,
                  "earliest_refresh_at": now + 3500}
        result.update(state.token_updates)
        return result

    state.tokens = tokens

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, body, status=200, content_type="application/json"):
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            if content_type is not None:
                self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            uri = urlsplit(self.path)
            state.requests.append(("GET", uri.path, dict(self.headers), None))
            if uri.path == urlsplit(AUTHORIZE).path:
                query = {key: value[0] for key, value in parse_qs(uri.query).items()}
                state.authorizations.append(query)
                client = query["client_id"]
                if client == "dynamic_agent_client":
                    client = "oaiapp_fixture_" + str(len(state.authorizations))
                code = "fixture-code-" + str(len(state.codes))
                state.codes[code] = (query, client)
                returned = {"state": query["state"], "error": "access_denied"} if state.deny else {
                    "state": query["state"], "code": code, "client_id": client,
                    "scope": SCOPES,  # Intentionally not authoritative.
                }
                self.send_response(302)
                self.send_header("Location", query["redirect_uri"] + "?" + urlencode(returned))
                self.end_headers()
            elif uri.path == urlsplit(JWKS).path:
                self.send(state.jwks)
            elif uri.path == urlsplit(MODELS).path:
                self.send(state.catalog)
            else:
                self.send({}, 404)

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            uri = urlsplit(self.path)
            body = json.loads(raw) if uri.path == urlsplit(RESPONSES).path else {
                key: value[0] for key, value in parse_qs(raw.decode()).items()
            }
            state.requests.append(("POST", uri.path, dict(self.headers), body))
            if uri.path == urlsplit(TOKEN).path:
                if body["grant_type"] == "refresh_token":
                    state.refreshes += 1
                    if state.refresh_error:
                        return self.send(state.refresh_error[1], state.refresh_error[0])
                    return self.send(tokens(None, body["client_id"], refresh=True))
                query, client = state.codes[body["code"]]
                assert body["client_id"] == client
                assert body["redirect_uri"] == query["redirect_uri"]
                challenge = base64.urlsafe_b64encode(hashlib.sha256(body["code_verifier"].encode()).digest()).decode().rstrip("=")
                assert challenge == query["code_challenge"]
                if state.code_error_once:
                    state.code_error_once = False
                    return self.send({"error": "invalid_grant"}, 400)
                self.send(tokens(query["nonce"], client))
            elif uri.path == urlsplit(RESPONSES).path:
                if state.redirect_status:
                    self.send_response(state.redirect_status)
                    self.send_header("Location", f"http://127.0.0.1:{server.server_port}/fixture-access-PRIVATE-initial")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if state.hang_stream:
                    self.send_response(200)
                    if state.stream_type is not None:
                        self.send_header("Content-Type", state.stream_type)
                    self.end_headers()
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    time.sleep(state.hang_stream)
                    return
                if state.api_error:
                    return self.send(state.api_error[1], state.api_error[0])
                self.send(state.streams.pop(0) if state.streams else sse(), content_type=state.stream_type)
            else:
                self.send({}, 404)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
    thread.start()

    class LocalSession(requests.Session):
        def request(self, method, url, **kwargs):
            uri = urlsplit(url)
            assert uri.hostname in {"auth.openai.com", "api.openai.com"}
            local = f"http://127.0.0.1:{server.server_port}" + uri.path + ("?" + uri.query if uri.query else "")
            return super().request(method, local, **kwargs)

    http = PublicHTTP(LocalSession())
    auth = Auth(Vault(tmp_path / "vault"), http)

    def browser(url):
        def redirect():
            with LocalSession() as session:
                session.trust_env = False
                first = session.get(url, timeout=5, allow_redirects=False)
            with requests.Session() as session:
                session.trust_env = False
                result = session.get(first.headers["Location"], timeout=5)
                assert result.status_code == 200
                assert "fixture-code" not in result.text

        task = threading.Thread(target=redirect, daemon=True)
        state.browser_threads.append(task)
        task.start()
        return True

    state.auth, state.http, state.browser = auth, http, browser
    try:
        yield state
    finally:
        for task in state.browser_threads:
            task.join(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def signed(service, label="personal"):
    result = service.auth.sign_in(label, browser=service.browser, seconds=10)
    assert result["plan_enabled"]
    return service.auth


def expire(service):
    with service.auth.vault.locked():
        data = service.auth.vault.read()
        data["accounts"]["personal"]["expires_at"] = 0
        service.auth.vault.write(data)


def test_browser_dynamic_registration_pkce_callback_and_returning_account(service, capsys, caplog):
    adapter = signed(service)
    first = service.authorizations[0]
    assert first["client_id"] == "dynamic_agent_client"
    assert first["agent_name_hint"] == "ScryRaven"
    assert first["ext_agent_host_id"].startswith("urn:uuid:")
    assert first["resource"] == RESOURCE and first["scope"] == SCOPES
    assert first["code_challenge_method"] == "S256"
    assert first["redirect_uri"].startswith("http://127.0.0.1:")
    assert first["redirect_uri"].endswith("/auth/callback")
    assert main(["models", "--account", "personal"], auth=adapter)["models"] == [
        {"slug": "gpt-6-luna", "display_name": "Luna"}, {"slug": "gpt-6.1-sol", "display_name": "Sol"},
    ]
    signed(service)
    second = service.authorizations[1]
    assert second["client_id"] == "oaiapp_fixture_1" and "agent_name_hint" not in second
    assert second["ext_agent_host_id"] == first["ext_agent_host_id"]
    assert second["id_token_hint"] and second["login_hint"] == "fixture@example.invalid"
    assert first["state"] != second["state"] and first["nonce"] != second["nonce"]
    assert first["code_challenge"] != second["code_challenge"]
    assert "fixture-access" not in capsys.readouterr().out + caplog.text


def test_denied_browser_permission_makes_no_exchange(service):
    service.deny = True
    with pytest.raises(PlanError, match="model_access_denied"):
        service.auth.sign_in("personal", browser=service.browser, seconds=5)
    assert not any(method == "POST" for method, *_ in service.requests)
    assert service.auth.accounts() == []


def test_identity_without_direct_scope_is_retained_but_cannot_infer(service):
    service.scope = "openid profile email offline_access"
    assert service.auth.sign_in("personal", browser=service.browser, seconds=5)["plan_enabled"] is False
    adapter = service.auth
    with pytest.raises(PlanError, match="model_access_denied"):
        adapter.access("personal")
    assert not any(path in {urlsplit(MODELS).path, urlsplit(RESPONSES).path} for _, path, *_ in service.requests)
    assert service.auth.accounts()[0]["plan_enabled"] is False


@pytest.mark.parametrize("claims", [
    {"iss": "https://attacker.invalid"}, {"aud": "other-client"}, {"exp": 1}, {"nonce": "wrong"},
    {"sub": ""}, {"iat": int(time.time()) + 10000},
    {"aud": ["oaiapp_fixture_1", "other"], "azp": "other"},
])
def test_id_token_validation(service, claims):
    service.claim_updates = claims
    with pytest.raises(PlanError, match="model_authentication_failed"):
        service.auth.sign_in("personal", browser=service.browser, seconds=5)
    assert service.auth.accounts() == []


def test_bad_signature_unknown_key_and_unsafe_algorithm(service):
    service.signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(PlanError, match="model_authentication_failed"):
        service.auth.sign_in("personal", browser=service.browser, seconds=5)
    service.signing_key = None
    service.jwks["keys"][0]["kid"] = "different"
    with pytest.raises(PlanError, match="model_authentication_failed"):
        service.auth.sign_in("personal", browser=service.browser, seconds=5)
    with pytest.raises(PlanError, match="model_authentication_failed"):
        service.auth.verify(jwt.encode({"sub": "attacker"}, "test-fixture-" * 4, algorithm="HS256"),
                            "oaiapp_fixture_1", "nonce", Deadline(5))


def test_callback_state_client_code_expiry_and_one_time_consumption(service):
    attempt = service.auth.prepare("personal", "http://127.0.0.1:56789/auth/callback")
    for query in ({"state": "wrong", "error": "access_denied"}, {"error": "access_denied"}):
        with pytest.raises(PlanError, match="model_authentication_failed"):
            service.auth.complete(attempt, query)
    assert not attempt.consumed
    with pytest.raises(PlanError, match="model_authentication_failed"):
        service.auth.complete(attempt, {"state": attempt.state, "code": "code"})
    assert attempt.consumed
    with pytest.raises(PlanError, match="model_authentication_failed"):
        service.auth.complete(attempt, {"state": attempt.state, "code": "code", "client_id": "oaiapp_valid"})
    attempt = service.auth.prepare("personal", "http://127.0.0.1:56789/auth/callback")
    attempt.expires_at = 0
    with pytest.raises(PlanError, match="model_authentication_failed"):
        service.auth.complete(attempt, {"state": attempt.state})
    assert service.requests == []
    assert "nonce" not in repr(attempt) and "verifier" not in repr(attempt)


def test_returning_callback_client_and_identity_cannot_replace_registration(service):
    signed(service)
    before = service.auth.vault.path.read_bytes()
    attempt = service.auth.prepare("personal", "http://127.0.0.1:56789/auth/callback")
    with pytest.raises(PlanError, match="model_authentication_failed"):
        service.auth.complete(attempt, {"state": attempt.state, "code": "fixture", "client_id": "oaiapp_other"})
    service.claim_updates = {"sub": "another-person"}
    with pytest.raises(PlanError, match="model_authentication_failed"):
        service.auth.sign_in("personal", browser=service.browser, seconds=5)
    assert service.auth.vault.path.read_bytes() == before


def test_registrations_with_same_email_are_separate_and_host_is_stable(service):
    signed(service, "personal")
    signed(service, "workspace")
    assert len(service.auth.accounts()) == 2
    with service.auth.vault.locked():
        data = service.auth.vault.read()
    rows = list(data["accounts"].values())
    assert rows[0]["email"] == rows[1]["email"] and rows[0]["subject"] == rows[1]["subject"]
    assert rows[0]["client_id"] != rows[1]["client_id"]
    assert service.authorizations[0]["ext_agent_host_id"] == service.authorizations[1]["ext_agent_host_id"]


def test_invalid_grant_restarts_once_with_issued_client_and_fresh_pkce(service):
    service.code_error_once = True
    signed(service)
    assert len(service.authorizations) == 2
    first, second = service.authorizations
    assert second["client_id"] == "oaiapp_fixture_1"
    assert second["state"] != first["state"] and second["code_challenge"] != first["code_challenge"]
    assert "agent_name_hint" not in second


@pytest.mark.parametrize("changes", [
    {"token_type": "Basic"}, {"token_type": {}}, {"scope": None}, {"access_token": ""},
    {"refresh_token": ""}, {"id_token": None}, {"expires_in": -1}, {"expires_in": True},
])
def test_malformed_token_responses_never_install_credentials(service, changes):
    service.token_updates = changes
    with pytest.raises(PlanError):
        service.auth.sign_in("personal", browser=service.browser, seconds=5)
    assert service.auth.accounts() == []


def test_refresh_without_new_id_or_scope_retains_identity_and_permissions(service):
    signed(service)
    expire(service)
    service.token_updates = {"id_token": None}
    row = service.auth.access("personal")
    assert row["subject"] == "fixture-subject" and row["id_token"]


def test_refresh_serialized_between_independent_instances(service):
    signed(service)
    expire(service)
    other = Auth(Vault(service.auth.vault.directory), service.http)
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(lambda auth: auth.access("personal"), [service.auth, other]))
    assert service.refreshes == 1 and rows[0]["refresh_token"] == rows[1]["refresh_token"]


@pytest.mark.parametrize("code", ["invalid_grant", "refresh_token_expired", "refresh_token_reused"])
def test_terminal_refresh_failure_clears_tokens_retains_registration(service, code):
    signed(service)
    expire(service)
    service.refresh_error = (400, {"error": code, "error_description": "fixture-refresh-PRIVATE-initial"})
    with pytest.raises(PlanError):
        service.auth.access("personal")
    with service.auth.vault.locked():
        data = service.auth.vault.read()
    row = data["accounts"]["personal"]
    assert row["client_id"] == "oaiapp_fixture_1" and row["subject"] == "fixture-subject"
    assert all(row[key] is None for key in ("access_token", "refresh_token", "id_token"))
    assert service.auth.accounts()[0]["sign_in_required"]
    with pytest.raises(PlanError):
        service.auth.access("personal")
    assert service.refreshes == 1


def test_temporary_refresh_failure_preserves_exact_vault_without_retry(service):
    signed(service)
    expire(service)
    before = service.auth.vault.path.read_bytes()
    service.refresh_error = (503, {"detail": "fixture-refresh-PRIVATE-initial"})
    with pytest.raises(PlanError):
        service.auth.access("personal")
    assert before == service.auth.vault.path.read_bytes() and service.refreshes == 1


def test_refresh_permission_loss_and_identity_mismatch_stop_inference(service):
    adapter = signed(service)
    expire(service)
    service.claim_updates = {"sub": "wrong-subject"}
    before = service.auth.vault.path.read_bytes()
    with pytest.raises(PlanError):
        adapter.access("personal")
    assert service.auth.vault.path.read_bytes() == before
    service.claim_updates = {}
    service.scope = "openid profile email offline_access"
    with pytest.raises(PlanError, match="model_access_denied"):
        adapter.access("personal")
    assert not service.auth.accounts()[0]["plan_enabled"]
    assert not any(path == urlsplit(RESPONSES).path for _, path, *_ in service.requests)


def test_windows_vault_contains_no_plaintext_and_atomic_failure_preserves_old(service, monkeypatch):
    signed(service)
    vault = service.auth.vault
    before = vault.path.read_bytes()
    assert b"fixture-access" not in before and b"fixture-refresh" not in before and b"fixture@example" not in before
    with vault.locked():
        data = vault.read()
        monkeypatch.setattr(storage.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("fixture-private")))
        with pytest.raises(PlanError):
            vault.write(data)
    assert vault.path.read_bytes() == before
    assert sorted(path.name for path in vault.directory.iterdir()) == ["plan-v1.bin", "vault.lock"]


def test_dpapi_tamper_rejected_and_no_plaintext_fallback(service):
    signed(service)
    service.auth.vault.path.write_bytes(b"not a DPAPI blob")
    with pytest.raises(PlanError):
        service.auth.accounts()


def test_cross_process_vault_lock_is_bounded(service):
    signed(service)
    script = """from scryraven.chatgpt_plan.storage import Vault
from scryraven.chatgpt_plan.http import PlanError
import sys
try:
    with Vault(sys.argv[1]).locked(timeout=0.15):
        print('unexpected_lock')
except PlanError as exc:
    print(exc.diagnostic['reason'])
"""
    with service.auth.vault.locked():
        result = subprocess.run([sys.executable, "-c", script, str(service.auth.vault.directory)],
                                capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and result.stdout.strip() == "credential_lock_timeout"


def test_sse_multiline_and_comment_framing_and_total_deadline():
    class Response:
        def iter_content(self, **kwargs):
            yield b': comment\n\nevent: response.completed\ndata: {"type":\ndata: "response.completed"}\n\n'
    reader = events(Response(), Deadline(5))
    assert next(reader) == {"type": "response.completed"}
    deadline = Deadline(1)
    deadline.end = 0
    with pytest.raises(PlanError, match="model_request_timed_out"):
        next(events(Response(), deadline))


def test_no_ambient_credentials_endpoints_timeouts_or_error_text_leak(monkeypatch):
    http = PublicHTTP()
    assert http.session.trust_env is False
    for url in ("https://chatgpt.com/backend-api/responses", "http://api.openai.com/v1/responses"):
        with pytest.raises(PlanError, match="model_request_rejected"):
            http.request("POST", url, timeout=1)
    monkeypatch.setattr(http.session, "request", lambda *a, **k: (_ for _ in ()).throw(requests.Timeout("fixture-private")))
    with pytest.raises(PlanError, match="model_request_timed_out") as caught:
        http.json("GET", MODELS)
    assert "fixture-private" not in str(caught.value) + repr(caught.value.diagnostic)
