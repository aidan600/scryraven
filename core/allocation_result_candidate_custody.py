"""Allocation-result admission into candidate custody.

This helper consumes already-sanitized provider-review allocation summaries
and exposes them as inputs for the existing passport, provider-result bridge,
and ControllerEvidenceLedger projections. It does not retrieve, route, rank,
classify, fit, cite, prompt, or alter final-answer behavior.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse, urlunparse

from core.controller_provider_search_allocation import (
    BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE,
    PROVIDER_SEARCH_ALLOCATION_ACTION,
    PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY,
    PROVIDER_SEARCH_ALLOCATION_OWNER,
    PROVIDER_SEARCH_ALLOCATION_RESULT_SUMMARIES_KEY,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
    PROVIDER_SEARCH_REVIEW_REQUEST,
)

ALLOCATION_RESULT_CANDIDATE_CUSTODY_SCHEMA_VERSION = (
    "allocation_result_candidate_custody_ag95q_v1"
)
ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY = (
    "allocation_result_candidate_custody"
)
ALLOCATION_RESULT_CANDIDATE_CUSTODY_COMPATIBILITY_STATUS = (
    "sanitized_observation_input_for_run_kernel_evidence_ledger_ag91j"
)

UNKNOWN = "unknown"
NOT_OBSERVABLE = "not_observable"

_MAX_LIST_ITEMS = 20
_MAX_TEXT_CHARS = 240
_LOWER_TIER_TIERS = frozenset(
    {"secondary", "trusted_community", "social_or_forum", "context", "analysis"}
)
_LOWER_TIER_CLASSES = frozenset({"secondary", "secondary_only", "context"})
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "cache",
    "credential",
    "db",
    "env",
    "full_trace",
    "key",
    "log",
    "output_packet",
    "password",
    "prompt",
    "provider" + "_payload",
    "raw_",
    "secret",
    "snippet",
    "text",
    "token",
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(
        r"(?i)\b(api[_ -]?key|secret|token|password)\b\s*[:=]\s*[^,\s;]+"
    ),
)


def build_allocation_result_candidate_custody_trace(
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build the trace envelope for provider-review allocation custody."""

    return {
        "schema_version": ALLOCATION_RESULT_CANDIDATE_CUSTODY_SCHEMA_VERSION,
        "trace_key": ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY,
        "run_kernel_compatibility_status": (
            ALLOCATION_RESULT_CANDIDATE_CUSTODY_COMPATIBILITY_STATUS
        ),
        "trace_mode": "canonical_provider_review_allocation_result_candidate_custody",
        "diagnostic_only": False,
        "sanitized": True,
        "behavior_changed": False,
        "AllocationResultCandidateCustody": (
            build_allocation_result_candidate_custody_projection(runtime_trace)
        ),
    }


