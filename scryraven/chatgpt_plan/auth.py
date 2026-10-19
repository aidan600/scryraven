"""Documented public-client dynamic registration, OIDC validation and renewal."""

from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import math
import re
import secrets
import time
import uuid
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt

from .http import AUTHORIZE, DIRECT, ISSUER, JWKS, RESOURCE, SCOPES, TOKEN, PlanError, PublicHTTP
from .storage import Vault

TERMINAL_REFRESH = {
    "invalid_grant", "invalid_refresh_token", "token_expired", "refresh_token_expired",
    "refresh_token_invalidated", "refresh_token_reused",
}


class Deadline:
    def __init__(self, seconds):
        if not math.isfinite(seconds) or seconds <= 0:
            raise PlanError("model_request_timed_out")
        self.end = time.monotonic() + seconds

    def left(self):
        value = self.end - time.monotonic()
        if value <= 0:
            raise PlanError("model_request_timed_out")
        return value


@dataclass(repr=False)
class Attempt:
    label: str
    host_id: str
    redirect_uri: str
    previous: dict | None
    client_id: str
    state: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    nonce: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    verifier: str = field(default_factory=lambda: secrets.token_urlsafe(64))
    expires_at: float = field(default_factory=lambda: time.monotonic() + 180)
    consumed: bool = False

    def url(self, *, consent=False):
        query = {
            "client_id": self.client_id, "ext_agent_host_id": self.host_id,
            "response_type": "code", "redirect_uri": self.redirect_uri, "scope": SCOPES,
            "resource": RESOURCE, "state": self.state, "nonce": self.nonce,
            "code_challenge_method": "S256",
            "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest())
            .decode().rstrip("="),
        }
        if self.client_id == "dynamic_agent_client":
            query["agent_name_hint"] = "ScryRaven"
        if self.previous:
            if self.previous.get("id_token"):
                query["id_token_hint"] = self.previous["id_token"]
            if self.previous.get("email"):
                query["login_hint"] = self.previous["email"]
        if consent:
            query["prompt"] = "consent"
        return AUTHORIZE + "?" + urlencode(query)


def _label(label):
    if not isinstance(label, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,47}", label):
        raise PlanError("model_configuration_missing", reason="invalid_account_label")


