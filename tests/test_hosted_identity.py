"""Signed synthetic Access tokens and deployment configuration, entirely offline."""

from __future__ import annotations

import json
from dataclasses import replace
from threading import Event
from time import time

import jwt
import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa

from scryraven.hosted import (
    AccessDenied,
    AccessTokenValidator,
    HostedConfig,
    HostedConfigurationError,
)
from scryraven.run_settings import RunSettings


@pytest.fixture
def config(tmp_path):
    return HostedConfig(
        "dogfood.example.test", "https://synthetic-team.cloudflareaccess.com", "synthetic-app-audience",
        "owner@example.test", frozenset({"alice@example.test", "bob@example.test"}), tmp_path,
        RunSettings("openai", "gpt-6.1-terra", "medium", "gpt-6.1-sol", "medium", "standard", 40),
    )


@pytest.fixture(scope="module")
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def claims(config, **overrides):
    now = int(time())
    return {"type": "app", "iss": config.issuer, "aud": [config.audience],
            "iat": now - 1, "exp": now + 120, "sub": "synthetic-access-uuid",
            "email": "alice@example.test", **overrides}


def token(config, key, **overrides):
    return jwt.encode(claims(config, **overrides), key, algorithm="RS256", headers={"kid": "synthetic-key"})


def jwks(key, kid="synthetic-key"):
    return {"keys": [{**jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True),
                      "kid": kid, "use": "sig", "alg": "RS256"}]}


class Response:
    def __init__(self, value, status=200):
        self.body = json.dumps(value).encode()
        self.status_code = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def iter_content(self, size):
        yield self.body


def validator(config, key, **kwargs):
    return AccessTokenValidator(config, get=lambda *args, **kw: Response(jwks(key)), **kwargs)


def test_valid_identity_and_admin_are_derived_from_signed_claims(config, key):
    check = validator(config, key)
    alice = check.validate(token(config, key, email="ALICE@example.test"))
    assert alice.email == alice.owner_id == "alice@example.test"
    assert alice.subject == "synthetic-access-uuid" and not alice.is_admin
    assert check.validate(token(config, key, email="owner@example.test")).is_admin


@pytest.mark.parametrize("change", [
    {"iss": "https://other.cloudflareaccess.com"}, {"aud": "other-app"},
    {"exp": int(time()) - 60}, {"iat": int(time()) + 3600}, {"nbf": int(time()) + 3600},
    {"email": "outsider@example.test"}, {"email": "owner@example.test\n"},
    {"email_verified": False}, {"type": "service"}, {"sub": ""},
    {"exp": "9999999999"}, {"iat": True}, {"email": ["alice@example.test"]},
])
def test_rejects_invalid_claims(config, key, change):
    with pytest.raises(AccessDenied, match="^access_denied$"):
        validator(config, key).validate(token(config, key, **change))


@pytest.mark.parametrize("field", ["iss", "aud", "exp", "iat", "sub", "email"])
def test_rejects_missing_claims(config, key, field):
    value = claims(config)
    del value[field]
    raw = jwt.encode(value, key, algorithm="RS256", headers={"kid": "synthetic-key"})
    with pytest.raises(AccessDenied):
        validator(config, key).validate(raw)


@pytest.mark.parametrize("raw", [None, "", "not-a-token", "a" * 16385])
def test_malformed_token_never_fetches_keys(config, raw):
    def forbidden(*_args, **_kwargs):
        pytest.fail("Malformed token caused network I/O")

    with pytest.raises(AccessDenied):
        AccessTokenValidator(config, get=forbidden).validate(raw)


def test_rejects_wrong_signing_key_and_pinned_algorithm(config, key):
    wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(AccessDenied):
        validator(config, key).validate(token(config, wrong))
    for algorithm, signing_key in [("none", None), ("HS256", b"synthetic-only-secret-of-at-least-32-bytes")]:
        raw = jwt.encode(claims(config), signing_key, algorithm=algorithm, headers={"kid": "synthetic-key"})
        with pytest.raises(AccessDenied):
            validator(config, key).validate(raw)


