from __future__ import annotations

from pathlib import Path
from typing import Any

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
    is_explicit_academic_literature_request,
)
from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.official_source_obligation_bridge import (
    apply_official_source_obligation_bridge,
)
from core.official_source_obligation_candidate_visibility import (
    NOT_REQUIRED,
    UNKNOWN,
    OfficialSourceObligationCandidateVisibilityFacts,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.source_class_recovery import (
    build_recovery_source_quality_diagnostics,
    build_source_class_observability_telemetry,
    build_source_class_recovery_candidate_v2,
    build_source_class_recovery_recommendation,
)
from tests import test_source_hierarchy_answer_contract_invariants_ag57a as ag57a

_ROOT = Path(__file__).resolve().parents[1]
_PROTECTED_UNCHANGED_PATHS = (
    _ROOT / "core" / "pipeline_orchestrator.py",
    _ROOT / "core" / "prompts.py",
    _ROOT / "core" / "routing.py",
    _ROOT / "core" / "search_providers.py",
    _ROOT / "core" / "followup.py",
)


def _source(
    url: str,
    *,
    title: str,
    text: str,
    source_tier: str,
    source_class: str | None = None,
) -> dict[str, Any]:
    source: dict[str, Any] = {
        "source_id": url,
        "url": url,
        "title": title,
        "text": text,
        "source_tier": source_tier,
    }
    if source_class is not None:
        source["source_class"] = source_class
    return source


def _recommendation(query: str, *, query_type: str = "technical_reference") -> dict[str, Any]:
    return build_source_class_recovery_recommendation(
        query=query,
        current_date="2026-05-26",
        intent="general",
        report_type="general_research",
        query_type=query_type,
        core_topic=query,
        primary_entity="",
        anchor_packet=None,
        source_tier_counts={"secondary": 2},
        source_domain_counts={"analysis.example": 2},
        top_source_domains=[{"domain": "analysis.example", "count": 2}],
        official_evidence_found=False,
    )


def _observability(
    query: str,
    final_top_evidence: list[dict[str, Any]],
    *,
    query_type: str = "technical_reference",
) -> dict[str, Any]:
    return build_source_class_observability_telemetry(
        query=query,
        intent="general",
        report_type="general_research",
        query_type=query_type,
        core_topic=query,
        primary_entity="",
        anchor_packet=None,
        final_top_evidence=final_top_evidence,
        final_answer_source_ids=[],
    )


def test_ag58a_canonical_technical_docs_recovery_preserves_primary_docs_obligation() -> None:
    for query in (
        "Use official documentation to explain PostgreSQL MVCC behavior.",
        "Use reference docs to explain SQLite WAL mode tradeoffs.",
        "Use Python dataclasses documentation to explain field defaults.",
        "Use MDN Fetch API reference docs to explain credentials behavior.",
        "Use Kubernetes configuration docs to explain pod restart policy.",
    ):
        recommendation = _recommendation(query)

        assert recommendation["source_class_recovery_recommended"] is True
        assert recommendation["missing_expected_source_classes"] == [
            "primary_source_documents"
        ]
        assert recommendation["source_class_recovery_reason"] == (
            "missing_expected_source_class:primary_source_documents"
        )
        query_text = " ".join(recommendation["source_class_recovery_queries"]).casefold()
        assert "documentation" in query_text
        assert "reference" in query_text
        assert "paper" not in query_text
        assert "arxiv" not in query_text


def test_ag58a_canonical_docs_secondary_evidence_is_secondary_only_not_satisfied() -> None:
    trace = _observability(
        "Use official documentation to explain PostgreSQL MVCC behavior.",
        [
            _source(
                "https://analysis.example/postgresql-mvcc",
                title="PostgreSQL MVCC analysis",
                text="A secondary article discusses official documentation.",
                source_tier="secondary",
            )
        ],
    )
    candidate = build_source_class_recovery_candidate_v2(
        {
            **trace,
            "answer_class": "partial_answer",
            "evidence_sufficient": False,
            "corpus_state": "HEALTHY",
            "weak_corpus_recovery_decision": "no_action",
            "active_source_class_recovery_used": False,
            "active_source_class_recovery_blockers": [],
        }
    )

    assert trace["expected_source_classes_raw"] == ["primary_source_documents"]
    assert trace["source_class_gap_candidates"] == ["primary_source_documents"]
    assert trace["source_class_satisfaction_status"]["primary_source_documents"] == (
        "expected_but_only_secondary"
    )
    assert trace["source_class_strong_satisfaction_counts"]["primary_source_documents"] == 0
    assert candidate["source_class_recovery_candidate_v2_classes"] == [
        "primary_source_documents"
    ]
    assert "expected_source_class_secondary_only" in candidate[
        "source_class_recovery_candidate_v2_reasons"
    ]


def test_ag58a_explicit_academic_requests_do_not_collapse_into_canonical_recovery() -> None:
    for query in (
        "Find peer-reviewed papers about PostgreSQL MVCC performance.",
        "Give me an academic literature review on SQLite WAL benchmarks.",
        "Summarize empirical studies of Fetch API performance.",
        "Find arXiv papers about Kubernetes scheduler tradeoffs.",
    ):
        recommendation = _recommendation(query)

        assert is_explicit_academic_literature_request(query)
        assert recommendation["source_class_recovery_recommended"] is False
        assert recommendation["missing_expected_source_classes"] == []
        assert recommendation["source_class_recovery_queries"] == []


def test_ag58a_official_current_numeric_rule_secondary_only_remains_required() -> None:
    result = apply_official_source_obligation_bridge(
        runtime_trace={
            "query_preview": (
                "What is the current 2026 eligibility threshold and fee for "
                "the public benefit program?"
            ),
            "query_type": "quantitative_comparison",
            "source_class_satisfaction_status": {
                "official_current_rules": "expected_but_only_secondary",
            },
            "source_class_strong_satisfaction_counts": {
                "official_current_rules": 0,
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


def test_ag58a_legal_current_primary_requires_legal_or_official_class() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query=(
            "What is the current compliance deadline under the California "
            "privacy law, and what does the regulation require?"
        ),
        report_type="general_research",
        query_type="legal",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        source_classes_present=("reputable_secondary",),
        source_classes_missing=("legal_or_regulatory_text",),
    )
    action = decide_answer_controller_action(
        build_answer_controller_state(contract, evidence_state_summary=evidence)
    )

    assert contract.family is AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    assert {
        "legal_or_regulatory_text",
        "official_current_rules",
    } <= set(contract.evidence_classes_needed)
    assert action.action_name is AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS
    assert action.stable_reason_code == "missing_required_source_class"


def test_ag58a_ordinary_conceptual_explainer_does_not_force_official_recovery() -> None:
    facts = OfficialSourceObligationCandidateVisibilityFacts.from_runtime_trace(
        {
            "query_preview": "Explain why compound interest matters for beginners.",
            "query_type": "conceptual_explainer",
        }
    )
    recommendation = _recommendation(
        "Explain why compound interest matters for beginners.",
        query_type="conceptual_explainer",
    )

    assert facts.obligation_status == NOT_REQUIRED
    assert facts.required_source_classes == ()
    assert recommendation["source_class_recovery_recommended"] is False
    assert recommendation["missing_expected_source_classes"] == []


def test_ag58a_weak_no_good_evidence_preserves_missing_required_class() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.WEAK_EVIDENCE_OR_NO_GOOD_EVIDENCE_ANSWER,
        user_intent_interpretation="User asks whether a thinly sourced claim is true.",
        answer_goal="Assess support without inventing facts.",
    )
    action = decide_answer_controller_action(
        build_answer_controller_state(
            contract,
            evidence_state_summary=EvidenceStateSummary(
                evidence_available=True,
                weak_corpus=True,
                weak_corpus_reason="retrieval returned off-topic evidence",
                source_classes_missing=("official_current_rules",),
            ),
            caps=AnswerControllerCaps(max_iterations=2, max_recovery_attempts=0),
        )
    )

    assert action.action_name is AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT
    assert action.stable_reason_code == "weak_corpus_unresolved"
    assert action.contract_items_affected == contract.evidence_classes_needed


def test_ag58a_recovered_secondary_or_social_declared_classes_do_not_satisfy_official_gap() -> None:
    secondary_declared = _source(
        "https://analysis.example/official-rule-explainer",
        title="Explainer on official current eligibility rules",
        text="A secondary explainer summarizes the official eligibility rules.",
        source_tier="secondary",
        source_class="official_current_rules",
    )
    social_declared = _source(
        "https://reddit.com/r/example/comments/abc",
        title="Forum thread about official rules",
        text="Users discuss official eligibility rules.",
        source_tier="social_or_forum",
        source_class="official_current_rules",
    )
    quality = build_recovery_source_quality_diagnostics(
        [secondary_declared, social_declared]
    )
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[
            _source(
                "https://analysis.example/context",
                title="Context",
                text="Contextual secondary source.",
                source_tier="secondary",
            )
        ],
        recovered_passages=[secondary_declared, social_declared],
        lifecycle_trace={
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_reason": (
                "answer_contract_official_gap:official_current_rules"
            ),
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_missing_classes": [
                "official_current_rules"
            ],
            "active_source_class_recovery_attempt_count": 1,
            **quality,
        },
        max_final_evidence=4,
    )

    assert quality["recovered_source_class_counts"] == {}
    assert quality["recovery_source_quality_status"] == "secondary_only"
    assert [source["url"] for source in final] == ["https://analysis.example/context"]
    assert decision.used is False
    assert decision.reason == "secondary_only"
    assert decision.source_fit_status == "not_evaluated"


