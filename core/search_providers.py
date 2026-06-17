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

from core.cost_accounting import CostAccumulator
from core.run_logging import log_provider_error, log_retrieval_timeout

logger = logging.getLogger(__name__)

# HTTP / SDK wall-clock bounds (seconds); override via env for ops tuning.
TAVILY_SEARCH_TIMEOUT_SEC = float(os.environ.get("TAVILY_SEARCH_TIMEOUT_SEC", "30"))
LINKUP_SEARCH_TIMEOUT_SEC = float(os.environ.get("LINKUP_SEARCH_TIMEOUT_SEC", "30"))
BRAVE_SEARCH_TIMEOUT_SEC = float(os.environ.get("BRAVE_SEARCH_TIMEOUT_SEC", "8"))

# Exa SDK uses requests without per-request timeout; bound wall-clock wait (orphan thread may still finish in background).
EXA_SEARCH_TIMEOUT_SEC = float(os.environ.get("EXA_SEARCH_TIMEOUT_SEC", "30"))

_RETRIEVAL_TIMEOUT_SEC = {
    "tavily": TAVILY_SEARCH_TIMEOUT_SEC,
    "linkup": LINKUP_SEARCH_TIMEOUT_SEC,
    "exa": EXA_SEARCH_TIMEOUT_SEC,
    "brave": BRAVE_SEARCH_TIMEOUT_SEC,
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
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Function {func.__name__} failed after {max_retries} attempts. Error: {e}")
                        raise
                    time.sleep(base_delay * (2**attempt))

        return wrapper

    return decorator


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
    elif intent == "general" and any(k in text for k in ["journal", "study", "research", "official", "dataset", "forum"]):
        score += 1
    return score


def get_news_date_window(complexity: str) -> Tuple[str, str]:
    news_windows = {"low": 14, "medium": 21, "high": 30}
    days = news_windows.get(complexity, 14)
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return from_date, to_date


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

    r = requests.post("https://api.tavily.com/search", json=payload, timeout=TAVILY_SEARCH_TIMEOUT_SEC)
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

    r = requests.post(
        "https://api.linkup.so/v1/search",
        json=payload,
        headers=headers,
        timeout=LINKUP_SEARCH_TIMEOUT_SEC,
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
) -> Tuple[List[Dict[str, Any]], List[str]]:
    if not os.getenv("EXA_API_KEY"):
        raise RuntimeError("EXA_API_KEY is not set")

    try:
        exa = get_exa_client()
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
        results = []
        if cost_accumulator is not None:
            cost_accumulator.record_search_call(phase=cost_phase, provider="exa")
        for item in response.results:
            item_url = getattr(item, "url", "") or ""
            title = getattr(item, "title", "") or ""
            content = getattr(item, "text", "") or ""
            results.append(
                {
                    "title": title,
                    "url": item_url,
                    "snippet": content[:500],
                    "raw_content": content,
                    "domain": normalize_domain(item_url),
                    "credibility": credibility_score(item_url, title, content, intent),
                    "_exa_score": getattr(item, "score", 0.0) or 0.0,
                }
            )
        return [x for x in results if x.get("url")], []
    except Exception as e:
        logger.error(f"Exa provider error: {type(e).__name__}: {e}")
        log_provider_error(
            provider="exa",
            error=f"{type(e).__name__}: {e}",
            query_preview=query[:200],
            phase="retrieval",
            logger=logger,
        )
        return [], []


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
) -> list[dict[str, Any]]:
    """Provider-neutral lightweight scout search.

    The scout role is provider-neutral. Brave is the only supported provider
    surface for this path today; later providers can join the same contract.
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
    try:
        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
            timeout=BRAVE_SEARCH_TIMEOUT_SEC,
        )
        response.raise_for_status()
        data = response.json()
        if cost_accumulator is not None:
            cost_accumulator.record_search_call(phase=cost_phase, provider="brave")
    except Exception as e:
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
