from __future__ import annotations

from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS, RECOVER_WEAK_CORPUS
from core.controller_state_reducer import ControllerEvidenceBoundary
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
    EvidenceIntegrationDecision,
    EvidenceIntegrationExpectedValue,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.source_class_recovery import (
    build_official_source_recovery_domain_constraints,
    build_recovery_source_quality_diagnostics,
    build_source_class_recovery_recommendation,
)
from tests.test_source_class_recovery_trace import _run_case
from tests.test_weak_corpus_recovery import _run as _run_weak_corpus_case

_OFFICIAL_LEGAL_CLASSES = (
    "official_current_rules",
    "legal_or_regulatory_text",
)
_BASE_AUTHORITY_DOMAINS = {
    "federalregister.gov",
    "ecfr.gov",
    "govinfo.gov",
    "regulations.gov",
}
_EU_AUTHORITY_DOMAINS = {"eur-lex.europa.eu"}
_UK_AUTHORITY_DOMAINS = {"legislation.gov.uk"}


def _checkpoint_decision(action_name: str) -> EvidenceIntegrationDecision:
    return EvidenceIntegrationDecision(
        action_name=action_name,
        reason=f"ag22_forced_{action_name}",
        contract_gap_addressed=(
            "official_current_rules"
            if action_name == RECOVER_MISSING_SOURCE_CLASS
            else None
        ),
        expected_value=EvidenceIntegrationExpectedValue.HIGH,
        budget_rationale="ag22 forced checkpoint decision",
        blocked_or_skipped_action_rationale={},
        evidence_boundary=ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY,
    )


def _force_checkpoint_action(
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> None:
    monkeypatch.setattr(
        orchestrator,
        "decide_evidence_integration_checkpoint",
        lambda _snapshot: _checkpoint_decision(action_name),
    )


def _assert_authority_lifecycle_recovery_action(trace: dict[str, Any]) -> None:
    action = trace["authority_lifecycle"]["recovery_action"]
    assert action["action_type"] == RECOVER_MISSING_SOURCE_CLASS
    assert action["approved"] is True


def _target_domains(query: str, *, core_topic: str = "", primary_entity: str = "") -> set[str]:
    return set(
        build_official_source_recovery_domain_constraints(
            missing_expected_source_classes=_OFFICIAL_LEGAL_CLASSES,
            query=query,
            core_topic=core_topic,
            primary_entity=primary_entity,
            recovery_queries=(),
        )
    )


def _recovered(
    url: str,
    *,
    title: str,
    text: str,
    source_tier: str = "official",
) -> dict[str, Any]:
    return {
        "title": title,
        "url": url,
        "text": text,
        "score": 0.1,
        "source_tier": source_tier,
        "_provider_role": "source_class_recovery",
        "retrieval_stage": "source_class_recovery",
    }


def _lifecycle(
    missing: str,
    *,
    quality_status: str = "official_or_primary_found",
) -> dict[str, Any]:
    reason_prefix = {
        "official_current_rules": "answer_contract_official_gap",
        "legal_or_regulatory_text": "answer_contract_legal_text_gap",
        "current_primary_or_official": "answer_contract_current_primary_gap",
    }[missing]
    return {
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_reason": f"{reason_prefix}:{missing}",
        "active_source_class_recovery_skip_reason": None,
        "active_source_class_recovery_blockers": [],
        "active_source_class_recovery_missing_classes": [missing],
        "active_source_class_recovery_attempt_count": 1,
        "recovery_source_quality_status": quality_status,
    }


def test_ag22_dot_official_domain_targets_include_transportation_and_legal_domains() -> None:
    domains = _target_domains(
        (
            "As of today, what are the current U.S. DOT rules for airline "
            "passengers who use wheelchairs under the Air Carrier Access Act?"
        ),
        core_topic="DOT wheelchair airline passenger current rules",
        primary_entity="U.S. Department of Transportation",
    )

    assert _BASE_AUTHORITY_DOMAINS | {"transportation.gov"} <= domains


@pytest.mark.parametrize(
    ("query", "core_topic", "primary_entity", "agency_domain"),
    [
        (
            (
                "What is the current legal status of the FTC noncompete rule, "
                "and what court or agency deadlines matter now?"
            ),
            "FTC noncompete rule current legal status",
            "FTC noncompete rule",
            "ftc.gov",
        ),
        (
            (
                "What is the current FDA enforcement posture for laboratory "
                "developed tests after the LDT final rule?"
            ),
            "FDA LDT final rule enforcement posture",
            "FDA laboratory developed tests",
            "fda.gov",
        ),
    ],
)
def test_ag22_agency_contexts_include_agency_plus_legal_domains(
    query: str,
    core_topic: str,
    primary_entity: str,
    agency_domain: str,
) -> None:
    domains = _target_domains(
        query,
        core_topic=core_topic,
        primary_entity=primary_entity,
    )

    assert _BASE_AUTHORITY_DOMAINS | {agency_domain} <= domains


def test_ag22_eu_legal_context_uses_eurlex_without_us_federal_domains() -> None:
    domains = _target_domains(
        (
            "For the EU AI Act, what legal obligations are already in force, "
            "and what does the current regulation text require?"
        ),
        core_topic="EU AI Act legal obligations regulation text",
        primary_entity="EU AI Act",
    )

    assert _EU_AUTHORITY_DOMAINS <= domains
    assert domains.isdisjoint(_BASE_AUTHORITY_DOMAINS)


def test_ag22_uk_legal_context_uses_legislation_gov_without_us_federal_domains() -> None:
    domains = _target_domains(
        (
            "Under the UK Online Safety Act, what current legal duties and "
            "regulatory requirements apply?"
        ),
        core_topic="UK Online Safety Act legal duties",
        primary_entity="Online Safety Act",
    )

    assert _UK_AUTHORITY_DOMAINS <= domains
    assert domains.isdisjoint(_BASE_AUTHORITY_DOMAINS)


def test_ag22_unrecognized_non_us_legal_context_emits_no_wrong_us_constraints() -> None:
    domains = _target_domains(
        (
            "For Brazil's data protection law, what current legal obligations "
            "and regulatory text should companies read?"
        ),
        core_topic="Brazil data protection law legal obligations",
        primary_entity="Brazil data protection law",
    )

    assert domains == set()


def test_ag22_generic_current_primary_context_emits_no_us_legal_domains() -> None:
    domains = build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=("current_primary_or_official",),
        query=(
            "Find the current primary source for the Acme Cloud release "
            "timeline and product roadmap."
        ),
        core_topic="Acme Cloud release timeline product roadmap",
        primary_entity="Acme Cloud",
    )

    assert domains == []


