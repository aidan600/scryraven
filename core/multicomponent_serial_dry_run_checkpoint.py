"""Serial dry-run checkpoint over multi-component graph/admission refs.

The checkpoint is a reviewable composition artifact over existing
ComponentWorkNode, ComponentWorkGraph, Cross-Component Analyst Workbench,
synthesis D-prime validation, and RunKernel graph/synthesis admission refs. It
does not execute or schedule graph work, dispatch retrieval, perform Workbench
or D-prime work, perform RunKernel admission, create SufficiencyReadiness/FAP/
Author/source display, render citations, or claim product correctness.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_work_graph import (
    COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
    GRAPH_CLOSED_DOWNSTREAM_FLAGS,
    GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
    validate_component_work_graph_v0,
)
from core.component_work_node import COMPONENT_WORK_NODE_V0_SCHEMA_VERSION
from core.cross_component_analyst_workbench import (
    CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION,
    validate_cross_component_analyst_workbench_v0,
)
from core.dprime_synthesis_validation import (
    DPRIME_SYNTHESIS_VALIDATION_V0_SCHEMA_VERSION,
    dprime_synthesis_validation_v0_ref,
    validate_dprime_synthesis_validation_v0,
)
from core.runkernel_component_graph_admission import (
    ADMISSION_STATUS_ADMISSION_REQUESTED,
    ADMISSION_STATUS_ADMITTED,
    ADMISSION_STATUS_ADMITTED_WITH_CAVEATS,
    ADMISSION_STATUS_BLOCKED,
    ADMISSION_STATUS_CHALLENGED,
    ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED,
    ADMISSION_STATUS_DRAFT,
    ADMISSION_STATUS_RECOVERY_AUTHORIZED,
    ADMISSION_STATUS_UNSUPPORTED,
    ALLOWED_ADMISSION_STATUSES,
    RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_SCHEMA_VERSION,
    runkernel_component_graph_admission_v0_ref,
    validate_runkernel_component_graph_admission_v0,
)

MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_SCHEMA_VERSION = (
    "multicomponent_serial_dry_run_checkpoint_v0"
)
MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_PHASE = (
    "MULTICOMPONENT-SERIAL-DRY-RUN-PLANNING-CHECKPOINT-01"
)
MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_RUNTIME_CONSUMER = (
    "future Sufficiency/FAP phases after explicit licensing"
)

SERIAL_DRY_RUN_STATUS_DRAFT = "draft"
SERIAL_DRY_RUN_STATUS_REPRESENTED = "represented"
SERIAL_DRY_RUN_STATUS_REPRESENTED_WITH_CAVEATS = "represented_with_caveats"
SERIAL_DRY_RUN_STATUS_BLOCKED = "blocked"
SERIAL_DRY_RUN_STATUS_CHALLENGED = "challenged"
SERIAL_DRY_RUN_STATUS_RECOVERY_AUTHORIZED = "recovery_authorized"
SERIAL_DRY_RUN_STATUS_UNSUPPORTED = "unsupported"

REPRESENTED_SERIAL_STATUSES = frozenset(
    {
        SERIAL_DRY_RUN_STATUS_REPRESENTED,
        SERIAL_DRY_RUN_STATUS_REPRESENTED_WITH_CAVEATS,
    }
)
ALLOWED_SERIAL_DRY_RUN_STATUSES = frozenset(
    {
        SERIAL_DRY_RUN_STATUS_DRAFT,
        SERIAL_DRY_RUN_STATUS_REPRESENTED,
        SERIAL_DRY_RUN_STATUS_REPRESENTED_WITH_CAVEATS,
        SERIAL_DRY_RUN_STATUS_BLOCKED,
        SERIAL_DRY_RUN_STATUS_CHALLENGED,
        SERIAL_DRY_RUN_STATUS_RECOVERY_AUTHORIZED,
        SERIAL_DRY_RUN_STATUS_UNSUPPORTED,
    }
)

SERIAL_CHECKPOINT_CLOSED_DOWNSTREAM_FLAGS = {
    "serial_checkpoint_executed_graph": False,
    "serial_checkpoint_scheduled_graph": False,
    "serial_checkpoint_created_runtime_parallelism": False,
    "serial_checkpoint_created_budget_lease": False,
    "serial_checkpoint_dispatched_search": False,
    "serial_checkpoint_called_provider": False,
    "serial_checkpoint_called_model": False,
    "serial_checkpoint_called_fetch_read": False,
    "serial_checkpoint_called_retrieval": False,
    "serial_checkpoint_performed_cross_component_analysis": False,
    "serial_checkpoint_performed_dprime_validation": False,
    "serial_checkpoint_performed_runkernel_admission": False,
    "serial_checkpoint_created_sufficiency_readiness": False,
    "serial_checkpoint_created_fap": False,
    "serial_checkpoint_created_author_output": False,
    "serial_checkpoint_created_source_display": False,
    "serial_checkpoint_rendered_citations": False,
    "serial_checkpoint_claimed_source_obligation_satisfaction": False,
    "serial_checkpoint_claimed_product_correctness": False,
    "serial_checkpoint_claimed_friend_mvp": False,
}

SERIAL_CHECKPOINT_RAW_PRIVATE_RETENTION_FALSE_FLAGS = {
    "api_keys_retained": False,
    "authorization_retained": False,
    "cookies_retained": False,
    "headers_retained": False,
    "passwords_retained": False,
    "secrets_retained": False,
    "tokens_retained": False,
    "env_retained": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_source_text_retained": False,
    "raw_text_retained": False,
    "raw_page_text_retained": False,
    "raw_page_content_retained": False,
    "source_text_retained": False,
    "bounded_text_retained": False,
    "full_text_retained": False,
    "html_retained": False,
    "raw_html_retained": False,
    "raw_prompt_retained": False,
    "full_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "cache_rows_retained": False,
    "db_rows_retained": False,
    "full_trace_retained": False,
    "local_output_packet_retained": False,
}

SERIAL_CHECKPOINT_NONCLAIMS = (
    "The serial dry-run checkpoint is a review artifact over typed refs only.",
    "The serial dry-run checkpoint does not execute graph nodes, schedule graph work, create runtime parallelism, or create budget leases.",
    "The serial dry-run checkpoint does not dispatch search, call providers, call models, call fetch/read, or call retrieval.",
    "The serial dry-run checkpoint does not perform Cross-Component Analyst work, D-prime validation, or RunKernel admission.",
    "The serial dry-run checkpoint does not create SufficiencyReadiness, FAP, Author output, source display, rendered citations, source-obligation satisfaction, product correctness, or friend-level MVP.",
)

_REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "phase",
    "checkpoint_id",
    "checkpoint_digest",
    "parent_run_id",
    "user_query_ref",
    "scenario_kind",
    "serial_dry_run_status",
    "component_node_refs",
    "parent_graph_ref",
    "dependency_edge_refs",
    "cross_component_analyst_ref",
    "dprime_synthesis_validation_ref",
    "runkernel_graph_admission_ref",
    "admitted_synthesis_refs",
    "blocked_synthesis_refs",
    "challenge_refs",
    "recovery_authorization_refs",
    "required_caveat_refs",
    "preserved_nonclaim_refs",
    "blocker_refs",
    "serial_trace_refs",
    "review_packet_refs",
    "closed_downstream_flags",
    "raw_private_retention_flags",
    "nonclaims",
)

_FORBIDDEN_NORMALIZED_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "bounded_text",
        "cache_row",
        "cookie",
        "cookies",
        "db_row",
        "env",
        "full_prompt",
        "full_text",
        "full_trace",
        "headers",
        "html",
        "local_output_packet",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "raw_html",
        "raw_model_response",
        "raw_model_responses",
        "raw_page_content",
        "raw_page_text",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "raw_source_text",
        "raw_text",
        "secret",
        "secrets",
        "source_text",
        "token",
    }
)

_CLOSED_CALL_DISPATCH_FALSE_KEYS = frozenset(
    {
        "search_dispatched",
        "retrieval_dispatched",
        "called_provider",
        "called_model",
        "called_fetch_read",
        "called_retrieval",
        "provider_called",
        "model_called",
        "fetch_read_called",
        "retrieval_called",
    }
)

_ALLOWED_FALSE_KEYS = frozenset(
    {
        *SERIAL_CHECKPOINT_CLOSED_DOWNSTREAM_FLAGS,
        *SERIAL_CHECKPOINT_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
        *GRAPH_CLOSED_DOWNSTREAM_FLAGS,
        *GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
        *_CLOSED_CALL_DISPATCH_FALSE_KEYS,
        "admitted",
        "admitted_support",
        "answer_contract_mutated",
        "author_created",
        "author_output_created",
        "author_ready",
        "budget_lease_created",
        "citation_eligible",
        "citation_rendered",
        "citation_rendering_created",
        "claimed_friend_mvp",
        "claimed_product_correctness",
        "claimed_source_obligation_satisfaction",
        "correct",
        "created_author_output",
        "created_budget_lease",
        "created_by_component_work_graph",
        "created_fap",
        "created_runtime_parallelism",
        "created_source_display",
        "created_sufficiency_readiness",
        "executed_graph",
        "fap_created",
        "fap_ready",
        "friend_mvp_claimed",
        "graph_executed",
        "graph_executed_nodes",
        "graph_scheduled",
        "graph_scheduled_runtime_work",
        "not_created_by_graph",
        "performed_cross_component_analysis",
        "performed_dprime_validation",
        "performed_runkernel_admission",
        "product_correctness_claimed",
        "rendered_citations",
        "runkernel_admitted",
        "scheduled_graph",
        "source_display_created",
        "source_obligation_satisfaction_claimed",
        "source_obligation_satisfied",
        "sufficiency_readiness_created",
        "validated_synthesis",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *SERIAL_CHECKPOINT_CLOSED_DOWNSTREAM_FLAGS,
        *_CLOSED_CALL_DISPATCH_FALSE_KEYS,
        "admitted_support",
        "answer_contract_mutated",
        "answer_created",
        "author_created",
        "author_output_created",
        "author_ready",
        "budget_lease_created",
        "citation_eligible",
        "citation_rendered",
        "citation_rendering_created",
        "claimed_friend_mvp",
        "claimed_product_correctness",
        "claimed_source_obligation_satisfaction",
        "created_author_output",
        "created_budget_lease",
        "created_fap",
        "created_runtime_parallelism",
        "created_source_display",
        "created_sufficiency_readiness",
        "executed_graph",
        "fap_created",
        "fap_ready",
        "friend_mvp_claimed",
        "graph_executed",
        "graph_executed_nodes",
        "graph_scheduled",
        "graph_scheduled_runtime_work",
        "performed_cross_component_analysis",
        "performed_dprime_validation",
        "performed_runkernel_admission",
        "product_correctness_claimed",
        "rendered_citations",
        "retrieval_authorized",
        "scheduled_graph",
        "source_display_created",
        "source_obligation_satisfaction_claimed",
        "source_obligation_satisfied",
        "sufficiency_readiness_created",
    }
)

_STATUS_KEYS = frozenset(
    {
        "admission_status",
        "approval_status",
        "authorization_status",
        "decision_status",
        "execution_status",
        "graph_status",
        "readiness_status",
        "recovery_status",
        "ref_status",
        "review_status",
        "runkernel_admission_status",
        "scenario_status",
        "search_authorization_status",
        "serial_dry_run_status",
        "state_status",
        "status",
        "trace_status",
        "validation_status",
    }
)

_DANGEROUS_STATUS_VALUES = frozenset(
    {
        "accepted",
        "admitted",
        "admitted_with_caveats",
        "applied",
        "approved",
        "authorized",
        "correct",
        "dispatched",
        "executed",
        "ready",
        "rendered",
        "scheduled",
        "satisfied",
    }
)

_RUNKERNEL_OUTPUT_ALLOWED_STATUS_FIELDS = frozenset(
    {
        "admission_status",
        "challenge_status",
    }
)


class MulticomponentSerialDryRunCheckpointError(ValueError):
    """Raised when the serial dry-run checkpoint loses ref or boundary safety."""


def multicomponent_serial_dry_run_checkpoint_v0_from_artifacts(
    *,
    parent_graph_artifact: Mapping[str, Any],
    cross_component_analyst_artifact: Mapping[str, Any],
    dprime_synthesis_validation_artifact: Mapping[str, Any],
    runkernel_graph_admission_artifact: Mapping[str, Any],
    checkpoint_id: str | None = None,
    scenario_kind: str = "small_user_style_multicomponent_serial_dry_run",
    serial_dry_run_status: str | None = None,
    user_query_ref: Mapping[str, Any] | None = None,
    serial_trace_refs: Sequence[Mapping[str, Any]] | None = None,
    review_packet_refs: Sequence[Mapping[str, Any]] | None = None,
    nonclaims: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Build a validated serial dry-run checkpoint from existing artifacts.

    The builder validates the existing graph, Workbench, D-prime validation, and
    RunKernel admission artifacts through their owning validators, then emits a
    review checkpoint over their refs. It performs no runtime work and does not
    inspect raw evidence.
    """

    graph = _validate_graph_input(parent_graph_artifact)
    workbench = _validate_workbench_input(cross_component_analyst_artifact)
    validation = _validate_dprime_validation_input(dprime_synthesis_validation_artifact)
    admission = _validate_admission_input(runkernel_graph_admission_artifact)

    parent_graph_ref = _compact_parent_graph_ref(graph)
    workbench_ref = _compact_workbench_ref(workbench)
    validation_ref = dprime_synthesis_validation_v0_ref(validation)
    admission_ref = runkernel_component_graph_admission_v0_ref(admission)
    _validate_input_binding(
        parent_graph_ref=parent_graph_ref,
        workbench_ref=workbench_ref,
        validation_ref=validation_ref,
        admission_ref=admission_ref,
    )

    status = _required_serial_status(
        serial_dry_run_status
        or _default_serial_status(admission_ref.get("admission_status"))
    )
    checkpoint_id_value = (
        _clean_text(checkpoint_id, limit=260)
        or _default_checkpoint_id(
            parent_graph_ref=parent_graph_ref,
            workbench_ref=workbench_ref,
            validation_ref=validation_ref,
            admission_ref=admission_ref,
            serial_dry_run_status=status,
        )
    )
    component_refs = [_json_safe(item) for item in graph["component_node_refs"]]
    dependency_refs = [_dependency_edge_ref(item) for item in graph["dependency_edges"]]
    supplied_user_query_ref = user_query_ref or graph["user_query_ref"]
    traces = (
        list(serial_trace_refs)
        if serial_trace_refs is not None
        else _default_serial_trace_refs(
            checkpoint_id=checkpoint_id_value,
            component_node_refs=component_refs,
            dependency_edge_refs=dependency_refs,
            parent_graph_ref=parent_graph_ref,
            workbench_ref=workbench_ref,
            validation_ref=validation_ref,
            admission_ref=admission_ref,
        )
    )
    reviews = (
        list(review_packet_refs)
        if review_packet_refs is not None
        else _default_review_packet_refs(
            checkpoint_id=checkpoint_id_value,
            scenario_kind=scenario_kind,
            serial_dry_run_status=status,
            parent_graph_ref=parent_graph_ref,
            workbench_ref=workbench_ref,
            validation_ref=validation_ref,
            admission_ref=admission_ref,
        )
    )
    artifact = {
        "schema_version": (
            MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_SCHEMA_VERSION
        ),
        "phase": MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_PHASE,
        "runtime_consumer": (
            MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_RUNTIME_CONSUMER
        ),
        "checkpoint_id": checkpoint_id_value,
        "checkpoint_digest": None,
        "parent_run_id": parent_graph_ref["parent_run_id"],
        "user_query_ref": dict(supplied_user_query_ref),
        "scenario_kind": _required_text(scenario_kind, "scenario_kind"),
        "serial_dry_run_status": status,
        "component_node_refs": component_refs,
        "parent_graph_ref": parent_graph_ref,
        "dependency_edge_refs": dependency_refs,
        "cross_component_analyst_ref": workbench_ref,
        "dprime_synthesis_validation_ref": validation_ref,
        "runkernel_graph_admission_ref": admission_ref,
        "admitted_synthesis_refs": list(admission.get("admitted_synthesis_refs", [])),
        "blocked_synthesis_refs": list(admission.get("blocked_synthesis_refs", [])),
        "challenge_refs": list(admission.get("challenge_refs", [])),
        "recovery_authorization_refs": list(
            admission.get("recovery_authorization_refs", [])
        ),
        "required_caveat_refs": list(admission.get("required_caveat_refs", [])),
        "preserved_nonclaim_refs": list(
            admission.get("preserved_nonclaim_refs", [])
        ),
        "blocker_refs": list(admission.get("blocker_refs", [])),
        "serial_trace_refs": traces,
        "review_packet_refs": reviews,
        "closed_downstream_flags": dict(SERIAL_CHECKPOINT_CLOSED_DOWNSTREAM_FLAGS),
        "raw_private_retention_flags": dict(
            SERIAL_CHECKPOINT_RAW_PRIVATE_RETENTION_FALSE_FLAGS
        ),
        "nonclaims": _nonclaims(nonclaims),
        **SERIAL_CHECKPOINT_CLOSED_DOWNSTREAM_FLAGS,
    }
    return validate_multicomponent_serial_dry_run_checkpoint_v0(artifact)


