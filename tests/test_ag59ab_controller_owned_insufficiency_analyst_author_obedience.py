from __future__ import annotations

import json
from pathlib import Path

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
)
from core.canonical_technical_docs_policy import (
    is_canonical_technical_documentation_context,
    is_explicit_academic_literature_request,
)
from core.prompts import DEFAULT_SYSTEM
from core.source_class_recovery import build_source_class_recovery_recommendation
from tests import test_source_hierarchy_answer_contract_invariants_ag57a as ag57a

_ROOT = Path(__file__).resolve().parents[1]


def test_ag59ab_official_current_unmet_obligation_sets_partial_controller_posture() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.CURRENT_OFFICIAL_RULES,
        user_intent_interpretation="User asks for current official eligibility rules.",
        answer_goal="Answer from current official eligibility rules.",
    )
    handoff = build_answer_contract_fulfillment(
        build_answer_controller_state(
            contract,
            evidence_state_summary=EvidenceStateSummary(
                evidence_available=True,
                evidence_sufficient=True,
                source_classes_present=("reputable_secondary",),
                fulfilled_obligations=contract.must_satisfy,
            ),
        ),
        evidence_used=(
            EvidenceReference(
                reference="secondary-summary",
                source_class="reputable_secondary",
                summary="A secondary explainer discusses eligibility rules.",
                supports=("identify the current official rule or policy",),
            ),
        ),
    )
    payload = handoff.to_dict()

    assert payload["final_answer_posture"] == "answer with official-evidence caveat"
    assert payload["source_obligation_status"] == "partial"
    assert payload["partial_source_classes"] == ["official_current_rules"]
    assert payload["unfulfilled_source_classes"] == ["official_current_rules"]
    assert "official_current_rules" in payload["unfulfilled_items"]
    assert "identify the current official rule or policy" in payload["partial_items"]
    assert "official/current legal evidence missing or secondary-only" in payload[
        "warnings_to_Analyst_or_Author"
    ]


def test_ag59ab_canonical_docs_secondary_only_is_not_laundered_as_fulfilled() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.CONCEPTUAL_EXPLAINER,
        user_intent_interpretation="User asks for canonical PostgreSQL MVCC docs.",
        answer_goal="Explain PostgreSQL MVCC behavior from canonical docs.",
        must_satisfy=("explain documented behavior from canonical documentation",),
        evidence_classes_needed=("primary_source_documents",),
        answer_posture_if_fulfilled="answer from canonical documentation",
        answer_posture_if_partial="answer with canonical-documentation caveat",
    )
    handoff = build_answer_contract_fulfillment(
        build_answer_controller_state(
            contract,
            evidence_state_summary=EvidenceStateSummary(
                evidence_available=True,
                evidence_sufficient=True,
                source_classes_present=("reputable_secondary",),
                fulfilled_obligations=contract.must_satisfy,
            ),
        ),
        evidence_used=(
            EvidenceReference(
                reference="analysis.example/postgresql-mvcc",
                source_class="reputable_secondary",
                summary="A secondary article discusses the official docs.",
                supports=("explain documented behavior from canonical documentation",),
            ),
        ),
    )
    payload = handoff.to_dict()

    assert payload["final_answer_posture"] == "answer with canonical-documentation caveat"
    assert payload["source_obligation_status"] == "partial"
    assert payload["unfulfilled_source_classes"] == ["primary_source_documents"]
    assert "primary_source_documents" in payload["unfulfilled_items"]
    assert "explain documented behavior from canonical documentation" in payload[
        "partial_items"
    ]
    assert "canonical/official documentation missing or secondary-only" in payload[
        "warnings_to_Analyst_or_Author"
    ]


def test_ag59ab_analyst_prompt_obeys_controller_authorized_posture() -> None:
    analyst_prompt = DEFAULT_SYSTEM["analyst"].casefold()

    assert "controller posture" in analyst_prompt
    assert "synthesize only inside that posture" in analyst_prompt
    assert "do not convert unmet official/current/canonical/primary/legal obligations" in (
        analyst_prompt
    )
    assert "baseline expert knowledge" in analyst_prompt
    assert "must not stand in for a missing required source class" in analyst_prompt
    assert "combined with your baseline expert knowledge" not in analyst_prompt


def test_ag59ab_author_prompt_preserves_insufficiency_and_blocks_citation_laundering() -> None:
    author_prompt = DEFAULT_SYSTEM["author"].casefold()

    assert "controller posture" in author_prompt
    assert "preserve that posture and its caveats" in author_prompt
    assert "citation-laundering" in author_prompt
    assert "do not cite secondary, community, social, weak, or off-topic sources" in (
        author_prompt
    )
    assert "missing official/current/canonical/primary/legal evidence" in author_prompt


