from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from core.conflict_resolution_controller import (
    ConflictResolutionControllerDecision,
    ConflictResolutionDecision,
)
from core.lifecycle_trace_projection import (
    build_evidence_integration_snapshot_from_runtime,
    conflict_resolution_lifecycle_facts,
    weak_corpus_lifecycle_facts,
)
from core.weak_corpus_controller import (
    WeakCorpusRecoveryControllerDecision,
    WeakCorpusRecoveryDecision,
)


def test_weak_corpus_lifecycle_facts_recovery_approved_exact_dict() -> None:
    decision = WeakCorpusRecoveryDecision(
        decision=WeakCorpusRecoveryControllerDecision.RUN_WEAK_CORPUS_RECOVERY,
        reason="weak_corpus_first_pass",
        queries=("Acme official filing",),
    )

    assert weak_corpus_lifecycle_facts(decision) == {
        "approved": True,
        "reason": "weak_corpus_first_pass",
        "blockers": [],
    }


def test_weak_corpus_lifecycle_facts_skipped_or_no_decision_exact_dicts() -> None:
    skipped = WeakCorpusRecoveryDecision(
        decision=WeakCorpusRecoveryControllerDecision.BLOCKED_WITH_REASON,
        reason="no_recovery_queries",
        blockers=("no_recovery_queries", "max_iterations_1"),
    )

    assert weak_corpus_lifecycle_facts(skipped) == {
        "approved": False,
        "reason": "no_recovery_queries",
        "blockers": ["no_recovery_queries", "max_iterations_1"],
    }
    assert weak_corpus_lifecycle_facts(None) is None


def test_conflict_resolution_lifecycle_facts_decision_approved_exact_dict() -> None:
    decision = ConflictResolutionDecision(
        decision=ConflictResolutionControllerDecision.RUN_CONFLICT_RESOLUTION,
        reason="conflict_resolution_candidate_available",
        blockers=(),
        queries=("Acme contradiction official source",),
    )

    assert conflict_resolution_lifecycle_facts(
        decision=decision,
        lifecycle_trace={"active_conflict_resolution_considered": True},
    ) == {
        "approved": True,
        "reason": "conflict_resolution_candidate_available",
        "blockers": [],
        "active_conflict_resolution_considered": True,
    }


def test_conflict_resolution_lifecycle_facts_lifecycle_only_fallback_exact_dict() -> None:
    assert conflict_resolution_lifecycle_facts(
        decision=None,
        lifecycle_trace={
            "active_conflict_resolution_skip_reason": "no_resolving_queries",
            "active_conflict_resolution_reason": "ignored_when_skip_exists",
            "active_conflict_resolution_blockers": ("no_resolving_queries",),
            "active_conflict_resolution_considered": True,
        },
    ) == {
        "approved": False,
        "reason": "no_resolving_queries",
        "blockers": ["no_resolving_queries"],
        "active_conflict_resolution_considered": True,
    }
    assert conflict_resolution_lifecycle_facts(decision=None, lifecycle_trace={}) == {
        "approved": False,
        "reason": "blocked_by_lifecycle",
        "blockers": [],
        "active_conflict_resolution_considered": False,
    }


