from __future__ import annotations

import ast
import json
from pathlib import Path

from core.answer_contract_controller import (
    AnswerContractFamily,
    AnswerControllerActionName,
    AnswerControllerCaps,
    AnswerControllerStopReason,
    EvidenceReference,
    MarginalValueJudgment,
    SocialSignalRelevance,
)
from core.answer_contract_loop_harness import (
    FixtureDrivenActionExecutor,
    SimulatedActionOutcome,
    run_offline_answer_controller_loop_from_pipeline_facts,
)
from core.answer_contract_pipeline_adapter import (
    PipelineAnswerContractFacts,
    PipelineEvidenceFacts,
    PipelineEvidenceReferenceFact,
    PipelineRouterFacts,
)

_ROOT = Path(__file__).resolve().parents[1]
_HARNESS_PATH = _ROOT / "core" / "answer_contract_loop_harness.py"
_ADAPTER_PATH = _ROOT / "core" / "answer_contract_pipeline_adapter.py"


def _action_names(result: object) -> list[AnswerControllerActionName]:
    return [item.action_name for item in result.action_history]  # type: ignore[attr-defined]


def test_easy_sufficient_evidence_stops_early_without_recovery_scrutineer_or_social() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="Explain how TCP congestion control works.",
            report_type="general_research",
            query_type="concept",
            mode="Balanced",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            evidence_sufficient=True,
            source_classes_present=("reputable_secondary",),
            fulfilled_obligations=(
                "explain the core concept accurately",
                "use reputable evidence for factual claims",
            ),
        ),
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(facts)
    handoff = result.fulfillment_handoff.to_dict()

    assert result.final_state.active_contract.family is AnswerContractFamily.CONCEPTUAL_EXPLAINER
    assert _action_names(result) == [AnswerControllerActionName.STOP_SUFFICIENT]
    assert result.stopped_by == AnswerControllerStopReason.EVIDENCE_SUFFICIENT.value
    assert handoff["unfulfilled_items"] == []
    assert AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS not in _action_names(result)
    assert AnswerControllerActionName.RECOVER_WEAK_CORPUS not in _action_names(result)
    assert AnswerControllerActionName.RUN_SCRUTINEER_REVIEW not in _action_names(result)
    assert AnswerControllerActionName.REQUEST_SOCIAL_SIGNAL_CHECK not in _action_names(result)


