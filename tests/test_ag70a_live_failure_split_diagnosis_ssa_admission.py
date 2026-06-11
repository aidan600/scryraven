from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action import (
    AuthoritativeSourceActionFacts,
    build_authoritative_source_obligation_state_and_action,
)
from core.authoritative_source_action_orchestrator_adapter import (
    build_authoritative_source_action_facts_from_orchestrator_state,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    build_controller_loop_spine_result,
)
from core.official_canonical_recovery_execution_admission import (
    build_official_canonical_recovery_execution_admission,
)
from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.run_controller import RunController

_ROOT = Path(__file__).resolve().parents[1]
_ACTION_PATH = _ROOT / "core" / "authoritative_source_action.py"
_ADAPTER_PATH = _ROOT / "core" / "authoritative_source_action_orchestrator_adapter.py"
_ADMISSION_PATH = _ROOT / "core" / "official_canonical_recovery_execution_admission.py"
_QUERY_ACQUISITION_PATH = _ROOT / "core" / "official_canonical_recovery_query_acquisition.py"
_CANDIDATE_VISIBILITY_PATH = _ROOT / "core" / "authority_lifecycle_candidate_visibility.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

_SSA_QUERY = (
    "What is the current Social Security taxable maximum wage base for 2026, "
    "and what official source supports it? Keep the answer concise."
)
_UPSTREAM_SSA_QUERY = (
    "official SSA taxable maximum wage base 2026 supporting source"
)


def _recommendation(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": ["official_current_rules"],
        "source_class_recovery_queries": [],
        "source_class_recovery_query_count": 0,
        "source_class_recovery_reason": "source_class_recovery:ssa_official_gap",
        "source_class_recovery_trigger_fields": ["runtime_source_class_expectation"],
    }
    payload.update(overrides)
    return payload


def _observability() -> dict[str, Any]:
    return {
        "source_class_satisfaction_status": {
            "official_current_rules": "expected_but_only_secondary"
        },
        "source_class_strong_satisfaction_counts": {"official_current_rules": 0},
        "source_class_gap_candidates": ["official_current_rules"],
    }


def _answer_contract_result(
    *,
    next_queries: tuple[str, ...] = (_UPSTREAM_SSA_QUERY,),
    source_classes_missing: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        adapter_result=SimpleNamespace(
            contract=SimpleNamespace(
                family=SimpleNamespace(value="current_official_rules")
            )
        ),
        state=SimpleNamespace(
            evidence_state_summary=SimpleNamespace(
                source_classes_missing=source_classes_missing,
                next_queries=next_queries,
            )
        ),
        fulfillment_handoff=SimpleNamespace(
            unfulfilled_items=("official current source",),
            partial_items=("secondary context only",),
        ),
    )


def _facts(
    *,
    recommendation: dict[str, Any] | None = None,
    upstream_queries: tuple[str, ...] = (_UPSTREAM_SSA_QUERY,),
    terminal_stop_approved: bool = False,
    corpus_weak: bool = False,
    weak_corpus_recovery_used: bool = False,
) -> AuthoritativeSourceActionFacts:
    return AuthoritativeSourceActionFacts(
        query=_SSA_QUERY,
        intent="general",
        report_type="answer",
        query_type="official_current_status",
        core_topic="Social Security taxable maximum wage base for 2026",
        primary_entity="Social Security Administration",
        recommendation=recommendation or _recommendation(),
        source_class_observability=_observability(),
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 3},
            "source_domain_counts": {"payroll.example": 2},
            "top_source_domains": [{"domain": "payroll.example", "count": 2}],
            "unique_source_domain_count": 1,
            "on_domain_source_count": 0,
            "off_domain_source_count": 1,
            "official_evidence_found": False,
            "community_signal_found": False,
            "low_trust_sources_found": False,
            "pollution_detected": False,
        },
        corpus_state="OFF_TOPIC" if corpus_weak else "HEALTHY",
        corpus_weak=corpus_weak,
        weak_corpus_recovery_considered=weak_corpus_recovery_used,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=(
            "weak_corpus_recovery_used" if weak_corpus_recovery_used else None
        ),
        current_search_depth="basic",
        iteration_budget_available=False,
        answer_contract_recovery_query_candidates=upstream_queries,
        terminal_stop_approved=terminal_stop_approved,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    )


def _handoff(facts: AuthoritativeSourceActionFacts) -> Any:
    return build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=facts,
    )


