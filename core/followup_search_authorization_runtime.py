"""RunKernel-owned follow-up search authorization state.

This module evaluates validated ``FollowupSearchIntentPacket`` proposals and
builds bounded follow-up search work identity only. It does not dispatch search,
call providers or brokers, fetch/read, admit evidence, create SemanticObservation
or ComponentCoverage state, decide Sufficiency, create FinalAnswerPacket state,
or create Author input.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from core.analysis_gap_followup_search_packet import (
    NON_SEARCHABLE_REVIEW_GAP,
    validate_followup_search_intent_packet,
)

FOLLOWUP_SEARCH_AUTHORIZATION_SCHEMA_VERSION = (
    "followup_search_authorization_ag_followup_search_authorization_reentry_01_v1"
)
FOLLOWUP_SEARCH_AUTHORIZATION_OBSERVATION_SCHEMA_VERSION = (
    "followup_search_authorization_observation_ag_followup_search_authorization_reentry_01_v1"
)
FOLLOWUP_SEARCH_QUERY_BUNDLE_SCHEMA_VERSION = (
    "followup_search_query_bundle_ag_followup_search_authorization_reentry_01_v1"
)
FOLLOWUP_SEARCH_WORK_IDENTITY_SCHEMA_VERSION = (
    "followup_search_work_identity_ag_followup_search_authorization_reentry_01_v1"
)
FOLLOWUP_SEARCH_AUTHORIZATION_STAGE = "followup_search_authorization"
FOLLOWUP_SEARCH_AUTHORIZATION_REASON = (
    "followup_search_authorization_from_runkernel_followup_intent"
)
FOLLOWUP_SEARCH_AUTHORIZATION_TRACE_KEY = "followup_search_authorization"
FOLLOWUP_SEARCH_AUTHORIZATION_OWNER = "RunKernel.FollowupSearchAuthorization"

_MODE_LABELS = {
    "fast": "Fast",
    "balanced": "Balanced",
    "deep": "Deep",
}
_SUPPORTED_SOURCE_CLASS_HINTS = frozenset(
    {
        "analysis_bearing_source",
        "comparison_or_reconciliation_source",
        "current_primary_or_official",
        "fact_bearing_source",
        "legal_or_regulatory_text",
        "official_current_or_primary_source",
        "official_current_rules",
        "primary_source_documents",
        "readable_replacement_source",
        "scope_disambiguating_source",
    }
)
_CONCRETE_BLOCKER_KINDS = frozenset(
    {
        "currentness_concern",
        "missing_fact",
        "missing_readable_source",
        "possible_contradiction",
        "scope_mismatch",
        "unreadable_source",
    }
)
_CLOSED_FALSE_FLAGS = {
    "live_dispatch_executed": False,
    "provider_called": False,
    "broker_called": False,
    "model_called": False,
    "retrieval_executed": False,
    "live_fetch_read_executed": False,
    "search_result_candidate_packet_created": False,
    "fetch_read_content_packet_created": False,
    "evidence_ledger_admitted": False,
    "semantic_observation_admitted": False,
    "component_coverage_created": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "current_answer_contract_mutated": False,
    "product_correctness_claimed": False,
}
_RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "body",
        "cache",
        "cookie",
        "db",
        "env",
        "full_prompt",
        "full_text",
        "full_trace",
        "headers",
        "html",
        "log",
        "logs",
        "model_response",
        "page_content",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_model_response",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "token",
        "unbounded_text",
    }
)
_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "author_input",
        "citation",
        "citations",
        "component_coverage",
        "current_answer_contract",
        "evidence",
        "final_answer",
        "final_answer_packet",
        "semantic_observation",
        "source_obligation_satisfaction",
        "sufficiency_judgment",
    }
)
_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_CLOSED_FALSE_FLAGS,
        "author_input_ready",
        "citation_rendered",
        "component_satisfied",
        "evidence_admitted",
        "final_answer_ready",
        "live_provider_called",
        "live_search_executed",
        "provider_execution_licensed",
        "search_dispatched",
        "source_obligation_support_created",
    }
)


class FollowupSearchAuthorizationRuntimeError(ValueError):
    """Raised when follow-up search authorization cannot be reduced safely."""


def build_followup_search_authorization_action_inputs(
    *,
    run_id: str,
    request_id: str,
    followup_search_intent_packet: Mapping[str, Any],
    current_answer_contract: Mapping[str, Any],
    existing_authorization_projection: Mapping[str, Any] | None = None,
    mode: str = "Balanced",
    proposal_ids: Sequence[str] = (),
    logical_depth: int = 1,
    unresolved_blocker_ids: Sequence[str] = (),
    new_evidence_expected: bool = True,
    extra_recovery_authorized: bool = False,
) -> dict[str, Any]:
    """Build action inputs for an authorized follow-up search work identity."""

    _reject_forbidden_surface_claims(
        followup_search_intent_packet,
        context="follow-up search intent packet",
    )
    packet = validate_followup_search_intent_packet(followup_search_intent_packet)
    clean_run_id = _required_token(run_id, "follow-up authorization requires run_id")
    clean_request_id = _required_token(
        request_id,
        "follow-up authorization requires request_id",
    )
    if packet.get("run_id") != clean_run_id or packet.get("request_id") != clean_request_id:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up intent packet run/request lineage does not match RunKernel"
        )
    mode_label = _mode_label(mode)
    contract_ref = _contract_ref_from_contract(current_answer_contract)
    if not contract_ref:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization requires current_answer_contract lineage"
        )
    packet_contract_ref = _safe_mapping(packet.get("current_answer_contract_ref"))
    if not packet_contract_ref or packet_contract_ref != contract_ref:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up intent packet current_answer_contract lineage is stale"
        )
    if packet.get("current_answer_contract_digest") != contract_ref.get("contract_digest"):
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up intent packet current_answer_contract digest is stale"
        )

    selected = _selected_proposals(packet, proposal_ids)
    _validate_selected_proposals(selected)
    unresolved_ids = _text_list(unresolved_blocker_ids, limit=320)
    depth = _bounded_int(logical_depth, default=1)
    if depth <= 0:
        depth = 1
    existing = _safe_mapping(existing_authorization_projection)
    loop_count = _bounded_int(existing.get("authorized_loop_count"), default=0) + 1
    _enforce_mode_budget(
        mode=mode_label,
        loop_count=loop_count,
        logical_depth=depth,
        unresolved_blocker_ids=unresolved_ids,
        extra_recovery_authorized=extra_recovery_authorized,
    )
    if new_evidence_expected is not True:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization rejected: no_new_evidence_expected"
        )

    query_bundle = _query_bundle(
        run_id=clean_run_id,
        request_id=clean_request_id,
        mode=mode_label,
        current_answer_contract_ref=contract_ref,
        packet=packet,
        selected=selected,
        logical_depth=depth,
    )
    work_identity = _work_identity(
        run_id=clean_run_id,
        request_id=clean_request_id,
        mode=mode_label,
        current_answer_contract_ref=contract_ref,
        packet=packet,
        selected=selected,
        query_bundle=query_bundle,
        logical_depth=depth,
    )
    _reject_duplicate_work(existing, work_identity)
    authorization_base = {
        "schema_version": FOLLOWUP_SEARCH_AUTHORIZATION_SCHEMA_VERSION,
        "owner": FOLLOWUP_SEARCH_AUTHORIZATION_OWNER,
        "trace_key": FOLLOWUP_SEARCH_AUTHORIZATION_TRACE_KEY,
        "canonical_state": True,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "mode": mode_label,
        "logical_depth": depth,
        "authorized_loop_count": loop_count,
        "followup_search_authorized": True,
        "proposal_packet_ref": _packet_ref(packet),
        "authorized_proposal_refs": [_proposal_ref(item) for item in selected],
        "authorized_source_gap_kinds": [
            item["source_gap_kind"] for item in selected
        ],
        "current_answer_contract_ref": contract_ref,
        "current_answer_contract_digest": contract_ref["contract_digest"],
        "mode_budget": _mode_budget(mode_label, extra_recovery_authorized),
        "budget_policy_enforced": True,
        "criteria_enforced": [
            "validated_followup_search_intent_packet",
            "ready_for_authorization_review",
            "current_answer_contract_lineage",
            "mode_budget_available",
            "non_duplicate_work_identity",
            "supported_source_class_hint",
            "no_downstream_authority_claims",
        ],
        "unresolved_blocker_ids": unresolved_ids,
        "query_bundle": query_bundle,
        "authorized_work_identity": work_identity,
        "query_bundle_created": True,
        "search_executor_handoff_style_identity_created": True,
        "live_dispatch_allowed": False,
        "fixture_reentry_only": True,
        "proposal_packet_authorizes_search_by_itself": False,
        "search_executor_handoff_state_mutated": False,
        **_CLOSED_FALSE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
    }
    authorization_id = (
        "followup-search-authorization:"
        f"{clean_request_id}:{_digest_json(authorization_base)[:16]}"
    )
    authorization = {
        **authorization_base,
        "authorization_id": authorization_id,
        "authorization_digest": _digest_json(
            {**authorization_base, "authorization_id": authorization_id}
        ),
    }
    return authorization


def build_followup_search_authorization_observation_payload(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a reducer observation payload from an authorized action."""

    inputs = _safe_mapping(action_inputs)
    if inputs.get("schema_version") != FOLLOWUP_SEARCH_AUTHORIZATION_SCHEMA_VERSION:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization action input schema mismatch"
        )
    state = {
        **inputs,
        "authorized_action_id": _required_token(
            action_id,
            "follow-up search authorization observation requires action_id",
            limit=200,
        ),
    }
    return {
        "schema_version": FOLLOWUP_SEARCH_AUTHORIZATION_OBSERVATION_SCHEMA_VERSION,
        "followup_search_authorization": state,
    }


