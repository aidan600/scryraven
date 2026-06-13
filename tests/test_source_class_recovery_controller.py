from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.source_class_recovery_controller import (
    SourceClassRecoveryControllerDecision,
    build_source_class_recovery_controller_input,
    decide_source_class_recovery,
)

_ROOT = Path(__file__).resolve().parents[1]
_CONTROLLER_PATH = _ROOT / "core" / "source_class_recovery_controller.py"


def _recommendation(
    *,
    recommended: bool = True,
    missing: list[str] | None = None,
    queries: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    missing_classes = list(missing or ["official_current_rules"])
    recovery_queries = list(
        queries
        if queries is not None
        else [
            "Care Program official current eligibility requirements rules government",
            "Care Program current program rules official government requirements",
        ]
    )
    return {
        "source_class_recovery_recommended": recommended,
        "missing_expected_source_classes": missing_classes if recommended else [],
        "source_class_recovery_queries": recovery_queries if recommended else [],
        "source_class_recovery_reason": (
            reason
            if reason is not None
            else "missing_expected_source_class:" + ",".join(missing_classes)
            if recommended
            else None
        ),
    }


def _input(
    *,
    recommendation: dict[str, Any] | None = None,
    weak_corpus_recovery_considered: bool = False,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_skip_reason: str | None = None,
    prior_attempt_count: int = 0,
    iteration_budget_available: bool = True,
    answer_contract_source_class_slot_available: bool = False,
    official_canonical_source_class_slot_available: bool = False,
) -> Any:
    return build_source_class_recovery_controller_input(
        recommendation=recommendation if recommendation is not None else _recommendation(),
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2, "unknown": 1},
            "source_domain_counts": {"regionalnews.example": 2},
            "top_source_domains": [{"domain": "regionalnews.example", "count": 2}],
            "unique_source_domain_count": 1,
            "official_evidence_found": False,
            "raw_evidence": "must not be copied",
            "raw_prompt": "must not be copied",
        },
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=weak_corpus_recovery_considered,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
        current_search_depth="basic",
        iteration_budget_available=iteration_budget_available,
        prior_attempt_count=prior_attempt_count,
        answer_contract_source_class_slot_available=(
            answer_contract_source_class_slot_available
        ),
        official_canonical_source_class_slot_available=(
            official_canonical_source_class_slot_available
        ),
    )


def test_controller_approves_source_class_recovery_from_compact_snapshot() -> None:
    snapshot = _input(
        recommendation=_recommendation(
            queries=[
                "Care Program official rules",
                "Care Program official rules",
                "Care Program current requirements",
            ]
        )
    )

    decision = decide_source_class_recovery(snapshot)

    assert decision.decision is (
        SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
    )
    assert decision.to_dict()["decision"] == "run_source_class_recovery"
    assert decision.reason == "missing_expected_source_class:official_current_rules"
    assert decision.blockers == ()
    assert decision.queries == (
        "Care Program official rules",
        "Care Program current requirements",
    )
    assert decision.provider_role == "source_class_recovery"
    assert decision.search_depth == "basic"
    assert decision.attempt_count == 1
    assert decision.action_envelope is not None
    assert decision.action_envelope.to_dict()["action_type"] == (
        "recover_missing_source_class"
    )
    assert decision.action_envelope.to_dict()["allowed_action"] is True
    assert decision.action_envelope.to_dict()["required_source_class"] == [
        "official_current_rules"
    ]

    snapshot_payload = snapshot.to_dict()
    assert snapshot_payload["evidence_signals"] == {
        "source_tier_counts": {"secondary": 2, "unknown": 1},
        "source_domain_counts": {"regionalnews.example": 2},
        "top_source_domains": [{"domain": "regionalnews.example", "count": 2}],
        "unique_source_domain_count": 1,
        "official_evidence_found": False,
    }
    assert "raw_evidence" not in snapshot_payload["evidence_signals"]
    assert "raw_prompt" not in snapshot_payload["evidence_signals"]


def test_controller_returns_no_action_when_source_class_recovery_not_recommended() -> None:
    decision = decide_source_class_recovery(
        _input(recommendation=_recommendation(recommended=False))
    )

    assert decision.decision is SourceClassRecoveryControllerDecision.NO_ACTION
    assert decision.to_dict()["decision"] == "no_action"
    assert decision.reason == "not_recommended"
    assert decision.provider_role is None
    assert decision.search_depth is None
    assert decision.attempt_count == 0


