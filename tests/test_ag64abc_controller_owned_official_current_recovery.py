from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.controller_loop_spine import (
    RECOVER_WEAK_CORPUS,
    RESOLVE_CONFLICT,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    build_controller_loop_spine_result,
)
from core.official_canonical_recovery_execution_admission import (
    build_official_canonical_recovery_execution_admission,
)
from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.run_controller import RunController
from core.source_class_recovery import (
    build_official_source_recovery_domain_constraints,
    build_source_class_recovery_recommendation,
)
from core.source_class_recovery_controller import (
    SourceClassRecoveryControllerDecision,
    build_source_class_recovery_controller_input,
    decide_source_class_recovery,
)
from core.source_class_recovery_executor import execute_source_class_recovery_action
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_QUERY_ACQUISITION_PATH = (
    _ROOT / "core" / "official_canonical_recovery_query_acquisition.py"
)


def _recommendation(
    *,
    query: str = "What is the current IRS standard mileage rate for business use of a car in 2026?",
    missing: list[str] | None = None,
    queries: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    missing_classes = missing or ["official_current_rules"]
    recovery_queries = queries if queries is not None else [f"{query} official source"]
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": missing_classes,
        "source_class_recovery_reason": (
            reason or "official_canonical_recovery_query_acquisition:"
            + ",".join(missing_classes)
        ),
        "source_class_recovery_queries": recovery_queries,
        "source_class_recovery_query_count": len(recovery_queries),
        "source_class_recovery_trigger_fields": [
            "official_canonical_recovery_query_acquisition"
        ],
    }


def _irs_live_query() -> str:
    return (
        "What is the current IRS standard mileage rate for business use of a "
        "car in 2026, and what official source supports it?"
    )


def _controller_input(recommendation: dict[str, Any]) -> Any:
    return build_source_class_recovery_controller_input(
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"news.example": 2},
            "top_source_domains": [{"domain": "news.example", "count": 2}],
            "official_evidence_found": False,
            "raw_prompt": "must not leak",
            "provider_payload": "must not leak",
        },
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=True,
        prior_attempt_count=0,
    )


def _record_lifecycle(
    controller: RunController,
    recommendation: dict[str, Any],
) -> dict[str, Any]:
    return record_source_class_recovery_lifecycle(
        controller,
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={"source_tier_counts": {"secondary": 2}},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=True,
    )


def test_ag64a_controller_action_envelope_owns_official_current_recovery() -> None:
    decision = decide_source_class_recovery(_controller_input(_recommendation()))

    assert decision.decision is (
        SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
    )
    assert decision.action_envelope is not None
    envelope = decision.action_envelope.to_dict()
    assert envelope["action_type"] == "recover_missing_source_class"
    assert envelope["required_source_class"] == ["official_current_rules"]
    assert envelope["obligation_status"] == "required"
    assert envelope["current_evidence_status"] == "missing_required_source_class"
    assert envelope["allowed_action"] is True
    assert envelope["budget_attempt_context"] == {
        "attempt_count": 1,
        "current_search_depth": "basic",
        "provider_role": "source_class_recovery",
        "iteration_budget_available": False,
        "answer_contract_source_class_slot_available": False,
        "official_canonical_source_class_slot_available": True,
    }
    assert envelope["stop_posture_if_unmet"] == "stop_insufficient_with_caveat"
    assert "raw_prompt" not in str(envelope)
    assert "provider_payload" not in str(envelope)


def test_ag64a_lifecycle_and_executor_consume_controller_envelope() -> None:
    controller = RunController()
    lifecycle = _record_lifecycle(controller, _recommendation())
    action = controller.snapshot_ledger()["retrieval_actions"][0]

    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert action["metadata"]["controller_action_envelope"] == (
        lifecycle["active_source_class_recovery_action_envelope"]
    )

    def fake_search(
        _queries: list[str],
        _intent: str,
        _complexity: str,
        _search_depth: str,
        _results_per_query: int,
        _include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        seen_urls: set[str],
        _collected_images: set[str],
        *_args: Any,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        seen_urls.add("https://www.irs.gov/example")
        return [{"url": "https://www.irs.gov/example", "title": "IRS", "text": "Official"}]

    result = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=[],
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[0.0],
        seen_urls=set(),
        collected_images=set(),
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        search_providers=["tavily"],
        exa_domain_filter=None,
        entity_hint=None,
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )

    assert result["attempted"] is True
    assert lifecycle["active_source_class_recovery_execution_attempted"] is True


