from __future__ import annotations

import inspect
from collections import Counter
from typing import Any, Callable

PROVIDER_DIAGNOSTICS_SCHEMA_VERSION = "provider_diagnostics_v1"
QUERY_PREVIEW_MAX_CHARS = 200
_MAX_RESULT_SUMMARIES = 20
_MAX_SUMMARY_TEXT_CHARS = 240
_SENSITIVE_SUMMARY_KEY_MARKERS = (
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
    "provider_payload",
    "raw_",
    "secret",
    "snippet",
    "text",
    "token",
)


def _bounded_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _query_preview(query: Any) -> str:
    return str(query or "")[:QUERY_PREVIEW_MAX_CHARS]


def _clean_summary_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())[:_MAX_SUMMARY_TEXT_CHARS]


def _safe_provider_result_summary(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    summary: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key or "")
        key_lower = key_text.casefold()
        if any(marker in key_lower for marker in _SENSITIVE_SUMMARY_KEY_MARKERS):
            continue
        if item is None or isinstance(item, (bool, int, float)):
            summary[key_text] = item
        else:
            summary[key_text] = _clean_summary_text(item)
    return summary


def build_provider_attempt_diagnostic(
    *,
    provider: str,
    provider_role: str,
    cost_phase: str,
    query: Any,
    iteration: int | None = None,
    query_count: int = 1,
    depth: str | None = None,
    output_type: str | None = None,
    max_results: int | None = None,
    answer_endpoint_used: bool = False,
    raw_content_requested: bool = False,
    success: bool = True,
    failure_type: str | None = None,
    result_count: int = 0,
    image_count: int = 0,
    new_url_count: int = 0,
    accepted_url_count: int = 0,
    logical_attempt_count: int = 1,
    raw_url_count: int | None = None,
    raw_unique_url_count: int | None = None,
    raw_url_overlap_count: int | None = None,
    raw_domain_count: int | None = None,
    raw_domain_overlap_count: int | None = None,
    accepted_url_overlap_count: int | None = None,
    accepted_domain_count: int | None = None,
    new_domain_count: int | None = None,
    new_source_count: int | None = None,
    query_similarity_max: float | None = None,
    query_similarity_basis: str | None = None,
    provider_overlap_diagnostics_available: bool | None = None,
    provider_result_summaries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one call-site-level provider diagnostic record.

    This is shadow telemetry only. It intentionally does not estimate money,
    inspect hidden retries, or affect provider execution.
    """
    attempt: dict[str, Any] = {
        "schema_version": PROVIDER_DIAGNOSTICS_SCHEMA_VERSION,
        "provider": str(provider or "unknown"),
        "provider_role": str(provider_role or "unknown"),
        "cost_phase": str(cost_phase or "retrieval"),
        "query_count": _bounded_int(query_count) or 0,
        "query_preview": _query_preview(query),
        "depth": str(depth) if depth is not None else None,
        "output_type": str(output_type) if output_type is not None else None,
        "max_results": _bounded_int(max_results),
        "answer_endpoint_used": bool(answer_endpoint_used),
        "raw_content_requested": bool(raw_content_requested),
        "success": bool(success),
        "failure_type": None if success else str(failure_type or "provider_error")[:120],
        "result_count": _bounded_int(result_count) or 0,
        "image_count": _bounded_int(image_count) or 0,
        "new_url_count": _bounded_int(new_url_count) or 0,
        "accepted_url_count": _bounded_int(accepted_url_count) or 0,
        "logical_attempt_count": _bounded_int(logical_attempt_count) or 1,
    }
    if iteration is not None:
        attempt["iteration"] = _bounded_int(iteration)
    optional_counts = {
        "raw_url_count": raw_url_count,
        "raw_unique_url_count": raw_unique_url_count,
        "raw_url_overlap_count": raw_url_overlap_count,
        "raw_domain_count": raw_domain_count,
        "raw_domain_overlap_count": raw_domain_overlap_count,
        "accepted_url_overlap_count": accepted_url_overlap_count,
        "accepted_domain_count": accepted_domain_count,
        "new_domain_count": new_domain_count,
        "new_source_count": new_source_count,
    }
    for key, value in optional_counts.items():
        bounded = _bounded_int(value)
        if bounded is not None:
            attempt[key] = bounded
    if query_similarity_max is not None:
        try:
            attempt["query_similarity_max"] = max(0.0, min(1.0, float(query_similarity_max)))
        except (TypeError, ValueError):
            pass
    if query_similarity_basis:
        attempt["query_similarity_basis"] = str(query_similarity_basis)[:120]
    if provider_overlap_diagnostics_available is not None:
        attempt["provider_overlap_diagnostics_available"] = bool(
            provider_overlap_diagnostics_available
        )
    summaries = [
        summary
        for item in (provider_result_summaries or [])[:_MAX_RESULT_SUMMARIES]
        if (summary := _safe_provider_result_summary(item)) is not None
    ]
    if summaries:
        attempt["provider_result_summaries"] = summaries
        attempt["provider_result_summary_count"] = len(summaries)
    return attempt


def summarize_provider_diagnostics(attempts: list[dict[str, Any]] | None) -> dict[str, Any]:
    successful_by_provider: Counter[str] = Counter()
    failed_by_provider: Counter[str] = Counter()
    attempts_by_role: Counter[str] = Counter()

    for attempt in attempts or []:
        if not isinstance(attempt, dict):
            continue
        provider = str(attempt.get("provider") or "unknown")
        role = str(attempt.get("provider_role") or "unknown")
        logical_attempt_count = _bounded_int(attempt.get("logical_attempt_count")) or 1
        attempts_by_role[role] += logical_attempt_count
        if attempt.get("success") is False:
            failed_by_provider[provider] += logical_attempt_count
        else:
            successful_by_provider[provider] += logical_attempt_count

    return {
        "provider_successful_attempts_by_provider": dict(sorted(successful_by_provider.items())),
        "provider_failed_attempts_by_provider": dict(sorted(failed_by_provider.items())),
        "provider_attempts_by_role": dict(sorted(attempts_by_role.items())),
        "provider_shadow_cost_estimate_available": False,
        "provider_estimated_cost_usd": None,
    }


def provider_diagnostics_payload(attempts: list[dict[str, Any]] | None) -> dict[str, Any]:
    clean_attempts = [dict(attempt) for attempt in attempts or [] if isinstance(attempt, dict)]
    return {
        "provider_diagnostics": clean_attempts,
        **summarize_provider_diagnostics(clean_attempts),
    }


def supported_diagnostic_kwargs(callable_obj: Callable[..., Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return only diagnostic kwargs accepted by a possibly injected callable."""
    try:
        signature = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return dict(kwargs)
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
        return dict(kwargs)
    return {key: value for key, value in kwargs.items() if key in signature.parameters}
