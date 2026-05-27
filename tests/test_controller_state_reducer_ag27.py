from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.answer_contract_controller import (
    AnswerControllerActionName,
    AnswerControllerActionResult,
)
from core.controller_action_envelope import (
    HANDOFF_TO_ANALYST,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RETRIEVE_TARGETED,
    RUN_SCRUTINEER_REVIEW,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    ControllerActionAuthority,
    envelope_from_answer_contract_action_result,
    social_signal_placeholder_envelope,
)
from core.controller_action_loop_parity import (
    ControllerActionLoopParityFacts,
    replay_offline_controller_action_loop,
)
from core.controller_state_reducer import (
    ControllerBudgetClass,
    ControllerEvidenceBoundary,
    ControllerExecutorMode,
    ControllerStateSnapshot,
    controller_budget_descriptors,
    controller_evidence_boundary_descriptors,
    controller_executor_descriptors,
    reduce_controller_state,
)
from core.retrieval_stop_controller import build_retrieval_stop_controller_input
from core.source_class_recovery_controller import (
    build_source_class_recovery_controller_input,
)
from core.source_class_recovery_diagnostics import (
    build_source_class_recovery_validation_packet,
)
from core.weak_corpus_controller import build_weak_corpus_recovery_controller_input

_ROOT = Path(__file__).resolve().parents[1]
_REDUCER_PATH = _ROOT / "core" / "controller_state_reducer.py"


def _weak_snapshot() -> Any:
    return build_weak_corpus_recovery_controller_input(
        corpus_state="OFF_TOPIC",
        corpus_weak=True,
        iteration=1,
        max_iterations=2,
        prior_attempted=False,
        readable_passage_count=2,
        recovery_queries=("Acme independent confirmation",),
    )


def _source_recommendation(
    *,
    missing: tuple[str, ...] = ("reputable_reviews",),
    query: str = "Acme expert review source",
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": list(missing),
        "source_class_recovery_queries": [query],
        "source_class_recovery_reason": (
            reason
            if reason is not None
            else "missing_expected_source_class:" + ",".join(missing)
        ),
    }


def _source_snapshot(
    *,
    missing: tuple[str, ...] = ("reputable_reviews",),
    reason: str | None = None,
    iteration_budget_available: bool = True,
    answer_contract_source_class_slot_available: bool = False,
) -> Any:
    return build_source_class_recovery_controller_input(
        recommendation=_source_recommendation(missing=missing, reason=reason),
        recommendation_evaluated=True,
        source_class_evidence_signals={
            "source_tier_counts": {"secondary": 2},
            "source_domain_counts": {"analysis.example": 2},
            "top_source_domains": [{"domain": "analysis.example", "count": 2}],
            "unique_source_domain_count": 1,
            "official_evidence_found": False,
        },
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=iteration_budget_available,
        prior_attempt_count=0,
        answer_contract_source_class_slot_available=(
            answer_contract_source_class_slot_available
        ),
    )


def _l1_trace() -> dict[str, object]:
    return {
        "source_class_recovery_recommended": True,
        "active_source_class_recovery_considered": True,
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_reason": (
            "answer_contract_legal_text_gap:legal_or_regulatory_text"
        ),
        "active_source_class_recovery_missing_classes": [
            "legal_or_regulatory_text"
        ],
        "active_source_class_recovery_queries": [
            "Care Program official legal requirements current text site:ecfr.gov"
        ],
        "source_class_recovery_official_domains": [
            "ecfr.gov",
            "federalregister.gov",
        ],
        "provider_diagnostics": [
            {
                "provider": "tavily",
                "provider_role": "source_class_recovery",
                "depth": "basic",
                "max_results": 6,
                "query_count": 1,
                "success": True,
                "result_count": 1,
                "new_url_count": 1,
                "accepted_url_count": 1,
            }
        ],
        "recovered_accepted_url_count": 1,
        "recovered_source_class_counts": {"legal_or_regulatory_text": 1},
        "recovered_official_or_primary_count": 1,
        "recovery_source_quality_status": "official_or_primary_found",
        "final_answer_source_ids_used": [],
    }


