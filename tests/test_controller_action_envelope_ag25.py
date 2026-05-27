from __future__ import annotations

import ast
import json
from pathlib import Path

from core.answer_contract_controller import (
    AnswerControllerActionName,
    AnswerControllerActionResult,
)
from core.conflict_resolution_controller import (
    ConflictResolutionControllerDecision,
    ConflictResolutionDecision,
)
from core.controller_action_envelope import (
    CONFLICT_RESOLUTION_TRACE_KEYS,
    HANDOFF_TO_ANALYST,
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    REQUEST_SOCIAL_SIGNAL_CHECK,
    RESOLVE_CONFLICT,
    RETRIEVE_TARGETED,
    RUN_SCRUTINEER_REVIEW,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    STOP_SUFFICIENT,
    ControllerActionAuthority,
    action_can_enter_ordinary_evidence,
    action_can_satisfy_evidence_class,
    controller_action_names,
    controller_action_registry,
    envelope_from_answer_contract_action_result,
    envelope_from_conflict_resolution_decision,
    envelope_from_retrieval_stop_decision,
    envelope_from_source_class_recovery_decision,
    envelope_from_weak_corpus_recovery_decision,
    envelopes_from_answer_contract_action_history,
    social_signal_placeholder_envelope,
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
    build_weak_corpus_recovery_controller_input,
)

_ROOT = Path(__file__).resolve().parents[1]
_ENVELOPE_PATH = _ROOT / "core" / "controller_action_envelope.py"


def test_registry_covers_required_controller_action_names() -> None:
    required = {
        RECOVER_WEAK_CORPUS,
        RECOVER_MISSING_SOURCE_CLASS,
        RESOLVE_CONFLICT,
        RETRIEVE_TARGETED,
        STOP_SUFFICIENT,
        STOP_INSUFFICIENT_WITH_CAVEAT,
        REQUEST_SOCIAL_SIGNAL_CHECK,
        RUN_SCRUTINEER_REVIEW,
        HANDOFF_TO_ANALYST,
    }

    registry = controller_action_registry()

    assert required <= set(controller_action_names())
    assert required <= set(registry)
    assert registry[RECOVER_WEAK_CORPUS]["side_effect_class"] == "retrieval"
    assert registry[RECOVER_MISSING_SOURCE_CLASS]["authority"] == "active"
    assert registry[RESOLVE_CONFLICT]["authority"] == "passive"
    assert registry[RESOLVE_CONFLICT]["metadata"]["active_runtime_dispatch"] is False
    assert registry[RESOLVE_CONFLICT]["metadata"]["query_source"] == (
        "resolving_queries_only"
    )
    assert registry[REQUEST_SOCIAL_SIGNAL_CHECK]["authority"] == "future"
    assert registry[REQUEST_SOCIAL_SIGNAL_CHECK]["handoff_boundary"] == (
        "sanitized_summary_only"
    )


def test_approved_source_class_recovery_maps_to_json_safe_envelope() -> None:
    decision = SourceClassRecoveryDecision(
        decision=SourceClassRecoveryControllerDecision.RUN_SOURCE_CLASS_RECOVERY,
        reason="answer_contract_official_gap:official_current_rules",
        missing_expected_source_classes=("official_current_rules",),
        queries=("Care Program official current rules",),
        provider_role="source_class_recovery",
        search_depth="basic",
        attempt_count=1,
    )

    envelope = envelope_from_source_class_recovery_decision(
        decision,
        input_summary={
            "source": "unit_test",
            "raw_prompt": "must not serialize",
            "raw_evidence": "must not serialize",
        },
    )
    payload = envelope.to_dict()

    assert payload["name"] == RECOVER_MISSING_SOURCE_CLASS
    assert payload["status"] == "approved"
    assert payload["authority"] == "active"
    assert payload["side_effect_class"] == "retrieval"
    assert payload["executor"] == (
        "core.source_class_recovery_executor:execute_source_class_recovery_action"
    )
    assert payload["reason"] == "answer_contract_official_gap:official_current_rules"
    assert payload["handoff_boundary"] == "ordinary_evidence_eligible"
    assert "active_source_class_recovery_queries" in payload["trace_keys"]
    assert payload["approved_work"]["queries"] == [
        "Care Program official current rules"
    ]
    assert "AG-22 live validation" in " ".join(payload["safety_notes"])
    assert "raw_prompt" not in payload["input_summary"]
    assert "raw_evidence" not in payload["input_summary"]
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload


