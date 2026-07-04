"""Shared model-assisted planning reducer for single-relation dogfood.

FastModel may propose planning metadata only. This module owns the shared
proposal form, strict-route adapter seam, and deterministic reducer used by the
ordinary generic single-relation dogfood path. It imports no provider client,
loads no credentials, stores no raw prompt/model output/provider payload, and
creates no evidence, support, source authority, citations, answer text, FAP, or
Author material.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

MODEL_ASSISTED_SINGLE_RELATION_PLANNING_PHASE = (
    "MODEL-ASSISTED-SINGLE-RELATION-PLANNING-01"
)
MODEL_ASSISTED_SINGLE_RELATION_PLANNING_SCHEMA_VERSION = (
    "model_assisted_single_relation_planning_v1"
)

PLANNING_CONTEXT_INITIAL_SINGLE_RELATION = "initial_single_relation_planning"
PLANNING_CONTEXT_ACQUISITION = "acquisition_planning"
PLANNING_CONTEXT_DISAMBIGUATION = "disambiguation_planning"
PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY = (
    "source_of_record_recovery_planning"
)
ALLOWED_PLANNING_CONTEXT_KINDS = frozenset(
    {
        PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        PLANNING_CONTEXT_ACQUISITION,
        PLANNING_CONTEXT_DISAMBIGUATION,
        PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY,
    }
)

MODEL_ASSISTED_PLANNING_MODEL_TASK = (
    "model_assisted_single_relation_planning"
)
MODEL_ASSISTED_PLANNING_PRODUCT_MODEL_ROLE = "fast"

BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE = (
    "BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE"
)
BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_CALL_FAILED = (
    "BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_CALL_FAILED"
)
BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID = (
    "BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID"
)

REDUCED_STATUS_CLEAR_SINGLE_RELATION = "clear_single_relation"
REDUCED_STATUS_AMBIGUOUS_NEEDS_DISAMBIGUATION = (
    "ambiguous_needs_disambiguation"
)
REDUCED_STATUS_LIKELY_MULTI_COMPONENT_CURRENTLY_CLOSED = (
    "likely_multi_component_currently_closed"
)
REDUCED_STATUS_SOURCE_CLASS_UNCERTAIN = "source_class_uncertain"
REDUCED_STATUS_OFFICIAL_ARTIFACT_UNCERTAIN = "official_artifact_uncertain"
REDUCED_STATUS_ACQUISITION_HYPOTHESES_AVAILABLE = (
    "acquisition_hypotheses_available"
)
REDUCED_STATUS_RECOVERY_HYPOTHESES_AVAILABLE = (
    "recovery_hypotheses_available"
)
REDUCED_STATUS_BLOCKED_MODEL_OUTPUT_INVALID = "blocked_model_output_invalid"
ALLOWED_REDUCED_STATUSES = frozenset(
    {
        REDUCED_STATUS_CLEAR_SINGLE_RELATION,
        REDUCED_STATUS_AMBIGUOUS_NEEDS_DISAMBIGUATION,
        REDUCED_STATUS_LIKELY_MULTI_COMPONENT_CURRENTLY_CLOSED,
        REDUCED_STATUS_SOURCE_CLASS_UNCERTAIN,
        REDUCED_STATUS_OFFICIAL_ARTIFACT_UNCERTAIN,
        REDUCED_STATUS_ACQUISITION_HYPOTHESES_AVAILABLE,
        REDUCED_STATUS_RECOVERY_HYPOTHESES_AVAILABLE,
        REDUCED_STATUS_BLOCKED_MODEL_OUTPUT_INVALID,
    }
)

_ALLOWED_COMPONENT_COUNT_HYPOTHESES = frozenset(
    {
        "single",
        "likely_single",
        "uncertain",
        "multiple",
        "likely_multi_component",
    }
)
_ALLOWED_DISAMBIGUATION_STATUSES = frozenset(
    {
        "clear",
        "ambiguous_needs_disambiguation",
        "uncertain",
        "not_applicable",
    }
)
_ALLOWED_VALUE_TOKEN_KINDS = frozenset(
    {
        "currency",
        "date_like",
        "identifier",
        "number",
        "percentage",
        "text_label",
        "unknown",
    }
)
_CLOSED_SURFACE_FLAGS = frozenset(
    {
        "answer_text_created",
        "author_input_created",
        "citation_eligibility_created",
        "dprime_support_relation_created",
        "evidence_created",
        "final_answer_packet_created",
        "multi_component_execution_opened",
        "product_correctness_claimed",
        "provider_routing_changed",
        "raw_model_response_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "runkernel_dag_scheduling_opened",
        "semantic_support_created",
        "source_authority_decided",
        "source_obligation_satisfaction_created",
        "sufficiency_or_readiness_decided",
    }
)
_RAW_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "cache",
        "cache_row",
        "cookie",
        "db",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
        "headers",
        "html",
        "log",
        "logs",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "private_logs",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_html",
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
_AUTHORITY_KEYS = frozenset(
    {
        "answer",
        "answer_text",
        "author",
        "author_input",
        "citation",
        "citation_eligible",
        "citation_eligibility",
        "citations",
        "component_coverage",
        "correctness",
        "dprime_support_relation",
        "evidence",
        "final_answer",
        "final_answer_packet",
        "fap",
        "product_correctness",
        "readiness",
        "run_kernel_support_admission",
        "semantic_observation",
        "semantic_support",
        "source_authority",
        "source_authority_decision",
        "source_obligation_satisfaction",
        "source_obligation_satisfied",
        "sufficiency",
        "validated_support_proposal",
    }
)
_DANGEROUS_TRUE_KEYS = _AUTHORITY_KEYS | _CLOSED_SURFACE_FLAGS | frozenset(
    {
        "answer_created",
        "author_created",
        "citation_created",
        "evidence_admitted",
        "evidence_acquired",
        "model_output_is_evidence",
        "planner_output_citation_eligible",
        "provider_called",
        "search_called",
        "source_authority_adjudicated",
        "source_obligation_satisfied",
        "support_claimed",
    }
)
_PRIVATE_VALUE_MARKERS = frozenset(
    {
        "api_key",
        "authorization:",
        "bearer ",
        "private_sentinel",
        "provider_payload",
        "raw_model_response",
        "raw_private",
        "raw_prompt",
        "raw_provider",
        "secret",
        "sk-",
    }
)

MODEL_ASSISTED_SINGLE_RELATION_PLANNING_SYSTEM_PROMPT = (
    "You are a planning-only assistant for ScryRaven's single-relation "
    "dogfood path. Return one JSON object matching the requested proposal "
    "form. Do not answer the user question, do not cite sources, do not decide "
    "source authority, and do not claim evidence, support, sufficiency, "
    "citation eligibility, source-obligation satisfaction, FinalAnswerPacket, "
    "Author, or product correctness."
)

ModelAssistedPlannerCallable = Callable[..., Any]


class ModelAssistedSingleRelationPlanningError(ValueError):
    """Raised when model-assisted planning must fail closed."""

    def __init__(self, blocker: str, detail: str) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail


def build_model_assisted_single_relation_planning_packet(
    *,
    planning_context_kind: str,
    context_state: Mapping[str, Any],
    planner_callable: ModelAssistedPlannerCallable | None,
    strict_model_route_ref: Mapping[str, Any] | None,
    clean_json_response: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Invoke a strict injected planner once and return a reduced packet."""

    context_kind = _planning_context_kind(planning_context_kind)
    safe_context = sanitize_planning_context(context_state)
    route_validation = validate_model_assisted_planning_strict_route(
        strict_model_route_ref
    )
    if planner_callable is None or not route_validation["valid"]:
        return _blocked_packet(
            planning_context_kind=context_kind,
            context_state=safe_context,
            blocker=BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE,
            detail=(
                "No strict reusable FastModel planning route is configured for "
                "one-call model-assisted planning."
            ),
            route_validation=route_validation,
            model_calls_attempted=0,
            model_calls_completed=0,
        )

    prompt = _build_planning_prompt(
        planning_context_kind=context_kind,
        context_state=safe_context,
    )
    prompt_ref = _prompt_ref(prompt)
    try:
        raw = planner_callable(
            prompt,
            MODEL_ASSISTED_SINGLE_RELATION_PLANNING_SYSTEM_PROMPT,
            planning_context_kind=context_kind,
            strict_model_route_ref=dict(route_validation["route_ref"]),
            provider=route_validation["route_ref"].get("configured_fast_provider"),
            model=route_validation["route_ref"].get("configured_fast_model"),
            effort="low",
            require_json=True,
            use_reasoning=False,
            max_tokens=1800,
        )
    except Exception as exc:
        return _blocked_packet(
            planning_context_kind=context_kind,
            context_state=safe_context,
            blocker=BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_CALL_FAILED,
            detail=(
                "Strict FastModel planning callable failed closed: "
                f"{type(exc).__name__}."
            ),
            route_validation=route_validation,
            model_calls_attempted=1,
            model_calls_completed=0,
            prompt_ref=prompt_ref,
        )

    try:
        parsed = _parse_model_output(raw, clean_json_response=clean_json_response)
        reduced = reduce_model_assisted_single_relation_proposal(
            parsed,
            planning_context_kind=context_kind,
            context_state=safe_context,
        )
    except ModelAssistedSingleRelationPlanningError as exc:
        return _blocked_packet(
            planning_context_kind=context_kind,
            context_state=safe_context,
            blocker=exc.blocker,
            detail=exc.detail,
            route_validation=route_validation,
            model_calls_attempted=1,
            model_calls_completed=1,
            prompt_ref=prompt_ref,
        )

    reduced.update(
        {
            "strict_model_route_ref": dict(route_validation["route_ref"]),
            "strict_model_route_valid": True,
            "planner_callable_invoked": True,
            "model_calls_attempted": 1,
            "model_calls_completed": 1,
            "planning_input_ref": prompt_ref,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        }
    )
    return _finalize_packet(reduced)