def test_reducer_contract_descriptors_cover_actions_budgets_and_boundaries() -> None:
    executors = controller_executor_descriptors()
    budgets = controller_budget_descriptors()
    boundaries = controller_evidence_boundary_descriptors()

    assert executors[RECOVER_WEAK_CORPUS]["executor_mode"] == (
        ControllerExecutorMode.ACTIVE_RUNTIME_OWNED.value
    )
    assert executors[STOP_INSUFFICIENT_WITH_CAVEAT]["executor_mode"] == (
        ControllerExecutorMode.ACTIVE_TERMINAL_RUNTIME_OWNED.value
    )
    assert executors[REQUEST_SOCIAL_SIGNAL_CHECK]["executor_mode"] == (
        ControllerExecutorMode.FUTURE_PLACEHOLDER.value
    )
    assert executors[RUN_SCRUTINEER_REVIEW]["executor_mode"] == (
        ControllerExecutorMode.PASSIVE_DESCRIPTOR.value
    )
    assert {item.value for item in ControllerBudgetClass} <= set(budgets)
    assert budgets[ControllerBudgetClass.LIVE_CALL.value]["limit_source"] == (
        "always zero in this offline reducer"
    )
    assert {
        item.value for item in ControllerEvidenceBoundary
    } <= set(boundaries)
    assert REQUEST_SOCIAL_SIGNAL_CHECK in boundaries[
        ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE.value
    ]["allowed_actions"]
    assert boundaries[
        ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE.value
    ]["ordinary_evidence_registry_merge_allowed"] is False


def test_ag26_replay_envelopes_reduce_to_expected_offline_state() -> None:
    parity = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            weak_corpus_snapshot=_weak_snapshot(),
            source_class_snapshot=_source_snapshot(),
            retrieval_stop_snapshot=build_retrieval_stop_controller_input(
                evaluator_sufficient=False,
                iteration=2,
                max_iterations=3,
                prior_queries=("Acme status",),
                next_queries=(),
                query_source="evaluator",
            ),
            retrieval_stop_authority=ControllerActionAuthority.ACTIVE,
            retrieval_stop_stage="evaluator_no_queries",
            retrieval_stop_mode="active_stop_no_queries",
        )
    )

    reduced = reduce_controller_state(
        ControllerStateSnapshot(iteration=1),
        parity.envelopes,
    )
    after = reduced.to_dict()["after"]

    assert [item["name"] for item in after["action_history"]] == [
        RECOVER_WEAK_CORPUS,
        RECOVER_MISSING_SOURCE_CLASS,
        STOP_INSUFFICIENT_WITH_CAVEAT,
    ]
    assert after["recovery_attempts"] == {
        RECOVER_MISSING_SOURCE_CLASS: 1,
        RECOVER_WEAK_CORPUS: 1,
    }
    assert after["budget_counters"][
        ControllerBudgetClass.WEAK_CORPUS_RECOVERY.value
    ] == 1
    assert after["budget_counters"][
        ControllerBudgetClass.SOURCE_CLASS_RECOVERY.value
    ] == 1
    assert after["ordinary_evidence_action_names"] == [
        RECOVER_WEAK_CORPUS,
        RECOVER_MISSING_SOURCE_CLASS,
    ]
    assert after["ordinary_evidence_candidate_count"] == 2
    assert after["pending_queries"] == [
        "Acme independent confirmation",
        "Acme expert review source",
    ]
    assert after["stopped"] is True
    assert after["final_answer_posture"] == "answer with caveats"
    assert reduced.to_dict()["metadata"]["runtime_behavior_changed"] is False
    assert json.loads(json.dumps(reduced.to_dict(), sort_keys=True)) == reduced.to_dict()


def test_retrieve_targeted_passive_action_reduces_budget_and_queries() -> None:
    envelope = envelope_from_answer_contract_action_result(
        AnswerControllerActionResult(
            action_name=AnswerControllerActionName.RETRIEVE_TARGETED,
            reason="A targeted query is available.",
            preconditions=("targeted_query_available",),
            approved_queries_or_none=("Acme official rollout facts",),
            stable_reason_code="targeted_query_available",
            iteration=2,
        )
    )

    reduced = reduce_controller_state(ControllerStateSnapshot(), (envelope,))
    after = reduced.to_dict()["after"]

    assert after["action_history"][0]["name"] == RETRIEVE_TARGETED
    assert after["budget_counters"][
        ControllerBudgetClass.RETRIEVAL_ITERATION.value
    ] == 1
    assert after["pending_queries"] == ["Acme official rollout facts"]
    assert after["ordinary_evidence_action_names"] == [RETRIEVE_TARGETED]