def build_allocation_result_candidate_custody_projection(
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Represent eligible allocation results as existing custody inputs."""

    trace = _mapping(runtime_trace)
    execution = _allocation_execution(trace)
    blocker = _admission_blocker(trace=trace, execution=execution)
    provider_inputs: list[dict[str, Any]] = []
    candidate_inputs: list[dict[str, Any]] = []
    non_represented: list[dict[str, Any]] = []

    if blocker is None:
        for index, result in enumerate(_allocation_result_summaries(execution), start=1):
            provider_input, candidate_input, reason = _represent_result(
                result,
                index=index,
            )
            if provider_input is None or candidate_input is None:
                non_represented.append(
                    {
                        "allocation_result_id": _result_id(result, index=index),
                        "non_representation_reason": reason
                        or "insufficient_sanitized_result_metadata",
                    }
                )
                continue
            provider_inputs.append(provider_input)
            candidate_inputs.append(candidate_input)

    non_representation_reasons = sorted(
        {
            str(item.get("non_representation_reason") or UNKNOWN)
            for item in non_represented
        }
    )
    if blocker is not None:
        non_representation_reasons = [blocker]

    return {
        "schema_version": ALLOCATION_RESULT_CANDIDATE_CUSTODY_SCHEMA_VERSION,
        "run_kernel_compatibility_status": (
            ALLOCATION_RESULT_CANDIDATE_CUSTODY_COMPATIBILITY_STATUS
        ),
        "admission_owner": "ControllerEvidenceLedger",
        "allocation_owner": PROVIDER_SEARCH_ALLOCATION_OWNER,
        "allocation_trace_present": bool(trace.get(PROVIDER_SEARCH_ALLOCATION_TRACE_KEY)),
        "allocation_execution_authorized": blocker
        not in {
            "missing_provider_search_allocation_execution_trace",
            "allocation_execution_not_canonical_provider_review_authorized",
        },
        "allocation_execution_executed": execution.get("executed") is True,
        "allocation_execution_attempted": execution.get("execution_attempted") is True,
        "allocation_bounded_profile": _text(execution.get("bounded_profile")),
        "allocation_result_count": _int(execution.get("result_count")),
        "allocation_new_url_count": _int(execution.get("new_url_count")),
        "admission_used": blocker is None and bool(provider_inputs or non_represented),
        "admitted_result_count": len(provider_inputs),
        "non_represented_result_count": len(non_represented),
        "non_representation_reasons": non_representation_reasons,
        "provider_result_bridge_inputs": provider_inputs,
        "represented_candidate_inputs": candidate_inputs,
        "non_represented_results": non_represented,
        "provider_result_bridge_visible": _trace_payload_visible(
            trace,
            "provider_result_represented_candidate_bridge",
            "ProviderResultRepresentedCandidateBridge",
        ),
        "authority_candidate_passport_visible": _trace_payload_visible(
            trace,
            "authority_candidate_passport_projection",
            "AuthorityCandidatePassportProjection",
        ),
        "controller_evidence_ledger_visible": _trace_payload_visible(
            trace,
            "controller_evidence_ledger",
            "ControllerEvidenceLedger",
        ),
        "source_obligation_satisfied": False,
        "final_evidence_changed": False,
        "final_citation_changed": False,
        "raw_payload_exposed": False,
        "behavior_changed": False,
    }


def allocation_result_candidate_inputs(
    runtime_trace: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return represented candidate inputs already admitted by the helper."""

    payload = allocation_result_candidate_custody_payload(runtime_trace)
    return [
        _safe_mapping(item)
        for item in _list(payload.get("represented_candidate_inputs"))
    ]


def allocation_result_provider_result_inputs(
    runtime_trace: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return provider-result bridge inputs already admitted by the helper."""

    payload = allocation_result_candidate_custody_payload(runtime_trace)
    return [
        _safe_mapping(item)
        for item in _list(payload.get("provider_result_bridge_inputs"))
    ]


def allocation_result_candidate_custody_payload(
    runtime_trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Extract the nested custody projection from a runtime trace."""

    trace = _mapping(runtime_trace)
    packet = trace.get(ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY)
    if isinstance(packet, Mapping):
        payload = packet.get("AllocationResultCandidateCustody")
        if isinstance(payload, Mapping):
            return _safe_mapping(payload)
    return {}


def _admission_blocker(
    *,
    trace: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> str | None:
    if not execution:
        return "missing_provider_search_allocation_execution_trace"
    if not _execution_authorized(execution):
        return "allocation_execution_not_canonical_provider_review_authorized"
    if execution.get("execution_attempted") is not True:
        if execution.get("executed") is not True:
            return _text(execution.get("unexecutable_reason")) or (
                "allocation_execution_not_attempted"
            )
        return "allocation_execution_not_attempted"
    if execution.get("executed") is not True:
        return _text(execution.get("unexecutable_reason")) or (
            "allocation_execution_not_executed"
        )
    if _int(execution.get("result_count")) <= 0:
        return "allocation_execution_zero_result_count"
    if not _allocation_result_summaries(execution):
        return "missing_sanitized_allocation_result_summaries"
    return None


def _execution_authorized(execution: Mapping[str, Any]) -> bool:
    return (
        execution.get("allocation_owner") == PROVIDER_SEARCH_ALLOCATION_OWNER
        and execution.get("authorized_decision") == PROVIDER_SEARCH_REVIEW_REQUEST
        and execution.get("authorized_executor_action")
        == PROVIDER_SEARCH_ALLOCATION_ACTION
        and execution.get("bounded_profile")
        == BOUNDED_EXISTING_SOURCE_CLASS_RECOVERY_PROFILE
    )


def _allocation_execution(trace: Mapping[str, Any]) -> dict[str, Any]:
    packet = trace.get(PROVIDER_SEARCH_ALLOCATION_TRACE_KEY)
    if not isinstance(packet, Mapping):
        return {}
    payload = packet.get(PROVIDER_SEARCH_ALLOCATION_EXECUTION_TRACE_KEY)
    if not isinstance(payload, Mapping):
        payload = packet.get("ProviderSearchAllocationExecution")
    return _safe_mapping(payload) if isinstance(payload, Mapping) else {}


def _allocation_result_summaries(
    execution: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        _safe_mapping(item)
        for item in _list(execution.get(PROVIDER_SEARCH_ALLOCATION_RESULT_SUMMARIES_KEY))
    ][:_MAX_LIST_ITEMS]


def _represent_result(
    result: Mapping[str, Any],
    *,
    index: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    source_url = _text(
        result.get("source_url") or result.get("url") or result.get("accepted_url")
    )
    title = _text(result.get("title"), limit=180)
    if not source_url and not title:
        return None, None, "insufficient_sanitized_result_metadata"

    normalized_url = _normalize_url(source_url)
    source_tier = _token(result.get("source_tier")) or UNKNOWN
    source_class = _token(result.get("source_class")) or UNKNOWN
    lower_tier = (
        source_tier in _LOWER_TIER_TIERS
        or source_class in _LOWER_TIER_CLASSES
    )
    reason = (
        "lower_tier_or_secondary_not_satisfying_official_current_obligation"
        if lower_tier
        else "allocation_result_requires_existing_classifier_fit_disposition"
    )
    candidate_id = _candidate_id(
        result,
        normalized_url=normalized_url,
        title=title,
        index=index,
    )
    provider_result_id = _result_id(result, index=index)
    common = {
        "provider_result_id": provider_result_id,
        "candidate_id": candidate_id,
        "provider_name": _text(result.get("provider_name"), limit=80) or UNKNOWN,
        "provider_role": _text(result.get("provider_role"), limit=80)
        or "source_class_recovery",
        "retrieval_pass_id": _text(result.get("retrieval_pass_id"), limit=80)
        or "canonical_provider_review_allocation_result",
        "query_preview": _text(result.get("query_preview"), limit=140) or UNKNOWN,
        "provider_rank_or_position": _int(result.get("provider_rank_or_position")),
        "source_url": source_url,
        "url": source_url,
        "accepted_url": source_url,
        "normalized_domain": _text(result.get("normalized_domain"), limit=120)
        or _normalized_domain(source_url),
        "title": title,
        "source_tier": source_tier,
        "source_class": source_class,
        "classification_reason": _text(result.get("classification_reason")),
        "currentness_signal": _text(result.get("currentness_signal")) or UNKNOWN,
        "temporal_anchor_required": _text(result.get("temporal_anchor_required"))
        or UNKNOWN,
        "temporal_anchor_observed": _text(result.get("temporal_anchor_observed"))
        or UNKNOWN,
        "provider_returned": True,
        "allocation_result_admitted": True,
        "non_representation_reason": reason,
        "sanitized": True,
        "raw_payload_exposed": False,
    }
    provider_input = {key: value for key, value in common.items() if value != ""}
    candidate_input = {
        **provider_input,
        "readability_status": "not_evaluated",
        "readable_text_available": False,
        "fit_state": "rejected_with_reason",
        "satisfies_authority": False,
        "rejection_reason": reason,
        "rejection_owner": "allocation_result_candidate_custody",
        "final_evidence_changed": False,
        "final_citation_changed": False,
    }
    return provider_input, candidate_input, None


def _safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key or "")
        key_lower = key_text.casefold()
        if any(marker in key_lower for marker in _SENSITIVE_KEY_MARKERS):
            continue
        safe = _safe_value(item)
        if safe is not None:
            out[key_text] = safe
    return out


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0.0, value)
    if isinstance(value, Mapping):
        return _safe_mapping(value)
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item) for item in list(value)[:_MAX_LIST_ITEMS]]
    text = _text(value)
    if any(pattern.search(text) for pattern in _SECRET_VALUE_PATTERNS):
        return None
    return text


