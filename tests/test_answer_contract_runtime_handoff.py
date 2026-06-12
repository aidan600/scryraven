from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.answer_contract_controller import (
    AnswerContractFamily,
    AnswerControllerActionName,
)
from core.answer_contract_runtime_handoff import (
    ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY,
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
    retrieval_stop_decision_from_runtime_trace,
    source_class_recovery_decision_from_runtime_trace,
)
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.evidence_integration_checkpoint import EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
from core.retrieval_stop_controller import RetrievalStopControllerDecision
from core.run_controller import RunController
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
)
from tests.test_source_class_recovery_trace import _run_case

_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME_HANDOFF_PATH = _ROOT / "core" / "answer_contract_runtime_handoff.py"


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


def _recommendation(
    *,
    recommended: bool = True,
    missing: list[str] | None = None,
    queries: list[str] | None = None,
) -> dict[str, Any]:
    missing_classes = list(missing if missing is not None else ["official_current_rules"])
    recovery_queries = list(
        queries
        if queries is not None
        else [
            "Care Program official current rules",
            "Care Program official eligibility requirements",
        ]
    )
    return {
        "source_class_recovery_recommended": recommended,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": missing_classes if recommended else [],
        "source_class_recovery_reason": (
            "missing_expected_source_class:" + ",".join(missing_classes)
            if recommended
            else None
        ),
        "source_class_recovery_queries": recovery_queries if recommended else [],
        "source_class_recovery_query_count": len(recovery_queries) if recommended else 0,
        "source_class_recovery_trigger_fields": ["query"] if recommended else [],
    }


