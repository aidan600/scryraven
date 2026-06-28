"""Shared PR2 invocation scaffold for search-only live validation.

This module is intentionally transport-free. It builds and validates sanitized
request/response shapes that a broker or trusted local runner can use later,
then reduces sanitized provider-result candidates through the PR1 RunKernel
live-search-validation seam when a caller supplies a kernel.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE,
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
    LIVE_SEARCH_VALIDATION_EXECUTION_MODES,
    build_live_search_validation_observation_payload,
    contract_ref_from_contract,
    handoff_ref_from_handoff_state,
)
from core.run_kernel import Observation, ObservationType, RunStageStatus

AG_LIVE_XAXIS_VALIDATION_PR2_PHASE = "AG-LIVE-XAXIS-VALIDATION-01A-PR2"
AG_LIVE_XAXIS_VALIDATION_PR2_PROOF_CLASS = (
    "offline_governed_live_search_invocation_scaffold"
)
AG_LIVE_XAXIS_SEARCH_REQUEST_KIND = "ag_live_xaxis_search_validation"
AG_LIVE_XAXIS_SEARCH_PROFILE = "AG-LIVE-XAXIS-SEARCH-CANDIDATES"
AG_LIVE_XAXIS_SEARCH_SCHEMA_VERSION = (
    "ag_live_xaxis_search_validation_invocation_pr2_v1"
)
AG_LIVE_XAXIS_DEFAULT_JOB_ID = "ag-live-xaxis-validation-01a-pr2-search-once"
AG_LIVE_XAXIS_DEFAULT_PROVIDER_CALL_CAP = 1
AG_LIVE_XAXIS_DEFAULT_RESULTS_PER_TASK_CAP = 2
AG_LIVE_XAXIS_MAX_SELECTED_SEARCH_TASKS = 1
AG_LIVE_XAXIS_ALLOWED_PROVIDERS = frozenset({"serper", "brave"})
AG_LIVE_XAXIS_OUTPUT_DIRNAME = "output"

_ZERO_CAP_FIELDS = (
    "retry_cap",
    "fetch_read_cap",
    "retrieval_cap",
    "evidence_ledger_admission_cap",
    "citation_eligibility_cap",
    "sufficiency_cap",
    "final_answer_packet_cap",
    "author_cap",
)

_DOWNSTREAM_FALSE_FLAGS = {
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

_RETENTION_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
}

_SAFE_TASK_REF_KEYS = (
    "search_task_id",
    "query_intent_id",
    "component_id",
    "search_requirement_id",
    "source_obligation_candidate_ids",
    "provider_preference_hint",
    "max_results",
    "execution_status",
    "not_live",
    "no_fetch_read_policy_active",
)

_ALLOWED_PROVIDER_RESULT_KEYS = frozenset(
    {
        "title",
        "url",
        "link",
        "domain",
        "snippet",
        "date",
        "published_or_observed_date",
        "rank",
        "result_rank",
        "call_index",
        "provider_call_index",
    }
)

_RAW_OR_PRIVATE_RESULT_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "auth_header",
        "auth_headers",
        "authorization",
        "cache",
        "db",
        "db_row",
        "env",
        "full_trace",
        "headers",
        "log",
        "logs",
        "prompt",
        "raw_content",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "secret",
        "token",
    }
)


class LiveSearchValidationInvocationError(ValueError):
    """Raised when the PR2 invocation scaffold shape is unsafe or invalid."""


@dataclass(frozen=True, slots=True)
class LiveSearchValidationCaps:
    """Search-only PR2 cap envelope."""

    provider_call_cap: int = AG_LIVE_XAXIS_DEFAULT_PROVIDER_CALL_CAP
    results_per_task_cap: int = AG_LIVE_XAXIS_DEFAULT_RESULTS_PER_TASK_CAP
    retry_cap: int = 0
    fetch_read_cap: int = 0
    retrieval_cap: int = 0
    evidence_ledger_admission_cap: int = 0
    citation_eligibility_cap: int = 0
    sufficiency_cap: int = 0
    final_answer_packet_cap: int = 0
    author_cap: int = 0

    def to_payload(self) -> dict[str, int]:
        payload = {
            "provider_call_cap": int(self.provider_call_cap),
            "results_per_task_cap": int(self.results_per_task_cap),
            "retry_cap": int(self.retry_cap),
            "fetch_read_cap": int(self.fetch_read_cap),
            "retrieval_cap": int(self.retrieval_cap),
            "evidence_ledger_admission_cap": int(
                self.evidence_ledger_admission_cap
            ),
            "citation_eligibility_cap": int(self.citation_eligibility_cap),
            "sufficiency_cap": int(self.sufficiency_cap),
            "final_answer_packet_cap": int(self.final_answer_packet_cap),
            "author_cap": int(self.author_cap),
        }
        validate_cap_policy(payload)
        return payload


def build_live_search_validation_request_packet(
    *,
    current_answer_contract: Mapping[str, Any],
    search_executor_handoff_state: Mapping[str, Any],
    selected_search_task_ids: Sequence[str],
    provider_authorized: str,
    output_packet_path: str | Path,
    root: str | Path,
    job_id: str = AG_LIVE_XAXIS_DEFAULT_JOB_ID,
    run_id: str | None = None,
    request_id: str | None = None,
    caps: LiveSearchValidationCaps | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the shared broker/direct PR2 request packet."""

    clean_provider = validate_provider_authorized(provider_authorized)
    cap_payload = _caps_payload(caps)
    selected_ids = _ordered_unique(selected_search_task_ids)
    if not selected_ids:
        raise LiveSearchValidationInvocationError(
            "live search validation request requires selected_search_task_ids"
        )
    if len(selected_ids) > AG_LIVE_XAXIS_MAX_SELECTED_SEARCH_TASKS:
        raise LiveSearchValidationInvocationError(
            "live search validation request selected task count exceeds PR2 cap"
        )
    if len(selected_ids) > cap_payload["provider_call_cap"]:
        raise LiveSearchValidationInvocationError(
            "live search validation request selected tasks exceed provider_call_cap"
        )

    contract_ref = contract_ref_from_contract(
        current_answer_contract,
        source="current_answer_contract",
    )
    handoff_ref = handoff_ref_from_handoff_state(search_executor_handoff_state)
    if not contract_ref:
        raise LiveSearchValidationInvocationError(
            "live search validation request requires current_answer_contract ref"
        )
    if not handoff_ref:
        raise LiveSearchValidationInvocationError(
            "live search validation request requires SearchExecutorHandoff ref"
        )
    task_refs = _selected_search_task_refs(
        search_executor_handoff_state,
        selected_ids,
    )
    output_path = validate_safe_output_packet_path(output_packet_path, root=root)
    packet = {
        "request_kind": AG_LIVE_XAXIS_SEARCH_REQUEST_KIND,
        "schema_version": AG_LIVE_XAXIS_SEARCH_SCHEMA_VERSION,
        "job_id": _required_token(job_id, "request requires job_id", limit=180),
        "profile": AG_LIVE_XAXIS_SEARCH_PROFILE,
        "run_id": _required_token(
            run_id or _safe_mapping(current_answer_contract).get("run_id"),
            "request requires run_id",
            limit=180,
        ),
        "request_id": _required_token(
            request_id
            or _safe_mapping(current_answer_contract).get("request_id")
            or _safe_mapping(search_executor_handoff_state).get("request_id"),
            "request requires request_id",
            limit=180,
        ),
        "provider_authorized": clean_provider,
        "selected_search_task_ids": selected_ids,
        **cap_payload,
        **_RETENTION_FALSE_FLAGS,
        "current_answer_contract_ref": contract_ref,
        "search_executor_handoff_ref": handoff_ref,
        "selected_search_task_refs": task_refs,
        "output_packet_path": str(output_path.relative_to(Path(root).resolve())),
        "confirm_live_provider_call_required": True,
        "provider_preference_hint_authority": "diagnostic_only",
        "redaction_posture": "sanitized_candidates_only_no_raw_retention",
        "closed_surface_flags": dict(_DOWNSTREAM_FALSE_FLAGS),
    }
    validate_request_packet(packet, root=root)
    return _json_safe(packet)