def _spine(lifecycle: dict[str, Any], *, action_name: str) -> Any:
    return build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": {"action_name": action_name},
            "recommended_action_name": action_name,
            "terminal_stop_approved": action_name == STOP_INSUFFICIENT_WITH_CAVEAT,
        },
        source_class_lifecycle_trace=lifecycle,
        weak_corpus_lifecycle_trace={
            "approved": True,
            "reason": "weak fixture",
            "blockers": [],
        },
    )


def test_ssa_shaped_required_recovery_promotes_upstream_query_candidate() -> None:
    result = _handoff(_facts())
    acquisition = result.official_canonical_recovery_query_acquisition_trace[
        "OfficialCanonicalRecoveryQueryAcquisition"
    ]

    assert result.recommendation["source_class_recovery_queries"] == [
        _UPSTREAM_SSA_QUERY
    ]
    assert acquisition["promoted_recovery_query_count"] == 1
    assert acquisition["executable_recovery_query_count"] == 1
    assert result.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_queries"
    ] == [_UPSTREAM_SSA_QUERY]


def test_required_recovery_with_upstream_query_does_not_end_missing_executable() -> None:
    result = _handoff(_facts())
    lifecycle = result.active_source_class_recovery_lifecycle

    assert result.official_canonical_recovery_execution_admitted is True
    assert lifecycle["active_source_class_recovery_eligible"] is True
    assert lifecycle["active_source_class_recovery_skip_reason"] is None
    assert lifecycle["authority_lifecycle"]["recovery_query_count"] == 1
    assert lifecycle["authority_lifecycle"]["explicit_blockers"] == []


def test_query_surfacing_feeds_acquisition_path_visibility_and_admission() -> None:
    result = _handoff(_facts())
    admission = result.official_canonical_recovery_execution_admission_trace[
        "OfficialCanonicalRecoveryExecutionAdmission"
    ]

    assert admission["admission_acquisition_path_visible"] is True
    assert admission["recovery_query_available"] is True
    assert admission["recovery_query_previews"] == [_UPSTREAM_SSA_QUERY]
    assert admission["admission_used"] is True


def test_admission_requires_promoted_lifecycle_query_not_projection_preview() -> None:
    recommendation = _recommendation()
    runtime_trace = {
        "query_preview": _SSA_QUERY,
        "query_type": "official_current_status",
        "core_topic": "Social Security taxable maximum wage base for 2026",
        "primary_entity": "Social Security Administration",
        "candidate_query_previews": [_UPSTREAM_SSA_QUERY],
        "official_canonical_recovery_query_acquisition_trace": {
            "OfficialCanonicalRecoveryQueryAcquisition": {
                "acquisition_repair_used": True
            }
        },
        **recommendation,
        **_observability(),
    }
    projection_only = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace=runtime_trace,
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
    ).trace["OfficialCanonicalRecoveryExecutionAdmission"]

    acquired = apply_official_canonical_recovery_query_acquisition(
        recommendation=recommendation,
        runtime_trace=runtime_trace,
    ).recommendation
    lifecycle_owned = build_official_canonical_recovery_execution_admission(
        recommendation=acquired,
        runtime_trace={**runtime_trace, **acquired},
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
    ).trace["OfficialCanonicalRecoveryExecutionAdmission"]

    assert projection_only["admission_used"] is False
    assert projection_only["recovery_query_available"] is False
    assert projection_only["admission_skip_reason"] == "no_recovery_query_available"
    assert lifecycle_owned["admission_used"] is True
    assert lifecycle_owned["recovery_query_previews"] == [_UPSTREAM_SSA_QUERY]


def test_no_executable_query_records_requirement_bound_lifecycle_blocker() -> None:
    trace = build_authority_runtime_arbitration(
        requirement_id="official_current_rules",
        required_authority="official_current_rules",
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=(),
        required_source_classes=("official_current_rules",),
        recovery_action_allowed=True,
    ).to_trace_fields()
    blocker = trace["authority_lifecycle_execution_blocker"]

    assert trace["authority_lifecycle_required_recovery_allowed"] is False
    assert blocker["requirement_id"] == "official_current_rules"
    assert blocker["owner"] == "controller/lifecycle"
    assert blocker["blocker_reason"] == "missing_executable_recovery_query"
    assert blocker["recovery_may_be_retried"] is True


