"""Synthesis D-prime validation over Cross-Component Analyst proposals.

The artifact in this module validates Cross-Component Analyst Workbench V0
synthesis proposal refs against component, dependency, caveat, contradiction,
missing-component, and revisit refs. It does not choose synthesis claims, admit
support, mutate the parent graph or Workbench artifact, authorize retrieval,
create RunKernel admission, create FAP/Author/source display, render citations,
or claim product correctness.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_work_graph import COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION
from core.component_work_node import COMPONENT_WORK_NODE_V0_SCHEMA_VERSION
from core.cross_component_analyst_workbench import (
    CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION,
    validate_cross_component_analyst_workbench_v0,
)

DPRIME_SYNTHESIS_VALIDATION_V0_SCHEMA_VERSION = "dprime_synthesis_validation_v0"
DPRIME_SYNTHESIS_VALIDATION_V0_PHASE = "DPRIME-SYNTHESIS-VALIDATION-V0-01"
DPRIME_SYNTHESIS_VALIDATION_V0_RUNTIME_CONSUMER = (
    "future RUNKERNEL-COMPONENT-GRAPH-ADMISSION-V0-01"
)

VALIDATION_STATUS_DRAFT = "draft"
VALIDATION_STATUS_SUPPORTED = "validated_supported"
VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS = "validated_with_caveats"
VALIDATION_STATUS_CHALLENGED = "challenged"
VALIDATION_STATUS_BLOCKED_MISSING_DEPENDENCY = "blocked_missing_dependency"
VALIDATION_STATUS_BLOCKED_CONTRADICTION = "blocked_contradiction"
VALIDATION_STATUS_BLOCKED_MISSING_COMPONENT = "blocked_missing_component"
VALIDATION_STATUS_FOLLOWUP_NEEDED = "followup_needed"
VALIDATION_STATUS_UNSUPPORTED = "unsupported"

SUPPORT_LIKE_VALIDATION_STATUSES = frozenset(
    {
        VALIDATION_STATUS_SUPPORTED,
        VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS,
    }
)
ALLOWED_VALIDATION_STATUSES = frozenset(
    {
        VALIDATION_STATUS_DRAFT,
        VALIDATION_STATUS_SUPPORTED,
        VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS,
        VALIDATION_STATUS_CHALLENGED,
        VALIDATION_STATUS_BLOCKED_MISSING_DEPENDENCY,
        VALIDATION_STATUS_BLOCKED_CONTRADICTION,
        VALIDATION_STATUS_BLOCKED_MISSING_COMPONENT,
        VALIDATION_STATUS_FOLLOWUP_NEEDED,
        VALIDATION_STATUS_UNSUPPORTED,
    }
)

DPRIME_SYNTHESIS_CLOSED_DOWNSTREAM_FLAGS = {
    "dprime_synthesis_became_cross_component_analyst": False,
    "dprime_synthesis_chose_synthesis_claim": False,
    "dprime_synthesis_invented_claim": False,
    "dprime_synthesis_dropped_caveat": False,
    "dprime_synthesis_erased_blocker": False,
    "dprime_synthesis_admitted_support": False,
    "dprime_synthesis_mutated_answer_contract": False,
    "dprime_synthesis_mutated_parent_graph": False,
    "dprime_synthesis_mutated_workbench_artifact": False,
    "dprime_synthesis_authorized_retrieval": False,
    "dprime_synthesis_dispatched_search": False,
    "dprime_synthesis_called_provider": False,
    "dprime_synthesis_called_model": False,
    "dprime_synthesis_called_fetch_read": False,
    "dprime_synthesis_called_retrieval": False,
    "dprime_synthesis_created_runkernel_admission": False,
    "dprime_synthesis_created_sufficiency_readiness": False,
    "dprime_synthesis_created_fap": False,
    "dprime_synthesis_created_author_output": False,
    "dprime_synthesis_created_source_display": False,
    "dprime_synthesis_rendered_citations": False,
    "dprime_synthesis_claimed_product_correctness": False,
}

DPRIME_SYNTHESIS_RAW_PRIVATE_RETENTION_FALSE_FLAGS = {
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

DPRIME_SYNTHESIS_NONCLAIMS = (
    "Synthesis D-prime validation V0 validates existing Workbench proposal refs only.",
    "Synthesis D-prime validation V0 does not become Cross-Component Analyst or choose a synthesis claim.",
    "Synthesis D-prime validation V0 does not admit support or mutate AnswerContract state.",
    "Synthesis D-prime validation V0 does not mutate the parent ComponentWorkGraph or Workbench artifact.",
    "Synthesis D-prime validation V0 does not authorize retrieval or dispatch search.",
    "Synthesis D-prime validation V0 does not create FAP, Author output, source display, rendered citations, or product correctness.",
)

_REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "phase",
    "dprime_synthesis_validation_id",
    "dprime_synthesis_validation_digest",
    "parent_run_id",
    "parent_graph_ref",
    "cross_component_analyst_ref",
    "input_workbench_status",
    "synthesis_proposal_refs",
    "component_refs_under_validation",
    "dependency_edge_refs_under_validation",
    "caveat_refs_under_validation",
    "nonclaim_refs_under_validation",
    "contradiction_refs_under_validation",
    "unresolved_dependency_refs_under_validation",
    "missing_component_refs_under_validation",
    "evidence_refs_to_revisit",
    "source_refs_to_revisit",
    "validation_status",
    "support_validation_refs",
    "challenge_refs",
    "missing_dependency_refs",
    "caveat_preservation_refs",
    "overbreadth_challenge_refs",
    "contradiction_challenge_refs",
    "followup_need_refs",
    "runkernel_consideration_refs",
    "closed_downstream_flags",
    "raw_private_retention_flags",
    "nonclaims",
)

_OUTPUT_REF_FIELDS = (
    "support_validation_refs",
    "challenge_refs",
    "missing_dependency_refs",
    "caveat_preservation_refs",
    "overbreadth_challenge_refs",
    "contradiction_challenge_refs",
    "followup_need_refs",
    "runkernel_consideration_refs",
)

_WORKBENCH_REF_LIST_FIELDS = (
    ("caveat_refs_under_validation", "required_caveat_refs"),
    ("nonclaim_refs_under_validation", "nonclaim_refs"),
    ("contradiction_refs_under_validation", "contradiction_refs"),
    ("unresolved_dependency_refs_under_validation", "unresolved_dependency_refs"),
    ("missing_component_refs_under_validation", "missing_component_proposal_refs"),
    ("evidence_refs_to_revisit", "evidence_refs_to_revisit"),
    ("source_refs_to_revisit", "source_refs_to_revisit"),
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
        *DPRIME_SYNTHESIS_CLOSED_DOWNSTREAM_FLAGS,
        *DPRIME_SYNTHESIS_RAW_PRIVATE_RETENTION_FALSE_FLAGS,
        "admitted",
        "admitted_support",
        "answer_contract_mutated",
        "answer_created",
        "authorization_created",
        "authorization_granted",
        "author_output_created",
        "author_ready",
        "called_fetch_read",
        "called_model",
        "called_provider",
        "called_retrieval",
        "citation_eligible",
        "citation_rendered",
        "correct",
        "created_by_dprime_synthesis_validation",
        "created_fap",
        "created_runkernel_admission",
        "created_source_display",
        "created_sufficiency_readiness",
        "direct_retrieval_dispatch",
        "dispatched_search",
        "dprime_validation_became_analyst",
        "evidence_admitted",
        "fap_ready",
        "followup_authorized",
        "mutated_answer_contract",
        "mutated_parent_graph",
        "mutated_workbench_artifact",
        "not_created_by_dprime_synthesis_validation",
        "product_correctness_claimed",
        "retrieval_authorized",
        "runkernel_admission_created",
        "runkernel_admitted",
        "runkernel_authorized",
        "search_authorized",
        "search_dispatched",
        "source_display_created",
        "source_obligation_satisfied",
        "sufficiency_ready",
        "support_admitted",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *DPRIME_SYNTHESIS_CLOSED_DOWNSTREAM_FLAGS,
        "admitted",
        "admitted_by_runkernel",
        "admitted_support",
        "answer_contract_mutated",
        "answer_created",
        "authorization_created",
        "authorization_granted",
        "author_output_created",
        "author_ready",
        "called_fetch_read",
        "called_model",
        "called_provider",
        "called_retrieval",
        "citation_eligible",
        "citation_rendered",
        "correct",
        "created_by_dprime_synthesis_validation",
        "created_fap",
        "created_runkernel_admission",
        "created_source_display",
        "created_sufficiency_readiness",
        "direct_retrieval_dispatch",
        "dispatched_search",
        "dprime_validation_became_analyst",
        "evidence_admitted",
        "fap_created",
        "fap_ready",
        "followup_authorized",
        "mutated_answer_contract",
        "mutated_parent_graph",
        "mutated_workbench_artifact",
        "product_correctness_claimed",
        "retrieval_authorized",
        "runkernel_admission_created",
        "runkernel_admitted",
        "runkernel_authorized",
        "search_authorized",
        "search_dispatched",
        "source_display_created",
        "source_obligation_satisfied",
        "sufficiency_ready",
        "support_admitted",
    }
)

_STATUS_KEYS = frozenset(
    {
        "admission_status",
        "approval_status",
        "authorization_status",
        "dispatch_status",
        "execution_status",
        "fap_status",
        "readiness_status",
        "retrieval_authorization_status",
        "runkernel_admission_status",
        "runkernel_authorization_status",
        "search_authorization_status",
        "source_display_status",
        "status",
        "support_admission_status",
    }
)

_DANGEROUS_STATUS_VALUES = frozenset(
    {
        "accepted",
        "admitted",
        "applied",
        "approved",
        "author_ready",
        "authorized",
        "citation_eligible",
        "correct",
        "dispatched",
        "executed",
        "fap_ready",
        "mutated",
        "passed",
        "product_correct",
        "ready_for_author",
        "ready_for_fap",
        "retrieval_authorized",
        "runkernel_admitted",
        "runkernel_authorized",
        "search_authorized",
        "source_obligation_satisfied",
        "sufficiency_ready",
        "support_admitted",
    }
)

_SYNTHESIS_CLAIM_SELECTION_KEYS = frozenset(
    {
        "chosen_synthesis_claim_ref",
        "selected_synthesis_claim_ref",
        "validated_synthesis_claim_ref",
        "different_synthesis_claim_ref",
        "new_synthesis_claim_ref",
        "synthesis_claim_id",
        "synthesis_claim_digest",
        "chosen_synthesis_claim_id",
        "selected_synthesis_claim_id",
        "validated_synthesis_claim_id",
    }
)

_SYNTHESIS_PROPOSAL_CREATION_KEYS = frozenset(
    {
        "created_synthesis_proposal_ref",
        "created_synthesis_proposal_refs",
        "new_synthesis_proposal_ref",
        "new_synthesis_proposal_refs",
        "synthesis_proposal_ref_created",
        "synthesis_proposal_refs_created",
    }
)


class DPrimeSynthesisValidationError(ValueError):
    """Raised when synthesis D-prime validation crosses a closed boundary."""


def dprime_synthesis_validation_v0_from_workbench(
    *,
    workbench_artifact: Mapping[str, Any],
    dprime_synthesis_validation_id: str | None = None,
    validation_status: str = VALIDATION_STATUS_DRAFT,
    support_validation_refs: Sequence[Mapping[str, Any]] | None = None,
    challenge_refs: Sequence[Mapping[str, Any]] | None = None,
    missing_dependency_refs: Sequence[Mapping[str, Any]] | None = None,
    caveat_preservation_refs: Sequence[Mapping[str, Any]] | None = None,
    overbreadth_challenge_refs: Sequence[Mapping[str, Any]] | None = None,
    contradiction_challenge_refs: Sequence[Mapping[str, Any]] | None = None,
    followup_need_refs: Sequence[Mapping[str, Any]] | None = None,
    runkernel_consideration_refs: Sequence[Mapping[str, Any]] | None = None,
    component_refs_under_validation: Sequence[Mapping[str, Any]] | None = None,
    dependency_edge_refs_under_validation: Sequence[Mapping[str, Any]] | None = None,
    caveat_refs_under_validation: Sequence[Mapping[str, Any]] | None = None,
    nonclaim_refs_under_validation: Sequence[Mapping[str, Any]] | None = None,
    contradiction_refs_under_validation: Sequence[Mapping[str, Any]] | None = None,
    unresolved_dependency_refs_under_validation: Sequence[Mapping[str, Any]] | None = None,
    missing_component_refs_under_validation: Sequence[Mapping[str, Any]] | None = None,
    evidence_refs_to_revisit: Sequence[Mapping[str, Any]] | None = None,
    source_refs_to_revisit: Sequence[Mapping[str, Any]] | None = None,
    nonclaims: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Build a non-authority validation artifact from a Workbench proposal.

    The builder consumes only the typed Workbench/graph/node refs and the
    caller-supplied validation, challenge, and follow-up refs.
    """

    workbench = _validate_workbench_input(workbench_artifact)
    synthesis_refs = [dict(item) for item in workbench["synthesis_proposal_refs"]]
    node_index = _component_node_index(workbench["component_node_refs"])
    edge_index = _dependency_edge_index(workbench["dependency_edge_refs"])
    default_component_refs = _dedupe_component_refs(
        [
            *workbench.get("component_refs_supporting_synthesis", []),
            *_component_refs_from_synthesis_refs(synthesis_refs),
        ],
        node_index=node_index,
    )
    default_dependency_refs = _dedupe_dependency_refs(
        [
            *workbench.get("dependency_edge_refs", []),
            *_dependency_refs_from_synthesis_refs(synthesis_refs),
        ],
        edge_index=edge_index,
    )
    seed_payload = {
        "phase": DPRIME_SYNTHESIS_VALIDATION_V0_PHASE,
        "cross_component_analyst_digest": workbench.get(
            "cross_component_analyst_digest"
        ),
        "synthesis_proposal_refs": _synthesis_proposal_identity_refs(synthesis_refs),
        "validation_status": validation_status,
        "support_validation_refs": list(support_validation_refs or []),
        "challenge_refs": list(challenge_refs or []),
        "followup_need_refs": list(followup_need_refs or []),
    }
    seed_digest = _digest_json(seed_payload)
    artifact = {
        "schema_version": DPRIME_SYNTHESIS_VALIDATION_V0_SCHEMA_VERSION,
        "phase": DPRIME_SYNTHESIS_VALIDATION_V0_PHASE,
        "runtime_consumer": DPRIME_SYNTHESIS_VALIDATION_V0_RUNTIME_CONSUMER,
        "dprime_synthesis_validation_id": (
            _clean_text(dprime_synthesis_validation_id, limit=260)
            or f"dprime-synthesis-validation:v0:{seed_digest[:20]}"
        ),
        "dprime_synthesis_validation_digest": None,
        "parent_run_id": workbench["parent_run_id"],
        "parent_graph_ref": _compact_parent_graph_ref(workbench["parent_graph_ref"]),
        "cross_component_analyst_ref": _compact_workbench_ref(workbench),
        "input_workbench_status": workbench["analysis_status"],
        "synthesis_proposal_refs": synthesis_refs,
        "component_refs_under_validation": list(
            component_refs_under_validation or default_component_refs
        ),
        "dependency_edge_refs_under_validation": list(
            dependency_edge_refs_under_validation or default_dependency_refs
        ),
        "caveat_refs_under_validation": list(
            caveat_refs_under_validation or workbench["required_caveat_refs"]
        ),
        "nonclaim_refs_under_validation": list(
            nonclaim_refs_under_validation or workbench["nonclaim_refs"]
        ),
        "contradiction_refs_under_validation": list(
            contradiction_refs_under_validation or workbench["contradiction_refs"]
        ),
        "unresolved_dependency_refs_under_validation": list(
            unresolved_dependency_refs_under_validation
            or workbench["unresolved_dependency_refs"]
        ),
        "missing_component_refs_under_validation": list(
            missing_component_refs_under_validation
            or workbench["missing_component_proposal_refs"]
        ),
        "evidence_refs_to_revisit": list(
            evidence_refs_to_revisit or workbench["evidence_refs_to_revisit"]
        ),
        "source_refs_to_revisit": list(
            source_refs_to_revisit or workbench["source_refs_to_revisit"]
        ),
        "validation_status": _required_validation_status(validation_status),
        "support_validation_refs": list(support_validation_refs or []),
        "challenge_refs": list(challenge_refs or []),
        "missing_dependency_refs": list(missing_dependency_refs or []),
        "caveat_preservation_refs": list(caveat_preservation_refs or []),
        "overbreadth_challenge_refs": list(overbreadth_challenge_refs or []),
        "contradiction_challenge_refs": list(contradiction_challenge_refs or []),
        "followup_need_refs": list(followup_need_refs or []),
        "runkernel_consideration_refs": list(runkernel_consideration_refs or []),
        "closed_downstream_flags": dict(DPRIME_SYNTHESIS_CLOSED_DOWNSTREAM_FLAGS),
        "raw_private_retention_flags": dict(
            DPRIME_SYNTHESIS_RAW_PRIVATE_RETENTION_FALSE_FLAGS
        ),
        "nonclaims": _nonclaims(nonclaims),
        "parent_graph_mutated": False,
        "workbench_artifact_mutated": False,
        "answer_contract_mutated": False,
        **DPRIME_SYNTHESIS_CLOSED_DOWNSTREAM_FLAGS,
    }
    return validate_dprime_synthesis_validation_v0(artifact)


