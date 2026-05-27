from __future__ import annotations

import ast
import json
from pathlib import Path

from core.controller_action_envelope import (
    ASK_USER_CLARIFICATION,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    controller_action_names,
)
from core.controller_budget_semantics import (
    SUPPORTED_BUDGET_ACTIONS,
    ControllerBudgetAllowance,
    ControllerBudgetHardCaps,
    ControllerBudgetSpent,
    ControllerBudgetState,
    MarginalValueCostTier,
    MarginalValueDecisionStatus,
    MarginalValueLevel,
    evaluate_controller_budget_action_gate,
)
from core.controller_state_reducer import (
    ControllerBudgetClass,
    controller_budget_descriptors,
)

_ROOT = Path(__file__).resolve().parents[1]
_BUDGET_PATH = _ROOT / "core" / "controller_budget_semantics.py"


def _balanced_state(**overrides: object) -> ControllerBudgetState:
    values = {
        "hard_caps": ControllerBudgetHardCaps.from_mode_policy("Balanced"),
        "spent": ControllerBudgetSpent(retrieval_iterations=1),
        "allowance": ControllerBudgetAllowance(
            retrieval_action_reserve=1,
            targeted_retrieval_reserve=1,
            weak_corpus_recovery_reserve=1,
            source_class_recovery_reserve=1,
            conflict_resolution_reserve=1,
        ),
    }
    values.update(overrides)
    return ControllerBudgetState(**values)


def test_balanced_simple_question_stops_after_sufficient_evidence() -> None:
    result = evaluate_controller_budget_action_gate(
        _balanced_state(
            proposed_action=STOP_SUFFICIENT,
            missing_contract_items=(),
            centrality=MarginalValueLevel.LOW,
            evidence_gap_severity=MarginalValueLevel.LOW,
            conflict_risk=MarginalValueLevel.LOW,
            expected_value=MarginalValueLevel.LOW,
        )
    )
    payload = result.to_dict()

    assert payload["decision"]["status"] == MarginalValueDecisionStatus.APPROVED.value
    assert payload["decision"]["approved"] is True
    assert payload["decision"]["proposed_action"] == STOP_SUFFICIENT
    assert payload["runtime_behavior_changed"] is False
    assert payload["live_side_effects"] is False
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload


def test_balanced_official_legal_gap_approves_bounded_source_class_recovery() -> None:
    result = evaluate_controller_budget_action_gate(
        _balanced_state(
            proposed_action=RECOVER_MISSING_SOURCE_CLASS,
            contract_family="current_legal_or_official_answer",
            contract_obligation="official current rules",
            missing_contract_items=("legal_or_regulatory_text",),
            centrality=MarginalValueLevel.HIGH,
            evidence_gap_severity=MarginalValueLevel.HIGH,
            redundancy_risk=MarginalValueLevel.LOW,
            expected_value=MarginalValueLevel.HIGH,
            cost_tier=MarginalValueCostTier.MEDIUM,
            requires_official_or_legal_evidence=True,
        )
    )
    payload = result.to_dict()

    assert payload["decision"]["status"] == "approved"
    assert payload["decision"]["approved"] is True
    assert payload["state"]["remaining"]["source_class_recovery_remaining"] == 1
    assert payload["state"]["hard_caps"]["mode"] == "Balanced"
    assert payload["state"]["hard_caps"]["search_depth"] == "basic"
    assert payload["metadata"]["provider_routing_boundary"] == "orchestrator_owned"


def test_balanced_redundant_query_skips_spend_and_carries_caveat_reason() -> None:
    result = evaluate_controller_budget_action_gate(
        _balanced_state(
            proposed_action=RETRIEVE_TARGETED,
            missing_contract_items=("independent confirmation",),
            centrality=MarginalValueLevel.MEDIUM,
            evidence_gap_severity=MarginalValueLevel.MEDIUM,
            redundancy_risk=MarginalValueLevel.HIGH,
            expected_value=MarginalValueLevel.MEDIUM,
        )
    )

    decision = result.to_dict()["decision"]

    assert decision["status"] == "skipped"
    assert decision["approved"] is False
    assert decision["stop_reason"] == "redundant_or_low_marginal_value"