def test_ag22_negative_controls_do_not_emit_official_domain_constraints() -> None:
    historical = build_source_class_recovery_recommendation(
        query=(
            "Explain the historical background of the current official rule "
            "concept for this program, not the current requirements."
        ),
        current_date="2026-05-22",
        intent="general",
        report_type="general_research",
        query_type="history",
        core_topic="official current rule concept",
        primary_entity="program",
        anchor_packet={
            "source_class_expectation": "official",
            "claim_or_metric_type": "rule",
            "freshness_requirement": "official-current",
        },
        source_tier_counts={"secondary": 2},
        source_domain_counts={"history.example": 2},
        top_source_domains=[{"domain": "history.example", "count": 2}],
        official_evidence_found=False,
    )
    quantitative = build_source_class_recovery_recommendation(
        query=(
            "A snack has 140 calories per 28g, and another has 210 calories "
            "per 55g. Which is more calorie-dense?"
        ),
        current_date="2026-05-22",
        intent="general",
        report_type="quantitative_comparison",
        query_type="comparison",
        core_topic="snack calorie density comparison",
        primary_entity="snack",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"nutrition.example": 2},
        top_source_domains=[{"domain": "nutrition.example", "count": 2}],
        official_evidence_found=False,
    )
    issuer_domains = build_official_source_recovery_domain_constraints(
        missing_expected_source_classes=("issuer_filings_or_company_materials",),
        query="Compare company-reported revenue growth from the latest 10-Q.",
        core_topic="company revenue growth",
        primary_entity="Example Corp",
    )

    assert historical["source_class_recovery_recommended"] is False
    assert "source_class_recovery_official_domains" not in historical
    assert quantitative["source_class_recovery_recommended"] is False
    assert "source_class_recovery_official_domains" not in quantitative
    assert issuer_domains == []