def validate_dprime_synthesis_validation_v0(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and normalize a synthesis D-prime validation artifact."""

    artifact = _safe_mapping(value)
    for key in _REQUIRED_TOP_LEVEL_FIELDS:
        if key not in artifact:
            raise DPrimeSynthesisValidationError(
                f"D-prime synthesis validation requires {key}"
            )
    _reject_forbidden_material(artifact, context="D-prime synthesis validation V0")
    _reject_synthesis_claim_selection(artifact)
    _reject_synthesis_proposal_creation(artifact)
    if artifact.get("schema_version") != DPRIME_SYNTHESIS_VALIDATION_V0_SCHEMA_VERSION:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation schema mismatch"
        )
    if artifact.get("phase") != DPRIME_SYNTHESIS_VALIDATION_V0_PHASE:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation phase mismatch"
        )
    validation_id = _required_text(
        artifact.get("dprime_synthesis_validation_id"),
        "dprime_synthesis_validation_id",
    )
    parent_run_id = _required_text(artifact.get("parent_run_id"), "parent_run_id")
    parent_graph_ref = _validate_parent_graph_ref(artifact.get("parent_graph_ref"))
    if parent_graph_ref.get("parent_run_id") != parent_run_id:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation parent graph run mismatch"
        )
    workbench_ref = _validate_workbench_ref(artifact.get("cross_component_analyst_ref"))
    if workbench_ref.get("parent_run_id") != parent_run_id:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation Workbench run mismatch"
        )
    input_workbench_status = _required_text(
        artifact.get("input_workbench_status"),
        "input_workbench_status",
    )
    if input_workbench_status != workbench_ref.get("analysis_status"):
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation Workbench status mismatch"
        )
    validation_status = _required_validation_status(
        artifact.get("validation_status")
    )
    node_index = _component_node_index(workbench_ref["component_node_refs"])
    edge_index = _dependency_edge_index(workbench_ref["dependency_edge_refs"])
    synthesis_refs = _validate_synthesis_proposal_refs(
        artifact.get("synthesis_proposal_refs"),
        node_index=node_index,
        workbench_ref=workbench_ref,
    )
    proposal_index = _synthesis_proposal_index(synthesis_refs)
    component_refs = _dedupe_component_refs(
        artifact.get("component_refs_under_validation"),
        node_index=node_index,
    )
    _require_component_refs_cover_synthesis(component_refs, synthesis_refs)
    dependency_refs = _dedupe_dependency_refs(
        artifact.get("dependency_edge_refs_under_validation"),
        edge_index=edge_index,
    )
    _require_dependency_refs_traceable(dependency_refs, edge_index=edge_index)
    caveat_refs = _safe_refs(artifact.get("caveat_refs_under_validation"))
    nonclaim_refs = _safe_refs(artifact.get("nonclaim_refs_under_validation"))
    contradiction_refs = _safe_refs(
        artifact.get("contradiction_refs_under_validation")
    )
    unresolved_dependency_refs = _safe_refs(
        artifact.get("unresolved_dependency_refs_under_validation")
    )
    missing_component_refs = _safe_refs(
        artifact.get("missing_component_refs_under_validation")
    )
    evidence_revisit_refs = _safe_refs(artifact.get("evidence_refs_to_revisit"))
    source_revisit_refs = _safe_refs(artifact.get("source_refs_to_revisit"))
    _require_preserved_workbench_refs(
        artifact,
        workbench_ref=workbench_ref,
        normalized_refs={
            "caveat_refs_under_validation": caveat_refs,
            "nonclaim_refs_under_validation": nonclaim_refs,
            "contradiction_refs_under_validation": contradiction_refs,
            "unresolved_dependency_refs_under_validation": unresolved_dependency_refs,
            "missing_component_refs_under_validation": missing_component_refs,
            "evidence_refs_to_revisit": evidence_revisit_refs,
            "source_refs_to_revisit": source_revisit_refs,
        },
    )
    output_refs = {
        field_name: _validate_output_refs(
            artifact.get(field_name),
            field_name=field_name,
            proposal_index=proposal_index,
        )
        for field_name in _OUTPUT_REF_FIELDS
    }
    _validate_status_semantics(
        validation_status,
        synthesis_refs=synthesis_refs,
        output_refs=output_refs,
        caveat_refs=caveat_refs,
        contradiction_refs=contradiction_refs,
        unresolved_dependency_refs=unresolved_dependency_refs,
        missing_component_refs=missing_component_refs,
    )
    closed_flags = _validate_closed_downstream_flags(artifact)
    raw_flags = _validate_raw_private_flags(artifact)
    normalized = {
        **_json_safe(artifact),
        "dprime_synthesis_validation_id": validation_id,
        "parent_run_id": parent_run_id,
        "parent_graph_ref": parent_graph_ref,
        "cross_component_analyst_ref": workbench_ref,
        "input_workbench_status": input_workbench_status,
        "synthesis_proposal_refs": synthesis_refs,
        "component_refs_under_validation": component_refs,
        "dependency_edge_refs_under_validation": dependency_refs,
        "caveat_refs_under_validation": caveat_refs,
        "nonclaim_refs_under_validation": nonclaim_refs,
        "contradiction_refs_under_validation": contradiction_refs,
        "unresolved_dependency_refs_under_validation": unresolved_dependency_refs,
        "missing_component_refs_under_validation": missing_component_refs,
        "evidence_refs_to_revisit": evidence_revisit_refs,
        "source_refs_to_revisit": source_revisit_refs,
        "validation_status": validation_status,
        **output_refs,
        "closed_downstream_flags": closed_flags,
        "raw_private_retention_flags": raw_flags,
        "nonclaims": _nonclaims(artifact.get("nonclaims")),
        **closed_flags,
    }
    declared = _clean_text(
        artifact.get("dprime_synthesis_validation_digest"),
        limit=128,
    )
    digest = _digest_json(_without_validation_digest(normalized))
    if declared and declared != digest:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation digest mismatch"
        )
    normalized["dprime_synthesis_validation_digest"] = digest
    _reject_forbidden_material(
        normalized,
        context="D-prime synthesis validation V0",
    )
    return normalized


def dprime_synthesis_validation_v0_ref(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a compact safe validation ref for future graph/admission phases."""

    if not _safe_mapping(value):
        return {}
    validation = validate_dprime_synthesis_validation_v0(value)
    return _without_empty(
        {
            "schema_version": validation.get("schema_version"),
            "phase": validation.get("phase"),
            "dprime_synthesis_validation_id": validation.get(
                "dprime_synthesis_validation_id"
            ),
            "dprime_synthesis_validation_digest": validation.get(
                "dprime_synthesis_validation_digest"
            ),
            "parent_run_id": validation.get("parent_run_id"),
            "parent_graph_ref": _safe_mapping(validation.get("parent_graph_ref")),
            "cross_component_analyst_ref": _safe_mapping(
                validation.get("cross_component_analyst_ref")
            ),
            "validation_status": validation.get("validation_status"),
            "synthesis_proposal_refs": _synthesis_proposal_identity_refs(
                _safe_sequence(validation.get("synthesis_proposal_refs"))
            ),
            "support_validation_ref_count": len(
                _safe_sequence(validation.get("support_validation_refs"))
            ),
            "challenge_ref_count": len(_safe_sequence(validation.get("challenge_refs"))),
            "followup_need_ref_count": len(
                _safe_sequence(validation.get("followup_need_refs"))
            ),
            "runkernel_consideration_ref_count": len(
                _safe_sequence(validation.get("runkernel_consideration_refs"))
            ),
            "runkernel_admission_created": False,
            "answer_contract_mutated": False,
            "retrieval_authorized": False,
            "product_correctness_claimed": False,
        }
    )


def _validate_workbench_input(value: Mapping[str, Any]) -> dict[str, Any]:
    artifact = _safe_mapping(value)
    if not artifact:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation requires Workbench input"
        )
    if artifact.get("schema_version") != CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation requires Cross-Component Analyst Workbench V0"
        )
    try:
        return validate_cross_component_analyst_workbench_v0(artifact)
    except Exception as exc:  # noqa: BLE001 - fail closed behind local error type.
        raise DPrimeSynthesisValidationError(
            f"Cross-Component Analyst Workbench input invalid: {exc}"
        ) from None


