from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.authority_lifecycle_contract import (
    AuthorityEvidenceFitState,
    AuthorityFinalPosture,
    AuthorityLifecycle,
    AuthoritySatisfactionState,
    LowerTierContextState,
    RecoveryNeededState,
)
from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
    source_class_recovery_execution_blocked_if_needed,
)
from core.authority_lifecycle_forced_corridor_classification import (
    AUTHORITY_LIFECYCLE_FORCED_CORRIDOR_CLASSIFICATION_SCHEMA_VERSION,
    classify_authority_lifecycle_forced_corridor,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    RECOVER_WEAK_CORPUS,
    STOP_INSUFFICIENT_WITH_CAVEAT,
    build_controller_loop_spine_result,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)

_ROOT = Path(__file__).resolve().parents[1]
_CLASSIFIER_PATH = (
    _ROOT / "core" / "authority_lifecycle_forced_corridor_classification.py"
)
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _trace(
    *,
    requirement_id: str = "official_current_rules",
    required_authority: str = "official_current_rules",
    claim_type: str = "official_current_status",
    recovery_queries: tuple[str, ...] = ("agency official current source",),
    required_source_classes: tuple[str, ...] = ("official_current_rules",),
    terminal_stop_approved: bool = False,
    weak_corpus_recovery_used: bool = False,
    corpus_weak: bool = False,
) -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id=requirement_id,
        required_authority=required_authority,
        claim_type=claim_type,
        required_recovery=True,
        recovery_queries=recovery_queries,
        required_source_classes=required_source_classes,
        recovery_action_allowed=True,
        terminal_stop_approved=terminal_stop_approved,
        weak_corpus_recovery_used=weak_corpus_recovery_used,
        corpus_weak=corpus_weak,
    ).to_trace_fields()
    trace.update(
        {
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_missing_classes": list(
                required_source_classes
            ),
            "active_source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:"
                f"{required_source_classes[0]}"
            ),
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": list(required_source_classes),
                "allowed_action": True,
            },
        }
    )
    return trace


def _checkpoint_terminal() -> dict[str, Any]:
    return {
        "available": True,
        "decision": {"action_name": STOP_INSUFFICIENT_WITH_CAVEAT},
        "recommended_action_name": STOP_INSUFFICIENT_WITH_CAVEAT,
    }


def _checkpoint_weak() -> dict[str, Any]:
    return {
        "available": True,
        "decision": {"action_name": RECOVER_WEAK_CORPUS},
        "recommended_action_name": RECOVER_WEAK_CORPUS,
    }


def _weak_lifecycle() -> dict[str, Any]:
    return {"approved": True, "reason": "weak_corpus_fixture", "blockers": []}


def _existing_secondary() -> dict[str, Any]:
    return {
        "title": "Existing lower-tier analysis",
        "url": "https://analysis.example/context",
        "text": "Lower-tier context fixture.",
        "source_tier": "secondary",
    }


def _official_source(
    *,
    url: str = "https://www.irs.gov/ag69f-current",
    source_class: str = "official_current_rules",
) -> dict[str, Any]:
    return {
        "title": "Official current fixture",
        "url": url,
        "text": "Official current source fixture.",
        "source_tier": "official",
        "source_class": source_class,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
    }


def _secondary_recovered_source() -> dict[str, Any]:
    return {
        "title": "Secondary returned fixture",
        "url": "https://analysis.example/ag69f-returned",
        "text": "Secondary returned source fixture.",
        "source_tier": "secondary",
        "source_class": "official_current_rules",
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
    }


def _run_visibility(
    trace: dict[str, Any],
    recovered: list[dict[str, Any]],
    *,
    final: list[dict[str, Any]] | None = None,
    max_final_evidence: int = 4,
) -> dict[str, Any]:
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=final or [_existing_secondary()],
        recovered_passages=recovered,
        lifecycle_trace=trace,
        max_final_evidence=max_final_evidence,
    )
    assert final
    trace.update(decision.to_trace_fields())
    return trace