def validate_request_packet(
    packet: Mapping[str, Any],
    *,
    root: str | Path,
) -> dict[str, Any]:
    """Validate and return a sanitized PR2 request packet."""

    request = _safe_mapping(packet)
    _reject_forbidden_keys(request, context="live search validation request")
    if request.get("request_kind") != AG_LIVE_XAXIS_SEARCH_REQUEST_KIND:
        raise LiveSearchValidationInvocationError(
            "live search validation request_kind does not match"
        )
    if request.get("schema_version") != AG_LIVE_XAXIS_SEARCH_SCHEMA_VERSION:
        raise LiveSearchValidationInvocationError(
            "live search validation request schema_version does not match"
        )
    if request.get("profile") != AG_LIVE_XAXIS_SEARCH_PROFILE:
        raise LiveSearchValidationInvocationError(
            "live search validation request profile does not match"
        )
    for key in ("job_id", "run_id", "request_id"):
        _required_token(request.get(key), f"request requires {key}", limit=180)
    validate_provider_authorized(request.get("provider_authorized"))
    selected_ids = _ordered_unique(request.get("selected_search_task_ids"))
    if not selected_ids:
        raise LiveSearchValidationInvocationError(
            "request requires selected_search_task_ids"
        )
    if len(selected_ids) > AG_LIVE_XAXIS_MAX_SELECTED_SEARCH_TASKS:
        raise LiveSearchValidationInvocationError(
            "request selected task count exceeds PR2 cap"
        )
    validate_cap_policy(request)
    if len(selected_ids) > int(request["provider_call_cap"]):
        raise LiveSearchValidationInvocationError(
            "request selected tasks exceed provider_call_cap"
        )
    if request.get("confirm_live_provider_call_required") is not True:
        raise LiveSearchValidationInvocationError(
            "request must require confirm_live_provider_call"
        )
    if request.get("raw_provider_payload_retained") is not False:
        raise LiveSearchValidationInvocationError(
            "request must keep raw_provider_payload_retained false"
        )
    if request.get("raw_search_response_retained") is not False:
        raise LiveSearchValidationInvocationError(
            "request must keep raw_search_response_retained false"
        )
    for ref_key in ("current_answer_contract_ref", "search_executor_handoff_ref"):
        if not _safe_mapping(request.get(ref_key)):
            raise LiveSearchValidationInvocationError(f"request requires {ref_key}")
    task_refs = _safe_list(request.get("selected_search_task_refs"))
    if [ref.get("search_task_id") for ref in task_refs] != selected_ids:
        raise LiveSearchValidationInvocationError(
            "request selected_search_task_refs must match selected ids"
        )
    for task_ref in task_refs:
        _validate_selected_task_ref(_safe_mapping(task_ref))
    validate_safe_output_packet_path(request.get("output_packet_path"), root=root)
    _validate_closed_surface_flags(request.get("closed_surface_flags"))
    return _json_safe(request)


