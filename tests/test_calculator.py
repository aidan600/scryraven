"""The Answer calculator is arithmetic only and returns bounded machine data."""

from __future__ import annotations

import pytest

from scryraven.calculator import calculate


@pytest.mark.parametrize(("expression", "expected"), [
    ("2 + 3 * 4", "14"),
    ("(2 + 3) * 4", "20"),
    ("-(-2.5) + +.25", "2.75"),
    ("10 / 4", "2.5"),
    ("0.1 + 0.2", "0.3"),
    ("15 * 20 / 100", "3"),
    ("(5 - 5) / 3", "0"),
    ("-0.000", "0"),
])
def test_finite_decimal_arithmetic(expression, expected):
    assert calculate(expression) == {"value": expected}


def test_sequential_results_can_be_reused_as_literals():
    first = calculate("100 / 4")
    assert first == {"value": "25"}
    second = calculate(f"({first['value']} + 5) * 1.5")
    assert second == {"value": "45"}


def test_nonterminating_division_returns_exact_reusable_ratio():
    result = calculate("1 / 3")
    assert result == {"value": "(1/3)"}
    assert calculate(f"{result['value']} * 3") == {"value": "1"}
    assert calculate("(1 / 3) * 3") == {"value": "1"}


def test_repeating_ratio_is_parenthesized_for_chained_precedence():
    result = calculate("1 / 3")
    assert calculate(f"2 / {result['value']}") == {"value": "6"}
    assert calculate(f"1 + {result['value']}") == {"value": "(4/3)"}


def test_large_exact_integer_is_unchanged_by_identity_arithmetic():
    literal = "9" * 51
    assert calculate(literal) == calculate(f"{literal} + 0")


def test_exact_decimal_arithmetic_survives_chaining():
    result = calculate("0.1 + 0.2")
    assert result == {"value": "0.3"}
    assert calculate(f"{result['value']} * 10 / 3") == {"value": "1"}


@pytest.mark.parametrize("expression", [
    "__import__('os').system('whoami')",
    "(1).__class__",
    "sum([1, 2])",
    "sqrt(4)",
    "1 ** 2",
    "1e999",
    "NaN",
    "1; 2",
    "1 2",
    "1 +",
    "(1 + 2",
    "()",
    "",
])
def test_arbitrary_code_names_and_malformed_expressions_are_rejected(expression):
    assert calculate(expression) == {"error": "invalid_expression"}


@pytest.mark.parametrize("expression", ["1 / 0", "0 / (2 - 2)", "1 / -0.0"])
def test_divide_by_zero_is_contained(expression):
    assert calculate(expression) == {"error": "division_by_zero"}


def test_overlarge_or_deep_expressions_are_bounded():
    assert calculate("1 + " * 1025 + "1") == {"error": "expression_too_complex"}
    assert calculate("(" * 65 + "1" + ")" * 65) == {"error": "expression_too_complex"}
    assert calculate("1" + "0" * 301) == {"error": "result_out_of_range"}
    assert calculate("9" * 3073) == {"error": "expression_too_complex"}


def test_exact_fraction_component_growth_is_bounded():
    base = 10 ** 299
    near_one = f"({base + 1}/{base + 2})"
    assert calculate(f"{near_one} * {near_one} * {near_one}") == {
        "error": "result_out_of_range",
    }


def test_non_string_input_cannot_crash_tool():
    assert calculate(None) == {"error": "invalid_expression"}
