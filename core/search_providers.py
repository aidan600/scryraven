import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import Any, Dict, List, Mapping, Optional, Tuple
from urllib.parse import urlparse

import requests
from exa_py import Exa

from core.bounded_product_profile import get_route_pricing
from core.cap_enforcement import (
    AttemptReservation,
    ExternalAttemptSpec,
    ExternalCallFamily,
    RunCapExceeded,
    RunCapPolicy,
    TokenUsage,
    mark_cap_aware,
)
from core.cost_accounting import CostAccumulator
from core.run_logging import log_provider_error, log_retrieval_timeout

logger = logging.getLogger(__name__)

# HTTP / SDK wall-clock bounds (seconds); override via env for ops tuning.
TAVILY_SEARCH_TIMEOUT_SEC = float(os.environ.get("TAVILY_SEARCH_TIMEOUT_SEC", "30"))
LINKUP_SEARCH_TIMEOUT_SEC = float(os.environ.get("LINKUP_SEARCH_TIMEOUT_SEC", "30"))
BRAVE_SEARCH_TIMEOUT_SEC = float(os.environ.get("BRAVE_SEARCH_TIMEOUT_SEC", "8"))
SERPER_SEARCH_TIMEOUT_SEC = float(os.environ.get("SERPER_SEARCH_TIMEOUT_SEC", "8"))

# Exa SDK uses requests without per-request timeout; bound wall-clock wait (orphan thread may still finish in background).
EXA_SEARCH_TIMEOUT_SEC = float(os.environ.get("EXA_SEARCH_TIMEOUT_SEC", "30"))

_RETRIEVAL_TIMEOUT_SEC = {
    "tavily": TAVILY_SEARCH_TIMEOUT_SEC,
    "linkup": LINKUP_SEARCH_TIMEOUT_SEC,
    "exa": EXA_SEARCH_TIMEOUT_SEC,
    "brave": BRAVE_SEARCH_TIMEOUT_SEC,
    "serper": SERPER_SEARCH_TIMEOUT_SEC,
}


def retrieval_timeout_seconds(provider: str) -> float:
    """Configured HTTP/SDK timeout for logging when a provider surfaces a timeout error."""
    return float(_RETRIEVAL_TIMEOUT_SEC.get(provider, 30.0))


@lru_cache(maxsize=1)
def get_exa_client() -> Exa:
    """Process-local singleton; matches prior Streamlit cache_resource lifetime per server process."""
    return Exa(api_key=os.getenv("EXA_API_KEY"))


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cap_policy = kwargs.get("cap_policy")
            bounded = isinstance(cap_policy, RunCapPolicy) and cap_policy.bounded
            attempt_limit = 1 if bounded and cap_policy.max_retries == 0 else max_retries
            for attempt in range(attempt_limit):
                call_kwargs = dict(kwargs)
                call_kwargs["_physical_retry_index"] = attempt
                try:
                    return func(*args, **call_kwargs)
                except RunCapExceeded:
                    raise
                except Exception as e:
                    if attempt == attempt_limit - 1:
                        if bounded:
                            logger.error(
                                "Bounded %s request failed.",
                                func.__name__,
                            )
                        else:
                            logger.error(
                                "Function %s failed after %s attempts. Error: %s",
                                func.__name__,
                                attempt_limit,
                                e,
                            )
                        raise
                    time.sleep(base_delay * (2**attempt))

        return wrapper

    return decorator


def _reserve_search_attempt(
    cap_policy: RunCapPolicy | None,
    *,
    provider: str,
    logical_call_id: str | None,
    retry_index: int,
    requested_timeout_seconds: float,
) -> AttemptReservation | None:
    if cap_policy is None or not cap_policy.bounded:
        return None
    logical_id = logical_call_id or cap_policy.new_logical_call_id(f"search-{provider}")
    pricing = get_route_pricing(
        ExternalCallFamily.SEARCH,
        provider,
        "search",
    )
    return cap_policy.reserve_attempt(
        ExternalAttemptSpec(
            family=ExternalCallFamily.SEARCH,
            provider=provider,
            route="search",
            operation="search",
            logical_call_id=logical_id,
            max_usage=TokenUsage(),
            pricing=pricing,
            requested_timeout_seconds=requested_timeout_seconds,
            is_retry=retry_index > 0,
        )
    )