def validate_cap_policy(caps: Mapping[str, Any]) -> dict[str, int]:
    """Validate PR2 cap policy and return normalized integers."""

    normalized = {
        "provider_call_cap": _positive_int(
            caps.get("provider_call_cap"),
            "provider_call_cap must be positive",
        ),
        "results_per_task_cap": _positive_int(
            caps.get("results_per_task_cap"),
            "results_per_task_cap must be positive",
        ),
    }
    if normalized["provider_call_cap"] > AG_LIVE_XAXIS_DEFAULT_PROVIDER_CALL_CAP:
        raise LiveSearchValidationInvocationError(
            "provider_call_cap exceeds AG-LIVE-XAXIS-SEARCH-CANDIDATES cap"
        )
    if normalized["results_per_task_cap"] > AG_LIVE_XAXIS_DEFAULT_RESULTS_PER_TASK_CAP:
        raise LiveSearchValidationInvocationError(
            "results_per_task_cap exceeds AG-LIVE-XAXIS-SEARCH-CANDIDATES cap"
        )
    for key in _ZERO_CAP_FIELDS:
        value = _bounded_int(caps.get(key))
        if value != 0:
            raise LiveSearchValidationInvocationError(f"{key} must be zero")
        normalized[key] = 0
    return normalized


def validate_provider_authorized(value: Any) -> str:
    provider = _required_token(
        value,
        "live search validation requires provider_authorized",
        limit=80,
    )
    if provider not in AG_LIVE_XAXIS_ALLOWED_PROVIDERS:
        raise LiveSearchValidationInvocationError(
            "provider_authorized is not allowlisted"
        )
    return provider