def test_ag22_pipeline_passes_domains_only_to_source_class_recovery(
    tmp_path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query=(
            "As of today, what are the current U.S. DOT rules for airline "
            "passengers who use wheelchairs, including complaint rights and "
            "2026 enforcement milestones?"
        ),
        core_topic="DOT wheelchair airline passenger current rules",
        primary_entity="DOT wheelchair passenger rules",
        researcher_query="DOT wheelchair airline passenger rules news",
        router_intent="regulatory",
        router_query_type="other",
        source_tiers=["secondary", "secondary", "secondary", "secondary"],
        domains=["news.example", "analysis.example"],
        recovery_source_tiers=["official"],
        recovery_domains=["transportation.gov"],
    )

    main_calls = [
        call
        for call in harness.search_calls
        if call["provider_role"] == "main_retrieval"
    ]
    recovery_calls = [
        call
        for call in harness.search_calls
        if call["provider_role"] == "source_class_recovery"
    ]
    assert main_calls
    assert recovery_calls
    assert all(call["include_domains"] == [] for call in main_calls)

    recovery_call = recovery_calls[-1]
    assert _BASE_AUTHORITY_DOMAINS | {"transportation.gov"} <= set(
        recovery_call["include_domains"]
    )
    assert _BASE_AUTHORITY_DOMAINS | {"transportation.gov"} <= set(
        recovery_call["exa_domain_filter"]
    )
    assert recovery_call["search_depth"] == "basic"
    assert recovery_call["search_providers"] == outcome.execution_trace[
        "pass_providers"
    ][-1]


@pytest.mark.parametrize(
    ("source", "expected_class"),
    [
        (
            _recovered(
                "https://www.federalregister.gov/documents/2026/01/01/example",
                title="Federal Register final rule",
                text="The Federal Register publishes final rule regulation text.",
            ),
            "legal_or_regulatory_text",
        ),
        (
            _recovered(
                "https://www.ecfr.gov/current/title-21/part-101",
                title="eCFR current regulation",
                text="The eCFR contains current Code of Federal Regulations text.",
            ),
            "legal_or_regulatory_text",
        ),
        (
            _recovered(
                "https://www.govinfo.gov/content/pkg/USCODE-2024-title42/html/example.htm",
                title="GovInfo statute compilation",
                text="GovInfo provides official statute and regulation source text.",
            ),
            "legal_or_regulatory_text",
        ),
        (
            _recovered(
                "https://www.ftc.gov/legal-library/browse/rules/noncompete-rule",
                title="FTC noncompete rule final rule",
                text="FTC official current rule requirements and enforcement status.",
            ),
            "official_current_rules",
        ),
    ],
)
def test_ag22_quality_gate_accepts_supported_official_sources(
    source: dict[str, Any],
    expected_class: str,
) -> None:
    diagnostics = build_recovery_source_quality_diagnostics([source])

    assert diagnostics["recovery_source_quality_status"] == (
        "official_or_primary_found"
    )
    assert diagnostics["recovered_source_class_counts"][expected_class] == 1
    assert diagnostics["recovered_official_or_primary_count"] == 1


def test_ag22_quality_gate_preserves_secondary_and_mismatch_outcomes() -> None:
    secondary = build_recovery_source_quality_diagnostics(
        [
            _recovered(
                "https://www.apnews.com/article/noncompete-rule",
                title="News report about the FTC noncompete rule",
                text="A secondary article summarizes the official agency rule.",
                source_tier="secondary",
            )
        ]
    )
    mismatch = build_recovery_source_quality_diagnostics(
        [
            _recovered(
                "https://agency.gov/about",
                title="Agency homepage",
                text="Office contact directory and general navigation.",
                source_tier="official",
            )
        ]
    )

    assert secondary["recovery_source_quality_status"] == "secondary_only"
    assert secondary["recovered_official_or_primary_count"] == 0
    assert mismatch["recovery_source_quality_status"] == "classification_mismatch"
    assert mismatch["recovered_official_or_primary_count"] == 0


def test_ag22_recovered_visibility_uses_existing_boundary_for_qualified_sources() -> None:
    recovered = _recovered(
        "https://www.federalregister.gov/documents/2026/01/01/example",
        title="Federal Register final rule",
        text="The Federal Register publishes final rule regulation text.",
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[
            {
                "title": "Secondary analysis",
                "url": "https://analysis.example/item",
                "text": "Secondary discussion.",
                "source_tier": "secondary",
            }
        ],
        recovered_passages=[recovered],
        lifecycle_trace=_lifecycle("legal_or_regulatory_text"),
        max_final_evidence=4,
    )

    assert final[-1]["url"] == recovered["url"]
    assert decision.used is True
    assert decision.reserved_source_count == 1


