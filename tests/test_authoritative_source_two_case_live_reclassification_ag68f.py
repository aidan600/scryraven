from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.authoritative_source_forced_corridor_live_classification import (
    build_pre_live_feasibility_checkpoint,
    classify_ag68f_cross_case,
    classify_ag68f_live_case,
    compare_ag68f_irs_to_prior_live_baselines,
    live_packet_header_is_safe,
)

_ROOT = Path(__file__).resolve().parents[1]
_HELPER_PATH = _ROOT / "tests" / "helpers" / "authoritative_source_forced_corridor_live_classification.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

_IRS_QUERY = (
    "What is the current IRS standard mileage rate for business use of a car "
    "in 2026, and what official source supports it? Keep the answer concise."
)
_SSA_QUERY = (
    "What is the current Social Security taxable maximum wage base for 2026, "
    "and what official source supports it? Keep the answer concise."
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


def _case(
    *,
    case_id: str,
    execution_attempted: str,
    recovery_used: str = "false",
    candidate_return_status: str = "not_attempted",
    recovered_result_count: int = 0,
    final_evidence_count: int = 0,
    final_citation_count: int = 0,
    next_failure_layer: str = "execution_not_attempted",
) -> dict[str, object]:
    return classify_ag68f_live_case(
        case_id=case_id,
        query=_IRS_QUERY if case_id == "case1_irs" else _SSA_QUERY,
        reliable_forced_corridor_available=True,
        live_budget_used="1/2" if case_id == "case1_irs" else "2/2",
        diagnostics={
            "official_canonical_recovery_visibility_status": "visible",
            "admission_used": "true",
            "source_class_recovery_eligible": "true",
            "source_class_recovery_used": recovery_used,
            "source_class_recovery_execution_attempted": execution_attempted,
            "recovery_query_count": 4,
            "recovered_result_count": recovered_result_count,
            "candidate_return_status": candidate_return_status,
            "candidate_acquisition_considered": ("true" if execution_attempted == "true" else "false"),
            "candidate_acquisition_used": recovery_used,
            "accepted_or_readable_official_or_canonical_count": final_evidence_count,
            "recovered_candidate_selected_readable_count": final_evidence_count,
            "final_evidence_official_or_canonical_count": final_evidence_count,
            "final_citation_official_or_canonical_count": final_citation_count,
            "next_failure_layer": next_failure_layer,
        },
    )


def test_ag68f_two_fixed_commands_pass_pre_live_feasibility() -> None:
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
            "output/ag68f_case1_irs_forced_corridor_live_report.md",
        ),
        packet_path="output/ag68f_two_case_forced_corridor_live_packet.md",
        ordinary_include_domains=("taxfoundation.org", "hrblock.com", "shrm.org"),
        recovery_domain_constraints=("irs.gov", "federalregister.gov"),
        report_diagnostic_keys=_REPORT_KEYS,
    )
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
            "output/ag68f_case2_ssa_forced_corridor_live_report.md",
        ),
        packet_path="output/ag68f_two_case_forced_corridor_live_packet.md",
        ordinary_include_domains=("shrm.org", "payroll.org", "adp.com"),
        recovery_domain_constraints=("ssa.gov", "federalregister.gov"),
        report_diagnostic_keys=_REPORT_KEYS,
    )

    assert irs.passed is True
    assert ssa.passed is True
    assert irs.block_reasons == ()
    assert ssa.block_reasons == ()


def test_ag68f_case_classifier_preserves_required_fields() -> None:
    classification = _case(
        case_id="case1_irs",
        execution_attempted="true",
        recovery_used="true",
        candidate_return_status="candidates_returned",
        recovered_result_count=2,
        final_evidence_count=1,
        final_citation_count=1,
        next_failure_layer="recovery_path_succeeded",
    )

    assert classification["case_id"] == "case1_irs"
    assert classification["query"] == _IRS_QUERY
    assert classification["reliable_forced_corridor_available"] == "yes"
    assert classification["ordinary_authoritative_source_already_present"] == "no"
    assert classification["missing_authoritative_source_state_forced"] == "yes"
    assert classification["authoritative_recovery_bridge_visible"] == "yes"
    assert classification["authoritative_recovery_query_created"] == "yes"
    assert classification["recovery_execution_admitted"] == "yes"
    assert classification["recovery_dispatch_authorized_or_attempted"] == "yes"
    assert classification["source_class_recovery_execution_attempted"] == "yes"
    assert classification["source_class_recovery_used"] == "yes"
    assert classification["candidate_return_status"] == "candidates_returned"
    assert classification["recovered_evidence_visible"] == "yes"
    assert classification["final_answer_citation_or_use"] == "yes"
    assert classification["ordinary_acquisition_counted_as_recovery_success"] == "no"