def test_cache_fixed_endpoint_rotation_and_expired_cache_outage(config, key):
    now = [1000.0]
    calls = []
    result = [Response(jwks(key))]

    def get(url, **kwargs):
        calls.append((url, kwargs))
        if isinstance(result[0], Exception):
            raise result[0]
        return result[0]

    check = AccessTokenValidator(config, get=get, clock=lambda: now[0])
    raw = token(config, key)
    check.validate(raw)
    check.validate(raw)
    assert len(calls) == 1
    assert calls[0][0] == config.issuer + "/cdn-cgi/access/certs"
    assert calls[0][1]["timeout"].total == 10
    assert calls[0][1]["timeout"].connect_timeout == 3
    assert calls[0][1]["allow_redirects"] is False and calls[0][1]["stream"] is True
    unknown = jwt.encode(claims(config), key, algorithm="RS256", headers={"kid": "rotated"})
    with pytest.raises(AccessDenied):
        check.validate(unknown)
    assert len(calls) == 1
    now[0] += 61
    result[0] = Response(jwks(key, "rotated"))
    check.validate(unknown)
    assert len(calls) == 2
    now[0] += 301
    result[0] = requests.ConnectionError("synthetic private transport text")
    with pytest.raises(AccessDenied, match="^access_denied$"):
        check.validate(unknown)
    assert len(calls) == 3


@pytest.mark.parametrize("value,status", [({}, 200), ({"keys": []}, 200), ({"keys": []}, 302),
                                         ({"keys": []}, 503), ({"keys": ["bad"]}, 200)])
def test_bad_key_service_response_fails_closed(config, key, value, status):
    check = AccessTokenValidator(config, get=lambda *args, **kwargs: Response(value, status))
    with pytest.raises(AccessDenied):
        check.validate(token(config, key))


@pytest.mark.filterwarnings("ignore:The RSA key is 1024 bits long")
def test_key_service_response_and_key_size_are_bounded(config, key):
    check = AccessTokenValidator(config, get=lambda *args, **kwargs: Response({"padding": "a" * 300000}))
    with pytest.raises(AccessDenied):
        check.validate(token(config, key))
    weak = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    with pytest.raises(AccessDenied):
        validator(config, weak).validate(token(config, weak))


def test_slow_key_response_has_total_body_deadline(config, key):
    released = Event()

    class SlowResponse(Response):
        def __init__(self):
            super().__init__(jwks(key))
            self.raw = self

        def shutdown(self):
            released.set()

        def iter_content(self, size):
            assert released.wait(2), "JWKS body deadline never interrupted the response"
            yield self.body

    check = AccessTokenValidator(config, get=lambda *args, **kwargs: SlowResponse())
    check.fetch_seconds = 0.03
    with pytest.raises(AccessDenied):
        check.validate(token(config, key))
    assert released.is_set()


def environment(tmp_path):
    return {"SCRYRAVEN_MODE": "hosted", "SCRYRAVEN_BILLING_AUTHORIZED": "true",
            "SCRYRAVEN_DATA_DIR": str(tmp_path), "CF_ACCESS_ISSUER": "https://synthetic.cloudflareaccess.com",
            "CF_ACCESS_AUD": "synthetic-app", "SCRYRAVEN_ADMIN_EMAIL": "owner@example.test",
            "SCRYRAVEN_TESTER_EMAILS": "alice@example.test,bob@example.test"}


