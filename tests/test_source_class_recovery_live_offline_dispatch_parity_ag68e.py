from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.controller_loop_spine import (
    STOP_INSUFFICIENT_WITH_CAVEAT,
    build_controller_loop_spine_result,
)
from core.run_controller import RunController
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)
from tests.helpers.authoritative_source_forced_corridor import (
    canonical_doc_forced_corridor_fixture,
    official_current_forced_corridor_fixture,
    run_forced_corridor_validation,
)

_ROOT = Path(__file__).resolve().parents[1]
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_RETRIEVAL_AUTHORITY_STAGE_PATH = _ROOT / "core" / "retrieval_authority_stage.py"
_RUNNER_PATH = _ROOT / "core" / "source_class_recovery_runner.py"

_LIVE_QUERY = (
    "What is the current IRS standard mileage rate for business use of a car "
    "in 2026, and what official source supports it? Keep the answer concise."
)
_OFFICIAL_QUERIES = (
    "IRS 2026 standard mileage rate business official notice revenue procedure",
    "IRS 2026 standard mileage rate revenue procedure official current source",
)


def _recommendation(
    *,
    source_class: str = "official_current_rules",
    queries: tuple[str, ...] = _OFFICIAL_QUERIES,
) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [source_class],
        "source_class_recovery_queries": list(queries),
        "source_class_recovery_query_count": len(queries),
        "source_class_recovery_reason": "source_class_recovery:visible_queries",
        "source_class_recovery_trigger_fields": ["runtime_source_class_expectation"],
    }


def _observability(
    *,
    source_class: str = "official_current_rules",
    status: str = "expected_but_only_secondary",
) -> dict[str, Any]:
    return {
        "source_class_satisfaction_status": {source_class: status},
        "source_class_strong_satisfaction_counts": {
            source_class: 1 if status == "satisfied_strong" else 0
        },
        "source_class_gap_candidates": [source_class],
    }


