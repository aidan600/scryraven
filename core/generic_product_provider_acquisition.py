"""Product-owned provider acquisition for generic single-relation dogfood.

The adapter reuses existing product provider surfaces and writes only the
sanitized provider-record envelope consumed by the generic product path. It does
not create source custody, evidence, citation eligibility, source-obligation
satisfaction, answer material, or product-correctness claims.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

from core.search_providers import search_scout_results, search_web_results

PRODUCT_PROVIDER_ACQUISITION_RESPONSE_KIND = (
    "generic_product_provider_acquisition_response"
)
BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE = (
    "BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE"
)
BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE = (
    "BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE"
)

DEFAULT_EXTRACTION_PROVIDER = "tavily"
DEFAULT_SCOUT_PROVIDER = "serper"
DEFAULT_OPERATION = "search"
DEFAULT_MAX_RESULTS = 5
PROVIDER_EXTRACTED_CONTENT_TYPE = "text/html"
PROVIDER_EXTRACTED_SOURCE_TEXT_MAX_CHARS = 20_000


@dataclass(frozen=True, slots=True)
class ProductProviderAcquisitionRequest:
    repo_root: Path
    output_path: Path
    query: str
    provider: str = DEFAULT_EXTRACTION_PROVIDER
    acquisition_provider_role: str = "extraction_provider"
    operation: str = DEFAULT_OPERATION
    max_results: int = DEFAULT_MAX_RESULTS
    domain_constraints: tuple[str, ...] = ()
    include_domains: tuple[str, ...] = ()
    exclude_domains: tuple[str, ...] = ()
    source_of_record_domain_constraints: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProductProviderAcquisitionResult:
    return_code: int
    output_path: Path
    provider_calls_attempted: int
    provider_calls_completed: int
    blocker: str | None = None
    detail: str | None = None


TavilyProductProviderCallable = Callable[..., tuple[list[dict[str, Any]], list[Any]]]
ScoutProductProviderCallable = Callable[..., list[dict[str, Any]]]
ProductProviderAcquisitionRunner = Callable[
    [ProductProviderAcquisitionRequest],
    ProductProviderAcquisitionResult,
]


def build_generic_product_provider_acquisition_runner(
    *,
    tavily_product_provider_callable: TavilyProductProviderCallable | None = None,
    scout_product_provider_callable: ScoutProductProviderCallable | None = None,
) -> ProductProviderAcquisitionRunner:
    """Build the default product-owned acquisition runner."""

    tavily_callable = tavily_product_provider_callable or search_web_results
    scout_callable = scout_product_provider_callable or search_scout_results

    def runner(
        request: ProductProviderAcquisitionRequest,
    ) -> ProductProviderAcquisitionResult:
        return run_generic_product_provider_acquisition(
            request,
            tavily_product_provider_callable=tavily_callable,
            scout_product_provider_callable=scout_callable,
        )

    return runner


def run_generic_product_provider_acquisition(
    request: ProductProviderAcquisitionRequest,
    *,
    tavily_product_provider_callable: TavilyProductProviderCallable = search_web_results,
    scout_product_provider_callable: ScoutProductProviderCallable = search_scout_results,
) -> ProductProviderAcquisitionResult:
    """Acquire sanitized provider records through product provider surfaces."""

    provider = _clean_provider(request.provider)
    operation = _clean_operation(request.operation)
    max_results = _max_results(request.max_results)
    include_domains = _domain_constraints(
        (
            *request.domain_constraints,
            *request.include_domains,
            *request.source_of_record_domain_constraints,
        )
    )
    exclude_domains = _domain_constraints(request.exclude_domains)
    if operation != DEFAULT_OPERATION:
        return _failed_result(
            request,
            blocker=BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE,
            detail="Only search operation is available for product provider acquisition.",
            provider_calls_attempted=0,
        )
    try:
        if provider == DEFAULT_EXTRACTION_PROVIDER:
            tavily_kwargs: dict[str, Any] = {
                "query": request.query,
                "intent": "general",
                "complexity": "low",
                "max_results": max_results,
                "search_depth": "basic",
            }
            if include_domains:
                tavily_kwargs["include_domains"] = list(include_domains)
            if exclude_domains:
                tavily_kwargs["exclude_domains"] = list(exclude_domains)
            provider_records, _images = tavily_product_provider_callable(
                **tavily_kwargs,
            )
            results = normalize_tavily_product_provider_results(
                provider_records,
                provider_call_index=1,
            )
        elif provider == DEFAULT_SCOUT_PROVIDER:
            provider_records = scout_product_provider_callable(
                provider=DEFAULT_SCOUT_PROVIDER,
                query=request.query,
                max_results=max_results,
            )
            results = normalize_scout_product_provider_results(
                provider_records,
                provider_call_index=1,
            )
        else:
            return _failed_result(
                request,
                blocker=BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE,
                detail=(
                    f"{provider} is not available for generic product provider "
                    "acquisition."
                ),
                provider_calls_attempted=0,
            )
    except Exception as exc:  # noqa: BLE001 - fail closed without leaking provider detail.
        return _provider_exception_result(
            request,
            provider=provider,
            exc=exc,
        )

    payload = {
        "request_kind": PRODUCT_PROVIDER_ACQUISITION_RESPONSE_KIND,
        "provider": provider,
        "acquisition_provider_role": _clean_provider_role(
            request.acquisition_provider_role
        ),
        "operation": operation,
        "result_count": len(results),
        "results": results,
        "domain_constraints": list(include_domains),
        "include_domains": list(include_domains),
        "exclude_domains": list(exclude_domains),
        "source_of_record_domain_constraints": list(
            _domain_constraints(request.source_of_record_domain_constraints)
        ),
        "domain_constraints_acquisition_only": True,
        "domain_constraints_create_source_authority": False,
        "domain_constraints_satisfy_source_obligation": False,
        "domain_constraints_citation_eligible": False,
        "domain_constraints_claim_correctness": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    _write_json(request.output_path, payload)
    return ProductProviderAcquisitionResult(
        return_code=0,
        output_path=request.output_path,
        provider_calls_attempted=1,
        provider_calls_completed=1,
    )


def normalize_tavily_product_provider_results(
    results: Sequence[Mapping[str, Any]],
    *,
    provider_call_index: int,
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    """Normalize Tavily records into the generic sanitized provider envelope."""

    normalized: list[dict[str, Any]] = []
    extracted_at = observed_at or _observed_at()
    for index, item in enumerate(results, 1):
        safe = _safe_mapping(item)
        url = _clean_text(safe.get("url"), limit=700)
        title = _clean_text(safe.get("title"), limit=220)
        if not url or not title:
            continue
        record: dict[str, Any] = {
            "title": title,
            "url": url,
            "domain": _domain(safe.get("domain"), url=url),
            "snippet": _clean_text(safe.get("snippet"), limit=500),
            "published_or_observed_date": (
                _clean_text(
                    safe.get("published_or_observed_date") or safe.get("date"),
                    limit=80,
                )
                or extracted_at[:10]
            ),
            "result_rank": _positive_int(
                safe.get("result_rank") or safe.get("rank") or index,
                default=index,
            ),
            "provider_call_index": _positive_int(
                safe.get("provider_call_index") or safe.get("call_index") or provider_call_index,
                default=provider_call_index,
            ),
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        }
        extracted_text = _bounded_provider_text(safe.get("raw_content"))
        if extracted_text:
            record.update(
                {
                    "provider_extracted_text": extracted_text,
                    "provider_extracted_text_sanitized": True,
                    "provider_extracted_text_bounded": True,
                    "provider_extracted_text_char_count": len(extracted_text),
                    "provider_extracted_text_digest": _digest_provider_text(
                        extracted_text
                    ),
                    "provider_extracted_source_text_digest": _digest_provider_text(
                        extracted_text
                    ),
                    "provider_extracted_content_type": (
                        PROVIDER_EXTRACTED_CONTENT_TYPE
                    ),
                    "provider_extracted_at": extracted_at,
                }
            )
        normalized.append(record)
    return normalized


def normalize_scout_product_provider_results(
    results: Sequence[Mapping[str, Any]],
    *,
    provider_call_index: int,
) -> list[dict[str, Any]]:
    """Normalize scout records as non-evidence directionality only."""

    normalized: list[dict[str, Any]] = []
    observed_date = _observed_at()[:10]
    for index, item in enumerate(results, 1):
        safe = _safe_mapping(item)
        url = _clean_text(safe.get("url") or safe.get("link"), limit=700)
        title = _clean_text(safe.get("title"), limit=220)
        if not url or not title:
            continue
        normalized.append(
            {
                "title": title,
                "url": url,
                "domain": _domain(safe.get("domain"), url=url),
                "snippet": _clean_text(safe.get("snippet"), limit=500),
                "published_or_observed_date": (
                    _clean_text(
                        safe.get("published_or_observed_date")
                        or safe.get("date")
                        or safe.get("age"),
                        limit=80,
                    )
                    or observed_date
                ),
                "result_rank": _positive_int(
                    safe.get("result_rank")
                    or safe.get("rank")
                    or safe.get("position")
                    or index,
                    default=index,
                ),
                "provider_call_index": _positive_int(
                    safe.get("provider_call_index")
                    or safe.get("call_index")
                    or provider_call_index,
                    default=provider_call_index,
                ),
                "raw_provider_payload_retained": False,
                "raw_search_response_retained": False,
            }
        )
    return normalized


def _provider_exception_result(
    request: ProductProviderAcquisitionRequest,
    *,
    provider: str,
    exc: Exception,
) -> ProductProviderAcquisitionResult:
    credential_name = _credential_name_from_exception(provider=provider, exc=exc)
    if credential_name:
        return _failed_result(
            request,
            blocker=BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE,
            detail=(
                f"{credential_name} is unavailable for {provider} product "
                "provider acquisition."
            ),
            provider_calls_attempted=1,
        )
    return _failed_result(
        request,
        blocker=BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE,
        detail=f"{provider} product provider acquisition failed closed.",
        provider_calls_attempted=1,
    )


def _failed_result(
    request: ProductProviderAcquisitionRequest,
    *,
    blocker: str,
    detail: str,
    provider_calls_attempted: int,
) -> ProductProviderAcquisitionResult:
    return ProductProviderAcquisitionResult(
        return_code=2,
        output_path=request.output_path,
        provider_calls_attempted=provider_calls_attempted,
        provider_calls_completed=0,
        blocker=blocker,
        detail=detail,
    )


def _credential_name_from_exception(*, provider: str, exc: Exception) -> str | None:
    detail = str(exc)
    if provider == DEFAULT_EXTRACTION_PROVIDER and "TAVILY_API_KEY" in detail:
        return "TAVILY_API_KEY"
    if provider == DEFAULT_SCOUT_PROVIDER and "SERPER_API_KEY" in detail:
        return "SERPER_API_KEY"
    return None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _digest_provider_text(text: str) -> str:
    encoded = json.dumps(
        {"provider_extracted_text": text},
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def _bounded_provider_text(value: Any) -> str | None:
    text = _clean_text(value, limit=PROVIDER_EXTRACTED_SOURCE_TEXT_MAX_CHARS)
    return text or None


def _clean_provider(value: Any) -> str:
    return str(value or "").strip().casefold() or DEFAULT_EXTRACTION_PROVIDER


def _clean_operation(value: Any) -> str:
    return str(value or "").strip().casefold() or DEFAULT_OPERATION


def _clean_provider_role(value: Any) -> str:
    text = str(value or "").strip().casefold().replace("-", "_")
    return text or "extraction_provider"


def _max_results(value: Any) -> int:
    parsed = _positive_int(value, default=DEFAULT_MAX_RESULTS)
    return min(parsed, DEFAULT_MAX_RESULTS)


def _domain_constraints(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        raw_items: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        raw_items = value
    else:
        raw_items = ()
    domains: list[str] = []
    seen: set[str] = set()
    for raw in raw_items:
        domain = _clean_domain_constraint(raw)
        if not domain or domain in seen:
            continue
        seen.add(domain)
        domains.append(domain)
    return tuple(domains[:DEFAULT_MAX_RESULTS])


def _clean_domain_constraint(value: Any) -> str | None:
    text = _clean_text(value, limit=260)
    if not text:
        return None
    parsed = urlparse(text if "://" in text else f"https://{text}")
    domain = (parsed.netloc or parsed.path).casefold().strip().strip("/")
    if not domain or "/" in domain or " " in domain:
        return None
    return domain[4:] if domain.startswith("www.") else domain


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed > 0 else default


def _domain(value: Any, *, url: str) -> str:
    parsed_url_domain = urlparse(url).netloc.lower()
    if parsed_url_domain:
        return parsed_url_domain
    explicit = _clean_text(value, limit=260)
    if explicit:
        parsed = urlparse(f"https://{explicit}" if "://" not in explicit else explicit)
        return (parsed.netloc or parsed.path).lower().strip("/")
    return ""


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _observed_at() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


__all__ = [
    "BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE",
    "BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE",
    "PRODUCT_PROVIDER_ACQUISITION_RESPONSE_KIND",
    "ProductProviderAcquisitionRequest",
    "ProductProviderAcquisitionResult",
    "ProductProviderAcquisitionRunner",
    "PROVIDER_EXTRACTED_SOURCE_TEXT_MAX_CHARS",
    "build_generic_product_provider_acquisition_runner",
    "normalize_scout_product_provider_results",
    "normalize_tavily_product_provider_results",
    "run_generic_product_provider_acquisition",
]
