from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.official_source_obligation_bridge import (
    OFFICIAL_SOURCE_OBLIGATION_BRIDGE_SCHEMA_VERSION,
    OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY,
    apply_official_source_obligation_bridge,
)
from core.official_source_obligation_candidate_visibility import UNKNOWN
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "core" / "official_source_obligation_bridge.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _bridge(
    trace: dict[str, Any],
    recommendation: dict[str, Any] | None = None,
    *,
    existing_blockers: tuple[str, ...] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = apply_official_source_obligation_bridge(
        recommendation=recommendation or {},
        runtime_trace=trace,
        existing_blockers=existing_blockers,
    )
    packet = result.trace
    assert packet["schema_version"] == OFFICIAL_SOURCE_OBLIGATION_BRIDGE_SCHEMA_VERSION
    return result.recommendation, packet["OfficialSourceObligationBridge"]


def test_ag49c_official_numeric_obligation_maps_to_recovery_input() -> None:
    recommendation, bridge = _bridge(
        {
            "query_preview": (
                "What are the 2026 vs 2025 Social Security COLA, taxable "
                "maximum, earnings-test limits, and SSI federal payment amounts?"
            ),
            "query_type": "quantitative_comparison",
        },
        {
            "source_class_recovery_recommended": False,
            "missing_expected_source_classes": [],
            "source_class_recovery_queries": [],
        },
    )

    assert bridge["bridge_considered"] is True
    assert bridge["bridge_eligible"] is True
    assert bridge["bridge_used"] is True
    assert bridge["bridge_required_source_classes"] == ["official_current_rules"]
    assert bridge["bridge_recovery_recommended"] is True
    assert recommendation["missing_expected_source_classes"] == [
        "official_current_rules"
    ]
    assert recommendation["source_class_recovery_queries"] == []
    assert bridge["behavior_changed"] is True


def test_ag49c_canonical_technical_reference_maps_without_specific_rule() -> None:
    recommendation, bridge = _bridge(
        {
            "query_preview": (
                "Explain how SQLite write-ahead logging works, why it improves "
                "concurrency, and when WAL mode is a bad idea."
            ),
            "query_type": "technical_reference",
        },
        {"source_class_recovery_recommended": False},
    )

    assert bridge["bridge_eligible"] is True
    assert bridge["bridge_used"] is True
    assert bridge["bridge_required_source_classes"] == ["primary_source_documents"]
    assert recommendation["missing_expected_source_classes"] == [
        "primary_source_documents"
    ]
    module_text = _MODULE_PATH.read_text(encoding="utf-8").casefold()
    assert "sqlite.org" not in module_text
    assert "ssa.gov" not in module_text


def test_ag49c_preferred_current_event_context_is_advisory_only() -> None:
    recommendation, bridge = _bridge(
        {
            "query_preview": (
                "What happened this week in the transit strike, and what should "
                "commuters know?"
            ),
            "query_type": "current_event_context",
        },
        {"source_class_recovery_recommended": False},
    )

    assert bridge["bridge_eligible"] is False
    assert bridge["bridge_used"] is False
    assert bridge["bridge_skip_reason"] == "preferred_obligation_advisory_only"
    assert recommendation == {"source_class_recovery_recommended": False}


def test_ag49c_conceptual_explainer_does_not_force_recovery() -> None:
    recommendation, bridge = _bridge(
        {
            "query_preview": "Explain why compound interest matters for beginners.",
            "query_type": "conceptual_explainer",
        },
        {"source_class_recovery_recommended": False},
    )

    assert bridge["bridge_eligible"] is False
    assert bridge["bridge_used"] is False
    assert bridge["bridge_skip_reason"] == "obligation_not_required"
    assert "missing_expected_source_classes" not in recommendation


def test_ag49c_unknown_obligation_leaves_inputs_unchanged() -> None:
    recommendation, bridge = _bridge({}, {"source_class_recovery_recommended": False})

    assert bridge["bridge_considered"] is False
    assert bridge["bridge_eligible"] is False
    assert bridge["bridge_used"] is False
    assert bridge["bridge_skip_reason"] == "obligation_unknown"
    assert bridge["bridge_candidate_query_available"] == UNKNOWN
    assert recommendation == {"source_class_recovery_recommended": False}


def test_ag49c_existing_required_source_class_satisfied_blocks_bridge() -> None:
    recommendation, bridge = _bridge(
        {
            "query_preview": (
                "Explain how write-ahead logging works in a database library."
            ),
            "query_type": "technical_reference",
            "source_class_satisfaction_status": {
                "primary_source_documents": "satisfied_strong"
            },
            "source_class_strong_satisfaction_counts": {
                "primary_source_documents": 1
            },
        },
        {"source_class_recovery_recommended": False},
    )

    assert bridge["bridge_eligible"] is False
    assert bridge["bridge_used"] is False
    assert bridge["bridge_skip_reason"] == "existing_source_class_satisfied"
    assert bridge["bridge_satisfied_source_classes"] == ["primary_source_documents"]
    assert "missing_expected_source_classes" not in recommendation


