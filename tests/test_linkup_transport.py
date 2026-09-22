"""Offline contract for LinkUp static Fetch as ordinary external Read."""

import pytest

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
