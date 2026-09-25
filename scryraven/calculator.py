"""Bounded exact arithmetic for the existing Answer semantic role.

The caller chooses the expression and the provenance of its numeric inputs. This
module performs only deterministic arithmetic; its results are not Evidence.
Terminating results use canonical decimals. Other results use parenthesized exact
ratios, which can be pasted into a later expression without changing precedence.
"""

from __future__ import annotations

import re
from fractions import Fraction

_NUMBER = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
_OPERATORS = frozenset("+-*/()")
_MAX_EXPRESSION_LENGTH = 4096
_MAX_TOKENS = 512
_MAX_LITERAL_LENGTH = 3072
_MAX_NESTING = 64
_MAX_RESULT_EXPONENT = 300
_MAX_COMPONENT_BITS = 2048
_MAX_OUTPUT_LENGTH = 3072
_MAX_ABSOLUTE_VALUE = 10 ** (_MAX_RESULT_EXPONENT + 1)
_MIN_ABSOLUTE_VALUE_DENOMINATOR = 10 ** _MAX_RESULT_EXPONENT


class _CalculatorError(Exception):
    def __init__(self, code: str):
        self.code = code


def _tokens(expression: str) -> list[str]:
    if not expression or len(expression) > _MAX_EXPRESSION_LENGTH:
        raise _CalculatorError("expression_too_complex" if expression else "invalid_expression")

    tokens: list[str] = []
    position = 0
    while position < len(expression):
        character = expression[position]
        if character.isspace():
            position += 1
            continue
        if character in _OPERATORS:
            tokens.append(character)
            position += 1
        else:
            number = _NUMBER.match(expression, position)
            if number is None:
                raise _CalculatorError("invalid_expression")
            literal = number.group()
            if len(literal) > _MAX_LITERAL_LENGTH:
                raise _CalculatorError("expression_too_complex")
            tokens.append(literal)
            position = number.end()
        if len(tokens) > _MAX_TOKENS:
            raise _CalculatorError("expression_too_complex")
    return tokens


def _bounded(value: Fraction) -> Fraction:
    numerator = abs(value.numerator)
    denominator = value.denominator
    if (numerator.bit_length() > _MAX_COMPONENT_BITS
            or denominator.bit_length() > _MAX_COMPONENT_BITS
            or (numerator and numerator >= denominator * _MAX_ABSOLUTE_VALUE)
            or (numerator and numerator * _MIN_ABSOLUTE_VALUE_DENOMINATOR < denominator)):
        raise _CalculatorError("result_out_of_range")
    return value


def _literal(token: str) -> Fraction:
    if "." not in token:
        return _bounded(Fraction(int(token)))
    integer, fractional = token.split(".", 1)
    digits = (integer or "0") + fractional
    return _bounded(Fraction(int(digits), 10 ** len(fractional)))


class _Parser:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.position = 0

    def _take(self, token: str) -> bool:
        if self.position < len(self.tokens) and self.tokens[self.position] == token:
            self.position += 1
            return True
        return False

    def parse(self) -> Fraction:
        value = self._expression(0)
        if self.position != len(self.tokens):
            raise _CalculatorError("invalid_expression")
        return _bounded(value)

    def _expression(self, depth: int) -> Fraction:
        value = self._term(depth)
        while self.position < len(self.tokens):
            if self._take("+"):
                value = _bounded(value + self._term(depth))
            elif self._take("-"):
                value = _bounded(value - self._term(depth))
            else:
                break
        return value

    def _term(self, depth: int) -> Fraction:
        value = self._factor(depth)
        while self.position < len(self.tokens):
            if self._take("*"):
                value = _bounded(value * self._factor(depth))
            elif self._take("/"):
                divisor = self._factor(depth)
                if not divisor:
                    raise _CalculatorError("division_by_zero")
                value = _bounded(value / divisor)
            else:
                break
        return value

    def _factor(self, depth: int) -> Fraction:
        if depth > _MAX_NESTING:
            raise _CalculatorError("expression_too_complex")
        if self._take("+"):
            return self._factor(depth + 1)
        if self._take("-"):
            return _bounded(-self._factor(depth + 1))
        if self._take("("):
            value = self._expression(depth + 1)
            if not self._take(")"):
                raise _CalculatorError("invalid_expression")
            return value
        if self.position >= len(self.tokens):
            raise _CalculatorError("invalid_expression")
        token = self.tokens[self.position]
        if _NUMBER.fullmatch(token) is None:
            raise _CalculatorError("invalid_expression")
        self.position += 1
        return _literal(token)


def _result_string(value: Fraction) -> str:
    if not value:
        return "0"
    denominator = value.denominator
    twos = 0
    fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        output = f"({value.numerator}/{value.denominator})"
    else:
        places = max(twos, fives)
        scaled = abs(value.numerator) * (10 ** places) // value.denominator
        digits = str(scaled)
        if places:
            digits = digits.zfill(places + 1)
            output = digits[:-places] + "." + digits[-places:]
            output = output.rstrip("0").rstrip(".")
        else:
            output = digits
        if value < 0:
            output = "-" + output
    if len(output) > _MAX_OUTPUT_LENGTH:
        raise _CalculatorError("result_out_of_range")
    return output


def calculate(expression: str) -> dict[str, str]:
    """Return an exact reusable value or a fixed safe error code."""
    if not isinstance(expression, str):
        return {"error": "invalid_expression"}
    try:
        tokens = _tokens(expression)
        return {"value": _result_string(_Parser(tokens).parse())}
    except _CalculatorError as error:
        return {"error": error.code}
    except (ArithmeticError, ValueError, OverflowError):
        return {"error": "result_out_of_range"}