class Auth:
    def __init__(self, vault=None, http=None, *, clock=time.time):
        self.vault = vault if vault is not None else Vault()
        self.http = http if http is not None else PublicHTTP()
        self.clock = clock

    def prepare(self, label, redirect_uri, *, client_id=None):
        _label(label)
        uri = urlsplit(redirect_uri)
        if uri.scheme != "http" or uri.hostname != "127.0.0.1" or uri.path != "/auth/callback" or (
            not uri.port or uri.query or uri.fragment or uri.username or uri.password
        ):
            raise PlanError("model_request_rejected", reason="invalid_loopback_uri")
        with self.vault.locked():
            data = self.vault.read()
            if not self.vault.path.exists():
                self.vault.write(data)  # Persist host identity before first authorization.
            previous = copy.deepcopy(data["accounts"].get(label))
        return Attempt(label, data["host_id"], redirect_uri, previous,
                       client_id or (previous["client_id"] if previous else "dynamic_agent_client"))

    def verify(self, encoded, client_id, nonce, deadline):
        try:
            header = jwt.get_unverified_header(encoded)
            algorithm = header.get("alg")
            if algorithm not in {"RS256", "ES256"} or not isinstance(header.get("kid"), str):
                raise ValueError
            keys = self.http.json("GET", JWKS, timeout=deadline.left()).get("keys")
            if not isinstance(keys, list):
                raise ValueError
            matches = [key for key in keys if isinstance(key, dict) and key.get("kid") == header["kid"]]
            if len(matches) != 1 or matches[0].get("use", "sig") != "sig":
                raise ValueError
            if matches[0].get("alg", algorithm) != algorithm:
                raise ValueError
            key = jwt.PyJWK.from_dict(matches[0], algorithm=algorithm).key
            claims = jwt.decode(encoded, key, algorithms=[algorithm], audience=client_id, issuer=ISSUER,
                                leeway=5, options={"require": ["sub", "exp", "iat"]})
            if not isinstance(claims["sub"], str) or not claims["sub"]:
                raise ValueError
            if nonce is not None and (
                not isinstance(claims.get("nonce"), str) or not hmac.compare_digest(claims["nonce"], nonce)
            ):
                raise ValueError
            if isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and claims.get("azp") != client_id:
                raise ValueError
            return claims
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise PlanError("model_authentication_failed", reason="id_token_invalid") from None

    def _record(self, body, client_id, nonce, deadline, *, previous=None):
        # A refresh may omit scope or id_token. Never inherit a scope on initial exchange.
        scope = body.get("scope", " ".join(previous["scopes"]) if previous else None)
        if not isinstance(scope, str) or not isinstance(body.get("token_type"), str) or body["token_type"].lower() != "bearer":
            raise PlanError("malformed_model_response", reason="invalid_token_response")
        expires = body.get("expires_in")
        if type(expires) not in {int, float} or not math.isfinite(expires) or expires <= 0:
            raise PlanError("malformed_model_response", reason="invalid_token_expiry")
        scopes = scope.split()
        access, refresh = body.get("access_token"), body.get("refresh_token")
        if not isinstance(access, str) or not access or ("offline_access" in scopes and (
            not isinstance(refresh, str) or not refresh
        )):
            raise PlanError("malformed_model_response", reason="missing_credentials")
        encoded = body.get("id_token")
        if previous is None or encoded is not None:
            if not isinstance(encoded, str) or not encoded:
                raise PlanError("model_authentication_failed", reason="missing_id_token")
            # A renewed ID token need not repeat the original nonce (OIDC refresh).
            claims = self.verify(encoded, client_id, nonce, deadline)
            if previous and claims["sub"] != previous["subject"]:
                raise PlanError("model_authentication_failed", reason="account_identity_changed")
            email = claims.get("email") if isinstance(claims.get("email"), str) else None
            subject = claims["sub"]
        else:
            encoded, email, subject = previous.get("id_token"), previous.get("email"), previous["subject"]
        now = self.clock()
        return {
            "issuer": ISSUER, "subject": subject, "client_id": client_id, "email": email,
            "id_token": encoded, "access_token": access, "refresh_token": refresh,
            "token_type": "Bearer", "scopes": scopes, "saved_at": now, "expires_at": now + expires,
            # Preserve this opaque provider field without assuming an undocumented format.
            "earliest_refresh_at": body.get("earliest_refresh_at"),
            "session_id": previous["session_id"] if previous else str(uuid.uuid4()),
        }

    def complete(self, attempt, query, *, timeout=30):
        if attempt.consumed or time.monotonic() >= attempt.expires_at:
            raise PlanError("model_authentication_failed", reason="authorization_attempt_expired_or_used")
        state = query.get("state")
        if not isinstance(state, str) or not hmac.compare_digest(state, attempt.state):
            raise PlanError("model_authentication_failed", reason="oauth_state_invalid")
        attempt.consumed = True
        if "error" in query:
            raise PlanError("model_access_denied", reason="authorization_denied")
        issued = query.get("client_id", attempt.client_id)
        if not isinstance(issued, str) or not issued.startswith("oaiapp_") or (
            attempt.client_id != "dynamic_agent_client" and issued != attempt.client_id
        ):
            raise PlanError("model_authentication_failed", reason="issued_client_invalid")
        attempt.client_id = issued  # Retain in memory if code exchange needs a fresh attempt.
        code = query.get("code")
        if not isinstance(code, str) or not code:
            raise PlanError("model_authentication_failed", reason="authorization_code_missing")
        deadline = Deadline(timeout)
        body = self.http.json("POST", TOKEN, timeout=deadline.left(), data={
            "grant_type": "authorization_code", "client_id": issued, "code": code,
            "code_verifier": attempt.verifier, "redirect_uri": attempt.redirect_uri, "resource": RESOURCE,
        })
        record = self._record(body, issued, attempt.nonce, deadline)
        if attempt.previous and record["subject"] != attempt.previous["subject"]:
            raise PlanError("model_authentication_failed", reason="account_identity_changed")
        with self.vault.locked(timeout=deadline.left()):
            data = self.vault.read()
            current = data["accounts"].get(attempt.label)
            if current != attempt.previous:
                raise PlanError("model_authentication_failed", reason="account_changed_during_sign_in")
            # Distinct labels cannot silently duplicate/overwrite the same registration.
            if any(label != attempt.label and row["client_id"] == issued for label, row in data["accounts"].items()):
                raise PlanError("model_authentication_failed", reason="registration_already_saved")
            data["accounts"][attempt.label] = record
            self.vault.write(data)
        return {"account": attempt.label, "plan_enabled": DIRECT in record["scopes"]}

    def accounts(self):
        with self.vault.locked():
            data = self.vault.read()
        return [{"account": label, "plan_enabled": DIRECT in row["scopes"],
                 "sign_in_required": not bool(row.get("access_token"))} for label, row in data["accounts"].items()]

    def access(self, label, *, timeout=30):
        _label(label)
        deadline = Deadline(timeout)
        with self.vault.locked(timeout=deadline.left()):
            data = self.vault.read()
            row = data["accounts"].get(label)
            if not row or not row.get("access_token"):
                raise PlanError("model_authentication_failed", reason="sign_in_required")
            if DIRECT not in row["scopes"]:
                raise PlanError("model_access_denied", reason="plan_permission_denied")
            if row["expires_at"] > self.clock() + 60:
                return copy.deepcopy(row)
            if not row.get("refresh_token"):
                raise PlanError("model_authentication_failed", reason="sign_in_required")
            try:
                body = self.http.json("POST", TOKEN, timeout=deadline.left(), data={
                    "grant_type": "refresh_token", "client_id": row["client_id"],
                    "refresh_token": row["refresh_token"], "resource": RESOURCE,
                })
            except PlanError as exc:
                if exc.diagnostic.get("provider_code") in TERMINAL_REFRESH:
                    # Preserve account/client/host mapping for reauthorization.
                    for name in ("access_token", "refresh_token", "id_token"):
                        row[name] = None
                    self.vault.write(data)
                raise
            replacement = self._record(body, row["client_id"], None, deadline, previous=row)
            data["accounts"][label] = replacement
            self.vault.write(data)
            if DIRECT not in replacement["scopes"]:
                raise PlanError("model_access_denied", reason="plan_permission_denied")
            return copy.deepcopy(replacement)

    def sign_in(self, label, *, browser=webbrowser.open, seconds=180, consent=False):
        """Only this explicitly invoked command opens a browser/listener."""
        deadline, retry_client = Deadline(seconds), None
        for _ in range(2):
            received = []
            attempt = None

            class Callback(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass  # Default HTTP logging would expose codes, state and query strings.

                def do_GET(self):
                    self.connection.settimeout(2)
                    uri = urlsplit(self.path)
                    query = parse_qs(uri.query, keep_blank_values=True, max_num_fields=16)
                    valid = (
                        len(self.path) <= 16384 and uri.path == "/auth/callback" and not uri.scheme
                        and self.headers.get("Host") == urlsplit(attempt.redirect_uri).netloc
                        and all(len(value) == 1 for value in query.values())
                        and len(query.get("state", [])) == 1
                        and hmac.compare_digest(query["state"][0], attempt.state)
                    )
                    if valid and not received:
                        received.append({key: value[0] for key, value in query.items()})
                    self.send_response(200 if valid else 400)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Referrer-Policy", "no-referrer")
                    self.end_headers()
                    self.wfile.write(b"Return to ScryRaven for the validated sign-in result.")

            class Listener(HTTPServer):
                def get_request(self):
                    connection, address = super().get_request()
                    connection.settimeout(min(2, deadline.left()))
                    return connection, address

                def handle_error(self, request, client_address):
                    pass  # No callback contents or socket exception transcripts.

            try:
                with Listener(("127.0.0.1", 0), Callback) as listener:
                    redirect = f"http://127.0.0.1:{listener.server_port}/auth/callback"
                    attempt = self.prepare(label, redirect, client_id=retry_client)
                    attempt.expires_at = deadline.end
                    if not browser(attempt.url(consent=consent)):
                        raise PlanError("model_configuration_missing", reason="browser_open_failed")
                    while not received:
                        listener.timeout = min(0.5, deadline.left())
                        listener.handle_request()
                return self.complete(attempt, received[0], timeout=deadline.left())
            except PlanError as exc:
                if exc.diagnostic.get("provider_code") == "invalid_grant" and retry_client is None:
                    retry_client = attempt.client_id
                    continue  # New state/nonce/verifier/code; never replay the rejected code.
                raise
            except OSError:
                raise PlanError("model_transport_failed", reason="loopback_listener_failed") from None
        raise PlanError("model_authentication_failed", reason="sign_in_required")
