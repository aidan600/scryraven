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


def test_ordinary_dogfood_policy_allows_q1_like_search_judgment_work(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.ag_live_bound_01_support import AgLiveBoundCaps

    scrub_offline_runtime(monkeypatch)
    caps = AgLiveBoundCaps()
    assert caps.max_smart_search_judgment_model_calls is None
    assert caps.max_retries == 0
    cap_policy = caps.to_run_cap_policy()
    assert cap_policy.max_retries == 0
    harness = _harness(tmp_path)

    _captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-25",
        session_id="session-ordinary-q1",
        run_id="run-ordinary-q1",
        capture_stages=(),
        cap_policy=cap_policy,
        smart_search_judgment_model=True,
        provider_availability={"tavily": True},
    )

    assert harness.read_assessment_calls
    assert cap_policy.smart_search_judgment_model_calls >= 1
    assert outcome.report


def test_explicit_search_judgment_cap_still_fails_closed() -> None:
    from scripts.ag_live_bound_01_support import AgLiveBoundCaps

    cap_policy = AgLiveBoundCaps(
        max_smart_search_judgment_model_calls=0
    ).to_run_cap_policy()

    with pytest.raises(
        RunCapExceeded,
        match="smart_search_judgment_model_calls cap exceeded",
    ):
        cap_policy.mark_smart_search_judgment_model_call()


def test_ordinary_dogfood_retry_authority_fails_closed() -> None:
    from scripts.ag_live_bound_01_support import AgLiveBoundCaps

    cap_policy = AgLiveBoundCaps().to_run_cap_policy()

    with pytest.raises(RunCapExceeded, match="retries cap exceeded"):
        cap_policy.mark_retry()


def test_explicit_retry_resource_cap_remains_available() -> None:
    from scripts.ag_live_bound_01_support import AgLiveBoundCaps

    caps = AgLiveBoundCaps(max_retries=2)
    assert caps.as_requested_dict()["max_retries"] == 2
    cap_policy = caps.to_run_cap_policy()

    cap_policy.mark_retry()
    cap_policy.mark_retry()
    with pytest.raises(RunCapExceeded, match="retries cap exceeded"):
        cap_policy.mark_retry()


def test_retired_utilization_retry_branch_does_not_claim_active_cap_evidence(
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

    assert all(call["provider_role"] != "disambiguation_retry" for call in harness.search_calls)
    cap_trace = outcome.execution_trace["cap_enforcement_trace"]
    assert cap_trace["search_dispatches"] == len(harness.search_calls)
    assert cap_trace["retries"] == 0
    assert "utilization_retry_disabled_by_cap_policy" not in cap_trace["facts"]
    assert cap_policy.bounded is False
    assert "physical" not in cap_trace


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


def test_retired_legacy_author_fixture_is_not_physical_cap_proof(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrub_offline_runtime(monkeypatch)
    cap_policy = RunCapPolicy(
        max_search_dispatches=2,
        max_fetch_read_operations=3,
        max_author_model_calls=0,
        max_retries=0,
    )
    harness = _harness(tmp_path)

    _captured, outcome = run_offline_ordinary_pipeline(
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
    assert cap_policy.bounded is False
    assert "physical" not in outcome.execution_trace["cap_enforcement_trace"]


def test_deep_discovery_uses_provider_material_without_fetch_read_cap_charge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_search_web_results(*_args: Any, **_kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
        return (
            [
                {
                    "title": "Official high credibility result",
                    "url": "https://www.irs.gov/example",
                    "domain": "irs.gov",
                    "credibility": 5,
                    "snippet": "Official provider-returned result. " * 10,
                    "raw_content": "Bounded provider-returned excerpt. " * 20,
                }
            ],
            [],
        )

    monkeypatch.setattr(pipeline, "search_web_results", fake_search_web_results)
    cap_policy = RunCapPolicy(
        max_search_dispatches=1,
        max_fetch_read_operations=0,
        max_author_model_calls=1,
        max_smart_search_judgment_model_calls=0,
        max_retries=0,
    )

    passages = pipeline.process_search_queries(
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
    )

    assert passages
    assert passages[0]["evidence_material_type"] == "snippet_only"
    assert passages[0]["discovery_material_type"] == "provider_returned_excerpt"
    assert passages[0]["separate_exact_url_transport_performed"] is False
    assert passages[0]["full_page_fetched"] is False
    assert cap_policy.fetch_read_operations == 0
