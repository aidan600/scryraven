"""Phase A6: deterministic run dedup key + TTL cache behavior."""

from __future__ import annotations

from core.run_dedup import (
    RUN_DEDUP_TTL_SEC,
    SEMANTIC_DEDUP_THRESHOLD,
    build_run_dedup_key,
    cosine_similarity,
    lookup_recent_run,
    lookup_semantic_similar_run,
    normalize_query_for_dedup,
    prune_dedup_cache,
    remember_run_for_dedup,
    routing_key_from_full_dedup_key,
)


def test_normalize_query_collapses_whitespace_and_case() -> None:
    assert normalize_query_for_dedup("  Foo\nBAR\tbaz  ") == "foo bar baz"


def test_build_run_dedup_key_same_inputs_same_key() -> None:
    args = dict(
        query="Same Q",
        strategy="Balanced",
        focus_academic=False,
        force_intent_news=True,
        provider_override=("exa", "tavily"),
        forced_corpus_state="mixed",
    )
    assert build_run_dedup_key(**args) == build_run_dedup_key(**args)


def test_build_run_dedup_key_provider_override_order_matters() -> None:
    """Call sites should normalize override order (e.g. sorted) before hashing."""
    base = dict(
        query="x",
        strategy="Balanced",
        focus_academic=False,
        force_intent_news=False,
        forced_corpus_state=None,
    )
    assert build_run_dedup_key(**base, provider_override=("a", "b")) != build_run_dedup_key(
        **base, provider_override=("b", "a")
    )


def test_build_run_dedup_key_differs_on_forced_state() -> None:
    base = dict(
        query="x",
        strategy="Fast",
        focus_academic=False,
        force_intent_news=False,
        provider_override=None,
    )
    assert build_run_dedup_key(**base, forced_corpus_state=None) != build_run_dedup_key(
        **base, forced_corpus_state="sparse"
    )


def test_lookup_returns_none_after_ttl() -> None:
    cache: dict[str, dict] = {}
    key = build_run_dedup_key(
        query="q",
        strategy="Balanced",
        focus_academic=False,
        force_intent_news=False,
        provider_override=None,
        forced_corpus_state=None,
    )
    t0 = 1000.0
    remember_run_for_dedup(
        cache,
        key,
        session_id="s1",
        title="t",
        ts=t0,
        ttl_sec=RUN_DEDUP_TTL_SEC,
    )
    assert lookup_recent_run(cache, key, now=t0 + 10, ttl_sec=RUN_DEDUP_TTL_SEC) is not None
    assert (
        lookup_recent_run(
            cache, key, now=t0 + RUN_DEDUP_TTL_SEC + 1, ttl_sec=RUN_DEDUP_TTL_SEC
        )
        is None
    )


def test_prune_drops_stale_entries() -> None:
    now = 2_000_000.0
    cache = {
        "a": {"ts": now - 400.0},
        "b": {"ts": now - 10.0},
    }
    prune_dedup_cache(cache, now=now, ttl_sec=300.0)
    assert "a" not in cache
    assert "b" in cache


def test_cosine_similarity_identical_orthogonal_and_guards() -> None:
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([], [1.0, 2.0]) == 0.0
    assert cosine_similarity([1.0, 2.0], []) == 0.0
    assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
    near = cosine_similarity([1.0, 1.0, 0.0], [1.0, 1.0, 0.001])
    assert 0.99 < near <= 1.0


def _key(**kw):
    base = dict(
        query="alpha",
        strategy="Balanced",
        focus_academic=False,
        force_intent_news=False,
        provider_override=None,
        forced_corpus_state=None,
    )
    base.update(kw)
    return build_run_dedup_key(**base)


def test_routing_key_equal_across_differing_q() -> None:
    k1 = _key(query="What is X?")
    k2 = _key(query="completely different prompt about Y")
    assert k1 != k2
    assert routing_key_from_full_dedup_key(k1) == routing_key_from_full_dedup_key(k2)