def test_evidence_integration_lifecycle_projection_exact_snapshot_dict() -> None:
    contract = SimpleNamespace(
        family=SimpleNamespace(value="current_events"),
        must_satisfy=("official current source",),
        should_satisfy=("secondary context",),
        evidence_classes_needed=("official_current_rules",),
        social_signal_relevance=SimpleNamespace(value="central"),
        scrutineer_relevance=SimpleNamespace(value="relevant_optional"),
    )
    evidence_state = SimpleNamespace(
        source_classes_missing=("official_current_rules",),
        evidence_available=True,
        evidence_sufficient=True,
        source_classes_present=("reputable_secondary",),
        conflicts_present=True,
        conflict_notes=("Source A and Source B disagree",),
        resolving_queries=("Acme conflict resolution",),
        prior_queries=("Acme first pass", "Acme second pass"),
        social_signal_status="missing",
        scrutineer_requested=True,
        scrutineer_needed=True,
    )
    answer_contract_result = SimpleNamespace(
        adapter_result=SimpleNamespace(
            contract=contract,
            evidence_used=("ref-1", "ref-2"),
        ),
        state=SimpleNamespace(
            evidence_state_summary=evidence_state,
            missing_information=("missing launch date",),
        ),
        fulfillment_handoff=SimpleNamespace(
            fulfilled_items=("background",),
            partial_items=("launch date",),
            unfulfilled_items=("official source",),
        ),
    )

    snapshot = build_evidence_integration_snapshot_from_runtime(
        answer_contract_result=answer_contract_result,
        source_class_recovery_recommendation={
            "missing_expected_source_classes": ("legal_or_regulatory_text",),
            "source_class_recovery_queries": ("Acme official rules",),
            "source_class_recovery_recommended": True,
        },
        active_source_class_recovery_lifecycle={
            "active_source_class_recovery_missing_classes": ("primary_update",),
            "active_source_class_recovery_eligible": True,
            "active_source_class_recovery_blockers": ("blocked_by_weak_corpus_recovery",),
        },
        strategy="Deep",
        is_sufficient=False,
        corpus_weak=True,
        corpus_state="weak_corpus",
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_attempted=False,
        weak_corpus_recovery_skip_reason=None,
        retrieval_stop_shadow_telemetry={
            "retrieval_stop_shadow_decision": "continue_retrieval",
            "retrieval_stop_shadow_next_query_count": 3,
        },
        iterations_run=1,
        max_iterations=3,
    )

    assert snapshot.to_dict() == {
        "schema_version": "evidence_integration_snapshot_ag32_v1",
        "contract_family": "current_events",
        "contract_must_satisfy": ["official current source"],
        "contract_should_satisfy": ["secondary context"],
        "required_source_classes": ["official_current_rules"],
        "contract_fulfillment": {
            "fulfilled": ["background"],
            "partial": ["launch date"],
            "unfulfilled": ["official source"],
            "missing_information": [
                "missing launch date",
                "ordinary continuation gap",
            ],
        },
        "evidence": {
            "available": True,
            "sufficient": False,
            "reference_count": 2,
            "source_classes_present": ["reputable_secondary"],
            "source_classes_missing": [
                "official_current_rules",
                "legal_or_regulatory_text",
                "primary_update",
            ],
        },
        "weak_corpus": {
            "active": True,
            "reason": "weak_corpus",
            "recovery_used": False,
            "recovery_available": True,
        },
        "source_class_state": {
            "recovery_recommended": True,
            "recovery_eligible": True,
            "missing_classes": [
                "official_current_rules",
                "legal_or_regulatory_text",
                "primary_update",
            ],
            "queries_available": True,
            "blockers": ["blocked_by_weak_corpus_recovery"],
        },
        "conflicts": {
            "present": True,
            "notes": ["Source A and Source B disagree"],
            "resolution_available": True,
        },
        "targeted_retrieval": {
            "next_queries_available": True,
            "next_query_redundant": False,
            "prior_query_count": 2,
            "next_query_count": 3,
        },
        "clarification_needed": False,
        "social_signal": {
            "requested": True,
            "status": "missing",
            "side_packet_placeholder_allowed": True,
            "ordinary_evidence_allowed": False,
            "evidence_boundary": "social_side_packet_evidence",
        },
        "scrutineer": {
            "requested": True,
            "needed": True,
            "allowed_by_mode": True,
            "allowed_by_contract": True,
        },
        "budget": {
            "mode": "Deep",
            "iteration": 1,
            "max_iterations": 3,
            "remaining": {
                "retrieval_action_budget_remaining": 2,
                "targeted_retrieval_remaining": 2,
                "weak_corpus_recovery_remaining": 2,
                "source_class_recovery_remaining": 1,
                "conflict_resolution_remaining": 2,
                "social_side_packet_placeholder_remaining": 1,
                "live_call_placeholder_remaining": 0,
            },
            "budget_classes": [
                "retrieval_iteration_budget",
                "weak_corpus_recovery_budget",
                "source_class_recovery_budget",
                "social_side_packet_budget_placeholder",
                "live_call_budget_placeholder",
            ],
            "scrutineer_review_allowed": True,
            "clarification_allowed": True,
            "low_value_stop_recommended": False,
            "protected_provider_depth_routing_boundary": True,
        },
        "metadata": {
            "stage": "post_retrieval_post_source_class_lifecycle_pre_source_class_execution",
            "shadow_only": True,
            "provider_routing_boundary": "orchestrator_owned",
            "search_depth_boundary": "orchestrator_owned",
        },
    }


def test_lifecycle_projection_helper_static_seam_guard() -> None:
    helper_path = Path("core/lifecycle_trace_projection.py")
    source = helper_path.read_text()
    tree = ast.parse(source)
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    forbidden_import_fragments = (
        "provider",
        "search_providers",
        "prompts",
        "citation",
        "final_evidence",
        "persistence",
        "db",
        "cache",
        "runtime_prompt",
    )
    forbidden_calls = {
        "ask_model",
        "process_search_queries",
        "select_providers",
        "embed_texts",
        "select_search_depth",
        "build_final_evidence_bundle",
        "attach_author_evidence",
        "execute_persistence_side_effects",
        "record_final_evidence_snapshot",
        "build_author_prompt_from_scope",
        "globals",
        "locals",
    }

    assert not any(
        fragment in module
        for module in imported_modules
        for fragment in forbidden_import_fragments
    )
    assert "{**globals(), **locals()}" not in source
    assert "globals()" not in source
    assert "locals()" not in source
    assert "raw_scope" not in source
    assert not {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } & forbidden_calls
