"""Serper yields bounded navigation candidates and safe transport failures."""

import pytest

from core import serper_transport as serper


class Response:
    def __init__(self, payload, error=None):
        self.payload, self.error = payload, error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


def test_serper_search_normalizes_only_navigation_fields():
    calls = []
    payload = {"organic": [
        {"title": "  Public   post ", "link": "https://example.test/post", "snippet": "  A   claimed fact ",
         "position": 2, "date": "Sep 2026", "providerAnswer": "must not be retained"},
        {"title": "Missing URL", "snippet": "ignored"},
    ], "answerBox": {"answer": "must not be retained"}}

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response(payload)

    result = serper.search_serper("  exact post  ", api_key="offline", post=post)  # pragma: allowlist secret
    assert calls == [(serper.SERPER_SEARCH_URL, {
        "json": {"q": "exact post", "num": 10},
        "headers": {"X-API-KEY": "offline", "Content-Type": "application/json"},  # pragma: allowlist secret
        "timeout": serper.DEFAULT_TIMEOUT_SECONDS,
    })]
    assert len(result) == 1
    assert (result[0].title, result[0].url, result[0].context_kind) == (
        "Public post", "https://example.test/post", "navigation")
    assert result[0].context == "position 2 | Sep 2026 | A claimed fact"
    assert "must not be retained" not in repr(result)


def test_serper_key_is_needed_only_when_invoked(monkeypatch):
    monkeypatch.delenv(serper.SERPER_API_KEY_ENV, raising=False)
    with pytest.raises(serper.SerperTransportError, match="^serper_configuration_missing$"):
        serper.search_serper("public post")


@pytest.mark.parametrize("payload,error,code", [
    ({}, OSError("private provider detail"), "serper_transport_failed"),
    ([], None, "serper_response_invalid"),
    ({"organic": "bad"}, None, "serper_results_invalid"),
])
def test_serper_failure_exposes_only_safe_code(payload, error, code):
    with pytest.raises(serper.SerperTransportError, match=f"^{code}$"):
        serper.search_serper("query", api_key="offline",  # pragma: allowlist secret
                             post=lambda *args, **kwargs: Response(payload, error))