def test_blocked_and_skipped_source_class_recovery_have_no_executor_side_effect() -> None:
    blocked = envelope_from_source_class_recovery_decision(
        SourceClassRecoveryDecision(
            decision=SourceClassRecoveryControllerDecision.BLOCKED_WITH_REASON,
            reason="blocked_by_iteration_budget",
            blockers=("blocked_by_iteration_budget",),
            missing_expected_source_classes=("official_current_rules",),
            queries=("Care Program official current rules",),
        )
    ).to_dict()
    skipped = envelope_from_source_class_recovery_decision(
        SourceClassRecoveryDecision(
            decision=SourceClassRecoveryControllerDecision.NO_ACTION,
            reason="not_recommended",
        )
    ).to_dict()

    assert blocked["status"] == "blocked"
    assert blocked["blockers"] == ["blocked_by_iteration_budget"]
    assert blocked["side_effect_class"] == "none"
    assert blocked["executor"] is None
    assert skipped["status"] == "skipped"
    assert skipped["skip_reason"] == "not_recommended"
    assert skipped["side_effect_class"] == "none"
    assert skipped["executor"] is None


def test_approved_weak_corpus_recovery_is_distinct_and_preserves_budget_metadata() -> None:
    snapshot = build_weak_corpus_recovery_controller_input(
        corpus_state="OFF_TOPIC",
        corpus_weak=True,
        iteration=1,
        max_iterations=2,
        prior_attempted=False,
        readable_passage_count=2,
        recovery_queries=("Acme independent confirmation",),
    )
    decision = WeakCorpusRecoveryDecision(
        decision=WeakCorpusRecoveryControllerDecision.RUN_WEAK_CORPUS_RECOVERY,
        reason="weak_corpus_first_pass",
        queries=("Acme independent confirmation",),
    )

    payload = envelope_from_weak_corpus_recovery_decision(
        decision,
        snapshot=snapshot,
    ).to_dict()

    assert payload["name"] == RECOVER_WEAK_CORPUS
    assert payload["name"] != RECOVER_MISSING_SOURCE_CLASS
    assert payload["status"] == "approved"
    assert payload["side_effect_class"] == "retrieval"
    assert payload["approved_work"]["provider_role"] == "weak_corpus_recovery"
    assert payload["metadata"]["one_attempt_only"] is True
    assert payload["metadata"]["budget_owner"] == "orchestrator_iteration_budget"
    assert payload["metadata"]["iteration"] == 1
    assert payload["metadata"]["max_iterations"] == 2
    assert payload["metadata"]["prior_attempted"] is False


def test_passive_conflict_resolution_envelope_is_not_active_dispatch() -> None:
    decision = ConflictResolutionDecision(
        decision=ConflictResolutionControllerDecision.RUN_CONFLICT_RESOLUTION,
        reason="material_conflict_resolution_available",
        conflict_notes=("official date conflicts with media date",),
        queries=("Acme official corrected launch date",),
        provider_role="conflict_resolution",
        search_depth="basic",
        attempt_count=1,
    )

    payload = envelope_from_conflict_resolution_decision(
        decision,
        input_summary={
            "source": "unit_test",
            "raw_prompt": "must not serialize",
            "raw_evidence": "must not serialize",
        },
    ).to_dict()

    assert payload["name"] == RESOLVE_CONFLICT
    assert payload["status"] == "approved"
    assert payload["authority"] == "passive"
    assert payload["side_effect_class"] == "retrieval"
    assert payload["executor"] == (
        "core.conflict_resolution_executor:execute_conflict_resolution_action"
    )
    assert payload["approved_work"]["provider_role"] == "conflict_resolution"
    assert payload["approved_work"]["queries"] == [
        "Acme official corrected launch date"
    ]
    assert payload["metadata"]["active_runtime_dispatch"] is False
    assert payload["metadata"]["query_source"] == "resolving_queries_only"
    assert payload["output_delta"]["resolve_conflict_attempted"] is False
    assert set(CONFLICT_RESOLUTION_TRACE_KEYS) <= set(payload["trace_keys"])
    assert "raw_prompt" not in payload["input_summary"]
    assert "raw_evidence" not in payload["input_summary"]


def test_blocked_conflict_resolution_has_no_executor_or_side_effect() -> None:
    payload = envelope_from_conflict_resolution_decision(
        ConflictResolutionDecision(
            decision=ConflictResolutionControllerDecision.BLOCKED_WITH_REASON,
            reason="no_resolving_queries",
            blockers=("no_resolving_queries",),
            conflict_notes=("official date conflicts with media date",),
        )
    ).to_dict()

    assert payload["name"] == RESOLVE_CONFLICT
    assert payload["status"] == "blocked"
    assert payload["skip_reason"] == "no_resolving_queries"
    assert payload["side_effect_class"] == "none"
    assert payload["executor"] is None
    assert payload["approved_work"] == {}


