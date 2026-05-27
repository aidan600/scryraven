from __future__ import annotations

import json

import pytest

from core.answer_contract_controller import (
    AnswerContractFamily,
    AnswerControllerActionName,
    AnswerControllerCaps,
    EvidenceReference,
    EvidenceStateSummary,
    build_answer_contract,
    build_answer_contract_fulfillment,
    build_answer_controller_state,
    decide_answer_controller_action,
    draft_answer_contract_from_router_metadata,
)
from core.canonical_technical_docs_policy import (
    is_canonical_technical_documentation_context,
    is_explicit_academic_literature_request,
)
from core.official_numeric_source_grounding import (
    ANSWER_CAVEATED_MISSING_EVIDENCE,
    CITATION_SOURCE_FIT_LANE,
    OFFICIAL_SOURCE_VISIBLE_NOT_CITED,
    OfficialNumericGroundingDiagnostic,
    classify_official_numeric_grounding,
)
from core.official_source_obligation_bridge import (
    apply_official_source_obligation_bridge,
)
from core.official_source_obligation_candidate_visibility import (
    NOT_REQUIRED,
    OfficialSourceObligationCandidateVisibilityFacts,
)
from core.source_classifier import classify_source


@pytest.mark.parametrize(
    "query",
    [
        "Use official documentation to explain PostgreSQL MVCC behavior.",
        "Use reference docs to explain SQLite WAL mode tradeoffs.",
        "Use Python dataclasses documentation to explain field defaults.",
        "Use MDN Fetch API reference docs to explain credentials behavior.",
        "Use Kubernetes configuration docs to explain pod restart policy.",
    ],
)
def test_ag57a_canonical_technical_docs_outrank_academic_by_default(
    query: str,
) -> None:
    assert is_canonical_technical_documentation_context(
        query,
        required_source_classes=("primary_source_documents",),
    )
    assert not is_explicit_academic_literature_request(query)


@pytest.mark.parametrize(
    "query",
    [
        "Find peer-reviewed papers about PostgreSQL MVCC performance.",
        "Give me an academic literature review on SQLite WAL benchmarks.",
        "Summarize empirical studies comparing browser fetch performance.",
        "Find arXiv papers about Kubernetes scheduler tradeoffs.",
    ],
)
def test_ag57a_explicit_academic_requests_preserve_academic_obligation(
    query: str,
) -> None:
    assert is_explicit_academic_literature_request(query)
    assert not is_canonical_technical_documentation_context(
        query,
        required_source_classes=("primary_source_documents",),
    )


def test_ag57a_secondary_evidence_does_not_satisfy_official_current_numeric_claim() -> None:
    result = apply_official_source_obligation_bridge(
        runtime_trace={
            "query_preview": (
                "What is the current 2026 official eligibility threshold "
                "for a federal benefit?"
            ),
            "query_type": "quantitative_comparison",
            "source_tier_counts": {"secondary": 4},
            "source_class_satisfaction_status": {
                "reputable_secondary": "satisfied_strong",
            },
        },
        recommendation={
            "source_class_recovery_recommended": False,
            "missing_expected_source_classes": [],
        },
    )
    bridge = result.trace["OfficialSourceObligationBridge"]

    assert bridge["bridge_used"] is True
    assert bridge["bridge_required_source_classes"] == ["official_current_rules"]
    assert result.recommendation["missing_expected_source_classes"] == [
        "official_current_rules"
    ]


def test_ag57a_legal_current_contract_requires_primary_or_official_source_class() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "What are the current compliance deadlines under the California "
            "privacy law?"
        ),
        report_type="general_research",
        query_type="legal",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        source_classes_present=("reputable_secondary",),
        source_classes_missing=("legal_or_regulatory_text",),
        approved_targeted_queries=(
            "California privacy law current compliance deadline official text",
        ),
    )
    state = build_answer_controller_state(contract, evidence_state_summary=evidence)
    action = decide_answer_controller_action(state)

    assert contract.family is AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    assert {
        "legal_or_regulatory_text",
        "official_current_rules",
    } <= set(contract.evidence_classes_needed)
    assert action.action_name is AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS
    assert action.stable_reason_code == "missing_required_source_class"


def test_ag57a_ordinary_conceptual_explainer_does_not_force_official_recovery() -> None:
    facts = OfficialSourceObligationCandidateVisibilityFacts.from_runtime_trace(
        {
            "query_preview": "Explain why compound interest matters for beginners.",
            "query_type": "conceptual_explainer",
        }
    )
    contract = draft_answer_contract_from_router_metadata(
        query="Explain why compound interest matters for beginners.",
        report_type="general_research",
        query_type="concept",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        evidence_sufficient=True,
        source_classes_present=("reputable_secondary",),
        fulfilled_obligations=contract.must_satisfy,
    )
    action = decide_answer_controller_action(
        build_answer_controller_state(contract, evidence_state_summary=evidence)
    )

    assert facts.obligation_status == NOT_REQUIRED
    assert facts.required_source_classes == ()
    assert contract.family is AnswerContractFamily.CONCEPTUAL_EXPLAINER
    assert action.action_name is AnswerControllerActionName.STOP_SUFFICIENT


