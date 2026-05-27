from __future__ import annotations

import ast
import json
from pathlib import Path

from core.answer_contract_controller import (
    ANSWER_CONTRACT_FAMILY_DESCRIPTIONS,
    AnswerContractFamily,
    AnswerControllerActionName,
    AnswerControllerActionResult,
    AnswerControllerCaps,
    EvidenceReference,
    EvidenceStateSummary,
    ScrutineerRelevance,
    SocialSignalRelevance,
    apply_answer_controller_action_result,
    attach_answer_controller_state,
    build_answer_contract,
    build_answer_contract_fulfillment,
    build_answer_controller_state,
    controller_action_from_retrieval_stop_decision,
    controller_action_from_source_class_recovery_decision,
    controller_action_from_weak_corpus_recovery_decision,
    decide_answer_controller_action,
    draft_answer_contract_from_router_metadata,
    revise_answer_contract,
)
from core.retrieval_stop_controller import (
    RetrievalStopControllerDecision,
    build_retrieval_stop_controller_input,
    decide_retrieval_stop,
)
from core.run_controller import RunController
from core.source_class_recovery_controller import (
    SourceClassRecoveryControllerDecision,
    SourceClassRecoveryDecision,
)
from core.weak_corpus_controller import (
    WeakCorpusRecoveryControllerDecision,
    WeakCorpusRecoveryDecision,
)

_ROOT = Path(__file__).resolve().parents[1]
_CONTROLLER_PATH = _ROOT / "core" / "answer_contract_controller.py"

_RAW_HANDOFF_MARKERS = (
    "controller_diagnostics",
    "planned_vs_observed",
    "task_ledger",
    "quantitative_packet",
    "quantitative_packet_v1",
    "economist_v1",
    "QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
    "## QUANTITATIVE FRAMEWORK",
    "ECONOMIST FRAMEWORK",
    "source_bound_values",
    "calculations_requested",
    "provider_diagnostics",
    "provider_attempts_by_role",
)


def test_answer_contract_family_taxonomy_v1_is_complete() -> None:
    assert {
        AnswerContractFamily.DEVELOPING_EVENT_ORIENTATION,
        AnswerContractFamily.CURRENT_OFFICIAL_RULES,
        AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT,
        AnswerContractFamily.RECOMMENDATION_DECISION_SUPPORT,
        AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL,
        AnswerContractFamily.CONCEPTUAL_EXPLAINER,
        AnswerContractFamily.HISTORICAL_OR_ARCHIVAL_ANSWER,
        AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER,
        AnswerContractFamily.WEAK_EVIDENCE_OR_NO_GOOD_EVIDENCE_ANSWER,
    } == set(AnswerContractFamily)
    assert set(ANSWER_CONTRACT_FAMILY_DESCRIPTIONS) == set(AnswerContractFamily)


def test_router_draft_contract_interface_uses_existing_metadata_without_prompt_change() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query="What are the current official eligibility rules for the Acme Care Program?",
        intent="general",
        report_type="general_research",
        query_type="product",
        mode="Balanced",
        core_topic="Acme Care Program eligibility",
    )

    assert contract.family is AnswerContractFamily.CURRENT_OFFICIAL_RULES
    assert "official_current_rules" in contract.evidence_classes_needed
    assert contract.social_signal_relevance is SocialSignalRelevance.IRRELEVANT
    assert contract.scrutineer_relevance is ScrutineerRelevance.NOT_RELEVANT
    assert "Router report_type: general_research" in contract.user_intent_interpretation


def test_controller_revises_contract_and_handoff_captures_revision() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query="Explain the Acme update",
        report_type="general_research",
        query_type="concept",
    )
    revised, revision = revise_answer_contract(
        contract,
        iteration=2,
        reason="evidence showed this is a regulatory filing question",
        family=AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT,
        evidence_classes_needed=("legal_or_regulatory_text",),
    )
    state = build_answer_controller_state(revised)
    state.contract_revisions.append(revision)
    handoff = build_answer_contract_fulfillment(state)

    assert revised.family is AnswerContractFamily.LEGAL_OR_REGULATORY_PRIMARY_TEXT
    assert handoff.to_dict()["contract_revisions"][0]["prior_family"] == "conceptual_explainer"
    assert handoff.to_dict()["contract_revisions"][0]["revised_family"] == "legal_or_regulatory_primary_text"


