from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.cost_accounting import CostAccumulator
from core.followup import MemorySearchResult, run_web_retrieval
from core.pipeline import fetch_linkup_precision_block, process_search_queries
from core.provider_diagnostics import (
    QUERY_PREVIEW_MAX_CHARS,
    build_provider_attempt_diagnostic,
    provider_diagnostics_payload,
)


def _result(url: str = "https://example.com/a") -> dict[str, object]:
    text = "Synthetic provider evidence. " * 12
    return {
        "title": "Synthetic result",
        "url": url,
        "snippet": text,
        "raw_content": text,
        "domain": "example.com",
        "credibility": 3,
    }


def test_tavily_main_retrieval_success_emits_provider_diagnostics_and_summary() -> None:
    diagnostics: list[dict[str, object]] = []
    long_query = "synthetic Tavily query " + ("x" * 400)

    with patch("core.pipeline.search_web_results", return_value=([_result()], ["https://example.com/img.jpg"])):
        passages = process_search_queries(
            [long_query],
            "general",
            "low",
            "basic",
            6,
            [],
            [],
            None,
            set(),
            set(),
            "OpenAI",
            "text-embedding-3-small",
            "http://localhost",
            lambda *_args, **_kwargs: [],
            lambda *_args, **_kwargs: [],
            status_container=MagicMock(),
            search_providers=["tavily"],
            provider_diagnostics=diagnostics,
            provider_role="main_retrieval",
            iteration=1,
        )

    assert passages
    assert len(diagnostics) == 1
    attempt = diagnostics[0]
    assert attempt["provider"] == "tavily"
    assert attempt["provider_role"] == "main_retrieval"
    assert attempt["depth"] == "basic"
    assert attempt["output_type"] == "searchResults"
    assert attempt["max_results"] == 6
    assert attempt["raw_content_requested"] is True
    assert attempt["success"] is True
    assert attempt["failure_type"] is None
    assert attempt["result_count"] == 1
    assert attempt["new_url_count"] == 1
    assert attempt["accepted_url_count"] == 1
    assert attempt["provider_overlap_diagnostics_available"] is True
    assert attempt["raw_url_count"] == 1
    assert attempt["raw_unique_url_count"] == 1
    assert attempt["raw_url_overlap_count"] == 0
    assert attempt["raw_domain_count"] == 1
    assert attempt["raw_domain_overlap_count"] == 0
    assert attempt["accepted_url_overlap_count"] == 0
    assert attempt["accepted_domain_count"] == 1
    assert attempt["new_domain_count"] == 1
    assert attempt["new_source_count"] == 1
    assert len(str(attempt["query_preview"])) == QUERY_PREVIEW_MAX_CHARS

    payload = provider_diagnostics_payload(diagnostics)
    assert payload["provider_successful_attempts_by_provider"] == {"tavily": 1}
    assert payload["provider_failed_attempts_by_provider"] == {}
    assert payload["provider_attempts_by_role"] == {"main_retrieval": 1}
    assert payload["provider_shadow_cost_estimate_available"] is False
    assert payload["provider_estimated_cost_usd"] is None


def test_linkup_precision_sourced_answer_diagnostic_flags_deep_answer_endpoint() -> None:
    diagnostics: list[dict[str, object]] = []
    sourced_results = [
        {
            "title": "Primary source",
            "url": "https://example.com/source",
            "raw_content": "Synthetic sourced answer.",
        }
    ]

    with patch("core.pipeline.search_linkup_results", return_value=(sourced_results, [])):
        block = fetch_linkup_precision_block(
            core_topic="synthetic precision topic",
            intent="general",
            complexity="high",
            include_domains=[],
            exclude_domains=[],
            provider_diagnostics=diagnostics,
        )

    assert "LINKUP PRECISION CONTEXT" in block
    assert len(diagnostics) == 1
    attempt = diagnostics[0]
    assert attempt["provider"] == "linkup"
    assert attempt["provider_role"] == "linkup_precision_sourced_answer"
    assert attempt["depth"] == "deep"
    assert attempt["output_type"] == "sourcedAnswer"
    assert attempt["answer_endpoint_used"] is True
    assert attempt["raw_content_requested"] is True
    assert attempt["success"] is True
    assert attempt["result_count"] == 1


