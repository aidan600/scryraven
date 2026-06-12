from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.official_canonical_recovery_execution_admission import (
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_SCHEMA_VERSION,
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY,
    build_official_canonical_recovery_execution_admission,
)
from core.official_current_source_custody import (
    OfficialCurrentCustodyStatus,
    OfficialCurrentSourceCustodyState,
)
from core.run_controller import RunController
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)
from core.source_class_recovery_controller import (
    SourceClassRecoveryControllerDecision,
    build_source_class_recovery_controller_input,
    decide_source_class_recovery,
)
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = (
    _ROOT / "core" / "official_canonical_recovery_execution_admission.py"
)
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_ACTION_HELPER_PATH = _ROOT / "core" / "authoritative_source_action.py"
_ORCHESTRATOR_ADAPTER_PATH = (
    _ROOT / "core" / "authoritative_source_action_orchestrator_adapter.py"
)


def _recommendation(
    *,
    missing: list[str],
    queries: list[str] | None = None,
    reason: str = "official_canonical_recovery_query_acquisition:gap",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recovery_queries = (
        list(queries)
        if queries is not None
        else ["canonical documentation storage engine"]
    )
    payload = {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": list(missing),
        "source_class_recovery_queries": recovery_queries,
        "source_class_recovery_query_count": len(recovery_queries),
        "source_class_recovery_reason": reason,
    }
    payload.update(extra or {})
    return payload


def _admission(
    trace: dict[str, Any],
    recommendation: dict[str, Any],
    *,
    existing_blockers: tuple[str, ...] = (),
    prior_recovery_attempt_count: int | None = 0,
    max_recovery_attempts: int = 1,
    ordinary_iteration_budget_remaining: int = 0,
) -> tuple[bool, dict[str, Any]]:
    result = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace=trace,
        existing_blockers=existing_blockers,
        prior_recovery_attempt_count=prior_recovery_attempt_count,
        max_recovery_attempts=max_recovery_attempts,
        ordinary_iteration_budget_remaining=ordinary_iteration_budget_remaining,
    )
    packet = result.trace
    assert (
        packet["schema_version"]
        == OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_SCHEMA_VERSION
    )
    assert packet["trace_mode"] == "recovery_execution_admission"
    return (
        result.source_class_recovery_execution_admitted,
        packet["OfficialCanonicalRecoveryExecutionAdmission"],
    )


def _controller_input(
    recommendation: dict[str, Any],
    *,
    iteration_budget_available: bool = False,
    official_canonical_slot: bool = True,
) -> Any:
    return build_source_class_recovery_controller_input(
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals={"source_tier_counts": {"secondary": 1}},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=iteration_budget_available,
        prior_attempt_count=0,
        official_canonical_source_class_slot_available=official_canonical_slot,
    )


def _accepted_custody(source_class: str) -> dict[str, Any]:
    return (
        OfficialCurrentSourceCustodyState()
        .require(source_class)
        .record_candidate_disposition(
            f"official_current_source:{source_class}",
            status=OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED,
            candidate_id=f"https://docs.example/{source_class}",
            reason="accepted_authority_custody",
        )
        .to_dict()
    )


def test_ag50b_canonical_positive_admits_recovery_with_ag50a_query() -> None:
    admitted, trace = _admission(
        {
            "query_preview": "Explain how PostgreSQL MVCC works in a database.",
            "query_type": "technical_reference",
        },
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation PostgreSQL MVCC"],
        ),
    )

    assert admitted is True
    assert trace["admission_considered"] is True
    assert trace["admission_eligible"] is True
    assert trace["admission_used"] is True
    assert trace["required_source_classes"] == ["primary_source_documents"]
    assert trace["unsatisfied_required_source_classes"] == [
        "primary_source_documents"
    ]
    assert trace["recovery_query_available"] is True
    assert trace["source_class_recovery_execution_admitted"] is True


def test_ag50b_official_current_positive_admits_recovery_with_query() -> None:
    admitted, trace = _admission(
        {
            "query_preview": "What are the current official rules for a federal benefit in 2026?",
            "query_type": "official_current_status",
        },
        _recommendation(
            missing=["official_current_rules"],
            queries=["official current source federal benefit 2026"],
        ),
    )

    assert admitted is True
    assert trace["admission_used"] is True
    assert trace["required_source_classes"] == ["official_current_rules"]


