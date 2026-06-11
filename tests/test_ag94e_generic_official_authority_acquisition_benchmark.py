from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.evidence_ledger import EvidenceLedger, SourceRequirementStatus
from core.official_canonical_recovery_candidate_acquisition import (
    build_official_canonical_recovery_candidate_acquisition_trace,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.provider_result_represented_visibility import (
    PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY,
    build_provider_result_represented_visibility_projection,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.source_class_recovery import build_source_class_recovery_recommendation

_ROOT = Path(__file__).resolve().parents[1]
_THIS_FILE = Path(__file__)

_OFFICIAL_CURRENT = "official_current_rules"
_LEGAL_PRIMARY = "legal_or_regulatory_text"
_CANONICAL_PRIMARY = "primary_source_documents"
_ISSUER_PRIMARY = "issuer_filings_or_company_materials"
_NONE = "none"

AG94E_BEHAVIOR_CHANGE_PROOF_FAMILIES: tuple[str, ...] = (
    "food_product_safety_regulation",
    "legal_regulatory_primary",
    "official_product_status",
    "current_government_rule",
    "canonical_technical_docs",
)


@dataclass(frozen=True)
class AuthorityFamily:
    family_id: str
    label: str
    source_obligation_expected: str
    satisfying_evidence: str
    lower_tier_role: str
    must_not_satisfy: str
    acquisition_posture: str
    insufficiency_posture: str


@dataclass(frozen=True)
class BenchmarkFixture:
    fixture_id: str
    user_query: str
    authority_family: str
    expected_source_obligation: str
    provider_results: tuple[dict[str, Any], ...]
    expected_lower_tier_role: str
    expected_official_candidate_outcome: str
    expected_failure_layer: str
    expected_final_sufficiency_posture: str
    expected_recognized_by_current_code: bool
    regression_only: bool = False
    non_us_non_transport: bool = False


AUTHORITY_FAMILIES: dict[str, AuthorityFamily] = {
    "current_government_rule": AuthorityFamily(
        family_id="current_government_rule",
        label="current government rule / eligibility / official guidance",
        source_obligation_expected=_OFFICIAL_CURRENT,
        satisfying_evidence=(
            "current official guidance, rule text, notice, or agency-primary "
            "eligibility/access material"
        ),
        lower_tier_role="lead/context only",
        must_not_satisfy="news, explainers, community posts, stale archives",
        acquisition_posture="seek current official or agency-primary authority",
        insufficiency_posture="answer must say official current authority is missing",
    ),
    "food_product_safety_regulation": AuthorityFamily(
        family_id="food_product_safety_regulation",
        label="food or product safety regulation / approved list",
        source_obligation_expected=_LEGAL_PRIMARY,
        satisfying_evidence=(
            "current regulator-primary rule text, approved list, legal act, "
            "official guidance, or canonical register entry"
        ),
        lower_tier_role="lead/context only",
        must_not_satisfy="manufacturer summaries, trade press, news, blogs",
        acquisition_posture="seek regulator/legal-primary current authority",
        insufficiency_posture="answer must not treat secondary approved-list claims as enough",
    ),
    "tax_numeric_rate": AuthorityFamily(
        family_id="tax_numeric_rate",
        label="tax / official numeric rate / official threshold",
        source_obligation_expected=_OFFICIAL_CURRENT,
        satisfying_evidence=(
            "issuer-primary tax authority notice, revenue procedure, official "
            "table, form instruction, or current agency page"
        ),
        lower_tier_role="lead/context only",
        must_not_satisfy="tax blogs, news summaries, calculators, forum posts",
        acquisition_posture="seek official source-bound numeric authority",
        insufficiency_posture="numeric value remains insufficient without official authority",
    ),
    "canonical_technical_docs": AuthorityFamily(
        family_id="canonical_technical_docs",
        label="canonical technical documentation / package behavior",
        source_obligation_expected=_CANONICAL_PRIMARY,
        satisfying_evidence=(
            "canonical project docs, reference manual, release docs, or "
            "maintainer-primary documentation"
        ),
        lower_tier_role="lead/context only",
        must_not_satisfy="Q&A pages, blogs, academic papers, tutorials",
        acquisition_posture="seek canonical docs/reference source",
        insufficiency_posture="explain that canonical documentation was not acquired",
    ),
    "legal_regulatory_primary": AuthorityFamily(
        family_id="legal_regulatory_primary",
        label="legal or regulatory primary/current rule",
        source_obligation_expected=_LEGAL_PRIMARY,
        satisfying_evidence=(
            "primary legal text, regulator rule text, official register, code, "
            "or court/regulator-primary current status"
        ),
        lower_tier_role="lead/context only",
        must_not_satisfy="law firm alerts, news, explainers, summaries",
        acquisition_posture="seek legal/regulatory primary authority",
        insufficiency_posture="answer must caveat missing primary legal authority",
    ),
    "official_product_status": AuthorityFamily(
        family_id="official_product_status",
        label="official product status / release / changelog",
        source_obligation_expected=_CANONICAL_PRIMARY,
        satisfying_evidence=(
            "official release notes, changelog, status page, support matrix, "
            "or maintainer-primary announcement"
        ),
        lower_tier_role="lead/context only",
        must_not_satisfy="news, forum posts, package mirrors, third-party trackers",
        acquisition_posture="seek official product-primary status source",
        insufficiency_posture="answer must say official product status was not acquired",
    ),
    "issuer_filing_primary": AuthorityFamily(
        family_id="issuer_filing_primary",
        label="issuer / filing / primary corporate disclosure",
        source_obligation_expected=_ISSUER_PRIMARY,
        satisfying_evidence=(
            "issuer filing, earnings release, investor presentation, annual or "
            "quarterly report, or company-primary disclosure"
        ),
        lower_tier_role="lead/context only",
        must_not_satisfy="analyst articles, finance news, quote pages, social posts",
        acquisition_posture="seek issuer-primary disclosure",
        insufficiency_posture="company-reported value remains insufficient without issuer-primary evidence",
    ),
    "ordinary_explainer": AuthorityFamily(
        family_id="ordinary_explainer",
        label="ordinary explainer control",
        source_obligation_expected=_NONE,
        satisfying_evidence="ordinary reputable context can be sufficient",
        lower_tier_role="ordinary evidence, not merely a lead",
        must_not_satisfy="not applicable unless the user asks for official/current/primary authority",
        acquisition_posture="do not over-require official sources",
        insufficiency_posture="no official-source insufficiency should be introduced",
    ),
}


def _source(
    *,
    source_id: str,
    title: str,
    url: str,
    text: str = "Fixture source text.",
    source_tier: str = "secondary",
    source_class: str = "secondary_only",
    currentness_signal: str = "current",
    readable_text_available: bool | None = True,
    readability_status: str = "readable",
) -> dict[str, Any]:
    return {
        "candidate_id": source_id,
        "source_id": source_id,
        "title": title,
        "url": url,
        "text": text,
        "source_tier": source_tier,
        "source_class": source_class,
        "currentness_signal": currentness_signal,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "provider_name": "ag94e_fixture_provider",
        "readable_text_available": readable_text_available,
        "readability_status": readability_status,
    }


def _secondary_source(source_id: str = "secondary-context") -> dict[str, Any]:
    return _source(
        source_id=source_id,
        title="Secondary explainer",
        url=f"https://analysis.example/{source_id}",
        text="Secondary context that may point toward an authority source.",
        source_tier="secondary",
        source_class="secondary_only",
    )


def _benchmark_fixtures() -> tuple[BenchmarkFixture, ...]:
    return (
        BenchmarkFixture(
            fixture_id="real_id_airport_id_regression_only",
            user_query=(
                "Do people need REAL ID or other acceptable identification for "
                "domestic flights now, and when did enforcement start?"
            ),
            authority_family="current_government_rule",
            expected_source_obligation=_OFFICIAL_CURRENT,
            provider_results=(
                _secondary_source("airport-news-lead"),
                _source(
                    source_id="official-airport-id-guidance",
                    title="Official accepted identification guidance",
                    url="https://official-transport.example/accepted-id-guidance",
                    text=(
                        "Official current guidance lists accepted identification "
                        "documents and enforcement timing."
                    ),
                    source_tier="official",
                    source_class=_OFFICIAL_CURRENT,
                ),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="accepted_final_authority",
            expected_failure_layer="official_source_acquisition_quality_satisfied",
            expected_final_sufficiency_posture="sufficient_with_official_authority",
            expected_recognized_by_current_code=True,
            regression_only=True,
        ),
        BenchmarkFixture(
            fixture_id="danish_baby_formula_additive_approved_list",
            user_query=(
                "What official legal or regulatory text currently lists approved "
                "preservatives and additives in Danish baby formula?"
            ),
            authority_family="food_product_safety_regulation",
            expected_source_obligation=_LEGAL_PRIMARY,
            provider_results=(
                _secondary_source("food-trade-press-lead"),
                _secondary_source("manufacturer-summary-lead"),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="provider_or_query_miss",
            expected_failure_layer=(
                "provider_or_query_failed_to_return_official_candidate"
            ),
            expected_final_sufficiency_posture="insufficient_official_authority_missing",
            expected_recognized_by_current_code=True,
            non_us_non_transport=True,
        ),
        BenchmarkFixture(
            fixture_id="current_legal_rule_primary_not_recognized",
            user_query=(
                "What does the current statute or regulation require for a "
                "landlord to return a security deposit?"
            ),
            authority_family="legal_regulatory_primary",
            expected_source_obligation=_LEGAL_PRIMARY,
            provider_results=(
                _secondary_source("legal-explainer-lead"),
                _secondary_source("law-firm-alert-lead"),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="provider_or_query_miss",
            expected_failure_layer=(
                "provider_or_query_failed_to_return_official_candidate"
            ),
            expected_final_sufficiency_posture="insufficient_official_authority_missing",
            expected_recognized_by_current_code=True,
        ),
        BenchmarkFixture(
            fixture_id="official_tax_numeric_rate_unreadable",
            user_query="What is the official 2026 tax mileage reimbursement rate and threshold?",
            authority_family="tax_numeric_rate",
            expected_source_obligation=_OFFICIAL_CURRENT,
            provider_results=(
                _secondary_source("tax-blog-lead"),
                _source(
                    source_id="official-tax-rate-unreadable",
                    title="Official 2026 rate notice",
                    url="https://tax-authority.example/2026-rate-notice",
                    text="",
                    source_tier="official",
                    source_class=_OFFICIAL_CURRENT,
                    readable_text_available=False,
                    readability_status="readability_failed",
                ),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="readability_failed",
            expected_failure_layer="official_candidate_readability_or_passport_failed",
            expected_final_sufficiency_posture="insufficient_official_authority_missing",
            expected_recognized_by_current_code=True,
        ),
        BenchmarkFixture(
            fixture_id="canonical_package_behavior_docs",
            user_query=(
                "According to canonical technical documentation, how does the "
                "package cache invalidation option behave?"
            ),
            authority_family="canonical_technical_docs",
            expected_source_obligation=_CANONICAL_PRIMARY,
            provider_results=(
                _secondary_source("package-tutorial-lead"),
                _source(
                    source_id="canonical-package-docs",
                    title="Package reference documentation",
                    url="https://docs.example/package/cache-invalidation",
                    text="Canonical reference documentation for the cache option.",
                    source_tier="canonical",
                    source_class=_CANONICAL_PRIMARY,
                ),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="accepted_final_authority",
            expected_failure_layer="official_source_acquisition_quality_satisfied",
            expected_final_sufficiency_posture="sufficient_with_canonical_docs",
            expected_recognized_by_current_code=True,
        ),
        BenchmarkFixture(
            fixture_id="canonical_docs_provider_forwarding_drop",
            user_query=(
                "According to canonical technical documentation, which package "
                "API option controls cache expiry?"
            ),
            authority_family="canonical_technical_docs",
            expected_source_obligation=_CANONICAL_PRIMARY,
            provider_results=(
                _secondary_source("package-blog-lead"),
                _source(
                    source_id="canonical-doc-result-unrepresented",
                    title="Canonical package API documentation",
                    url="https://docs.example/package/cache-expiry-option",
                    text="Canonical technical documentation for cache expiry.",
                    source_tier="canonical",
                    source_class=_CANONICAL_PRIMARY,
                ),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="provider_forwarding_drop",
            expected_failure_layer=(
                "provider_result_forwarding_or_filtering_dropped_official_candidate"
            ),
            expected_final_sufficiency_posture="insufficient_official_authority_missing",
            expected_recognized_by_current_code=True,
        ),
        BenchmarkFixture(
            fixture_id="canonical_docs_source_fit_rejects_wrong_primary_kind",
            user_query=(
                "According to canonical technical documentation, which package "
                "API option controls retry behavior?"
            ),
            authority_family="canonical_technical_docs",
            expected_source_obligation=_CANONICAL_PRIMARY,
            provider_results=(
                _source(
                    source_id="official-guidance-not-canonical-docs",
                    title="Official current guidance summary",
                    url="https://official-guidance.example/retry-option-summary",
                    text="Official current agency guidance summary only.",
                    source_tier="official",
                    source_class=_OFFICIAL_CURRENT,
                ),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="source_fit_rejected",
            expected_failure_layer="candidate_source_fit_rejected_official_candidate",
            expected_final_sufficiency_posture="insufficient_official_authority_missing",
            expected_recognized_by_current_code=True,
        ),
        BenchmarkFixture(
            fixture_id="official_product_release_status",
            user_query=(
                "What official product release note or changelog says whether "
                "version 4.2.1 is still supported?"
            ),
            authority_family="official_product_status",
            expected_source_obligation=_CANONICAL_PRIMARY,
            provider_results=(
                _secondary_source("release-news-lead"),
                _source(
                    source_id="official-release-note",
                    title="Official release note for version 4.2.1",
                    url="https://product.example/releases/4.2.1",
                    text="Official release notes and supported-version status.",
                    source_tier="canonical",
                    source_class=_CANONICAL_PRIMARY,
                ),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="accepted_final_authority",
            expected_failure_layer="official_source_acquisition_quality_satisfied",
            expected_final_sufficiency_posture="sufficient_with_official_product_primary",
            expected_recognized_by_current_code=True,
        ),
        BenchmarkFixture(
            fixture_id="issuer_quarterly_primary_disclosure",
            user_query=(
                "Use issuer filings or company primary disclosures for the "
                "latest quarterly revenue figure."
            ),
            authority_family="issuer_filing_primary",
            expected_source_obligation=_ISSUER_PRIMARY,
            provider_results=(
                _secondary_source("finance-news-lead"),
                _source(
                    source_id="issuer-quarterly-release",
                    title="Issuer quarterly results release",
                    url="https://issuer.example/investors/quarterly-results",
                    text="Issuer-primary quarterly results and revenue figure.",
                    source_tier="primary",
                    source_class=_ISSUER_PRIMARY,
                ),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="ledger_satisfied",
            expected_failure_layer="I:issuer_primary_outside_official_canonical_export",
            expected_final_sufficiency_posture="sufficient_with_issuer_primary",
            expected_recognized_by_current_code=True,
        ),
        BenchmarkFixture(
            fixture_id="canonical_docs_accepted_then_final_projection_lost",
            user_query=(
                "According to canonical technical documentation, how does the "
                "package retry behavior option work?"
            ),
            authority_family="canonical_technical_docs",
            expected_source_obligation=_CANONICAL_PRIMARY,
            provider_results=(
                _source(
                    source_id="canonical-docs-lost-after-fit",
                    title="Canonical retry option documentation",
                    url="https://docs.example/package/retry-option",
                    text="Canonical documentation for the retry option.",
                    source_tier="canonical",
                    source_class=_CANONICAL_PRIMARY,
                ),
            ),
            expected_lower_tier_role="lead/context only",
            expected_official_candidate_outcome="accepted_but_final_missing",
            expected_failure_layer="accepted_official_candidate_lost_after_acquisition",
            expected_final_sufficiency_posture="insufficient_final_authority_projection_missing",
            expected_recognized_by_current_code=True,
        ),
        BenchmarkFixture(
            fixture_id="ordinary_coffee_explainer_control",
            user_query="Explain why coffee tastes bitter in simple terms.",
            authority_family="ordinary_explainer",
            expected_source_obligation=_NONE,
            provider_results=(_secondary_source("ordinary-science-explainer"),),
            expected_lower_tier_role="ordinary evidence",
            expected_official_candidate_outcome="not_required",
            expected_failure_layer="H-control:no_official_overrequirement",
            expected_final_sufficiency_posture="ordinary_answer_allowed",
            expected_recognized_by_current_code=True,
        ),
    )


def _recommendation_for(fixture: BenchmarkFixture) -> dict[str, Any]:
    return build_source_class_recovery_recommendation(
        query=fixture.user_query,
        current_date="2026-06-11",
        intent="general",
        report_type=(
            "quantitative_comparison"
            if fixture.authority_family == "issuer_filing_primary"
            else "general_research"
        ),
        query_type=(
            "company_metric"
            if fixture.authority_family == "issuer_filing_primary"
            else "other"
        ),
        core_topic=fixture.user_query,
        primary_entity=(
            "ExampleIssuer"
            if fixture.authority_family == "issuer_filing_primary"
            else fixture.user_query
        ),
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"analysis.example": 2},
        top_source_domains=[{"domain": "analysis.example", "count": 2}],
        official_evidence_found=False,
    )


def _authority_trace(
    *,
    source_class: str,
    result_count: int,
    accepted_url_count: int,
) -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id=source_class,
        required_authority=source_class,
        claim_type="official_authority",
        required_recovery=True,
        recovery_queries=(f"official authority source for {source_class}",),
        required_source_classes=(source_class,),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace.update(
        {
            "official_canonical_recovery_execution_admission_trace": {
                "OfficialCanonicalRecoveryExecutionAdmission": {
                    "admission_considered": True,
                    "admission_eligible": True,
                    "admission_used": True,
                    "admission_skip_reason": None,
                    "admission_blockers": [],
                    "recovery_query_count": 1,
                    "recovery_query_previews": [
                        f"official authority source for {source_class}"
                    ],
                }
            },
            "required_source_class": source_class,
            "source_obligation_status": "official_current_required_unmet",
            "active_source_class_recovery_eligible": True,
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_reason": (
                f"official_canonical_recovery_query_acquisition:{source_class}"
            ),
            "active_source_class_recovery_skip_reason": None,
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_missing_classes": [source_class],
            "active_source_class_recovery_queries": [
                f"official authority source for {source_class}"
            ],
            "active_source_class_recovery_result_count": result_count,
            "recovered_accepted_url_count": accepted_url_count,
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": [source_class],
                "allowed_action": True,
            },
        }
    )
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=result_count,
        recovered_result_count=result_count,
        accepted_url_count=accepted_url_count,
    )
    trace.update(
        build_official_canonical_recovery_candidate_acquisition_trace(
            lifecycle_trace=trace,
            provider_diagnostics=[
                {
                    "provider": "ag94e_fixture_provider",
                    "provider_role": "source_class_recovery",
                    "success": True,
                    "result_count": result_count,
                    "accepted_url_count": accepted_url_count,
                    "new_source_count": accepted_url_count,
                }
            ],
        )
    )
    return trace


def _attach_provider_bridge(
    trace: dict[str, Any],
    provider_results: tuple[dict[str, Any], ...],
) -> None:
    records = []
    for source in provider_results:
        record = {
            "provider_name": source.get("provider_name"),
            "provider_role": "source_class_recovery",
            "source_url": source.get("url"),
            "title": source.get("title"),
            "source_tier": source.get("source_tier"),
            "source_class": source.get("source_class"),
        }
        if source.get("candidate_id") == "canonical-doc-result-unrepresented":
            record["non_representation_reason"] = (
                "filtered_before_candidate_acquisition"
            )
        records.append(record)
    trace[PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY] = {
        "ProviderResultRepresentedCandidateBridge": (
            build_provider_result_represented_visibility_projection(
                runtime_trace=trace,
                provider_results=records,
            )
        )
    }


def _export_for_fixture(fixture: BenchmarkFixture) -> dict[str, Any]:
    result_count = len(fixture.provider_results)
    official_candidates = [
        source
        for source in fixture.provider_results
        if source.get("source_class") == fixture.expected_source_obligation
        or source.get("source_tier") in {"official", "primary", "canonical"}
    ]
    trace = _authority_trace(
        source_class=fixture.expected_source_obligation,
        result_count=result_count,
        accepted_url_count=result_count,
    )

    if fixture.expected_official_candidate_outcome == "provider_forwarding_drop":
        trace["candidate_official_or_canonical_count"] = 0
        _attach_provider_bridge(trace, fixture.provider_results)
        return build_official_canonical_recovery_visibility_export(trace)

    if fixture.expected_official_candidate_outcome == "accepted_but_final_missing":
        trace.update(
            {
                "recovered_source_class_counts": {
                    fixture.expected_source_obligation: 1
                },
                "recovered_visibility_source_fit_status": "matched_selected",
                "recovered_visibility_source_fit_candidate_count": 1,
                "recovered_visibility_source_fit_selected_count": 1,
                "recovered_visibility_accepted_readable_authority_evidence_count": 1,
                "recovered_visibility_source_fit_rejection_reasons": [],
                "source_survival_final_evidence_official_or_canonical_count": 0,
            }
        )
        return build_official_canonical_recovery_visibility_export(trace)

    if not official_candidates:
        trace.update(
            {
                "recovered_source_tier_counts": {"secondary": result_count},
                "recovered_source_class_counts": {},
            }
        )
        return build_official_canonical_recovery_visibility_export(trace)

    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_secondary_source("visible-secondary-context")],
        recovered_passages=official_candidates,
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())
    if decision.source_fit_status == "matched_selected" and final:
        trace["source_survival_final_evidence_official_or_canonical_count"] = 1
    else:
        trace["source_survival_final_evidence_official_or_canonical_count"] = 0
    return build_official_canonical_recovery_visibility_export(trace)


def _requirement_for(source_class: str) -> dict[str, Any]:
    requirement_kind_by_class = {
        _OFFICIAL_CURRENT: "official_current",
        _LEGAL_PRIMARY: "legal",
        _CANONICAL_PRIMARY: "canonical",
        _ISSUER_PRIMARY: "official",
    }
    required_tier_by_class = {
        _OFFICIAL_CURRENT: "official",
        _LEGAL_PRIMARY: "",
        _CANONICAL_PRIMARY: "",
        _ISSUER_PRIMARY: "primary",
    }
    return {
        "requirement_id": f"ag94e:{source_class}",
        "requirement_kind": requirement_kind_by_class.get(
            source_class,
            "official",
        ),
        "origin_ref": "ag94e_benchmark",
        "required_source_class": source_class,
        "required_source_tier": required_tier_by_class.get(source_class, ""),
        "required_currentness": (
            "current" if source_class == _OFFICIAL_CURRENT else ""
        ),
    }


def _ledger_projection(
    *,
    source_class: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    ledger = EvidenceLedger()
    candidate = {
        **candidate,
        "candidate_id": candidate.get("candidate_id") or "ag94e-candidate",
        "disposition": "accepted",
        "record_kind": "fact",
        "requirement_id": f"ag94e:{source_class}",
        "eligible_for_stronger_obligation": True,
        "final_evidence_eligible": True,
    }
    ledger.reduce_observation(
        {
            "observation_id": f"ag94e-ledger-{source_class}",
            "observation_source": "retrieval_observation",
            "requirements": [_requirement_for(source_class)],
            "candidates": [candidate],
        }
    )
    return ledger.to_projection().to_dict()


def _ledger_requirement(projection: dict[str, Any], source_class: str) -> dict[str, Any]:
    requirement_id = f"ag94e:{source_class}"
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement
    raise AssertionError(f"missing requirement {requirement_id}")


def test_ag94e_authority_family_taxonomy_is_role_based_not_domain_registry() -> None:
    assert len(AUTHORITY_FAMILIES) == 8
    for family in AUTHORITY_FAMILIES.values():
        combined = " ".join(
            (
                family.source_obligation_expected,
                family.satisfying_evidence,
                family.lower_tier_role,
                family.must_not_satisfy,
                family.acquisition_posture,
                family.insufficiency_posture,
            )
        ).casefold()
        assert ".gov" not in combined
        assert "correct domain" not in combined
        assert "lead/context" in family.lower_tier_role or family.family_id == (
            "ordinary_explainer"
        )


def test_ag94e_benchmark_matrix_has_required_family_coverage_and_overfit_guards() -> None:
    fixtures = _benchmark_fixtures()
    fixture_families = {fixture.authority_family for fixture in fixtures}

    assert len(fixtures) >= 8
    assert len(fixture_families) >= 6
    assert "canonical_technical_docs" in fixture_families
    assert "ordinary_explainer" in fixture_families
    assert any(fixture.non_us_non_transport for fixture in fixtures)
    assert sum(1 for fixture in fixtures if fixture.authority_family == "tax_numeric_rate") >= 1
    assert sum(1 for fixture in fixtures if fixture.authority_family != "tax_numeric_rate") >= 7

    transport_regressions = [
        fixture
        for fixture in fixtures
        if any(
            marker in fixture.user_query.casefold()
            for marker in ("real id", "airport", "domestic flight")
        )
    ]
    assert len(transport_regressions) <= 1
    assert all(fixture.regression_only for fixture in transport_regressions)

    if AG94E_BEHAVIOR_CHANGE_PROOF_FAMILIES:
        changed = set(AG94E_BEHAVIOR_CHANGE_PROOF_FAMILIES)
        assert len(changed) >= 4
        assert "food_product_safety_regulation" in changed
        assert "current_government_rule" in changed
        assert "tax_numeric_rate" not in changed or len(changed) > 4


@pytest.mark.parametrize("fixture", _benchmark_fixtures(), ids=lambda item: item.fixture_id)
def test_ag94e_benchmark_classifies_current_generic_acquisition_behavior(
    fixture: BenchmarkFixture,
) -> None:
    family = AUTHORITY_FAMILIES[fixture.authority_family]
    assert family.source_obligation_expected == fixture.expected_source_obligation

    recommendation = _recommendation_for(fixture)
    missing = set(recommendation.get("missing_expected_source_classes") or ())

    if fixture.expected_source_obligation == _NONE:
        assert recommendation["source_class_recovery_recommended"] is False
        assert recommendation["missing_expected_source_classes"] == []
        assert fixture.expected_failure_layer == "H-control:no_official_overrequirement"
        return

    recognized = fixture.expected_source_obligation in missing
    assert recognized is fixture.expected_recognized_by_current_code

    if not recognized:
        assert recommendation["source_class_recovery_recommended"] is False
        assert fixture.expected_failure_layer == "A:source_obligation_not_recognized"
        return

    assert recommendation["source_class_recovery_recommended"] is True
    assert fixture.expected_source_obligation in recommendation[
        "missing_expected_source_classes"
    ]
    assert fixture.expected_lower_tier_role == "lead/context only"

    if fixture.expected_official_candidate_outcome == "ledger_satisfied":
        official_candidate = fixture.provider_results[-1]
        projection = _ledger_projection(
            source_class=fixture.expected_source_obligation,
            candidate=official_candidate,
        )
        requirement = _ledger_requirement(
            projection,
            fixture.expected_source_obligation,
        )
        assert requirement["status"] == SourceRequirementStatus.SATISFIED.value
        return

    export = _export_for_fixture(fixture)
    assert export["official_source_acquisition_quality_layer"] == (
        fixture.expected_failure_layer
    )


@pytest.mark.parametrize(
    "source_class",
    [_OFFICIAL_CURRENT, _LEGAL_PRIMARY, _CANONICAL_PRIMARY, _ISSUER_PRIMARY],
)
def test_ag94e_lower_tier_sources_are_leads_not_satisfaction_for_strong_obligations(
    source_class: str,
) -> None:
    projection = _ledger_projection(
        source_class=source_class,
        candidate=_secondary_source(f"lower-tier-{source_class}"),
    )
    requirement = _ledger_requirement(projection, source_class)

    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert requirement["reason"] in {
        "lower_tier_or_contextual_candidate_cannot_satisfy_stronger_obligation",
        "candidate_source_class_does_not_match_requirement",
        "no_linked_candidate_satisfies_requirement",
    }


@pytest.mark.parametrize(
    ("source_class", "candidate"),
    [
        (
            _OFFICIAL_CURRENT,
            _source(
                source_id="official-current-ledger",
                title="Official current guidance",
                url="https://official.example/current-guidance",
                source_tier="official",
                source_class=_OFFICIAL_CURRENT,
            ),
        ),
        (
            _LEGAL_PRIMARY,
            _source(
                source_id="legal-primary-ledger",
                title="Official legal text",
                url="https://legal-authority.example/rule-text",
                source_tier="official",
                source_class=_LEGAL_PRIMARY,
            ),
        ),
        (
            _CANONICAL_PRIMARY,
            _source(
                source_id="canonical-doc-ledger",
                title="Canonical reference documentation",
                url="https://docs.example/reference",
                source_tier="canonical",
                source_class=_CANONICAL_PRIMARY,
            ),
        ),
        (
            _ISSUER_PRIMARY,
            _source(
                source_id="issuer-primary-ledger",
                title="Issuer quarterly release",
                url="https://issuer.example/quarterly-release",
                source_tier="primary",
                source_class=_ISSUER_PRIMARY,
            ),
        ),
    ],
)
def test_ag94e_primary_or_official_candidates_can_satisfy_ledger_obligations(
    source_class: str,
    candidate: dict[str, Any],
) -> None:
    projection = _ledger_projection(source_class=source_class, candidate=candidate)
    requirement = _ledger_requirement(projection, source_class)

    assert projection["owner"] == "RunKernel.EvidenceLedger"
    assert projection["canonical_state"] is True
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value
    assert requirement["linked_candidate_ids"]


def test_ag94e_static_guard_keeps_benchmark_offline_and_non_source_specific() -> None:
    tree = ast.parse(_THIS_FILE.read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "requests",
        "openai",
    }
    forbidden_domains = {
        "".join(parts)
        for parts in (
            ("tsa", ".gov"),
            ("dhs", ".gov"),
            ("irs", ".gov"),
            ("sec", ".gov"),
        )
    }
    fixture_text = " ".join(
        str(value)
        for fixture in _benchmark_fixtures()
        for value in (
            fixture.user_query,
            fixture.fixture_id,
            fixture.provider_results,
        )
    ).casefold()

    assert imported_modules.isdisjoint(forbidden_imports)
    assert not (forbidden_domains & set(fixture_text.split()))
