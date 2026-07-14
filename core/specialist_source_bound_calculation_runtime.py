"""RunKernel-reduced Specialist source-bound calculation runtime.

This module implements the first narrow Specialist MVP: deterministic arithmetic
over already source-bound numeric inputs. It records calculation posture only.
It does not call models, providers, search, retrieval, fetch/read, execute
arbitrary code, reduce ComponentCoverage, decide Sufficiency, create
FinalAnswerPacket state, create Author input, create citations, satisfy source
obligations, mutate current_answer_contract, or claim product correctness.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

SPECIALIST_SOURCE_BOUND_CALCULATION_SCHEMA_VERSION = (
    "specialist_source_bound_calculation_ag_specialist_source_bound_calculation_01_v1"
)
SPECIALIST_SOURCE_BOUND_CALCULATION_ACTION_SCHEMA_VERSION = (
    "specialist_source_bound_calculation_action_ag_specialist_source_bound_calculation_01_v1"
)
SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE = "specialist_source_bound_calculation"
SPECIALIST_SOURCE_BOUND_CALCULATION_REASON = (
    "specialist_source_bound_calculation_from_runkernel_reduced_record"
)
SPECIALIST_SOURCE_BOUND_CALCULATION_TRACE_KEY = (
    "specialist_source_bound_calculation"
)
SPECIALIST_SOURCE_BOUND_CALCULATION_OWNER = (
    "RunKernel.SpecialistSourceBoundCalculation"
)
SPECIALIST_SOURCE_BOUND_CALCULATION_HELPER = (
    "specialist_source_bound_calculation_runtime_ag_specialist_source_bound_calculation_01"
)

SUPPORTED_OPERATORS = frozenset(
    {
        "sum",
        "difference",
        "product",
        "ratio",
        "percentage",
        "percentage_point_difference",
        "simple_rate",
        "weighted_average",
    }
)
CALCULATION_STATUSES = frozenset(
    {"computed", "blocked", "contested", "invalid_input", "not_applicable"}
)
_BAD_CURRENTNESS = frozenset(
    {"stale", "stale_or_unknown", "unknown", "currentness_unknown"}
)
_WEAK_SOURCE_CLASSES = frozenset(
    {
        "blog",
        "forum",
        "social_media",
        "unknown",
        "unvetted_secondary",
        "weak_secondary",
    }
)
_LINEAGE_REF_KEYS = frozenset(
    {
        "evidence_ledger_ref",
        "custody_ref",
        "fetch_read_candidate_custody_ref",
        "content_ref",
        "semantic_observation_ref",
        "analysis_packet_ref",
        "analyst_finding_ref",
        "component_ref",
        "candidate_ref",
        "reference_ref",
    }
)
_CLOSED_SURFACE_FLAGS = {
    "component_coverage_reduced": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "citation_eligible": False,
    "citation_created": False,
    "source_obligation_satisfied": False,
    "product_correctness_claimed": False,
    "current_answer_contract_mutated": False,
    "semantic_observation_admitted": False,
    "search_authorization_created": False,
    "query_bundle_created": False,
    "search_result_candidate_packet_created": False,
    "fetch_read_content_packet_created": False,
    "evidence_ledger_custody_created": False,
    "provider_called": False,
    "live_provider_called": False,
    "broker_called": False,
    "retrieval_executed": False,
    "live_fetch_read_executed": False,
    "model_called": False,
    "author_called": False,
}
_RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "body",
        "bounded_text",
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
        "output_packet",
        "page_content",
        "page_text",
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
        "snippet",
        "source_text",
        "text",
        "token",
        "unbounded_content",
        "unbounded_text",
    }
)
_SAFE_FALSE_RAW_RETENTION_KEYS = frozenset(
    {
        "raw_content_retained",
        "raw_headers_retained",
        "raw_model_response_retained",
        "raw_page_content_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)
_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_CLOSED_SURFACE_FLAGS,
        "answer_ready",
        "author_input_ready",
        "authorized_for_search",
        "citation_rendered",
        "component_satisfied",
        "content_citation_eligible",
        "coverage_decision",
        "evidence_admitted",
        "evidence_created",
        "final_answer_ready",
        "final_evidence_eligible",
        "readiness_decided",
        "search_dispatched",
        "search_executed",
        "semantic_observation_created",
        "semantic_support_created",
        "source_obligation_support_created",
    }
)


class SpecialistSourceBoundCalculationRuntimeError(ValueError):
    """Raised when Specialist calculation state exceeds its narrow authority."""


@dataclass(frozen=True, slots=True)
class SpecialistSourceBoundCalculationResult:
    """Compact runtime result for one reduced Specialist calculation."""

    calculation_record: Mapping[str, Any]
    calculation_projection: Mapping[str, Any]
    authorization_action_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_kind": "specialist_source_bound_calculation_result",
            "durable_packet": False,
            "helper": SPECIALIST_SOURCE_BOUND_CALCULATION_HELPER,
            "authorization_action_id": self.authorization_action_id,
            "calculation_record_ref": calculation_ref_from_record(
                self.calculation_record
            ),
            "calculation_projection": dict(self.calculation_projection),
            "component_coverage_reduced": False,
            "sufficiency_decided": False,
            "final_answer_packet_created": False,
            "author_input_created": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
        }


def evaluate_source_bound_calculation(
    *,
    calculation_kind: str,
    input_records: Sequence[Mapping[str, Any]],
    formula_label: str | None = None,
    output_unit: str | None = None,
    assumptions: Sequence[Any] = (),
    caveats: Sequence[Any] = (),
) -> dict[str, Any]:
    """Purely evaluate one deterministic source-bound calculation.

    This seam owns normalization, Decimal arithmetic, formula facts, blockers,
    and the bounded result facts shared by the compatibility record builder and
    the ordinary quantitative Specialist adapter.  It creates no RunKernel
    action or canonical state and grants no downstream authority.
    """

    operator = _operator(calculation_kind)
    normalized_inputs = _normalized_inputs(input_records)
    input_blockers = _input_blockers(normalized_inputs)
    formula = _formula_record(
        operator=operator,
        formula_label=formula_label,
        output_unit=output_unit,
        assumptions=assumptions,
        caveats=caveats,
        input_records=normalized_inputs,
    )
    operator_blockers: list[dict[str, Any]] = []
    result_value: Decimal | None = None
    result_unit = _clean_token(output_unit, limit=80)

    if not normalized_inputs:
        operator_blockers.append(
            _blocker("invalid_input", "calculation requires at least one input")
        )
    if operator not in SUPPORTED_OPERATORS:
        operator_blockers.append(
            _blocker(
                "unsupported_formula",
                f"unsupported deterministic operator: {operator or '<missing>'}",
            )
        )

    blocking_kinds = {item["blocker_kind"] for item in input_blockers}
    contested_kinds = blocking_kinds & {
        "stale_input",
        "contradictory_input",
        "weak_source_class",
    }
    hard_blockers = [
        item
        for item in input_blockers
        if item["blocker_kind"] not in contested_kinds
    ]
    if not hard_blockers and not operator_blockers and not contested_kinds:
        try:
            result_value, result_unit = _calculate(
                operator=operator,
                inputs=normalized_inputs,
                output_unit=result_unit,
                blockers=operator_blockers,
            )
        except SpecialistSourceBoundCalculationRuntimeError as exc:
            operator_blockers.append(_blocker("invalid_input", str(exc)))

    blockers = [*input_blockers, *operator_blockers]
    status = _calculation_status(blockers)
    result_base: dict[str, Any] = {
        "calculation_status": status,
        "unit": result_unit,
        "precision": "decimal_arithmetic_serialized_to_json_number",
        "rounding_posture": "no_extra_rounding_applied",
        "downstream_authority": "none",
    }
    if status == "computed" and result_value is not None:
        result_base["numeric_value"] = _json_number(result_value)
        result_base["numeric_value_text"] = _decimal_text(result_value)
    result = {**result_base, "result_digest": _digest_json(result_base)}
    return {
        "calculation_kind": operator,
        "deterministic_operator": operator,
        "formula_id": formula["formula_id"],
        "formula_digest": formula["formula_digest"],
        "formula_label": formula["formula_label"],
        "formula": formula,
        "input_records": normalized_inputs,
        "input_count": len(normalized_inputs),
        "result": result,
        "calculation_status": status,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "component_coverage_reduced": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
    }


def build_specialist_source_bound_calculation_record(
    *,
    run_id: str,
    request_id: str,
    calculation_kind: str,
    input_records: Sequence[Mapping[str, Any]],
    formula_label: str | None = None,
    output_unit: str | None = None,
    mode: str = "source_bound_calculation",
    assumptions: Sequence[Any] = (),
    caveats: Sequence[Any] = (),
    reviewed_artifact_refs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a bounded Specialist calculation record from structured inputs."""

    clean_run_id = _required_token(
        run_id,
        "Specialist calculation requires run_id",
    )
    clean_request_id = _required_token(
        request_id,
        "Specialist calculation requires request_id",
    )
    evaluation = evaluate_source_bound_calculation(
        calculation_kind=calculation_kind,
        input_records=input_records,
        formula_label=formula_label,
        output_unit=output_unit,
        assumptions=assumptions,
        caveats=caveats,
    )
    operator = str(evaluation["calculation_kind"])
    normalized_inputs = list(evaluation["input_records"])
    formula = dict(evaluation["formula"])
    blockers = list(evaluation["blockers"])
    status = str(evaluation["calculation_status"])
    result = dict(evaluation["result"])
    reviewed_refs = _reviewed_artifact_refs(
        reviewed_artifact_refs,
        input_records=normalized_inputs,
    )
    record_base = _without_empty(
        {
            "schema_version": SPECIALIST_SOURCE_BOUND_CALCULATION_SCHEMA_VERSION,
            "record_kind": "specialist_source_bound_calculation_record",
            "trace_key": SPECIALIST_SOURCE_BOUND_CALCULATION_TRACE_KEY,
            "owner": SPECIALIST_SOURCE_BOUND_CALCULATION_OWNER,
            "helper": SPECIALIST_SOURCE_BOUND_CALCULATION_HELPER,
            "canonical_state": False,
            "reduced_state": False,
            "proposal_packet": False,
            "durable_packet": False,
            "run_id": clean_run_id,
            "request_id": clean_request_id,
            "mode": _clean_token(mode, limit=120) or "source_bound_calculation",
            "calculation_kind": operator,
            "formula_id": formula["formula_id"],
            "formula_digest": formula["formula_digest"],
            "formula_label": formula["formula_label"],
            "deterministic_operator": operator,
            "formula": formula,
            "input_records": normalized_inputs,
            "input_count": len(normalized_inputs),
            "result": result,
            "calculation_status": status,
            "blockers": blockers,
            "blocker_count": len(blockers),
            "reviewed_artifact_refs": reviewed_refs,
            "signoff": {
                "specialist_calculation_signed_off": False,
                "final_answer_signed_off": False,
                "product_correctness_claimed": False,
            },
            "specialist_is_product_authority": False,
            "component_coverage_reduced": False,
            "sufficiency_decided": False,
            "final_answer_packet_created": False,
            "author_input_created": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
            "product_correctness_claimed": False,
            "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
            **_CLOSED_SURFACE_FLAGS,
        }
    )
    record_digest = _digest_json(_record_digest_payload(record_base))
    record_id = (
        "specialist-calculation:"
        f"{clean_request_id}:{operator or 'unsupported'}:{record_digest[:16]}"
    )
    record = {
        **record_base,
        "record_id": record_id,
        "record_digest": record_digest,
    }
    return validate_specialist_source_bound_calculation_record(record)


