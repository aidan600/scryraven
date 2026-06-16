"""Live-gated follow-up provider-job validation seam for AG-96I3B/AG-96I3C.

This module is a validation harness around the AG-96I3A provider-job execution
seam. It consumes a RunKernel-authorized official/current provider-job action,
optionally performs exactly one configured search call, strips provider output
to sanitized candidate facts, and feeds those facts back through the existing
follow-up provider-job executor. AG-96I3C adds sanitized result-set diagnostics
and provider-job-aware candidate selection. It owns no answer authority.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Mapping

from core.followup_deliberation import ProviderJobKind, clean_text, clean_token
from core.followup_provider_job_execution_runtime import (
    FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
    FollowupProviderJobExecutionActionResult,
    execute_followup_provider_job_action,
)
from core.followup_provider_result_set_diagnostics import (
    DISCOVERY_UNCONSTRAINED,
    build_official_current_discovery_diagnostics,
    sanitize_result_set_diagnostics,
    selected_or_bridge_result,
)

AG96I3B_LIVE_VALIDATION_SCHEMA_VERSION = "ag96i3b_live_followup_validation_v2"
AG96I3B_EXACT_VALIDATION_QUERY = (
    "What is the current IRS standard mileage rate for business use of a car "
    "in 2026, and what official source supports it? Keep the answer concise."
)
AG96I3B_LIVE_VALIDATION_PROVIDER_NAME = "brave_reconnaissance"

LIVE_VALIDATION_STATUS_CONFIG_MISSING = "config_missing_not_run"
LIVE_VALIDATION_STATUS_PROVIDER_SEARCH_ERROR = "provider_search_error"
LIVE_VALIDATION_STATUS_CANDIDATE_ACQUIRED = "candidate_acquired"
LIVE_VALIDATION_STATUS_NO_RESULT = "no_result"

ProviderSearch = Callable[[str], Iterable[Mapping[str, Any]]]
ConfigAvailable = Callable[[], bool]

_ALLOWED_CANDIDATE_FACT_KEYS = frozenset(
    {
        "url",
        "title",
        "domain",
        "source_tier",
        "source_class",
        "currentness_signal",
        "readable_status",
        "fetchable_status",
        "provider_name",
        "retrieval_pass_id",
        "adapter_result_id",
        "result_status",
        "bridge_only",
        "authorized_query_ref",
        "authorized_query",
    }
)

_OFFICIAL_CURRENT_JOB_KIND = (
    ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value
)
_SCOUT_BRIDGE_JOB_KINDS = frozenset(
    {
        ProviderJobKind.SCOUT_DISAMBIGUATION.value,
        ProviderJobKind.BRIDGE_HINT_DISCOVERY.value,
    }
)


@dataclass(frozen=True, slots=True)
class FollowupProviderJobLiveValidationRecord:
    validation_id: str
    run_id: str
    provider_job_kind: str
    authorized_query_ref: str | None
    authorized_query: str | None
    provider_name: str
    provider_config_available: bool
    provider_search_call_count: int
    fetch_read_attempt_count: int
    result_status: str
    stop_reason: str
    sanitized_candidate_facts: Mapping[str, Any]
    sanitized_result_set_diagnostics: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        candidate = _sanitize_candidate_fact_mapping(
            self.sanitized_candidate_facts,
            authorized_query_ref=self.authorized_query_ref,
            authorized_query=self.authorized_query,
            provider_name=self.provider_name,
            result_status=self.result_status,
        )
        return {
            "schema_version": AG96I3B_LIVE_VALIDATION_SCHEMA_VERSION,
            "record_type": "followup_provider_job_live_validation_record",
            "owner": "FollowupProviderJobLiveValidationRuntime",
            "canonical_state": False,
            "trace_only": False,
            "storage_only": False,
            "validation_id": clean_text(self.validation_id, limit=220),
            "run_id": clean_token(self.run_id),
            "provider_job_kind": clean_token(self.provider_job_kind),
            "authorized_query_ref": clean_token(
                self.authorized_query_ref,
                limit=180,
            ),
            "authorized_query": clean_text(self.authorized_query, limit=300),
            "provider_name": clean_token(self.provider_name),
            "provider_config_available": bool(self.provider_config_available),
            "provider_search_call_count": int(self.provider_search_call_count),
            "provider_search_call_occurred": self.provider_search_call_count > 0,
            "fetch_read_attempt_count": int(self.fetch_read_attempt_count),
            "fetch_read_occurred": self.fetch_read_attempt_count > 0,
            "live_budget": {
                "max_provider_search_calls": 1,
                "max_fetch_read_attempts": 0,
                "provider_search_call_count": int(self.provider_search_call_count),
                "fetch_read_attempt_count": int(self.fetch_read_attempt_count),
                "no_retries": True,
                "model_call_count": 0,
                "author_executor_call_count": 0,
            },
            "result_status": clean_token(self.result_status),
            "stop_reason": clean_token(self.stop_reason, limit=180),
            "sanitized_candidate_facts": candidate,
            "provider_result_set_diagnostics": sanitize_result_set_diagnostics(
                self.sanitized_result_set_diagnostics,
                provider_job_kind=self.provider_job_kind,
                provider_name=self.provider_name,
            ),
            "bridge_only": bool(candidate.get("bridge_only")),
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": _redaction_posture(),
            "raw_private_payloads_retained": False,
        }


@dataclass(frozen=True, slots=True)
class FollowupProviderJobLiveValidationActionResult:
    validation_record: FollowupProviderJobLiveValidationRecord
    provider_job_action_result: FollowupProviderJobExecutionActionResult | None

    def to_dict(self) -> dict[str, Any]:
        action_result = self.provider_job_action_result
        provider_job_state = (
            action_result.record.to_dict() if action_result is not None else None
        )
        return {
            "validation_record": self.validation_record.to_dict(),
            "provider_job_execution_state": provider_job_state,
        }


def execute_live_gated_followup_provider_job_validation_action(
    action: Any,
    *,
    live_validation_authorized: bool,
    provider_search: ProviderSearch | None = None,
    provider_config_available: ConfigAvailable | None = None,
    provider_name: str = AG96I3B_LIVE_VALIDATION_PROVIDER_NAME,
) -> FollowupProviderJobLiveValidationActionResult:
    """Run the AG-96I3B validation gate for one authorized provider-job action."""

    from core.run_kernel import (  # Local import avoids a module import cycle.
        FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE,
        ActionType,
        ObservationType,
        validate_authorized_action,
    )

    if live_validation_authorized is not True:
        raise PermissionError("AG-96I3B live validation requires explicit authorization")
    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_PROVIDER_JOB_EXECUTE,
        stage=FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED
        ),
    )
    inputs = dict(authorized.inputs)
    _validate_authorized_provider_job_inputs(inputs)

    authorized_query_ref = clean_token(inputs.get("authorized_query_ref"), limit=180)
    authorized_query = clean_text(inputs.get("authorized_query"), limit=300)
    query = authorized_query
    if not query:
        raise PermissionError("AG-96I3B live validation requires executable query text")

    config_available = (
        bool(provider_config_available())
        if provider_config_available is not None
        else _brave_config_available()
    )
    if not config_available:
        return _validation_only_result(
            inputs,
            provider_name=provider_name,
            provider_config_available=False,
            provider_search_call_count=0,
            result_status=LIVE_VALIDATION_STATUS_CONFIG_MISSING,
            stop_reason="provider_config_missing",
            candidate={},
            diagnostics=_empty_result_set_diagnostics(
                provider_job_kind=str(inputs.get("provider_job_kind") or ""),
                provider_name=provider_name,
                first_failure_layer="provider_config",
            ),
        )

    search = provider_search or _brave_provider_search
    provider_search_call_count = 0
    try:
        provider_search_call_count += 1
        search_results = list(search(query))
    except Exception:
        candidate = _adapter_error_candidate(
            provider_name=provider_name,
            authorized_query_ref=authorized_query_ref,
            authorized_query=authorized_query,
        )
        provider_job_action_result = execute_followup_provider_job_action(
            action,
            adapter_result_payload=candidate,
        )
        record = _validation_record(
            inputs,
            provider_name=provider_name,
            provider_config_available=True,
            provider_search_call_count=provider_search_call_count,
            result_status=LIVE_VALIDATION_STATUS_PROVIDER_SEARCH_ERROR,
            stop_reason="provider_search_error",
            candidate=candidate,
            diagnostics=_empty_result_set_diagnostics(
                provider_job_kind=str(inputs.get("provider_job_kind") or ""),
                provider_name=provider_name,
                first_failure_layer="provider_search",
            ),
        )
        return FollowupProviderJobLiveValidationActionResult(
            validation_record=record,
            provider_job_action_result=provider_job_action_result,
        )

    candidate, diagnostics = _candidate_from_search_results(
        search_results,
        provider_job_kind=str(inputs.get("provider_job_kind") or ""),
        provider_name=provider_name,
        authorized_query_ref=authorized_query_ref,
        authorized_query=authorized_query,
    )
    result_status = str(candidate.get("result_status") or LIVE_VALIDATION_STATUS_NO_RESULT)
    stop_reason = _stop_reason_for_candidate(
        candidate,
        diagnostics=diagnostics,
        result_status=result_status,
    )
    provider_job_action_result = None
    if inputs.get("provider_job_kind") == _OFFICIAL_CURRENT_JOB_KIND:
        provider_job_action_result = execute_followup_provider_job_action(
            action,
            adapter_result_payload=candidate,
        )
    record = _validation_record(
        inputs,
        provider_name=provider_name,
        provider_config_available=True,
        provider_search_call_count=provider_search_call_count,
        result_status=result_status,
        stop_reason=stop_reason,
        candidate=candidate,
        diagnostics=diagnostics,
    )
    return FollowupProviderJobLiveValidationActionResult(
        validation_record=record,
        provider_job_action_result=provider_job_action_result,
    )


def _validate_authorized_provider_job_inputs(inputs: Mapping[str, Any]) -> None:
    provider_job_kind = clean_token(inputs.get("provider_job_kind"))
    if provider_job_kind not in {_OFFICIAL_CURRENT_JOB_KIND, *_SCOUT_BRIDGE_JOB_KINDS}:
        raise PermissionError(
            "AG-96I3B live validation only accepts official/current or scout/bridge-hint"
        )
    if inputs.get("execution_mode") != FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE:
        raise PermissionError("AG-96I3B live validation requires the AG-96I3A seam")
    if not (
        clean_token(inputs.get("authorized_query_ref"), limit=180)
        or clean_text(inputs.get("authorized_query"), limit=300)
    ):
        raise PermissionError("AG-96I3B live validation requires authorized query/ref")
    if inputs.get("provider_execution_licensed") is not False:
        raise PermissionError("AG-96I3B live validation requires RunKernel custody")
    if inputs.get("model_called") is not False:
        raise PermissionError("AG-96I3B live validation cannot inherit model calls")
    try:
        ProviderJobKind(inputs.get("provider_job_kind"))
    except ValueError:
        raise PermissionError("AG-96I3B live validation requires known provider job")


def _candidate_from_search_results(
    results: list[Mapping[str, Any]],
    *,
    provider_job_kind: str,
    provider_name: str,
    authorized_query_ref: str | None,
    authorized_query: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider_job_kind = clean_token(provider_job_kind)
    diagnostics = build_official_current_discovery_diagnostics(
        results,
        provider_job_kind=provider_job_kind,
        provider_name=provider_name,
        provider_surface_role="candidate_acquisition",
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
        authorized_query_ref=authorized_query_ref,
        authorized_query=authorized_query,
    )
    selected = selected_or_bridge_result(diagnostics)
    if selected is None:
        return _no_result_candidate(
            provider_name=provider_name,
            authorized_query_ref=authorized_query_ref,
            authorized_query=authorized_query,
        ), diagnostics
    bridge_only = bool(diagnostics.get("bridge_only"))
    result_status = (
        "bridge_only" if bridge_only else LIVE_VALIDATION_STATUS_CANDIDATE_ACQUIRED
    )
    candidate = {
        "adapter_result_id": (
            f"ag96i3b-live-validation-result-{selected.get('rank') or 0}"
        ),
        "url": selected.get("url"),
        "title": selected.get("title"),
        "domain": selected.get("domain"),
        "source_tier": selected.get("source_tier"),
        "source_class": selected.get("source_class"),
        "currentness_signal": selected.get("currentness_signal"),
        "readable_status": "read_not_authorized_by_validation_gate",
        "fetchable_status": "fetch_not_authorized_by_validation_gate",
        "provider_name": clean_token(provider_name),
        "retrieval_pass_id": "ag96i3b-live-validation-search-pass-1",
        "result_status": result_status,
        "bridge_only": bridge_only,
        "authorized_query_ref": authorized_query_ref,
        "authorized_query": authorized_query,
    }
    return _sanitize_candidate_fact_mapping(
        candidate,
        authorized_query_ref=authorized_query_ref,
        authorized_query=authorized_query,
        provider_name=provider_name,
        result_status=result_status,
    ), diagnostics


def _no_result_candidate(
    *,
    provider_name: str,
    authorized_query_ref: str | None,
    authorized_query: str | None,
) -> dict[str, Any]:
    return _sanitize_candidate_fact_mapping(
        {
            "adapter_result_id": "ag96i3b-live-validation-no-result",
            "source_class": "unknown",
            "currentness_signal": "not_evaluated",
            "readable_status": "not_evaluated",
            "fetchable_status": "not_evaluated",
            "provider_name": provider_name,
            "retrieval_pass_id": "ag96i3b-live-validation-search-pass-1",
            "result_status": LIVE_VALIDATION_STATUS_NO_RESULT,
            "bridge_only": False,
        },
        authorized_query_ref=authorized_query_ref,
        authorized_query=authorized_query,
        provider_name=provider_name,
        result_status=LIVE_VALIDATION_STATUS_NO_RESULT,
    )


def _adapter_error_candidate(
    *,
    provider_name: str,
    authorized_query_ref: str | None,
    authorized_query: str | None,
) -> dict[str, Any]:
    return _sanitize_candidate_fact_mapping(
        {
            "adapter_result_id": "ag96i3b-live-validation-provider-error",
            "source_class": "unknown",
            "currentness_signal": "not_evaluated",
            "readable_status": "not_evaluated",
            "fetchable_status": "not_evaluated",
            "provider_name": provider_name,
            "retrieval_pass_id": "ag96i3b-live-validation-search-pass-1",
            "result_status": "adapter_error",
            "adapter_error": True,
            "adapter_error_code": "provider_search_error",
            "bridge_only": False,
        },
        authorized_query_ref=authorized_query_ref,
        authorized_query=authorized_query,
        provider_name=provider_name,
        result_status="adapter_error",
    ) | {"adapter_error": True, "adapter_error_code": "provider_search_error"}


def _sanitize_candidate_fact_mapping(
    value: Mapping[str, Any],
    *,
    authorized_query_ref: str | None,
    authorized_query: str | None,
    provider_name: str,
    result_status: str,
) -> dict[str, Any]:
    source = _mapping(value)
    out = {
        "url": clean_text(source.get("url"), limit=500),
        "title": clean_text(source.get("title"), limit=300),
        "domain": clean_text(source.get("domain"), limit=160),
        "source_tier": clean_token(source.get("source_tier")),
        "source_class": clean_token(source.get("source_class")) or "unknown",
        "currentness_signal": clean_token(
            source.get("currentness_signal") or "not_evaluated"
        ),
        "readable_status": clean_token(
            source.get("readable_status") or "not_evaluated"
        ),
        "fetchable_status": clean_token(
            source.get("fetchable_status") or "not_evaluated"
        ),
        "provider_name": clean_token(source.get("provider_name") or provider_name),
        "retrieval_pass_id": clean_token(
            source.get("retrieval_pass_id")
            or source.get("adapter_result_id")
            or "ag96i3b-live-validation-search-pass-1",
            limit=180,
        ),
        "adapter_result_id": clean_token(
            source.get("adapter_result_id")
            or source.get("retrieval_pass_id")
            or "ag96i3b-live-validation-result",
            limit=180,
        ),
        "result_status": clean_token(
            source.get("result_status") or result_status,
            limit=120,
        ),
        "bridge_only": bool(source.get("bridge_only")),
        "authorized_query_ref": clean_token(authorized_query_ref, limit=180),
        "authorized_query": clean_text(authorized_query, limit=300),
    }
    return {key: out[key] for key in _ALLOWED_CANDIDATE_FACT_KEYS}


def _validation_only_result(
    inputs: Mapping[str, Any],
    *,
    provider_name: str,
    provider_config_available: bool,
    provider_search_call_count: int,
    result_status: str,
    stop_reason: str,
    candidate: Mapping[str, Any],
    diagnostics: Mapping[str, Any] | None = None,
) -> FollowupProviderJobLiveValidationActionResult:
    return FollowupProviderJobLiveValidationActionResult(
        validation_record=_validation_record(
            inputs,
            provider_name=provider_name,
            provider_config_available=provider_config_available,
            provider_search_call_count=provider_search_call_count,
            result_status=result_status,
            stop_reason=stop_reason,
            candidate=candidate,
            diagnostics=diagnostics or {},
        ),
        provider_job_action_result=None,
    )


def _validation_record(
    inputs: Mapping[str, Any],
    *,
    provider_name: str,
    provider_config_available: bool,
    provider_search_call_count: int,
    result_status: str,
    stop_reason: str,
    candidate: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
) -> FollowupProviderJobLiveValidationRecord:
    return FollowupProviderJobLiveValidationRecord(
        validation_id=(
            "ag96i3b-live-validation:"
            f"{inputs.get('checkpoint_id')}:{inputs.get('sealed_candidate_id')}"
        ),
        run_id=str(inputs.get("run_id") or ""),
        provider_job_kind=str(inputs.get("provider_job_kind") or ""),
        authorized_query_ref=clean_token(inputs.get("authorized_query_ref"), limit=180),
        authorized_query=clean_text(inputs.get("authorized_query"), limit=300),
        provider_name=provider_name,
        provider_config_available=provider_config_available,
        provider_search_call_count=provider_search_call_count,
        fetch_read_attempt_count=0,
        result_status=result_status,
        stop_reason=stop_reason,
        sanitized_candidate_facts=candidate,
        sanitized_result_set_diagnostics=diagnostics,
    )


def _brave_config_available() -> bool:
    import os

    return bool(os.getenv("BRAVE_API_KEY"))


def _brave_provider_search(query: str) -> Iterable[Mapping[str, Any]]:
    from core.search_providers import brave_reconnaissance

    return brave_reconnaissance(
        query,
        num_results=5,
        cost_phase="followup_live_validation",
    )


def _stop_reason_for_candidate(
    candidate: Mapping[str, Any],
    *,
    diagnostics: Mapping[str, Any],
    result_status: str,
) -> str:
    first_failure = clean_token(diagnostics.get("first_failure_layer"))
    selected_reason = clean_token(diagnostics.get("selected_candidate_reason"))
    if result_status == LIVE_VALIDATION_STATUS_CANDIDATE_ACQUIRED:
        return "candidate_acquired"
    if first_failure == "provider_job_surface_alignment":
        return "provider_surface_mismatch_bridge_hint_only"
    if selected_reason == "no_satisfying_official_current_candidate_bridge_hint_recorded":
        return "no_satisfying_official_current_candidate"
    if selected_reason == "provider_result_set_lacked_official_current_candidate":
        return "no_satisfying_official_current_candidate"
    if selected_reason == "scout_bridge_hint_recorded_not_official_current_satisfaction":
        return "provider_hints_recorded"
    if bool(candidate.get("bridge_only")):
        return "provider_bridge_hint_recorded"
    return "provider_search_returned_no_candidate"


def _empty_result_set_diagnostics(
    *,
    provider_job_kind: str,
    provider_name: str,
    first_failure_layer: str,
) -> dict[str, Any]:
    diagnostics = build_official_current_discovery_diagnostics(
        [],
        provider_name=provider_name,
        provider_surface_role="candidate_acquisition",
        provider_job_kind=provider_job_kind,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
    )
    diagnostics["selected_candidate_reason"] = "no_provider_result_set_available"
    diagnostics["first_failure_layer"] = clean_token(first_failure_layer)
    return diagnostics


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        "official_current_candidate_acquisition_allowed": True,
        "scout_disambiguation_allowed": True,
        "bridge_hint_discovery_allowed": True,
        "other_provider_job_kinds_allowed": False,
        "query_generation_changed": False,
        "query_mutation_changed": False,
        "provider_routing_changed": False,
        "provider_selection_policy_changed": False,
        "retrieval_ranking_filtering_changed": False,
        "fetch_read_authorized": False,
        "model_called": False,
        "author_executor_invoked": False,
        "citation_formatter_invoked": False,
        "citation_behavior_changed": False,
        "product_answer_behavior_changed": False,
        "pipeline_orchestrator_domain_logic_changed": False,
    }


def _redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_candidate_facts_only": True,
        "raw_provider_payloads_retained": False,
        "raw_provider_payload_retained": False,
        "raw_page_text_retained": False,
        "raw_text_retained": False,
        "raw_snippets_retained": False,
        "raw_prompt_retained": False,
        "model_response_text_retained": False,
        "api_keys_retained": False,
        "env_values_retained": False,
        "db_rows_retained": False,
        "cache_rows_retained": False,
        "private_logs_retained": False,
        "full_trace_retained": False,
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "AG96I3B_EXACT_VALIDATION_QUERY",
    "AG96I3B_LIVE_VALIDATION_PROVIDER_NAME",
    "AG96I3B_LIVE_VALIDATION_SCHEMA_VERSION",
    "FollowupProviderJobLiveValidationActionResult",
    "FollowupProviderJobLiveValidationRecord",
    "execute_live_gated_followup_provider_job_validation_action",
]