def test_deep_conflicting_evidence_approves_conflict_resolution_action() -> None:
    result = evaluate_controller_budget_action_gate(
        ControllerBudgetState.from_mode(
            "Deep",
            spent=ControllerBudgetSpent(retrieval_iterations=1),
            allowance=ControllerBudgetAllowance(
                retrieval_action_reserve=2,
                conflict_resolution_reserve=1,
            ),
            proposed_action=RESOLVE_CONFLICT,
            missing_contract_items=("conflicting policy effective date",),
            centrality=MarginalValueLevel.HIGH,
            evidence_gap_severity=MarginalValueLevel.HIGH,
            conflict_risk=MarginalValueLevel.HIGH,
            expected_value=MarginalValueLevel.HIGH,
            cost_tier=MarginalValueCostTier.MEDIUM,
        )
    )

    payload = result.to_dict()

    assert payload["decision"]["status"] == "approved"
    assert payload["decision"]["approved"] is True
    assert payload["state"]["hard_caps"]["mode"] == "Deep"
    assert payload["state"]["remaining"]["conflict_resolution_remaining"] == 1


def test_exhausted_budget_stops_with_caveat_instead_of_spending() -> None:
    spend_result = evaluate_controller_budget_action_gate(
        _balanced_state(
            spent=ControllerBudgetSpent(retrieval_iterations=2),
            allowance=ControllerBudgetAllowance(
                retrieval_action_reserve=1,
                targeted_retrieval_reserve=1,
            ),
            proposed_action=RETRIEVE_TARGETED,
            missing_contract_items=("current primary evidence",),
            centrality=MarginalValueLevel.HIGH,
            evidence_gap_severity=MarginalValueLevel.HIGH,
            expected_value=MarginalValueLevel.HIGH,
        )
    )
    stop_result = evaluate_controller_budget_action_gate(
        _balanced_state(
            spent=ControllerBudgetSpent(retrieval_iterations=2),
            allowance=ControllerBudgetAllowance(),
            proposed_action=STOP_INSUFFICIENT_WITH_CAVEAT,
            missing_contract_items=("current primary evidence",),
            centrality=MarginalValueLevel.HIGH,
            evidence_gap_severity=MarginalValueLevel.HIGH,
            expected_value=MarginalValueLevel.MEDIUM,
        )
    )

    assert spend_result.to_dict()["decision"]["status"] == "blocked"
    assert spend_result.to_dict()["decision"]["stop_reason"] == (
        "budget_or_reserve_exhausted"
    )
    assert stop_result.to_dict()["decision"]["status"] == "approved"
    assert stop_result.to_dict()["decision"]["proposed_action"] == (
        STOP_INSUFFICIENT_WITH_CAVEAT
    )


def test_weak_corpus_recovery_is_bounded_and_does_not_create_side_loop() -> None:
    approved = evaluate_controller_budget_action_gate(
        _balanced_state(
            proposed_action=RECOVER_WEAK_CORPUS,
            weak_corpus=True,
            missing_contract_items=("stronger independent evidence",),
            centrality=MarginalValueLevel.HIGH,
            evidence_gap_severity=MarginalValueLevel.HIGH,
            expected_value=MarginalValueLevel.HIGH,
        )
    )
    exhausted = evaluate_controller_budget_action_gate(
        _balanced_state(
            proposed_action=RECOVER_WEAK_CORPUS,
            spent=ControllerBudgetSpent(
                retrieval_iterations=1,
                weak_corpus_recovery_attempts=1,
            ),
            allowance=ControllerBudgetAllowance(
                retrieval_action_reserve=1,
                weak_corpus_recovery_reserve=1,
            ),
            weak_corpus=True,
            missing_contract_items=("stronger independent evidence",),
            centrality=MarginalValueLevel.HIGH,
            evidence_gap_severity=MarginalValueLevel.HIGH,
            expected_value=MarginalValueLevel.HIGH,
        )
    )

    assert approved.to_dict()["decision"]["status"] == "approved"
    assert exhausted.to_dict()["decision"]["status"] == "blocked"
    assert exhausted.to_dict()["state"]["remaining"][
        "weak_corpus_recovery_remaining"
    ] == 0


