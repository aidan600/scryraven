from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.controller_action_envelope import (
    HANDOFF_TO_ANALYST,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RETRIEVE_TARGETED,
    RUN_SCRUTINEER_REVIEW,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    ControllerActionAuthority,
)
from core.controller_action_loop_parity import (
    ACTIVE_RETRIEVAL_STOP_CONTINUE_GAP,
    ACTIVE_STOP_SUFFICIENT_GAP,
    ControllerActionLoopParityFacts,
    ControllerActionLoopParityStatus,
    replay_offline_controller_action_loop,
)
from core.controller_runtime_promotion_readiness import (
    TERMINAL_STOP_ALLOWED_STATE_FIELDS,
    assess_runtime_promotion_candidate,
    runtime_promotion_readiness_matrix,
)
from core.controller_state_reducer import (
    ControllerBudgetClass,
    ControllerEvidenceBoundary,
    ControllerStateSnapshot,
    reduce_controller_state,
)
from core.retrieval_stop_controller import build_retrieval_stop_controller_input

_ROOT = Path(__file__).resolve().parents[1]
_READINESS_PATH = _ROOT / "core" / "controller_runtime_promotion_readiness.py"


def _terminal_stop_cases() -> tuple[tuple[str, Any], ...]:
    return (
        (
            "terminal_no_query",
            ControllerActionLoopParityFacts(
                retrieval_stop_snapshot=build_retrieval_stop_controller_input(
                    evaluator_sufficient=False,
                    iteration=1,
                    max_iterations=3,
                    prior_queries=("Acme status",),
                    next_queries=(),
                    query_source="evaluator",
                ),
                retrieval_stop_authority=ControllerActionAuthority.ACTIVE,
                retrieval_stop_stage="evaluator_no_queries",
                retrieval_stop_mode="active_stop_no_queries",
            ),
        ),
        (
            "terminal_budget_exhausted",
            ControllerActionLoopParityFacts(
                retrieval_stop_snapshot=build_retrieval_stop_controller_input(
                    evaluator_sufficient=False,
                    iteration=3,
                    max_iterations=3,
                    prior_queries=("Acme status",),
                    next_queries=("Acme official follow-up",),
                    query_source="evaluator",
                ),
                retrieval_stop_authority=ControllerActionAuthority.ACTIVE,
                retrieval_stop_stage="iteration_budget_exhausted",
                retrieval_stop_mode="active_stop_budget_exhausted",
            ),
        ),
    )


def test_terminal_stop_readiness_candidate_is_only_plausible_first_candidate() -> None:
    matrix = runtime_promotion_readiness_matrix()
    candidate = matrix[STOP_INSUFFICIENT_WITH_CAVEAT]

    assert candidate["plausible_first_promotion_candidate"] is True
    assert candidate["assessment"] == "readiness_gate_candidate_not_promoted"
    assert candidate["required_parity_scenarios"] == [
        "terminal_no_query",
        "terminal_budget_exhausted",
    ]
    assert candidate["runtime_behavior_changed"] is False
    assert "runtime_promotion_not_in_scope_ag28" in candidate["blockers"]

    blocked_actions = {
        RETRIEVE_TARGETED,
        STOP_SUFFICIENT,
        RECOVER_WEAK_CORPUS,
        RECOVER_MISSING_SOURCE_CLASS,
        REQUEST_SOCIAL_SIGNAL_CHECK,
    }
    assert blocked_actions <= set(matrix)
    assert all(
        matrix[action]["plausible_first_promotion_candidate"] is False
        for action in blocked_actions
    )
    assert matrix[RETRIEVE_TARGETED]["blockers"] == [
        "requires_retrieval_continuation_authority",
        "would_dispatch_queries",
        "provider_depth_ranking_policy_remains_runtime_owned",
    ]
    assert "weak_corpus_executor_not_factored_out" in matrix[RECOVER_WEAK_CORPUS][
        "blockers"
    ]
    assert "official_legal_quality_gap_remains" in matrix[
        RECOVER_MISSING_SOURCE_CLASS
    ]["blockers"]
    assert "future_placeholder_no_provider_integration" in matrix[
        REQUEST_SOCIAL_SIGNAL_CHECK
    ]["blockers"]