def validate_model_assisted_planning_strict_route(
    route_ref: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a safe validation ref for a reusable strict FastModel route."""

    route = _safe_mapping(route_ref)
    safe_route = {
        "model_task": _clean_text(route.get("model_task"), limit=120),
        "product_model_role": _normalize_token(route.get("product_model_role")),
        "product_route_kind": _clean_text(route.get("product_route_kind"), limit=160),
        "configured_fast_provider": _clean_text(
            route.get("configured_fast_provider") or route.get("fast_provider"),
            limit=80,
        ),
        "configured_fast_model": _clean_text(
            route.get("configured_fast_model") or route.get("fast_model"),
            limit=120,
        ),
        "configured_local_url_present": route.get("configured_local_url_present")
        is True,
        "configured_local_url_posture": _clean_text(
            route.get("configured_local_url_posture"),
            limit=80,
        ),
        "max_model_calls": _bounded_int(
            route.get("max_model_calls") or route.get("max_provider_attempts"),
            default=0,
        ),
        "retry_policy": _normalize_token(route.get("retry_policy")),
        "fallback_policy": _normalize_token(route.get("fallback_policy")),
        "timeout_policy": _normalize_token(route.get("timeout_policy")),
        "provider_switching_allowed": route.get("provider_switching_allowed")
        is True,
        "strict_one_shot": route.get("strict_one_shot") is True,
        "call_count": _bounded_int(route.get("call_count"), default=0),
        "raw_prompt_retained": _flag(route, "raw_prompt_retained", "raw_prompt_retention"),
        "raw_model_response_retained": _flag(
            route,
            "raw_model_response_retained",
            "raw_model_response_retention",
        ),
        "provider_payload_retained": _flag(
            route,
            "provider_payload_retained",
            "provider_payload_retention",
            "raw_provider_payload_retained",
        ),
    }
    blockers: list[str] = []
    if safe_route["model_task"] != MODEL_ASSISTED_PLANNING_MODEL_TASK:
        blockers.append("route model_task is not model-assisted planning")
    if safe_route["product_model_role"] != MODEL_ASSISTED_PLANNING_PRODUCT_MODEL_ROLE:
        blockers.append("route product_model_role is not fast")
    if safe_route["max_model_calls"] != 1:
        blockers.append("route must cap model calls at exactly one")
    if safe_route["retry_policy"] != "forbidden":
        blockers.append("route retries are not forbidden")
    if safe_route["fallback_policy"] != "forbidden":
        blockers.append("route fallback is not forbidden")
    if safe_route["provider_switching_allowed"]:
        blockers.append("route allows provider switching")
    if not safe_route["strict_one_shot"]:
        blockers.append("route does not prove strict_one_shot")
    if safe_route["call_count"] != 0:
        blockers.append("route call_count must start at zero")
    if safe_route["raw_prompt_retained"]:
        blockers.append("route may retain raw prompts")
    if safe_route["raw_model_response_retained"]:
        blockers.append("route may retain raw model responses")
    if safe_route["provider_payload_retained"]:
        blockers.append("route may retain provider payloads")
    _reject_raw_private_material(safe_route)
    return {
        "valid": not blockers,
        "route_ref": safe_route,
        "blockers": blockers,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "provider_payload_retained": False,
    }


def sanitize_planning_context(context_state: Mapping[str, Any]) -> dict[str, Any]:
    """Return a bounded safe context copy suitable for transient prompting."""

    safe = _json_safe(_safe_mapping(context_state), depth=0)
    if not isinstance(safe, Mapping):
        safe = {}
    _reject_raw_private_material(safe)
    return dict(safe)


def reduce_model_assisted_single_relation_proposal(
    proposal: Mapping[str, Any],
    *,
    planning_context_kind: str,
    context_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministically reduce one model proposal to planning metadata."""

    context_kind = _planning_context_kind(planning_context_kind)
    safe_context = sanitize_planning_context(context_state or {})
    model_output = _safe_mapping(proposal)
    if not model_output:
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "FastModel planning proposal must be a JSON object.",
        )
    _reject_raw_private_material(model_output)
    _reject_closed_surface_claims(model_output)

    proposed_kind = _clean_text(
        model_output.get("planning_context_kind"),
        limit=80,
    )
    if proposed_kind and proposed_kind != context_kind:
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "FastModel proposal planning_context_kind did not match request.",
        )

    component_hypothesis = _component_count_hypothesis(
        model_output.get("component_count_hypothesis")
    )
    disambiguation_status = _allowed_enum(
        model_output.get("disambiguation_status"),
        allowed=_ALLOWED_DISAMBIGUATION_STATUSES,
        default="uncertain",
    )
    reduced_status = _reduced_status(
        model_output.get("reduced_status") or model_output.get("status"),
        context_kind=context_kind,
        component_hypothesis=component_hypothesis,
        disambiguation_status=disambiguation_status,
        proposal=model_output,
    )
    official_artifact_hypotheses = _text_list(
        model_output.get("official_or_source_of_record_artifact_hypotheses"),
        item_limit=180,
        count_limit=6,
    )
    acquisition_query_variants = _text_list(
        model_output.get("acquisition_query_variants"),
        item_limit=220,
        count_limit=5,
    )
    preferred_acquisition_query = _clean_text(
        model_output.get("preferred_acquisition_query"),
        limit=220,
    )
    recovery_query_variants = _text_list(
        model_output.get("recovery_query_variants"),
        item_limit=240,
        count_limit=5,
    )
    preferred_recovery_query = _clean_text(
        model_output.get("preferred_recovery_query"),
        limit=240,
    )
    packet = {
        "schema_version": MODEL_ASSISTED_SINGLE_RELATION_PLANNING_SCHEMA_VERSION,
        "phase_name": MODEL_ASSISTED_SINGLE_RELATION_PLANNING_PHASE,
        "planning_context_kind": context_kind,
        "shared_planner_surface": (
            "core.model_assisted_single_relation_planning."
            "build_model_assisted_single_relation_planning_packet"
        ),
        "reduced_status": reduced_status,
        "proposal_reduced": True,
        "normalized_user_question": _clean_text(
            model_output.get("normalized_user_question")
            or safe_context.get("normalized_user_question")
            or safe_context.get("sanitized_query"),
            limit=500,
        ),
        "component_count_hypothesis": component_hypothesis,
        "single_relation_lane_eligible": _optional_bool(
            model_output.get("single_relation_lane_eligible")
        ),
        "relation_or_component_hypothesis": _clean_text(
            model_output.get("relation_or_component_hypothesis"),
            limit=300,
        ),
        "likely_fact_kind": _clean_text(model_output.get("likely_fact_kind"), limit=80),
        "source_obligation_hypothesis": _clean_text(
            model_output.get("source_obligation_hypothesis"),
            limit=320,
        ),
        "expected_source_class": _clean_text(
            model_output.get("expected_source_class"),
            limit=160,
        ),
        "source_class_uncertainty": _clean_text(
            model_output.get("source_class_uncertainty"),
            limit=160,
        ),
        "official_or_source_of_record_artifact_hypotheses": (
            official_artifact_hypotheses
        ),
        "likely_official_domains": _domain_list(
            model_output.get("likely_official_domains")
        ),
        "likely_official_path_or_page_hints": _text_list(
            model_output.get("likely_official_path_or_page_hints"),
            item_limit=160,
            count_limit=6,
        ),
        "acquisition_query_variants": acquisition_query_variants,
        "preferred_acquisition_query": preferred_acquisition_query,
        "disambiguation_status": disambiguation_status,
        "disambiguation_reason": _clean_text(
            model_output.get("disambiguation_reason"),
            limit=220,
        ),
        "disambiguation_questions_or_hints": _text_list(
            model_output.get("disambiguation_questions_or_hints"),
            item_limit=200,
            count_limit=5,
        ),
        "recovery_query_variants": recovery_query_variants,
        "preferred_recovery_query": preferred_recovery_query,
        "recovery_reasoning_summary": _clean_text(
            model_output.get("recovery_reasoning_summary"),
            limit=360,
        ),
        "answer_bearing_material_criteria": _text_list(
            model_output.get("answer_bearing_material_criteria"),
            item_limit=220,
            count_limit=6,
        ),
        "answer_bearing_anchor_terms": _text_list(
            model_output.get("answer_bearing_anchor_terms"),
            item_limit=120,
            count_limit=10,
        ),
        "expected_value_token_kinds": _value_token_kinds(
            model_output.get("expected_value_token_kinds")
        ),
        "currentness_hints": _text_list(
            model_output.get("currentness_hints"),
            item_limit=140,
            count_limit=5,
        ),
        "uncertainty_notes": _text_list(
            model_output.get("uncertainty_notes"),
            item_limit=220,
            count_limit=5,
        ),
        "planner_caveats": _text_list(
            model_output.get("planner_caveats"),
            item_limit=220,
            count_limit=5,
        ),
        "planner_output_is_evidence": False,
        "planner_output_citation_eligible": False,
        "planner_output_satisfies_source_obligation": False,
        "planner_output_decides_source_authority": False,
        "planner_output_creates_answer_text": False,
        "planner_output_claims_correctness": False,
        "closed_surface_flags": default_closed_surface_flags(),
        "raw_private_retention_flags": default_raw_private_retention_flags(),
        "unknown_fields_dropped": True,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    return _finalize_packet(_without_empty(packet))


def default_closed_surface_flags() -> dict[str, bool]:
    """Return required false closed-surface flags for reduced packets."""

    return {key: False for key in sorted(_CLOSED_SURFACE_FLAGS)}


def default_raw_private_retention_flags() -> dict[str, bool]:
    """Return required false raw/private retention flags."""

    return {
        "db_cache_rows_retained": False,
        "full_trace_retained": False,
        "private_logs_retained": False,
        "raw_model_response_retained": False,
        "raw_prompt_retained": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_source_content_retained": False,
    }


def _build_planning_prompt(
    *,
    planning_context_kind: str,
    context_state: Mapping[str, Any],
) -> str:
    form = {
        "planning_context_kind": planning_context_kind,
        "normalized_user_question": "",
        "component_count_hypothesis": "single | likely_single | uncertain | likely_multi_component",
        "single_relation_lane_eligible": True,
        "relation_or_component_hypothesis": "",
        "likely_fact_kind": "",
        "source_obligation_hypothesis": "",
        "expected_source_class": "",
        "source_class_uncertainty": "",
        "official_or_source_of_record_artifact_hypotheses": [],
        "likely_official_domains": [],
        "likely_official_path_or_page_hints": [],
        "acquisition_query_variants": [],
        "preferred_acquisition_query": "",
        "disambiguation_status": "clear | ambiguous_needs_disambiguation | uncertain",
        "disambiguation_reason": "",
        "disambiguation_questions_or_hints": [],
        "recovery_query_variants": [],
        "preferred_recovery_query": "",
        "recovery_reasoning_summary": "",
        "answer_bearing_material_criteria": [],
        "answer_bearing_anchor_terms": [],
        "expected_value_token_kinds": [],
        "currentness_hints": [],
        "uncertainty_notes": [],
        "planner_caveats": [],
        "reduced_status": "clear_single_relation",
    }
    payload = {
        "schema_version": MODEL_ASSISTED_SINGLE_RELATION_PLANNING_SCHEMA_VERSION,
        "task": MODEL_ASSISTED_PLANNING_MODEL_TASK,
        "planning_context_kind": planning_context_kind,
        "rules": [
            "Planning metadata only; do not answer the question.",
            "Do not claim evidence, support, authority, citation eligibility, sufficiency, FAP, Author, or correctness.",
            "Preserve uncertainty and partial hypotheses.",
            "Return only the JSON object.",
        ],
        "proposal_form": form,
        "safe_context_state": context_state,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _parse_model_output(
    raw: Any,
    *,
    clean_json_response: Callable[[str], str] | None,
) -> Mapping[str, Any]:
    if isinstance(raw, Mapping):
        return raw
    text = str(raw or "")
    if clean_json_response is not None:
        text = clean_json_response(text)
    try:
        parsed = json.loads(text)
    except Exception as exc:
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "FastModel planning output was not valid JSON.",
        ) from exc
    if not isinstance(parsed, Mapping):
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "FastModel planning output must be a JSON object.",
        )
    return parsed


