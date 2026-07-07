"""PRODUCT-PATH-REGRESSION: current-source Analyst Workbench slice.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-current-source-of-record-single-fact-run --query "<supported query>"
Runtime consumer: proplex.__main__ ->
proplex.mvp_single_relation_live_dogfood_run ->
proplex.live_semantic_coverage_status
Why ordinary product-path work cannot be done directly: offline validation must
not make live provider, fetch/read, retrieval, or model calls; injected fakes
preserve the same product runner, retained-artifact, and D-prime consumers.
Integration deadline: current phase.
Exit condition: keep while the current-source single-fact product CLI consumes
candidate intake and D-prime review, or replace with a broader product-path
guard if the Workbench becomes fully admitted runtime machinery.
Why this is not a shadow product path: tests call the existing product runner
and D-prime status consumer, not an alternate answer formatter or review path.
Forbidden interpretation: Workbench proposals are not evidence admission,
source-obligation satisfaction, citation eligibility, product correctness,
answer prose, live validation correctness, or arbitrary-query support.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import pytest

import proplex.mvp_single_relation_live_dogfood_run as dogfood
from core import runkernel_followup_search_reentry_ordinary_search_runtime as followup_runtime
from core.analyst_workbench_runtime import (
    ROLE_ANSWER_ADJACENT_CONTEXT,
    ROLE_OVERCLAIM_RISK,
    ROLE_QUALIFIER_EXCEPTION_CONTEXT,
    ROLE_STRICT_ANSWER_SUPPORT,
    ROLE_UNREADABLE_HIGH_VALUE_OFFICIAL,
    WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED,
)
from core.dprime_single_lane_answer_path_runtime import (
    DPrimeSingleLaneAnswerPathError,
)
from core.generic_query_to_relation_planning import build_generic_query_relation_plan
from proplex.mvp_single_relation_live_dogfood_run import (
    DEFAULT_OUTPUT_DIR,
    GenericLiveFetchReadResult,
    GenericProviderProxyRunRequest,
    GenericProviderProxyRunResult,
    build_generic_single_relation_live_dogfood_run_output,
)

ROOT = Path(__file__).resolve().parents[1]
N400_QUERY = "What is the current USCIS Form N-400 paper filing fee?"
SMALL_CLAIMS_QUERY = (
    "What is the current filing fee for small claims in Example County?"
)
SMALL_CLAIMS_URL = "https://example-county.invalid/civil/small-claims-fees"
DEADLINE_QUERY = (
    "What is the current filing deadline for Example County annual business "
    "license renewal?"
)
DEADLINE_URL = "https://example-county.invalid/business-license/deadlines"


def test_product_cli_consumes_workbench_and_dprime_dossier(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(N400_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []
    captured_input: dict[str, Any] = {}
    answer_claim = "The current USCIS Form N-400 paper filing fee is $760."

    def fake_review(*_args: Any, input_packet: Mapping[str, Any], **_kwargs: Any) -> dict[str, Any]:
        captured_input.update(dict(input_packet))
        return _assessment_payload(plan, answer_claim)

    result = build_generic_single_relation_live_dogfood_run_output(
        query=N400_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-product-n400",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "USCIS Form N-400 Filing Fee",
                    "https://www.uscis.gov/forms/filing-fees",
                    "USCIS lists the current Form N-400 paper filing fee as $760.",
                )
            ],
        ),
        fetch_read_runner=_failing_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    assert result.return_code == 0, packet.get("blocker_detail")
    assert packet["candidate_evidence_triage_consumed_by_product_path"] is True
    assert packet["analyst_workbench_consumed_by_product_path"] is True
    assert packet["workbench_dprime_dossier_consumed_by_product_path"] is True
    assert packet["workbench_dprime_dossier_consumed_by_dprime"] is True
    assert packet["optional_evidence_triage_implemented"] is True
    projection = packet["workbench_reduction_projection"]
    assert projection["owner"] == "AnalystWorkbenchRuntime"
    assert projection["run_kernel_reduced"] is False
    assert projection["run_kernel_reduction_pending"] is True
    assert projection["proposed_for_runkernel_reduction"] is True
    assert packet["analyst_workbench_packet"]["specialist_lane_placeholder"][
        "status"
    ] == "not_required"
    assert packet["analyst_workbench_packet"]["specialist_lane_placeholder"][
        "owner"
    ] == "AnalystWorkbenchRuntime.SpecialistLanePlaceholder"
    assert packet["analyst_workbench_packet"]["economist_lane_placeholder"][
        "status"
    ] == "not_required"
    assert packet["analyst_workbench_packet"]["economist_lane_placeholder"][
        "owner"
    ] == "AnalystWorkbenchRuntime.EconomistLanePlaceholder"
    assert packet["analyst_workbench_packet"]["scrutineer_lane_placeholder"][
        "status"
    ] in {"cleared", "challenge_recommended"}
    _assert_workbench_non_authority(packet)

    dossier_ref = packet["workbench_dprime_dossier_ref"]
    assert captured_input["workbench_dprime_dossier_ref"]["dossier_digest"] == (
        dossier_ref["dossier_digest"]
    )
    input_ref = packet["semantic_status_payload"]["dprime_status"]["input_packet_ref"]
    assert input_ref["workbench_dprime_dossier_ref"]["dossier_digest"] == (
        dossier_ref["dossier_digest"]
    )
    assert "CandidateEvidenceTriagePacket" not in result.output
    assert "AnalystWorkbenchPacket" not in result.output
    assert "- Review report: " in result.output

    report_json = json.loads(
        Path(packet["review_report_json_path"]).read_text(encoding="utf-8")
    )
    report_md = Path(packet["review_report_markdown_path"]).read_text(
        encoding="utf-8"
    )
    assert report_json["analyst_workbench"]["product_path_consumed"] is True
    assert report_json["analyst_workbench"][
        "workbench_dprime_dossier_consumed_by_dprime"
    ] is True
    assert report_json["analyst_workbench"]["run_kernel_reduced"] is False
    assert report_json["analyst_workbench"]["run_kernel_reduction_pending"] is True
    assert report_json["stage_lifecycle"]["retention"][
        "live_product_run_executed"
    ] is True
    assert report_json["stage_lifecycle"]["retention"][
        "live_validation_correctness_claimed"
    ] is False
    assert "## Analyst Workbench" in report_md
    assert "Live validation: not run" not in report_md
    assert "RunKernel reduced" not in report_md
    assert "Workbench reduction projection" in report_md
    assert "- RunKernel reduction pending: true" in report_md
    assert "- Live product run executed: true" in report_md
    assert "- Live validation correctness claimed: false" in report_md


def test_generic_dogfood_consumes_workbench_for_non_uscis_relation(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return _assessment_payload(
            plan,
            "The current Example County small claims filing fee is $54.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-small-claims-dogfood",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "Example County Clerk Small Claims Fee Schedule",
                    SMALL_CLAIMS_URL,
                    (
                        "Example County Clerk civil fee schedule. The standard "
                        "paper small claims filing fee is $54."
                    ),
                )
            ],
        ),
        fetch_read_runner=_failing_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    roles = _candidate_roles(packet)
    assert packet["entrypoint_kind"] == dogfood.DOGFOOD_ENTRYPOINT_KIND
    assert packet["analyst_workbench_consumed_by_product_path"] is True
    assert packet["candidate_evidence_triage_packet"][
        "generic_role_classification"
    ] is True
    assert ROLE_STRICT_ANSWER_SUPPORT in roles
    assert packet["workbench_dprime_dossier_consumed_by_dprime"] is True
    assert packet["workbench_dprime_dossier"]["dprime_review_candidate_ref"]
    assert packet["analyst_workbench_packet"]["display_candidate_ref_status"] == (
        "not_authorized_by_workbench"
    )
    assert "USCIS" not in json.dumps(packet, sort_keys=True)
    _assert_workbench_non_authority(packet)


def test_mixed_fee_schedule_keeps_strict_support_and_context_roles(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return _assessment_payload(
            plan,
            "The current Example County standard paper filing fee is $54.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-mixed-fee-schedule",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "Example County Clerk Fee Schedule",
                    SMALL_CLAIMS_URL,
                    (
                        "Standard paper filing fee is $54. Online filing is "
                        "$44. Reduced fee is $20 for eligible filers."
                    ),
                )
            ],
        ),
        fetch_read_runner=_failing_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    roles = _candidate_roles(packet)
    gap = packet["analysis_gap_search_proposal"]
    assert ROLE_STRICT_ANSWER_SUPPORT in roles
    assert ROLE_ANSWER_ADJACENT_CONTEXT in roles
    assert ROLE_QUALIFIER_EXCEPTION_CONTEXT in roles
    assert ROLE_OVERCLAIM_RISK in roles
    assert gap["gap_status"] == "not_required"
    assert gap["gap_kind"] == "not_required"
    assert gap["live_followup_required"] is False
    assert gap["proposed_runkernel_reduction_status"] == "not_required"
    reentry = packet["workbench_gap_reentry_ref"]
    assert reentry["workbench_gap_reentry_status"] == "not_required"
    assert reentry["followup_execution_status"] == "not_required"
    assert reentry["runkernel_followup_authorization_status"] == "not_required"
    assert packet["followup_execution_status"] != "followup_not_licensed"
    assert packet["workbench_reduction_projection_status"] != (
        WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED
    )
    assert packet["analyst_workbench_packet"]["scrutineer_lane_placeholder"][
        "status"
    ] == "challenge_recommended"
    _assert_workbench_non_authority(packet)


def test_mixed_deadline_schedule_keeps_strict_support_and_context_roles(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(DEADLINE_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return _assessment_payload(
            plan,
            "The current Example County standard filing deadline is April 15.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=DEADLINE_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-mixed-deadline-schedule",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "Example County Business License Deadline Schedule",
                    DEADLINE_URL,
                    (
                        "Standard filing deadline is April 15. Extension "
                        "deadline is October 15."
                    ),
                )
            ],
        ),
        fetch_read_runner=_failing_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    roles = _candidate_roles(packet)
    gap = packet["analysis_gap_search_proposal"]
    assert ROLE_STRICT_ANSWER_SUPPORT in roles
    assert ROLE_ANSWER_ADJACENT_CONTEXT in roles
    assert ROLE_QUALIFIER_EXCEPTION_CONTEXT in roles
    assert gap["gap_status"] == "not_required"
    assert gap["live_followup_required"] is False
    reentry = packet["workbench_gap_reentry_ref"]
    assert reentry["workbench_gap_reentry_status"] == "not_required"
    assert reentry["followup_execution_status"] == "not_required"
    assert packet["followup_execution_status"] != "followup_not_licensed"
    assert packet["workbench_reduction_projection_status"] != (
        WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED
    )
    _assert_workbench_non_authority(packet)


def test_contextual_non_uscis_material_proposes_gap_and_product_blocker(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        payload = _assessment_payload(
            plan,
            "Example County small claims online fee may be $20 for eligible filers.",
        )
        payload["support_relation"] = "partially_supports"
        payload["missing_qualifiers"] = [str(plan["component_text"])]
        payload["non_support_reason_when_not_direct"] = (
            "The source is a reduced online-fee context, not strict standard support."
        )
        payload["challenge_recommended"] = True
        return payload

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-small-claims-contextual",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "Example County Reduced Online Small Claims Fee",
                    SMALL_CLAIMS_URL,
                    (
                        "Example County online fee discount. Eligible low-income "
                        "filers may pay a reduced online small claims fee of $20."
                    ),
                )
            ],
        ),
        fetch_read_runner=_failing_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    roles = _candidate_roles(packet)
    gap = packet["analysis_gap_search_proposal"]
    assert result.return_code == 2
    assert gap["gap_status"] == "proposed"
    assert gap["gap_kind"] in {"strict_support_missing", "overclaim_risk"}
    assert (
        packet["decision"] == dogfood.BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED
    )
    reentry = packet["workbench_gap_reentry_ref"]
    assert reentry["workbench_gap_reentry_status"] == "followup_not_licensed"
    assert reentry["gap_sources"] == ["workbench", "dprime"]
    assert reentry["workbench_gap_proposal_ref"]["gap_status"] == "proposed"
    assert reentry["dprime_gap_ref"]["support_relation"] == "partially_supports"
    assert reentry["runkernel_followup_authorization_status"] == (
        "not_created_followup_not_licensed"
    )
    assert reentry["runkernel_followup_authorization_ref"] == {}
    assert reentry["proposal_or_blocker_ref_only"] is True
    assert reentry["ordinary_search_path_reused"] is True
    assert reentry["ordinary_search_reentry_intent_status"] == "intended_not_executed"
    assert reentry["followup_execution_licensed"] is False
    assert reentry["provider_called"] is False
    assert reentry["live_search_called"] is False
    assert reentry["fetch_read_executed"] is False
    assert reentry["dprime_dispatch_owner"] is False
    assert reentry["workbench_dispatch_owner"] is False
    assert reentry["new_search_subsystem_created"] is False
    assert reentry["evidence_admitted"] is False
    assert reentry["source_obligation_satisfied"] is False
    assert reentry["citation_eligible"] is False
    assert reentry["final_answer_packet_created"] is False
    assert reentry["author_prose_created"] is False
    assert reentry["product_correctness_claimed"] is False
    assert result.output.startswith(
        "Answer:\nBlocked before answer: official strict support follow-up is needed."
    )
    assert packet["workbench_reduction_projection_status"] == (
        WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED
    )
    assert packet["analyst_workbench_packet"]["scrutineer_lane_placeholder"][
        "status"
    ] == "challenge_recommended"
    assert packet["candidate_evidence_triage_packet"]["contextual_candidate_refs"]
    assert packet["candidate_evidence_triage_packet"]["overclaim_risk_candidate_refs"]
    assert ROLE_ANSWER_ADJACENT_CONTEXT in roles
    assert ROLE_OVERCLAIM_RISK in roles
    assert packet["candidate_evidence_triage_packet"]["top_candidate_ref"]
    assert packet["candidate_evidence_triage_packet"]["dprime_review_candidate_ref"]
    assert packet["analyst_workbench_packet"]["display_candidate_ref_status"] == (
        "not_authorized_by_workbench"
    )
    report_json = json.loads(
        Path(packet["review_report_json_path"]).read_text(encoding="utf-8")
    )
    report_md = Path(packet["review_report_markdown_path"]).read_text(
        encoding="utf-8"
    )
    gap_report = report_json["gap_reentry"]
    assert gap_report["workbench_gap_reentry_status"] == "followup_not_licensed"
    assert gap_report["runkernel_followup_authorization_status"] == (
        "not_created_followup_not_licensed"
    )
    assert gap_report["ordinary_search_path_reused"] is True
    assert gap_report["followup_execution_licensed"] is False
    assert gap_report["provider_called"] is False
    assert gap_report["live_search_called"] is False
    assert gap_report["fetch_read_executed"] is False
    assert gap_report["dprime_dispatch_owner"] is False
    assert gap_report["new_search_subsystem_created"] is False
    assert "## Gap Re-entry" in report_md
    assert "- Status: followup_not_licensed" in report_md
    assert "- Reducer-produced authorization ref: not created" in report_md
    _assert_workbench_non_authority(packet)


def test_licensed_followup_reentry_executes_one_second_ordinary_search(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []
    dprime_inputs: list[Mapping[str, Any]] = []

    def fake_review(*_args: Any, input_packet: Mapping[str, Any], **_kwargs: Any) -> dict[str, Any]:
        dprime_inputs.append(dict(input_packet))
        if len(dprime_inputs) == 1:
            return _assessment_payload(
                plan,
                "Example County small claims online fee may be $20 for eligible filers.",
                support_relation="weak_or_overclaim_risk",
                missing_qualifiers=[str(plan["component_text"])],
                non_support_reason=(
                    "The source is reduced-fee contextual material, not strict support."
                ),
            )
        return _assessment_payload(
            plan,
            "The current Example County standard paper small claims filing fee is $54.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-small-claims-licensed-followup",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_current_source_followup_reentry=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_sequential_proxy_runner(
            calls,
            [
                [
                    _provider_extracted_result(
                        "Example County Reduced Online Small Claims Fee",
                        SMALL_CLAIMS_URL,
                        (
                            "Example County online fee discount. Eligible "
                            "filers may pay a reduced online small claims fee of $20."
                        ),
                    )
                ],
                [
                    _provider_result(
                        "Example County Official Standard Paper Filing Fee PDF",
                        "https://example-county.gov/courts/standard-paper-fee.pdf",
                    )
                ],
            ],
        ),
        fetch_read_runner=_official_pdf_read_support_fetch_runner(
            "Example County official fee schedule. The current standard paper "
            "small claims filing fee is $54."
        ),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    assert result.return_code == 0, packet.get("blocker_detail")
    assert len(calls) == 2
    assert calls[0].query != calls[1].query
    assert calls[1].acquisition_provider_role == "current_source_followup_reentry"
    assert "official source of record" in calls[1].query
    assert "strict support" in calls[1].query
    for forbidden in ("USCIS", "N-400", "G-1055", "$760", "$710", "$380"):
        assert forbidden not in calls[1].query
    assert len(dprime_inputs) == 2
    assert packet["initial_provider_calls_attempted"] == 1
    assert packet["followup_provider_calls_attempted"] == 1
    assert packet["followup_provider_calls_completed"] == 1
    assert packet["initial_fetch_read_completed"] == 1
    assert packet["followup_fetch_read_completed"] == 1
    assert packet["initial_dprime_model_review_calls_attempted"] == 1
    assert packet["followup_dprime_model_review_calls_attempted"] == 1
    assert packet["dprime_model_review_calls_attempted"] == 2
    assert packet["followup_loop_count"] == 1
    reentry = packet["workbench_gap_reentry_ref"]
    assert reentry["workbench_gap_reentry_status"] == "runkernel_authorized_executed"
    assert reentry["followup_execution_status"] == "executed_ordinary_search_followup"
    assert reentry["followup_execution_licensed"] is True
    assert reentry["runkernel_followup_authorization_status"] == "authorized"
    assert reentry["runkernel_followup_authorization_ref"]
    assert reentry["proposal_or_blocker_ref_only"] is False
    assert reentry["ordinary_search_path_reused"] is True
    assert reentry["provider_called"] is True
    assert reentry["fetch_read_executed"] is True
    assert reentry["new_search_subsystem_created"] is False
    assert reentry["dprime_dispatch_owner"] is False
    assert reentry["source_obligation_satisfied"] is False
    assert reentry["citation_eligible"] is False
    assert reentry["fap_or_author_created"] is False
    assert reentry["product_correctness_claimed"] is False
    plan_ref = reentry["followup_planning_ref"]
    assert plan_ref["parent_component_id"] == plan["component_id"]
    assert plan_ref["parent_source_obligation_id"] == plan["source_obligation_id"]
    assert plan_ref["search_requirement_text"] == calls[1].query
    assert plan_ref["provider_query"] == calls[1].query
    assert plan_ref["query_seeds"] == [calls[1].query]
    assert plan_ref["non_authority_posture"]["provider_called"] is False
    assert reentry["followup_query_ref"]["query_text"] == calls[1].query
    followup_ref = packet["semantic_status_payload"][
        "dprime_followup_search_reentry_ref"
    ]
    assert followup_ref["product_followup_provider_execution_after_authorization"] is True
    assert followup_ref["product_followup_authorization_consumed"] is True
    assert followup_ref["product_followup_search_authorization_ref"]
    assert followup_ref["product_followup_search_executor_handoff_ref"]
    assert packet["final_answer_packet_created"] is True
    assert packet["author_prose_created"] is True
    assert packet["author_answer_created"] is True
    assert packet["citation_source_display_created"] is True
    assert packet["fap_author_opened"] is True
    assert packet["answer_text_present"] is True
    assert packet["product_answer_text"] == (
        "The current Example County standard paper small claims filing fee is $54."
    )
    assert packet["source_display_entries"]
    assert packet["product_correctness_claimed"] is False
    assert packet["decision_made_by_the_run"] == (
        "existing_dprime_single_lane_answer_path_consumed"
    )
    assert reentry["followup_provider_calls_attempted"] == 1
    assert reentry["followup_fetch_read_completed"] == 1
    assert reentry["followup_selected_source_candidate"]["url"].endswith(
        "standard-paper-fee.pdf"
    )
    assert reentry["followup_pdf_text_extraction_attempted"] is False
    assert packet["followup_source_acquisition_mode"] == (
        dogfood.SOURCE_ACQUISITION_MODE_DIRECT_FETCH_FALLBACK
    )
    assert packet["source_challenge_recovery_status"] == "not_triggered"
    assert packet["provider_snippets_used_as_evidence"] is False
    assert packet["raw_private_retention_flags"] == dogfood.RAW_FALSE_FLAGS


def test_licensed_followup_strict_support_blocks_when_answer_path_not_reached(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []
    dprime_inputs: list[Mapping[str, Any]] = []

    def fake_review(*_args: Any, input_packet: Mapping[str, Any], **_kwargs: Any) -> dict[str, Any]:
        dprime_inputs.append(dict(input_packet))
        if len(dprime_inputs) == 1:
            return _assessment_payload(
                plan,
                "Example County small claims online fee may be $20 for eligible filers.",
                support_relation="weak_or_overclaim_risk",
                missing_qualifiers=[str(plan["component_text"])],
                non_support_reason="Strict support was not established.",
            )
        return _assessment_payload(
            plan,
            "The current Example County standard paper small claims filing fee is $54.",
        )

    def block_answer_path(**_kwargs: Any) -> Any:
        raise DPrimeSingleLaneAnswerPathError(
            "BLOCKED_TEST_DPRIME_ANSWER_PATH",
            "forced answer path block after strict follow-up support",
            "test answer path",
        )

    monkeypatch.setattr(
        followup_runtime,
        "build_dprime_single_lane_answer_path",
        block_answer_path,
    )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-small-claims-followup-answer-path-blocked",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_current_source_followup_reentry=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_sequential_proxy_runner(
            calls,
            [
                [
                    _provider_extracted_result(
                        "Example County Reduced Online Small Claims Fee",
                        SMALL_CLAIMS_URL,
                        "Reduced online fee context says eligible filers may pay $20.",
                    )
                ],
                [
                    _provider_result(
                        "Example County Official Standard Paper Filing Fee PDF",
                        "https://example-county.gov/courts/standard-paper-fee.pdf",
                    )
                ],
            ],
        ),
        fetch_read_runner=_official_pdf_read_support_fetch_runner(
            "Example County official fee schedule. The current standard paper "
            "small claims filing fee is $54."
        ),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    assert result.return_code == 2
    assert packet["decision"] == (
        dogfood.BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_ANSWER_PATH_NOT_REACHED
    )
    assert len(calls) == 2
    assert len(dprime_inputs) == 2
    assert packet["followup_provider_calls_attempted"] == 1
    assert packet["followup_fetch_read_completed"] == 1
    assert packet["workbench_gap_reentry_status"] == "runkernel_authorized_executed"
    assert packet["followup_execution_licensed"] is True
    assert packet["dprime_answer_path_ref"]["status"] == "blocked"
    assert packet["final_answer_packet_created"] is False
    assert packet["author_prose_created"] is False
    assert packet["answer_text_present"] is False
    assert packet["product_answer_text"] == ""


def test_licensed_followup_blocks_with_named_exhausted_blocker_when_fetch_fails(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return _assessment_payload(
            plan,
            "Example County small claims online fee may be $20 for eligible filers.",
            support_relation="weak_or_overclaim_risk",
            missing_qualifiers=[str(plan["component_text"])],
            non_support_reason="Strict support was not established.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-small-claims-followup-exhausted",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_current_source_followup_reentry=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_sequential_proxy_runner(
            calls,
            [
                [
                    _provider_extracted_result(
                        "Example County Reduced Online Small Claims Fee",
                        SMALL_CLAIMS_URL,
                        "Reduced online fee context says eligible filers may pay $20.",
                    )
                ],
                [
                    _provider_result(
                        "Example County Standard Fee",
                        "https://example-county.gov/courts/standard-fee",
                    )
                ],
            ],
        ),
        fetch_read_runner=_empty_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    assert result.return_code == 2
    assert packet["decision"] == dogfood.BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_EXHAUSTED
    assert len(calls) == 2
    assert packet["followup_provider_calls_attempted"] == 1
    assert packet["followup_fetch_read_attempts"] == 1
    assert packet["followup_fetch_read_completed"] == 0
    assert packet["followup_execution_licensed"] is True
    assert packet["workbench_gap_reentry_ref"]["workbench_gap_reentry_status"] == (
        "runkernel_authorized_exhausted"
    )
    assert packet["workbench_gap_reentry_ref"]["followup_execution_status"] == (
        "exhausted"
    )


def test_unreadable_high_value_official_candidate_proposes_read_support_gap(
    tmp_path: Path,
) -> None:
    calls: list[GenericProviderProxyRunRequest] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-unreadable-official",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=False,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_result(
                    "Official Example County Small Claims Fee PDF",
                    "https://official.example.gov/courts/small-claims-fees.pdf",
                )
            ],
        ),
        fetch_read_runner=_http_403_pdf_fetch_runner,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    roles = _candidate_roles(packet)
    gap = packet["analysis_gap_search_proposal"]
    reentry = packet["workbench_gap_reentry_ref"]
    assert result.return_code == 2
    assert gap["gap_status"] == "proposed"
    assert gap["gap_kind"] == "unreadable_high_value_candidate"
    assert reentry["workbench_gap_reentry_status"] == "followup_not_licensed"
    assert reentry["gap_sources"] == ["workbench"]
    assert reentry["dprime_gap_ref"] == {}
    assert reentry["followup_execution_licensed"] is False
    assert len(calls) == 1
    assert packet["followup_provider_calls_attempted"] == 0
    assert packet["followup_fetch_read_attempts"] == 0
    assert reentry["runkernel_followup_authorization_ref"] == {}
    assert reentry["fetch_read_executed"] is False
    assert packet["pdf_parsing_opened"] is False
    assert packet["fetch_read_completed"] == 0
    assert packet["fetch_read_packet_created"] == 1
    assert ROLE_UNREADABLE_HIGH_VALUE_OFFICIAL in roles
    assert result.output.startswith(
        "Answer:\nBlocked before answer: official source read support is needed."
    )
    assert packet["official_pdf_table_read_support_needed"] is True
    assert packet["official_pdf_table_read_support_obtained"] is False
    assert packet["official_pdf_table_read_support_raw_content_retained"] is False
    assert packet["official_pdf_table_read_support_satisfies_source_obligation"] is False
    assert packet["official_pdf_table_read_support_citation_eligible"] is False
    report_json = json.loads(
        Path(packet["review_report_json_path"]).read_text(encoding="utf-8")
    )
    assert report_json["gap_reentry"]["workbench_gap_reentry_status"] == (
        "followup_not_licensed"
    )
    _assert_workbench_non_authority(packet)


def test_licensed_workbench_read_support_gap_runs_authorized_followup_pdf_extraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []
    dprime_inputs: list[Mapping[str, Any]] = []
    fetch_attempts: list[str] = []
    fetched_pdf_urls: list[str] = []
    pdf_text = (
        "Example County Clerk official fee schedule. The standard paper small "
        "claims filing fee is $54."
    )
    pdf_url = "https://official.example.gov/courts/small-claims-fees.pdf"
    monkeypatch.setattr(
        dogfood,
        "build_opener",
        lambda _redirect_handler: _RecordingPdfOpener(
            fetched_pdf_urls,
            _PdfResponse(
                _tiny_text_pdf_bytes(pdf_text),
                url=pdf_url,
                content_type="application/pdf",
            ),
        ),
    )

    def staged_fetch(url: str) -> GenericLiveFetchReadResult:
        fetch_attempts.append(url)
        if len(fetch_attempts) == 1:
            return _http_403_pdf_fetch_runner(url)
        return dogfood.fetch_public_url_once(url)

    def fake_review(*_args: Any, input_packet: Mapping[str, Any], **_kwargs: Any) -> dict[str, Any]:
        dprime_inputs.append(dict(input_packet))
        return _assessment_payload(
            plan,
            "The current Example County standard paper small claims filing fee is $54.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-read-support-gap-licensed-followup-pdf",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_current_source_followup_reentry=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_sequential_proxy_runner(
            calls,
            [
                [
                    _provider_result(
                        "Official Example County Small Claims Fee PDF",
                        pdf_url,
                    )
                ],
                [
                    _provider_result(
                        "Official Example County Small Claims Fee PDF",
                        pdf_url,
                    )
                ],
            ],
        ),
        fetch_read_runner=staged_fetch,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    reentry = packet["workbench_gap_reentry_ref"]
    followup_ref = packet["semantic_status_payload"][
        "dprime_followup_search_reentry_ref"
    ]
    assert result.return_code == 0, packet.get("blocker_detail")
    assert len(calls) == 2
    assert calls[1].acquisition_provider_role == "current_source_followup_reentry"
    assert fetch_attempts == [pdf_url, pdf_url]
    assert fetched_pdf_urls == [pdf_url]
    assert len(dprime_inputs) == 1
    assert packet["initial_dprime_model_review_calls_attempted"] == 0
    assert packet["followup_dprime_model_review_calls_attempted"] == 1
    assert packet["initial_provider_calls_attempted"] == 1
    assert packet["followup_provider_calls_attempted"] == 1
    assert packet["followup_provider_calls_completed"] == 1
    assert packet["initial_fetch_read_completed"] == 0
    assert packet["followup_fetch_read_attempts"] == 1
    assert packet["followup_fetch_read_completed"] == 1
    assert reentry["workbench_gap_reentry_status"] == "runkernel_authorized_executed"
    assert reentry["gap_sources"] == ["workbench"]
    assert reentry["followup_execution_licensed"] is True
    assert reentry["runkernel_followup_authorization_ref"]
    assert reentry["followup_planning_ref"]["triggering_workbench_gap_ref"][
        "gap_kind"
    ] == "unreadable_high_value_candidate"
    assert followup_ref["product_followup_provider_execution_after_authorization"] is True
    assert followup_ref["product_followup_authorization_consumed"] is True
    assert followup_ref["product_followup_search_authorization_ref"]
    assert followup_ref["product_followup_search_executor_handoff_ref"]
    assert reentry["followup_pdf_text_extraction_attempted"] is True
    assert reentry["followup_pdf_text_extraction_status_summary"] == {"extracted": 1}
    assert packet["final_answer_packet_created"] is True
    assert packet["author_prose_created"] is True
    assert packet["source_display_entries"]
    assert packet["product_answer_text"] == (
        "The current Example County standard paper small claims filing fee is $54."
    )
    assert packet["product_correctness_claimed"] is False
    followup_fetch_packet = _retained_followup_fetch_read_packet(result)
    reference = followup_fetch_packet["reference_records"][0]
    assert reference["fetch_read_status"] == "readable"
    assert reference["content_type"] == "application/pdf"
    assert reference["bounded_text"] == pdf_text
    assert reference["pdf_text_extraction_attempted"] is True
    assert reference["pdf_text_extraction_status"] == "extracted"
    assert reference["raw_pdf_bytes_retained"] is False
    assert reference["raw_pdf_text_retained"] is False
    assert packet["provider_snippets_used_as_evidence"] is False
    _assert_workbench_non_authority(packet)


def test_licensed_workbench_read_support_gap_exhausts_when_followup_fetch_fails(
    tmp_path: Path,
) -> None:
    calls: list[GenericProviderProxyRunRequest] = []
    dprime_inputs: list[Mapping[str, Any]] = []
    pdf_url = "https://official.example.gov/courts/small-claims-fees.pdf"

    def fake_review(*_args: Any, input_packet: Mapping[str, Any], **_kwargs: Any) -> dict[str, Any]:
        dprime_inputs.append(dict(input_packet))
        return _assessment_payload(
            build_generic_query_relation_plan(SMALL_CLAIMS_QUERY),
            "The current Example County standard paper small claims filing fee is $54.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-read-support-gap-licensed-followup-exhausted",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_current_source_followup_reentry=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_sequential_proxy_runner(
            calls,
            [
                [_provider_result("Official Example County Small Claims Fee PDF", pdf_url)],
                [_provider_result("Official Example County Small Claims Fee PDF", pdf_url)],
            ],
        ),
        fetch_read_runner=_http_403_pdf_fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    reentry = packet["workbench_gap_reentry_ref"]
    assert result.return_code == 2
    assert packet["decision"] == dogfood.BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_EXHAUSTED
    assert len(calls) == 2
    assert len(dprime_inputs) == 0
    assert packet["followup_provider_calls_attempted"] == 1
    assert packet["followup_provider_calls_completed"] == 1
    assert packet["followup_fetch_read_attempts"] == 1
    assert packet["followup_fetch_read_completed"] == 0
    assert packet["followup_execution_licensed"] is True
    assert reentry["workbench_gap_reentry_status"] == "runkernel_authorized_exhausted"
    assert reentry["followup_execution_status"] == "exhausted"
    assert reentry["runkernel_followup_authorization_ref"]
    assert packet["final_answer_packet_created"] is False
    assert packet["author_prose_created"] is False
    assert packet["product_answer_text"] == ""
    assert packet["provider_snippets_used_as_evidence"] is False
    _assert_workbench_non_authority(packet)


def test_official_pdf_fixture_read_support_feeds_existing_fetch_packet_workbench_and_dprime(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []
    captured_input: dict[str, Any] = {}
    readable_text = (
        "Example County Clerk official fee schedule. The standard paper small "
        "claims filing fee is $54."
    )

    def fake_review(*_args: Any, input_packet: Mapping[str, Any], **_kwargs: Any) -> dict[str, Any]:
        captured_input.update(dict(input_packet))
        return _assessment_payload(
            plan,
            "The current Example County standard paper small claims filing fee is $54.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-official-pdf-read-support",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_result(
                    "Example County Official Small Claims Fee Schedule PDF",
                    "https://example-county.gov/courts/small-claims-fee-schedule.pdf",
                )
            ],
        ),
        fetch_read_runner=_official_pdf_read_support_fetch_runner(readable_text),
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    roles = _candidate_roles(packet)
    assert packet["fetch_read_attempts"] == 1
    assert packet["fetch_read_completed"] == 1
    assert packet["official_pdf_table_read_support_adapter"] == (
        "existing_fetch_read_content_packet"
    )
    assert packet["official_pdf_table_artifact_candidate_count"] == 1
    assert packet["official_pdf_table_read_support_obtained"] is True
    assert packet["official_pdf_table_read_support_needed"] is False
    assert packet["official_pdf_table_read_support_adds_dependency"] is False
    assert packet["official_pdf_table_read_support_uses_ocr"] is False
    assert packet["official_pdf_table_read_support_uses_browser_automation"] is False
    assert packet["pdf_parsing_opened"] is False
    assert ROLE_STRICT_ANSWER_SUPPORT in roles
    assert packet["analysis_gap_search_proposal"]["gap_status"] == "not_required"
    assert packet["workbench_gap_reentry_ref"]["workbench_gap_reentry_status"] == (
        "not_required"
    )

    dprime_ref = packet["workbench_dprime_dossier"]["dprime_review_candidate_ref"]
    assert dprime_ref["official_pdf_or_table_artifact_candidate"] is True
    assert dprime_ref["official_artifact_type"] == "pdf_table_artifact"
    assert dprime_ref["official_artifact_read_support_status"] == (
        dogfood.OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_READABLE
    )
    assert captured_input["workbench_dprime_dossier_ref"]["dossier_digest"] == (
        packet["workbench_dprime_dossier_ref"]["dossier_digest"]
    )

    fetch_packet = _retained_fetch_read_packet(result)
    reference = fetch_packet["reference_records"][0]
    assert reference["content_type"] == "application/pdf"
    assert reference["fetch_read_status"] == "readable"
    assert reference["official_artifact_read_support"] is True
    assert reference["official_artifact_type"] == "pdf_table_artifact"
    assert reference["bounded_text"] == readable_text
    assert reference["official_artifact_read_support_raw_content_retained"] is False
    assert reference["official_artifact_read_support_creates_source_authority"] is False
    assert reference["official_artifact_read_support_satisfies_source_obligation"] is False
    assert reference["official_artifact_read_support_citation_eligible"] is False
    assert reference["official_artifact_read_support_claims_correctness"] is False
    assert reference["not_citation_eligible"] is True
    assert reference["not_source_obligation_satisfaction"] is True
    _assert_workbench_non_authority(packet)


def test_contextual_html_is_not_preferred_over_readable_official_pdf_artifact(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return _assessment_payload(
            plan,
            "The current Example County standard paper small claims filing fee is $54.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-contextual-html-vs-official-pdf",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "Example County Online Discount Filing Fee",
                    "https://example-county.gov/courts/online-discount",
                    (
                        "Online filing discount. Eligible filers may pay a "
                        "reduced online small claims fee of $20."
                    ),
                    rank=1,
                ),
                _provider_extracted_result(
                    "Example County Official Small Claims Fee Schedule PDF",
                    "https://example-county.gov/courts/small-claims-fee-schedule.pdf",
                    (
                        "Example County Clerk official fee schedule. The standard "
                        "paper small claims filing fee is $54."
                    ),
                    rank=2,
                    content_type="application/pdf",
                ),
            ],
        ),
        fetch_read_runner=_fetch_read_must_not_run,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    selected = packet["workbench_dprime_dossier"]["dprime_review_candidate_ref"]
    assert selected["url"].endswith("small-claims-fee-schedule.pdf")
    assert selected["official_pdf_or_table_artifact_candidate"] is True
    assert selected["official_artifact_read_support_status"] == (
        dogfood.OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_READABLE
    )
    assert packet["official_pdf_table_read_support_obtained"] is True
    assert packet["candidate_evidence_triage_packet"]["contextual_candidate_refs"]
    assert packet["candidate_evidence_triage_packet"]["overclaim_risk_candidate_refs"]
    assert packet["analysis_gap_search_proposal"]["gap_status"] == "not_required"
    assert packet["provider_snippets_used_as_evidence"] is False
    assert packet["candidate_selection_uses_provider_snippet"] is False
    _assert_workbench_non_authority(packet)


def test_contextual_provider_html_does_not_skip_direct_official_pdf_read_support(
    tmp_path: Path,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []
    captured_input: dict[str, Any] = {}
    fetched_urls: list[str] = []
    readable_text = (
        "Example County Clerk official fee schedule. The standard paper small "
        "claims filing fee is $54."
    )
    inner_fetch_runner = _official_pdf_read_support_fetch_runner(readable_text)

    def fetch_runner(url: str) -> GenericLiveFetchReadResult:
        fetched_urls.append(url)
        return inner_fetch_runner(url)

    def fake_review(*_args: Any, input_packet: Mapping[str, Any], **_kwargs: Any) -> dict[str, Any]:
        captured_input.update(dict(input_packet))
        return _assessment_payload(
            plan,
            "The current Example County standard paper small claims filing fee is $54.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-contextual-html-direct-official-pdf-read-support",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "Example County Online Discount Filing Fee",
                    "https://example-county.gov/courts/online-discount",
                    (
                        "Online filing discount. Eligible filers may pay a "
                        "reduced online small claims fee of $20."
                    ),
                    rank=1,
                ),
                _provider_result(
                    "Example County Official Small Claims Fee Schedule PDF",
                    "https://example-county.gov/courts/small-claims-fee-schedule.pdf",
                    rank=2,
                ),
            ],
        ),
        fetch_read_runner=fetch_runner,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    assert fetched_urls == [
        "https://example-county.gov/courts/small-claims-fee-schedule.pdf"
    ]
    assert packet["provider_extracted_content_candidate_count"] == 1
    assert packet["provider_extracted_content_handoff_created"] is False
    assert packet["direct_fetch_read_attempts"] == 1
    assert packet["fetch_read_attempts"] == 1
    assert packet["fetch_read_completed"] == 1
    assert packet["fetch_read_cap_preserved"] is True
    assert packet["fetch_read_cap_value"] == dogfood.MAX_FETCH_READ_ATTEMPTS
    assert packet["analysis_gap_search_proposal"]["gap_status"] == "not_required"
    assert packet["dprime_model_review_calls_completed"] == 1

    triage = packet["candidate_evidence_triage_packet"]
    assert triage["contextual_candidate_refs"]
    assert triage["overclaim_risk_candidate_refs"]
    assert triage["contextual_candidate_refs"][0]["url"].endswith("online-discount")
    dprime_ref = packet["workbench_dprime_dossier"]["dprime_review_candidate_ref"]
    assert dprime_ref["url"].endswith("small-claims-fee-schedule.pdf")
    assert dprime_ref["official_pdf_or_table_artifact_candidate"] is True
    assert dprime_ref["official_artifact_read_support_status"] == (
        dogfood.OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_READABLE
    )
    assert captured_input["workbench_dprime_dossier_ref"]["dossier_digest"] == (
        packet["workbench_dprime_dossier_ref"]["dossier_digest"]
    )

    fetch_packet = _retained_fetch_read_packet(result)
    reference = fetch_packet["reference_records"][0]
    assert reference["original_source_url"].endswith("small-claims-fee-schedule.pdf")
    assert reference["content_type"] == "application/pdf"
    assert reference["bounded_text"] == readable_text
    assert reference["official_artifact_read_support"] is True
    assert reference["official_artifact_read_support_raw_content_retained"] is False
    assert reference["official_artifact_read_support_creates_source_authority"] is False
    assert reference["official_artifact_read_support_satisfies_source_obligation"] is False
    assert reference["official_artifact_read_support_citation_eligible"] is False
    assert reference["official_artifact_read_support_claims_correctness"] is False
    assert packet["provider_snippets_used_as_evidence"] is False
    assert packet["candidate_selection_uses_provider_snippet"] is False
    assert packet["pdf_parsing_opened"] is False
    assert packet["official_pdf_table_read_support_adds_dependency"] is False
    assert packet["official_pdf_table_read_support_uses_ocr"] is False
    assert packet["official_pdf_table_read_support_uses_browser_automation"] is False
    assert packet["fap_calls"] == 0
    assert packet["author_calls"] == 0
    _assert_workbench_non_authority(packet)


def test_contextual_html_plus_official_pdf_uses_generic_pdf_text_extraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    calls: list[GenericProviderProxyRunRequest] = []
    captured_input: dict[str, Any] = {}
    fetched_urls: list[str] = []
    pdf_text = (
        "Example County Clerk official fee schedule. The standard paper small "
        "claims filing fee is $54."
    )
    pdf_url = "https://example-county.gov/courts/small-claims-fee-schedule.pdf"
    monkeypatch.setattr(
        dogfood,
        "build_opener",
        lambda _redirect_handler: _RecordingPdfOpener(
            fetched_urls,
            _PdfResponse(
                _tiny_text_pdf_bytes(pdf_text),
                url=pdf_url,
                content_type="application/pdf",
            ),
        ),
    )

    def fake_review(*_args: Any, input_packet: Mapping[str, Any], **_kwargs: Any) -> dict[str, Any]:
        captured_input.update(dict(input_packet))
        return _assessment_payload(
            plan,
            "The current Example County standard paper small claims filing fee is $54.",
        )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-contextual-html-generic-pdf-extraction",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                _provider_extracted_result(
                    "Example County Online Discount Filing Fee",
                    "https://example-county.gov/courts/online-discount",
                    (
                        "Online filing discount. Eligible filers may pay a "
                        "reduced online small claims fee of $20."
                    ),
                    rank=1,
                ),
                _provider_result(
                    "Example County Official Small Claims Fee Schedule PDF",
                    pdf_url,
                    rank=2,
                ),
            ],
        ),
        fetch_read_runner=dogfood.fetch_public_url_once,
        dprime_model_review_callable=fake_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    assert fetched_urls == [pdf_url]
    assert packet["fetch_read_completed"] == 1
    assert packet["pdf_text_extraction_attempted"] is True
    assert packet["pdf_text_extraction_status_summary"] == {"extracted": 1}
    assert packet["pdf_text_extraction_char_count"] == len(pdf_text)
    assert packet["pdf_text_extraction_page_count"] == 1
    assert packet["pdf_content_type_support_opened"] is True
    assert packet["pdf_parsing_opened"] is True
    assert packet["raw_pdf_bytes_retained"] is False
    assert packet["raw_pdf_text_retained"] is False
    assert packet["bounded_text_retained"] is True
    assert packet["pdf_text_extraction_uses_ocr"] is False
    assert packet["pdf_text_extraction_uses_browser_automation"] is False
    assert packet["pdf_text_extraction_uses_external_service"] is False
    assert packet["official_pdf_table_read_support_obtained"] is True

    triage = packet["candidate_evidence_triage_packet"]
    assert triage["contextual_candidate_refs"]
    assert triage["overclaim_risk_candidate_refs"]
    dprime_ref = packet["workbench_dprime_dossier"]["dprime_review_candidate_ref"]
    assert dprime_ref["url"].endswith("small-claims-fee-schedule.pdf")
    assert dprime_ref["official_pdf_or_table_artifact_candidate"] is True
    assert captured_input["workbench_dprime_dossier_ref"]["dossier_digest"] == (
        packet["workbench_dprime_dossier_ref"]["dossier_digest"]
    )

    fetch_packet = _retained_fetch_read_packet(result)
    reference = fetch_packet["reference_records"][0]
    assert reference["content_type"] == "application/pdf"
    assert reference["fetch_read_status"] == "readable"
    assert reference["bounded_text"] == pdf_text
    assert reference["pdf_text_extraction_attempted"] is True
    assert reference["pdf_text_extraction_status"] == "extracted"
    assert reference["raw_pdf_bytes_retained"] is False
    assert reference["raw_pdf_text_retained"] is False
    assert reference["bounded_text_retained"] is True
    assert reference["official_artifact_read_support"] is True
    assert reference["official_artifact_read_support_satisfies_source_obligation"] is False
    assert reference["official_artifact_read_support_citation_eligible"] is False
    assert reference["source_obligation_satisfied"] is False
    assert reference["citation_eligible"] is False
    assert packet["provider_snippets_used_as_evidence"] is False
    _assert_workbench_non_authority(packet)


def test_provider_snippet_text_does_not_create_workbench_strict_support(
    tmp_path: Path,
) -> None:
    calls: list[GenericProviderProxyRunRequest] = []
    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="workbench-snippet-not-evidence",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=False,
        entrypoint_surface=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
        entrypoint_kind=dogfood.PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=False,
        supported_query_class=dogfood.PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        provider_proxy_runner=_recording_proxy_runner(
            calls,
            [
                {
                    **_provider_result(
                        "Example County Clerk Fee Page",
                        SMALL_CLAIMS_URL,
                    ),
                    "snippet": (
                        "Snippet says the standard paper small claims filing fee "
                        "is $54, but no extracted source text is retained."
                    ),
                }
            ],
        ),
        fetch_read_runner=_http_403_pdf_fetch_runner,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    roles = _candidate_roles(packet)
    assert result.return_code == 2
    assert ROLE_STRICT_ANSWER_SUPPORT not in roles
    assert packet["provider_snippets_used_as_evidence"] is False
    assert packet["candidate_selection_uses_provider_snippet"] is False
    candidate = packet["fetch_read_candidate_diagnostics"][0]
    assert candidate["provider_snippet_used_as_evidence"] is False
    assert candidate["provider_snippet_used_as_extracted_source_text"] is False
    assert packet["analysis_gap_search_proposal"]["gap_status"] == "proposed"
    _assert_workbench_non_authority(packet)


def test_analyst_workbench_runtime_has_no_domain_specific_production_branching() -> None:
    forbidden_literals = ("USCIS", "N-400", "G-1055", "$760", "$710", "$380")
    production_paths = (
        ROOT / "core" / "analyst_workbench_runtime.py",
        ROOT / "core" / "dprime_model_review_assessment.py",
        ROOT / "proplex" / "live_semantic_coverage_status.py",
        ROOT / "proplex" / "mvp_single_relation_live_dogfood_run.py",
    )
    for path in production_paths:
        text = path.read_text(encoding="utf-8")
        for literal in forbidden_literals:
            assert literal not in text, f"{literal} leaked into {path}"


def _recording_proxy_runner(
    calls: list[GenericProviderProxyRunRequest],
    results: list[dict[str, Any]],
) -> Any:
    def runner(request: GenericProviderProxyRunRequest) -> GenericProviderProxyRunResult:
        calls.append(request)
        payload = {
            "request_kind": "provider_proxy_search",
            "provider": request.provider,
            "operation": request.operation,
            "result_count": len(results),
            "results": results,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        }
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return GenericProviderProxyRunResult(
            return_code=0,
            output_path=request.output_path,
            provider_calls_attempted=1,
            provider_calls_completed=1,
        )

    return runner


def _sequential_proxy_runner(
    calls: list[GenericProviderProxyRunRequest],
    result_batches: list[list[dict[str, Any]]],
) -> Any:
    def runner(request: GenericProviderProxyRunRequest) -> GenericProviderProxyRunResult:
        calls.append(request)
        index = min(len(calls) - 1, len(result_batches) - 1)
        results = result_batches[index]
        payload = {
            "request_kind": "provider_proxy_search",
            "provider": request.provider,
            "operation": request.operation,
            "result_count": len(results),
            "results": results,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        }
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return GenericProviderProxyRunResult(
            return_code=0,
            output_path=request.output_path,
            provider_calls_attempted=1,
            provider_calls_completed=1,
        )

    return runner


def _provider_result(title: str, url: str, *, rank: int = 1) -> dict[str, Any]:
    return {
        "title": title,
        "url": url,
        "domain": urlparse(url).netloc.lower(),
        "snippet": f"{title} states the current filing fee.",
        "published_or_observed_date": "2026-07-03",
        "result_rank": rank,
        "provider_call_index": 1,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _provider_extracted_result(
    title: str,
    url: str,
    extracted_text: str,
    *,
    rank: int = 1,
    content_type: str = "text/html",
) -> dict[str, Any]:
    result = _provider_result(title, url, rank=rank)
    digest = dogfood._digest_json({"provider_extracted_text": extracted_text})
    result.update(
        {
            "provider_extracted_text": extracted_text,
            "provider_extracted_text_sanitized": True,
            "provider_extracted_text_bounded": True,
            "provider_extracted_text_char_count": len(extracted_text),
            "provider_extracted_text_digest": digest,
            "provider_extracted_source_text_digest": digest,
            "provider_extracted_content_type": content_type,
            "provider_extracted_at": "2026-07-03T00:00:00+00:00",
        }
    )
    return result


def _failing_fetch_runner(url: str) -> GenericLiveFetchReadResult:
    raise AssertionError(f"provider-extracted content should bypass fetch: {url}")


def _fetch_read_must_not_run(url: str) -> GenericLiveFetchReadResult:
    raise AssertionError(f"fetch/read should not run for provider fixture: {url}")


def _http_403_pdf_fetch_runner(url: str) -> GenericLiveFetchReadResult:
    parsed = urlparse(url)
    return GenericLiveFetchReadResult(
        attempted_url=url,
        final_url=url,
        final_domain=parsed.netloc.lower(),
        status_code=403,
        status_class="4xx",
        content_type="application/pdf",
        fetched_byte_count=0,
        sanitized_text="",
        content_title="Official PDF",
        redirect_count=0,
        retrieved_or_observed_at="2026-07-03T00:00:00+00:00",
    )


def _official_pdf_read_support_fetch_runner(text: str) -> Any:
    def runner(url: str) -> GenericLiveFetchReadResult:
        parsed = urlparse(url)
        return GenericLiveFetchReadResult(
            attempted_url=url,
            final_url=url,
            final_domain=parsed.netloc.lower(),
            status_code=200,
            status_class="2xx",
            content_type="application/pdf",
            fetched_byte_count=len(text.encode("utf-8")),
            sanitized_text=text,
            content_title="Official PDF",
            redirect_count=0,
            retrieved_or_observed_at="2026-07-03T00:00:00+00:00",
            official_artifact_read_support=True,
            official_artifact_read_support_source=(
                dogfood.OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_FETCH_RUNNER
            ),
        )

    return runner


def _fake_fetch_runner(text: str) -> Any:
    def runner(url: str) -> GenericLiveFetchReadResult:
        parsed = urlparse(url)
        return GenericLiveFetchReadResult(
            attempted_url=url,
            final_url=url,
            final_domain=parsed.netloc.lower(),
            status_code=200,
            status_class="2xx",
            content_type="text/html",
            fetched_byte_count=512,
            sanitized_text=text,
            content_title="Fake Source",
            redirect_count=0,
            retrieved_or_observed_at="2026-07-03T00:00:00+00:00",
        )

    return runner


def _empty_fetch_runner(url: str) -> GenericLiveFetchReadResult:
    parsed = urlparse(url)
    return GenericLiveFetchReadResult(
        attempted_url=url,
        final_url=url,
        final_domain=parsed.netloc.lower(),
        status_code=200,
        status_class="2xx",
        content_type="text/html",
        fetched_byte_count=0,
        sanitized_text="",
        content_title="Empty Source",
        redirect_count=0,
        retrieved_or_observed_at="2026-07-03T00:00:00+00:00",
    )


class _PdfHeaders(dict[str, str]):
    def get(self, key: str, default: str | None = None) -> str:
        return super().get(key.lower(), default or "")


class _PdfResponse:
    def __init__(self, body: bytes, *, url: str, content_type: str) -> None:
        self._body = body
        self._url = url
        self.status = 200
        self.headers = _PdfHeaders({"content-type": content_type})

    def __enter__(self) -> "_PdfResponse":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url


class _RecordingPdfOpener:
    def __init__(self, fetched_urls: list[str], response: _PdfResponse) -> None:
        self._fetched_urls = fetched_urls
        self._response = response

    def open(self, request: Any, *, timeout: int) -> _PdfResponse:
        assert timeout == 20
        self._fetched_urls.append(request.full_url)
        return self._response


def _tiny_text_pdf_bytes(text: str) -> bytes:
    from io import BytesIO

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({safe_text}) Tj ET".encode("ascii"))
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = writer._add_object(stream)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def _assessment_payload(
    plan: Mapping[str, Any],
    answer_claim: str,
    *,
    support_relation: str = "directly_supports",
    missing_qualifiers: list[str] | None = None,
    non_support_reason: str = "",
) -> dict[str, Any]:
    component_text = str(plan["component_text"])
    missing = [] if missing_qualifiers is None else list(missing_qualifiers)
    direct = support_relation == "directly_supports"
    return {
        "source_proposition": f"The retained source states: {answer_claim}",
        "answer_component_claim": {
            "component_id": plan["component_id"],
            "claim": answer_claim,
        },
        "support_relation": support_relation,
        "required_qualifiers": [component_text],
        "observed_qualifiers": [] if missing else [component_text],
        "missing_qualifiers": missing,
        "scope_check": {"status": "passed" if direct else "insufficient"},
        "currentness_check": {"status": "current"},
        "contradiction_check": {"status": "absent"},
        "evidential_adequacy_notes": "Fake review maps to the plan component.",
        "non_support_reason_when_not_direct": non_support_reason,
        "producer_abstained": False,
        "challenge_recommended": not direct,
        "closed_surface_flags": {
            "model_review_licensed": False,
            "assessment_created": False,
            "validated_support_proposal_created": False,
            "run_kernel_support_admission_request_created": False,
            "semantic_observation_created": False,
            "component_coverage_bound": False,
            "citation_eligibility_claimed": False,
            "source_obligation_satisfaction_claimed": False,
            "answer_text_created": False,
            "product_correctness_claimed": False,
        },
    }


def _candidate_roles(packet: Mapping[str, Any]) -> set[str]:
    proposals = packet["candidate_evidence_triage_packet"]["evidence_role_proposals"]
    return {str(item["role"]) for item in proposals}


def _retained_fetch_read_packet(result: Any) -> Mapping[str, Any]:
    root = Path(result.retained_artifact_root)
    path = root / dogfood.FETCH_READ_ARTIFACT_DIR / dogfood.FETCH_READ_CONTENT_PACKET_NAME
    return json.loads(path.read_text(encoding="utf-8"))


def _retained_followup_fetch_read_packet(result: Any) -> Mapping[str, Any]:
    root = Path(result.retained_artifact_root)
    path = (
        root
        / "current_source_followup_reentry"
        / dogfood.FETCH_READ_ARTIFACT_DIR
        / dogfood.FETCH_READ_CONTENT_PACKET_NAME
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_workbench_non_authority(packet: Mapping[str, Any]) -> None:
    for section_key in (
        "candidate_evidence_triage_packet",
        "analyst_workbench_packet",
        "analysis_gap_search_proposal",
        "workbench_dprime_dossier",
        "workbench_reduction_projection",
    ):
        section = packet[section_key]
        assert section["proposal_only"] is True
        assert section["source_obligation_satisfied"] is False
        assert section["citation_eligible"] is False
        assert section["source_authority_finalized"] is False
        assert section["product_correctness_claimed"] is False
        assert section["raw_private_retention_flags"] == dogfood.RAW_FALSE_FLAGS
        for raw_key in dogfood.RAW_FALSE_FLAGS:
            assert section[raw_key] is False
    projection = packet["workbench_reduction_projection"]
    assert projection["owner"] == "AnalystWorkbenchRuntime"
    assert projection["run_kernel_reduced"] is False
    assert projection["run_kernel_reduction_pending"] is True
    assert projection["proposed_for_runkernel_reduction"] is True