def _compact_parent_graph_ref(parent_graph_ref: Mapping[str, Any]) -> dict[str, Any]:
    ref = _safe_mapping(parent_graph_ref)
    return _without_empty(
        {
            "schema_version": ref.get("schema_version"),
            "phase": ref.get("phase"),
            "graph_id": ref.get("graph_id"),
            "graph_digest": ref.get("graph_digest"),
            "parent_run_id": ref.get("parent_run_id"),
            "graph_status": ref.get("graph_status"),
            "component_node_count": ref.get("component_node_count"),
            "closed_downstream_flags": _safe_mapping(
                ref.get("closed_downstream_flags")
            ),
            "raw_private_retention_flags": _safe_mapping(
                ref.get("raw_private_retention_flags")
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
            "evidence_refs_to_revisit": _safe_refs(
                workbench.get("evidence_refs_to_revisit")
            ),
            "source_refs_to_revisit": _safe_refs(
                workbench.get("source_refs_to_revisit")
            ),
            "cross_component_analyst_created_dprime_validation": False,
            "cross_component_analyst_created_runkernel_admission": False,
            "cross_component_analyst_admitted_support": False,
            "cross_component_analyst_mutated_answer_contract": False,
            "cross_component_analyst_mutated_parent_graph": False,
        }
    )


def _validate_parent_graph_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION:
        raise DPrimeSynthesisValidationError("parent_graph_ref schema mismatch")
    for key in ("graph_id", "graph_digest", "parent_run_id", "graph_status"):
        _required_text(ref.get(key), f"parent_graph_ref.{key}")
    _reject_forbidden_material(ref, context="parent_graph_ref")
    return _json_safe(ref)


def _validate_workbench_ref(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    if ref.get("schema_version") != CROSS_COMPONENT_ANALYST_WORKBENCH_V0_SCHEMA_VERSION:
        raise DPrimeSynthesisValidationError(
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
        raise DPrimeSynthesisValidationError(
            "cross_component_analyst_ref must remain proposal-only"
        )
    component_node_refs = _validate_component_node_refs(ref.get("component_node_refs"))
    dependency_edge_refs = _safe_refs(ref.get("dependency_edge_refs"))
    for edge in dependency_edge_refs:
        _validate_dependency_ref_shape(edge)
    normalized = {
        **_json_safe(ref),
        "component_node_refs": component_node_refs,
        "dependency_edge_refs": dependency_edge_refs,
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
        "evidence_refs_to_revisit": _safe_refs(ref.get("evidence_refs_to_revisit")),
        "source_refs_to_revisit": _safe_refs(ref.get("source_refs_to_revisit")),
    }
    _reject_forbidden_material(normalized, context="cross_component_analyst_ref")
    return normalized


def _validate_synthesis_proposal_refs(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]],
    workbench_ref: Mapping[str, Any],
) -> list[dict[str, Any]]:
    refs = _safe_refs(value)
    expected = _proposal_identity_set(workbench_ref.get("synthesis_proposal_refs"))
    expected_claims = _proposal_claim_identity_map(
        workbench_ref.get("synthesis_proposal_refs")
    )
    actual = _proposal_identity_set(refs)
    if expected and actual != expected:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation cannot create or drop synthesis proposal refs"
        )
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        proposal_id, proposal_digest = _required_synthesis_identity(ref)
        identity = (proposal_id, proposal_digest)
        if identity in seen:
            continue
        seen.add(identity)
        if ref.get("proposal_only") is not True:
            raise DPrimeSynthesisValidationError(
                "synthesis proposal refs must remain proposal-only"
            )
        component_refs = _dedupe_component_refs(
            _component_refs_from_synthesis_ref(ref),
            node_index=node_index,
        )
        if len({(item["node_id"], item["component_id"]) for item in component_refs}) < 2:
            raise DPrimeSynthesisValidationError(
                "synthesis proposal refs must reference at least two known components"
            )
        expected_claim = expected_claims.get(identity, {})
        actual_claim = _synthesis_claim_identity_ref(ref.get("synthesis_claim_ref"))
        if expected_claim and not actual_claim:
            raise DPrimeSynthesisValidationError(
                "D-prime synthesis validation cannot remove synthesis_claim_ref"
            )
        if not expected_claim and actual_claim:
            raise DPrimeSynthesisValidationError(
                "D-prime synthesis validation cannot add synthesis_claim_ref"
            )
        if expected_claim != actual_claim:
            raise DPrimeSynthesisValidationError(
                "D-prime synthesis validation cannot change synthesis_claim_ref"
            )
        normalized_ref = {
            **_json_safe(ref),
            "component_node_refs": component_refs,
            "proposal_only": True,
        }
        if expected_claim:
            normalized_ref["synthesis_claim_ref"] = dict(expected_claim)
        normalized.append(normalized_ref)
    return normalized