def _dispatch_search(
    reservation: AttemptReservation | None,
    operation: Any,
) -> Any:
    if reservation is None:
        return operation()
    reservation.mark_dispatched()
    try:
        response = operation()
    except Exception:
        reservation.settle_conservative("dispatch_outcome_ambiguous")
        raise
    reservation.settle_observed(TokenUsage())
    return response


def _timeout(
    configured: float,
    reservation: AttemptReservation | None,
) -> float:
    if reservation is None:
        return configured
    return min(configured, reservation.timeout_seconds)


def normalize_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def credibility_score(url: str, title: str = "", snippet: str = "", intent: str = "general") -> int:
    domain = normalize_domain(url)
    text = f"{title} {snippet}".lower()
    gov_academic = (".gov", ".edu", "nih.gov", "nature.com", "science.org", "ncbi.nlm.nih.gov")
    news_media = ("reuters.com", "apnews.com", "bbc.com", "nytimes.com", "wsj.com", "bloomberg.com")
    low_domains = (
        "medium.com",
        "quora.com",
        "reddit.com",
        "tiktok.com",
        "youtube.com",
        "brainly.com",
        "chegg.com",
        "coursehero.com",
        "hdforums.com",
        "tripadvisor.com",
        "yelp.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "pinterest.com",
        "answers.yahoo.com",
    )

    score = 0
    if intent == "news":
        if any(domain.endswith(x) for x in news_media):
            score += 4
        elif any(domain.endswith(x) for x in gov_academic):
            score += 2
    else:
        if any(domain.endswith(x) for x in gov_academic):
            score += 4
        elif any(domain.endswith(x) for x in news_media):
            score += 2

    if any(domain.endswith(x) for x in low_domains):
        score -= 4
    if intent == "news" and any(k in text for k in ["breaking", "live", "update", "latest"]):
        score += 1
    elif intent == "general" and any(
        k in text for k in ["journal", "study", "research", "official", "dataset", "forum"]
    ):
        score += 1
    return score


def get_news_date_window(complexity: str) -> Tuple[str, str]:
    news_windows = {"low": 14, "medium": 21, "high": 30}
    days = news_windows.get(complexity, 14)
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return from_date, to_date


@mark_cap_aware
@retry_with_backoff(max_retries=3, base_delay=2.0)
def search_web_results(
    query: str,
    intent: str = "general",
    complexity: str = "low",
    max_results: int = 6,
    search_depth: str = "basic",
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    cost_accumulator: Optional[CostAccumulator] = None,
    cost_phase: str = "retrieval",
    cap_policy: RunCapPolicy | None = None,
    logical_call_id: str | None = None,
    _physical_retry_index: int = 0,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is not set")

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "topic": "news" if intent == "news" else "general",
        "include_answer": False,
        "include_images": True,
        "include_raw_content": True,
        "max_results": max_results,
    }
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains

    if intent == "news":
        news_windows = {"low": 14, "medium": 21, "high": 30}
        payload["days"] = news_windows.get(complexity, 14)

    reservation = _reserve_search_attempt(
        cap_policy,
        provider="tavily",
        logical_call_id=logical_call_id,
        retry_index=_physical_retry_index,
        requested_timeout_seconds=TAVILY_SEARCH_TIMEOUT_SEC,
    )
    r = _dispatch_search(
        reservation,
        lambda: requests.post(
            "https://api.tavily.com/search",
            json=payload,
            timeout=_timeout(TAVILY_SEARCH_TIMEOUT_SEC, reservation),
        ),
    )
    r.raise_for_status()
    data = r.json()
    if cost_accumulator is not None:
        cost_accumulator.record_search_call(phase=cost_phase, provider="tavily")

    results = []
    for item in data.get("results", []):
        item_url = item.get("url", "").strip()
        title = item.get("title", "").strip()
        snippet = item.get("content", "").strip()
        raw_content = item.get("raw_content", "")
        results.append(
            {
                "title": title,
                "url": item_url,
                "snippet": snippet,
                "raw_content": raw_content,
                "domain": normalize_domain(item_url),
                "credibility": credibility_score(item_url, title, snippet, intent),
            }
        )
    return [x for x in results if x["url"]], data.get("images", [])