def validate_safe_output_packet_path(path: Any, *, root: str | Path) -> Path:
    """Resolve and require an output path under repo output/."""

    raw = _required_token(path, "output_packet_path is required", limit=400)
    root_path = Path(root).resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    resolved = candidate.resolve()
    output_root = (root_path / AG_LIVE_XAXIS_OUTPUT_DIRNAME).resolve()
    try:
        resolved.relative_to(output_root)
    except ValueError as exc:
        raise LiveSearchValidationInvocationError(
            "output_packet_path must stay under output/"
        ) from exc
    return resolved


def normalize_provider_results_by_task(
    *,
    request_packet: Mapping[str, Any],
    provider_results_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    root: str | Path,
) -> dict[str, list[dict[str, Any]]]:
    """Normalize sanitized provider result records by selected task id."""

    request = validate_request_packet(request_packet, root=root)
    selected_ids = _ordered_unique(request["selected_search_task_ids"])
    selected_set = set(selected_ids)
    results_per_task_cap = int(request["results_per_task_cap"])
    raw_result_map: dict[str, Sequence[Mapping[str, Any]]] = {}
    for raw_task_id, raw_results in provider_results_by_task.items():
        task_id = _required_token(
            raw_task_id,
            "provider result task id is required",
            limit=260,
        )
        if task_id in raw_result_map:
            raise LiveSearchValidationInvocationError(
                "provider results contain duplicate search task ids"
            )
        if task_id not in selected_set:
            raise LiveSearchValidationInvocationError(
                "provider results reference unselected search task"
            )
        if isinstance(raw_results, str | bytes) or not isinstance(
            raw_results,
            Sequence,
        ):
            raise LiveSearchValidationInvocationError(
                "provider results for selected search task must be a sequence"
            )
        raw_result_map[task_id] = raw_results

    missing_task_ids = [
        task_id for task_id in selected_ids if task_id not in raw_result_map
    ]
    if missing_task_ids:
        raise LiveSearchValidationInvocationError(
            "provider results missing selected search task ids: "
            + ", ".join(missing_task_ids)
        )

    normalized: dict[str, list[dict[str, Any]]] = {}
    for task_id in selected_ids:
        result_list = _safe_list(raw_result_map[task_id])
        if len(result_list) > results_per_task_cap:
            raise LiveSearchValidationInvocationError(
                "provider results exceed results_per_task_cap"
            )
        normalized[task_id] = [
            normalize_provider_result(
                result,
                default_rank=index,
                default_call_index=index,
            )
            for index, result in enumerate(result_list, start=1)
        ]
    return normalized


def normalize_provider_result(
    result: Mapping[str, Any],
    *,
    default_rank: int = 1,
    default_call_index: int = 1,
) -> dict[str, Any]:
    """Normalize one sanitized provider result into PR1 candidate input shape."""

    raw = _safe_mapping(result)
    _reject_forbidden_keys(raw, context="provider result")
    unknown = sorted(set(raw) - _ALLOWED_PROVIDER_RESULT_KEYS)
    if unknown:
        raise LiveSearchValidationInvocationError(
            "provider result contains unsupported fields: " + ", ".join(unknown)
        )
    title = _required_token(raw.get("title"), "provider result requires title", 220)
    url = _required_url(raw.get("url") or raw.get("link"))
    domain = _clean_domain(raw.get("domain")) or _domain_from_url(url)
    if not domain:
        raise LiveSearchValidationInvocationError(
            "provider result requires domain or http(s) URL"
        )
    return _without_empty(
        {
            "title": title,
            "url": url,
            "domain": domain,
            "snippet": _clean_token(raw.get("snippet"), limit=500),
            "published_or_observed_date": _clean_token(
                raw.get("published_or_observed_date") or raw.get("date"),
                limit=80,
            ),
            "result_rank": _positive_int(
                raw.get("result_rank") or raw.get("rank") or default_rank,
                "provider result rank must be positive",
            ),
            "provider_call_index": _positive_int(
                raw.get("provider_call_index")
                or raw.get("call_index")
                or default_call_index,
                "provider result call index must be positive",
            ),
        }
    )