def test_followup_search_records_provider_depth_and_max_results() -> None:
    memory = MemorySearchResult(
        sources={},
        next_source_id=1,
        conversation_history="",
        query_embedding=None,
        existing_evidence_block="",
        needs_search=True,
        followup_queries=["synthetic follow-up query"],
    )

    with patch.dict("os.environ", {}, clear=True):
        with patch("core.pipeline.search_web_results", return_value=([_result()], [])):
            web = run_web_retrieval(
                memory_result=memory,
                session={},
                intent="general",
                complexity="medium",
                fu_params={"search_depth": "advanced", "max_results": 3, "top_passage_count": 2},
                include_domains=[],
                exclude_domains=[],
                embed_provider="OpenAI",
                embed_model="text-embedding-3-small",
                local_url="",
                embed_texts=lambda *_args, **_kwargs: [],
                compute_similarities=lambda *_args, **_kwargs: [],
                search_fn=process_search_queries,
            )

    assert web.search_ran is True
    assert web.new_passages
    assert len(web.provider_diagnostics) == 1
    attempt = web.provider_diagnostics[0]
    assert attempt["provider"] == "tavily"
    assert attempt["provider_role"] == "chat_followup_search"
    assert attempt["depth"] == "advanced"
    assert attempt["max_results"] == 3


def test_provider_cost_shadow_fields_do_not_mutate_cost_accumulator() -> None:
    accumulator = CostAccumulator()
    accumulator.record_model_call(
        phase="model",
        model="gpt-5.4-mini",
        input_tokens=1000,
        output_tokens=500,
    )
    before = accumulator.snapshot()["total_cost_usd"]

    payload = provider_diagnostics_payload(
        [
            build_provider_attempt_diagnostic(
                provider="tavily",
                provider_role="main_retrieval",
                cost_phase="retrieval",
                query="synthetic",
            )
        ]
    )

    assert accumulator.snapshot()["total_cost_usd"] == before
    assert payload["provider_shadow_cost_estimate_available"] is False
    assert payload["provider_estimated_cost_usd"] is None


def test_provider_failure_diagnostics_do_not_change_returned_passages() -> None:
    diagnostics: list[dict[str, object]] = []

    with patch.dict("os.environ", {"LINKUP_API_KEY": "test-placeholder"}, clear=False):  # pragma: allowlist secret
        with patch("core.pipeline.search_web_results", return_value=([_result("https://example.com/ok")], [])):
            with patch("core.pipeline.search_linkup_results", side_effect=RuntimeError("linkup down")):
                passages = process_search_queries(
                    ["synthetic query"],
                    "general",
                    "medium",
                    "advanced",
                    6,
                    [],
                    [],
                    None,
                    set(),
                    set(),
                    "OpenAI",
                    "text-embedding-3-small",
                    "http://localhost",
                    lambda *_args, **_kwargs: [],
                    lambda *_args, **_kwargs: [],
                    status_container=MagicMock(),
                    search_providers=["tavily", "linkup"],
                    provider_diagnostics=diagnostics,
                    provider_role="main_retrieval",
                    iteration=1,
                )

    assert [passage["url"] for passage in passages] == ["https://example.com/ok"]
    failures = [attempt for attempt in diagnostics if attempt["success"] is False]
    successes = [attempt for attempt in diagnostics if attempt["success"] is True]
    assert len(failures) == 1
    assert failures[0]["provider"] == "linkup"
    assert failures[0]["failure_type"] == "RuntimeError"
    assert failures[0]["provider_overlap_diagnostics_available"] is False
    assert failures[0]["raw_url_count"] == 0
    assert failures[0]["new_source_count"] == 0
    assert len(successes) == 1
    assert successes[0]["provider"] == "tavily"


def test_exa_empty_results_are_successful_no_results_not_provider_failure() -> None:
    diagnostics: list[dict[str, object]] = []

    with patch.dict("os.environ", {"EXA_API_KEY": "test-placeholder"}, clear=False):  # pragma: allowlist secret
        with patch("core.pipeline.search_exa_results", return_value=([], [])):
            passages = process_search_queries(
                ["synthetic empty exa query"],
                "general",
                "medium",
                "advanced",
                6,
                [],
                [],
                None,
                set(),
                set(),
                "OpenAI",
                "text-embedding-3-small",
                "http://localhost",
                lambda *_args, **_kwargs: [],
                lambda *_args, **_kwargs: [],
                status_container=MagicMock(),
                search_providers=["exa"],
                provider_diagnostics=diagnostics,
                provider_role="main_retrieval",
                iteration=1,
            )

    assert passages == []
    assert len(diagnostics) == 1
    assert diagnostics[0]["provider"] == "exa"
    assert diagnostics[0]["success"] is True
    assert diagnostics[0]["failure_type"] is None
    assert diagnostics[0]["result_count"] == 0
    assert diagnostics[0]["provider_overlap_diagnostics_available"] is True
    assert diagnostics[0]["raw_url_count"] == 0
    assert diagnostics[0]["raw_unique_url_count"] == 0
    assert diagnostics[0]["raw_url_overlap_count"] == 0
    assert diagnostics[0]["accepted_url_count"] == 0
    assert diagnostics[0]["new_source_count"] == 0


