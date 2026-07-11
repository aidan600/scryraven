"""ComponentWorkNode V0 projection for the generic single-relation lane.

The node is a typed review contract over existing product-path refs. It does not
plan components, schedule graph work, create budget leases, admit support,
satisfy source obligations, render citations, create FAP/Author output, or claim
product correctness.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

COMPONENT_WORK_NODE_V0_SCHEMA_VERSION = "component_work_node_v0"
COMPONENT_WORK_NODE_V0_PHASE = "COMPONENTWORKNODE-SINGLE-RELATION-LIFT-01"
COMPONENT_WORK_NODE_V0_RUNTIME_CONSUMER = (
    "proplex.mvp_single_relation_live_dogfood_run"
)
COMPONENT_WORK_NODE_V1_SCHEMA_VERSION = "component_work_node_v1"
COMPONENT_WORK_NODE_V1_PHASE = (
    "AG-MULTICOMPONENT-ORDINARY-END-TO-END-SYNTHESIS-01"
)
COMPONENT_WORK_NODE_V1_RUNTIME_CONSUMER = (
    "ordinary ComponentWorkGraph V1 synthesis runtime"
)

COMPONENT_WORK_NODE_STATUS_CONSUMED = "consumed"
COMPONENT_WORK_NODE_STATUS_BLOCKED = "blocked"
COMPONENT_WORK_NODE_STATUS_NOT_REACHED = "not_reached"

RAW_PRIVATE_RETENTION_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_source_content_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}

COMPONENT_WORK_NODE_CLOSED_DOWNSTREAM_FLAGS = {
    "component_work_node_created_source_display": False,
    "component_work_node_created_fap": False,
    "component_work_node_created_author": False,
    "component_work_node_rendered_citations": False,
    "component_work_node_claimed_product_correctness": False,
    "component_work_node_created_final_aggregation": False,
    "component_work_node_created_component_graph": False,
    "component_work_node_created_scheduler": False,
    "component_work_node_created_budget_lease": False,
}

COMPONENT_WORK_NODE_NEGATIVE_CONTROL_FLAGS = {
    "single_component_only": True,
    "one_source_obligation_lane_only": True,
    "multi_component_planning_opened": False,
    "component_work_graph_scheduling_opened": False,
    "parallel_component_execution_opened": False,
    "budget_lease_created": False,
    "final_analyst_aggregation_created": False,
    "fap_created_by_node": False,
    "author_created_by_node": False,
    "source_display_created_by_node": False,
    "rendered_citations_created_by_node": False,
    "product_correctness_claimed": False,
    "candidate_fetch_read_refs_treated_as_semantic_support": False,
    "component_coverage_treated_as_source_obligation_satisfaction": False,
}

_FORBIDDEN_NORMALIZED_KEYS = {
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
    "model_response",
    "page_content",
    "page_text",
    "password",
    "private_log",
    "prompt",
    "provider_payload",
    "raw_html",
    "raw_model_response",
    "raw_page",
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
    "unbounded_text",
}

_DANGEROUS_TRUE_KEYS = {
    "author_created_by_node",
    "budget_lease_created",
    "candidate_fetch_read_refs_treated_as_semantic_support",
    "citation_eligible",
    "component_coverage_treated_as_source_obligation_satisfaction",
    "component_work_graph_scheduling_opened",
    "component_work_node_claimed_product_correctness",
    "component_work_node_created_author",
    "component_work_node_created_budget_lease",
    "component_work_node_created_component_graph",
    "component_work_node_created_fap",
    "component_work_node_created_final_aggregation",
    "component_work_node_created_scheduler",
    "component_work_node_created_source_display",
    "component_work_node_rendered_citations",
    "fap_created_by_node",
    "final_analyst_aggregation_created",
    "multi_component_planning_opened",
    "parallel_component_execution_opened",
    "product_correctness_claimed",
    "rendered_citations_created_by_node",
    "source_display_created_by_node",
    "source_obligation_satisfaction_claimed",
}


class ComponentWorkNodeError(ValueError):
    """Raised when ComponentWorkNode V0 would lose boundaries or lineage."""


def component_work_node_v0_refs_from_product_packet(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Build validated V0 input/output refs from an existing product packet."""

    safe = _safe_mapping(packet)
    input_ref = _build_input_ref(safe)
    output_ref = _build_output_ref(safe, input_ref=input_ref)
    refs = {
        "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
        "phase": COMPONENT_WORK_NODE_V0_PHASE,
        "runtime_consumer": COMPONENT_WORK_NODE_V0_RUNTIME_CONSUMER,
        "component_work_node_v0_input_ref": input_ref,
        "component_work_node_v0_output_ref": output_ref,
        "component_work_node_v0_status": output_ref["node_status"],
        "single_component_only": True,
        "component_work_graph_scheduling_opened": False,
        "product_correctness_claimed": False,
    }
    refs["component_work_node_v0_digest"] = _digest_json(refs)
    return validate_component_work_node_v0_refs(refs)


