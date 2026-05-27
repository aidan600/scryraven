from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.answer_contract_controller import (
    AnswerContractFamily,
    AnswerControllerActionName,
)
from core.answer_contract_runtime_handoff import (
    ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY,
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.run_controller import RunController
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
)
from tests.test_source_class_recovery_trace import _run_case

_MAX_HANDOFF_BYTES = 4_500
_PROTECTED_HANDOFF_MARKERS = (
    "controller_diagnostics",
    "planned_vs_observed",
    "task_ledger",
    "quantitative_packet",
    "quantitative_packet_v1",
    "economist_v1",
    "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
    "## QUANTITATIVE FRAMEWORK",
    "ECONOMIST FRAMEWORK",
    "source_bound_values",
    "calculations_requested",
    "provider_diagnostics",
    "provider_attempts_by_role",
    "raw_provider",
    "raw evidence dump",
    "raw prompt",
    "internal diagnostics",
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _recommendation(
    *,
    recommended: bool = True,
    missing: tuple[str, ...] = ("official_current_rules",),
    queries: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    recovery_queries = tuple(
        queries
        if queries is not None
        else (
            "official current rules",
            "official eligibility requirements",
        )
    )
    return {
        "source_class_recovery_recommended": recommended,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": list(missing if recommended else ()),
        "source_class_recovery_reason": (
            "missing_expected_source_class:" + ",".join(missing)
            if recommended
            else None
        ),
        "source_class_recovery_queries": list(recovery_queries if recommended else ()),
        "source_class_recovery_query_count": len(recovery_queries) if recommended else 0,
        "source_class_recovery_trigger_fields": ["query"] if recommended else [],
    }


def _lifecycle(
    *,
    recommendation: dict[str, Any] | None = None,
    source_tier_counts: dict[str, int] | None = None,
    corpus_state: str = "HEALTHY",
    corpus_weak: bool = False,
    weak_corpus_recovery_considered: bool = False,
    weak_corpus_recovery_used: bool = False,
) -> dict[str, Any]:
    counts = dict(source_tier_counts or {"secondary": 2})
    return record_source_class_recovery_lifecycle(
        RunController(),
        recommendation=recommendation if recommendation is not None else _recommendation(),
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": counts,
            "source_domain_counts": {"official.gov": counts.get("official", 0), "analysis.example": 2},
            "top_source_domains": [{"domain": "analysis.example", "count": 2}],
            "unique_source_domain_count": 2,
            "on_domain_source_count": 0,
            "off_domain_source_count": 2,
            "official_evidence_found": bool(counts.get("official")),
            "community_signal_found": bool(counts.get("social_or_forum")),
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        corpus_state=corpus_state,
        corpus_weak=corpus_weak,
        weak_corpus_recovery_considered=weak_corpus_recovery_considered,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=(
            "weak_corpus_recovery_used" if weak_corpus_recovery_used else None
        ),
        current_search_depth="basic",
        iteration_budget_available=True,
    )


def _evidence(
    *,
    title: str,
    url: str,
    source_tier: str = "secondary",
) -> tuple[dict[str, Any], ...]:
    return (
        {
            "source_id": 1,
            "title": title,
            "url": url,
            "text": "Fixture body text must not be copied into the handoff.",
            "source_tier": source_tier,
        },
    )


@dataclass(frozen=True)
class RuntimeValidationCase:
    name: str
    facts: RuntimeAnswerContractFacts
    expected_family: AnswerContractFamily
    expected_taken: tuple[AnswerControllerActionName, ...] = ()
    expected_skipped: tuple[AnswerControllerActionName, ...] = ()
    expected_unfulfilled: tuple[str, ...] = ()
    expected_social_summary_fragment: str | None = None
    expected_posture_fragment: str | None = None


def _runtime_validation_cases() -> tuple[RuntimeValidationCase, ...]:
    ai_act_recommendation = _recommendation(
        missing=("official_current_rules",),
        queries=(
            "EU AI Act GPAI provider official obligations timeline 2026",
            "European Commission AI Act general-purpose AI official obligations",
        ),
    )
    tax_not_recommended = _recommendation(recommended=False, missing=(), queries=())
    historical_recommendation = _recommendation(
        missing=("primary_or_archival", "historical_legal_text"),
        queries=(
            "EPA leaded gasoline phase-down original rule text",
            "Federal Register leaded gasoline phase-down amendments",
        ),
    )

    return (
        RuntimeValidationCase(
            name="current_official_rules_gap",
            facts=RuntimeAnswerContractFacts(
                query=(
                    "As of today, what are the current EU AI Act obligations and timeline "
                    "for general-purpose AI model providers, and what changes or enforcement "
                    "milestones matter in 2026?"
                ),
                intent="regulatory",
                report_type="general_research",
                query_type="other",
                mode="Balanced",
                current_date="2026-05-21",
                core_topic="EU AI Act general-purpose AI provider obligations",
                evidence_available=True,
                evidence_sufficient=False,
                source_tier_counts={"secondary": 2},
                source_class_recovery_telemetry=ai_act_recommendation,
                active_source_class_recovery_lifecycle=_lifecycle(
                    recommendation=ai_act_recommendation
                ),
                queries_by_iteration={"1": ["EU AI Act GPAI obligations 2026"]},
                final_top_evidence=_evidence(
                    title="Secondary AI Act explainer",
                    url="https://analysis.example/eu-ai-act",
                ),
                unfulfilled_obligations=("official_current_rules",),
            ),
            expected_family=AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT,
            expected_taken=(AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS,),
            expected_unfulfilled=("official_current_rules",),
            expected_posture_fragment="legal/regulatory",
        ),
        RuntimeValidationCase(
            name="developing_event_orientation",
            facts=RuntimeAnswerContractFacts(
                query=(
                    "What is currently happening with the European Commission's high-risk AI "
                    "guidelines under the AI Act, what is settled, and what remains uncertain?"
                ),
                intent="news",
                report_type="general_research",
                query_type="current_events",
                mode="Balanced",
                current_date="2026-05-21",
                core_topic="European Commission high-risk AI guidelines",
                evidence_available=True,
                evidence_sufficient=False,
                source_tier_counts={"official": 1, "secondary": 2},
                retrieval_stop_active_telemetry={
                    "retrieval_stop_active_available": True,
                    "retrieval_stop_active_decision": "stop_no_queries",
                    "retrieval_stop_active_reason": "no_resolving_update_available",
                    "retrieval_stop_active_blockers": ["no_resolving_update_available"],
                },
                queries_by_iteration={"1": ["European Commission high-risk AI guidelines"]},
                final_top_evidence=_evidence(
                    title="Commission guidance landing page",
                    url="https://official.gov/ai-guidelines",
                    source_tier="official",
                ),
                fulfilled_obligations=("identify known facts",),
                partial_obligations=("identify unsettled points",),
                unfulfilled_obligations=("settled official guidance status",),
            ),
            expected_family=AnswerContractFamily.DEVELOPING_EVENT_ORIENTATION,
            expected_taken=(AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,),
            expected_unfulfilled=("settled official guidance status",),
            expected_posture_fragment="caveats",
        ),
        RuntimeValidationCase(
            name="official_tax_rules_satisfied",
            facts=RuntimeAnswerContractFacts(
                query=(
                    "What are the current federal rules for claiming a tax credit for "
                    "installing an EV charger at home in 2026, and what deadlines or limits matter?"
                ),
                intent="regulatory",
                report_type="general_research",
                query_type="other",
                mode="Balanced",
                current_date="2026-05-21",
                core_topic="federal EV charger tax credit rules",
                evidence_available=True,
                evidence_sufficient=True,
                source_tier_counts={"official": 1, "secondary": 1},
                source_class_recovery_telemetry=tax_not_recommended,
                active_source_class_recovery_lifecycle=_lifecycle(
                    recommendation=tax_not_recommended,
                    source_tier_counts={"official": 1, "secondary": 1},
                ),
                final_top_evidence=_evidence(
                    title="IRS alternative fuel refueling property credit",
                    url="https://official.gov/irs-ev-credit",
                    source_tier="official",
                ),
                fulfilled_obligations=(
                    "identify relevant primary legal or regulatory text",
                    "distinguish text from interpretation",
                ),
            ),
            expected_family=AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT,
            expected_skipped=(AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS,),
            expected_posture_fragment="primary-text-grounded",
        ),
        RuntimeValidationCase(
            name="quantitative_comparison_satisfied",
            facts=RuntimeAnswerContractFacts(
                query=(
                    "A sandwich bread label says 90 calories per 35g, and an artisan loaf says "
                    "150 calories per 85g. Which is more calorie-dense, and what explains the difference?"
                ),
                intent="general",
                report_type="quantitative_comparison",
                query_type="comparison",
                mode="Balanced",
                current_date="2026-05-21",
                core_topic="bread calorie density comparison",
                evidence_available=True,
                evidence_sufficient=True,
                fulfilled_obligations=(
                    "identify variables and units",
                    "state assumptions",
                    "separate sourced values from calculations",
                ),
            ),
            expected_family=AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL,
            expected_posture_fragment="quantitative",
        ),
        RuntimeValidationCase(
            name="recommendation_social_optional",
            facts=RuntimeAnswerContractFacts(
                query=(
                    "For a developer choosing between Cursor and VS Code with GitHub Copilot "
                    "in 2026, what are the practical tradeoffs, and what user-experience evidence would matter?"
                ),
                intent="recommendation",
                report_type="general_research",
                query_type="product",
                mode="Balanced",
                current_date="2026-05-21",
                core_topic="Cursor versus VS Code with GitHub Copilot",
                evidence_available=True,
                evidence_sufficient=True,
                source_tier_counts={"official": 1, "secondary": 2},
                final_top_evidence=_evidence(
                    title="Editor feature comparison",
                    url="https://analysis.example/editor-comparison",
                ),
                fulfilled_obligations=(
                    "identify decision criteria",
                    "compare tradeoffs against user constraints",
                ),
            ),
            expected_family=AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT,
            expected_social_summary_fragment="relevant_optional",
            expected_posture_fragment="recommendation",
        ),
        RuntimeValidationCase(
            name="explicit_social_signal_partial",
            facts=RuntimeAnswerContractFacts(
                query=(
                    "What is Reddit or social media sentiment saying about Cursor's recent "
                    "agent features, and how much should I trust that signal?"
                ),
                intent="general",
                report_type="general_research",
                query_type="other",
                mode="Balanced",
                current_date="2026-05-21",
                core_topic="Cursor agent feature social sentiment",
                evidence_available=True,
                evidence_sufficient=False,
                source_tier_counts={"secondary": 2},
                final_top_evidence=_evidence(
                    title="Secondary article about Cursor agents",
                    url="https://analysis.example/cursor-agents",
                ),
                partial_obligations=("separate social sentiment from factual authority",),
                unfulfilled_obligations=("social_signal",),
                missing_information=("social signal provider unavailable in this runtime path",),
                warnings_to_analyst_or_author=(
                    "Social signal is central here; do not treat secondary commentary as social proof.",
                ),
            ),
            expected_family=AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER,
            expected_unfulfilled=("social_signal",),
            expected_social_summary_fragment="central",
            expected_posture_fragment="social signal unavailable",
        ),
        RuntimeValidationCase(
            name="weak_evidence_social_partial",
            facts=RuntimeAnswerContractFacts(
                query=(
                    "Is Bluesky overtaking X among journalists in 2026, and what evidence would "
                    "actually be needed to answer that responsibly?"
                ),
                intent="social sentiment",
                report_type="general_research",
                query_type="other",
                mode="Balanced",
                current_date="2026-05-21",
                core_topic="Bluesky versus X among journalists",
                evidence_available=True,
                evidence_sufficient=False,
                weak_corpus=True,
                weak_corpus_reason="scattered social/search snippets",
                source_tier_counts={"secondary": 2, "social_or_forum": 1},
                final_top_evidence=_evidence(
                    title="Partial social platform adoption commentary",
                    url="https://analysis.example/bluesky-x-journalists",
                ),
                partial_obligations=("separate social sentiment from factual authority",),
                unfulfilled_obligations=("stronger independent evidence",),
                missing_information=("representative journalist adoption data",),
            ),
            expected_family=AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER,
            expected_unfulfilled=("stronger independent evidence",),
            expected_social_summary_fragment="central",
            expected_posture_fragment="social signal unavailable",
        ),
        RuntimeValidationCase(
            name="historical_archival_gap",
            facts=RuntimeAnswerContractFacts(
                query=(
                    "What did the original U.S. leaded gasoline phase-down rules require, "
                    "and how did the requirements change over time?"
                ),
                intent="historical",
                report_type="general_research",
                query_type="other",
                mode="Balanced",
                current_date="2026-05-21",
                core_topic="original U.S. leaded gasoline phase-down rules",
                evidence_available=True,
                evidence_sufficient=False,
                source_tier_counts={"secondary": 2},
                source_class_recovery_telemetry=historical_recommendation,
                active_source_class_recovery_lifecycle=_lifecycle(
                    recommendation=historical_recommendation
                ),
                final_top_evidence=_evidence(
                    title="Secondary history of leaded gasoline phase-down",
                    url="https://analysis.example/leaded-gasoline",
                ),
                unfulfilled_obligations=("primary_or_archival", "historical_legal_text"),
            ),
            expected_family=AnswerContractFamily.HISTORICAL_OR_ARCHIVAL_ANSWER,
            expected_taken=(AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS,),
            expected_unfulfilled=("primary_or_archival", "historical_legal_text"),
            expected_posture_fragment="historical",
        ),
    )


def _assert_safe_and_compact(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    assert len(encoded.encode("utf-8")) <= _MAX_HANDOFF_BYTES
    assert len(payload.get("evidence_used") or []) <= 5
    for marker in _PROTECTED_HANDOFF_MARKERS:
        assert marker not in encoded
        assert marker.casefold() not in encoded.casefold()


@pytest.mark.parametrize("case", _runtime_validation_cases(), ids=lambda case: case.name)
def test_ag5_runtime_handoff_offline_replay_matrix(case: RuntimeValidationCase) -> None:
    result = build_runtime_answer_contract_handoff(case.facts)
    payload = result.execution_trace_fragment()[ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY]

    assert result.adapter_result.contract.family is case.expected_family
    assert payload["schema_version"] == "answer_contract_fulfillment_v1"
    _assert_safe_and_compact(payload)

    taken = tuple(
        AnswerControllerActionName(item["action_name"])
        for item in payload["actions_taken"]
    )
    skipped = tuple(
        AnswerControllerActionName(item["action_name"])
        for item in payload["actions_skipped_and_why"]
    )
    for action in case.expected_taken:
        assert action in taken
    for action in case.expected_skipped:
        assert action in skipped
    for item in case.expected_unfulfilled:
        assert item in payload["unfulfilled_items"]
    if case.expected_social_summary_fragment is not None:
        assert case.expected_social_summary_fragment in payload["social_signal_summary"]
    if case.expected_posture_fragment is not None:
        assert case.expected_posture_fragment in payload["final_answer_posture"]


def test_ag5_runtime_handoff_behavior_preservation_negative_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_outcome, active_harness, active_log = _run_case(
        tmp_path / "active",
        query="Explain how DNS caching works in ordinary web browsing.",
        core_topic="DNS caching",
        primary_entity="DNS caching",
        researcher_query="DNS caching explanation",
        router_query_type="concept",
    )

    class _DisabledHandoff:
        def execution_trace_fragment(self) -> dict[str, Any]:
            return {}

    def disabled_handoff(*_args: Any, **_kwargs: Any) -> _DisabledHandoff:
        return _DisabledHandoff()

    monkeypatch.setattr(
        orchestrator,
        "build_runtime_answer_contract_handoff",
        disabled_handoff,
    )
    baseline_outcome, baseline_harness, baseline_log = _run_case(
        tmp_path / "baseline",
        query="Explain how DNS caching works in ordinary web browsing.",
        core_topic="DNS caching",
        primary_entity="DNS caching",
        researcher_query="DNS caching explanation",
        router_query_type="concept",
    )

    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY in active_outcome.execution_trace
    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY in active_log["execution_trace"]
    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY not in baseline_outcome.execution_trace
    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY not in baseline_log["execution_trace"]
    assert active_harness.search_calls == baseline_harness.search_calls
    assert active_harness.author_prompts == baseline_harness.author_prompts
    assert active_outcome.report == baseline_outcome.report
    assert set(active_log) == set(baseline_log)
    assert (
        set(active_outcome.execution_trace) ^ set(baseline_outcome.execution_trace)
    ) <= {ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY}
    assert set(execution_jsonl_to_run_row(active_log) or {}) == set(RUN_COLUMNS)
    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY not in (
        execution_jsonl_to_run_row(active_log) or {}
    )

    handoff = active_outcome.execution_trace[ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY]
    _assert_safe_and_compact(handoff)
    taken_names = {action["action_name"] for action in handoff["actions_taken"]}
    assert AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS.value not in taken_names
    assert AnswerControllerActionName.RECOVER_WEAK_CORPUS.value not in taken_names
    assert AnswerControllerActionName.REQUEST_SOCIAL_SIGNAL_CHECK.value not in taken_names
    assert AnswerControllerActionName.RUN_SCRUTINEER_REVIEW.value not in taken_names
    assert active_harness.search_calls[0]["provider_role"] == "main_retrieval"
    assert_execution_trace_payload_contract(active_outcome.execution_trace)
    assert_execution_trace_payload_contract(active_log["execution_trace"])
