from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_PATH = _ROOT / "tests" / "fixtures" / "legal_current_source_quality_l2b.json"


def _fixture() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _case(case_id: str) -> dict[str, Any]:
    for item in _fixture()["reference_cases"]:
        if item["case_id"] == case_id:
            return item
    raise AssertionError(f"Missing L2B legal/current fixture case: {case_id}")


def test_l2b_fixture_is_diagnostic_only_and_non_runtime() -> None:
    data = _fixture()

    assert data["schema_version"] == "legal_current_source_quality_l2b_fixture_v1"
    assert data["diagnostic_only"] is True
    assert data["runtime_behavior_authorized"] is False


def test_l2b_bottleneck_taxonomy_matches_design_contract() -> None:
    assert _fixture()["bottleneck_taxonomy"] == [
        "source_class_need_not_detected",
        "recovery_not_triggered",
        "no_official_candidates_returned",
        "official_candidates_rejected_or_misclassified",
        "accepted_official_sources_not_visible_in_final_evidence",
        "visible_official_sources_not_cited",
        "source_unavailable_from_current_provider_stack",
        "query_domain_strategy_insufficient",
        "source_specific_official_resolver_api_likely_needed",
        "final_answer_posture_too_confident",
    ]


def test_l2b_currentness_fields_cover_legal_status_dates_and_uncertainty() -> None:
    assert set(_fixture()["currentness_fields"]) == {
        "publication_date",
        "effective_date",
        "application_date",
        "amendment_date",
        "enforcement_date",
        "compliance_deadline",
        "stayed_enjoined_suspended_status",
        "superseded_withdrawn_archived_status",
        "stale_source_warning",
        "jurisdiction_uncertainty",
    }


def test_l2b_cta_fincen_requires_current_official_agency_or_legal_source() -> None:
    case = _case("cta_fincen_boi_current_status")

    assert case["question_type"] == "current_legal_rule"
    assert "official_agency_page" in case["required_source_classes"]
    assert "statutory_or_regulatory_text" in case["required_source_classes"]
    assert "fincen.gov" in case["required_authority_examples"]
    assert "current_status" in case["must_cite_for"]
    assert case["secondary_satisfies_legal_effect"] is False


def test_l2b_osha_heat_requires_official_osha_current_rule_guidance_sources() -> None:
    case = _case("osha_heat_illness_prevention")

    assert case["question_type"] == "agency_guidance_or_enforcement"
    assert {
        "official_agency_page",
        "official_guidance_or_faq",
        "government_register",
        "statutory_or_regulatory_text",
        "regulator_press_release",
    } <= set(case["required_source_classes"])
    assert {
        "osha.gov",
        "federalregister.gov",
        "ecfr.gov",
        "regulations.gov",
    } <= set(case["required_authority_examples"])
    assert "enforcement_posture" in case["must_cite_for"]
    assert case["secondary_satisfies_legal_effect"] is False


def test_l2b_eu_ai_act_requires_official_eu_text_and_blocks_secondary_displacement() -> None:
    case = _case("eu_ai_act_dates_obligations")

    assert "official_eu_legal_text" in case["required_source_classes"]
    assert {"CELEX", "ELI", "OJ"} <= set(case["required_identifiers"])
    assert "eur-lex.europa.eu" in case["required_authority_examples"]
    assert "legal_obligation" in case["must_cite_for"]
    assert case["secondary_satisfies_legal_effect"] is False
    assert case["secondary_can_displace_official_when_official_present"] is False


def test_l2b_ssdi_positive_control_accepts_federal_official_legal_sources() -> None:
    case = _case("ssdi_eligibility_positive_control")

    assert case["official_federal_legal_sources_satisfy"] is True
    assert {"ecfr.gov", "federalregister.gov", "ssa.gov"} <= set(
        case["satisfying_source_examples"]
    )
    assert {
        "official_agency_page",
        "statutory_or_regulatory_text",
        "government_register",
    } <= set(case["required_source_classes"])


def test_l2b_court_status_requires_docket_order_opinion_or_reliable_mirror() -> None:
    case = _case("court_injunction_status")

    assert case["question_type"] == "court_status"
    assert case["required_source_classes"] == ["court_docket_or_order"]
    assert case["allowed_proxy_source_classes"] == ["reliable_docket_mirror"]
    assert {
        "court_order",
        "court_opinion",
        "official_docket",
        "recap_or_courtlistener_mirror",
    } <= set(case["required_authority_examples"])
    assert case["reputable_news_satisfies_status"] is False


def test_l2b_legal_regulatory_event_news_can_report_but_not_set_legal_effect() -> None:
    case = _case("legal_regulatory_current_event")

    assert case["reputable_news_satisfies_what_happened"] is True
    assert case["reputable_news_satisfies_current_legal_effect"] is False
    assert "reputable_news" in case["required_source_classes_for_what_happened"]
    assert "court_docket_or_order" in case["required_source_classes_for_legal_effect"]


def test_l2b_secondary_legal_analysis_is_context_not_current_law() -> None:
    case = _case("secondary_legal_analysis_only")

    assert case["role"] == "interpretation_context_only"
    assert case["satisfies_current_law"] is False
    assert {
        "current_legal_rule",
        "legal_effect",
        "compliance_deadline",
        "court_status",
    } <= set(case["must_not_satisfy"])
