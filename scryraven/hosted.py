"""Explicit hosted policy and verification of Cloudflare Access application JWTs.

This module owns only deployment and admission identity, never research policy.
No token, credential, raw request header or provider response is logged here.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic

import jwt
import requests
from urllib3.util import Timeout

from scryraven.model import ModelError, built_in_model_config
from scryraven.run_settings import PHYSICAL_REQUEST_CEILING, RunSettings

_ISSUER = re.compile(r"https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.cloudflareaccess\.com\Z")
_HOSTNAME = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\Z")
_EMAIL = re.compile(r"[^\s@,;\x00-\x1f\x7f]+@[^\s@,;\x00-\x1f\x7f]+\.[^\s@,;\x00-\x1f\x7f]+\Z", re.ASCII)
_KID = re.compile(r"[A-Za-z0-9._-]{1,256}\Z")


class HostedConfigurationError(ValueError):
    def __init__(self):
        super().__init__("invalid_hosted_configuration")


class AccessDenied(ValueError):
    def __init__(self):
        super().__init__("access_denied")


def _email(value: str) -> str:
    if not isinstance(value, str) or len(value) > 254 or not _EMAIL.fullmatch(value) or not value.isascii():
        raise ValueError("invalid_identity")
    return value.lower()


@dataclass(frozen=True)
class AccessIdentity:
    email: str
    subject: str
    is_admin: bool

    @property
    def owner_id(self) -> str:
        return self.email


@dataclass(frozen=True)
class HostedConfig:
    hostname: str
    issuer: str
    audience: str
    admin_email: str
    tester_emails: frozenset[str]
    data_dir: Path
    run_settings: RunSettings
    submissions_per_day: int = 20
    forensic_days: int = 30
    forensic_max_bytes: int = 1_073_741_824

    def __post_init__(self):
        try:
            if (not _ISSUER.fullmatch(self.issuer)
                    or not isinstance(self.audience, str) or not 1 <= len(self.audience) <= 256
                    or any(c.isspace() for c in self.audience)
                    or not (_HOSTNAME.fullmatch(self.hostname) or self.hostname == "localhost")
                    or not isinstance(self.data_dir, Path) or not self.data_dir.is_absolute()
                    or self.data_dir == self.data_dir.parent
                    or self.run_settings.backend != "openai"
                    or self.run_settings.physical_request_limit != PHYSICAL_REQUEST_CEILING
                    or type(self.submissions_per_day) is not int or self.submissions_per_day < 1
                    or type(self.forensic_days) is not int or self.forensic_days < 1
                    or type(self.forensic_max_bytes) is not int or self.forensic_max_bytes < 1024):
                raise ValueError()
            admin = _email(self.admin_email)
            testers = frozenset(_email(item) for item in self.tester_emails)
            if not testers or admin in testers:
                raise ValueError()
            object.__setattr__(self, "admin_email", admin)
            object.__setattr__(self, "tester_emails", testers)
            object.__setattr__(self, "data_dir", self.data_dir.resolve())
        except (AttributeError, TypeError, ValueError):
            raise HostedConfigurationError() from None

    @property
    def origin(self) -> str:
        return "https://" + self.hostname

    @property
    def database(self) -> Path:
        return self.data_dir / "sessions.sqlite3"

    @property
    def diagnostics_dir(self) -> Path:
        return self.data_dir / "diagnostics"

    @classmethod
    def from_env(cls, environment: Mapping[str, str] | None = None) -> HostedConfig:
        """Read only explicit hosted settings; never load a dotenv/personal file."""
        env = os.environ if environment is None else environment
        try:
            if env.get("SCRYRAVEN_MODE") != "hosted" or env.get("SCRYRAVEN_BILLING_AUTHORIZED") != "true":
                raise ValueError()
            defaults = built_in_model_config()
            processing = env.get("SCRYRAVEN_API_PROCESSING", "standard")
            settings = RunSettings(
                "openai", env.get("SCRYRAVEN_RESEARCH_MODEL", defaults.research.model),
                env.get("SCRYRAVEN_RESEARCH_REASONING", defaults.research.reasoning) or None,
                env.get("SCRYRAVEN_ANSWER_MODEL", defaults.answer.model),
                env.get("SCRYRAVEN_ANSWER_REASONING", defaults.answer.reasoning) or None,
                processing, PHYSICAL_REQUEST_CEILING,
            )
            hostname = env.get("SCRYRAVEN_HOSTNAME", "dogfood.scryraven.com")
            # The environment entrypoint accepts a real DNS hostname only. A
            # directly constructed localhost config is useful for offline tests.
            if not _HOSTNAME.fullmatch(hostname):
                raise ValueError()
            data_dir = Path(env["SCRYRAVEN_DATA_DIR"])
            if env.get("RAILWAY_ENVIRONMENT_ID"):
                mount = Path(env["RAILWAY_VOLUME_MOUNT_PATH"])
                if (not mount.is_absolute() or mount == mount.parent or not mount.is_dir()
                        or not data_dir.is_absolute() or not data_dir.resolve().is_relative_to(mount.resolve())):
                    raise ValueError()
            return cls(
                hostname, env["CF_ACCESS_ISSUER"], env["CF_ACCESS_AUD"],
                env["SCRYRAVEN_ADMIN_EMAIL"],
                frozenset(item.strip() for item in env["SCRYRAVEN_TESTER_EMAILS"].split(",")),
                data_dir, settings,
                int(env.get("SCRYRAVEN_SUBMISSIONS_PER_DAY", "20")),
                int(env.get("SCRYRAVEN_FORENSIC_DAYS", "30")),
                int(env.get("SCRYRAVEN_FORENSIC_MAX_BYTES", "1073741824")),
            )
        except (KeyError, TypeError, ValueError, OSError):
            raise HostedConfigurationError() from None


class AccessTokenValidator:
    """RS256 verification with a bounded, trusted-origin JWKS cache.

    Untrusted JWT headers never choose an endpoint or an algorithm. Unknown key
    IDs can refresh at most once per minute; an expired cache cannot authenticate
    during a key-service outage. Successful cached verification needs no I/O.
    """

    cache_seconds = 300
    refresh_seconds = 60
    max_jwks_bytes = 256 * 1024
    fetch_seconds = 10

    def __init__(self, config: HostedConfig, *, get=None, clock=monotonic):
        self.config = config
        if get is None:
            session = requests.Session()
            # JWKS transport consumes no ambient .netrc credentials or proxy
            # settings. Trust is the configured HTTPS issuer and system CA set.
            session.trust_env = False
            get = session.get
        self.get = get
        self.clock = clock
        self.lock = Lock()
        self.keys = {}
        self.valid_until = 0.0
        self.next_refresh = 0.0

    def _refresh(self, now):
        from scryraven.chatgpt_plan.http import response_deadline

        self.next_refresh = now + self.refresh_seconds
        url = self.config.issuer + "/cdn-cgi/access/certs"
        started = monotonic()
        with self.get(url, timeout=Timeout(total=self.fetch_seconds, connect=3, read=5),
                      allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise AccessDenied()
            content = bytearray()
            with response_deadline(response, self.fetch_seconds - (monotonic() - started)):
                for chunk in response.iter_content(8192):
                    content.extend(chunk)
                    if len(content) > self.max_jwks_bytes:
                        raise AccessDenied()
        document = json.loads(content)
        if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
            raise AccessDenied()
        keys = {}
        for item in document["keys"]:
            if (not isinstance(item, dict) or item.get("kty") != "RSA"
                    or item.get("use", "sig") != "sig" or item.get("alg", "RS256") != "RS256"
                    or not isinstance(item.get("kid"), str) or not _KID.fullmatch(item["kid"])):
                continue
            if item["kid"] in keys:
                raise AccessDenied()
            key = jwt.PyJWK.from_dict(item, algorithm="RS256").key
            if key.key_size < 2048:
                raise AccessDenied()
            keys[item["kid"]] = key
        if not keys:
            raise AccessDenied()
        self.keys = keys
        self.valid_until = now + self.cache_seconds

    def validate(self, token: str | None) -> AccessIdentity:
        try:
            if not isinstance(token, str) or not 1 <= len(token) <= 16384:
                raise AccessDenied()
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if header.get("alg") != "RS256" or not isinstance(kid, str) or not _KID.fullmatch(kid):
                raise AccessDenied()
            with self.lock:
                now = self.clock()
                if (now >= self.valid_until or kid not in self.keys) and now >= self.next_refresh:
                    self._refresh(now)
                if now >= self.valid_until or kid not in self.keys:
                    raise AccessDenied()
                key = self.keys[kid]
            claims = jwt.decode(
                token, key, algorithms=["RS256"], audience=self.config.audience,
                issuer=self.config.issuer,
                options={"require": ["iss", "aud", "exp", "iat", "sub", "email"]},
            )
            if (claims.get("type") != "app"
                    or any(type(claims[name]) not in {int, float} for name in ("exp", "iat"))
                    or claims["exp"] <= claims["iat"]
                    or claims.get("email_verified", True) is not True
                    or not isinstance(claims["sub"], str) or not 1 <= len(claims["sub"]) <= 256):
                raise AccessDenied()
            email = _email(claims["email"])
            if email != self.config.admin_email and email not in self.config.tester_emails:
                raise AccessDenied()
            return AccessIdentity(email, claims["sub"], email == self.config.admin_email)
        except (jwt.PyJWTError, requests.RequestException, ModelError, OSError, TypeError, ValueError,
                KeyError, RecursionError, OverflowError):
            raise AccessDenied() from None