def test_ag50b_preferred_only_current_event_does_not_admit_recovery() -> None:
    admitted, trace = _admission(
        {
            "query_preview": "What happened this week in the transit strike?",
            "query_type": "current_event_context",
        },
        {"source_class_recovery_recommended": False},
    )

    assert admitted is False
    assert trace["admission_skip_reason"] == "preferred_obligation_advisory_only"


def test_ag50b_conceptual_explainer_does_not_admit_recovery() -> None:
    admitted, trace = _admission(
        {"query_preview": "Explain why compound interest matters for beginners."},
        {"source_class_recovery_recommended": False},
    )

    assert admitted is False
    assert trace["admission_skip_reason"] == "obligation_not_required"


def test_ag50b_unknown_obligation_does_not_admit_recovery() -> None:
    admitted, trace = _admission({}, {"source_class_recovery_recommended": False})

    assert admitted is False
    assert trace["admission_considered"] is False
    assert trace["admission_skip_reason"] == "obligation_unknown"


def test_ag50b_aggregate_satisfied_source_class_does_not_block_admission() -> None:
    admitted, trace = _admission(
        {
            "query_preview": "Explain how database MVCC works.",
            "source_class_satisfaction_status": {
                "primary_source_documents": "satisfied_strong"
            },
            "source_class_strong_satisfaction_counts": {
                "primary_source_documents": 1
            },
        },
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
    )

    assert admitted is True
    assert trace["admission_skip_reason"] is None
    assert trace["unsatisfied_required_source_classes"] == [
        "primary_source_documents"
    ]


def test_ag50b_custody_backed_source_class_still_blocks_admission() -> None:
    admitted, trace = _admission(
        {
            "query_preview": "Explain how database MVCC works.",
            "official_current_source_custody": _accepted_custody(
                "primary_source_documents"
            ),
        },
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
    )

    assert admitted is False
    assert trace["admission_skip_reason"] == "existing_source_class_satisfied"
    assert trace["unsatisfied_required_source_classes"] == []


def test_ag50b_prior_recovery_used_blocks_repeated_admission_unless_cap_allows() -> None:
    blocked, blocked_trace = _admission(
        {"query_preview": "Explain how database MVCC works."},
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
        prior_recovery_attempt_count=1,
        max_recovery_attempts=1,
    )
    allowed, allowed_trace = _admission(
        {"query_preview": "Explain how database MVCC works."},
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
        prior_recovery_attempt_count=1,
        max_recovery_attempts=2,
    )

    assert blocked is False
    assert blocked_trace["admission_skip_reason"] == "existing_runtime_blocker"
    assert "budget_hard_exhausted" in blocked_trace["admission_blockers"]
    assert allowed is True
    assert allowed_trace["source_class_recovery_execution_admitted"] is True


def test_ag50b_terminal_stop_blocks_admission() -> None:
    admitted, trace = _admission(
        {"query_preview": "Explain how database MVCC works."},
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
        existing_blockers=("terminal_stop_approved",),
    )

    assert admitted is False
    assert trace["admission_skip_reason"] == "existing_runtime_blocker"
    assert trace["admission_blockers"] == ["terminal_stop_approved"]


def test_ag50b_weak_corpus_ownership_blocks_admission() -> None:
    admitted, trace = _admission(
        {
            "query_preview": "Explain how database MVCC works.",
            "weak_corpus_recovery_used": True,
        },
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
    )

    assert admitted is False
    assert "weak_corpus_recovery_owns_path" in trace["admission_blockers"]


def test_ag50b_conflict_ownership_blocks_admission() -> None:
    admitted, trace = _admission(
        {
            "query_preview": "Explain how database MVCC works.",
            "conflict_resolution_owns_path": True,
        },
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
    )

    assert admitted is False
    assert "conflict_resolution_owns_path" in trace["admission_blockers"]


def test_ag50b_iteration_budget_repair_allows_one_bounded_official_canonical_slot() -> None:
    recommendation = _recommendation(
        missing=["primary_source_documents"],
        queries=["canonical documentation database MVCC"],
    )
    admitted, trace = _admission(
        {"query_preview": "Explain how database MVCC works."},
        recommendation,
        ordinary_iteration_budget_remaining=0,
    )
    decision = decide_source_class_recovery(
        _controller_input(
            recommendation,
            iteration_budget_available=False,
            official_canonical_slot=admitted,
        )
    )

    assert admitted is True
    assert trace["ordinary_iteration_budget_remaining"] == 0
    assert trace["recovery_slot_available"] is True
    assert decision.decision is (
        SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
    )
    assert "blocked_by_iteration_budget" not in decision.blockers