def test_ag64a_executor_rejects_recovery_action_without_envelope() -> None:
    controller = RunController()
    lifecycle = _record_lifecycle(controller, _recommendation())
    controller.state.recovery_action_records[0].metadata.pop(
        "controller_action_envelope"
    )
    controller.ledger.retrieval_actions[0].metadata.pop("controller_action_envelope")

    with pytest.raises(RuntimeError, match="missing controller envelope"):
        execute_source_class_recovery_action(
            controller,
            lifecycle_trace=lifecycle,
            process_search_queries=lambda *_args, **_kwargs: [],
            all_passages=[],
            intent="general",
            complexity="medium",
            results_per_query=5,
            include_domains=[],
            exclude_domains=[],
            query_embedding=[0.0],
            seen_urls=set(),
            collected_images=set(),
            embed_provider="OpenAI",
            embed_model="text-embedding-3-small",
            local_url="http://localhost",
            embed_texts=lambda *_args, **_kwargs: [],
            compute_similarities=lambda *_args, **_kwargs: [],
            status_container=object(),
            search_providers=["tavily"],
            exa_domain_filter=None,
            entity_hint=None,
            provider_diagnostics=[],
            retrieval_pass_records=[],
        )


def _acquire(query: str, *, existing_query: str | None = None) -> dict[str, Any]:
    result = apply_official_canonical_recovery_query_acquisition(
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["official_current_rules"],
            "source_class_recovery_queries": [
                existing_query
                or f"{query} official source current rules government agency guidance"
            ],
        },
        runtime_trace={
            "query_preview": query,
            "query_type": "official_current_status",
        },
    )
    return result.recommendation


def test_ag64b_irs_numeric_rule_acquisition_adds_notice_revenue_procedure_query() -> None:
    recommendation = _acquire(
        "What is the current IRS standard mileage rate for business use of a car in 2026?"
    )

    assert any(
        "IRS 2026 standard mileage rate business official notice revenue procedure"
        == query
        for query in recommendation["source_class_recovery_queries"]
    )
    assert len(recommendation["source_class_recovery_queries"]) <= 3


def test_ag64b_irs_live_style_generic_query_does_not_block_specific_variant() -> None:
    query = (
        "What is the current IRS standard mileage rate for business use of a car "
        "in 2026, and what official source supports it? Keep the answer concise."
    )
    generic_query = (
        "official current source IRS standard mileage rate for business use of "
        "a car in 2026 and official source"
    )

    recommendation = _acquire(query, existing_query=generic_query)

    assert recommendation["source_class_recovery_queries"][:2] == [
        generic_query,
        "IRS 2026 standard mileage rate business official notice revenue procedure",
    ]
    assert any(
        query == "IRS 2026 standard mileage rate business official notice revenue procedure"
        for query in recommendation["source_class_recovery_queries"]
    )


def test_ag64b_ssa_numeric_rule_acquisition_adds_benefit_base_query() -> None:
    recommendation = _acquire(
        "What is the 2026 Social Security taxable maximum wage base?"
    )

    assert any(
        query
        == (
            "SSA 2026 Social Security taxable maximum wage base official "
            "contribution benefit base"
        )
        for query in recommendation["source_class_recovery_queries"]
    )


def test_ag64b_federal_agency_domain_constraints_cover_numeric_rule_targets() -> None:
    federal_domains = [
        "federalregister.gov",
        "ecfr.gov",
        "govinfo.gov",
        "regulations.gov",
    ]
    assert build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=["official_current_rules"],
        query="2026 IRS standard mileage rate for business use of a car",
    ) == [*federal_domains, "irs.gov"]
    assert build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=["official_current_rules"],
        query="2026 Social Security taxable maximum wage base",
    ) == [*federal_domains, "ssa.gov"]
    assert build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=["official_current_rules"],
        query="current federal minimum wage",
    ) == [*federal_domains, "dol.gov"]
    assert build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=["official_current_rules"],
        query="current USCIS fee to file Form N-400 online",
    ) == [*federal_domains, "uscis.gov"]


