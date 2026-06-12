from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.official_canonical_recovery_query_acquisition import (
    OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_SCHEMA_VERSION,
    OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY,
    apply_official_canonical_recovery_query_acquisition,
)
from core.official_current_source_custody import (
    OfficialCurrentCustodyStatus,
    OfficialCurrentSourceCustodyState,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "core" / "official_canonical_recovery_query_acquisition.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_ACTION_HELPER_PATH = _ROOT / "core" / "authoritative_source_action.py"
_ORCHESTRATOR_ADAPTER_PATH = (
    _ROOT / "core" / "authoritative_source_action_orchestrator_adapter.py"
)


def _acquisition(
    trace: dict[str, Any],
    recommendation: dict[str, Any] | None = None,
    *,
    existing_blockers: tuple[str, ...] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = apply_official_canonical_recovery_query_acquisition(
        recommendation=recommendation or {},
        runtime_trace=trace,
        existing_blockers=existing_blockers,
    )
    packet = result.trace
    assert (
        packet["schema_version"]
        == OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_SCHEMA_VERSION
    )
    assert packet["trace_mode"] == "recovery_query_acquisition_repair"
    return result.recommendation, packet["OfficialCanonicalRecoveryQueryAcquisition"]


def _accepted_custody(source_class: str) -> dict[str, Any]:
    return (
        OfficialCurrentSourceCustodyState()
        .require(source_class)
        .record_candidate_disposition(
            f"official_current_source:{source_class}",
            status=OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED,
            candidate_id=f"https://docs.example/{source_class}",
            reason="accepted_authority_custody",
        )
        .to_dict()
    )


def test_ag50a_canonical_technical_obligation_adds_generic_documentation_query() -> None:
    recommendation, trace = _acquisition(
        {
            "query_preview": (
                "Explain how SQLite write-ahead logging works, why it improves "
                "concurrency, and when WAL mode is a bad idea."
            ),
            "query_type": "technical_reference",
        },
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
    )

    assert trace["acquisition_repair_considered"] is True
    assert trace["acquisition_repair_eligible"] is True
    assert trace["acquisition_repair_used"] is True
    assert trace["required_source_classes"] == ["primary_source_documents"]
    assert trace["generic_query_intent"] == "canonical_documentation"
    assert trace["added_recovery_query_count"] == 2
    assert trace["source_specific_terms_present"] is False
    assert recommendation["source_class_recovery_queries"] == [
        (
            "official documentation Explain how SQLite write-ahead logging "
            "works, why it improves concurrency, and when WAL mode is a bad idea."
        ),
        (
            "reference documentation Explain how SQLite write-ahead logging "
            "works, why it improves concurrency, and when WAL mode is a bad idea."
        ),
    ]


def test_ag50a_official_current_obligation_adds_generic_official_query() -> None:
    recommendation, trace = _acquisition(
        {
            "query_preview": (
                "What are the current official eligibility rules for a federal "
                "benefit in 2026?"
            ),
            "query_type": "official_current_status",
        },
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["official_current_rules"],
            "source_class_recovery_queries": [],
        },
    )

    assert trace["acquisition_repair_used"] is True
    assert trace["required_source_classes"] == ["official_current_rules"]
    assert trace["generic_query_intent"] == "official_current_source"
    assert recommendation["source_class_recovery_queries"] == [
        (
            "federal agency official current eligibility threshold status rule "
            "What are the current official eligibility rules for a federal benefit in 2026?"
        ),
        (
            "official current source What are the current official eligibility "
            "rules for a federal benefit in 2026?"
        ),
    ]


def test_ag50a_preserves_existing_query_and_appends_needed_generic_query() -> None:
    recommendation, trace = _acquisition(
        {"query_preview": "Explain how a database storage engine protocol works."},
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": ["database storage engine overview"],
        },
    )

    assert recommendation["source_class_recovery_queries"] == [
        "database storage engine overview",
        "official documentation Explain how a database storage engine protocol works.",
        "reference documentation Explain how a database storage engine protocol works.",
    ]
    assert trace["existing_recovery_query_count"] == 1
    assert trace["added_recovery_query_count"] == 2


def test_ag50a_existing_query_with_weak_intent_adds_official_reference_variants() -> None:
    recommendation, trace = _acquisition(
        {"query_preview": "Explain how a database write-ahead log mode works."},
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [
                "canonical documentation database write-ahead log mode"
            ],
        },
    )

    assert trace["acquisition_repair_used"] is True
    assert trace["added_recovery_query_count"] == 2
    assert recommendation["source_class_recovery_queries"] == [
        "canonical documentation database write-ahead log mode",
        "official documentation Explain how a database write-ahead log mode works.",
        "reference documentation Explain how a database write-ahead log mode works.",
    ]


def test_ag50a_existing_official_reference_profile_prevents_duplicate() -> None:
    recommendation, trace = _acquisition(
        {"query_preview": "Explain how a database write-ahead log mode works."},
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [
                "official documentation database write-ahead log mode",
                "reference documentation database write-ahead log mode",
            ],
        },
    )

    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == "existing_query_satisfies_intent"
    assert recommendation["source_class_recovery_queries"] == [
        "official documentation database write-ahead log mode",
        "reference documentation database write-ahead log mode",
    ]


def test_ag50a_preferred_only_current_context_is_noop() -> None:
    recommendation, trace = _acquisition(
        {
            "query_preview": (
                "What happened this week in the transit strike, and what should "
                "commuters know?"
            ),
            "query_type": "current_event_context",
        },
        {"source_class_recovery_recommended": False},
    )

    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == (
        "preferred_obligation_advisory_only"
    )
    assert recommendation == {"source_class_recovery_recommended": False}


