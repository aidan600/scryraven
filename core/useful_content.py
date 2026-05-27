"""Deterministic post-author signal for whether the report looks substantively useful."""

from __future__ import annotations

import re

from core.review_flags import REFUSAL_PATTERNS
from core.routing import is_quantitative_query

# Currency / unit-economics style signal for quant runs (exclude bare ISO years separately).
_QUANT_NUMERIC_SIGNAL = re.compile(
    r"(?:"
    r"[\$€£]|¢|\bUSD\b|\bUS\s*\$|\bGBP\b|\bEUR\b"
    r"|%"
    r"|\d+\.\d+"
    r"|\d+\s*[–\-]\s*\d+(?:\s*(?:¢|cents?|%|USD))?"
    r"|\d+\s*/\s*\d+"
    r"|\d+(?:\s*,\s*\d{3})+(?:\.\d+)?"
    r")",
    re.I,
)
_YEAR_TOKEN = re.compile(r"\b(?:19|20)\d{2}\b")


def _has_quant_numeric_signal(text: str) -> bool:
    """True when output carries substantive numeric content beyond a bare calendar year."""
    sans_years = _YEAR_TOKEN.sub(" ", text)
    return bool(_QUANT_NUMERIC_SIGNAL.search(sans_years))


def evaluate_useful_content(
    text: str,
    *,
    query_type: str | None = None,
    report_type: str | None = None,
) -> tuple[bool, str]:
    raw = (text or "").strip()
    if not raw:
        return False, "empty_output"
    if is_quantitative_query(query_type, report_type) and not _has_quant_numeric_signal(raw):
        return False, "quant_query_missing_numeric_signal"
    words = raw.split()
    wc = len(words)
    has_link = "[[" in raw or "](http" in raw
    has_header = "\n###" in raw or raw.lstrip().startswith("###")
    has_digit = bool(re.search(r"\d", raw))

    refusal_hit = any(re.search(p, raw[:900], re.IGNORECASE) for p in REFUSAL_PATTERNS)
    has_estimate_language = bool(
        re.search(
            r"\b(model-derived|declared assumptions|approximate range|directional estimate)\b",
            raw,
            re.IGNORECASE,
        )
    )
    has_metric_table = "|" in raw and "---" in raw

    if refusal_hit and not has_estimate_language and wc <= 400 and not has_metric_table:
        return False, "refusal_without_substantive_estimate"

    if wc >= 120:
        return True, f"word_count={wc}"
    if wc >= 55 and (has_link or has_header or has_digit):
        return True, f"word_count={wc}_structured"
    if wc < 45:
        return False, f"thin_text_wc={wc}"
    if has_link or has_header:
        return True, f"word_count={wc}_structured"
    return False, f"low_substance_wc={wc}"
