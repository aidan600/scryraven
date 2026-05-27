"""In-session duplicate-run guardrail (Phase A6): same signature within TTL → intercept."""

from __future__ import annotations

import json
from typing import Any

RUN_DEDUP_TTL_SEC = 300
SEMANTIC_DEDUP_THRESHOLD = 0.90


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na_sq = 0.0
    nb_sq = 0.0
    for x, y in zip(a, b, strict=True):
        dot += float(x) * float(y)
        na_sq += float(x) * float(x)
        nb_sq += float(y) * float(y)
    na = na_sq**0.5
    nb = nb_sq**0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def routing_key_from_full_dedup_key(full_key: str) -> str:
    payload = json.loads(full_key)
    if not isinstance(payload, dict):
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))
    slim = {k: v for k, v in payload.items() if k != "q"}
    return json.dumps(slim, sort_keys=True, separators=(",", ":"))


def normalize_query_for_dedup(query: str) -> str:
    return " ".join((query or "").strip().casefold().split())


def build_run_dedup_key(
    *,
    query: str,
    strategy: str,
    focus_academic: bool,
    force_intent_news: bool,
    provider_override: tuple[str, ...] | None,
    forced_corpus_state: str | None,
) -> str:
    pov = tuple(provider_override) if provider_override else ()
    payload = {
        "q": normalize_query_for_dedup(query),
        "strategy": str(strategy or "").strip(),
        "focus_academic": bool(focus_academic),
        "force_intent_news": bool(force_intent_news),
        "provider_override": pov,
        "forced_corpus_state": (forced_corpus_state or "").strip() or None,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def prune_dedup_cache(cache: dict[str, dict], now: float, ttl_sec: float = RUN_DEDUP_TTL_SEC) -> None:
    if not cache:
        return
    cutoff = float(now) - float(ttl_sec)
    stale = [k for k, v in cache.items() if float(v.get("ts") or 0.0) < cutoff]
    for k in stale:
        cache.pop(k, None)


def remember_run_for_dedup(
    cache: dict[str, dict],
    key: str,
    *,
    session_id: str,
    title: str,
    ts: float,
    ttl_sec: float = RUN_DEDUP_TTL_SEC,
    routing_key: str | None = None,
    query_embedding: list[float] | None = None,
) -> None:
    prune_dedup_cache(cache, ts, ttl_sec=ttl_sec)
    row: dict[str, Any] = {
        "ts": float(ts),
        "session_id": str(session_id),
        "title": str(title or "")[:200],
    }
    if routing_key is not None:
        row["routing_key"] = str(routing_key)
    if query_embedding is not None:
        row["query_embedding"] = list(query_embedding)
    cache[key] = row


def lookup_semantic_similar_run(
    cache: dict[str, dict],
    *,
    routing_key: str,
    query_embedding: list[float],
    exclude_full_key: str,
    now: float,
    ttl_sec: float = RUN_DEDUP_TTL_SEC,
    threshold: float = SEMANTIC_DEDUP_THRESHOLD,
) -> dict | None:
    if not query_embedding:
        return None
    best: dict[str, Any] | None = None
    best_sim = threshold
    cutoff = float(now) - float(ttl_sec)
    for full_key, row in cache.items():
        if full_key == exclude_full_key:
            continue
        if float(row.get("ts") or 0.0) < cutoff:
            continue
        row_rk = str(row.get("routing_key") or "").strip() or routing_key_from_full_dedup_key(full_key)
        if row_rk != routing_key:
            continue
        emb = row.get("query_embedding")
        if not isinstance(emb, list) or not emb:
            continue
        sim = cosine_similarity(query_embedding, emb)
        if sim >= best_sim:
            best_sim = sim
            best = {**row, "similarity": float(sim), "matched_key": full_key}
    return best


def lookup_recent_run(
    cache: dict[str, dict],
    key: str,
    *,
    now: float,
    ttl_sec: float = RUN_DEDUP_TTL_SEC,
) -> dict | None:
    entry = cache.get(key)
    if not entry:
        return None
    if float(now) - float(entry.get("ts") or 0.0) > float(ttl_sec):
        return None
    return entry
