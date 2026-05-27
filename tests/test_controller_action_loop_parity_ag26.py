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
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RETRIEVE_TARGETED,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    ControllerActionAuthority,
)
from core.controller_action_loop_parity import (
    OFFICIAL_LEGAL_RECOVERY_LIMITATION_GAP,
    SOCIAL_SIGNAL_SIDE_PACKET_ONLY_GAP,
    ControllerActionLoopParityFacts,
    ControllerActionLoopParityStatus,
    replay_offline_controller_action_loop,
)
from core.retrieval_stop_controller import build_retrieval_stop_controller_input
from core.source_class_recovery_controller import (
    build_source_class_recovery_controller_input,
)
from core.weak_corpus_controller import build_weak_corpus_recovery_controller_input

_ROOT = Path(__file__).resolve().parents[1]
_HARNESS_PATH = _ROOT / "core" / "controller_action_loop_parity.py"


def _weak_snapshot(
    *,
    corpus_weak: bool = True,
    max_iterations: int = 2,
    readable_passage_count: int = 2,
    recovery_queries: tuple[str, ...] = ("Acme independent confirmation",),
) -> Any:
    return build_weak_corpus_recovery_controller_input(
        corpus_state="OFF_TOPIC" if corpus_weak else "HEALTHY",
        corpus_weak=corpus_weak,
        iteration=1,
        max_iterations=max_iterations,
        prior_attempted=False,
        readable_passage_count=readable_passage_count,
        recovery_queries=recovery_queries,
    )


def _source_recommendation(
    *,
    recommended: bool = True,
    missing: tuple[str, ...] = ("reputable_reviews",),
    queries: tuple[str, ...] = ("Acme expert review source",),
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": recommended,
        "missing_expected_source_classes": list(missing if recommended else ()),
        "source_class_recovery_queries": list(queries if recommended else ()),
        "source_class_recovery_reason": (
            reason
            if reason is not None
            else "missing_expected_source_class:" + ",".join(missing)
            if recommended
            else None
        ),
    }


def _source_snapshot(
    *,
    recommendation: dict[str, Any] | None = None,
    missing: tuple[str, ...] = ("reputable_reviews",),
    reason: str | None = None,
    weak_corpus_recovery_used: bool = False,
    iteration_budget_available: bool = True,
    answer_contract_source_class_slot_available: bool = False,
) -> Any:
    return build_source_class_recovery_controller_input(
        recommendation=recommendation
        if recommendation is not None
        else _source_recommendation(missing=missing, reason=reason),
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
        weak_corpus_recovery_considered=weak_corpus_recovery_used,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=iteration_budget_available,
        prior_attempt_count=0,
        answer_contract_source_class_slot_available=(
            answer_contract_source_class_slot_available
        ),
    )


def _envelope_payload(result: Any, index: int = 0) -> dict[str, Any]:
    return result.to_dict()["envelopes"][index]


def test_weak_corpus_recovery_approved_replays_ag25_envelope_only() -> None:
    result = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(weak_corpus_snapshot=_weak_snapshot())
    )
    payload = _envelope_payload(result)

    assert result.status is ControllerActionLoopParityStatus.REPLAYED
    assert payload["name"] == RECOVER_WEAK_CORPUS
    assert payload["status"] == "approved"
    assert payload["side_effect_class"] == "retrieval"
    assert payload["approved_work"]["provider_role"] == "weak_corpus_recovery"
    assert result.to_dict()["metadata"]["offline_only"] is True
    assert result.to_dict()["metadata"]["runtime_behavior_changed"] is False
    assert result.to_dict()["metadata"]["live_side_effects"] is False


def test_weak_corpus_recovery_blocked_and_skipped_stay_side_effect_free() -> None:
    blocked = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            weak_corpus_snapshot=_weak_snapshot(max_iterations=1)
        )
    )
    skipped = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            weak_corpus_snapshot=_weak_snapshot(corpus_weak=False)
        )
    )

    blocked_payload = _envelope_payload(blocked)
    skipped_payload = _envelope_payload(skipped)
    assert blocked_payload["status"] == "blocked"
    assert blocked_payload["side_effect_class"] == "none"
    assert blocked_payload["executor"] is None
    assert blocked_payload["skip_reason"] == "max_iterations_1"
    assert skipped_payload["status"] == "skipped"
    assert skipped_payload["side_effect_class"] == "none"
    assert skipped_payload["skip_reason"] == "not_weak_corpus"


def test_source_class_recovery_approved_replays_current_controller_decision() -> None:
    result = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(source_class_snapshot=_source_snapshot())
    )
    payload = _envelope_payload(result)

    assert result.status is ControllerActionLoopParityStatus.REPLAYED
    assert payload["name"] == RECOVER_MISSING_SOURCE_CLASS
    assert payload["status"] == "approved"
    assert payload["authority"] == "active"
    assert payload["side_effect_class"] == "retrieval"
    assert payload["approved_work"]["queries"] == ["Acme expert review source"]
    assert payload["approved_work"]["search_depth"] == "basic"


def test_official_legal_source_class_recovery_reports_ag22_limitation_gap() -> None:
    result = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            source_class_snapshot=_source_snapshot(
                missing=("legal_or_regulatory_text",),
                reason="answer_contract_legal_text_gap:legal_or_regulatory_text",
                iteration_budget_available=False,
                answer_contract_source_class_slot_available=True,
            )
        )
    )
    payload = _envelope_payload(result)
    gap_payloads = [gap.to_dict() for gap in result.gaps]

    assert result.status is ControllerActionLoopParityStatus.REPLAYED_WITH_KNOWN_GAPS
    assert payload["status"] == "approved"
    assert payload["name"] == RECOVER_MISSING_SOURCE_CLASS
    assert "AG-22 live validation" in " ".join(payload["safety_notes"])
    assert gap_payloads[0]["code"] == OFFICIAL_LEGAL_RECOVERY_LIMITATION_GAP
    assert gap_payloads[0]["metadata"]["ag22_limitation"] is True


