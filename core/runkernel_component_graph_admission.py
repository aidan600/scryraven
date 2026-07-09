"""RunKernel graph/synthesis admission V0 over validated compact refs.

This module is a deterministic admission boundary for ComponentWorkGraph V0,
Cross-Component Analyst Workbench V0, and synthesis D-prime validation V0 refs.
It does not execute graph nodes, schedule work, dispatch retrieval, perform
Workbench or D-prime work, mutate the live AnswerContract, create
SufficiencyReadiness/FAP/Author/source display, render citations, or claim
product correctness.
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
    SUPPORT_LIKE_VALIDATION_STATUSES,
    dprime_synthesis_validation_v0_ref,
    validate_dprime_synthesis_validation_v0,
)

RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_SCHEMA_VERSION = (
    "runkernel_component_graph_admission_v0"
)
RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_PHASE = (
    "RUNKERNEL-COMPONENT-GRAPH-ADMISSION-V0-01"
)
RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_RUNTIME_CONSUMER = (
    "future MULTICOMPONENT-SERIAL-DRY-RUN-PLANNING-CHECKPOINT-01 and later Sufficiency/FAP phases"
)
RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_OWNER = (
    "RunKernel.ComponentGraphAdmission"
)

ADMISSION_STATUS_DRAFT = "draft"
ADMISSION_STATUS_ADMISSION_REQUESTED = "admission_requested"
ADMISSION_STATUS_ADMITTED = "admitted"
ADMISSION_STATUS_ADMITTED_WITH_CAVEATS = "admitted_with_caveats"
ADMISSION_STATUS_BLOCKED = "blocked"
ADMISSION_STATUS_CHALLENGED = "challenged"
ADMISSION_STATUS_RECOVERY_AUTHORIZED = "recovery_authorized"
ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED = "contract_amendment_required"
ADMISSION_STATUS_UNSUPPORTED = "unsupported"

SUPPORT_ADMISSION_STATUSES = frozenset(
    {ADMISSION_STATUS_ADMITTED, ADMISSION_STATUS_ADMITTED_WITH_CAVEATS}
)
ALLOWED_ADMISSION_STATUSES = frozenset(
    {
        ADMISSION_STATUS_DRAFT,
        ADMISSION_STATUS_ADMISSION_REQUESTED,
        ADMISSION_STATUS_ADMITTED,
        ADMISSION_STATUS_ADMITTED_WITH_CAVEATS,
        ADMISSION_STATUS_BLOCKED,
        ADMISSION_STATUS_CHALLENGED,
        ADMISSION_STATUS_RECOVERY_AUTHORIZED,
        ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED,
        ADMISSION_STATUS_UNSUPPORTED,
    }
)

RUNKERNEL_GRAPH_ADMISSION_CLOSED_DOWNSTREAM_FLAGS = {
    "runkernel_graph_admission_executed_graph": False,
    "runkernel_graph_admission_scheduled_graph": False,
    "runkernel_graph_admission_created_runtime_parallelism": False,
    "runkernel_graph_admission_created_budget_lease": False,
    "runkernel_graph_admission_dispatched_search": False,
    "runkernel_graph_admission_called_provider": False,
    "runkernel_graph_admission_called_model": False,
    "runkernel_graph_admission_called_fetch_read": False,
    "runkernel_graph_admission_called_retrieval": False,
    "runkernel_graph_admission_performed_cross_component_analysis": False,
    "runkernel_graph_admission_performed_dprime_validation": False,
    "runkernel_graph_admission_created_sufficiency_readiness": False,
    "runkernel_graph_admission_created_fap": False,
    "runkernel_graph_admission_created_author_output": False,
    "runkernel_graph_admission_created_source_display": False,
    "runkernel_graph_admission_rendered_citations": False,
    "runkernel_graph_admission_claimed_product_correctness": False,
}

RUNKERNEL_GRAPH_ADMISSION_RAW_PRIVATE_RETENTION_FALSE_FLAGS = {
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
    "full_trace_retained": False,
    "local_output_packet_retained": False,
    "secrets_retained": False,
}

RUNKERNEL_GRAPH_ADMISSION_NONCLAIMS = (
    "RunKernel graph/synthesis admission V0 admits, blocks, challenges, or authorizes bounded future recovery over refs only.",
    "RunKernel graph/synthesis admission V0 does not execute graph nodes, schedule work, create runtime parallelism, or create budget leases.",
    "RunKernel graph/synthesis admission V0 does not dispatch search, provider, model, fetch/read, or retrieval work.",
    "RunKernel graph/synthesis admission V0 does not perform Cross-Component Analyst work or D-prime validation.",
    "RunKernel graph/synthesis admission V0 does not mutate the live/current AnswerContract in this phase.",
    "RunKernel graph/synthesis admission V0 does not create SufficiencyReadiness, FAP, Author output, source display, rendered citations, or product correctness.",
)

_REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "phase",
    "runkernel_graph_admission_id",
    "runkernel_graph_admission_digest",
    "parent_run_id",
    "parent_graph_ref",
    "cross_component_analyst_ref",
    "dprime_synthesis_validation_ref",
    "input_graph_status",
    "input_workbench_status",
    "input_validation_status",
    "admission_status",
    "admission_decision_refs",
    "admitted_synthesis_refs",
    "blocked_synthesis_refs",
    "challenge_refs",
    "recovery_authorization_refs",
    "contract_amendment_candidate_refs",
    "accepted_graph_state_refs",
    "accepted_synthesis_state_refs",
    "required_caveat_refs",
    "preserved_nonclaim_refs",
    "blocker_refs",
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

_ALLOWED_FALSE_KEYS = frozenset(
    {
        *RUNKERNEL_GRAPH_ADMISSION_CLOSED_DOWNSTREAM_FLAGS,
        *RUNKERNEL_GRAPH_ADMISSION_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
        *GRAPH_CLOSED_DOWNSTREAM_FLAGS,
        *GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
        "answer_contract_mutated",
        "applied_to_current_answer_contract",
        "called_fetch_read",
        "called_model",
        "called_provider",
        "called_retrieval",
        "contract_amendment_applied",
        "current_answer_contract_mutated",
        "dispatched_retrieval",
        "dispatched_search",
        "executed_graph",
        "graph_executed_nodes",
        "graph_scheduled_runtime_work",
        "live_current_answer_contract_mutated",
        "mutated_answer_contract",
        "performed_cross_component_analysis",
        "performed_dprime_validation",
        "product_correctness_claimed",
        "retrieval_dispatched",
        "scheduled_graph",
        "search_dispatched",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *RUNKERNEL_GRAPH_ADMISSION_CLOSED_DOWNSTREAM_FLAGS,
        "admitted_support",
        "answer_contract_applied",
        "answer_contract_mutated",
        "applied_to_current_answer_contract",
        "author_output_created",
        "author_ready",
        "budget_lease_created",
        "called_fetch_read",
        "called_model",
        "called_provider",
        "called_retrieval",
        "citation_rendering_created",
        "citations_rendered",
        "contract_amendment_applied",
        "created_author_output",
        "created_budget_lease",
        "created_fap",
        "created_runtime_parallelism",
        "created_source_display",
        "created_sufficiency_readiness",
        "current_answer_contract_mutated",
        "dispatched_retrieval",
        "dispatched_search",
        "executed_graph",
        "fap_created",
        "fap_ready",
        "graph_executed_nodes",
        "graph_scheduled_runtime_work",
        "live_current_answer_contract_mutated",
        "mutated_answer_contract",
        "performed_cross_component_analysis",
        "performed_dprime_validation",
        "product_correctness_claimed",
        "provider_called",
        "rendered_citations",
        "retrieval_authorized",
        "retrieval_dispatched",
        "runkernel_admitted",
        "scheduled_graph",
        "search_dispatched",
        "source_display_created",
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
        "recovery_status",
        "ref_status",
        "runkernel_admission_status",
        "search_authorization_status",
        "state_status",
        "status",
        "validation_status",
    }
)

_DANGEROUS_STATUS_VALUES = frozenset(
    {
        "accepted",
        "admitted",
        "applied",
        "approved",
        "authorized",
        "dispatched",
        "executed",
    }
)


class RunKernelComponentGraphAdmissionError(ValueError):
    """Raised when RunKernel graph/synthesis admission V0 validation fails."""


def runkernel_component_graph_admission_v0_from_refs(
    *,
    parent_graph_ref: Mapping[str, Any],
    cross_component_analyst_ref: Mapping[str, Any],
    dprime_synthesis_validation_ref: Mapping[str, Any],
    runkernel_graph_admission_id: str | None = None,
    admission_status: str | None = None,
    admission_decision_refs: Sequence[Mapping[str, Any]] | None = None,
    admitted_synthesis_refs: Sequence[Mapping[str, Any]] | None = None,
    blocked_synthesis_refs: Sequence[Mapping[str, Any]] | None = None,
    challenge_refs: Sequence[Mapping[str, Any]] | None = None,
    recovery_authorization_refs: Sequence[Mapping[str, Any]] | None = None,
    contract_amendment_candidate_refs: Sequence[Mapping[str, Any]] | None = None,
    accepted_graph_state_refs: Sequence[Mapping[str, Any]] | None = None,
    accepted_synthesis_state_refs: Sequence[Mapping[str, Any]] | None = None,
    required_caveat_refs: Sequence[Mapping[str, Any]] | None = None,
    preserved_nonclaim_refs: Sequence[Mapping[str, Any]] | None = None,
    blocker_refs: Sequence[Mapping[str, Any]] | None = None,
    nonclaims: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Build a validated RunKernel-owned admission artifact from validated inputs.

    The builder accepts the existing typed graph, Workbench, and synthesis
    D-prime artifacts/refs and validates them through their owning helpers
    before creating RunKernel admission refs. It performs no runtime work.
    """

    graph = _validate_graph_input(parent_graph_ref)
    workbench = _validate_workbench_input(cross_component_analyst_ref)
    validation = _validate_dprime_validation_input(dprime_synthesis_validation_ref)
    graph_ref = _compact_parent_graph_ref(graph)
    workbench_ref = _compact_workbench_ref(workbench)
    validation_ref = dprime_synthesis_validation_v0_ref(validation)
    _validate_input_binding(
        parent_graph_ref=graph_ref,
        workbench_ref=workbench_ref,
        validation_ref=validation_ref,
    )

    status = _default_admission_status(
        validation_ref["validation_status"],
        has_recovery_refs=bool(recovery_authorization_refs),
    )
    if admission_status is not None:
        status = _required_admission_status(admission_status)
    caveats = _safe_refs(
        required_caveat_refs
        if required_caveat_refs is not None
        else validation.get("caveat_refs_under_validation")
    )
    nonclaim_refs = _safe_refs(
        preserved_nonclaim_refs
        if preserved_nonclaim_refs is not None
        else validation.get("nonclaim_refs_under_validation")
    )
    blockers = _safe_refs(blocker_refs)
    admission_id = (
        _clean_text(runkernel_graph_admission_id, limit=260)
        or _default_admission_id(
            parent_graph_ref=graph_ref,
            workbench_ref=workbench_ref,
            validation_ref=validation_ref,
            admission_status=status,
        )
    )
    default_admitted_refs: list[dict[str, Any]] = []
    if status in SUPPORT_ADMISSION_STATUSES:
        default_admitted_refs = [
            _admitted_synthesis_ref(
                admission_id=admission_id,
                proposal_ref=proposal,
                validation_ref=validation_ref,
                admission_status=status,
                required_caveat_refs=caveats,
                preserved_nonclaim_refs=nonclaim_refs,
            )
            for proposal in _safe_sequence(validation_ref.get("synthesis_proposal_refs"))
        ]
    normalized_admitted_refs = (
        list(admitted_synthesis_refs)
        if admitted_synthesis_refs is not None
        else default_admitted_refs
    )
    normalized_blocked_refs = (
        list(blocked_synthesis_refs)
        if blocked_synthesis_refs is not None
        else _default_blocked_synthesis_refs(
            admission_id=admission_id,
            validation_ref=validation_ref,
            admission_status=status,
        )
    )
    normalized_challenge_refs = (
        list(challenge_refs)
        if challenge_refs is not None
        else _default_challenge_refs(
            admission_id=admission_id,
            validation_ref=validation_ref,
            admission_status=status,
        )
    )
    normalized_decision_refs = (
        list(admission_decision_refs)
        if admission_decision_refs is not None
        else [
            _admission_decision_ref(
                admission_id=admission_id,
                validation_ref=validation_ref,
                admission_status=status,
            )
        ]
    )
    normalized_graph_state_refs = (
        list(accepted_graph_state_refs)
        if accepted_graph_state_refs is not None
        else [
            _accepted_graph_state_ref(
                admission_id=admission_id,
                parent_graph_ref=graph_ref,
                admission_status=status,
            )
        ]
    )
    normalized_synthesis_state_refs = (
        list(accepted_synthesis_state_refs)
        if accepted_synthesis_state_refs is not None
        else [
            _accepted_synthesis_state_ref(
                admission_id=admission_id,
                admitted_synthesis_ref=ref,
            )
            for ref in normalized_admitted_refs
        ]
    )
    artifact = {
        "schema_version": RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_SCHEMA_VERSION,
        "phase": RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_PHASE,
        "runtime_consumer": RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_RUNTIME_CONSUMER,
        "owner": RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_OWNER,
        "runkernel_graph_admission_id": admission_id,
        "runkernel_graph_admission_digest": None,
        "parent_run_id": graph_ref["parent_run_id"],
        "parent_graph_ref": graph_ref,
        "cross_component_analyst_ref": workbench_ref,
        "dprime_synthesis_validation_ref": validation_ref,
        "input_graph_status": graph_ref["graph_status"],
        "input_workbench_status": workbench_ref["analysis_status"],
        "input_validation_status": validation_ref["validation_status"],
        "admission_status": status,
        "admission_decision_refs": normalized_decision_refs,
        "admitted_synthesis_refs": normalized_admitted_refs,
        "blocked_synthesis_refs": normalized_blocked_refs,
        "challenge_refs": normalized_challenge_refs,
        "recovery_authorization_refs": list(recovery_authorization_refs or []),
        "contract_amendment_candidate_refs": list(
            contract_amendment_candidate_refs or []
        ),
        "accepted_graph_state_refs": normalized_graph_state_refs,
        "accepted_synthesis_state_refs": normalized_synthesis_state_refs,
        "required_caveat_refs": caveats,
        "preserved_nonclaim_refs": nonclaim_refs,
        "blocker_refs": blockers,
        "closed_downstream_flags": dict(
            RUNKERNEL_GRAPH_ADMISSION_CLOSED_DOWNSTREAM_FLAGS
        ),
        "raw_private_retention_flags": dict(
            RUNKERNEL_GRAPH_ADMISSION_RAW_PRIVATE_RETENTION_FALSE_FLAGS
        ),
        "nonclaims": _nonclaims(nonclaims),
        "answer_contract_mutated": False,
        "current_answer_contract_mutated": False,
        "contract_amendment_applied_to_current_answer_contract": False,
        **RUNKERNEL_GRAPH_ADMISSION_CLOSED_DOWNSTREAM_FLAGS,
    }
    return validate_runkernel_component_graph_admission_v0(artifact)


