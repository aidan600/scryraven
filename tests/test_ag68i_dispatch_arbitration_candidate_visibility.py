from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.official_canonical_recovery_execution_admission import (
    build_official_canonical_recovery_execution_admission,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)

_ROOT = Path(__file__).resolve().parents[1]
_VISIBILITY_PATH = _ROOT / "core" / "recovered_evidence_visibility.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _admission_recommendation(
    *,
    missing: list[str] | None = None,
    query: str = "official current agency source for 2026 taxable maximum",
) -> dict[str, Any]:
    required = list(missing or ["official_current_rules"])
    return {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": required,
        "source_class_recovery_reason": (
            "official_canonical_recovery_query_acquisition:" + ",".join(required)
        ),
        "source_class_recovery_queries": [query],
        "source_class_recovery_query_count": 1,
        "official_canonical_acquisition_path_visible": True,
        "source_class_satisfaction_status": {item: "unsatisfied" for item in required},
    }


def _admission_payload(result: Any) -> dict[str, Any]:
    return result.trace["OfficialCanonicalRecoveryExecutionAdmission"]


def _official_recovered_source() -> dict[str, Any]:
    return {
        "title": "Agency official current 2026 rule",
        "url": "https://www.irs.gov/newsroom/example-2026-official-rate",
        "text": (
            "Official agency guidance states the current 2026 rate and "
            "requirements."
        ),
        "source_tier": "official",
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "score": 0.01,
    }


def _official_canonical_lifecycle(**overrides: Any) -> dict[str, Any]:
    lifecycle: dict[str, Any] = {
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_execution_attempted": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_reason": (
            "missing_expected_source_class:official_current_rules"
        ),
        "active_source_class_recovery_skip_reason": None,
        "active_source_class_recovery_blockers": [],
        "active_source_class_recovery_missing_classes": ["official_current_rules"],
        "active_source_class_recovery_attempt_count": 1,
        "active_source_class_recovery_result_count": 1,
        "recovery_source_quality_status": "official_or_primary_found",
        "active_source_class_recovery_action_envelope": {
            "action_type": "recover_missing_source_class",
            "required_source_class": ["official_current_rules"],
            "allowed_action": True,
        },
    }
    lifecycle.update(overrides)
    return lifecycle


def _phase_shape_decision(
    *,
    ssa_surface: str,
    irs_surface: str,
    repaired_surfaces: set[str],
    shared_root_cause: bool = False,
    mechanical_fallout: bool = False,
) -> dict[str, Any]:
    independent = ssa_surface != irs_surface and not (
        shared_root_cause or mechanical_fallout
    )
    both_repaired = repaired_surfaces == {"ssa", "irs"}
    safe = not (independent and both_repaired)
    if independent and repaired_surfaces == {"irs"}:
        classification = "irs_only"
        recommended_next = "ssa_terminal_stop_arbitration_phase"
    elif independent and repaired_surfaces == {"ssa"}:
        classification = "ssa_only"
        recommended_next = "irs_candidate_visibility_source_fit_phase"
    elif both_repaired:
        classification = "shared_root_cause"
        recommended_next = "ag68j_bounded_live_classification"
    else:
        classification = "classification_only"
        recommended_next = "architecture_decision"
    return {
        "safe": safe,
        "classification": classification,
        "recommended_next": recommended_next,
        "independent_surfaces": independent,
        "both_repaired": both_repaired,
    }


def test_ag68i_phase_shape_independent_surfaces_repair_only_irs() -> None:
    decision = _phase_shape_decision(
        ssa_surface="admission_terminal_stop_arbitration",
        irs_surface="post_dispatch_candidate_visibility_source_fit",
        repaired_surfaces={"irs"},
    )

    assert decision["safe"] is True
    assert decision["independent_surfaces"] is True
    assert decision["both_repaired"] is False
    assert decision["classification"] == "irs_only"
    assert decision["recommended_next"] == "ssa_terminal_stop_arbitration_phase"


def test_ag68i_phase_shape_rejects_two_independent_behavior_repairs() -> None:
    decision = _phase_shape_decision(
        ssa_surface="admission_terminal_stop_arbitration",
        irs_surface="post_dispatch_candidate_visibility_source_fit",
        repaired_surfaces={"ssa", "irs"},
    )

    assert decision["safe"] is False
    assert decision["independent_surfaces"] is True
    assert decision["both_repaired"] is True


def test_ag68i_shared_root_cause_guard_allows_both_only_with_shared_seam() -> None:
    decision = _phase_shape_decision(
        ssa_surface="controller_lifecycle_handoff",
        irs_surface="controller_lifecycle_handoff",
        repaired_surfaces={"ssa", "irs"},
        shared_root_cause=True,
    )

    assert decision["safe"] is True
    assert decision["classification"] == "shared_root_cause"


def test_ag68i_ssa_fixture_terminal_stop_blocks_admission_precisely() -> None:
    result = build_official_canonical_recovery_execution_admission(
        recommendation=_admission_recommendation(),
        runtime_trace={"terminal_stop_approved": True},
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=1,
    )
    admission = _admission_payload(result)

    assert result.source_class_recovery_execution_admitted is False
    assert admission["admission_used"] is False
    assert admission["admission_skip_reason"] == "existing_runtime_blocker"
    assert "terminal_stop_approved" in admission["admission_blockers"]