def build_broker_request_envelope(
    request_packet: Mapping[str, Any],
    *,
    root: str | Path,
    confirm_live_provider_call: bool,
) -> dict[str, Any]:
    """Build the broker-facing envelope without sending it."""

    request = validate_request_packet(request_packet, root=root)
    return {
        "request_kind": AG_LIVE_XAXIS_SEARCH_REQUEST_KIND,
        "job_id": request["job_id"],
        "confirm_live_provider_call": bool(confirm_live_provider_call),
        "profile": AG_LIVE_XAXIS_SEARCH_PROFILE,
        "broker_request": request,
    }


def reduce_provider_results_through_run_kernel(
    *,
    kernel: Any,
    request_packet: Mapping[str, Any],
    provider_results_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    root: str | Path,
    execution_mode: str,
    broker_invoked: bool,
    live_provider_called: bool,
) -> dict[str, Any]:
    """Authorize and reduce sanitized candidate results through RunKernel."""

    request = validate_request_packet(request_packet, root=root)
    normalized_results = normalize_provider_results_by_task(
        request_packet=request,
        provider_results_by_task=provider_results_by_task,
        root=root,
    )
    provider_call_count = len(_ordered_unique(request["selected_search_task_ids"]))
    action = kernel.authorize_live_search_validation(
        selected_search_task_ids=request["selected_search_task_ids"],
        provider_authorized=request["provider_authorized"],
        provider_call_cap=int(request["provider_call_cap"]),
        results_per_task_cap=int(request["results_per_task_cap"]),
        parent_current_contract_version=request["current_answer_contract_ref"][
            "contract_version"
        ],
        parent_current_contract_digest=request["current_answer_contract_ref"][
            "contract_digest"
        ],
        handoff_id=request["search_executor_handoff_ref"]["handoff_id"],
        handoff_digest=request["search_executor_handoff_ref"]["handoff_digest"],
    )
    payload = build_live_search_validation_observation_payload(
        action=action,
        current_answer_contract=kernel.state.current_answer_contract,
        search_executor_handoff_state=kernel.state.search_executor_handoff_state,
        provider_used=request["provider_authorized"],
        provider_results_by_task=normalized_results,
        provider_calls_attempted_count=provider_call_count,
        provider_calls_completed_count=provider_call_count,
        execution_mode=execution_mode,
        broker_invoked=broker_invoked,
        live_provider_called=live_provider_called,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    kernel.reduce(observation)
    return build_output_packet(
        request_packet=request,
        validation_state=kernel.state.live_search_validation_state,
        budget_exhausted=False,
        decision_made_by_run="search_result_candidates_reduced",
    )


def build_output_packet(
    *,
    request_packet: Mapping[str, Any],
    validation_state: Mapping[str, Any] | None = None,
    budget_exhausted: bool,
    decision_made_by_run: str,
) -> dict[str, Any]:
    """Build the sanitized PR2 output packet."""

    request = _safe_mapping(request_packet)
    state = _safe_mapping(validation_state)
    candidates = _safe_list(state.get("search_result_candidates"))
    provider_used = (
        _clean_token(state.get("provider_used"))
        or _clean_token(request.get("provider_authorized"))
        or ""
    )
    execution_mode = (
        _clean_token(state.get("execution_mode"))
        or LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE
    )
    packet = {
        "phase": AG_LIVE_XAXIS_VALIDATION_PR2_PHASE,
        "proof_class": AG_LIVE_XAXIS_VALIDATION_PR2_PROOF_CLASS,
        "request_kind": AG_LIVE_XAXIS_SEARCH_REQUEST_KIND,
        "job_id": request.get("job_id"),
        "profile": request.get("profile"),
        "run_id": request.get("run_id"),
        "request_id": request.get("request_id"),
        "provider_authorized": request.get("provider_authorized"),
        "provider_used": provider_used,
        "provider_call_cap": request.get("provider_call_cap"),
        "provider_calls_attempted": state.get("provider_calls_attempted", 0),
        "provider_calls_completed": state.get("provider_calls_completed", 0),
        "results_per_task_cap": request.get("results_per_task_cap"),
        "selected_search_task_ids": _ordered_unique(
            request.get("selected_search_task_ids")
        ),
        "current_answer_contract_ref": _safe_mapping(
            request.get("current_answer_contract_ref")
        ),
        "search_executor_handoff_ref": _safe_mapping(
            request.get("search_executor_handoff_ref")
        ),
        "search_result_candidates": candidates,
        "candidate_count": len(candidates),
        "execution_mode": execution_mode,
        "broker_invoked": bool(state.get("broker_invoked", False)),
        "live_provider_called": bool(state.get("live_provider_called", False)),
        **_RETENTION_FALSE_FLAGS,
        **_DOWNSTREAM_FALSE_FLAGS,
        "budget_exhausted": bool(budget_exhausted),
        "decision_made_by_run": _required_token(
            decision_made_by_run,
            "output packet requires decision_made_by_run",
            limit=180,
        ),
    }
    _validate_downstream_packet_flags(packet)
    if packet["raw_provider_payload_retained"] is not False:
        raise LiveSearchValidationInvocationError(
            "output packet must not retain raw provider payloads"
        )
    if packet["raw_search_response_retained"] is not False:
        raise LiveSearchValidationInvocationError(
            "output packet must not retain raw search responses"
        )
    return _json_safe(packet)


def request_packet_digest(packet: Mapping[str, Any]) -> str:
    return _digest_json(packet)


def dumps_packet(packet: Mapping[str, Any]) -> str:
    return json.dumps(_json_safe(packet), indent=2, sort_keys=True) + "\n"


def execution_facts_for_mode(mode: str) -> dict[str, Any]:
    clean_mode = _required_token(mode, "execution mode is required", limit=80)
    if clean_mode not in LIVE_SEARCH_VALIDATION_EXECUTION_MODES:
        raise LiveSearchValidationInvocationError("execution mode is not allowed")
    return {
        "execution_mode": clean_mode,
        "broker_invoked": clean_mode == LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE,
        "live_provider_called": clean_mode
        in {
            LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE,
            LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
        },
    }


def _caps_payload(
    caps: LiveSearchValidationCaps | Mapping[str, Any] | None,
) -> dict[str, int]:
    if caps is None:
        return LiveSearchValidationCaps().to_payload()
    if isinstance(caps, LiveSearchValidationCaps):
        return caps.to_payload()
    return validate_cap_policy(_safe_mapping(caps))


def _selected_search_task_refs(
    search_executor_handoff_state: Mapping[str, Any],
    selected_ids: Sequence[str],
) -> list[dict[str, Any]]:
    tasks_by_id = {
        _clean_token(task.get("search_task_id"), limit=260): _safe_mapping(task)
        for task in _safe_list(
            _safe_mapping(search_executor_handoff_state).get("search_task_records")
        )
        if isinstance(task, Mapping)
    }
    refs: list[dict[str, Any]] = []
    for task_id in selected_ids:
        task = tasks_by_id.get(task_id)
        if not task:
            raise LiveSearchValidationInvocationError(
                "selected search task is missing from SearchExecutorHandoff"
            )
        ref = {key: _json_safe(task.get(key)) for key in _SAFE_TASK_REF_KEYS}
        ref = _without_empty(ref)
        _validate_selected_task_ref(ref)
        refs.append(ref)
    return refs


def _validate_selected_task_ref(task_ref: Mapping[str, Any]) -> None:
    for key in ("search_task_id", "query_intent_id", "component_id"):
        _required_token(task_ref.get(key), f"selected task ref requires {key}")
    if task_ref.get("execution_status") not in {None, "not_executed"}:
        raise LiveSearchValidationInvocationError(
            "selected task ref must remain not_executed"
        )
    if task_ref.get("not_live") is not True:
        raise LiveSearchValidationInvocationError("selected task ref must be not_live")
    if task_ref.get("no_fetch_read_policy_active") is not True:
        raise LiveSearchValidationInvocationError(
            "selected task ref must keep no_fetch_read_policy_active"
        )
    _reject_forbidden_keys(task_ref, context="selected search task ref")


def _validate_closed_surface_flags(value: Any) -> None:
    flags = _safe_mapping(value)
    for forbidden in ("broker_invoked", "live_provider_called"):
        if forbidden in flags:
            raise LiveSearchValidationInvocationError(
                "execution facts must not be closed_surface_flags"
            )
    for key, expected in _DOWNSTREAM_FALSE_FLAGS.items():
        if flags.get(key, expected) is not expected:
            raise LiveSearchValidationInvocationError(
                f"closed surface flag {key} must be false"
            )


def _validate_downstream_packet_flags(packet: Mapping[str, Any]) -> None:
    for key, expected in _DOWNSTREAM_FALSE_FLAGS.items():
        if packet.get(key) is not expected:
            raise LiveSearchValidationInvocationError(
                f"output packet downstream flag {key} must be false"
            )


def _reject_forbidden_keys(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(
        key
        for key in keys
        if key in _RAW_OR_PRIVATE_RESULT_KEYS or key.startswith("raw_")
    )
    for safe_key in _RETENTION_FALSE_FLAGS:
        if safe_key in forbidden:
            forbidden.remove(safe_key)
    if forbidden:
        raise LiveSearchValidationInvocationError(
            f"{context} contains raw/private fields: " + ", ".join(forbidden)
        )


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
    if isinstance(value, str):
        return _clean_token(value, limit=900)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            clean_key = _clean_token(key, limit=120)
            if clean_key:
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


def _required_url(value: Any) -> str:
    url = _required_token(value, "provider result requires url", limit=700)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LiveSearchValidationInvocationError(
            "provider result requires http(s) url"
        )
    return url


def _required_token(value: Any, message: str, limit: int = 160) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise LiveSearchValidationInvocationError(message)
    return text


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in ("api_key", "bearer ", "secret")):
        return "[redacted]"
    return text[:limit]


def _clean_domain(value: Any) -> str | None:
    text = _clean_token(value, limit=260)
    if not text:
        return None
    parsed = urlparse(f"https://{text}" if "://" not in text else text)
    return (parsed.netloc or parsed.path).lower().strip("/")


def _domain_from_url(value: str) -> str | None:
    parsed = urlparse(value)
    return parsed.netloc.lower() or None


def _positive_int(value: Any, message: str) -> int:
    parsed = _bounded_int(value)
    if parsed <= 0:
        raise LiveSearchValidationInvocationError(message)
    return parsed


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed >= 0 else 0


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


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "AG_LIVE_XAXIS_ALLOWED_PROVIDERS",
    "AG_LIVE_XAXIS_DEFAULT_JOB_ID",
    "AG_LIVE_XAXIS_DEFAULT_PROVIDER_CALL_CAP",
    "AG_LIVE_XAXIS_DEFAULT_RESULTS_PER_TASK_CAP",
    "AG_LIVE_XAXIS_MAX_SELECTED_SEARCH_TASKS",
    "AG_LIVE_XAXIS_SEARCH_PROFILE",
    "AG_LIVE_XAXIS_SEARCH_REQUEST_KIND",
    "AG_LIVE_XAXIS_SEARCH_SCHEMA_VERSION",
    "AG_LIVE_XAXIS_VALIDATION_PR2_PHASE",
    "AG_LIVE_XAXIS_VALIDATION_PR2_PROOF_CLASS",
    "LiveSearchValidationCaps",
    "LiveSearchValidationInvocationError",
    "build_broker_request_envelope",
    "build_live_search_validation_request_packet",
    "build_output_packet",
    "dumps_packet",
    "execution_facts_for_mode",
    "normalize_provider_result",
    "normalize_provider_results_by_task",
    "reduce_provider_results_through_run_kernel",
    "request_packet_digest",
    "validate_cap_policy",
    "validate_provider_authorized",
    "validate_request_packet",
    "validate_safe_output_packet_path",
]
