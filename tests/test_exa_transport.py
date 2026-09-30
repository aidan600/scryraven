"""The Exa path preserves source text and excludes generated outputs."""
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
    assert calls[0] == (exa.EXA_SEARCH_URL, {
        "json": {
            "query": "meaning sought", "type": "auto", "numResults": 6,
            "contents": {"text": False, "highlights": {
                "query": "meaning sought", "dynamic": True, "verbosity": "high",
            }},
        },
        "headers": {
            "x-api-key": "offline-test-key", "Content-Type": "application/json",
            "Exa-Beta": "dynamic-highlights-2026-08-28",
        },
        "timeout": exa.DEFAULT_TIMEOUT_SECONDS,
    })
    assert results[0].context == (
        passages[0] + "\n\n[Separate provider highlight; intervening context omitted]\n\n" + passages[1]
    )
    assert "Generated" not in results[0].context and "Unrequested" not in results[0].context
    assert results[0].context_kind == "provider_highlights"
    assert results[1].context_kind == "navigation" and not results[1].context


def test_search_uses_requested_result_count_and_preserves_six_result_order():
    query = "specific question"
    calls = []
    rows = [{"url": f"https://example.test/{i}", "title": f"Result {i}",
             "highlights": [f"Excerpt {i}"]} for i in range(6)]

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response({"results": rows})

    results = exa.search_exa(query, result_count=6, api_key="offline", post=post)  # pragma: allowlist secret
    assert calls[0][1]["json"]["numResults"] == 6
    assert [(r.url, r.title, r.context) for r in results] == [
        (row["url"], row["title"], row["highlights"][0]) for row in rows
    ]
    exa.search_exa(query, result_count=3, api_key="offline", post=post)  # pragma: allowlist secret
    assert calls[1][1]["json"]["numResults"] == 3


@pytest.mark.parametrize(("highlights", "context", "kind"), [
    (["A single selection."], "A single selection.", "provider_highlights"),
    (["First…\nline", "Second café…"],
     "First…\nline\n\n[Separate provider highlight; intervening context omitted]\n\nSecond café…",
     "provider_highlights"),
    ([], "", "navigation"),
    (None, "", "navigation"),
    ("malformed", "", "navigation"),
    ([None, 7, "  "], "", "navigation"),
])
def test_highlight_custody_and_navigation(highlights, context, kind):
    result = exa.search_exa("query", api_key="offline", post=lambda *a, **k: Response({  # pragma: allowlist secret
        "results": [{"url": "https://example.test/page", "title": "Page", "highlights": highlights}],
    }))[0]
    assert (result.url, result.title, result.context, result.context_kind) == (
        "https://example.test/page", "Page", context, kind,
    )


def test_uneven_highlight_lengths_have_no_fixed_per_result_cap():
    long_selection = "長" * 5_000
    results = exa.search_exa("query", api_key="offline", post=lambda *a, **k: Response({  # pragma: allowlist secret
        "results": [
            {"url": "https://example.test/short", "highlights": ["Short."]},
            {"url": "https://example.test/long", "highlights": [long_selection]},
        ],
    }))
    assert [r.context for r in results] == ["Short.", long_selection]
    assert all(r.context_kind == "provider_highlights" for r in results)


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
        calls.append((endpoint, kwargs))
        return Response({"results": [{"url": "https://example.test/wrong", "text": "wrong source"},
                                     {"id": url, "url": url, "text": body, "summary": "Generated"}]})

    result = exa.fetch_exa(url, api_key="offline", post=post)  # pragma: allowlist secret
    assert result == exa.FetchedMaterial(url, body)
    assert calls == [(exa.EXA_CONTENTS_URL, {
        "json": {"ids": [url], "text": {"verbosity": "full"}, "highlights": False, "maxAgeHours": 0},
        "headers": {"x-api-key": "offline", "Content-Type": "application/json"},
        "timeout": exa.DEFAULT_TIMEOUT_SECONDS,
    })]


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