def test_ag64b_federal_agency_sibling_adds_useful_official_query() -> None:
    recommendation = _acquire("What is the current federal minimum wage?")

    assert any(
        query == "Department of Labor current federal minimum wage official"
        for query in recommendation["source_class_recovery_queries"]
    )


def test_ag64b_canonical_docs_negative_control_still_uses_documentation_terms() -> None:
    result = apply_official_canonical_recovery_query_acquisition(
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
        runtime_trace={
            "query_preview": (
                "Explain how SQLite write-ahead logging works and why WAL mode "
                "changes read write concurrency."
            ),
            "query_type": "technical_reference",
        },
    )

    assert result.recommendation["source_class_recovery_queries"] == [
        (
            "official documentation Explain how SQLite write-ahead logging works "
            "and why WAL mode changes read write concurrency."
        ),
        (
            "reference documentation Explain how SQLite write-ahead logging works "
            "and why WAL mode changes read write concurrency."
        ),
    ]


def test_ag64b_ordinary_conceptual_negative_control_does_not_add_official_query() -> None:
    result = apply_official_canonical_recovery_query_acquisition(
        recommendation={"source_class_recovery_recommended": False},
        runtime_trace={
            "query_preview": "Explain why compound interest matters for beginners.",
            "query_type": "conceptual_explainer",
        },
    )

    assert result.recommendation == {"source_class_recovery_recommended": False}
    packet = result.trace["OfficialCanonicalRecoveryQueryAcquisition"]
    assert packet["acquisition_repair_used"] is False
    assert packet["acquisition_repair_skip_reason"] == "obligation_not_required"


def test_ag64c_irs_numeric_rule_classification_is_official_current() -> None:
    recommendation = build_source_class_recovery_recommendation(
        query=_irs_live_query(),
        current_date="2026-05-26",
        intent="general",
        report_type="answer",
        query_type="official_current_status",
        core_topic="IRS standard mileage rate",
        primary_entity="IRS",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"news.example": 2},
        top_source_domains=[{"domain": "news.example", "count": 2}],
        official_evidence_found=False,
    )

    missing = recommendation["missing_expected_source_classes"]
    assert "official_current_rules" in missing
    assert missing != ["primary_source_documents"]


def test_ag64c_irs_weak_corpus_does_not_preempt_official_current_recovery() -> None:
    query = _irs_live_query()
    recommendation = _acquire(
        query,
        existing_query="IRS standard mileage rate official documentation reference manual",
    )

    admission = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace={
            "query_preview": query,
            "query_type": "official_current_status",
            "weak_corpus_recovery_used": True,
            "corpus_weak": True,
        },
        existing_blockers=(
            "weak_corpus_recovery_owns_path",
            "blocked_by_corpus_weak",
        ),
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )
    admission_packet = admission.trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]
    controller_input = build_source_class_recovery_controller_input(
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"news.example": 2},
            "top_source_domains": [{"domain": "news.example", "count": 2}],
            "official_evidence_found": False,
        },
        corpus_state="OFF_TOPIC",
        corpus_weak=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=True,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=(
            admission.source_class_recovery_execution_admitted
        ),
        prior_attempt_count=0,
    )
    decision = decide_source_class_recovery(controller_input)

    assert admission.source_class_recovery_execution_admitted is True
    assert admission_packet["admission_blockers"] == []
    assert decision.decision is (
        SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
    )
    assert "blocked_by_weak_corpus_recovery" not in decision.blockers
    assert "blocked_by_corpus_weak" not in decision.blockers


