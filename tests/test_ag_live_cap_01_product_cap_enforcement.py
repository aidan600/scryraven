from __future__ import annotations

from typing import Any

import pytest

import core.pipeline as pipeline
import core.pipeline_orchestrator as orchestrator
from core.cap_enforcement import RunCapExceeded, RunCapPolicy
from tests.helpers.offline_ordinary_pipeline import (
    OfflineOrdinaryPipelineHarness,
    run_offline_ordinary_pipeline,
    scrub_offline_runtime,
)


class CapHarness(OfflineOrdinaryPipelineHarness):
    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "title": "Official rule",
                "url": "https://example.test/official-rule",
                "text": (
                    "Official public documentation says the bounded default value "
                    "is alpha and includes enough evidence for a concise answer."
                ),
                "snippet": "The bounded default value is alpha.",
                "source_type": "official",
            }
        ]


def _harness(tmp_path: Any) -> CapHarness:
    return CapHarness(
        tmp_path=tmp_path,
        query="What is the official bounded default value?",
        core_topic="bounded default value",
        primary_entity="BoundedWidget",
        raw_author_response="The bounded default value is alpha.",
    )


def test_default_run_config_has_no_cap_policy() -> None:
    from core.run_config import RunConfig

    assert RunConfig(query="hello").cap_policy is None
    assert RunConfig(query="hello").source_custody_policy is None


def test_utilization_retry_disabled_by_cap_policy_records_trace(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrub_offline_runtime(monkeypatch)
    monkeypatch.setattr(orchestrator, "should_retry_retrieval", lambda _rate: True)
    monkeypatch.setattr(
        orchestrator,
        "build_disambiguation_queries",
        lambda *_args, **_kwargs: ["retry query"],
    )
    cap_policy = RunCapPolicy(
        max_search_dispatches=2,
        max_fetch_read_operations=3,
        max_author_model_calls=1,
        max_smart_search_judgment_model_calls=0,
        max_retries=0,
    )
    harness = _harness(tmp_path)

    _captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-25",
        session_id="session-cap-retry",
        run_id="run-cap-retry",
        capture_stages=(),
        cap_policy=cap_policy,
        provider_availability={"tavily": True},
    )

    assert all(
        call["provider_role"] != "disambiguation_retry"
        for call in harness.search_calls
    )
    cap_trace = outcome.execution_trace["cap_enforcement_trace"]
    assert cap_trace["search_dispatches"] == len(harness.search_calls)
    assert cap_trace["retries"] == 0
    assert "utilization_retry_disabled_by_cap_policy" in cap_trace["facts"]


def test_search_dispatch_cap_overflow_fails_before_extra_dispatch(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrub_offline_runtime(monkeypatch)
    cap_policy = RunCapPolicy(
        max_search_dispatches=0,
        max_fetch_read_operations=3,
        max_author_model_calls=1,
        max_smart_search_judgment_model_calls=0,
        max_retries=0,
    )
    harness = _harness(tmp_path)

    with pytest.raises(RunCapExceeded, match="search_dispatches cap exceeded"):
        run_offline_ordinary_pipeline(
            harness,
            monkeypatch,
            current_date="2026-06-25",
            session_id="session-cap-search",
            run_id="run-cap-search",
            capture_stages=(),
            cap_policy=cap_policy,
            provider_availability={"tavily": True},
        )

    assert harness.search_calls == []
    assert cap_policy.search_dispatches == 0


def test_author_model_cap_overflow_fails_before_author_call(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrub_offline_runtime(monkeypatch)
    cap_policy = RunCapPolicy(
        max_search_dispatches=2,
        max_fetch_read_operations=3,
        max_author_model_calls=0,
        max_smart_search_judgment_model_calls=0,
        max_retries=0,
    )
    harness = _harness(tmp_path)

    with pytest.raises(RunCapExceeded, match="author_model_calls cap exceeded"):
        run_offline_ordinary_pipeline(
            harness,
            monkeypatch,
            current_date="2026-06-25",
            session_id="session-cap-author",
            run_id="run-cap-author",
            capture_stages=(),
            cap_policy=cap_policy,
            provider_availability={"tavily": True},
        )

    assert harness.author_prompts == []
    assert cap_policy.author_model_calls == 0


def test_fetch_read_cap_overflow_fails_before_fetch_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetch_page_called = False

    def fake_search_web_results(*_args: Any, **_kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        return (
            [
                {
                    "title": "Official high credibility result",
                    "url": "https://www.irs.gov/example",
                    "domain": "irs.gov",
                    "credibility": 5,
                    "snippet": "Official source result.",
                }
            ],
            [],
        )

    def fake_fetch_page(_item: Any) -> dict[str, Any]:
        nonlocal fetch_page_called
        fetch_page_called = True
        return {}

    monkeypatch.setattr(pipeline, "search_web_results", fake_search_web_results)
    monkeypatch.setattr(pipeline, "fetch_page", fake_fetch_page)
    cap_policy = RunCapPolicy(
        max_search_dispatches=1,
        max_fetch_read_operations=0,
        max_author_model_calls=1,
        max_smart_search_judgment_model_calls=0,
        max_retries=0,
    )

    with pytest.raises(RunCapExceeded, match="fetch_read_operations cap exceeded"):
        pipeline.process_search_queries(
            ["official result"],
            "general",
            "high",
            "advanced",
            1,
            [],
            [],
            None,
            set(),
            set(),
            "offline-embed-provider",
            "offline-embed-model",
            None,
            lambda *_args, **_kwargs: [],
            lambda *_args, **_kwargs: [],
            search_providers=["tavily"],
            cap_policy=cap_policy,
        )

    assert fetch_page_called is False
    assert cap_policy.fetch_read_operations == 0
