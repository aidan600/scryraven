"""RunKernel-owned search-only live validation seam.

PR1 keeps this seam offline-governed: tests inject fake provider result
metadata, and the reducer accepts only sanitized SearchResultCandidate records.
It does not call providers, broker, fetch/read, retrieval, EvidenceLedger,
citations, Sufficiency, FinalAnswerPacket, or Author code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

LIVE_SEARCH_VALIDATION_SCHEMA_VERSION = (
    "live_search_validation_runtime_ag_live_xaxis_validation_01a_v1"
)
LIVE_SEARCH_VALIDATION_OBSERVATION_SCHEMA_VERSION = (
    "live_search_validation_observation_ag_live_xaxis_validation_01a_v1"
)
LIVE_SEARCH_VALIDATION_STAGE = "live_search_validation"
LIVE_SEARCH_VALIDATION_REASON = (
    "live_search_validation_from_authorized_current_contract_and_handoff"
)
LIVE_SEARCH_VALIDATION_TRACE_KEY = "live_search_validation"
LIVE_SEARCH_VALIDATION_OWNER = "RunKernel.LiveSearchValidation"
LIVE_SEARCH_VALIDATION_MAX_SELECTED_TASKS = 2
LIVE_SEARCH_VALIDATION_DEFAULT_PROVIDER_CALL_CAP = 2
LIVE_SEARCH_VALIDATION_DEFAULT_RESULTS_PER_TASK_CAP = 2
LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP = 5
LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE = "offline_fake"
LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE = "broker_live"
LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE = "direct_live"
LIVE_SEARCH_VALIDATION_EXECUTION_MODES = frozenset(
    {
        LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
        LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE,
        LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
    }
)

_EXPECTED_ACTION_TYPE = "live_search_validate"
_EXPECTED_OBSERVATION_TYPE = "live_search_validated"

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "auth_header",
        "auth_headers",
        "authorization",
        "authorization_header",
        "cache",
        "cache_row",
        "cookie",
        "db",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
        "header",
        "headers",
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
        "serper_api_key",
        "serper_payload",
        "token",
        "unbounded_text",
    }
)

_PRIVATE_VALUE_MARKERS = frozenset(
    {
        "api_key",
        "authorization:",
        "bearer ",
        "private_sentinel",
        "provider_payload",
        "raw_private",
        "raw_prompt",
        "raw_provider",
        "secret",
    }
)

_SAFE_FALSE_RETENTION_KEYS = frozenset(
    {
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)

_DOWNSTREAM_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "fetch_read_executed": False,
    "fetch_read_retrieval_executed": False,
    "evidence_ledger_admitted": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
}

_EXECUTION_FACT_DEFAULTS = {
    "execution_mode": LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
    "broker_invoked": False,
    "live_provider_called": False,
}

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "admitted_sources",
        "answer",
        "api_key",
        "auth_headers",
        "author_input",
        "citation",
        "citation_sources",
        "citations",
        "content_fetched_from_url",
        "db_row",
        "evidence",
        "evidence_ledger",
        "evidence_ledger_admission",
        "evidence_sources",
        "fetched_content",
        "final_answer",
        "final_answer_packet",
        "full_trace",
        "model_response",
        "private_logs",
        "prompt",
        "raw_provider_payload",
        "raw_search_response",
        "search_response",
        "semantic_observation",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        *_DOWNSTREAM_FALSE_FLAGS,
        "author_executor_invoked",
        "author_input_created",
        "broker_called",
        "citation_created",
        "citation_rendered",
        "evidence_admitted",
        "evidence_ledger_custody_created",
        "fetch_executed",
        "final_answer_packet_created",
        "live_provider_call_executed",
        "live_search_called",
        "provider_called",
        "provider_payload_retained",
        "read_executed",
        "retrieval_executed",
        "search_executed",
        "source_obligation_support_created",
    }
)

_REQUIRED_ACTION_INPUT_KEYS = (
    "run_id",
    "request_id",
    "stage",
    "action_type",
    "expected_observation_type",
    "schema_version",
    "parent_current_contract_version",
    "parent_current_contract_digest",
    "handoff_id",
    "handoff_digest",
    "selected_search_task_ids",
    "provider_authorized",
    "provider_call_cap",
    "results_per_task_cap",
    "raw_provider_payload_retained",
    "raw_search_response_retained",
    "no_fetch_read_policy_active",
    "reason",
)


class LiveSearchValidationRuntimeError(ValueError):
    """Raised when validation construction or RunKernel reduction fails."""


@dataclass(frozen=True, slots=True)
class SearchResultCandidateShape:
    """Minimal sanitized fake-provider result shape accepted by PR1."""

    title: str
    url: str
    snippet: str | None = None
    domain: str | None = None
    published_or_observed_date: str | None = None
    provider_call_index: int | None = None
    result_rank: int | None = None

    def to_payload(self) -> dict[str, Any]:
        return _without_empty(
            {
                "title": self.title,
                "url": self.url,
                "domain": self.domain,
                "snippet": self.snippet,
                "published_or_observed_date": self.published_or_observed_date,
                "provider_call_index": self.provider_call_index,
                "result_rank": self.result_rank,
            }
        )


def build_live_search_validation_observation_payload(
    *,
    action: Any,
    current_answer_contract: Mapping[str, Any],
    search_executor_handoff_state: Mapping[str, Any],
    provider_used: str,
    provider_results_by_task: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    provider_call_count: int | None = None,
    provider_calls_attempted_count: int | None = None,
    provider_calls_completed_count: int | None = None,
    execution_mode: str = LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
    broker_invoked: bool = False,
    live_provider_called: bool = False,
) -> dict[str, Any]:
    """Build a sanitized live-search-validation observation payload."""

    _validate_action_like(action=action)
    inputs = _safe_mapping(getattr(action, "inputs", None))
    _validate_action_inputs(inputs)
    _reject_forbidden_surface_claims(
        provider_results_by_task or {},
        context="live search validation provider results",
    )

    selected_task_ids = _ordered_unique(inputs.get("selected_search_task_ids"))
    provider_authorized = _required_token(
        inputs.get("provider_authorized"),
        "live search validation requires provider_authorized",
    )
    clean_provider_used = _required_token(
        provider_used,
        "live search validation requires provider_used",
    )
    provider_call_cap = _positive_int(
        inputs.get("provider_call_cap"),
        "live search validation requires provider_call_cap",
    )
    results_per_task_cap = _positive_int(
        inputs.get("results_per_task_cap"),
        "live search validation requires results_per_task_cap",
    )
    contract_ref = contract_ref_from_contract(
        current_answer_contract,
        source="current_answer_contract",
    )
    handoff_ref = handoff_ref_from_handoff_state(search_executor_handoff_state)
    tasks_by_id = _tasks_by_id(search_executor_handoff_state)
    result_map = {
        _clean_token(task_id, limit=220): _safe_list(results)
        for task_id, results in (provider_results_by_task or {}).items()
        if _clean_token(task_id, limit=220)
    }

    candidates: list[dict[str, Any]] = []
    provider_call_indices: list[int] = []
    for call_index, task_id in enumerate(selected_task_ids, start=1):
        task = tasks_by_id.get(task_id, {})
        for rank, raw_result in enumerate(result_map.get(task_id, []), start=1):
            result = _safe_mapping(raw_result)
            result_call_index = _positive_int(
                result.get("provider_call_index") or call_index,
                "live search validation candidate requires provider_call_index",
            )
            result_rank = _positive_int(
                result.get("result_rank") or rank,
                "live search validation candidate requires result_rank",
            )
            provider_call_indices.append(result_call_index)
            candidate = _build_candidate_record(
                run_id=str(inputs["run_id"]),
                request_id=str(inputs["request_id"]),
                validation_id="",  # filled after validation_id is derived
                parent_current_contract_ref=contract_ref,
                parent_search_executor_handoff_ref=handoff_ref,
                selected_task=task,
                search_task_id=task_id,
                provider_authorized=provider_authorized,
                provider_used=clean_provider_used,
                provider_call_index=result_call_index,
                result_rank=result_rank,
                result=result,
            )
            candidates.append(candidate)

    provider_calls_from_results = max(provider_call_indices, default=0)
    provider_calls_planned = len(selected_task_ids)
    provider_calls_attempted = max(
        _bounded_int(
            provider_calls_attempted_count,
            default=_bounded_int(provider_call_count, default=provider_calls_planned),
        ),
        provider_calls_from_results,
    )
    provider_calls_completed = max(
        _bounded_int(
            provider_calls_completed_count,
            default=provider_calls_attempted,
        ),
        provider_calls_from_results,
    )
    execution_facts = _execution_facts(
        execution_mode=execution_mode,
        broker_invoked=broker_invoked,
        live_provider_called=live_provider_called,
    )

    validation_base = {
        "schema_version": LIVE_SEARCH_VALIDATION_SCHEMA_VERSION,
        "trace_key": LIVE_SEARCH_VALIDATION_TRACE_KEY,
        "owner": LIVE_SEARCH_VALIDATION_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "stage": LIVE_SEARCH_VALIDATION_STAGE,
        "action_type": _EXPECTED_ACTION_TYPE,
        "observation_type": _EXPECTED_OBSERVATION_TYPE,
        "run_id": inputs["run_id"],
        "request_id": inputs["request_id"],
        "authorized_action_id": getattr(action, "action_id", None),
        "parent_current_contract_ref": contract_ref,
        "parent_search_executor_handoff_ref": handoff_ref,
        "selected_search_task_ids": selected_task_ids,
        "provider_authorized": provider_authorized,
        "provider_used": clean_provider_used,
        "provider_call_cap": provider_call_cap,
        "provider_calls_attempted": provider_calls_attempted,
        "provider_calls_completed": provider_calls_completed,
        "results_per_task_cap": results_per_task_cap,
        "candidate_count": len(candidates),
        "search_result_candidates": [],
        **execution_facts,
        "not_live_executed_by_pr1": (
            execution_facts["execution_mode"]
            == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE
        ),
        "fake_provider_used": (
            execution_facts["execution_mode"]
            == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE
        ),
        "no_fetch_read_policy_active": True,
        "retention_flags": _retention_flags(),
        "closed_surface_flags": dict(_DOWNSTREAM_FALSE_FLAGS),
        **_DOWNSTREAM_FALSE_FLAGS,
    }
    dedupe_key = _dedupe_key(validation_base)
    validation_id = (
        "live-search-validation:"
        f"{_clean_token(inputs.get('request_id'))}:"
        f"{dedupe_key[:16]}"
    )
    completed_candidates = [
        {
            **candidate,
            "validation_id": validation_id,
            "candidate_id": (
                "search-result-candidate:"
                f"{validation_id}:{candidate['search_task_id']}:"
                f"{candidate['result_rank']}"
            ),
        }
        for candidate in candidates
    ]
    completed_candidates = [
        {
            **candidate,
            "candidate_digest": _digest_json(_candidate_digest_payload(candidate)),
        }
        for candidate in completed_candidates
    ]
    validation_without_digest = {
        **validation_base,
        "validation_id": validation_id,
        "dedupe_key": dedupe_key,
        "search_result_candidates": completed_candidates,
    }
    validation_digest = _digest_json(
        _validation_digest_payload(validation_without_digest)
    )
    validation = {
        **validation_without_digest,
        "validation_digest": validation_digest,
    }
    return {
        "schema_version": LIVE_SEARCH_VALIDATION_OBSERVATION_SCHEMA_VERSION,
        "live_search_validation": validation,
    }


def build_live_search_validation_state(
    *,
    action_id: str,
    action_inputs: Mapping[str, Any] | None,
    observation_payload: Mapping[str, Any],
    run_id: str,
    request_id: str,
    current_parent_current_contract: Mapping[str, Any] | None,
    current_search_executor_handoff_state: Mapping[str, Any] | None,
    existing_validation_history: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Validate one live-search-validation observation into RunKernel state."""

    clean_action_id = _required_token(
        action_id,
        "live search validation reduction requires action_id",
        limit=220,
    )
    clean_run_id = _required_token(
        run_id,
        "live search validation reduction requires run_id",
    )
    clean_request_id = _required_token(
        request_id,
        "live search validation reduction requires request_id",
    )
    inputs = _safe_mapping(action_inputs)
    _validate_action_inputs(inputs)
    raw_payload = _required_mapping(
        observation_payload,
        "live search validation observation payload",
    )
    _reject_forbidden_surface_claims(
        raw_payload,
        context="live search validation observation",
    )
    payload = _safe_mapping(raw_payload)
    validation = _safe_mapping(payload.get("live_search_validation"))
    if (
        payload.get("schema_version")
        != LIVE_SEARCH_VALIDATION_OBSERVATION_SCHEMA_VERSION
    ):
        raise LiveSearchValidationRuntimeError(
            "live search validation observation schema version does not match"
        )
    if not validation:
        raise LiveSearchValidationRuntimeError(
            "live search validation observation requires live_search_validation"
        )
    if validation.get("schema_version") != LIVE_SEARCH_VALIDATION_SCHEMA_VERSION:
        raise LiveSearchValidationRuntimeError(
            "live search validation schema version does not match"
        )
    if validation.get("owner") != LIVE_SEARCH_VALIDATION_OWNER:
        raise LiveSearchValidationRuntimeError(
            "live search validation owner does not match"
        )
    if validation.get("authorized_action_id") != clean_action_id:
        raise LiveSearchValidationRuntimeError(
            "live search validation action_id binding does not match"
        )
    if validation.get("stage") != LIVE_SEARCH_VALIDATION_STAGE:
        raise LiveSearchValidationRuntimeError(
            "live search validation stage does not match"
        )
    if validation.get("action_type") != _EXPECTED_ACTION_TYPE:
        raise LiveSearchValidationRuntimeError(
            "live search validation action type does not match"
        )
    if validation.get("observation_type") != _EXPECTED_OBSERVATION_TYPE:
        raise LiveSearchValidationRuntimeError(
            "live search validation observation type does not match"
        )
    if validation.get("run_id") != clean_run_id or inputs.get("run_id") != clean_run_id:
        raise LiveSearchValidationRuntimeError(
            "live search validation run_id does not match the run"
        )
    if (
        validation.get("request_id") != clean_request_id
        or inputs.get("request_id") != clean_request_id
    ):
        raise LiveSearchValidationRuntimeError(
            "live search validation request_id does not match the request"
        )

    contract_ref = _validate_current_contract_binding(
        action_inputs=inputs,
        validation=validation,
        current_parent_current_contract=current_parent_current_contract,
    )
    handoff_ref = _validate_handoff_binding(
        action_inputs=inputs,
        validation=validation,
        current_search_executor_handoff_state=current_search_executor_handoff_state,
        current_contract_ref=contract_ref,
    )
    tasks_by_id = _tasks_by_id(current_search_executor_handoff_state)
    intents_by_id = _intents_by_id(current_search_executor_handoff_state)
    selected_task_ids = _validate_selected_tasks(
        action_inputs=inputs,
        validation=validation,
        tasks_by_id=tasks_by_id,
    )
    provider_authorized = _required_token(
        inputs.get("provider_authorized"),
        "live search validation requires provider_authorized",
    )
    provider_used = _required_token(
        validation.get("provider_used"),
        "live search validation requires provider_used",
    )
    if validation.get("provider_authorized") != provider_authorized:
        raise LiveSearchValidationRuntimeError(
            "live search validation provider_authorized does not match action"
        )
    if provider_used != provider_authorized:
        raise LiveSearchValidationRuntimeError(
            "live search validation provider_used does not match authorization"
        )
    provider_call_cap = _positive_int(
        inputs.get("provider_call_cap"),
        "live search validation requires provider_call_cap",
    )
    results_per_task_cap = _positive_int(
        inputs.get("results_per_task_cap"),
        "live search validation requires results_per_task_cap",
    )
    if provider_call_cap > LIVE_SEARCH_VALIDATION_DEFAULT_PROVIDER_CALL_CAP:
        raise LiveSearchValidationRuntimeError(
            "live search validation provider_call_cap exceeds PR1 default"
        )
    if results_per_task_cap > LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP:
        raise LiveSearchValidationRuntimeError(
            "live search validation results_per_task_cap exceeds explicit cap"
        )
    if _positive_int(validation.get("provider_call_cap"), "provider_call_cap") != provider_call_cap:
        raise LiveSearchValidationRuntimeError(
            "live search validation provider_call_cap does not match action"
        )
    if (
        _positive_int(validation.get("results_per_task_cap"), "results_per_task_cap")
        != results_per_task_cap
    ):
        raise LiveSearchValidationRuntimeError(
            "live search validation results_per_task_cap does not match action"
        )
    provider_calls_attempted = _bounded_int(validation.get("provider_calls_attempted"))
    provider_calls_completed = _bounded_int(validation.get("provider_calls_completed"))
    if provider_calls_attempted > provider_call_cap:
        raise LiveSearchValidationRuntimeError(
            "live search validation provider_call_cap exceeded"
        )
    if provider_calls_completed > provider_call_cap:
        raise LiveSearchValidationRuntimeError(
            "live search validation provider_call_cap exceeded"
        )
    execution_facts = _validate_execution_facts(validation)

    candidates = _safe_list(validation.get("search_result_candidates"))
    if validation.get("candidate_count") != len(candidates):
        raise LiveSearchValidationRuntimeError(
            "live search validation candidate_count does not match candidates"
        )
    _validate_candidates(
        candidates=candidates,
        selected_task_ids=selected_task_ids,
        tasks_by_id=tasks_by_id,
        intents_by_id=intents_by_id,
        parent_current_contract_ref=contract_ref,
        parent_search_executor_handoff_ref=handoff_ref,
        run_id=clean_run_id,
        request_id=clean_request_id,
        validation_id=_required_token(
            validation.get("validation_id"),
            "live search validation requires validation_id",
            limit=260,
        ),
        provider_authorized=provider_authorized,
        provider_used=provider_used,
        provider_call_cap=provider_call_cap,
        results_per_task_cap=results_per_task_cap,
    )
    _validate_closed_validation_flags(validation)

    declared_digest = _required_token(
        validation.get("validation_digest"),
        "live search validation requires validation_digest",
        limit=128,
    )
    recomputed_digest = _digest_json(_validation_digest_payload(validation))
    if declared_digest != recomputed_digest:
        raise LiveSearchValidationRuntimeError(
            "stale live search validation: validation digest does not match payload"
        )
    dedupe_key = _required_token(
        validation.get("dedupe_key"),
        "live search validation requires dedupe_key",
        limit=128,
    )
    if dedupe_key != _dedupe_key(validation):
        raise LiveSearchValidationRuntimeError(
            "live search validation dedupe key does not match payload"
        )
    for item in existing_validation_history:
        if _safe_mapping(item).get("dedupe_key") == dedupe_key:
            raise LiveSearchValidationRuntimeError(
                "duplicate live search validation for the same contract/handoff/task/provider context"
            )

    state = {
        "schema_version": LIVE_SEARCH_VALIDATION_SCHEMA_VERSION,
        "trace_key": LIVE_SEARCH_VALIDATION_TRACE_KEY,
        "owner": LIVE_SEARCH_VALIDATION_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "validation_id": validation.get("validation_id"),
        "validation_digest": declared_digest,
        "dedupe_key": dedupe_key,
        "run_id": clean_run_id,
        "request_id": clean_request_id,
        "authorized_action_id": clean_action_id,
        "parent_current_contract_ref": contract_ref,
        "parent_search_executor_handoff_ref": handoff_ref,
        "selected_search_task_ids": selected_task_ids,
        "provider_authorized": provider_authorized,
        "provider_used": provider_used,
        "provider_call_cap": provider_call_cap,
        "provider_calls_attempted": provider_calls_attempted,
        "provider_calls_completed": provider_calls_completed,
        "results_per_task_cap": results_per_task_cap,
        "candidate_count": len(candidates),
        "search_result_candidates": candidates,
        **execution_facts,
        "not_live_executed_by_pr1": validation.get("not_live_executed_by_pr1"),
        "fake_provider_used": validation.get("fake_provider_used"),
        "no_fetch_read_policy_active": True,
        "retention_flags": _retention_flags(),
        "closed_surface_flags": dict(_DOWNSTREAM_FALSE_FLAGS),
        **_DOWNSTREAM_FALSE_FLAGS,
    }
    return _json_safe(state)