def test_ag58a_official_canonical_recovered_candidate_remains_visible_as_satisfying_class() -> None:
    recovered = _source(
        "https://docs.python.org/3/library/dataclasses.html",
        title="Python dataclasses official documentation",
        text="Official reference documentation for Python dataclasses behavior.",
        source_tier="unknown",
    )
    quality = build_recovery_source_quality_diagnostics([recovered])

    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=[recovered],
        lifecycle_trace={
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:canonical_documentation"
            ),
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_missing_classes": [
                "primary_source_documents"
            ],
            "active_source_class_recovery_attempt_count": 1,
            **quality,
        },
        max_final_evidence=4,
    )

    assert quality["recovered_source_class_counts"] == {
        "primary_source_documents": 1
    }
    assert decision.used is True
    assert decision.recovered_source_class == "primary_source_documents"
    assert [source["url"] for source in final] == [recovered["url"]]


def test_ag58a_unknown_candidate_fields_remain_unknown_not_backfilled() -> None:
    facts = OfficialSourceObligationCandidateVisibilityFacts.from_runtime_trace(
        {
            "expected_source_classes_raw": ["primary_source_documents"],
            "source_survival_final_evidence_official_or_canonical_count": 1,
        }
    )

    assert facts.candidate_query_count == UNKNOWN
    assert facts.candidate_official_source_count == UNKNOWN
    assert facts.accepted_or_readable_official_source_count == UNKNOWN