def _blocked_packet(
    *,
    planning_context_kind: str,
    context_state: Mapping[str, Any],
    blocker: str,
    detail: str,
    route_validation: Mapping[str, Any],
    model_calls_attempted: int,
    model_calls_completed: int,
    prompt_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = {
        "schema_version": MODEL_ASSISTED_SINGLE_RELATION_PLANNING_SCHEMA_VERSION,
        "phase_name": MODEL_ASSISTED_SINGLE_RELATION_PLANNING_PHASE,
        "planning_context_kind": planning_context_kind,
        "shared_planner_surface": (
            "core.model_assisted_single_relation_planning."
            "build_model_assisted_single_relation_planning_packet"
        ),
        "reduced_status": REDUCED_STATUS_BLOCKED_MODEL_OUTPUT_INVALID,
        "blocker": blocker,
        "blocker_detail": detail,
        "proposal_reduced": False,
        "normalized_user_question": _clean_text(
            context_state.get("normalized_user_question")
            or context_state.get("sanitized_query"),
            limit=500,
        ),
        "strict_model_route_valid": route_validation.get("valid") is True,
        "strict_model_route_ref": _safe_mapping(route_validation.get("route_ref")),
        "strict_model_route_blockers": list(
            _safe_sequence(route_validation.get("blockers"))
        ),
        "planner_callable_invoked": model_calls_attempted > 0,
        "model_calls_attempted": model_calls_attempted,
        "model_calls_completed": model_calls_completed,
        "planning_input_ref": dict(prompt_ref or {}),
        "planner_output_is_evidence": False,
        "planner_output_citation_eligible": False,
        "planner_output_satisfies_source_obligation": False,
        "planner_output_decides_source_authority": False,
        "planner_output_creates_answer_text": False,
        "planner_output_claims_correctness": False,
        "closed_surface_flags": default_closed_surface_flags(),
        "raw_private_retention_flags": default_raw_private_retention_flags(),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    return _finalize_packet(_without_empty(packet))


def _finalize_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    safe = _json_safe(packet, depth=0)
    if not isinstance(safe, Mapping):
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "Reduced FastModel planning packet was not an object.",
        )
    out = dict(safe)
    _reject_raw_private_material(out)
    _require_false_flags(_safe_mapping(out.get("closed_surface_flags")))
    _require_false_flags(_safe_mapping(out.get("raw_private_retention_flags")))
    for key in (
        "planner_output_is_evidence",
        "planner_output_citation_eligible",
        "planner_output_satisfies_source_obligation",
        "planner_output_decides_source_authority",
        "planner_output_creates_answer_text",
        "planner_output_claims_correctness",
        "raw_prompt_retained",
        "raw_model_response_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    ):
        if out.get(key) is not False:
            raise ModelAssistedSingleRelationPlanningError(
                BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
                f"Reduced FastModel planning packet opened {key}.",
            )
    out["packet_digest"] = _digest_json({k: v for k, v in out.items() if k != "packet_digest"})
    return out


def _planning_context_kind(value: Any) -> str:
    text = _clean_text(value, limit=100) or ""
    if text not in ALLOWED_PLANNING_CONTEXT_KINDS:
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "Unknown model-assisted planning_context_kind.",
        )
    return text


def _reduced_status(
    value: Any,
    *,
    context_kind: str,
    component_hypothesis: str,
    disambiguation_status: str,
    proposal: Mapping[str, Any],
) -> str:
    explicit = _clean_text(value, limit=80)
    if explicit:
        if explicit not in ALLOWED_REDUCED_STATUSES:
            raise ModelAssistedSingleRelationPlanningError(
                BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
                "FastModel proposal emitted unsupported reduced_status.",
            )
        return explicit
    if component_hypothesis == "likely_multi_component":
        return REDUCED_STATUS_LIKELY_MULTI_COMPONENT_CURRENTLY_CLOSED
    if disambiguation_status == REDUCED_STATUS_AMBIGUOUS_NEEDS_DISAMBIGUATION:
        return REDUCED_STATUS_AMBIGUOUS_NEEDS_DISAMBIGUATION
    if context_kind == PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY and (
        proposal.get("preferred_recovery_query")
        or proposal.get("recovery_query_variants")
    ):
        return REDUCED_STATUS_RECOVERY_HYPOTHESES_AVAILABLE
    if proposal.get("source_class_uncertainty"):
        return REDUCED_STATUS_SOURCE_CLASS_UNCERTAIN
    if proposal.get("official_or_source_of_record_artifact_hypotheses") or proposal.get(
        "preferred_acquisition_query"
    ):
        return REDUCED_STATUS_ACQUISITION_HYPOTHESES_AVAILABLE
    return REDUCED_STATUS_CLEAR_SINGLE_RELATION


def _component_count_hypothesis(value: Any) -> str:
    if isinstance(value, bool):
        return "uncertain"
    if isinstance(value, int):
        return "single" if value == 1 else "likely_multi_component"
    text = _normalize_token(value)
    if text in {"1", "one"}:
        return "single"
    if text in {"2", "two", "multi", "multiple_components", "multi_component"}:
        return "likely_multi_component"
    if text in _ALLOWED_COMPONENT_COUNT_HYPOTHESES:
        return text
    return "uncertain"


def _allowed_enum(value: Any, *, allowed: frozenset[str], default: str) -> str:
    text = _normalize_token(value)
    return text if text in allowed else default


def _value_token_kinds(value: Any) -> list[str]:
    items = _text_list(value, item_limit=40, count_limit=6)
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        token = _normalize_token(item)
        if token in _ALLOWED_VALUE_TOKEN_KINDS and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _domain_list(value: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in _safe_sequence(value):
        domain = _clean_domain(item)
        if domain and domain not in seen:
            seen.add(domain)
            out.append(domain)
    return out[:6]


def _clean_domain(value: Any) -> str | None:
    text = _clean_text(value, limit=260)
    if not text:
        return None
    parsed = urlparse(text if "://" in text else f"https://{text}")
    domain = (parsed.netloc or parsed.path).casefold().strip("/")
    if domain.startswith("www."):
        domain = domain[4:]
    if not domain or "/" in domain or " " in domain:
        return None
    return domain


def _text_list(value: Any, *, item_limit: int, count_limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in _safe_sequence(value):
        text = _clean_text(item, limit=item_limit)
        key = text.casefold() if text else ""
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out[:count_limit]


def _reject_raw_private_material(value: Any) -> None:
    keys = _collect_keys(value)
    forbidden: list[str] = []
    for key in sorted(keys):
        if key == "raw_private_retention_flags":
            flags = _safe_mapping(_first_normalized_key_value(value, key))
            if not flags or any(item is not False for item in flags.values()):
                forbidden.append(key)
            continue
        if key in _RAW_PRIVATE_KEYS:
            if key.startswith("raw_") and _all_key_values_false(value, key):
                continue
            forbidden.append(key)
        elif key.startswith("raw_") and not _all_key_values_false(value, key):
            forbidden.append(key)
    if forbidden:
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "FastModel planning material contains raw/private fields: "
            + ", ".join(forbidden),
        )
    markers = sorted(_private_value_markers(value))
    if markers:
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "FastModel planning material contains private-looking values: "
            + ", ".join(markers),
        )


def _reject_closed_surface_claims(value: Any) -> None:
    claims = sorted(_closed_surface_claims(value))
    if claims:
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "FastModel proposal attempts closed-surface claims: "
            + ", ".join(claims),
        )


