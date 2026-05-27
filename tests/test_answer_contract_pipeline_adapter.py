from __future__ import annotations

import ast
import json
from pathlib import Path

from core.answer_contract_controller import (
    AnswerContractFamily,
    AnswerControllerActionName,
    SocialSignalRelevance,
    decide_answer_controller_action,
)
from core.answer_contract_pipeline_adapter import (
    PipelineAnswerContractFacts,
    PipelineControllerDecisionFacts,
    PipelineEvidenceFacts,
    PipelineEvidenceReferenceFact,
    PipelineRouterFacts,
    adapt_pipeline_facts_to_answer_contract_controller,
)
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    RetrievalStopDecision,
)
from core.source_class_recovery_controller import (
    SourceClassRecoveryControllerDecision,
    SourceClassRecoveryDecision,
)
from core.weak_corpus_controller import (
    WeakCorpusRecoveryControllerDecision,
    WeakCorpusRecoveryDecision,
)

_ROOT = Path(__file__).resolve().parents[1]
_ADAPTER_PATH = _ROOT / "core" / "answer_contract_pipeline_adapter.py"


def test_pipeline_facts_map_official_gap_to_contract_state_and_handoff() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="What are the current official rules for Acme Care eligibility?",
            intent="general",
            report_type="general_research",
            query_type="product",
            mode="Balanced",
            current_date="2026-05-21",
            core_topic="Acme Care eligibility",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            source_classes_present=("reputable_secondary",),
            source_classes_missing=("official_current_rules",),
            approved_targeted_queries=("Acme Care official eligibility rules 2026",),
            evidence_references=(
                PipelineEvidenceReferenceFact(
                    reference="secondary-summary",
                    source_class="reputable_secondary",
                    summary="Secondary explainer says the rules changed recently.",
                    supports=("separate official requirements from interpretation",),
                ),
            ),
        ),
    )

    adapted = adapt_pipeline_facts_to_answer_contract_controller(facts)
    action = decide_answer_controller_action(adapted.state)

    assert adapted.contract.family is AnswerContractFamily.CURRENT_OFFICIAL_RULES
    assert "Current date: 2026-05-21" in adapted.contract.user_intent_interpretation
    assert adapted.evidence_state_summary.source_classes_present == ("reputable_secondary",)
    assert adapted.evidence_state_summary.source_classes_missing == ("official_current_rules",)
    assert action.action_name is AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS
    assert action.approved_queries_or_none == ("Acme Care official eligibility rules 2026",)
    assert adapted.fulfillment_handoff.to_dict()["evidence_used"][0]["reference"] == "secondary-summary"


def test_pipeline_conceptual_sufficient_fixture_stops_without_recovery_or_scrutineer() -> None:
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

    adapted = adapt_pipeline_facts_to_answer_contract_controller(facts)
    action = decide_answer_controller_action(adapted.state)

    assert adapted.contract.family is AnswerContractFamily.CONCEPTUAL_EXPLAINER
    assert action.action_name is AnswerControllerActionName.STOP_SUFFICIENT
    assert adapted.contract.social_signal_relevance is SocialSignalRelevance.IRRELEVANT
    assert adapted.evidence_state_summary.scrutineer_needed is False
    assert adapted.fulfillment_handoff.to_dict()["unfulfilled_items"] == []


def test_pipeline_adapter_replays_existing_recovery_and_stop_decisions_as_history() -> None:
    source_decision = SourceClassRecoveryDecision(
        decision=SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY,
        reason="missing_expected_source_class:official_current_rules",
        missing_expected_source_classes=("official_current_rules",),
        queries=("Acme official current rules",),
        provider_role="source_class_recovery",
        search_depth="basic",
        attempt_count=1,
    )
    weak_decision = WeakCorpusRecoveryDecision(
        decision=WeakCorpusRecoveryControllerDecision.RUN_WEAK_CORPUS_RECOVERY,
        reason="weak_corpus_first_pass",
        queries=("Acme independent evidence",),
    )
    retrieval_decision = RetrievalStopDecision(
        decision=RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES,
        reason="redundant_next_query",
        next_queries=("Acme official current rules",),
        redundancy_score=1.0,
    )
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="What are the current official rules for Acme Care eligibility?",
            report_type="general_research",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            source_classes_missing=("official_current_rules",),
            weak_corpus=True,
        ),
        decisions=PipelineControllerDecisionFacts(
            source_class_recovery_decisions=(source_decision,),
            weak_corpus_recovery_decisions=(weak_decision,),
            retrieval_stop_decisions=(retrieval_decision,),
        ),
    )

    adapted = adapt_pipeline_facts_to_answer_contract_controller(facts)
    action_names = [item.action_name for item in adapted.state.action_history]

    assert action_names == [
        AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS,
        AnswerControllerActionName.RECOVER_WEAK_CORPUS,
        AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT,
    ]
    assert adapted.state.recovery_attempts["recover_missing_source_class"] == 1
    assert adapted.state.recovery_attempts["recover_weak_corpus"] == 1
    assert adapted.state.action_history[0].stable_reason_code == "missing_required_source_class"
    assert adapted.state.action_history[1].stable_reason_code == "weak_corpus_first_pass"
    assert adapted.state.action_history[2].stable_reason_code == "redundant_next_query"
    assert source_decision.provider_role == "source_class_recovery"
    assert source_decision.search_depth == "basic"


def test_pipeline_adapter_handoff_redacts_protected_material() -> None:
    facts = PipelineAnswerContractFacts(
        router=PipelineRouterFacts(
            query="Compare Acme margins for option A and option B.",
            report_type="quantitative_comparison",
            query_type="comparison",
        ),
        evidence=PipelineEvidenceFacts(
            evidence_available=True,
            partial_obligations=("state assumptions",),
            unfulfilled_obligations=("missing sourced numeric values",),
            evidence_references=(
                PipelineEvidenceReferenceFact(
                    reference="provider_diagnostics_dump",
                    source_class="sourced_numeric_values",
                    summary="raw quantitative_packet economist_v1 should not pass through",
                    supports=("source_bound_values",),
                ),
            ),
            warnings_to_analyst_or_author=("Do not expose ECONOMIST FRAMEWORK internals.",),
        ),
    )

    adapted = adapt_pipeline_facts_to_answer_contract_controller(facts)
    payload = json.dumps(adapted.fulfillment_handoff.to_dict(), sort_keys=True)

    for marker in (
        "quantitative_packet",
        "economist_v1",
        "ECONOMIST FRAMEWORK",
        "source_bound_values",
        "provider_diagnostics",
        "raw evidence dump",
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


def test_pipeline_adapter_static_import_guard() -> None:
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
    )

    violations = [
        name
        for name in _imported_names(_ADAPTER_PATH)
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    source = _ADAPTER_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