def build_followup_search_authorization_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    existing_authorization_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the reducer observation and build canonical authorization state."""

    clean_action_id = _required_token(
        action_id,
        "follow-up search authorization reduction requires action_id",
        limit=200,
    )
    clean_run_id = _required_token(
        run_id,
        "follow-up search authorization reduction requires run_id",
    )
    clean_request_id = _required_token(
        request_id,
        "follow-up search authorization reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    payload = _safe_mapping(observation_payload)
    if payload.get("schema_version") != FOLLOWUP_SEARCH_AUTHORIZATION_OBSERVATION_SCHEMA_VERSION:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization observation schema mismatch"
        )
    state = _safe_mapping(payload.get("followup_search_authorization"))
    if not state:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization observation requires state"
        )
    if state.get("authorized_action_id") != clean_action_id:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization action_id binding mismatch"
        )
    if state.get("run_id") != clean_run_id or state.get("request_id") != clean_request_id:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization run/request binding mismatch"
        )
    comparable_state = dict(state)
    comparable_state.pop("authorized_action_id", None)
    if inputs != comparable_state:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization observation does not match action inputs"
        )
    _validate_closed_flags(state)
    declared_digest = _required_token(
        state.get("authorization_digest"),
        "follow-up search authorization requires authorization_digest",
        limit=128,
    )
    digest_payload = dict(state)
    digest_payload.pop("authorization_digest", None)
    digest_payload.pop("authorized_action_id", None)
    if declared_digest != _digest_json(digest_payload):
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization digest mismatch"
        )

    existing = _safe_mapping(existing_authorization_projection)
    prior_history = [
        _safe_mapping(item)
        for item in _safe_list(existing.get("authorization_history"))
    ]
    prior_work = [
        _safe_mapping(item)
        for item in _safe_list(existing.get("authorized_work_identities"))
    ]
    latest = _authorization_history_entry(state)
    history = [*prior_history, latest]
    work = [*prior_work, _safe_mapping(state.get("authorized_work_identity"))]
    return {
        **state,
        "authorization_history": history,
        "authorized_work_identities": work,
        "authorized_loop_count": len(history),
    }


def build_followup_search_authorization_projection(
    *,
    authorization_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project canonical follow-up search authorization with closed surfaces."""

    state = _safe_mapping(authorization_state)
    latest = _authorization_history_entry(state)
    return {
        "owner": FOLLOWUP_SEARCH_AUTHORIZATION_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": FOLLOWUP_SEARCH_AUTHORIZATION_TRACE_KEY,
        "canonical_state": True,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "mode": state.get("mode"),
        "logical_depth": state.get("logical_depth"),
        "authorized_loop_count": _bounded_int(
            state.get("authorized_loop_count"),
            default=0,
        ),
        "latest_authorization": latest,
        "authorization_history": [
            _authorization_history_entry(item)
            for item in _safe_list(state.get("authorization_history"))
        ],
        "authorized_work_identities": [
            _work_projection(item)
            for item in _safe_list(state.get("authorized_work_identities"))
        ],
        "current_answer_contract_ref": _safe_mapping(
            state.get("current_answer_contract_ref")
        ),
        "current_answer_contract_digest": state.get("current_answer_contract_digest"),
        "mode_budget": _safe_mapping(state.get("mode_budget")),
        "budget_policy_enforced": state.get("budget_policy_enforced") is True,
        "live_dispatch_allowed": False,
        "fixture_reentry_only": True,
        "proposal_packet_authorizes_search_by_itself": False,
        "search_executor_handoff_state_mutated": False,
        **_CLOSED_FALSE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
    }


