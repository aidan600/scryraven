from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.controller_action_envelope import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RESOLVE_CONFLICT,
    RUN_SCRUTINEER_REVIEW,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_ACTION_NAMES,
    EvidenceIntegrationBudgetSnapshot,
    EvidenceIntegrationSnapshot,
    decide_evidence_integration_checkpoint,
)

_ROOT = Path(__file__).resolve().parents[1]
_CHECKPOINT_PATH = _ROOT / "core" / "evidence_integration_checkpoint.py"


def _budget(**overrides: Any) -> EvidenceIntegrationBudgetSnapshot:
    values: dict[str, Any] = {
        "mode": "Balanced",
        "iteration": 1,
        "max_iterations": 3,
        "retrieval_action_budget_remaining": 2,
        "targeted_retrieval_remaining": 2,
        "weak_corpus_recovery_remaining": 1,
        "source_class_recovery_remaining": 1,
        "conflict_resolution_remaining": 1,
        "social_side_packet_placeholder_remaining": 1,
        "scrutineer_review_allowed": False,
        "clarification_allowed": True,
    }
    values.update(overrides)
    return EvidenceIntegrationBudgetSnapshot(**values)


def _snapshot(**overrides: Any) -> EvidenceIntegrationSnapshot:
    values: dict[str, Any] = {
        "contract_family": "conceptual_explainer",
        "contract_must_satisfy": ("answer the question",),
        "required_source_classes": ("reputable_secondary",),
        "fulfilled_contract_items": ("answer the question",),
        "evidence_available": True,
        "evidence_sufficient": False,
        "evidence_reference_count": 2,
        "source_classes_present": ("reputable_secondary",),
        "budget": _budget(),
    }
    values.update(overrides)
    return EvidenceIntegrationSnapshot(**values)


def test_checkpoint_recommends_exactly_one_ag25_action() -> None:
    decision = decide_evidence_integration_checkpoint(
        _snapshot(
            evidence_sufficient=True,
            fulfilled_contract_items=("answer the question",),
        )
    )
    payload = decision.to_dict()

    assert isinstance(payload["action_name"], str)
    assert payload["action_name"] in EVIDENCE_INTEGRATION_ACTION_NAMES
    assert "candidate_actions" not in payload
    assert "recommended_actions" not in payload
    assert payload["action_executed"] is False
    assert payload["runtime_behavior_changed"] is False
    assert payload["reason"]
    assert "budget_rationale" in payload
    assert "blocked_or_skipped_action_rationale" in payload


def test_sufficient_evidence_recommends_stop_sufficient() -> None:
    decision = decide_evidence_integration_checkpoint(
        _snapshot(evidence_sufficient=True)
    )

    assert decision.action_name == STOP_SUFFICIENT
    assert decision.contract_gap_addressed is None


def test_weak_evidence_can_recommend_recover_weak_corpus() -> None:
    decision = decide_evidence_integration_checkpoint(
        _snapshot(
            fulfilled_contract_items=(),
            unfulfilled_contract_items=("stronger independent evidence",),
            weak_corpus=True,
            weak_corpus_reason="first-pass corpus is off topic",
            weak_corpus_recovery_available=True,
        )
    )

    assert decision.action_name == RECOVER_WEAK_CORPUS
    assert decision.contract_gap_addressed == "first-pass corpus is off topic"


def test_missing_required_source_class_recommends_recovery() -> None:
    decision = decide_evidence_integration_checkpoint(
        _snapshot(
            fulfilled_contract_items=(),
            unfulfilled_contract_items=("official_current_rules",),
            required_source_classes=("official_current_rules",),
            source_classes_present=("reputable_secondary",),
            source_classes_missing=("official_current_rules",),
            source_class_recovery_recommended=True,
            source_class_recovery_eligible=True,
            source_class_recovery_missing_classes=("official_current_rules",),
            source_class_recovery_queries_available=True,
        )
    )

    assert decision.action_name == RECOVER_MISSING_SOURCE_CLASS
    assert decision.contract_gap_addressed == "official_current_rules"