def _validate_component_node_refs(value: Any) -> list[dict[str, Any]]:
    refs = _safe_refs(value)
    if not refs:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation requires component node refs"
        )
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        if ref.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
            raise DPrimeSynthesisValidationError(
                "component refs must be typed ComponentWorkNode refs"
            )
        node_id = _required_text(ref.get("node_id"), "component node_id")
        component_id = _required_text(ref.get("component_id"), "component_id")
        key = (node_id, component_id)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                **_json_safe(ref),
                "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
                "node_id": node_id,
                "component_id": component_id,
            }
        )
    return normalized


def _dedupe_component_refs(
    value: Any,
    *,
    node_index: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = _safe_sequence(value)
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in refs:
        ref = _safe_mapping(item)
        if not ref:
            continue
        _reject_forbidden_material(ref, context="component ref")
        if ref.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
            raise DPrimeSynthesisValidationError(
                "component refs must be typed ComponentWorkNode refs"
            )
        node_id = _required_text(ref.get("node_id"), "component node_id")
        component_id = _required_text(ref.get("component_id"), "component_id")
        known = _safe_mapping(node_index.get(node_id))
        if not known or known.get("component_id") != component_id:
            raise DPrimeSynthesisValidationError(
                "component refs must match known node_id/component_id pairs"
            )
        key = (node_id, component_id)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
                "node_id": node_id,
                "component_id": component_id,
            }
        )
    return normalized


