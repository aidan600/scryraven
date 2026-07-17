"""Mechanical, one-shot provider adapters for typed acquisition requests."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

import requests

from core.acquisition_contracts import (
    AcquisitionArtifact,
    AcquisitionArtifactKind,
    AcquisitionContractError,
    AcquisitionExecutionResult,
    AcquisitionExecutionStatus,
    AcquisitionPageArtifact,
    AcquisitionRequest,
    compact_failure_detail,
    normalized_host,
    retained_text_digest,
    url_is_within_request_scope,
    validate_acquisition_request,
)
from core.routing import AcquisitionCapability

LINKUP_FETCH_URL = "https://api.linkup.so/v1/fetch"
LINKUP_SEARCH_URL = "https://api.linkup.so/v1/search"
TAVILY_API_ROOT = "https://api.tavily.com"
ACQUISITION_TRANSPORT_TIMEOUT_SECONDS = 30

Transport = Callable[[dict[str, Any]], Mapping[str, Any]]

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "admitted_source",
        "answer",
        "answer_material",
        "author",
        "author_input",
        "citation",
        "citation_eligible",
        "citations",
        "component_coverage",
        "evidence_admitted",
        "evidence_authority",
        "fap",
        "final_answer_packet",
        "semantic_observation",
        "source_obligation_satisfied",
        "sufficiency_decided",
    }
)
_FORBIDDEN_RAW_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "cookies",
        "headers",
        "raw_html",
        "rawhtml",
        "raw_provider_payload",
        "secret",
        "token",
    }
)


@dataclass(frozen=True, slots=True)
class AcquisitionTransports:
    """Dependency-injected provider transports; adapters never select among them."""

    linkup_fetch: Transport | None = None
    tavily_extract: Transport | None = None
    tavily_map: Transport | None = None
    tavily_crawl: Transport | None = None
    linkup_deep_search: Transport | None = None


def dispatch_acquisition(
    request: AcquisitionRequest,
    *,
    transports: AcquisitionTransports | None = None,
    before_transport: Callable[[], None] | None = None,
) -> AcquisitionExecutionResult:
    """Dispatch exactly one completed route decision or return a typed block."""

    try:
        validate_acquisition_request(request)
    except AcquisitionContractError as exc:
        return _blocked_result(request, code=exc.code, detail=str(exc))

    transport = _transport_for_request(request, transports=transports)
    if transport is None:
        return _blocked_result(
            request,
            code="selected_adapter_transport_unavailable",
            detail="the selected provider adapter has no available transport",
        )
    if before_transport is not None:
        before_transport()
    try:
        response = transport(_request_payload(request))
    except Exception as exc:  # noqa: BLE001 - provider failure is typed and sanitized.
        return _failure_result(
            request,
            code="selected_provider_transport_failed",
            detail=compact_failure_detail(type(exc).__name__),
            attempted=1,
        )
    try:
        artifacts = _normalize_response(request, response)
    except AcquisitionContractError as exc:
        return _failure_result(
            request,
            code=exc.code,
            detail=str(exc),
            attempted=1,
            completed=1,
        )
    return AcquisitionExecutionResult(
        request=request,
        status=AcquisitionExecutionStatus.SUCCEEDED,
        artifacts=artifacts,
        provider_calls_attempted=1,
        provider_calls_completed=1,
        transport_posture="one_selected_adapter_completed",
    )


def _transport_for_request(
    request: AcquisitionRequest,
    *,
    transports: AcquisitionTransports | None,
) -> Transport | None:
    provider = request.provider
    operation = request.operation
    configured = transports or AcquisitionTransports(
        linkup_fetch=_linkup_fetch_transport,
        tavily_extract=_tavily_extract_transport,
        tavily_map=_tavily_map_transport,
        tavily_crawl=_tavily_crawl_transport,
        linkup_deep_search=_linkup_deep_transport,
    )
    if (provider, operation) == ("linkup", "fetch"):
        return configured.linkup_fetch
    if (provider, operation) == ("tavily", "extract"):
        return configured.tavily_extract
    if (provider, operation) == ("tavily", "map"):
        return configured.tavily_map
    if (provider, operation) == ("tavily", "crawl"):
        return configured.tavily_crawl
    if (
        provider == "linkup"
        and operation == "search"
        and request.route_decision.variant == "deep"
        and request.route_decision.output_type == "searchResults"
    ):
        return configured.linkup_deep_search
    return None


def _request_payload(request: AcquisitionRequest) -> dict[str, Any]:
    capability = request.capability
    if capability is AcquisitionCapability.READ:
        if request.provider == "linkup":
            return {
                "url": request.selected_urls[0],
                "extractImages": False,
                "includeRawHtml": False,
                "renderJs": request.render_javascript,
            }
        return _tavily_extract_payload(request, focused=False)
    if capability is AcquisitionCapability.FOCUSED_EXTRACT:
        return _tavily_extract_payload(request, focused=True)
    if capability is AcquisitionCapability.MAP_SITE:
        return _tavily_site_payload(request, operation="map")
    if capability is AcquisitionCapability.CRAWL_SITE:
        return _tavily_site_payload(request, operation="crawl")
    if capability is AcquisitionCapability.DISCOVER:
        payload: dict[str, Any] = {
            "q": request.queries[0],
            "depth": "deep",
            "outputType": "searchResults",
            "maxResults": request.max_results,
            "includeImages": False,
        }
        if request.include_domains:
            payload["includeDomains"] = list(request.include_domains)
        if request.exclude_domains:
            payload["excludeDomains"] = list(request.exclude_domains)
        return payload
    raise AcquisitionContractError(
        "unsupported_acquisition_capability",
        f"unsupported acquisition capability: {capability.value}",
    )


def _tavily_extract_payload(
    request: AcquisitionRequest,
    *,
    focused: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "urls": (
            request.selected_urls[0]
            if len(request.selected_urls) == 1
            else list(request.selected_urls)
        ),
        "extract_depth": "basic",
        "include_images": False,
        "include_favicon": False,
        "format": "markdown",
        "include_usage": False,
    }
    if focused:
        payload["query"] = request.focus_text
        payload["chunks_per_source"] = 5
    return payload


def _tavily_site_payload(
    request: AcquisitionRequest,
    *,
    operation: str,
) -> dict[str, Any]:
    host = normalized_host(request.root_url or "")
    payload: dict[str, Any] = {
        "url": request.root_url,
        "max_depth": request.max_depth or 1,
        "max_breadth": max(1, min(request.max_pages or request.max_results, 100)),
        "limit": request.max_pages if operation == "crawl" else request.max_results,
        "select_domains": [f"^{re.escape(host)}$"],
        "allow_external": False,
        "include_usage": False,
    }
    if request.include_path_prefix:
        payload["select_paths"] = [f"^{re.escape(request.include_path_prefix)}.*"]
    if request.exclude_path_prefixes:
        payload["exclude_paths"] = [
            f"^{re.escape(prefix)}.*" for prefix in request.exclude_path_prefixes
        ]
    if operation == "crawl":
        payload.update(
            {
                "include_images": False,
                "include_favicon": False,
                "extract_depth": "basic",
                "format": "markdown",
            }
        )
    return payload


def _normalize_response(
    request: AcquisitionRequest,
    response: Mapping[str, Any],
) -> tuple[AcquisitionArtifact, ...]:
    if not isinstance(response, Mapping) or not response:
        raise AcquisitionContractError(
            "provider_response_missing",
            "selected provider returned no response mapping",
        )
    _reject_closed_fields(response)
    if request.capability is AcquisitionCapability.READ:
        return (_normalize_read(request, response),)
    if request.capability is AcquisitionCapability.FOCUSED_EXTRACT:
        return _normalize_focused_extract(request, response)
    if request.capability is AcquisitionCapability.MAP_SITE:
        return (_normalize_map(request, response),)
    if request.capability is AcquisitionCapability.CRAWL_SITE:
        return (_normalize_crawl(request, response),)
    if request.capability is AcquisitionCapability.DISCOVER:
        return _normalize_deep_discovery(request, response)
    raise AcquisitionContractError(
        "unsupported_acquisition_response",
        "selected provider returned an unsupported acquisition response",
    )


def _normalize_read(
    request: AcquisitionRequest,
    response: Mapping[str, Any],
) -> AcquisitionArtifact:
    selected_url = request.selected_urls[0]
    if request.provider == "tavily":
        results = _mapping_list(response.get("results"))
        failed_results = _mapping_list(response.get("failed_results"))
        if failed_results and not results:
            raise AcquisitionContractError(
                "read_provider_reported_failure",
                "selected URL read failed",
            )
        if len(results) != 1:
            raise AcquisitionContractError(
                "read_result_cardinality_invalid",
                "READ requires exactly one normalized result",
            )
        source = results[0]
        text = _scalar_text(source.get("raw_content"))
    else:
        source = dict(response)
        text = _scalar_text(source.get("markdown"))
    echoed_requested = _url(source.get("requested_url"))
    attempted = _url(source.get("attempted_url")) or selected_url
    if echoed_requested and _normalized_url(echoed_requested) != _normalized_url(selected_url):
        raise AcquisitionContractError(
            "read_requested_url_mismatch",
            "provider read material is not bound to the selected URL",
        )
    if _normalized_url(attempted) != _normalized_url(selected_url):
        raise AcquisitionContractError(
            "read_attempted_url_mismatch",
            "provider attempted URL is not the selected URL",
        )
    if not text:
        raise AcquisitionContractError(
            "read_material_empty_or_unreadable",
            "selected URL read returned no readable material",
        )
    http_status = _reported_http_status(source)
    if http_status is not None and not 200 <= http_status < 400:
        raise AcquisitionContractError(
            "read_http_status_unreadable",
            "selected URL read returned an unreadable HTTP status",
        )
    retained, posture = _bounded_text(text, request.max_retained_characters)
    provider_reported_url = _url(source.get("url"))
    final_url = _url(source.get("final_url"))
    resolved_url = _url(source.get("resolved_url"))
    canonical_url = _url(source.get("canonical_url"))
    return _artifact(
        request,
        kind=AcquisitionArtifactKind.SELECTED_URL_READ,
        status="readable",
        observed_at=_observed_at(source),
        requested_url=selected_url,
        attempted_url=attempted,
        provider_reported_url=provider_reported_url,
        resolved_url=resolved_url,
        final_url=final_url,
        canonical_url=canonical_url,
        content_type=_scalar_text(source.get("content_type")) or "text/markdown",
        http_status=http_status,
        title=_scalar_text(source.get("title") or source.get("content_title")),
        retained_text=retained,
        retained_character_count=len(retained),
        retained_digest=retained_text_digest(retained),
        truncation_posture=posture,
    )


def _normalize_focused_extract(
    request: AcquisitionRequest,
    response: Mapping[str, Any],
) -> tuple[AcquisitionArtifact, ...]:
    results = _mapping_list(response.get("results"))
    if not results:
        raise AcquisitionContractError(
            "focused_extract_material_missing",
            "FOCUSED_EXTRACT returned no selected-URL material",
        )
    selected = {_normalized_url(url): url for url in request.selected_urls}
    artifacts: list[AcquisitionArtifact] = []
    for source in results:
        provider_reported_url = _url(source.get("url"))
        reported_attempted = _url(source.get("attempted_url"))
        binding_url = reported_attempted or provider_reported_url
        if not binding_url or _normalized_url(binding_url) not in selected:
            raise AcquisitionContractError(
                "focused_extract_url_mismatch",
                "FOCUSED_EXTRACT returned material for an unselected URL",
            )
        text = _scalar_text(source.get("raw_content"))
        if not text:
            raise AcquisitionContractError(
                "focused_extract_material_unreadable",
                "FOCUSED_EXTRACT returned unreadable material",
            )
        retained, posture = _bounded_text(text, request.max_retained_characters)
        selected_url = selected[_normalized_url(binding_url)]
        artifacts.append(
            _artifact(
                request,
                kind=AcquisitionArtifactKind.FOCUSED_SELECTED_URL_EXTRACTION,
                status="readable",
                observed_at=_observed_at(source),
                requested_url=selected_url,
                attempted_url=selected_url,
                provider_reported_url=provider_reported_url,
                resolved_url=_url(source.get("resolved_url")),
                final_url=_url(source.get("final_url")),
                canonical_url=_url(source.get("canonical_url")),
                content_type=_scalar_text(source.get("content_type")) or "text/markdown",
                title=_scalar_text(source.get("title")),
                retained_text=retained,
                retained_character_count=len(retained),
                retained_digest=retained_text_digest(retained),
                truncation_posture=posture,
            )
        )
    return tuple(artifacts)


def _normalize_map(
    request: AcquisitionRequest,
    response: Mapping[str, Any],
) -> AcquisitionArtifact:
    raw_results = response.get("results")
    if not isinstance(raw_results, Sequence) or isinstance(raw_results, str | bytes):
        raise AcquisitionContractError(
            "map_results_invalid",
            "MAP_SITE requires a URL result list",
        )
    urls: list[str] = []
    seen: set[str] = set()
    for raw in raw_results:
        url = _url(raw)
        if not url or not url_is_within_request_scope(url, request):
            raise AcquisitionContractError(
                "map_result_out_of_scope",
                "MAP_SITE returned an invalid or cross-domain URL",
            )
        normalized = _normalized_url(url)
        if normalized in seen:
            continue
        seen.add(normalized)
        urls.append(url)
    if not urls:
        raise AcquisitionContractError(
            "map_results_empty",
            "MAP_SITE returned no in-scope URLs",
        )
    truncated = len(urls) > request.max_results
    retained = tuple(urls[: request.max_results])
    return _artifact(
        request,
        kind=AcquisitionArtifactKind.SITE_URL_TOPOLOGY,
        status="mapped",
        observed_at=_observed_at(response),
        root_url=request.root_url,
        requested_url=request.root_url,
        attempted_url=request.root_url,
        urls=retained,
        retained_character_count=sum(len(url) for url in retained),
        retained_digest=retained_text_digest("\n".join(retained)),
        truncation_posture=(
            "provider_excess_urls_truncated_to_authorized_limit"
            if truncated
            else "not_truncated"
        ),
    )


def _normalize_crawl(
    request: AcquisitionRequest,
    response: Mapping[str, Any],
) -> AcquisitionArtifact:
    results = _mapping_list(response.get("results"))
    if not results:
        raise AcquisitionContractError(
            "crawl_results_empty",
            "CRAWL_SITE returned no pages",
        )
    for source in results:
        url = _url(source.get("url"))
        if not url or not url_is_within_request_scope(url, request):
            raise AcquisitionContractError(
                "crawl_result_out_of_scope",
                "CRAWL_SITE returned an invalid or out-of-scope page",
            )
        for lineage_key in (
            "attempted_url",
            "resolved_url",
            "final_url",
            "canonical_url",
            "parent_url",
        ):
            lineage_url = _url(source.get(lineage_key))
            if lineage_url and not url_is_within_request_scope(lineage_url, request):
                raise AcquisitionContractError(
                    "crawl_lineage_out_of_scope",
                    "CRAWL_SITE returned out-of-scope page lineage",
                )
    page_excess = len(results) > request.max_pages
    aggregate_remaining = request.max_aggregate_retained_characters
    pages: list[AcquisitionPageArtifact] = []
    aggregate_truncated = False
    for source in results[: request.max_pages]:
        url = _url(source.get("url"))
        text = _scalar_text(source.get("raw_content"))
        if not url or not text:
            raise AcquisitionContractError(
                "crawl_page_unreadable",
                "CRAWL_SITE returned an unreadable page",
            )
        http_status = _reported_http_status(source)
        if http_status is not None and not 200 <= http_status < 400:
            raise AcquisitionContractError(
                "crawl_page_unreadable",
                "CRAWL_SITE returned an unreadable page status",
            )
        page_limit = min(request.max_retained_characters, aggregate_remaining)
        retained, posture = _bounded_text(text, max(0, page_limit))
        if len(text) > len(retained):
            aggregate_truncated = True
        if not retained:
            aggregate_truncated = True
            break
        aggregate_remaining -= len(retained)
        pages.append(
            AcquisitionPageArtifact(
                status="readable",
                observed_at=_observed_at(source),
                requested_url=None,
                attempted_url=_url(source.get("attempted_url")),
                provider_reported_url=url,
                resolved_url=_url(source.get("resolved_url")),
                final_url=_url(source.get("final_url")),
                canonical_url=_url(source.get("canonical_url")),
                parent_url=_url(source.get("parent_url")),
                content_type=_scalar_text(source.get("content_type")) or "text/markdown",
                http_status=http_status,
                title=_scalar_text(source.get("title")),
                retained_text=retained,
                retained_character_count=len(retained),
                retained_digest=retained_text_digest(retained),
                truncation_posture=posture,
            )
        )
    if not pages:
        raise AcquisitionContractError(
            "crawl_retained_material_empty",
            "CRAWL_SITE retained no bounded page material",
        )
    postures: list[str] = []
    if page_excess:
        postures.append("provider_excess_pages_truncated_to_authorized_limit")
    if aggregate_truncated:
        postures.append("provider_excess_content_truncated_to_authorized_budget")
    return _artifact(
        request,
        kind=AcquisitionArtifactKind.BOUNDED_PAGE_COLLECTION,
        status="crawled",
        observed_at=_observed_at(response),
        root_url=request.root_url,
        requested_url=request.root_url,
        attempted_url=request.root_url,
        pages=tuple(pages),
        retained_character_count=sum(page.retained_character_count for page in pages),
        retained_digest=retained_text_digest(
            "\n".join(page.retained_digest or "" for page in pages)
        ),
        truncation_posture=";".join(postures) if postures else "not_truncated",
    )


def _normalize_deep_discovery(
    request: AcquisitionRequest,
    response: Mapping[str, Any],
) -> tuple[AcquisitionArtifact, ...]:
    if response.get("answer") or response.get("structured"):
        raise AcquisitionContractError(
            "provider_synthesis_response_rejected",
            "general Linkup Deep accepts searchResults only",
        )
    results = _mapping_list(response.get("results"))
    if not results:
        raise AcquisitionContractError(
            "general_deep_results_empty",
            "general Linkup Deep returned no search results",
        )
    artifacts: list[AcquisitionArtifact] = []
    for source in results[: request.max_results]:
        url = _url(source.get("url"))
        if not url:
            raise AcquisitionContractError(
                "general_deep_result_url_invalid",
                "general Linkup Deep returned a result without a URL",
            )
        text = _scalar_text(source.get("content")) or ""
        retained, posture = _bounded_text(text, request.max_retained_characters)
        artifacts.append(
            _artifact(
                request,
                kind=AcquisitionArtifactKind.DISCOVERY_CANDIDATE,
                status="candidate_returned",
                observed_at=_observed_at(source),
                requested_url=None,
                provider_reported_url=url,
                final_url=_url(source.get("final_url")),
                canonical_url=_url(source.get("canonical_url")),
                title=_scalar_text(source.get("name") or source.get("title")),
                retained_text=retained or None,
                retained_character_count=len(retained),
                retained_digest=retained_text_digest(retained) if retained else None,
                truncation_posture=posture,
            )
        )
    return tuple(artifacts)


def _artifact(
    request: AcquisitionRequest,
    *,
    kind: AcquisitionArtifactKind,
    status: str,
    observed_at: str,
    **kwargs: Any,
) -> AcquisitionArtifact:
    decision = request.route_decision
    return AcquisitionArtifact(
        kind=kind,
        provider=decision.selected_provider or "",
        operation=decision.operation or "",
        provider_variant=decision.variant or "",
        output_type=decision.output_type or "",
        acquisition_job_id=request.acquisition_job_id,
        parent_acquisition_job_id=request.parent_acquisition_job_id,
        acquisition_lineage_id=request.acquisition_lineage_id,
        candidate_reference=request.candidate_reference,
        query_reference=request.query_reference,
        obligation_reference=request.obligation_reference,
        status=status,
        observed_at=observed_at,
        **kwargs,
    )


def _blocked_result(
    request: AcquisitionRequest,
    *,
    code: str,
    detail: str,
) -> AcquisitionExecutionResult:
    return AcquisitionExecutionResult(
        request=request,
        status=AcquisitionExecutionStatus.BLOCKED,
        block_code=code,
        detail=compact_failure_detail(detail),
        transport_posture="blocked_before_transport",
    )


def _failure_result(
    request: AcquisitionRequest,
    *,
    code: str,
    detail: str,
    attempted: int,
    completed: int = 0,
) -> AcquisitionExecutionResult:
    artifact = _artifact(
        request,
        kind=AcquisitionArtifactKind.PROVIDER_FAILURE,
        status="failed",
        observed_at=_now(),
        failure_code=code,
        failure_reason=compact_failure_detail(detail),
    )
    return AcquisitionExecutionResult(
        request=request,
        status=AcquisitionExecutionStatus.FAILED,
        artifacts=(artifact,),
        provider_calls_attempted=attempted,
        provider_calls_completed=completed,
        failure_code=code,
        detail=compact_failure_detail(detail),
        transport_posture="selected_adapter_failed_no_fallback",
    )


def _reject_closed_fields(value: Any) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(keys & (_FORBIDDEN_AUTHORITY_KEYS | _FORBIDDEN_RAW_KEYS))
    if forbidden:
        raise AcquisitionContractError(
            "provider_response_closed_fields_rejected",
            "provider response opens closed fields: " + ", ".join(forbidden),
        )


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _bounded_text(text: str, limit: int) -> tuple[str, str]:
    if limit <= 0:
        return "", "provider_excess_content_truncated_to_authorized_budget"
    if len(text) <= limit:
        return text, "not_truncated"
    return text[:limit], "provider_excess_content_truncated_to_authorized_budget"


def _scalar_text(value: Any) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text or None


def _http_status(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if 100 <= parsed <= 599 else None


def _reported_http_status(source: Mapping[str, Any]) -> int | None:
    value = (
        source.get("http_status")
        if "http_status" in source
        else source.get("status_code")
    )
    return _http_status(value)


def _url(value: Any) -> str | None:
    text = _scalar_text(value)
    parsed = urlsplit(text or "")
    if not text or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return text


def _normalized_url(value: str) -> str:
    parsed = urlsplit(value)
    path = parsed.path or "/"
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            path.rstrip("/") or "/",
            parsed.query,
            "",
        )
    )


def _observed_at(value: Mapping[str, Any]) -> str:
    return (
        _scalar_text(
            value.get("observed_at")
            or value.get("retrieved_or_observed_at")
            or value.get("retrieved_at")
        )
        or _now()
    )


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _authorization_headers(env_name: str) -> dict[str, str]:
    token = os.getenv(env_name)
    if not token:
        raise RuntimeError(f"{env_name} is not set")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _post_json(url: str, payload: dict[str, Any], *, env_name: str) -> Mapping[str, Any]:
    response = requests.post(
        url,
        json=payload,
        headers=_authorization_headers(env_name),
        timeout=ACQUISITION_TRANSPORT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, Mapping):
        raise ValueError("provider response is not an object")
    return data


def _linkup_fetch_transport(payload: dict[str, Any]) -> Mapping[str, Any]:
    return _post_json(LINKUP_FETCH_URL, payload, env_name="LINKUP_API_KEY")


def _linkup_deep_transport(payload: dict[str, Any]) -> Mapping[str, Any]:
    return _post_json(LINKUP_SEARCH_URL, payload, env_name="LINKUP_API_KEY")


def _tavily_extract_transport(payload: dict[str, Any]) -> Mapping[str, Any]:
    return _post_json(f"{TAVILY_API_ROOT}/extract", payload, env_name="TAVILY_API_KEY")


def _tavily_map_transport(payload: dict[str, Any]) -> Mapping[str, Any]:
    return _post_json(f"{TAVILY_API_ROOT}/map", payload, env_name="TAVILY_API_KEY")


def _tavily_crawl_transport(payload: dict[str, Any]) -> Mapping[str, Any]:
    return _post_json(f"{TAVILY_API_ROOT}/crawl", payload, env_name="TAVILY_API_KEY")


__all__ = [
    "ACQUISITION_TRANSPORT_TIMEOUT_SECONDS",
    "AcquisitionTransports",
    "LINKUP_FETCH_URL",
    "LINKUP_SEARCH_URL",
    "TAVILY_API_ROOT",
    "dispatch_acquisition",
]
