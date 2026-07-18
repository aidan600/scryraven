import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import numpy as np

logger = logging.getLogger(__name__)

COMMERCE_DOMAINS = (
    "ebay.com",
    "amazon.com",
    "etsy.com",
    "walmart.com",
    "bestbuy.com",
    "aliexpress.com",
    "target.com",
    "craigslist.org",
    "homedepot.com",
    "lowes.com",
    "wayfair.com",
)

CONSUMER_FORUMS = (
    "hdforums.com",
    "cvoharley.com",
    "tripadvisor.com",
    "yelp.com",
    "houzz.com",
    "gardenweb.com",
    "ign.com",
    "fandom.com",
    "disboards.com",
    "motorcycle.com",
    "medium.com",
    "quora.com",
    "reddit.com",
    "tiktok.com",
    "youtube.com",
    "brainly.com",
    "chegg.com",
    "coursehero.com",
)

NEWS_PREFERRED_DOMAINS = [
    "apnews.com",
    "bbc.com",
    "aljazeera.com",
    "npr.org",
    "theguardian.com",
    "axios.com",
    "politico.com",
    "cbsnews.com",
    "nbcnews.com",
    "abcnews.go.com",
]

ACADEMIC_DOMAINS = [
    "arxiv.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "nature.com",
    "science.org",
    "plos.org",
    "biorxiv.org",
    "medrxiv.org",
    "ssrn.com",
    "jstor.org",
    "semanticscholar.org",
]


def normalize_domain(url: str) -> str:
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def rrf_merge(provider_result_lists: dict[str, list[dict]], k: int = 60) -> list[dict]:
    url_to_result: dict[str, dict] = {}
    url_to_rrf: dict[str, float] = {}

    for provider, results in provider_result_lists.items():
        for rank, result in enumerate(results):
            url = result.get("url", "")
            if not url:
                continue
            if url not in url_to_result:
                url_to_result[url] = result
                url_to_rrf[url] = 0.0
            url_to_rrf[url] += 1.0 / (k + rank + 1)

    merged = []
    for url, result in url_to_result.items():
        result["rrf_score"] = url_to_rrf[url]
        merged.append(result)

    merged.sort(key=lambda x: x["rrf_score"], reverse=True)
    return merged


def is_plausible_domain(url: str) -> bool:
    domain = normalize_domain(url)
    return not any(domain.endswith(d) for d in COMMERCE_DOMAINS + CONSUMER_FORUMS)


def get_news_date_window(complexity: str) -> Tuple[str, str]:
    news_windows = {"low": 14, "medium": 21, "high": 30}
    days = news_windows.get(complexity, 14)
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return from_date, to_date


def compute_similarities(q_emb: List[float], doc_embs: List[List[float]]) -> np.ndarray:
    if not doc_embs:
        return np.array([])
    q_vec = np.array(q_emb)
    embs_matrix = np.array(doc_embs)
    dot_products = np.dot(embs_matrix, q_vec)
    norms = np.linalg.norm(embs_matrix, axis=1) * np.linalg.norm(q_vec)
    return np.divide(dot_products, norms, out=np.zeros_like(dot_products), where=norms != 0)


def chunk_text(text: str, chunk_size: int = 1200) -> List[str]:
    paragraphs = re.split(r"\n\n+", text)
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue

        if len(current_chunk) + len(p) <= chunk_size:
            current_chunk += p + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = ""

            if len(p) > chunk_size:
                sentences = re.split(r"(?<=[.!?]) +", p)
                for s in sentences:
                    if len(current_chunk) + len(s) <= chunk_size:
                        current_chunk += s + " "
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = s + " "
            else:
                current_chunk += p + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [c for c in chunks if c.strip()]


def ensure_passage_source_ids(passages: List[Dict[str, Any]]) -> None:
    """Assign source_id on every passage: one numeric id per distinct URL (first-seen order); unique ids when URL is missing."""
    url_to_id: Dict[str, int] = {}
    next_id = 1
    for p in passages:
        url = (p.get("url") or "").strip()
        if url:
            if url not in url_to_id:
                url_to_id[url] = next_id
                next_id += 1
            p["source_id"] = url_to_id[url]
        else:
            p["source_id"] = next_id
            next_id += 1


def filter_top_evidence(passages: List[Dict[str, Any]], max_chunks: int, max_per_domain: int) -> List[Dict[str, Any]]:
    filtered = []
    doc_chunk_counts = {}
    for p in passages:
        domain = p.get("domain", "")
        if doc_chunk_counts.get(domain, 0) < max_per_domain:
            filtered.append(p)
            doc_chunk_counts[domain] = doc_chunk_counts.get(domain, 0) + 1
        if len(filtered) >= max_chunks:
            break
    if os.environ.get("PROPLEX_TRACE_EVIDENCE", "").strip().lower() in ("1", "true", "yes", "on"):
        lines: List[str] = []
        for i, p in enumerate(filtered[:10], 1):
            u = p.get("url", "") or ""
            sc = p.get("score")
            lines.append(f"  {i}. score={sc} {u[:500]}")
        logger.info(
            "filter_top_evidence: returned %d chunk(s); top 10 (order preserved, pre-author):\n%s",
            len(filtered),
            "\n".join(lines) if lines else "  (none)",
        )
    return filtered


def clean_markdown_for_snippet(text: str) -> str:
    text = re.sub(r"[#*`]", "", text)
    text = re.sub(r"\[.*?\]\(.*?\)", "", text)
    return text[:250] + "..." if len(text) > 250 else text


def anchor_query_to_topic(query: str, core_topic: str) -> str:
    """Ensure expander/component queries retain the core topic anchor (delegates to retrieval_quality)."""
    from core.retrieval_quality import (
        apply_domain_anchor_to_query,
        approved_entity_aliases,
        primary_anchor,
    )

    ct = (core_topic or "").strip()
    q0 = (query or "").strip()
    if not ct:
        return q0[:300]
    pe = ct[:200]
    aliases = approved_entity_aliases(pe, [pe], ct)
    pd = primary_anchor(pe, [pe], ct)
    out = apply_domain_anchor_to_query(q0, aliases=aliases, primary_display=pd)
    return out[:300]