def test_source_class_recovery_blocked_and_skipped_replay_without_executor() -> None:
    blocked = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            source_class_snapshot=_source_snapshot(weak_corpus_recovery_used=True)
        )
    )
    skipped = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            source_class_snapshot=_source_snapshot(
                recommendation=_source_recommendation(recommended=False)
            )
        )
    )

    blocked_payload = _envelope_payload(blocked)
    skipped_payload = _envelope_payload(skipped)
    assert blocked_payload["status"] == "blocked"
    assert blocked_payload["side_effect_class"] == "none"
    assert blocked_payload["executor"] is None
    assert "blocked_by_weak_corpus_recovery" in blocked_payload["blockers"]
    assert skipped_payload["status"] == "skipped"
    assert skipped_payload["side_effect_class"] == "none"
    assert skipped_payload["skip_reason"] == "not_recommended"


def test_retrieval_stop_active_terminal_no_query_and_budget_exhausted_replay_as_stop() -> None:
    no_query = replay_offline_controller_action_loop(
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
        )
    )
    budget = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            retrieval_stop_snapshot=build_retrieval_stop_controller_input(
                evaluator_sufficient=False,
                iteration=3,
                max_iterations=3,
                prior_queries=("Acme status",),
                next_queries=("Acme follow-up official",),
                query_source="evaluator",
            ),
            retrieval_stop_authority=ControllerActionAuthority.ACTIVE,
            retrieval_stop_stage="iteration_budget_exhausted",
            retrieval_stop_mode="active_stop_budget_exhausted",
        )
    )

    for result in (no_query, budget):
        payload = _envelope_payload(result)
        assert result.status is ControllerActionLoopParityStatus.REPLAYED
        assert payload["name"] == STOP_INSUFFICIENT_WITH_CAVEAT
        assert payload["status"] == "completed"
        assert payload["authority"] == "active"
        assert payload["side_effect_class"] == "stop"
        assert payload["handoff_boundary"] == "final_answer_posture_only"


def test_retrieval_stop_shadow_continue_replays_as_informational_only() -> None:
    result = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(
            retrieval_stop_snapshot=build_retrieval_stop_controller_input(
                evaluator_sufficient=False,
                iteration=1,
                max_iterations=3,
                prior_queries=("Acme status",),
                next_queries=("Acme official update",),
                query_source="evaluator",
            ),
            retrieval_stop_authority=ControllerActionAuthority.SHADOW,
            retrieval_stop_stage="evaluator_continue",
        )
    )
    payload = _envelope_payload(result)

    assert result.status is ControllerActionLoopParityStatus.REPLAYED
    assert payload["name"] == RETRIEVE_TARGETED
    assert payload["status"] == "informational"
    assert payload["authority"] == "shadow"
    assert payload["side_effect_class"] == "none"
    assert payload["approved_work"] == {}


def test_answer_contract_action_history_replays_to_passive_envelopes() -> None:
    action = AnswerControllerActionResult(
        action_name=AnswerControllerActionName.RETRIEVE_TARGETED,
        reason="A non-redundant query is available for the remaining gap.",
        preconditions=("targeted_query_available",),
        approved_queries_or_none=("Acme official rollout facts",),
        stable_reason_code="targeted_query_available",
        iteration=2,
    )
    result = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(answer_contract_action_history=(action,))
    )
    payload = _envelope_payload(result)

    assert result.status is ControllerActionLoopParityStatus.REPLAYED
    assert payload["name"] == RETRIEVE_TARGETED
    assert payload["status"] == "approved"
    assert payload["authority"] == "passive"
    assert payload["approved_work"]["queries"] == ["Acme official rollout facts"]
    assert result.compact_action_history[0]["name"] == RETRIEVE_TARGETED
    assert json.loads(json.dumps(result.to_dict(), sort_keys=True)) == result.to_dict()


def test_social_signal_placeholder_remains_future_side_packet_only() -> None:
    result = replay_offline_controller_action_loop(
        ControllerActionLoopParityFacts(include_social_signal_placeholder=True)
    )
    payload = _envelope_payload(result)
    gap_payload = result.gaps[0].to_dict()

    assert result.status is ControllerActionLoopParityStatus.REPLAYED_WITH_KNOWN_GAPS
    assert payload["name"] == REQUEST_SOCIAL_SIGNAL_CHECK
    assert payload["status"] == "informational"
    assert payload["authority"] == "future"
    assert payload["side_effect_class"] == "social_side_packet"
    assert payload["input_summary"]["ordinary_evidence_eligible"] is False
    assert gap_payload["code"] == SOCIAL_SIGNAL_SIDE_PACKET_ONLY_GAP
    assert gap_payload["metadata"]["ordinary_evidence_eligible"] is False


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_parity_harness_static_no_provider_runtime_persistence_prompt_or_orchestrator_imports() -> None:
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

    violations = [
        name
        for name in _imported_names(_HARNESS_PATH)
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    source = _HARNESS_PATH.read_text(encoding="utf-8")

    assert violations == []
    assert all(term not in source for term in forbidden_terms)
