"""Explicit model-backed SearchPlanner adapter for AG-SEARCH-PLANNER-MODEL-01.

The adapter is live-capable only when constructed with an injected callable and
an explicit enabled/licensed flag. It imports no provider client and stores no
raw prompt, model response, or provider payload.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from core.search_planner_model_prompt import (
    SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION,
    SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
    build_search_planner_model_prompt,
    prompt_metadata,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_MAX_ANSWER_COMPONENTS,
    SearchPlannerRuntimeError,
)
from core.search_work_plan import SourceObligationKind, SourceObligationStrictness

SEARCH_PLANNER_MODEL_ADAPTER_SCHEMA_VERSION = "search_planner_model_adapter_ag_search_planner_model_01_v1"

_TOP_LEVEL_REQUIRED = (
    "question_meaning_summary",
    "requested_output",
    "semantic_slots",
    "answer_components",
    "source_obligation_candidates",
    "component_search_requirements",
    "material_ambiguity_posture",
    "mandatory_caveats",
    "prohibited_upgrades",
    "normalization_obligations",
    "assumptions",
    "unsupported_or_deferred_outputs",
)

_SEMANTIC_SLOT_KINDS = frozenset(
    {
        "entity",
        "variant",
        "metric",
        "numerator",
        "denominator",
        "time_period",
        "geography",
        "currency_basis",
        "inflation_basis",
        "configuration",
        "route_profile",
        "load_factor",
        "direct_vs_computed",
        "source_basis",
        "unknown_or_other",
    }
)
_SEMANTIC_SLOT_STATUSES = frozenset(
    {"explicit", "implied", "ambiguous", "unresolved"}
)
_MATERIALITY_VALUES = frozenset({"material", "non_material", "unknown"})
_REQUIREMENT_POSTURES = frozenset({"required", "conditional", "optional"})
_SUPPORT_KINDS = frozenset({"direct", "inferred", "computed"})
_PARTIAL_ANSWER_POLICIES = frozenset(
    {
        "qualify_visible_gap",
        "block_if_required_unsatisfied",
        "allow_if_optional_only",
    }
)
_QUERY_CANDIDATE_KINDS = frozenset({"primary", "secondary"})
_QUERY_ROLES = frozenset(
    {
        "initial",
        "official_bias",
        "canonical_bias",
        "recency",
        "disambiguation",
        "recon_rewrite",
    }
)
_RECON_POSTURES = frozenset({"not_needed", "optional", "required"})
_SOURCE_OBLIGATION_KINDS = frozenset(item.value for item in SourceObligationKind)
_SOURCE_OBLIGATION_STRICTNESSES = frozenset(
    item.value for item in SourceObligationStrictness
)
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


class SearchPlannerModelAdapterError(SearchPlannerRuntimeError):
    """Raised when the model adapter fails closed before planner observation."""


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
        if not self.enabled or not self.licensed or self.ask_model is None:
            raise SearchPlannerModelAdapterError("search planner model adapter is not explicitly enabled")
        if not str(self.provider or "").strip() or not str(self.model or "").strip():
            raise SearchPlannerModelAdapterError(
                "selected search planner provider and model must be available"
            )

        try:
            prompt = build_search_planner_model_prompt(planner_input)
            metadata = prompt_metadata(prompt)
        except Exception as exc:
            raise SearchPlannerModelAdapterError(
                f"search planner model input failed closed: {type(exc).__name__}"
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
                f"search planner model call failed closed: {type(exc).__name__}"
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
                f"search planner model output cleaning failed closed: {type(exc).__name__}"
            ) from exc
    try:
        parsed = json.loads(text)
    except Exception as exc:
        raise SearchPlannerModelAdapterError("search planner model output was not valid JSON") from exc
    if not isinstance(parsed, Mapping):
        raise SearchPlannerModelAdapterError("search planner model output must be a JSON object")
    return parsed


def validate_and_sanitize_model_output(model_output: Mapping[str, Any]) -> dict[str, Any]:
    """Return a runtime-compatible planner proposal or fail closed."""

    _reject_unsafe_payload(model_output)
    missing = [field for field in _TOP_LEVEL_REQUIRED if field not in model_output]
    if missing:
        raise SearchPlannerModelAdapterError(
            "search planner model output missing required fields: " + ", ".join(missing)
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
        "question_meaning_summary": _required_text(model_output, "question_meaning_summary", limit=420),
        "requested_output": _required_text(model_output, "requested_output", limit=300),
        "semantic_slots": semantic_slots,
        "answer_components": answer_components,
        "source_obligation_candidates": source_obligations,
        "component_search_requirements": component_requirements,
        "material_ambiguity_posture": _required_text(
            model_output,
            "material_ambiguity_posture",
            limit=120,
        ),
        "mandatory_caveats": _required_text_list(model_output, "mandatory_caveats", limit=260, allow_empty=True),
        "prohibited_upgrades": _required_text_list(model_output, "prohibited_upgrades", limit=260, allow_empty=True),
        "normalization_obligations": _required_text_list(
            model_output,
            "normalization_obligations",
            limit=260,
            allow_empty=True,
        ),
        "assumptions": _required_text_list(model_output, "assumptions", limit=260, allow_empty=True),
        "unsupported_or_deferred_outputs": _required_text_list(
            model_output,
            "unsupported_or_deferred_outputs",
            limit=260,
            allow_empty=True,
        ),
        "contract_amendment_candidates": _contract_amendment_candidates(
            model_output.get("contract_amendment_candidates")
        ),
    }


def _semantic_slots(value: Any) -> list[dict[str, Any]]:
    items = _required_sequence(value, "semantic_slots")
    if not items:
        raise SearchPlannerModelAdapterError("search planner model output requires at least one semantic slot")
    slots: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        mapping = _required_mapping(item, "semantic slot")
        slot_id = _required_text(mapping, "slot_id")
        if slot_id in seen:
            raise SearchPlannerModelAdapterError(f"duplicate semantic slot id: {slot_id}")
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
                f"material semantic slot {slot_id} requires user_confirmation_required"
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
                    "candidate_values": _optional_text_list(mapping.get("candidate_values"), limit=220),
                    "selected_value": _clean_text(mapping.get("selected_value"), limit=220),
                    "materiality": materiality,
                    "user_confirmation_required": user_confirmation_required,
                    "normalization_notes": _optional_text_list(mapping.get("normalization_notes"), limit=260),
                    "metadata": _safe_metadata(mapping.get("metadata")),
                }
            )
        )
    return slots


def _answer_components(value: Any) -> list[dict[str, Any]]:
    items = _required_sequence(value, "answer_components")
    if not items:
        raise SearchPlannerModelAdapterError("search planner model output requires at least one answer component")
    if len(items) > SEARCH_PLANNER_MAX_ANSWER_COMPONENTS:
        raise SearchPlannerModelAdapterError(
            "search planner model output exceeds the five-component acceptance ceiling"
        )
    components: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        mapping = _required_mapping(item, "answer component")
        component_id = _required_text(mapping, "component_id")
        if component_id in seen:
            raise SearchPlannerModelAdapterError(f"duplicate answer component id: {component_id}")
        seen.add(component_id)
        source_obligation_ids = _required_text_list(mapping, "source_obligation_candidate_ids")
        if not source_obligation_ids:
            raise SearchPlannerModelAdapterError(
                f"answer component {component_id} requires source obligation candidates"
            )
        requirement_posture = _required_enum_text(
            mapping,
            "requirement_posture",
            allowed=_REQUIREMENT_POSTURES,
        )
        allowed_support_kinds = _required_text_list(
            mapping,
            "allowed_support_kinds",
        )
        unsupported_kinds = sorted(set(allowed_support_kinds) - _SUPPORT_KINDS)
        if unsupported_kinds:
            raise SearchPlannerModelAdapterError(
                "answer component contains unsupported support kinds: "
                + ", ".join(unsupported_kinds)
            )
        partial_answer_policy = _clean_text(mapping.get("partial_answer_policy"))
        if (
            partial_answer_policy is not None
            and partial_answer_policy not in _PARTIAL_ANSWER_POLICIES
        ):
            raise SearchPlannerModelAdapterError(
                f"unsupported partial answer policy: {partial_answer_policy}"
            )
        components.append(
            _without_empty(
                {
                    "component_id": component_id,
                    "component_revision": _required_text(mapping, "component_revision"),
                    "user_facing_label": _required_text(mapping, "user_facing_label", limit=180),
                    "user_facing_question": _required_text(mapping, "user_facing_question", limit=400),
                    "requirement_posture": requirement_posture,
                    "acceptance_criteria": _required_text_list(mapping, "acceptance_criteria", limit=320),
                    "semantic_slot_ids": _required_text_list(mapping, "semantic_slot_ids"),
                    "source_obligation_candidate_ids": source_obligation_ids,
                    "allowed_support_kinds": allowed_support_kinds,
                    "max_inference_depth": _required_non_negative_int(mapping, "max_inference_depth"),
                    "normalization_policy": _clean_text(mapping.get("normalization_policy"), limit=300),
                    "calculation_policy": _clean_text(mapping.get("calculation_policy"), limit=300),
                    "dependency_component_ids": _optional_text_list(mapping.get("dependency_component_ids")),
                    "partial_answer_policy": partial_answer_policy,
                    "mandatory_caveats": _optional_text_list(mapping.get("mandatory_caveats"), limit=260),
                    "prohibited_upgrades": _optional_text_list(mapping.get("prohibited_upgrades"), limit=260),
                    "materiality": _required_enum_text(
                        mapping,
                        "materiality",
                        allowed=_MATERIALITY_VALUES,
                    ),
                    "metadata": _safe_metadata(mapping.get("metadata")),
                }
            )
        )
    if not any(
        component.get("requirement_posture") == "required"
        for component in components
    ):
        raise SearchPlannerModelAdapterError(
            "search planner model output requires at least one required answer component"
        )
    return components


def _source_obligation_candidates(value: Any) -> list[dict[str, Any]]:
    items = _required_sequence(value, "source_obligation_candidates")
    if not items:
        raise SearchPlannerModelAdapterError("search planner model output requires source obligation candidates")
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        mapping = _required_mapping(item, "source obligation candidate")
        candidate_id = _required_text(mapping, "candidate_id")
        if candidate_id in seen:
            raise SearchPlannerModelAdapterError(f"duplicate source obligation candidate id: {candidate_id}")
        seen.add(candidate_id)
        strictness = _clean_text(mapping.get("strictness"))
        if strictness is not None and strictness not in _SOURCE_OBLIGATION_STRICTNESSES:
            raise SearchPlannerModelAdapterError(
                f"unsupported value for strictness: {strictness}"
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
                    "component_candidate_ids": _required_text_list(mapping, "component_candidate_ids"),
                    "strictness": strictness,
                    "metadata": _safe_metadata(mapping.get("metadata")),
                }
            )
        )
    return candidates


def _component_search_requirements(value: Any) -> list[dict[str, Any]]:
    items = _required_sequence(value, "component_search_requirements")
    if not items:
        raise SearchPlannerModelAdapterError("search planner model output requires component search requirements")
    requirements: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        mapping = _required_mapping(item, "component search requirement")
        _reject_executing_requirement(mapping)
        requirement_id = _required_text(mapping, "requirement_id")
        if requirement_id in seen:
            raise SearchPlannerModelAdapterError(f"duplicate component search requirement id: {requirement_id}")
        seen.add(requirement_id)
        raw_metadata = mapping.get("metadata")
        _validate_query_strategy_metadata(
            raw_metadata,
            component_id=_required_text(mapping, "component_id"),
        )
        requirements.append(
            _without_empty(
                {
                    "component_id": _required_text(mapping, "component_id"),
                    "requirement_id": requirement_id,
                    "requirement_summary": _required_text(mapping, "requirement_summary", limit=320),
                    "source_obligation_candidate_ids": _required_text_list(
                        mapping,
                        "source_obligation_candidate_ids",
                    ),
                    "preferred_source_kinds": _optional_text_list(mapping.get("preferred_source_kinds")),
                    "recency_requirement": _clean_text(mapping.get("recency_requirement"), limit=220),
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
            f"component {component_id} search requirement requires metadata"
        )
    candidates = _required_sequence(
        value.get("query_strategy_candidates"),
        "query_strategy_candidates",
    )
    if not candidates:
        raise SearchPlannerModelAdapterError(
            f"component {component_id} requires query strategy candidates"
        )
    seen_strategy_ids: set[str] = set()
    for raw_candidate in candidates:
        candidate = _required_mapping(raw_candidate, "query strategy candidate")
        forbidden = sorted(
            _collect_keys(candidate) & _FORBIDDEN_QUERY_AUTHORITY_KEYS
        )
        if forbidden:
            raise SearchPlannerModelAdapterError(
                "query strategy candidate selects forbidden provider/model authority: "
                + ", ".join(forbidden)
            )
        strategy_id = _required_text(candidate, "strategy_id")
        if strategy_id in seen_strategy_ids:
            raise SearchPlannerModelAdapterError(
                f"duplicate query strategy id: {strategy_id}"
            )
        seen_strategy_ids.add(strategy_id)
        candidate_component_id = _required_text(candidate, "component_id")
        if candidate_component_id != component_id:
            raise SearchPlannerModelAdapterError(
                f"query strategy {strategy_id} has stale component binding"
            )
        _required_enum_text(
            candidate,
            "candidate_kind",
            allowed=_QUERY_CANDIDATE_KINDS,
        )
        _required_text(candidate, "candidate_query_text", limit=300)
        _required_enum_text(
            candidate,
            "requested_role",
            allowed=_QUERY_ROLES,
        )
        if not _required_text_list(
            candidate,
            "source_obligation_candidate_ids",
        ):
            raise SearchPlannerModelAdapterError(
                f"query strategy {strategy_id} requires source obligations"
            )
        _required_text(
            candidate,
            "distinct_need_justification",
            limit=300,
        )
        recon = _required_mapping(
            candidate.get("recon_requirement"),
            "recon requirement",
        )
        _required_enum_text(
            recon,
            "posture",
            allowed=_RECON_POSTURES,
        )
        _required_text_list(
            recon,
            "unresolved_dimension_ids",
            allow_empty=True,
        )
        recon_candidates = _required_sequence(
            recon.get("candidate_queries"),
            "recon candidate_queries",
        )
        for raw_recon_candidate in recon_candidates:
            recon_candidate = _required_mapping(
                raw_recon_candidate,
                "recon candidate query",
            )
            _required_text(recon_candidate, "dimension_id")
            _required_text(
                recon_candidate,
                "candidate_query_text",
                limit=300,
            )
            _required_text(recon_candidate, "query_kind")


def _contract_amendment_candidates(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    candidates: list[dict[str, Any]] = []
    for item in _required_sequence(value, "contract_amendment_candidates"):
        mapping = _required_mapping(item, "contract amendment candidate")
        candidates.append(
            _without_empty(
                {
                    "candidate_id": _clean_text(mapping.get("candidate_id")),
                    "operation_kind": _clean_text(mapping.get("operation_kind")),
                    "summary": _clean_text(mapping.get("summary"), limit=260),
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
    required_component_ids = {
        str(component["component_id"])
        for component in answer_components
        if component.get("requirement_posture") == "required"
    }
    primary_count_by_component = {
        component_id: 0 for component_id in required_component_ids
    }
    for component in answer_components:
        component_id = str(component["component_id"])
        for slot_id in component.get("semantic_slot_ids") or ():
            if slot_id not in slot_ids:
                raise SearchPlannerModelAdapterError(f"component {component_id} references missing slot {slot_id}")
        for obligation_id in component.get("source_obligation_candidate_ids") or ():
            if obligation_id not in obligation_ids:
                raise SearchPlannerModelAdapterError(
                    f"component {component_id} references missing source obligation {obligation_id}"
                )
        dependency_ids = list(component.get("dependency_component_ids") or ())
        if len(dependency_ids) != len(set(dependency_ids)):
            raise SearchPlannerModelAdapterError(
                f"component {component_id} contains duplicate component dependencies"
            )
        for dependency_id in dependency_ids:
            if dependency_id not in component_ids:
                raise SearchPlannerModelAdapterError(
                    f"component {component_id} depends on missing component {dependency_id}"
                )
            if dependency_id == component_id:
                raise SearchPlannerModelAdapterError(
                    f"component {component_id} cannot depend on itself"
                )
    for obligation in source_obligations:
        obligation_id = str(obligation["candidate_id"])
        for component_id in obligation.get("component_candidate_ids") or ():
            if component_id not in component_ids:
                raise SearchPlannerModelAdapterError(
                    f"source obligation {obligation_id} references missing component {component_id}"
                )
    for requirement in component_search_requirements:
        component_id = str(requirement["component_id"])
        if component_id not in component_ids:
            raise SearchPlannerModelAdapterError(
                f"component search requirement references missing component {component_id}"
            )
        for obligation_id in requirement.get("source_obligation_candidate_ids") or ():
            if obligation_id not in obligation_ids:
                raise SearchPlannerModelAdapterError(
                    f"component search requirement references missing source obligation {obligation_id}"
                )
        metadata = requirement.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        for strategy in metadata.get("query_strategy_candidates") or ():
            if not isinstance(strategy, Mapping):
                continue
            strategy_id = str(strategy.get("strategy_id") or "")
            if (
                strategy.get("candidate_kind") == "primary"
                and component_id in primary_count_by_component
            ):
                primary_count_by_component[component_id] += 1
            for obligation_id in strategy.get(
                "source_obligation_candidate_ids"
            ) or ():
                if obligation_id not in obligation_ids:
                    raise SearchPlannerModelAdapterError(
                        f"query strategy {strategy_id} references missing source obligation {obligation_id}"
                    )
    invalid_primary_counts = {
        component_id: count
        for component_id, count in primary_count_by_component.items()
        if count != 1
    }
    if invalid_primary_counts:
        details = ", ".join(
            f"{component_id}={count}"
            for component_id, count in sorted(invalid_primary_counts.items())
        )
        raise SearchPlannerModelAdapterError(
            "each required component requires exactly one primary query strategy: "
            + details
        )


def _reject_unsafe_payload(value: Any) -> None:
    keys = _collect_keys(value)
    sensitive = sorted(key for key in keys if _is_sensitive_key(key))
    if sensitive:
        raise SearchPlannerModelAdapterError(
            "search planner model output contains raw/private fields: " + ", ".join(sensitive)
        )
    forbidden = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if forbidden:
        raise SearchPlannerModelAdapterError(
            "search planner model output contains closed authority fields: " + ", ".join(forbidden)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SearchPlannerModelAdapterError(
            "search planner model output opens closed runtime surfaces: " + ", ".join(dangerous)
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
            raise SearchPlannerModelAdapterError("component search requirement claims executable search")
        if key == "subordinate_to_answer_contract" and value.get(key) is not True:
            raise SearchPlannerModelAdapterError("component search requirement is not subordinate")
        if key not in {"must_not_execute", "subordinate_to_answer_contract"} and value.get(key) is True:
            raise SearchPlannerModelAdapterError("component search requirement claims closed surface execution")


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


def _required_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SearchPlannerModelAdapterError(f"{label} must be a JSON object")
    return value


def _required_sequence(value: Any, label: str) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise SearchPlannerModelAdapterError(f"{label} must be a JSON array")
    return list(value)


def _required_text(mapping: Mapping[str, Any], key: str, *, limit: int = 160) -> str:
    if key not in mapping:
        raise SearchPlannerModelAdapterError(f"missing required field: {key}")
    raw_text = " ".join(str(mapping.get(key) or "").strip().split())
    if len(raw_text) > limit:
        raise SearchPlannerModelAdapterError(
            f"required field exceeds bounded length: {key}"
        )
    text = _clean_text(mapping.get(key), limit=limit)
    if not text:
        raise SearchPlannerModelAdapterError(f"required field is empty: {key}")
    return text


def _required_enum_text(
    mapping: Mapping[str, Any],
    key: str,
    *,
    allowed: frozenset[str],
) -> str:
    text = _required_text(mapping, key)
    if text not in allowed:
        raise SearchPlannerModelAdapterError(
            f"unsupported value for {key}: {text}"
        )
    return text


def _required_text_list(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int = 160,
    allow_empty: bool = False,
) -> list[str]:
    if key not in mapping:
        raise SearchPlannerModelAdapterError(f"missing required field: {key}")
    items = _required_sequence(mapping.get(key), key)
    out = _optional_text_list(items, limit=limit)
    if not out and not allow_empty:
        raise SearchPlannerModelAdapterError(f"required field must contain text values: {key}")
    return out


def _optional_text_list(value: Any, *, limit: int = 160) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise SearchPlannerModelAdapterError("expected an array of strings")
    out: list[str] = []
    for item in value:
        raw_text = " ".join(str(item or "").strip().split())
        if len(raw_text) > limit:
            raise SearchPlannerModelAdapterError(
                "array text value exceeds bounded length"
            )
        text = _clean_text(item, limit=limit)
        if text:
            out.append(text)
    return out


def _required_non_negative_int(mapping: Mapping[str, Any], key: str) -> int:
    if key not in mapping or isinstance(mapping.get(key), bool):
        raise SearchPlannerModelAdapterError(f"missing required integer field: {key}")
    try:
        value = int(mapping.get(key))
    except (TypeError, ValueError) as exc:
        raise SearchPlannerModelAdapterError(f"required field must be an integer: {key}") from exc
    if value < 0:
        raise SearchPlannerModelAdapterError(f"required field must be non-negative: {key}")
    return value


def _safe_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise SearchPlannerModelAdapterError("metadata must be a JSON object")
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


def _clean_text(value: Any, *, limit: int = 160) -> str | None:
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
    "validate_and_sanitize_model_output",
]