def validate_runkernel_component_graph_admission_v0(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and normalize a RunKernel graph/synthesis admission artifact."""

    artifact = _safe_mapping(value)
    for key in _REQUIRED_TOP_LEVEL_FIELDS:
        if key not in artifact:
            raise RunKernelComponentGraphAdmissionError(
                f"RunKernel graph/synthesis admission requires {key}"
            )
    _reject_forbidden_material(artifact, context="RunKernel graph/synthesis admission V0")
    _reject_status_laundering(
        artifact,
        context="RunKernel graph/synthesis admission V0",
    )
    if artifact.get("schema_version") != (
        RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_SCHEMA_VERSION
    ):
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph/synthesis admission schema mismatch"
        )
    if artifact.get("phase") != RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_PHASE:
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph/synthesis admission phase mismatch"
        )
    admission_id = _required_text(
        artifact.get("runkernel_graph_admission_id"),
        "runkernel_graph_admission_id",
    )
    parent_run_id = _required_text(artifact.get("parent_run_id"), "parent_run_id")
    parent_graph_ref = _validate_parent_graph_ref(artifact.get("parent_graph_ref"))
    if parent_graph_ref["parent_run_id"] != parent_run_id:
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph admission parent graph run mismatch"
        )
    workbench_ref = _validate_workbench_ref(artifact.get("cross_component_analyst_ref"))
    validation_ref = _validate_dprime_validation_ref(
        artifact.get("dprime_synthesis_validation_ref")
    )
    _validate_input_binding(
        parent_graph_ref=parent_graph_ref,
        workbench_ref=workbench_ref,
        validation_ref=validation_ref,
    )
    input_graph_status = _required_text(
        artifact.get("input_graph_status"),
        "input_graph_status",
    )
    if input_graph_status != parent_graph_ref["graph_status"]:
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph admission input graph status mismatch"
        )
    input_workbench_status = _required_text(
        artifact.get("input_workbench_status"),
        "input_workbench_status",
    )
    if input_workbench_status != workbench_ref["analysis_status"]:
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph admission input Workbench status mismatch"
        )
    input_validation_status = _required_text(
        artifact.get("input_validation_status"),
        "input_validation_status",
    )
    if input_validation_status != validation_ref["validation_status"]:
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph admission input validation status mismatch"
        )
    admission_status = _required_admission_status(artifact.get("admission_status"))
    required_caveats = _safe_refs(artifact.get("required_caveat_refs"))
    preserved_nonclaims = _safe_refs(artifact.get("preserved_nonclaim_refs"))
    _require_preserved_refs(
        expected=_safe_refs(workbench_ref.get("required_caveat_refs")),
        actual=required_caveats,
        context="required caveat refs",
    )
    _require_preserved_refs(
        expected=_safe_refs(workbench_ref.get("nonclaim_refs")),
        actual=preserved_nonclaims,
        context="nonclaim refs",
    )
    blocker_refs = _validate_non_runkernel_refs(
        artifact.get("blocker_refs"),
        field_name="blocker_refs",
    )
    admitted_synthesis_refs = _validate_admitted_synthesis_refs(
        artifact.get("admitted_synthesis_refs"),
        admission_id=admission_id,
        admission_status=admission_status,
        validation_ref=validation_ref,
        required_caveat_refs=required_caveats,
        preserved_nonclaim_refs=preserved_nonclaims,
    )
    blocked_synthesis_refs = _validate_bound_output_refs(
        artifact.get("blocked_synthesis_refs"),
        field_name="blocked_synthesis_refs",
        admission_id=admission_id,
        validation_ref=validation_ref,
        require_proposal_binding=True,
    )
    challenge_refs = _validate_bound_output_refs(
        artifact.get("challenge_refs"),
        field_name="challenge_refs",
        admission_id=admission_id,
        validation_ref=validation_ref,
        require_proposal_binding=False,
    )
    recovery_authorization_refs = _validate_recovery_authorization_refs(
        artifact.get("recovery_authorization_refs"),
        admission_id=admission_id,
        validation_ref=validation_ref,
        known_component_refs=_safe_sequence(workbench_ref.get("component_node_refs")),
    )
    contract_refs = _validate_contract_amendment_candidate_refs(
        artifact.get("contract_amendment_candidate_refs")
    )
    decision_refs = _validate_bound_output_refs(
        artifact.get("admission_decision_refs"),
        field_name="admission_decision_refs",
        admission_id=admission_id,
        validation_ref=validation_ref,
        require_proposal_binding=False,
    )
    if not decision_refs:
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph admission requires admission_decision_refs"
        )
    accepted_graph_state_refs = _validate_bound_output_refs(
        artifact.get("accepted_graph_state_refs"),
        field_name="accepted_graph_state_refs",
        admission_id=admission_id,
        validation_ref=validation_ref,
        require_proposal_binding=False,
    )
    accepted_synthesis_state_refs = _validate_bound_output_refs(
        artifact.get("accepted_synthesis_state_refs"),
        field_name="accepted_synthesis_state_refs",
        admission_id=admission_id,
        validation_ref=validation_ref,
        require_proposal_binding=True,
    )
    _validate_admission_semantics(
        admission_status=admission_status,
        validation_status=validation_ref["validation_status"],
        admitted_synthesis_refs=admitted_synthesis_refs,
        blocked_synthesis_refs=blocked_synthesis_refs,
        challenge_refs=challenge_refs,
        recovery_authorization_refs=recovery_authorization_refs,
        contract_amendment_candidate_refs=contract_refs,
        blocker_refs=blocker_refs,
    )
    closed_flags = _validate_closed_downstream_flags(artifact)
    raw_flags = _validate_raw_private_flags(artifact)
    _validate_contract_boundary_flags(artifact)
    normalized = {
        **_json_safe(artifact),
        "runkernel_graph_admission_id": admission_id,
        "parent_run_id": parent_run_id,
        "parent_graph_ref": parent_graph_ref,
        "cross_component_analyst_ref": workbench_ref,
        "dprime_synthesis_validation_ref": validation_ref,
        "input_graph_status": input_graph_status,
        "input_workbench_status": input_workbench_status,
        "input_validation_status": input_validation_status,
        "admission_status": admission_status,
        "admission_decision_refs": decision_refs,
        "admitted_synthesis_refs": admitted_synthesis_refs,
        "blocked_synthesis_refs": blocked_synthesis_refs,
        "challenge_refs": challenge_refs,
        "recovery_authorization_refs": recovery_authorization_refs,
        "contract_amendment_candidate_refs": contract_refs,
        "accepted_graph_state_refs": accepted_graph_state_refs,
        "accepted_synthesis_state_refs": accepted_synthesis_state_refs,
        "required_caveat_refs": required_caveats,
        "preserved_nonclaim_refs": preserved_nonclaims,
        "blocker_refs": blocker_refs,
        "closed_downstream_flags": closed_flags,
        "raw_private_retention_flags": raw_flags,
        "nonclaims": _nonclaims(artifact.get("nonclaims")),
        "answer_contract_mutated": False,
        "current_answer_contract_mutated": False,
        "contract_amendment_applied_to_current_answer_contract": False,
        **closed_flags,
    }
    declared = _clean_text(
        artifact.get("runkernel_graph_admission_digest"),
        limit=128,
    )
    digest = _digest_json(_without_admission_digest(normalized))
    if declared and declared != digest:
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph/synthesis admission digest mismatch"
        )
    normalized["runkernel_graph_admission_digest"] = digest
    _reject_forbidden_material(
        normalized,
        context="RunKernel graph/synthesis admission V0",
    )
    _reject_status_laundering(
        normalized,
        context="RunKernel graph/synthesis admission V0",
    )
    return normalized


def runkernel_component_graph_admission_v0_ref(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a compact safe RunKernel admission ref for future graph consumers."""

    if not _safe_mapping(value):
        return {}
    admission = validate_runkernel_component_graph_admission_v0(value)
    return _without_empty(
        {
            "schema_version": admission.get("schema_version"),
            "phase": admission.get("phase"),
            "owner": admission.get("owner"),
            "runkernel_graph_admission_id": admission.get(
                "runkernel_graph_admission_id"
            ),
            "runkernel_graph_admission_digest": admission.get(
                "runkernel_graph_admission_digest"
            ),
            "parent_run_id": admission.get("parent_run_id"),
            "parent_graph_ref": _safe_mapping(admission.get("parent_graph_ref")),
            "cross_component_analyst_ref": _safe_mapping(
                admission.get("cross_component_analyst_ref")
            ),
            "dprime_synthesis_validation_ref": _safe_mapping(
                admission.get("dprime_synthesis_validation_ref")
            ),
            "admission_status": admission.get("admission_status"),
            "admitted_synthesis_ref_count": len(
                _safe_sequence(admission.get("admitted_synthesis_refs"))
            ),
            "blocked_synthesis_ref_count": len(
                _safe_sequence(admission.get("blocked_synthesis_refs"))
            ),
            "challenge_ref_count": len(_safe_sequence(admission.get("challenge_refs"))),
            "recovery_authorization_ref_count": len(
                _safe_sequence(admission.get("recovery_authorization_refs"))
            ),
            "contract_amendment_candidate_ref_count": len(
                _safe_sequence(admission.get("contract_amendment_candidate_refs"))
            ),
            "runkernel_owned_output_ref": True,
            "created_by_runkernel_component_graph_admission_v0": True,
            "graph_executed": False,
            "search_dispatched": False,
            "retrieval_dispatched": False,
            "answer_contract_mutated": False,
            "product_correctness_claimed": False,
        }
    )


def _validate_graph_input(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_component_work_graph_v0(value)
    except Exception as exc:  # noqa: BLE001 - fail closed behind local error type.
        raise RunKernelComponentGraphAdmissionError(
            f"ComponentWorkGraph input invalid: {exc}"
        ) from None


def _validate_workbench_input(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_cross_component_analyst_workbench_v0(value)
    except Exception as exc:  # noqa: BLE001 - fail closed behind local error type.
        raise RunKernelComponentGraphAdmissionError(
            f"Cross-Component Analyst Workbench input invalid: {exc}"
        ) from None


def _validate_dprime_validation_input(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_dprime_synthesis_validation_v0(value)
    except Exception as exc:  # noqa: BLE001 - fail closed behind local error type.
        raise RunKernelComponentGraphAdmissionError(
            f"D-prime synthesis validation input invalid: {exc}"
        ) from None


def _compact_parent_graph_ref(graph: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": graph.get("schema_version"),
            "phase": graph.get("phase"),
            "graph_id": graph.get("graph_id"),
            "graph_digest": graph.get("graph_digest"),
            "parent_run_id": graph.get("parent_run_id"),
            "graph_status": graph.get("graph_status"),
            "component_node_count": graph.get("component_node_count"),
            "closed_downstream_flags": _safe_mapping(
                graph.get("closed_downstream_flags")
            ),
            "raw_private_retention_flags": _safe_mapping(
                graph.get("raw_private_retention_flags")
            ),
        }
    )


def _compact_workbench_ref(workbench: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": workbench.get("schema_version"),
            "phase": workbench.get("phase"),
            "cross_component_analyst_id": workbench.get("cross_component_analyst_id"),
            "cross_component_analyst_digest": workbench.get(
                "cross_component_analyst_digest"
            ),
            "parent_run_id": workbench.get("parent_run_id"),
            "parent_graph_ref": _safe_mapping(workbench.get("parent_graph_ref")),
            "analysis_status": workbench.get("analysis_status"),
            "proposal_only": True,
            "component_node_refs": _safe_refs(workbench.get("component_node_refs")),
            "dependency_edge_refs": _safe_refs(workbench.get("dependency_edge_refs")),
            "synthesis_proposal_refs": _synthesis_proposal_identity_refs(
                workbench.get("synthesis_proposal_refs")
            ),
            "required_caveat_refs": _safe_refs(workbench.get("required_caveat_refs")),
            "nonclaim_refs": _safe_refs(workbench.get("nonclaim_refs")),
            "contradiction_refs": _safe_refs(workbench.get("contradiction_refs")),
            "unresolved_dependency_refs": _safe_refs(
                workbench.get("unresolved_dependency_refs")
            ),
            "missing_component_proposal_refs": _safe_refs(
                workbench.get("missing_component_proposal_refs")
            ),
            "cross_component_analyst_created_runkernel_admission": False,
            "cross_component_analyst_admitted_support": False,
            "cross_component_analyst_mutated_answer_contract": False,
            "cross_component_analyst_mutated_parent_graph": False,
        }
    )


def _validate_parent_graph_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION:
        raise RunKernelComponentGraphAdmissionError("parent_graph_ref schema mismatch")
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
        raise RunKernelComponentGraphAdmissionError(
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
        raise RunKernelComponentGraphAdmissionError(
            "cross_component_analyst_ref must remain proposal-only"
        )
    parent_graph_ref = _validate_parent_graph_ref(ref.get("parent_graph_ref"))
    component_node_refs = _validate_component_node_refs(ref.get("component_node_refs"))
    normalized = {
        **_json_safe(ref),
        "parent_graph_ref": parent_graph_ref,
        "component_node_refs": component_node_refs,
        "dependency_edge_refs": _safe_refs(ref.get("dependency_edge_refs")),
        "synthesis_proposal_refs": _synthesis_proposal_identity_refs(
            ref.get("synthesis_proposal_refs")
        ),
        "required_caveat_refs": _safe_refs(ref.get("required_caveat_refs")),
        "nonclaim_refs": _safe_refs(ref.get("nonclaim_refs")),
        "contradiction_refs": _safe_refs(ref.get("contradiction_refs")),
        "unresolved_dependency_refs": _safe_refs(ref.get("unresolved_dependency_refs")),
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
        raise RunKernelComponentGraphAdmissionError(
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
        "runkernel_admission_created": False,
        "answer_contract_mutated": False,
        "retrieval_authorized": False,
        "product_correctness_claimed": False,
    }
    for key in (
        "runkernel_admission_created",
        "answer_contract_mutated",
        "retrieval_authorized",
        "product_correctness_claimed",
    ):
        if ref.get(key) is not False:
            raise RunKernelComponentGraphAdmissionError(
                f"dprime_synthesis_validation_ref must keep {key}=false"
            )
    _reject_forbidden_material(normalized, context="dprime_synthesis_validation_ref")
    _reject_status_laundering(normalized, context="dprime_synthesis_validation_ref")
    return normalized


def _validate_dprime_workbench_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION:
        raise RunKernelComponentGraphAdmissionError(
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
        raise RunKernelComponentGraphAdmissionError(
            "D-prime validation Workbench ref must remain proposal-only"
        )
    return _json_safe(ref)


def _validate_input_binding(
    *,
    parent_graph_ref: Mapping[str, Any],
    workbench_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
) -> None:
    if workbench_ref.get("parent_run_id") != parent_graph_ref.get("parent_run_id"):
        raise RunKernelComponentGraphAdmissionError(
            "Workbench ref parent_run_id must match graph ref"
        )
    if validation_ref.get("parent_run_id") != parent_graph_ref.get("parent_run_id"):
        raise RunKernelComponentGraphAdmissionError(
            "D-prime validation ref parent_run_id must match graph ref"
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
    validation_workbench = _safe_mapping(validation_ref.get("cross_component_analyst_ref"))
    for key in ("cross_component_analyst_id", "cross_component_analyst_digest"):
        if validation_workbench.get(key) != workbench_ref.get(key):
            raise RunKernelComponentGraphAdmissionError(
                "D-prime validation ref must bind to the Workbench id/digest"
            )
    workbench_proposals = _proposal_claim_identity_map(
        workbench_ref.get("synthesis_proposal_refs")
    )
    validation_proposals = _proposal_claim_identity_map(
        validation_ref.get("synthesis_proposal_refs")
    )
    if not validation_proposals:
        raise RunKernelComponentGraphAdmissionError(
            "D-prime validation ref requires synthesis proposal id/digest refs"
        )
    if validation_proposals != {
        key: workbench_proposals.get(key)
        for key in validation_proposals
    }:
        raise RunKernelComponentGraphAdmissionError(
            "D-prime validation ref synthesis proposal/claim identity must match Workbench ref"
        )


def _validate_admitted_synthesis_refs(
    value: Any,
    *,
    admission_id: str,
    admission_status: str,
    validation_ref: Mapping[str, Any],
    required_caveat_refs: Sequence[Mapping[str, Any]],
    preserved_nonclaim_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = _validate_bound_output_refs(
        value,
        field_name="admitted_synthesis_refs",
        admission_id=admission_id,
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
            raise RunKernelComponentGraphAdmissionError(
                "admitted synthesis refs must preserve synthesis claim id/digest"
            )
        if ref.get("admission_status") != admission_status:
            raise RunKernelComponentGraphAdmissionError(
                "admitted synthesis refs must match top-level admission_status"
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


def _validate_bound_output_refs(
    value: Any,
    *,
    field_name: str,
    admission_id: str,
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
            raise RunKernelComponentGraphAdmissionError(
                f"{field_name} must be typed RunKernel-owned output refs"
            )
        if ref.get("runkernel_graph_admission_id") != admission_id:
            raise RunKernelComponentGraphAdmissionError(
                f"{field_name} must bind to this admission id"
            )
        if ref.get("dprime_synthesis_validation_id") not in (
            None,
            validation_ref.get("dprime_synthesis_validation_id"),
        ):
            raise RunKernelComponentGraphAdmissionError(
                f"{field_name} D-prime validation id mismatch"
            )
        if ref.get("dprime_synthesis_validation_digest") not in (
            None,
            validation_ref.get("dprime_synthesis_validation_digest"),
        ):
            raise RunKernelComponentGraphAdmissionError(
                f"{field_name} D-prime validation digest mismatch"
            )
        has_proposal = bool(
            _clean_text(ref.get("synthesis_proposal_id"), limit=320)
            or _safe_mapping(ref.get("synthesis_proposal_ref"))
        )
        if require_proposal_binding or has_proposal:
            proposal_id, proposal_digest = _required_synthesis_identity(ref)
            if (proposal_id, proposal_digest) not in proposal_index:
                raise RunKernelComponentGraphAdmissionError(
                    f"{field_name} references unknown synthesis proposal id/digest"
                )
        refs.append(_json_safe(ref))
    return refs


def _validate_recovery_authorization_refs(
    value: Any,
    *,
    admission_id: str,
    validation_ref: Mapping[str, Any],
    known_component_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = _validate_bound_output_refs(
        value,
        field_name="recovery_authorization_refs",
        admission_id=admission_id,
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
            raise RunKernelComponentGraphAdmissionError(
                "recovery authorization refs require a bounded lifecycle marker"
            )
        if _bounded_int(ref.get("max_attempts"), default=0) <= 0:
            raise RunKernelComponentGraphAdmissionError(
                "recovery authorization refs require max_attempts"
            )
        if ref.get("no_dispatch") is not True or ref.get("not_executed") is not True:
            raise RunKernelComponentGraphAdmissionError(
                "recovery authorization refs require no_dispatch and not_executed flags"
            )
        component_refs = _safe_sequence(ref.get("component_refs_involved"))
        if not component_refs:
            raise RunKernelComponentGraphAdmissionError(
                "recovery authorization refs require component refs involved"
            )
        for component_ref in component_refs:
            normalized = _validate_component_ref(component_ref)
            if (normalized["node_id"], normalized["component_id"]) not in component_index:
                raise RunKernelComponentGraphAdmissionError(
                    "recovery authorization component refs must be known Workbench components"
                )
        for key in (
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
        ):
            if ref.get(key) is True:
                raise RunKernelComponentGraphAdmissionError(
                    "recovery authorization refs must remain non-dispatching"
                )
    return refs


def _validate_contract_amendment_candidate_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        _reject_forbidden_material(
            ref,
            context="contract_amendment_candidate_refs",
        )
        _reject_status_laundering(
            ref,
            context="contract_amendment_candidate_refs",
        )
        if not _typed_ref(ref):
            raise RunKernelComponentGraphAdmissionError(
                "contract amendment candidate refs must be typed refs"
            )
        for key in (
            "answer_contract_mutated",
            "current_answer_contract_mutated",
            "live_current_answer_contract_mutated",
            "applied_to_current_answer_contract",
            "contract_amendment_applied",
        ):
            if ref.get(key) is not False:
                raise RunKernelComponentGraphAdmissionError(
                    "contract amendment candidate refs must not claim live contract mutation or application"
                )
        refs.append(_json_safe(ref))
    return refs


def _validate_non_runkernel_refs(value: Any, *, field_name: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        _reject_forbidden_material(ref, context=field_name)
        _reject_status_laundering(ref, context=field_name)
        if not _typed_ref(ref):
            raise RunKernelComponentGraphAdmissionError(
                f"{field_name} must contain typed refs"
            )
        refs.append(_json_safe(ref))
    return refs


def _validate_admission_semantics(
    *,
    admission_status: str,
    validation_status: str,
    admitted_synthesis_refs: Sequence[Mapping[str, Any]],
    blocked_synthesis_refs: Sequence[Mapping[str, Any]],
    challenge_refs: Sequence[Mapping[str, Any]],
    recovery_authorization_refs: Sequence[Mapping[str, Any]],
    contract_amendment_candidate_refs: Sequence[Mapping[str, Any]],
    blocker_refs: Sequence[Mapping[str, Any]],
) -> None:
    support_like = validation_status in SUPPORT_LIKE_VALIDATION_STATUSES
    if admission_status in SUPPORT_ADMISSION_STATUSES:
        if not support_like:
            raise RunKernelComponentGraphAdmissionError(
                "admitted synthesis requires supported D-prime validation status"
            )
        if blocker_refs:
            raise RunKernelComponentGraphAdmissionError(
                "unresolved blockers prevent admitted graph/synthesis status"
            )
        if not admitted_synthesis_refs:
            raise RunKernelComponentGraphAdmissionError(
                "admitted graph/synthesis status requires admitted synthesis refs"
            )
    elif admitted_synthesis_refs:
        raise RunKernelComponentGraphAdmissionError(
            "admitted synthesis refs are allowed only for admitted statuses"
        )
    if admission_status == ADMISSION_STATUS_RECOVERY_AUTHORIZED and not (
        recovery_authorization_refs
    ):
        raise RunKernelComponentGraphAdmissionError(
            "recovery_authorized status requires recovery authorization refs"
        )
    if admission_status == ADMISSION_STATUS_CHALLENGED and not challenge_refs:
        raise RunKernelComponentGraphAdmissionError(
            "challenged status requires challenge refs"
        )
    if admission_status == ADMISSION_STATUS_BLOCKED and not (
        blocked_synthesis_refs or blocker_refs
    ):
        raise RunKernelComponentGraphAdmissionError(
            "blocked status requires blocked synthesis or blocker refs"
        )
    if admission_status == ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED and not (
        contract_amendment_candidate_refs
    ):
        raise RunKernelComponentGraphAdmissionError(
            "contract_amendment_required status requires candidate refs"
        )


def _validate_closed_downstream_flags(artifact: Mapping[str, Any]) -> dict[str, bool]:
    closed = _safe_mapping(artifact.get("closed_downstream_flags"))
    if not closed:
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph admission missing closed_downstream_flags"
        )
    normalized: dict[str, bool] = {}
    for key in RUNKERNEL_GRAPH_ADMISSION_CLOSED_DOWNSTREAM_FLAGS:
        if closed.get(key) is not False:
            raise RunKernelComponentGraphAdmissionError(
                f"RunKernel graph admission closed flag must remain false: {key}"
            )
        if artifact.get(key) is not False:
            raise RunKernelComponentGraphAdmissionError(
                f"RunKernel graph admission top-level flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_raw_private_flags(artifact: Mapping[str, Any]) -> dict[str, bool]:
    flags = _safe_mapping(artifact.get("raw_private_retention_flags"))
    if not flags:
        raise RunKernelComponentGraphAdmissionError(
            "RunKernel graph admission missing raw_private_retention_flags"
        )
    normalized: dict[str, bool] = {}
    for key in RUNKERNEL_GRAPH_ADMISSION_RAW_PRIVATE_RETENTION_FALSE_FLAGS:
        if flags.get(key) is not False:
            raise RunKernelComponentGraphAdmissionError(
                f"RunKernel graph admission raw/private flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_graph_closed_flags(ref: Mapping[str, Any]) -> dict[str, bool]:
    closed = _safe_mapping(ref.get("closed_downstream_flags"))
    if not closed:
        raise RunKernelComponentGraphAdmissionError(
            "parent_graph_ref missing closed_downstream_flags"
        )
    normalized: dict[str, bool] = {}
    for key in GRAPH_CLOSED_DOWNSTREAM_FLAGS:
        if closed.get(key) is not False:
            raise RunKernelComponentGraphAdmissionError(
                f"parent_graph_ref closed flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_graph_raw_flags(ref: Mapping[str, Any]) -> dict[str, bool]:
    flags = _safe_mapping(ref.get("raw_private_retention_flags"))
    if not flags:
        raise RunKernelComponentGraphAdmissionError(
            "parent_graph_ref missing raw_private_retention_flags"
        )
    normalized: dict[str, bool] = {}
    for key in GRAPH_RAW_PRIVATE_RETENTION_FALSE_FLAGS:
        if flags.get(key) is not False:
            raise RunKernelComponentGraphAdmissionError(
                f"parent_graph_ref raw/private flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _validate_contract_boundary_flags(artifact: Mapping[str, Any]) -> None:
    for key in (
        "answer_contract_mutated",
        "current_answer_contract_mutated",
        "contract_amendment_applied_to_current_answer_contract",
    ):
        if artifact.get(key) is not False:
            raise RunKernelComponentGraphAdmissionError(
                "RunKernel graph admission must keep live/current AnswerContract mutation flags false"
            )


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & _FORBIDDEN_NORMALIZED_KEYS)
    if forbidden:
        raise RunKernelComponentGraphAdmissionError(
            f"{context} includes forbidden raw/private material: "
            + ", ".join(forbidden)
        )
    invalid_false_flags = sorted(_invalid_false_flags(value))
    if invalid_false_flags:
        raise RunKernelComponentGraphAdmissionError(
            f"{context} raw/private or closed flags must be explicitly false: "
            + ", ".join(invalid_false_flags)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise RunKernelComponentGraphAdmissionError(
            f"{context} attempts forbidden authority upgrade: "
            + ", ".join(dangerous)
        )


def _reject_status_laundering(value: Any, *, context: str, depth: int = 0) -> None:
    if isinstance(value, Mapping):
        if _is_runkernel_output_ref(value):
            return
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            normalized_value = _normalize_key(item)
            if (
                normalized_key in _STATUS_KEYS
                and normalized_value in _DANGEROUS_STATUS_VALUES
                and not (depth == 0 and normalized_key == "admission_status")
            ):
                raise RunKernelComponentGraphAdmissionError(
                    f"{context} carries forbidden status claim: {normalized_key}={normalized_value}"
                )
            _reject_status_laundering(item, context=context, depth=depth + 1)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            _reject_status_laundering(item, context=context, depth=depth + 1)


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        if _is_runkernel_output_ref(value):
            return found
        for key, item in value.items():
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
        if _is_runkernel_output_ref(value):
            return found
        for key, item in value.items():
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


def _admission_decision_ref(
    *,
    admission_id: str,
    validation_ref: Mapping[str, Any],
    admission_status: str,
) -> dict[str, Any]:
    return _runkernel_output_ref(
        schema_version="runkernel_graph_admission_decision_ref_v0",
        runkernel_graph_admission_id=admission_id,
        admission_decision_id=f"{admission_id}:decision",
        admission_decision_digest=_digest_json(
            {
                "admission_id": admission_id,
                "validation": validation_ref.get("dprime_synthesis_validation_digest"),
                "status": admission_status,
            }
        ),
        admission_status=admission_status,
        dprime_synthesis_validation_id=validation_ref.get(
            "dprime_synthesis_validation_id"
        ),
        dprime_synthesis_validation_digest=validation_ref.get(
            "dprime_synthesis_validation_digest"
        ),
        graph_executed=False,
        search_dispatched=False,
        retrieval_dispatched=False,
        answer_contract_mutated=False,
    )


def _admitted_synthesis_ref(
    *,
    admission_id: str,
    proposal_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
    admission_status: str,
    required_caveat_refs: Sequence[Mapping[str, Any]],
    preserved_nonclaim_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    proposal_id, proposal_digest = _required_synthesis_identity(proposal_ref)
    claim = _synthesis_claim_identity_ref(proposal_ref.get("synthesis_claim_ref"))
    return _runkernel_output_ref(
        schema_version="runkernel_graph_admission_admitted_synthesis_ref_v0",
        runkernel_graph_admission_id=admission_id,
        admitted_synthesis_id=f"{admission_id}:admitted:{proposal_id}",
        admitted_synthesis_digest=_digest_json(
            {
                "admission_id": admission_id,
                "proposal_id": proposal_id,
                "proposal_digest": proposal_digest,
                "claim": claim,
            }
        ),
        admission_status=admission_status,
        dprime_synthesis_validation_id=validation_ref.get(
            "dprime_synthesis_validation_id"
        ),
        dprime_synthesis_validation_digest=validation_ref.get(
            "dprime_synthesis_validation_digest"
        ),
        synthesis_proposal_id=proposal_id,
        synthesis_proposal_digest=proposal_digest,
        synthesis_claim_ref=claim,
        required_caveat_refs=list(required_caveat_refs),
        preserved_nonclaim_refs=list(preserved_nonclaim_refs),
        graph_executed=False,
        search_dispatched=False,
        retrieval_dispatched=False,
        answer_contract_mutated=False,
        product_correctness_claimed=False,
    )


def _default_blocked_synthesis_refs(
    *,
    admission_id: str,
    validation_ref: Mapping[str, Any],
    admission_status: str,
) -> list[dict[str, Any]]:
    if admission_status not in {ADMISSION_STATUS_BLOCKED, ADMISSION_STATUS_UNSUPPORTED}:
        return []
    return [
        _runkernel_output_ref(
            schema_version="runkernel_graph_admission_blocked_synthesis_ref_v0",
            runkernel_graph_admission_id=admission_id,
            blocked_synthesis_id=f"{admission_id}:blocked:{proposal['synthesis_proposal_id']}",
            blocked_synthesis_digest=_digest_json(
                {
                    "admission_id": admission_id,
                    "proposal": proposal,
                    "status": admission_status,
                }
            ),
            admission_status=admission_status,
            dprime_synthesis_validation_id=validation_ref.get(
                "dprime_synthesis_validation_id"
            ),
            dprime_synthesis_validation_digest=validation_ref.get(
                "dprime_synthesis_validation_digest"
            ),
            synthesis_proposal_id=proposal["synthesis_proposal_id"],
            synthesis_proposal_digest=proposal["synthesis_proposal_digest"],
            graph_executed=False,
            search_dispatched=False,
            retrieval_dispatched=False,
            support_admitted=False,
            answer_contract_mutated=False,
            product_correctness_claimed=False,
        )
        for proposal in _safe_sequence(validation_ref.get("synthesis_proposal_refs"))
    ]


def _default_challenge_refs(
    *,
    admission_id: str,
    validation_ref: Mapping[str, Any],
    admission_status: str,
) -> list[dict[str, Any]]:
    if admission_status != ADMISSION_STATUS_CHALLENGED:
        return []
    return [
        _runkernel_output_ref(
            schema_version="runkernel_graph_admission_challenge_ref_v0",
            runkernel_graph_admission_id=admission_id,
            challenge_id=f"{admission_id}:challenge:{proposal['synthesis_proposal_id']}",
            challenge_digest=_digest_json(
                {
                    "admission_id": admission_id,
                    "proposal": proposal,
                    "validation_status": validation_ref.get("validation_status"),
                }
            ),
            challenge_status=ADMISSION_STATUS_CHALLENGED,
            dprime_synthesis_validation_id=validation_ref.get(
                "dprime_synthesis_validation_id"
            ),
            dprime_synthesis_validation_digest=validation_ref.get(
                "dprime_synthesis_validation_digest"
            ),
            synthesis_proposal_id=proposal["synthesis_proposal_id"],
            synthesis_proposal_digest=proposal["synthesis_proposal_digest"],
            graph_executed=False,
            search_dispatched=False,
            retrieval_dispatched=False,
            answer_contract_mutated=False,
            product_correctness_claimed=False,
        )
        for proposal in _safe_sequence(validation_ref.get("synthesis_proposal_refs"))
    ]


def _accepted_graph_state_ref(
    *,
    admission_id: str,
    parent_graph_ref: Mapping[str, Any],
    admission_status: str,
) -> dict[str, Any]:
    return _runkernel_output_ref(
        schema_version="runkernel_graph_admission_accepted_graph_state_ref_v0",
        runkernel_graph_admission_id=admission_id,
        accepted_graph_state_id=f"{admission_id}:graph-state",
        accepted_graph_state_digest=_digest_json(
            {
                "admission_id": admission_id,
                "graph_id": parent_graph_ref.get("graph_id"),
                "graph_digest": parent_graph_ref.get("graph_digest"),
                "status": admission_status,
            }
        ),
        admission_status=admission_status,
        graph_id=parent_graph_ref.get("graph_id"),
        graph_digest=parent_graph_ref.get("graph_digest"),
        accepted_state_ref_only=True,
        answer_contract_mutated=False,
        graph_executed=False,
        search_dispatched=False,
        retrieval_dispatched=False,
    )


def _accepted_synthesis_state_ref(
    *,
    admission_id: str,
    admitted_synthesis_ref: Mapping[str, Any],
) -> dict[str, Any]:
    proposal_id, proposal_digest = _required_synthesis_identity(admitted_synthesis_ref)
    return _runkernel_output_ref(
        schema_version="runkernel_graph_admission_accepted_synthesis_state_ref_v0",
        runkernel_graph_admission_id=admission_id,
        accepted_synthesis_state_id=f"{admission_id}:synthesis-state:{proposal_id}",
        accepted_synthesis_state_digest=_digest_json(
            {
                "admission_id": admission_id,
                "proposal_id": proposal_id,
                "proposal_digest": proposal_digest,
            }
        ),
        synthesis_proposal_id=proposal_id,
        synthesis_proposal_digest=proposal_digest,
        synthesis_claim_ref=_safe_mapping(admitted_synthesis_ref.get("synthesis_claim_ref")),
        dprime_synthesis_validation_id=admitted_synthesis_ref.get(
            "dprime_synthesis_validation_id"
        ),
        dprime_synthesis_validation_digest=admitted_synthesis_ref.get(
            "dprime_synthesis_validation_digest"
        ),
        accepted_state_ref_only=True,
        answer_contract_mutated=False,
        graph_executed=False,
        search_dispatched=False,
        retrieval_dispatched=False,
    )


def _runkernel_output_ref(
    *,
    schema_version: str,
    runkernel_graph_admission_id: str,
    **payload: Any,
) -> dict[str, Any]:
    return _without_empty(
        {
            "schema_version": schema_version,
            "runkernel_graph_admission_id": runkernel_graph_admission_id,
            "runkernel_owned_output_ref": True,
            "created_by_runkernel_component_graph_admission_v0": True,
            "owner": RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_OWNER,
            **payload,
        }
    )


def _default_admission_status(
    validation_status: str,
    *,
    has_recovery_refs: bool,
) -> str:
    if validation_status == "validated_supported":
        return ADMISSION_STATUS_ADMITTED
    if validation_status == "validated_with_caveats":
        return ADMISSION_STATUS_ADMITTED_WITH_CAVEATS
    if validation_status == "unsupported":
        return ADMISSION_STATUS_UNSUPPORTED
    if validation_status == "challenged":
        return ADMISSION_STATUS_CHALLENGED
    if validation_status == "followup_needed":
        if has_recovery_refs:
            return ADMISSION_STATUS_RECOVERY_AUTHORIZED
        return ADMISSION_STATUS_CHALLENGED
    if validation_status.startswith("blocked_"):
        return ADMISSION_STATUS_BLOCKED
    return ADMISSION_STATUS_ADMISSION_REQUESTED


def _default_admission_id(
    *,
    parent_graph_ref: Mapping[str, Any],
    workbench_ref: Mapping[str, Any],
    validation_ref: Mapping[str, Any],
    admission_status: str,
) -> str:
    digest = _digest_json(
        {
            "phase": RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_PHASE,
            "graph_digest": parent_graph_ref.get("graph_digest"),
            "workbench_digest": workbench_ref.get("cross_component_analyst_digest"),
            "validation_digest": validation_ref.get("dprime_synthesis_validation_digest"),
            "admission_status": admission_status,
        }
    )
    return f"runkernel-component-graph-admission:v0:{digest[:20]}"


def _required_admission_status(value: Any) -> str:
    status = _required_text(value, "admission_status")
    if status not in ALLOWED_ADMISSION_STATUSES:
        raise RunKernelComponentGraphAdmissionError(
            f"unsupported RunKernel graph admission status: {status}"
        )
    return status


def _validate_component_node_refs(value: Any) -> list[dict[str, Any]]:
    refs = [_validate_component_ref(item) for item in _safe_sequence(value)]
    if not refs:
        raise RunKernelComponentGraphAdmissionError(
            "component_node_refs must contain typed ComponentWorkNode refs"
        )
    return refs


def _validate_component_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
        raise RunKernelComponentGraphAdmissionError(
            "component ref must be ComponentWorkNode V0"
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
        raise RunKernelComponentGraphAdmissionError(
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
        raise RunKernelComponentGraphAdmissionError(
            "synthesis_claim_ref requires claim id and digest"
        )
    return {"claim_id": claim_id, "claim_digest": claim_digest}


def _require_same_graph_ref(
    *,
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    context: str,
) -> None:
    for key in ("graph_id", "graph_digest", "parent_run_id"):
        if actual.get(key) != expected.get(key):
            raise RunKernelComponentGraphAdmissionError(
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
        raise RunKernelComponentGraphAdmissionError(
            f"RunKernel graph admission must preserve {context}"
        )


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
        raise RunKernelComponentGraphAdmissionError(f"missing {key}")
    return text


def _nonclaims(value: Any) -> list[str]:
    supplied = _text_tuple(value, limit=400)
    combined: list[str] = []
    for item in (*RUNKERNEL_GRAPH_ADMISSION_NONCLAIMS, *supplied):
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


def _without_admission_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key != "runkernel_graph_admission_digest"
    }


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ADMISSION_STATUS_ADMISSION_REQUESTED",
    "ADMISSION_STATUS_ADMITTED",
    "ADMISSION_STATUS_ADMITTED_WITH_CAVEATS",
    "ADMISSION_STATUS_BLOCKED",
    "ADMISSION_STATUS_CHALLENGED",
    "ADMISSION_STATUS_CONTRACT_AMENDMENT_REQUIRED",
    "ADMISSION_STATUS_DRAFT",
    "ADMISSION_STATUS_RECOVERY_AUTHORIZED",
    "ADMISSION_STATUS_UNSUPPORTED",
    "ALLOWED_ADMISSION_STATUSES",
    "RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_PHASE",
    "RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_RUNTIME_CONSUMER",
    "RUNKERNEL_COMPONENT_GRAPH_ADMISSION_V0_SCHEMA_VERSION",
    "RUNKERNEL_GRAPH_ADMISSION_CLOSED_DOWNSTREAM_FLAGS",
    "RUNKERNEL_GRAPH_ADMISSION_RAW_PRIVATE_RETENTION_FALSE_FLAGS",
    "RunKernelComponentGraphAdmissionError",
    "runkernel_component_graph_admission_v0_from_refs",
    "runkernel_component_graph_admission_v0_ref",
    "validate_runkernel_component_graph_admission_v0",
]