def test_retrieval_stop_terminal_and_shadow_envelopes_preserve_boundaries() -> None:
    budget_decision = RetrievalStopDecision(
        decision=RetrievalStopControllerDecision.STOP_BUDGET_EXHAUSTED,
        reason="iteration_budget_exhausted",
        blockers=("iteration_budget_exhausted",),
    )
    no_query_decision = RetrievalStopDecision(
        decision=RetrievalStopControllerDecision.STOP_NO_QUERIES,
        reason="no_new_queries",
        blockers=("no_new_queries",),
    )

    budget_payload = envelope_from_retrieval_stop_decision(
        budget_decision,
        authority=ControllerActionAuthority.ACTIVE,
        stage="iteration_budget_exhausted",
        mode="active_stop_budget_exhausted",
    ).to_dict()
    no_query_payload = envelope_from_retrieval_stop_decision(
        no_query_decision,
        authority=ControllerActionAuthority.ACTIVE,
        stage="evaluator_no_queries",
        mode="active_stop_no_queries",
    ).to_dict()
    shadow_payload = envelope_from_retrieval_stop_decision(
        no_query_decision,
        authority=ControllerActionAuthority.SHADOW,
        stage="evaluator_no_queries",
    ).to_dict()

    for payload in (budget_payload, no_query_payload):
        assert payload["name"] == STOP_INSUFFICIENT_WITH_CAVEAT
        assert payload["status"] == "completed"
        assert payload["authority"] == "active"
        assert payload["side_effect_class"] == "stop"
        assert payload["handoff_boundary"] == "final_answer_posture_only"
        assert payload["output_delta"]["stop_state"]["final_answer_posture"] == (
            "answer with caveats"
        )

    assert shadow_payload["status"] == "informational"
    assert shadow_payload["authority"] == "shadow"
    assert shadow_payload["side_effect_class"] == "none"
    assert shadow_payload["output_delta"] == {}
    assert "retrieval_stop_shadow_decision" in shadow_payload["trace_keys"]


def test_answer_contract_action_history_items_become_envelopes_without_semantic_change() -> None:
    action = AnswerControllerActionResult(
        action_name=AnswerControllerActionName.RETRIEVE_TARGETED,
        reason="A non-redundant query is available.",
        preconditions=("targeted_query_available",),
        approved_queries_or_none=("Acme official rollout facts",),
        stable_reason_code="targeted_query_available",
        iteration=2,
    )

    payload = envelope_from_answer_contract_action_result(action).to_dict()
    history = envelopes_from_answer_contract_action_history((action,))

    assert action.approved is True
    assert payload["name"] == RETRIEVE_TARGETED
    assert payload["status"] == "approved"
    assert payload["authority"] == "passive"
    assert payload["side_effect_class"] == "retrieval"
    assert payload["approved_work"]["queries"] == ["Acme official rollout facts"]
    assert payload["metadata"]["stable_reason_code"] == "targeted_query_available"
    assert len(history) == 1
    assert history[0].to_dict() == payload


def test_social_signal_placeholder_is_side_packet_only_and_not_ordinary_evidence() -> None:
    payload = social_signal_placeholder_envelope().to_dict()

    assert payload["name"] == REQUEST_SOCIAL_SIGNAL_CHECK
    assert payload["status"] == "informational"
    assert payload["authority"] == "future"
    assert payload["side_effect_class"] == "social_side_packet"
    assert payload["handoff_boundary"] == "sanitized_summary_only"
    assert payload["input_summary"]["ordinary_evidence_eligible"] is False
    assert action_can_enter_ordinary_evidence(REQUEST_SOCIAL_SIGNAL_CHECK) is False
    assert action_can_satisfy_evidence_class(
        REQUEST_SOCIAL_SIGNAL_CHECK,
        "official_current_rules",
    ) is False
    assert action_can_satisfy_evidence_class(
        REQUEST_SOCIAL_SIGNAL_CHECK,
        "legal_or_regulatory_text",
    ) is False
    assert action_can_satisfy_evidence_class(
        REQUEST_SOCIAL_SIGNAL_CHECK,
        "current_primary_or_official",
    ) is False
    assert action_can_satisfy_evidence_class(
        REQUEST_SOCIAL_SIGNAL_CHECK,
        "factual_evidence",
    ) is False
    assert action_can_satisfy_evidence_class(
        REQUEST_SOCIAL_SIGNAL_CHECK,
        "social_signal_side_packet",
    ) is True


def test_controller_action_envelope_static_import_guard() -> None:
    tree = ast.parse(_ENVELOPE_PATH.read_text(encoding="utf-8"))
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


def test_envelope_dicts_are_deterministic_plain_json_safe_values() -> None:
    action = AnswerControllerActionResult(
        action_name=AnswerControllerActionName.RUN_SCRUTINEER_REVIEW,
        reason="The contract marks Scrutineer review as central.",
        preconditions=("scrutineer_contract_need",),
        stable_reason_code="scrutineer_contract_need",
        iteration=1,
        next_state_delta={"review": {"raw_packet": "do not serialize", "ok": True}},
    )

    first = envelope_from_answer_contract_action_result(
        action,
        metadata={"z": {"b", "a"}, "raw_provider_payload": {"secret": True}},
    ).to_dict()
    second = envelope_from_answer_contract_action_result(
        action,
        metadata={"z": {"a", "b"}, "raw_provider_payload": {"secret": True}},
    ).to_dict()

    assert first == second
    assert first["output_delta"]["review"] == {"ok": True}
    assert "raw_provider_payload" not in first["metadata"]
    assert json.loads(json.dumps(first, sort_keys=True)) == first