def test_ag68i_terminal_stop_absent_admits_from_controller_facts() -> None:
    result = build_official_canonical_recovery_execution_admission(
        recommendation=_admission_recommendation(),
        runtime_trace={},
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=1,
    )
    admission = _admission_payload(result)

    assert result.source_class_recovery_execution_admitted is True
    assert admission["admission_used"] is True
    assert admission["admission_blockers"] == []


def test_ag68i_weak_corpus_ownership_remains_fail_closed() -> None:
    result = build_official_canonical_recovery_execution_admission(
        recommendation=_admission_recommendation(
            missing=["primary_source_documents"],
            query="canonical project document source",
        ),
        runtime_trace={
            "weak_corpus_recovery_used": True,
            "corpus_weak": True,
            "active_source_class_recovery_blockers": [
                "weak_corpus_recovery_owns_path"
            ],
        },
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=1,
    )
    admission = _admission_payload(result)

    assert result.source_class_recovery_execution_admitted is False
    assert admission["admission_used"] is False
    assert "weak_corpus_recovery_owns_path" in admission["admission_blockers"]
    assert "blocked_by_corpus_weak" in admission["admission_blockers"]


def test_ag68i_ordinary_acquisition_is_not_recovery_success() -> None:
    lifecycle = _official_canonical_lifecycle(
        active_source_class_recovery_used=False,
        active_source_class_recovery_execution_attempted=False,
        active_source_class_recovery_official_canonical_admitted=False,
        active_source_class_recovery_provider_role=None,
        active_source_class_recovery_action_envelope={},
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[
            {
                "title": "Official ordinary source",
                "url": "https://www.ssa.gov/oact/cola/cbb.html",
                "text": "Official current Social Security wage base table.",
                "source_tier": "official",
            }
        ],
        recovered_passages=[],
        lifecycle_trace=lifecycle,
        max_final_evidence=4,
    )

    assert len(final) == 1
    assert decision.used is False
    assert "source_class_recovery_not_used" in decision.blockers


def test_ag68i_irs_fixture_reproduces_post_dispatch_candidate_visibility_gap() -> None:
    lifecycle = _official_canonical_lifecycle(
        active_source_class_recovery_official_canonical_admitted=False,
        active_source_class_recovery_action_envelope={},
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[
            {
                "title": "Secondary mileage analysis",
                "url": "https://analysis.example/mileage-rate",
                "text": "Secondary discussion of the mileage rate.",
                "source_tier": "secondary",
            }
        ],
        recovered_passages=[_official_recovered_source()],
        lifecycle_trace=lifecycle,
        max_final_evidence=4,
    )

    assert [source["url"] for source in final] == [
        "https://analysis.example/mileage-rate"
    ]
    assert decision.considered is True
    assert decision.used is False
    assert decision.source_fit_status == "not_evaluated"
    assert "reason_not_answer_contract_gap" in decision.blockers


def test_ag68i_irs_official_current_candidates_become_recovered_evidence() -> None:
    recovered = _official_recovered_source()
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[
            {
                "title": "Secondary mileage analysis",
                "url": "https://analysis.example/mileage-rate",
                "text": "Secondary discussion of the mileage rate.",
                "source_tier": "secondary",
            }
        ],
        recovered_passages=[recovered],
        lifecycle_trace=_official_canonical_lifecycle(),
        max_final_evidence=4,
    )

    trace = decision.to_trace_fields()
    assert final[-1]["url"] == recovered["url"]
    assert decision.used is True
    assert trace["recovered_visibility_source_fit_status"] == "matched_selected"
    assert trace["recovered_visibility_source_fit_candidate_count"] == 1
    assert trace["recovered_visibility_source_fit_selected_count"] == 1
    export = build_official_canonical_recovery_visibility_export(
        {
            **_official_canonical_lifecycle(),
            **trace,
            "recovered_source_class_counts": {"official_current_rules": 1},
            "active_source_class_recovery_result_count": 1,
            "source_survival_final_evidence_official_or_canonical_count": 1,
        }
    )
    assert export["recovered_candidate_source_fit_status"] == "matched_selected"
    assert export["recovered_candidate_selected_readable_count"] == 1
    assert export["accepted_or_readable_official_or_canonical_count"] == 1


def test_ag68i_candidate_visibility_repair_does_not_touch_routing_or_query_policy() -> None:
    tree = ast.parse(_VISIBILITY_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported.isdisjoint(
        {
            "openai",
            "requests",
            "core.pipeline_orchestrator",
            "core.prompts",
            "core.routing",
            "core.search_providers",
            "core.source_classifier",
        }
    )
    visibility_source = _VISIBILITY_PATH.read_text(encoding="utf-8").casefold()
    assert "select_providers(" not in visibility_source
    assert "choose_supplemental_search_depth(" not in visibility_source
    assert "rank_sources(" not in visibility_source
    assert "build_author_prompt(" not in visibility_source
    assert "build_final_answer(" not in visibility_source
    assert "ag68i" not in _PIPELINE_PATH.read_text(encoding="utf-8").casefold()


def test_ag68i_recovered_visibility_trace_shape_is_preserved() -> None:
    _final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=[_official_recovered_source()],
        lifecycle_trace=_official_canonical_lifecycle(),
        max_final_evidence=4,
    )
    trace = decision.to_trace_fields()

    assert {
        "recovered_visibility_considered",
        "recovered_visibility_eligible",
        "recovered_visibility_used",
        "recovered_visibility_reason",
        "recovered_visibility_source_fit_status",
        "recovered_visibility_source_fit_candidate_count",
        "recovered_visibility_source_fit_selected_count",
        "recovered_visibility_source_fit_rejection_reasons",
    } <= set(trace)