def validate_component_work_node_v0_refs(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the combined ComponentWorkNode V0 projection refs."""

    refs = _safe_mapping(value)
    if refs.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
        raise ComponentWorkNodeError("ComponentWorkNode refs schema mismatch")
    if refs.get("phase") != COMPONENT_WORK_NODE_V0_PHASE:
        raise ComponentWorkNodeError("ComponentWorkNode refs phase mismatch")
    input_ref = validate_component_work_node_v0_input_ref(
        _safe_mapping(refs.get("component_work_node_v0_input_ref"))
    )
    output_ref = validate_component_work_node_v0_output_ref(
        _safe_mapping(refs.get("component_work_node_v0_output_ref"))
    )
    if output_ref.get("node_id") != input_ref.get("node_id"):
        raise ComponentWorkNodeError("ComponentWorkNode input/output node id mismatch")
    if output_ref.get("component_id") != input_ref.get("component_id"):
        raise ComponentWorkNodeError("ComponentWorkNode component id mismatch")
    if refs.get("component_work_node_v0_status") != output_ref.get("node_status"):
        raise ComponentWorkNodeError("ComponentWorkNode status alias mismatch")
    if refs.get("single_component_only") is not True:
        raise ComponentWorkNodeError("ComponentWorkNode must remain single component")
    _require_false(refs, ("component_work_graph_scheduling_opened",))
    _require_false(refs, ("product_correctness_claimed",))
    _reject_forbidden_material(refs, context="ComponentWorkNode V0 refs")
    normalized = _json_safe(
        {
            **refs,
            "component_work_node_v0_input_ref": input_ref,
            "component_work_node_v0_output_ref": output_ref,
        }
    )
    digest_payload = dict(normalized)
    declared = digest_payload.pop("component_work_node_v0_digest", None)
    digest = _digest_json(digest_payload)
    if declared and declared != digest:
        raise ComponentWorkNodeError("ComponentWorkNode refs digest mismatch")
    normalized["component_work_node_v0_digest"] = digest
    return normalized


def validate_component_work_node_v0_input_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one-component node input/ref shape."""

    ref = _safe_mapping(value)
    if ref.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
        raise ComponentWorkNodeError("ComponentWorkNode input schema mismatch")
    if ref.get("node_kind") != "component_work_node_v0_input":
        raise ComponentWorkNodeError("ComponentWorkNode input kind mismatch")
    for key in (
        "node_id",
        "parent_run_id",
        "component_id",
        "component_text",
        "supported_query_class",
        "source_obligation_id",
        "source_obligation_text",
        "requested_answer_type",
        "expected_value_shape",
        "search_requirement_id",
        "search_requirement_text",
    ):
        if not _clean_text(ref.get(key), limit=800):
            raise ComponentWorkNodeError(f"ComponentWorkNode input requires {key}")
    component_ids = _text_tuple(ref.get("component_ids"), limit=320)
    source_lanes = _text_tuple(ref.get("source_obligation_lane_ids"), limit=320)
    if len(component_ids) != 1 or component_ids[0] != ref.get("component_id"):
        raise ComponentWorkNodeError(
            "ComponentWorkNode V0 cannot contain multiple component ids"
        )
    if len(source_lanes) != 1 or source_lanes[0] != ref.get("source_obligation_id"):
        raise ComponentWorkNodeError(
            "ComponentWorkNode V0 cannot merge multiple source-obligation lanes"
        )
    if not _safe_mapping(ref.get("relation_plan_ref")):
        raise ComponentWorkNodeError("ComponentWorkNode input missing relation plan ref")
    if not _safe_mapping(ref.get("component_answer_type_binding_ref")):
        raise ComponentWorkNodeError(
            "ComponentWorkNode input missing answer-type binding ref"
        )
    if not _clean_text(
        ref.get("source_authority_posture_requirement_ref"),
        limit=320,
    ):
        raise ComponentWorkNodeError(
            "ComponentWorkNode input missing source-authority requirement ref"
        )
    _validate_boundary_flags(ref)
    _reject_forbidden_material(ref, context="ComponentWorkNode V0 input")
    return _json_safe(ref)


def validate_component_work_node_v0_output_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one-component node output/ref shape."""

    ref = _safe_mapping(value)
    if ref.get("schema_version") != COMPONENT_WORK_NODE_V0_SCHEMA_VERSION:
        raise ComponentWorkNodeError("ComponentWorkNode output schema mismatch")
    if ref.get("node_kind") != "component_work_node_v0_output":
        raise ComponentWorkNodeError("ComponentWorkNode output kind mismatch")
    if ref.get("node_status") not in {
        COMPONENT_WORK_NODE_STATUS_CONSUMED,
        COMPONENT_WORK_NODE_STATUS_BLOCKED,
        COMPONENT_WORK_NODE_STATUS_NOT_REACHED,
    }:
        raise ComponentWorkNodeError("ComponentWorkNode output status invalid")
    component_ids = _text_tuple(ref.get("component_ids"), limit=320)
    source_lanes = _text_tuple(ref.get("source_obligation_lane_ids"), limit=320)
    if len(component_ids) != 1 or component_ids[0] != ref.get("component_id"):
        raise ComponentWorkNodeError(
            "ComponentWorkNode output cannot contain multiple component ids"
        )
    if len(source_lanes) != 1 or source_lanes[0] != ref.get("source_obligation_id"):
        raise ComponentWorkNodeError(
            "ComponentWorkNode output cannot merge multiple source-obligation lanes"
        )
    _validate_boundary_flags(ref)
    closed = _safe_mapping(ref.get("closed_downstream_flags"))
    if closed != COMPONENT_WORK_NODE_CLOSED_DOWNSTREAM_FLAGS:
        raise ComponentWorkNodeError("ComponentWorkNode closed downstream flags invalid")
    for key, expected in COMPONENT_WORK_NODE_CLOSED_DOWNSTREAM_FLAGS.items():
        if ref.get(key) is not expected:
            raise ComponentWorkNodeError(f"ComponentWorkNode output {key} invalid")
    if ref.get("candidate_fetch_read_refs_treated_as_semantic_support") is not False:
        raise ComponentWorkNodeError(
            "ComponentWorkNode output cannot treat candidate/fetch-read refs as support"
        )
    if (
        ref.get("component_coverage_treated_as_source_obligation_satisfaction")
        is not False
    ):
        raise ComponentWorkNodeError(
            "ComponentWorkNode output cannot treat ComponentCoverage as "
            "source-obligation satisfaction"
        )
    if (
        ref.get("source_obligation_authority_consumed") is not True
        and ref.get("source_obligation_satisfaction_claimed") is not False
    ):
        raise ComponentWorkNodeError(
            "source-obligation satisfaction requires existing authority refs"
        )
    _validate_multi_source_shape(ref)
    _reject_forbidden_material(ref, context="ComponentWorkNode V0 output")
    return _json_safe(ref)


def _build_input_ref(packet: Mapping[str, Any]) -> dict[str, Any]:
    component_id = _required_text(packet.get("component_id"), "component_id")
    source_obligation_id = _required_text(
        packet.get("source_obligation_id"),
        "source_obligation_id",
    )
    run_id = _required_text(packet.get("run_id"), "run_id")
    relation_plan_id = _required_text(packet.get("relation_plan_id"), "relation_plan_id")
    digest = _digest_json(
        {
            "phase": COMPONENT_WORK_NODE_V0_PHASE,
            "run_id": run_id,
            "relation_plan_id": relation_plan_id,
            "component_id": component_id,
            "source_obligation_id": source_obligation_id,
        }
    )
    ref = {
        "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
        "phase": COMPONENT_WORK_NODE_V0_PHASE,
        "node_kind": "component_work_node_v0_input",
        "node_id": f"component-work-node:v0:{digest[:20]}",
        "parent_run_id": run_id,
        "parent_run_ref": {
            "run_id": run_id,
            "packet_id": packet.get("packet_id"),
            "ordinary_entrypoint": packet.get("ordinary_entrypoint"),
            "command_flag": packet.get("command_flag"),
        },
        "component_id": component_id,
        "component_ids": [component_id],
        "component_text": _required_text(packet.get("component_text"), "component_text"),
        "component_label": _clean_text(packet.get("component_text"), limit=260),
        "supported_query_class": _required_text(
            packet.get("supported_query_class_id")
            or packet.get("supported_query_class"),
            "supported_query_class",
        ),
        "source_obligation_id": source_obligation_id,
        "source_obligation_lane_ids": [source_obligation_id],
        "source_obligation_text": _required_text(
            packet.get("source_obligation_text"),
            "source_obligation_text",
        ),
        "requested_answer_type": _required_text(
            packet.get("requested_answer_type"),
            "requested_answer_type",
        ),
        "expected_value_shape": _required_text(
            packet.get("expected_value_shape"),
            "expected_value_shape",
        ),
        "search_requirement_id": _required_text(
            packet.get("search_requirement_id"),
            "search_requirement_id",
        ),
        "search_requirement_text": _required_text(
            packet.get("search_requirement_text"),
            "search_requirement_text",
        ),
        "source_authority_posture_requirement_ref": _required_text(
            packet.get("source_authority_posture_requirement_ref"),
            "source_authority_posture_requirement_ref",
        ),
        "source_authority_posture_requirement": _safe_mapping(
            packet.get("source_authority_posture_requirement")
        ),
        "relation_plan_ref": _without_empty(
            {
                "relation_plan_id": relation_plan_id,
                "relation_plan_packet_id": packet.get("relation_plan_packet_id"),
                "relation_plan_packet_digest": packet.get(
                    "relation_plan_packet_digest"
                ),
                "planning_status": (
                    "consumed" if packet.get("relation_plan_consumed") is True else None
                ),
            }
        ),
        "component_answer_type_binding_ref": _safe_mapping(
            packet.get("component_answer_type_binding_ref")
        ),
        "mode_or_budget_placeholder_ref": {
            "mode": packet.get("mode"),
            "budget_lease_created": False,
            "budget_lease_ref": "not_created_component_work_node_v0",
            "future_only": True,
        },
        **COMPONENT_WORK_NODE_NEGATIVE_CONTROL_FLAGS,
        "component_work_graph_implemented": False,
        "raw_private_retention_flags": dict(RAW_PRIVATE_RETENTION_FALSE_FLAGS),
        "node_is_projection_over_existing_refs": True,
        "node_creates_authority": False,
    }
    ref["input_ref_digest"] = _digest_json(ref)
    return validate_component_work_node_v0_input_ref(ref)


def _build_output_ref(
    packet: Mapping[str, Any],
    *,
    input_ref: Mapping[str, Any],
) -> dict[str, Any]:
    semantic = _safe_mapping(packet.get("semantic_status_payload"))
    dprime = _safe_mapping(semantic.get("dprime_status"))
    relation_ref = _safe_mapping(packet.get("dprime_relation_intake_ref")) or _safe_mapping(
        semantic.get("dprime_relation_intake_ref")
    )
    source_authority = _safe_mapping(
        semantic.get("source_obligation_authority_ref")
    ) or _safe_mapping(
        _safe_mapping(packet.get("single_relation_dprime_authority_integration")).get(
            "source_obligation_authority_ref"
        )
    )
    citation_authority = _safe_mapping(
        semantic.get("citation_eligibility_authority_ref")
    ) or _safe_mapping(
        _safe_mapping(packet.get("single_relation_dprime_authority_integration")).get(
            "citation_source_handoff_authority_ref"
        )
    )
    status = _node_status(packet)
    relation_refs = _relation_refs(packet, semantic, dprime, relation_ref)
    source_refs = _source_refs(packet, semantic, dprime, relation_ref, citation_authority)
    candidate_refs = _candidate_refs(packet, semantic, dprime, relation_ref)
    multi_shape = _multi_source_shape_ref(
        semantic,
        dprime,
        relation_refs=relation_refs,
        source_refs=source_refs,
        candidate_refs=candidate_refs,
    )
    ref = {
        "schema_version": COMPONENT_WORK_NODE_V0_SCHEMA_VERSION,
        "phase": COMPONENT_WORK_NODE_V0_PHASE,
        "node_kind": "component_work_node_v0_output",
        "node_id": input_ref["node_id"],
        "parent_run_id": input_ref["parent_run_id"],
        "component_id": input_ref["component_id"],
        "component_ids": [input_ref["component_id"]],
        "source_obligation_id": input_ref["source_obligation_id"],
        "source_obligation_lane_ids": [input_ref["source_obligation_id"]],
        "node_status": status,
        "decision_ref": _without_empty(
            {
                "decision": packet.get("decision"),
                "status_decision": packet.get("status_decision"),
                "blocker_code": packet.get("blocker_code"),
                "failure_attribution_bucket": packet.get(
                    "failure_attribution_bucket"
                ),
                "node_never_claims_product_correctness": True,
            }
        ),
        "selected_candidate_refs": _safe_refs(
            packet.get("selected_answer_bearing_candidate_refs")
        ),
        "candidate_refs": candidate_refs,
        "candidate_ref_count": len(candidate_refs),
        "fetch_read_packet_refs": _without_empty(
            {
                "fetch_read_packet_created": packet.get("fetch_read_packet_created"),
                "fetch_read_attempts": packet.get("fetch_read_attempts"),
                "fetch_read_completed": packet.get("fetch_read_completed"),
                "fetch_read_blocker": packet.get("fetch_read_blocker"),
                "fetch_read_blocker_detail": packet.get("fetch_read_blocker_detail"),
                "fetch_read_handoff_status": semantic.get("fetch_read_handoff_status"),
                "followup_fetch_read_packet_created": packet.get(
                    "followup_fetch_read_packet_created"
                ),
                "followup_fetch_read_attempts": packet.get(
                    "followup_fetch_read_attempts"
                ),
                "followup_fetch_read_completed": packet.get(
                    "followup_fetch_read_completed"
                ),
                "candidate_fetch_read_refs_are_semantic_support": False,
            }
        ),
        "source_evidence_admission_refs": _safe_refs(
            [semantic.get("source_evidence_admission_ref")]
        ),
        "evidence_ledger_source_evidence_admission_refs": _safe_refs(
            [semantic.get("source_evidence_admission_ref")]
        ),
        "workbench_refs": _safe_refs(
            [
                packet.get("candidate_evidence_triage_ref"),
                packet.get("analyst_workbench_ref"),
                packet.get("workbench_dprime_dossier_ref"),
                packet.get("analysis_gap_search_proposal_ref"),
                packet.get("workbench_reduction_projection_ref"),
            ]
        ),
        "workbench_dossier_ref": _safe_mapping(
            packet.get("workbench_dprime_dossier_ref")
        ),
        "analyst_finding_proposal_refs": _analyst_finding_refs(packet),
        "dprime_analyst_finding_support_validation_refs": _safe_refs(
            [packet.get("dprime_analyst_finding_support_validation_ref")]
        ),
        "dprime_relation_refs": relation_refs,
        "relation_ref_count": len(relation_refs),
        "source_refs": source_refs,
        "source_ref_count": len(source_refs),
        "dprime_multi_source_posture_refs": _safe_refs(
            [
                semantic.get("dprime_multi_source_relation_set_ref"),
                dprime.get("multi_source_relation_set_ref"),
                semantic.get("dprime_multi_source_support_posture_ref"),
                dprime.get("multi_source_support_posture_ref"),
                semantic.get("dprime_scrutineer_challenge_ref"),
                dprime.get("multi_source_scrutineer_challenge_ref"),
            ]
        ),
        "multi_source_shape_ref": multi_shape,
        "run_kernel_admission_refs": _safe_refs(
            [
                packet.get("runkernel_analyst_finding_admission_ref"),
                dprime.get("run_kernel_support_admission_request_ref"),
                dprime.get("run_kernel_support_admission_ref"),
            ]
        ),
        "semantic_observation_refs": _safe_refs(
            [
                packet.get("analyst_finding_semantic_observation_ref"),
                semantic.get("semantic_observation_admission_ref"),
                dprime.get("semantic_observation_ref"),
                dprime.get("analyst_finding_semantic_observation_ref"),
            ]
        ),
        "component_coverage_refs": _safe_refs(
            [
                packet.get("analyst_finding_component_coverage_ref"),
                semantic.get("component_coverage_ref"),
                dprime.get("analyst_finding_component_coverage_ref"),
            ]
        ),
        "source_obligation_authority_refs": _safe_refs([source_authority]),
        "citation_source_handoff_refs": _safe_refs([citation_authority]),
        "followup_recovery_refs": _safe_refs(
            [
                packet.get("workbench_gap_reentry_ref"),
                packet.get("followup_search_intent_ref"),
                packet.get("runkernel_followup_authorization_ref"),
                packet.get("source_obligation_recovery_authorization"),
                packet.get("source_challenge_recovery_plan"),
                semantic.get("dprime_followup_search_reentry_ref"),
            ]
        ),
        "blocker_refs": _blocker_refs(packet),
        "caveats": _text_tuple(packet.get("explicit_non_proofs"), limit=400),
        "nonclaims": (
            "ComponentWorkNode V0 is a projection over one existing component lane.",
            "ComponentWorkNode V0 does not create authority.",
            "ComponentWorkNode V0 does not prove product correctness.",
            "Candidate and fetch/read refs are custody or lineage until existing support authority consumes them.",
        ),
        "raw_private_retention_flags": dict(RAW_PRIVATE_RETENTION_FALSE_FLAGS),
        "closed_downstream_flags": dict(COMPONENT_WORK_NODE_CLOSED_DOWNSTREAM_FLAGS),
        **COMPONENT_WORK_NODE_CLOSED_DOWNSTREAM_FLAGS,
        **COMPONENT_WORK_NODE_NEGATIVE_CONTROL_FLAGS,
        "source_obligation_authority_consumed": (
            packet.get("source_obligation_authority_consumed") is True
        ),
        "citation_source_handoff_authority_consumed": (
            packet.get("citation_source_handoff_authority_consumed") is True
        ),
        "source_obligation_satisfaction_claimed": False,
        "citation_eligibility_claimed": False,
        "node_pass_product_correctness": False,
        "node_created_new_dprime_path": False,
        "node_created_parallel_query_planner": False,
        "node_created_parallel_evidence_lane": False,
    }
    ref["output_ref_digest"] = _digest_json(ref)
    return validate_component_work_node_v0_output_ref(ref)


def _node_status(packet: Mapping[str, Any]) -> str:
    if packet.get("source_obligation_authority_consumed") is True or packet.get(
        "citation_source_handoff_authority_consumed"
    ) is True:
        return COMPONENT_WORK_NODE_STATUS_CONSUMED
    if _clean_text(packet.get("blocker_code"), limit=220):
        return COMPONENT_WORK_NODE_STATUS_BLOCKED
    if packet.get("relation_plan_consumed") is True:
        return COMPONENT_WORK_NODE_STATUS_BLOCKED
    return COMPONENT_WORK_NODE_STATUS_NOT_REACHED


def _relation_refs(
    packet: Mapping[str, Any],
    semantic: Mapping[str, Any],
    dprime: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
) -> list[dict[str, Any]]:
    relation_set = _safe_mapping(
        semantic.get("dprime_multi_source_relation_set_ref")
    ) or _safe_mapping(dprime.get("multi_source_relation_set_ref"))
    return _dedupe_refs(
        [
            relation_ref,
            packet.get("relation_plan_dprime_relation_intake_candidate"),
            *[
                _safe_mapping(item)
                for item in _safe_sequence(relation_set.get("relation_intake_refs"))
            ],
        ]
    )


def _source_refs(
    packet: Mapping[str, Any],
    semantic: Mapping[str, Any],
    dprime: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
    citation_authority: Mapping[str, Any],
) -> list[dict[str, Any]]:
    relation_set = _safe_mapping(
        semantic.get("dprime_multi_source_relation_set_ref")
    ) or _safe_mapping(dprime.get("multi_source_relation_set_ref"))
    support_posture = _safe_mapping(
        semantic.get("dprime_multi_source_support_posture_ref")
    ) or _safe_mapping(dprime.get("multi_source_support_posture_ref"))
    relation_source = _without_empty(
        {
            "candidate_id": relation_ref.get("evidence_candidate_id")
            or relation_ref.get("candidate_id"),
            "candidate_digest": relation_ref.get("candidate_digest"),
            "reference_id": relation_ref.get("evidence_reference_id")
            or relation_ref.get("reference_id"),
            "title": relation_ref.get("source_title"),
            "url": relation_ref.get("source_url"),
            "domain": relation_ref.get("source_domain"),
        }
    )
    citation_records = [
        _safe_mapping(item)
        for item in _safe_sequence(citation_authority.get("citation_source_records"))
    ]
    return _dedupe_refs(
        [
            relation_source,
            packet.get("selected_source_candidate_ref"),
            packet.get("followup_selected_source_candidate"),
            *[
                _safe_mapping(item)
                for item in _safe_sequence(relation_set.get("evidence_source_refs"))
            ],
            *[
                _safe_mapping(item)
                for item in _safe_sequence(
                    support_posture.get("source_display_candidate_refs")
                )
            ],
            *citation_records,
        ]
    )


def _candidate_refs(
    packet: Mapping[str, Any],
    semantic: Mapping[str, Any],
    dprime: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
) -> list[dict[str, Any]]:
    relation_set = _safe_mapping(
        semantic.get("dprime_multi_source_relation_set_ref")
    ) or _safe_mapping(dprime.get("multi_source_relation_set_ref"))
    support_posture = _safe_mapping(
        semantic.get("dprime_multi_source_support_posture_ref")
    ) or _safe_mapping(dprime.get("multi_source_support_posture_ref"))
    source_admission = _safe_mapping(semantic.get("source_evidence_admission_ref"))
    relation_candidate = _without_empty(
        {
            "candidate_id": relation_ref.get("evidence_candidate_id")
            or relation_ref.get("candidate_id"),
            "candidate_digest": relation_ref.get("candidate_digest"),
            "reference_id": relation_ref.get("evidence_reference_id")
            or relation_ref.get("reference_id"),
            "title": relation_ref.get("source_title"),
            "url": relation_ref.get("source_url"),
            "domain": relation_ref.get("source_domain"),
        }
    )
    return _dedupe_refs(
        [
            *[
                _safe_mapping(item)
                for item in _safe_sequence(
                    packet.get("selected_answer_bearing_candidate_refs")
                )
            ],
            source_admission,
            relation_candidate,
            packet.get("workbench_expected_candidate_ref"),
            packet.get("dprime_intake_actual_candidate_ref"),
            packet.get("selected_source_candidate_ref"),
            packet.get("source_display_candidate_ref"),
            packet.get("followup_selected_source_candidate"),
            *[
                _safe_mapping(item)
                for item in _safe_sequence(relation_set.get("evidence_source_refs"))
            ],
            *[
                _safe_mapping(item)
                for item in _safe_sequence(
                    support_posture.get("source_display_candidate_refs")
                )
            ],
        ]
    )


def _multi_source_shape_ref(
    semantic: Mapping[str, Any],
    dprime: Mapping[str, Any],
    *,
    relation_refs: Sequence[Mapping[str, Any]],
    source_refs: Sequence[Mapping[str, Any]],
    candidate_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    relation_set = _safe_mapping(
        semantic.get("dprime_multi_source_relation_set_ref")
    ) or _safe_mapping(dprime.get("multi_source_relation_set_ref"))
    support_posture = _safe_mapping(
        semantic.get("dprime_multi_source_support_posture_ref")
    ) or _safe_mapping(dprime.get("multi_source_support_posture_ref"))
    scrutineer = _safe_mapping(
        semantic.get("dprime_scrutineer_challenge_ref")
    ) or _safe_mapping(dprime.get("multi_source_scrutineer_challenge_ref"))
    relation_ref_count = len(relation_refs)
    source_ref_count = len(source_refs)
    candidate_ref_count = len(candidate_refs)
    relation_count = _first_count(
        (
            semantic.get("dprime_multi_source_relation_count"),
            relation_set.get("relation_count"),
            support_posture.get("relation_count"),
        ),
        default=relation_ref_count,
    )
    source_count = _first_count(
        (
            semantic.get("dprime_multi_source_source_count"),
            relation_set.get("source_count"),
            support_posture.get("source_count"),
        ),
        default=source_ref_count,
    )
    return _without_empty(
        {
            "status": (
                "preserved"
                if relation_set or support_posture or relation_count > 1
                else "not_present"
            ),
            "relation_set_ref": relation_set,
            "support_posture_ref": support_posture,
            "scrutineer_challenge_ref": scrutineer,
            "relation_count": relation_count,
            "source_count": source_count,
            "relation_ref_count": relation_ref_count,
            "source_ref_count": source_ref_count,
            "candidate_ref_count": candidate_ref_count,
            "relation_refs": [dict(item) for item in relation_refs],
            "source_refs": [dict(item) for item in source_refs],
            "candidate_refs": [dict(item) for item in candidate_refs],
            "currentness_posture": support_posture.get("currentness_posture"),
            "conflict_posture": support_posture.get("conflict_posture"),
            "challenge_kind": support_posture.get("challenge_kind")
            or scrutineer.get("challenge_kind"),
            "answer_path_allowed": support_posture.get("answer_path_allowed"),
            "best_source_collapse_created": False,
            "single_undifferentiated_source_output_created": False,
            "multi_component_claimed": False,
        }
    )


def _analyst_finding_refs(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    dossier = _safe_mapping(packet.get("workbench_dprime_dossier"))
    dossier_ref = _safe_mapping(packet.get("workbench_dprime_dossier_ref"))
    refs = [
        dossier.get("analyst_finding_proposal_ref"),
        dossier.get("analyst_finding_proposal"),
        dossier_ref.get("analyst_finding_proposal_ref"),
        packet.get("first_pass_analyst_finding_proposal_ref"),
        packet.get("followup_analyst_finding_proposal_ref"),
    ]
    return _safe_refs(refs)


def _blocker_refs(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _safe_refs(
        [
            {
                "blocker_code": packet.get("blocker_code"),
                "blocker_detail": packet.get("blocker_detail"),
                "decision": packet.get("decision"),
                "status_decision": packet.get("status_decision"),
            },
            packet.get("source_readiness_gateway"),
            packet.get("single_relation_dprime_authority_integration"),
            packet.get("source_citation_display_boundary"),
            packet.get("workbench_gap_reentry_ref"),
        ]
    )


def _validate_boundary_flags(ref: Mapping[str, Any]) -> None:
    for key, expected in COMPONENT_WORK_NODE_NEGATIVE_CONTROL_FLAGS.items():
        if key in ref and ref.get(key) is not expected:
            raise ComponentWorkNodeError(f"ComponentWorkNode boundary flag invalid: {key}")
    for key in (
        "multi_component_planning_opened",
        "component_work_graph_scheduling_opened",
        "parallel_component_execution_opened",
        "budget_lease_created",
        "final_analyst_aggregation_created",
        "product_correctness_claimed",
    ):
        if ref.get(key) is not False:
            raise ComponentWorkNodeError(f"ComponentWorkNode must keep {key}=false")


def _validate_multi_source_shape(ref: Mapping[str, Any]) -> None:
    shape = _safe_mapping(ref.get("multi_source_shape_ref"))
    if not shape:
        raise ComponentWorkNodeError("ComponentWorkNode output missing multi-source ref")
    if shape.get("best_source_collapse_created") is not False:
        raise ComponentWorkNodeError("ComponentWorkNode collapsed sources into best source")
    if shape.get("single_undifferentiated_source_output_created") is not False:
        raise ComponentWorkNodeError("ComponentWorkNode collapsed multi-source shape")
    relation_count = _bounded_int(shape.get("relation_count"))
    source_count = _bounded_int(shape.get("source_count"))
    if relation_count > 1 and len(_safe_sequence(shape.get("relation_refs"))) < 2:
        raise ComponentWorkNodeError("multi-source relation refs were collapsed")
    if source_count > 1 and len(_safe_sequence(shape.get("source_refs"))) < 2:
        raise ComponentWorkNodeError("multi-source source refs were collapsed")
    if source_count > 1 and _bounded_int(shape.get("candidate_ref_count")) < 2:
        raise ComponentWorkNodeError("multi-source candidate refs were collapsed")


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    allowed_false_keys = set(RAW_PRIVATE_RETENTION_FALSE_FLAGS)
    forbidden = sorted(
        key for key in keys & _FORBIDDEN_NORMALIZED_KEYS if key not in allowed_false_keys
    )
    if forbidden:
        raise ComponentWorkNodeError(
            f"{context} includes forbidden material: {', '.join(forbidden)}"
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise ComponentWorkNodeError(
            f"{context} attempts forbidden authority upgrade: "
            + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(normalized)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _require_false(value: Mapping[str, Any], keys: Sequence[str]) -> None:
    for key in keys:
        if value.get(key) is not False:
            raise ComponentWorkNodeError(f"ComponentWorkNode must keep {key}=false")


def _required_text(value: Any, key: str) -> str:
    text = _clean_text(value, limit=900)
    if not text:
        raise ComponentWorkNodeError(f"ComponentWorkNode requires {key}")
    return text


def _dedupe_refs(values: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        ref = _safe_mapping(value)
        if not ref:
            continue
        _reject_forbidden_material(ref, context="ComponentWorkNode nested ref")
        identity = (
            _clean_text(ref.get("relation_intake_id"), limit=320)
            or _clean_text(ref.get("candidate_id"), limit=320)
            or _clean_text(ref.get("reference_id"), limit=320)
            or _clean_text(ref.get("url"), limit=900)
            or _digest_json(ref)
        )
        if identity in seen:
            continue
        seen.add(identity)
        out.append(_json_safe(ref))
    return out


def _safe_refs(values: Any) -> list[dict[str, Any]]:
    if isinstance(values, Mapping):
        return [dict(values)] if values else []
    refs: list[dict[str, Any]] = []
    for item in _safe_sequence(values):
        ref = _safe_mapping(item)
        if ref:
            refs.append(ref)
    return _dedupe_refs(refs)


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


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _first_count(values: Sequence[Any], *, default: int = 0) -> int:
    for value in values:
        if value is None or value == "":
            continue
        return _bounded_int(value, default=default)
    return default


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {}, ())
    }


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def component_work_node_v1_from_admitted_component(
    *,
    run_id: str,
    request_id: str,
    accepted_component_ref: Mapping[str, Any],
    component_admission_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a V1 node from canonical ordinary RunKernel component state.

    V0 remains the single-relation compatibility surface.  V1 is the ordinary
    graph input and therefore requires current run/revision/digest bindings and
    a RunKernel component-admission posture before graph consumption.
    """

    component = _safe_mapping(accepted_component_ref)
    admission = _safe_mapping(component_admission_ref)
    if (
        admission.get("schema_version")
        != "multicomponent_component_admission_ref_v1"
        or admission.get("owner")
        != "RunKernel.MulticomponentComponentAdmission"
        or admission.get("canonical_state") is not True
        or not _clean_text(admission.get("action_id"), limit=200)
        or not _clean_text(
            admission.get("accepted_contract_version"),
            limit=200,
        )
        or not _clean_text(
            admission.get("accepted_contract_digest"),
            limit=128,
        )
    ):
        raise ComponentWorkNodeError(
            "ComponentWorkNode V1 requires canonical RunKernel component admission"
        )
    component_id = _required_text(component.get("component_id"), "component_id")
    component_revision = _required_text(
        component.get("component_revision"), "component_revision"
    )
    component_digest = _required_text(
        component.get("component_digest"), "component_digest"
    )
    if admission.get("run_id") != run_id or admission.get("request_id") != request_id:
        raise ComponentWorkNodeError("ComponentWorkNode V1 cross-run admission ref")
    if (
        admission.get("component_id") != component_id
        or admission.get("component_revision") != component_revision
        or admission.get("component_digest") != component_digest
    ):
        raise ComponentWorkNodeError(
            "ComponentWorkNode V1 component admission binding mismatch"
        )
    status = _clean_text(admission.get("admission_status"), limit=80)
    if status not in {"admitted", "admitted_with_caveats", "blocked", "unsupported"}:
        raise ComponentWorkNodeError("ComponentWorkNode V1 admission status invalid")
    analyst_ref = _safe_mapping(admission.get("analyst_finding_ref"))
    dprime_ref = _safe_mapping(admission.get("dprime_validation_ref"))
    if not analyst_ref or not dprime_ref:
        raise ComponentWorkNodeError(
            "ComponentWorkNode V1 requires Analyst and component D-prime refs"
        )
    observation_ref = _safe_mapping(admission.get("semantic_observation_ref"))
    coverage_ref = _safe_mapping(admission.get("component_coverage_ref"))
    admitted_claim_ref = _safe_mapping(admission.get("admitted_claim_ref"))
    admitted = status in {"admitted", "admitted_with_caveats"}
    if admitted and (not observation_ref or not coverage_ref or not admitted_claim_ref):
        raise ComponentWorkNodeError(
            "admitted ComponentWorkNode V1 requires claim, SemanticObservation, and ComponentCoverage"
        )
    if not admitted and (observation_ref or coverage_ref or admitted_claim_ref):
        raise ComponentWorkNodeError(
            "blocked ComponentWorkNode V1 cannot carry admitted semantic state"
        )

    node = {
        "schema_version": COMPONENT_WORK_NODE_V1_SCHEMA_VERSION,
        "phase": COMPONENT_WORK_NODE_V1_PHASE,
        "runtime_consumer": COMPONENT_WORK_NODE_V1_RUNTIME_CONSUMER,
        "node_kind": "component",
        "node_id": f"component-work-node:v1:{component_id}",
        "node_revision": component_revision,
        "node_digest": None,
        "run_id": run_id,
        "request_id": request_id,
        "component_id": component_id,
        "component_revision": component_revision,
        "component_digest": component_digest,
        "component_label": _clean_text(
            component.get("user_facing_label")
            or component.get("user_facing_question"),
            limit=240,
        ),
        "component_question": _clean_text(
            component.get("user_facing_question")
            or component.get("user_facing_label"),
            limit=400,
        ),
        "admission_status": status,
        "current": admission.get("current") is True,
        "stale": admission.get("stale") is True,
        "analyst_finding_ref": analyst_ref,
        "dprime_validation_ref": dprime_ref,
        "admitted_claim_ref": admitted_claim_ref,
        "semantic_observation_ref": observation_ref,
        "component_coverage_ref": coverage_ref,
        "evidence_refs": _safe_refs(admission.get("evidence_refs")),
        "required_caveats": list(
            _text_tuple(admission.get("required_caveats"), limit=320)
        ),
        "preserved_nonclaims": list(
            _text_tuple(admission.get("preserved_nonclaims"), limit=320)
        ),
        "blocker_refs": _safe_refs(admission.get("blocker_refs")),
        "direct_output_eligible": admitted and admission.get("current") is True,
        "created_from_canonical_component_admission": True,
        "component_admission_action_ref": {
            "action_id": admission.get("action_id"),
            "owner": admission.get("owner"),
        },
        "graph_scheduler": False,
        "runtime_parallelism": False,
        "citation_eligible": False,
        "final_answer_packet_created": False,
        "author_output_created": False,
        "product_correctness_claimed": False,
    }
    node["node_digest"] = _digest_json(
        {key: value for key, value in node.items() if key != "node_digest"}
    )
    return validate_component_work_node_v1(node)


def validate_component_work_node_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    node = _safe_mapping(value)
    if node.get("schema_version") != COMPONENT_WORK_NODE_V1_SCHEMA_VERSION:
        raise ComponentWorkNodeError("ComponentWorkNode V1 schema mismatch")
    if node.get("phase") != COMPONENT_WORK_NODE_V1_PHASE:
        raise ComponentWorkNodeError("ComponentWorkNode V1 phase mismatch")
    for key in (
        "node_id",
        "node_revision",
        "node_digest",
        "run_id",
        "request_id",
        "component_id",
        "component_revision",
        "component_digest",
    ):
        _required_text(node.get(key), key)
    if node.get("node_kind") != "component":
        raise ComponentWorkNodeError("ComponentWorkNode V1 kind mismatch")
    if node.get("node_revision") != node.get("component_revision"):
        raise ComponentWorkNodeError("ComponentWorkNode V1 revision mismatch")
    if node.get("stale") is True or node.get("current") is not True:
        if node.get("direct_output_eligible") is True:
            raise ComponentWorkNodeError(
                "stale ComponentWorkNode V1 cannot be direct-output eligible"
            )
    for key in (
        "graph_scheduler",
        "runtime_parallelism",
        "citation_eligible",
        "final_answer_packet_created",
        "author_output_created",
        "product_correctness_claimed",
    ):
        if node.get(key) is not False:
            raise ComponentWorkNodeError(f"ComponentWorkNode V1 requires {key}=false")
    expected = _digest_json(
        {key: value for key, value in node.items() if key != "node_digest"}
    )
    if node.get("node_digest") != expected:
        raise ComponentWorkNodeError("ComponentWorkNode V1 digest mismatch")
    _reject_forbidden_material(node, context="ComponentWorkNode V1")
    return _json_safe(node)


__all__ = [
    "COMPONENT_WORK_NODE_STATUS_BLOCKED",
    "COMPONENT_WORK_NODE_STATUS_CONSUMED",
    "COMPONENT_WORK_NODE_STATUS_NOT_REACHED",
    "COMPONENT_WORK_NODE_V0_PHASE",
    "COMPONENT_WORK_NODE_V0_SCHEMA_VERSION",
    "COMPONENT_WORK_NODE_V0_RUNTIME_CONSUMER",
    "COMPONENT_WORK_NODE_V1_PHASE",
    "COMPONENT_WORK_NODE_V1_RUNTIME_CONSUMER",
    "COMPONENT_WORK_NODE_V1_SCHEMA_VERSION",
    "ComponentWorkNodeError",
    "component_work_node_v0_refs_from_product_packet",
    "component_work_node_v1_from_admitted_component",
    "validate_component_work_node_v0_input_ref",
    "validate_component_work_node_v0_output_ref",
    "validate_component_work_node_v0_refs",
    "validate_component_work_node_v1",
]