def test_controller_blocks_when_weak_corpus_path_owns_recovery() -> None:
    decision = decide_source_class_recovery(
        _input(
            weak_corpus_recovery_considered=True,
            weak_corpus_recovery_used=True,
        )
    )

    assert decision.decision is (
        SourceClassRecoveryControllerDecision.BLOCKED_WITH_REASON
    )
    assert decision.to_dict()["decision"] == "blocked_with_reason"
    assert decision.reason == "blocked_by_weak_corpus_recovery"
    assert "blocked_by_weak_corpus_recovery" in decision.blockers
    assert decision.provider_role is None
    assert decision.attempt_count == 0


def test_controller_blocks_recovery_without_usable_queries() -> None:
    decision = decide_source_class_recovery(
        _input(
            recommendation=_recommendation(
                recommended=True,
                missing=["official_current_rules"],
                queries=[],
            )
        )
    )

    assert decision.decision is (
        SourceClassRecoveryControllerDecision.BLOCKED_WITH_REASON
    )
    assert decision.reason == "no_recovery_queries"
    assert decision.queries == ()


def test_answer_contract_slot_can_run_when_main_iteration_budget_is_spent() -> None:
    decision = decide_source_class_recovery(
        _input(
            recommendation=_recommendation(
                reason="answer_contract_official_gap:official_current_rules"
            ),
            iteration_budget_available=False,
            answer_contract_source_class_slot_available=True,
        )
    )

    assert decision.decision is (
        SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
    )
    assert decision.reason == "answer_contract_official_gap:official_current_rules"
    assert "blocked_by_iteration_budget" not in decision.blockers
    assert decision.provider_role == "source_class_recovery"
    assert decision.search_depth == "basic"
    assert decision.attempt_count == 1


def test_answer_contract_budget_exhaustion_still_blocks_without_recovery_slot() -> None:
    decision = decide_source_class_recovery(
        _input(
            recommendation=_recommendation(
                reason="answer_contract_official_gap:official_current_rules"
            ),
            iteration_budget_available=False,
            answer_contract_source_class_slot_available=False,
        )
    )

    assert decision.decision is (
        SourceClassRecoveryControllerDecision.BLOCKED_WITH_REASON
    )
    assert decision.reason == "blocked_by_iteration_budget"
    assert "blocked_by_iteration_budget" in decision.blockers


def test_official_authority_queries_survive_active_recovery_query_cap() -> None:
    decision = decide_source_class_recovery(
        _input(
            recommendation=_recommendation(
                queries=[
                    "IRS standard mileage rate official documentation reference manual",
                    "IRS standard mileage rate official current source",
                    (
                        "IRS 2026 standard mileage rate business official notice "
                        "revenue procedure"
                    ),
                ],
            )
            | {"source_class_recovery_official_domains": ["irs.gov"]},
            iteration_budget_available=False,
            official_canonical_source_class_slot_available=True,
        )
    )

    assert decision.decision is (
        SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY
    )
    assert decision.queries[0] == (
        "IRS 2026 standard mileage rate business official notice revenue procedure"
    )
    assert len(decision.queries) == 2
    assert "blocked_by_iteration_budget" not in decision.blockers


def test_generic_source_class_gap_cannot_use_answer_contract_slot() -> None:
    decision = decide_source_class_recovery(
        _input(
            recommendation=_recommendation(),
            iteration_budget_available=False,
            answer_contract_source_class_slot_available=True,
        )
    )

    assert decision.decision is (
        SourceClassRecoveryControllerDecision.BLOCKED_WITH_REASON
    )
    assert decision.reason == "blocked_by_iteration_budget"
    assert "blocked_by_iteration_budget" in decision.blockers


def test_source_class_recovery_controller_static_import_guard() -> None:
    tree = ast.parse(_CONTROLLER_PATH.read_text(encoding="utf-8"))
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
        "core.routing",
        "core.scout",
        "core.weak_corpus_controller",
        "core.weak_corpus_recovery",
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

    assert violations == []
