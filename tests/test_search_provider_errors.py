"""Sprint 3: retrieval provider failures write execution_log-style events (timeout vs provider_error)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests


def test_process_search_queries_logs_provider_error_on_search_failure() -> None:
    from core.pipeline import process_search_queries

    status = MagicMock()
    with patch("core.pipeline.search_web_results", side_effect=ValueError("tavily down")):
        with patch("core.pipeline.log_provider_error") as log_err:
            with patch("core.pipeline.log_retrieval_timeout") as log_to:
                process_search_queries(
                    ["my query"],
                    "general",
                    "low",
                    "basic",
                    6,
                    [],
                    [],
                    [0.0, 1.0],
                    set(),
                    set(),
                    "OpenAI",
                    "text-embedding-3-small",
                    "http://localhost",
                    lambda *a, **k: [[0.0]],
                    lambda *a, **k: None,
                    status_container=status,
                    search_providers=["tavily"],
                )
                log_err.assert_called_once()
                assert log_err.call_args.kwargs["provider"] == "tavily"
                assert "tavily down" in log_err.call_args.kwargs["error"]
                log_to.assert_not_called()


def test_process_search_queries_logs_retrieval_timeout_on_requests_timeout() -> None:
    from core.pipeline import process_search_queries

    status = MagicMock()
    with patch("core.pipeline.search_web_results", side_effect=requests.exceptions.ReadTimeout()):
        with patch("core.pipeline.log_provider_error") as log_err:
            with patch("core.pipeline.log_retrieval_timeout") as log_to:
                process_search_queries(
                    ["slow"],
                    "general",
                    "low",
                    "basic",
                    6,
                    [],
                    [],
                    [0.0, 1.0],
                    set(),
                    set(),
                    "OpenAI",
                    "text-embedding-3-small",
                    "http://localhost",
                    lambda *a, **k: [[0.0]],
                    lambda *a, **k: None,
                    status_container=status,
                    search_providers=["tavily"],
                )
                log_to.assert_called_once()
                assert log_to.call_args.kwargs["provider"] == "tavily"
                log_err.assert_not_called()


def test_process_search_queries_without_completed_route_performs_zero_transport() -> None:
    from core.pipeline import process_search_queries

    status = MagicMock()
    with patch.dict(
        "os.environ",
        {"LINKUP_API_KEY": "linkup-test-key", "EXA_API_KEY": "exa-test-key"},  # pragma: allowlist secret
        clear=False,
    ):
        with patch("core.pipeline.search_web_results", return_value=([], [])) as tavily:
            with patch("core.pipeline.search_exa_results", return_value=([], [])) as exa:
                with patch("core.pipeline.search_linkup_results") as linkup:
                    process_search_queries(
                        ["balanced query"],
                        "general",
                        "medium",
                        "advanced",
                        6,
                        [],
                        [],
                        [0.0, 1.0],
                        set(),
                        set(),
                        "OpenAI",
                        "text-embedding-3-small",
                        "http://localhost",
                        lambda *a, **k: [[0.0]],
                        lambda *a, **k: None,
                        status_container=status,
                        search_providers=None,
                    )
                    tavily.assert_not_called()
                    exa.assert_not_called()
                    linkup.assert_not_called()


def test_search_exa_logs_provider_error_on_exception() -> None:
    from core.search_providers import search_exa_results

    with patch.dict("os.environ", {"EXA_API_KEY": "test-placeholder-not-real"}, clear=False):  # pragma: allowlist secret
        with patch("core.search_providers.get_exa_client") as gc:
            mock_exa = MagicMock()
            mock_exa.search_and_contents.side_effect = RuntimeError("exa api error")
            gc.return_value = mock_exa
            with patch("core.search_providers.log_provider_error") as log_pe:
                results, imgs = search_exa_results("q", intent="general", max_results=3)
                assert results == []
                assert imgs == []
                log_pe.assert_called_once()
                assert log_pe.call_args.kwargs["provider"] == "exa"
                assert "exa api error" in log_pe.call_args.kwargs["error"]


def test_brave_reconnaissance_returns_empty_and_logs_provider_error_on_http_error() -> None:
    import httpx

    from core.search_providers import brave_reconnaissance

    with patch.dict("os.environ", {"BRAVE_API_KEY": "k"}, clear=False):
        with patch("httpx.get") as hg:
            hg.side_effect = httpx.HTTPError("network")
            with patch("core.search_providers.log_provider_error") as log_pe:
                with patch("core.search_providers.log_retrieval_timeout") as log_to:
                    out = brave_reconnaissance("entity query", num_results=3)
                    assert out == []
                    log_pe.assert_called_once()
                    assert log_pe.call_args.kwargs["provider"] == "brave"
                    log_to.assert_not_called()


def test_brave_reconnaissance_timeout_logs_retrieval_timeout_not_provider_error() -> None:
    import httpx

    from core.search_providers import brave_reconnaissance

    with patch.dict("os.environ", {"BRAVE_API_KEY": "k"}, clear=False):
        with patch("httpx.get") as hg:
            hg.side_effect = httpx.ReadTimeout("t")
            with patch("core.search_providers.log_provider_error") as log_pe:
                with patch("core.search_providers.log_retrieval_timeout") as log_to:
                    assert brave_reconnaissance("q") == []
                    log_to.assert_called_once()
                    assert log_to.call_args.kwargs["provider"] == "brave"
                    log_pe.assert_not_called()


def test_fetch_linkup_precision_block_logs_provider_error() -> None:
    from core.pipeline import fetch_linkup_precision_block

    with patch("core.pipeline.search_linkup_results", side_effect=ConnectionError("offline")):
        with patch("core.pipeline.log_provider_error") as log_pe:
            out = fetch_linkup_precision_block(
                core_topic="topic here",
                intent="general",
                complexity="high",
                include_domains=[],
                exclude_domains=[],
            )
            assert out == ""
            log_pe.assert_called_once()
            assert log_pe.call_args.kwargs["provider"] == "linkup"