@mark_cap_aware
@retry_with_backoff(max_retries=3, base_delay=2.0)
def search_linkup_results(
    query: str,
    depth: str = "standard",
    output_type: str = "searchResults",
    intent: str = "general",
    max_results: int = 6,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    structured_schema: Optional[str] = None,
    cost_accumulator: Optional[CostAccumulator] = None,
    cost_phase: str = "retrieval",
    cap_policy: RunCapPolicy | None = None,
    logical_call_id: str | None = None,
    _physical_retry_index: int = 0,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    api_key = os.getenv("LINKUP_API_KEY")
    if not api_key:
        raise RuntimeError("LINKUP_API_KEY is not set")

    payload = {
        "q": query,
        "depth": depth,
        "outputType": output_type,
        "maxResults": max_results,
        "includeImages": True,
    }

    if include_domains:
        payload["includeDomains"] = include_domains
    if exclude_domains:
        payload["excludeDomains"] = exclude_domains
    if from_date:
        payload["fromDate"] = from_date
    if to_date:
        payload["toDate"] = to_date
    if output_type == "structured" and structured_schema:
        payload["structuredOutputSchema"] = structured_schema
    if output_type == "sourcedAnswer":
        payload["includeInlineCitations"] = True
        payload["includeSources"] = True

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    reservation = _reserve_search_attempt(
        cap_policy,
        provider="linkup",
        logical_call_id=logical_call_id,
        retry_index=_physical_retry_index,
        requested_timeout_seconds=LINKUP_SEARCH_TIMEOUT_SEC,
    )
    r = _dispatch_search(
        reservation,
        lambda: requests.post(
            "https://api.linkup.so/v1/search",
            json=payload,
            headers=headers,
            timeout=_timeout(LINKUP_SEARCH_TIMEOUT_SEC, reservation),
        ),
    )
    r.raise_for_status()
    data = r.json()
    if cost_accumulator is not None:
        cost_accumulator.record_search_call(phase=cost_phase, provider="linkup")

    results = []
    images = []

    if output_type == "sourcedAnswer":
        answer_text = data.get("answer", "")
        sources = data.get("sources", [])
        for src in sources:
            src_url = src.get("url", "")
            src_title = src.get("name", "")
            results.append(
                {
                    "title": src_title,
                    "url": src_url,
                    "snippet": answer_text[:1000],
                    "raw_content": answer_text,
                    "domain": normalize_domain(src_url),
                    "credibility": credibility_score(src_url, src_title, answer_text, intent),
                    "_linkup_sourced_answer": True,
                }
            )
    else:
        for item in data.get("results", []):
            item_url = item.get("url", "")
            title = item.get("name", "")
            content = item.get("content", "")
            if item.get("type") == "image":
                images.append(item_url)
                continue
            results.append(
                {
                    "title": title,
                    "url": item_url,
                    "snippet": content[:500],
                    "raw_content": content,
                    "domain": normalize_domain(item_url),
                    "credibility": credibility_score(item_url, title, content, intent),
                }
            )

    return [x for x in results if x.get("url")], images


@mark_cap_aware
@retry_with_backoff(max_retries=3, base_delay=2.0)
def search_exa_results(
    query: str,
    intent: str = "general",
    max_results: int = 6,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    cost_accumulator: Optional[CostAccumulator] = None,
    cost_phase: str = "retrieval",
    cap_policy: RunCapPolicy | None = None,
    logical_call_id: str | None = None,
    _physical_retry_index: int = 0,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise RuntimeError("EXA_API_KEY is not set")

    try:
        reservation = _reserve_search_attempt(
            cap_policy,
            provider="exa",
            logical_call_id=logical_call_id,
            retry_index=_physical_retry_index,
            requested_timeout_seconds=EXA_SEARCH_TIMEOUT_SEC,
        )
        kwargs = {
            "num_results": max_results,
            "type": "neural",
            "text": True,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains
        if from_date:
            kwargs["start_published_date"] = from_date
        if to_date:
            kwargs["end_published_date"] = to_date

        if reservation is not None:
            payload: dict[str, Any] = {
                "query": query,
                "numResults": max_results,
                "type": "neural",
                "contents": {"text": True},
            }
            if include_domains:
                payload["includeDomains"] = include_domains
            if exclude_domains:
                payload["excludeDomains"] = exclude_domains
            if from_date:
                payload["startPublishedDate"] = from_date
            if to_date:
                payload["endPublishedDate"] = to_date
            raw_response = _dispatch_search(
                reservation,
                lambda: requests.post(
                    "https://api.exa.ai/search",
                    headers={
                        "x-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=_timeout(EXA_SEARCH_TIMEOUT_SEC, reservation),
                ),
            )
            raw_response.raise_for_status()
            response_items = raw_response.json().get("results", [])
        else:
            exa = get_exa_client()

            def _search() -> Any:
                return exa.search_and_contents(query, **kwargs)

            with ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(_search)
                try:
                    response = fut.result(timeout=EXA_SEARCH_TIMEOUT_SEC)
                except FuturesTimeout:
                    logger.error(
                        "Exa provider error: TimeoutError: search_and_contents exceeded %.0fs",
                        EXA_SEARCH_TIMEOUT_SEC,
                    )
                    log_retrieval_timeout(
                        provider="exa",
                        query=query,
                        timeout_seconds=EXA_SEARCH_TIMEOUT_SEC,
                        logger=logger,
                    )
                    return [], []
            response_items = response.results
        results = []
        if cost_accumulator is not None:
            cost_accumulator.record_search_call(phase=cost_phase, provider="exa")
        for item in response_items:
            if isinstance(item, Mapping):
                item_url = str(item.get("url") or "")
                title = str(item.get("title") or "")
                content = str(item.get("text") or "")
                score = item.get("score", 0.0) or 0.0
            else:
                item_url = getattr(item, "url", "") or ""
                title = getattr(item, "title", "") or ""
                content = getattr(item, "text", "") or ""
                score = getattr(item, "score", 0.0) or 0.0
            results.append(
                {
                    "title": title,
                    "url": item_url,
                    "snippet": content[:500],
                    "raw_content": content,
                    "domain": normalize_domain(item_url),
                    "credibility": credibility_score(item_url, title, content, intent),
                    "_exa_score": score,
                }
            )
        return [x for x in results if x.get("url")], []
    except RunCapExceeded:
        raise
    except Exception as e:
        if cap_policy is not None and cap_policy.bounded:
            logger.error("Bounded Exa provider request failed.")
            return [], []
        logger.error(f"Exa provider error: {type(e).__name__}: {e}")
        log_provider_error(
            provider="exa",
            error=f"{type(e).__name__}: {e}",
            query_preview=query[:200],
            phase="retrieval",
            logger=logger,
        )
        return [], []


@mark_cap_aware
def search_scout_results(
    *,
    provider: str,
    query: str,
    max_results: int | None = None,
    num_results: int | None = None,
    provider_freshness_value: str | None = None,
    freshness_policy: Mapping[str, Any] | None = None,
    cost_accumulator: CostAccumulator | None = None,
    cost_phase: str = "scout",
    cap_policy: RunCapPolicy | None = None,
    logical_call_id: str | None = None,
) -> list[dict[str, Any]]:
    """Provider-neutral lightweight scout search.

    The scout role is provider-neutral. Provider surfaces join this same
    candidate-discovery contract without becoming separate evidence roles.
    Freshness is supplied by the caller's search-job policy and is omitted when
    no policy value is present.
    """

    provider_name = (provider or "").casefold()
    result_count = num_results if num_results is not None else max_results
    if result_count is None:
        result_count = 5
    freshness = provider_freshness_value
    if freshness is None and freshness_policy:
        by_provider = freshness_policy.get("provider_freshness_value_by_provider")
        if isinstance(by_provider, Mapping):
            value = by_provider.get(provider_name)
            freshness = str(value) if value else None
    if provider_name == "brave":
        return _brave_search_results(
            query,
            num_results=int(result_count),
            freshness=freshness,
            cost_accumulator=cost_accumulator,
            cost_phase=cost_phase,
            log_context="Brave scout search",
            cap_policy=cap_policy,
            logical_call_id=logical_call_id,
        )
    if provider_name == "serper":
        return _serper_search_results(
            query,
            num_results=int(result_count),
            freshness=freshness,
            cost_accumulator=cost_accumulator,
            cost_phase=cost_phase,
            cap_policy=cap_policy,
            logical_call_id=logical_call_id,
        )
    raise ValueError(f"unsupported scout provider: {provider}")


def brave_reconnaissance(
    query: str,
    api_key: str | None = None,
    num_results: int = 5,
    cost_accumulator: CostAccumulator | None = None,
    cost_phase: str = "recon",
) -> list[dict[str, Any]]:
    """
    Legacy compatibility alias for lightweight Brave entity/term resolution.

    New scout callsites should use ``search_scout_results(...)`` and supply
    provider freshness from a provider-neutral freshness policy.
    Returns titles, URLs, and snippets; no full fetch, chunking, or embedding.
    """
    return _brave_search_results(
        query,
        api_key=api_key,
        num_results=num_results,
        freshness="pw",
        cost_accumulator=cost_accumulator,
        cost_phase=cost_phase,
        log_context="Brave reconnaissance",
    )


def _brave_search_results(
    query: str,
    api_key: str | None = None,
    num_results: int = 5,
    freshness: str | None = None,
    cost_accumulator: CostAccumulator | None = None,
    cost_phase: str = "scout",
    log_context: str = "Brave scout search",
    cap_policy: RunCapPolicy | None = None,
    logical_call_id: str | None = None,
) -> list[dict[str, Any]]:
    import httpx

    key = api_key or os.getenv("BRAVE_API_KEY")
    if not key:
        raise RuntimeError("BRAVE_API_KEY is not set")

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": key,
    }
    params = {
        "q": query,
        "count": num_results,
        "text_decorations": False,
        "search_lang": "en",
    }
    if freshness:
        params["freshness"] = freshness
    reservation = _reserve_search_attempt(
        cap_policy,
        provider="brave",
        logical_call_id=logical_call_id,
        retry_index=0,
        requested_timeout_seconds=BRAVE_SEARCH_TIMEOUT_SEC,
    )
    try:
        response = _dispatch_search(
            reservation,
            lambda: httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
                timeout=_timeout(BRAVE_SEARCH_TIMEOUT_SEC, reservation),
            ),
        )
        response.raise_for_status()
        data = response.json()
        if cost_accumulator is not None:
            cost_accumulator.record_search_call(phase=cost_phase, provider="brave")
    except RunCapExceeded:
        raise
    except Exception as e:
        if cap_policy is not None and cap_policy.bounded:
            logger.error("Bounded Brave provider request failed.")
            return []
        if isinstance(e, httpx.TimeoutException):
            log_retrieval_timeout(
                provider="brave",
                query=query,
                timeout_seconds=BRAVE_SEARCH_TIMEOUT_SEC,
                logger=logger,
            )
        else:
            log_provider_error(
                provider="brave",
                error=f"{type(e).__name__}: {e}",
                query_preview=(query or "")[:200],
                phase="retrieval",
                logger=logger,
            )
        logger.error("%s failed: %s: %s", log_context, type(e).__name__, e)
        return []

    results = data.get("web", {}).get("results", [])
    return [
        {
            "title": r.get("title", "") or "",
            "url": r.get("url", "") or "",
            "snippet": r.get("description", "") or "",
            "age": r.get("age", "") or "",
        }
        for r in results
    ]


def _serper_search_results(
    query: str,
    api_key: str | None = None,
    num_results: int = 5,
    freshness: str | None = None,
    cost_accumulator: CostAccumulator | None = None,
    cost_phase: str = "scout",
    cap_policy: RunCapPolicy | None = None,
    logical_call_id: str | None = None,
) -> list[dict[str, Any]]:
    key = api_key or os.getenv("SERPER_API_KEY")
    if not key:
        raise RuntimeError("SERPER_API_KEY is not set")

    headers = {
        "X-API-KEY": key,
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "q": query,
        "num": int(num_results),
    }
    if freshness:
        payload["tbs"] = freshness

    reservation = _reserve_search_attempt(
        cap_policy,
        provider="serper",
        logical_call_id=logical_call_id,
        retry_index=0,
        requested_timeout_seconds=SERPER_SEARCH_TIMEOUT_SEC,
    )
    try:
        response = _dispatch_search(
            reservation,
            lambda: requests.post(
                "https://google.serper.dev/search",
                headers=headers,
                json=payload,
                timeout=_timeout(SERPER_SEARCH_TIMEOUT_SEC, reservation),
            ),
        )
        response.raise_for_status()
        data = response.json()
        if cost_accumulator is not None:
            cost_accumulator.record_search_call(phase=cost_phase, provider="serper")
    except RunCapExceeded:
        raise
    except Exception as e:
        if cap_policy is not None and cap_policy.bounded:
            logger.error("Bounded Serper provider request failed.")
            return []
        if isinstance(e, requests.exceptions.Timeout):
            log_retrieval_timeout(
                provider="serper",
                query=query,
                timeout_seconds=SERPER_SEARCH_TIMEOUT_SEC,
                logger=logger,
            )
        else:
            log_provider_error(
                provider="serper",
                error=f"{type(e).__name__}: {e}",
                query_preview=(query or "")[:200],
                phase="retrieval",
                logger=logger,
            )
        logger.error("Serper scout search failed: %s: %s", type(e).__name__, e)
        return []

    results = []
    for item in data.get("organic", []):
        if not isinstance(item, Mapping):
            continue
        url = _serper_text(item.get("link"), limit=500)
        title = _serper_text(item.get("title"), limit=300)
        snippet = _serper_text(item.get("snippet"), limit=500)
        normalized: dict[str, Any] = {
            "title": title,
            "url": url,
            "snippet": snippet,
            "domain": normalize_domain(url),
            "credibility": credibility_score(url, title, snippet, "general"),
        }
        position = _serper_position(item.get("position"))
        if position is not None:
            normalized["position"] = position
        date_value = _serper_date(item.get("date"))
        if date_value:
            normalized["date"] = date_value
        if normalized["url"]:
            results.append(normalized)
    return results


def _serper_position(value: Any) -> int | None:
    try:
        position = int(value)
    except (TypeError, ValueError):
        return None
    if position < 1:
        return None
    return position


def _serper_date(value: Any) -> str:
    return _serper_text(value, limit=80)


def _serper_text(value: Any, *, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]