def _selected_proposals(
    packet: Mapping[str, Any],
    proposal_ids: Sequence[str],
) -> list[dict[str, Any]]:
    proposals = [
        _safe_mapping(item)
        for item in _safe_list(packet.get("analysis_gap_search_proposals"))
    ]
    requested = _text_list(proposal_ids, limit=320)
    if requested:
        by_id = {item.get("proposal_id"): item for item in proposals}
        missing = [item for item in requested if item not in by_id]
        if missing:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization references unknown proposal(s): "
                + ", ".join(missing)
            )
        return [by_id[item] for item in requested]
    return [
        item
        for item in proposals
        if item.get("ready_for_authorization_review") is True
        and item.get("followup_intent_kind") != NON_SEARCHABLE_REVIEW_GAP
    ]


def _validate_selected_proposals(selected: Sequence[Mapping[str, Any]]) -> None:
    if not selected:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization requires at least one review-ready proposal"
        )
    for proposal in selected:
        if proposal.get("proposal_only") is not True:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization can only consume proposal-only records"
            )
        if proposal.get("ready_for_authorization_review") is not True:
            blockers = ", ".join(
                _text_list(proposal.get("authorization_review_blockers"), limit=320)
            )
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization rejected: "
                f"proposal_not_review_ready {blockers}".strip()
            )
        if proposal.get("search_intent_proposed") is not True:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization rejected: proposal_does_not_search"
            )
        required = (
            "proposal_id",
            "proposal_digest",
            "source_gap_id",
            "source_gap_digest",
            "source_gap_kind",
            "trigger_reference_id",
            "trigger_reference_digest",
            "current_answer_contract_ref",
            "current_answer_contract_digest",
            "evidence_relative_analysis_packet_id",
            "evidence_relative_analysis_packet_digest",
            "analyst_report_id",
            "analyst_report_digest",
        )
        missing = [key for key in required if not proposal.get(key)]
        if missing:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization rejected: missing_lineage "
                + ", ".join(missing)
            )
        source_class = _clean_token(
            proposal.get("required_source_class_hint"),
            limit=260,
        )
        if source_class not in _SUPPORTED_SOURCE_CLASS_HINTS:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization rejected: unsupported_source_class "
                + str(source_class)
            )
        if proposal.get("authorized") is not False:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization rejected: proposal_already_authorized"
            )
        _validate_closed_flags(proposal, require_all=False)


