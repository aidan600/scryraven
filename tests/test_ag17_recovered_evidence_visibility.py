from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.run_config import RunConfig
from tests.test_source_class_recovery_trace import (
    _execution_event_from_log,
    _TraceHarness,
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _source(
    url: str,
    *,
    title: str = "Evidence source",
    text: str = "Evidence text.",
    source_tier: str = "secondary",
    score: float = 0.5,
) -> dict[str, Any]:
    return {
        "title": title,
        "url": url,
        "text": text,
        "score": score,
        "source_tier": source_tier,
    }


def _recovered_source(
    url: str,
    *,
    title: str = "Recovered source",
    text: str = "Recovered evidence text.",
    source_tier: str = "official",
    score: float = 0.1,
) -> dict[str, Any]:
    source = _source(
        url,
        title=title,
        text=text,
        source_tier=source_tier,
        score=score,
    )
    source["_provider_role"] = "source_class_recovery"
    source["retrieval_stage"] = "source_class_recovery"
    return source


def _lifecycle(
    missing_source_class: str,
    *,
    reason: str | None = None,
    used: bool = True,
    provider_role: str | None = "source_class_recovery",
    skip_reason: str | None = None,
    blockers: list[str] | None = None,
    attempt_count: int = 1,
    quality_status: str = "official_or_primary_found",
) -> dict[str, Any]:
    reason_prefix = {
        "official_current_rules": "answer_contract_official_gap",
        "legal_or_regulatory_text": "answer_contract_legal_text_gap",
        "current_primary_or_official": "answer_contract_current_primary_gap",
    }.get(missing_source_class, "answer_contract_official_gap")
    return {
        "active_source_class_recovery_used": used,
        "active_source_class_recovery_provider_role": provider_role,
        "active_source_class_recovery_reason": (
            reason or f"{reason_prefix}:{missing_source_class}"
        ),
        "active_source_class_recovery_skip_reason": skip_reason,
        "active_source_class_recovery_blockers": list(blockers or []),
        "active_source_class_recovery_missing_classes": [missing_source_class],
        "active_source_class_recovery_attempt_count": attempt_count,
        "recovery_source_quality_status": quality_status,
    }


def test_ag17_official_dot_source_is_appended_under_contract_gap() -> None:
    recovered = _recovered_source(
        "https://www.transportation.gov/briefing-room/current-rule",
        title="DOT official agency guidance",
        text="Official agency guidance explains the current rule and requirements.",
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[
            _source(
                "https://analysis.example/program",
                title="Secondary program analysis",
            )
        ],
        recovered_passages=[recovered],
        lifecycle_trace=_lifecycle("official_current_rules"),
        max_final_evidence=4,
    )

    trace = decision.to_trace_fields()
    assert final[-1]["url"] == recovered["url"]
    assert trace["recovered_visibility_considered"] is True
    assert trace["recovered_visibility_eligible"] is True
    assert trace["recovered_visibility_used"] is True
    assert trace["recovered_visibility_reason"] == "reserved_append"
    assert trace["recovered_visibility_reserved_count"] == 1
    assert trace["recovered_visibility_reserved_source_ids"] == [recovered["url"]]
    assert trace["recovered_visibility_reserved_source_classes"] == [
        "official_current_rules"
    ]


@pytest.mark.parametrize(
    ("url", "title", "text"),
    [
        (
            "https://www.federalregister.gov/documents/2026/01/01/example",
            "Federal Register final rule",
            "The Federal Register publishes final rule regulation text.",
        ),
        (
            "https://www.ecfr.gov/current/title-21/part-101",
            "eCFR current regulation",
            "The eCFR contains current Code of Federal Regulations text.",
        ),
        (
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title42/html/example.htm",
            "GovInfo statute compilation",
            "GovInfo provides official statute and regulation source text.",
        ),
    ],
)
def test_ag17_legal_regulatory_recovered_sources_are_eligible(
    url: str,
    title: str,
    text: str,
) -> None:
    recovered = _recovered_source(url, title=title, text=text)
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/legal")],
        recovered_passages=[recovered],
        lifecycle_trace=_lifecycle("legal_or_regulatory_text"),
        max_final_evidence=4,
    )

    assert final[-1]["url"] == url
    assert decision.used is True
    assert decision.recovered_source_class == "legal_or_regulatory_text"
    assert decision.missing_source_class == "legal_or_regulatory_text"


