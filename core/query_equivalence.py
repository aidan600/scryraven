"""Neutral pure query cleaning and material-equivalence helpers."""

from __future__ import annotations

import re
from collections.abc import Sequence

REDUNDANT_QUERY_JACCARD_THRESHOLD = 0.7
_QUERY_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def clean_query_for_equivalence(query: str) -> str:
    """Apply the established bounded mechanical cleaning rule."""

    text = " ".join((query or "").strip().split())
    if not text:
        return ""
    words = text.split(" ")
    last = words[-1]
    if len(last) < 3 and last.isalpha() and "." not in last:
        words = words[:-1]
    return " ".join(words)[:300]


def query_token_set(queries: Sequence[str]) -> set[str]:
    return {
        token.casefold()
        for query in queries
        for token in _QUERY_TOKEN_RE.findall(clean_query_for_equivalence(query))
    }


def query_jaccard_similarity(
    queries_a: Sequence[str],
    queries_b: Sequence[str],
) -> float:
    tokens_a = query_token_set(queries_a)
    tokens_b = query_token_set(queries_b)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def queries_materially_equivalent(
    query_a: str,
    query_b: str,
    *,
    threshold: float = REDUNDANT_QUERY_JACCARD_THRESHOLD,
) -> bool:
    """Return the existing exact-or-above-threshold mechanical decision."""

    clean_a = clean_query_for_equivalence(query_a)
    clean_b = clean_query_for_equivalence(query_b)
    if not clean_a or not clean_b:
        return False
    if clean_a.casefold() == clean_b.casefold():
        return True
    return query_jaccard_similarity((clean_a,), (clean_b,)) > threshold


__all__ = [
    "REDUNDANT_QUERY_JACCARD_THRESHOLD",
    "clean_query_for_equivalence",
    "queries_materially_equivalent",
    "query_jaccard_similarity",
    "query_token_set",
]