def test_ag57a_weak_corpus_stops_with_insufficient_posture_when_recovery_spent() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.WEAK_EVIDENCE_OR_NO_GOOD_EVIDENCE_ANSWER,
        user_intent_interpretation="User asks whether a thinly sourced claim is true.",
        answer_goal="Assess support for the claim without inventing facts",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        weak_corpus=True,
        weak_corpus_reason="retrieval returned off-topic or low-utility evidence",
    )
    state = build_answer_controller_state(
        contract,
        evidence_state_summary=evidence,
        caps=AnswerControllerCaps(max_iterations=2, max_recovery_attempts=0),
    )
    action = decide_answer_controller_action(state)

    assert action.action_name is AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT
    assert action.stable_reason_code == "weak_corpus_unresolved"
    assert action.next_state_delta["stop_state"]["final_answer_posture"] == (
        contract.answer_posture_if_partial
    )


def test_ag57a_fulfillment_handoff_blocks_citation_laundering_over_secondary_only() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.CURRENT_OFFICIAL_RULES,
        user_intent_interpretation="User asks for current official eligibility rules.",
        answer_goal="Answer current official eligibility rules",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        evidence_sufficient=True,
        source_classes_present=("reputable_secondary",),
        fulfilled_obligations=contract.must_satisfy,
    )
    state = build_answer_controller_state(contract, evidence_state_summary=evidence)
    handoff = build_answer_contract_fulfillment(
        state,
        evidence_used=(
            EvidenceReference(
                reference="secondary-explainer",
                source_class="reputable_secondary",
                summary="A secondary explainer discusses the eligibility rule.",
                supports=("identify the current official rule or policy",),
            ),
        ),
    )
    payload = handoff.to_dict()

    assert payload["final_answer_posture"] == contract.answer_posture_if_partial
    assert "official_current_rules" in payload["unfulfilled_items"]
    assert "identify the current official rule or policy" in payload["partial_items"]
    assert "official/current legal evidence missing or secondary-only" in payload[
        "warnings_to_Analyst_or_Author"
    ]


def test_ag57a_quantitative_numeric_diagnostics_preserve_source_bound_abort_lane() -> None:
    classification = classify_official_numeric_grounding(
        OfficialNumericGroundingDiagnostic(
            question_type="government_program_amount",
            official_source_required=True,
            source_need_detected=True,
            official_source_acquired=False,
            numeric_values_extracted=False,
            numeric_values_source_bound=False,
            caveat_present=True,
        )
    )

    assert classification.bottleneck_class == ANSWER_CAVEATED_MISSING_EVIDENCE
    assert classification.behavior_changed is False


def test_ag57a_author_citation_source_fit_diagnostic_marks_visible_uncited_official_gap() -> None:
    classification = classify_official_numeric_grounding(
        OfficialNumericGroundingDiagnostic(
            question_type="current_status",
            official_source_required=True,
            source_need_detected=True,
            official_source_acquired=True,
            official_source_accepted=True,
            official_source_in_final_evidence=True,
            official_source_cited=False,
        )
    )

    assert classification.bottleneck_class == OFFICIAL_SOURCE_VISIBLE_NOT_CITED
    assert classification.next_recommended_lane == CITATION_SOURCE_FIT_LANE
    assert classification.behavior_changed is False


def test_ag57a_source_classifier_keeps_community_social_and_secondary_directional() -> None:
    assert classify_source("https://github.com/python/cpython/issues/123") == (
        "trusted_community"
    )
    assert classify_source("https://reddit.com/r/python/comments/abc/example") == (
        "social_or_forum"
    )
    assert classify_source("https://apnews.com/article/example") == "secondary"
    assert classify_source("https://www.irs.gov/credits-deductions/example") == (
        "official"
    )


def test_ag57a_public_handoff_does_not_expose_raw_prompts_packets_or_traces() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL,
        user_intent_interpretation="User asks for a numeric comparison.",
        answer_goal="Compare two numeric options",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        partial_obligations=("state assumptions",),
        unfulfilled_obligations=("missing sourced numeric values",),
    )
    handoff = build_answer_contract_fulfillment(
        build_answer_controller_state(contract, evidence_state_summary=evidence),
        evidence_used=(
            EvidenceReference(
                reference="raw prompt and full_trace should be redacted",
                source_class="sourced_numeric_values",
                summary="raw quantitative_packet economist_v1 provider_payload",
            ),
        ),
        warnings_to_Analyst_or_Author=("Do not expose raw_prompt or economist_v1.",),
    )
    payload = json.dumps(handoff.to_dict(), sort_keys=True)

    for marker in (
        "raw prompt",
        "raw_prompt",
        "full_trace",
        "provider_payload",
        "quantitative_packet",
        "economist_v1",
    ):
        assert marker not in payload
        assert marker.casefold() not in payload.casefold()
    assert "[redacted protected material]" in payload


@pytest.mark.xfail(
    strict=True,
    reason=(
        "AG-57A documents the mixed canonical plus academic representation gap; "
        "repair requires a future product/modeling decision."
    ),
)
def test_ag57a_mixed_canonical_and_academic_obligation_needs_multi_source_contract() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "What do the PostgreSQL docs say about MVCC, and what do "
            "peer-reviewed studies show about performance in practice?"
        ),
        report_type="general_research",
        query_type="technical_reference",
    )

    assert "primary_source_documents" in contract.evidence_classes_needed
    assert "academic_literature" in contract.evidence_classes_needed