def test_blocked_source_class_recovery_does_not_overclaim_eligibility() -> None:
    decision = decide_evidence_integration_checkpoint(
        _snapshot(
            fulfilled_contract_items=(),
            unfulfilled_contract_items=("official_current_rules",),
            required_source_classes=("official_current_rules",),
            source_classes_present=("reputable_secondary",),
            source_classes_missing=("official_current_rules",),
            source_class_recovery_recommended=True,
            source_class_recovery_eligible=False,
            source_class_recovery_missing_classes=("official_current_rules",),
            source_class_recovery_queries_available=True,
            source_class_recovery_blockers=("blocked_by_iteration_budget",),
        )
    )

    assert decision.action_name != RECOVER_MISSING_SOURCE_CLASS
    assert decision.blocked_or_skipped_action_rationale[
        RECOVER_MISSING_SOURCE_CLASS
    ] == "blocked:blocked_by_iteration_budget"


def test_material_conflict_recommends_resolve_conflict() -> None:
    decision = decide_evidence_integration_checkpoint(
        _snapshot(
            fulfilled_contract_items=(),
            partial_contract_items=("conflicting launch dates",),
            conflicts_present=True,
            conflict_notes=("sources materially disagree on launch date",),
            conflict_resolution_available=True,
        )
    )

    assert decision.action_name == RESOLVE_CONFLICT
    assert decision.contract_gap_addressed == (
        "sources materially disagree on launch date"
    )


def test_exhausted_or_low_value_budget_stops_with_caveat() -> None:
    decision = decide_evidence_integration_checkpoint(
        _snapshot(
            fulfilled_contract_items=(),
            unfulfilled_contract_items=("missing current corroboration",),
            budget=_budget(
                retrieval_action_budget_remaining=0,
                targeted_retrieval_remaining=0,
                weak_corpus_recovery_remaining=0,
                source_class_recovery_remaining=0,
                conflict_resolution_remaining=0,
                low_value_stop_recommended=True,
            ),
        )
    )

    assert decision.action_name == STOP_INSUFFICIENT_WITH_CAVEAT
    assert "low" in decision.budget_rationale


def test_social_recommendation_is_placeholder_side_packet_only() -> None:
    decision = decide_evidence_integration_checkpoint(
        _snapshot(
            fulfilled_contract_items=(),
            unfulfilled_contract_items=("social_signal",),
            social_signal_requested=True,
            social_signal_status="provider_unavailable",
            social_side_packet_placeholder_allowed=True,
        )
    )

    assert decision.action_name == REQUEST_SOCIAL_SIGNAL_CHECK
    assert decision.side_packet_placeholder_only is True
    assert decision.ordinary_evidence_allowed is False
    assert decision.evidence_boundary.value == "social_side_packet_evidence"
    assert "ordinary evidence" in decision.budget_rationale


def test_scrutineer_is_blocked_unless_mode_and_contract_allow_it() -> None:
    blocked = decide_evidence_integration_checkpoint(
        _snapshot(
            fulfilled_contract_items=(),
            unfulfilled_contract_items=("review-sensitive claim",),
            scrutineer_needed=True,
            scrutineer_allowed_by_mode=True,
            scrutineer_allowed_by_contract=False,
        )
    )
    assert blocked.action_name != RUN_SCRUTINEER_REVIEW
    assert (
        blocked.blocked_or_skipped_action_rationale[RUN_SCRUTINEER_REVIEW]
        == "blocked_by_contract"
    )

    allowed = decide_evidence_integration_checkpoint(
        _snapshot(
            fulfilled_contract_items=(),
            unfulfilled_contract_items=("review-sensitive claim",),
            scrutineer_needed=True,
            scrutineer_allowed_by_mode=True,
            scrutineer_allowed_by_contract=True,
            budget=_budget(scrutineer_review_allowed=True),
        )
    )
    assert allowed.action_name == RUN_SCRUTINEER_REVIEW


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_checkpoint_static_import_guard_no_provider_search_model_calls() -> None:
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
        "core.pipeline_orchestrator",
        "core.retrieval",
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
        "execute_source_class_recovery_action",
        "choose_retrieval_search_depth",
        "DEFAULT_SYSTEM",
    )

    violations = [
        name
        for name in _imported_names(_CHECKPOINT_PATH)
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    source = _CHECKPOINT_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
