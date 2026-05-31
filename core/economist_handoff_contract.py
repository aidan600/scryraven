"""Controller-owned Economist handoff contract.

This module is deliberately passive and deterministic. It copies already
computed Economist admission, preflight, quantitative-packet, unsupported-value,
output-exposure, and upstream-contract facts into Controller-owned state. It does
not build prompts, call providers, retrieve, execute code, run calculations,
change quantitative policy, change Analyst/Author behavior, select citations,
persist sessions, or change final-answer behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence

ECONOMIST_HANDOFF_SCHEMA_VERSION = "AG76D-ECO.v1"
ECONOMIST_HANDOFF_TRACE_KEY = "economist_handoff_contract"


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _copy_sequence(value: Sequence[Any] | None) -> tuple[Any, ...]:
    return tuple(deepcopy(list(value or ())))


def _string_tuple(value: Sequence[Any] | None) -> tuple[str, ...]:
    return tuple(str(item) for item in (value or ()))


def _hash_text(value: Any) -> str:
    return sha256(str(value or "").encode("utf-8")).hexdigest()


def _hash_payload(value: Any) -> str:
    return sha256(
        repr(deepcopy(value)).encode("utf-8", errors="replace")
    ).hexdigest()


def _state_ref(value: Any | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return _copy_mapping(value)
    if hasattr(value, "to_controller_state"):
        result = value.to_controller_state()
        return _copy_mapping(result if isinstance(result, Mapping) else {})
    if hasattr(value, "to_trace_fragment"):
        fragment = value.to_trace_fragment()
        if isinstance(fragment, Mapping):
            if len(fragment) == 1:
                only = next(iter(fragment.values()))
                if isinstance(only, Mapping):
                    return _copy_mapping(only)
            return _copy_mapping(fragment)
    if hasattr(value, "execution_trace_fragment"):
        result = value.execution_trace_fragment()
        return _copy_mapping(result if isinstance(result, Mapping) else {})
    if hasattr(value, "to_trace"):
        result = value.to_trace()
        return _copy_mapping(result if isinstance(result, Mapping) else {})
    return {"ref_type": type(value).__name__}


def _packet_identity(packet: Mapping[str, Any] | None) -> dict[str, Any]:
    packet_copy = _copy_mapping(packet)
    source_bound_values = packet_copy.get("source_bound_values")
    unsupported_values = packet_copy.get("unsupported_values")
    calculation_results = packet_copy.get("calculation_results")
    source_ids_used = packet_copy.get("source_ids_used")
    return {
        "present": bool(packet_copy),
        "schema_version": packet_copy.get("schema_version"),
        "hash": _hash_payload(packet_copy) if packet_copy else None,
        "repr_length": len(repr(packet_copy)) if packet_copy else 0,
        "source_ids_used": list(source_ids_used) if isinstance(source_ids_used, list) else [],
        "source_bound_value_count": (
            len(source_bound_values) if isinstance(source_bound_values, list) else 0
        ),
        "source_bound_values_hash": (
            _hash_payload(source_bound_values) if isinstance(source_bound_values, list) else None
        ),
        "unsupported_values_count": (
            len(unsupported_values) if isinstance(unsupported_values, list) else 0
        ),
        "unsupported_values_hash": (
            _hash_payload(unsupported_values) if isinstance(unsupported_values, list) else None
        ),
        "calculation_result_count": (
            len(calculation_results) if isinstance(calculation_results, list) else 0
        ),
        "calculation_results_hash": (
            _hash_payload(calculation_results) if isinstance(calculation_results, list) else None
        ),
        "requires_analyst": bool(packet_copy.get("requires_analyst")),
        "direct_use_eligible": bool(packet_copy.get("direct_use_eligible")),
        "high_stakes_quant_detected": bool(packet_copy.get("high_stakes_quant_detected")),
        "validation_errors": list(packet_copy.get("validation_errors") or []),
        "raw_packet_included": False,
    }


@dataclass(frozen=True)
class EconomistAdmissionDescriptor:
    economist_should_run: bool
    economist_ran: bool
    economist_blocked: bool
    economist_unavailable: bool
    economist_skip_reason: str | None = None
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "economist_should_run": bool(self.economist_should_run),
            "economist_ran": bool(self.economist_ran),
            "economist_blocked": bool(self.economist_blocked),
            "economist_unavailable": bool(self.economist_unavailable),
            "economist_skip_reason": self.economist_skip_reason,
            "mechanical_executor_boundary": True,
        }


@dataclass(frozen=True)
class EconomistPreflightDescriptor:
    evaluated: bool
    allowed: bool | None
    block_reason: str | None
    missing_entities: tuple[str, ...] = field(default_factory=tuple)
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "evaluated": bool(self.evaluated),
            "allowed": self.allowed,
            "block_reason": self.block_reason,
            "missing_entities": list(self.missing_entities),
            "missing_entity_count": len(self.missing_entities),
        }


@dataclass(frozen=True)
class SourceBoundQuantitativePacketDescriptor:
    telemetry: dict[str, Any]
    packet_identity: dict[str, Any]
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        keys = (
            "quantitative_packet_present",
            "quantitative_packet_valid",
            "quantitative_packet_validation_errors",
            "quantitative_packet_direct_use_eligible",
            "quantitative_packet_requires_analyst",
            "quantitative_packet_shadow_mode",
            "quantitative_packet_gate_reason",
            "source_bound_value_count",
            "source_binding_valid",
            "source_binding_missing_count",
            "source_ids_used",
            "target_metric_names",
            "target_metric_missing",
        )
        return {
            "controller_owned": bool(self.controller_owned),
            "telemetry": {key: deepcopy(self.telemetry.get(key)) for key in keys if key in self.telemetry},
            "packet_identity": deepcopy(self.packet_identity),
            "source_bound_posture_visible_to_controller": True,
            "raw_packet_included": False,
        }


@dataclass(frozen=True)
class UnsupportedQuantitativeValueDescriptor:
    unsupported_values_count: int
    unsupported_values_hash: str | None
    missing_target_metrics: tuple[str, ...]
    model_derived_value_flags: dict[str, Any]
    estimate_from_priors_requested: bool
    estimate_from_priors_blocked_by_pre_analyst_gate: bool
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "unsupported_values_count": int(self.unsupported_values_count),
            "unsupported_values_hash": self.unsupported_values_hash,
            "missing_target_metrics": list(self.missing_target_metrics),
            "model_derived_value_flags": deepcopy(self.model_derived_value_flags),
            "estimate_from_priors_requested": bool(self.estimate_from_priors_requested),
            "estimate_from_priors_blocked_by_pre_analyst_gate": bool(
                self.estimate_from_priors_blocked_by_pre_analyst_gate
            ),
            "unsupported_values_raw_included": False,
        }


@dataclass(frozen=True)
class EconomistOutputDescriptor:
    economist_schema_version: str | None
    economist_schema_valid: bool
    output_present: bool
    output_identity: dict[str, Any]
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "economist_schema_version": self.economist_schema_version,
            "economist_schema_valid": bool(self.economist_schema_valid),
            "output_present": bool(self.output_present),
            "output_identity": deepcopy(self.output_identity),
            "raw_economist_output_included": False,
        }


@dataclass(frozen=True)
class EconomistAnalystExposureDescriptor:
    analyst_skipped_after_economist: bool
    analyst_after_economist_skip_reason: str | None
    economist_output_used_as_analysis: bool
    quantitative_packet_injected: bool
    analyst_reviewed_packet: bool
    analyst_model_called: bool
    analyst_author_handoff_ref: dict[str, Any] = field(default_factory=dict)
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "analyst_skipped_after_economist": bool(self.analyst_skipped_after_economist),
            "analyst_after_economist_skip_reason": self.analyst_after_economist_skip_reason,
            "economist_output_used_as_analysis": bool(self.economist_output_used_as_analysis),
            "quantitative_packet_injected": bool(self.quantitative_packet_injected),
            "analyst_reviewed_packet": bool(self.analyst_reviewed_packet),
            "analyst_model_called": bool(self.analyst_model_called),
            "analyst_author_handoff_ref": deepcopy(self.analyst_author_handoff_ref),
            "does_not_bypass_analyst_author_contract": True,
        }


@dataclass(frozen=True)
class EconomistAuthorExposureDescriptor:
    author_quant_content_source: str | None
    author_received_raw_quant_packet: bool
    author_received_economist_framework: bool
    author_received_analyst_packet_marker: bool
    citation_source_handoff_ref: dict[str, Any] = field(default_factory=dict)
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "author_quant_content_source": self.author_quant_content_source,
            "author_received_raw_quant_packet": bool(self.author_received_raw_quant_packet),
            "author_received_economist_framework": bool(self.author_received_economist_framework),
            "author_received_analyst_packet_marker": bool(self.author_received_analyst_packet_marker),
            "citation_source_handoff_ref": deepcopy(self.citation_source_handoff_ref),
            "does_not_bypass_author_contract": True,
            "raw_economist_packet_author_facing": False,
        }


@dataclass(frozen=True)
class EconomistSafetyDescriptor:
    code_execution_requested: bool
    code_execution_blocked: bool
    safety_status: str
    no_code_execution_boundary: bool = True
    controller_owned: bool = True

    def to_trace(self) -> dict[str, Any]:
        return {
            "controller_owned": bool(self.controller_owned),
            "economist_code_execution_requested": bool(self.code_execution_requested),
            "economist_code_execution_blocked": bool(self.code_execution_blocked),
            "economist_safety_status": self.safety_status,
            "no_model_generated_code_execution": bool(self.no_code_execution_boundary),
            "subprocess_eval_exec_shell_enabled": False,
            "dynamic_script_execution_enabled": False,
        }


@dataclass(frozen=True)
class EconomistHandoffState:
    admission: EconomistAdmissionDescriptor
    preflight: EconomistPreflightDescriptor
    source_bound_packet: SourceBoundQuantitativePacketDescriptor
    unsupported_values: UnsupportedQuantitativeValueDescriptor
    output: EconomistOutputDescriptor
    analyst_exposure: EconomistAnalystExposureDescriptor
    author_exposure: EconomistAuthorExposureDescriptor
    safety: EconomistSafetyDescriptor
    run_id: str | None = None
    answer_contract_ref: dict[str, Any] = field(default_factory=dict)
    analyst_author_handoff_ref: dict[str, Any] = field(default_factory=dict)
    citation_source_handoff_ref: dict[str, Any] = field(default_factory=dict)
    trace_visibility: dict[str, Any] = field(default_factory=dict)
    schema_version: str = ECONOMIST_HANDOFF_SCHEMA_VERSION
    controller_owned: bool = True

    def to_trace_fragment(self) -> dict[str, Any]:
        return {
            ECONOMIST_HANDOFF_TRACE_KEY: {
                "schema_version": self.schema_version,
                "controller_owned": bool(self.controller_owned),
                "run_id": self.run_id,
                "admission": self.admission.to_trace(),
                "preflight": self.preflight.to_trace(),
                "source_bound_packet": self.source_bound_packet.to_trace(),
                "unsupported_values": self.unsupported_values.to_trace(),
                "output": self.output.to_trace(),
                "analyst_exposure": self.analyst_exposure.to_trace(),
                "author_exposure": self.author_exposure.to_trace(),
                "safety": self.safety.to_trace(),
                "answer_contract_ref": deepcopy(self.answer_contract_ref),
                "analyst_author_handoff_ref": deepcopy(self.analyst_author_handoff_ref),
                "citation_source_handoff_ref": deepcopy(self.citation_source_handoff_ref),
                "trace_visibility": {
                    "additive_only": True,
                    "legacy_trace_fields_preserved": True,
                    "owned_by": "Controller",
                    **deepcopy(self.trace_visibility),
                },
                "did_change_economist_behavior": False,
                "did_change_economist_prompt_text": False,
                "did_change_quantitative_policy": False,
                "did_change_source_bound_numeric_policy": False,
                "did_change_code_execution_behavior": False,
                "did_change_analyst_behavior": False,
                "did_change_author_behavior": False,
                "did_change_final_answer_behavior": False,
                "did_change_citation_behavior": False,
                "did_change_provider_search_query_behavior": False,
                "did_change_db_session_run_outcome_shape": False,
                "did_change_cache_behavior": False,
                "mechanical_executor_boundary": True,
            }
        }

    def to_controller_state(self) -> dict[str, Any]:
        return deepcopy(self.to_trace_fragment()[ECONOMIST_HANDOFF_TRACE_KEY])


@dataclass(frozen=True)
class EconomistExecutionEnvelope:
    economist_should_run: bool
    economist_ran: bool
    economist_blocked: bool
    economist_unavailable: bool
    economist_skip_reason: str | None
    economist_preflight_allowed: bool | None
    economist_preflight_block_reason: str | None
    economist_preflight_missing_entities: tuple[str, ...]
    analyst_skipped_after_economist: bool
    analyst_after_economist_skip_reason: str | None
    economist_output_used_as_analysis: bool
    controller_owned: bool = True
    mechanical_handoff_only: bool = True


def build_economist_handoff_state(
    *,
    run_id: str | None = None,
    need_economist: bool,
    economist_ran: bool,
    economist_preflight_allowed: bool | None,
    economist_preflight_block_reason: str | None,
    economist_preflight_missing_entities: Sequence[Any] | None = None,
    economist_safety_telemetry: Mapping[str, Any] | None = None,
    economist_pre_analyst_skip_candidate_telemetry: Mapping[str, Any] | None = None,
    analyst_quant_packet_handoff_telemetry: Mapping[str, Any] | None = None,
    author_quant_source_telemetry: Mapping[str, Any] | None = None,
    analyst_skipped_after_economist: bool = False,
    analyst_after_economist_skip_reason: str | None = None,
    economist_output_used_as_analysis: bool = False,
    estimate_from_priors_requested: bool = False,
    estimate_from_priors_blocked_by_pre_analyst_gate: bool = False,
    answer_contract_ref: Any | None = None,
    analyst_author_handoff_state: Any | None = None,
    citation_source_handoff_state: Any | None = None,
) -> EconomistHandoffState:
    """Build Controller-owned state from already-computed Economist facts."""

    safety_telemetry = _copy_mapping(economist_safety_telemetry)
    pre_skip_telemetry = _copy_mapping(economist_pre_analyst_skip_candidate_telemetry)
    analyst_packet_telemetry = _copy_mapping(analyst_quant_packet_handoff_telemetry)
    author_quant_telemetry = _copy_mapping(author_quant_source_telemetry)
    packet = safety_telemetry.get("quantitative_packet")
    packet_mapping = packet if isinstance(packet, Mapping) else {}
    packet_identity = _packet_identity(packet_mapping)
    preflight_evaluated = economist_preflight_allowed is not None
    skip_reason = safety_telemetry.get("economist_skip_reason")
    blocked = bool(
        (need_economist and preflight_evaluated and economist_preflight_allowed is False)
        or safety_telemetry.get("economist_code_execution_blocked")
    )
    unavailable = bool(need_economist and not preflight_evaluated and not economist_ran)
    output_present = bool(
        economist_ran
        and (
            safety_telemetry.get("economist_schema_version")
            or safety_telemetry.get("quantitative_packet_present")
            or packet_mapping
        )
    )
    output_identity = {
        "economist_safety_telemetry_hash": _hash_payload(safety_telemetry),
        "economist_safety_telemetry_key_count": len(safety_telemetry),
        "quantitative_packet_hash": packet_identity.get("hash"),
        "quantitative_packet_repr_length": packet_identity.get("repr_length"),
        "raw_economist_json_included": False,
    }
    missing_metrics = safety_telemetry.get("target_metric_missing")
    if not isinstance(missing_metrics, list):
        missing_metrics = []
    unsupported_hash = packet_identity.get("unsupported_values_hash")
    model_derived_flags = {
        "quantitative_packet_requires_analyst": bool(
            safety_telemetry.get("quantitative_packet_requires_analyst")
        ),
        "quantitative_packet_direct_use_eligible": bool(
            safety_telemetry.get("quantitative_packet_direct_use_eligible")
        ),
        "economist_pre_analyst_skip_candidate_shadow": bool(
            pre_skip_telemetry.get("economist_pre_analyst_skip_candidate_shadow")
        ),
        "missing_target_metric_directive_supported": bool(missing_metrics),
    }
    analyst_ref = _state_ref(analyst_author_handoff_state)
    citation_ref = _state_ref(citation_source_handoff_state)
    return EconomistHandoffState(
        admission=EconomistAdmissionDescriptor(
            economist_should_run=bool(need_economist),
            economist_ran=bool(economist_ran),
            economist_blocked=blocked,
            economist_unavailable=unavailable,
            economist_skip_reason=None if skip_reason is None else str(skip_reason),
        ),
        preflight=EconomistPreflightDescriptor(
            evaluated=preflight_evaluated,
            allowed=economist_preflight_allowed,
            block_reason=economist_preflight_block_reason,
            missing_entities=_string_tuple(economist_preflight_missing_entities),
        ),
        source_bound_packet=SourceBoundQuantitativePacketDescriptor(
            telemetry=safety_telemetry,
            packet_identity=packet_identity,
        ),
        unsupported_values=UnsupportedQuantitativeValueDescriptor(
            unsupported_values_count=int(packet_identity.get("unsupported_values_count") or 0),
            unsupported_values_hash=unsupported_hash,
            missing_target_metrics=_string_tuple(missing_metrics),
            model_derived_value_flags=model_derived_flags,
            estimate_from_priors_requested=bool(estimate_from_priors_requested),
            estimate_from_priors_blocked_by_pre_analyst_gate=bool(
                estimate_from_priors_blocked_by_pre_analyst_gate
            ),
        ),
        output=EconomistOutputDescriptor(
            economist_schema_version=(
                str(safety_telemetry.get("economist_schema_version"))
                if safety_telemetry.get("economist_schema_version") is not None
                else None
            ),
            economist_schema_valid=bool(safety_telemetry.get("economist_schema_valid")),
            output_present=output_present,
            output_identity=output_identity,
        ),
        analyst_exposure=EconomistAnalystExposureDescriptor(
            analyst_skipped_after_economist=bool(analyst_skipped_after_economist),
            analyst_after_economist_skip_reason=analyst_after_economist_skip_reason,
            economist_output_used_as_analysis=bool(economist_output_used_as_analysis),
            quantitative_packet_injected=bool(
                analyst_packet_telemetry.get("analyst_quant_packet_injected")
            ),
            analyst_reviewed_packet=bool(
                analyst_packet_telemetry.get("analyst_quant_packet_reviewed_by_model")
            ),
            analyst_model_called=bool(analyst_packet_telemetry.get("analyst_model_called")),
            analyst_author_handoff_ref=analyst_ref,
        ),
        author_exposure=EconomistAuthorExposureDescriptor(
            author_quant_content_source=(
                str(author_quant_telemetry.get("author_quant_content_source"))
                if author_quant_telemetry.get("author_quant_content_source") is not None
                else None
            ),
            author_received_raw_quant_packet=bool(
                author_quant_telemetry.get("author_received_raw_quant_packet")
            ),
            author_received_economist_framework=bool(
                author_quant_telemetry.get("author_received_economist_framework")
            ),
            author_received_analyst_packet_marker=bool(
                author_quant_telemetry.get("author_received_analyst_packet_marker")
            ),
            citation_source_handoff_ref=citation_ref,
        ),
        safety=EconomistSafetyDescriptor(
            code_execution_requested=bool(
                safety_telemetry.get("economist_code_execution_requested")
            ),
            code_execution_blocked=bool(
                safety_telemetry.get("economist_code_execution_blocked")
            ),
            safety_status=str(
                safety_telemetry.get("economist_safety_status")
                or "code_execution_disabled"
            ),
        ),
        run_id=run_id,
        answer_contract_ref=_state_ref(answer_contract_ref),
        analyst_author_handoff_ref=analyst_ref,
        citation_source_handoff_ref=citation_ref,
    )


def execute_economist_handoff(state: EconomistHandoffState) -> EconomistExecutionEnvelope:
    """Return legacy-compatible Economist handoff facts without new decisions."""

    return EconomistExecutionEnvelope(
        economist_should_run=bool(state.admission.economist_should_run),
        economist_ran=bool(state.admission.economist_ran),
        economist_blocked=bool(state.admission.economist_blocked),
        economist_unavailable=bool(state.admission.economist_unavailable),
        economist_skip_reason=state.admission.economist_skip_reason,
        economist_preflight_allowed=state.preflight.allowed,
        economist_preflight_block_reason=state.preflight.block_reason,
        economist_preflight_missing_entities=tuple(state.preflight.missing_entities),
        analyst_skipped_after_economist=bool(
            state.analyst_exposure.analyst_skipped_after_economist
        ),
        analyst_after_economist_skip_reason=(
            state.analyst_exposure.analyst_after_economist_skip_reason
        ),
        economist_output_used_as_analysis=bool(
            state.analyst_exposure.economist_output_used_as_analysis
        ),
    )