def reduce_specialist_source_bound_calculation(
    *,
    run_kernel: Any,
    specialist_source_bound_calculation_record: Mapping[str, Any],
) -> SpecialistSourceBoundCalculationResult:
    """Authorize and reduce one Specialist calculation record through RunKernel."""

    record = validate_specialist_source_bound_calculation_record(
        specialist_source_bound_calculation_record
    )
    try:
        action = run_kernel.authorize_specialist_source_bound_calculation(
            specialist_source_bound_calculation_record=record,
        )
        from core.run_kernel import Observation, ObservationType, RunStageStatus

        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=(
                    ObservationType.SPECIALIST_SOURCE_BOUND_CALCULATION_REDUCED
                ),
                status=RunStageStatus.COMPLETED,
                payload={
                    "specialist_source_bound_calculation_record": record,
                },
            )
        )
    except Exception as exc:  # pragma: no cover - translated for callers/tests.
        if exc.__class__.__name__ == "RunKernelTransitionError":
            raise SpecialistSourceBoundCalculationRuntimeError(str(exc)) from exc
        raise
    return SpecialistSourceBoundCalculationResult(
        calculation_record=record,
        calculation_projection=dict(
            run_kernel.state.specialist_source_bound_calculation_projection
        ),
        authorization_action_id=action.action_id,
    )