def test_official_source_missing_runs_targeted_recovery_then_fulfills() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="What are the current official rules for Acme Care eligibility?",
            report_type="general_research",
            query_type="product",
            core_topic="Acme Care eligibility",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            source_classes_present=("reputable_secondary",),
            source_classes_missing=("official_current_rules",),
            approved_targeted_queries=("Acme Care official eligibility rules 2026",),
        ),
    )
    executor = FixtureDrivenActionExecutor(
        {
            AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS: (
                SimulatedActionOutcome(
                    evidence_state_delta={
                        "evidence_sufficient": True,
                        "source_classes_present": ("reputable_secondary", "official_current_rules"),
                        "source_classes_missing": (),
                        "fulfilled_obligations": (
                            "identify the current official rule or policy",
                            "separate official requirements from interpretation",
                        ),
                    },
                    evidence_used=(
                        EvidenceReference(
                            reference="official-rules-fixture",
                            source_class="official_current_rules",
                            summary="Synthetic official rules fixture.",
                            supports=("identify the current official rule or policy",),
                        ),
                    ),
                ),
            )
        }
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(facts, executor)
    handoff = result.fulfillment_handoff.to_dict()

    assert _action_names(result) == [
        AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS,
        AnswerControllerActionName.STOP_SUFFICIENT,
    ]
    assert result.final_state.evidence_state_summary.source_classes_present == (
        "reputable_secondary",
        "official_current_rules",
    )
    assert result.stopped_by == AnswerControllerStopReason.EVIDENCE_SUFFICIENT.value
    assert "identify the current official rule or policy" in handoff["fulfilled_items"]
    assert handoff["unfulfilled_items"] == []


def test_official_source_missing_stops_partial_after_recovery_cap() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="What are the current official rules for Acme Care eligibility?",
            report_type="general_research",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            source_classes_present=("reputable_secondary",),
            source_classes_missing=("official_current_rules",),
            approved_targeted_queries=("Acme Care official eligibility rules 2026",),
        ),
        caps=AnswerControllerCaps(max_iterations=3, max_recovery_attempts=1),
    )
    executor = FixtureDrivenActionExecutor(
        {
            AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS: (
                SimulatedActionOutcome(
                    evidence_state_delta={
                        "source_classes_missing": ("official_current_rules",),
                        "approved_targeted_queries": (),
                        "next_queries": (),
                        "unfulfilled_obligations": ("official evidence gap: official_current_rules",),
                    }
                ),
            )
        }
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(facts, executor)
    handoff = result.fulfillment_handoff.to_dict()

    assert _action_names(result) == [
        AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS,
        AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
    ]
    assert result.final_state.recovery_attempts["recover_missing_source_class"] == 1
    assert result.stopped_by == AnswerControllerStopReason.OFFICIAL_OR_PRIMARY_UNAVAILABLE.value
    assert handoff["unfulfilled_items"] == ["official evidence gap: official_current_rules"]
    assert handoff["final_answer_posture"] == "answer with official-evidence caveat"


def test_weak_corpus_records_stronger_evidence_requirement_and_stops_partial_when_unresolved() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="Is the Acme claim well supported?",
            report_type="general_research",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            weak_corpus=True,
            weak_corpus_reason="off-topic or low-utility passages",
            next_queries=("Acme claim independent verification",),
        ),
        caps=AnswerControllerCaps(max_iterations=3, max_recovery_attempts=1),
    )
    executor = FixtureDrivenActionExecutor(
        {
            AnswerControllerActionName.RECOVER_WEAK_CORPUS: (
                SimulatedActionOutcome(
                    evidence_state_delta={
                        "weak_corpus": True,
                        "next_queries": (),
                        "unfulfilled_obligations": ("stronger independent evidence",),
                    }
                ),
            )
        }
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(facts, executor)
    handoff = result.fulfillment_handoff.to_dict()

    assert _action_names(result) == [
        AnswerControllerActionName.RECOVER_WEAK_CORPUS,
        AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
    ]
    assert result.final_state.recovery_attempts["recover_weak_corpus"] == 1
    assert "stronger independent evidence" in result.final_state.missing_information
    assert handoff["unfulfilled_items"] == ["stronger independent evidence"]
    assert result.stopped_by == AnswerControllerStopReason.WEAK_CORPUS_UNRESOLVED.value


def test_redundant_query_loop_stops_without_repeating_retrieval() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="Explain the Acme policy shift.",
            report_type="general_research",
            query_type="concept",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            prior_queries=("Acme policy shift official overview",),
            next_queries=("Acme policy shift official overview",),
            next_query_redundant=True,
        ),
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(facts)

    assert _action_names(result) == [AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT]
    assert result.stopped_by == AnswerControllerStopReason.REDUNDANT_NEXT_QUERY.value


def test_conflicting_evidence_resolves_with_fixture_or_caveats_with_warning() -> None:
    resolving_facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="What is happening with Acme outage reports?",
            intent="news",
            query_type="news",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            conflicts_present=True,
            conflict_notes=("official status conflicts with media timestamp",),
            resolving_queries=("Acme official outage status latest timestamp",),
        ),
    )
    resolving_executor = FixtureDrivenActionExecutor(
        {
            AnswerControllerActionName.RESOLVE_CONFLICT: (
                SimulatedActionOutcome(
                    evidence_state_delta={
                        "conflicts_present": False,
                        "conflict_notes": (),
                        "resolving_queries": (),
                        "evidence_sufficient": True,
                        "fulfilled_obligations": (
                            "identify known facts",
                            "identify unsettled points",
                            "give a directional reading with caveats",
                        ),
                    },
                    evidence_used=(
                        EvidenceReference(
                            reference="official-status-fixture",
                            source_class="current_primary_or_official",
                            summary="Synthetic resolving official status.",
                        ),
                    ),
                ),
            )
        }
    )

    resolved = run_offline_answer_controller_loop_from_pipeline_facts(
        resolving_facts,
        resolving_executor,
    )

    assert _action_names(resolved) == [
        AnswerControllerActionName.RESOLVE_CONFLICT,
        AnswerControllerActionName.STOP_SUFFICIENT,
    ]
    assert resolved.stopped_by == AnswerControllerStopReason.EVIDENCE_SUFFICIENT.value

    unresolved_executor = FixtureDrivenActionExecutor(
        {
            AnswerControllerActionName.RESOLVE_CONFLICT: (
                SimulatedActionOutcome(
                    evidence_state_delta={
                        "conflicts_present": True,
                        "resolving_queries": (),
                        "unfulfilled_obligations": ("unresolved conflict: official timestamp mismatch",),
                    },
                    warnings_to_analyst_or_author=("Conflict remains unresolved; preserve caveat.",),
                ),
            )
        }
    )

    unresolved = run_offline_answer_controller_loop_from_pipeline_facts(
        resolving_facts,
        unresolved_executor,
    )
    handoff = unresolved.fulfillment_handoff.to_dict()

    assert _action_names(unresolved) == [
        AnswerControllerActionName.RESOLVE_CONFLICT,
        AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
    ]
    assert handoff["unfulfilled_items"] == ["unresolved conflict: official timestamp mismatch"]
    assert handoff["warnings_to_Analyst_or_Author"] == ["Conflict remains unresolved; preserve caveat."]


