from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from core.authoritative_source_action import (
    AUTHORITATIVE_SOURCE_ACTION_TRACE_KEY,
    AuthoritativeSourceActionFacts,
    AuthoritativeSourceActionName,
    build_authoritative_source_obligation_state_and_action,
)
from core.authoritative_source_action_orchestrator_adapter import (
    authoritative_source_action_trace_fragment,
    build_authoritative_source_action_facts_from_orchestrator_state,
    build_authoritative_source_action_orchestrator_handoff,
)
from core.authoritative_source_obligations import AuthorityStatus
from core.controller_loop_spine import (
    RESOLVE_CONFLICT,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    ControllerLoopSpineInput,
    build_controller_loop_spine_result,
)
from core.official_canonical_recovery_execution_admission import (
    build_official_canonical_recovery_execution_admission,
)
from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.run_controller import RunController
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_HELPER_PATH = _ROOT / "core" / "authoritative_source_action.py"
_ADAPTER_PATH = _ROOT / "core" / "authoritative_source_action_orchestrator_adapter.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_SESSION_OUTPUT_PROJECTION_PATH = _ROOT / "core" / "session_output_projection.py"


def _evidence_signals() -> dict[str, Any]:
    return {
        "source_tier_counts": {"secondary": 2},
        "source_domain_counts": {"analysis.example": 2},
        "top_source_domains": [{"domain": "analysis.example", "count": 2}],
        "unique_source_domain_count": 1,
        "on_domain_source_count": 0,
        "off_domain_source_count": 1,
        "official_evidence_found": False,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _source_tier_lifecycle() -> dict[str, Any]:
    return {
        "source_tier_counts": {"secondary": 2},
        "official_evidence_found": False,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _source_domain_lifecycle() -> dict[str, Any]:
    return {
        "source_domain_counts": {"analysis.example": 2},
        "top_source_domains": [{"domain": "analysis.example", "count": 2}],
        "unique_source_domain_count": 1,
        "on_domain_source_count": 0,
        "off_domain_source_count": 1,
    }


def _recommendation(source_class: str, **overrides: Any) -> dict[str, Any]:
    base = {
        "source_class_recovery_recommended": True,
        "source_class_recovery_shadow_mode": True,
        "missing_expected_source_classes": [source_class],
        "source_class_recovery_reason": f"missing_expected_source_class:{source_class}",
        "source_class_recovery_queries": [],
        "source_class_recovery_query_count": 0,
        "source_class_recovery_trigger_fields": ["query"],
    }
    base.update(overrides)
    return base


def _observability(**overrides: Any) -> dict[str, Any]:
    base = {
        "source_class_satisfaction_status": {},
        "source_class_strong_satisfaction_counts": {},
        "source_class_gap_candidates": [],
    }
    base.update(overrides)
    return base


def _facts(
    source_class: str = "official_current_rules",
    *,
    recommendation: dict[str, Any] | None = None,
    observability: dict[str, Any] | None = None,
    **overrides: Any,
) -> AuthoritativeSourceActionFacts:
    base: dict[str, Any] = {
        "query": "What is the IRS 2026 standard mileage rate for business use?",
        "intent": "general",
        "report_type": "general_research",
        "query_type": "official_current_status",
        "core_topic": "IRS 2026 standard mileage rate business",
        "primary_entity": "IRS",
        "recommendation": recommendation or _recommendation(source_class),
        "source_class_observability": observability or _observability(),
        "source_class_evidence_signals": _evidence_signals(),
        "current_search_depth": "basic",
        "iteration_budget_available": False,
        "answer_contract_source_class_slot_available": False,
        "max_recovery_attempts": 1,
        "ordinary_iteration_budget_remaining": 0,
    }
    base.update(overrides)
    return AuthoritativeSourceActionFacts(**base)


def _answer_contract_result(**overrides: Any) -> SimpleNamespace:
    base = {
        "adapter_result": SimpleNamespace(
            contract=SimpleNamespace(
                family=SimpleNamespace(value="current_official_rules")
            )
        ),
        "state": SimpleNamespace(
            evidence_state_summary=SimpleNamespace(source_classes_missing=())
        ),
        "fulfillment_handoff": SimpleNamespace(
            unfulfilled_items=(),
            partial_items=(),
        ),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _orchestrator_state(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query": "What is the IRS 2026 standard mileage rate for business use?",
        "intent": "general",
        "report_type": "general_research",
        "query_type": "official_current_status",
        "core_topic": "IRS 2026 standard mileage rate business",
        "primary_entity": "IRS",
        "_source_class_recovery_lifecycle_recommendation": _recommendation(
            "official_current_rules"
        ),
        "_source_class_recovery_answer_contract_observability": _observability(),
        "_source_tier_recovery_lifecycle": _source_tier_lifecycle(),
        "_source_domain_recovery_lifecycle": _source_domain_lifecycle(),
        "_pre_recovery_answer_contract_result": _answer_contract_result(),
        "corpus_state": "HEALTHY",
        "corpus_weak": False,
        "weak_corpus_recovery_considered": False,
        "weak_corpus_recovery_used": False,
        "weak_corpus_recovery_skip_reason": None,
        "evidence_integration_checkpoint_trace": {},
        "current_search_depth_for_recovery": "basic",
        "iterations_run": 0,
        "max_iterations": 1,
        "waste_flags": [],
    }
    base.update(overrides)
    return base


def _direct_query_acquisition(
    facts: AuthoritativeSourceActionFacts,
) -> dict[str, Any]:
    runtime_trace = {
        "query_preview": facts.query,
        "intent": facts.intent,
        "query_type": facts.query_type,
        "report_type": facts.report_type,
        "core_topic": facts.core_topic,
        "primary_entity": facts.primary_entity,
        **dict(facts.recommendation or {}),
        **dict(facts.source_class_observability or {}),
    }
    return apply_official_canonical_recovery_query_acquisition(
        recommendation=facts.recommendation,
        runtime_trace=runtime_trace,
    ).recommendation


def _direct_admission(
    facts: AuthoritativeSourceActionFacts,
    recommendation: dict[str, Any],
) -> bool:
    runtime_trace = {
        "query_preview": facts.query,
        "intent": facts.intent,
        "query_type": facts.query_type,
        "report_type": facts.report_type,
        "core_topic": facts.core_topic,
        "primary_entity": facts.primary_entity,
        **recommendation,
        **dict(facts.source_class_observability or {}),
    }
    return build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace=runtime_trace,
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
        ordinary_iteration_budget_remaining=0,
    ).source_class_recovery_execution_admitted


def _direct_lifecycle(
    facts: AuthoritativeSourceActionFacts,
    recommendation: dict[str, Any],
    *,
    admitted: bool,
) -> dict[str, Any]:
    return record_source_class_recovery_lifecycle(
        RunController(),
        recommendation=recommendation,
        recommendation_evaluated=True,
        source_class_evidence_signals=facts.source_class_evidence_signals or {},
        corpus_state=facts.corpus_state,
        corpus_weak=facts.corpus_weak,
        weak_corpus_recovery_considered=facts.weak_corpus_recovery_considered,
        weak_corpus_recovery_used=facts.weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=facts.weak_corpus_recovery_skip_reason,
        current_search_depth=facts.current_search_depth,
        iteration_budget_available=facts.iteration_budget_available,
        answer_contract_source_class_slot_available=(
            facts.answer_contract_source_class_slot_available
        ),
        official_canonical_source_class_slot_available=admitted,
        provider_policy_reusable=True,
        provider_swap_required=False,
        search_depth_reusable=True,
        search_depth_escalation_required=False,
        retrieve_to_anchor_recommended=False,
        pre_analyst_phase=True,
        author_phase=False,
    )


def test_named_helper_builds_authoritative_action_envelope_from_facts() -> None:
    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=_facts(),
    )

    assert result.action_decision.action_name is (
        AuthoritativeSourceActionName.SOURCE_CLASS_RECOVERY
    )
    assert result.action_decision.approved is True
    assert result.action_decision.required_source_classes == (
        "official_current_rules",
    )
    assert result.action_decision.action_envelope["allowed_action"] is True
    assert result.trace["helper"] == (
        "build_authoritative_source_obligation_state_and_action"
    )
    assert result.trace["protected_surface"]["provider_selection_unchanged"] is True


def test_helper_preserves_official_current_recovery_readiness_parity() -> None:
    facts = _facts()
    expected_recommendation = _direct_query_acquisition(facts)
    expected_admitted = _direct_admission(facts, expected_recommendation)
    expected_lifecycle = _direct_lifecycle(
        facts,
        expected_recommendation,
        admitted=expected_admitted,
    )

    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=facts,
    )

    assert result.recommendation == expected_recommendation
    assert result.official_canonical_recovery_execution_admitted is expected_admitted
    assert result.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_eligible"
    ] == expected_lifecycle["active_source_class_recovery_eligible"]
    assert result.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_queries"
    ] == expected_lifecycle["active_source_class_recovery_queries"]