def test_ag49c_budget_and_terminal_blockers_remain_authoritative() -> None:
    recommendation, bridge = _bridge(
        {
            "query_preview": (
                "What are the current official eligibility rules for a federal "
                "benefit in 2026?"
            ),
            "query_type": "official_current_status",
        },
        {"source_class_recovery_recommended": False},
        existing_blockers=("blocked_by_iteration_budget", "terminal_stop_approved"),
    )

    assert bridge["bridge_eligible"] is False
    assert bridge["bridge_used"] is False
    assert bridge["bridge_skip_reason"] == "existing_runtime_blocker"
    assert bridge["bridge_blockers"] == [
        "blocked_by_iteration_budget",
        "terminal_stop_approved",
    ]
    assert recommendation == {"source_class_recovery_recommended": False}


def test_ag49c_preserves_existing_recovery_reason_when_adding_class() -> None:
    recommendation, bridge = _bridge(
        {
            "query_preview": (
                "What are the current official eligibility rules for a federal "
                "benefit in 2026?"
            ),
            "query_type": "official_current_status",
        },
        {
            "source_class_recovery_recommended": True,
            "source_class_recovery_reason": (
                "answer_contract_legal_text_gap:legal_or_regulatory_text"
            ),
            "missing_expected_source_classes": ["legal_or_regulatory_text"],
        },
    )

    assert bridge["bridge_used"] is True
    assert recommendation["missing_expected_source_classes"] == [
        "legal_or_regulatory_text",
        "official_current_rules",
    ]
    assert recommendation["source_class_recovery_reason"] == (
        "answer_contract_legal_text_gap:legal_or_regulatory_text"
    )


def test_ag49c_does_not_create_new_provider_role_or_executor() -> None:
    recommendation, bridge = _bridge(
        {
            "query_preview": (
                "Explain how a database write-ahead log mode works and its "
                "tradeoffs."
            ),
            "query_type": "technical_reference",
        },
        {"source_class_recovery_recommended": False},
    )

    assert "provider_role" not in recommendation
    assert "active_source_class_recovery_provider_role" not in recommendation
    assert "search_depth" not in recommendation
    assert "source_class_recovery_queries" not in recommendation
    assert bridge["protected_surface"]["retrieve_targeted_promoted"] is False
    assert bridge["protected_surface"]["provider_policy_unchanged"] is True
    assert bridge["protected_surface"]["depth_policy_unchanged"] is True
    assert bridge["protected_surface"]["generated_query_text_unchanged"] is True


def test_ag49c_preserves_unknown_candidate_and_acceptance_stage_visibility() -> None:
    _recommendation, bridge = _bridge(
        {
            "query_preview": (
                "Explain how write-ahead logging works in a database library."
            ),
            "query_type": "technical_reference",
            "source_survival_final_evidence_official_or_canonical_count": 1,
            "source_survival_final_citation_official_or_canonical_count": 1,
        },
        {"source_class_recovery_recommended": False},
    )

    assert bridge["bridge_candidate_query_available"] == UNKNOWN
    assert bridge["bridge_candidate_query_count"] == UNKNOWN
    assert bridge["bridge_candidate_query_previews"] == []


def test_ag49c_runtime_attachment_mirrors_bridge_into_checkpoint() -> None:
    execution_trace = {
        "run_id": "ag49c",
        "query_preview": (
            "Explain how write-ahead logging works in a database library."
        ),
        "query_type": "technical_reference",
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
    }

    returned = attach_passive_runtime_projection_traces(execution_trace)

    assert returned is execution_trace
    assert OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY in returned
    assert (
        returned[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY
        ]
        == returned[OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY]
    )
    bridge = returned[OFFICIAL_SOURCE_OBLIGATION_BRIDGE_TRACE_KEY][
        "OfficialSourceObligationBridge"
    ]
    assert bridge["bridge_required_source_classes"] == [
        "primary_source_documents"
    ]


def test_ag49c_static_guards_keep_protected_surfaces_out() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden_modules = {
        "core.db",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.provider",
        "core.providers",
        "core.routing",
        "core.run_logging",
        "core.search_providers",
        "core.source_class_recovery_executor",
        "core.source_classifier",
    }
    assert imported.isdisjoint(forbidden_modules)

    source = _MODULE_PATH.read_text(encoding="utf-8")
    forbidden_surface_markers = {
        "retrieve_targeted_provider_role",
        "process_search_queries",
        "choose_supplemental_search_depth",
        "select_providers",
        "author_prompt",
        "economist",
    }
    assert forbidden_surface_markers.isdisjoint(source.casefold().split())
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "apply_official_source_obligation_bridge" in pipeline_source