def _dedupe_dependency_refs(
    value: Any,
    *,
    edge_index: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs = _safe_sequence(value)
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in refs:
        ref = _safe_mapping(item)
        if not ref:
            continue
        _reject_forbidden_material(ref, context="dependency ref")
        _validate_dependency_ref_shape(ref)
        edge_id = _required_text(ref.get("edge_id"), "dependency edge_id")
        known = _safe_mapping(edge_index.get(edge_id))
        if not known:
            raise DPrimeSynthesisValidationError(
                "dependency refs must be known and traceable"
            )
        edge_digest = _clean_text(ref.get("edge_digest"), limit=128)
        known_digest = _clean_text(known.get("edge_digest"), limit=128)
        if edge_digest and known_digest and edge_digest != known_digest:
            raise DPrimeSynthesisValidationError("dependency edge digest mismatch")
        if edge_id in seen:
            continue
        seen.add(edge_id)
        normalized.append(
            _without_empty(
                {
                    "schema_version": COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION,
                    "edge_id": edge_id,
                    "edge_digest": edge_digest or known_digest,
                    "from_component_node_ref": _safe_mapping(
                        known.get("from_component_node_ref")
                    )
                    or _safe_mapping(ref.get("from_component_node_ref")),
                    "to_component_node_ref": _safe_mapping(
                        known.get("to_component_node_ref")
                    )
                    or _safe_mapping(ref.get("to_component_node_ref")),
                    "dependency_kind": known.get("dependency_kind")
                    or ref.get("dependency_kind"),
                    "blocking": (
                        known.get("blocking")
                        if "blocking" in known
                        else ref.get("blocking")
                    )
                    is True,
                }
            )
        )
    return normalized


def _validate_dependency_ref_shape(ref: Mapping[str, Any]) -> None:
    if ref.get("schema_version") != COMPONENT_WORK_GRAPH_V0_SCHEMA_VERSION:
        raise DPrimeSynthesisValidationError(
            "dependency refs must be typed ComponentWorkGraph edge refs"
        )
    _required_text(ref.get("edge_id"), "dependency edge_id")


def _validate_output_refs(
    value: Any,
    *,
    field_name: str,
    proposal_index: Mapping[tuple[str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if not ref:
            continue
        _reject_forbidden_material(ref, context=field_name)
        proposal_ref = _require_known_synthesis_binding(
            ref,
            field_name=field_name,
            proposal_index=proposal_index,
        )
        normalized = {
            **_json_safe(ref),
            "synthesis_proposal_id": proposal_ref["synthesis_proposal_id"],
            "synthesis_proposal_digest": proposal_ref["synthesis_proposal_digest"],
            "dprime_synthesis_validation_output_only": True,
            "runkernel_admission_created": False,
            "answer_contract_mutated": False,
            "retrieval_authorized": False,
            "product_correctness_claimed": False,
        }
        if field_name == "followup_need_refs":
            _reject_followup_authorization_claims(normalized)
        if field_name == "runkernel_consideration_refs":
            _reject_runkernel_admission_claims(normalized)
        refs.append(normalized)
    return refs


def _require_known_synthesis_binding(
    ref: Mapping[str, Any],
    *,
    field_name: str,
    proposal_index: Mapping[tuple[str, str], Mapping[str, Any]],
) -> Mapping[str, Any]:
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
        raise DPrimeSynthesisValidationError(
            f"{field_name} must reference an input synthesis proposal by id/digest"
        )
    proposal = proposal_index.get((proposal_id, proposal_digest))
    if not proposal:
        raise DPrimeSynthesisValidationError(
            f"{field_name} references unknown synthesis proposal id/digest"
        )
    return proposal


def _validate_status_semantics(
    validation_status: str,
    *,
    synthesis_refs: Sequence[Mapping[str, Any]],
    output_refs: Mapping[str, Sequence[Mapping[str, Any]]],
    caveat_refs: Sequence[Mapping[str, Any]],
    contradiction_refs: Sequence[Mapping[str, Any]],
    unresolved_dependency_refs: Sequence[Mapping[str, Any]],
    missing_component_refs: Sequence[Mapping[str, Any]],
) -> None:
    if validation_status in SUPPORT_LIKE_VALIDATION_STATUSES:
        if not synthesis_refs:
            raise DPrimeSynthesisValidationError(
                "support-like synthesis validation requires synthesis proposal refs"
            )
        if not output_refs["support_validation_refs"]:
            raise DPrimeSynthesisValidationError(
                "support-like synthesis validation requires support validation refs"
            )
        if contradiction_refs:
            raise DPrimeSynthesisValidationError(
                "support-like synthesis validation cannot ignore contradiction refs"
            )
        if unresolved_dependency_refs:
            raise DPrimeSynthesisValidationError(
                "support-like synthesis validation cannot ignore unresolved dependency refs"
            )
        if missing_component_refs:
            raise DPrimeSynthesisValidationError(
                "support-like synthesis validation cannot ignore missing-component refs"
            )
    if validation_status == VALIDATION_STATUS_BLOCKED_MISSING_DEPENDENCY and not (
        output_refs["missing_dependency_refs"] or unresolved_dependency_refs
    ):
        raise DPrimeSynthesisValidationError(
            "blocked_missing_dependency requires missing dependency refs"
        )
    if validation_status == VALIDATION_STATUS_FOLLOWUP_NEEDED and not (
        output_refs["followup_need_refs"]
    ):
        raise DPrimeSynthesisValidationError(
            "followup_needed requires follow-up need refs"
        )
    _require_caveats_preserved_or_challenged(
        caveat_refs,
        output_refs=output_refs,
    )


def _require_caveats_preserved_or_challenged(
    caveat_refs: Sequence[Mapping[str, Any]],
    *,
    output_refs: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    required = {_ref_identity(item) for item in caveat_refs}
    if not required:
        return
    preserved_or_challenged = {
        _ref_identity(item)
        for field in (
            "caveat_preservation_refs",
            "challenge_refs",
            "overbreadth_challenge_refs",
        )
        for item in output_refs[field]
        if _ref_identity(item) != _empty_identity()
    }
    if not required <= preserved_or_challenged:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation cannot drop required caveat refs"
        )


def _require_preserved_workbench_refs(
    artifact: Mapping[str, Any],
    *,
    workbench_ref: Mapping[str, Any],
    normalized_refs: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    del artifact
    for artifact_field, workbench_field in _WORKBENCH_REF_LIST_FIELDS:
        expected = {_ref_identity(item) for item in workbench_ref.get(workbench_field, [])}
        actual = {_ref_identity(item) for item in normalized_refs[artifact_field]}
        if not expected <= actual:
            raise DPrimeSynthesisValidationError(
                f"D-prime synthesis validation cannot erase {workbench_field}"
            )


def _require_component_refs_cover_synthesis(
    component_refs: Sequence[Mapping[str, Any]],
    synthesis_refs: Sequence[Mapping[str, Any]],
) -> None:
    actual = {
        (item.get("node_id"), item.get("component_id"))
        for item in component_refs
    }
    required = {
        (item.get("node_id"), item.get("component_id"))
        for ref in synthesis_refs
        for item in _safe_sequence(ref.get("component_node_refs"))
    }
    if not required <= actual:
        raise DPrimeSynthesisValidationError(
            "component refs under validation must cover synthesis proposal refs"
        )


def _require_dependency_refs_traceable(
    dependency_refs: Sequence[Mapping[str, Any]],
    *,
    edge_index: Mapping[str, Mapping[str, Any]],
) -> None:
    for ref in dependency_refs:
        edge_id = _required_text(ref.get("edge_id"), "dependency edge_id")
        if edge_id not in edge_index:
            raise DPrimeSynthesisValidationError(
                "dependency refs under validation must be known and traceable"
            )


def _validate_closed_downstream_flags(artifact: Mapping[str, Any]) -> dict[str, bool]:
    closed = _safe_mapping(artifact.get("closed_downstream_flags"))
    if not closed:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation missing closed_downstream_flags"
        )
    normalized: dict[str, bool] = {}
    for key in DPRIME_SYNTHESIS_CLOSED_DOWNSTREAM_FLAGS:
        if closed.get(key) is not False:
            raise DPrimeSynthesisValidationError(
                f"D-prime synthesis validation closed flag must remain false: {key}"
            )
        if artifact.get(key) is not False:
            raise DPrimeSynthesisValidationError(
                f"D-prime synthesis validation top-level flag must remain false: {key}"
            )
        normalized[key] = False
    for key in ("parent_graph_mutated", "workbench_artifact_mutated", "answer_contract_mutated"):
        if key in artifact and artifact.get(key) is not False:
            raise DPrimeSynthesisValidationError(
                f"D-prime synthesis validation must keep {key}=false"
            )
    return normalized


def _validate_raw_private_flags(artifact: Mapping[str, Any]) -> dict[str, bool]:
    flags = _safe_mapping(artifact.get("raw_private_retention_flags"))
    if not flags:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation missing raw_private_retention_flags"
        )
    normalized: dict[str, bool] = {}
    for key in DPRIME_SYNTHESIS_RAW_PRIVATE_RETENTION_FALSE_FLAGS:
        if flags.get(key) is not False:
            raise DPrimeSynthesisValidationError(
                f"D-prime synthesis validation raw/private flag must remain false: {key}"
            )
        normalized[key] = False
    return normalized


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & _FORBIDDEN_NORMALIZED_KEYS)
    if forbidden:
        raise DPrimeSynthesisValidationError(
            f"{context} includes forbidden raw/private material: "
            + ", ".join(forbidden)
        )
    invalid_false_flags = sorted(_invalid_false_flags(value))
    if invalid_false_flags:
        raise DPrimeSynthesisValidationError(
            f"{context} raw/private or closed flags must be explicitly false: "
            + ", ".join(invalid_false_flags)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise DPrimeSynthesisValidationError(
            f"{context} attempts forbidden authority upgrade: "
            + ", ".join(dangerous)
        )
    dangerous_statuses = sorted(_dangerous_status_claims(value))
    if dangerous_statuses:
        raise DPrimeSynthesisValidationError(
            f"{context} carries forbidden status claims: "
            + ", ".join(dangerous_statuses)
        )


def _reject_synthesis_claim_selection(value: Any) -> None:
    for path, item in _walk_mappings_with_path(value):
        in_input_proposal = "synthesis_proposal_refs" in path
        for key in item:
            normalized = _normalize_key(key)
            if normalized == "synthesis_claim_ref" and not in_input_proposal:
                raise DPrimeSynthesisValidationError(
                    "D-prime synthesis validation cannot introduce a synthesis_claim_ref"
                )
            if normalized in _SYNTHESIS_CLAIM_SELECTION_KEYS:
                raise DPrimeSynthesisValidationError(
                    "D-prime synthesis validation cannot choose a different synthesis claim"
                )


def _reject_synthesis_proposal_creation(value: Any) -> None:
    keys = _collect_keys(value)
    invalid = sorted(keys & _SYNTHESIS_PROPOSAL_CREATION_KEYS)
    if invalid:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation cannot create synthesis proposal refs: "
            + ", ".join(invalid)
        )


def _reject_followup_authorization_claims(value: Mapping[str, Any]) -> None:
    for item in _walk_mappings(value):
        if item.get("followup_authorized") is True:
            raise DPrimeSynthesisValidationError(
                "follow-up need refs must not authorize retrieval"
            )
        for key, raw in item.items():
            normalized_key = _normalize_key(key)
            normalized_value = _normalize_key(raw)
            if normalized_key in {
                "authorization_status",
                "retrieval_authorization_status",
                "runkernel_authorization_status",
                "search_authorization_status",
            } and normalized_value in {"authorized", "approved", "admitted"}:
                raise DPrimeSynthesisValidationError(
                    "follow-up need refs must not authorize retrieval"
                )


def _reject_runkernel_admission_claims(value: Mapping[str, Any]) -> None:
    for item in _walk_mappings(value):
        if item.get("runkernel_admitted") is True:
            raise DPrimeSynthesisValidationError(
                "RunKernel consideration refs must not claim admission"
            )
        for key, raw in item.items():
            normalized_key = _normalize_key(key)
            normalized_value = _normalize_key(raw)
            if normalized_key in {
                "admission_status",
                "runkernel_admission_status",
                "status",
            } and normalized_value == "admitted":
                raise DPrimeSynthesisValidationError(
                    "RunKernel consideration refs must not claim admission"
                )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
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
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _ALLOWED_FALSE_KEYS and item not in (False, True):
                found.add(normalized)
            if normalized in _ALLOWED_FALSE_KEYS and item is True:
                continue
            if (
                (
                    normalized.endswith("_retained")
                    or normalized.endswith("_called")
                    or normalized.endswith("_dispatched")
                    or normalized.endswith("_executed")
                )
                and item is not False
            ):
                found.add(normalized)
            found.update(_invalid_false_flags(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            found.update(_invalid_false_flags(item))
    return found


def _dangerous_status_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            status_value = _normalize_key(item)
            if normalized in _STATUS_KEYS and status_value in _DANGEROUS_STATUS_VALUES:
                found.add(f"{normalized}={status_value}")
            found.update(_dangerous_status_claims(item))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            found.update(_dangerous_status_claims(item))
    return found


def _component_refs_from_synthesis_refs(
    refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        item
        for ref in refs
        for item in _component_refs_from_synthesis_ref(ref)
    ]


def _component_refs_from_synthesis_ref(ref: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for key in (
        "component_node_refs",
        "component_refs",
        "component_refs_supporting_synthesis",
    ):
        refs.extend(_safe_refs(ref.get(key)))
    return refs


def _dependency_refs_from_synthesis_refs(
    refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ref in refs:
        for key in ("dependency_edge_refs", "dependency_refs"):
            out.extend(_safe_refs(ref.get(key)))
    return out


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


def _synthesis_proposal_index(
    refs: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        _required_synthesis_identity(ref): {
            "synthesis_proposal_id": _required_synthesis_identity(ref)[0],
            "synthesis_proposal_digest": _required_synthesis_identity(ref)[1],
        }
        for ref in refs
    }


def _required_synthesis_identity(ref: Mapping[str, Any]) -> tuple[str, str]:
    proposal_id = _required_text(
        ref.get("synthesis_proposal_id"),
        "synthesis_proposal_id",
    )
    proposal_digest = _required_text(
        ref.get("synthesis_proposal_digest"),
        "synthesis_proposal_digest",
        limit=128,
    )
    return proposal_id, proposal_digest


def _proposal_identity_set(value: Any) -> set[tuple[str, str]]:
    identities: set[tuple[str, str]] = set()
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        proposal_id = _clean_text(ref.get("synthesis_proposal_id"), limit=320)
        proposal_digest = _clean_text(
            ref.get("synthesis_proposal_digest"),
            limit=128,
        )
        if proposal_id and proposal_digest:
            identities.add((proposal_id, proposal_digest))
    return identities


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
        raise DPrimeSynthesisValidationError(
            "synthesis_claim_ref requires claim id and digest"
        )
    return {
        "claim_id": claim_id,
        "claim_digest": claim_digest,
    }


def _component_node_index(
    refs: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        str(ref["node_id"]): dict(ref)
        for ref in refs
        if _safe_mapping(ref).get("node_id")
    }


def _dependency_edge_index(
    refs: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        str(ref["edge_id"]): dict(ref)
        for ref in refs
        if _safe_mapping(ref).get("edge_id")
    }


def _ref_identity(ref: Mapping[str, Any]) -> tuple[str, str]:
    safe = _safe_mapping(ref)
    if not safe:
        return _empty_identity()
    id_value = ""
    digest_value = ""
    for key, value in sorted(safe.items()):
        normalized = _normalize_key(key)
        if not id_value and (
            normalized == "ref_id"
            or normalized.endswith("_id")
            or normalized in {"id", "edge_id", "node_id"}
        ):
            id_value = _clean_text(value, limit=320) or ""
        if not digest_value and (
            normalized == "ref_digest"
            or normalized.endswith("_digest")
            or normalized in {"digest", "edge_digest"}
        ):
            digest_value = _clean_text(value, limit=128) or ""
    if not id_value and not digest_value:
        digest_value = _digest_json(safe)
    return id_value, digest_value


def _empty_identity() -> tuple[str, str]:
    return "", ""


def _safe_refs(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(value):
        ref = _safe_mapping(item)
        if ref:
            _reject_forbidden_material(ref, context="nested ref")
            refs.append(_json_safe(ref))
    return refs


def _required_validation_status(value: Any) -> str:
    status = _clean_text(value, limit=120)
    if status not in ALLOWED_VALIDATION_STATUSES:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation status invalid"
        )
    return status


def _required_text(value: Any, key: str, *, limit: int = 900) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        raise DPrimeSynthesisValidationError(
            f"D-prime synthesis validation requires {key}"
        )
    return text


def _nonclaims(value: Any) -> list[str]:
    claims = list(
        _text_tuple(
            value if value is not None else DPRIME_SYNTHESIS_NONCLAIMS,
            limit=700,
        )
    )
    if not claims:
        raise DPrimeSynthesisValidationError(
            "D-prime synthesis validation requires nonclaims"
        )
    return claims


def _walk_mappings(value: Any) -> list[dict[str, Any]]:
    return [item for _path, item in _walk_mappings_with_path(value)]


def _walk_mappings_with_path(
    value: Any,
    *,
    path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], dict[str, Any]]]:
    out: list[tuple[tuple[str, ...], dict[str, Any]]] = []
    if isinstance(value, Mapping):
        safe = dict(value)
        out.append((path, safe))
        for key, item in safe.items():
            out.extend(
                _walk_mappings_with_path(
                    item,
                    path=(*path, _normalize_key(key)),
                )
            )
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for item in value:
            out.extend(_walk_mappings_with_path(item, path=path))
    return out


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _safe_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _text_tuple(value: Any, *, limit: int) -> tuple[str, ...]:
    if isinstance(value, str):
        text = _clean_text(value, limit=limit)
        return (text,) if text else ()
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {}, ())
    }


def _without_validation_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key != "dprime_synthesis_validation_digest"
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ALLOWED_VALIDATION_STATUSES",
    "DPRIME_SYNTHESIS_CLOSED_DOWNSTREAM_FLAGS",
    "DPRIME_SYNTHESIS_RAW_PRIVATE_RETENTION_FALSE_FLAGS",
    "DPRIME_SYNTHESIS_VALIDATION_V0_PHASE",
    "DPRIME_SYNTHESIS_VALIDATION_V0_RUNTIME_CONSUMER",
    "DPRIME_SYNTHESIS_VALIDATION_V0_SCHEMA_VERSION",
    "DPrimeSynthesisValidationError",
    "SUPPORT_LIKE_VALIDATION_STATUSES",
    "VALIDATION_STATUS_BLOCKED_CONTRADICTION",
    "VALIDATION_STATUS_BLOCKED_MISSING_COMPONENT",
    "VALIDATION_STATUS_BLOCKED_MISSING_DEPENDENCY",
    "VALIDATION_STATUS_CHALLENGED",
    "VALIDATION_STATUS_DRAFT",
    "VALIDATION_STATUS_FOLLOWUP_NEEDED",
    "VALIDATION_STATUS_SUPPORTED",
    "VALIDATION_STATUS_SUPPORTED_WITH_CAVEATS",
    "VALIDATION_STATUS_UNSUPPORTED",
    "dprime_synthesis_validation_v0_from_workbench",
    "dprime_synthesis_validation_v0_ref",
    "validate_dprime_synthesis_validation_v0",
]