def _evidence_signals(*, official: bool = False) -> dict[str, Any]:
    return {
        "source_tier_counts": (
            {"official": 1, "secondary": 1} if official else {"secondary": 2}
        ),
        "source_domain_counts": (
            {"official.gov": 1, "analysis.example": 1}
            if official
            else {"analysis.example": 2}
        ),
        "top_source_domains": [{"domain": "analysis.example", "count": 2}],
        "unique_source_domain_count": 1,
        "on_domain_source_count": 0,
        "off_domain_source_count": 2,
        "official_evidence_found": official,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _lifecycle(
    *,
    recommendation: dict[str, Any] | None = None,
    corpus_state: str = "HEALTHY",
    corpus_weak: bool = False,
    weak_corpus_recovery_considered: bool = False,
    weak_corpus_recovery_used: bool = False,
    weak_corpus_recovery_skip_reason: str | None = None,
) -> dict[str, Any]:
    return record_source_class_recovery_lifecycle(
        RunController(),
        recommendation=recommendation if recommendation is not None else _recommendation(),
        recommendation_evaluated=True,
        source_class_evidence_signals=_evidence_signals(official=False),
        corpus_state=corpus_state,
        corpus_weak=corpus_weak,
        weak_corpus_recovery_considered=weak_corpus_recovery_considered,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=weak_corpus_recovery_skip_reason,
        current_search_depth="basic",
        iteration_budget_available=True,
    )


def _base_facts(**overrides: Any) -> RuntimeAnswerContractFacts:
    values: dict[str, Any] = {
        "query": "What are the current official rules for Care Program eligibility?",
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "mode": "Balanced",
        "current_date": "2026-05-21",
        "core_topic": "Care Program eligibility",
        "evidence_available": True,
        "evidence_sufficient": False,
        "source_tier_counts": {"secondary": 2},
        "source_class_recovery_telemetry": _recommendation(),
        "active_source_class_recovery_lifecycle": _lifecycle(),
        "queries_by_iteration": {"1": ["Care Program eligibility"]},
        "final_top_evidence": (
            {
                "source_id": 1,
                "title": "Care Program secondary explainer",
                "url": "https://analysis.example/care",
                "text": "Raw excerpt is deliberately not copied into the handoff.",
                "source_tier": "secondary",
            },
        ),
    }
    values.update(overrides)
    return RuntimeAnswerContractFacts(**values)


def _handoff_payload(facts: RuntimeAnswerContractFacts) -> dict[str, Any]:
    result = build_runtime_answer_contract_handoff(facts)
    return result.execution_trace_fragment()[ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY]


def test_runtime_facts_map_official_gap_to_fulfillment_and_source_class_action() -> None:
    result = build_runtime_answer_contract_handoff(_base_facts())
    payload = result.execution_trace_fragment()[ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY]

    assert result.adapter_result.contract.family is AnswerContractFamily.CURRENT_OFFICIAL_RULES
    assert "official_current_rules" in result.state.evidence_state_summary.source_classes_missing
    assert "official_current_rules" in payload["unfulfilled_items"]
    assert payload["actions_taken"][0]["action_name"] == (
        AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS.value
    )
    assert payload["actions_taken"][0]["stable_reason_code"] == (
        "missing_required_source_class"
    )


def test_runtime_official_source_satisfied_has_no_approved_recovery() -> None:
    recommendation = _recommendation(recommended=False, missing=[], queries=[])
    payload = _handoff_payload(
        _base_facts(
            evidence_sufficient=True,
            source_tier_counts={"official": 1, "secondary": 1},
            source_class_recovery_telemetry=recommendation,
            active_source_class_recovery_lifecycle=_lifecycle(
                recommendation=recommendation
            ),
            final_top_evidence=(
                {
                    "source_id": 1,
                    "title": "Care Program official rules",
                    "url": "https://official.gov/care",
                    "source_tier": "official",
                },
            ),
        )
    )

    assert payload["unfulfilled_items"] == []
    assert all(
        action["action_name"] != AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS.value
        for action in payload["actions_taken"]
    )
    assert payload["actions_skipped_and_why"][0]["stable_reason_code"] == (
        "not_recommended"
    )


def test_runtime_conceptual_sufficient_stops_without_recovery_or_scrutineer() -> None:
    result = build_runtime_answer_contract_handoff(
        _base_facts(
            query="Explain how TCP congestion control works.",
            query_type="concept",
            core_topic="TCP congestion control",
            evidence_sufficient=True,
            source_class_recovery_telemetry={},
            active_source_class_recovery_lifecycle={},
            retrieval_stop_shadow_telemetry={
                "retrieval_stop_shadow_available": True,
                "retrieval_stop_shadow_decision": "proceed_to_synthesis",
                "retrieval_stop_shadow_reason": "evaluator_sufficient",
                "retrieval_stop_shadow_blockers": [],
            },
        )
    )
    payload = result.execution_trace_fragment()[ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY]

    assert result.adapter_result.contract.family is AnswerContractFamily.CONCEPTUAL_EXPLAINER
    assert payload["unfulfilled_items"] == []
    assert payload["actions_taken"][0]["action_name"] == (
        AnswerControllerActionName.STOP_SUFFICIENT.value
    )
    action_names = {
        action["action_name"]
        for action in payload["actions_taken"] + payload["actions_skipped_and_why"]
    }
    assert AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS.value not in action_names
    assert AnswerControllerActionName.RECOVER_WEAK_CORPUS.value not in action_names
    assert AnswerControllerActionName.RUN_SCRUTINEER_REVIEW.value not in action_names
    assert payload["social_signal_summary"] is None


def test_runtime_weak_corpus_ownership_stays_separate_from_source_class_pilot() -> None:
    payload = _handoff_payload(
        _base_facts(
            weak_corpus=True,
            weak_corpus_reason="weak first pass",
            weak_corpus_recovery_considered=True,
            weak_corpus_recovery_used=True,
            source_class_recovery_telemetry=_recommendation(),
            active_source_class_recovery_lifecycle=_lifecycle(
                corpus_state="OFF_TOPIC",
                corpus_weak=True,
                weak_corpus_recovery_considered=True,
                weak_corpus_recovery_used=True,
            ),
        )
    )
    action_names = {
        action["action_name"]
        for action in payload["actions_taken"] + payload["actions_skipped_and_why"]
    }

    assert AnswerControllerActionName.RECOVER_WEAK_CORPUS.value not in action_names
    assert payload["actions_skipped_and_why"][0]["action_name"] == (
        AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS.value
    )
    assert payload["actions_skipped_and_why"][0]["stable_reason_code"] == (
        "blocked_by_weak_corpus_recovery"
    )
    assert payload["actions_taken"] == []


def test_source_class_runtime_decision_preserves_lifecycle_parity() -> None:
    recommendation = _recommendation(
        queries=[
            "Care Program official current rules",
            "Care Program official current rules",
            "Care Program official requirements",
        ]
    )
    lifecycle = _lifecycle(recommendation=recommendation)

    decision = source_class_recovery_decision_from_runtime_trace(
        source_class_recovery_telemetry=recommendation,
        active_source_class_recovery_lifecycle=lifecycle,
    )

    assert decision is not None
    assert decision.to_dict() == {
        "decision": "run_source_class_recovery",
        "reason": "missing_expected_source_class:official_current_rules",
        "blockers": [],
        "missing_expected_source_classes": ["official_current_rules"],
        "queries": [
            "Care Program official current rules",
            "Care Program official requirements",
        ],
        "provider_role": "source_class_recovery",
        "search_depth": "basic",
        "attempt_count": 1,
    }


def test_retrieval_stop_runtime_mapping_reuses_existing_decision_vocabulary() -> None:
    decision = retrieval_stop_decision_from_runtime_trace(
        retrieval_stop_active_telemetry={
            "retrieval_stop_active_available": True,
            "retrieval_stop_active_decision": "stop_no_queries",
            "retrieval_stop_active_reason": "no_new_queries",
            "retrieval_stop_active_blockers": ["no_new_queries"],
        },
        retrieval_stop_shadow_telemetry={
            "retrieval_stop_shadow_available": True,
            "retrieval_stop_shadow_decision": "continue_retrieval",
        },
    )

    assert decision is not None
    assert decision.decision is RetrievalStopControllerDecision.STOP_NO_QUERIES
    assert decision.to_dict() == {
        "decision": "stop_no_queries",
        "reason": "no_new_queries",
        "blockers": ["no_new_queries"],
        "next_queries": [],
        "query_source": None,
        "redundancy_score": None,
    }


def test_ag30_active_terminal_stop_handoff_exposes_only_stop_posture() -> None:
    payload = _handoff_payload(
        _base_facts(
            evidence_sufficient=False,
            source_class_recovery_telemetry={},
            active_source_class_recovery_lifecycle={},
            retrieval_stop_active_telemetry={
                "retrieval_stop_active_available": True,
                "retrieval_stop_active_action_name": "stop_insufficient_with_caveat",
                "retrieval_stop_active_authority": "active",
                "retrieval_stop_active_decision": "stop_budget_exhausted",
                "retrieval_stop_active_reason": "iteration_budget_exhausted",
                "retrieval_stop_active_blockers": ["iteration_budget_exhausted"],
                "retrieval_stop_active_next_query_count": 2,
                "retrieval_stop_active_approved_query_count": 0,
                "retrieval_stop_active_stage": "iteration_budget_exhausted",
                "retrieval_stop_active_mode": "active_stop_budget_exhausted",
                "retrieval_stop_active_ag28_candidate": (
                    "ag28:stop_insufficient_with_caveat:"
                    "terminal_no_query_or_budget_exhausted"
                ),
            },
            retrieval_stop_shadow_telemetry={
                "retrieval_stop_shadow_available": True,
                "retrieval_stop_shadow_decision": "stop_budget_exhausted",
            },
        )
    )

    stop_actions = [
        action
        for action in payload["actions_taken"]
        if action["action_name"]
        == AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT.value
    ]
    assert len(stop_actions) == 1
    assert "approved_query_count" not in stop_actions[0]
    assert payload["stop_reason"] == "no_useful_new_query"
    assert payload["final_answer_posture"] == "answer with caveats"

    encoded = json.dumps(payload, sort_keys=True)
    for marker in (
        "retrieval_stop_active",
        "active_stop_budget_exhausted",
        "active",
        "ag28:",
        "approved_query_count",
        "retrieval_stop_shadow",
    ):
        assert marker not in encoded


def test_ag30_malformed_active_terminal_stop_handoff_falls_back_to_shadow_safely() -> None:
    raw_marker = "RAW_ACTIVE_TERMINAL_STOP_SHOULD_NOT_LEAK_AG30"
    payload = _handoff_payload(
        _base_facts(
            evidence_sufficient=False,
            source_class_recovery_telemetry={},
            active_source_class_recovery_lifecycle={},
            retrieval_stop_active_telemetry={
                "retrieval_stop_active_available": False,
                "retrieval_stop_active_decision": raw_marker,
                "retrieval_stop_active_reason": raw_marker,
                "retrieval_stop_active_blockers": [raw_marker],
                "retrieval_stop_active_stage": raw_marker,
                "retrieval_stop_active_mode": raw_marker,
                "retrieval_stop_active_fallback_reason": raw_marker,
            },
            retrieval_stop_shadow_telemetry={
                "retrieval_stop_shadow_available": True,
                "retrieval_stop_shadow_decision": "stop_no_queries",
                "retrieval_stop_shadow_reason": "no_new_queries",
                "retrieval_stop_shadow_blockers": ["no_new_queries"],
            },
        )
    )

    assert any(
        action["action_name"]
        == AnswerControllerActionName.STOP_INSUFFICIENT_WITH_CAVEAT.value
        for action in payload["actions_taken"]
    )
    encoded = json.dumps(payload, sort_keys=True)
    assert raw_marker not in encoded
    assert "retrieval_stop_active" not in encoded


def test_runtime_handoff_redacts_raw_protected_material() -> None:
    payload = _handoff_payload(
        _base_facts(
            final_top_evidence=(
                {
                    "source_id": 1,
                    "title": "provider_diagnostics raw prompt source",
                    "url": "https://analysis.example/raw",
                    "text": "quantitative_packet economist_v1 raw evidence dump",
                    "source_tier": "secondary",
                },
            ),
            warnings_to_analyst_or_author=(
                "Do not expose ECONOMIST FRAMEWORK or quantitative_packet internals.",
            ),
        )
    )
    encoded = json.dumps(payload, sort_keys=True)

    for marker in (
        "quantitative_packet",
        "economist_v1",
        "ECONOMIST FRAMEWORK",
        "provider_diagnostics",
        "raw prompt",
        "raw evidence dump",
    ):
        assert marker not in encoded
        assert marker.lower() not in encoded.lower()
    assert "[redacted protected material]" in encoded


def test_pipeline_runtime_handoff_trace_preserves_active_gate_visibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_outcome, active_harness, active_log = _run_case(
        tmp_path / "active",
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    class _NoopHandoff:
        def execution_trace_fragment(self) -> dict[str, Any]:
            return {}

    def disabled_handoff(*_args: Any, **_kwargs: Any) -> _NoopHandoff:
        return _NoopHandoff()

    monkeypatch.setattr(
        orchestrator,
        "build_runtime_answer_contract_handoff",
        disabled_handoff,
    )
    baseline_outcome, baseline_harness, baseline_log = _run_case(
        tmp_path / "baseline",
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY in active_outcome.execution_trace
    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY in active_log["execution_trace"]
    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY not in baseline_outcome.execution_trace
    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY not in baseline_log["execution_trace"]
    assert [call["provider_role"] for call in active_harness.search_calls] == [
        "main_retrieval",
        "source_class_recovery",
    ]
    assert [call["provider_role"] for call in baseline_harness.search_calls] == [
        "main_retrieval",
        "source_class_recovery",
    ]
    assert execution_jsonl_to_run_row(active_log) is not None
    assert set(execution_jsonl_to_run_row(active_log) or {}) == set(RUN_COLUMNS)
    assert ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY not in (
        execution_jsonl_to_run_row(active_log) or {}
    )

    handoff = active_outcome.execution_trace[ANSWER_CONTRACT_RUNTIME_HANDOFF_TRACE_KEY]
    assert handoff["schema_version"] == "answer_contract_fulfillment_v1"
    assert any(
        action["action_name"] == AnswerControllerActionName.RECOVER_MISSING_SOURCE_CLASS.value
        for action in handoff["actions_taken"]
    )
    active_gate = active_outcome.execution_trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]
    baseline_gate = baseline_outcome.execution_trace[
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY
    ]
    assert active_gate["controller_gate_active"] is True
    assert active_gate["executor_dispatched"] is True
    assert active_gate["runtime_behavior_changed"] is True
    assert baseline_gate["controller_gate_active"] is True
    assert baseline_gate["available"] is False
    assert baseline_gate["executor_dispatched"] is False
    assert baseline_gate["gate_reason"] == "checkpoint_unavailable"
    assert_execution_trace_payload_contract(active_outcome.execution_trace)
    assert_execution_trace_payload_contract(active_log["execution_trace"])


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_runtime_handoff_static_import_guard() -> None:
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
        "build_source_class_recovery_recommendation",
        "execute_source_class_recovery_action",
        "choose_retrieval_search_depth",
        "DEFAULT_SYSTEM",
    )

    violations = [
        name
        for name in _imported_names(_RUNTIME_HANDOFF_PATH)
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    source = _RUNTIME_HANDOFF_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
