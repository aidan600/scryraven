"""PRODUCT-PATH-REGRESSION: AnalystFindingProposal V1 custody contract.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: current-source single-fact Workbench bundle
consumed by proplex.mvp_single_relation_live_dogfood_run and D-prime refs.
Runtime consumer: core.analyst_workbench_runtime ->
proplex.live_semantic_coverage_status D-prime dossier/input refs.
Why ordinary product-path work cannot be done directly: offline validation must
not run live provider, fetch/read, retrieval, or model calls; the Workbench
builder is the product-consumed seam and fake model output is structured only.
Integration deadline: current phase.
Exit condition: keep while AnalystFindingProposal remains the Workbench to
D-prime analysis custody contract, or replace with broader product-path coverage.
Why this is not a shadow product path: tests use the existing Workbench builder
and D-prime handoff refs, not an alternate answer path or formatter.
Forbidden interpretation: Analyst findings are not evidence, citations, answer
authority, source-obligation satisfaction, FAP/Author output, live validation
correctness, or product correctness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import pytest

import proplex.mvp_single_relation_live_dogfood_run as dogfood
from core.analyst_workbench_runtime import (
    REQUESTED_ANSWER_TYPE_ADJACENT_ONLY,
    REQUESTED_ANSWER_TYPE_MATCH,
    TRIAGE_ROLE_ANSWER_BEARING,
    TRIAGE_ROLE_QUALIFIER_EXCEPTION,
    TRIAGE_ROLE_UNREADABLE_HIGH_VALUE,
    build_current_source_record_analyst_workbench,
)
from core.current_source_analyst_finding_proposal import (
    ANALYST_MODEL_ROLE_SMART,
    ANALYST_ROLE_SURFACE,
    FINDING_STATUS_FOLLOWUP_REQUIRED,
    FINDING_STATUS_SOURCE_GROUNDED_PROPOSED,
    MODEL_ADAPTER_KIND_FAKE_TEST,
    MODEL_ADAPTER_KIND_REAL_SMART,
    MODEL_ASSISTED_NOT_RUN_MISSING_ADAPTER,
    MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE,
    MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE_AND_ADAPTER,
    AnalystFindingProposalError,
    build_analyst_finding_safe_model_input_packet,
    build_fake_model_assisted_analyst_finding_proposal,
    build_model_assisted_analyst_finding_proposal,
    build_model_assisted_analyst_license,
    validate_analyst_finding_safe_model_input_packet,
)
from core.generic_query_to_relation_planning import build_generic_query_relation_plan

SMALL_CLAIMS_QUERY = (
    "What is the current filing fee for small claims in Example County?"
)
SMALL_CLAIMS_REQUIREMENT_QUERY = (
    "What is the current filing requirement for Example County small claims?"
)
SMALL_CLAIMS_URL = "https://example-county.invalid/civil/small-claims-fees"
ROOT = Path(__file__).resolve().parents[1]


def test_answer_bearing_evidence_produces_source_grounded_analyst_finding() -> None:
    bundle = _direct_workbench_bundle(
        SMALL_CLAIMS_QUERY,
        [
            _direct_provider_result(
                "Official Reduced Fee And Waiver Context",
                "https://example-county.gov/courts/reduced-fee-waiver",
                "Fee waiver eligibility depends on income and is not the standard fee.",
                rank=1,
            ),
            _direct_provider_result(
                "Official Current Standard Filing Fee",
                "https://example-county.gov/courts/current-filing-fee",
                "The current standard paper small claims filing fee is $54.",
                rank=2,
                selected=True,
            ),
            _direct_provider_result(
                "Official Fee Schedule PDF",
                "https://example-county.gov/courts/fee-schedule.pdf",
                None,
                rank=3,
                official_artifact=True,
                unreadable=True,
            ),
        ],
    )

    finding = _finding(bundle)
    answer_claim = finding["proposed_answer_claim"]
    support_map = finding["source_support_map"]

    assert finding["finding_status"] == FINDING_STATUS_SOURCE_GROUNDED_PROPOSED
    assert answer_claim["requested_answer_type"] == (
        "fee_amount_current_standard_value"
    )
    assert answer_claim["expected_value_shape"] == "currency_amount"
    assert answer_claim["selected_answer_bearing_candidate_refs"]
    assert answer_claim["source_support_map_ref"] == finding["source_support_map_ref"]
    assert finding["analysis_body"]["analysis_summary"]
    assert finding["analysis_body"]["analysis_claim_refs"]
    assert finding["source_support_map_ref"]["source_support_map_digest"]
    assert support_map["analysis_claim_support_edges"]
    assert _candidate_ids(answer_claim["selected_answer_bearing_candidate_refs"]) == {
        "direct-candidate-2"
    }
    assert "direct-candidate-1" in _candidate_ids(
        finding["adjacent_context_candidate_refs"]
    )
    assert "direct-candidate-3" in _candidate_ids(
        finding["unreadable_high_value_candidate_refs"]
    )
    assert finding["caveat_refs"]
    assert finding["unresolved_gap_refs"]
    assert finding["requires_dprime_validation"] is True
    _assert_finding_non_authority(finding)


def test_adjacent_only_evidence_does_not_produce_answer_claim() -> None:
    bundle = _direct_workbench_bundle(
        SMALL_CLAIMS_QUERY,
        [
            _direct_provider_result(
                "Official Online Discount Context",
                "https://example-county.gov/courts/online-discount",
                "Eligible online filers may pay a reduced small claims fee of $20.",
                rank=1,
                selected=True,
            ),
            _direct_provider_result(
                "Official Fee Schedule PDF",
                "https://example-county.gov/courts/fee-schedule.pdf",
                None,
                rank=2,
                official_artifact=True,
                unreadable=True,
            ),
        ],
    )

    finding = _finding(bundle)
    triage = bundle["candidate_evidence_triage_packet"]

    assert "proposed_answer_claim" not in finding
    assert finding["finding_status"] == FINDING_STATUS_FOLLOWUP_REQUIRED
    assert finding["selected_answer_bearing_candidate_refs"] == []
    assert finding["adjacent_claim_exclusion_refs"]
    assert finding["unresolved_gap_refs"]
    assert triage["selected_answer_bearing_candidate_refs"] == []
    assert triage["candidate_triage_records"][1]["proposed_candidate_role"] == (
        TRIAGE_ROLE_UNREADABLE_HIGH_VALUE
    )
    assert _candidate_ids(finding["unreadable_high_value_candidate_refs"]) == {
        "direct-candidate-2"
    }
    _assert_finding_non_authority(finding)


def test_same_source_text_changes_analysis_under_different_binding() -> None:
    candidate_text = "Applicants must file on paper for this current filing."
    fee_bundle = _direct_workbench_bundle(
        SMALL_CLAIMS_QUERY,
        [
            _direct_provider_result(
                "Official Filing Requirement Text",
                SMALL_CLAIMS_URL,
                candidate_text,
                rank=1,
                selected=True,
            ),
        ],
    )
    requirement_bundle = _direct_workbench_bundle(
        SMALL_CLAIMS_REQUIREMENT_QUERY,
        [
            _direct_provider_result(
                "Official Filing Requirement Text",
                SMALL_CLAIMS_URL,
                candidate_text,
                rank=1,
                selected=True,
            ),
        ],
    )

    fee_record = fee_bundle["candidate_evidence_triage_packet"][
        "candidate_triage_records"
    ][0]
    requirement_record = requirement_bundle["candidate_evidence_triage_packet"][
        "candidate_triage_records"
    ][0]

    assert fee_record["requested_answer_type_match_status"] == (
        REQUESTED_ANSWER_TYPE_ADJACENT_ONLY
    )
    assert fee_record["proposed_candidate_role"] == TRIAGE_ROLE_QUALIFIER_EXCEPTION
    assert "proposed_answer_claim" not in _finding(fee_bundle)
    assert requirement_record["requested_answer_type_match_status"] == (
        REQUESTED_ANSWER_TYPE_MATCH
    )
    assert requirement_record["proposed_candidate_role"] == TRIAGE_ROLE_ANSWER_BEARING
    assert _finding(requirement_bundle)["proposed_answer_claim"]


def test_fake_model_assisted_analyst_output_validates_without_raw_retention() -> None:
    bundle = _answer_bearing_bundle()
    deterministic = _finding(bundle)

    def fake_adapter(input_packet: Mapping[str, Any]) -> Mapping[str, Any]:
        assert input_packet["raw_prompt_retained"] is False
        assert input_packet["raw_model_response_retained"] is False
        return {"analyst_finding_proposal": deterministic}

    proposal = build_fake_model_assisted_analyst_finding_proposal(
        triage_packet=bundle["candidate_evidence_triage_packet"],
        analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
        fake_model_adapter=fake_adapter,
    )

    assert proposal["model_assisted_analysis_run"] is True
    assert proposal["model_adapter_kind"] == MODEL_ADAPTER_KIND_FAKE_TEST
    assert proposal["live_model_call_run"] is False
    assert proposal["safe_model_input_packet_ref"]
    assert proposal["model_output_validation_ref"]
    assert proposal["raw_prompt_retained"] is False
    assert proposal["raw_model_response_retained"] is False
    _assert_finding_non_authority(proposal)


def test_default_model_assisted_route_falls_back_to_deterministic_no_model() -> None:
    bundle = _answer_bearing_bundle()

    proposal = build_model_assisted_analyst_finding_proposal(
        triage_packet=bundle["candidate_evidence_triage_packet"],
        analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
    )

    assert proposal["model_assisted_analysis_run"] is False
    assert proposal["model_assisted_analysis_not_run_reason"] == (
        MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE_AND_ADAPTER
    )
    assert proposal["model_role"] == ANALYST_MODEL_ROLE_SMART
    assert proposal["role_surface"] == ANALYST_ROLE_SURFACE
    assert proposal["live_model_call_run"] is False
    assert proposal["model_calls_attempted"] == 0
    assert proposal["model_calls_completed"] == 0
    assert proposal["model_route_diagnostics"][
        "model_assisted_analyst_license_present"
    ] is False
    _assert_finding_non_authority(proposal)


def test_license_alone_does_not_execute_analyst_model() -> None:
    bundle = _answer_bearing_bundle()
    license_ref = build_model_assisted_analyst_license(
        license_id="analyst-license-alone:test",
    )

    proposal = build_model_assisted_analyst_finding_proposal(
        triage_packet=bundle["candidate_evidence_triage_packet"],
        analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
        model_assisted_analyst_license=license_ref,
    )

    assert proposal["model_assisted_analysis_run"] is False
    assert proposal["model_assisted_analysis_not_run_reason"] == (
        MODEL_ASSISTED_NOT_RUN_MISSING_ADAPTER
    )
    assert proposal["model_route_diagnostics"][
        "model_assisted_analyst_license_present"
    ] is True
    assert proposal["model_route_diagnostics"][
        "model_assisted_analyst_adapter_present"
    ] is False
    assert proposal["live_model_call_run"] is False


def test_adapter_alone_does_not_execute_analyst_model() -> None:
    bundle = _answer_bearing_bundle()
    called = False

    def fake_adapter(_input_packet: Mapping[str, Any]) -> Mapping[str, Any]:
        nonlocal called
        called = True
        raise AssertionError("adapter must not be called without license")

    proposal = build_model_assisted_analyst_finding_proposal(
        triage_packet=bundle["candidate_evidence_triage_packet"],
        analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
        model_assisted_analyst_adapter=fake_adapter,
    )

    assert called is False
    assert proposal["model_assisted_analysis_run"] is False
    assert proposal["model_assisted_analysis_not_run_reason"] == (
        MODEL_ASSISTED_NOT_RUN_MISSING_LICENSE
    )
    assert proposal["model_route_diagnostics"][
        "model_assisted_analyst_license_present"
    ] is False
    assert proposal["model_route_diagnostics"][
        "model_assisted_analyst_adapter_present"
    ] is True


def test_licensed_fake_smart_model_path_produces_valid_proposal() -> None:
    bundle = _answer_bearing_bundle()
    deterministic = _finding(bundle)
    captured: dict[str, Any] = {}
    license_ref = build_model_assisted_analyst_license(
        license_id="analyst-fake-smart:test",
    )

    def fake_adapter(input_packet: Mapping[str, Any]) -> Mapping[str, Any]:
        captured.update(input_packet)
        assert input_packet["model_role"] == ANALYST_MODEL_ROLE_SMART
        assert input_packet["role_surface"] == ANALYST_ROLE_SURFACE
        assert input_packet["candidate_triage_records"]
        assert "provider_extracted_text" not in json.dumps(input_packet)
        return {"analyst_finding_proposal": deterministic}

    proposal = build_model_assisted_analyst_finding_proposal(
        triage_packet=bundle["candidate_evidence_triage_packet"],
        analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
        model_assisted_analyst_license=license_ref,
        model_assisted_analyst_adapter=fake_adapter,
    )

    assert captured["safe_model_input_packet_digest"]
    assert proposal["model_assisted_analysis_run"] is True
    assert proposal["model_adapter_kind"] == MODEL_ADAPTER_KIND_FAKE_TEST
    assert proposal["model_role"] == ANALYST_MODEL_ROLE_SMART
    assert proposal["role_surface"] == ANALYST_ROLE_SURFACE
    assert proposal["live_model_call_run"] is False
    assert proposal["model_calls_attempted"] == 1
    assert proposal["model_calls_completed"] == 1
    assert proposal["safe_model_input_packet_ref"]
    assert proposal["model_output_validation_ref"]
    assert proposal["dprime_handoff_refs"]["analysis_claim_refs"]
    _assert_finding_non_authority(proposal)


def test_real_smart_model_route_is_gated_without_adapter() -> None:
    bundle = _answer_bearing_bundle()
    real_license = build_model_assisted_analyst_license(
        license_id="analyst-real-smart:test",
        test_only=False,
        adapter_kind=MODEL_ADAPTER_KIND_REAL_SMART,
    )

    proposal = build_model_assisted_analyst_finding_proposal(
        triage_packet=bundle["candidate_evidence_triage_packet"],
        analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
        model_assisted_analyst_license=real_license,
    )

    assert proposal["model_assisted_analysis_run"] is False
    assert proposal["model_assisted_analysis_not_run_reason"] == (
        MODEL_ASSISTED_NOT_RUN_MISSING_ADAPTER
    )
    assert proposal["model_route_diagnostics"]["model_role"] == "smart"
    assert proposal["live_model_call_run"] is False


def test_ungrounded_fake_model_output_is_rejected() -> None:
    bundle = _answer_bearing_bundle()
    ungrounded = json.loads(json.dumps(_finding(bundle)))
    ungrounded["analysis_claims"][0]["supporting_candidate_refs"] = []
    ungrounded["analysis_claims"][0]["supporting_source_excerpt_refs"] = []
    ungrounded["analysis_claims"][0]["bounded_content_refs"] = []

    def fake_adapter(_input_packet: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"analyst_finding_proposal": ungrounded}

    with pytest.raises(AnalystFindingProposalError):
        build_fake_model_assisted_analyst_finding_proposal(
            triage_packet=bundle["candidate_evidence_triage_packet"],
            analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
            fake_model_adapter=fake_adapter,
        )


def test_adjacent_as_answer_model_output_is_rejected() -> None:
    adjacent_bundle = _direct_workbench_bundle(
        SMALL_CLAIMS_QUERY,
        [
            _direct_provider_result(
                "Official Online Discount Context",
                "https://example-county.gov/courts/online-discount",
                "Eligible online filers may pay a reduced small claims fee of $20.",
                rank=1,
                selected=True,
            )
        ],
    )
    answer_bundle = _answer_bearing_bundle()
    invalid = json.loads(json.dumps(_finding(answer_bundle)))
    adjacent_ref = adjacent_bundle["candidate_evidence_triage_packet"][
        "adjacent_context_candidate_refs"
    ][0]
    invalid["selected_answer_bearing_candidate_refs"] = [adjacent_ref]
    invalid["proposed_answer_claim"]["selected_answer_bearing_candidate_refs"] = [
        adjacent_ref
    ]

    def fake_adapter(_input_packet: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"analyst_finding_proposal": invalid}

    with pytest.raises(AnalystFindingProposalError):
        build_model_assisted_analyst_finding_proposal(
            triage_packet=adjacent_bundle["candidate_evidence_triage_packet"],
            analysis_gap_search_proposal=adjacent_bundle[
                "analysis_gap_search_proposal"
            ],
            model_assisted_analyst_license=build_model_assisted_analyst_license(
                license_id="analyst-adjacent-as-answer:test",
            ),
            model_assisted_analyst_adapter=fake_adapter,
        )


def test_model_output_cannot_upgrade_authority() -> None:
    bundle = _answer_bearing_bundle()
    upgraded = json.loads(json.dumps(_finding(bundle)))
    upgraded["evidence_admitted"] = True

    def fake_adapter(_input_packet: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"analyst_finding_proposal": upgraded}

    with pytest.raises(AnalystFindingProposalError):
        build_model_assisted_analyst_finding_proposal(
            triage_packet=bundle["candidate_evidence_triage_packet"],
            analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
            model_assisted_analyst_license=build_model_assisted_analyst_license(
                license_id="analyst-authority-upgrade:test",
            ),
            model_assisted_analyst_adapter=fake_adapter,
        )


def test_safe_model_input_rejects_raw_private_material() -> None:
    bundle = _answer_bearing_bundle()
    safe_packet = build_analyst_finding_safe_model_input_packet(
        triage_packet=bundle["candidate_evidence_triage_packet"],
        analysis_gap_search_proposal=bundle["analysis_gap_search_proposal"],
    )
    unsafe = {**safe_packet, "raw_prompt": "RAW_PROMPT_SENTINEL"}

    with pytest.raises(AnalystFindingProposalError):
        validate_analyst_finding_safe_model_input_packet(unsafe)


def test_analyst_model_route_does_not_use_fast_or_embed_roles() -> None:
    module_text = (ROOT / "core" / "current_source_analyst_finding_proposal.py").read_text(
        encoding="utf-8"
    ).casefold()

    assert "fast_model" not in module_text
    assert "embed_model" not in module_text


def test_analysis_refs_are_forwarded_to_dprime_dossier() -> None:
    bundle = _answer_bearing_bundle()
    dossier = bundle["workbench_dprime_dossier"]
    dossier_ref = bundle["workbench_dprime_dossier_ref"]

    for surface in (dossier, dossier_ref):
        assert surface["analyst_finding_proposal_ref"]
        assert surface["proposed_answer_claim_ref"]
        assert surface["analysis_claim_refs"]
        assert surface["source_support_map_ref"]
        assert surface["caveat_refs"]
        assert surface["adjacent_claim_exclusion_refs"]
        assert surface["unresolved_gap_refs"]
        assert surface["candidate_triage_summary_ref"]
        assert surface["selected_answer_bearing_candidate_refs"]
        assert surface["adjacent_context_candidate_refs"]
        assert surface["excluded_scope_candidate_refs"]
        assert surface["unreadable_high_value_candidate_refs"]


def test_scrutineer_challenge_seed_is_staged_but_not_implemented() -> None:
    finding = _finding(_answer_bearing_bundle())
    seed = finding["scrutineer_challenge_seed"]
    seed_ref = finding["scrutineer_challenge_seed_ref"]

    assert seed_ref["scrutineer_challenge_seed_digest"]
    assert seed_ref["challenge_target_count"] >= 1
    assert seed["scrutineer_lane_placeholder"] is True
    assert seed["scrutineer_validation_run"] is False
    assert seed["scrutineer_admission_created"] is False
    _assert_finding_non_authority(finding)


def _answer_bearing_bundle() -> dict[str, Any]:
    return _direct_workbench_bundle(
        SMALL_CLAIMS_QUERY,
        [
            _direct_provider_result(
                "Official Reduced Fee And Waiver Context",
                "https://example-county.gov/courts/reduced-fee-waiver",
                "Fee waiver eligibility depends on income and is not the standard fee.",
                rank=1,
            ),
            _direct_provider_result(
                "Official Current Standard Filing Fee",
                "https://example-county.gov/courts/current-filing-fee",
                "The current standard paper small claims filing fee is $54.",
                rank=2,
                selected=True,
            ),
            _direct_provider_result(
                "Official Fee Schedule PDF",
                "https://example-county.gov/courts/fee-schedule.pdf",
                None,
                rank=3,
                official_artifact=True,
                unreadable=True,
            ),
        ],
    )


def _direct_workbench_bundle(
    query: str,
    provider_results: list[dict[str, Any]],
) -> dict[str, Any]:
    plan = build_generic_query_relation_plan(query)
    diagnostics = [
        _direct_candidate_diagnostic(result, index=index)
        for index, result in enumerate(provider_results, 1)
    ]
    return build_current_source_record_analyst_workbench(
        relation_plan=plan,
        acquisition_plan={
            "acquisition_query": query,
            "expected_value_token_kinds": plan.get("expected_value_token_kinds", []),
        },
        candidate_diagnostics=diagnostics,
        answer_bearing_candidate_window_diagnostics=diagnostics,
        provider_results=provider_results,
        fetch_read_content_packet={"packet_digest": "direct-fixture-fetch-packet"},
        entrypoint_kind="offline_direct_workbench_fixture",
    )


def _direct_provider_result(
    title: str,
    url: str,
    extracted_text: str | None,
    *,
    rank: int,
    selected: bool = False,
    official_artifact: bool = False,
    unreadable: bool = False,
) -> dict[str, Any]:
    result = {
        "title": title,
        "url": url,
        "link": url,
        "rank": rank,
        "provider_rank": rank,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    if extracted_text is not None:
        result["provider_extracted_text"] = extracted_text
        result["provider_extracted_text_digest"] = f"extracted-digest-{rank}"
        result["provider_extracted_text_char_count"] = len(extracted_text)
    result["_direct_selected"] = selected
    result["_direct_official_artifact"] = official_artifact
    result["_direct_unreadable"] = unreadable
    return result


def _direct_candidate_diagnostic(
    provider_result: Mapping[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    text = str(provider_result.get("provider_extracted_text") or "")
    has_currency = "$" in text
    official_artifact = provider_result.get("_direct_official_artifact") is True
    unreadable = provider_result.get("_direct_unreadable") is True
    selected = provider_result.get("_direct_selected") is True
    candidate_id = f"direct-candidate-{index}"
    read_support_status = None
    if official_artifact and unreadable:
        read_support_status = dogfood.OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_UNREADABLE
    elif official_artifact:
        read_support_status = dogfood.OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_READABLE
    return {
        "candidate_id": candidate_id,
        "candidate_digest": f"direct-digest-{index}",
        "title": provider_result["title"],
        "domain": urlparse(str(provider_result["url"])).netloc.lower(),
        "url": provider_result["url"],
        "provider_rank": index,
        "result_rank": index,
        "fetch_read_priority_rank": index,
        "candidate_selection_features": {
            "source_of_record_domain_signal": True,
            "official_domain_signal": True,
            "public_agency_domain_signal": True,
            "derivative_domain_signal": False,
        },
        "official_or_source_record_looking_http_candidate": True,
        "source_survival_candidate_signal": "source_of_record_looking",
        "official_pdf_or_table_artifact_candidate": official_artifact,
        "official_artifact_type": "pdf_artifact" if official_artifact else None,
        "official_artifact_read_support_status": read_support_status,
        "official_artifact_read_support_source": (
            dogfood.OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_FETCH_RUNNER
            if official_artifact
            else None
        ),
        "official_artifact_read_support_raw_content_retained": False,
        "provider_extracted_text_obtained": bool(text),
        "readable_text_obtained": bool(text),
        "answer_bearing_candidate_window_selected": selected,
        "candidate_window_selected": selected,
        "selected_window_digest": f"direct-window-{index}" if text else None,
        "selected_window_char_count": len(text),
        "matched_anchor_count": 1 if text else 0,
        "matched_value_token_kinds": ["currency"] if has_currency else [],
        "matched_value_token_kind_count": 1 if has_currency else 0,
        "raw_private_retention_flags": dict(dogfood.RAW_FALSE_FLAGS),
    }


def _finding(bundle: Mapping[str, Any]) -> Mapping[str, Any]:
    proposals = bundle["analyst_workbench_packet"]["analyst_finding_proposals"]
    assert len(proposals) == 1
    return proposals[0]


def _candidate_ids(refs: Any) -> set[str]:
    return {
        str(_safe_mapping(item).get("candidate_id"))
        for item in refs
        if _safe_mapping(item).get("candidate_id")
    }


def _assert_finding_non_authority(finding: Mapping[str, Any]) -> None:
    sections = [
        finding,
        _safe_mapping(finding.get("proposed_answer_claim")),
        _safe_mapping(finding.get("source_support_map")),
        _safe_mapping(finding.get("scrutineer_challenge_seed")),
    ]
    sections.extend(
        _safe_mapping(item) for item in finding.get("analysis_claims", [])
    )
    for section in sections:
        if not section:
            continue
        assert section["evidence_admitted"] is False
        assert section["source_obligation_satisfied"] is False
        assert section["citation_eligibility_created"] is False
        assert section["final_answer_packet_created"] is False
        assert section["author_output_created"] is False
        assert section["product_correctness_claimed"] is False
        assert section["raw_private_retention_flags"] == dogfood.RAW_FALSE_FLAGS
        for raw_key in dogfood.RAW_FALSE_FLAGS:
            assert section[raw_key] is False


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