def _source_tier_lifecycle(*, official_found: bool = False) -> dict[str, Any]:
    return {
        "source_tier_counts": {"official": 1} if official_found else {"secondary": 2},
        "official_evidence_found": official_found,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _source_domain_lifecycle(*, official_found: bool = False) -> dict[str, Any]:
    return {
        "source_domain_counts": (
            {"irs.gov": 1} if official_found else {"analysis.example": 2}
        ),
        "top_source_domains": [
            {"domain": "irs.gov" if official_found else "analysis.example", "count": 1}
        ],
        "unique_source_domain_count": 1,
        "on_domain_source_count": 1 if official_found else 0,
        "off_domain_source_count": 0 if official_found else 1,
    }


def _answer_contract_result() -> SimpleNamespace:
    return SimpleNamespace(
        adapter_result=SimpleNamespace(
            contract=SimpleNamespace(
                family=SimpleNamespace(value="current_official_rules")
            )
        ),
        state=SimpleNamespace(
            evidence_state_summary=SimpleNamespace(source_classes_missing=())
        ),
        fulfillment_handoff=SimpleNamespace(
            unfulfilled_items=(),
            partial_items=(),
        ),
    )


def _checkpoint(reason: str, *, fallback_allowed: bool = False) -> dict[str, Any]:
    trace = {
        "available": False,
        "reason": reason,
        "decision": None,
        "recommended_action_name": None,
    }
    if fallback_allowed:
        trace["official_canonical_checkpoint_exception_fallback_allowed"] = True
    return trace


def _orchestrator_state(
    *,
    recommendation: dict[str, Any] | None = None,
    observability: dict[str, Any] | None = None,
    checkpoint_trace: dict[str, Any] | None = None,
    official_found: bool = False,
    corpus_weak: bool = False,
    weak_corpus_recovery_used: bool = False,
) -> dict[str, Any]:
    return {
        "query": _LIVE_QUERY,
        "intent": "general",
        "report_type": "answer",
        "query_type": "official_current_status",
        "core_topic": "IRS 2026 standard mileage rate business",
        "primary_entity": "IRS",
        "_source_class_recovery_lifecycle_recommendation": (
            recommendation or _recommendation()
        ),
        "_source_class_recovery_answer_contract_observability": (
            observability or _observability()
        ),
        "_source_tier_recovery_lifecycle": _source_tier_lifecycle(
            official_found=official_found
        ),
        "_source_domain_recovery_lifecycle": _source_domain_lifecycle(
            official_found=official_found
        ),
        "_pre_recovery_answer_contract_result": _answer_contract_result(),
        "corpus_state": "OFF_TOPIC" if corpus_weak else "HEALTHY",
        "corpus_weak": corpus_weak,
        "weak_corpus_recovery_considered": weak_corpus_recovery_used,
        "weak_corpus_recovery_used": weak_corpus_recovery_used,
        "weak_corpus_recovery_skip_reason": (
            "weak_corpus_recovery_used" if weak_corpus_recovery_used else None
        ),
        "evidence_integration_checkpoint_trace": checkpoint_trace or {},
        "current_search_depth_for_recovery": "basic",
        "iterations_run": 0,
        "max_iterations": 1,
        "waste_flags": [],
    }


def _handoff(
    controller: RunController,
    *,
    state: dict[str, Any] | None = None,
) -> Any:
    return build_authoritative_source_action_orchestrator_handoff(
        controller,
        orchestrator_state=state or _orchestrator_state(),
    )


def _assert_canonical_recovery_action(lifecycle: dict[str, Any]) -> None:
    action = lifecycle["authority_lifecycle"]["recovery_action"]
    assert action["action_type"] == "recover_missing_source_class"
    assert action["approved"] is True
    assert action["required_source_classes"] == ["official_current_rules"]
    assert action["recovery_query_count"] == len(_OFFICIAL_QUERIES)


def _spine(
    lifecycle: dict[str, Any],
    *,
    checkpoint_trace: dict[str, Any],
) -> Any:
    return build_controller_loop_spine_result(
        checkpoint_trace=checkpoint_trace,
        source_class_lifecycle_trace=lifecycle,
    )


def _run_product_call_site_dispatch(
    controller: RunController,
    lifecycle: dict[str, Any],
) -> tuple[dict[str, int | bool], list[str]]:
    captured_queries: list[str] = []

    def fake_search(
        queries: list[str],
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
        captured_queries.extend(queries)
        seen_urls.add("https://www.irs.gov/ag68e-product-path-fixture")
        return [
            {
                "url": "https://www.irs.gov/ag68e-product-path-fixture",
                "title": "IRS AG-68E product-path fixture",
                "text": "Offline product-path source-class recovery fixture.",
                "source_class": "official_current_rules",
                "source_tier": "official",
            }
        ]

    execution = run_source_class_recovery_dispatch(
        SourceClassRecoveryRunnerContext(
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
            search_providers=["offline-fixture"],
            exa_domain_filter=None,
            entity_hint="IRS",
            provider_diagnostics=[],
            retrieval_pass_records=[],
        )
    ).source_class_recovery_execution
    return execution, captured_queries


def test_ag68e_live_equivalent_product_path_executes_after_exception_parity_repair() -> None:
    controller = RunController()
    handoff = _handoff(
        controller,
        state=_orchestrator_state(
            checkpoint_trace=_checkpoint(
                "checkpoint_exception",
                fallback_allowed=True,
            )
        ),
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle
    execution, captured_queries = _run_product_call_site_dispatch(
        controller,
        lifecycle,
    )

    _assert_canonical_recovery_action(lifecycle)
    assert lifecycle["source_class_recovery_dispatch_authority"] == (
        "authority_lifecycle.recovery_action"
    )
    assert execution["attempted"] is True
    assert lifecycle["authority_lifecycle"]["execution_state"]["state"] == "attempted"
    assert captured_queries == list(_OFFICIAL_QUERIES)


def test_ag68e_product_call_site_does_not_execute_without_canonical_action() -> None:
    controller = RunController()
    lifecycle = _handoff(controller).active_source_class_recovery_lifecycle
    blocked_lifecycle = {**lifecycle, "authority_lifecycle": None}
    execution, captured_queries = _run_product_call_site_dispatch(
        controller,
        blocked_lifecycle,
    )

    assert execution["attempted"] is False
    assert blocked_lifecycle["source_class_recovery_dispatch_authority"] == (
        "authority_lifecycle.recovery_action"
    )
    assert blocked_lifecycle["source_class_recovery_dispatch_reason"] == (
        "canonical_authority_lifecycle_absent"
    )
    assert captured_queries == []


def test_ag68e_dispatch_uses_canonical_action_not_trace_projection() -> None:
    controller = RunController()
    handoff = _handoff(controller)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    trace = handoff.authoritative_source_action_trace
    projection = dict(trace["obligation_projection"])
    projection["active_source_class_recovery_action_envelope"] = {
        "action_type": "recover_missing_source_class",
        "required_source_class": ["official_current_rules"],
        "allowed_action": True,
    }
    lifecycle_without_action = {
        **lifecycle,
        "authority_lifecycle": {
            **lifecycle["authority_lifecycle"],
            "recovery_action": None,
        },
        "active_source_class_recovery_action_envelope": {
            "action_type": "recover_missing_source_class",
            "required_source_class": ["official_current_rules"],
            "allowed_action": True,
        },
    }
    assert trace["protected_surface"]["projection_used_as_control_input"] is False
    execution, captured_queries = _run_product_call_site_dispatch(
        controller,
        lifecycle_without_action,
    )

    assert execution["attempted"] is False
    assert captured_queries == []
    assert lifecycle_without_action["source_class_recovery_dispatch_authority"] == (
        "authority_lifecycle.recovery_action"
    )
    assert lifecycle_without_action["source_class_recovery_dispatch_reason"] == (
        "canonical_recovery_action_absent"
    )


def test_ag68e_terminal_stop_defers_to_authority_lifecycle_recovery() -> None:
    controller = RunController()
    lifecycle = _handoff(controller).active_source_class_recovery_lifecycle
    spine = _spine(
        lifecycle,
        checkpoint_trace={
            "available": True,
            "decision": {"action_name": STOP_INSUFFICIENT_WITH_CAVEAT},
            "recommended_action_name": STOP_INSUFFICIENT_WITH_CAVEAT,
        },
    )

    _assert_canonical_recovery_action(lifecycle)
    assert spine.terminal_stop_approved is True
    execution, captured_queries = _run_product_call_site_dispatch(
        controller,
        lifecycle,
    )

    assert execution["attempted"] is True
    assert captured_queries == controller.state.recovery_action_records[0].queries


def test_ag68e_weak_corpus_ownership_defers_to_authority_lifecycle() -> None:
    controller = RunController()
    handoff = _handoff(
        controller,
        state=_orchestrator_state(
            corpus_weak=True,
            weak_corpus_recovery_used=True,
            checkpoint_trace=_checkpoint("checkpoint_exception", fallback_allowed=True),
        ),
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle

    _assert_canonical_recovery_action(lifecycle)
    execution, captured_queries = _run_product_call_site_dispatch(
        controller,
        lifecycle,
    )

    assert execution["attempted"] is True
    assert captured_queries == controller.state.recovery_action_records[0].queries


def test_ag68e_aggregate_ordinary_status_no_longer_blocks_recovery_dispatch() -> None:
    controller = RunController()
    handoff = _handoff(
        controller,
        state=_orchestrator_state(
            recommendation={
                **_recommendation(),
                "source_class_recovery_recommended": False,
                "missing_expected_source_classes": [],
                "source_class_recovery_queries": [],
                "source_class_recovery_query_count": 0,
            },
            observability=_observability(status="satisfied_strong"),
            official_found=True,
            checkpoint_trace=_checkpoint("checkpoint_exception", fallback_allowed=True),
        ),
    )
    lifecycle = handoff.active_source_class_recovery_lifecycle

    _assert_canonical_recovery_action(lifecycle)
    execution, captured_queries = _run_product_call_site_dispatch(
        controller,
        lifecycle,
    )

    assert execution["attempted"] is True
    assert captured_queries == controller.state.recovery_action_records[0].queries


def test_ag68e_public_forced_corridor_helper_shapes_are_preserved() -> None:
    official = run_forced_corridor_validation(official_current_forced_corridor_fixture())
    canonical = run_forced_corridor_validation(canonical_doc_forced_corridor_fixture())

    assert official.classification["next_failure_layer"] == (
        "offline_recovery_dispatch_fixture_succeeded"
    )
    assert canonical.classification["next_failure_layer"] == (
        "offline_recovery_dispatch_fixture_succeeded"
    )
    assert "active_source_class_recovery_action_envelope" in (
        official.action_result.active_source_class_recovery_lifecycle
    )


def test_ag68e_pipeline_call_site_remains_single_tiny_executor_gate() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    stage_source = _RETRIEVAL_AUTHORITY_STAGE_PATH.read_text(encoding="utf-8")
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8")

    assert pipeline_source.count("execute_source_class_recovery_action(") == 0
    assert runner_source.count("execute_source_class_recovery_action(") == 1
    assert "run_source_class_recovery_dispatch(" in pipeline_source
    assert "authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS" not in (
        pipeline_source
    )
    assert "authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS" not in runner_source
    assert "authority_lifecycle.recovery_action" in runner_source
    assert (
        "official_canonical_checkpoint_exception_fallback_allowed"
        in stage_source
    )


def test_ag68e_static_guard_keeps_protected_surfaces_closed() -> None:
    tree = ast.parse(_SPINE_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imports.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert imports.isdisjoint(
        {
            "core.pipeline_orchestrator",
            "core.prompts",
            "core.routing",
            "core.search_providers",
            "core.source_classifier",
            "openai",
            "requests",
        }
    )

    spine_source = _SPINE_PATH.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "select_providers(",
        "choose_supplemental_search_depth(",
        "rank_sources(",
        "build_author_prompt(",
        "build_final_answer(",
        "scrutineer_policy",
        "followup_prompt",
    ):
        assert forbidden not in spine_source