def _enforce_mode_budget(
    *,
    mode: str,
    loop_count: int,
    logical_depth: int,
    unresolved_blocker_ids: Sequence[str],
    extra_recovery_authorized: bool,
) -> None:
    if mode == "Fast":
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization rejected: mode_fast_has_zero_followup_budget"
        )
    if mode == "Balanced":
        if logical_depth > 1:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization rejected: balanced_logical_depth_exceeded"
            )
        if loop_count > 2:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization rejected: balanced_followup_budget_exhausted"
            )
        if loop_count == 2 and not unresolved_blocker_ids:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization rejected: "
                "balanced_second_loop_requires_concrete_blocker"
            )
        return
    max_loops = 4 if extra_recovery_authorized else 3
    if logical_depth > max_loops:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization rejected: deep_logical_depth_exceeded"
        )
    if loop_count > max_loops:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization rejected: deep_followup_budget_exhausted"
        )


def _query_bundle(
    *,
    run_id: str,
    request_id: str,
    mode: str,
    current_answer_contract_ref: Mapping[str, Any],
    packet: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    logical_depth: int,
) -> dict[str, Any]:
    queries = []
    for index, proposal in enumerate(selected, start=1):
        query_text = _clean_text(
            proposal.get("proposed_query_hint") or proposal.get("search_direction"),
            limit=420,
        )
        if not query_text:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization requires tactical query text"
            )
        query_base = {
            "query_id": (
                "followup-query:"
                f"{_clean_token(proposal.get('proposal_digest'), limit=128)[:16]}:{index}"
            ),
            "query_text": query_text,
            "proposal_id": proposal.get("proposal_id"),
            "proposal_digest": proposal.get("proposal_digest"),
            "component_id": proposal.get("component_id"),
            "source_gap_kind": proposal.get("source_gap_kind"),
            "followup_intent_kind": proposal.get("followup_intent_kind"),
            "required_source_class_hint": proposal.get("required_source_class_hint"),
            "required_source_tier_hint": proposal.get("required_source_tier_hint"),
            "required_currentness_hint": proposal.get("required_currentness_hint"),
            "tactical_query_not_provider_dispatch": True,
        }
        queries.append({**query_base, "query_digest": _digest_json(query_base)})
    bundle_base = {
        "schema_version": FOLLOWUP_SEARCH_QUERY_BUNDLE_SCHEMA_VERSION,
        "bundle_kind": "followup_search_query_bundle",
        "durable_proposal_packet": False,
        "run_id": run_id,
        "request_id": request_id,
        "mode": mode,
        "logical_depth": logical_depth,
        "current_answer_contract_ref": _safe_mapping(current_answer_contract_ref),
        "followup_search_intent_packet_ref": _packet_ref(packet),
        "proposal_count": len(selected),
        "query_count": len(queries),
        "queries": queries,
        "query_fanout_allowed_inside_authorized_group": True,
        "live_dispatch_allowed": False,
    }
    bundle_digest = _digest_json(bundle_base)
    return {
        **bundle_base,
        "query_bundle_id": f"followup-query-bundle:{request_id}:{bundle_digest[:16]}",
        "query_bundle_digest": bundle_digest,
    }


