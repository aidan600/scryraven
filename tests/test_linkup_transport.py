"""Offline coverage for the narrow Linkup transport donors."""

from __future__ import annotations

from typing import Any

import pytest

from core import linkup_transport as linkup


class _Response:
    def __init__(self, payload: Any, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def json(self) -> Any:
        return self.payload


def test_search_preserves_full_navigation_context() -> None:
    calls: list[dict[str, Any]] = []
    long_context = " ".join(["context"] * 200)

    def post(url: str, **kwargs: Any) -> _Response:
        calls.append({"url": url, **kwargs})
        return _Response(
            {
                "results": [
                    {
                        "name": "  First title  ",
                        "url": " https://example.test/first ",
                        "content": f"  first line\n{long_context}",
                    },
                    {
                        "title": "Second title",
                        "url": "https://example.test/second",
                        "snippet": "second clue",
                    },
                    {"name": "No URL"},
                ]
            }
        )

    candidates = linkup.search_linkup(
        "  a question about sources  ",
        result_count=2,
        api_key="offline-test-key",  # pragma: allowlist secret
        timeout_seconds=12,
        post=post,
    )

    assert calls == [
        {
            "url": linkup.LINKUP_SEARCH_URL,
            "json": {
                "q": "a question about sources",
                "depth": "standard",
                "outputType": "searchResults",
                "maxResults": 2,
            },
            "headers": {
                "Authorization": "Bearer offline-test-key",
                "Content-Type": "application/json",
            },
            "timeout": 12.0,
        }
    ]
    assert candidates == [
        linkup.DiscoveryCandidate(
            title="First title",
            url="https://example.test/first",
            context=(
                "first line\n" + " ".join(["context"] * 200)
            ),
        ),
        linkup.DiscoveryCandidate(
            title="Second title",
            url="https://example.test/second",
            context="second clue",
        ),
    ]
    assert len(candidates[0].context) > 500


def test_pathological_context_is_explicitly_omitted_without_a_misleading_prefix():
    size = linkup.DISCOVERY_CONTEXT_SAFETY_LIMIT + 1
    result = linkup.search_linkup("query", api_key="offline-test-key", post=lambda *a, **k: _Response({  # pragma: allowlist secret
        "results": [{"url": "https://example.test/large", "content": "x" * size}],
    }))
    assert result[0].context_omitted_characters == size
    assert "omitted" in result[0].context and "xxx" not in result[0].context


def test_search_uses_environment_injected_credential_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(linkup.LINKUP_API_KEY_ENV, "offline-env-key")
    captured: dict[str, Any] = {}

    def post(url: str, **kwargs: Any) -> _Response:
        captured.update({"url": url, **kwargs})
        return _Response({"results": []})

    assert linkup.search_linkup("question", result_count=1, post=post) == []
    assert captured["headers"]["Authorization"] == "Bearer offline-env-key"


@pytest.mark.parametrize(
    "failure",
    [
        OSError("offline transport failure"),
        ValueError("offline response failure"),
    ],
)
def test_search_reports_ordinary_transport_and_response_failure(
    failure: Exception,
) -> None:
    def post(_url: str, **_kwargs: Any) -> _Response:
        return _Response({}, error=failure)

    with pytest.raises(
        linkup.LinkupTransportError,
        match="Linkup search transport or response handling failed",
    ):
        linkup.search_linkup(
            "question", api_key="offline-test-key",  # pragma: allowlist secret
            post=post,
        )


def test_fetch_builds_selected_url_request_and_associates_readable_material() -> None:
    calls: list[dict[str, Any]] = []
    selected_url = "https://example.test/selected"

    def post(url: str, **kwargs: Any) -> _Response:
        calls.append({"url": url, **kwargs})
        return _Response(
            {
                "url": "https://example.test/selected",
                "title": "Readable page",
                "markdown": "Readable returned representation.",
            }
        )

    material = linkup.fetch_linkup(
        selected_url,
        api_key="offline-test-key",  # pragma: allowlist secret
        timeout_seconds=9,
        post=post,
    )

    assert calls == [
        {
            "url": linkup.LINKUP_FETCH_URL,
            "json": {"url": selected_url},
            "headers": {
                "Authorization": "Bearer offline-test-key",
                "Content-Type": "application/json",
            },
            "timeout": 9.0,
        }
    ]
    assert material == linkup.FetchedMaterial(
        requested_url=selected_url,
        readable_text="Readable returned representation.",
    )


def test_fetch_accepts_readable_content_fallback() -> None:
    def post(_url: str, **_kwargs: Any) -> _Response:
        return _Response({"content": "Readable content fallback."})

    material = linkup.fetch_linkup(
        "https://example.test/fallback",
        api_key="offline-test-key",  # pragma: allowlist secret
        post=post,
    )

    assert material.readable_text == "Readable content fallback."


def test_fetch_reports_failure_and_does_not_require_control_plane_state() -> None:
    def post(_url: str, **_kwargs: Any) -> _Response:
        return _Response({"markdown": ""})

    with pytest.raises(
        linkup.LinkupTransportError,
        match="no readable material",
    ):
        linkup.fetch_linkup(
            "https://example.test/empty",
            api_key="offline-test-key",  # pragma: allowlist secret
            post=post,
        )


def test_missing_credential_is_reported_before_transport() -> None:
    called = False

    def post(_url: str, **_kwargs: Any) -> _Response:
        nonlocal called
        called = True
        return _Response({})

    with pytest.raises(linkup.LinkupTransportError, match="not configured"):
        linkup.search_linkup("question", post=post)
    assert called is False