def test_ag58a_ag50a_preserves_canonical_docs_queries_without_academic_terms() -> None:
    result = apply_official_canonical_recovery_query_acquisition(
        runtime_trace={
            "query_preview": "Use official documentation to explain PostgreSQL MVCC behavior.",
            "core_topic": "PostgreSQL MVCC",
            "primary_entity": "PostgreSQL",
        },
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
    )

    query_text = " ".join(result.recommendation["source_class_recovery_queries"]).casefold()
    assert "official documentation" in query_text
    assert "reference documentation" in query_text
    assert "paper" not in query_text
    assert "arxiv" not in query_text


def test_ag58a_mixed_canonical_academic_gap_remains_strict_xfail() -> None:
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


def test_ag58a_secondary_only_support_keeps_answer_contract_partial_posture() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.CURRENT_OFFICIAL_RULES,
        user_intent_interpretation="User asks for current official rules.",
        answer_goal="Answer from current official rules.",
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
                reference="secondary-explainer",
                source_class="reputable_secondary",
                summary="Secondary explainer summarizes official current rules.",
                supports=("identify the current official rule or policy",),
            ),
        ),
    )

    assert handoff.final_answer_posture == contract.answer_posture_if_partial
    assert "official_current_rules" in handoff.unfulfilled_items


def test_ag58a_static_protected_surfaces_remain_closed() -> None:
    for path in _PROTECTED_UNCHANGED_PATHS:
        assert path.exists()

    source_recovery = (_ROOT / "core" / "source_class_recovery.py").read_text(
        encoding="utf-8"
    ).casefold()
    forbidden_terms = {
        "select_providers",
        "choose_supplemental_search_depth",
        "author_prompt",
        "rank_sources",
        "postgresql.org",
        "sqlite.org",
        "docs.python.org",
        "developer.mozilla.org",
    }
    assert all(term not in source_recovery for term in forbidden_terms)