def test_social_signal_stays_side_packet_only_and_cannot_satisfy_legal_gap() -> None:
    result = evaluate_controller_budget_action_gate(
        _balanced_state(
            allowance=ControllerBudgetAllowance(
                social_side_packet_placeholder_allowed=True
            ),
            proposed_action=REQUEST_SOCIAL_SIGNAL_CHECK,
            social_signal_requested=True,
            missing_contract_items=("legal_or_regulatory_text",),
            centrality=MarginalValueLevel.HIGH,
            evidence_gap_severity=MarginalValueLevel.HIGH,
            expected_value=MarginalValueLevel.MEDIUM,
        )
    )
    payload = result.to_dict()

    assert payload["decision"]["status"] == "skipped"
    assert payload["decision"]["approved"] is False
    assert payload["decision"]["stop_reason"] == (
        "social_signal_cannot_satisfy_factual_or_official_gap"
    )
    assert payload["state"]["remaining"][
        "social_side_packet_placeholder_remaining"
    ] == 1
    assert payload["live_side_effects"] is False


def test_fast_mode_has_no_search_reserve_but_allows_safe_clarification() -> None:
    search_result = evaluate_controller_budget_action_gate(
        ControllerBudgetState.from_mode(
            "Fast",
            spent=ControllerBudgetSpent(retrieval_iterations=1),
            allowance=ControllerBudgetAllowance(
                retrieval_action_reserve=0,
                targeted_retrieval_reserve=0,
                clarification_allowed=True,
            ),
            proposed_action=RETRIEVE_TARGETED,
            missing_contract_items=("ambiguous target jurisdiction",),
            centrality=MarginalValueLevel.HIGH,
            evidence_gap_severity=MarginalValueLevel.HIGH,
            expected_value=MarginalValueLevel.HIGH,
        )
    )
    clarify_result = evaluate_controller_budget_action_gate(
        ControllerBudgetState.from_mode(
            "Fast",
            spent=ControllerBudgetSpent(retrieval_iterations=1),
            allowance=ControllerBudgetAllowance(clarification_allowed=True),
            proposed_action=ASK_USER_CLARIFICATION,
            missing_contract_items=("ambiguous target jurisdiction",),
            centrality=MarginalValueLevel.HIGH,
            evidence_gap_severity=MarginalValueLevel.HIGH,
            expected_value=MarginalValueLevel.MEDIUM,
        )
    )

    assert search_result.to_dict()["decision"]["status"] == "blocked"
    assert clarify_result.to_dict()["decision"]["status"] == "approved"
    assert clarify_result.to_dict()["state"]["hard_caps"]["max_iterations"] == 1


def test_budget_gate_uses_ag25_actions_and_aligns_with_ag27_budget_descriptors() -> None:
    descriptors = controller_budget_descriptors()
    result = evaluate_controller_budget_action_gate(
        _balanced_state(proposed_action=STOP_SUFFICIENT)
    ).to_dict()

    assert set(SUPPORTED_BUDGET_ACTIONS) <= set(controller_action_names())
    assert set(result["supported_actions"]) == set(SUPPORTED_BUDGET_ACTIONS)
    assert {item.value for item in ControllerBudgetClass} <= set(descriptors)
    assert set(result["ag27_budget_classes"]) == {
        item.value for item in ControllerBudgetClass
    }
    assert result["warnings"] == []


def test_budget_gate_static_no_runtime_provider_persistence_prompt_or_logs_imports() -> None:
    tree = ast.parse(_BUDGET_PATH.read_text(encoding="utf-8"))
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
        "core.provider_validation",
        "core.provider_diagnostics",
        "core.db",
        "core.storage",
        "core.run_logging",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.retrieval_quality",
        "core.routing",
        "core.scout",
        "core.answer_contract_runtime_handoff",
        "core.run_controller",
        "core.source_class_recovery_lifecycle",
        "core.source_class_recovery_executor",
        "core.weak_corpus_recovery",
    )
    forbidden_terms = (
        "ask_model",
        "process_search_queries",
        "select_providers",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "build_runtime_answer_contract_handoff",
        "record_source_class_recovery_lifecycle",
        "record_weak_corpus_recovery_decision",
        "execute_source_class_recovery_action",
        "run_weak_corpus_recovery",
        "choose_retrieval_search_depth",
        "DEFAULT_SYSTEM",
        "RunController(",
    )

    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

    violations = [
        name
        for name in imported_names
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    source = _BUDGET_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