def test_quantitative_comparison_decomposes_variables_without_economist_code_or_raw_handoff() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="Compare total cost of Option A vs Option B over three years.",
            report_type="quantitative_comparison",
            query_type="comparison",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            quantitative_variables_needed=("upfront cost", "annual maintenance"),
            quantitative_assumptions_needed=("discount rate",),
            evidence_references=(
                PipelineEvidenceReferenceFact(
                    reference="cost-source",
                    source_class="sourced_numeric_values",
                    summary="raw quantitative_packet economist_v1 should be suppressed",
                ),
            ),
        ),
    )
    executor = FixtureDrivenActionExecutor(
        {
            AnswerControllerActionName.DECOMPOSE_QUANTITATIVE_QUESTION: (
                SimulatedActionOutcome(
                    evidence_state_delta={
                        "quantitative_variables_needed": (),
                        "quantitative_assumptions_needed": (),
                        "evidence_sufficient": True,
                        "fulfilled_obligations": (
                            "identify variables and units",
                            "state assumptions",
                            "separate sourced values from calculations",
                        ),
                    }
                ),
            )
        }
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(facts, executor)
    first_action = result.action_history[0]
    payload = json.dumps(result.fulfillment_handoff.to_dict(), sort_keys=True)

    assert result.final_state.active_contract.family is AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL
    assert first_action.action_name is AnswerControllerActionName.DECOMPOSE_QUANTITATIVE_QUESTION
    assert first_action.contract_items_affected == ("upfront cost", "annual maintenance", "discount rate")
    assert "quantitative_packet" not in payload
    assert "economist_v1" not in payload
    assert "execute" not in payload.lower()


def test_explicit_social_media_query_requests_social_check_without_provider_integration() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="What is Reddit saying about Acme's new pricing?",
            report_type="general_research",
            query_type="other",
        ),
        evidence=PipelineEvidenceFacts(evidence_available=True),
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(facts)
    handoff = result.fulfillment_handoff.to_dict()

    assert result.final_state.active_contract.family is AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER
    assert result.final_state.active_contract.social_signal_relevance is SocialSignalRelevance.CENTRAL
    assert _action_names(result) == [AnswerControllerActionName.REQUEST_SOCIAL_SIGNAL_CHECK]
    assert result.action_history[0].skip_reason_or_none == "social_provider_not_integrated_ag1"
    assert "provider_unavailable" in handoff["social_signal_summary"]
    assert "social signal evidence unavailable in AG-1" in handoff["unfulfilled_items"]


def test_recommendation_query_marks_social_optional_but_not_authoritative() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="Which Acme laptop should I buy for travel?",
            report_type="general_research",
            query_type="product",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            evidence_sufficient=True,
            source_classes_present=("current_specs_or_availability", "reputable_reviews"),
            fulfilled_obligations=("identify decision criteria", "compare tradeoffs against user constraints"),
            social_signal_status="not_checked",
        ),
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(facts)

    assert result.final_state.active_contract.family is AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT
    assert result.final_state.active_contract.social_signal_relevance is SocialSignalRelevance.RELEVANT_OPTIONAL
    assert _action_names(result) == [AnswerControllerActionName.STOP_SUFFICIENT]
    assert AnswerControllerActionName.REQUEST_SOCIAL_SIGNAL_CHECK not in _action_names(result)
    assert result.final_state.evidence_state_summary.source_classes_present == (
        "current_specs_or_availability",
        "reputable_reviews",
    )


