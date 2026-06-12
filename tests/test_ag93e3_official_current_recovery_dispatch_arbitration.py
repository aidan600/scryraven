from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.allocation_result_candidate_custody import (
    build_allocation_result_candidate_custody_projection,
)
from core.controller_provider_search_allocation import (
    BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
)
from core.controller_recovery_decision import (
    REQUEST_PROVIDER_SEARCH_REVIEW,
    STOP_INSUFFICIENT,
    build_controller_recovery_decision,
)
from core.evidence_ledger import (
    EvidenceLedger,
    SourceRequirementStatus,
    build_evidence_ledger_observation_from_runtime,
)
from core.run_controller import RunController
from core.source_class_recovery import build_source_class_recovery_recommendation
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)

_ROOT = Path(__file__).resolve().parents[1]


def _authority_recommendation(
    *,
    missing: list[str] | None = None,
    queries: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    missing_classes = list(missing or ["official_current_rules"])
    recovery_queries = list(
        queries
        or [
            "official current source agency benefit eligibility rule",
            "government agency current eligibility requirements",
        ]
    )
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": missing_classes,
        "source_class_recovery_reason": (
            reason
            or "official_canonical_recovery_query_acquisition:"
            + ",".join(missing_classes)
        ),
        "source_class_recovery_queries": recovery_queries,
        "source_class_recovery_query_count": len(recovery_queries),
        "source_class_recovery_trigger_fields": [
            "official_source_obligation_bridge",
            "official_canonical_recovery_query_acquisition",
        ],
    }


def _secondary_evidence_signals() -> dict[str, Any]:
    return {
        "source_tier_counts": {"secondary": 3},
        "source_domain_counts": {"news.example": 2, "analysis.example": 1},
        "top_source_domains": [{"domain": "news.example", "count": 2}],
        "unique_source_domain_count": 2,
        "official_evidence_found": False,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _record_strong_official_lifecycle(
    controller: RunController,
    *,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_skip_reason: str | None = (
        "blocked_by_weak_corpus_recovery"
    ),
    iteration_budget_available: bool = False,
) -> dict[str, Any]:
    return record_source_class_recovery_lifecycle(
        controller,
        recommendation=_authority_recommendation(),
        recommendation_evaluated=True,
        source_class_evidence_signals=_secondary_evidence_signals(),
        corpus_state="OFF_TOPIC",
        corpus_weak=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
        current_search_depth="basic",
        iteration_budget_available=iteration_budget_available,
        official_canonical_source_class_slot_available=True,
    )


def _runner_context(
    *,
    controller: RunController,
    lifecycle: dict[str, Any],
    decision: Any,
    process_search_queries: Any,
) -> SourceClassRecoveryRunnerContext:
    return SourceClassRecoveryRunnerContext(
        controller=controller,
        controller_recovery_decision=decision,
        lifecycle_trace=lifecycle,
        process_search_queries=process_search_queries,
        all_passages=[],
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[],
        seen_urls=set(),
        collected_images=set(),
        embed_provider="fixture",
        embed_model="fixture",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        search_providers=["offline-fixture"],
        exa_domain_filter=None,
        entity_hint="Agency Benefit",
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )


def test_ag93e3_request_provider_search_review_executes_bounded_allocation() -> None:
    controller = RunController()
    lifecycle = _record_strong_official_lifecycle(controller)
    lifecycle.update(
        {
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_result_count": 0,
            "candidate_return_status": "zero_candidates",
            "recovered_result_count": 0,
            "recovery_slot_available": False,
        }
    )
    decision = build_controller_recovery_decision(lifecycle)
    captured: dict[str, Any] = {}

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        search_depth: str,
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured["queries"] = list(queries)
        captured["search_depth"] = search_depth
        captured["provider_role"] = kwargs["provider_role"]
        return [
            {
                "provider_name": "offline-fixture",
                "title": "Agency current eligibility rule",
                "url": "https://agency.example/current-eligibility-rule",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
            }
        ]

    result = run_source_class_recovery_dispatch(
        _runner_context(
            controller=controller,
            lifecycle=lifecycle,
            decision=decision,
            process_search_queries=fake_search,
        )
    )

    assert decision.decision == REQUEST_PROVIDER_SEARCH_REVIEW
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is True
    assert result.provider_search_allocation.execution_attempted is True
    assert result.provider_search_allocation.executed is True
    assert captured == {
        "queries": [
            "official current source agency benefit eligibility rule",
            "government agency current eligibility requirements",
        ],
        "search_depth": "basic",
        "provider_role": "source_class_recovery",
    }
    packet = lifecycle[PROVIDER_SEARCH_ALLOCATION_TRACE_KEY]
    execution = packet[PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY]
    assert execution["bounded_profile"] == BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE
    assert execution["executed"] is True
    assert execution["execution_attempted"] is True
    assert execution["unexecutable_reason"] is None
    custody = build_allocation_result_candidate_custody_projection(lifecycle)
    assert custody["allocation_execution_authorized"] is True
    assert custody["allocation_execution_executed"] is True
    assert custody["allocation_result_count"] == 1


def test_ag93e3_weak_corpus_does_not_block_strong_official_obligation() -> None:
    controller = RunController()

    lifecycle = _record_strong_official_lifecycle(
        controller,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason="blocked_by_weak_corpus_recovery",
        iteration_budget_available=False,
    )

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_skip_reason"] is None
    assert "blocked_by_weak_corpus_recovery" not in lifecycle[
        "active_source_class_recovery_blockers"
    ]
    assert lifecycle["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert controller.snapshot_ledger()["retrieval_actions"][0]["provider_role"] == (
        "source_class_recovery"
    )


def test_ag93e4_access_id_missing_class_activates_weak_corpus_override() -> None:
    recommendation = build_source_class_recovery_recommendation(
        query=(
            "Do people need REAL ID or other acceptable identification for "
            "domestic flights now, and when did enforcement start?"
        ),
        current_date="2026-06-10",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic="acceptable identification for domestic flights",
        primary_entity="domestic flight identification requirements",
        anchor_packet=None,
        source_tier_counts={"secondary": 3},
        source_domain_counts={"news.example": 2, "analysis.example": 1},
        top_source_domains=[{"domain": "news.example", "count": 2}],
        official_evidence_found=False,
    )
    controller = RunController()

    lifecycle = record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals=_secondary_evidence_signals(),
        corpus_state="OFF_TOPIC",
        corpus_weak=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason="blocked_by_weak_corpus_recovery",
        current_search_depth="basic",
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=True,
    )

    assert recommendation["source_class_recovery_recommended"] is True
    assert recommendation["missing_expected_source_classes"] == [
        "official_current_rules"
    ]
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_skip_reason"] is None
    assert "blocked_by_weak_corpus_recovery" not in lifecycle[
        "active_source_class_recovery_blockers"
    ]
    envelope = lifecycle["active_source_class_recovery_action_envelope"]
    assert envelope["required_source_class"] == ["official_current_rules"]
    assert envelope["allowed_action"] is True
    assert envelope["obligation_status"] == "required"
    assert controller.snapshot_ledger()["retrieval_actions"][0]["provider_role"] == (
        "source_class_recovery"
    )


