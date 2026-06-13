"""Canonical technical documentation prompt/query-policy helpers.

The helpers here are deliberately small and deterministic. They do not call
providers, choose routing, choose depth, rank evidence, alter prompts, or
affect final-answer behavior.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

CANONICAL_TECHNICAL_DOC_SOURCE_CLASSES = frozenset({"primary_source_documents"})

ACADEMIC_LITERATURE_DOMAINS = frozenset(
    {
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
    }
)

_EXPLICIT_ACADEMIC_RE = re.compile(
    r"\b("
    r"academic|arxiv|bibliograph(?:y|ies)|empirical|journal|journals|"
    r"literature|papers?|peer[-\s]?reviewed|preprints?|scholarly|studies"
    r")\b",
    re.IGNORECASE,
)
_EXPLICIT_ACADEMIC_PHRASES = (
    "academic literature",
    "academic papers",
    "empirical benchmark",
    "empirical benchmarks",
    "empirical literature",
    "empirical research",
    "journal article",
    "journal articles",
    "peer reviewed",
    "peer-reviewed",
    "research literature",
    "scientific literature",
)
_DOC_TERMS = (
    "canonical",
    "docs",
    "documentation",
    "manual",
    "official",
    "reference",
)
_TECHNICAL_TERMS = (
    "api",
    "browser",
    "class",
    "concurrency",
    "configuration",
    "credentials",
    "database",
    "dataclass",
    "dataclasses",
    "fetch",
    "framework",
    "language",
    "library",
    "mode",
    "module",
    "mvcc",
    "package",
    "project",
    "protocol",
    "sdk",
    "software",
    "standard",
    "wal",
    "write-ahead",
)
_BEHAVIOR_TERMS = (
    "behavior",
    "configuration",
    "credentials",
    "handles",
    "how",
    "mode",
    "option",
    "options",
    "reference",
    "semantics",
    "tradeoff",
    "tradeoffs",
    "works",
)
_OFFICIAL_RATE_OR_RULE_RE = re.compile(
    r"\b("
    r"official|current|agency|government|legal|regulatory|rule|rules|"
    r"requirements?|rates?|fees?|thresholds?|limits?|maximum|minimum|"
    r"mileage|wage|tax|filing"
    r")\b",
    re.IGNORECASE,
)


def is_explicit_academic_literature_request(*texts: Any) -> bool:
    """Return True when the user asked for papers/literature-style evidence."""
    policy_text = _policy_text(*texts)
    if not policy_text:
        return False
    return bool(_EXPLICIT_ACADEMIC_RE.search(policy_text)) or any(
        phrase in policy_text for phrase in _EXPLICIT_ACADEMIC_PHRASES
    )


def is_academic_literature_domain_filter(domains: Iterable[Any] | None) -> bool:
    """Return True when a domain filter is only the academic-literature set."""
    normalized = _domain_set(domains)
    return bool(normalized) and normalized.issubset(ACADEMIC_LITERATURE_DOMAINS)


def is_canonical_technical_documentation_context(
    *texts: Any,
    required_source_classes: Iterable[Any] = (),
) -> bool:
    """Classify canonical technical docs requests without source-specific domains."""
    policy_text = _policy_text(*texts)
    if not policy_text:
        return False
    if is_explicit_academic_literature_request(policy_text):
        return False

    source_classes = _token_set(required_source_classes)
    has_primary_docs_obligation = bool(
        source_classes & CANONICAL_TECHNICAL_DOC_SOURCE_CLASSES
    )
    has_doc_cue = _has_any_term(policy_text, _DOC_TERMS)
    technical_terms = _matched_terms(policy_text, _TECHNICAL_TERMS)
    if technical_terms == {"standard"} and _OFFICIAL_RATE_OR_RULE_RE.search(
        policy_text
    ):
        return False
    has_technical_cue = bool(technical_terms)
    has_behavior_cue = _has_any_term(policy_text, _BEHAVIOR_TERMS)
    return bool(
        has_doc_cue
        and has_technical_cue
        and (has_behavior_cue or has_primary_docs_obligation)
    )


def _policy_text(*texts: Any) -> str:
    return " ".join(
        re.sub(r"\s+", " ", str(text or "").strip()).casefold()
        for text in texts
        if str(text or "").strip()
    )


def _has_any_term(text: str, terms: Iterable[str]) -> bool:
    padded = f" {text.replace('-', ' ')} "
    return any(f" {term.replace('-', ' ')} " in padded for term in terms)


def _matched_terms(text: str, terms: Iterable[str]) -> set[str]:
    padded = f" {text.replace('-', ' ')} "
    return {term for term in terms if f" {term.replace('-', ' ')} " in padded}


def _token_set(values: Iterable[Any] | None) -> set[str]:
    out: set[str] = set()
    if values is None:
        return out
    for item in values:
        token = re.sub(r"[^a-z0-9_]+", "_", str(item or "").casefold()).strip("_")
        if token:
            out.add(token)
    return out


def _domain_set(values: Iterable[Any] | None) -> set[str]:
    out: set[str] = set()
    if values is None:
        return out
    for item in values:
        domain = " ".join(str(item or "").strip().casefold().split())
        domain = re.sub(r"^https?://", "", domain).split("/", 1)[0].rstrip(".")
        if domain.startswith("www."):
            domain = domain[4:]
        if "." in domain and " " not in domain:
            out.add(domain)
    return out


__all__ = [
    "ACADEMIC_LITERATURE_DOMAINS",
    "CANONICAL_TECHNICAL_DOC_SOURCE_CLASSES",
    "is_academic_literature_domain_filter",
    "is_canonical_technical_documentation_context",
    "is_explicit_academic_literature_request",
]