def test_terminal_stop_blocks_but_weak_corpus_cannot_preempt_surfaced_recovery() -> None:
    terminal = _handoff(_facts(terminal_stop_approved=True))
    weak = _handoff(_facts(corpus_weak=True, weak_corpus_recovery_used=True))

    terminal_spine = _spine(
        terminal.active_source_class_recovery_lifecycle,
        action_name=STOP_INSUFFICIENT_WITH_CAVEAT,
    )
    weak_spine = _spine(
        weak.active_source_class_recovery_lifecycle,
        action_name=RECOVER_WEAK_CORPUS,
    )

    assert terminal.official_canonical_recovery_execution_admitted is False
    assert weak.official_canonical_recovery_execution_admitted is True
    assert terminal_spine.authorized_dispatch is None
    assert weak_spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS


def test_lower_tier_evidence_remains_context_not_official_satisfaction() -> None:
    result = _handoff(_facts())
    lifecycle = result.active_source_class_recovery_lifecycle["authority_lifecycle"]

    assert result.obligation_state.satisfaction_for(
        "official_current_rules"
    ).status.value != "fulfilled"
    assert lifecycle["existing_evidence_fit"] == "missing"
    assert lifecycle["satisfaction_state"] == "unsatisfied"


def test_irs_candidate_fit_visibility_surface_is_not_repaired_by_ag70a() -> None:
    trace = build_authority_runtime_arbitration(
        requirement_id="official_current_rules",
        required_authority="official_current_rules",
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=("IRS 2026 standard mileage rate official source",),
        required_source_classes=("official_current_rules",),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace.update(
        {
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_missing_classes": [
                "official_current_rules"
            ],
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": ["official_current_rules"],
                "allowed_action": True,
            },
        }
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[
            {
                "url": "https://www.shrm.org/context",
                "title": "Context",
                "text": "Secondary context.",
                "source_tier": "secondary",
            }
        ],
        recovered_passages=[
            {
                "url": "https://www.irs.gov/ag70a-candidate",
                "title": "IRS candidate already visible",
                "text": "Official fixture.",
                "source_tier": "official",
                "source_class": "official_current_rules",
                "retrieval_stage": "source_class_recovery",
                "_provider_role": "source_class_recovery",
            }
        ],
        lifecycle_trace=trace,
        max_final_evidence=1,
    )

    assert final
    fields = decision.to_trace_fields()
    assert fields["recovered_visibility_source_fit_status"] == "no_matching_source_fit"
    assert fields["recovered_visibility_source_fit_selected_count"] == 0


def test_orchestrator_adapter_surfaces_answer_contract_next_queries() -> None:
    facts = build_authoritative_source_action_facts_from_orchestrator_state(
        RunController(),
        orchestrator_state={
            "query": _SSA_QUERY,
            "intent": "general",
            "report_type": "answer",
            "query_type": "official_current_status",
            "core_topic": "Social Security taxable maximum wage base for 2026",
            "primary_entity": "Social Security Administration",
            "_source_class_recovery_lifecycle_recommendation": _recommendation(),
            "_source_class_recovery_answer_contract_observability": _observability(),
            "_source_tier_recovery_lifecycle": {},
            "_source_domain_recovery_lifecycle": {},
            "_pre_recovery_answer_contract_result": _answer_contract_result(),
            "corpus_state": "HEALTHY",
            "corpus_weak": False,
            "weak_corpus_recovery_considered": False,
            "weak_corpus_recovery_used": False,
            "weak_corpus_recovery_skip_reason": None,
            "evidence_integration_checkpoint_trace": {},
            "current_search_depth_for_recovery": "basic",
            "iterations_run": 0,
            "max_iterations": 1,
            "waste_flags": [],
        },
    )

    assert facts.answer_contract_recovery_query_candidates == (_UPSTREAM_SSA_QUERY,)


def test_ag70a_protected_surfaces_and_docs_remain_in_scope() -> None:
    docs = (
        _ROOT
        / "docs"
        / "validation"
        / "AG70A_LIVE_FAILURE_SPLIT_DIAGNOSIS_SSA_ADMISSION.md"
    )
    for path in (
        _ACTION_PATH,
        _ADAPTER_PATH,
        _ADMISSION_PATH,
        _QUERY_ACQUISITION_PATH,
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
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

    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8").casefold()
    query_source = _QUERY_ACQUISITION_PATH.read_text(encoding="utf-8").casefold()
    candidate_visibility_source = _CANDIDATE_VISIBILITY_PATH.read_text(
        encoding="utf-8"
    ).casefold()

    assert docs.exists()
    assert "ag69f_bounded_live_controller_lifecycle_validation" not in query_source
    assert "standard mileage" not in candidate_visibility_source
    assert "candidate_fit" not in pipeline_source
    assert "build_final_answer(" not in query_source
