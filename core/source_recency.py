"""Infer coarse date signals from passage titles/snippets for author calibration (roadmap P1-6)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from core.retrieval_quality import should_merge_recency_queries

_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


def infer_year_span(passages: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    """Min/max calendar years seen in titles and excerpts (heuristic)."""
    ys: list[int] = []
    for p in passages:
        blob = f"{p.get('title', '')} {str(p.get('text', ''))[:4000]}"
        for m in _YEAR_RE.finditer(blob):
            y = int(m.group(1))
            if 1993 <= y <= 2035:
                ys.append(y)
    if not ys:
        return None, None
    return min(ys), max(ys)


def current_year_from_banner(current_date: str) -> int:
    m = _YEAR_RE.search(current_date or "")
    if m:
        return int(m.group(1))
    return datetime.now().year


def build_recency_author_notes(
    passages: list[dict[str, Any]],
    *,
    query: str,
    intent: str,
    query_type: str,
    current_date: str,
) -> tuple[str, bool]:
    """
    Returns (block to append to the author user prompt, stale_corpus flag for waste_flags).

    The model is nudged to add a one-line source time disclosure in the report when useful.
    """
    min_y, max_y = infer_year_span(passages)
    cy = current_year_from_banner(current_date)
    parts: list[str] = []
    stale = False

    if min_y is not None and max_y is not None:
        if min_y == max_y:
            parts.append(
                f"Approximate time signals in retrieved titles/snippets often reference **{min_y}** "
                f"(inferred heuristically, not exact publish dates)."
            )
        else:
            parts.append(
                f"Approximate time signals in retrieved titles/snippets span roughly **{min_y}–{max_y}** "
                "(inferred heuristically, not exact publish dates)."
            )

    wants_recency = should_merge_recency_queries(query, intent, query_type or "")
    if wants_recency and max_y is not None and max_y < cy:
        parts.append(
            f"The newest inferred year in this material ({max_y}) is **before** the current calendar year ({cy}). "
            "If the user asked for the latest developments, say briefly that sources may not reflect the very "
            "current window."
        )
        stale = True

    if not parts:
        return "", False

    block = (
        "TEMPORAL CALIBRATION (for your prose — when helpful, add **one short line** near the top on what "
        "period the retrieved material reflects; avoid labelling this as exact publication dates):\n"
        + "\n".join(f"- {p}" for p in parts)
    )
    return block, stale