def test_helper_preserves_canonical_doc_recovery_readiness_parity() -> None:
    facts = _facts(
        "primary_source_documents",
        recommendation=_recommendation("primary_source_documents"),
        query="Explain how PostgreSQL MVCC works in a database.",
        query_type="technical_reference",
        core_topic="PostgreSQL MVCC official documentation",
        primary_entity="PostgreSQL",
    )
    expected_recommendation = _direct_query_acquisition(facts)
    expected_admitted = _direct_admission(facts, expected_recommendation)

    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=facts,
    )

    assert expected_recommendation["source_class_recovery_queries"]
    assert result.recommendation == expected_recommendation
    assert result.official_canonical_recovery_execution_admitted is expected_admitted
    assert result.action_decision.required_source_classes == (
        "primary_source_documents",
    )


def test_helper_represents_legal_current_primary_without_answer_behavior_change() -> None:
    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=_facts(
            "legal_or_regulatory_text",
            query="What does the current California rule require?",
            query_type="legal_current",
            legal_current_requirement_id="legal_or_regulatory_text",
            legal_current_jurisdiction="California",
            legal_current_anchor="2026-05-26",
            legal_current_temporal_anchor="current compliance deadline",
            legal_current_evidence_facts=[
                {
                    "evidence_id": "ca-rule",
                    "source_class": "statutory_or_regulatory_text",
                    "source_tier": "official",
                    "jurisdiction": "California",
                    "currentness_status": "current",
                }
            ],
        ),
    )

    satisfaction = result.obligation_state.satisfaction_for(
        "legal_or_regulatory_text"
    )
    assert satisfaction.status is AuthorityStatus.FULFILLED
    assert result.legal_current_primary_projection is not None
    assert result.trace["protected_surface"]["final_answer_behavior_unchanged"] is True
    assert result.trace["protected_surface"]["citation_behavior_unchanged"] is True