def test_ag50b_hard_recovery_cap_blocks_admission() -> None:
    admitted, trace = _admission(
        {"query_preview": "Explain how database MVCC works."},
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
        prior_recovery_attempt_count=1,
        max_recovery_attempts=1,
    )

    assert admitted is False
    assert "budget_hard_exhausted" in trace["admission_blockers"]


def test_ag50b_query_required_for_execution_admission() -> None:
    admitted, trace = _admission(
        {"query_preview": "Explain how database MVCC works."},
        _recommendation(missing=["primary_source_documents"], queries=[]),
    )

    assert admitted is False
    assert trace["admission_skip_reason"] == "no_recovery_query_available"
    assert trace["recovery_query_available"] is False


def test_ag50b_lifecycle_records_admitted_action_when_iteration_budget_exhausted() -> None:
    controller = RunController()
    trace = record_source_class_recovery_lifecycle(
        controller,
        recommendation=_recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
        recommendation_evaluated=True,
        source_class_evidence_signals={"source_tier_counts": {"secondary": 1}},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=False,
        official_canonical_source_class_slot_available=True,
    )

    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_skip_reason"] is None
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert controller.snapshot_ledger()["retrieval_actions"][0]["provider_role"] == (
        "source_class_recovery"
    )


def test_ag50b_output_does_not_set_provider_depth_ranking_or_answer_behavior() -> None:
    _admitted, trace = _admission(
        {"query_preview": "Explain how database MVCC works."},
        _recommendation(
            missing=["primary_source_documents"],
            queries=["canonical documentation database MVCC"],
        ),
    )
    forbidden_output_keys = {
        "provider_role",
        "provider_name",
        "provider_list",
        "search_depth",
        "ranking_policy",
        "returned_source_classification",
        "final_answer_behavior",
    }

    assert forbidden_output_keys.isdisjoint(trace)
    assert trace["provider_policy_unchanged"] is True
    assert trace["depth_policy_unchanged"] is True
    assert trace["ranking_unchanged"] is True
    assert trace["final_answer_behavior_unchanged"] is True
    assert trace["protected_surface"]["retrieve_targeted_promoted"] is False


def test_ag50b_helper_static_protected_surface_guard() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden_modules = {
        "core.answer_contract_runtime_handoff",
        "core.db",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.provider",
        "core.providers",
        "core.routing",
        "core.run_logging",
        "core.search_providers",
        "core.source_class_recovery_executor",
        "core.source_classifier",
    }

    assert imported.isdisjoint(forbidden_modules)
    assert "build_official_canonical_recovery_execution_admission" in (
        _ACTION_HELPER_PATH.read_text(encoding="utf-8")
    )
    assert "build_authoritative_source_obligation_state_and_action(" in (
        _ORCHESTRATOR_ADAPTER_PATH.read_text(encoding="utf-8")
    )
    assert "build_authoritative_source_action_orchestrator_handoff(" in (
        _PIPELINE_PATH.read_text(encoding="utf-8")
    )


def test_ag50b_overfit_guard_has_no_source_specific_domains_or_branches() -> None:
    module_source = _MODULE_PATH.read_text(encoding="utf-8").casefold()
    forbidden_terms = {
        "sqlite.org",
        "ssa.gov",
        "irs.gov",
        "nasa.gov",
        "postgresql.org",
    }

    assert forbidden_terms.isdisjoint(module_source.split())


def test_ag50b_runtime_projection_mirrors_admission_trace_into_checkpoint() -> None:
    admission_trace = {
        "schema_version": OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_SCHEMA_VERSION,
        "trace_mode": "recovery_execution_admission",
        "OfficialCanonicalRecoveryExecutionAdmission": {
            "admission_used": True
        },
    }
    execution_trace = {
        "run_id": "ag50b",
        OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY: admission_trace,
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
    }

    returned = attach_passive_runtime_projection_traces(execution_trace)

    assert returned is execution_trace
    assert (
        returned[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY
        ]
        == admission_trace
    )
