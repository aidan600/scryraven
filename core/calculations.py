from __future__ import annotations

import math
import re
from typing import Any, Callable


class CalculationError(ValueError):
    """Stable error type for deterministic calculation failures."""


def percent_change(old: float, new: float) -> float:
    if old == 0:
        raise CalculationError("percent_change_old_zero")
    return (new - old) / old


def ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        raise CalculationError("ratio_denominator_zero")
    return numerator / denominator


def difference(a: float, b: float) -> float:
    return a - b


def _require_finite_number(value: Any, error_code: str) -> float:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculationError(error_code)
    number = float(value)
    if not math.isfinite(number):
        raise CalculationError(error_code)
    return number


def normalize_per_100g(value: float, serving_grams: float) -> float:
    numeric_value = _require_finite_number(value, "normalize_per_100g_value_non_numeric")
    numeric_serving_grams = _require_finite_number(
        serving_grams,
        "normalize_per_100g_serving_grams_non_numeric",
    )
    if numeric_serving_grams <= 0:
        raise CalculationError("normalize_per_100g_serving_grams_non_positive")
    return numeric_value * 100 / numeric_serving_grams


ALLOWED_CALCULATIONS: dict[str, Callable[..., float]] = {
    "percent_change": percent_change,
    "ratio": ratio,
    "difference": difference,
    "normalize_per_100g": normalize_per_100g,
}


_REJECTED_STRINGS = {"", "n/a", "na", "tbd", "unknown", "—", "-"}
_RANGE_PATTERN = re.compile(
    r"\d\s*(?:-|–|—|\bto\b)\s*\d",
    flags=re.IGNORECASE,
)
_NUMBER_PATTERN = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)


def sanitize_to_float(value: Any) -> float:
    if value is None:
        raise ValueError("unsupported_numeric_value")
    if isinstance(value, bool):
        raise ValueError("unsupported_numeric_value")
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        raise ValueError("unsupported_numeric_value")

    text = value.strip()
    if text.casefold() in _REJECTED_STRINGS:
        raise ValueError("unsupported_numeric_value")
    if _RANGE_PATTERN.search(text):
        raise ValueError("unsupported_numeric_value")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    for prefix in ("~", "≈"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()

    if text.startswith("$"):
        text = text[1:].strip()

    percent = False
    if text.endswith("%"):
        percent = True
        text = text[:-1].strip()

    multiplier = 1.0
    if text and text[-1] in "KkMmBbTt":
        suffix = text[-1].casefold()
        multiplier = {
            "k": 1e3,
            "m": 1e6,
            "b": 1e9,
            "t": 1e12,
        }[suffix]
        text = text[:-1].strip()

    text = text.replace(",", "")
    if not _NUMBER_PATTERN.fullmatch(text):
        raise ValueError("unsupported_numeric_value")

    result = float(text) * multiplier
    if percent:
        result /= 100.0
    if negative:
        result = -result
    return result