def _closed_surface_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(normalized)
            if (
                normalized in _AUTHORITY_KEYS
                and item not in (False, None, "", (), [], {})
            ):
                found.add(normalized)
            found.update(_closed_surface_claims(item))
    elif isinstance(value, list | tuple):
        for item in value:
            found.update(_closed_surface_claims(item))
    return found


def _require_false_flags(flags: Mapping[str, Any]) -> None:
    for key, value in flags.items():
        if value is not False:
            raise ModelAssistedSingleRelationPlanningError(
                BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
                f"Reduced FastModel planning flag must remain false: {key}.",
            )


def _private_value_markers(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for item in value.values():
            found.update(_private_value_markers(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_private_value_markers(item))
    elif isinstance(value, str):
        lowered = value.casefold()
        for marker in _PRIVATE_VALUE_MARKERS:
            if marker in lowered:
                found.add(marker)
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


def _all_key_values_false(value: Any, normalized_key: str) -> bool:
    values = _normalized_key_values(value, normalized_key)
    return bool(values) and all(item is False for item in values)


def _first_normalized_key_value(value: Any, normalized_key: str) -> Any:
    values = _normalized_key_values(value, normalized_key)
    return values[0] if values else None


def _normalized_key_values(value: Any, normalized_key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_key(key) == normalized_key:
                found.append(item)
            found.extend(_normalized_key_values(item, normalized_key))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.extend(_normalized_key_values(item, normalized_key))
    return found


def _prompt_ref(prompt: str) -> dict[str, Any]:
    return {
        "planning_input_digest": sha256(prompt.encode("utf-8")).hexdigest(),
        "planning_input_char_count": len(prompt),
        "raw_prompt_retained": False,
    }


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _flag(value: Mapping[str, Any], *keys: str) -> bool:
    return any(value.get(key) is True for key in keys)


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
    if not text:
        return None
    if _private_value_markers(text):
        raise ModelAssistedSingleRelationPlanningError(
            BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID,
            "FastModel planning text contains private-looking material.",
        )
    return text[:limit]


def _clean_key(value: Any, *, limit: int = 120) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _normalize_token(value: Any) -> str:
    return _normalize_key(value)


def _bounded_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_key(key, limit=120)
            if not clean_key:
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, list | tuple | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items[:20]]
    return _clean_text(value, limit=300)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ALLOWED_PLANNING_CONTEXT_KINDS",
    "BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_CALL_FAILED",
    "BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID",
    "BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE",
    "MODEL_ASSISTED_PLANNING_MODEL_TASK",
    "MODEL_ASSISTED_PLANNING_PRODUCT_MODEL_ROLE",
    "MODEL_ASSISTED_SINGLE_RELATION_PLANNING_PHASE",
    "MODEL_ASSISTED_SINGLE_RELATION_PLANNING_SCHEMA_VERSION",
    "PLANNING_CONTEXT_ACQUISITION",
    "PLANNING_CONTEXT_DISAMBIGUATION",
    "PLANNING_CONTEXT_INITIAL_SINGLE_RELATION",
    "PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY",
    "ModelAssistedSingleRelationPlanningError",
    "build_model_assisted_single_relation_planning_packet",
    "default_closed_surface_flags",
    "default_raw_private_retention_flags",
    "reduce_model_assisted_single_relation_proposal",
    "sanitize_planning_context",
    "validate_model_assisted_planning_strict_route",
]