def _record_attempted(
    trace: dict[str, Any],
    *,
    result_count: int = 1,
    accepted_url_count: int = 1,
) -> dict[str, Any]:
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=result_count,
        recovered_result_count=result_count,
        accepted_url_count=accepted_url_count,
    )
    return trace


def test_ag69f_forced_ssa_terminal_stop_cannot_preempt_lifecycle_recovery() -> None:
    trace = _trace(terminal_stop_approved=True)
    spine = build_controller_loop_spine_result(
        checkpoint_trace=_checkpoint_terminal(),
        source_class_lifecycle_trace=trace,
    )
    _record_attempted(trace, result_count=0, accepted_url_count=0)
    packet = classify_authority_lifecycle_forced_corridor(
        trace,
        corridor_name="ssa_terminal_stop_forced_official_current",
    )

    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert packet["terminal_stop_state"] == "approved"
    assert packet["recovery_action_state"] == "approved"
    assert packet["execution_attempted"] is True
    assert packet["terminal_paths"] == ["approved_action_executed"]
    assert packet["lifecycle_contract_valid"] is True
    assert "terminal_stop_preempts_required_recovery" not in packet[
        "forbidden_state_codes"
    ]


def test_ag69f_forced_weak_corpus_cannot_preempt_lifecycle_recovery() -> None:
    trace = _trace(weak_corpus_recovery_used=True, corpus_weak=True)
    spine = build_controller_loop_spine_result(
        checkpoint_trace=_checkpoint_weak(),
        source_class_lifecycle_trace=trace,
        weak_corpus_lifecycle_trace=_weak_lifecycle(),
    )
    _record_attempted(trace, result_count=0, accepted_url_count=0)
    packet = classify_authority_lifecycle_forced_corridor(
        trace,
        corridor_name="ssa_weak_corpus_forced_official_current",
    )

    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert packet["weak_corpus_state"] == "owns_path"
    assert packet["execution_attempted"] is True
    assert packet["terminal_paths"] == ["approved_action_executed"]
    assert packet["lifecycle_contract_valid"] is True
    assert "weak_corpus_preempts_authority_recovery" not in packet[
        "forbidden_state_codes"
    ]


def test_ag69f_forced_recovery_records_structured_blocker_when_not_dispatched() -> None:
    trace = _trace()
    source_class_recovery_execution_blocked_if_needed(
        trace,
        authorized_for_executor=False,
        blocker_reason="ag69f_forced_corridor_executor_not_authorized",
    )
    packet = classify_authority_lifecycle_forced_corridor(
        trace,
        corridor_name="executor_blocker_forced_official_current",
    )

    assert packet["execution_state"] == "blocked"
    assert packet["structured_execution_blocker"]["requirement_id"] == (
        "official_current_rules"
    )
    assert packet["structured_execution_blocker"]["owner"] == "controller/lifecycle"
    assert packet["terminal_paths"] == ["controller_hard_blocker"]
    assert packet["remaining_failure_layer"] == "blocked_by_controller_lifecycle"
    assert packet["lifecycle_contract_valid"] is True


def test_ag69f_forced_recovered_candidate_return_gets_fit_or_rejection() -> None:
    trace = _record_attempted(_trace(), result_count=0, accepted_url_count=0)
    _run_visibility(trace, [_secondary_recovered_source()])
    packet = classify_authority_lifecycle_forced_corridor(
        trace,
        corridor_name="irs_returned_candidate_fit_forced_official_current",
    )

    assert packet["candidate_return_status"] == "candidates_returned"
    assert packet["candidate_fit_state"] == "rejected_with_reason"
    assert packet["structured_candidate_rejections"]
    assert packet["final_evidence_state"] == "explained_absent"
    assert packet["remaining_failure_layer"] == "candidate_fit_visibility_layer"
    assert packet["lifecycle_contract_valid"] is True