def test_ag17_current_primary_gap_accepts_current_official_primary_source() -> None:
    recovered = _recovered_source(
        "https://agency.gov/current/primary-statement",
        title="Agency current primary source statement",
        text=(
            "Official current primary-source statement with source text and "
            "agency guidance."
        ),
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/current-event")],
        recovered_passages=[recovered],
        lifecycle_trace=_lifecycle("current_primary_or_official"),
        max_final_evidence=4,
    )

    assert final[-1]["url"] == recovered["url"]
    assert decision.used is True
    assert decision.missing_source_class == "current_primary_or_official"
    assert decision.recovered_source_class in {
        "official_current_rules",
        "primary_source_documents",
    }


def test_ag17_already_visible_recovered_source_is_not_duplicated() -> None:
    recovered = _recovered_source(
        "https://agency.gov/current/rules",
        title="Agency current rules",
        text="Official current agency rule requirements.",
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[recovered],
        recovered_passages=[recovered],
        lifecycle_trace=_lifecycle("official_current_rules"),
        max_final_evidence=4,
    )

    assert [source["url"] for source in final] == [recovered["url"]]
    assert decision.used is False
    assert decision.reason == "already_visible_authority_satisfying"
    assert decision.dropped_source_ids_or_urls == (recovered["url"],)


@pytest.mark.parametrize(
    ("quality_status", "recovered", "expected_reason"),
    [
        (
            "secondary_only",
            [
                _recovered_source(
                    "https://apnews.com/article/example-rule",
                    title="News report about an agency rule",
                    text="A secondary report discusses what the agency said.",
                    source_tier="secondary",
                )
            ],
            "secondary_only",
        ),
        ("no_relevant_sources", [], "no_relevant_sources"),
        (
            "classification_mismatch",
            [
                _recovered_source(
                    "https://law.cornell.edu/wex/example",
                    title="Authority page without text",
                    text="General background with no legal or regulatory text.",
                    source_tier="unknown",
                )
            ],
            "classification_mismatch",
        ),
    ],
)
def test_ag17_quality_status_negative_controls_reserve_nothing(
    quality_status: str,
    recovered: list[dict[str, Any]],
    expected_reason: str,
) -> None:
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/item")],
        recovered_passages=recovered,
        lifecycle_trace=_lifecycle(
            "official_current_rules",
            quality_status=quality_status,
        ),
        max_final_evidence=4,
    )

    assert len(final) == 1
    assert decision.used is False
    assert decision.reason == expected_reason
    assert decision.drop_reason == expected_reason


def test_ag17_recommendation_legal_constraint_is_not_hijacked() -> None:
    recovered = _recovered_source(
        "https://agency.gov/tax-credit-rule",
        title="Agency tax credit rule",
        text="Official current agency rule requirements.",
    )
    _final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://reviews.example/charger")],
        recovered_passages=[recovered],
        lifecycle_trace=_lifecycle(
            "official_current_rules",
            reason="missing_expected_source_class:official_current_rules",
        ),
        max_final_evidence=4,
    )

    assert decision.used is False
    assert "reason_not_answer_contract_gap" in decision.blockers


def test_ag17_historical_archival_source_does_not_become_current_official() -> None:
    recovered = _recovered_source(
        "https://www.archives.gov/historical/program-rule",
        title="Historical archive of original program rule",
        text="Archive historical original text for an older program rule.",
    )
    _final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/history")],
        recovered_passages=[recovered],
        lifecycle_trace=_lifecycle("official_current_rules"),
        max_final_evidence=4,
    )

    assert decision.used is False
    assert decision.reason == "historical_or_archival_not_current"


@pytest.mark.parametrize(
    ("lifecycle", "expected_blocker"),
    [
        (
            _lifecycle(
                "official_current_rules",
                used=False,
                reason="not_recommended",
                provider_role=None,
                quality_status="unknown",
            ),
            "source_class_recovery_not_used",
        ),
        (
            _lifecycle(
                "social_signal",
                reason="social_provider_unavailable:social_signal",
                quality_status="unknown",
            ),
            "reason_not_answer_contract_gap",
        ),
        (
            _lifecycle(
                "official_current_rules",
                used=False,
                blockers=["blocked_by_weak_corpus_recovery"],
                quality_status="unknown",
            ),
            "blocked_by_weak_corpus_recovery",
        ),
        (
            _lifecycle(
                "official_current_rules",
                used=False,
                skip_reason="already_attempted",
                quality_status="unknown",
            ),
            "duplicate_attempt_blocked",
        ),
    ],
)
def test_ag17_non_active_social_weak_and_duplicate_controls_reserve_nothing(
    lifecycle: dict[str, Any],
    expected_blocker: str,
) -> None:
    recovered = _recovered_source(
        "https://agency.gov/current/rules",
        title="Agency current rules",
        text="Official current agency rule requirements.",
    )
    _final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_source("https://analysis.example/item")],
        recovered_passages=[recovered],
        lifecycle_trace=lifecycle,
        max_final_evidence=4,
    )

    assert decision.used is False
    assert expected_blocker in decision.blockers


