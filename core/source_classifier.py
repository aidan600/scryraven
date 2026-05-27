"""Heuristic source tier labels for retrieved URLs (conservative; extensible rule lists).

Not wired into ranking or filtering yet — classification only.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

# --- Extensible rule lists (append domains/patterns as needed) ---

# Company, standards body, or primary project web properties (not social hosts).
OFFICIAL_DOMAINS: tuple[str, ...] = (
    "python.org",
    "rust-lang.org",
    "golang.org",
    "kubernetes.io",
    "mozilla.org",
    "apache.org",
    "openjdk.org",
    "gnu.org",
    "eclipse.org",
    "ietf.org",
    "w3.org",
    "unicode.org",
    "microsoft.com",
    "apple.com",
    "oracle.com",
    "tesla.com",
)

# High-confidence government domains. A bare ``gov`` entry intentionally
# matches only ``*.gov`` host suffixes via _host_suffix_matches.
OFFICIAL_GOVERNMENT_DOMAINS: tuple[str, ...] = (
    "gov",
)

# High-precision financial official/official-like source surfaces.
FINANCIAL_REGULATOR_DOMAINS: tuple[str, ...] = (
    "sec.gov",
)

# Secondary archives/CDNs are only official-like when the page/report context
# looks like issuer financial reporting. Do not generalize this to all CDNs.
OFFICIAL_FINANCIAL_ARCHIVE_DOMAINS: tuple[str, ...] = (
    "annualreports.com",
)

INVESTOR_REPORT_CDN_DOMAINS: tuple[str, ...] = (
    "q4cdn.com",
)

INVESTOR_RELATIONS_SUBDOMAIN_LABELS: tuple[str, ...] = (
    "investor",
    "investors",
    "ir",
)

OFFICIAL_FINANCIAL_CONTEXT_PATTERNS: tuple[str, ...] = (
    r"\bsec[-_\s]?filings?\b",
    r"\bform[-_\s]+(?:10[-_\s]?k|10[-_\s]?q|8[-_\s]?k|20[-_\s]?f|40[-_\s]?f)\b",
    r"\b(?:10[-_\s]?k|10[-_\s]?q|8[-_\s]?k|20[-_\s]?f|40[-_\s]?f)\b",
    r"\bannual[-_\s]?reports?\b",
    r"\bquarterly[-_\s]+(?:reports?|results?|earnings)\b",
    r"\bearnings[-_\s]+(?:release|results?|presentation)\b",
    r"\binvestor[-_\s]+relations?\b",
    r"\bproxy[-_\s]+statement\b",
    r"\bfinancial[-_\s]+(?:results?|statements?|reports?)\b",
    r"\bdoc[-_]?financials\b",
)

# Typical UGC / discussion surfaces (signal-only; not treated as official).
SOCIAL_OR_FORUM_DOMAINS: tuple[str, ...] = (
    "reddit.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "discord.com",
    "discord.gg",
    "tumblr.com",
    "pinterest.com",
    "snapchat.com",
    "threads.net",
    "bluesky.social",
    "quora.com",
)

# Reference, Q&A, wikis, and common open-source collaboration hosts.
TRUSTED_COMMUNITY_DOMAINS: tuple[str, ...] = (
    "wikipedia.org",
    "wiktionary.org",
    "stackoverflow.com",
    "stackexchange.com",
    "wiki.gg",
    "fandom.com",
    "pcgamingwiki.com",
    "liquipedia.net",
    "github.com",
    "gitlab.com",
    "sr.ht",
)

# Named reputable news, scientific, and policy/research sources. These are
# useful diagnostics, but they are not official/primary evidence.
SECONDARY_DOMAINS: tuple[str, ...] = (
    "apnews.com",
    "arxiv.org",
    "cbsnews.com",
    "nature.com",
    "ncbi.nlm.nih.gov",
    "politico.com",
    "theicct.org",
)

# Match against the full URL string (lowercased). Prefer high-precision phrases.
LOW_TRUST_COMMERCIAL_PATTERNS: tuple[str, ...] = (
    r"buy[-_\s]+(?:in[-_]?game|digital)[-_\s]+(?:currency|gold|coins)",
    r"sell(?:ing)?[-_\s]+(?:in[-_]?game|digital)[-_\s]+(?:currency|gold|coins)",
    r"\brmt\b",
    r"real[-_\s]?money[-_\s]?trad(?:e|ing)",
    r"(?:power|account)[-_\s]?level(?:ling)?[-_\s]?(?:boost|service)",
    r"boost(?:ing)?[-_\s]?(?:service|offer)",
    r"(?:cheap|discount)[-_\s]+(?:boost|carry|currency)",
    r"playerauctions",
    r"igvault",
    r"g2g\.com",
    r"mmogah",
    r"mmoshop",
)

# Match against lowercase title + snippet only (not hostname).
CONTENT_MILL_PATTERNS: tuple[str, ...] = (
    r"everything you need to know",
    r"\bultimate guide to\b",
    r"affiliate disclosure",
    r"\bsponsored content\b",
    r"you won'?t believe",
    r"\b(?:one )?weird trick\b",
)


def normalize_source_domain(url: str) -> str:
    """Return a normalized hostname for passive source-domain telemetry."""
    if not (url or "").strip():
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def _normalize_host(url: str) -> str:
    return normalize_source_domain(url)


def _host_suffix_matches(host: str, domain: str) -> bool:
    d = domain.lower().lstrip(".")
    if not host or not d:
        return False
    return host == d or host.endswith("." + d)


def _host_in_list(host: str, domains: tuple[str, ...]) -> bool:
    return any(_host_suffix_matches(host, d) for d in domains)


@lru_cache(maxsize=1)
def _compiled(patterns: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    if not text.strip():
        return False
    for rx in _compiled(patterns):
        if rx.search(text):
            return True
    return False


def _domain_anchor_tokens(anchor: str) -> set[str]:
    stop = {
        "and",
        "for",
        "inc",
        "llc",
        "ltd",
        "the",
        "with",
    }
    return {
        t
        for t in re.findall(r"[a-z0-9]+", (anchor or "").lower())
        if len(t) >= 3 and t not in stop
    }


def _first_host_label(host: str) -> str:
    labels = [part for part in (host or "").split(".") if part]
    return labels[0] if labels else ""


def _host_matches_source_context(host: str, source_context: str) -> bool:
    anchor_tokens = _domain_anchor_tokens(source_context)
    if not host or not anchor_tokens:
        return False
    compact = re.sub(r"[^a-z0-9]+", "", host.lower())
    return any(token in compact for token in anchor_tokens)


def _has_official_financial_context(url: str, title: str, snippet: str) -> bool:
    text = f"{url} {title} {snippet}".strip().lower()
    return _matches_any(text, OFFICIAL_FINANCIAL_CONTEXT_PATTERNS)


def _is_official_financial_source(
    host: str,
    url: str,
    title: str,
    snippet: str,
    source_context: str,
) -> bool:
    if _host_in_list(host, FINANCIAL_REGULATOR_DOMAINS):
        return True

    has_reporting_context = _has_official_financial_context(url, title, snippet)
    if not has_reporting_context:
        return False

    if _host_in_list(host, OFFICIAL_FINANCIAL_ARCHIVE_DOMAINS):
        return True
    if _host_in_list(host, INVESTOR_REPORT_CDN_DOMAINS):
        return True

    if (
        _first_host_label(host) in INVESTOR_RELATIONS_SUBDOMAIN_LABELS
        and _host_matches_source_context(host, source_context)
    ):
        return True

    return False


def classify_source(
    url: str,
    title: str = "",
    snippet: str = "",
    *,
    source_context: str = "",
) -> str:
    """Return a coarse source tier for a candidate page.

    Conservative: when in doubt, returns ``unknown``. Hostname rules take
    precedence over title/snippet heuristics.
    """
    url_s = (url or "").strip()
    host = _normalize_host(url_s)

    if host:
        if _host_in_list(host, SOCIAL_OR_FORUM_DOMAINS):
            return "social_or_forum"
        if _host_in_list(host, OFFICIAL_DOMAINS):
            return "official"
        if _is_official_financial_source(host, url_s, title, snippet, source_context):
            return "official"
        if _host_in_list(host, TRUSTED_COMMUNITY_DOMAINS):
            return "trusted_community"
        if _host_in_list(host, SECONDARY_DOMAINS):
            return "secondary"
        if _host_in_list(host, OFFICIAL_GOVERNMENT_DOMAINS):
            return "official"

    url_lower = url_s.lower()
    if url_lower and _matches_any(url_lower, LOW_TRUST_COMMERCIAL_PATTERNS):
        return "low_trust_commercial"

    text = f"{title} {snippet}".strip().lower()
    if text and _matches_any(text, CONTENT_MILL_PATTERNS):
        return "content_mill"

    return "unknown"


def source_tier_telemetry(passages: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate tier histogram and boolean flags from passage dicts (``source_tier`` key).

    Intended for execution_trace / JSONL; does not filter or rank passages.
    """
    counts: dict[str, int] = {}
    for p in passages:
        tier = (p.get("source_tier") or "unknown").strip() or "unknown"
        counts[tier] = counts.get(tier, 0) + 1
    return {
        "source_tier_counts": counts,
        "official_evidence_found": counts.get("official", 0) > 0,
        "community_signal_found": (counts.get("trusted_community", 0) + counts.get("social_or_forum", 0)) > 0,
        "low_trust_sources_found": counts.get("low_trust_commercial", 0) > 0,
        "pollution_detected": counts.get("content_mill", 0) > 0,
    }


def source_domain_telemetry(
    passages: list[dict[str, Any]],
    *,
    domain_anchor: str = "",
    top_n: int = 10,
) -> dict[str, Any]:
    """Aggregate passive source-domain diagnostics from retrieved passage URLs.

    This is observability only: it does not filter, rank, or classify sources.
    """
    counts: dict[str, int] = {}
    for p in passages:
        domain = normalize_source_domain(str(p.get("url") or "")) or "unknown"
        counts[domain] = counts.get(domain, 0) + 1

    top = [
        {"domain": domain, "count": count}
        for domain, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top_n]
    ]

    anchor_tokens = _domain_anchor_tokens(domain_anchor)
    on_domain = 0
    off_domain = 0
    if anchor_tokens:
        for domain, count in counts.items():
            compact = re.sub(r"[^a-z0-9]+", "", domain.lower())
            token_hit = any(token in compact for token in anchor_tokens)
            if token_hit:
                on_domain += count
            elif domain != "unknown":
                off_domain += count

    return {
        "source_domain_counts": counts,
        "top_source_domains": top,
        "unique_source_domain_count": len(counts),
        "on_domain_source_count": on_domain,
        "off_domain_source_count": off_domain,
    }