def test_social_placeholder_reduces_only_to_side_packet_boundary() -> None:
    reduced = reduce_controller_state(
        ControllerStateSnapshot(),
        (social_signal_placeholder_envelope(metadata={"raw_packet": "blocked"}),),
    )
    payload = reduced.to_dict()
    after = payload["after"]
    encoded = json.dumps(payload, sort_keys=True)

    assert after["social_side_packet_action_names"] == [
        REQUEST_SOCIAL_SIGNAL_CHECK
    ]
    assert after["social_side_packet_status"] == "placeholder_future_action"
    assert after["ordinary_evidence_action_names"] == []
    assert after["official_legal_current_primary_action_names"] == []
    assert ControllerBudgetClass.LIVE_CALL.value not in after["budget_counters"]
    assert "blocked" not in encoded
    social_assertions = [
        item
        for item in payload["evidence_boundary_assertions"]
        if item["boundary"]
        == ControllerEvidenceBoundary.SOCIAL_SIDE_PACKET_EVIDENCE.value
    ]
    assert social_assertions[0]["allowed"] is True
    assert social_assertions[0]["metadata"][
        "ordinary_evidence_registry_merge_allowed"
    ] is False
    assert social_assertions[0]["metadata"]["may_support_factual_claims"] is False


def test_l1_legal_diagnostics_action_alignment_survives_reduction() -> None:
    packet = build_source_class_recovery_validation_packet(_l1_trace())
    parity = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            source_class_snapshot=_source_snapshot(
                missing=("legal_or_regulatory_text",),
                reason="answer_contract_legal_text_gap:legal_or_regulatory_text",
                iteration_budget_available=False,
                answer_contract_source_class_slot_available=True,
            )
        )
    )
    envelope_payload = parity.envelopes[0].to_dict()
    reduced = reduce_controller_state(ControllerStateSnapshot(), parity.envelopes)
    after = reduced.to_dict()["after"]

    assert packet["ag25_action"]["name"] == envelope_payload["name"]
    assert packet["ag25_action"]["status"] == envelope_payload["status"]
    assert packet["ag25_action"]["authority"] == envelope_payload["authority"]
    assert packet["ag25_action"]["side_effect_class"] == (
        envelope_payload["side_effect_class"]
    )
    assert packet["ag25_action"]["handoff_boundary"] == (
        envelope_payload["handoff_boundary"]
    )
    assert after["ordinary_evidence_action_names"] == [
        RECOVER_MISSING_SOURCE_CLASS
    ]
    assert after["official_legal_current_primary_action_names"] == [
        RECOVER_MISSING_SOURCE_CLASS
    ]


def test_passive_handoff_and_review_actions_are_sanitized_handoff_only() -> None:
    handoff = envelope_from_answer_contract_action_result(
        AnswerControllerActionResult(
            action_name=AnswerControllerActionName.HANDOFF_TO_ANALYST,
            reason="Safe fulfillment handoff is ready.",
            preconditions=("handoff_ready",),
            stable_reason_code="handoff_ready",
            iteration=1,
            next_state_delta={"raw_prompt": "blocked", "safe": True},
        )
    )
    review = envelope_from_answer_contract_action_result(
        AnswerControllerActionResult(
            action_name=AnswerControllerActionName.RUN_SCRUTINEER_REVIEW,
            reason="The contract marks review as central.",
            preconditions=("scrutineer_contract_need",),
            stable_reason_code="scrutineer_contract_need",
            iteration=1,
        )
    )

    reduced = reduce_controller_state(ControllerStateSnapshot(), (handoff, review))
    after = reduced.to_dict()["after"]
    encoded = json.dumps(reduced.to_dict(), sort_keys=True)

    assert after["sanitized_handoff_action_names"] == [
        HANDOFF_TO_ANALYST,
        RUN_SCRUTINEER_REVIEW,
    ]
    assert after["ordinary_evidence_action_names"] == []
    assert "raw_prompt" not in encoded
    assert "blocked" not in encoded


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_state_reducer_static_no_provider_persistence_prompt_live_or_orchestrator_imports() -> None:
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

    violations = [
        name
        for name in _imported_names(_REDUCER_PATH)
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    source = _REDUCER_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
