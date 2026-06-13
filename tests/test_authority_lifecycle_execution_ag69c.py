from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import core.source_class_recovery_runner as runner_module
from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_orchestrator_handoff,
)
from core.authority_lifecycle_execution import (
    sync_authority_lifecycle_execution_from_source_class_trace,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.controller_action_envelope import STOP_INSUFFICIENT_WITH_CAVEAT
from core.run_controller import RunController
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

_QUERY = (
    "What is the current Social Security taxable maximum wage base for 2026, "
    "and what official source supports it? Keep the answer concise."
)
_RECOVERY_QUERIES = (
    "SSA 2026 Social Security taxable maximum wage base official source",
    "official current Social Security contribution benefit base 2026",
)


def _recommendation(
    *,
    queries: tuple[str, ...] = _RECOVERY_QUERIES,
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": ["official_current_rules"],
        "source_class_recovery_queries": list(queries),
        "source_class_recovery_query_count": len(queries),
        "source_class_recovery_reason": "source_class_recovery:ag69c_gap",
        "source_class_recovery_trigger_fields": [
            "runtime_source_class_expectation"
        ],
    }
    if blockers is not None:
        payload["authority_lifecycle_blockers"] = blockers
    return payload


def _observability() -> dict[str, Any]:
    return {
        "source_class_satisfaction_status": {
            "official_current_rules": "expected_but_only_secondary"
        },
        "source_class_strong_satisfaction_counts": {
            "official_current_rules": 0
        },
        "source_class_gap_candidates": ["official_current_rules"],
    }


def _answer_contract_result() -> SimpleNamespace:
    contract = SimpleNamespace(
        family=SimpleNamespace(value="current_official_rules"),
        must_satisfy=("official current source",),
        should_satisfy=(),
        evidence_classes_needed=("official_current_rules",),
    )
    evidence_state = SimpleNamespace(
        evidence_available=True,
        evidence_sufficient=False,
        source_classes_present=("reputable_secondary",),
        source_classes_missing=("official_current_rules",),
        conflicts_present=False,
        conflict_notes=(),
        resolving_queries=(),
        prior_queries=("ssa secondary wage base",),
        next_queries=("official SSA taxable maximum wage base",),
        next_query_redundant=False,
        social_signal_status=None,
        scrutineer_requested=False,
        scrutineer_needed=False,
    )
    return SimpleNamespace(
        adapter_result=SimpleNamespace(
            contract=contract,
            evidence_used=("secondary-evidence",),
        ),
        state=SimpleNamespace(
            evidence_state_summary=evidence_state,
            missing_information=("official current source missing",),
        ),
        fulfillment_handoff=SimpleNamespace(
            fulfilled_items=(),
            partial_items=("secondary source found",),
            unfulfilled_items=("official current source",),
        ),
    )


def _orchestrator_state(
    *,
    recommendation: dict[str, Any] | None = None,
    terminal_stop: bool = False,
    corpus_weak: bool = False,
    weak_corpus_recovery_used: bool = False,
) -> dict[str, Any]:
    checkpoint = (
        {
            "available": True,
            "decision": {"action_name": STOP_INSUFFICIENT_WITH_CAVEAT},
            "recommended_action_name": STOP_INSUFFICIENT_WITH_CAVEAT,
            "terminal_stop_approved": True,
        }
        if terminal_stop
        else {}
    )
    return {
        "query": _QUERY,
        "intent": "general",
        "report_type": "answer",
        "query_type": "official_current_status",
        "core_topic": "SSA 2026 Social Security taxable maximum wage base",
        "primary_entity": "SSA",
        "_source_class_recovery_lifecycle_recommendation": (
            recommendation or _recommendation()
        ),
        "_source_class_recovery_answer_contract_observability": _observability(),
        "_source_tier_recovery_lifecycle": {
            "source_tier_counts": {"secondary": 2},
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        "_source_domain_recovery_lifecycle": {
            "source_domain_counts": {"payroll.example": 2},
            "top_source_domains": [{"domain": "payroll.example", "count": 2}],
            "unique_source_domain_count": 1,
            "on_domain_source_count": 0,
            "off_domain_source_count": 1,
        },
        "_pre_recovery_answer_contract_result": _answer_contract_result(),
        "corpus_state": "OFF_TOPIC" if corpus_weak else "HEALTHY",
        "corpus_weak": corpus_weak,
        "weak_corpus_recovery_considered": weak_corpus_recovery_used,
        "weak_corpus_recovery_used": weak_corpus_recovery_used,
        "weak_corpus_recovery_skip_reason": (
            "weak_corpus_recovery_used" if weak_corpus_recovery_used else None
        ),
        "evidence_integration_checkpoint_trace": checkpoint,
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


def _run_lifecycle_dispatch(
    controller: RunController,
    lifecycle: dict[str, Any],
) -> tuple[dict[str, int | bool], list[str], list[dict[str, Any]]]:
    captured_queries: list[str] = []
    all_passages: list[dict[str, Any]] = []

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
        seen_urls.add("https://www.ssa.gov/ag69c-offline-fixture")
        return [
            {
                "url": "https://www.ssa.gov/ag69c-offline-fixture",
                "title": "SSA AG-69C offline fixture",
                "text": "Offline fixture for AuthorityLifecycle execution.",
                "source_class": "official_current_rules",
                "source_tier": "official",
            }
        ]

    result = run_source_class_recovery_dispatch(
        SourceClassRecoveryRunnerContext(
            controller=controller,
            lifecycle_trace=lifecycle,
            process_search_queries=fake_search,
            all_passages=all_passages,
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
            entity_hint="SSA",
            provider_diagnostics=[],
            retrieval_pass_records=[],
        )
    ).source_class_recovery_execution
    return result, captured_queries, all_passages


def _requirement_bound_blocker(requirement_id: str) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "kind": "execution_hard_blocker",
        "reason": "controller_bound_execution_blocker",
        "owner": "controller",
        "hard": True,
    }


def _execution_blocker(lifecycle: dict[str, Any]) -> dict[str, Any]:
    blocker = lifecycle["authority_lifecycle_execution_blocker"]
    assert isinstance(blocker, dict)
    return blocker


def test_ag69c_lifecycle_approved_recovery_reaches_existing_executor_entrypoint(
    monkeypatch: Any,
) -> None:
    controller = RunController()
    handoff = _handoff(controller)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    calls: list[bool] = []
    original = runner_module.execute_source_class_recovery_action

    def spy(*args: Any, **kwargs: Any) -> dict[str, int | bool]:
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(runner_module, "execute_source_class_recovery_action", spy)
    execution, captured_queries, passages = _run_lifecycle_dispatch(
        controller,
        lifecycle,
    )

    assert calls == [True]
    assert execution["attempted"] is True
    assert lifecycle["source_class_recovery_dispatch_authority"] == (
        "authority_lifecycle.recovery_action"
    )
    assert captured_queries == list(_RECOVERY_QUERIES)
    assert passages[0]["retrieval_stage"] == "source_class_recovery"
    assert lifecycle["authority_lifecycle"]["execution_state"]["state"] == "attempted"
    assert lifecycle["active_source_class_recovery_execution_attempted"] is True


def test_ag69c_legacy_execution_attempted_is_only_projected_after_entrypoint() -> None:
    controller = RunController()
    lifecycle = _handoff(controller).active_source_class_recovery_lifecycle

    lifecycle["active_source_class_recovery_execution_attempted"] = True
    sync_authority_lifecycle_execution_from_source_class_trace(lifecycle)

    assert lifecycle["authority_lifecycle"]["execution_state"]["state"] == (
        "approved_pending_execution"
    )
    assert lifecycle["active_source_class_recovery_execution_attempted"] is False

    _run_lifecycle_dispatch(
        controller,
        lifecycle,
    )

    assert lifecycle["authority_lifecycle_execution_attempted"] is True
    assert lifecycle["active_source_class_recovery_execution_attempted"] is True


def test_ag69c_admitted_eligible_without_dispatch_records_structured_blocker() -> None:
    controller = RunController()
    handoff = _handoff(controller)
    lifecycle = handoff.active_source_class_recovery_lifecycle
    blocked_lifecycle = {
        **lifecycle,
        "authority_lifecycle": {
            **lifecycle["authority_lifecycle"],
            "recovery_action": {
                **lifecycle["authority_lifecycle"]["recovery_action"],
                "approved": False,
            },
        },
    }
    execution, captured_queries, _passages = _run_lifecycle_dispatch(
        controller,
        blocked_lifecycle,
    )

    assert handoff.official_canonical_recovery_execution_admitted is True
    assert execution["attempted"] is False
    assert captured_queries == []
    assert blocked_lifecycle["source_class_recovery_dispatch_reason"] == (
        "canonical_recovery_action_not_approved"
    )
    assert blocked_lifecycle["authority_lifecycle_execution_blocked"] is True
    assert blocked_lifecycle["authority_lifecycle"]["execution_state"]["state"] == (
        "blocked"
    )
    assert _execution_blocker(blocked_lifecycle)["requirement_id"] == (
        "official_current_rules"
    )


def test_ag69c_missing_executable_query_records_structured_execution_blocker() -> None:
    arbitration = build_authority_runtime_arbitration(
        requirement_id="official_current_rules",
        required_authority="official_current_rules",
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=(),
        required_source_classes=("official_current_rules",),
        recovery_action_allowed=True,
    )
    trace = arbitration.to_trace_fields()
    lifecycle = trace["authority_lifecycle"]
    blocker = trace["authority_lifecycle_execution_blocker"]

    assert lifecycle["recovery_action"]["approved"] is True
    assert lifecycle["recovery_action"]["recovery_query_count"] == 0
    assert trace["authority_lifecycle_execution_blocked"] is True
    assert blocker == {
        "requirement_id": "official_current_rules",
        "kind": "recovery_execution_blocked",
        "reason": "missing_executable_recovery_query",
        "owner": "controller/lifecycle",
        "hard": True,
        "blocker_reason": "missing_executable_recovery_query",
        "blocker_owner": "controller/lifecycle",
        "recovery_may_be_retried": True,
        "final_posture_must_be_insufficient_partial": True,
    }


def test_ag69c_hard_blocker_prevents_execution_only_when_requirement_bound() -> None:
    wrong_controller = RunController()
    wrong = _handoff(
        wrong_controller,
        state=_orchestrator_state(
            recommendation=_recommendation(
                blockers=[_requirement_bound_blocker("different-requirement")]
            )
        ),
    )
    bound_controller = RunController()
    bound = _handoff(
        bound_controller,
        state=_orchestrator_state(
            recommendation=_recommendation(
                blockers=[_requirement_bound_blocker("official_current_rules")]
            )
        ),
    )

    wrong_execution, wrong_queries, _wrong_passages = _run_lifecycle_dispatch(
        wrong_controller,
        wrong.active_source_class_recovery_lifecycle,
    )
    bound_execution, bound_queries, _bound_passages = _run_lifecycle_dispatch(
        bound_controller,
        bound.active_source_class_recovery_lifecycle,
    )

    assert wrong_execution["attempted"] is True
    assert wrong_queries == list(_RECOVERY_QUERIES)
    assert wrong.active_source_class_recovery_lifecycle[
        "authority_lifecycle_required_recovery_allowed"
    ] is True
    assert bound_execution["attempted"] is False
    assert bound_queries == []
    assert bound.active_source_class_recovery_lifecycle[
        "source_class_recovery_dispatch_reason"
    ] == "canonical_recovery_execution_blocked"
    assert bound.active_source_class_recovery_lifecycle[
        "authority_lifecycle_execution_blocked"
    ] is True
    blocker = bound.active_source_class_recovery_lifecycle["authority_lifecycle"][
        "explicit_blockers"
    ][0]
    assert blocker["requirement_id"] == "official_current_rules"
    assert blocker["blocker_reason"] == "controller_bound_execution_blocker"


def test_ag69c_terminal_stop_and_weak_corpus_do_not_become_execution_blockers() -> None:
    terminal_controller = RunController()
    terminal = _handoff(
        terminal_controller,
        state=_orchestrator_state(terminal_stop=True),
    )
    weak_controller = RunController()
    weak = _handoff(
        weak_controller,
        state=_orchestrator_state(
            corpus_weak=True,
            weak_corpus_recovery_used=True,
        ),
    )

    terminal_execution, terminal_queries, _terminal_passages = _run_lifecycle_dispatch(
        terminal_controller,
        terminal.active_source_class_recovery_lifecycle,
    )
    weak_execution, weak_queries, _weak_passages = _run_lifecycle_dispatch(
        weak_controller,
        weak.active_source_class_recovery_lifecycle,
    )

    assert terminal_execution["attempted"] is False
    assert terminal_queries == []
    assert terminal.active_source_class_recovery_lifecycle[
        "source_class_recovery_dispatch_authorized"
    ] is True
    assert terminal.active_source_class_recovery_lifecycle[
        "source_class_recovery_dispatch_reason"
    ] == "canonical_authority_lifecycle_recovery_action"
    assert weak_execution["attempted"] is True
    assert weak_queries == list(_RECOVERY_QUERIES)
    assert terminal.active_source_class_recovery_lifecycle[
        "authority_lifecycle_execution_blocker"
    ] is None
    assert weak.active_source_class_recovery_lifecycle[
        "authority_lifecycle_execution_blocker"
    ] is None


def test_ag69c_execution_and_candidate_acquisition_states_remain_distinct() -> None:
    controller = RunController()
    lifecycle = _handoff(controller).active_source_class_recovery_lifecycle
    execution, _captured_queries, _passages = _run_lifecycle_dispatch(
        controller,
        lifecycle,
    )

    assert execution["attempted"] is True
    assert lifecycle["authority_lifecycle_execution_attempted"] is True
    assert lifecycle["candidate_acquisition_considered"] is True
    assert lifecycle["acquisition_attempted"] is True
    assert lifecycle["candidate_return_status"] == "candidates_returned"
    assert lifecycle["active_source_class_recovery_used"] is True
    assert lifecycle["authority_lifecycle"]["candidate_acquisition_state"] == (
        "attempted"
    )
    assert lifecycle["authority_lifecycle"]["candidate_fit"]["fit_state"] == (
        "not_evaluated"
    )


def test_ag69c_pipeline_change_remains_tiny_plumbing() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    runner_source = (_ROOT / "core" / "source_class_recovery_runner.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(pipeline_source)

    assert pipeline_source.count("execute_source_class_recovery_action(") == 0
    assert runner_source.count("execute_source_class_recovery_action(") == 1
    assert (
        pipeline_source.count(
            "record_source_class_recovery_execution_blocked_if_needed("
        )
        == 0
    )
    assert (
        runner_source.count(
            "record_source_class_recovery_execution_blocked_if_needed("
        )
        == 2
    )
    assert "run_source_class_recovery_dispatch(" in pipeline_source
    call_index = runner_source.index(
        "record_source_class_recovery_execution_blocked_if_needed("
    )
    helper_region = runner_source[call_index - 500 : call_index + 500].casefold()
    for forbidden in (
        "select_providers(",
        "choose_supplemental_search_depth(",
        "rank_sources(",
        "build_author_prompt(",
        "build_final_answer(",
        "standard mileage rate",
        "social security taxable maximum",
    ):
        assert forbidden not in helper_region
    assert not {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and "authority_lifecycle" in node.name
    }