def _top_score_filter(
    passages: list[dict[str, Any]],
    max_chunks: int,
    *_args: Any,
    **_kwargs: Any,
) -> list[dict[str, Any]]:
    return sorted(
        passages,
        key=lambda passage: passage.get("score", 0),
        reverse=True,
    )[:max_chunks]


def _run_visibility_case(
    tmp_path: Path,
    *,
    filter_top_evidence: Any = _top_score_filter,
    harness_cls: type[_TraceHarness] = _TraceHarness,
    **harness_kwargs: Any,
) -> tuple[Any, _TraceHarness, dict[str, Any]]:
    harness = harness_cls(tmp_path, **harness_kwargs)
    deps = harness.deps()
    deps.filter_top_evidence = filter_top_evidence
    deps.logger = logging.getLogger("test_ag17_recovered_visibility")
    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode="Balanced",
            current_date="2026-05-22",
            use_reasoning=False,
        ),
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )
    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")
    return outcome, harness, log_entry


class _BudgetExhaustionVisibilityHarness(_TraceHarness):
    def __init__(self, *args: Any, second_iteration_query: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.second_iteration_query = second_iteration_query

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return json.dumps(
                {
                    "is_sufficient": False,
                    "new_queries": [self.second_iteration_query],
                }
            )
        return super().ask_model(prompt, system_prompt, **kwargs)


def test_ag17_pipeline_reserves_recovered_official_source_at_final_cap(
    tmp_path: Path,
) -> None:
    outcome, harness, log_entry = _run_visibility_case(
        tmp_path,
        harness_cls=_BudgetExhaustionVisibilityHarness,
        query=(
            "What are the current official rules for Care Program eligibility "
            "in 2026?"
        ),
        core_topic="Care Program current official eligibility rules",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements secondary analysis",
        second_iteration_query="Care Program eligibility analysis deadlines",
        router_intent="regulatory",
        router_query_type="other",
        source_tiers=["secondary"] * 20,
        domains=[f"analysis{idx}.example" for idx in range(20)],
        recovery_source_tiers=["official"],
        recovery_domains=["transportation.gov"],
        recovery_scores=[0.01],
    )

    trace = outcome.execution_trace
    recovered_urls = [
        source["url"]
        for source in outcome.top_passages
        if source.get("retrieval_stage") == "source_class_recovery"
    ]
    assert len(outcome.top_passages) == 20
    assert recovered_urls == ["https://transportation.gov/official-recovery-0"]
    assert trace["recovered_visibility_considered"] is True
    assert trace["recovered_visibility_eligible"] is True
    assert trace["recovered_visibility_used"] is True
    assert trace["recovered_visibility_reason"] == "reserved_replace"
    assert trace["recovered_visibility_reserved_count"] == 1
    assert trace["recovered_visibility_reserved_source_ids"] == recovered_urls
    assert trace["recovered_visibility_reserved_source_classes"] == [
        "official_current_rules"
    ]
    assert trace["final_official_source_count"] >= 1
    handoff = trace["answer_contract_fulfillment_handoff"]
    assert not any(
        "official_current_rules" in item
        for item in handoff.get("unfulfilled_items", [])
    ), handoff.get("unfulfilled_items")
    assert harness.search_calls[2]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[2]["search_depth"] == "basic"
    assert harness.search_calls[2]["search_providers"] == trace["pass_providers"][-1]
    assert log_entry["execution_trace"]["recovered_visibility_used"] is True


def test_ag17_pipeline_secondary_only_recovery_is_not_reserved(
    tmp_path: Path,
) -> None:
    outcome, _harness, _log_entry = _run_visibility_case(
        tmp_path,
        harness_cls=_BudgetExhaustionVisibilityHarness,
        query=(
            "What are the current official rules for Care Program eligibility "
            "in 2026?"
        ),
        core_topic="Care Program current official eligibility rules",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements secondary analysis",
        second_iteration_query="Care Program eligibility analysis deadlines",
        router_intent="regulatory",
        router_query_type="other",
        source_tiers=["secondary"] * 20,
        domains=[f"analysis{idx}.example" for idx in range(20)],
        recovery_source_tiers=["secondary"],
        recovery_domains=["apnews.com"],
        recovery_scores=[0.01],
    )

    trace = outcome.execution_trace
    assert not any(
        source.get("retrieval_stage") == "source_class_recovery"
        for source in outcome.top_passages
    )
    assert trace["recovery_source_quality_status"] == "secondary_only"
    assert trace["recovered_visibility_used"] is False
    assert trace["recovered_visibility_drop_reason"] == "secondary_only"
    assert trace["recovered_visibility_reserved_count"] == 0
