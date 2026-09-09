"""The fixed Exa path preserves source text and excludes generated outputs."""
import pytest

from core import exa_transport as exa


class Response:
    def __init__(self, payload, error=None):
        self.payload, self.error = payload, error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


def test_search_preserves_highlights_and_excludes_summary_and_metadata(monkeypatch):
    monkeypatch.setenv(exa.EXA_API_KEY_ENV, "offline-test-key")
    calls = []
    passages = ["  The range is 3–5 units.\n", "Applies only when the device is idle."]

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response({"results": [{"url": "https://example.test/rule", "title": "Rules",
                                     "highlights": passages, "summary": "Generated unsupported certainty",
                                     "text": "Unrequested text", "publishedDate": "2099-01-01"},
                                    {"url": "https://example.test/nav", "summary": "Generated answer"}]})

    results = exa.search_exa("meaning sought", post=post)
    assert calls[0][0] == exa.EXA_SEARCH_URL
    payload = calls[0][1]["json"]
    assert payload["contents"] == {"text": False, "highlights": {"query": "meaning sought", "maxCharacters": 4000}}
    assert payload["type"] == "auto" and payload["numResults"] == 6
    assert all(passage in results[0].context for passage in passages)
    assert "Separate provider highlight" in results[0].context
    assert "Generated" not in results[0].context and "Unrequested" not in results[0].context
    assert results[0].context_kind == "provider_highlights"
    assert results[1].context_kind == "navigation" and not results[1].context


def test_pathological_highlights_are_visible_as_omitted_navigation():
    size = exa.DISCOVERY_CONTEXT_SAFETY_LIMIT + 1
    result = exa.search_exa("query", api_key="offline", post=lambda *a, **k: Response({  # pragma: allowlist secret
        "results": [{"url": "https://example.test/large", "highlights": ["x" * size]}],
    }))[0]
    assert result.context_omitted_characters == size
    assert result.context_kind == "navigation" and "xxx" not in result.context


def test_contents_uses_full_fresh_text_and_exact_requested_identity():
    calls = []
    url = "https://example.test/source"
    body = "  Publication date: 26 March 2026\nActual source.  "

    def post(endpoint, **kwargs):
        calls.append((endpoint, kwargs["json"]))
        return Response({"results": [{"url": "https://example.test/wrong", "text": "wrong source"},
                                     {"id": url, "url": url, "text": body, "summary": "Generated"}]})

    result = exa.fetch_exa(url, api_key="offline", post=post)  # pragma: allowlist secret
    assert result == exa.FetchedMaterial(url, body)
    assert calls == [(exa.EXA_CONTENTS_URL, {"ids": [url], "text": {"verbosity": "full"}, "highlights": False, "maxAgeHours": 0})]


@pytest.mark.parametrize("payload", [
    {"results": [{"url": "https://example.test/other", "text": "wrong identity"}]},
    {"results": [{"url": "https://example.test/source", "summary": "Only generated material"}]},
    {"results": [], "statuses": [{"status": "error", "error": {"tag": "CRAWL_NOT_FOUND"}}]},
])
def test_missing_or_unrelated_contents_cannot_be_admitted(payload):
    with pytest.raises(exa.ExaTransportError, match="contents_material_unavailable"):
        exa.fetch_exa("https://example.test/source", api_key="offline", post=lambda *a, **k: Response(payload))  # pragma: allowlist secret


def test_transport_errors_do_not_expose_provider_details():
    with pytest.raises(exa.ExaTransportError, match="^exa_transport_failed$"):
        exa.search_exa("query", api_key="offline", post=lambda *a, **k: Response({}, OSError("private provider detail")))  # pragma: allowlist secret


def test_missing_configuration(monkeypatch):
    monkeypatch.delenv(exa.EXA_API_KEY_ENV, raising=False)
    with pytest.raises(exa.ExaTransportError, match="exa_configuration_missing"):
        exa.search_exa("query")