def _work_identity(
    *,
    run_id: str,
    request_id: str,
    mode: str,
    current_answer_contract_ref: Mapping[str, Any],
    packet: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    query_bundle: Mapping[str, Any],
    logical_depth: int,
) -> dict[str, Any]:
    task_records = []
    for index, query in enumerate(_safe_list(query_bundle.get("queries")), start=1):
        task_base = {
            "search_task_id": (
                "followup-search-task:"
                f"{_clean_token(query.get('query_digest'), limit=128)[:16]}:{index}"
            ),
            "query_intent_id": query.get("query_id"),
            "query_text": query.get("query_text"),
            "component_id": query.get("component_id"),
            "source_gap_kind": query.get("source_gap_kind"),
            "required_source_class_hint": query.get("required_source_class_hint"),
            "execution_status": "not_dispatched_fixture_reentry_only",
        }
        task_records.append({**task_base, "task_digest": _digest_json(task_base)})
    work_base = {
        "schema_version": FOLLOWUP_SEARCH_WORK_IDENTITY_SCHEMA_VERSION,
        "owner": FOLLOWUP_SEARCH_AUTHORIZATION_OWNER,
        "run_id": run_id,
        "request_id": request_id,
        "mode": mode,
        "logical_depth": logical_depth,
        "current_answer_contract_ref": _safe_mapping(current_answer_contract_ref),
        "parent_current_contract_ref": _safe_mapping(current_answer_contract_ref),
        "contract_parent_kind": "current_answer_contract",
        "followup_search_intent_packet_ref": _packet_ref(packet),
        "authorized_proposal_refs": [_proposal_ref(item) for item in selected],
        "query_bundle_ref": {
            "query_bundle_id": query_bundle.get("query_bundle_id"),
            "query_bundle_digest": query_bundle.get("query_bundle_digest"),
            "query_count": query_bundle.get("query_count"),
        },
        "query_bundle": _safe_mapping(query_bundle),
        "search_task_records": task_records,
        "search_executor_handoff_style_identity": True,
        "actual_search_executor_handoff_state": False,
        "current_answer_contract_mutated": False,
        "live_dispatch_allowed": False,
        "fixture_reentry_only": True,
    }
    dedupe_key = _digest_json(
        {
            "contract": current_answer_contract_ref,
            "proposal_ids": [item.get("proposal_id") for item in selected],
            "queries": [item.get("query_digest") for item in task_records],
            "logical_depth": logical_depth,
        }
    )
    work_id = f"followup-search-work:{request_id}:{dedupe_key[:16]}"
    work_without_digest = {
        **work_base,
        "handoff_id": work_id,
        "dedupe_key": dedupe_key,
        "work_dedupe_key": dedupe_key,
    }
    work_digest = _digest_json(work_without_digest)
    return {
        **work_without_digest,
        "handoff_digest": work_digest,
        "work_digest": work_digest,
    }