def test_repeated_raw_urls_emit_overlap_yield_counts_without_duplicate_passages() -> None:
    diagnostics: list[dict[str, object]] = []
    repeated = "https://example.com/repeated"
    fresh = "https://second.example.com/fresh"

    with patch("core.pipeline.search_web_results", return_value=([_result(repeated), _result(repeated), _result(fresh)], [])):
        passages = process_search_queries(
            ["synthetic duplicate raw URL query"],
            "general",
            "low",
            "basic",
            6,
            [],
            [],
            None,
            set(),
            set(),
            "OpenAI",
            "text-embedding-3-small",
            "http://localhost",
            lambda *_args, **_kwargs: [],
            lambda *_args, **_kwargs: [],
            status_container=MagicMock(),
            search_providers=["tavily"],
            provider_diagnostics=diagnostics,
            provider_role="main_retrieval",
            iteration=1,
        )

    assert [passage["url"] for passage in passages] == [repeated, fresh]
    attempt = diagnostics[0]
    assert attempt["raw_url_count"] == 3
    assert attempt["raw_unique_url_count"] == 2
    assert attempt["accepted_url_count"] == 2
    assert attempt["new_source_count"] == 2


def test_previously_seen_urls_emit_overlap_counts_without_duplicate_passages() -> None:
    diagnostics: list[dict[str, object]] = []
    seen_url = "https://seen.example.com/already"
    fresh_url = "https://fresh.example.com/new"
    seen_urls = {seen_url}

    with patch("core.pipeline.search_web_results", return_value=([_result(seen_url), _result(fresh_url)], [])):
        passages = process_search_queries(
            ["synthetic previously seen URL query"],
            "general",
            "low",
            "basic",
            6,
            [],
            [],
            None,
            seen_urls,
            set(),
            "OpenAI",
            "text-embedding-3-small",
            "http://localhost",
            lambda *_args, **_kwargs: [],
            lambda *_args, **_kwargs: [],
            status_container=MagicMock(),
            search_providers=["tavily"],
            provider_diagnostics=diagnostics,
            provider_role="main_retrieval",
            iteration=1,
        )

    assert [passage["url"] for passage in passages] == [fresh_url]
    assert seen_urls == {seen_url, fresh_url}
    attempt = diagnostics[0]
    assert attempt["raw_url_count"] == 2
    assert attempt["raw_unique_url_count"] == 2
    assert attempt["raw_url_overlap_count"] == 1
    assert attempt["raw_domain_overlap_count"] == 1
    assert attempt["accepted_url_overlap_count"] == 0
    assert attempt["accepted_url_count"] == 1
    assert attempt["accepted_domain_count"] == 1
    assert attempt["new_domain_count"] == 1
    assert attempt["new_source_count"] == 1


def test_query_similarity_metadata_is_optional_shadow_only() -> None:
    diagnostics: list[dict[str, object]] = []

    with patch("core.pipeline.search_web_results", return_value=([_result()], [])):
        process_search_queries(
            ["synthetic overlap query"],
            "general",
            "low",
            "basic",
            6,
            [],
            [],
            None,
            set(),
            set(),
            "OpenAI",
            "text-embedding-3-small",
            "http://localhost",
            lambda *_args, **_kwargs: [],
            lambda *_args, **_kwargs: [],
            status_container=MagicMock(),
            search_providers=["tavily"],
            provider_diagnostics=diagnostics,
            prior_queries_for_similarity=["synthetic overlap prior"],
            query_similarity_basis="previous_main_retrieval_iteration",
        )

    attempt = diagnostics[0]
    assert attempt["query_similarity_max"] > 0
    assert attempt["query_similarity_basis"] == "previous_main_retrieval_iteration"
