"""
Deterministic helpers for extracting search entities when the router returns none.
Pure string/regex logic — safe for Tier 1 tests (no APIs).
"""

from __future__ import annotations

import re
from collections.abc import Callable

PatternSpec = tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]]

def normalize_entity_string(raw: object, *, max_len: int = 200) -> str:
    s = re.sub(r"\s+", " ", str(raw).strip())
    return s[:max_len] if s else ""


def normalize_entities_list(raw: object, *, max_len: int = 200) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        norm = normalize_entity_string(item, max_len=max_len)
        if not norm:
            continue
        key = norm.casefold()
        if key not in seen:
            seen.add(key)
            out.append(norm)
    return out


_FALLBACK_REGISTRY: list[PatternSpec] = [
    (re.compile(r"\bScott\s+Galloway\b", re.I), "Scott Galloway"),
    (re.compile(r"\bCole\s+Tomas\s+Allen\b", re.I), "Cole Tomas Allen"),
    (re.compile(r"\bClaude\s*3\.5\s+Sonnet\b", re.I), "Claude 3.5 Sonnet"),
    (re.compile(r"\bGPT\s*-\s*4\b|\bGPT-4\b", re.I), "GPT-4"),
    (re.compile(r"\bRTX\s*(\d{4})\b", re.I), lambda m: f"RTX {m.group(1)}"),
    (re.compile(r"\bMD\s*-\s*80\b|\bMD80\b|\bMD-80\b", re.I), "MD-80"),
    (
        re.compile(r"\b777\s*-\s*300\s*(?:ER)?\b|\b777-300ER\b|\b777300\b", re.I),
        "777-300",
    ),
    (re.compile(r"\bA\s*320\s*neo\b|\bA320neo\b", re.I), "A320neo"),
    (re.compile(r"\b737\s+MAX\b|\b737MAX\b|\b737-MAX\b", re.I), "737 MAX"),
    (re.compile(r"\bASML\b"), "ASML"),
    (re.compile(r"\bBTC\b|\bBitcoin\b", re.I), "BTC"),
    (
        re.compile(r"\bDiablo\s*(?:IV|4|four)\b|\bDiablo\s*4\b", re.I),
        "Diablo 4",
    ),
]


def _looks_like_vague_advice_question(q: str, q_lower: str) -> bool:
    if not q_lower.endswith("?"):
        return False
    if len(q) > 120:
        return False
    markers = (
        "good idea",
        "should i",
        "what do you think",
        "is it worth",
        "this a good",
        "any thoughts",
        "ideas?",
        "bad idea",
    )
    return any(m in q_lower for m in markers)


def fallback_entities_from_query(query: str) -> list[str]:
    """
    Best-effort entity extraction without an LLM. Order-preserving unique list.
    Intentionally returns [] for vague prompts like \"is this a good idea?\"
    """
    q = " ".join((query or "").strip().split())
    if not q:
        return []

    q_lower = q.lower()
    entities: list[str] = []
    seen: set[str] = set()
    spans: list[tuple[int, int, str]] = []

    for pat, repl in _FALLBACK_REGISTRY:
        for m in pat.finditer(q):
            if callable(repl):
                label = normalize_entity_string(repl(m))
            else:
                label = normalize_entity_string(repl)
            if label:
                spans.append((m.start(), m.end(), label))

    # Left-to-right, prefer longer span at the same start (overlap conflicts).
    spans.sort(key=lambda t: (t[0], -(t[1] - t[0])))

    occupied: list[tuple[int, int]] = []

    def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return not (a[1] <= b[0] or b[1] <= a[0])

    for start, end, label in spans:
        rng = (start, end)
        if any(_overlaps(rng, oc) for oc in occupied):
            continue
        key = label.casefold()
        if key not in seen:
            seen.add(key)
            entities.append(label[:200])
        occupied.append(rng)

    # Gamer shorthand "d4 difficulty" → allow D4 alongside Diablo mentions
    if re.search(r"\bd4\b", q_lower) and any(
        w in q_lower for w in ("diablo", "level", "difficulty", "tier", "world")
    ):
        if "d4".casefold() not in seen:
            entities.insert(0, "D4")
            seen.add("d4".casefold())

    if not entities and _looks_like_vague_advice_question(q, q_lower):
        return []

    return entities