def test_ag22_recovered_visibility_still_reserves_zero_for_no_relevant_sources() -> None:
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[
            {
                "title": "Secondary analysis",
                "url": "https://analysis.example/item",
                "text": "Secondary discussion.",
                "source_tier": "secondary",
            }
        ],
        recovered_passages=[],
        lifecycle_trace=_lifecycle(
            "legal_or_regulatory_text",
            quality_status="no_relevant_sources",
        ),
        max_final_evidence=4,
    )

    assert len(final) == 1
    assert decision.used is False
    assert decision.reserved_source_count == 0
    assert decision.reason == "no_relevant_sources"


def test_ag22_weak_corpus_checkpoint_preserves_required_official_recovery(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_WEAK_CORPUS)

    generic_outcome, generic_harness = _run_weak_corpus_case(tmp_path)
    official_outcome, official_harness = _run_weak_corpus_case(
        tmp_path,
        query=(
            "What is the current legal status of the FTC noncompete rule, "
            "and what court or agency deadlines matter now?"
        ),
        core_topic="FTC noncompete rule current legal status",
        primary_entity="FTC noncompete rule",
        researcher_query="current legal status court deadlines",
    )

    assert generic_outcome.execution_trace["weak_corpus_recovery_used"] is True
    assert generic_outcome.execution_trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
        "promoted_action_name"
    ] == RECOVER_WEAK_CORPUS
    assert generic_outcome.execution_trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
        "executed_action_name"
    ] == RECOVER_WEAK_CORPUS
    assert all(
        detail["provider_role"] != "source_class_recovery"
        for detail in generic_harness.search_call_details
    )
    assert official_outcome.execution_trace["weak_corpus_recovery_used"] is True
    _assert_authority_lifecycle_recovery_action(official_outcome.execution_trace)
    official_provider_roles = [
        detail["provider_role"] for detail in official_harness.search_call_details
    ]
    assert "weak_corpus_recovery" in official_provider_roles
    assert "source_class_recovery" in official_provider_roles


def test_ag22_source_class_checkpoint_skips_weak_and_preserves_official_lane(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_checkpoint_action(monkeypatch, RECOVER_MISSING_SOURCE_CLASS)

    official_outcome, official_harness = _run_weak_corpus_case(
        tmp_path,
        query=(
            "What is the current legal status of the FTC noncompete rule, "
            "and what court or agency deadlines matter now?"
        ),
        core_topic="FTC noncompete rule current legal status",
        primary_entity="FTC noncompete rule",
        researcher_query="current legal status court deadlines",
    )

    trace = official_outcome.execution_trace

    assert trace["weak_corpus_recovery_used"] is False
    assert trace["weak_corpus_recovery_skip_reason"] == (
        "checkpoint_action_not_approved"
    )
    _assert_authority_lifecycle_recovery_action(trace)
    assert trace["authority_lifecycle"]["execution_state"]["state"] == "attempted"
    assert official_harness.search_call_details[-1]["provider_role"] == (
        "source_class_recovery"
    )


def test_ag22_domain_constraints_do_not_leak_into_author_prompt(tmp_path) -> None:
    _outcome, harness, _log_entry = _run_case(
        tmp_path,
        query=(
            "What is the current legal status of the FTC noncompete rule, "
            "and what court or agency deadlines matter now?"
        ),
        core_topic="FTC noncompete rule current legal status",
        primary_entity="FTC noncompete rule",
        researcher_query="FTC noncompete rule secondary analysis",
        router_intent="regulatory",
        router_query_type="other",
        source_tiers=["secondary", "secondary", "secondary"],
        domains=["analysis.example", "news.example"],
        recovery_source_tiers=["official"],
        recovery_domains=["ftc.gov"],
    )

    assert harness.author_prompts
    prompt = harness.author_prompts[-1]
    assert "source_class_recovery_official_domains" not in prompt
    assert "official_domain_constraints" not in prompt
    assert "controller_diagnostics" not in prompt