def test_terminal_no_query_and_budget_exhausted_replay_and_reduce_posture_only() -> None:
    readiness = assess_runtime_promotion_candidate(STOP_INSUFFICIENT_WITH_CAVEAT)
    assert readiness.plausible_first_promotion_candidate is True

    for scenario, facts in _terminal_stop_cases():
        parity = replay_offline_controller_action_loop(facts)
        envelope = parity.envelopes[0].to_dict()
        reduced = reduce_controller_state(ControllerStateSnapshot(), parity.envelopes)
        payload = reduced.to_dict()
        after = payload["after"]

        assert parity.status is ControllerActionLoopParityStatus.REPLAYED
        assert parity.gaps == ()
        assert envelope["name"] == STOP_INSUFFICIENT_WITH_CAVEAT
        assert envelope["status"] == "completed"
        assert envelope["authority"] == "active"
        assert envelope["side_effect_class"] == "stop"
        assert envelope["handoff_boundary"] == "final_answer_posture_only"
        assert envelope["approved_work"] == {}
        assert envelope["metadata"]["controller_decision"] in {
            "stop_no_queries",
            "stop_budget_exhausted",
        }
        assert envelope["input_summary"]["stage"] == facts.retrieval_stop_stage
        assert scenario in readiness.required_parity_scenarios

        assert after["stopped"] is True
        assert after["final_answer_posture"] == "answer with caveats"
        assert after["pending_queries"] == []
        assert after["ordinary_evidence_action_names"] == []
        assert after["ordinary_evidence_candidate_count"] == 0
        assert after["official_legal_current_primary_action_names"] == []
        assert after["social_side_packet_action_names"] == []
        assert after["sanitized_handoff_action_names"] == []
        assert ControllerBudgetClass.LIVE_CALL.value not in after["budget_counters"]
        assert (
            ControllerBudgetClass.RETRIEVAL_ITERATION.value
            not in after["budget_counters"]
        )
        assert set(payload["state_delta"]) <= set(TERMINAL_STOP_ALLOWED_STATE_FIELDS)
        assert payload["metadata"]["runtime_behavior_changed"] is False
        assert payload["metadata"]["controller_drives_runtime"] is False
        assert json.loads(json.dumps(payload, sort_keys=True)) == payload


def test_terminal_stop_evidence_boundaries_exclude_evidence_and_handoffs() -> None:
    for _scenario, facts in _terminal_stop_cases():
        parity = replay_offline_controller_action_loop(facts)
        reduced = reduce_controller_state(
            ControllerStateSnapshot(
                sanitized_handoff_action_names=(
                    HANDOFF_TO_ANALYST,
                    RUN_SCRUTINEER_REVIEW,
                ),
                metadata={"handoff_contract": "preserve"},
            ),
            parity.envelopes,
        )
        payload = reduced.to_dict()
        after = payload["after"]
        assertions = payload["evidence_boundary_assertions"]

        by_boundary = {item["boundary"]: item for item in assertions}
        assert by_boundary[
            ControllerEvidenceBoundary.ORDINARY_EVIDENCE_ELIGIBILITY.value
        ]["allowed"] is False
        assert by_boundary[
            ControllerEvidenceBoundary.OFFICIAL_LEGAL_CURRENT_PRIMARY_EVIDENCE.value
        ]["allowed"] is False
        assert by_boundary[
            ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE.value
        ]["allowed"] is False
        assert by_boundary[
            ControllerEvidenceBoundary.FINAL_ANSWER_POSTURE_ONLY.value
        ]["allowed"] is True
        assert by_boundary[
            ControllerEvidenceBoundary.SANITIZED_HANDOFF_ONLY.value
        ]["allowed"] is False

        assert after["sanitized_handoff_action_names"] == [
            HANDOFF_TO_ANALYST,
            RUN_SCRUTINEER_REVIEW,
        ]
        assert after["metadata"]["handoff_contract"] == "preserve"
        encoded = json.dumps(payload, sort_keys=True)
        for protected_marker in (
            "Analyst prompt",
            "Economist packet",
            "Author handoff",
            "Scrutineer rewrite",
            "provider_payload",
            "raw_prompt",
        ):
            assert protected_marker not in encoded


def test_retrieve_targeted_and_stop_sufficient_are_negative_promotion_controls() -> None:
    continue_result = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            retrieval_stop_snapshot=build_retrieval_stop_controller_input(
                evaluator_sufficient=False,
                iteration=1,
                max_iterations=3,
                prior_queries=("Acme status",),
                next_queries=("Acme official update",),
                query_source="evaluator",
            ),
            retrieval_stop_authority=ControllerActionAuthority.ACTIVE,
        )
    )
    sufficient_result = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            retrieval_stop_snapshot=build_retrieval_stop_controller_input(
                evaluator_sufficient=True,
                iteration=1,
                max_iterations=3,
                next_queries=(),
            ),
            retrieval_stop_authority=ControllerActionAuthority.ACTIVE,
        )
    )

    assert continue_result.gaps[0].code == ACTIVE_RETRIEVAL_STOP_CONTINUE_GAP
    assert continue_result.gaps[0].action_name == RETRIEVE_TARGETED
    assert continue_result.gaps[0].blocks_runtime_promotion is True
    assert continue_result.envelopes[0].to_dict()["name"] == RETRIEVE_TARGETED
    assert assess_runtime_promotion_candidate(
        RETRIEVE_TARGETED
    ).plausible_first_promotion_candidate is False

    assert sufficient_result.gaps[0].code == ACTIVE_STOP_SUFFICIENT_GAP
    assert sufficient_result.gaps[0].action_name == STOP_SUFFICIENT
    assert sufficient_result.gaps[0].blocks_runtime_promotion is True
    assert sufficient_result.envelopes[0].to_dict()["name"] == STOP_SUFFICIENT
    assert assess_runtime_promotion_candidate(
        STOP_SUFFICIENT
    ).plausible_first_promotion_candidate is False


def test_readiness_helper_static_no_runtime_provider_persistence_prompt_coupling() -> None:
    tree = ast.parse(_READINESS_PATH.read_text(encoding="utf-8"))
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
    source = _READINESS_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
    assert "STOP_INSUFFICIENT_WITH_CAVEAT" in source