def test_query_acquisition_and_execution_admission_outputs_remain_unchanged() -> None:
    facts = _facts()
    expected_recommendation = _direct_query_acquisition(facts)
    expected_admitted = _direct_admission(facts, expected_recommendation)

    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=facts,
    )

    assert result.recommendation["source_class_recovery_queries"] == (
        expected_recommendation["source_class_recovery_queries"]
    )
    assert result.official_canonical_recovery_execution_admitted is expected_admitted


def test_source_class_recovery_lifecycle_handoff_remains_unchanged() -> None:
    facts = _facts()
    expected_recommendation = _direct_query_acquisition(facts)
    expected_admitted = _direct_admission(facts, expected_recommendation)
    expected_lifecycle = _direct_lifecycle(
        facts,
        expected_recommendation,
        admitted=expected_admitted,
    )
    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=facts,
    )

    for key in (
        "active_source_class_recovery_eligible",
        "active_source_class_recovery_provider_role",
        "active_source_class_recovery_search_depth",
        "active_source_class_recovery_attempt_count",
        "active_source_class_recovery_action_envelope",
    ):
        assert result.active_source_class_recovery_lifecycle[key] == (
            expected_lifecycle[key]
        )


def test_competing_checkpoint_action_blocks_fallback_dispatch_as_before() -> None:
    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=_facts(),
    )
    spine = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace={
                "available": True,
                "decision": {"action_name": RESOLVE_CONFLICT},
                "recommended_action_name": RESOLVE_CONFLICT,
            },
            source_class_lifecycle_trace=result.active_source_class_recovery_lifecycle,
            conflict_resolution_lifecycle_trace={
                "approved": True,
                "active_conflict_resolution_considered": True,
            },
        )
    )

    assert result.action_decision.approved is True
    assert spine.source_class_checkpoint_gate_trace["spine_authorization_source"] is None


