from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.run_controller import RunController
from core.source_class_recovery_lifecycle import (
    ACTIVE_SOURCE_CLASS_RECOVERY_TRACE_FIELDS,
    record_source_class_recovery_lifecycle,
)

_ROOT = Path(__file__).resolve().parents[1]
_LIFECYCLE_HELPER_PATH = _ROOT / "core" / "source_class_recovery_lifecycle.py"


def _recommendation(
    *,
    recommended: bool = True,
    missing: list[str] | None = None,
    queries: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    missing_classes = list(
        missing if missing is not None else ["official_current_rules"]
    )
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
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": missing_classes,
        "source_class_recovery_reason": (
            reason
            if reason is not None
            else "missing_expected_source_class:" + ",".join(missing_classes)
            if recommended
            else None
        ),
        "source_class_recovery_queries": recovery_queries,
        "source_class_recovery_query_count": len(recovery_queries),
        "source_class_recovery_trigger_fields": ["query"],
    }


def _evidence_signals() -> dict[str, Any]:
    return {
        "source_tier_counts": {"secondary": 2, "unknown": 1},
        "source_domain_counts": {"regionalnews.example": 2},
        "top_source_domains": [{"domain": "regionalnews.example", "count": 2}],
        "unique_source_domain_count": 1,
        "on_domain_source_count": 0,
        "off_domain_source_count": 2,
        "official_evidence_found": False,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _record(
    controller: RunController,
    *,
    recommendation: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "recommendation": recommendation if recommendation is not None else _recommendation(),
        "recommendation_evaluated": True,
        "source_class_evidence_signals": _evidence_signals(),
        "corpus_state": "HEALTHY",
        "corpus_weak": False,
        "weak_corpus_recovery_considered": False,
        "weak_corpus_recovery_used": False,
        "weak_corpus_recovery_skip_reason": None,
        "current_search_depth": "basic",
        "iteration_budget_available": True,
    }
    kwargs.update(overrides)
    return record_source_class_recovery_lifecycle(controller, **kwargs)


def test_source_class_recovery_lifecycle_records_active_approved_action() -> None:
    controller = RunController()

    trace = _record(controller)
    ledger = controller.snapshot_ledger()
    state = controller.snapshot_state()

    assert set(trace) == set(ACTIVE_SOURCE_CLASS_RECOVERY_TRACE_FIELDS)
    assert trace["active_source_class_recovery_considered"] is True
    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_reason"] == (
        "missing_expected_source_class:official_current_rules"
    )
    assert trace["active_source_class_recovery_skip_reason"] is None
    assert trace["active_source_class_recovery_blockers"] == []
    assert trace["active_source_class_recovery_missing_classes"] == [
        "official_current_rules"
    ]
    assert trace["active_source_class_recovery_queries"]
    assert trace["active_source_class_recovery_result_count"] == 0
    assert trace["active_source_class_recovery_new_url_count"] == 0
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert trace["active_source_class_recovery_search_depth"] == "basic"
    assert trace["active_source_class_recovery_attempt_count"] == 1
    envelope = trace["active_source_class_recovery_action_envelope"]
    assert envelope["action_type"] == "recover_missing_source_class"
    assert envelope["required_source_class"] == ["official_current_rules"]
    assert envelope["obligation_status"] == "required"
    assert envelope["allowed_action"] is True
    assert envelope["budget_attempt_context"]["provider_role"] == (
        "source_class_recovery"
    )

    assert state["active_source_class_recovery_eligible"] is True
    assert state["active_source_class_recovery_used"] is False
    assert state["active_source_class_recovery_result_count"] == 0
    assert state["corpus"]["metadata"]["source_class_recovery"][
        "missing_expected_source_classes"
    ] == ["official_current_rules"]

    action = ledger["retrieval_actions"][0]
    decision = ledger["decision_records"][0]
    facts = [
        (record["stage"], record["name"], record["value"])
        for record in ledger["fact_records"]
    ]

    assert action["name"] == "source_class_recovery"
    assert action["active"] is True
    assert action["shadow"] is False
    assert action["provider"] is None
    assert action["provider_role"] == "source_class_recovery"
    assert action["search_depth"] == "basic"
    assert action["metadata"]["execution"] == "controller_approved_pending_executor"
    assert action["metadata"]["controller_decision"] == "run_source_class_recovery"
    assert action["metadata"]["controller_action_envelope"] == envelope
    assert decision["name"] == "run_source_class_recovery"
    assert decision["active"] is True
    assert decision["shadow"] is False
    assert decision["metadata"]["execution"] == "minimal_active_controller"
    assert decision["metadata"]["decision"] == "run_source_class_recovery"
    assert decision["recommended_actions"][0]["name"] == "source_class_recovery"
    assert ("source_class_recovery", "skip_reason", None) in facts
    assert ("source_class_recovery", "attempt_count", 1) in facts


