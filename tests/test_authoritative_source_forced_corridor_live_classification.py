from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers.authoritative_source_forced_corridor_live_classification import (
    build_pre_live_feasibility_checkpoint,
    classify_allowed_live_report_diagnostics,
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

_LIVE_QUERY = (
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


def _checkpoint() -> object:
    return build_pre_live_feasibility_checkpoint(
        live_query=_LIVE_QUERY,
        live_command=(
            "py",
            "-m",
            "proplex",
            _LIVE_QUERY,
            "--mode",
            "Balanced",
            "--include-domains",
            "taxfoundation.org,hrblock.com,shrm.org",
            "--output",
            "output/ag67b_forced_corridor_live_report.md",
        ),
        packet_path="output/ag67b_forced_corridor_live_packet.md",
        ordinary_include_domains=("taxfoundation.org", "hrblock.com", "shrm.org"),
        recovery_domain_constraints=("irs.gov", "federalregister.gov"),
        report_diagnostic_keys=_REPORT_KEYS,
    )


def test_pre_live_feasibility_checkpoint_answers_all_a_to_g() -> None:
    checkpoint = _checkpoint()

    assert checkpoint.passed is True
    assert checkpoint.block_reasons == ()
    assert set(checkpoint.answers) == {"A", "B", "C", "D", "E", "F", "G"}
    assert all(checkpoint.answers.values())


def test_pre_live_feasibility_checkpoint_blocks_when_answers_are_missing() -> None:
    checkpoint = build_pre_live_feasibility_checkpoint(
        live_query=_LIVE_QUERY,
        live_command=("py", "-m", "proplex", _LIVE_QUERY),
        packet_path="output/ag67b_forced_corridor_live_packet.md",
        ordinary_include_domains=(),
        recovery_domain_constraints=(),
        report_diagnostic_keys=("admission_used",),
    )

    assert checkpoint.passed is False
    assert "ordinary_allow_list_present" in checkpoint.block_reasons
    assert "official_recovery_domain_constraints_present" in checkpoint.block_reasons
    assert "report_diagnostics_cover_required_layers" in checkpoint.block_reasons
    assert "all_checkpoint_answers_present" in checkpoint.block_reasons


def test_live_report_classification_distinguishes_ordinary_acquisition() -> None:
    classification = classify_allowed_live_report_diagnostics(
        {
            "admission_used": "false",
            "admission_skip_reason": "existing_source_class_satisfied",
            "source_class_recovery_execution_attempted": "false",
            "recovery_query_count": 0,
            "recovered_result_count": 0,
            "final_evidence_official_or_canonical_count": 5,
            "final_citation_official_or_canonical_count": 2,
            "next_failure_layer": "admission_not_used",
        }
    )

    assert classification["ordinary_authoritative_source_already_present"] == "yes"
    assert classification["missing_authoritative_source_state_forced"] == "no"
    assert classification["recovery_execution_admitted"] == "no"
    assert classification["recovery_dispatch_authorized_or_attempted"] == "no"
    assert classification["recovered_evidence_visible"] == "not_applicable"
    assert classification["recovery_path_success"] == "no"
    assert classification["ordinary_acquisition_counted_as_recovery_success"] == "no"
    assert classification["next_failure_layer"] == "ordinary_acquisition_only"


def test_live_report_classification_requires_recovery_execution_for_success() -> None:
    classification = classify_allowed_live_report_diagnostics(
        {
            "admission_used": "true",
            "source_class_recovery_eligible": "true",
            "source_class_recovery_execution_attempted": "true",
            "recovery_query_count": 2,
            "recovered_result_count": 3,
            "accepted_or_readable_official_or_canonical_count": 1,
            "recovered_candidate_selected_readable_count": 1,
            "final_evidence_official_or_canonical_count": 1,
            "final_citation_official_or_canonical_count": 1,
            "next_failure_layer": "canonical_source_cited",
        }
    )

    assert classification["ordinary_authoritative_source_already_present"] == "no"
    assert classification["missing_authoritative_source_state_forced"] == "yes"
    assert classification["authoritative_recovery_query_created"] == "yes"
    assert classification["recovery_execution_admitted"] == "yes"
    assert classification["recovery_dispatch_authorized_or_attempted"] == "yes"
    assert classification["recovered_evidence_visible"] == "yes"
    assert classification["final_answer_citation_or_use"] == "yes"
    assert classification["recovery_path_success"] == "yes"


def test_live_report_classification_exposes_admission_to_dispatch_gap() -> None:
    classification = classify_allowed_live_report_diagnostics(
        {
            "admission_used": "true",
            "source_class_recovery_eligible": "true",
            "source_class_recovery_execution_attempted": "false",
            "recovery_query_count": 1,
            "recovered_result_count": 0,
            "final_citation_official_or_canonical_count": 0,
            "next_failure_layer": "execution_not_attempted",
        }
    )

    assert classification["missing_authoritative_source_state_forced"] == "yes"
    assert classification["recovery_execution_admitted"] == "yes"
    assert classification["recovery_dispatch_authorized_or_attempted"] == "no"
    assert classification["recovered_evidence_visible"] == "no"
    assert classification["recovery_path_success"] == "no"
    assert classification["next_failure_layer"] == "execution_not_attempted"


def test_live_packet_hygiene_helpers_are_local_output_safe() -> None:
    assert live_packet_header_is_safe(
        "LOCAL/UNTRACKED — DO NOT COMMIT\n\nclassification"
    )
    assert not live_packet_header_is_safe("classification")
    assert _checkpoint().passed is True


def test_ag67b_static_guard_keeps_protected_surfaces_closed() -> None:
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
            "openai",
            "requests",
        }
    )

    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "select_providers(",
        "rank_sources(",
        "build_author_prompt(",
        "build_final_answer(",
        "scrutineer_policy",
        "followup_prompt",
    ):
        assert forbidden not in helper_source

    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "authoritative_source_forced_corridor_live_classification" not in (
        pipeline_source
    )