def build_live_search_validation_projection(
    *,
    validation_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Project sanitized validation state for trace/history consumers."""

    state = _safe_mapping(validation_state)
    return {
        "owner": LIVE_SEARCH_VALIDATION_OWNER,
        "schema_version": state.get("schema_version"),
        "trace_key": LIVE_SEARCH_VALIDATION_TRACE_KEY,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "validation_id": state.get("validation_id"),
        "validation_digest": state.get("validation_digest"),
        "dedupe_key": state.get("dedupe_key"),
        "run_id": state.get("run_id"),
        "request_id": state.get("request_id"),
        "authorized_action_id": state.get("authorized_action_id"),
        "parent_current_contract_ref": _safe_mapping(
            state.get("parent_current_contract_ref")
        ),
        "parent_search_executor_handoff_ref": _safe_mapping(
            state.get("parent_search_executor_handoff_ref")
        ),
        "selected_search_task_ids": _text_list(
            state.get("selected_search_task_ids")
        ),
        "provider_authorized": state.get("provider_authorized"),
        "provider_used": state.get("provider_used"),
        "provider_call_cap": state.get("provider_call_cap"),
        "provider_calls_attempted": state.get("provider_calls_attempted"),
        "provider_calls_completed": state.get("provider_calls_completed"),
        "results_per_task_cap": state.get("results_per_task_cap"),
        "candidate_count": state.get("candidate_count"),
        "search_result_candidates": _safe_list(
            state.get("search_result_candidates")
        ),
        "execution_mode": state.get("execution_mode"),
        "broker_invoked": state.get("broker_invoked"),
        "live_provider_called": state.get("live_provider_called"),
        "not_live_executed_by_pr1": state.get("not_live_executed_by_pr1"),
        "fake_provider_used": state.get("fake_provider_used"),
        "no_fetch_read_policy_active": True,
        "retention_flags": _retention_flags(),
        "closed_surface_flags": dict(_DOWNSTREAM_FALSE_FLAGS),
        **_DOWNSTREAM_FALSE_FLAGS,
    }


def live_search_validation_ref_from_state(
    validation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = _safe_mapping(validation_state)
    validation_id = _clean_token(state.get("validation_id"), limit=260)
    validation_digest = _clean_token(state.get("validation_digest"), limit=128)
    if not validation_id or not validation_digest:
        return {}
    return {
        "validation_id": validation_id,
        "validation_digest": validation_digest,
        "schema_version": _clean_token(state.get("schema_version")),
        "dedupe_key": _clean_token(state.get("dedupe_key"), limit=128),
        "provider_used": _clean_token(state.get("provider_used")),
        "candidate_count": _bounded_int(state.get("candidate_count")),
    }


def contract_ref_from_contract(
    contract: Mapping[str, Any] | None,
    *,
    source: str,
) -> dict[str, Any]:
    ref = _safe_mapping(contract)
    version = _clean_token(
        ref.get("accepted_contract_version")
        or ref.get("current_contract_version")
        or ref.get("contract_version")
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
        "source": _clean_token(source) or "current_answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def handoff_ref_from_handoff_state(
    handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = _safe_mapping(handoff_state)
    handoff_id = _clean_token(state.get("handoff_id"), limit=220)
    handoff_digest = _clean_token(state.get("handoff_digest"), limit=128)
    if not handoff_id or not handoff_digest:
        return {}
    return {
        "handoff_id": handoff_id,
        "handoff_digest": handoff_digest,
        "schema_version": _clean_token(state.get("schema_version")),
        "dedupe_key": _clean_token(state.get("dedupe_key"), limit=128),
        "contract_parent_kind": _clean_token(state.get("contract_parent_kind")),
        "parent_current_contract_ref": _safe_mapping(
            state.get("parent_current_contract_ref")
        ),
        "parent_initial_contract_ref": _safe_mapping(
            state.get("parent_initial_contract_ref")
        ),
    }


def _build_candidate_record(
    *,
    run_id: str,
    request_id: str,
    validation_id: str,
    parent_current_contract_ref: Mapping[str, Any],
    parent_search_executor_handoff_ref: Mapping[str, Any],
    selected_task: Mapping[str, Any],
    search_task_id: str,
    provider_authorized: str,
    provider_used: str,
    provider_call_index: int,
    result_rank: int,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    title = _required_token(
        result.get("title"),
        "live search validation candidate requires title",
        limit=220,
    )
    url = _required_url(result.get("url") or result.get("link"))
    domain = _clean_domain(result.get("domain")) or _domain_from_url(url)
    if not domain:
        raise LiveSearchValidationRuntimeError(
            "live search validation candidate requires domain"
        )
    snippet = _clean_text(result.get("snippet"), limit=500)
    candidate = {
        "schema_version": LIVE_SEARCH_VALIDATION_SCHEMA_VERSION,
        "candidate_id": "",
        "candidate_digest": "",
        "run_id": run_id,
        "request_id": request_id,
        "validation_id": validation_id,
        "parent_current_contract_ref": _safe_mapping(parent_current_contract_ref),
        "parent_search_executor_handoff_ref": _safe_mapping(
            parent_search_executor_handoff_ref
        ),
        "search_task_id": search_task_id,
        "query_intent_id": _clean_token(selected_task.get("query_intent_id")),
        "component_id": _clean_token(selected_task.get("component_id")),
        "source_obligation_candidate_ids": _text_list(
            selected_task.get("source_obligation_candidate_ids")
        ),
        "provider_authorized": provider_authorized,
        "provider_used": provider_used,
        "provider_call_index": provider_call_index,
        "result_rank": result_rank,
        "title": title,
        "url": url,
        "domain": domain,
        "snippet": snippet,
        "published_or_observed_date": _clean_token(
            result.get("published_or_observed_date") or result.get("date"),
            limit=80,
        ),
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "fetch_read_executed": False,
        "fetch_read_retrieval_executed": False,
        "evidence_ledger_admitted": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "partial_answer_ready": False,
        "product_correctness_claimed": False,
    }
    return _without_empty(candidate)


def _validate_action_like(*, action: Any) -> None:
    action_type = _enum_or_text(getattr(action, "action_type", None))
    expected_observation_type = _enum_or_text(
        getattr(action, "expected_observation_type", None)
    )
    if getattr(action, "stage", None) != LIVE_SEARCH_VALIDATION_STAGE:
        raise LiveSearchValidationRuntimeError(
            "live search validation action stage does not match"
        )
    if action_type != _EXPECTED_ACTION_TYPE:
        raise LiveSearchValidationRuntimeError(
            "live search validation action type does not match"
        )
    if expected_observation_type != _EXPECTED_OBSERVATION_TYPE:
        raise LiveSearchValidationRuntimeError(
            "live search validation expected observation type does not match"
        )


def _validate_action_inputs(inputs: Mapping[str, Any]) -> None:
    missing = [key for key in _REQUIRED_ACTION_INPUT_KEYS if key not in inputs]
    if missing:
        raise LiveSearchValidationRuntimeError(
            "live search validation action missing required bindings: "
            + ", ".join(missing)
        )
    for key in (
        "run_id",
        "request_id",
        "stage",
        "action_type",
        "expected_observation_type",
        "schema_version",
        "parent_current_contract_version",
        "parent_current_contract_digest",
        "handoff_id",
        "handoff_digest",
        "provider_authorized",
        "reason",
    ):
        if not _clean_token(inputs.get(key), limit=260):
            raise LiveSearchValidationRuntimeError(
                f"live search validation action requires {key} binding"
            )
    if inputs.get("stage") != LIVE_SEARCH_VALIDATION_STAGE:
        raise LiveSearchValidationRuntimeError(
            "live search validation action binds the wrong stage"
        )
    if inputs.get("action_type") != _EXPECTED_ACTION_TYPE:
        raise LiveSearchValidationRuntimeError(
            "live search validation action binds the wrong action type"
        )
    if inputs.get("expected_observation_type") != _EXPECTED_OBSERVATION_TYPE:
        raise LiveSearchValidationRuntimeError(
            "live search validation action binds the wrong observation type"
        )
    if inputs.get("schema_version") != LIVE_SEARCH_VALIDATION_SCHEMA_VERSION:
        raise LiveSearchValidationRuntimeError(
            "live search validation action binds the wrong schema version"
        )
    selected = _ordered_unique(inputs.get("selected_search_task_ids"))
    if not selected:
        raise LiveSearchValidationRuntimeError(
            "live search validation action requires selected_search_task_ids"
        )
    if len(selected) > LIVE_SEARCH_VALIDATION_MAX_SELECTED_TASKS:
        raise LiveSearchValidationRuntimeError(
            "live search validation selected task count exceeds PR1 cap"
        )
    if len(selected) != len(_text_list(inputs.get("selected_search_task_ids"))):
        raise LiveSearchValidationRuntimeError(
            "live search validation selected task ids must be unique"
        )
    provider_call_cap = _positive_int(
        inputs.get("provider_call_cap"),
        "live search validation requires provider_call_cap",
    )
    results_per_task_cap = _positive_int(
        inputs.get("results_per_task_cap"),
        "live search validation requires results_per_task_cap",
    )
    if provider_call_cap > LIVE_SEARCH_VALIDATION_DEFAULT_PROVIDER_CALL_CAP:
        raise LiveSearchValidationRuntimeError(
            "live search validation provider_call_cap exceeds PR1 default"
        )
    if results_per_task_cap > LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP:
        raise LiveSearchValidationRuntimeError(
            "live search validation results_per_task_cap exceeds explicit cap"
        )
    if inputs.get("raw_provider_payload_retained") is not False:
        raise LiveSearchValidationRuntimeError(
            "live search validation requires raw_provider_payload_retained false"
        )
    if inputs.get("raw_search_response_retained") is not False:
        raise LiveSearchValidationRuntimeError(
            "live search validation requires raw_search_response_retained false"
        )
    if inputs.get("no_fetch_read_policy_active") is not True:
        raise LiveSearchValidationRuntimeError(
            "live search validation requires no_fetch_read_policy_active true"
        )
    _reject_forbidden_surface_claims(
        inputs,
        context="live search validation action inputs",
    )


def _validate_current_contract_binding(
    *,
    action_inputs: Mapping[str, Any],
    validation: Mapping[str, Any],
    current_parent_current_contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    expected_ref = contract_ref_from_contract(
        current_parent_current_contract,
        source="current_answer_contract",
    )
    if not expected_ref:
        raise LiveSearchValidationRuntimeError(
            "live search validation requires current_answer_contract"
        )
    validation_ref = _contract_ref_or_empty(
        validation.get("parent_current_contract_ref")
    )
    action_ref = _contract_ref_or_empty(
        {
            "source": "current_answer_contract",
            "contract_version": action_inputs.get(
                "parent_current_contract_version"
            ),
            "contract_digest": action_inputs.get("parent_current_contract_digest"),
        }
    )
    if validation_ref != expected_ref or action_ref != expected_ref:
        raise LiveSearchValidationRuntimeError(
            "stale current_answer_contract digest: live search validation is not bound to current contract"
        )
    return expected_ref


def _validate_handoff_binding(
    *,
    action_inputs: Mapping[str, Any],
    validation: Mapping[str, Any],
    current_search_executor_handoff_state: Mapping[str, Any] | None,
    current_contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    expected_ref = handoff_ref_from_handoff_state(
        current_search_executor_handoff_state
    )
    if not expected_ref:
        raise LiveSearchValidationRuntimeError(
            "live search validation requires SearchExecutorHandoff"
        )
    validation_ref = _handoff_ref_or_empty(
        validation.get("parent_search_executor_handoff_ref")
    )
    action_ref = _handoff_ref_or_empty(
        {
            "handoff_id": action_inputs.get("handoff_id"),
            "handoff_digest": action_inputs.get("handoff_digest"),
            "schema_version": expected_ref.get("schema_version"),
            "dedupe_key": expected_ref.get("dedupe_key"),
            "contract_parent_kind": expected_ref.get("contract_parent_kind"),
            "parent_current_contract_ref": expected_ref.get(
                "parent_current_contract_ref"
            ),
            "parent_initial_contract_ref": expected_ref.get(
                "parent_initial_contract_ref"
            ),
        }
    )
    if validation_ref != expected_ref or action_ref != expected_ref:
        raise LiveSearchValidationRuntimeError(
            "stale SearchExecutorHandoff digest: live search validation is not bound to current handoff"
        )
    if _contract_ref_or_empty(expected_ref.get("parent_current_contract_ref")) != current_contract_ref:
        raise LiveSearchValidationRuntimeError(
            "SearchExecutorHandoff is not bound to current_answer_contract"
        )
    return expected_ref


def _validate_selected_tasks(
    *,
    action_inputs: Mapping[str, Any],
    validation: Mapping[str, Any],
    tasks_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    selected_action = _ordered_unique(action_inputs.get("selected_search_task_ids"))
    selected_validation = _ordered_unique(validation.get("selected_search_task_ids"))
    if selected_action != selected_validation:
        raise LiveSearchValidationRuntimeError(
            "live search validation selected task ids do not match action"
        )
    if len(selected_action) > LIVE_SEARCH_VALIDATION_MAX_SELECTED_TASKS:
        raise LiveSearchValidationRuntimeError(
            "live search validation selected task count exceeds PR1 cap"
        )
    missing = [task_id for task_id in selected_action if task_id not in tasks_by_id]
    if missing:
        raise LiveSearchValidationRuntimeError(
            "live search validation selected task ids are missing from SearchExecutorHandoff: "
            + ", ".join(missing)
        )
    return selected_action


def _validate_candidates(
    *,
    candidates: Sequence[Any],
    selected_task_ids: Sequence[str],
    tasks_by_id: Mapping[str, Mapping[str, Any]],
    intents_by_id: Mapping[str, Mapping[str, Any]],
    parent_current_contract_ref: Mapping[str, Any],
    parent_search_executor_handoff_ref: Mapping[str, Any],
    run_id: str,
    request_id: str,
    validation_id: str,
    provider_authorized: str,
    provider_used: str,
    provider_call_cap: int,
    results_per_task_cap: int,
) -> None:
    selected = set(selected_task_ids)
    seen_candidate_ids: set[str] = set()
    for raw_candidate in candidates:
        candidate = _safe_mapping(raw_candidate)
        candidate_id = _required_token(
            candidate.get("candidate_id"),
            "live search validation candidate requires candidate_id",
            limit=300,
        )
        if candidate_id in seen_candidate_ids:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate ids must be unique"
            )
        seen_candidate_ids.add(candidate_id)
        if candidate.get("run_id") != run_id or candidate.get("request_id") != request_id:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate run/request binding does not match"
            )
        if candidate.get("validation_id") != validation_id:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate validation_id does not match"
            )
        if _contract_ref_or_empty(candidate.get("parent_current_contract_ref")) != parent_current_contract_ref:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate current contract ref does not match"
            )
        if _handoff_ref_or_empty(candidate.get("parent_search_executor_handoff_ref")) != parent_search_executor_handoff_ref:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate handoff ref does not match"
            )
        task_id = _required_token(
            candidate.get("search_task_id"),
            "live search validation candidate requires search_task_id",
            limit=260,
        )
        if task_id not in selected:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate references unselected search task"
            )
        task = tasks_by_id.get(task_id)
        if not task:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate references unknown search task"
            )
        intent = intents_by_id.get(str(task.get("query_intent_id")))
        if not intent:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate references unknown query intent"
            )
        if candidate.get("query_intent_id") != task.get("query_intent_id"):
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate query_intent_id does not match task"
            )
        if candidate.get("component_id") != task.get("component_id"):
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate component_id does not match task"
            )
        if _text_list(candidate.get("source_obligation_candidate_ids")) != _text_list(
            task.get("source_obligation_candidate_ids")
        ):
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate source obligation ids do not match task"
            )
        if candidate.get("provider_authorized") != provider_authorized:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate provider_authorized does not match"
            )
        if candidate.get("provider_used") != provider_used:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate provider_used does not match"
            )
        provider_call_index = _positive_int(
            candidate.get("provider_call_index"),
            "live search validation candidate requires provider_call_index",
        )
        result_rank = _positive_int(
            candidate.get("result_rank"),
            "live search validation candidate requires result_rank",
        )
        if provider_call_index > provider_call_cap:
            raise LiveSearchValidationRuntimeError(
                "live search validation provider_call_cap exceeded"
            )
        if result_rank > results_per_task_cap:
            raise LiveSearchValidationRuntimeError(
                "live search validation results_per_task_cap exceeded"
            )
        for key in ("title", "url", "domain"):
            if not _clean_token(candidate.get(key), limit=500):
                raise LiveSearchValidationRuntimeError(
                    f"live search validation candidate requires {key}"
                )
        if _clean_text(candidate.get("snippet"), limit=501) and len(
            str(candidate.get("snippet"))
        ) > 500:
            raise LiveSearchValidationRuntimeError(
                "live search validation candidate snippet exceeds limit"
            )
        _validate_closed_candidate_flags(candidate)
        declared_digest = _required_token(
            candidate.get("candidate_digest"),
            "live search validation candidate requires candidate_digest",
            limit=128,
        )
        recomputed_digest = _digest_json(_candidate_digest_payload(candidate))
        if declared_digest != recomputed_digest:
            raise LiveSearchValidationRuntimeError(
                "tampered SearchResultCandidate digest rejected"
            )


def _validate_closed_candidate_flags(candidate: Mapping[str, Any]) -> None:
    for key, expected in _candidate_false_flags().items():
        value = candidate.get(key, False if key in _SAFE_FALSE_RETENTION_KEYS else None)
        if value is not expected:
            raise LiveSearchValidationRuntimeError(
                f"SearchResultCandidate must keep {key} false"
            )


def _execution_facts(
    *,
    execution_mode: str,
    broker_invoked: bool,
    live_provider_called: bool,
) -> dict[str, Any]:
    mode = _required_token(
        execution_mode,
        "live search validation requires execution_mode",
        limit=80,
    )
    if mode not in LIVE_SEARCH_VALIDATION_EXECUTION_MODES:
        raise LiveSearchValidationRuntimeError(
            "live search validation execution_mode is not allowed"
        )
    if not isinstance(broker_invoked, bool):
        raise LiveSearchValidationRuntimeError(
            "live search validation broker_invoked must be boolean"
        )
    if not isinstance(live_provider_called, bool):
        raise LiveSearchValidationRuntimeError(
            "live search validation live_provider_called must be boolean"
        )
    if mode == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE:
        if broker_invoked or live_provider_called:
            raise LiveSearchValidationRuntimeError(
                "offline fake validation cannot claim broker or live provider execution"
            )
    elif mode == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE:
        if broker_invoked is not True:
            raise LiveSearchValidationRuntimeError(
                "broker live validation requires broker_invoked true"
            )
    elif mode == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE:
        if broker_invoked:
            raise LiveSearchValidationRuntimeError(
                "direct live validation cannot claim broker_invoked"
            )
    return {
        "execution_mode": mode,
        "broker_invoked": broker_invoked,
        "live_provider_called": live_provider_called,
    }


def _validate_execution_facts(validation: Mapping[str, Any]) -> dict[str, Any]:
    facts = _execution_facts(
        execution_mode=validation.get("execution_mode")
        or _EXECUTION_FACT_DEFAULTS["execution_mode"],
        broker_invoked=validation.get(
            "broker_invoked",
            _EXECUTION_FACT_DEFAULTS["broker_invoked"],
        ),
        live_provider_called=validation.get(
            "live_provider_called",
            _EXECUTION_FACT_DEFAULTS["live_provider_called"],
        ),
    )
    offline = (
        facts["execution_mode"] == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE
    )
    if validation.get("not_live_executed_by_pr1") is not offline:
        raise LiveSearchValidationRuntimeError(
            "live search validation not_live_executed_by_pr1 must match execution_mode"
        )
    if validation.get("fake_provider_used") is not offline:
        raise LiveSearchValidationRuntimeError(
            "live search validation fake_provider_used must match execution_mode"
        )
    return facts


def _validate_closed_validation_flags(validation: Mapping[str, Any]) -> None:
    for key, expected in _DOWNSTREAM_FALSE_FLAGS.items():
        value = validation.get(key, False if key in _SAFE_FALSE_RETENTION_KEYS else None)
        if value is not expected:
            raise LiveSearchValidationRuntimeError(
                f"live search validation must keep {key} false"
            )
    flags = _safe_mapping(validation.get("closed_surface_flags"))
    for forbidden_execution_fact in ("broker_invoked", "live_provider_called"):
        if forbidden_execution_fact in flags:
            raise LiveSearchValidationRuntimeError(
                "live search validation closed-surface flags cannot include "
                f"{forbidden_execution_fact}"
            )
    for key, expected in _DOWNSTREAM_FALSE_FLAGS.items():
        value = flags.get(key, False if key in _SAFE_FALSE_RETENTION_KEYS else None)
        if value is not expected:
            raise LiveSearchValidationRuntimeError(
                f"live search validation closed-surface flag {key} must be false"
            )
    retention = _safe_mapping(validation.get("retention_flags"))
    for key, expected in _retention_flags().items():
        if retention.get(key) is not expected:
            raise LiveSearchValidationRuntimeError(
                f"live search validation retention flag {key} must be false"
            )
    if validation.get("no_fetch_read_policy_active") is not True:
        raise LiveSearchValidationRuntimeError(
            "live search validation requires no_fetch_read_policy_active"
        )


def _tasks_by_id(handoff_state: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    tasks: dict[str, dict[str, Any]] = {}
    for item in _safe_list(_safe_mapping(handoff_state).get("search_task_records")):
        task = _safe_mapping(item)
        task_id = _clean_token(task.get("search_task_id"), limit=260)
        if task_id:
            tasks[task_id] = task
    return tasks


def _intents_by_id(handoff_state: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    intents: dict[str, dict[str, Any]] = {}
    for item in _safe_list(_safe_mapping(handoff_state).get("query_intent_records")):
        intent = _safe_mapping(item)
        intent_id = _clean_token(intent.get("query_intent_id"), limit=260)
        if intent_id:
            intents[intent_id] = intent
    return intents


def _candidate_false_flags() -> dict[str, bool]:
    return {
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "fetch_read_executed": False,
        "fetch_read_retrieval_executed": False,
        "evidence_ledger_admitted": False,
        "citation_eligible": False,
        "source_obligation_satisfied": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "partial_answer_ready": False,
        "product_correctness_claimed": False,
    }


def _retention_flags() -> dict[str, bool]:
    return {
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "private_artifact_retained": False,
        "full_trace_retained": False,
        "output_packet_retained": False,
    }


def _reject_forbidden_surface_claims(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    sensitive = sorted(key for key in keys if _is_sensitive_key(key))
    if sensitive:
        raise LiveSearchValidationRuntimeError(
            f"{context} contains raw/private fields: " + ", ".join(sensitive)
        )
    forbidden = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if forbidden:
        raise LiveSearchValidationRuntimeError(
            f"{context} includes closed authority fields: " + ", ".join(forbidden)
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise LiveSearchValidationRuntimeError(
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


def _is_sensitive_key(key: Any) -> bool:
    normalized = _normalize_key(key)
    if normalized in _SAFE_FALSE_RETENTION_KEYS:
        return False
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _dedupe_key(validation: Mapping[str, Any]) -> str:
    return _digest_json(
        {
            "parent_current_contract_ref": _contract_ref_or_empty(
                validation.get("parent_current_contract_ref")
            ),
            "parent_search_executor_handoff_ref": _handoff_ref_or_empty(
                validation.get("parent_search_executor_handoff_ref")
            ),
            "selected_search_task_ids": _ordered_unique(
                validation.get("selected_search_task_ids")
            ),
            "provider_authorized": _clean_token(
                validation.get("provider_authorized")
            ),
            "provider_used": _clean_token(validation.get("provider_used")),
            "provider_call_cap": _bounded_int(validation.get("provider_call_cap")),
            "results_per_task_cap": _bounded_int(
                validation.get("results_per_task_cap")
            ),
            "action_type": _EXPECTED_ACTION_TYPE,
        }
    )


def _validation_digest_payload(validation: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(validation)
    payload.pop("validation_digest", None)
    return payload


def _candidate_digest_payload(candidate: Mapping[str, Any]) -> dict[str, Any]:
    payload = _safe_mapping(candidate)
    payload.pop("candidate_digest", None)
    return payload


def _contract_ref_or_empty(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    version = _clean_token(
        ref.get("accepted_contract_version")
        or ref.get("current_contract_version")
        or ref.get("contract_version")
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
        "source": _clean_token(ref.get("source")) or "current_answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _handoff_ref_or_empty(value: Any) -> dict[str, Any]:
    ref = _safe_mapping(value)
    handoff_id = _clean_token(ref.get("handoff_id"), limit=220)
    handoff_digest = _clean_token(ref.get("handoff_digest"), limit=128)
    if not handoff_id or not handoff_digest:
        return {}
    return {
        "handoff_id": handoff_id,
        "handoff_digest": handoff_digest,
        "schema_version": _clean_token(ref.get("schema_version")),
        "dedupe_key": _clean_token(ref.get("dedupe_key"), limit=128),
        "contract_parent_kind": _clean_token(ref.get("contract_parent_kind")),
        "parent_current_contract_ref": _contract_ref_or_empty(
            ref.get("parent_current_contract_ref")
        ),
        "parent_initial_contract_ref": _contract_ref_or_empty(
            ref.get("parent_initial_contract_ref")
        ),
    }


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
    if depth > 7:
        return "[truncated]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_token(value, limit=900)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_key_token(key, limit=120)
            if not clean_key:
                continue
            if _is_sensitive_key(clean_key):
                if value[key] is False and clean_key in _SAFE_FALSE_RETENTION_KEYS:
                    out[clean_key] = False
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
    return _clean_token(value, limit=300)


def _required_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LiveSearchValidationRuntimeError(f"{label} must be a mapping")
    return value


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise LiveSearchValidationRuntimeError(message)
    return text


def _required_url(value: Any) -> str:
    url = _required_token(
        value,
        "live search validation candidate requires url",
        limit=700,
    )
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LiveSearchValidationRuntimeError(
            "live search validation candidate requires http(s) url"
        )
    return url


def _positive_int(value: Any, message: str) -> int:
    parsed = _bounded_int(value)
    if parsed <= 0:
        raise LiveSearchValidationRuntimeError(message)
    return parsed


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed < 0:
        return 0
    return parsed


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    return _clean_token(value, limit=limit)


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in _PRIVATE_VALUE_MARKERS):
        return "[redacted]"
    return text[:limit]


def _clean_key_token(value: Any, *, limit: int = 120) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_domain(value: Any) -> str | None:
    text = _clean_token(value, limit=260)
    if not text:
        return None
    parsed = urlparse(f"https://{text}" if "://" not in text else text)
    return (parsed.netloc or parsed.path).lower().strip("/")


def _domain_from_url(value: str) -> str | None:
    parsed = urlparse(value)
    domain = parsed.netloc.lower()
    return domain or None


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


def _ordered_unique(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, bytes):
        items = []
    else:
        try:
            items = list(value)
        except TypeError:
            items = []
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_token(item, limit=260)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _enum_or_text(value: Any) -> str | None:
    if isinstance(value, Enum):
        return str(value.value)
    return _clean_token(value)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "LIVE_SEARCH_VALIDATION_DEFAULT_PROVIDER_CALL_CAP",
    "LIVE_SEARCH_VALIDATION_DEFAULT_RESULTS_PER_TASK_CAP",
    "LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP",
    "LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE",
    "LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE",
    "LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE",
    "LIVE_SEARCH_VALIDATION_EXECUTION_MODES",
    "LIVE_SEARCH_VALIDATION_MAX_SELECTED_TASKS",
    "LIVE_SEARCH_VALIDATION_OBSERVATION_SCHEMA_VERSION",
    "LIVE_SEARCH_VALIDATION_OWNER",
    "LIVE_SEARCH_VALIDATION_REASON",
    "LIVE_SEARCH_VALIDATION_SCHEMA_VERSION",
    "LIVE_SEARCH_VALIDATION_STAGE",
    "LIVE_SEARCH_VALIDATION_TRACE_KEY",
    "LiveSearchValidationRuntimeError",
    "SearchResultCandidateShape",
    "build_live_search_validation_observation_payload",
    "build_live_search_validation_projection",
    "build_live_search_validation_state",
    "contract_ref_from_contract",
    "handoff_ref_from_handoff_state",
    "live_search_validation_ref_from_state",
]