def build_specialist_source_bound_calculation_action_inputs(
    *,
    run_id: str,
    request_id: str,
    specialist_source_bound_calculation_record: Mapping[str, Any],
) -> dict[str, Any]:
    """Build RunKernel action inputs for reducing a calculation record."""

    record = validate_specialist_source_bound_calculation_record(
        specialist_source_bound_calculation_record
    )
    clean_run_id = _required_token(
        run_id,
        "Specialist calculation action requires run_id",
    )
    clean_request_id = _required_token(
        request_id,
        "Specialist calculation action requires request_id",
    )
    if record.get("run_id") != clean_run_id or record.get("request_id") != clean_request_id:
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation record run/request lineage does not match RunKernel"
        )
    return {
        "schema_version": SPECIALIST_SOURCE_BOUND_CALCULATION_ACTION_SCHEMA_VERSION,
        "owner": SPECIALIST_SOURCE_BOUND_CALCULATION_OWNER,
        "trace_key": SPECIALIST_SOURCE_BOUND_CALCULATION_TRACE_KEY,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "record_id": record["record_id"],
        "record_digest": record["record_digest"],
        "calculation_kind": record["calculation_kind"],
        "deterministic_operator": record["deterministic_operator"],
        "formula_digest": record["formula_digest"],
        "input_count": record["input_count"],
        "calculation_status": record["calculation_status"],
        "blocker_count": record["blocker_count"],
        "calculation_only": True,
        "specialist_is_product_authority": False,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def build_specialist_source_bound_calculation_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    existing_calculation_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate reducer observation and build canonical Specialist state."""

    clean_action_id = _required_token(
        action_id,
        "Specialist calculation reduction requires action_id",
        limit=200,
    )
    clean_run_id = _required_token(
        run_id,
        "Specialist calculation reduction requires run_id",
    )
    clean_request_id = _required_token(
        request_id,
        "Specialist calculation reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    if inputs.get("schema_version") != (
        SPECIALIST_SOURCE_BOUND_CALCULATION_ACTION_SCHEMA_VERSION
    ):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation action schema mismatch"
        )
    payload = _safe_mapping(observation_payload)
    record = validate_specialist_source_bound_calculation_record(
        _safe_mapping(payload.get("specialist_source_bound_calculation_record"))
    )
    if record.get("run_id") != clean_run_id or record.get("request_id") != clean_request_id:
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation observation run/request binding mismatch"
        )
    for key in (
        "record_id",
        "record_digest",
        "calculation_kind",
        "deterministic_operator",
        "formula_digest",
        "input_count",
        "calculation_status",
        "blocker_count",
    ):
        if inputs.get(key) != record.get(key):
            raise SpecialistSourceBoundCalculationRuntimeError(
                f"Specialist calculation action binding mismatch for {key}"
            )
    _validate_closed_flags(inputs, context="Specialist calculation action inputs")
    existing = _safe_mapping(existing_calculation_projection)
    prior_history = [
        _safe_mapping(item)
        for item in _safe_list(existing.get("calculation_history"))
    ]
    if record["record_digest"] in {
        item.get("record_digest") for item in prior_history if isinstance(item, Mapping)
    }:
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation record was already reduced"
        )
    history = [*prior_history, _history_entry(record, clean_action_id)]
    return {
        **record,
        "canonical_state": True,
        "reduced_state": True,
        "authorized_action_id": clean_action_id,
        "calculation_history": history,
        "calculation_count": len(history),
    }


def build_specialist_source_bound_calculation_projection(
    *,
    calculation_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project canonical Specialist calculation state without answer authority."""

    state = validate_specialist_source_bound_calculation_record(calculation_state)
    history = [
        _safe_mapping(item)
        for item in _safe_list(calculation_state.get("calculation_history"))
    ]
    if not history:
        history = [_history_entry(state, state.get("authorized_action_id"))]
    return {
        "owner": SPECIALIST_SOURCE_BOUND_CALCULATION_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": SPECIALIST_SOURCE_BOUND_CALCULATION_TRACE_KEY,
        "canonical_state": True,
        "reduced_state": True,
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "record_id": state.get("record_id"),
        "record_digest": state.get("record_digest"),
        "mode": state.get("mode"),
        "calculation_kind": state.get("calculation_kind"),
        "formula_id": state.get("formula_id"),
        "formula_digest": state.get("formula_digest"),
        "formula_label": state.get("formula_label"),
        "deterministic_operator": state.get("deterministic_operator"),
        "input_records": [dict(item) for item in state.get("input_records") or ()],
        "input_count": state.get("input_count"),
        "result": _safe_mapping(state.get("result")),
        "calculation_status": state.get("calculation_status"),
        "blockers": [dict(item) for item in state.get("blockers") or ()],
        "blocker_count": state.get("blocker_count"),
        "reviewed_artifact_refs": _safe_mapping(state.get("reviewed_artifact_refs")),
        "latest_calculation": _history_entry(
            state,
            state.get("authorized_action_id"),
        ),
        "calculation_history": history,
        "calculation_count": len(history),
        "signoff": _safe_mapping(state.get("signoff")),
        "specialist_is_product_authority": False,
        "component_coverage_reduced": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "product_correctness_claimed": False,
        **_CLOSED_SURFACE_FLAGS,
        "closed_surface_flags": dict(_CLOSED_SURFACE_FLAGS),
    }


def validate_specialist_source_bound_calculation_record(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a Specialist calculation record and return a sanitized copy."""

    safe = _safe_mapping(record)
    if not safe:
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation record is required"
        )
    _reject_raw_private_or_dangerous(safe, context="Specialist calculation record")
    if safe.get("schema_version") != (
        SPECIALIST_SOURCE_BOUND_CALCULATION_SCHEMA_VERSION
    ):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation schema mismatch"
        )
    if safe.get("record_kind") != "specialist_source_bound_calculation_record":
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation record kind mismatch"
        )
    if safe.get("owner") != SPECIALIST_SOURCE_BOUND_CALCULATION_OWNER:
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation owner mismatch"
        )
    if safe.get("calculation_status") not in CALCULATION_STATUSES:
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation status mismatch"
        )
    if safe.get("deterministic_operator") != safe.get("calculation_kind"):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation operator mismatch"
        )
    if safe.get("specialist_is_product_authority") is not False:
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist must not be product authority"
        )
    _validate_closed_flags(safe, context="Specialist calculation record")
    signoff = _safe_mapping(safe.get("signoff"))
    for key in (
        "specialist_calculation_signed_off",
        "final_answer_signed_off",
        "product_correctness_claimed",
    ):
        if signoff.get(key) is not False:
            raise SpecialistSourceBoundCalculationRuntimeError(
                f"Specialist calculation signoff must keep {key}=False"
            )
    inputs = [_safe_mapping(item) for item in _safe_list(safe.get("input_records"))]
    if int(safe.get("input_count") or 0) != len(inputs):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation input count mismatch"
        )
    for item in inputs:
        _validate_input_record(item)
    blockers = [_safe_mapping(item) for item in _safe_list(safe.get("blockers"))]
    if int(safe.get("blocker_count") or 0) != len(blockers):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation blocker count mismatch"
        )
    result = _safe_mapping(safe.get("result"))
    if result.get("calculation_status") != safe.get("calculation_status"):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation result status mismatch"
        )
    declared_result_digest = _required_token(
        result.get("result_digest"),
        "Specialist calculation result requires digest",
        limit=128,
    )
    result_payload = dict(result)
    result_payload.pop("result_digest", None)
    if declared_result_digest != _digest_json(result_payload):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation result digest mismatch"
        )
    if safe.get("calculation_status") == "computed":
        if "numeric_value" not in result:
            raise SpecialistSourceBoundCalculationRuntimeError(
                "computed Specialist calculation requires numeric result"
            )
        if blockers:
            raise SpecialistSourceBoundCalculationRuntimeError(
                "computed Specialist calculation cannot carry blockers"
            )
    else:
        if "numeric_value" in result:
            raise SpecialistSourceBoundCalculationRuntimeError(
                "blocked or contested Specialist calculation cannot carry numeric result"
            )
    formula = _safe_mapping(safe.get("formula"))
    if formula.get("formula_digest") != safe.get("formula_digest"):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation formula digest mismatch"
        )
    formula_payload = dict(formula)
    declared_formula_digest = formula_payload.pop("formula_digest", None)
    formula_id = formula_payload.pop("formula_id", None)
    if declared_formula_digest != _digest_json(formula_payload):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation formula content digest mismatch"
        )
    expected_formula_id = (
        "specialist-formula:"
        f"{safe.get('calculation_kind')}:{str(declared_formula_digest)[:16]}"
    )
    if formula_id != expected_formula_id or safe.get("formula_id") != expected_formula_id:
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation formula id mismatch"
        )
    declared_digest = _required_token(
        safe.get("record_digest"),
        "Specialist calculation requires record_digest",
        limit=128,
    )
    if declared_digest != _digest_json(_record_digest_payload(safe)):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation record digest mismatch"
        )
    expected_id = (
        "specialist-calculation:"
        f"{_clean_token(safe.get('request_id'), limit=120)}:"
        f"{safe.get('calculation_kind') or 'unsupported'}:{declared_digest[:16]}"
    )
    if safe.get("record_id") != expected_id:
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation record id mismatch"
        )
    return safe


def calculation_ref_from_record(record: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a compact downstream review reference for a calculation record."""

    safe = _safe_mapping(record)
    record_id = _clean_token(safe.get("record_id"), limit=260)
    record_digest = _clean_token(safe.get("record_digest"), limit=128)
    if not record_id or not record_digest:
        return {}
    result = _safe_mapping(safe.get("result"))
    return _without_empty(
        {
            "record_id": record_id,
            "record_digest": record_digest,
            "calculation_kind": safe.get("calculation_kind"),
            "deterministic_operator": safe.get("deterministic_operator"),
            "calculation_status": safe.get("calculation_status"),
            "result_digest": result.get("result_digest"),
            "result_unit": result.get("unit"),
            "blocker_count": safe.get("blocker_count"),
        }
    )


def _calculate(
    *,
    operator: str,
    inputs: Sequence[Mapping[str, Any]],
    output_unit: str | None,
    blockers: list[dict[str, Any]],
) -> tuple[Decimal | None, str | None]:
    values = [_decimal_from_input(item) for item in inputs]
    units = [_required_unit(item) for item in inputs]
    if operator == "sum":
        _require_matching_units(units, blockers)
        return (sum(values, Decimal("0")), units[0] if units else None)
    if operator == "difference":
        _require_count(inputs, 2, "difference", blockers)
        if blockers:
            return None, units[0] if units else None
        _require_matching_units(units, blockers)
        return (values[0] - values[1], units[0])
    if operator == "product":
        if not output_unit:
            blockers.append(
                _blocker(
                    "missing_output_unit",
                    "product requires explicit output_unit",
                )
            )
            return None, output_unit
        product = Decimal("1")
        for value in values:
            product *= value
        return product, output_unit
    if operator == "ratio":
        _require_count(inputs, 2, "ratio", blockers)
        if blockers:
            return None, output_unit or "dimensionless"
        if values[1] == 0:
            blockers.append(_blocker("denominator_zero", "ratio denominator is zero"))
            return None, output_unit or "dimensionless"
        if output_unit:
            return values[0] / values[1], output_unit
        _require_matching_units(units, blockers)
        return values[0] / values[1], "dimensionless"
    if operator == "percentage":
        _require_count(inputs, 2, "percentage", blockers)
        if blockers:
            return None, "%"
        _require_matching_units(units, blockers)
        if values[1] == 0:
            blockers.append(
                _blocker("denominator_zero", "percentage denominator is zero")
            )
            return None, "%"
        return (values[0] / values[1]) * Decimal("100"), "%"
    if operator == "percentage_point_difference":
        _require_count(inputs, 2, "percentage_point_difference", blockers)
        if blockers:
            return None, "percentage_points"
        normalized_units = {unit.casefold() for unit in units}
        if not normalized_units <= {"%", "percent", "percentage"}:
            blockers.append(
                _blocker(
                    "incompatible_units",
                    "percentage_point_difference requires percentage inputs",
                )
            )
            return None, "percentage_points"
        return values[0] - values[1], "percentage_points"
    if operator == "simple_rate":
        _require_count(inputs, 2, "simple_rate", blockers)
        if blockers:
            return None, output_unit
        if not output_unit:
            blockers.append(
                _blocker(
                    "missing_output_unit",
                    "simple_rate requires explicit output_unit",
                )
            )
            return None, output_unit
        if values[1] == 0:
            blockers.append(
                _blocker("denominator_zero", "simple_rate denominator is zero")
            )
            return None, output_unit
        return values[0] / values[1], output_unit
    if operator == "weighted_average":
        return _weighted_average(inputs, blockers)
    blockers.append(
        _blocker("unsupported_formula", f"unsupported deterministic operator: {operator}")
    )
    return None, output_unit


def _weighted_average(
    inputs: Sequence[Mapping[str, Any]],
    blockers: list[dict[str, Any]],
) -> tuple[Decimal | None, str | None]:
    pairs: dict[str, dict[str, Mapping[str, Any]]] = {}
    for item in inputs:
        pair_id = _clean_token(item.get("pair_id"), limit=160)
        role = _clean_token(item.get("role"), limit=80)
        if not pair_id or role not in {"value", "weight"}:
            blockers.append(
                _blocker(
                    "invalid_input",
                    "weighted_average inputs require value/weight roles and pair_id",
                    input_ref=_input_ref(item),
                )
            )
            continue
        pairs.setdefault(pair_id, {})[role] = item
    weighted_sum = Decimal("0")
    total_weight = Decimal("0")
    value_units: list[str] = []
    for pair_id, pair in pairs.items():
        value_record = pair.get("value")
        weight_record = pair.get("weight")
        if value_record is None or weight_record is None:
            blockers.append(
                _blocker(
                    "missing_weight",
                    f"weighted_average pair {pair_id} requires value and weight",
                )
            )
            continue
        if weight_record.get("source_bound") is not True and weight_record.get(
            "fixture_bound"
        ) is not True:
            blockers.append(
                _blocker(
                    "missing_source_bound_input",
                    "weighted_average weight is neither source-bound nor fixture-bound",
                    input_ref=_input_ref(weight_record),
                )
            )
        value_units.append(_required_unit(value_record))
        value = _decimal_from_input(value_record)
        weight = _decimal_from_input(weight_record)
        weighted_sum += value * weight
        total_weight += weight
    _require_matching_units(value_units, blockers)
    if total_weight == 0:
        blockers.append(
            _blocker("denominator_zero", "weighted_average total weight is zero")
        )
        return None, value_units[0] if value_units else None
    if blockers:
        return None, value_units[0] if value_units else None
    return weighted_sum / total_weight, value_units[0] if value_units else None


def _normalized_inputs(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    inputs = _safe_list(records)
    out: list[dict[str, Any]] = []
    for index, item in enumerate(inputs):
        if not isinstance(item, Mapping):
            item = {}
        mapped = _safe_mapping(item)
        label = _clean_token(mapped.get("label"), limit=160) or f"input_{index + 1}"
        numeric_value, numeric_valid = _typed_decimal(mapped.get("numeric_value"))
        source_ref = _safe_mapping(mapped.get("source_bound_ref"))
        component_id = _clean_token(
            mapped.get("component_id")
            or _safe_mapping(source_ref.get("component_ref")).get("component_id"),
            limit=260,
        )
        base = _without_empty(
            {
                "label": label,
                "numeric_value": _json_number(numeric_value)
                if numeric_valid and numeric_value is not None
                else None,
                "numeric_value_text": _decimal_text(numeric_value)
                if numeric_valid and numeric_value is not None
                else None,
                "numeric_value_type": type(mapped.get("numeric_value")).__name__,
                "numeric_value_valid": numeric_valid,
                "unit": _clean_token(mapped.get("unit"), limit=80),
                "scale": _clean_token(mapped.get("scale"), limit=80)
                or "unit_scale",
                "source_bound": mapped.get("source_bound") is True,
                "fixture_bound": mapped.get("fixture_bound") is True,
                "source_bound_ref": source_ref,
                "fixture_ref": _safe_mapping(mapped.get("fixture_ref")),
                "component_id": component_id,
                "role": _clean_token(mapped.get("role"), limit=80),
                "pair_id": _clean_token(mapped.get("pair_id"), limit=160),
                "currentness_posture": _clean_token(
                    mapped.get("currentness_posture"),
                    limit=80,
                )
                or "unknown",
                "source_class_posture": _clean_token(
                    mapped.get("source_class_posture"),
                    limit=120,
                )
                or "unknown",
                "conflict_posture": _clean_token(
                    mapped.get("conflict_posture"),
                    limit=80,
                )
                or "unknown",
                "contradictory": mapped.get("contradictory") is True,
                "caveats": _text_list(mapped.get("caveats"), limit=300),
            }
        )
        digest = _digest_json(_input_digest_payload(base))
        out.append(
            {
                **base,
                "input_id": _clean_token(mapped.get("input_id"), limit=260)
                or f"specialist-input:{index + 1}:{digest[:16]}",
                "input_digest": digest,
            }
        )
    return out


def _input_blockers(inputs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for item in inputs:
        ref = _input_ref(item)
        role = _clean_token(item.get("role"), limit=80)
        fixture_weight = role == "weight" and item.get("fixture_bound") is True
        if item.get("numeric_value_valid") is not True:
            blockers.append(
                _blocker("non_numeric_input", "input is not typed numeric", input_ref=ref)
            )
        if not _clean_token(item.get("unit"), limit=80):
            blockers.append(_blocker("missing_unit", "input unit is missing", input_ref=ref))
        if item.get("source_bound") is not True and not fixture_weight:
            blockers.append(
                _blocker(
                    "missing_source_bound_input",
                    "input is not marked source-bound",
                    input_ref=ref,
                )
            )
        if not fixture_weight and not _has_lineage_ref(item.get("source_bound_ref")):
            blockers.append(
                _blocker(
                    "insufficient_lineage",
                    "input lacks source/custody/content/semantic lineage ref",
                    input_ref=ref,
                )
            )
        if not _clean_token(item.get("component_id"), limit=260):
            blockers.append(
                _blocker(
                    "insufficient_lineage",
                    "input lacks component_id lineage",
                    input_ref=ref,
                )
            )
        if str(item.get("currentness_posture") or "").casefold() in _BAD_CURRENTNESS:
            blockers.append(
                _blocker(
                    "stale_input",
                    "input currentness is stale or unknown",
                    input_ref=ref,
                )
            )
        if str(item.get("source_class_posture") or "").casefold() in _WEAK_SOURCE_CLASSES:
            blockers.append(
                _blocker(
                    "weak_source_class",
                    "input source class is weak or unknown",
                    input_ref=ref,
                )
            )
        if (
            item.get("contradictory") is True
            or str(item.get("conflict_posture") or "").casefold() == "present"
        ):
            blockers.append(
                _blocker(
                    "contradictory_input",
                    "input carries unresolved contradiction posture",
                    input_ref=ref,
                )
            )
    return blockers


def _calculation_status(blockers: Sequence[Mapping[str, Any]]) -> str:
    if not blockers:
        return "computed"
    kinds = {item.get("blocker_kind") for item in blockers}
    if "non_numeric_input" in kinds:
        return "invalid_input"
    contested_only = {"stale_input", "contradictory_input", "weak_source_class"}
    if kinds <= contested_only:
        return "contested"
    return "blocked"


def _formula_record(
    *,
    operator: str,
    formula_label: str | None,
    output_unit: str | None,
    assumptions: Sequence[Any],
    caveats: Sequence[Any],
    input_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    formula_base = _without_empty(
        {
            "formula_label": _clean_token(formula_label, limit=160)
            or f"{operator}_source_bound_calculation",
            "deterministic_operator": operator,
            "output_unit": _clean_token(output_unit, limit=80),
            "input_digests": [
                item.get("input_digest") for item in input_records if item.get("input_digest")
            ],
            "assumptions": _text_list(assumptions, limit=300),
            "caveats": _text_list(caveats, limit=300),
            "arbitrary_formula_parsing": False,
            "arbitrary_code_execution": False,
        }
    )
    digest = _digest_json(formula_base)
    return {
        **formula_base,
        "formula_id": f"specialist-formula:{operator}:{digest[:16]}",
        "formula_digest": digest,
    }


def _reviewed_artifact_refs(
    supplied: Mapping[str, Any] | None,
    *,
    input_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    refs = _safe_mapping(supplied)
    evidence_refs: list[dict[str, Any]] = []
    content_refs: list[dict[str, Any]] = []
    semantic_refs: list[dict[str, Any]] = []
    analysis_refs: list[dict[str, Any]] = []
    component_refs: list[dict[str, Any]] = []
    for item in input_records:
        source_ref = _safe_mapping(item.get("source_bound_ref"))
        for key, out in (
            ("evidence_ledger_ref", evidence_refs),
            ("custody_ref", evidence_refs),
            ("content_ref", content_refs),
            ("semantic_observation_ref", semantic_refs),
            ("analysis_packet_ref", analysis_refs),
            ("analyst_finding_ref", analysis_refs),
            ("component_ref", component_refs),
        ):
            mapped = _safe_mapping(source_ref.get(key))
            if mapped:
                out.append(mapped)
        component_id = _clean_token(item.get("component_id"), limit=260)
        if component_id:
            component_refs.append({"component_id": component_id})
    return _without_empty(
        {
            **refs,
            "evidence_ledger_refs": _dedupe_refs(evidence_refs),
            "content_refs": _dedupe_refs(content_refs),
            "semantic_observation_refs": _dedupe_refs(semantic_refs),
            "analysis_packet_refs": _dedupe_refs(analysis_refs),
            "component_refs": _dedupe_refs(component_refs),
        }
    )


def _validate_input_record(item: Mapping[str, Any]) -> None:
    if not _clean_token(item.get("input_id"), limit=260):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation input requires input_id"
        )
    declared = _required_token(
        item.get("input_digest"),
        "Specialist calculation input requires digest",
        limit=128,
    )
    if declared != _digest_json(_input_digest_payload(item)):
        raise SpecialistSourceBoundCalculationRuntimeError(
            "Specialist calculation input digest mismatch"
        )


def _validate_closed_flags(value: Mapping[str, Any], *, context: str) -> None:
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if value.get(key) is not expected:
            raise SpecialistSourceBoundCalculationRuntimeError(
                f"{context} must keep {key}=False"
            )
    flags = _safe_mapping(value.get("closed_surface_flags"))
    for key, expected in _CLOSED_SURFACE_FLAGS.items():
        if flags.get(key) is not expected:
            raise SpecialistSourceBoundCalculationRuntimeError(
                f"{context} closed_surface_flags must keep {key}=False"
            )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SpecialistSourceBoundCalculationRuntimeError(
            f"{context} opens closed surfaces: " + ", ".join(dangerous)
        )


def _reject_raw_private_or_dangerous(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    raw_or_private = sorted(key for key in keys if _is_raw_or_private_key(key))
    if raw_or_private:
        raise SpecialistSourceBoundCalculationRuntimeError(
            f"{context} contains raw/private fields: " + ", ".join(raw_or_private)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SpecialistSourceBoundCalculationRuntimeError(
            f"{context} opens closed runtime surfaces: " + ", ".join(dangerous)
        )


def _require_count(
    inputs: Sequence[Mapping[str, Any]],
    expected: int,
    label: str,
    blockers: list[dict[str, Any]],
) -> None:
    if len(inputs) != expected:
        blockers.append(
            _blocker(
                "invalid_input",
                f"{label} requires exactly {expected} inputs",
            )
        )


def _require_matching_units(units: Sequence[str], blockers: list[dict[str, Any]]) -> None:
    if not units:
        blockers.append(_blocker("missing_unit", "calculation requires units"))
        return
    if len({unit.casefold() for unit in units}) > 1:
        blockers.append(
            _blocker("incompatible_units", "calculation input units are incompatible")
        )


def _required_unit(item: Mapping[str, Any]) -> str:
    unit = _clean_token(item.get("unit"), limit=80)
    if not unit:
        raise SpecialistSourceBoundCalculationRuntimeError("input unit is missing")
    return unit


def _decimal_from_input(item: Mapping[str, Any]) -> Decimal:
    exact_text = item.get("numeric_value_text")
    if isinstance(exact_text, str) and exact_text:
        try:
            parsed = Decimal(exact_text)
        except InvalidOperation as exc:
            raise SpecialistSourceBoundCalculationRuntimeError(
                "input exact numeric text is invalid"
            ) from exc
        if parsed.is_finite():
            return parsed
    value, ok = _typed_decimal(item.get("numeric_value"))
    if not ok or value is None:
        raise SpecialistSourceBoundCalculationRuntimeError("input is not typed numeric")
    return value


def _typed_decimal(value: Any) -> tuple[Decimal | None, bool]:
    if isinstance(value, bool) or value is None:
        return None, False
    if isinstance(value, Decimal):
        return value, value.is_finite()
    if isinstance(value, int):
        return Decimal(value), True
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            return None, False
        try:
            parsed = Decimal(str(value))
        except InvalidOperation:
            return None, False
        return parsed, parsed.is_finite()
    return None, False


def _json_number(value: Decimal | None) -> int | float | None:
    if value is None:
        return None
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.normalize(), "f")


def _operator(value: Any) -> str:
    return (_clean_token(value, limit=120) or "").casefold()


def _has_lineage_ref(value: Any) -> bool:
    mapped = _safe_mapping(value)
    if not mapped:
        return False
    return any(_safe_mapping(mapped.get(key)) for key in _LINEAGE_REF_KEYS)


def _input_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "input_id": item.get("input_id"),
            "input_digest": item.get("input_digest"),
            "label": item.get("label"),
            "component_id": item.get("component_id"),
        }
    )


def _blocker(
    blocker_kind: str,
    reason: str,
    *,
    input_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    base = _without_empty(
        {
            "blocker_kind": _clean_token(blocker_kind, limit=120),
            "reason": _clean_text(reason, limit=400),
            "input_ref": _safe_mapping(input_ref),
        }
    )
    return {
        **base,
        "blocker_id": f"specialist-blocker:{blocker_kind}:{_digest_json(base)[:16]}",
        "blocker_digest": _digest_json(base),
    }


def _history_entry(record: Mapping[str, Any], action_id: Any) -> dict[str, Any]:
    result = _safe_mapping(record.get("result"))
    return {
        "record_id": record.get("record_id"),
        "record_digest": record.get("record_digest"),
        "authorized_action_id": action_id,
        "calculation_kind": record.get("calculation_kind"),
        "deterministic_operator": record.get("deterministic_operator"),
        "calculation_status": record.get("calculation_status"),
        "result_digest": result.get("result_digest"),
        "result_unit": result.get("unit"),
        "blocker_count": record.get("blocker_count"),
        "component_coverage_reduced": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "product_correctness_claimed": False,
    }


def _dedupe_refs(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        mapped = _safe_mapping(record)
        key = (
            _clean_token(mapped.get("record_digest"), limit=128)
            or _clean_token(mapped.get("packet_digest"), limit=128)
            or _clean_token(mapped.get("observation_digest"), limit=128)
            or _clean_token(mapped.get("content_digest"), limit=128)
            or _clean_token(mapped.get("component_id"), limit=260)
            or _digest_json(mapped)
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(mapped)
    return out


def _input_digest_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(record)
    payload.pop("input_id", None)
    payload.pop("input_digest", None)
    return payload


def _record_digest_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(record)
    for key in (
        "record_id",
        "record_digest",
        "authorized_action_id",
        "calculation_history",
        "calculation_count",
    ):
        payload.pop(key, None)
    payload["canonical_state"] = False
    payload["reduced_state"] = False
    return payload


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
    if normalized in _SAFE_FALSE_RAW_RETENTION_KEYS:
        return False
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
    if isinstance(value, Decimal):
        return _json_number(value)
    if isinstance(value, str):
        return _clean_text(value, limit=900)
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


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise SpecialistSourceBoundCalculationRuntimeError(message)
    return text


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "CALCULATION_STATUSES",
    "SPECIALIST_SOURCE_BOUND_CALCULATION_ACTION_SCHEMA_VERSION",
    "SPECIALIST_SOURCE_BOUND_CALCULATION_HELPER",
    "SPECIALIST_SOURCE_BOUND_CALCULATION_OWNER",
    "SPECIALIST_SOURCE_BOUND_CALCULATION_REASON",
    "SPECIALIST_SOURCE_BOUND_CALCULATION_SCHEMA_VERSION",
    "SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE",
    "SPECIALIST_SOURCE_BOUND_CALCULATION_TRACE_KEY",
    "SUPPORTED_OPERATORS",
    "SpecialistSourceBoundCalculationResult",
    "SpecialistSourceBoundCalculationRuntimeError",
    "build_specialist_source_bound_calculation_action_inputs",
    "build_specialist_source_bound_calculation_projection",
    "build_specialist_source_bound_calculation_record",
    "build_specialist_source_bound_calculation_state",
    "calculation_ref_from_record",
    "evaluate_source_bound_calculation",
    "reduce_specialist_source_bound_calculation",
    "validate_specialist_source_bound_calculation_record",
]