def test_ag69f_returned_candidate_cannot_vanish_without_final_evidence_explanation() -> None:
    trace = _record_attempted(_trace())
    _run_visibility(
        trace,
        [_official_source()],
        final=[
            _official_source(
                url="https://www.irs.gov/ag69f-existing-protected",
            )
        ],
        max_final_evidence=1,
    )
    packet = classify_authority_lifecycle_forced_corridor(
        trace,
        corridor_name="irs_returned_candidate_visibility_forced_official_current",
    )

    assert packet["candidate_return_status"] == "candidates_returned"
    assert packet["candidate_fit_state"] == "matched_not_selected"
    assert packet["final_evidence_state"] == "explained_absent"
    assert "official_current_rules" in packet["final_evidence_explanation"]
    assert "recovered_results_not_visible_without_explanation" not in packet[
        "forbidden_state_codes"
    ]
    assert packet["lifecycle_contract_valid"] is True


def test_ag69f_canonical_technical_docs_corridor_classifies_success() -> None:
    trace = _trace(
        requirement_id="primary_source_documents",
        required_authority="primary_source_documents",
        claim_type="technical_reference",
        recovery_queries=("PostgreSQL MVCC official documentation",),
        required_source_classes=("primary_source_documents",),
    )
    _record_attempted(trace)
    _run_visibility(
        trace,
        [
            _official_source(
                url="https://www.postgresql.org/docs/ag69f-mvcc.html",
                source_class="primary_source_documents",
            )
        ],
    )
    packet = classify_authority_lifecycle_forced_corridor(
        trace,
        corridor_name="canonical_docs_forced_primary_source_documents",
    )

    assert packet["required_authority"] == "primary_source_documents"
    assert packet["candidate_fit_state"] == "matched_selected"
    assert packet["selected_authority_evidence"]
    assert packet["final_evidence_state"] == "visible"
    assert packet["citation_eligibility_projection"] == "eligible"
    assert packet["remaining_failure_layer"] == "none_lifecycle_succeeded"


def test_ag69f_legal_current_primary_corridor_is_represented_offline() -> None:
    trace = _trace(
        requirement_id="legal_or_regulatory_text",
        required_authority="legal_or_regulatory_text",
        claim_type="legal_current_primary",
        recovery_queries=("current primary legal text official fixture",),
        required_source_classes=("legal_or_regulatory_text",),
    )
    _record_attempted(trace)
    _run_visibility(
        trace,
        [
            _official_source(
                url="https://law.example/ag69f-current-primary",
                source_class="legal_or_regulatory_text",
            )
        ],
    )
    packet = classify_authority_lifecycle_forced_corridor(
        trace,
        corridor_name="legal_current_primary_offline_fixture",
    )

    assert packet["required_authority"] == "legal_or_regulatory_text"
    assert packet["selected_authority_evidence"][0]["requirement_id"] == (
        "legal_or_regulatory_text"
    )
    assert packet["remaining_failure_layer"] == "none_lifecycle_succeeded"
    assert packet["protected_surface"]["final_answer_behavior_changed"] is False


def test_ag69f_lower_tier_context_remains_partial_not_required_authority() -> None:
    lifecycle = AuthorityLifecycle(
        requirement_id="official_current_rules",
        required_authority="official_current_rules",
        claim_type="official_current_status",
        existing_evidence_fit=AuthorityEvidenceFitState.LOWER_TIER_CONTEXT_ONLY,
        lower_tier_context_state=LowerTierContextState.USED_AS_CONTEXT,
        recovery_needed=RecoveryNeededState.REQUIRED,
        satisfaction_state=AuthoritySatisfactionState.PARTIAL,
        final_posture=AuthorityFinalPosture.INSUFFICIENT_PARTIAL,
    )
    packet = classify_authority_lifecycle_forced_corridor(
        lifecycle.to_projection(),
        corridor_name="lower_tier_context_fallback",
    )

    assert packet["existing_evidence_fit"] == "lower_tier_context_only"
    assert packet["lower_tier_context_state"] == "used_as_context"
    assert packet["terminal_paths"] == ["controller_insufficient_partial_posture"]
    assert packet["remaining_failure_layer"] == "controller_insufficient_partial"
    assert packet["lifecycle_contract_valid"] is True


