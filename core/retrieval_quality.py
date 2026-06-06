"""
Heuristics for source–entity match (utilization) and one-shot disambiguation retries.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

# Below this ratio of on-topic URLs, we run one disambiguation search pass; below after retry → corpus_weak.
DEFAULT_UTILIZATION_THRESHOLD = 0.25

# Below this utilization (Balanced/Deep only), author tier matches Fast-style brevity (roadmap P2-8).
VERBOSITY_GATE_UTILIZATION_THRESHOLD = 0.5


def _entity_tokens(entity: str) -> list[str]:
    s = re.sub(r"[^\w\s.-]", " ", (entity or "").lower()).strip()
    return [t for t in s.split() if len(t) >= 2]


def utilization_entity_anchor(entity: str, query_type: str = "other") -> str:
    """
    Build a compact anchor for utilization scoring.

    Long resolved phrases (common for event/current-event recon) can undercount
    utilization if we require near-full token overlap. Prefer stable anchors:
    - person: first two tokens (name-like anchor)
    - event/current_events/news with very long phrase: leading proper-name span
      when present, else first 4 tokens.
    """
    e = re.sub(r"\s+", " ", (entity or "").strip())
    if not e:
        return ""
    qt = (query_type or "other").lower()
    toks = e.split()
    if qt == "person" and len(toks) >= 2:
        return " ".join(toks[:2])
    if qt in ("event", "current_events", "news") and len(toks) > 6:
        m = re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}", e)
        if m:
            return m.group(0).strip()
        return " ".join(toks[:4])
    return e


def _entity_blob(p: dict[str, Any]) -> str:
    """Title + text, lowercased and whitespace-normalized (for substring / boundary matching)."""
    s = f"{p.get('title', '')} {p.get('text', '')}"
    return re.sub(r"\s+", " ", s).strip().lower()


def passage_mentions_entity_full_phrase(p: dict[str, Any], entity: str) -> bool:
    """
    Strict match for entity-dependent scoring: the normalized entity string must
    appear as a contiguous subsequence, not a token-OR. Case-insensitive.

    - Multi-word (or a single long token): case-insensitive substring in title+text.
    - Single short token: whole-word match (avoids substring matches inside other words).

    Use this for the embedding score floor, not for URL-level utilization (see
    passage_mentions_entity).
    """
    e = re.sub(r"\s+", " ", (entity or "").strip().lower())
    if not e:
        return True
    blob = _entity_blob(p)
    if " " in e or len(e) > 32:
        return e in blob
    if len(e) <= 2:
        return e in blob
    m = re.search(r"\b" + re.escape(e) + r"\b", blob)
    return m is not None


def passage_mentions_entity(p: dict[str, Any], entity: str) -> bool:
    """Heuristic for URL/pool utilization: may use token overlap when the full name is not quoted.

    For embedding score boosts, use passage_mentions_entity_full_phrase so unrelated
    chunks do not get boosted on shared surnames or first names only.
    """
    blob = f"{p.get('title', '')} {p.get('text', '')}".lower()
    e = (entity or "").strip()
    if not e:
        return True
    el = e.lower()
    if len(el) <= 60 and el in blob:
        return True
    toks = [t for t in _entity_tokens(e) if len(t) > 2]
    if not toks:
        return el[:20] in blob
    return sum(1 for t in toks if t in blob) >= max(1, len(toks) - 1)


def utilization_rate(passages: list[dict[str, Any]], entity: str) -> float:
    if not passages:
        return 0.0
    e = (entity or "").strip()
    if not e:
        return 1.0
    by_url: dict[str, list[dict]] = defaultdict(list)
    for p in passages:
        u = p.get("url") or ""
        if u:
            by_url[u].append(p)
    if not by_url:
        return 0.0
    urls = list(by_url.keys())[:20]
    hits = sum(1 for u in urls if any(passage_mentions_entity(x, e) for x in by_url[u]))
    return hits / max(1, len(urls))


def should_retry_retrieval(
    u: float,
    threshold: float = DEFAULT_UTILIZATION_THRESHOLD,
) -> bool:
    return u < threshold


def _extract_retry_year(current_date: str | None) -> str:
    """Extract a realistic 4-digit year (19xx/20xx) from a date-like string."""
    if not current_date:
        return ""
    m = re.search(r"\b(19\d{2}|20\d{2})\b", current_date)
    return m.group(1) if m else ""


def build_disambiguation_queries(
    user_query: str,
    core_topic: str,
    primary_entity: str,
    query_type: str,
    current_date: str,
) -> list[str]:
    """
    2 short keyword queries, max 10 words each, to disambiguate person/entity.
    No LLM: deterministic.
    """
    out: list[str] = []
    name = (primary_entity or core_topic or "").strip()[:120]
    if not name:
        return []
    qt = (query_type or "other").lower()
    year = _extract_retry_year(current_date) or "2026"

    if qt == "person":
        out.append(f'"{name}" interview podcast {year}'[:300])
        out.append(f"{name} professor business commentary"[:300])
    else:
        out.append(f'"{name}"'[:300].strip() + f" {year} news"[:200])
        out.append(f"{name} explained overview"[:300])
    if user_query and len(user_query) < 80 and user_query not in (name, name.lower()):
        q = re.sub(r"\s+", " ", user_query)[:200]
        out.append(f"{q} {name}"[:300])
    seen = set()
    uniq: list[str] = []
    for o in out:
        o2 = o.strip()[:300]
        if o2 and o2 not in seen:
            seen.add(o2)
            uniq.append(o2)
    return uniq[:2]


def should_merge_recency_queries(
    user_query: str, intent: str, query_type: str
) -> bool:
    q = (user_query or "").lower()
    hot = any(
        w in q
        for w in (
            "controversy",
            "controversies",
            "scandal",
            "breaking",
            "latest",
            "news",
            "today",
        )
    )
    return intent == "news" or (query_type or "").lower() in ("person", "news", "other") and hot


def extract_recon_context(recon_results: list[dict]) -> dict[str, Any]:
    """
    Packs reconnaissance hits into prompt-sized strings for the query rewriter.
    """
    if not recon_results:
        return {"recon_titles": "", "recon_snippets": ""}
    combined_titles = " | ".join((r.get("title") or "") for r in recon_results[:5])
    combined_snippets = " ".join((r.get("snippet") or "") for r in recon_results[:5])
    return {
        "recon_titles": combined_titles,
        "recon_snippets": combined_snippets[:800],
    }


def jaccard_similarity(queries_a: list[str], queries_b: list[str]) -> float:
    """Token Jaccard overlap between two query lists (for redundancy detection)."""
    tokens_a = set(" ".join(queries_a).lower().split())
    tokens_b = set(" ".join(queries_b).lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# --- Generic domain anchoring for retrieval queries ---------------------------------

_TOKEN_STOP = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "for",
        "in",
        "to",
        "and",
        "or",
        "is",
        "are",
        "vs",
        "on",
        "at",
        "as",
        "by",
    }
)

_OFFICIAL_BIAS_TRIGGERS = (
    "patch notes",
    "changelog",
    "release notes",
    "pricing",
    "policy",
    "official announcement",
    "upcoming patch",
)


def primary_anchor(
    primary_entity: str,
    entities_list: list[str] | None,
    core_topic: str,
) -> str:
    """
    Preferred display string for quoting and official-source-biased queries.
    """
    ent = (primary_entity or "").strip()
    if ent:
        return ent[:200]
    el = entities_list or []
    if el:
        return str(el[0]).strip()[:200]
    return (core_topic or "").strip()[:200]


def approved_entity_aliases(
    primary_entity: str,
    entities_list: list[str] | None,
    core_topic: str,
) -> list[str]:
    """Unique entity strings (order preserved) used to decide if a query is already anchored."""
    raw: list[str] = []
    for x in (primary_entity, *list(entities_list or []), core_topic):
        s = (x or "").strip()
        if s:
            raw.append(s[:200])
    out: list[str] = []
    seen: set[str] = set()
    for s in raw:
        k = s.casefold()
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


def _anchor_substantive_tokens(alias_lower: str) -> list[str]:
    """Tokens used for multi-word anchor overlap: not stopwords, length ≥4 or contains a digit."""
    toks = re.findall(r"[\w.]+", alias_lower)
    return [
        t
        for t in toks
        if t not in _TOKEN_STOP and (len(t) >= 4 or any(c.isdigit() for c in t))
    ]


def _alias_covers_query(ql: str, al: str) -> bool:
    """Whether normalized *al* counts as anchoring *ql* (full phrase, multi-word token pair, or single-token hit)."""
    if len(al) <= 2:
        return False
    is_multi = " " in al or any(c.isdigit() for c in al)
    if is_multi:
        if al in ql:
            return True
        sts = _anchor_substantive_tokens(al)
        hits = sum(1 for t in sts if re.search(r"\b" + re.escape(t) + r"\b", ql))
        return hits >= 2
    return re.search(r"\b" + re.escape(al) + r"\b", ql) is not None


def query_has_domain_anchor(
    query: str,
    aliases: list[str],
) -> bool:
    """
    True if *query* already references an approved alias: full normalized phrase, a
    whole-word single-token alias, or (for multi-word / numeric aliases) at least two
    substantive tokens from that alias. A single weak token from a multi-word name
    does not anchor unless a separate single-token alias matches (e.g. a listed short name).
    """
    if not (query or "").strip() or not aliases:
        return True
    ql = re.sub(r"\s+", " ", query.lower().strip())
    for alias in sorted({a for a in aliases if a}, key=len, reverse=True):
        al = re.sub(r"\s+", " ", alias.strip().lower())
        if _alias_covers_query(ql, al):
            return True
    return False


def secondary_terms_ambiguous(query: str, aliases: list[str]) -> bool:
    """True when the query has no domain anchor (standalone secondary/ambiguous terms)."""
    return not query_has_domain_anchor(query, aliases)


def format_quoted_anchor(anchor: str) -> str:
    """Prefer double-quoted exact anchors for multi-word or numeric product names."""
    a = re.sub(r"\s+", " ", (anchor or "").strip())
    if not a or len(a) <= 2:
        return a
    if a.startswith('"') and a.endswith('"'):
        return a
    if " " in a or re.search(r"\d", a):
        return f'"{a}"'
    return a


def apply_domain_anchor_to_query(
    query: str,
    *,
    aliases: list[str],
    primary_display: str,
) -> str:
    """Prefix *query* with the primary anchor when it lacks any approved alias."""
    q = re.sub(r"\s+", " ", (query or "").strip())
    if not q:
        return ""
    if not aliases and not (primary_display or "").strip():
        return q
    if query_has_domain_anchor(q, aliases):
        return q
    pfx_src = (primary_display or "").strip() or (aliases[0] if aliases else "")
    pfx = format_quoted_anchor(pfx_src)
    if not pfx:
        return q
    return f"{pfx} {q}".strip()


def anchored_query_variants(
    query: str,
    *,
    primary_entity: str,
    entities_list: list[str] | None,
    core_topic: str,
) -> list[str]:
    """Single-element list of the anchored variant (test / call-site helper)."""
    aliases = approved_entity_aliases(primary_entity, entities_list, core_topic)
    pd = primary_anchor(primary_entity, entities_list, core_topic)
    return [apply_domain_anchor_to_query(query, aliases=aliases, primary_display=pd)]


def wants_official_source_bias(user_query: str, intent: str) -> bool:
    u = (user_query or "").lower()
    if any(t in u for t in _OFFICIAL_BIAS_TRIGGERS):
        return True
    if re.search(r"\bpatch\b", u) and ("update" in u or "note" in u or "release" in u):
        return True
    if "price" in u or "pricing" in u:
        return True
    return False


def official_bias_phrase(user_query: str) -> str:
    u = (user_query or "").lower()
    if "policy" in u:
        return "official policy"
    if "pricing" in u or "price" in u:
        return "official pricing"
    if "announcement" in u:
        return "official announcement"
    if any(x in u for x in ("changelog", "release notes", "patch notes", "upcoming patch")) or (
        "patch" in u and ("update" in u or "note" in u)
    ):
        return "official patch notes"
    return "official"


def inject_official_source_query(
    queries: list[str],
    *,
    aliases: list[str],
    primary_display: str,
    user_query: str,
    intent: str,
    clean: Any | None = None,
) -> list[str]:
    """
    When the user asks for patches, pricing, policy, etc., ensure at least one query
    biases toward primary/official sources (keyword-only, no provider routing changes).
    """
    _clean = clean or (lambda s: re.sub(r"\s+", " ", (s or "").strip()))
    qs = [q for q in (_clean(x) for x in queries) if q]
    if not wants_official_source_bias(user_query, intent) or not (primary_display or "").strip():
        return qs
    phrase = official_bias_phrase(user_query)
    for q in qs:
        if "official" in q.lower() and query_has_domain_anchor(q, aliases):
            return qs
    pfx = format_quoted_anchor(primary_display)
    bias_q = _clean(f"{pfx} {phrase}")[:300]
    if not bias_q:
        return qs
    low = bias_q.casefold()
    if any(low == x.casefold() for x in qs) or any(low in x.casefold() for x in qs):
        return qs
    return [bias_q] + qs


def finalize_retrieval_queries(
    queries: list[str],
    *,
    primary_entity: str,
    entities_list: list[str] | None,
    core_topic: str,
    user_query: str,
    intent: str,
    clean: Any | None = None,
    include_official_bias: bool = True,
) -> list[str]:
    """
    Compatibility facade for AG-89C QueryPlan authority.

    The legacy local finalizer no longer owns query identity independently; it
    delegates deterministic finalization to ``core.query_plan`` and returns the
    authorized query text for existing callers.
    """
    from core.query_plan import authorize_retrieval_queries

    _plan, authorized = authorize_retrieval_queries(
        queries,
        primary_entity=primary_entity,
        entities_list=entities_list,
        core_topic=core_topic,
        user_query=user_query,
        intent=intent,
        clean=clean,
        include_official_bias=include_official_bias,
    )
    return authorized
