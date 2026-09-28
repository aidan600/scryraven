"""Offline contract for LinkUp static Fetch as ordinary external Read."""

import traceback

import pytest
import requests

from core import linkup_transport as linkup
from core.transport import FetchedMaterial


class Response:
    def __init__(self, payload, error=None):
        self.payload, self.error = payload, error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


def test_static_fetch_preserves_returned_markdown_for_the_exact_requested_url():
    requested_url = "https://example.test/public-source"
    source = "  # Original provider Markdown\n\nExact source words.  "
    calls = []

    def post(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return Response({"markdown": source})

    assert linkup.fetch_linkup(requested_url, api_key="offline", post=post) == FetchedMaterial(requested_url, source)  # pragma: allowlist secret
    assert calls == [(linkup.LINKUP_FETCH_URL, {
        "json": {"url": requested_url},
        "headers": {"Authorization": "Bearer offline", "Content-Type": "application/json"},
        "timeout": linkup.DEFAULT_TIMEOUT_SECONDS,
    })]


def test_missing_credential_fails_closed(monkeypatch):
    monkeypatch.delenv(linkup.LINKUP_API_KEY_ENV, raising=False)
    with pytest.raises(linkup.LinkupTransportError, match="^linkup_configuration_missing$"):
        linkup.fetch_linkup("https://example.test/source")


def test_transport_failure_is_safe():
    with pytest.raises(linkup.LinkupTransportError, match="^linkup_transport_failed$"):
        linkup.fetch_linkup("https://example.test/source", api_key="offline",  # pragma: allowlist secret
                            post=lambda *args, **kwargs: Response({}, OSError("private provider response")))


@pytest.mark.parametrize("payload", [None, [], {}, {"markdown": ""}, {"content": "   "}])
def test_invalid_or_empty_response_fails_closed(payload):
    with pytest.raises(linkup.LinkupTransportError, match="^(linkup_response_invalid|linkup_material_unavailable)$"):
        linkup.fetch_linkup("https://example.test/source", api_key="offline",  # pragma: allowlist secret
                            post=lambda *args, **kwargs: Response(payload))


def test_content_is_accepted_without_rewriting_when_markdown_is_absent():
    url = "https://example.test/source"
    source = "Unchanged provider content\n"
    result = linkup.fetch_linkup(url, api_key="offline", post=lambda *args, **kwargs: Response({"content": source}))  # pragma: allowlist secret
    assert result.requested_url == url and result.readable_text == source


@pytest.mark.parametrize("failure, expected", [
    ("timeout", "linkup_timeout"),
    ("connection", "linkup_connection_failed"),
    (401, "linkup_endpoint_access_rejected"),
    (403, "linkup_endpoint_access_rejected"),
    (429, "linkup_endpoint_rate_limited"),
    (500, "linkup_endpoint_server_failed"),
    (503, "linkup_endpoint_server_failed"),
    (404, "linkup_transport_failed"),
    ("http_unknown", "linkup_transport_failed"),
    ("json", "linkup_json_invalid"),
    ("json_unknown", "linkup_transport_failed"),
    ("shape", "linkup_response_invalid"),
    ("blank", "linkup_material_unavailable"),
    ("missing", "linkup_material_unavailable"),
    ("unknown", "linkup_transport_failed"),
])
def test_failure_classification_exposes_only_fixed_codes(failure, expected):
    private = "SYNTHETIC_PRIVATE_BODY_HEADER_AND_EXCEPTION"
    token = "SYNTHETIC_PRIVATE_TOKEN"  # pragma: allowlist secret
    response = requests.Response()
    response.status_code = failure if type(failure) is int else 200
    response._content = (private + token).encode()
    response.headers["Private"] = private
    response.url = "https://api.linkup.so/v1/fetch"

    def post(*args, **kwargs):
        if failure == "timeout":
            raise requests.exceptions.Timeout(private + token)
        if failure == "connection":
            raise requests.exceptions.ConnectionError(private + token)
        if failure == "http_unknown":
            raise requests.exceptions.HTTPError(private + token)
        if failure == "unknown":
            raise RuntimeError(private + token)
        if failure == "json_unknown":
            def broken_json():
                raise RuntimeError(private + token)
            response.json = broken_json
        elif failure == "shape":
            response._content = ('["' + private + '"]').encode()
        elif failure == "blank":
            response._content = b'{"markdown":" ","content":" "}'
        elif failure == "missing":
            response._content = b'{}'
        return response

    with pytest.raises(linkup.LinkupTransportError) as caught:
        linkup.fetch_linkup("https://example.test/source", api_key=token, post=post)
    assert str(caught.value) == expected
    assert caught.value.args == (expected,)
    assert not vars(caught.value)
    displayed = "".join(traceback.format_exception(caught.value))
    assert private not in displayed and token not in displayed
