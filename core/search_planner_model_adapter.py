"""Explicit model-backed SearchPlanner adapter for AG-SEARCH-PLANNER-MODEL-01.

The adapter is live-capable only when constructed with an injected callable and
an explicit enabled/licensed flag. It imports no provider client and stores no
raw prompt, model response, or provider payload.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

from core.search_planner_model_prompt import (
    SEARCH_PLANNER_MODEL_ALLOWED_SUPPORT_KIND_COMBINATIONS,
    SEARCH_PLANNER_MODEL_COMPONENT_PURPOSES,
    SEARCH_PLANNER_MODEL_MATERIALITY_VALUES,
    SEARCH_PLANNER_MODEL_PARTIAL_ANSWER_POLICIES,
    SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION,
    SEARCH_PLANNER_MODEL_QUERY_CANDIDATE_KINDS,
    SEARCH_PLANNER_MODEL_QUERY_ROLES,
    SEARCH_PLANNER_MODEL_RECON_POSTURES,
    SEARCH_PLANNER_MODEL_REQUIRED_TOP_LEVEL_FIELDS,
    SEARCH_PLANNER_MODEL_REQUIREMENT_POSTURES,
    SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_KINDS,
    SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_STATUSES,
    SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_KINDS,
    SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_STRICTNESSES,
    SEARCH_PLANNER_MODEL_SUPPORT_KINDS,
    SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
    SEARCH_PLANNER_MODEL_TEXT_LIMITS,
    build_search_planner_model_prompt,
    prompt_metadata,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_MAX_ANSWER_COMPONENTS,
    SearchPlannerRuntimeError,
)

SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION = "search_planner_model_adapter_ag_search_planner_model_01_v1"

_TOP_LEVEL_REQUIRED = SEARCH_PLANNER_MODEL_REQUIRED_TOP_LEVEL_FIELDS
_SEMANTIC_SLOT_KINDS = SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_KINDS
_SEMANTIC_SLOT_STATUSES = SEARCH_PLANNER_MODEL_SEMANTIC_SLOT_STATUSES
_MATERIALITY_VALUES = SEARCH_PLANNER_MODEL_MATERIALITY_VALUES
_REQUIREMENT_POSTURES = SEARCH_PLANNER_MODEL_REQUIREMENT_POSTURES
_COMPONENT_PURPOSES = SEARCH_PLANNER_MODEL_COMPONENT_PURPOSES
_SUPPORT_KINDS = SEARCH_PLANNER_MODEL_SUPPORT_KINDS
_PARTIAL_ANSWER_POLICIES = SEARCH_PLANNER_MODEL_PARTIAL_ANSWER_POLICIES
_QUERY_CANDIDATE_KINDS = SEARCH_PLANNER_MODEL_QUERY_CANDIDATE_KINDS
_QUERY_ROLES = SEARCH_PLANNER_MODEL_QUERY_ROLES
_RECON_POSTURES = SEARCH_PLANNER_MODEL_RECON_POSTURES
_SOURCE_OBLIGATION_KINDS = SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_KINDS
_SOURCE_OBLIGATION_STRICTNESSES = SEARCH_PLANNER_MODEL_SOURCE_OBLIGATION_STRICTNESSES
_MISSING = object()
_FORBIDDEN_QUERY_AUTHORITY_KEYS = frozenset(
    {
        "provider",
        "provider_hint",
        "provider_name",
        "provider_order",
        "provider_depth",
        "provider_variant",
        "provider_fallback",
        "model",
        "model_name",
        "model_selector",
    }
)

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "cache_row",
        "db",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output_packet",
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
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "token",
        "unbounded_text",
    }
)

_PRIVATE_VALUE_MARKERS = frozenset(
    {
        "api_key",
        "full_trace",
        "output_packet",
        "private_sentinel",
        "provider_payload",
        "raw_model_response",
        "raw_private",
        "raw_prompt",
        "raw_provider",
        "secret",
    }
)

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "accepted_amendment",
        "accepted_contract",
        "answer",
        "author_input",
        "canonical_coverage",
        "citation",
        "citations",
        "component_coverage_record",
        "contract_amendment_record",
        "current_answer_contract",
        "evidence",
        "evidence_ledger_admission",
        "final_answer",
        "final_answer_packet",
        "initial_answer_contract",
        "search_judgment_decision",
        "semantic_observation",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        "accepted_authority",
        "amendment_admitted",
        "amendment_applied",
        "author_behavior_changed",
        "author_executor_invoked",
        "author_input_created",
        "citation_behavior_changed",
        "citation_eligible",
        "citation_rendered",
        "component_satisfied",
        "constructs_search_work_plan",
        "contract_mutation_applied",
        "current_answer_contract_mutated",
        "evidence_admitted",
        "fetch_read_retrieval_behavior_changed",
        "final_answer_packet_created",
        "initial_answer_contract_mutated",
        "live_model_called",
        "live_validation_run",
        "model_called",
        "partial_answer_readiness_changed",
        "provider_called",
        "provider_search_behavior_changed",
        "query_plan_activated",
        "raw_model_response_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_trace_retained",
        "runtime_behavior_changed",
        "scout_runtime_activated",
        "search_executed",
        "search_executor_runtime_activated",
        "search_judgment_decided",
        "search_work_plan_activated",
        "source_obligation_satisfied",
        "sufficiency_decided",
    }
)


class SearchPlannerModelAdapterFailureStage(str, Enum):
    """Stable adapter-owned stage for one fail-closed Planner error."""

    INPUT = "INPUT"
    MODEL_CALL = "MODEL_CALL"
    OUTPUT_CLEANING = "OUTPUT_CLEANING"
    JSON_PARSING = "JSON_PARSING"
    MODEL_OUTPUT_VALIDATION = "MODEL_OUTPUT_VALIDATION"
    CROSS_REFERENCE_VALIDATION = "CROSS_REFERENCE_VALIDATION"


class SearchPlannerModelAdapterFailureCode(str, Enum):
    """Repository-owned bounded classification for adapter failures."""

    ADAPTER_DISABLED = "ADAPTER_DISABLED"
    ROUTE_UNAVAILABLE = "ROUTE_UNAVAILABLE"
    INPUT_CONSTRUCTION_FAILED = "INPUT_CONSTRUCTION_FAILED"
    MODEL_CALL_FAILED = "MODEL_CALL_FAILED"
    OUTPUT_CLEANING_FAILED = "OUTPUT_CLEANING_FAILED"
    INVALID_JSON = "INVALID_JSON"
    JSON_VALUE_NOT_OBJECT = "JSON_VALUE_NOT_OBJECT"
    MISSING_REQUIRED_TOP_LEVEL_FIELDS = "MISSING_REQUIRED_TOP_LEVEL_FIELDS"
    MISSING_REQUIRED_NESTED_FIELD = "MISSING_REQUIRED_NESTED_FIELD"
    INVALID_NESTED_TYPE = "INVALID_NESTED_TYPE"
    INVALID_ENUM_OR_BOUNDED_VALUE = "INVALID_ENUM_OR_BOUNDED_VALUE"
    INVALID_COMPONENT_COUNT = "INVALID_COMPONENT_COUNT"
    INVALID_COMPONENT_SUPPORT_MATRIX = "INVALID_COMPONENT_SUPPORT_MATRIX"
    INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION = "INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION"
    INVALID_ID_OR_CROSS_REFERENCE = "INVALID_ID_OR_CROSS_REFERENCE"
    INVALID_DEPENDENCY_OR_INFERENCE_DEPTH = "INVALID_DEPENDENCY_OR_INFERENCE_DEPTH"
    INVALID_QUERY_STRATEGY_METADATA = "INVALID_QUERY_STRATEGY_METADATA"
    CLOSED_AUTHORITY_VIOLATION = "CLOSED_AUTHORITY_VIOLATION"
    PRIVACY_OR_RAW_MATERIAL_VIOLATION = "PRIVACY_OR_RAW_MATERIAL_VIOLATION"
    LINEAGE_OR_BINDING_FAILURE = "LINEAGE_OR_BINDING_FAILURE"


_FailureCode = SearchPlannerModelAdapterFailureCode
_ADAPTER_MECHANICAL_RULE_IDS = frozenset(f"M{index:02d}" for index in range(1, 11))


@dataclass(frozen=True, slots=True)
class SearchPlannerModelAdapterFailureMetadata:
    """Immutable sanitized facts attached to an adapter failure."""

    failure_stage: SearchPlannerModelAdapterFailureStage
    failure_code: SearchPlannerModelAdapterFailureCode
    mechanical_rule_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.failure_stage,
            SearchPlannerModelAdapterFailureStage,
        ):
            raise TypeError("failure_stage must be an adapter-owned stage")
        if not isinstance(
            self.failure_code,
            SearchPlannerModelAdapterFailureCode,
        ):
            raise TypeError("failure_code must be a repository-owned code")
        if self.mechanical_rule_id is not None and self.mechanical_rule_id not in _ADAPTER_MECHANICAL_RULE_IDS:
            raise ValueError("mechanical_rule_id must be M01 through M10")


_FAILURE_STAGE_AND_RULE_BY_CODE: Mapping[
    SearchPlannerModelAdapterFailureCode,
    tuple[SearchPlannerModelAdapterFailureStage, str | None],
] = MappingProxyType({
    _FailureCode.ADAPTER_DISABLED: (
        SearchPlannerModelAdapterFailureStage.INPUT,
        None,
    ),
    _FailureCode.ROUTE_UNAVAILABLE: (
        SearchPlannerModelAdapterFailureStage.INPUT,
        None,
    ),
    _FailureCode.INPUT_CONSTRUCTION_FAILED: (
        SearchPlannerModelAdapterFailureStage.INPUT,
        None,
    ),
    _FailureCode.MODEL_CALL_FAILED: (
        SearchPlannerModelAdapterFailureStage.MODEL_CALL,
        None,
    ),
    _FailureCode.OUTPUT_CLEANING_FAILED: (
        SearchPlannerModelAdapterFailureStage.OUTPUT_CLEANING,
        None,
    ),
    _FailureCode.INVALID_JSON: (
        SearchPlannerModelAdapterFailureStage.JSON_PARSING,
        "M01",
    ),
    _FailureCode.JSON_VALUE_NOT_OBJECT: (
        SearchPlannerModelAdapterFailureStage.JSON_PARSING,
        "M01",
    ),
    _FailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M01",
    ),
    _FailureCode.MISSING_REQUIRED_NESTED_FIELD: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M02",
    ),
    _FailureCode.INVALID_NESTED_TYPE: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M02",
    ),
    _FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M02",
    ),
    _FailureCode.INVALID_COMPONENT_COUNT: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M02",
    ),
    _FailureCode.INVALID_COMPONENT_SUPPORT_MATRIX: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M05",
    ),
    _FailureCode.INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M06",
    ),
    _FailureCode.INVALID_ID_OR_CROSS_REFERENCE: (
        SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION,
        "M03",
    ),
    _FailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH: (
        SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION,
        "M04",
    ),
    _FailureCode.INVALID_QUERY_STRATEGY_METADATA: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M07",
    ),
    _FailureCode.CLOSED_AUTHORITY_VIOLATION: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M08",
    ),
    _FailureCode.PRIVACY_OR_RAW_MATERIAL_VIOLATION: (
        SearchPlannerModelAdapterFailureStage.MODEL_OUTPUT_VALIDATION,
        "M09",
    ),
    _FailureCode.LINEAGE_OR_BINDING_FAILURE: (
        SearchPlannerModelAdapterFailureStage.CROSS_REFERENCE_VALIDATION,
        "M10",
    ),
})


class SearchPlannerModelAdapterError(SearchPlannerRuntimeError):
    """Raised when the model adapter fails closed before planner observation."""

    __slots__ = ("_failure_metadata",)

    def __init__(
        self,
        message: str,
        *,
        failure_code: SearchPlannerModelAdapterFailureCode,
    ) -> None:
        super().__init__(message)
        try:
            failure_stage, mechanical_rule_id = _FAILURE_STAGE_AND_RULE_BY_CODE[failure_code]
        except KeyError as exc:
            raise ValueError("adapter failure code is not registered") from exc
        self._failure_metadata = SearchPlannerModelAdapterFailureMetadata(
            failure_stage=failure_stage,
            failure_code=failure_code,
            mechanical_rule_id=mechanical_rule_id,
        )

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_failure_metadata" and hasattr(self, name):
            raise AttributeError("adapter failure metadata is immutable")
        super().__setattr__(name, value)

    @property
    def failure_metadata(self) -> SearchPlannerModelAdapterFailureMetadata:
        return self._failure_metadata

    @property
    def failure_stage(self) -> SearchPlannerModelAdapterFailureStage:
        return self._failure_metadata.failure_stage

    @property
    def failure_code(self) -> SearchPlannerModelAdapterFailureCode:
        return self._failure_metadata.failure_code

    @property
    def mechanical_rule_id(self) -> str | None:
        return self._failure_metadata.mechanical_rule_id


@dataclass(frozen=True, slots=True)
class SearchPlannerModelAdapter:
    """Model-backed implementation of ``SearchPlannerAdapter``."""

    ask_model: Callable[..., Any] | None
    clean_json_response: Callable[[str], str] | None = None
    provider: str | None = None
    model: str | None = None
    effort: str = "low"
    use_reasoning: bool = True
    max_tokens: int | None = None
    enabled: bool = False
    licensed: bool = False

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        if not self.enabled or not self.licensed:
            raise SearchPlannerModelAdapterError(
                "search planner model adapter is not explicitly enabled",
                failure_code=_FailureCode.ADAPTER_DISABLED,
            )
        if self.ask_model is None:
            raise SearchPlannerModelAdapterError(
                "search planner model adapter is not explicitly enabled",
                failure_code=_FailureCode.ROUTE_UNAVAILABLE,
            )
        if not str(self.provider or "").strip() or not str(self.model or "").strip():
            raise SearchPlannerModelAdapterError(
                "selected search planner provider and model must be available",
                failure_code=_FailureCode.ROUTE_UNAVAILABLE,
            )

        try:
            prompt = build_search_planner_model_prompt(planner_input)
            metadata = prompt_metadata(prompt)
        except Exception as exc:
            raise SearchPlannerModelAdapterError(
                f"search planner model input failed closed: {type(exc).__name__}",
                failure_code=(_FailureCode.INPUT_CONSTRUCTION_FAILED),
            ) from exc
        model_kwargs = {
            "provider": self.provider,
            "model": self.model,
            "effort": self.effort,
            "require_json": True,
            "use_reasoning": self.use_reasoning,
        }
        if self.max_tokens is not None:
            model_kwargs["max_tokens"] = self.max_tokens
        try:
            raw = self.ask_model(
                prompt,
                SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
                **model_kwargs,
            )
        except Exception as exc:
            raise SearchPlannerModelAdapterError(
                f"search planner model call failed closed: {type(exc).__name__}",
                failure_code=_FailureCode.MODEL_CALL_FAILED,
            ) from exc

        parsed = _parse_model_output(raw, clean_json_response=self.clean_json_response)
        proposal = validate_and_sanitize_model_output(parsed)
        proposal["planner_model_metadata"] = _planner_model_metadata(
            prompt_meta=metadata,
            provider=self.provider,
            model=self.model,
            effort=self.effort,
            use_reasoning=self.use_reasoning,
        )
        return proposal


def _parse_model_output(
    raw: Any,
    *,
    clean_json_response: Callable[[str], str] | None,
) -> Mapping[str, Any]:
    text = str(raw or "")
    if clean_json_response is not None:
        try:
            text = clean_json_response(text)
        except Exception as exc:
            raise SearchPlannerModelAdapterError(
                f"search planner model output cleaning failed closed: {type(exc).__name__}",
                failure_code=(_FailureCode.OUTPUT_CLEANING_FAILED),
            ) from exc
    parse_failed = False
    try:
        parsed = json.loads(
            text,
            parse_constant=_reject_nonfinite_json_constant,
            object_pairs_hook=_reject_duplicate_json_members,
        )
    except Exception:
        parse_failed = True
    if parse_failed:
        raise SearchPlannerModelAdapterError(
            "search planner model output was not valid JSON",
            failure_code=_FailureCode.INVALID_JSON,
        )
    if not isinstance(parsed, Mapping):
        raise SearchPlannerModelAdapterError(
            "search planner model output must be a JSON object",
            failure_code=(_FailureCode.JSON_VALUE_NOT_OBJECT),
        )
    return parsed


def _reject_nonfinite_json_constant(_token: str) -> None:
    raise ValueError("strict JSON parsing rejected a nonfinite constant")


def _reject_duplicate_json_members(members: list[tuple[str, Any]]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for key, value in members:
        if key in parsed:
            raise ValueError("strict JSON parsing rejected a duplicate member")
        parsed[key] = value
    return parsed


def validate_and_sanitize_model_output(model_output: Mapping[str, Any]) -> dict[str, Any]:
    """Return a runtime-compatible planner proposal or fail closed."""

    _reject_unsafe_payload(model_output)
    missing = [field for field in _TOP_LEVEL_REQUIRED if field not in model_output]
    if missing:
        raise SearchPlannerModelAdapterError(
            "search planner model output missing required fields: " + ", ".join(missing),
            failure_code=(_FailureCode.MISSING_REQUIRED_TOP_LEVEL_FIELDS),
        )

    semantic_slots = _semantic_slots(model_output.get("semantic_slots"))
    answer_components = _answer_components(model_output.get("answer_components"))
    source_obligations = _source_obligation_candidates(model_output.get("source_obligation_candidates"))
    component_requirements = _component_search_requirements(model_output.get("component_search_requirements"))

    slot_ids = {slot["slot_id"] for slot in semantic_slots}
    component_ids = {component["component_id"] for component in answer_components}
    obligation_ids = {candidate["candidate_id"] for candidate in source_obligations}
    _validate_component_refs(
        answer_components=answer_components,
        source_obligations=source_obligations,
        component_search_requirements=component_requirements,
        slot_ids=slot_ids,
        component_ids=component_ids,
        obligation_ids=obligation_ids,
    )

    return {
        "question_meaning_summary": _required_text(
            model_output,
            "question_meaning_summary",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["question_meaning_summary"],
        ),
        "requested_output": _required_text(
            model_output,
            "requested_output",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["requested_output"],
        ),
        "semantic_slots": semantic_slots,
        "answer_components": answer_components,
        "source_obligation_candidates": source_obligations,
        "component_search_requirements": component_requirements,
        "material_ambiguity_posture": _required_text(
            model_output,
            "material_ambiguity_posture",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["material_ambiguity_posture"],
        ),
        "mandatory_caveats": _required_text_list(
            model_output,
            "mandatory_caveats",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
            allow_empty=True,
        ),
        "prohibited_upgrades": _required_text_list(
            model_output,
            "prohibited_upgrades",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
            allow_empty=True,
        ),
        "normalization_obligations": _required_text_list(
            model_output,
            "normalization_obligations",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
            allow_empty=True,
        ),
        "assumptions": _required_text_list(
            model_output,
            "assumptions",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
            allow_empty=True,
        ),
        "unsupported_or_deferred_outputs": _required_text_list(
            model_output,
            "unsupported_or_deferred_outputs",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["top_level_text_list_item"],
            allow_empty=True,
        ),
        "contract_amendment_candidates": _contract_amendment_candidates(
            model_output.get("contract_amendment_candidates")
        ),
        "relationship_hypotheses": _relationship_hypotheses(model_output.get("relationship_hypotheses")),
    }


def _semantic_slots(value: Any) -> list[dict[str, Any]]:
    items = _required_sequence(value, "semantic_slots")
    if not items:
        raise SearchPlannerModelAdapterError(
            "search planner model output requires at least one semantic slot",
            failure_code=(_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
        )
    slots: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        mapping = _required_mapping(item, "semantic slot")
        slot_id = _required_text(
            mapping,
            "slot_id",
            failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
        )
        if slot_id in seen:
            raise SearchPlannerModelAdapterError(
                f"duplicate semantic slot id: {slot_id}",
                failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
            )
        seen.add(slot_id)
        status = _required_enum_text(
            mapping,
            "status",
            allowed=_SEMANTIC_SLOT_STATUSES,
        )
        materiality = _required_enum_text(
            mapping,
            "materiality",
            allowed=_MATERIALITY_VALUES,
        )
        user_confirmation_required = bool(mapping.get("user_confirmation_required", False))
        if materiality == "material" and status in {"ambiguous", "unresolved"} and not user_confirmation_required:
            raise SearchPlannerModelAdapterError(
                f"material semantic slot {slot_id} requires user_confirmation_required",
                failure_code=(_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
            )
        slots.append(
            _without_empty(
                {
                    "slot_id": slot_id,
                    "slot_kind": _required_enum_text(
                        mapping,
                        "slot_kind",
                        allowed=_SEMANTIC_SLOT_KINDS,
                    ),
                    "status": status,
                    "candidate_values": _optional_text_list(
                        mapping.get("candidate_values", _MISSING),
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "semantic_slot_candidate_value"
                        ],
                    ),
                    "selected_value": _optional_model_text(
                        mapping,
                        "selected_value",
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "semantic_slot_selected_value"
                        ],
                    ),
                    "materiality": materiality,
                    "user_confirmation_required": user_confirmation_required,
                    "normalization_notes": _optional_text_list(
                        mapping.get("normalization_notes", _MISSING),
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "semantic_slot_normalization_note"
                        ],
                    ),
                    "metadata": _safe_metadata(mapping.get("metadata")),
                }
            )
        )
    return slots


def _answer_components(value: Any) -> list[dict[str, Any]]:
    items = _required_sequence(value, "answer_components")
    if not items:
        raise SearchPlannerModelAdapterError(
            "search planner model output requires at least one answer component",
            failure_code=_FailureCode.INVALID_COMPONENT_COUNT,
        )
    if len(items) > SEARCH_PLANNER_MAX_ANSWER_COMPONENTS:
        raise SearchPlannerModelAdapterError(
            "search planner model output exceeds the five-component acceptance ceiling",
            failure_code=_FailureCode.INVALID_COMPONENT_COUNT,
        )
    components: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        mapping = _required_mapping(item, "answer component")
        component_id = _required_text(
            mapping,
            "component_id",
            failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
        )
        if component_id in seen:
            raise SearchPlannerModelAdapterError(
                f"duplicate answer component id: {component_id}",
                failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
            )
        seen.add(component_id)
        source_obligation_ids = _optional_text_list(
            mapping.get("source_obligation_candidate_ids", _MISSING),
            failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
        )
        requirement_posture = _required_enum_text(
            mapping,
            "requirement_posture",
            allowed=_REQUIREMENT_POSTURES,
        )
        allowed_support_kinds = _required_support_kind_list(mapping)
        support_tuple = tuple(allowed_support_kinds)
        if support_tuple not in SEARCH_PLANNER_MODEL_ALLOWED_SUPPORT_KIND_COMBINATIONS:
            raise SearchPlannerModelAdapterError(
                f"answer component {component_id} has an invalid support-kind combination",
                failure_code=(_FailureCode.INVALID_COMPONENT_SUPPORT_MATRIX),
            )
        dependencies = _optional_text_list(
            mapping.get("dependency_component_ids", _MISSING),
            failure_code=_FailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH,
        )
        max_inference_depth = _required_non_negative_int(
            mapping,
            "max_inference_depth",
        )
        if support_tuple == ("direct",):
            if max_inference_depth != 0 or len(source_obligation_ids) != 1:
                raise SearchPlannerModelAdapterError(
                    f"answer component {component_id} violates the direct-only component matrix",
                    failure_code=(_FailureCode.INVALID_COMPONENT_SUPPORT_MATRIX),
                )
        elif support_tuple == ("inferred",):
            if max_inference_depth < 1 or not dependencies or source_obligation_ids:
                raise SearchPlannerModelAdapterError(
                    f"answer component {component_id} violates the inferred-only component matrix",
                    failure_code=(_FailureCode.INVALID_COMPONENT_SUPPORT_MATRIX),
                )
        elif max_inference_depth < 1 or not dependencies or len(source_obligation_ids) != 1:
            raise SearchPlannerModelAdapterError(
                f"answer component {component_id} violates the direct-or-inferred component matrix",
                failure_code=(_FailureCode.INVALID_COMPONENT_SUPPORT_MATRIX),
            )
        partial_answer_policy = _optional_model_text(mapping, "partial_answer_policy")
        if partial_answer_policy is not None and partial_answer_policy not in _PARTIAL_ANSWER_POLICIES:
            raise SearchPlannerModelAdapterError(
                f"unsupported partial answer policy: {partial_answer_policy}",
                failure_code=(_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
            )
        components.append(
            _without_empty(
                {
                    "component_id": component_id,
                    "component_revision": _required_text(
                        mapping,
                        "component_revision",
                        failure_code=_FailureCode.LINEAGE_OR_BINDING_FAILURE,
                    ),
                    "component_purpose": _required_enum_text(
                        mapping,
                        "component_purpose",
                        allowed=_COMPONENT_PURPOSES,
                        failure_code=(_FailureCode.INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION),
                    ),
                    "user_facing_label": _required_text(
                        mapping,
                        "user_facing_label",
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "answer_component_user_facing_label"
                        ],
                    ),
                    "user_facing_question": _required_text(
                        mapping,
                        "user_facing_question",
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "answer_component_user_facing_question"
                        ],
                    ),
                    "requirement_posture": requirement_posture,
                    "acceptance_criteria": _required_text_list(
                        mapping,
                        "acceptance_criteria",
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "answer_component_acceptance_criterion"
                        ],
                    ),
                    "semantic_slot_ids": _required_text_list(
                        mapping,
                        "semantic_slot_ids",
                        failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
                    ),
                    "source_obligation_candidate_ids": source_obligation_ids,
                    "allowed_support_kinds": allowed_support_kinds,
                    "max_inference_depth": max_inference_depth,
                    "normalization_policy": _optional_model_text(
                        mapping,
                        "normalization_policy",
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "answer_component_normalization_policy"
                        ],
                    ),
                    "calculation_policy": _optional_model_text(
                        mapping,
                        "calculation_policy",
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "answer_component_calculation_policy"
                        ],
                    ),
                    "dependency_component_ids": dependencies,
                    "partial_answer_policy": partial_answer_policy,
                    "mandatory_caveats": _optional_text_list(
                        mapping.get("mandatory_caveats", _MISSING),
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "answer_component_mandatory_caveat"
                        ],
                    ),
                    "prohibited_upgrades": _optional_text_list(
                        mapping.get("prohibited_upgrades", _MISSING),
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "answer_component_prohibited_upgrade"
                        ],
                    ),
                    "materiality": _required_enum_text(
                        mapping,
                        "materiality",
                        allowed=_MATERIALITY_VALUES,
                    ),
                    "metadata": _safe_metadata(mapping.get("metadata")),
                }
            )
        )
    if not any(component.get("requirement_posture") == "required" for component in components):
        raise SearchPlannerModelAdapterError(
            "search planner model output requires at least one required answer component",
            failure_code=(_FailureCode.INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION),
        )
    return components


def _relationship_hypotheses(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    hypotheses: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _required_sequence(value, "relationship_hypotheses"):
        if len(hypotheses) >= SEARCH_PLANNER_MAX_ANSWER_COMPONENTS:
            raise SearchPlannerModelAdapterError(
                "relationship hypotheses exceed the five-item local ceiling",
                failure_code=(_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
            )
        mapping = _required_mapping(item, "relationship hypothesis")
        hypothesis_id = _required_text(
            mapping,
            "hypothesis_id",
            failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
        )
        if hypothesis_id in seen:
            raise SearchPlannerModelAdapterError(
                f"duplicate relationship hypothesis id: {hypothesis_id}",
                failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
            )
        seen.add(hypothesis_id)
        hypotheses.append(
            {
                "hypothesis_id": hypothesis_id,
                "target_component_id": _required_text(
                    mapping,
                    "target_component_id",
                    failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
                ),
                "premise_component_ids": _required_text_list(
                    mapping,
                    "premise_component_ids",
                    failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
                ),
                "relationship_summary": _required_text(
                    mapping,
                    "relationship_summary",
                    limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                        "relationship_hypothesis_summary"
                    ],
                ),
                "proposal_only": True,
                "canonical_state": False,
                "supporting_authority": False,
                "constructs_search_work": False,
            }
        )
    return hypotheses


def _source_obligation_candidates(value: Any) -> list[dict[str, Any]]:
    items = _required_sequence(value, "source_obligation_candidates")
    if not items:
        raise SearchPlannerModelAdapterError(
            "search planner model output requires source obligation candidates",
            failure_code=(_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
        )
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        mapping = _required_mapping(item, "source obligation candidate")
        candidate_id = _required_text(
            mapping,
            "candidate_id",
            failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
        )
        if candidate_id in seen:
            raise SearchPlannerModelAdapterError(
                f"duplicate source obligation candidate id: {candidate_id}",
                failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
            )
        seen.add(candidate_id)
        strictness = _optional_model_text(mapping, "strictness")
        if strictness is not None and strictness not in _SOURCE_OBLIGATION_STRICTNESSES:
            raise SearchPlannerModelAdapterError(
                f"unsupported value for strictness: {strictness}",
                failure_code=(_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
            )
        candidates.append(
            _without_empty(
                {
                    "candidate_id": candidate_id,
                    "obligation_kind": _required_enum_text(
                        mapping,
                        "obligation_kind",
                        allowed=_SOURCE_OBLIGATION_KINDS,
                    ),
                    "component_candidate_ids": _required_text_list(
                        mapping,
                        "component_candidate_ids",
                        failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
                    ),
                    "strictness": strictness,
                    "metadata": _safe_metadata(mapping.get("metadata")),
                }
            )
        )
    return candidates


def _component_search_requirements(value: Any) -> list[dict[str, Any]]:
    items = _required_sequence(value, "component_search_requirements")
    if not items:
        raise SearchPlannerModelAdapterError(
            "search planner model output requires component search requirements",
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
    requirements: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        mapping = _required_mapping(item, "component search requirement")
        _reject_executing_requirement(mapping)
        requirement_id = _required_text(
            mapping,
            "requirement_id",
            failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
        )
        if requirement_id in seen:
            raise SearchPlannerModelAdapterError(
                f"duplicate component search requirement id: {requirement_id}",
                failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
            )
        seen.add(requirement_id)
        raw_metadata = mapping.get("metadata")
        _validate_query_strategy_metadata(
            raw_metadata,
            component_id=_required_text(
                mapping,
                "component_id",
                failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
            ),
        )
        requirements.append(
            _without_empty(
                {
                    "component_id": _required_text(
                        mapping,
                        "component_id",
                        failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
                    ),
                    "requirement_id": requirement_id,
                    "requirement_summary": _required_text(
                        mapping,
                        "requirement_summary",
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "component_search_requirement_summary"
                        ],
                    ),
                    "source_obligation_candidate_ids": _required_text_list(
                        mapping,
                        "source_obligation_candidate_ids",
                        failure_code=_FailureCode.INVALID_ID_OR_CROSS_REFERENCE,
                    ),
                    "preferred_source_kinds": _optional_text_list(
                        mapping.get("preferred_source_kinds", _MISSING)
                    ),
                    "recency_requirement": _optional_model_text(
                        mapping,
                        "recency_requirement",
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "component_search_requirement_recency"
                        ],
                    ),
                    "metadata": _safe_metadata(raw_metadata),
                }
            )
        )
    return requirements


def _validate_query_strategy_metadata(
    value: Any,
    *,
    component_id: str,
) -> None:
    if not isinstance(value, Mapping):
        raise SearchPlannerModelAdapterError(
            f"component {component_id} search requirement requires metadata",
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
    candidates = _required_sequence(
        value.get("query_strategy_candidates"),
        "query_strategy_candidates",
        failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
    )
    if not candidates:
        raise SearchPlannerModelAdapterError(
            f"component {component_id} requires query strategy candidates",
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
    seen_strategy_ids: set[str] = set()
    for raw_candidate in candidates:
        candidate = _required_mapping(
            raw_candidate,
            "query strategy candidate",
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
        forbidden = sorted(_collect_keys(candidate) & _FORBIDDEN_QUERY_AUTHORITY_KEYS)
        if forbidden:
            raise SearchPlannerModelAdapterError(
                "query strategy candidate selects forbidden provider/model authority: " + ", ".join(forbidden),
                failure_code=(_FailureCode.CLOSED_AUTHORITY_VIOLATION),
            )
        strategy_id = _required_text(
            candidate,
            "strategy_id",
            failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
        )
        if strategy_id in seen_strategy_ids:
            raise SearchPlannerModelAdapterError(
                f"duplicate query strategy id: {strategy_id}",
                failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
            )
        seen_strategy_ids.add(strategy_id)
        candidate_component_id = _required_text(
            candidate,
            "component_id",
            failure_code=(_FailureCode.LINEAGE_OR_BINDING_FAILURE),
        )
        if candidate_component_id != component_id:
            raise SearchPlannerModelAdapterError(
                f"query strategy {strategy_id} has stale component binding",
                failure_code=(_FailureCode.LINEAGE_OR_BINDING_FAILURE),
            )
        _required_enum_text(
            candidate,
            "candidate_kind",
            allowed=_QUERY_CANDIDATE_KINDS,
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
        _required_text(
            candidate,
            "candidate_query_text",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                "query_strategy_candidate_query"
            ],
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
        _required_enum_text(
            candidate,
            "requested_role",
            allowed=_QUERY_ROLES,
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
        if not _required_text_list(
            candidate,
            "source_obligation_candidate_ids",
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        ):
            raise SearchPlannerModelAdapterError(
                f"query strategy {strategy_id} requires source obligations",
                failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
            )
        _required_text(
            candidate,
            "distinct_need_justification",
            limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                "query_strategy_distinct_need_justification"
            ],
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
        recon = _required_mapping(
            candidate.get("recon_requirement"),
            "recon requirement",
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
        _required_enum_text(
            recon,
            "posture",
            allowed=_RECON_POSTURES,
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
        _required_text_list(
            recon,
            "unresolved_dimension_ids",
            allow_empty=True,
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
        recon_candidates = _required_sequence(
            recon.get("candidate_queries"),
            "recon candidate_queries",
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )
        for raw_recon_candidate in recon_candidates:
            recon_candidate = _required_mapping(
                raw_recon_candidate,
                "recon candidate query",
                failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
            )
            _required_text(
                recon_candidate,
                "dimension_id",
                failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
            )
            _required_text(
                recon_candidate,
                "candidate_query_text",
                limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS["recon_candidate_query"],
                failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
            )
            _required_text(
                recon_candidate,
                "query_kind",
                failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
            )


def _contract_amendment_candidates(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    candidates: list[dict[str, Any]] = []
    for item in _required_sequence(value, "contract_amendment_candidates"):
        mapping = _required_mapping(item, "contract amendment candidate")
        candidates.append(
            _without_empty(
                {
                    "candidate_id": _optional_model_text(mapping, "candidate_id"),
                    "operation_kind": _optional_model_text(mapping, "operation_kind"),
                    "summary": _optional_model_text(
                        mapping,
                        "summary",
                        limit=SEARCH_PLANNER_MODEL_TEXT_LIMITS[
                            "contract_amendment_candidate_summary"
                        ],
                    ),
                    "proposal_only": True,
                    "deferred": True,
                    "accepted_authority": False,
                    "metadata": _safe_metadata(mapping.get("metadata")),
                }
            )
        )
    return candidates


def _validate_component_refs(
    *,
    answer_components: Sequence[Mapping[str, Any]],
    source_obligations: Sequence[Mapping[str, Any]],
    component_search_requirements: Sequence[Mapping[str, Any]],
    slot_ids: set[str],
    component_ids: set[str],
    obligation_ids: set[str],
) -> None:
    direct_required_component_ids = {
        str(component["component_id"])
        for component in answer_components
        if component.get("requirement_posture") == "required"
        and "direct" in (component.get("allowed_support_kinds") or ())
    }
    primary_count_by_component = {component_id: 0 for component_id in direct_required_component_ids}
    for component in answer_components:
        component_id = str(component["component_id"])
        for slot_id in component.get("semantic_slot_ids") or ():
            if slot_id not in slot_ids:
                raise SearchPlannerModelAdapterError(
                    f"component {component_id} references missing slot {slot_id}",
                    failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
                )
        for obligation_id in component.get("source_obligation_candidate_ids") or ():
            if obligation_id not in obligation_ids:
                raise SearchPlannerModelAdapterError(
                    f"component {component_id} references missing source obligation {obligation_id}",
                    failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
                )
        dependency_ids = list(component.get("dependency_component_ids") or ())
        if len(dependency_ids) != len(set(dependency_ids)):
            raise SearchPlannerModelAdapterError(
                f"component {component_id} contains duplicate component dependencies",
                failure_code=(_FailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH),
            )
        for dependency_id in dependency_ids:
            if dependency_id not in component_ids:
                raise SearchPlannerModelAdapterError(
                    f"component {component_id} depends on missing component {dependency_id}",
                    failure_code=(_FailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH),
                )
            if dependency_id == component_id:
                raise SearchPlannerModelAdapterError(
                    f"component {component_id} cannot depend on itself",
                    failure_code=(_FailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH),
                )
    for obligation in source_obligations:
        obligation_id = str(obligation["candidate_id"])
        for component_id in obligation.get("component_candidate_ids") or ():
            if component_id not in component_ids:
                raise SearchPlannerModelAdapterError(
                    f"source obligation {obligation_id} references missing component {component_id}",
                    failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
                )
    for requirement in component_search_requirements:
        component_id = str(requirement["component_id"])
        if component_id not in component_ids:
            raise SearchPlannerModelAdapterError(
                f"component search requirement references missing component {component_id}",
                failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
            )
        component = next(item for item in answer_components if item.get("component_id") == component_id)
        if tuple(component.get("allowed_support_kinds") or ()) == ("inferred",):
            raise SearchPlannerModelAdapterError(
                f"inferred-only component {component_id} cannot own component search requirements",
                failure_code=(_FailureCode.INVALID_COMPONENT_PURPOSE_OR_SOURCE_TARGET_SEPARATION),
            )
        for obligation_id in requirement.get("source_obligation_candidate_ids") or ():
            if obligation_id not in obligation_ids:
                raise SearchPlannerModelAdapterError(
                    f"component search requirement references missing source obligation {obligation_id}",
                    failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
                )
        metadata = requirement.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        for strategy in metadata.get("query_strategy_candidates") or ():
            if not isinstance(strategy, Mapping):
                continue
            strategy_id = str(strategy.get("strategy_id") or "")
            if strategy.get("candidate_kind") == "primary" and component_id in primary_count_by_component:
                primary_count_by_component[component_id] += 1
            for obligation_id in strategy.get("source_obligation_candidate_ids") or ():
                if obligation_id not in obligation_ids:
                    raise SearchPlannerModelAdapterError(
                        f"query strategy {strategy_id} references missing source obligation {obligation_id}",
                        failure_code=(_FailureCode.INVALID_ID_OR_CROSS_REFERENCE),
                    )
    invalid_primary_counts = {
        component_id: count for component_id, count in primary_count_by_component.items() if count != 1
    }
    if invalid_primary_counts:
        details = ", ".join(f"{component_id}={count}" for component_id, count in sorted(invalid_primary_counts.items()))
        raise SearchPlannerModelAdapterError(
            "each required component requires exactly one primary query strategy: " + details,
            failure_code=(_FailureCode.INVALID_QUERY_STRATEGY_METADATA),
        )


def _reject_unsafe_payload(value: Any) -> None:
    keys = _collect_keys(value)
    sensitive = sorted(key for key in keys if _is_sensitive_key(key))
    if sensitive:
        raise SearchPlannerModelAdapterError(
            "search planner model output contains raw/private fields: " + ", ".join(sensitive),
            failure_code=(_FailureCode.PRIVACY_OR_RAW_MATERIAL_VIOLATION),
        )
    forbidden = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if forbidden:
        raise SearchPlannerModelAdapterError(
            "search planner model output contains closed authority fields: " + ", ".join(forbidden),
            failure_code=(_FailureCode.CLOSED_AUTHORITY_VIOLATION),
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SearchPlannerModelAdapterError(
            "search planner model output opens closed runtime surfaces: " + ", ".join(dangerous),
            failure_code=(_FailureCode.CLOSED_AUTHORITY_VIOLATION),
        )


def _reject_executing_requirement(value: Mapping[str, Any]) -> None:
    for key in (
        "must_not_execute",
        "subordinate_to_answer_contract",
        "search_executed",
        "fetch_read_retrieval_behavior_changed",
        "source_obligation_satisfied",
        "evidence_admitted",
        "citation_eligible",
    ):
        if key not in value:
            continue
        if key == "must_not_execute" and value.get(key) is not True:
            raise SearchPlannerModelAdapterError(
                "component search requirement claims executable search",
                failure_code=(_FailureCode.CLOSED_AUTHORITY_VIOLATION),
            )
        if key == "subordinate_to_answer_contract" and value.get(key) is not True:
            raise SearchPlannerModelAdapterError(
                "component search requirement is not subordinate",
                failure_code=(_FailureCode.LINEAGE_OR_BINDING_FAILURE),
            )
        if key not in {"must_not_execute", "subordinate_to_answer_contract"} and value.get(key) is True:
            raise SearchPlannerModelAdapterError(
                "component search requirement claims closed surface execution",
                failure_code=(_FailureCode.CLOSED_AUTHORITY_VIOLATION),
            )


def _planner_model_metadata(
    *,
    prompt_meta: Mapping[str, Any],
    provider: str | None,
    model: str | None,
    effort: str,
    use_reasoning: bool,
) -> dict[str, Any]:
    return {
        "planner_model_adapter_schema_version": SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION,
        "planner_model_prompt_schema_version": SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION,
        "prompt_hash": _clean_text(prompt_meta.get("prompt_hash"), limit=128),
        "prompt_length": int(prompt_meta.get("prompt_length") or 0),
        "provider": _clean_text(provider),
        "model": _clean_text(model),
        "effort": _clean_text(effort),
        "use_reasoning": bool(use_reasoning),
        "require_json": True,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "provider_payload_retained": False,
        "model_adapter_enabled": True,
    }


def _required_mapping(
    value: Any,
    label: str,
    *,
    failure_code: SearchPlannerModelAdapterFailureCode = (_FailureCode.INVALID_NESTED_TYPE),
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SearchPlannerModelAdapterError(
            f"{label} must be a JSON object",
            failure_code=failure_code,
        )
    return value


def _required_sequence(
    value: Any,
    label: str,
    *,
    failure_code: SearchPlannerModelAdapterFailureCode = (_FailureCode.INVALID_NESTED_TYPE),
) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise SearchPlannerModelAdapterError(
            f"{label} must be a JSON array",
            failure_code=failure_code,
        )
    return list(value)


def _required_text(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int = SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
    failure_code: SearchPlannerModelAdapterFailureCode | None = None,
) -> str:
    if key not in mapping:
        raise SearchPlannerModelAdapterError(
            f"missing required field: {key}",
            failure_code=(failure_code or _FailureCode.MISSING_REQUIRED_NESTED_FIELD),
        )
    value = _model_visible_text(mapping[key])
    raw_text = " ".join(value.strip().split())
    if len(raw_text) > limit:
        raise SearchPlannerModelAdapterError(
            f"required field exceeds bounded length: {key}",
            failure_code=(failure_code or _FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
        )
    text = _clean_text(value, limit=limit)
    if not text:
        raise SearchPlannerModelAdapterError(
            f"required field is empty: {key}",
            failure_code=(failure_code or _FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
        )
    return text


def _required_enum_text(
    mapping: Mapping[str, Any],
    key: str,
    *,
    allowed: frozenset[str],
    failure_code: SearchPlannerModelAdapterFailureCode = (_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
) -> str:
    text = _required_text(
        mapping,
        key,
        failure_code=failure_code,
    )
    if text not in allowed:
        raise SearchPlannerModelAdapterError(
            f"unsupported value for {key}: {text}",
            failure_code=failure_code,
        )
    return text


def _required_text_list(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int = SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
    allow_empty: bool = False,
    failure_code: SearchPlannerModelAdapterFailureCode | None = None,
) -> list[str]:
    if key not in mapping:
        raise SearchPlannerModelAdapterError(
            f"missing required field: {key}",
            failure_code=(failure_code or _FailureCode.MISSING_REQUIRED_NESTED_FIELD),
        )
    items = _required_sequence(
        mapping.get(key),
        key,
        failure_code=_FailureCode.INVALID_NESTED_TYPE,
    )
    out = _optional_text_list(
        items,
        limit=limit,
        failure_code=failure_code,
    )
    if not out and not allow_empty:
        raise SearchPlannerModelAdapterError(
            f"required field must contain text values: {key}",
            failure_code=(failure_code or _FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
        )
    return out


def _required_support_kind_list(mapping: Mapping[str, Any]) -> list[str]:
    key = "allowed_support_kinds"
    if key not in mapping:
        raise SearchPlannerModelAdapterError(
            f"missing required field: {key}",
            failure_code=_FailureCode.MISSING_REQUIRED_NESTED_FIELD,
        )
    items = _required_sequence(
        mapping.get(key),
        key,
        failure_code=_FailureCode.INVALID_NESTED_TYPE,
    )
    if not items:
        raise SearchPlannerModelAdapterError(
            "answer component requires allowed support kinds",
            failure_code=_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE,
        )

    support_kinds: list[str] = []
    for item in items:
        text_item = _model_visible_text(item)
        raw_text = " ".join(text_item.strip().split())
        if len(raw_text) > SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"]:
            raise SearchPlannerModelAdapterError(
                "answer component has invalid allowed support kinds",
                failure_code=_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE,
            )
        support_kind = _clean_text(text_item)
        if support_kind not in _SUPPORT_KINDS:
            raise SearchPlannerModelAdapterError(
                "answer component has invalid allowed support kinds",
                failure_code=_FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE,
            )
        support_kinds.append(support_kind)
    return support_kinds


def _optional_text_list(
    value: Any,
    *,
    limit: int = SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
    failure_code: SearchPlannerModelAdapterFailureCode | None = None,
) -> list[str]:
    if value is _MISSING:
        return []
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise SearchPlannerModelAdapterError(
            "expected an array of strings",
            failure_code=_FailureCode.INVALID_NESTED_TYPE,
        )
    out: list[str] = []
    for item in value:
        text_item = _model_visible_text(item)
        raw_text = " ".join(text_item.strip().split())
        if len(raw_text) > limit:
            raise SearchPlannerModelAdapterError(
                "array text value exceeds bounded length",
                failure_code=(failure_code or _FailureCode.INVALID_ENUM_OR_BOUNDED_VALUE),
            )
        text = _clean_text(text_item, limit=limit)
        if text:
            out.append(text)
    return out


def _optional_model_text(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int = SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
) -> str | None:
    if key not in mapping:
        return None
    return _clean_text(_model_visible_text(mapping[key]), limit=limit)


def _model_visible_text(value: Any) -> str:
    if not isinstance(value, str):
        raise SearchPlannerModelAdapterError(
            "model-visible text value must be a JSON string",
            failure_code=_FailureCode.INVALID_NESTED_TYPE,
        )
    return value


def _required_non_negative_int(mapping: Mapping[str, Any], key: str) -> int:
    if key not in mapping or isinstance(mapping.get(key), bool):
        raise SearchPlannerModelAdapterError(
            f"missing required integer field: {key}",
            failure_code=(_FailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH),
        )
    try:
        value = int(mapping.get(key))
    except (TypeError, ValueError) as exc:
        raise SearchPlannerModelAdapterError(
            f"required field must be an integer: {key}",
            failure_code=(_FailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH),
        ) from exc
    if value < 0:
        raise SearchPlannerModelAdapterError(
            f"required field must be non-negative: {key}",
            failure_code=(_FailureCode.INVALID_DEPENDENCY_OR_INFERENCE_DEPTH),
        )
    return value


def _safe_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise SearchPlannerModelAdapterError(
            "metadata must be a JSON object",
            failure_code=(_FailureCode.INVALID_NESTED_TYPE),
        )
    _reject_unsafe_payload(value)
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 12:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_text(key, limit=120)
            if not clean_key or _is_sensitive_key(clean_key):
                continue
            out[clean_key] = _json_safe(value[key], depth=depth + 1)
        return out
    if isinstance(value, tuple | list | set | frozenset):
        items = list(value)
        if isinstance(value, set | frozenset):
            items = sorted(items, key=str)
        return [_json_safe(item, depth=depth + 1) for item in items]
    return _clean_text(value, limit=300)


def _clean_text(
    value: Any,
    *,
    limit: int = SEARCH_PLANNER_MODEL_TEXT_LIMITS["default_text"],
) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PRIVATE_VALUE_MARKERS):
        return "[redacted]"
    return text[:limit]


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None and value != [] and value != {}}


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _normalize_key(key)
            if token in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(token)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _is_sensitive_key(key: Any) -> bool:
    normalized = _normalize_key(key)
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


__all__ = [
    "SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION",
    "SearchPlannerModelAdapter",
    "SearchPlannerModelAdapterError",
    "SearchPlannerModelAdapterFailureCode",
    "SearchPlannerModelAdapterFailureMetadata",
    "SearchPlannerModelAdapterFailureStage",
    "validate_and_sanitize_model_output",
]