def test_ag68f_irs_comparison_marks_dispatch_movement_after_ag68e() -> None:
    comparison = compare_ag68f_irs_to_prior_live_baselines(
        {
            "admission_used": "true",
            "source_class_recovery_used": "true",
            "source_class_recovery_execution_attempted": "true",
            "recovered_result_count": 0,
            "candidate_return_status": "zero_candidates",
            "final_evidence_official_or_canonical_count": 0,
            "final_citation_official_or_canonical_count": 0,
            "next_failure_layer": "execution_attempted_zero_candidates",
        }
    )

    assert comparison["admission_used_remained_true"] is True
    assert comparison["source_class_recovery_execution_attempted_moved_false_to_true"] is True
    assert comparison["source_class_recovery_used_moved_false_to_true"] is True
    assert comparison["candidate_return_status_moved_from_not_attempted"] is True
    assert comparison["recovered_result_count_positive"] is False
    assert comparison["provider_search_review_justified"] is True


def test_ag68f_provider_review_requires_both_cases_to_dispatch_and_zero_candidates() -> None:
    irs = _case(
        case_id="case1_irs",
        execution_attempted="true",
        recovery_used="true",
        candidate_return_status="zero_candidates",
        next_failure_layer="execution_attempted_zero_candidates",
    )
    ssa = _case(
        case_id="case2_ssa",
        execution_attempted="true",
        recovery_used="true",
        candidate_return_status="zero_candidates",
        next_failure_layer="execution_attempted_zero_candidates",
    )

    cross_case = classify_ag68f_cross_case(irs, ssa)

    assert cross_case["both_cases_dispatch_recovery"] is True
    assert cross_case["provider_search_review_justified"] is True
    assert cross_case["recommended_next_action"] == "provider_search_allocation_review"


def test_ag68f_provider_review_stays_closed_without_actual_dispatch() -> None:
    irs = _case(case_id="case1_irs", execution_attempted="false")
    ssa = _case(case_id="case2_ssa", execution_attempted="false")

    cross_case = classify_ag68f_cross_case(irs, ssa)

    assert cross_case["neither_case_dispatches_recovery"] is True
    assert cross_case["ag68e_moved_live_failure_layer"] is False
    assert cross_case["provider_search_review_justified"] is False
    assert cross_case["recommended_next_action"] == ("focused_live_product_dispatch_repair")


def test_ag68f_single_case_dispatch_recommends_generalization_before_provider_review() -> None:
    irs = _case(
        case_id="case1_irs",
        execution_attempted="true",
        recovery_used="true",
        candidate_return_status="zero_candidates",
        next_failure_layer="execution_attempted_zero_candidates",
    )
    ssa = _case(case_id="case2_ssa", execution_attempted="false")

    cross_case = classify_ag68f_cross_case(irs, ssa)

    assert cross_case["only_one_case_dispatches_recovery"] is True
    assert cross_case["provider_search_review_justified"] is False
    assert cross_case["recommended_next_action"] == ("focused_official_current_numeric_rule_generalization")


def test_ag68f_packet_hygiene_marker_is_required() -> None:
    assert live_packet_header_is_safe("LOCAL/UNTRACKED \u2014 DO NOT COMMIT\n\nAG-68F")
    assert not live_packet_header_is_safe("AG-68F\nLOCAL/UNTRACKED \u2014 DO NOT COMMIT")


def test_ag68f_static_guard_prevents_protected_surface_drift() -> None:
    tree = ast.parse(_HELPER_PATH.read_text(encoding="utf-8"))
    imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    imported.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)

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
    assert "authoritative_source_two_case_live_reclassification" not in (pipeline_source)
