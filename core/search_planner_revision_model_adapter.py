"""Explicit model-shaped SearchPlannerRevision adapter.

The adapter is live-capable only when constructed with an injected callable and
explicit enabled/licensed flags. It imports no provider client and stores no raw
prompt, model response, or provider payload.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from core.search_planner_revision_model_prompt import (
    SEARCH_PLANNER_REVISION_MODEL_PROMPT_SCHEMA_VERSION,
    SEARCH_PLANNER_REVISION_MODEL_SYSTEM_PROMPT,
    build_search_planner_revision_model_prompt,
    prompt_metadata,
)
from core.search_planner_revision_runtime import SearchPlannerRevisionRuntimeError

SEARCH_PLANNER_REVISION_MODEL_ADAPTER_SCHEMA_VERSION = (
    "search_planner_revision_model_adapter_ag_search_planner_revision_01_v1"
)

_TOP_LEVEL_REQUIRED = (
    "revised_question_meaning_summary",
    "semantic_slot_updates",
    "answer_component_updates",
    "component_search_requirement_updates",
    "mandatory_caveats",
    "prohibited_upgrades",
    "normalization_obligations",
    "assumptions",
    "unresolved_ambiguities",
    "consumed_ambiguity_dimension_ids",
    "consumed_scout_hint_ids",
    "amendment_candidates",
    "closed_surface_flags",
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
        "raw_search_response",
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
        "current_answer_contract",
        "evidence",
        "evidence_ledger_admission",
        "final_answer",
        "final_answer_packet",
        "initial_answer_contract",
        "search_executor",
        "search_judgment_decision",
        "semantic_observation",
        "source_obligation_support",
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
        "live_provider_calls_executed",
        "live_validation_run",
        "model_called",
        "partial_answer_readiness_changed",
        "provider_called",
        "provider_search_behavior_changed",
        "query_plan_activated",
        "raw_model_response_retained",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "raw_trace_retained",
        "runtime_behavior_changed",
        "scout_hints_are_evidence",
        "scout_runtime_activated",
        "search_executed",
        "search_executor_runtime_activated",
        "search_judgment_decided",
        "search_work_plan_activated",
        "search_work_plan_constructed",
        "source_obligation_satisfied",
        "sufficiency_decided",
    }
)

_FORBIDDEN_OPERATION_KINDS = frozenset(
    {
        "mark_requirement_satisfied",
        "mark_source_obligation_satisfied",
        "resolve_slot",
    }
)
_ALLOWED_OPERATION_KINDS = frozenset({"add_caveat", "strengthen_source_obligation"})


class SearchPlannerRevisionModelAdapterError(SearchPlannerRevisionRuntimeError):
    """Raised when the model adapter fails closed before revision observation."""


@dataclass(frozen=True, slots=True)
class SearchPlannerRevisionModelAdapter:
    """Model-shaped implementation of ``SearchPlannerRevisionAdapter``."""

    revision_model_callable: Callable[..., Any] | None
    clean_json_response: Callable[[str], str] | None = None
    provider: str | None = None
    model: str | None = None
    effort: str = "low"
    use_reasoning: bool = True
    max_tokens: int | None = None
    enabled: bool = False
    licensed: bool = False

    def produce(self, revision_input: Mapping[str, Any]) -> Mapping[str, Any]:
        if (
            not self.enabled
            or not self.licensed
            or self.revision_model_callable is None
        ):
            raise SearchPlannerRevisionModelAdapterError(
                "search planner revision model adapter is not explicitly enabled"
            )

        prompt = build_search_planner_revision_model_prompt(revision_input)
        metadata = prompt_metadata(prompt)
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
            raw = self.revision_model_callable(
                prompt,
                SEARCH_PLANNER_REVISION_MODEL_SYSTEM_PROMPT,
                **model_kwargs,
            )
        except Exception as exc:
            raise SearchPlannerRevisionModelAdapterError(
                f"search planner revision model call failed closed: {type(exc).__name__}"
            ) from exc

        parsed = _parse_model_output(raw, clean_json_response=self.clean_json_response)
        proposal = validate_and_sanitize_model_output(parsed)
        proposal["planner_revision_model_metadata"] = _planner_revision_model_metadata(
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
        text = clean_json_response(text)
    try:
        parsed = json.loads(text)
    except Exception as exc:
        raise SearchPlannerRevisionModelAdapterError(
            "search planner revision model output was not valid JSON"
        ) from exc
    if not isinstance(parsed, Mapping):
        raise SearchPlannerRevisionModelAdapterError(
            "search planner revision model output must be a JSON object"
        )
    return parsed


def validate_and_sanitize_model_output(model_output: Mapping[str, Any]) -> dict[str, Any]:
    """Return a runtime-compatible planner revision proposal or fail closed."""

    _reject_unsafe_payload(model_output)
    missing = [field for field in _TOP_LEVEL_REQUIRED if field not in model_output]
    if missing:
        raise SearchPlannerRevisionModelAdapterError(
            "search planner revision model output missing required fields: "
            + ", ".join(missing)
        )

    return {
        "revised_question_meaning_summary": _required_text(
            model_output,
            "revised_question_meaning_summary",
            limit=500,
        ),
        "semantic_slot_updates": _mapping_list(
            model_output.get("semantic_slot_updates"),
            "semantic_slot_updates",
        ),
        "answer_component_updates": _mapping_list(
            model_output.get("answer_component_updates"),
            "answer_component_updates",
        ),
        "component_search_requirement_updates": _mapping_list(
            model_output.get("component_search_requirement_updates"),
            "component_search_requirement_updates",
        ),
        "mandatory_caveats": _required_text_list(
            model_output,
            "mandatory_caveats",
            limit=360,
            allow_empty=True,
        ),
        "prohibited_upgrades": _required_text_list(
            model_output,
            "prohibited_upgrades",
            limit=260,
            allow_empty=True,
        ),
        "normalization_obligations": _required_text_list(
            model_output,
            "normalization_obligations",
            limit=260,
            allow_empty=True,
        ),
        "assumptions": _required_text_list(
            model_output,
            "assumptions",
            limit=260,
            allow_empty=True,
        ),
        "unresolved_ambiguities": _mapping_list(
            model_output.get("unresolved_ambiguities"),
            "unresolved_ambiguities",
        ),
        "consumed_ambiguity_dimension_ids": _required_text_list(
            model_output,
            "consumed_ambiguity_dimension_ids",
        ),
        "consumed_scout_hint_ids": _required_text_list(
            model_output,
            "consumed_scout_hint_ids",
            allow_empty=True,
        ),
        "amendment_candidates": _amendment_candidates(
            model_output.get("amendment_candidates")
        ),
        "closed_surface_flags": _false_flag_mapping(
            model_output.get("closed_surface_flags")
        ),
        "revised_source_obligation_candidates": _mapping_list(
            model_output.get("revised_source_obligation_candidates"),
            "revised_source_obligation_candidates",
            allow_missing=True,
        ),
        "source_obligation_focus_updates": _mapping_list(
            model_output.get("source_obligation_focus_updates"),
            "source_obligation_focus_updates",
            allow_missing=True,
        ),
        "planner_revision_notes": _optional_text_list(
            model_output.get("planner_revision_notes"),
            limit=300,
        ),
        "confidence_posture": _clean_text(
            model_output.get("confidence_posture"),
            limit=120,
        ),
        "revision_posture": _clean_text(
            model_output.get("revision_posture"),
            limit=120,
        ),
    }


def _amendment_candidates(value: Any) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in _required_sequence(value, "amendment_candidates"):
        mapping = _required_mapping(item, "amendment candidate")
        operation_kind = _clean_text(mapping.get("operation_kind")) or "add_caveat"
        normalized_kind = _normalize_key(operation_kind)
        if normalized_kind in _FORBIDDEN_OPERATION_KINDS:
            raise SearchPlannerRevisionModelAdapterError(
                "search planner revision model output emits forbidden amendment operation: "
                + normalized_kind
            )
        if normalized_kind not in _ALLOWED_OPERATION_KINDS:
            raise SearchPlannerRevisionModelAdapterError(
                "search planner revision model output emits unsupported amendment operation: "
                + normalized_kind
            )
        candidate = {
            "candidate_id": _clean_text(mapping.get("candidate_id")),
            "operation_kind": normalized_kind,
            "caveat": _clean_text(mapping.get("caveat"), limit=360),
            "required_caveats": _optional_text_list(
                mapping.get("required_caveats"),
                limit=360,
            ),
            "summary": _clean_text(mapping.get("summary"), limit=300),
            "component_id": _clean_text(mapping.get("component_id")),
            "proposal_only": True,
            "passive": True,
            "scout_hints_are_evidence": False,
            "citation_eligible": False,
            "source_obligation_satisfied": False,
            "evidence_admitted": False,
            "contract_mutation_applied": False,
            "metadata": _safe_metadata(mapping.get("metadata")),
        }
        candidates.append(_without_empty(candidate))
    return candidates


def _reject_unsafe_payload(value: Any) -> None:
    keys = _collect_keys(value)
    sensitive = sorted(key for key in keys if _is_sensitive_key(key))
    if sensitive:
        raise SearchPlannerRevisionModelAdapterError(
            "search planner revision model output contains raw/private fields: "
            + ", ".join(sensitive)
        )
    forbidden = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if forbidden:
        raise SearchPlannerRevisionModelAdapterError(
            "search planner revision model output contains closed authority fields: "
            + ", ".join(forbidden)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SearchPlannerRevisionModelAdapterError(
            "search planner revision model output opens closed runtime surfaces: "
            + ", ".join(dangerous)
        )


def _planner_revision_model_metadata(
    *,
    prompt_meta: Mapping[str, Any],
    provider: str | None,
    model: str | None,
    effort: str,
    use_reasoning: bool,
) -> dict[str, Any]:
    return {
        "planner_revision_model_adapter_schema_version": (
            SEARCH_PLANNER_REVISION_MODEL_ADAPTER_SCHEMA_VERSION
        ),
        "planner_revision_model_prompt_schema_version": (
            SEARCH_PLANNER_REVISION_MODEL_PROMPT_SCHEMA_VERSION
        ),
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
        raise SearchPlannerRevisionModelAdapterError(f"{label} must be a JSON object")
    return value


def _required_sequence(value: Any, label: str) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise SearchPlannerRevisionModelAdapterError(f"{label} must be a JSON array")
    return list(value)


def _required_text(mapping: Mapping[str, Any], key: str, *, limit: int = 160) -> str:
    if key not in mapping:
        raise SearchPlannerRevisionModelAdapterError(f"missing required field: {key}")
    text = _clean_text(mapping.get(key), limit=limit)
    if not text:
        raise SearchPlannerRevisionModelAdapterError(f"required field is empty: {key}")
    return text


def _required_text_list(
    mapping: Mapping[str, Any],
    key: str,
    *,
    limit: int = 160,
    allow_empty: bool = False,
) -> list[str]:
    if key not in mapping:
        raise SearchPlannerRevisionModelAdapterError(f"missing required field: {key}")
    out = _optional_text_list(mapping.get(key), limit=limit)
    if not out and not allow_empty:
        raise SearchPlannerRevisionModelAdapterError(
            f"required field must contain text values: {key}"
        )
    return out


def _optional_text_list(value: Any, *, limit: int = 160) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise SearchPlannerRevisionModelAdapterError("expected an array of strings")
    out: list[str] = []
    for item in value:
        text = _clean_text(item, limit=limit)
        if text and text not in out:
            out.append(text)
    return out


def _mapping_list(
    value: Any,
    label: str,
    *,
    allow_missing: bool = False,
) -> list[dict[str, Any]]:
    if value is None and allow_missing:
        return []
    items = _required_sequence(value, label)
    return [_safe_metadata(_required_mapping(item, label)) for item in items]


def _false_flag_mapping(value: Any) -> dict[str, bool]:
    mapping = _required_mapping(value, "closed_surface_flags")
    flags: dict[str, bool] = {}
    for key, item in mapping.items():
        clean_key = _normalize_key(key)
        if clean_key and bool(item):
            raise SearchPlannerRevisionModelAdapterError(
                f"closed surface flag must remain false: {clean_key}"
            )
        if clean_key:
            flags[clean_key] = False
    return flags


def _safe_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise SearchPlannerRevisionModelAdapterError("metadata must be a JSON object")
    _reject_unsafe_payload(value)
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
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
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


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
    "SEARCH_PLANNER_REVISION_MODEL_ADAPTER_SCHEMA_VERSION",
    "SearchPlannerRevisionModelAdapter",
    "SearchPlannerRevisionModelAdapterError",
    "validate_and_sanitize_model_output",
]