def test_source_class_recovery_lifecycle_not_recommended_skips_without_action() -> None:
    controller = RunController()

    trace = _record(
        controller,
        recommendation=_recommendation(recommended=False, missing=[], queries=[]),
    )
    ledger = controller.snapshot_ledger()

    assert trace["active_source_class_recovery_considered"] is True
    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_skip_reason"] == "not_recommended"
    assert trace["active_source_class_recovery_attempt_count"] == 0
    assert ledger["retrieval_actions"] == []
    assert ledger["decision_records"][0]["name"] == "no_action"
    assert ledger["decision_records"][0]["reason"] == "not_recommended"
    assert ledger["fact_records"][0]["value"] == "not_recommended"


def test_source_class_recovery_lifecycle_weak_corpus_blocks_separate_path() -> None:
    controller = RunController()

    trace = _record(
        controller,
        corpus_state="OFF_TOPIC",
        corpus_weak=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=True,
    )

    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_skip_reason"] == (
        "blocked_by_weak_corpus_recovery"
    )
    assert "blocked_by_weak_corpus_recovery" in trace[
        "active_source_class_recovery_blockers"
    ]
    assert controller.snapshot_ledger()["decision_records"][0]["name"] == (
        "blocked_with_reason"
    )
    assert controller.snapshot_ledger()["retrieval_actions"] == []


def test_source_class_recovery_lifecycle_is_idempotent_after_approved_attempt() -> None:
    controller = RunController()

    first = _record(controller)
    second = _record(controller)
    ledger = controller.snapshot_ledger()

    assert first["active_source_class_recovery_eligible"] is True
    assert first["active_source_class_recovery_attempt_count"] == 1
    assert second["active_source_class_recovery_eligible"] is False
    assert second["active_source_class_recovery_skip_reason"] == "already_attempted"
    assert second["active_source_class_recovery_attempt_count"] == 1
    assert [
        action["name"] for action in ledger["retrieval_actions"]
    ] == ["source_class_recovery"]


def test_retrieve_to_anchor_recommendation_blocks_without_renaming_action() -> None:
    controller = RunController()

    trace = _record(controller, retrieve_to_anchor_recommended=True)

    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_skip_reason"] == (
        "blocked_by_retrieve_to_anchor_recommendation"
    )
    assert "blocked_by_retrieve_to_anchor_recommendation" in trace[
        "active_source_class_recovery_blockers"
    ]
    assert controller.snapshot_ledger()["retrieval_actions"] == []


def test_answer_contract_slot_records_action_after_main_iteration_budget() -> None:
    controller = RunController()

    trace = _record(
        controller,
        recommendation=_recommendation(
            reason="answer_contract_legal_text_gap:legal_or_regulatory_text",
            missing=["legal_or_regulatory_text"],
        ),
        iteration_budget_available=False,
        answer_contract_source_class_slot_available=True,
    )

    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_skip_reason"] is None
    assert trace["active_source_class_recovery_reason"] == (
        "answer_contract_legal_text_gap:legal_or_regulatory_text"
    )
    assert trace["active_source_class_recovery_missing_classes"] == [
        "legal_or_regulatory_text"
    ]
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert controller.snapshot_ledger()["retrieval_actions"][0]["provider_role"] == (
        "source_class_recovery"
    )


def test_answer_contract_official_gap_can_override_weak_corpus_once() -> None:
    controller = RunController()

    trace = _record(
        controller,
        recommendation=_recommendation(
            reason="answer_contract_official_gap:official_current_rules"
        ),
        iteration_budget_available=False,
        answer_contract_source_class_slot_available=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=True,
    )

    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_skip_reason"] is None
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert len(controller.snapshot_ledger()["retrieval_actions"]) == 1


def test_source_class_recovery_lifecycle_static_import_guard() -> None:
    tree = ast.parse(_LIFECYCLE_HELPER_PATH.read_text(encoding="utf-8"))
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
    forbidden_terms = (
        "process_search_queries",
        "select_providers",
        "ask_model",
        "append_jsonl",
        "insert_run",
        "upsert_session",
        "build_source_class_recovery_recommendation",
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

    source = _LIFECYCLE_HELPER_PATH.read_text(encoding="utf-8")
    assert violations == []
    assert all(term not in source for term in forbidden_terms)
