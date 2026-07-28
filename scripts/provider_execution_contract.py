"""Versioned contract for the loopback ScryRaven provider-execution broker.

The contract is deliberately mechanical.  It carries one explicit provider
route and one operation-tagged payload, and it contains no product, phase, job,
profile, semantic-role, ranking, evidence, or answer authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping
from urllib.parse import urlparse

SCHEMA_VERSION = "2"
REQUEST_KIND = "scryraven_provider_execution_request_v2"
RESPONSE_KIND = "scryraven_provider_execution_response_v2"
MODEL_PROOF_KIND = "scryraven_model_generation_proof_v2"
SEARCH_PROOF_KIND = "scryraven_search_query_proof_v2"
BROKER_HOST = "127.0.0.1"
BROKER_DEFAULT_PORT = 8765
BROKER_RUN_PATH = "/run"
BROKER_HEALTH_PATH = "/health"
BROKER_TOKEN_HEADER = "X-ScryRaven-Broker-Session"
BROKER_TOKEN_ENV_VAR = "SCRYRAVEN_BROKER_SESSION_TOKEN"
BROKER_ENV_FILE_PATH_ENV_VAR = "SCRYRAVEN_BROKER_ENV_FILE"
BROKER_MAX_REQUESTS_ENV_VAR = "SCRYRAVEN_BROKER_MAX_REQUESTS"

SEARCH_QUERY_OPERATION = "search.query"
MODEL_GENERATE_OPERATION = "model.generate"
GPT54_MODEL_ID = "gpt-5.4-2026-03-05"
SUPPORTED_ROUTES = frozenset(
    {
        ("serper", SEARCH_QUERY_OPERATION),
        ("tavily", SEARCH_QUERY_OPERATION),
        ("openai", MODEL_GENERATE_OPERATION),
    }
)
SUPPORTED_PROVIDERS = frozenset(provider for provider, _operation in SUPPORTED_ROUTES)
SUPPORTED_OPERATIONS = frozenset(operation for _provider, operation in SUPPORTED_ROUTES)

MAX_RESULTS = 10
MAX_QUERY_CHARS = 2_000
MAX_SYSTEM_INSTRUCTION_CHARS = 32_000
MAX_INPUT_PROMPT_CHARS = 100_000
MAX_OUTPUT_TEXT_CHARS = 200_000
MAX_OUTPUT_TOKENS = 32_000
MAX_TIMEOUT_SECONDS = 600.0
MAX_RETRY_CAP = 2
MAX_PROVIDER_EXTRACTED_TEXT_CHARS = 2_000
MAX_PROVIDER_ELAPSED_MILLISECONDS_TOTAL = 2_000_000
ALLOWED_REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh"})
ALLOWED_GENERATION_STATUSES = frozenset({"completed", "incomplete"})
ALLOWED_INCOMPLETE_REASONS = frozenset({"max_output_tokens", "content_filter"})
ALLOWED_ROUTE_ALIASES = frozenset({"fast", "smart", "embed"})

COMMON_REQUEST_KEYS = frozenset(
    {
        "schema_version",
        "request_kind",
        "provider",
        "operation",
        "base_url",
        "timeout_seconds",
        "retry_cap",
        "raw_provider_payload_retained",
        "raw_request_material_retained",
        "raw_response_material_retained",
        "raw_search_response_retained",
        "correlation_id",
        "requested_route_alias",
        "resolved_route_config_digest",
    }
)
SEARCH_REQUEST_KEYS = COMMON_REQUEST_KEYS | {"query", "max_results"}
MODEL_REQUEST_KEYS = COMMON_REQUEST_KEYS | {
    "model",
    "system_instructions",
    "input_prompt",
    "reasoning_effort",
    "max_output_tokens",
    "store",
}
COMMON_RESPONSE_KEYS = frozenset(
    {
        "schema_version",
        "response_kind",
        "provider",
        "operation",
        "model",
        "reasoning_effort",
        "status",
        "failure_class",
        "physical_attempt_count",
        "provider_elapsed_milliseconds_total",
        "results",
        "output_text",
        "generation_status",
        "generation_incomplete_reason",
        "max_output_tokens_reached",
        "output_text_present",
        "usage",
        "correlation_id",
        "requested_route_alias",
        "resolved_route_config_digest",
        "raw_provider_payload_retained",
        "raw_request_material_retained",
        "raw_response_material_retained",
        "raw_search_response_retained",
    }
)
SEARCH_RESULT_KEYS = frozenset(
    {
        "title",
        "url",
        "domain",
        "snippet",
        "provider_extracted_text",
        "provider_extracted_text_sanitized",
        "provider_extracted_text_bounded",
        "provider_extracted_text_char_count",
        "provider_extracted_text_digest",
        "provider_extracted_content_type",
        "published_or_observed_date",
        "result_rank",
        "provider_call_index",
        "provider",
        "operation",
    }
)
FORBIDDEN_REQUEST_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "authorization_header",
        "command",
        "credentials",
        "env_file",
        "executable",
        "job_id",
        "module",
        "module_path",
        "phase",
        "phase_name",
        "profile",
        "provider_payload",
        "python_module",
        "secret",
        "shell",
        "shell_command",
        "token",
        "validation_profile",
    }
)
FORBIDDEN_RESPONSE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "authorization_header",
        "cache",
        "cookie",
        "credentials",
        "db",
        "db_row",
        "env",
        "env_file",
        "full_trace",
        "headers",
        "id",
        "log",
        "logs",
        "output_items",
        "prompt",
        "raw_content",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_request",
        "raw_response",
        "raw_search_response",
        "reasoning",
        "reasoning_items",
        "reasoning_summary",
        "reasoning_text",
        "response_id",
        "secret",
        "token",
    }
)
FALSE_RETENTION_FLAGS = (
    "raw_provider_payload_retained",
    "raw_request_material_retained",
    "raw_response_material_retained",
    "raw_search_response_retained",
)


class ProviderExecutionContractError(ValueError):
    """Raised when a generic broker request or response violates the contract."""

    def __init__(self, failure_class: str) -> None:
        self.failure_class = _clean_failure_class(failure_class)
        super().__init__(self.failure_class)


def build_search_request(
    *,
    provider: str,
    query: str,
    max_results: int,
    timeout_seconds: float,
    retry_cap: int,
    correlation_id: str | None = None,
    requested_route_alias: str | None = None,
    resolved_route_config_digest: str | None = None,
) -> dict[str, Any]:
    payload = _common_request(
        provider=provider,
        operation=SEARCH_QUERY_OPERATION,
        timeout_seconds=timeout_seconds,
        retry_cap=retry_cap,
        correlation_id=correlation_id,
        requested_route_alias=requested_route_alias,
        resolved_route_config_digest=resolved_route_config_digest,
    )
    payload.update({"query": query, "max_results": max_results})
    return validate_provider_execution_request(payload)


def build_model_request(
    *,
    provider: str,
    model: str,
    system_instructions: str,
    input_prompt: str,
    reasoning_effort: str | None,
    max_output_tokens: int,
    timeout_seconds: float,
    retry_cap: int,
    base_url: str | None = None,
    correlation_id: str | None = None,
    requested_route_alias: str | None = None,
    resolved_route_config_digest: str | None = None,
) -> dict[str, Any]:
    payload = _common_request(
        provider=provider,
        operation=MODEL_GENERATE_OPERATION,
        timeout_seconds=timeout_seconds,
        retry_cap=retry_cap,
        base_url=base_url,
        correlation_id=correlation_id,
        requested_route_alias=requested_route_alias,
        resolved_route_config_digest=resolved_route_config_digest,
    )
    payload.update(
        {
            "model": model,
            "system_instructions": system_instructions,
            "input_prompt": input_prompt,
            "reasoning_effort": reasoning_effort,
            "max_output_tokens": max_output_tokens,
            "store": False,
        }
    )
    return validate_provider_execution_request(payload)


def validate_provider_execution_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ProviderExecutionContractError("request_body_must_be_object")
    raw = dict(payload)
    _reject_nested_keys(raw, FORBIDDEN_REQUEST_KEYS, "forbidden_request_field")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ProviderExecutionContractError("unsupported_schema_version")
    if raw.get("request_kind") != REQUEST_KIND:
        raise ProviderExecutionContractError("unsupported_request_kind")

    provider = _required_token(raw.get("provider"), "missing_provider", 80)
    operation = _required_token(raw.get("operation"), "missing_operation", 80)
    if (provider, operation) not in SUPPORTED_ROUTES:
        if provider not in SUPPORTED_PROVIDERS:
            raise ProviderExecutionContractError("unsupported_provider")
        if operation not in SUPPORTED_OPERATIONS:
            raise ProviderExecutionContractError("unsupported_operation")
        raise ProviderExecutionContractError("unsupported_provider_operation")

    allowed_keys = (
        SEARCH_REQUEST_KEYS
        if operation == SEARCH_QUERY_OPERATION
        else MODEL_REQUEST_KEYS
    )
    unknown = sorted(set(raw) - allowed_keys)
    if unknown:
        raise ProviderExecutionContractError("unsupported_request_fields")
    for flag in FALSE_RETENTION_FLAGS:
        if raw.get(flag) is not False:
            raise ProviderExecutionContractError(f"{flag}_must_be_false")

    timeout_seconds = _bounded_float(
        raw.get("timeout_seconds"),
        "timeout_seconds_out_of_bounds",
        minimum=0.1,
        maximum=MAX_TIMEOUT_SECONDS,
    )
    retry_cap = _bounded_int(
        raw.get("retry_cap"),
        "retry_cap_out_of_bounds",
        minimum=0,
        maximum=MAX_RETRY_CAP,
    )
    base_url = _validate_base_url(raw.get("base_url"), provider=provider, operation=operation)
    correlation_id = _optional_token(raw.get("correlation_id"), 128)
    requested_route_alias = _optional_token(raw.get("requested_route_alias"), 16)
    if (
        requested_route_alias is not None
        and requested_route_alias not in ALLOWED_ROUTE_ALIASES
    ):
        raise ProviderExecutionContractError("invalid_route_alias_attestation")
    resolved_digest = _optional_digest(raw.get("resolved_route_config_digest"))

    normalized = _common_request(
        provider=provider,
        operation=operation,
        timeout_seconds=timeout_seconds,
        retry_cap=retry_cap,
        base_url=base_url,
        correlation_id=correlation_id,
        requested_route_alias=requested_route_alias,
        resolved_route_config_digest=resolved_digest,
    )
    if operation == SEARCH_QUERY_OPERATION:
        normalized.update(
            {
                "query": _required_text(raw.get("query"), "missing_query", MAX_QUERY_CHARS),
                "max_results": _bounded_int(
                    raw.get("max_results"),
                    "max_results_out_of_bounds",
                    minimum=1,
                    maximum=MAX_RESULTS,
                ),
            }
        )
        return normalized

    model = _required_token(raw.get("model"), "missing_model", 200)
    reasoning_effort = _optional_token(raw.get("reasoning_effort"), 16)
    if (
        reasoning_effort is not None
        and reasoning_effort not in ALLOWED_REASONING_EFFORTS
    ):
        raise ProviderExecutionContractError("unsupported_reasoning_effort")
    if model == GPT54_MODEL_ID and reasoning_effort is None:
        raise ProviderExecutionContractError("missing_reasoning_effort")
    if raw.get("store") is not False:
        raise ProviderExecutionContractError("store_must_be_false")
    normalized.update(
        {
            "model": model,
            "system_instructions": _bounded_text(
                raw.get("system_instructions"),
                "system_instructions_out_of_bounds",
                MAX_SYSTEM_INSTRUCTION_CHARS,
                allow_empty=True,
            ),
            "input_prompt": _required_text(
                raw.get("input_prompt"),
                "missing_input_prompt",
                MAX_INPUT_PROMPT_CHARS,
            ),
            "reasoning_effort": reasoning_effort,
            "max_output_tokens": _bounded_int(
                raw.get("max_output_tokens"),
                "max_output_tokens_out_of_bounds",
                minimum=1,
                maximum=MAX_OUTPUT_TOKENS,
            ),
            "store": False,
        }
    )
    return _without_none(normalized)


def build_success_response(
    request_payload: Mapping[str, Any],
    *,
    physical_attempt_count: int,
    provider_elapsed_milliseconds_total: int,
    results: list[Mapping[str, Any]] | None = None,
    output_text: str | None = None,
    generation_status: str | None = None,
    generation_incomplete_reason: str | None = None,
    usage_observed: bool | None = None,
    input_tokens: int | None = None,
    cached_input_tokens: int | None = None,
    output_tokens: int | None = None,
    reasoning_tokens: int | None = None,
    total_tokens: int | None = None,
) -> dict[str, Any]:
    request_value = validate_provider_execution_request(request_payload)
    operation = request_value["operation"]
    response = _base_response(
        request_value,
        status="ok",
        physical_attempt_count=physical_attempt_count,
        provider_elapsed_milliseconds_total=provider_elapsed_milliseconds_total,
    )
    if operation == SEARCH_QUERY_OPERATION:
        if any(
            value is not None
            for value in (
                output_text,
                generation_status,
                generation_incomplete_reason,
                usage_observed,
                input_tokens,
                cached_input_tokens,
                output_tokens,
                reasoning_tokens,
                total_tokens,
            )
        ):
            raise ProviderExecutionContractError("search_response_union_mismatch")
        response["results"] = [
            validate_search_result(
                item,
                provider=request_value["provider"],
                operation=operation,
            )
            for item in (results or [])
        ]
    else:
        if results is not None:
            raise ProviderExecutionContractError("model_response_union_mismatch")
        if (
            usage_observed is True
            and isinstance(input_tokens, int)
            and isinstance(cached_input_tokens, int)
            and cached_input_tokens > input_tokens
        ):
            raise ProviderExecutionContractError(
                "cached_input_tokens_exceed_input_tokens"
            )
        if (
            usage_observed is True
            and isinstance(output_tokens, int)
            and isinstance(reasoning_tokens, int)
            and reasoning_tokens > output_tokens
        ):
            raise ProviderExecutionContractError(
                "reasoning_tokens_exceed_output_tokens"
            )
        response.update(
            _normalize_generation_telemetry(
                generation_status=generation_status,
                generation_incomplete_reason=generation_incomplete_reason,
                output_text=output_text,
            )
        )
        response["usage"] = _normalize_usage(
            usage_observed=usage_observed,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            uncached_input_tokens=(
                input_tokens - cached_input_tokens
                if (
                    usage_observed is True
                    and isinstance(input_tokens, int)
                    and isinstance(cached_input_tokens, int)
                )
                else None
            ),
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            non_reasoning_output_tokens=(
                output_tokens - reasoning_tokens
                if (
                    usage_observed is True
                    and isinstance(output_tokens, int)
                    and isinstance(reasoning_tokens, int)
                )
                else None
            ),
            total_tokens=total_tokens,
        )
    return validate_provider_execution_response(response, request_payload=request_value)


def build_failure_response(
    *,
    request_payload: Mapping[str, Any] | None,
    failure_class: str,
    physical_attempt_count: int,
    provider_elapsed_milliseconds_total: int = 0,
) -> dict[str, Any]:
    safe_request: dict[str, Any] = {}
    if isinstance(request_payload, Mapping):
        safe_request = {
            key: request_payload.get(key)
            for key in (
                "provider",
                "operation",
                "model",
                "correlation_id",
                "requested_route_alias",
                "resolved_route_config_digest",
            )
            if request_payload.get(key) is not None
        }

    def safe_optional_token(key: str, maximum: int) -> str | None:
        try:
            return _optional_token(safe_request.get(key), maximum)
        except ProviderExecutionContractError:
            return None

    def safe_optional_digest() -> str | None:
        try:
            return _optional_digest(safe_request.get("resolved_route_config_digest"))
        except ProviderExecutionContractError:
            return None

    response = {
        "schema_version": SCHEMA_VERSION,
        "response_kind": RESPONSE_KIND,
        "provider": safe_optional_token("provider", 80),
        "operation": safe_optional_token("operation", 80),
        "model": safe_optional_token("model", 200),
        "status": "failed",
        "failure_class": _clean_failure_class(failure_class),
        "physical_attempt_count": _bounded_int(
            physical_attempt_count,
            "invalid_physical_attempt_count",
            minimum=0,
            maximum=MAX_RETRY_CAP + 1,
        ),
        "provider_elapsed_milliseconds_total": _bounded_int(
            provider_elapsed_milliseconds_total,
            "invalid_provider_elapsed_milliseconds_total",
            minimum=0,
            maximum=MAX_PROVIDER_ELAPSED_MILLISECONDS_TOTAL,
        ),
        "correlation_id": safe_optional_token("correlation_id", 128),
        "requested_route_alias": safe_optional_token("requested_route_alias", 16),
        "resolved_route_config_digest": safe_optional_digest(),
        **{flag: False for flag in FALSE_RETENTION_FLAGS},
    }
    return _without_none(response)


def validate_provider_execution_response(
    response: Mapping[str, Any],
    *,
    request_payload: Mapping[str, Any],
) -> dict[str, Any]:
    request_value = validate_provider_execution_request(request_payload)
    if not isinstance(response, Mapping):
        raise ProviderExecutionContractError("response_body_must_be_object")
    raw = dict(response)
    _reject_nested_keys(raw, FORBIDDEN_RESPONSE_KEYS, "forbidden_response_field")
    unknown = sorted(set(raw) - COMMON_RESPONSE_KEYS)
    if unknown:
        raise ProviderExecutionContractError("unsupported_response_fields")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ProviderExecutionContractError("response_schema_mismatch")
    if raw.get("response_kind") != RESPONSE_KIND:
        raise ProviderExecutionContractError("response_kind_mismatch")
    for flag in FALSE_RETENTION_FLAGS:
        if raw.get(flag) is not False:
            raise ProviderExecutionContractError(f"{flag}_must_be_false")
    for key in (
        "provider",
        "operation",
        "model",
        "reasoning_effort",
        "correlation_id",
        "requested_route_alias",
        "resolved_route_config_digest",
    ):
        if raw.get(key) != request_value.get(key):
            raise ProviderExecutionContractError("route_attestation_mismatch")
    attempt_count = _bounded_int(
        raw.get("physical_attempt_count"),
        "invalid_physical_attempt_count",
        minimum=0,
        maximum=request_value["retry_cap"] + 1,
    )
    elapsed_milliseconds = _bounded_int(
        raw.get("provider_elapsed_milliseconds_total"),
        "invalid_provider_elapsed_milliseconds_total",
        minimum=0,
        maximum=MAX_PROVIDER_ELAPSED_MILLISECONDS_TOTAL,
    )
    status = raw.get("status")
    if status == "failed":
        allowed_failure_keys = (
            COMMON_RESPONSE_KEYS
            - {"results", "output_text", "usage"}
        )
        if set(raw) - allowed_failure_keys:
            raise ProviderExecutionContractError("failure_response_union_mismatch")
        failure = _clean_failure_class(raw.get("failure_class"))
        return _without_none(
            {
                **_base_response(
                    request_value,
                    status="failed",
                    physical_attempt_count=attempt_count,
                    provider_elapsed_milliseconds_total=elapsed_milliseconds,
                ),
                "failure_class": failure,
            }
        )
    if status != "ok":
        raise ProviderExecutionContractError("invalid_response_status")
    if attempt_count < 1:
        raise ProviderExecutionContractError("invalid_physical_attempt_count")

    normalized = _base_response(
        request_value,
        status="ok",
        physical_attempt_count=attempt_count,
        provider_elapsed_milliseconds_total=elapsed_milliseconds,
    )
    if request_value["operation"] == SEARCH_QUERY_OPERATION:
        if any(
            raw.get(key) is not None
            for key in (
                "output_text",
                "usage",
                "generation_status",
                "generation_incomplete_reason",
                "max_output_tokens_reached",
                "output_text_present",
            )
        ):
            raise ProviderExecutionContractError("search_response_union_mismatch")
        results = raw.get("results")
        if not isinstance(results, list):
            raise ProviderExecutionContractError("search_results_must_be_list")
        normalized["results"] = [
            validate_search_result(
                item,
                provider=request_value["provider"],
                operation=request_value["operation"],
            )
            for item in results
        ]
    else:
        if raw.get("results") is not None:
            raise ProviderExecutionContractError("model_response_union_mismatch")
        normalized.update(
            _normalize_generation_telemetry(
                generation_status=raw.get("generation_status"),
                generation_incomplete_reason=raw.get(
                    "generation_incomplete_reason"
                ),
                output_text=raw.get("output_text"),
                max_output_tokens_reached=raw.get(
                    "max_output_tokens_reached"
                ),
                output_text_present=raw.get("output_text_present"),
            )
        )
        usage = raw.get("usage")
        if not isinstance(usage, Mapping):
            raise ProviderExecutionContractError("missing_or_invalid_usage")
        normalized["usage"] = _normalize_usage(**dict(usage))
    return normalized


def validate_search_result(
    value: Mapping[str, Any],
    *,
    provider: str,
    operation: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderExecutionContractError("search_result_must_be_object")
    raw = dict(value)
    _reject_nested_keys(raw, FORBIDDEN_RESPONSE_KEYS, "forbidden_response_field")
    if set(raw) - SEARCH_RESULT_KEYS:
        raise ProviderExecutionContractError("unsupported_search_result_fields")
    if raw.get("provider") != provider or raw.get("operation") != operation:
        raise ProviderExecutionContractError("search_result_route_attestation_mismatch")
    url = _required_http_url(raw.get("url"))
    domain = _required_token(raw.get("domain"), "missing_result_domain", 260)
    normalized = {
        "title": _required_text(raw.get("title"), "missing_result_title", 220),
        "url": url,
        "domain": domain,
        "snippet": _bounded_text(
            raw.get("snippet"),
            "invalid_result_snippet",
            500,
            allow_empty=True,
        ),
        "published_or_observed_date": _optional_token(
            raw.get("published_or_observed_date"),
            80,
        ),
        "result_rank": _bounded_int(
            raw.get("result_rank"),
            "invalid_result_rank",
            minimum=1,
            maximum=10**9,
        ),
        "provider_call_index": _bounded_int(
            raw.get("provider_call_index"),
            "invalid_provider_call_index",
            minimum=1,
            maximum=MAX_RETRY_CAP + 1,
        ),
        "provider": provider,
        "operation": operation,
    }
    extracted = raw.get("provider_extracted_text")
    if extracted is not None:
        extracted_text = _required_text(
            extracted,
            "invalid_provider_extracted_text",
            MAX_PROVIDER_EXTRACTED_TEXT_CHARS,
        )
        expected_digest = digest_text(extracted_text)
        if (
            raw.get("provider_extracted_text_sanitized") is not True
            or raw.get("provider_extracted_text_bounded") is not True
            or raw.get("provider_extracted_text_char_count") != len(extracted_text)
            or raw.get("provider_extracted_text_digest") != expected_digest
            or raw.get("provider_extracted_content_type") != "text/html"
        ):
            raise ProviderExecutionContractError("invalid_provider_extracted_text_posture")
        normalized.update(
            {
                "provider_extracted_text": extracted_text,
                "provider_extracted_text_sanitized": True,
                "provider_extracted_text_bounded": True,
                "provider_extracted_text_char_count": len(extracted_text),
                "provider_extracted_text_digest": expected_digest,
                "provider_extracted_content_type": "text/html",
            }
        )
    return _without_none(normalized)


def normalize_search_provider_result(
    value: Mapping[str, Any],
    *,
    provider: str,
    result_rank: int,
    provider_call_index: int,
) -> dict[str, Any]:
    """Normalize one transient provider record before raw material is discarded."""

    if not isinstance(value, Mapping):
        raise ProviderExecutionContractError("invalid_provider_result")
    title = _required_text(value.get("title"), "missing_result_title", 220)
    url = _required_http_url(value.get("url") or value.get("link"))
    domain = _optional_token(value.get("domain"), 260)
    if not domain:
        domain = (urlparse(url).hostname or "").casefold()
    if not domain:
        raise ProviderExecutionContractError("missing_result_domain")
    extracted_text: str | None = None
    if provider == "tavily" and value.get("raw_content"):
        extracted_text = _truncated_text(
            value.get("raw_content"),
            "invalid_provider_extracted_text",
            MAX_PROVIDER_EXTRACTED_TEXT_CHARS,
        )
    normalized: dict[str, Any] = {
        "title": title,
        "url": url,
        "domain": domain,
        "snippet": _truncated_text(
            value.get("snippet") or value.get("content"),
            "invalid_result_snippet",
            500,
        ),
        "published_or_observed_date": _optional_token(
            value.get("published_or_observed_date")
            or value.get("date")
            or value.get("age"),
            80,
        ),
        "result_rank": result_rank,
        "provider_call_index": provider_call_index,
        "provider": provider,
        "operation": SEARCH_QUERY_OPERATION,
    }
    if extracted_text:
        normalized.update(
            {
                "provider_extracted_text": extracted_text,
                "provider_extracted_text_sanitized": True,
                "provider_extracted_text_bounded": True,
                "provider_extracted_text_char_count": len(extracted_text),
                "provider_extracted_text_digest": digest_text(extracted_text),
                "provider_extracted_content_type": "text/html",
            }
        )
    return validate_search_result(
        normalized,
        provider=provider,
        operation=SEARCH_QUERY_OPERATION,
    )


def build_model_proof(
    response: Mapping[str, Any],
    *,
    request_payload: Mapping[str, Any],
    maximum_input_tokens: int,
    ordinary_input_price_usd_per_million: str,
    cached_input_price_usd_per_million: str,
    output_price_usd_per_million: str,
    cost_ceiling_usd: str,
    expected_json_status: str | None = None,
) -> dict[str, Any]:
    """Consume transient output text and return only a digest/length projection."""

    from decimal import Decimal

    normalized = validate_provider_execution_response(
        response,
        request_payload=request_payload,
    )
    if normalized["operation"] != MODEL_GENERATE_OPERATION:
        raise ProviderExecutionContractError("model_proof_requires_model_response")
    output_text = normalized["output_text"]
    usage = normalized["usage"]
    maximum_input = _bounded_int(
        maximum_input_tokens,
        "maximum_input_tokens_out_of_bounds",
        minimum=1,
        maximum=10**9,
    )
    if usage["usage_observed"] and usage["input_tokens"] > maximum_input:
        raise ProviderExecutionContractError("input_token_cap_exceeded")
    try:
        ordinary_input_price = Decimal(ordinary_input_price_usd_per_million)
        cached_input_price = Decimal(cached_input_price_usd_per_million)
        output_price = Decimal(output_price_usd_per_million)
        ceiling = Decimal(cost_ceiling_usd)
    except Exception as exc:
        raise ProviderExecutionContractError("invalid_caller_cost_policy") from exc
    if (
        min(ordinary_input_price, cached_input_price, output_price, ceiling) < 0
        or ceiling <= 0
    ):
        raise ProviderExecutionContractError("invalid_caller_cost_policy")
    cost: Decimal | None = None
    if usage["usage_observed"]:
        cost = (
            Decimal(usage["uncached_input_tokens"]) * ordinary_input_price
            + Decimal(usage["cached_input_tokens"]) * cached_input_price
            + Decimal(usage["output_tokens"]) * output_price
        ) / Decimal(1_000_000)
        if cost > ceiling:
            raise ProviderExecutionContractError("caller_cost_ceiling_exceeded")
    parsed_status: str | None = None
    if expected_json_status is not None:
        if normalized["generation_status"] != "completed":
            raise ProviderExecutionContractError(
                "model_output_json_status_unavailable"
            )
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ProviderExecutionContractError(
                "model_output_json_status_invalid"
            ) from exc
        if (
            not isinstance(parsed, Mapping)
            or set(parsed) != {"status"}
            or not isinstance(parsed.get("status"), str)
        ):
            raise ProviderExecutionContractError("model_output_json_status_invalid")
        parsed_status = parsed["status"]
        if parsed_status != expected_json_status:
            raise ProviderExecutionContractError("model_output_json_status_mismatch")
    proof = {
        "schema_version": SCHEMA_VERSION,
        "proof_kind": MODEL_PROOF_KIND,
        "provider": normalized["provider"],
        "operation": normalized["operation"],
        "model": normalized["model"],
        "reasoning_effort": normalized["reasoning_effort"],
        "status": "ok",
        "generation_status": normalized["generation_status"],
        "generation_incomplete_reason": normalized.get(
            "generation_incomplete_reason"
        ),
        "max_output_tokens_reached": normalized[
            "max_output_tokens_reached"
        ],
        "usage_observed": usage["usage_observed"],
        "requested_maximum_output_tokens": request_payload[
            "max_output_tokens"
        ],
        "output_text_present": normalized["output_text_present"],
        "output_digest": digest_text(output_text),
        "output_character_count": len(output_text),
        "provider_elapsed_milliseconds_total": normalized[
            "provider_elapsed_milliseconds_total"
        ],
        "physical_attempt_count": normalized["physical_attempt_count"],
        "retry_count": max(0, normalized["physical_attempt_count"] - 1),
        "cost_posture": "exact" if cost is not None else "unknown",
        "request_may_still_be_billable": cost is None,
        "caller_cost_ceiling_usd": format(ceiling, "f"),
        "correlation_id": normalized.get("correlation_id"),
        "parsed_status": parsed_status,
        **{flag: False for flag in FALSE_RETENTION_FLAGS},
        "output_text_retained": False,
    }
    if usage["usage_observed"]:
        proof.update(
            {
                key: usage[key]
                for key in (
                    "input_tokens",
                    "cached_input_tokens",
                    "uncached_input_tokens",
                    "output_tokens",
                    "reasoning_tokens",
                    "non_reasoning_output_tokens",
                    "total_tokens",
                )
            }
        )
        proof["output_token_utilization"] = format(
            Decimal(usage["output_tokens"])
            / Decimal(request_payload["max_output_tokens"]),
            "f",
        )
        proof["reasoning_token_share"] = (
            format(
                Decimal(usage["reasoning_tokens"])
                / Decimal(usage["output_tokens"]),
                "f",
            )
            if usage["output_tokens"] > 0
            else None
        )
        assert cost is not None
        proof["caller_calculated_route_priced_cost_usd"] = format(cost, "f")
    output_text = ""
    return _without_none(proof)


def _normalize_generation_telemetry(
    *,
    generation_status: Any,
    generation_incomplete_reason: Any,
    output_text: Any,
    max_output_tokens_reached: Any | None = None,
    output_text_present: Any | None = None,
) -> dict[str, Any]:
    status = _required_token(
        generation_status,
        "invalid_generation_status",
        32,
    )
    if status not in ALLOWED_GENERATION_STATUSES:
        raise ProviderExecutionContractError("invalid_generation_status")
    reason = _optional_token(generation_incomplete_reason, 32)
    if status == "completed":
        if reason is not None:
            raise ProviderExecutionContractError(
                "completed_generation_has_incomplete_reason"
            )
    elif reason not in ALLOWED_INCOMPLETE_REASONS:
        raise ProviderExecutionContractError(
            "unsupported_generation_incomplete_reason"
        )
    text = _bounded_text(
        output_text if output_text is not None else "",
        "invalid_output_text",
        MAX_OUTPUT_TEXT_CHARS,
        allow_empty=True,
    )
    present = bool(text)
    exhausted = reason == "max_output_tokens"
    if output_text_present is not None and output_text_present is not present:
        raise ProviderExecutionContractError("output_text_present_mismatch")
    if (
        max_output_tokens_reached is not None
        and max_output_tokens_reached is not exhausted
    ):
        raise ProviderExecutionContractError(
            "max_output_tokens_reached_mismatch"
        )
    if status == "completed" and not present:
        raise ProviderExecutionContractError(
            "completed_generation_requires_output_text"
        )
    return {
        "generation_status": status,
        "generation_incomplete_reason": reason,
        "max_output_tokens_reached": exhausted,
        "output_text_present": present,
        "output_text": text,
    }


def _normalize_usage(
    *,
    usage_observed: Any,
    input_tokens: Any = None,
    cached_input_tokens: Any = None,
    uncached_input_tokens: Any = None,
    output_tokens: Any = None,
    reasoning_tokens: Any = None,
    non_reasoning_output_tokens: Any = None,
    total_tokens: Any = None,
) -> dict[str, Any]:
    if not isinstance(usage_observed, bool):
        raise ProviderExecutionContractError("invalid_usage_observed")
    supplied = {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "uncached_input_tokens": uncached_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "non_reasoning_output_tokens": non_reasoning_output_tokens,
        "total_tokens": total_tokens,
    }
    if not usage_observed:
        if any(value is not None for value in supplied.values()):
            raise ProviderExecutionContractError(
                "unobserved_usage_must_not_include_counts"
            )
        return {"usage_observed": False}
    required = {
        key: _bounded_int(
            value,
            f"missing_or_invalid_{key}",
            minimum=0,
            maximum=10**9,
        )
        for key, value in supplied.items()
    }
    if required["cached_input_tokens"] > required["input_tokens"]:
        raise ProviderExecutionContractError(
            "cached_input_tokens_exceed_input_tokens"
        )
    expected_uncached = (
        required["input_tokens"] - required["cached_input_tokens"]
    )
    if required["uncached_input_tokens"] != expected_uncached:
        raise ProviderExecutionContractError("uncached_input_tokens_mismatch")
    if required["reasoning_tokens"] > required["output_tokens"]:
        raise ProviderExecutionContractError(
            "reasoning_tokens_exceed_output_tokens"
        )
    expected_non_reasoning = (
        required["output_tokens"] - required["reasoning_tokens"]
    )
    if required["non_reasoning_output_tokens"] != expected_non_reasoning:
        raise ProviderExecutionContractError(
            "non_reasoning_output_tokens_mismatch"
        )
    if (
        required["total_tokens"]
        != required["input_tokens"] + required["output_tokens"]
    ):
        raise ProviderExecutionContractError("total_tokens_mismatch")
    return {"usage_observed": True, **required}


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _common_request(
    *,
    provider: str,
    operation: str,
    timeout_seconds: float,
    retry_cap: int,
    base_url: str | None = None,
    correlation_id: str | None = None,
    requested_route_alias: str | None = None,
    resolved_route_config_digest: str | None = None,
) -> dict[str, Any]:
    return _without_none(
        {
            "schema_version": SCHEMA_VERSION,
            "request_kind": REQUEST_KIND,
            "provider": provider,
            "operation": operation,
            "base_url": base_url,
            "timeout_seconds": timeout_seconds,
            "retry_cap": retry_cap,
            "raw_provider_payload_retained": False,
            "raw_request_material_retained": False,
            "raw_response_material_retained": False,
            "raw_search_response_retained": False,
            "correlation_id": correlation_id,
            "requested_route_alias": requested_route_alias,
            "resolved_route_config_digest": resolved_route_config_digest,
        }
    )


def _base_response(
    request_payload: Mapping[str, Any],
    *,
    status: str,
    physical_attempt_count: int,
    provider_elapsed_milliseconds_total: int,
) -> dict[str, Any]:
    return _without_none(
        {
            "schema_version": SCHEMA_VERSION,
            "response_kind": RESPONSE_KIND,
            "provider": request_payload.get("provider"),
            "operation": request_payload.get("operation"),
            "model": request_payload.get("model"),
            "reasoning_effort": request_payload.get("reasoning_effort"),
            "status": status,
            "physical_attempt_count": physical_attempt_count,
            "provider_elapsed_milliseconds_total": (
                provider_elapsed_milliseconds_total
            ),
            "correlation_id": request_payload.get("correlation_id"),
            "requested_route_alias": request_payload.get("requested_route_alias"),
            "resolved_route_config_digest": request_payload.get(
                "resolved_route_config_digest"
            ),
            **{flag: False for flag in FALSE_RETENTION_FLAGS},
        }
    )


def _validate_base_url(value: Any, *, provider: str, operation: str) -> str | None:
    if value is None or value == "":
        return None
    if provider != "openai" or operation != MODEL_GENERATE_OPERATION:
        raise ProviderExecutionContractError("base_url_not_supported_for_route")
    text = _required_token(value, "invalid_base_url", 300)
    parsed = urlparse(text)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.openai.com"
        or parsed.port not in {None, 443}
        or parsed.path.rstrip("/") != "/v1"
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ProviderExecutionContractError("invalid_base_url")
    return "https://api.openai.com/v1"


def _reject_nested_keys(
    value: Any,
    forbidden: frozenset[str],
    failure_class: str,
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _normalize_key(key)
            if normalized in forbidden:
                raise ProviderExecutionContractError(failure_class)
            _reject_nested_keys(item, forbidden, failure_class)
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            _reject_nested_keys(item, forbidden, failure_class)


def _required_http_url(value: Any) -> str:
    text = _required_token(value, "missing_result_url", 700)
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProviderExecutionContractError("invalid_result_url")
    return text


def _required_text(value: Any, failure_class: str, limit: int) -> str:
    return _bounded_text(value, failure_class, limit, allow_empty=False)


def _bounded_text(
    value: Any,
    failure_class: str,
    limit: int,
    *,
    allow_empty: bool,
) -> str:
    if not isinstance(value, str):
        raise ProviderExecutionContractError(failure_class)
    if len(value) > limit or (not allow_empty and not value.strip()):
        raise ProviderExecutionContractError(failure_class)
    return value


def _truncated_text(value: Any, failure_class: str, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ProviderExecutionContractError(failure_class)
    return value[:limit]


def _required_token(value: Any, failure_class: str, limit: int) -> str:
    token = _optional_token(value, limit)
    if token is None:
        raise ProviderExecutionContractError(failure_class)
    return token


def _optional_token(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderExecutionContractError("invalid_string_field")
    token = value.strip()
    if not token or len(token) > limit or any(ord(char) < 32 for char in token):
        raise ProviderExecutionContractError("invalid_string_field")
    return token


def _optional_digest(value: Any) -> str | None:
    if value is None:
        return None
    token = _required_token(value, "invalid_route_config_digest", 64)
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        raise ProviderExecutionContractError("invalid_route_config_digest")
    return token


def _bounded_int(
    value: Any,
    failure_class: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProviderExecutionContractError(failure_class)
    if value < minimum or value > maximum:
        raise ProviderExecutionContractError(failure_class)
    return value


def _bounded_float(
    value: Any,
    failure_class: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool):
        raise ProviderExecutionContractError(failure_class)
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ProviderExecutionContractError(failure_class) from exc
    if parsed < minimum or parsed > maximum:
        raise ProviderExecutionContractError(failure_class)
    return parsed


def _clean_failure_class(value: Any) -> str:
    if not isinstance(value, str):
        return "provider_execution_failed"
    normalized = "".join(
        char if char.isalnum() or char == "_" else "_"
        for char in value.strip().casefold()
    )
    normalized = "_".join(part for part in normalized.split("_") if part)
    return normalized[:120] or "provider_execution_failed"


def _without_none(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _normalize_key(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .casefold()
        .replace("-", "_")
        .replace(" ", "_")
    )


__all__ = [
    "BROKER_DEFAULT_PORT",
    "BROKER_ENV_FILE_PATH_ENV_VAR",
    "BROKER_HEALTH_PATH",
    "BROKER_HOST",
    "BROKER_MAX_REQUESTS_ENV_VAR",
    "BROKER_RUN_PATH",
    "BROKER_TOKEN_ENV_VAR",
    "BROKER_TOKEN_HEADER",
    "FALSE_RETENTION_FLAGS",
    "GPT54_MODEL_ID",
    "MAX_PROVIDER_ELAPSED_MILLISECONDS_TOTAL",
    "MAX_RETRY_CAP",
    "MODEL_GENERATE_OPERATION",
    "MODEL_PROOF_KIND",
    "ProviderExecutionContractError",
    "REQUEST_KIND",
    "RESPONSE_KIND",
    "SCHEMA_VERSION",
    "SEARCH_PROOF_KIND",
    "SEARCH_QUERY_OPERATION",
    "SUPPORTED_OPERATIONS",
    "SUPPORTED_PROVIDERS",
    "SUPPORTED_ROUTES",
    "build_failure_response",
    "build_model_proof",
    "build_model_request",
    "build_search_request",
    "build_success_response",
    "canonical_json_bytes",
    "digest_text",
    "normalize_search_provider_result",
    "validate_provider_execution_request",
    "validate_provider_execution_response",
    "validate_search_result",
]