def _reject_duplicate_work(
    existing_projection: Mapping[str, Any],
    work_identity: Mapping[str, Any],
) -> None:
    dedupe = _clean_token(work_identity.get("work_dedupe_key"), limit=128)
    for item in _safe_list(existing_projection.get("authorized_work_identities")):
        work = _safe_mapping(item)
        if dedupe and work.get("work_dedupe_key") == dedupe:
            raise FollowupSearchAuthorizationRuntimeError(
                "follow-up search authorization rejected: duplicate_work_identity"
            )


def _authorization_history_entry(state: Mapping[str, Any]) -> dict[str, Any]:
    work = _safe_mapping(state.get("authorized_work_identity"))
    bundle = _safe_mapping(state.get("query_bundle"))
    return {
        "authorization_id": state.get("authorization_id"),
        "authorization_digest": state.get("authorization_digest"),
        "authorized_action_id": state.get("authorized_action_id"),
        "mode": state.get("mode"),
        "logical_depth": state.get("logical_depth"),
        "proposal_packet_ref": _safe_mapping(state.get("proposal_packet_ref")),
        "authorized_proposal_refs": [
            _safe_mapping(item)
            for item in _safe_list(state.get("authorized_proposal_refs"))
        ],
        "query_bundle_id": bundle.get("query_bundle_id"),
        "query_bundle_digest": bundle.get("query_bundle_digest"),
        "query_count": bundle.get("query_count"),
        "handoff_id": work.get("handoff_id"),
        "handoff_digest": work.get("handoff_digest"),
        "work_dedupe_key": work.get("work_dedupe_key"),
        "fixture_reentry_only": True,
        "live_dispatch_allowed": False,
    }


def _work_projection(work: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(work)
    return {
        "schema_version": safe.get("schema_version"),
        "run_id": safe.get("run_id"),
        "request_id": safe.get("request_id"),
        "mode": safe.get("mode"),
        "logical_depth": safe.get("logical_depth"),
        "handoff_id": safe.get("handoff_id"),
        "handoff_digest": safe.get("handoff_digest"),
        "work_dedupe_key": safe.get("work_dedupe_key"),
        "current_answer_contract_ref": _safe_mapping(
            safe.get("current_answer_contract_ref")
        ),
        "contract_parent_kind": safe.get("contract_parent_kind"),
        "parent_current_contract_ref": _safe_mapping(
            safe.get("parent_current_contract_ref")
        ),
        "query_bundle_ref": _safe_mapping(safe.get("query_bundle_ref")),
        "search_task_records": [
            _safe_mapping(item)
            for item in _safe_list(safe.get("search_task_records"))
        ],
        "search_executor_handoff_style_identity": True,
        "actual_search_executor_handoff_state": False,
        "fixture_reentry_only": True,
        "live_dispatch_allowed": False,
    }


def _contract_ref_from_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    ref = _safe_mapping(contract)
    version = _clean_token(
        ref.get("accepted_contract_version")
        or ref.get("current_contract_version")
        or ref.get("contract_version"),
        limit=160,
    )
    digest = _clean_token(
        ref.get("accepted_contract_digest")
        or ref.get("current_contract_digest")
        or ref.get("contract_digest"),
        limit=128,
    )
    if not version or not digest:
        return {}
    return {
        "source": "current_answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _packet_ref(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": packet.get("packet_id"),
        "packet_digest": packet.get("packet_digest"),
        "schema_version": packet.get("schema_version"),
        "proposal_count": packet.get("proposal_count"),
    }


def _proposal_ref(proposal: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal_id": proposal.get("proposal_id"),
        "proposal_digest": proposal.get("proposal_digest"),
        "source_gap_id": proposal.get("source_gap_id"),
        "source_gap_kind": proposal.get("source_gap_kind"),
        "component_id": proposal.get("component_id"),
        "required_source_class_hint": proposal.get("required_source_class_hint"),
    }


def _mode_label(mode: Any) -> str:
    normalized = _clean_token(mode, limit=40)
    label = _MODE_LABELS.get(str(normalized or "").casefold())
    if not label:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization mode must be Fast, Balanced, or Deep"
        )
    return label


