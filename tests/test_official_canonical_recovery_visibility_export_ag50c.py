from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.controller_provider_search_allocation import (
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_OWNER,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
    PROVIDER_SEARCH_REVIEW_REQUEST,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.official_canonical_recovery_execution_admission import (
    OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY,
)
from core.official_canonical_recovery_visibility_export import (
    NOT_OBSERVABLE,
    OFFICIAL_CANONICAL_RECOVERY_DIAGNOSTICS_TITLE,
    OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_SCHEMA_VERSION,
    OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY,
    UNKNOWN,
    append_official_canonical_recovery_diagnostics_section,
    build_official_canonical_recovery_visibility_export,
    format_official_canonical_recovery_diagnostics_markdown,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "core" / "official_canonical_recovery_visibility_export.py"
_CLI_PATH = _ROOT / "proplex" / "__main__.py"


def _admission(**payload: Any) -> dict[str, Any]:
    base = {
        "admission_considered": True,
        "admission_eligible": True,
        "admission_used": True,
        "admission_skip_reason": None,
        "admission_blockers": [],
        "recovery_query_count": 1,
        "recovery_query_previews": ["canonical documentation PostgreSQL MVCC"],
    }
    base.update(payload)
    return {
        OFFICIAL_CANONICAL_RECOVERY_EXECUTION_ADMISSION_TRACE_KEY: {
            "schema_version": "official_canonical_recovery_execution_admission_ag50b_v1",
            "trace_mode": "recovery_execution_admission",
            "OfficialCanonicalRecoveryExecutionAdmission": base,
        }
    }


def _trace(**overrides: Any) -> dict[str, Any]:
    trace = {
        **_admission(),
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_skip_reason": None,
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_queries": [
            "canonical documentation PostgreSQL MVCC"
        ],
        "active_source_class_recovery_result_count": 3,
        "recovered_accepted_url_count": 1,
        "recovered_source_class_counts": {"primary_source_documents": 1},
        "recovered_source_tier_counts": {"official": 1},
        "recovered_official_or_primary_count": 1,
        "source_survival_final_evidence_official_or_canonical_count": 1,
        "source_survival_final_citation_official_or_canonical_count": 1,
    }
    trace.update(overrides)
    return trace


def _export(trace: dict[str, Any]) -> dict[str, Any]:
    packet = build_official_canonical_recovery_visibility_export(trace)
    assert packet["schema_version"] == (
        OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_SCHEMA_VERSION
    )
    return packet


def test_ag50c_full_ag50b_trace_visible_in_allowed_export() -> None:
    packet = _export(_trace())

    assert packet["admission_considered"] is True
    assert packet["admission_eligible"] is True
    assert packet["admission_used"] is True
    assert packet["recovery_query_count"] == 1
    assert packet["recovery_query_previews"] == [
        "canonical documentation PostgreSQL MVCC"
    ]
    assert packet["behavior_changed"] is False


def test_ag50c_source_class_recovery_execution_fields_render() -> None:
    packet = _export(_trace())
    rendered = format_official_canonical_recovery_diagnostics_markdown(packet)

    assert packet["source_class_recovery_eligible"] is True
    assert packet["source_class_recovery_used"] is True
    assert packet["source_class_recovery_provider_role"] == "source_class_recovery"
    assert packet["recovered_result_count"] == 3
    assert f"## {OFFICIAL_CANONICAL_RECOVERY_DIAGNOSTICS_TITLE}" in rendered
    assert "`source_class_recovery_provider_role`: source_class_recovery" in rendered


def test_ag50c_admitted_but_execution_not_attempted_layer() -> None:
    packet = _export(
        _trace(
            active_source_class_recovery_used=False,
            active_source_class_recovery_result_count=0,
            recovered_source_class_counts={},
            recovered_official_or_primary_count=0,
        )
    )

    assert packet["likely_next_failure_layer"] == "execution_not_attempted"


def test_ag50c_recovery_executed_candidate_return_unknown_layer() -> None:
    trace = _trace()
    trace.pop("active_source_class_recovery_result_count")
    packet = _export(trace)

    assert packet["recovered_result_count"] == UNKNOWN
    assert packet["candidate_return_visibility_status"] == NOT_OBSERVABLE
    assert packet["likely_next_failure_layer"] == "candidate_return_not_visible"


def test_ag50c_recovery_executed_zero_candidate_count_layer() -> None:
    packet = _export(
        _trace(
            active_source_class_recovery_result_count=0,
            recovered_source_class_counts={},
            recovered_official_or_primary_count=0,
        )
    )

    assert packet["recovered_result_count"] == 0
    assert packet["likely_next_failure_layer"] == (
        "recovery_executed_no_candidate_visibility"
    )


def test_ag50c_candidate_visible_but_not_accepted_layer() -> None:
    trace = _trace(
        active_source_class_recovery_result_count=2,
        candidate_official_or_canonical_count=1,
        source_survival_final_evidence_official_or_canonical_count=0,
        source_survival_final_citation_official_or_canonical_count=0,
    )
    trace.pop("recovered_official_or_primary_count")
    packet = _export(trace)

    assert packet["candidate_official_or_canonical_count"] == 1
    assert packet["accepted_or_readable_official_or_canonical_count"] == UNKNOWN
    assert packet["likely_next_failure_layer"] == (
        "official_canonical_candidate_visible_not_accepted"
    )


def test_ag50c_final_evidence_survived_but_citation_missing_layer() -> None:
    packet = _export(
        _trace(
            accepted_or_readable_official_or_canonical_count=1,
            source_survival_final_evidence_official_or_canonical_count=1,
            source_survival_final_citation_official_or_canonical_count=0,
        )
    )

    assert packet["final_evidence_official_or_canonical_count"] == 1
    assert packet["final_citation_official_or_canonical_count"] == 0
    assert packet["likely_next_failure_layer"] == "final_evidence_source_not_cited"


def test_ag50c_unknown_preservation_for_historical_records() -> None:
    packet = _export({})
    rendered = format_official_canonical_recovery_diagnostics_markdown({})

    assert packet["official_canonical_recovery_visibility_status"] == NOT_OBSERVABLE
    assert packet["admission_considered"] == UNKNOWN
    assert packet["source_class_recovery_used"] == UNKNOWN
    assert packet["likely_next_failure_layer"] == NOT_OBSERVABLE
    assert "controller_recovery_decision_observed" not in packet
    assert "controller_recovery_decision" not in packet
    assert "controller_recovery_retry_allowed" not in packet
    assert "admission_considered" in packet["unknown_fields"]
    assert OFFICIAL_CANONICAL_RECOVERY_DIAGNOSTICS_TITLE in rendered


def test_ag95rst_visibility_export_drops_controller_recovery_decision_fields() -> None:
    packet = _export(
        _trace(
            active_source_class_recovery_result_count=0,
            candidate_return_status="zero_candidates",
            controller_recovery_decision="request_provider_search_review",
            recovery_decision="request_provider_search_review",
        )
    )
    rendered = format_official_canonical_recovery_diagnostics_markdown(packet)

    assert "controller_recovery_decision_observed" not in packet
    assert "controller_recovery_decision" not in packet
    assert "controller_recovery_retry_allowed" not in packet
    assert "`controller_recovery_decision_observed`:" not in rendered
    assert "`controller_recovery_decision`:" not in rendered
    assert "`controller_recovery_retry_allowed`:" not in rendered


def test_ag95rst_visibility_export_observes_canonical_provider_review_request() -> None:
    allocation_trace = {
        "schema_version": "canonical_provider_search_allocation_gate_ag95q_v1",
        "trace_mode": "canonical_provider_review_allocation_execution",
        "ProviderSearchAllocation": {
            "schema_version": "canonical_provider_search_allocation_gate_ag95q_v1",
            "allocation_owner": PROVIDER_SEARCH_ALLOCATION_OWNER,
            "mechanical_owner": "source_class_recovery_runner",
            "decision": PROVIDER_SEARCH_REVIEW_REQUEST,
            "decision_reason": "no_candidate_acquired_provider_search_review_needed",
            "candidate_state_summary": (
                "no_plausible_official_current_candidate_acquired"
            ),
            "allocation_action": "record_provider_search_review_request",
            "allocation_shape": "bounded_record_plus_execution_provider_search_review",
            "execution_mode": "record_plus_optional_bounded_existing_provider_call",
            "provider_policy_unchanged": True,
            "provider_selection_unchanged": True,
            "search_depth_policy_unchanged": True,
            "query_strategy_unchanged": True,
            "source_constraints_unchanged": True,
            "new_provider_added": False,
            "provider_swap": False,
            "unbounded_depth": False,
            "live_validation_used": False,
            "final_answer_behavior_unchanged": True,
            "citation_behavior_unchanged": True,
        },
        PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY: {
            "schema_version": "canonical_provider_review_allocation_execution_ag95q_v1",
            "allocation_owner": PROVIDER_SEARCH_ALLOCATION_OWNER,
            "mechanical_owner": "source_class_recovery_runner",
            "authorized_decision": PROVIDER_SEARCH_REVIEW_REQUEST,
            "authorized_executor_action": "record_provider_search_review_request",
            "bounded_profile": "bounded_existing_source_class_recovery_profile_v1",
            "execution_mode": "bounded_existing_provider_allocation_unexecutable",
            "executed": False,
            "execution_attempted": False,
            "unexecutable_reason": "missing_execution_context",
            "provider_role": "source_class_recovery",
            "search_depth": "basic",
            "query_count": 1,
            "result_count": 0,
            "new_url_count": 0,
            "allocation_result_summary_count": 0,
            "provider_policy_unchanged": True,
            "provider_selection_unchanged": True,
            "search_depth_policy_unchanged": True,
            "query_strategy_unchanged": True,
            "source_constraints_unchanged": True,
            "new_provider_added": False,
            "provider_swap": False,
            "unbounded_depth": False,
            "live_validation_used": False,
            "final_answer_behavior_unchanged": True,
            "citation_behavior_unchanged": True,
            "raw_payload_exposed": False,
        },
    }
    packet = _export(
        _trace(
            **{
                PROVIDER_SEARCH_ALLOCATION_TRACE_KEY: allocation_trace,
                "controller_recovery_decision_trace": {
                    "ControllerRecoveryDecision": {
                        "decision": "retry_recovery",
                        "retry_allowed": True,
                    }
                },
            },
        )
    )
    rendered = format_official_canonical_recovery_diagnostics_markdown(packet)

    assert "controller_recovery_decision_observed" not in packet
    assert "controller_recovery_decision" not in packet
    assert packet["provider_search_allocation_trace"]["allocation_owner"] == (
        PROVIDER_SEARCH_ALLOCATION_OWNER
    )
    assert packet["provider_search_allocation_trace"]["decision"] == (
        PROVIDER_SEARCH_REVIEW_REQUEST
    )
    assert packet["provider_search_allocation_execution_trace"]["query_count"] == 1
    assert "`provider_search_allocation_trace`:" in rendered
    assert "`controller_recovery_decision`:" not in rendered


def test_ag50c_raw_artifact_guard_drops_or_redacts_private_fields() -> None:
    packet = _export(
        {
            **_admission(
                recovery_query_previews=[
                    "raw prompt protected_marker_value TOKEN=super-secret"
                ]
            ),
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_result_count": 1,
            "raw_provider_payload": {"body": "provider_payload should not leak"},
            "raw_prompt": "raw prompt should not leak",
            "db_row": {"private": "db row should not leak"},
            "cache": "C:/private/cache/path",
            "logs": "private log should not leak",
            "output_packet": "generated packet should not leak",
            "sec" + "ret": "sensitive value should not leak",
            "tok" + "en": "credential value should not leak",
            "full_trace": {"too": "much"},
        }
    )
    payload = json.dumps(packet, sort_keys=True)

    assert "provider_payload should not leak" not in payload
    assert "raw prompt should not leak" not in payload
    assert "db row should not leak" not in payload
    assert "C:/private/cache/path" not in payload
    assert "private log should not leak" not in payload
    assert "generated packet should not leak" not in payload
    assert "sensitive value should not leak" not in payload
    assert "credential value should not leak" not in payload
    assert packet["recovery_query_previews"] == ["[redacted protected material]"]


def test_ag50c_query_previews_are_compact_deduped_and_capped() -> None:
    long_query = "canonical documentation " + ("PostgreSQL MVCC " * 30)
    packet = _export(
        {
            **_admission(
                recovery_query_previews=[
                    long_query,
                    long_query,
                    "official current source one",
                    "official current source two",
                    "official current source three",
                ],
                recovery_query_count=5,
            ),
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_result_count": 1,
        }
    )

    assert 1 <= len(packet["recovery_query_previews"]) <= 3
    assert len(set(packet["recovery_query_previews"])) == len(
        packet["recovery_query_previews"]
    )
    assert all(len(item) <= 140 for item in packet["recovery_query_previews"])


def test_ag50c_report_output_section_contains_visible_fields() -> None:
    output = append_official_canonical_recovery_diagnostics_section(
        "Final answer body.",
        _trace(),
    )

    assert output.startswith("Final answer body.")
    assert f"## {OFFICIAL_CANONICAL_RECOVERY_DIAGNOSTICS_TITLE}" in output
    assert (
        "`likely_next_failure_layer`: recovery_lane_source_citation_observed"
        in output
    )
    assert (
        "`likely_next_failure_layer_custody_interpretation`: "
        "recovery_lane_observation_not_controller_custody_status"
    ) in output


def test_ag50c_runtime_projection_attaches_export_to_checkpoint() -> None:
    execution_trace = {
        **_trace(),
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
    }

    returned = attach_passive_runtime_projection_traces(execution_trace)
    trace = returned[OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY]

    assert returned is execution_trace
    assert (
        returned[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY
        ]
        == trace
    )
    assert trace["OfficialCanonicalRecoveryVisibility"]["behavior_changed"] is False


def test_ag50c_behavior_neutrality_and_cli_only_report_wiring() -> None:
    packet = _export(_trace())
    assert packet["behavior_changed"] is False

    protected_behavior_files = [
        _ROOT / "core" / "pipeline.py",
        _ROOT / "core" / "routing.py",
        _ROOT / "core" / "prompts.py",
        _ROOT / "core" / "source_classifier.py",
        _ROOT / "core" / "source_class_recovery_executor.py",
    ]
    for path in protected_behavior_files:
        assert "official_canonical_recovery_visibility_export" not in (
            path.read_text(encoding="utf-8")
        )

    assert "append_official_canonical_recovery_diagnostics_section" in (
        _CLI_PATH.read_text(encoding="utf-8")
    )


def test_ag50c_static_protected_surface_guard() -> None:
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
    source = _MODULE_PATH.read_text(encoding="utf-8").casefold()
    forbidden_surface_markers = {
        "build_controller_recovery_decision",
        "hydrated_authoritative_lifecycle_projection",
        "process_search_queries",
        "choose_supplemental_search_depth",
        "select_providers",
        "author_prompt",
        "economist",
    }
    assert forbidden_surface_markers.isdisjoint(source.split())