def test_terminal_stop_checkpoint_blocks_required_recovery() -> None:
    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=_facts(terminal_stop_approved=True),
    )
    spine = build_controller_loop_spine_result(
        ControllerLoopSpineInput.from_traces(
            checkpoint_trace={
                "available": True,
                "decision": {"action_name": STOP_INSUFFICIENT_WITH_CAVEAT},
                "recommended_action_name": STOP_INSUFFICIENT_WITH_CAVEAT,
                "terminal_stop_approved": True,
            },
            source_class_lifecycle_trace=result.active_source_class_recovery_lifecycle,
        )
    )

    assert result.official_canonical_recovery_execution_admitted is False
    assert result.active_source_class_recovery_lifecycle[
        "authority_lifecycle_required_recovery_allowed"
    ] is True
    assert spine.terminal_stop_approved is True
    assert spine.trace_packet["blocked_or_skipped_actions"][
        "recover_missing_source_class"
    ] == "blocked_by_terminal_stop"


def test_weak_corpus_blocker_remains_authoritative_for_canonical_docs() -> None:
    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=_facts(
            "primary_source_documents",
            recommendation=_recommendation("primary_source_documents"),
            query_type="technical_reference",
            corpus_state="OFF_TOPIC",
            corpus_weak=True,
            weak_corpus_recovery_considered=True,
            weak_corpus_recovery_used=True,
        ),
    )

    assert result.action_decision.approved is False
    assert "blocked_by_weak_corpus_recovery" in result.action_decision.blockers
    assert result.official_canonical_recovery_execution_admitted is False


def test_trace_safe_projection_contains_no_raw_private_material() -> None:
    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=_facts(
            recommendation={
                **_recommendation("official_current_rules"),
                "raw_prompt": "provider_payload full_trace private log secret",
            },
            observability={
                "source_class_gap_candidates": ["official_current_rules"],
                "source_class_satisfaction_status": {
                    "official_current_rules": "expected_but_only_secondary"
                },
                "raw_provider_payload": {"token": "secret"},
            },
        ),
    )
    payload = json.dumps(result.trace, sort_keys=True)

    assert result.trace["trace_safe"] is True
    for marker in (
        "raw_prompt",
        "raw_provider",
        "provider_payload full_trace",
        "private log",
        "token",
    ):
        assert marker not in payload.casefold()


def test_projection_fields_are_not_control_inputs() -> None:
    result = build_authoritative_source_obligation_state_and_action(
        RunController(),
        facts=_facts(),
    )

    assert result.trace["protected_surface"]["projection_used_as_control_input"] is False
    assert "obligation_projection" in result.trace["control_inputs_exclude"]
    assert result.action_decision.to_dict() == result.trace["action_decision"]


def test_orchestrator_adapter_builds_same_action_facts_from_runtime_state() -> None:
    controller = RunController()
    facts = build_authoritative_source_action_facts_from_orchestrator_state(
        controller,
        orchestrator_state=_orchestrator_state(),
    )

    assert facts.recommendation == _recommendation("official_current_rules")
    assert facts.source_class_observability == _observability()
    assert facts.source_class_evidence_signals == _evidence_signals()
    assert facts.query_type == "official_current_status"
    assert facts.current_search_depth == "basic"
    assert facts.prior_recovery_attempt_count == 0
    assert facts.iteration_budget_available is True