def test_easy_sufficient_evidence_stops_early_without_recovery_or_scrutineer() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query="Explain TCP congestion control.",
        report_type="general_research",
        query_type="concept",
        mode="Balanced",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        evidence_sufficient=True,
        source_classes_present=("reputable_secondary",),
        fulfilled_obligations=(
            "explain the core concept accurately",
            "use reputable evidence for factual claims",
        ),
    )
    state = build_answer_controller_state(contract, evidence_state_summary=evidence)

    action = decide_answer_controller_action(state)
    updated = apply_answer_controller_action_result(state, action)
    handoff = build_answer_contract_fulfillment(updated)

    assert action.action_name is AnswerControllerActionName.STOP_SUFFICIENT
    assert action.stable_reason_code == "evidence_sufficient"
    assert all(
        item.action_name
        not in {
            AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS,
            AnswerControllerActionName.RECOVER_WEAK_CORPUS,
            AnswerControllerActionName.RUN_SCRUTINEER_REVIEW,
        }
        for item in updated.action_history
    )
    assert contract.scrutineer_relevance is ScrutineerRelevance.NOT_RELEVANT
    assert handoff.to_dict()["unfulfilled_items"] == []


def test_official_source_missing_runs_targeted_source_class_recovery_under_caps() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.CURRENT_OFFICIAL_RULES,
        user_intent_interpretation="User asks for current official program rules.",
        answer_goal="Answer current Acme Care Program eligibility rules",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        source_classes_present=("reputable_secondary",),
        source_classes_missing=("official_current_rules",),
        approved_targeted_queries=("Acme Care Program official eligibility rules 2026",),
    )
    state = build_answer_controller_state(
        contract,
        evidence_state_summary=evidence,
        caps=AnswerControllerCaps(max_iterations=3, max_recovery_attempts=1),
    )

    action = decide_answer_controller_action(state)
    updated = apply_answer_controller_action_result(state, action)

    assert action.action_name is AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS
    assert action.stable_reason_code == "missing_required_source_class"
    assert action.approved_queries_or_none == (
        "Acme Care Program official eligibility rules 2026",
    )
    assert updated.recovery_attempts["recover_missing_source_class"] == 1


def test_weak_corpus_identifies_what_would_make_answer_stronger() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.WEAK_EVIDENCE_OR_NO_GOOD_EVIDENCE_ANSWER,
        user_intent_interpretation="User asks about a claim with weak evidence.",
        answer_goal="Assess whether the Acme claim is supported",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        weak_corpus=True,
        weak_corpus_reason="off-topic or low-utility passages",
        next_queries=("Acme claim independent verification",),
    )
    state = build_answer_controller_state(contract, evidence_state_summary=evidence)

    action = decide_answer_controller_action(state)
    updated = apply_answer_controller_action_result(state, action)
    handoff = build_answer_contract_fulfillment(updated)

    assert action.action_name is AnswerControllerActionName.RECOVER_WEAK_CORPUS
    assert action.stable_reason_code == "weak_corpus_needs_stronger_evidence"
    assert "stronger independent evidence" in updated.missing_information
    assert "stronger independent evidence" in handoff.to_dict()["unfulfilled_items"]


def test_redundant_query_loop_stops_with_caveat() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query="Explain the Acme policy shift.",
        report_type="general_research",
        query_type="concept",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        prior_queries=("Acme policy shift official overview",),
        next_queries=("Acme policy shift official overview",),
        next_query_redundant=True,
    )
    state = build_answer_controller_state(contract, evidence_state_summary=evidence)

    action = decide_answer_controller_action(state)

    assert action.action_name is AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT
    assert action.stable_reason_code == "redundant_next_query"


def test_conflicting_evidence_seeks_resolving_source_before_caveat() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.DEVELOPING_EVENT_ORIENTATION,
        user_intent_interpretation="User asks what is happening with Acme outage reports.",
        answer_goal="Orient the user on the Acme outage reports",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        conflicts_present=True,
        conflict_notes=("official status conflicts with media timestamp",),
        resolving_queries=("Acme official outage status latest timestamp",),
    )
    state = build_answer_controller_state(contract, evidence_state_summary=evidence)

    action = decide_answer_controller_action(state)

    assert action.action_name is AnswerControllerActionName.RESOLVE_CONFLICT
    assert action.stable_reason_code == "conflict_requires_resolution"
    assert action.approved_queries_or_none == ("Acme official outage status latest timestamp",)


def test_quantitative_comparison_identifies_needed_variables_and_assumptions() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query="Compare total cost of Option A vs Option B over three years.",
        report_type="quantitative_comparison",
        query_type="comparison",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        quantitative_variables_needed=("upfront cost", "annual maintenance"),
        quantitative_assumptions_needed=("discount rate",),
    )
    state = build_answer_controller_state(contract, evidence_state_summary=evidence)

    action = decide_answer_controller_action(state)

    assert contract.family is AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL
    assert action.action_name is AnswerControllerActionName.DECOMPOSE_QUANTITATIVE_QUESTION
    assert action.stable_reason_code == "quantitative_variables_or_assumptions_missing"
    assert "upfront cost" in action.contract_items_affected
    assert "discount rate" in action.contract_items_affected


