"""Fixed public endpoints, no environment credentials, redirects or retries."""

from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager

import requests
from urllib3.exceptions import ReadTimeoutError
from urllib3.util import Timeout

from scryraven.model import ModelError

ISSUER = "https://auth.openai.com"
AUTHORIZE = ISSUER + "/api/accounts/authorize"
TOKEN = ISSUER + "/api/accounts/oauth/token"
JWKS = ISSUER + "/.well-known/jwks.json"
RESOURCE = "https://api.openai.com/v1"
MODELS = RESOURCE + "/models"
RESPONSES = RESOURCE + "/responses"
DIRECT = "chatgpt.tokens.use.direct"
SCOPES = "openid profile email offline_access resource.invoke " + DIRECT
OAUTH_ERRORS = {
    "invalid_grant", "invalid_client", "invalid_refresh_token", "token_expired",
    "refresh_token_expired", "refresh_token_invalidated", "refresh_token_reused",
}
PLAN_ERRORS = {
    "subscription_sharing_user_not_eligible", "subscription_sharing_usage_limit_exceeded",
    "subscription_sharing_usage_unavailable", "subscription_sharing_unsupported_capability",
    "subscription_sharing_route_not_supported", "subscription_sharing_invalid_user",
    "subscription_sharing_user_unavailable", "chatpass_v2_scope_not_authorized",
    "chatpass_v2_invalid_authorization_context",
}
PARAMS = {
    "model", "reasoning", "reasoning.effort", "text", "text.format", "service_tier", "input",
    "tools", "store", "stream", "max_output_tokens", "prompt_cache_breakpoint",
}


class PlanError(ModelError):
    """Safe fixed code plus body-free, allowlisted diagnostic attributes."""

    def __init__(self, code, *, reason=None, status=None, provider_code=None, param=None, shape=None):
        super().__init__(code)
        self.diagnostic = {"code": code}
        for key, value in (
            ("reason", reason), ("http_status", status), ("provider_code", provider_code),
            ("param", param), ("body_shape", shape),
        ):
            if value is not None:
                self.diagnostic[key] = value


@contextmanager
def response_deadline(response, seconds):
    """Interrupt a blocked body read, including a silent reasoning stream.

    A requests read timeout alone is an inactivity timeout, not a total deadline.
    urllib3's public shutdown API interrupts the read without a background model
    request or a persistent worker. The watchdog ends with this response.
    """
    if seconds <= 0:
        raise PlanError("model_request_timed_out")
    expired = threading.Event()

    def shutdown():
        expired.set()
        try:
            response.raw.shutdown()
        except (OSError, ValueError, RuntimeError):
            pass  # The connection may already have completed/released.

    timer = threading.Timer(seconds, shutdown)
    timer.daemon = True
    timer.start()
    try:
        yield
        if expired.is_set():
            raise PlanError("model_request_timed_out")
    except (requests.RequestException, PlanError) as exc:
        # requests wraps streamed urllib3 read timeouts in ConnectionError.
        if expired.is_set() or isinstance(exc, requests.Timeout) or (
            isinstance(exc, requests.RequestException) and any(isinstance(arg, ReadTimeoutError) for arg in exc.args)
        ):
            raise PlanError("model_request_timed_out") from None
        raise
    finally:
        timer.cancel()
        timer.join()


def failure(status, body):
    """Never copy provider messages, arbitrary keys, request IDs or body values.

    Request IDs are deliberately omitted: an untrusted server can echo a token
    there. Preserve status, known code/parameter and the broad body shape instead.
    """
    error = body.get("error") if isinstance(body, dict) else None
    code = error.get("code") if isinstance(error, dict) else error
    code = code if isinstance(code, str) and code in OAUTH_ERRORS | PLAN_ERRORS else None
    param = error.get("param") if isinstance(error, dict) else None
    param = param if isinstance(param, str) and param in PARAMS else None
    shape = "error_object" if isinstance(error, dict) else "oauth_error" if isinstance(error, str) else (
        "detail_object" if isinstance(body, dict) and "detail" in body else "other_object"
        if isinstance(body, dict) else "non_object"
    )
    inferred_status = {
        "subscription_sharing_usage_limit_exceeded": 429,
        "subscription_sharing_usage_unavailable": 503,
        "subscription_sharing_user_unavailable": 503,
        "subscription_sharing_user_not_eligible": 403,
        "subscription_sharing_invalid_user": 401,
        "subscription_sharing_unsupported_capability": 400,
        "subscription_sharing_route_not_supported": 403,
        "chatpass_v2_scope_not_authorized": 403,
        "chatpass_v2_invalid_authorization_context": 403,
    }.get(code)
    classification_status = status if status is not None else inferred_status
    safe = {
        401: "model_authentication_failed", 403: "model_access_denied", 429: "model_rate_limited",
        400: "model_request_rejected",
    }.get(classification_status, "model_unavailable" if classification_status and classification_status >= 500 else "model_transport_failed")
    return PlanError(safe, status=status, provider_code=code, param=param, shape=shape)


class PublicHTTP:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        # In particular, ignore .netrc, proxy variables and ambient API settings.
        self.session.trust_env = False

    def request(self, method, url, *, timeout, **kwargs):
        if (method, url) not in {("GET", JWKS), ("POST", TOKEN), ("GET", MODELS), ("POST", RESPONSES)}:
            raise PlanError("model_request_rejected", reason="unsupported_endpoint")
        try:
            return self.session.request(method, url, timeout=Timeout(total=timeout, connect=timeout, read=timeout),
                                        allow_redirects=False, **kwargs)
        except requests.Timeout:
            raise PlanError("model_request_timed_out") from None
        except requests.RequestException:
            raise PlanError("model_transport_failed") from None

    def json(self, method, url, *, timeout=30, **kwargs):
        end = time.monotonic() + timeout
        response = self.request(method, url, timeout=timeout, stream=True, **kwargs)
        try:
            with response_deadline(response, end - time.monotonic()):
                content = bytearray()
                for chunk in response.iter_content(chunk_size=4096):
                    content.extend(chunk)
                    if len(content) > 2_000_000:
                        raise PlanError("malformed_model_response", reason="json_size_limit")
                try:
                    body = json.loads(content)
                except (ValueError, RecursionError):
                    body = None
                if response.status_code != 200:
                    raise failure(response.status_code, body)
                if not isinstance(body, dict):
                    raise PlanError("malformed_model_response", reason="invalid_json_object")
                return body
        except requests.Timeout:
            raise PlanError("model_request_timed_out") from None
        except requests.RequestException:
            raise PlanError("model_transport_failed") from None
        finally:
            response.close()
