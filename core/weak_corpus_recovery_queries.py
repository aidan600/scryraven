"""Deterministic weak-corpus recovery query seed construction."""

from __future__ import annotations

import re

from core.retrieval_quality import (
    format_quoted_anchor,
    official_bias_phrase,
    wants_official_source_bias,
)


def clean_query(q: str) -> str:
    """Normalize query text and drop likely trailing token truncation."""
    q2 = " ".join((q or "").strip().split())
    if not q2:
        return ""
    words = q2.split(" ")
    last = words[-1]
    if len(last) < 3 and last.isalpha() and "." not in last:
        words = words[:-1]
    return " ".join(words)[:300]


def extract_year(text: str) -> str:
    match = re.search(r"\b(19|20)\d{2}\b", text or "")
    return match.group(0) if match else "2026"


def weak_corpus_recovery_seed_queries(
    *,
    user_query: str,
    core_topic: str,
    primary_entity: str,
    canonical_subject: str | None,
    current_date: str,
    previous_queries: list[str] | None = None,
) -> list[str]:
    """Small deterministic query seed set for one bounded weak-corpus recovery pass."""
    anchor = (canonical_subject or primary_entity or core_topic or "").strip()
    uq = clean_query(user_query)
    topic = clean_query(core_topic)
    year = extract_year(current_date)
    anchor_tokens = set(re.findall(r"[a-z0-9]+", anchor.casefold()))
    stop = set(
        "about after and are before does expected find for give have into "
        "latest need show tell that the their there these this what when where "
        "which with".split()
    )

    def _intent_terms(*texts: str, cap: int = 6) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for text in texts:
            for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9.-]*", text or ""):
                key = tok.casefold().strip(".-")
                if len(key) < 3 or key in stop or key in anchor_tokens or key in seen:
                    continue
                seen.add(key)
                out.append(tok.strip(".-"))
                if len(out) >= cap:
                    return out
        return out

    def _sig(q: str) -> set[str]:
        return {
            t
            for t in re.findall(r"[a-z0-9]+", (q or "").casefold())
            if len(t) >= 3 and t not in stop
        }

    previous_sigs = [_sig(q) for q in (previous_queries or []) if q]

    def _is_near_previous(q: str) -> bool:
        sig = _sig(q)
        if not sig:
            return False
        for prev in previous_sigs:
            if not prev:
                continue
            overlap = len(sig & prev) / max(1, len(sig))
            if (sig == prev) or (overlap >= 0.85 and len(sig) <= len(prev) + 1):
                return True
        return False

    terms = _intent_terms(uq, topic)
    term_tail = " ".join(terms)
    compact_tail = " ".join(terms[:4])
    quoted_anchor = format_quoted_anchor(anchor)
    raw: list[str] = []

    if anchor and compact_tail:
        raw.append(f"{quoted_anchor} \"{compact_tail}\"")
    if anchor and wants_official_source_bias(user_query, "general"):
        phrase = official_bias_phrase(user_query)
        raw.append(f"{quoted_anchor} {phrase} {compact_tail}".strip())
    if anchor and term_tail:
        raw.append(f"{quoted_anchor} {term_tail}")
    if anchor and topic and topic.casefold() != anchor.casefold():
        raw.append(f"{quoted_anchor} {topic}")
    if anchor and term_tail and year:
        raw.append(f"{quoted_anchor} {term_tail} {year}")
    if not anchor and uq:
        raw.append(uq)

    seen: set[str] = set()
    seen_signatures: set[frozenset[str]] = set()
    out: list[str] = []
    for q in raw:
        q2 = clean_query(q)
        key = q2.casefold()
        sig = frozenset(_sig(q2))
        if q2 and key not in seen and sig not in seen_signatures and not _is_near_previous(q2):
            seen.add(key)
            seen_signatures.add(sig)
            out.append(q2)
    return out[:4]