def _mode_budget(mode: str, extra_recovery_authorized: bool) -> dict[str, Any]:
    if mode == "Fast":
        return {"max_followup_loops": 0, "max_logical_depth": 0}
    if mode == "Balanced":
        return {
            "max_followup_loops": 2,
            "max_logical_depth": 1,
            "query_fanout_allowed_inside_authorized_group": True,
            "second_loop_requires_concrete_blocker": True,
        }
    return {
        "max_followup_loops": 4 if extra_recovery_authorized else 3,
        "max_logical_depth": 4 if extra_recovery_authorized else 3,
        "extra_recovery_authorized": bool(extra_recovery_authorized),
    }


def _validate_closed_flags(
    value: Mapping[str, Any],
    *,
    require_all: bool = True,
) -> None:
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if (require_all or key in value) and value.get(key) is not expected:
            raise FollowupSearchAuthorizationRuntimeError(
                f"follow-up search authorization must keep {key} false"
            )
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_FALSE_FLAGS.items():
        if key in flags and flags.get(key) is not expected:
            raise FollowupSearchAuthorizationRuntimeError(
                f"follow-up search authorization closed flag {key} must be false"
            )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise FollowupSearchAuthorizationRuntimeError(
            "follow-up search authorization opens closed surfaces: "
            + ", ".join(dangerous)
        )


def _reject_forbidden_surface_claims(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    raw_or_private = sorted(key for key in keys if _is_raw_or_private_key(key))
    if raw_or_private:
        raise FollowupSearchAuthorizationRuntimeError(
            f"{context} contains raw/private fields: " + ", ".join(raw_or_private)
        )
    authority = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if authority:
        raise FollowupSearchAuthorizationRuntimeError(
            f"{context} includes closed authority fields: " + ", ".join(authority)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise FollowupSearchAuthorizationRuntimeError(
            f"{context} opens closed runtime surfaces: " + ", ".join(dangerous)
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _normalize_key(key)
            if token in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(token)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


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


def _is_raw_or_private_key(key: str) -> bool:
    normalized = _normalize_key(key)
    return normalized.startswith("raw_") or normalized in _RAW_OR_PRIVATE_KEYS


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return {}
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    safe = _json_safe(list(value))
    return list(safe) if isinstance(safe, list) else []


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=1_000)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if not clean_key:
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict(), depth=depth + 1)
    return _clean_text(value, limit=300)


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise FollowupSearchAuthorizationRuntimeError(message)
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _text_list(value: Any, *, limit: int = 160) -> list[str]:
    if isinstance(value, str):
        text = _clean_token(value, limit=limit)
        return [text] if text else []
    if isinstance(value, bytes) or not isinstance(value, Sequence):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_token(item, limit=limit)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed >= 0 else default


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "FOLLOWUP_SEARCH_AUTHORIZATION_OBSERVATION_SCHEMA_VERSION",
    "FOLLOWUP_SEARCH_AUTHORIZATION_OWNER",
    "FOLLOWUP_SEARCH_AUTHORIZATION_REASON",
    "FOLLOWUP_SEARCH_AUTHORIZATION_SCHEMA_VERSION",
    "FOLLOWUP_SEARCH_AUTHORIZATION_STAGE",
    "FOLLOWUP_SEARCH_AUTHORIZATION_TRACE_KEY",
    "FOLLOWUP_SEARCH_QUERY_BUNDLE_SCHEMA_VERSION",
    "FOLLOWUP_SEARCH_WORK_IDENTITY_SCHEMA_VERSION",
    "FollowupSearchAuthorizationRuntimeError",
    "build_followup_search_authorization_action_inputs",
    "build_followup_search_authorization_observation_payload",
    "build_followup_search_authorization_projection",
    "build_followup_search_authorization_state",
]