def test_ag50a_conceptual_explainer_is_noop() -> None:
    recommendation, trace = _acquisition(
        {
            "query_preview": "Explain why compound interest matters for beginners.",
            "query_type": "conceptual_explainer",
        },
        {"source_class_recovery_recommended": False},
    )

    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == "obligation_not_required"
    assert "source_class_recovery_queries" not in recommendation


def test_ag50a_proxy_qualitative_primary_source_negative_control_is_noop() -> None:
    recommendation, trace = _acquisition(
        {
            "query_preview": (
                "give a proxy or qualitative framing for the private category"
            ),
            "query_type": "other",
            "core_topic": "private category proxy qualitative framing",
            "primary_entity": "private category",
        },
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
    )

    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == (
        "required_source_class_not_visible_or_supported_for_query"
    )
    assert recommendation["source_class_recovery_queries"] == []


def test_ag50a_unknown_obligation_is_noop() -> None:
    recommendation, trace = _acquisition({}, {"source_class_recovery_recommended": False})

    assert trace["acquisition_repair_considered"] is False
    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == "obligation_unknown"
    assert recommendation == {"source_class_recovery_recommended": False}


def test_ag50a_aggregate_satisfied_required_class_does_not_block_query_addition() -> None:
    recommendation, trace = _acquisition(
        {
            "query_preview": "Explain how a database library protocol works.",
            "source_class_satisfaction_status": {
                "primary_source_documents": "satisfied_strong"
            },
            "source_class_strong_satisfaction_counts": {
                "primary_source_documents": 1
            },
        },
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
    )

    assert trace["acquisition_repair_used"] is True
    assert trace["acquisition_repair_skip_reason"] is None
    assert trace["required_source_classes"] == ["primary_source_documents"]
    assert recommendation["source_class_recovery_queries"] == [
        "official documentation Explain how a database library protocol works.",
        "reference documentation Explain how a database library protocol works.",
    ]


def test_ag50a_custody_backed_required_class_blocks_query_addition() -> None:
    recommendation, trace = _acquisition(
        {
            "query_preview": "Explain how a database library protocol works.",
            "official_current_source_custody": _accepted_custody(
                "primary_source_documents"
            ),
        },
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
    )

    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == "existing_source_class_satisfied"
    assert trace["required_source_classes"] == []
    assert recommendation["source_class_recovery_queries"] == []


@pytest.mark.parametrize(
    "blocker",
    [
        "blocked_by_iteration_budget",
        "terminal_stop_approved",
        "weak_corpus_recovery_owns_path",
        "active_recovery_already_used",
        "blocked_by_provider_policy_change_required",
        "blocked_by_search_depth_escalation_required",
    ],
)
def test_ag50a_runtime_blockers_prevent_query_acquisition(blocker: str) -> None:
    recommendation, trace = _acquisition(
        {"query_preview": "Explain how a database storage protocol works."},
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
        existing_blockers=(blocker,),
    )

    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == "existing_runtime_blocker"
    assert trace["acquisition_repair_blockers"] == [blocker]
    assert recommendation["source_class_recovery_queries"] == []


def test_ag50a_runtime_boolean_blockers_prevent_query_acquisition() -> None:
    _recommendation, trace = _acquisition(
        {
            "query_preview": "Explain how a database storage protocol works.",
            "query_redundancy_skipped": True,
        },
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
    )

    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_blockers"] == ["blocked_by_redundant_query"]


def test_ag50a_source_specific_overfit_guard() -> None:
    module_source = _MODULE_PATH.read_text(encoding="utf-8").casefold()
    forbidden_terms = {
        "sqlite.org",
        "nasa.gov",
        "postgresql.org",
    }

    assert forbidden_terms.isdisjoint(module_source.split())


def test_ag50a_helper_keeps_protected_surfaces_out() -> None:
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
        "core.answer_contract_runtime_handoff",
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

    helper_source = _ACTION_HELPER_PATH.read_text(encoding="utf-8")
    adapter_source = _ORCHESTRATOR_ADAPTER_PATH.read_text(encoding="utf-8")
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "apply_official_canonical_recovery_query_acquisition" in helper_source
    assert "build_authoritative_source_obligation_state_and_action(" in adapter_source
    assert "build_authoritative_source_action_orchestrator_handoff(" in pipeline_source


def test_ag50a_output_does_not_set_provider_depth_ranking_or_answer_behavior() -> None:
    recommendation, trace = _acquisition(
        {"query_preview": "Explain how a database storage protocol works."},
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [],
        },
    )
    forbidden_output_keys = {
        "provider_role",
        "provider_name",
        "search_depth",
        "ranking_policy",
        "returned_source_classification",
        "final_answer_behavior",
    }

    assert forbidden_output_keys.isdisjoint(recommendation)
    assert trace["provider_policy_unchanged"] is True
    assert trace["depth_policy_unchanged"] is True
    assert trace["ranking_unchanged"] is True
    assert trace["final_answer_behavior_unchanged"] is True
    assert trace["protected_surface"]["retrieve_targeted_promoted"] is False


def test_ag50a_runtime_projection_mirrors_trace_into_checkpoint() -> None:
    acquisition_trace = {
        "schema_version": OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_SCHEMA_VERSION,
        "trace_mode": "recovery_query_acquisition_repair",
        "OfficialCanonicalRecoveryQueryAcquisition": {
            "acquisition_repair_used": True
        },
    }
    execution_trace = {
        "run_id": "ag50a",
        OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY: acquisition_trace,
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
    }

    returned = attach_passive_runtime_projection_traces(execution_trace)

    assert returned is execution_trace
    assert (
        returned[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            OFFICIAL_CANONICAL_RECOVERY_QUERY_ACQUISITION_TRACE_KEY
        ]
        == acquisition_trace
    )