def test_orchestrator_adapter_handoff_preserves_named_action_result_keys() -> None:
    orchestrator_state = _orchestrator_state()
    direct_controller = RunController()
    adapter_controller = RunController()
    facts = build_authoritative_source_action_facts_from_orchestrator_state(
        direct_controller,
        orchestrator_state=orchestrator_state,
    )
    direct = build_authoritative_source_obligation_state_and_action(
        direct_controller,
        facts=facts,
    )
    handoff = build_authoritative_source_action_orchestrator_handoff(
        adapter_controller,
        orchestrator_state=orchestrator_state,
    )

    assert handoff.recommendation == direct.recommendation
    assert handoff.active_source_class_recovery_lifecycle == (
        direct.active_source_class_recovery_lifecycle
    )
    assert handoff.official_canonical_recovery_execution_admitted is (
        direct.official_canonical_recovery_execution_admitted
    )
    assert handoff.authoritative_source_action_trace == direct.trace
    assert handoff.compatibility_runtime_values()[0] == direct.recommendation
    assert handoff.legacy_runtime_values() == handoff.compatibility_runtime_values()


def test_orchestrator_adapter_trace_fragment_attaches_trace_safe_outputs_only() -> None:
    fragment = authoritative_source_action_trace_fragment(
        authoritative_source_action_trace={"trace_safe": True},
        official_source_obligation_bridge_trace={"bridge_used": True},
        official_canonical_recovery_query_acquisition_trace=None,
        official_canonical_recovery_execution_admission_trace={
            "admission_used": True
        },
    )

    assert fragment[AUTHORITATIVE_SOURCE_ACTION_TRACE_KEY] == {"trace_safe": True}
    assert "official_source_obligation_bridge_trace" in fragment
    assert "official_canonical_recovery_query_acquisition_trace" not in fragment
    assert "official_canonical_recovery_execution_admission_trace" in fragment


def test_pipeline_uses_tiny_named_action_adapter_handoff() -> None:
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    projection_source = _SESSION_OUTPUT_PROJECTION_PATH.read_text(encoding="utf-8")

    assert pipeline_source.count(
        "build_authoritative_source_action_orchestrator_handoff("
    ) == 1
    assert projection_source.count("authoritative_source_action_trace_fragment(") == 1
    assert "AuthoritativeSourceActionFacts(" not in pipeline_source
    assert pipeline_source.count(
        "build_authoritative_source_obligation_state_and_action("
    ) == 0
    assert "_source_class_recovery_evidence_signals = {" not in pipeline_source
    assert "_authoritative_source_action_result." not in pipeline_source
    for retired_inline_call in (
        "apply_answer_contract_source_class_recovery_gap_trigger(",
        "apply_official_canonical_recovery_query_acquisition(",
        "build_official_canonical_recovery_execution_admission(",
        "record_source_class_recovery_lifecycle(",
    ):
        assert retired_inline_call not in pipeline_source


def test_static_guard_keeps_protected_surfaces_closed() -> None:
    helper_tree = ast.parse(_HELPER_PATH.read_text(encoding="utf-8"))
    adapter_tree = ast.parse(_ADAPTER_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module
        for tree in (helper_tree, adapter_tree)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imports.update(
        alias.name
        for tree in (helper_tree, adapter_tree)
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.pipeline",
        "core.prompts",
        "core.routing",
        "core.search_providers",
        "core.source_class_recovery_executor",
        "core.source_classifier",
        "openai",
        "requests",
    }
    assert imports.isdisjoint(forbidden_imports)

    helper_source = _HELPER_PATH.read_text(encoding="utf-8").casefold()
    adapter_source = _ADAPTER_PATH.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "select_providers(",
        "choose_supplemental_search_depth(",
        "rank_sources(",
        "process_search_queries(",
        "build_author_prompt(",
        "scrutineer_policy",
        "followup_prompt",
        "build_final_answer(",
    ):
        assert forbidden not in helper_source
        assert forbidden not in adapter_source

    assert "obligation_projection" not in adapter_source
