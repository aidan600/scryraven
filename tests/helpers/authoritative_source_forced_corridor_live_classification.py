"""Test-only AG-67B live forced-corridor classification helpers.

These helpers classify sanitized CLI/report-visible diagnostics. They do not
retrieve, route providers, choose depth, rank/filter sources, alter prompts,
read logs, inspect secrets, or affect final-answer behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

AG67B_LIVE_CLASSIFICATION_SCHEMA_VERSION = (
    "authoritative_source_forced_corridor_live_classification_ag67b_v1"
)
AG68B_LIVE_RECLASSIFICATION_SCHEMA_VERSION = (
    "authoritative_source_forced_corridor_live_reclassification_ag68b_v1"
)
AG68D_LIVE_RECLASSIFICATION_SCHEMA_VERSION = (
    "authoritative_source_forced_corridor_live_reclassification_ag68d_v1"
)
AG68F_LIVE_RECLASSIFICATION_SCHEMA_VERSION = (
    "authoritative_source_two_case_live_reclassification_ag68f_v1"
)
AG68H_LIVE_RECLASSIFICATION_SCHEMA_VERSION = (
    "authoritative_source_live_dispatch_reclassification_ag68h_v1"
)

_UNKNOWN = "unknown"
_YES = "yes"
_NO = "no"
_NA = "not_applicable"
_PACKET_MARKER = "LOCAL/UNTRACKED \u2014 DO NOT COMMIT"


@dataclass(frozen=True)
class PreLiveFeasibilityCheckpoint:
    """Concise A-G checkpoint result for deciding whether live use is allowed."""

    answers: dict[str, str]
    passed: bool
    block_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": AG67B_LIVE_CLASSIFICATION_SCHEMA_VERSION,
            "answers": dict(self.answers),
            "passed": self.passed,
            "block_reasons": list(self.block_reasons),
        }


def build_pre_live_feasibility_checkpoint(
    *,
    live_query: str,
    live_command: Sequence[str],
    packet_path: str,
    ordinary_include_domains: Sequence[str],
    recovery_domain_constraints: Sequence[str],
    report_diagnostic_keys: Sequence[str],
) -> PreLiveFeasibilityCheckpoint:
    """Return whether the proposed live command can distinguish the corridor."""

    command = tuple(str(part) for part in live_command)
    diagnostics = {str(key) for key in report_diagnostic_keys}
    include_domains = tuple(
        str(domain).strip().casefold()
        for domain in ordinary_include_domains
        if str(domain).strip()
    )
    recovery_domains = tuple(
        str(domain).strip().casefold()
        for domain in recovery_domain_constraints
        if str(domain).strip()
    )

    has_output = "--output" in command and _safe_live_packet_path(packet_path)
    has_include = "--include-domains" in command and bool(include_domains)
    has_official_recovery_domain = any(
        domain.endswith(".gov") or domain == "irs.gov" for domain in recovery_domains
    )
    has_stage_diagnostics = _required_diagnostics_present(diagnostics)
    exact_query = bool(str(live_query).strip())

    answers = {
        "A": (
            "CLI include-domain allow-list bounds ordinary acquisition to "
            "lower-tier context domains; the existing source-class recovery "
            "executor can add official recovery domain constraints."
            if has_include and has_official_recovery_domain
            else ""
        ),
        "B": (
            "Report diagnostics can prove the missing-authoritative state by "
            "admission_used=true and recovery_query_count>0, which AG-50B "
            "only emits after an unsatisfied required class is visible."
            if "admission_used" in diagnostics and "recovery_query_count" in diagnostics
            else ""
        ),
        "C": (
            "admission_considered/admission_eligible/admission_used and "
            "source_class_recovery_eligible prove readiness/admission."
            if {
                "admission_considered",
                "admission_eligible",
                "admission_used",
                "source_class_recovery_eligible",
            }
            <= diagnostics
            else ""
        ),
        "D": (
            "source_class_recovery_execution_attempted and "
            "source_class_recovery_used prove dispatch was authorized or "
            "attempted through the controller/executor path."
            if {
                "source_class_recovery_execution_attempted",
                "source_class_recovery_used",
            }
            <= diagnostics
            else ""
        ),
        "E": (
            "recovered_result_count, accepted_or_readable_official_or_canonical_count, "
            "recovered_candidate_selected_readable_count, and final evidence/citation "
            "counts classify recovered evidence visibility."
            if {
                "recovered_result_count",
                "accepted_or_readable_official_or_canonical_count",
                "recovered_candidate_selected_readable_count",
                "final_evidence_official_or_canonical_count",
                "final_citation_official_or_canonical_count",
            }
            <= diagnostics
            else ""
        ),
        "F": (
            "Ordinary acquisition is classified separately when admission_used=false "
            "with admission_skip_reason=existing_source_class_satisfied and final "
            "official/canonical evidence or citation counts are positive."
            if {
                "admission_skip_reason",
                "final_evidence_official_or_canonical_count",
                "final_citation_official_or_canonical_count",
            }
            <= diagnostics
            else ""
        ),
        "G": (
            "The command uses the exact fixed query plus an ordinary allow-list "
            "corridor and an ignored output packet, so success can be separated "
            "from ordinary official-source acquisition."
            if exact_query and has_include and has_output
            else ""
        ),
    }
    checks = {
        "exact_live_query_present": exact_query,
        "ignored_output_packet_path": has_output,
        "ordinary_allow_list_present": has_include,
        "official_recovery_domain_constraints_present": has_official_recovery_domain,
        "report_diagnostics_cover_required_layers": has_stage_diagnostics,
        "all_checkpoint_answers_present": all(answers.values()),
    }
    block_reasons = tuple(key for key, ok in checks.items() if not ok)
    return PreLiveFeasibilityCheckpoint(
        answers=answers,
        passed=not block_reasons,
        block_reasons=block_reasons,
    )


def classify_allowed_live_report_diagnostics(
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify sanitized report-visible recovery diagnostics."""

    admission_used = _boolish(diagnostics.get("admission_used"))
    execution_attempted = _boolish(
        diagnostics.get("source_class_recovery_execution_attempted")
    )
    recovery_query_count = _intish(diagnostics.get("recovery_query_count"))
    selected_recovered = _intish(
        diagnostics.get("recovered_candidate_selected_readable_count")
    )
    accepted_official = _intish(
        diagnostics.get("accepted_or_readable_official_or_canonical_count")
    )
    final_evidence = _intish(
        diagnostics.get("final_evidence_official_or_canonical_count")
    )
    final_citation = _intish(
        diagnostics.get("final_citation_official_or_canonical_count")
    )
    admission_skip = str(diagnostics.get("admission_skip_reason") or "")

    ordinary_present = (
        admission_used is False
        and admission_skip == "existing_source_class_satisfied"
        and (_positive(final_evidence) or _positive(final_citation))
    )
    missing_forced = (
        admission_used is True
        or _boolish(diagnostics.get("source_class_recovery_eligible")) is True
        or (not ordinary_present and _positive(recovery_query_count))
    )

    recovered_visible = _NA
    if execution_attempted is True:
        recovered_visible = _yes_no_unknown(
            _positive(selected_recovered)
            or _positive(accepted_official)
            or _positive(final_evidence)
        )
    elif ordinary_present:
        recovered_visible = _NA
    elif execution_attempted is False:
        recovered_visible = _NO

    final_answer_citation_or_use = _UNKNOWN
    if final_citation is not None:
        final_answer_citation_or_use = _yes_no_unknown(_positive(final_citation))

    recovery_path_success = all(
        value == _YES
        for value in (
            _yes_no_unknown(missing_forced),
            _yes_no_unknown(admission_used is True),
            _yes_no_unknown(execution_attempted is True),
            recovered_visible,
            final_answer_citation_or_use,
        )
    )
    if ordinary_present:
        next_failure_layer = "ordinary_acquisition_only"
    else:
        next_failure_layer = str(
            diagnostics.get("next_failure_layer")
            or diagnostics.get("likely_next_failure_layer")
            or _UNKNOWN
        )

    return {
        "schema_version": AG67B_LIVE_CLASSIFICATION_SCHEMA_VERSION,
        "reliable_forced_corridor_available": _UNKNOWN,
        "pre_live_feasibility_checkpoint_passed": _UNKNOWN,
        "ordinary_authoritative_source_already_present": _yes_no_unknown(
            ordinary_present
        ),
        "missing_authoritative_source_state_forced": _yes_no_unknown(
            missing_forced
        ),
        "authoritative_recovery_bridge_visible": _UNKNOWN,
        "authoritative_recovery_query_created": _yes_no_unknown(
            _positive(recovery_query_count)
        ),
        "recovery_execution_admitted": _yes_no_unknown(admission_used is True),
        "recovery_dispatch_authorized_or_attempted": _yes_no_unknown(
            execution_attempted is True
        ),
        "recovered_evidence_visible": recovered_visible,
        "final_answer_citation_or_use": final_answer_citation_or_use,
        "ordinary_acquisition_counted_as_recovery_success": _NO,
        "recovery_path_success": _yes_no_unknown(recovery_path_success),
        "next_failure_layer": next_failure_layer,
    }