def test_balanced_scrutineer_negative_control_does_not_broaden_invocation() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="Explain what DNS caching does.",
            report_type="general_research",
            query_type="concept",
            mode="Balanced",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            evidence_sufficient=True,
            source_classes_present=("reputable_secondary",),
        ),
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(facts)

    assert result.final_state.active_contract.scrutineer_relevance.value == "not_relevant"
    assert result.final_state.evidence_state_summary.scrutineer_needed is False
    assert AnswerControllerActionName.RUN_SCRUTINEER_REVIEW not in _action_names(result)


def test_marginal_value_low_fixture_stops_with_stable_reason() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="Explain a niche Acme claim with limited evidence.",
            report_type="general_research",
            query_type="concept",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            approved_targeted_queries=("Acme niche claim more evidence",),
        ),
    )
    marginal = MarginalValueJudgment(
        likely_change_answer_posture=False,
        missing_information_central=True,
        current_evidence_directionally_useful=True,
        caveat_more_honest_than_more_retrieval=True,
        public_rationale="More offline retrieval would not change the answer posture.",
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(
        facts,
        marginal_value_judgments_by_iteration={1: marginal},
    )

    assert _action_names(result) == [AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT]
    assert result.stopped_by == AnswerControllerStopReason.MARGINAL_VALUE_LOW.value


def test_protected_handoff_leak_material_is_suppressed_in_loop_result() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="Compare Acme unit economics.",
            report_type="quantitative_comparison",
            query_type="comparison",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            quantitative_variables_needed=("margin",),
            evidence_references=(
                PipelineEvidenceReferenceFact(
                    reference="raw_provider_diagnostics",
                    source_class="sourced_numeric_values",
                    summary="QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
                    supports=("raw evidence dump",),
                ),
            ),
            warnings_to_analyst_or_author=("Never expose raw economist_v1 framework.",),
        ),
    )

    result = run_offline_answer_controller_loop_from_pipeline_facts(
        facts,
        FixtureDrivenActionExecutor(
            {
                AnswerControllerActionName.DECOMPOSE_QUANTITATIVE_QUESTION: (
                    SimulatedActionOutcome(
                        evidence_state_delta={
                            "quantitative_variables_needed": (),
                            "unfulfilled_obligations": ("missing sourced numeric values",),
                        },
                        warnings_to_analyst_or_author=("provider_diagnostics should remain internal",),
                        stop_loop=True,
                    ),
                )
            }
        ),
    )
    payload = json.dumps(result.fulfillment_handoff.to_dict(), sort_keys=True)

    for marker in (
        "quantitative_packet",
        "Economist framework",
        "economist_v1",
        "raw_provider",
        "provider_diagnostics",
        "raw evidence dump",
        "raw prompt",
        "internal diagnostics",
    ):
        assert marker not in payload
        assert marker.lower() not in payload.lower()
    assert "[redacted protected material]" in payload


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_static_no_live_provider_prompt_persistence_or_orchestrator_imports() -> None:
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.llm",
        "core.prompts",
        "core.search_providers",
        "core.db",
        "core.storage",
        "core.run_logging",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.retrieval_quality",
        "core.routing",
        "core.scout",
        "core.source_class_recovery",
        "core.weak_corpus_recovery",
    )
    forbidden_terms = (
        "ask_model",
        "process_search_queries",
        "select_providers",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "run_source_class_recovery",
        "run_weak_corpus_recovery",
        "choose_retrieval_search_depth",
        "execute_economist",
    )

    for path in (_HARNESS_PATH, _ADAPTER_PATH):
        violations = [
            name
            for name in _imported_names(path)
            for prefix in forbidden_import_prefixes
            if name == prefix or name.startswith(prefix + ".")
        ]
        source = path.read_text(encoding="utf-8")

        assert violations == []
        assert all(term not in source for term in forbidden_terms)