def _trace_payload_visible(
    trace: Mapping[str, Any],
    trace_key: str,
    payload_key: str,
) -> bool:
    packet = trace.get(trace_key)
    return isinstance(packet, Mapping) and isinstance(packet.get(payload_key), Mapping)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple, set)) else []


def _text(value: Any, *, limit: int = _MAX_TEXT_CHARS) -> str:
    text = " ".join(str(value or "").strip().split())
    return text[:limit]


def _token(value: Any) -> str:
    return _text(value, limit=80).casefold().replace(" ", "_").replace("-", "_")


def _int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _normalize_url(value: Any) -> str:
    text = _text(value, limit=300)
    if not text:
        return ""
    parsed = urlparse(text)
    if not parsed.netloc:
        return text.casefold()
    return urlunparse(
        (
            parsed.scheme.casefold() or "https",
            parsed.netloc.casefold(),
            parsed.path.rstrip("/"),
            "",
            parsed.query,
            "",
        )
    )


def _normalized_domain(value: Any) -> str:
    parsed = urlparse(_text(value, limit=300))
    return parsed.netloc.casefold()


def _candidate_id(
    result: Mapping[str, Any],
    *,
    normalized_url: str,
    title: str,
    index: int,
) -> str:
    explicit = _text(result.get("candidate_id"), limit=160)
    if explicit:
        return explicit
    basis = normalized_url or title or f"allocation-result:{index}"
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"allocation-result-candidate:{digest}"


def _result_id(result: Mapping[str, Any], *, index: int) -> str:
    explicit = _text(result.get("provider_result_id"), limit=160)
    if explicit:
        return explicit
    basis = (
        _normalize_url(result.get("source_url") or result.get("url"))
        or _text(result.get("title"), limit=180)
        or f"allocation-result:{index}"
    )
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"allocation-result:{digest}"


__all__ = [
    "ALLOCATION_RESULT_CANDIDATE_CUSTODY_SCHEMA_VERSION",
    "ALLOCATION_RESULT_CANDIDATE_CUSTODY_COMPATIBILITY_STATUS",
    "ALLOCATION_RESULT_CANDIDATE_CUSTODY_TRACE_KEY",
    "allocation_result_candidate_custody_payload",
    "allocation_result_candidate_inputs",
    "allocation_result_provider_result_inputs",
    "build_allocation_result_candidate_custody_projection",
    "build_allocation_result_candidate_custody_trace",
]