def compare_ag68b_to_ag67b_live_baseline(
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare sanitized AG-68B diagnostics against the AG-67B failure layer."""

    admission_used = _boolish(diagnostics.get("admission_used"))
    execution_attempted = _boolish(
        diagnostics.get("source_class_recovery_execution_attempted")
    )
    recovered_result_count = _intish(diagnostics.get("recovered_result_count"))
    final_evidence = _intish(
        diagnostics.get("final_evidence_official_or_canonical_count")
    )
    final_citation = _intish(
        diagnostics.get("final_citation_official_or_canonical_count")
    )
    selected_recovered = _intish(
        diagnostics.get("recovered_candidate_selected_readable_count")
    )
    accepted_official = _intish(
        diagnostics.get("accepted_or_readable_official_or_canonical_count")
    )
    admission_skip = str(diagnostics.get("admission_skip_reason") or "")
    explicit_safe_use = _boolish(
        diagnostics.get("final_answer_uses_recovered_source_safely")
    )
    cited_or_used = execution_attempted is True and (
        _positive(final_citation) or explicit_safe_use is True
    )

    return {
        "schema_version": AG68B_LIVE_RECLASSIFICATION_SCHEMA_VERSION,
        "ag67b_admission_used": False,
        "ag68b_admission_used": admission_used,
        "admission_used_moved_false_to_true": admission_used is True,
        "ag67b_admission_skip_reason": (
            "official_canonical_acquisition_path_not_visible"
        ),
        "ag68b_admission_skip_reason": admission_skip or _UNKNOWN,
        "admission_skip_reason_changed": (
            bool(admission_skip)
            and admission_skip != "official_canonical_acquisition_path_not_visible"
        ),
        "ag67b_source_class_recovery_execution_attempted": False,
        "ag68b_source_class_recovery_execution_attempted": execution_attempted,
        "source_class_recovery_execution_attempted_moved_false_to_true": (
            execution_attempted is True
        ),
        "recovered_result_count_positive": _positive(recovered_result_count),
        "official_canonical_evidence_visible": (
            _positive(final_evidence)
            or _positive(selected_recovered)
            or _positive(accepted_official)
        ),
        "official_canonical_citation_survived": _positive(final_citation),
        "final_answer_used_recovered_source_safely": _yes_no_unknown(cited_or_used),
    }


def compare_ag68d_to_prior_live_baselines(
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare sanitized AG-68D diagnostics against AG-67B and AG-68B."""

    admission_used = _boolish(diagnostics.get("admission_used"))
    execution_attempted = _boolish(
        diagnostics.get("source_class_recovery_execution_attempted")
    )
    recovery_used = _boolish(diagnostics.get("source_class_recovery_used"))
    recovered_result_count = _intish(diagnostics.get("recovered_result_count"))
    final_evidence = _intish(
        diagnostics.get("final_evidence_official_or_canonical_count")
    )
    final_citation = _intish(
        diagnostics.get("final_citation_official_or_canonical_count")
    )
    selected_recovered = _intish(
        diagnostics.get("recovered_candidate_selected_readable_count")
    )
    accepted_official = _intish(
        diagnostics.get("accepted_or_readable_official_or_canonical_count")
    )
    candidate_return_status = str(
        diagnostics.get("candidate_return_status")
        or diagnostics.get("candidate_return_visibility_status")
        or _UNKNOWN
    )
    next_failure_layer = str(
        diagnostics.get("next_failure_layer")
        or diagnostics.get("likely_next_failure_layer")
        or _UNKNOWN
    )
    ordinary_present = _ordinary_authoritative_source_already_present(diagnostics)
    candidate_visibility = _candidate_return_visibility(
        execution_attempted=execution_attempted,
        recovered_result_count=recovered_result_count,
        candidate_return_status=candidate_return_status,
    )
    provider_review_justified = (
        execution_attempted is True
        and not ordinary_present
        and candidate_visibility in {"zero_candidates", "no_candidates"}
        and next_failure_layer
        in {
            "execution_attempted_zero_candidates",
            "zero_candidates",
            "no_candidates",
            "provider_acquisition_zero_candidates",
        }
    )
    official_visible = (
        _positive(final_evidence)
        or _positive(selected_recovered)
        or _positive(accepted_official)
    )
    explicit_safe_use = _boolish(
        diagnostics.get("final_answer_uses_recovered_source_safely")
    )
    cited_or_used = execution_attempted is True and (
        _positive(final_citation) or explicit_safe_use is True
    )

    return {
        "schema_version": AG68D_LIVE_RECLASSIFICATION_SCHEMA_VERSION,
        "ag67b_admission_used": False,
        "ag68b_admission_used": True,
        "ag68d_admission_used": admission_used,
        "admission_used_remained_true_after_ag68a": admission_used is True,
        "ag68b_source_class_recovery_execution_attempted": False,
        "ag68d_source_class_recovery_execution_attempted": execution_attempted,
        "source_class_recovery_execution_attempted_moved_false_to_true_after_ag68c": (
            execution_attempted is True
        ),
        "ag68b_source_class_recovery_used": False,
        "ag68d_source_class_recovery_used": recovery_used,
        "source_class_recovery_used_moved_false_to_true": recovery_used is True,
        "recovered_result_count_positive": _positive(recovered_result_count),
        "candidate_acquisition_return_visibility": candidate_visibility,
        "candidate_acquisition_return_visibility_moved_from_not_attempted": (
            candidate_visibility != "not_attempted"
        ),
        "official_canonical_evidence_accepted_or_visible": official_visible,
        "official_canonical_citation_survived": _positive(final_citation),
        "final_answer_used_recovered_source_safely": _yes_no_unknown(cited_or_used),
        "ordinary_acquisition_counted_as_recovery_success": False,
        "provider_search_review_justified": provider_review_justified,
        "next_failure_layer": next_failure_layer,
    }


def classify_ag68f_live_case(
    *,
    case_id: str,
    query: str,
    diagnostics: Mapping[str, Any],
    reliable_forced_corridor_available: bool,
    live_budget_used: str,
) -> dict[str, Any]:
    """Classify one AG-68F forced-corridor live case from sanitized fields."""

    admission_used = _boolish(diagnostics.get("admission_used"))
    source_class_eligible = _boolish(
        diagnostics.get("source_class_recovery_eligible")
    )
    recovery_used = _boolish(diagnostics.get("source_class_recovery_used"))
    execution_attempted = _boolish(
        diagnostics.get("source_class_recovery_execution_attempted")
    )
    recovery_query_count = _intish(diagnostics.get("recovery_query_count"))
    recovered_result_count = _intish(diagnostics.get("recovered_result_count"))
    selected_recovered = _intish(
        diagnostics.get("recovered_candidate_selected_readable_count")
    )
    accepted_official = _intish(
        diagnostics.get("accepted_or_readable_official_or_canonical_count")
    )
    final_evidence = _intish(
        diagnostics.get("final_evidence_official_or_canonical_count")
    )
    final_citation = _intish(
        diagnostics.get("final_citation_official_or_canonical_count")
    )
    candidate_return_status = str(
        diagnostics.get("candidate_return_status")
        or diagnostics.get("candidate_return_visibility_status")
        or _UNKNOWN
    )
    candidate_considered = _boolish(
        diagnostics.get("candidate_acquisition_considered")
    )
    candidate_used = _boolish(diagnostics.get("candidate_acquisition_used"))
    ordinary_present = _ordinary_authoritative_source_already_present(diagnostics)
    missing_forced = (
        admission_used is True
        or source_class_eligible is True
        or (not ordinary_present and _positive(recovery_query_count))
    )
    recovered_visible = (
        _positive(selected_recovered)
        or _positive(accepted_official)
        or _positive(final_evidence)
    )
    explicit_safe_use = _boolish(
        diagnostics.get("final_answer_uses_recovered_source_safely")
    )
    final_answer_citation_or_use = (
        _positive(final_citation) or explicit_safe_use is True
    )
    candidate_visibility = _candidate_return_visibility(
        execution_attempted=execution_attempted,
        recovered_result_count=recovered_result_count,
        candidate_return_status=candidate_return_status,
    )
    next_failure_layer = str(
        diagnostics.get("next_failure_layer")
        or diagnostics.get("likely_next_failure_layer")
        or _UNKNOWN
    )

    return {
        "schema_version": AG68F_LIVE_RECLASSIFICATION_SCHEMA_VERSION,
        "case_id": str(case_id),
        "query": str(query),
        "reliable_forced_corridor_available": _yes_no_unknown(
            reliable_forced_corridor_available
        ),
        "live_budget_used": str(live_budget_used),
        "ordinary_authoritative_source_already_present": _yes_no_unknown(
            ordinary_present
        ),
        "missing_authoritative_source_state_forced": _yes_no_unknown(
            missing_forced
        ),
        "authoritative_recovery_bridge_visible": _yes_no_unknown(
            str(
                diagnostics.get("official_canonical_recovery_visibility_status")
                or ""
            )
            == "visible"
        ),
        "authoritative_recovery_query_created": _yes_no_unknown(
            _positive(recovery_query_count)
        ),
        "recovery_execution_admitted": _yes_no_unknown(admission_used is True),
        "recovery_dispatch_authorized_or_attempted": _yes_no_unknown(
            recovery_used is True or execution_attempted is True
        ),
        "source_class_recovery_execution_attempted": _yes_no_unknown(
            execution_attempted is True
        ),
        "source_class_recovery_used": _yes_no_unknown(recovery_used is True),
        "recovered_result_count": recovered_result_count
        if recovered_result_count is not None
        else _UNKNOWN,
        "candidate_return_status": candidate_visibility,
        "candidate_acquisition_considered": _yes_no_unknown(
            candidate_considered is True
        ),
        "candidate_acquisition_used": _yes_no_unknown(candidate_used is True),
        "recovered_evidence_visible": _yes_no_unknown(recovered_visible),
        "final_answer_citation_or_use": _yes_no_unknown(
            final_answer_citation_or_use
        ),
        "ordinary_acquisition_counted_as_recovery_success": _NO,
        "provider_search_review_justified": False,
        "next_failure_layer": next_failure_layer,
    }


def compare_ag68f_irs_to_prior_live_baselines(
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare AG-68F IRS diagnostics against AG-67B/68B/68D IRS baselines."""

    ag68d = compare_ag68d_to_prior_live_baselines(diagnostics)
    execution_attempted = _boolish(
        diagnostics.get("source_class_recovery_execution_attempted")
    )
    recovery_used = _boolish(diagnostics.get("source_class_recovery_used"))
    recovered_result_count = _intish(diagnostics.get("recovered_result_count"))
    final_evidence = _intish(
        diagnostics.get("final_evidence_official_or_canonical_count")
    )
    final_citation = _intish(
        diagnostics.get("final_citation_official_or_canonical_count")
    )
    explicit_safe_use = _boolish(
        diagnostics.get("final_answer_uses_recovered_source_safely")
    )

    return {
        "schema_version": AG68F_LIVE_RECLASSIFICATION_SCHEMA_VERSION,
        "ag67b_admission_used": False,
        "ag68b_admission_used": True,
        "ag68d_admission_used": True,
        "ag68f_admission_used": ag68d["ag68d_admission_used"],
        "admission_used_remained_true": (
            ag68d["ag68d_admission_used"] is True
        ),
        "ag67b_source_class_recovery_execution_attempted": False,
        "ag68b_source_class_recovery_execution_attempted": False,
        "ag68d_source_class_recovery_execution_attempted": False,
        "ag68f_source_class_recovery_execution_attempted": execution_attempted,
        "source_class_recovery_execution_attempted_moved_false_to_true": (
            execution_attempted is True
        ),
        "source_class_recovery_used_moved_false_to_true": recovery_used is True,
        "candidate_return_status_moved_from_not_attempted": (
            ag68d["candidate_acquisition_return_visibility"] != "not_attempted"
        ),
        "recovered_result_count_positive": _positive(recovered_result_count),
        "official_current_evidence_accepted_or_visible": _positive(final_evidence),
        "official_current_citation_survived": _positive(final_citation),
        "final_answer_used_recovered_source_safely": _yes_no_unknown(
            explicit_safe_use is True
            or (execution_attempted is True and _positive(final_citation))
        ),
        "provider_search_review_justified": ag68d[
            "provider_search_review_justified"
        ],
        "next_failure_layer": ag68d["next_failure_layer"],
    }


def classify_ag68f_cross_case(
    irs_case: Mapping[str, Any],
    ssa_case: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the AG-68F two-case decision tree."""

    case1_dispatch = _yes(irs_case.get("source_class_recovery_execution_attempted"))
    case2_dispatch = _yes(ssa_case.get("source_class_recovery_execution_attempted"))
    case1_used = _yes(irs_case.get("source_class_recovery_used"))
    case2_used = _yes(ssa_case.get("source_class_recovery_used"))
    both_dispatched = case1_dispatch and case2_dispatch
    neither_dispatched = not case1_dispatch and not case2_dispatch
    one_dispatched = case1_dispatch != case2_dispatch
    both_zero_candidate_dispatch = both_dispatched and all(
        _zero_candidate_status(case.get("candidate_return_status"))
        for case in (irs_case, ssa_case)
    )
    any_candidates_returned = any(
        _candidate_returned_status(case.get("candidate_return_status"))
        for case in (irs_case, ssa_case)
    )
    any_visible = any(
        _yes(case.get("recovered_evidence_visible"))
        for case in (irs_case, ssa_case)
    )
    any_cited = any(
        _yes(case.get("final_answer_citation_or_use"))
        for case in (irs_case, ssa_case)
    )
    any_success = any(
        _yes(case.get("source_class_recovery_execution_attempted"))
        and _yes(case.get("recovered_evidence_visible"))
        and _yes(case.get("final_answer_citation_or_use"))
        for case in (irs_case, ssa_case)
    )

    if neither_dispatched:
        recommended_next_action = "focused_live_product_dispatch_repair"
        next_failure_layer = "execution_not_attempted"
    elif one_dispatched:
        recommended_next_action = "focused_official_current_numeric_rule_generalization"
        next_failure_layer = "single_case_dispatch_gap"
    elif both_zero_candidate_dispatch:
        recommended_next_action = "provider_search_allocation_review"
        next_failure_layer = "execution_attempted_zero_candidates"
    elif any_candidates_returned and not any_visible:
        recommended_next_action = "recovered_evidence_visibility_source_fit_repair"
        next_failure_layer = "candidates_returned_not_visible"
    elif any_visible and not any_cited:
        recommended_next_action = "citation_survival_source_claim_fit_repair"
        next_failure_layer = "official_current_visible_not_cited"
    elif any_success:
        recommended_next_action = "targeted_dogfood_expansion_or_sibling_hardening"
        next_failure_layer = "recovery_path_succeeded_for_at_least_one_case"
    else:
        recommended_next_action = "continue_classification_at_observed_failure_layer"
        next_failure_layer = "mixed_or_unknown"

    return {
        "schema_version": AG68F_LIVE_RECLASSIFICATION_SCHEMA_VERSION,
        "both_cases_dispatch_recovery": both_dispatched,
        "only_one_case_dispatches_recovery": one_dispatched,
        "neither_case_dispatches_recovery": neither_dispatched,
        "case1_recovery_dispatch_executed": case1_dispatch,
        "case2_recovery_dispatch_executed": case2_dispatch,
        "case1_source_class_recovery_used": case1_used,
        "case2_source_class_recovery_used": case2_used,
        "authoritative_candidate_acquisition_succeeded": (
            both_dispatched and any_candidates_returned
        ),
        "provider_search_review_justified": both_zero_candidate_dispatch,
        "ag68e_moved_live_failure_layer": case1_dispatch or case2_dispatch,
        "ordinary_acquisition_counted_as_recovery_success": False,
        "next_failure_layer": next_failure_layer,
        "recommended_next_action": recommended_next_action,
    }


def compare_ag68h_ssa_to_ag68f_baseline(
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare AG-68H SSA diagnostics against the AG-68F SSA live baseline."""

    classification = classify_ag68f_live_case(
        case_id="case1_ssa",
        query=str(diagnostics.get("query") or ""),
        diagnostics=diagnostics,
        reliable_forced_corridor_available=True,
        live_budget_used=str(diagnostics.get("live_budget_used") or "1/2"),
    )
    execution_attempted = _yes(
        classification["source_class_recovery_execution_attempted"]
    )
    recovery_used = _yes(classification["source_class_recovery_used"])
    recovered_result_count = _intish(classification["recovered_result_count"])
    candidate_status = str(classification["candidate_return_status"])
    official_visible = _yes(classification["recovered_evidence_visible"])
    cited_or_used = _yes(classification["final_answer_citation_or_use"])

    return {
        "schema_version": AG68H_LIVE_RECLASSIFICATION_SCHEMA_VERSION,
        "ag68f_source_class_recovery_execution_attempted": False,
        "ag68h_source_class_recovery_execution_attempted": execution_attempted,
        "source_class_recovery_execution_attempted_moved_false_to_true": (
            execution_attempted is True
        ),
        "ag68f_source_class_recovery_used": False,
        "ag68h_source_class_recovery_used": recovery_used,
        "source_class_recovery_used_moved_false_to_true": recovery_used is True,
        "ag68f_candidate_return_status": "not_attempted",
        "ag68h_candidate_return_status": candidate_status,
        "candidate_return_status_moved_from_not_attempted": (
            candidate_status != "not_attempted"
        ),
        "recovered_result_count_positive": _positive(recovered_result_count),
        "official_current_evidence_accepted_or_visible": official_visible,
        "official_current_citation_survived": cited_or_used,
        "ag68g_moved_live_product_callsite_failure_layer": execution_attempted,
        "ordinary_acquisition_counted_as_recovery_success": False,
        "next_failure_layer": classification["next_failure_layer"],
    }


def compare_ag68h_irs_to_ag68f_baseline(
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare AG-68H IRS diagnostics against the AG-68F weak-corpus baseline."""

    classification = classify_ag68f_live_case(
        case_id="case2_irs",
        query=str(diagnostics.get("query") or ""),
        diagnostics=diagnostics,
        reliable_forced_corridor_available=True,
        live_budget_used=str(diagnostics.get("live_budget_used") or "2/2"),
    )
    admission_used = _boolish(diagnostics.get("admission_used"))
    admission_skip = str(diagnostics.get("admission_skip_reason") or _UNKNOWN)
    blockers = {
        str(blocker).strip()
        for blocker in diagnostics.get("admission_blockers", ()) or ()
        if str(blocker).strip()
    }
    weak_corpus_blocked = (
        admission_used is False
        and (
            admission_skip == "existing_runtime_blocker"
            or "weak_corpus_recovery_owns_path" in blockers
            or "blocked_by_corpus_weak" in blockers
            or str(
                diagnostics.get("source_class_recovery_skip_reason") or ""
            )
            == "blocked_by_weak_corpus_recovery"
        )
    )
    execution_attempted = _yes(
        classification["source_class_recovery_execution_attempted"]
    )

    return {
        "schema_version": AG68H_LIVE_RECLASSIFICATION_SCHEMA_VERSION,
        "ag68f_admission_used": False,
        "ag68h_admission_used": admission_used,
        "ag68f_weak_corpus_ownership_blocked_admission": True,
        "ag68h_weak_corpus_ownership_blocked_admission": weak_corpus_blocked,
        "weak_corpus_ownership_still_blocks_before_admission": (
            weak_corpus_blocked is True
        ),
        "ag68f_source_class_recovery_execution_attempted": False,
        "ag68h_source_class_recovery_execution_attempted": execution_attempted,
        "irs_reached_dispatch": execution_attempted,
        "ordinary_acquisition_counted_as_recovery_success": False,
        "provider_search_review_justified": False,
        "next_failure_layer": (
            "weak_corpus_arbitration_ownership"
            if weak_corpus_blocked
            else classification["next_failure_layer"]
        ),
    }


def classify_ag68h_cross_case(
    *,
    ssa_case: Mapping[str, Any],
    irs_case: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply the AG-68H bounded live reclassification decision tree."""

    ssa_dispatch = _yes(ssa_case.get("source_class_recovery_execution_attempted"))
    ssa_candidate_status = str(ssa_case.get("candidate_return_status") or _UNKNOWN)
    ssa_visible = _yes(ssa_case.get("recovered_evidence_visible"))
    ssa_cited = _yes(ssa_case.get("final_answer_citation_or_use"))
    irs_dispatch = (
        _yes(irs_case.get("source_class_recovery_execution_attempted"))
        if irs_case is not None
        else False
    )
    irs_weak_corpus_blocked = (
        str(irs_case.get("next_failure_layer") or "")
        == "weak_corpus_arbitration_ownership"
        if irs_case is not None
        else False
    )
    both_dispatched = ssa_dispatch and irs_dispatch
    both_zero_candidate_dispatch = both_dispatched and all(
        _zero_candidate_status(case.get("candidate_return_status"))
        for case in (ssa_case, irs_case or {})
    )

    if not ssa_dispatch:
        provider_search_review_justified = False
        recommended_next_action = "focused_product_callsite_repair"
        next_failure_layer = "execution_not_attempted"
    elif _zero_candidate_status(ssa_candidate_status):
        provider_search_review_justified = True
        recommended_next_action = "provider_search_allocation_review"
        next_failure_layer = "execution_attempted_zero_candidates"
    elif _candidate_returned_status(ssa_candidate_status) and not ssa_visible:
        provider_search_review_justified = False
        recommended_next_action = "recovered_evidence_visibility_source_fit_repair"
        next_failure_layer = "candidates_returned_not_visible"
    elif ssa_visible and not ssa_cited:
        provider_search_review_justified = False
        recommended_next_action = "citation_survival_source_claim_fit_repair"
        next_failure_layer = "official_current_visible_not_cited"
    elif ssa_visible and ssa_cited:
        provider_search_review_justified = False
        recommended_next_action = "targeted_dogfood_expansion_or_sibling_hardening"
        next_failure_layer = "recovery_path_succeeded_for_ssa"
    else:
        provider_search_review_justified = False
        recommended_next_action = "continue_classification_at_observed_failure_layer"
        next_failure_layer = str(ssa_case.get("next_failure_layer") or _UNKNOWN)

    if irs_case is not None and ssa_dispatch != irs_dispatch:
        provider_search_review_justified = False
        if irs_weak_corpus_blocked:
            recommended_next_action = "focused_generalization_or_arbitration_repair"
            next_failure_layer = "single_case_dispatch_with_weak_corpus_arbitration"
        elif not both_zero_candidate_dispatch:
            recommended_next_action = "focused_generalization_or_arbitration_repair"
            next_failure_layer = "single_case_dispatch_gap"

    return {
        "schema_version": AG68H_LIVE_RECLASSIFICATION_SCHEMA_VERSION,
        "ssa_recovery_dispatch_executed": ssa_dispatch,
        "irs_recovery_dispatch_executed": irs_dispatch,
        "irs_weak_corpus_ownership_still_blocks": irs_weak_corpus_blocked,
        "both_cases_dispatch_recovery": both_dispatched,
        "only_one_case_dispatches_recovery": ssa_dispatch != irs_dispatch,
        "provider_search_review_justified": provider_search_review_justified,
        "ag68g_moved_ssa_live_product_callsite_failure_layer": ssa_dispatch,
        "ordinary_acquisition_counted_as_recovery_success": False,
        "next_failure_layer": next_failure_layer,
        "recommended_next_action": recommended_next_action,
    }


def _ordinary_authoritative_source_already_present(
    diagnostics: Mapping[str, Any],
) -> bool:
    admission_used = _boolish(diagnostics.get("admission_used"))
    final_evidence = _intish(
        diagnostics.get("final_evidence_official_or_canonical_count")
    )
    final_citation = _intish(
        diagnostics.get("final_citation_official_or_canonical_count")
    )
    admission_skip = str(diagnostics.get("admission_skip_reason") or "")
    return (
        admission_used is False
        and admission_skip == "existing_source_class_satisfied"
        and (_positive(final_evidence) or _positive(final_citation))
    )


def _candidate_return_visibility(
    *,
    execution_attempted: bool | None,
    recovered_result_count: int | None,
    candidate_return_status: str,
) -> str:
    normalized = candidate_return_status.strip().casefold()
    if execution_attempted is not True:
        return "not_attempted"
    if normalized and normalized != _UNKNOWN:
        return normalized
    if _positive(recovered_result_count):
        return "candidates_returned"
    if recovered_result_count == 0:
        return "zero_candidates"
    return _UNKNOWN


def _required_diagnostics_present(keys: set[str]) -> bool:
    return {
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
    } <= keys


def _safe_live_packet_path(path: str) -> bool:
    pure = PurePath(path)
    parts = tuple(part.casefold() for part in pure.parts)
    return len(parts) >= 2 and parts[0] == "output" and pure.suffix == ".md"


def live_packet_header_is_safe(text: str) -> bool:
    """Return whether a local packet begins with the required marker."""

    return str(text or "").startswith(_PACKET_MARKER)


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().casefold()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def _intish(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _positive(value: int | None) -> bool:
    return isinstance(value, int) and value > 0


def _yes_no_unknown(value: bool | None) -> str:
    if value is True:
        return _YES
    if value is False:
        return _NO
    return _UNKNOWN


def _yes(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() == _YES
    return False


def _zero_candidate_status(value: Any) -> bool:
    return str(value or "").strip().casefold() in {
        "zero_candidates",
        "no_candidates",
        "provider_acquisition_zero_candidates",
        "execution_attempted_zero_candidates",
    }


def _candidate_returned_status(value: Any) -> bool:
    return str(value or "").strip().casefold() in {
        "candidates_returned",
        "attempted",
    }


__all__ = [
    "AG67B_LIVE_CLASSIFICATION_SCHEMA_VERSION",
    "AG68B_LIVE_RECLASSIFICATION_SCHEMA_VERSION",
    "AG68D_LIVE_RECLASSIFICATION_SCHEMA_VERSION",
    "AG68F_LIVE_RECLASSIFICATION_SCHEMA_VERSION",
    "AG68H_LIVE_RECLASSIFICATION_SCHEMA_VERSION",
    "PreLiveFeasibilityCheckpoint",
    "build_pre_live_feasibility_checkpoint",
    "compare_ag68b_to_ag67b_live_baseline",
    "compare_ag68d_to_prior_live_baselines",
    "compare_ag68f_irs_to_prior_live_baselines",
    "compare_ag68h_irs_to_ag68f_baseline",
    "compare_ag68h_ssa_to_ag68f_baseline",
    "classify_ag68h_cross_case",
    "classify_ag68f_cross_case",
    "classify_ag68f_live_case",
    "classify_allowed_live_report_diagnostics",
    "live_packet_header_is_safe",
]