def test_ag59ab_weak_no_good_evidence_keeps_insufficient_posture_without_invention() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.WEAK_EVIDENCE_OR_NO_GOOD_EVIDENCE_ANSWER,
        user_intent_interpretation="User asks whether a thinly sourced claim is true.",
        answer_goal="Assess support without inventing missing policy details.",
        evidence_classes_needed=("official_current_rules",),
    )
    state = build_answer_controller_state(
        contract,
        evidence_state_summary=EvidenceStateSummary(
            evidence_available=True,
            weak_corpus=True,
            weak_corpus_reason="retrieval returned weak or off-topic evidence",
            source_classes_missing=("official_current_rules",),
        ),
        caps=AnswerControllerCaps(max_iterations=2, max_recovery_attempts=0),
    )
    action = decide_answer_controller_action(state)
    handoff = build_answer_contract_fulfillment(state)

    assert action.action_name is AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT
    assert handoff.final_answer_posture == contract.answer_posture_if_partial
    assert handoff.source_obligation_status == "unfulfilled"
    assert handoff.unfulfilled_source_classes == ("official_current_rules",)
    assert "official_current_rules" in handoff.unfulfilled_items


def test_ag59ab_conceptual_explainer_secondary_evidence_negative_control() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.CONCEPTUAL_EXPLAINER,
        user_intent_interpretation="User asks for an ordinary conceptual explainer.",
        answer_goal="Explain why compound interest matters.",
    )
    handoff = build_answer_contract_fulfillment(
        build_answer_controller_state(
            contract,
            evidence_state_summary=EvidenceStateSummary(
                evidence_available=True,
                evidence_sufficient=True,
                source_classes_present=("reputable_secondary",),
                fulfilled_obligations=contract.must_satisfy,
            ),
        )
    )

    assert handoff.source_obligation_status == "fulfilled"
    assert handoff.unfulfilled_items == ()
    assert handoff.warnings_to_Analyst_or_Author == ()


def test_ag59ab_explicit_academic_request_negative_control() -> None:
    query = "Give me a peer-reviewed literature review on SQLite WAL benchmarks."

    assert is_explicit_academic_literature_request(query)
    assert not is_canonical_technical_documentation_context(
        query,
        required_source_classes=("primary_source_documents",),
    )


def test_ag59ab_canonical_docs_positive_control_remains_canonical_source_oriented() -> None:
    query = "Use official documentation to explain PostgreSQL MVCC behavior."
    recommendation = build_source_class_recovery_recommendation(
        query=query,
        current_date="2026-05-26",
        intent="general",
        report_type="general_research",
        query_type="technical_reference",
        core_topic=query,
        primary_entity="PostgreSQL",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"analysis.example": 2},
        top_source_domains=[{"domain": "analysis.example", "count": 2}],
        official_evidence_found=False,
    )

    assert recommendation["source_class_recovery_recommended"] is True
    assert recommendation["missing_expected_source_classes"] == [
        "primary_source_documents"
    ]


def test_ag59ab_mixed_canonical_academic_xfail_remains_preserved() -> None:
    marks = getattr(
        ag57a.test_ag57a_mixed_canonical_and_academic_obligation_needs_multi_source_contract,
        "pytestmark",
        [],
    )

    xfail_marks = [mark for mark in marks if mark.name == "xfail"]
    assert len(xfail_marks) == 1
    assert xfail_marks[0].kwargs["strict"] is True
    assert "mixed canonical plus academic representation gap" in xfail_marks[0].kwargs[
        "reason"
    ]


def test_ag59ab_public_handoff_leakage_guard_keeps_protected_material_out() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.CURRENT_OFFICIAL_RULES,
        user_intent_interpretation="User asks for current official rules.",
        answer_goal="Answer current official rules.",
    )
    handoff = build_answer_contract_fulfillment(
        build_answer_controller_state(
            contract,
            evidence_state_summary=EvidenceStateSummary(
                evidence_available=True,
                source_classes_missing=("official_current_rules",),
            ),
        ),
        evidence_used=(
            EvidenceReference(
                reference="provider_diagnostics raw_prompt",
                source_class="reputable_secondary",
                summary="raw evidence dump quantitative_packet economist_v1",
                supports=("controller_diagnostics",),
            ),
        ),
        warnings_to_Analyst_or_Author=(
            "Do not expose full_trace or provider_payload.",
        ),
    )
    payload = json.dumps(handoff.to_dict(), sort_keys=True)

    for marker in (
        "raw_prompt",
        "full_trace",
        "provider_payload",
        "quantitative_packet",
        "economist_v1",
        "controller_diagnostics",
    ):
        assert marker not in payload
        assert marker.casefold() not in payload.casefold()
    assert "[redacted protected material]" in payload


def test_ag59ab_protected_prompt_surfaces_stay_narrow() -> None:
    prompts = DEFAULT_SYSTEM

    assert "controller posture" in prompts["analyst"].casefold()
    assert "controller posture" in prompts["author"].casefold()
    assert "controllerhandoff" not in prompts["router"].casefold()
    assert "controllerhandoff" not in prompts["researcher"].casefold()
    assert "controller posture" not in prompts["economist"].casefold()
    assert "source-obligation posture" not in prompts["scrutineer"].casefold()

    orchestrator_source = (_ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "AG59AB" not in orchestrator_source
