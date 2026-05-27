from __future__ import annotations

import pytest

from core.calculations import (
    ALLOWED_CALCULATIONS,
    difference,
    normalize_per_100g,
    percent_change,
    ratio,
    sanitize_to_float,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (100, 100.0),
        ("1,000", 1000.0),
        ("$1,000.00", 1000.0),
        ("1.5M", 1500000.0),
        ("12%", 0.12),
        ("(123.45)", -123.45),
        ("~12", 12.0),
        ("≈12", 12.0),
    ],
)
def test_sanitize_to_float_accepts_common_numeric_formats(value, expected) -> None:
    assert sanitize_to_float(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "N/A",
        "TBD",
        "12-15%",
        "1 to 2 million",
        "about a lot",
    ],
)
def test_sanitize_to_float_rejects_unsupported_or_ambiguous_values(value) -> None:
    with pytest.raises(ValueError, match="unsupported_numeric_value"):
        sanitize_to_float(value)


def test_allowed_calculation_registry_contains_only_preapproved_functions() -> None:
    assert ALLOWED_CALCULATIONS == {
        "percent_change": percent_change,
        "ratio": ratio,
        "difference": difference,
        "normalize_per_100g": normalize_per_100g,
    }


def test_allowed_calculations_compute_expected_values() -> None:
    assert percent_change(100, 150) == 0.5
    assert ratio(10, 2) == 5
    assert difference(10, 2) == 8
    assert normalize_per_100g(1.88, 10) == pytest.approx(18.8)
    assert normalize_per_100g(0.14, 10) == pytest.approx(1.4)
    assert normalize_per_100g(93, 100) == pytest.approx(93)


def test_allowed_calculations_raise_stable_zero_division_errors() -> None:
    with pytest.raises(ValueError, match="percent_change_old_zero"):
        percent_change(0, 10)

    with pytest.raises(ValueError, match="ratio_denominator_zero"):
        ratio(1, 0)


def test_normalize_per_100g_rejects_invalid_denominators() -> None:
    with pytest.raises(ValueError, match="normalize_per_100g_serving_grams_non_positive"):
        normalize_per_100g(1.88, 0)

    with pytest.raises(ValueError, match="normalize_per_100g_serving_grams_non_numeric"):
        normalize_per_100g(1.88, None)  # type: ignore[arg-type]


def test_normalize_per_100g_rejects_nonnumeric_value() -> None:
    with pytest.raises(ValueError, match="normalize_per_100g_value_non_numeric"):
        normalize_per_100g("1.88", 10)  # type: ignore[arg-type]