def test_explicit_social_media_query_marks_social_check_central_without_provider_call() -> None:
    contract = draft_answer_contract_from_router_metadata(
        query="What is Reddit saying about Acme's new pricing?",
        report_type="general_research",
        query_type="other",
    )
    state = build_answer_controller_state(contract)

    action = decide_answer_controller_action(state)
    updated = apply_answer_controller_action_result(state, action)
    handoff = build_answer_contract_fulfillment(updated)

    assert contract.family is AnswerContractFamily.SOCIAL_MEDIA_OR_SOCIAL_SENTIMENT_ANSWER
    assert contract.social_signal_relevance is SocialSignalRelevance.CENTRAL
    assert action.action_name is AnswerControllerActionName.REQUEST_SOCIAL_SIGNAL_CHECK
    assert action.skip_reason_or_none == "social_provider_not_integrated_ag1"
    assert action.approved_queries_or_none is None
    assert handoff.to_dict()["social_signal_summary"] == (
        "social_signal_relevance=central; status=provider_unavailable"
    )


def test_existing_recovery_and_stop_controllers_map_into_answer_actions() -> None:
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
        queries=("Acme independent support",),
    )
    retrieval_decision = decide_retrieval_stop(
        build_retrieval_stop_controller_input(
            evaluator_sufficient=False,
            iteration=1,
            max_iterations=2,
            prior_queries=("Acme policy official docs",),
            next_queries=("Acme policy official docs",),
        )
    )

    source_action = controller_action_from_source_class_recovery_decision(
        source_decision,
        iteration=1,
    )
    weak_action = controller_action_from_weak_corpus_recovery_decision(
        weak_decision,
        iteration=1,
    )
    stop_action = controller_action_from_retrieval_stop_decision(
        retrieval_decision,
        iteration=1,
    )

    assert source_action.action_name is AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS
    assert source_action.approved_queries_or_none == ("Acme official current rules",)
    assert weak_action.action_name is AnswerControllerActionName.RECOVER_WEAK_CORPUS
    assert weak_action.stable_reason_code == "weak_corpus_first_pass"
    assert retrieval_decision.decision is RetrievalStopControllerDecision.STOP_REDUNDANT_QUERIES
    assert stop_action.action_name is AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT
    assert stop_action.stable_reason_code == "redundant_next_query"


def test_handoff_suppresses_protected_quant_economist_and_diagnostic_material() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL,
        user_intent_interpretation="User asks for a quantitative comparison.",
        answer_goal="Compare Acme margins",
    )
    evidence = EvidenceStateSummary(
        evidence_available=True,
        partial_obligations=("state assumptions",),
        unfulfilled_obligations=("missing sourced numeric values",),
    )
    state = build_answer_controller_state(contract, evidence_state_summary=evidence)
    state.action_history.append(
        AnswerControllerActionResult(
            action_name=AnswerControllerActionName.RETRIEVE_TARGETED,
            reason="controller_diagnostics included raw provider_diagnostics",
            stable_reason_code="targeted_query_available",
            iteration=1,
            next_state_delta={
                "quantitative_packet": {"schema_version": "economist_v1"},
                "source_bound_values": ["raw upstream metric"],
            },
        )
    )
    handoff = build_answer_contract_fulfillment(
        state,
        evidence_used=(
            EvidenceReference(
                reference="source-1",
                source_class="sourced_numeric_values",
                summary="QUANTITATIVE PACKET FOR ANALYST REVIEW ONLY",
            ),
        ),
        warnings_to_Analyst_or_Author=("Do not expose economist_v1 JSON.",),
    )

    payload = json.dumps(handoff.to_dict(), sort_keys=True)
    for marker in _RAW_HANDOFF_MARKERS:
        assert marker not in payload
        assert marker.lower() not in payload.lower()
    assert "[redacted protected material]" in payload


def test_answer_contract_state_attaches_to_run_controller_without_trace_side_effects() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.CONCEPTUAL_EXPLAINER,
        user_intent_interpretation="User asks for a concept explanation.",
        answer_goal="Explain Acme concept",
    )
    state = build_answer_controller_state(contract)
    action = decide_answer_controller_action(state)
    updated = apply_answer_controller_action_result(state, action)
    handoff = build_answer_contract_fulfillment(updated)
    controller = attach_answer_controller_state(RunController(), updated, fulfillment=handoff)

    snapshot = controller.snapshot_state()

    assert snapshot["answer_contract"]["family"] == "conceptual_explainer"
    assert snapshot["answer_contract_action_history"][0]["action_name"] == action.action_name.value
    assert snapshot["answer_contract_fulfillment_handoff"]["schema_version"] == "answer_contract_fulfillment_v1"
    assert controller.to_trace_fragment() == {}


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_answer_contract_controller_static_import_guard() -> None:
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
        for name in _imported_names(_CONTROLLER_PATH)
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    source = _CONTROLLER_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