def test_explicit_environment_never_reads_personal_model_configuration(tmp_path, monkeypatch):
    from scryraven import model

    monkeypatch.setattr(model, "default_model_config", lambda: pytest.fail("Read personal settings"))
    config = HostedConfig.from_env(environment(tmp_path))
    assert config.hostname == "dogfood.scryraven.com"
    assert config.origin == "https://dogfood.scryraven.com"
    assert config.database == tmp_path / "sessions.sqlite3"
    assert config.diagnostics_dir == tmp_path / "diagnostics"
    assert config.run_settings.backend == "openai" and config.run_settings.physical_request_limit == 40
    assert config.run_settings.api_processing == "fast"
    assert config.run_settings.research_model == "gpt-6.1-terra" and config.run_settings.research_reasoning == "medium"
    assert config.run_settings.answer_model == "gpt-6.1-sol" and config.run_settings.answer_reasoning == "medium"
    assert config.submissions_per_day == 20 and config.forensic_days == 30


@pytest.mark.parametrize("field", ["SCRYRAVEN_MODE", "SCRYRAVEN_BILLING_AUTHORIZED", "SCRYRAVEN_DATA_DIR",
                                  "CF_ACCESS_ISSUER", "CF_ACCESS_AUD", "SCRYRAVEN_ADMIN_EMAIL",
                                  "SCRYRAVEN_TESTER_EMAILS"])
def test_missing_hosted_settings_fails_closed(tmp_path, field):
    env = environment(tmp_path)
    del env[field]
    with pytest.raises(HostedConfigurationError, match="^invalid_hosted_configuration$"):
        HostedConfig.from_env(env)


@pytest.mark.parametrize("field,value", [
    ("CF_ACCESS_ISSUER", "http://synthetic.cloudflareaccess.com"),
    ("CF_ACCESS_ISSUER", "https://synthetic.cloudflareaccess.com.evil.test"),
    ("CF_ACCESS_ISSUER", "https://synthetic.cloudflareaccess.com/redirect"),
    ("SCRYRAVEN_DATA_DIR", "relative-data"), ("SCRYRAVEN_BILLING_AUTHORIZED", "false"),
    ("SCRYRAVEN_HOSTNAME", "*.example.test"), ("SCRYRAVEN_HOSTNAME", "localhost"),
    ("SCRYRAVEN_TESTER_EMAILS", "owner@example.test"), ("SCRYRAVEN_TESTER_EMAILS", ""),
    ("SCRYRAVEN_SUBMISSIONS_PER_DAY", "0"), ("SCRYRAVEN_FORENSIC_DAYS", "0"),
    ("SCRYRAVEN_FORENSIC_MAX_BYTES", "1"), ("SCRYRAVEN_RESEARCH_MODEL", "https://other.test/model"),
    ("SCRYRAVEN_API_PROCESSING", "unauthorized-tier"),
])
def test_invalid_hosted_configuration_rejected(tmp_path, field, value):
    env = environment(tmp_path)
    env[field] = value
    with pytest.raises(HostedConfigurationError):
        HostedConfig.from_env(env)


def test_config_cannot_enable_unauthorized_backend(config):
    settings = replace(config.run_settings, backend="chatgpt_plan", api_processing=None)
    with pytest.raises(HostedConfigurationError):
        replace(config, run_settings=settings)


def test_railway_requires_existing_volume_and_persistent_data_location(tmp_path):
    mount = tmp_path / "volume"
    mount.mkdir()
    env = {**environment(mount / "application"), "RAILWAY_ENVIRONMENT_ID": "synthetic-environment"}
    with pytest.raises(HostedConfigurationError):
        HostedConfig.from_env(env)
    env["RAILWAY_VOLUME_MOUNT_PATH"] = str(mount)
    assert HostedConfig.from_env(env).data_dir == mount / "application"
    for invalid in [str(tmp_path / "ephemeral"), str(mount / ".." / "ephemeral"), "relative-data"]:
        with pytest.raises(HostedConfigurationError):
            HostedConfig.from_env({**env, "SCRYRAVEN_DATA_DIR": invalid})
    for invalid in [str(tmp_path / "missing-volume"), "relative-volume", ""]:
        with pytest.raises(HostedConfigurationError):
            HostedConfig.from_env({**env, "RAILWAY_VOLUME_MOUNT_PATH": invalid})