def test_routing_key_differs_on_routing_fields() -> None:
    k_balanced = _key(strategy="Balanced")
    k_fast = _key(strategy="Fast")
    assert routing_key_from_full_dedup_key(k_balanced) != routing_key_from_full_dedup_key(k_fast)

    k_news = _key(force_intent_news=True)
    assert routing_key_from_full_dedup_key(_key()) != routing_key_from_full_dedup_key(k_news)


def test_lookup_semantic_similar_run_match_within_threshold() -> None:
    cache: dict[str, dict] = {}
    t0 = 1000.0
    full_key_prior = _key(query="prior prompt phrasing")
    routing_only = routing_key_from_full_dedup_key(full_key_prior)
    remember_run_for_dedup(
        cache,
        full_key_prior,
        session_id="s-prior",
        title="Prior thread",
        ts=t0,
        routing_key=routing_only,
        query_embedding=[1.0, 0.0, 0.0],
    )
    full_key_new = _key(query="new prompt phrasing")
    hit = lookup_semantic_similar_run(
        cache,
        routing_key=routing_only,
        query_embedding=[1.0, 0.0, 0.0],
        exclude_full_key=full_key_new,
        now=t0 + 5.0,
    )
    assert hit is not None
    assert hit["session_id"] == "s-prior"
    assert hit["matched_key"] == full_key_prior
    assert hit["similarity"] >= SEMANTIC_DEDUP_THRESHOLD


def test_lookup_semantic_similar_run_miss_on_routing_mismatch() -> None:
    cache: dict[str, dict] = {}
    t0 = 1000.0
    full_key_prior = _key(query="prior", strategy="Fast")
    routing_other = routing_key_from_full_dedup_key(full_key_prior)
    remember_run_for_dedup(
        cache,
        full_key_prior,
        session_id="s-prior",
        title="Prior",
        ts=t0,
        routing_key=routing_other,
        query_embedding=[1.0, 0.0, 0.0],
    )
    full_key_new = _key(query="prior", strategy="Balanced")
    routing_now = routing_key_from_full_dedup_key(full_key_new)
    assert routing_now != routing_other
    hit = lookup_semantic_similar_run(
        cache,
        routing_key=routing_now,
        query_embedding=[1.0, 0.0, 0.0],
        exclude_full_key=full_key_new,
        now=t0 + 5.0,
    )
    assert hit is None


def test_lookup_semantic_similar_run_miss_after_ttl() -> None:
    cache: dict[str, dict] = {}
    t0 = 1000.0
    full_key_prior = _key(query="prior")
    routing_only = routing_key_from_full_dedup_key(full_key_prior)
    remember_run_for_dedup(
        cache,
        full_key_prior,
        session_id="s-prior",
        title="Prior",
        ts=t0,
        routing_key=routing_only,
        query_embedding=[1.0, 0.0, 0.0],
    )
    full_key_new = _key(query="new")
    hit = lookup_semantic_similar_run(
        cache,
        routing_key=routing_only,
        query_embedding=[1.0, 0.0, 0.0],
        exclude_full_key=full_key_new,
        now=t0 + RUN_DEDUP_TTL_SEC + 1,
    )
    assert hit is None


def test_lookup_semantic_similar_run_excludes_full_key() -> None:
    cache: dict[str, dict] = {}
    t0 = 1000.0
    full_key = _key(query="same prompt")
    routing_only = routing_key_from_full_dedup_key(full_key)
    remember_run_for_dedup(
        cache,
        full_key,
        session_id="s1",
        title="self",
        ts=t0,
        routing_key=routing_only,
        query_embedding=[1.0, 0.0, 0.0],
    )
    hit = lookup_semantic_similar_run(
        cache,
        routing_key=routing_only,
        query_embedding=[1.0, 0.0, 0.0],
        exclude_full_key=full_key,
        now=t0 + 5.0,
    )
    assert hit is None
