from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.authoritative_source_forced_corridor_live_classification import (
    build_pre_live_feasibility_checkpoint,
    classify_ag68f_live_case,
    classify_ag68h_cross_case,
    compare_ag68h_irs_to_ag68f_baseline,
    compare_ag68h_ssa_to_ag68f_baseline,
    live_packet_header_is_safe,
)

_ROOT = Path(__file__).resolve().parents[1]
_HELPER_PATH = (
    _ROOT
    / "tests"
    / "helpers"
    / "authoritative_source_forced_corridor_live_classification.py"
)
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

_SSA_QUERY = (
    "What is the current Social Security taxable maximum wage base for 2026, "
    "and what official source supports it? Keep the answer concise."
)
_IRS_QUERY = (
    "What is the current IRS standard mileage rate for business use of a car "
    "in 2026, and what official source supports it? Keep the answer concise."
)
_REPORT_KEYS = (
    "admission_considered",
    "admission_eligible",
    "admission_used",
    "admission_skip_reason",
    "source_class_recovery_eligible",
    "source_class_recovery_used",
    "source_class_recovery_execution_attempted",
    "recovery_query_count",
    "recovered_result_count",
    "accepted_or_readable_official_or_canonical_count",
    "recovered_candidate_selected_readable_count",
    "final_evidence_official_or_canonical_count",
    "final_citation_official_or_canonical_count",
    "next_failure_layer",
)


def _ssa_diagnostics(
    *,
    execution_attempted: str = "true",
    recovery_used: str = "true",
    candidate_return_status: str = "zero_candidates",
    recovered_result_count: int = 0,
    final_evidence_count: int = 0,
    final_citation_count: int = 0,
    next_failure_layer: str = "execution_attempted_zero_candidates",
) -> dict[str, object]:
    return {
        "query": _SSA_QUERY,
        "live_budget_used": "1/2",
        "official_canonical_recovery_visibility_status": "visible",
        "admission_used": "true",
        "source_class_recovery_eligible": "true",
        "source_class_recovery_used": recovery_used,
        "source_class_recovery_execution_attempted": execution_attempted,
        "recovery_query_count": 2,
        "recovered_result_count": recovered_result_count,
        "candidate_return_status": candidate_return_status,
        "candidate_acquisition_considered": execution_attempted,
        "candidate_acquisition_used": recovery_used,
        "accepted_or_readable_official_or_canonical_count": final_evidence_count,
        "recovered_candidate_selected_readable_count": final_evidence_count,
        "final_evidence_official_or_canonical_count": final_evidence_count,
        "final_citation_official_or_canonical_count": final_citation_count,
        "next_failure_layer": next_failure_layer,
    }


def _irs_blocked_diagnostics() -> dict[str, object]:
    return {
        "query": _IRS_QUERY,
        "live_budget_used": "2/2",
        "official_canonical_recovery_visibility_status": "visible",
        "admission_used": "false",
        "admission_skip_reason": "existing_runtime_blocker",
        "admission_blockers": (
            "weak_corpus_recovery_owns_path",
            "blocked_by_corpus_weak",
        ),
        "source_class_recovery_eligible": "false",
        "source_class_recovery_used": "false",
        "source_class_recovery_execution_attempted": "false",
        "source_class_recovery_skip_reason": "blocked_by_weak_corpus_recovery",
        "recovery_query_count": 2,
        "recovered_result_count": 0,
        "candidate_return_status": "not_attempted",
        "candidate_acquisition_considered": "false",
        "candidate_acquisition_used": "false",
        "accepted_or_readable_official_or_canonical_count": 0,
        "recovered_candidate_selected_readable_count": 0,
        "final_evidence_official_or_canonical_count": 0,
        "final_citation_official_or_canonical_count": 0,
        "next_failure_layer": "admission_not_used",
    }


def _classify_ssa(diagnostics: dict[str, object]) -> dict[str, object]:
    return classify_ag68f_live_case(
        case_id="case1_ssa",
        query=_SSA_QUERY,
        diagnostics=diagnostics,
        reliable_forced_corridor_available=True,
        live_budget_used="1/2",
    )


def _classify_irs(diagnostics: dict[str, object]) -> dict[str, object]:
    classification = classify_ag68f_live_case(
        case_id="case2_irs",
        query=_IRS_QUERY,
        diagnostics=diagnostics,
        reliable_forced_corridor_available=True,
        live_budget_used="2/2",
    )
    comparison = compare_ag68h_irs_to_ag68f_baseline(diagnostics)
    return {
        **classification,
        "next_failure_layer": comparison["next_failure_layer"],
    }


