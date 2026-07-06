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

import proplex.mvp_single_relation_live_dogfood_run as dogfood
from core.analyst_workbench_runtime import (
    ROLE_ANSWER_ADJACENT_CONTEXT,
    ROLE_OVERCLAIM_RISK,
    ROLE_QUALIFIER_EXCEPTION_CONTEXT,
    ROLE_STRICT_ANSWER_SUPPORT,
    ROLE_UNREADABLE_HIGH_VALUE_OFFICIAL,
    WORKBENCH_REDUCTION_FOLLOWUP_NOT_LICENSED,
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
    assert reentry["fetch_read_executed"] is False
    assert packet["pdf_parsing_opened"] is False
    assert packet["fetch_read_completed"] == 0
    assert packet["fetch_read_packet_created"] == 1
    assert ROLE_UNREADABLE_HIGH_VALUE_OFFICIAL in roles
    assert result.output.startswith(
        "Answer:\nBlocked before answer: official strict support follow-up is needed."
    )
    report_json = json.loads(
        Path(packet["review_report_json_path"]).read_text(encoding="utf-8")
    )
    assert report_json["gap_reentry"]["workbench_gap_reentry_status"] == (
        "followup_not_licensed"
    )
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
            "provider_extracted_content_type": "text/html",
            "provider_extracted_at": "2026-07-03T00:00:00+00:00",
        }
    )
    return result


def _failing_fetch_runner(url: str) -> GenericLiveFetchReadResult:
    raise AssertionError(f"provider-extracted content should bypass fetch: {url}")


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


def _assessment_payload(plan: Mapping[str, Any], answer_claim: str) -> dict[str, Any]:
    component_text = str(plan["component_text"])
    return {
        "source_proposition": f"The retained source states: {answer_claim}",
        "answer_component_claim": {
            "component_id": plan["component_id"],
            "claim": answer_claim,
        },
        "support_relation": "directly_supports",
        "required_qualifiers": [component_text],
        "observed_qualifiers": [component_text],
        "missing_qualifiers": [],
        "scope_check": {"status": "passed"},
        "currentness_check": {"status": "current"},
        "contradiction_check": {"status": "absent"},
        "evidential_adequacy_notes": "Fake review maps to the plan component.",
        "non_support_reason_when_not_direct": "",
        "producer_abstained": False,
        "challenge_recommended": False,
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