def test_ag69f_legacy_projection_export_fields_do_not_control_classification() -> None:
    trace = _record_attempted(_trace())
    trace.update(
        {
            "active_source_class_recovery_execution_attempted": False,
            "official_canonical_recovery_visibility_status": "not_observable",
            "candidate_return_status": "not_attempted",
            "authority_lifecycle_projection_used_as_control_input": False,
        }
    )
    packet = classify_authority_lifecycle_forced_corridor(
        trace,
        corridor_name="projection_poisoned_forced_official_current",
    )

    assert packet["execution_attempted"] is True
    assert packet["execution_state"] == "attempted"
    assert packet["projection_used_as_control_input"] is False
    assert "projection_used_as_control_input" not in packet["forbidden_state_codes"]


def test_ag69f_each_forced_corridor_produces_compact_classification_packet() -> None:
    packets = []
    for name, trace in (
        (
            "ssa_terminal",
            _record_attempted(
                _trace(terminal_stop_approved=True),
                result_count=0,
                accepted_url_count=0,
            ),
        ),
        (
            "ssa_weak",
            _record_attempted(
                _trace(weak_corpus_recovery_used=True, corpus_weak=True),
                result_count=0,
                accepted_url_count=0,
            ),
        ),
        ("irs_visibility", _run_visibility(_record_attempted(_trace()), [_official_source()])),
        (
            "canonical_docs",
            _run_visibility(
                _record_attempted(
                    _trace(
                        requirement_id="primary_source_documents",
                        required_authority="primary_source_documents",
                        claim_type="technical_reference",
                        required_source_classes=("primary_source_documents",),
                    )
                ),
                [
                    _official_source(
                        url="https://docs.example/ag69f",
                        source_class="primary_source_documents",
                    )
                ],
            ),
        ),
        (
            "legal_current_primary",
            _run_visibility(
                _record_attempted(
                    _trace(
                        requirement_id="legal_or_regulatory_text",
                        required_authority="legal_or_regulatory_text",
                        claim_type="legal_current_primary",
                        required_source_classes=("legal_or_regulatory_text",),
                    )
                ),
                [
                    _official_source(
                        url="https://law.example/ag69f",
                        source_class="legal_or_regulatory_text",
                    )
                ],
            ),
        ),
    ):
        packets.append(
            classify_authority_lifecycle_forced_corridor(trace, corridor_name=name)
        )

    required_keys = {
        "required_authority",
        "requirement_id",
        "existing_evidence_fit",
        "lower_tier_context_state",
        "recovery_needed",
        "recovery_action_state",
        "terminal_stop_state",
        "weak_corpus_state",
        "execution_state",
        "candidate_acquisition_state",
        "candidate_return_status",
        "candidate_fit_state",
        "final_evidence_state",
        "citation_eligibility_projection",
        "final_posture",
        "remaining_failure_layer",
    }
    for packet in packets:
        assert packet["schema_version"] == (
            AUTHORITY_LIFECYCLE_FORCED_CORRIDOR_CLASSIFICATION_SCHEMA_VERSION
        )
        assert packet["classification_compact"] is True
        assert packet["sanitized"] is True
        assert required_keys <= set(packet)
        assert packet["exactly_one_terminal_path"] is True


def test_ag69f_static_guard_keeps_protected_surfaces_closed() -> None:
    tree = ast.parse(_CLASSIFIER_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imports.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert imports.isdisjoint(
        {
            "openai",
            "requests",
            "core.pipeline_orchestrator",
            "core.prompts",
            "core.routing",
            "core.search_providers",
            "core.author",
            "core.economist",
            "core.source_classifier",
        }
    )
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8").casefold()
    assert "authority_lifecycle_forced_corridor_classification" not in pipeline_source
    assert "ag69f" not in pipeline_source