def test_ag93e3_hard_exhausted_budget_still_stops_insufficient() -> None:
    decision = build_controller_recovery_decision(
        {
            "required_source_classes": ["official_current_rules"],
            "unsatisfied_required_source_classes": ["official_current_rules"],
            "source_obligation_status": "official_current_required_unmet",
            "prior_recovery_attempt_count": 1,
            "max_recovery_attempts": 1,
            "candidate_return_status": "not_attempted",
            "recovery_slot_available": False,
        }
    )

    assert decision.decision == STOP_INSUFFICIENT
    assert decision.payload["decision_reason"] == (
        "recovery_budget_exhausted_obligation_unmet"
    )
    assert decision.provider_search_review_requested is False


def test_ag93e3_ordinary_explainer_does_not_trigger_official_allocation() -> None:
    recommendation = build_source_class_recovery_recommendation(
        query="Explain how composting works for a home garden.",
        current_date="2026-06-10",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic="home composting",
        primary_entity="composting",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"explainer.example": 2},
        top_source_domains=[{"domain": "explainer.example", "count": 2}],
        official_evidence_found=False,
    )
    controller = RunController()
    lifecycle = record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals=_secondary_evidence_signals(),
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=True,
    )
    decision = build_controller_recovery_decision(lifecycle)

    result = run_source_class_recovery_dispatch(
        _runner_context(
            controller=controller,
            lifecycle=lifecycle,
            decision=decision,
            process_search_queries=lambda *_args, **_kwargs: [],
        )
    )

    assert recommendation["source_class_recovery_recommended"] is False
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is False
    assert PROVIDER_SEARCH_ALLOCATION_TRACE_KEY not in lifecycle
    custody = build_allocation_result_candidate_custody_projection(lifecycle)
    assert custody["allocation_execution_authorized"] is False
    assert custody["allocation_execution_executed"] is False


def _requirement() -> dict[str, Any]:
    return {
        "requirement_id": "official_current_source:agency_rule",
        "requirement_kind": "official_current",
        "origin_ref": "ag93e3_fixture",
        "required_source_class": "official_current_rules",
        "required_source_tier": "official",
        "required_currentness": "current",
    }


def _source(
    *,
    source_id: str,
    source_tier: str,
    source_class: str,
    currentness_signal: str,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "title": source_id.replace("-", " ").title(),
        "url": f"https://{source_id}.example/rule",
        "source_tier": source_tier,
        "source_class": source_class,
        "currentness_signal": currentness_signal,
        "readability_status": "readable",
    }


def _requirement_status(final_source: dict[str, Any]) -> str:
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        {
            "observation_id": "ag93e3-contract",
            "observation_source": "run_authority_contract",
            "requirements": [_requirement()],
        }
    )
    ledger.reduce_observation(
        build_evidence_ledger_observation_from_runtime(
            observation_id="ag93e3-final",
            observation_source="final_evidence_bundle",
            final_top_evidence=[final_source],
            final_evidence_selected=True,
        ).to_dict()
    )
    requirement = ledger.to_projection().to_dict()["source_requirements"][0]
    return str(requirement["status"])


def test_ag93e3_secondary_news_and_stale_evidence_do_not_satisfy_official_current() -> None:
    secondary_news = _source(
        source_id="news-context",
        source_tier="secondary",
        source_class="reputable_secondary",
        currentness_signal="current",
    )
    stale_official = _source(
        source_id="stale-official",
        source_tier="official",
        source_class="official_current_rules",
        currentness_signal="stale",
    )

    assert _requirement_status(secondary_news) == SourceRequirementStatus.UNSATISFIED.value
    assert _requirement_status(stale_official) == SourceRequirementStatus.UNSATISFIED.value


def test_ag93e3_core_dispatch_has_no_case_specific_real_id_logic() -> None:
    marker = re.compile(r"\breal[-\s]?id\b|\btsa\b|\bdhs\b", re.IGNORECASE)
    for path in (
        _ROOT / "core" / "source_class_recovery.py",
        _ROOT / "core" / "source_class_recovery_controller.py",
        _ROOT / "core" / "controller_recovery_decision.py",
        _ROOT / "core" / "controller_provider_search_allocation.py",
        _ROOT / "core" / "source_class_recovery_runner.py",
    ):
        assert marker.search(path.read_text(encoding="utf-8")) is None