def validate_multicomponent_serial_dry_run_checkpoint_v0(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and normalize a serial dry-run checkpoint artifact."""

    artifact = _safe_mapping(value)
    for key in _REQUIRED_TOP_LEVEL_FIELDS:
        if key not in artifact:
            raise MulticomponentSerialDryRunCheckpointError(
                f"serial dry-run checkpoint requires {key}"
            )
    _reject_forbidden_material(artifact, context="serial dry-run checkpoint V0")
    _reject_status_laundering(
        artifact,
        context="serial dry-run checkpoint V0",
        allowed_status_context="serial_checkpoint",
    )
    if artifact.get("schema_version") != (
        MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_SCHEMA_VERSION
    ):
        raise MulticomponentSerialDryRunCheckpointError(
            "serial dry-run checkpoint schema mismatch"
        )
    if artifact.get("phase") != MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_PHASE:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial dry-run checkpoint phase mismatch"
        )
    checkpoint_id = _required_text(artifact.get("checkpoint_id"), "checkpoint_id")
    parent_run_id = _required_text(artifact.get("parent_run_id"), "parent_run_id")
    user_query_ref = _validate_typed_review_ref(
        artifact.get("user_query_ref"),
        field_name="user_query_ref",
    )
    scenario_kind = _required_text(artifact.get("scenario_kind"), "scenario_kind")
    serial_status = _required_serial_status(artifact.get("serial_dry_run_status"))
    parent_graph_ref = _validate_parent_graph_ref(artifact.get("parent_graph_ref"))
    if parent_graph_ref["parent_run_id"] != parent_run_id:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial checkpoint parent graph run mismatch"
        )
    component_refs = _validate_component_node_refs(artifact.get("component_node_refs"))
    dependency_refs = _validate_dependency_edge_refs(
        artifact.get("dependency_edge_refs"),
        component_node_refs=component_refs,
    )
    _require_component_count_matches_graph(
        component_node_refs=component_refs,
        parent_graph_ref=parent_graph_ref,
    )
    workbench_ref = _validate_workbench_ref(
        artifact.get("cross_component_analyst_ref")
    )
    validation_ref = _validate_dprime_validation_ref(
        artifact.get("dprime_synthesis_validation_ref")
    )
    admission_ref = _validate_admission_ref(
        artifact.get("runkernel_graph_admission_ref")
    )
    _validate_input_binding(
        parent_graph_ref=parent_graph_ref,
        workbench_ref=workbench_ref,
        validation_ref=validation_ref,
        admission_ref=admission_ref,
    )
    _require_preserved_refs(
        expected=component_refs,
        actual=_safe_refs(workbench_ref.get("component_node_refs")),
        context="Workbench component node refs",
    )
    _require_preserved_refs(
        expected=dependency_refs,
        actual=_safe_refs(workbench_ref.get("dependency_edge_refs")),
        context="Workbench dependency edge refs",
    )
    admitted_refs = _validate_admitted_synthesis_refs(
        artifact.get("admitted_synthesis_refs"),
        admission_ref=admission_ref,
        validation_ref=validation_ref,
        required_caveat_refs=_safe_refs(artifact.get("required_caveat_refs")),
        preserved_nonclaim_refs=_safe_refs(artifact.get("preserved_nonclaim_refs")),
    )
    blocked_refs = _validate_runkernel_output_refs(
        artifact.get("blocked_synthesis_refs"),
        field_name="blocked_synthesis_refs",
        admission_ref=admission_ref,
        validation_ref=validation_ref,
        require_proposal_binding=True,
    )
    challenge_refs = _validate_runkernel_output_refs(
        artifact.get("challenge_refs"),
        field_name="challenge_refs",
        admission_ref=admission_ref,
        validation_ref=validation_ref,
        require_proposal_binding=False,
    )
    recovery_refs = _validate_recovery_authorization_refs(
        artifact.get("recovery_authorization_refs"),
        admission_ref=admission_ref,
        validation_ref=validation_ref,
        known_component_refs=component_refs,
    )
    caveat_refs = _validate_typed_ref_list(
        artifact.get("required_caveat_refs"),
        field_name="required_caveat_refs",
    )
    nonclaim_refs = _validate_typed_ref_list(
        artifact.get("preserved_nonclaim_refs"),
        field_name="preserved_nonclaim_refs",
    )
    blocker_refs = _validate_typed_ref_list(
        artifact.get("blocker_refs"),
        field_name="blocker_refs",
    )
    _require_preserved_refs(
        expected=_safe_refs(workbench_ref.get("required_caveat_refs")),
        actual=caveat_refs,
        context="required caveat refs",
    )
    _require_preserved_refs(
        expected=_safe_refs(workbench_ref.get("nonclaim_refs")),
        actual=nonclaim_refs,
        context="nonclaim refs",
    )
    serial_traces = _validate_serial_trace_refs(
        artifact.get("serial_trace_refs"),
        checkpoint_id=checkpoint_id,
    )
    review_refs = _validate_review_packet_refs(
        artifact.get("review_packet_refs"),
        checkpoint_id=checkpoint_id,
    )
    _validate_checkpoint_status_semantics(
        serial_dry_run_status=serial_status,
        admission_status=admission_ref["admission_status"],
        admitted_synthesis_refs=admitted_refs,
        blocked_synthesis_refs=blocked_refs,
        challenge_refs=challenge_refs,
        recovery_authorization_refs=recovery_refs,
        blocker_refs=blocker_refs,
    )
    closed_flags = _validate_closed_downstream_flags(artifact)
    raw_flags = _validate_raw_private_flags(artifact)
    normalized = {
        **_json_safe(artifact),
        "checkpoint_id": checkpoint_id,
        "parent_run_id": parent_run_id,
        "user_query_ref": user_query_ref,
        "scenario_kind": scenario_kind,
        "serial_dry_run_status": serial_status,
        "component_node_refs": component_refs,
        "parent_graph_ref": parent_graph_ref,
        "dependency_edge_refs": dependency_refs,
        "cross_component_analyst_ref": workbench_ref,
        "dprime_synthesis_validation_ref": validation_ref,
        "runkernel_graph_admission_ref": admission_ref,
        "admitted_synthesis_refs": admitted_refs,
        "blocked_synthesis_refs": blocked_refs,
        "challenge_refs": challenge_refs,
        "recovery_authorization_refs": recovery_refs,
        "required_caveat_refs": caveat_refs,
        "preserved_nonclaim_refs": nonclaim_refs,
        "blocker_refs": blocker_refs,
        "serial_trace_refs": serial_traces,
        "review_packet_refs": review_refs,
        "closed_downstream_flags": closed_flags,
        "raw_private_retention_flags": raw_flags,
        "nonclaims": _nonclaims(artifact.get("nonclaims")),
        **closed_flags,
    }
    declared = _clean_text(artifact.get("checkpoint_digest"), limit=128)
    digest = _digest_json(_without_checkpoint_digest(normalized))
    if declared and declared != digest:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial dry-run checkpoint digest mismatch"
        )
    normalized["checkpoint_digest"] = digest
    _reject_forbidden_material(normalized, context="serial dry-run checkpoint V0")
    _reject_status_laundering(
        normalized,
        context="serial dry-run checkpoint V0",
        allowed_status_context="serial_checkpoint",
    )
    return normalized


def multicomponent_serial_dry_run_checkpoint_v0_ref(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a compact checkpoint ref for future licensed consumers."""

    if not _safe_mapping(value):
        return {}
    checkpoint = validate_multicomponent_serial_dry_run_checkpoint_v0(value)
    return _without_empty(
        {
            "schema_version": checkpoint.get("schema_version"),
            "phase": checkpoint.get("phase"),
            "checkpoint_id": checkpoint.get("checkpoint_id"),
            "checkpoint_digest": checkpoint.get("checkpoint_digest"),
            "parent_run_id": checkpoint.get("parent_run_id"),
            "parent_graph_ref": checkpoint.get("parent_graph_ref"),
            "runkernel_graph_admission_ref": checkpoint.get(
                "runkernel_graph_admission_ref"
            ),
            "serial_dry_run_status": checkpoint.get("serial_dry_run_status"),
            "component_node_ref_count": len(
                _safe_sequence(checkpoint.get("component_node_refs"))
            ),
            "dependency_edge_ref_count": len(
                _safe_sequence(checkpoint.get("dependency_edge_refs"))
            ),
            "review_artifact_only": True,
            "graph_executed": False,
            "graph_scheduled": False,
            "search_dispatched": False,
            "retrieval_dispatched": False,
            "fap_created": False,
            "author_output_created": False,
            "source_display_created": False,
            "citations_rendered": False,
            "product_correctness_claimed": False,
            "friend_mvp_claimed": False,
        }
    )


def _validate_graph_input(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_component_work_graph_v0(value)
    except Exception as exc:  # noqa: BLE001 - fail closed behind local error type.
        raise MulticomponentSerialDryRunCheckpointError(
            f"ComponentWorkGraph input invalid: {exc}"
        ) from None


def _validate_workbench_input(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_cross_component_analyst_workbench_v0(value)
    except Exception as exc:  # noqa: BLE001 - fail closed behind local error type.
        raise MulticomponentSerialDryRunCheckpointError(
            f"Cross-Component Analyst Workbench input invalid: {exc}"
        ) from None


def _validate_dprime_validation_input(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_dprime_synthesis_validation_v0(value)
    except Exception as exc:  # noqa: BLE001 - fail closed behind local error type.
        raise MulticomponentSerialDryRunCheckpointError(
            f"D-prime synthesis validation input invalid: {exc}"
        ) from None


def _validate_admission_input(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_runkernel_component_graph_admission_v0(value)
    except Exception as exc:  # noqa: BLE001 - fail closed behind local error type.
        raise MulticomponentSerialDryRunCheckpointError(
            f"RunKernel graph admission input invalid: {exc}"
        ) from None


def _compact_parent_graph_ref(graph: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_parent_graph_ref(
        _without_empty(
            {
                "schema_version": graph.get("schema_version"),
                "phase": graph.get("phase"),
                "graph_id": graph.get("graph_id"),
                "graph_digest": graph.get("graph_digest"),
                "parent_run_id": graph.get("parent_run_id"),
                "graph_status": graph.get("graph_status"),
                "component_node_count": graph.get("component_node_count"),
                "dependency_edge_count": len(
                    _safe_sequence(graph.get("dependency_edges"))
                ),
                "closed_downstream_flags": _safe_mapping(
                    graph.get("closed_downstream_flags")
                ),
                "raw_private_retention_flags": _safe_mapping(
                    graph.get("raw_private_retention_flags")
                ),
            }
        )
    )


def _compact_workbench_ref(workbench: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_workbench_ref(
        _without_empty(
            {
                "schema_version": workbench.get("schema_version"),
                "phase": workbench.get("phase"),
                "cross_component_analyst_id": workbench.get(
                    "cross_component_analyst_id"
                ),
                "cross_component_analyst_digest": workbench.get(
                    "cross_component_analyst_digest"
                ),
                "parent_run_id": workbench.get("parent_run_id"),
                "parent_graph_ref": _safe_mapping(workbench.get("parent_graph_ref")),
                "analysis_status": workbench.get("analysis_status"),
                "proposal_only": True,
                "component_node_refs": _safe_refs(
                    workbench.get("component_node_refs")
                ),
                "dependency_edge_refs": _safe_refs(
                    workbench.get("dependency_edge_refs")
                ),
                "synthesis_proposal_refs": _synthesis_proposal_identity_refs(
                    workbench.get("synthesis_proposal_refs")
                ),
                "required_caveat_refs": _safe_refs(
                    workbench.get("required_caveat_refs")
                ),
                "nonclaim_refs": _safe_refs(workbench.get("nonclaim_refs")),
                "contradiction_refs": _safe_refs(workbench.get("contradiction_refs")),
                "unresolved_dependency_refs": _safe_refs(
                    workbench.get("unresolved_dependency_refs")
                ),
                "missing_component_proposal_refs": _safe_refs(
                    workbench.get("missing_component_proposal_refs")
                ),
            }
        )
    )


def _validate_parent_graph_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION:
        raise MulticomponentSerialDryRunCheckpointError(
            "parent_graph_ref must be ComponentWorkGraph V0"
        )
    for key in ("graph_id", "graph_digest", "parent_run_id", "graph_status"):
        _required_text(ref.get(key), f"parent_graph_ref.{key}")
    closed_flags = _validate_graph_closed_flags(ref)
    raw_flags = _validate_graph_raw_flags(ref)
    normalized = {
        **_json_safe(ref),
        "closed_downstream_flags": closed_flags,
        "raw_private_retention_flags": raw_flags,
    }
    _reject_forbidden_material(normalized, context="parent_graph_ref")
    return normalized


def _validate_workbench_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION:
        raise MulticomponentSerialDryRunCheckpointError(
            "cross_component_analyst_ref schema mismatch"
        )
    for key in (
        "cross_component_analyst_id",
        "cross_component_analyst_digest",
        "parent_run_id",
        "analysis_status",
    ):
        _required_text(ref.get(key), f"cross_component_analyst_ref.{key}")
    if ref.get("proposal_only") is not True:
        raise MulticomponentSerialDryRunCheckpointError(
            "cross_component_analyst_ref must remain proposal-only"
        )
    parent_graph_ref = _validate_parent_graph_ref(ref.get("parent_graph_ref"))
    normalized = {
        **_json_safe(ref),
        "parent_graph_ref": parent_graph_ref,
        "component_node_refs": _validate_component_node_refs(
            ref.get("component_node_refs")
        ),
        "dependency_edge_refs": _validate_dependency_edge_refs(
            ref.get("dependency_edge_refs"),
            component_node_refs=_safe_refs(ref.get("component_node_refs")),
        ),
        "synthesis_proposal_refs": _synthesis_proposal_identity_refs(
            ref.get("synthesis_proposal_refs")
        ),
        "required_caveat_refs": _safe_refs(ref.get("required_caveat_refs")),
        "nonclaim_refs": _safe_refs(ref.get("nonclaim_refs")),
        "contradiction_refs": _safe_refs(ref.get("contradiction_refs")),
        "unresolved_dependency_refs": _safe_refs(
            ref.get("unresolved_dependency_refs")
        ),
        "missing_component_proposal_refs": _safe_refs(
            ref.get("missing_component_proposal_refs")
        ),
    }
    _reject_forbidden_material(normalized, context="cross_component_analyst_ref")
    _reject_status_laundering(normalized, context="cross_component_analyst_ref")
    return normalized


def _validate_dprime_validation_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != DPRIME_SYNTHESIS_VALIDATION_V0_SCHEMA_VERSION:
        raise MulticomponentSerialDryRunCheckpointError(
            "dprime_synthesis_validation_ref schema mismatch"
        )
    for key in (
        "dprime_synthesis_validation_id",
        "dprime_synthesis_validation_digest",
        "parent_run_id",
        "validation_status",
    ):
        _required_text(ref.get(key), f"dprime_synthesis_validation_ref.{key}")
    parent_graph_ref = _validate_parent_graph_ref(ref.get("parent_graph_ref"))
    workbench_ref = _validate_dprime_workbench_ref(
        ref.get("cross_component_analyst_ref")
    )
    normalized = {
        **_json_safe(ref),
        "parent_graph_ref": parent_graph_ref,
        "cross_component_analyst_ref": workbench_ref,
        "synthesis_proposal_refs": _synthesis_proposal_identity_refs(
            ref.get("synthesis_proposal_refs")
        ),
    }
    for key in (
        "runkernel_admission_created",
        "answer_contract_mutated",
        "retrieval_authorized",
        "product_correctness_claimed",
    ):
        if ref.get(key) is not False:
            raise MulticomponentSerialDryRunCheckpointError(
                f"dprime_synthesis_validation_ref must keep {key}=false"
            )
    _reject_forbidden_material(normalized, context="dprime_synthesis_validation_ref")
    _reject_status_laundering(normalized, context="dprime_synthesis_validation_ref")
    return normalized


def _validate_admission_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_SCHEMA_VERSION:
        raise MulticomponentSerialDryRunCheckpointError(
            "runkernel_graph_admission_ref schema mismatch"
        )
    for key in (
        "runkernel_graph_admission_id",
        "runkernel_graph_admission_digest",
        "parent_run_id",
        "admission_status",
    ):
        _required_text(ref.get(key), f"runkernel_graph_admission_ref.{key}")
    admission_status = _required_admission_status(ref.get("admission_status"))
    normalized = {
        **_json_safe(ref),
        "parent_graph_ref": _validate_parent_graph_ref(ref.get("parent_graph_ref")),
        "cross_component_analyst_ref": _validate_workbench_ref(
            ref.get("cross_component_analyst_ref")
        ),
        "dprime_synthesis_validation_ref": _validate_dprime_validation_ref(
            ref.get("dprime_synthesis_validation_ref")
        ),
        "admission_status": admission_status,
    }
    for key in (
        "graph_executed",
        "search_dispatched",
        "retrieval_dispatched",
        "answer_contract_mutated",
        "product_correctness_claimed",
    ):
        if ref.get(key) is not False:
            raise MulticomponentSerialDryRunCheckpointError(
                f"runkernel_graph_admission_ref must keep {key}=false"
            )
    _reject_forbidden_material(normalized, context="runkernel_graph_admission_ref")
    _reject_status_laundering(
        normalized,
        context="runkernel_graph_admission_ref",
        allowed_status_context="runkernel_admission_ref",
    )
    return normalized


def _validate_dprime_workbench_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION:
        raise MulticomponentSerialDryRunCheckpointError(
            "D-prime validation Workbench ref schema mismatch"
        )
    for key in (
        "cross_component_analyst_id",
        "cross_component_analyst_digest",
        "parent_run_id",
        "analysis_status",
    ):
        _required_text(ref.get(key), f"D-prime validation Workbench ref.{key}")
    if ref.get("proposal_only") is not True:
        raise MulticomponentSerialDryRunCheckpointError(
            "D-prime validation Workbench ref must remain proposal-only"
        )
    _reject_forbidden_material(ref, context="D-prime validation Workbench ref")
    _reject_status_laundering(ref, context="D-prime validation Workbench ref")
    return _json_safe(ref)


def _validate_input_binding(
    *,
    parent_graph_ref: Mapping[str, Any],
    workbench_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
) -> None:
    if workbench_ref.get("parent_run_id") != parent_graph_ref.get("parent_run_id"):
        raise MulticomponentSerialDryRunCheckpointError(
            "Workbench ref parent_run_id must match graph ref"
        )
    if validation_ref.get("parent_run_id") != parent_graph_ref.get("parent_run_id"):
        raise MulticomponentSerialDryRunCheckpointError(
            "D-prime validation ref parent_run_id must match graph ref"
        )
    if admission_ref.get("parent_run_id") != parent_graph_ref.get("parent_run_id"):
        raise MulticomponentSerialDryRunCheckpointError(
            "RunKernel admission ref parent_run_id must match graph ref"
        )
    _require_same_graph_ref(
        expected=parent_graph_ref,
        actual=_safe_mapping(workbench_ref.get("parent_graph_ref")),
        context="Workbench parent graph ref",
    )
    _require_same_graph_ref(
        expected=parent_graph_ref,
        actual=_safe_mapping(validation_ref.get("parent_graph_ref")),
        context="D-prime validation parent graph ref",
    )
    _require_same_graph_ref(
        expected=parent_graph_ref,
        actual=_safe_mapping(admission_ref.get("parent_graph_ref")),
        context="RunKernel admission parent graph ref",
    )
    validation_workbench = _safe_mapping(validation_ref.get("cross_component_analyst_ref"))
    admission_workbench = _safe_mapping(admission_ref.get("cross_component_analyst_ref"))
    for key in ("cross_component_analyst_id", "cross_component_analyst_digest"):
        if validation_workbench.get(key) != workbench_ref.get(key):
            raise MulticomponentSerialDryRunCheckpointError(
                "D-prime validation ref must bind to Workbench id/digest"
            )
        if admission_workbench.get(key) != workbench_ref.get(key):
            raise MulticomponentSerialDryRunCheckpointError(
                "RunKernel admission ref must bind to Workbench id/digest"
            )
    admission_validation = _safe_mapping(
        admission_ref.get("dprime_synthesis_validation_ref")
    )
    for key in ("dprime_synthesis_validation_id", "dprime_synthesis_validation_digest"):
        if admission_validation.get(key) != validation_ref.get(key):
            raise MulticomponentSerialDryRunCheckpointError(
                "RunKernel admission ref must bind to D-prime validation id/digest"
            )
    workbench_proposals = _proposal_claim_identity_map(
        workbench_ref.get("synthesis_proposal_refs")
    )
    validation_proposals = _proposal_claim_identity_map(
        validation_ref.get("synthesis_proposal_refs")
    )
    if validation_proposals != {
        key: workbench_proposals.get(key)
        for key in validation_proposals
    }:
        raise MulticomponentSerialDryRunCheckpointError(
            "D-prime validation ref synthesis proposal/claim identity must match Workbench ref"
        )


def _validate_component_node_refs(value: Any) -> list[dict[str, Any]]:
    refs = [_validate_component_ref(item) for item in _safe_sequence(value)]
    if len(refs) < 2:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial dry-run checkpoint requires at least two ComponentWorkNode refs"
        )
    return refs


def _validate_component_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
        raise MulticomponentSerialDryRunCheckpointError(
            "component node refs must be ComponentWorkNode V0"
        )
    node_id = _required_text(ref.get("node_id"), "component ref node_id")
    component_id = _required_text(ref.get("component_id"), "component ref component_id")
    _reject_forbidden_material(ref, context="component ref")
    return _without_empty(
        {
            **_json_safe(ref),
            "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
            "node_id": node_id,
            "component_id": component_id,
        }
    )


def _validate_dependency_edge_refs(
    value: Any,
    *,
    component_node_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = [_validate_dependency_edge_ref(item) for item in _safe_sequence(value)]
    if not refs:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial dry-run checkpoint requires dependency_edge_refs"
        )
    known = {
        (ref.get("node_id"), ref.get("component_id"))
        for ref in component_node_refs
        if _safe_mapping(ref)
    }
    for edge in refs:
        for field_name in ("from_component_node_ref", "to_component_node_ref"):
            component_ref = _validate_component_ref(edge.get(field_name))
            if (component_ref["node_id"], component_ref["component_id"]) not in known:
                raise MulticomponentSerialDryRunCheckpointError(
                    "dependency edge refs must reference known component node refs"
                )
    return refs


def _validate_dependency_edge_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION:
        raise MulticomponentSerialDryRunCheckpointError(
            "dependency_edge_refs must be ComponentWorkGraph V0 edge refs"
        )
    _required_text(ref.get("edge_id"), "dependency edge edge_id")
    _required_text(ref.get("edge_digest"), "dependency edge edge_digest")
    _reject_forbidden_material(ref, context="dependency_edge_ref")
    return _json_safe(ref)


def _dependency_edge_ref(edge: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(edge)
    return _without_empty(
        {
            "schema_version": safe.get("schema_version"),
            "edge_id": safe.get("edge_id"),
            "edge_digest": safe.get("edge_digest"),
            "from_component_node_ref": safe.get("from_component_node_ref"),
            "to_component_node_ref": safe.get("to_component_node_ref"),
            "dependency_kind": safe.get("dependency_kind"),
            "blocking": safe.get("blocking") is True,
        }
    )


def _validate_admitted_synthesis_refs(
    value: Any,
    *,
    admission_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
    required_caveat_refs: Sequence[Mapping[str, Any]],
    preserved_nonclaim_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = _validate_runkernel_output_refs(
        value,
        field_name="admitted_synthesis_refs",
        admission_ref=admission_ref,
        validation_ref=validation_ref,
        require_proposal_binding=True,
    )
    proposal_claims = _proposal_claim_identity_map(
        validation_ref.get("synthesis_proposal_refs")
    )
    for ref in refs:
        proposal_id, proposal_digest = _required_synthesis_identity(ref)
        claim = _synthesis_claim_identity_ref(ref.get("synthesis_claim_ref"))
        expected_claim = proposal_claims.get((proposal_id, proposal_digest), {})
        if not claim or claim != expected_claim:
            raise MulticomponentSerialDryRunCheckpointError(
                "admitted synthesis refs must preserve synthesis claim id/digest"
            )
        if ref.get("admission_status") != admission_ref.get("admission_status"):
            raise MulticomponentSerialDryRunCheckpointError(
                "admitted synthesis refs must match RunKernel admission status"
            )
        _require_preserved_refs(
            expected=required_caveat_refs,
            actual=_safe_refs(ref.get("required_caveat_refs")),
            context="admitted synthesis required caveats",
        )
        _require_preserved_refs(
            expected=preserved_nonclaim_refs,
            actual=_safe_refs(ref.get("preserved_nonclaim_refs")),
            context="admitted synthesis nonclaims",
        )
    return refs


def _validate_runkernel_output_refs(
    value: Any,
    *,
    field_name: str,
    admission_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
    require_proposal_binding: bool,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    proposal_index = _proposal_claim_identity_map(
        validation_ref.get("synthesis_proposal_refs")
    )
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        _reject_forbidden_material(ref, context=field_name)
        if not _is_runkernel_output_ref(ref):
            raise MulticomponentSerialDryRunCheckpointError(
                f"{field_name} must be typed RunKernel-owned output refs"
            )
        _validate_runkernel_output_ref_boundary(ref, field_name=field_name)
        if ref.get("runkernel_graph_admission_id") != admission_ref.get(
            "runkernel_graph_admission_id"
        ):
            raise MulticomponentSerialDryRunCheckpointError(
                f"{field_name} must bind to this admission id"
            )
        if ref.get("dprime_synthesis_validation_id") not in (
            None,
            validation_ref.get("dprime_synthesis_validation_id"),
        ):
            raise MulticomponentSerialDryRunCheckpointError(
                f"{field_name} D-prime validation id mismatch"
            )
        if ref.get("dprime_synthesis_validation_digest") not in (
            None,
            validation_ref.get("dprime_synthesis_validation_digest"),
        ):
            raise MulticomponentSerialDryRunCheckpointError(
                f"{field_name} D-prime validation digest mismatch"
            )
        has_proposal = bool(
            _clean_text(ref.get("synthesis_proposal_id"), limit=320)
            or _safe_mapping(ref.get("synthesis_proposal_ref"))
        )
        if require_proposal_binding or has_proposal:
            proposal_id, proposal_digest = _required_synthesis_identity(ref)
            if (proposal_id, proposal_digest) not in proposal_index:
                raise MulticomponentSerialDryRunCheckpointError(
                    f"{field_name} references unknown synthesis proposal id/digest"
                )
        refs.append(_json_safe(ref))
    return refs


def _validate_recovery_authorization_refs(
    value: Any,
    *,
    admission_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
    known_component_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = _validate_runkernel_output_refs(
        value,
        field_name="recovery_authorization_refs",
        admission_ref=admission_ref,
        validation_ref=validation_ref,
        require_proposal_binding=True,
    )
    component_index = {
        (ref.get("node_id"), ref.get("component_id"))
        for ref in known_component_refs
        if _safe_mapping(ref)
    }
    for ref in refs:
        _required_text(ref.get("recovery_authorization_id"), "recovery_authorization_id")
        _required_text(ref.get("reason"), "recovery authorization reason")
        _required_text(
            ref.get("allowed_future_recovery_surface"),
            "allowed_future_recovery_surface",
        )
        lifecycle = _clean_text(
            ref.get("expires_or_requires_new_admission")
            or ref.get("bounded_lifecycle_marker"),
            limit=500,
        )
        if not lifecycle:
            raise MulticomponentSerialDryRunCheckpointError(
                "recovery authorization refs require a bounded lifecycle marker"
            )
        if _bounded_int(ref.get("max_attempts"), default=0) <= 0:
            raise MulticomponentSerialDryRunCheckpointError(
                "recovery authorization refs require max_attempts"
            )
        if ref.get("no_dispatch") is not True or ref.get("not_executed") is not True:
            raise MulticomponentSerialDryRunCheckpointError(
                "recovery authorization refs require no_dispatch and not_executed flags"
            )
        component_refs = _safe_sequence(ref.get("component_refs_involved"))
        if not component_refs:
            raise MulticomponentSerialDryRunCheckpointError(
                "recovery authorization refs require component refs involved"
            )
        for component_ref in component_refs:
            normalized = _validate_component_ref(component_ref)
            if (normalized["node_id"], normalized["component_id"]) not in component_index:
                raise MulticomponentSerialDryRunCheckpointError(
                    "recovery authorization component refs must be known components"
                )
        _reject_non_false_closed_call_dispatch_flags(
            ref,
            context="recovery authorization refs",
        )
    return refs


def _validate_typed_ref_list(value: Any, *, field_name: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _validate_typed_review_ref(item, field_name=field_name)
        refs.append(ref)
    return refs


def _validate_typed_review_ref(value: Any, *, field_name: str) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if not ref:
        raise MulticomponentSerialDryRunCheckpointError(f"{field_name} malformed")
    _reject_forbidden_material(ref, context=field_name)
    _reject_status_laundering(ref, context=field_name)
    if field_name == "user_query_ref":
        query_id = _clean_text(ref.get("query_id"), limit=320)
        query_digest = _clean_text(ref.get("query_digest"), limit=128)
        if query_id and query_digest:
            return {
                **_json_safe(ref),
                "ref_kind": ref.get("ref_kind") or "user_query_ref",
            }
    if not _typed_ref(ref):
        raise MulticomponentSerialDryRunCheckpointError(
            f"{field_name} must contain typed refs"
        )
    return _json_safe(ref)


def _validate_serial_trace_refs(
    value: Any,
    *,
    checkpoint_id: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        _reject_forbidden_material(ref, context="serial_trace_refs")
        _reject_status_laundering(ref, context="serial_trace_refs")
        if ref.get("schema_version") != "multicomponent_serial_trace_ref_v0":
            raise MulticomponentSerialDryRunCheckpointError(
                "serial_trace_refs must be typed serial trace refs"
            )
        _required_text(ref.get("serial_trace_id"), "serial_trace_id")
        _required_text(ref.get("serial_trace_digest"), "serial_trace_digest")
        _required_text(ref.get("trace_kind"), "trace_kind")
        if ref.get("checkpoint_id") != checkpoint_id:
            raise MulticomponentSerialDryRunCheckpointError(
                "serial_trace_refs must bind to checkpoint_id"
            )
        if ref.get("deterministic_serial_only") is not True:
            raise MulticomponentSerialDryRunCheckpointError(
                "serial_trace_refs must be deterministic serial refs"
            )
        if _bounded_int(ref.get("serial_order_index"), default=-1) < 0:
            raise MulticomponentSerialDryRunCheckpointError(
                "serial_trace_refs require serial_order_index"
            )
        for key in (
            "scheduled_graph",
            "executed_graph",
            "created_runtime_parallelism",
            "created_budget_lease",
            "graph_scheduled",
            "graph_executed",
            "runtime_parallelism_created",
            "budget_lease_created",
        ):
            if ref.get(key) is not False:
                raise MulticomponentSerialDryRunCheckpointError(
                    "serial_trace_refs must not claim scheduling, execution, parallelism, budget, or calls"
                )
        _reject_non_false_closed_call_dispatch_flags(
            ref,
            context="serial_trace_refs",
        )
        refs.append(_json_safe(ref))
    if not refs:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial dry-run checkpoint requires serial_trace_refs"
        )
    return refs


def _validate_review_packet_refs(
    value: Any,
    *,
    checkpoint_id: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        _reject_forbidden_material(ref, context="review_packet_refs")
        _reject_status_laundering(ref, context="review_packet_refs")
        if ref.get("schema_version") != "multicomponent_serial_review_packet_ref_v0":
            raise MulticomponentSerialDryRunCheckpointError(
                "review_packet_refs must be typed review packet refs"
            )
        _required_text(ref.get("review_packet_id"), "review_packet_id")
        _required_text(ref.get("review_packet_digest"), "review_packet_digest")
        if ref.get("checkpoint_id") != checkpoint_id:
            raise MulticomponentSerialDryRunCheckpointError(
                "review_packet_refs must bind to checkpoint_id"
            )
        if ref.get("review_artifact_only") is not True:
            raise MulticomponentSerialDryRunCheckpointError(
                "review_packet_refs must remain review artifacts only"
            )
        _reject_non_false_closed_call_dispatch_flags(
            ref,
            context="review_packet_refs",
        )
        for key in (
            "created_fap",
            "created_author_output",
            "created_source_display",
            "rendered_citations",
            "claimed_source_obligation_satisfaction",
            "claimed_product_correctness",
            "claimed_friend_mvp",
            "fap_created",
            "author_output_created",
            "source_display_created",
            "citations_rendered",
            "source_obligation_satisfaction_claimed",
            "product_correctness_claimed",
            "friend_mvp_claimed",
            "product_ready",
        ):
            if ref.get(key) is not False:
                raise MulticomponentSerialDryRunCheckpointError(
                    "review_packet_refs must not claim downstream answer/rendering readiness"
                )
        refs.append(_json_safe(ref))
    if not refs:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial dry-run checkpoint requires review_packet_refs"
        )
    return refs


def _validate_checkpoint_status_semantics(
    *,
    serial_dry_run_status: str,
    admission_status: str,
    admitted_synthesis_refs: Sequence[Mapping[str, Any]],
    blocked_synthesis_refs: Sequence[Mapping[str, Any]],
    challenge_refs: Sequence[Mapping[str, Any]],
    recovery_authorization_refs: Sequence[Mapping[str, Any]],
    blocker_refs: Sequence[Mapping[str, Any]],
) -> None:
    if serial_dry_run_status == SERIAL_DRY_RUN_STATUS_REPRESENTED:
        if admission_status != ADMISSION_STATUS_ADMITTED:
            raise MulticomponentSerialDryRunCheckpointError(
                "represented checkpoint requires admitted RunKernel graph admission"
            )
        if not admitted_synthesis_refs:
            raise MulticomponentSerialDryRunCheckpointError(
                "represented checkpoint requires admitted synthesis refs"
            )
    elif serial_dry_run_status == SERIAL_DRY_RUN_STATUS_REPRESENTED_WITH_CAVEATS:
        if admission_status != ADMISSION_STATUS_ADMITTED_WITH_CAVEATS:
            raise MulticomponentSerialDryRunCheckpointError(
                "represented_with_caveats checkpoint requires admitted_with_caveats RunKernel graph admission"
            )
        if not admitted_synthesis_refs:
            raise MulticomponentSerialDryRunCheckpointError(
                "represented_with_caveats checkpoint requires admitted synthesis refs"
            )
    elif admitted_synthesis_refs:
        raise MulticomponentSerialDryRunCheckpointError(
            "non-represented checkpoint statuses must not carry admitted synthesis refs as represented state"
        )
    if serial_dry_run_status == SERIAL_DRY_RUN_STATUS_BLOCKED and not (
        blocked_synthesis_refs or blocker_refs
    ):
        raise MulticomponentSerialDryRunCheckpointError(
            "blocked checkpoint requires blocked synthesis or blocker refs"
        )
    if serial_dry_run_status == SERIAL_DRY_RUN_STATUS_CHALLENGED and not challenge_refs:
        raise MulticomponentSerialDryRunCheckpointError(
            "challenged checkpoint requires challenge refs"
        )
    if (
        serial_dry_run_status == SERIAL_DRY_RUN_STATUS_RECOVERY_AUTHORIZED
        and not recovery_authorization_refs
    ):
        raise MulticomponentSerialDryRunCheckpointError(
            "recovery_authorized checkpoint requires recovery authorization refs"
        )
    expected = _default_serial_status(admission_status)
    if serial_dry_run_status != SERIAL_DRY_RUN_STATUS_DRAFT and serial_dry_run_status != expected:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial dry-run status must preserve RunKernel admission posture"
        )


def _validate_closed_downstream_flags(artifact: Mapping[str, Any]) -> dict[str, bool]:
    closed = _safe_mapping(artifact.get("closed_downstream_flags"))
    if not closed:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial checkpoint missing closed_downstream_flags"
        )
    normalized: dict[str, bool] = {}
    for key in SERIAL_CHECKPOINT_CLOSED_DOWNSTREAM_FLAGS:
        if closed.get(key) is not False:
            raise MulticomponentSerialDryRunCheckpointError(
                f"serial checkpoint closed flag must remain false: {key}"
            )
        if artifact.get(key) is not False:
            raise MulticomponentSerialDryRunCheckpointError(
                f"serial checkpoint top-level flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_raw_private_flags(artifact: Mapping[str, Any]) -> dict[str, bool]:
    flags = _safe_mapping(artifact.get("raw_private_retention_flags"))
    if not flags:
        raise MulticomponentSerialDryRunCheckpointError(
            "serial checkpoint missing raw_private_retention_flags"
        )
    normalized: dict[str, bool] = {}
    for key in SERIAL_CHECKPOINT_RAW_PRIVATE_RETENTION_FALSE_FLAGS:
        if flags.get(key) is not False:
            raise MulticomponentSerialDryRunCheckpointError(
                f"serial checkpoint raw/private flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_graph_closed_flags(ref: Mapping[str, Any]) -> dict[str, bool]:
    closed = _safe_mapping(ref.get("closed_downstream_flags"))
    if not closed:
        raise MulticomponentSerialDryRunCheckpointError(
            "parent_graph_ref missing closed_downstream_flags"
        )
    normalized: dict[str, bool] = {}
    for key in GRAPH_CLOSED_DOWNSTREAM_FLAGS:
        if closed.get(key) is not False:
            raise MulticomponentSerialDryRunCheckpointError(
                f"parent_graph_ref closed flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_graph_raw_flags(ref: Mapping[str, Any]) -> dict[str, bool]:
    flags = _safe_mapping(ref.get("raw_private_retention_flags"))
    if not flags:
        raise MulticomponentSerialDryRunCheckpointError(
            "parent_graph_ref missing raw_private_retention_flags"
        )
    normalized: dict[str, bool] = {}
    for key in GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS:
        if flags.get(key) is not False:
            raise MulticomponentSerialDryRunCheckpointError(
                f"parent_graph_ref raw/private flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_runkernel_output_ref_boundary(
    value: Any,
    *,
    field_name: str,
) -> None:
    forbidden = sorted(_collect_keys(value) & _FORBIDDEN_NORMALIZED_KEYS)
    if forbidden:
        raise MulticomponentSerialDryRunCheckpointError(
            f"{field_name} RunKernel output ref includes forbidden raw/private material: "
            + ", ".join(forbidden)
        )
    for item in _walk_mappings(value):
        for key, raw in item.items():
            normalized_key = _normalize_key(key)
            normalized_value = _normalize_key(raw)
            if normalized_key in _DANGEROUS_TRUE_KEYS:
                if raw is not False:
                    raise MulticomponentSerialDryRunCheckpointError(
                        f"{field_name} RunKernel output ref must keep {normalized_key}=false"
                    )
                continue
            if normalized_key in _ALLOWED_FALSE_KEYS and raw is not False:
                raise MulticomponentSerialDryRunCheckpointError(
                    f"{field_name} RunKernel output ref must keep {normalized_key}=false"
                )
            if not _is_status_key(normalized_key):
                continue
            if normalized_key in _RUNKERNEL_OUTPUT_ALLOWED_STATUS_FIELDS:
                if normalized_value not in ALLOWED_ADMISSION_STATUSES:
                    raise MulticomponentSerialDryRunCheckpointError(
                        f"{field_name} RunKernel output ref carries invalid module-owned status"
                    )
                continue
            if normalized_value in _DANGEROUS_STATUS_VALUES:
                raise MulticomponentSerialDryRunCheckpointError(
                    f"{field_name} RunKernel output ref carries forbidden status claim: "
                    f"{normalized_key}={normalized_value}"
                )


def _reject_non_false_closed_call_dispatch_flags(
    value: Mapping[str, Any],
    *,
    context: str,
) -> None:
    invalid = sorted(
        key
        for key in _CLOSED_CALL_DISPATCH_FALSE_KEYS
        if key in value and value.get(key) is not False
    )
    if invalid:
        raise MulticomponentSerialDryRunCheckpointError(
            f"{context} call/dispatch flags must be absent or exactly false: "
            + ", ".join(invalid)
        )


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & _FORBIDDEN_NORMALIZED_KEYS)
    if forbidden:
        raise MulticomponentSerialDryRunCheckpointError(
            f"{context} includes forbidden raw/private material: "
            + ", ".join(forbidden)
        )
    invalid_false_flags = sorted(_invalid_false_flags(value))
    if invalid_false_flags:
        raise MulticomponentSerialDryRunCheckpointError(
            f"{context} raw/private or closed flags must be explicitly false: "
            + ", ".join(invalid_false_flags)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise MulticomponentSerialDryRunCheckpointError(
            f"{context} attempts forbidden authority upgrade: "
            + ", ".join(dangerous)
        )


def _reject_status_laundering(
    value: Any,
    *,
    context: str,
    depth: int = 0,
    allowed_status_context: str | None = None,
) -> None:
    if isinstance(value, Mapping):
        safe = _safe_mapping(value)
        if _is_runkernel_output_ref(safe):
            _validate_runkernel_output_ref_boundary(safe, field_name=context)
            return
        for key, item in safe.items():
            normalized_key = _normalize_key(key)
            normalized_value = _normalize_key(item)
            if (
                allowed_status_context == "serial_checkpoint"
                and depth == 0
                and normalized_key == "runkernel_graph_admission_ref"
            ):
                _validate_admission_ref(item)
                continue
            if normalized_key == "admission_status":
                if not (
                    allowed_status_context == "runkernel_admission_ref"
                    and depth == 0
                    and normalized_value in ALLOWED_ADMISSION_STATUSES
                ):
                    raise MulticomponentSerialDryRunCheckpointError(
                        f"{context} carries forbidden status claim: "
                        f"{normalized_key}={normalized_value}"
                    )
            elif (
                normalized_key in _STATUS_KEYS
                and normalized_value in _DANGEROUS_STATUS_VALUES
                and not (depth == 0 and normalized_key == "serial_dry_run_status")
            ):
                raise MulticomponentSerialDryRunCheckpointError(
                    f"{context} carries forbidden status claim: "
                    f"{normalized_key}={normalized_value}"
                )
            _reject_status_laundering(item, context=context, depth=depth + 1)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            _reject_status_laundering(item, context=context, depth=depth + 1)


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        safe = _safe_mapping(value)
        if _is_runkernel_output_ref(safe):
            return found
        for key, item in safe.items():
            normalized = _normalize_key(key)
            if normalized in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(normalized)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _invalid_false_flags(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        safe = _safe_mapping(value)
        if _is_runkernel_output_ref(safe):
            return found
        for key, item in safe.items():
            normalized = _normalize_key(key)
            if normalized in _ALLOWED_FALSE_KEYS and item is not False:
                found.add(normalized)
            found.update(_invalid_false_flags(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            found.update(_invalid_false_flags(item))
    return found


def _is_runkernel_output_ref(value: Mapping[str, Any]) -> bool:
    schema = _clean_text(value.get("schema_version"), limit=260)
    return (
        bool(schema)
        and schema.startswith("runkernel_graph_admission_")
        and value.get("runkernel_owned_output_ref") is True
        and value.get("created_by_runkernel_component_graph_admission_v0") is True
    )


def _is_status_key(normalized_key: str) -> bool:
    return normalized_key in _STATUS_KEYS or normalized_key.endswith("_status")


def _walk_mappings(value: Any) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        safe = _safe_mapping(value)
        mappings.append(safe)
        for item in safe.values():
            mappings.extend(_walk_mappings(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            mappings.extend(_walk_mappings(item))
    return mappings


def _default_serial_trace_refs(
    *,
    checkpoint_id: str,
    component_node_refs: Sequence[Mapping[str, Any]],
    dependency_edge_refs: Sequence[Mapping[str, Any]],
    parent_graph_ref: Mapping[str, Any],
    workbench_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
) -> list[dict[str, Any]]:
    steps = [
        ("component_node_refs_preserved", component_node_refs),
        ("dependency_edge_refs_preserved", dependency_edge_refs),
        ("parent_graph_ref_consumed", parent_graph_ref),
        ("cross_component_analyst_ref_consumed", workbench_ref),
        ("dprime_synthesis_validation_ref_consumed", validation_ref),
        ("runkernel_graph_admission_ref_consumed", admission_ref),
    ]
    refs: list[dict[str, Any]] = []
    for index, (kind, payload) in enumerate(steps):
        trace_seed = {
            "checkpoint_id": checkpoint_id,
            "trace_kind": kind,
            "payload_digest": _digest_json(payload),
            "serial_order_index": index,
        }
        digest = _digest_json(trace_seed)
        refs.append(
            {
                "schema_version": "multicomponent_serial_trace_ref_v0",
                "serial_trace_id": f"{checkpoint_id}:trace:{index}:{kind}",
                "serial_trace_digest": digest,
                "checkpoint_id": checkpoint_id,
                "trace_kind": kind,
                "serial_order_index": index,
                "deterministic_serial_only": True,
                "checkpoint_review_artifact_only": True,
                "scheduled_graph": False,
                "executed_graph": False,
                "created_runtime_parallelism": False,
                "created_budget_lease": False,
                "graph_scheduled": False,
                "graph_executed": False,
                "runtime_parallelism_created": False,
                "budget_lease_created": False,
                "search_dispatched": False,
                "retrieval_dispatched": False,
                "called_provider": False,
                "called_model": False,
                "called_fetch_read": False,
                "called_retrieval": False,
            }
        )
    return refs


def _default_review_packet_refs(
    *,
    checkpoint_id: str,
    scenario_kind: str,
    serial_dry_run_status: str,
    parent_graph_ref: Mapping[str, Any],
    workbench_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
) -> list[dict[str, Any]]:
    packet_seed = {
        "checkpoint_id": checkpoint_id,
        "scenario_kind": scenario_kind,
        "serial_dry_run_status": serial_dry_run_status,
        "graph_digest": parent_graph_ref.get("graph_digest"),
        "workbench_digest": workbench_ref.get("cross_component_analyst_digest"),
        "validation_digest": validation_ref.get("dprime_synthesis_validation_digest"),
        "admission_digest": admission_ref.get("runkernel_graph_admission_digest"),
    }
    digest = _digest_json(packet_seed)
    return [
        {
            "schema_version": "multicomponent_serial_review_packet_ref_v0",
            "review_packet_id": f"{checkpoint_id}:review-packet",
            "review_packet_digest": digest,
            "checkpoint_id": checkpoint_id,
            "scenario_kind": scenario_kind,
            "serial_dry_run_status": serial_dry_run_status,
            "review_artifact_only": True,
            "product_ready": False,
            "created_fap": False,
            "created_author_output": False,
            "created_source_display": False,
            "rendered_citations": False,
            "claimed_source_obligation_satisfaction": False,
            "claimed_product_correctness": False,
            "claimed_friend_mvp": False,
            "fap_created": False,
            "author_output_created": False,
            "source_display_created": False,
            "citations_rendered": False,
            "source_obligation_satisfaction_claimed": False,
            "product_correctness_claimed": False,
            "friend_mvp_claimed": False,
        }
    ]


def _default_serial_status(admission_status: Any) -> str:
    status = _clean_text(admission_status, limit=120)
    if status == ADMISSION_STATUS_ADMITTED:
        return SERIAL_DRY_RUN_STATUS_REPRESENTED
    if status == ADMISSION_STATUS_ADMITTED_WITH_CAVEATS:
        return SERIAL_DRY_RUN_STATUS_REPRESENTED_WITH_CAVEATS
    if status in {
        ADMISSION_STATUS_BLOCKED,
        ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED,
    }:
        return SERIAL_DRY_RUN_STATUS_BLOCKED
    if status == ADMISSION_STATUS_CHALLENGED:
        return SERIAL_DRY_RUN_STATUS_CHALLENGED
    if status == ADMISSION_STATUS_RECOVERY_AUTHORIZED:
        return SERIAL_DRY_RUN_STATUS_RECOVERY_AUTHORIZED
    if status == ADMISSION_STATUS_UNSUPPORTED:
        return SERIAL_DRY_RUN_STATUS_UNSUPPORTED
    if status in {ADMISSION_STATUS_DRAFT, ADMISSION_STATUS_ADMISSION_REQUESTED}:
        return SERIAL_DRY_RUN_STATUS_DRAFT
    return SERIAL_DRY_RUN_STATUS_UNSUPPORTED


def _default_checkpoint_id(
    *,
    parent_graph_ref: Mapping[str, Any],
    workbench_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
    serial_dry_run_status: str,
) -> str:
    digest = _digest_json(
        {
            "phase": MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_PHASE,
            "graph_digest": parent_graph_ref.get("graph_digest"),
            "workbench_digest": workbench_ref.get("cross_component_analyst_digest"),
            "validation_digest": validation_ref.get("dprime_synthesis_validation_digest"),
            "admission_digest": admission_ref.get("runkernel_graph_admission_digest"),
            "serial_dry_run_status": serial_dry_run_status,
        }
    )
    return f"multicomponent-serial-dry-run-checkpoint:v0:{digest[:20]}"


def _required_serial_status(value: Any) -> str:
    status = _required_text(value, "serial_dry_run_status")
    if status not in ALLOWED_SERIAL_DRY_RUN_STATUSES:
        raise MulticomponentSerialDryRunCheckpointError(
            f"unsupported serial dry-run checkpoint status: {status}"
        )
    return status


def _required_admission_status(value: Any) -> str:
    status = _required_text(value, "admission_status")
    if status not in ALLOWED_ADMISSION_STATUSES:
        raise MulticomponentSerialDryRunCheckpointError(
            f"unsupported RunKernel graph admission status: {status}"
        )
    return status


def _require_component_count_matches_graph(
    *,
    component_node_refs: Sequence[Mapping[str, Any]],
    parent_graph_ref: Mapping[str, Any],
) -> None:
    declared = _bounded_int(parent_graph_ref.get("component_node_count"), default=-1)
    if declared >= 0 and declared != len(component_node_refs):
        raise MulticomponentSerialDryRunCheckpointError(
            "serial checkpoint component refs must preserve parent graph component count"
        )


def _require_same_graph_ref(
    *,
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    context: str,
) -> None:
    for key in ("graph_id", "graph_digest", "parent_run_id"):
        if actual.get(key) != expected.get(key):
            raise MulticomponentSerialDryRunCheckpointError(
                f"{context} must match parent graph {key}"
            )


def _require_preserved_refs(
    *,
    expected: Sequence[Mapping[str, Any]],
    actual: Sequence[Mapping[str, Any]],
    context: str,
) -> None:
    expected_ids = {_ref_identity(item) for item in expected}
    expected_ids.discard(_empty_identity())
    if not expected_ids:
        return
    actual_ids = {_ref_identity(item) for item in actual}
    if not expected_ids <= actual_ids:
        raise MulticomponentSerialDryRunCheckpointError(
            f"serial checkpoint must preserve {context}"
        )


def _proposal_claim_identity_map(value: Any) -> dict[tuple[str, str], dict[str, str]]:
    claims: dict[tuple[str, str], dict[str, str]] = {}
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        proposal_id = _clean_text(ref.get("synthesis_proposal_id"), limit=320)
        proposal_digest = _clean_text(
            ref.get("synthesis_proposal_digest"),
            limit=128,
        )
        if proposal_id and proposal_digest:
            claims[(proposal_id, proposal_digest)] = _synthesis_claim_identity_ref(
                ref.get("synthesis_claim_ref")
            )
    return claims


def _synthesis_proposal_identity_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        proposal_id = _clean_text(ref.get("synthesis_proposal_id"), limit=320)
        proposal_digest = _clean_text(
            ref.get("synthesis_proposal_digest"),
            limit=128,
        )
        if not proposal_id or not proposal_digest:
            continue
        identity = (proposal_id, proposal_digest)
        if identity in seen:
            continue
        seen.add(identity)
        refs.append(
            _without_empty(
                {
                    "schema_version": ref.get("schema_version"),
                    "synthesis_proposal_id": proposal_id,
                    "synthesis_proposal_digest": proposal_digest,
                    "proposal_only": ref.get("proposal_only") is True,
                    "synthesis_claim_ref": _synthesis_claim_identity_ref(
                        ref.get("synthesis_claim_ref")
                    ),
                }
            )
        )
    return refs


def _required_synthesis_identity(ref: Mapping[str, Any]) -> tuple[str, str]:
    nested = _safe_mapping(ref.get("synthesis_proposal_ref"))
    proposal_id = (
        _clean_text(ref.get("synthesis_proposal_id"), limit=320)
        or _clean_text(nested.get("synthesis_proposal_id"), limit=320)
    )
    proposal_digest = (
        _clean_text(ref.get("synthesis_proposal_digest"), limit=128)
        or _clean_text(nested.get("synthesis_proposal_digest"), limit=128)
    )
    if not proposal_id or not proposal_digest:
        raise MulticomponentSerialDryRunCheckpointError(
            "synthesis refs must bind synthesis proposal id/digest"
        )
    return proposal_id, proposal_digest


def _synthesis_claim_identity_ref(value: Any) -> dict[str, str]:
    ref = _safe_mapping(value)
    if not ref:
        return {}
    _reject_forbidden_material(ref, context="synthesis_claim_ref")
    claim_id = _clean_text(
        ref.get("claim_id") or ref.get("synthesis_claim_id"),
        limit=320,
    )
    claim_digest = _clean_text(
        ref.get("claim_digest") or ref.get("synthesis_claim_digest"),
        limit=128,
    )
    if not claim_id or not claim_digest:
        raise MulticomponentSerialDryRunCheckpointError(
            "synthesis_claim_ref requires claim id and digest"
        )
    return {"claim_id": claim_id, "claim_digest": claim_digest}


def _typed_ref(ref: Mapping[str, Any]) -> bool:
    has_type = any(
        _clean_text(ref.get(key), limit=260)
        for key in ("schema_version", "ref_kind", "kind", "status")
    )
    has_identity = any(
        _clean_text(value, limit=320)
        for key, value in ref.items()
        if _normalize_key(key).endswith(("_id", "_digest", "_ref"))
    )
    return bool(has_type and has_identity)


def _ref_identity(ref: Mapping[str, Any]) -> tuple[str, str]:
    safe = _safe_mapping(ref)
    id_value = ""
    digest_value = ""
    for key, value in safe.items():
        normalized = _normalize_key(key)
        if normalized.endswith("_id") and not id_value:
            id_value = _clean_text(value, limit=320) or ""
        if normalized.endswith("_digest") and not digest_value:
            digest_value = _clean_text(value, limit=128) or ""
    if not id_value and not digest_value:
        id_value = _clean_text(safe.get("node_id"), limit=320) or ""
        digest_value = _clean_text(safe.get("component_id"), limit=320) or ""
    return id_value, digest_value


def _empty_identity() -> tuple[str, str]:
    return "", ""


def _collect_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            found.add(_normalize_key(key))
            found.update(_collect_keys(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            found.update(_collect_keys(item))
    return found


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def _safe_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return list(value)
    return [value]


def _safe_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if ref:
            refs.append(_json_safe(ref))
    return refs


def _required_text(value: Any, key: str, *, limit: int = 900) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        raise MulticomponentSerialDryRunCheckpointError(f"missing {key}")
    return text


def _nonclaims(value: Any) -> list[str]:
    supplied = _text_tuple(value, limit=500)
    combined: list[str] = []
    for item in (*SERIAL_CHECKPOINT_NONCLAIMS, *supplied):
        if item not in combined:
            combined.append(item)
    return combined


def _text_tuple(value: Any, *, limit: int) -> tuple[str, ...]:
    texts: list[str] = []
    for item in _safe_sequence(value):
        text = _clean_text(item, limit=limit)
        if text and text not in texts:
            texts.append(text)
    return tuple(texts)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:limit]


def _bounded_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in payload.items()
        if item not in (None, "", [], {})
    }


def _without_checkpoint_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "checkpoint_digest"}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ALLOWED_SERIAL_DRY_RUN_STATUSES",
    "MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_PHASE",
    "MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_RUNTIME_CONSUMER",
    "MULTICOMPONENT_SERIAL_DRY_RUN_CHECKPOINT_V0_SCHEMA_VERSION",
    "MulticomponentSerialDryRunCheckpointError",
    "SERIAL_CHECKPOINT_CLOSED_DOWNSTREAM_FLAGS",
    "SERIAL_CHECKPOINT_RAW_PRIVATE_RETENTION_FALSE_FLAGS",
    "SERIAL_DRY_RUN_STATUS_BLOCKED",
    "SERIAL_DRY_RUN_STATUS_CHALLENGED",
    "SERIAL_DRY_RUN_STATUS_DRAFT",
    "SERIAL_DRY_RUN_STATUS_RECOVERY_AUTHORIZED",
    "SERIAL_DRY_RUN_STATUS_REPRESENTED",
    "SERIAL_DRY_RUN_STATUS_REPRESENTED_WITH_CAVEATS",
    "SERIAL_DRY_RUN_STATUS_UNSUPPORTED",
    "multicomponent_serial_dry_run_checkpoint_v0_from_artifacts",
    "multicomponent_serial_dry_run_checkpoint_v0_ref",
    "validate_multicomponent_serial_dry_run_checkpoint_v0",
]