def test_ag68h_two_fixed_commands_pass_pre_live_feasibility() -> None:
    ssa = build_pre_live_feasibility_checkpoint(
        live_query=_SSA_QUERY,
        live_command=(
            "py",
            "-m",
            "proplex",
            _SSA_QUERY,
            "--mode",
            "Balanced",
            "--include-domains",
            "shrm.org,payroll.org,adp.com",
            "--output",
            "output/ag68h_case1_ssa_forced_corridor_live_report.md",
        ),
        packet_path="output/ag68h_live_dispatch_reclassification_packet.md",
        ordinary_include_domains=("shrm.org", "payroll.org", "adp.com"),
        recovery_domain_constraints=("ssa.gov", "federalregister.gov"),
        report_diagnostic_keys=_REPORT_KEYS,
    )
    irs = build_pre_live_feasibility_checkpoint(
        live_query=_IRS_QUERY,
        live_command=(
            "py",
            "-m",
            "proplex",
            _IRS_QUERY,
            "--mode",
            "Balanced",
            "--include-domains",
            "taxfoundation.org,hrblock.com,shrm.org",
            "--output",
            "output/ag68h_case2_irs_forced_corridor_live_report.md",
        ),
        packet_path="output/ag68h_live_dispatch_reclassification_packet.md",
        ordinary_include_domains=("taxfoundation.org", "hrblock.com", "shrm.org"),
        recovery_domain_constraints=("irs.gov", "federalregister.gov"),
        report_diagnostic_keys=_REPORT_KEYS,
    )

    assert ssa.passed is True
    assert irs.passed is True
    assert ssa.block_reasons == ()
    assert irs.block_reasons == ()


def test_ag68h_ssa_comparison_detects_dispatch_movement_from_ag68f() -> None:
    comparison = compare_ag68h_ssa_to_ag68f_baseline(
        _ssa_diagnostics(
            candidate_return_status="candidates_returned",
            recovered_result_count=2,
            final_evidence_count=1,
            final_citation_count=1,
            next_failure_layer="recovery_path_succeeded",
        )
    )

    assert comparison["source_class_recovery_execution_attempted_moved_false_to_true"]
    assert comparison["source_class_recovery_used_moved_false_to_true"]
    assert comparison["candidate_return_status_moved_from_not_attempted"]
    assert comparison["recovered_result_count_positive"]
    assert comparison["official_current_evidence_accepted_or_visible"]
    assert comparison["official_current_citation_survived"]
    assert comparison["ag68g_moved_live_product_callsite_failure_layer"]


def test_ag68h_irs_weak_corpus_ownership_classifies_before_dispatch() -> None:
    comparison = compare_ag68h_irs_to_ag68f_baseline(_irs_blocked_diagnostics())

    assert comparison["weak_corpus_ownership_still_blocks_before_admission"]
    assert comparison["irs_reached_dispatch"] is False
    assert comparison["provider_search_review_justified"] is False
    assert comparison["next_failure_layer"] == "weak_corpus_arbitration_ownership"


def test_ag68h_provider_review_requires_actual_dispatch_and_acquisition_failure() -> None:
    ssa = _classify_ssa(
        _ssa_diagnostics(
            candidate_return_status="zero_candidates",
            next_failure_layer="execution_attempted_zero_candidates",
        )
    )

    cross_case = classify_ag68h_cross_case(ssa_case=ssa)

    assert cross_case["ssa_recovery_dispatch_executed"] is True
    assert cross_case["provider_search_review_justified"] is True
    assert cross_case["recommended_next_action"] == "provider_search_allocation_review"


def test_ag68h_one_dispatch_and_one_weak_corpus_block_stays_before_provider_review() -> None:
    ssa = _classify_ssa(
        _ssa_diagnostics(
            candidate_return_status="zero_candidates",
            next_failure_layer="execution_attempted_zero_candidates",
        )
    )
    irs = _classify_irs(_irs_blocked_diagnostics())

    cross_case = classify_ag68h_cross_case(ssa_case=ssa, irs_case=irs)

    assert cross_case["only_one_case_dispatches_recovery"] is True
    assert cross_case["irs_weak_corpus_ownership_still_blocks"] is True
    assert cross_case["provider_search_review_justified"] is False
    assert cross_case["recommended_next_action"] == (
        "focused_generalization_or_arbitration_repair"
    )


def test_ag68h_ordinary_acquisition_remains_separate_from_recovery_success() -> None:
    ordinary = _classify_ssa(
        {
            **_ssa_diagnostics(execution_attempted="false", recovery_used="false"),
            "admission_used": "false",
            "admission_skip_reason": "existing_source_class_satisfied",
            "source_class_recovery_eligible": "false",
            "recovery_query_count": 0,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
        }
    )
    cross_case = classify_ag68h_cross_case(ssa_case=ordinary)

    assert ordinary["ordinary_authoritative_source_already_present"] == "yes"
    assert ordinary["ordinary_acquisition_counted_as_recovery_success"] == "no"
    assert cross_case["ag68g_moved_ssa_live_product_callsite_failure_layer"] is False
    assert cross_case["provider_search_review_justified"] is False


def test_ag68h_packet_hygiene_marker_is_required() -> None:
    assert live_packet_header_is_safe("LOCAL/UNTRACKED \u2014 DO NOT COMMIT\n\nAG-68H")
    assert not live_packet_header_is_safe("AG-68H\nLOCAL/UNTRACKED \u2014 DO NOT COMMIT")


def test_ag68h_static_guard_prevents_protected_surface_drift() -> None:
    tree = ast.parse(_HELPER_PATH.read_text(encoding="utf-8"))
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

    assert imported.isdisjoint(
        {
            "core.pipeline",
            "core.pipeline_orchestrator",
            "core.prompts",
            "core.routing",
            "core.search_providers",
            "core.source_classifier",
            "openai",
            "requests",
        }
    )

    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "select_providers(",
        "choose_supplemental_search_depth(",
        "rank_sources(",
        "build_author_prompt(",
        "build_final_answer(",
        "scrutineer_policy",
        "followup_prompt",
    ):
        assert forbidden not in helper_source

    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "authoritative_source_live_dispatch_reclassification_ag68h" not in (
        pipeline_source
    )