def test_ag64c_irs_live_style_previews_include_specific_official_current_query() -> None:
    query = _irs_live_query() + " Keep the answer concise."
    recommendation = _acquire(
        query,
        existing_query="IRS standard mileage rate official documentation reference manual",
    )
    admission = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace={
            "query_preview": query,
            "query_type": "official_current_status",
            "weak_corpus_recovery_used": True,
            "corpus_weak": True,
        },
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )
    packet = admission.trace["OfficialCanonicalRecoveryExecutionAdmission"]

    assert (
        "IRS 2026 standard mileage rate business official notice revenue procedure"
        in packet["recovery_query_previews"]
    )
    assert packet["recovery_query_previews"] != [
        "IRS standard mileage rate official documentation reference manual"
    ]


def test_ag64c_safe_insufficiency_posture_survives_after_admitted_action() -> None:
    decision = decide_source_class_recovery(_controller_input(_recommendation()))

    assert decision.action_envelope is not None
    envelope = decision.action_envelope.to_dict()
    assert envelope["allowed_action"] is True
    assert envelope["stop_posture_if_unmet"] == "stop_insufficient_with_caveat"


def test_ag64d_live_style_admitted_official_current_recovery_executes() -> None:
    query = _irs_live_query() + " Keep the answer concise."
    recommendation = _acquire(
        query,
        existing_query="IRS standard mileage rate official documentation reference manual",
    )
    admission = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace={
            "query_preview": query,
            "query_type": "official_current_status",
        },
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )
    controller = RunController()
    lifecycle = _record_lifecycle(controller, recommendation)
    spine = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": None,
            "recommended_action_name": None,
        },
        source_class_lifecycle_trace=lifecycle,
    )
    captured_queries: list[str] = []

    def fake_search(
        queries: list[str],
        *_args: Any,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        captured_queries.extend(queries)
        return []

    assert admission.source_class_recovery_execution_admitted is True
    assert lifecycle["active_source_class_recovery_official_canonical_admitted"] is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_action_envelope"][
        "allowed_action"
    ] is True
    assert spine.trace_packet["gate_reason"] == (
        "approved_by_official_canonical_admission"
    )
    assert (
        "IRS 2026 standard mileage rate business official notice revenue procedure"
        in controller.snapshot_ledger()["retrieval_actions"][0]["queries"]
    )

    result = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=[],
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[0.0],
        seen_urls=set(),
        collected_images=set(),
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        search_providers=["tavily"],
        exa_domain_filter=None,
        entity_hint=None,
        provider_diagnostics=[],
        retrieval_pass_records=[],
    )

    assert result["attempted"] is True
    assert lifecycle["active_source_class_recovery_execution_attempted"] is True
    assert (
        "IRS 2026 standard mileage rate business official notice revenue procedure"
        in captured_queries
    )


@pytest.mark.parametrize(
    "checkpoint_action",
    [
        RECOVER_WEAK_CORPUS,
        RESOLVE_CONFLICT,
        "retrieve_targeted",
        STOP_INSUFFICIENT_WITH_CAVEAT,
    ],
)
def test_ag64d_checkpoint_ownership_blocks_official_current_fallback(
    checkpoint_action: str,
) -> None:
    recommendation = _acquire(_irs_live_query())
    controller = RunController()
    lifecycle = _record_lifecycle(controller, recommendation)
    spine = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": {"action_name": checkpoint_action},
            "recommended_action_name": checkpoint_action,
        },
        source_class_lifecycle_trace=lifecycle,
        weak_corpus_lifecycle_trace={"approved": checkpoint_action == RECOVER_WEAK_CORPUS},
        conflict_resolution_lifecycle_trace={
            "approved": checkpoint_action == RESOLVE_CONFLICT,
            "active_conflict_resolution_considered": True,
        },
    )

    assert lifecycle["active_source_class_recovery_official_canonical_admitted"] is True
    assert spine.source_class_checkpoint_gate_trace["spine_authorization_source"] is None


def test_ag64b_protected_surface_static_scan() -> None:
    query_tree = ast.parse(_QUERY_ACQUISITION_PATH.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(query_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported.update(
        alias.name
        for node in ast.walk(query_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert imported.isdisjoint(
        {
            "core.search_providers",
            "core.routing",
            "core.prompts",
            "core.source_classifier",
        }
    )

    orchestrator_source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    assert "Serper" not in orchestrator_source
    assert "DataForSEO" not in orchestrator_source
    assert "Firecrawl" not in orchestrator_source
