"""Claim-scoped quantitative authority for every final-answer prose route.

This module projects only authority already present in a FinalAnswerPacket (or
its hardened compatibility form) and validates candidate prose deterministically.
It does not calculate, convert, admit claims, interpret evidence, or call a
model.  Assertion binding is intentionally conservative: the complete bounded
assertion fingerprint, not merely a numeric value/unit pair, must match.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.quantitative_specialist_product_activation import (
    QUANTITATIVE_CAPABILITY_ID,
    QUANTITATIVE_CAPABILITY_VERSION,
    QuantitativeSpecialistProductError,
    parse_source_bound_numeric_literal,
)

QUANTITATIVE_FINALIZATION_AUTHORITY_MANIFEST_SCHEMA_VERSION = (
    "quantitative_finalization_authority_manifest_v1"
)
QUANTITATIVE_FINALIZATION_VALIDATION_SCHEMA_VERSION = (
    "quantitative_finalization_validation_v1"
)
QUANTITATIVE_FINALIZATION_PARSER_VERSION = (
    "claim_scoped_quantitative_finalization_parser_v2"
)

_PROHIBITED_TRANSFORMATIONS = (
    "calculation",
    "conversion",
    "estimation",
    "interpolation",
    "unsupported_rounding",
    "rescaling",
    "ratio_or_rate_creation",
    "percentage_or_basis_point_creation",
    "aggregation",
    "new_comparison_magnitude",
    "subject_or_metric_substitution",
)
_SCALE_FACTORS = {
    "thousand": Decimal("1000"),
    "million": Decimal("1000000"),
    "billion": Decimal("1000000000"),
    "trillion": Decimal("1000000000000"),
}
_CARDINAL_VALUES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_ORDINAL_VALUES = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}
_TEXT_SCALE_VALUES = {
    "hundred": 100,
    "thousand": 1000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    "trillion": 1_000_000_000_000,
}
_UNBOUNDED_QUANTIFIER_WORDS = frozenset(
    {
        "couple",
        "dozen",
        "double",
        "twice",
        "triple",
        "thrice",
        "half",
        "quarter",
        "third",
        "fold",
    }
)
_UNIT_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "being",
        "but",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "of",
        "on",
        "or",
        "than",
        "that",
        "the",
        "then",
        "to",
        "was",
        "were",
        "which",
        "with",
    }
)
_COMPACT_CURRENCY_CODES = frozenset(
    {
        "AED",
        "AUD",
        "BRL",
        "CAD",
        "CHF",
        "CNY",
        "DKK",
        "EUR",
        "GBP",
        "HKD",
        "INR",
        "JPY",
        "KRW",
        "MXN",
        "NOK",
        "NZD",
        "PLN",
        "SEK",
        "SGD",
        "USD",
        "ZAR",
    }
)
_MACHINE_CITATION_RE = re.compile(
    r"(?:\[\s*\d+(?:\s*[-,]\s*\d+)*\s*\]|【[^】]{1,120}】)"
)
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]{0,300})\]\((?:https?://|www\.)[^)]+\)")
_BARE_URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
_HTML_TAG_RE = re.compile(r"<[^>]{1,200}>")
_DIGEST_CONTEXT_RE = re.compile(
    r"(?i)\b(?:sha(?:-?\d+)?|digest|hash)(?:"
    r"\s*[:=]\s*[0-9a-f]{8,128}\b|\s*\(\s*[0-9a-f]{8,128}\s*\))"
)
_DIGEST_PAREN_RE = re.compile(
    r"\(\s*(?=[0-9a-fA-F]{8,64}\s*\))(?=[0-9a-fA-F]*[a-fA-F])"
    r"[0-9a-fA-F]{8,64}\s*\)"
)
_ALPHANUMERIC_TRANSPORT_ID_RE = re.compile(
    r"(?i)\b(?=[a-z][a-z0-9_.:\-/]*\b)(?=[a-z0-9_.:\-/]*\d)"
    r"[a-z][a-z0-9_.:\-/]*\b"
)
_DIGIT_LITERAL_RE = re.compile(
    r"""
    (?P<qualifier>(?i:approximately|approx\.?|about|around|roughly|rounded)\s+)?
    (?P<sign>[+\-\u2212])?\s*
    (?:(?P<currency_code>[A-Z]{3})\s+|(?P<compact_currency_code>[A-Z]{3})(?=\d)|(?P<currency_symbol>[$€£¥])\s*)?
    (?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)
    (?P<exponent>[eE][+\-]?\d+)?
    (?:\s+(?P<scale>(?i:thousand|million|billion|trillion)))?
    (?P<percent>\s*%)?
    (?:\s+(?P<unit>(?i:basis\s+points?|percentage\s+points?|bps|percent|percentage|[A-Za-zµ°][A-Za-z0-9µ°_-]{0,31}(?:[/*][A-Za-zµ°][A-Za-z0-9µ°_-]{0,31})*|per\s+[A-Za-zµ°][A-Za-z0-9µ°_-]{0,31})))?
    """,
    re.VERBOSE,
)
_WORD_TOKEN_RE = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)?")
_UNSUPPORTED_NUMERIC_SURFACE_RE = re.compile(
    r"(?P<digit_ordinal>(?<![A-Za-z0-9_])\d+(?:st|nd|rd|th)\b)"
    r"|(?P<unicode_fraction>[\u00bc-\u00be\u2150-\u215e])"
    r"|(?P<fullwidth_digits>[\uff10-\uff19]+(?:\uff0e[\uff10-\uff19]+)?)"
)
_NUMERIC_GLYPH_RE = re.compile(r"[0-9\u00bc-\u00be\u2150-\u215e\uff10-\uff19]+")
_TRANSPORT_SECTION_HEADING_RE = re.compile(
    r"(?i)^\s*(?:support\s+refs?|source\s+refs?|sources?|citations?)\s*:\s*"
)
_TRANSPORT_SECTION_ASSERTION_CUE_RE = re.compile(
    r"(?i)(?:\b(?:is|are|was|were|has|have|had|reports|reported|states|stated|"
    r"reached|costs?|totals?|equals?|amounts?)\b|^[^:\n]{1,120}:\s*\S)"
)
_TRANSPORT_REFERENCE_ONLY_HINT_RE = re.compile(
    r"(?i)\b(?:source|reference|citation|report|memo|document|publication)\b"
)
_MARKDOWN_LIST_MARKER_RE = re.compile(r"^\s*[-*+]\s+")
_NUMERIC_LIST_MARKER_RE = re.compile(r"^\s*(?P<ordinal>\d+)[.)]\s+")
_MAX_STRUCTURAL_LIST_ORDINAL = 20
_QUANTITATIVE_VALUE_LEAD_RE = re.compile(
    r"(?i)^(?:[$€£¥%]|[a-zµ°][a-z0-9µ°_-]{0,31}\s+"
    r"(?:is|are|was|were|equals?|amounts?|costs?|totals?))\b"
)
_SAFE_REF_EXACT_KEYS = frozenset(
    {
        "available",
        "canonical_unit",
        "claim_scoped",
        "component_revision",
        "current",
        "entry_kind",
        "execution_posture",
        "normalized_numeric_value_text",
        "owner",
        "precision_posture",
        "role",
        "route",
        "selected_occurrence",
        "sequence",
        "stage",
        "stale",
        "target_kind",
        "target_revision",
    }
)
_SAFE_REF_KEY_SUFFIXES = (
    "_allowed",
    "_available",
    "_complete",
    "_count",
    "_digest",
    "_id",
    "_index",
    "_key",
    "_kind",
    "_ordinal",
    "_posture",
    "_ref",
    "_refs",
    "_route",
    "_status",
    "_version",
)
_AUTHORITY_KINDS = frozenset(
    {
        "direct_source_numeric",
        "specialist_derived_numeric",
    }
)
_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "source_fap_ref",
        "authorized_numeric_claims",
        "prohibited_transformations",
        "claim_scoped",
        "value_only_matching_prohibited",
        "calculation_performed",
        "conversion_performed",
        "claim_admission_performed",
        "sufficiency_changed",
        "manifest_digest",
    }
)
_AUTHORIZED_CLAIM_FIELDS = frozenset(
    {
        "local_claim_key",
        "claim_literal_ordinal",
        "current_claim_ref",
        "claim_authority_posture",
        "authority_kind",
        "normalized_numeric_value_text",
        "canonical_unit",
        "precision_posture",
        "evidence_or_specialist_ref",
        "applicable_dprime_ref",
        "applicable_dprime_consumption_ref",
        "admitted_claim_ref",
        "fap_material_ref",
        "semantic_claim_fingerprint_or_existing_equivalent",
        "literal_signature_digest",
    }
)
_AUTHORIZED_CLAIM_REF_FIELDS = (
    "current_claim_ref",
    "evidence_or_specialist_ref",
    "applicable_dprime_ref",
    "applicable_dprime_consumption_ref",
    "admitted_claim_ref",
    "fap_material_ref",
)


class QuantitativeFinalizationAuthorityError(ValueError):
    """Raised when candidate final prose cannot bind to current FAP authority."""

    def __init__(self, reason: str, *, diagnostic: Mapping[str, Any]) -> None:
        reason_refs = _mapping_sequence(diagnostic.get("reason_refs"))
        bounded_reasons = ",".join(
            f"{item.get('assertion_index', '?')}:{item.get('reason_code', 'rejected')}"
            for item in reason_refs[:10]
        )
        super().__init__(f"{reason} [{bounded_reasons}]" if bounded_reasons else reason)
        self.reason = reason
        self.diagnostic = dict(diagnostic)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_sequence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _clean_text(value: Any, *, limit: int = 2000) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())[:limit]


def _safe_ref_key(value: Any) -> str | None:
    key = str(value or "").strip()[:100]
    normalized = key.casefold()
    if not key or not (
        normalized in _SAFE_REF_EXACT_KEYS
        or normalized.endswith(_SAFE_REF_KEY_SUFFIXES)
    ):
        return None
    return key


def _safe_ref_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[bounded]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return value[:240]
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            clean_key = _safe_ref_key(key)
            if clean_key:
                safe_item = _safe_ref_value(item, depth=depth + 1)
                if safe_item not in (None, "", [], {}):
                    result[clean_key] = safe_item
        return result
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_safe_ref_value(item, depth=depth + 1) for item in value[:40]]
    return str(value)[:240]


def _safe_ref(value: Any) -> dict[str, Any]:
    safe = _safe_ref_value(_mapping(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _safe_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[bounded]"
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _safe_value(item, depth=depth + 1)
            for key, item in value.items()
            if str(key).casefold()
            not in {
                "prompt",
                "raw_prompt",
                "raw_text",
                "bounded_text",
                "source_text",
                "model_response",
                "provider_payload",
                "raw_provider_payload",
                "full_trace",
                "private_log",
                "api_key",
                "secret",
            }
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_safe_value(item, depth=depth + 1) for item in value[:40]]
    return str(value)[:240]


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(
            _safe_value(value),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _text_digest(value: str) -> str:
    return sha256(str(value or "").encode("utf-8")).hexdigest()


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _strip_machine_citation(match: re.Match[str]) -> str:
    token = match.group(0)
    if token.startswith("["):
        prefix = match.string[max(0, match.start() - 48) : match.start()]
        tail = match.string[match.end() : match.end() + 48]
        proposition_prefix = re.search(
            r"(?i)\b(?:is|are|was|were|equals?)\s*$",
            prefix,
        )
        proposition_unit = re.match(
            r"(?i)^\s*(?:%|basis\s+points?|percentage\s+points?|bps|percent|"
            r"km|kilometers?|m|meters?|miles?|kg|kilograms?|g|grams?|"
            r"usd|eur|gbp|jpy|cad|aud|chf|cny)\b",
            tail,
        )
        if proposition_prefix or proposition_unit:
            return f" {token[1:-1].strip()} "
    return " "


def _strip_alphanumeric_transport_id(match: re.Match[str]) -> str:
    token = match.group(0)
    compact_currency = re.fullmatch(r"([A-Z]{3})\d+(?:\.\d+)?", token)
    if compact_currency and compact_currency.group(1) in _COMPACT_CURRENCY_CODES:
        return token
    return " "


def _strip_nonprose_transport(text: str) -> str:
    value = str(text or "")
    value = _MARKDOWN_LINK_RE.sub(r"\1", value)
    value = _BARE_URL_RE.sub(" ", value)
    value = _MACHINE_CITATION_RE.sub(_strip_machine_citation, value)
    value = _HTML_TAG_RE.sub(" ", value)
    value = _DIGEST_CONTEXT_RE.sub(" ", value)
    value = _DIGEST_PAREN_RE.sub(" ", value)
    value = _ALPHANUMERIC_TRANSPORT_ID_RE.sub(
        _strip_alphanumeric_transport_id,
        value,
    )
    value = re.sub(r"\s+([.!?;])", r"\1", value)
    return value


def _strip_assertion_list_marker(line: str) -> tuple[str, bool]:
    markdown = _MARKDOWN_LIST_MARKER_RE.match(line)
    if markdown:
        return line[markdown.end() :], True
    numeric = _NUMERIC_LIST_MARKER_RE.match(line)
    if not numeric:
        return line, False
    remainder = line[numeric.end() :]
    if (
        int(numeric.group("ordinal")) > _MAX_STRUCTURAL_LIST_ORDINAL
        or _QUANTITATIVE_VALUE_LEAD_RE.match(remainder)
    ):
        return f"{numeric.group('ordinal')} {remainder}", False
    return remainder, True


def _assertions(text: str) -> list[str]:
    prose = _strip_nonprose_transport(text)
    out: list[str] = []
    paragraph_parts: list[str] = []
    in_transport_section = False

    def flush_paragraph() -> None:
        if not paragraph_parts:
            return
        paragraph = " ".join(paragraph_parts)
        paragraph_parts.clear()
        for part in re.split(
            r"(?<=[!?;])\s+|\.(?:\s+|$)",
            paragraph,
        ):
            cleaned = _clean_text(part, limit=2000)
            if cleaned:
                out.append(cleaned)

    for raw_line in prose.splitlines() or [prose]:
        line = re.sub(r"^\s*#{1,6}\s*", "", raw_line)
        line, list_item = _strip_assertion_list_marker(line)
        heading = _TRANSPORT_SECTION_HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            line = line[heading.end() :]
            in_transport_section = True
        if not line.strip():
            flush_paragraph()
            if not heading:
                in_transport_section = False
            continue
        if (
            in_transport_section
            and _TRANSPORT_REFERENCE_ONLY_HINT_RE.search(line)
            and not _TRANSPORT_SECTION_ASSERTION_CUE_RE.search(line)
        ):
            if list_item:
                flush_paragraph()
            continue
        if list_item:
            flush_paragraph()
        paragraph_parts.append(line.strip())
        if list_item:
            flush_paragraph()
    flush_paragraph()
    return out


def _currency_code(match: re.Match[str]) -> str:
    return str(
        match.group("currency_code") or match.group("compact_currency_code") or ""
    )


def _unit_text(match: re.Match[str]) -> tuple[str | None, int]:
    percent = match.group("percent")
    unit = _clean_text(match.group("unit"), limit=80)
    if percent:
        return "percent", match.end("percent")
    if not unit:
        currency = _currency_code(match) or match.group("currency_symbol")
        return (str(currency) if currency else None), match.end("scale") if match.group("scale") else match.end("number")
    normalized = (
        unit.upper()
        if len(unit) == 3 and unit.isalpha() and unit.isupper()
        else unit.casefold().replace(" ", "_")
    )
    if normalized in _UNIT_STOPWORDS:
        return None, match.end("scale") if match.group("scale") else match.end("number")
    if normalized in {"percent", "percentage"}:
        normalized = "percent"
    elif normalized in {"basis_point", "basis_points", "bps"}:
        normalized = "basis_points"
    elif normalized in {"percentage_point", "percentage_points"}:
        normalized = "percentage_points"
    elif normalized.startswith("per_"):
        normalized = "/" + normalized.removeprefix("per_")
    return normalized, match.end("unit")


def _digit_literal(match: re.Match[str]) -> dict[str, Any] | None:
    number = str(match.group("number") or "")
    exponent = str(match.group("exponent") or "")
    scale = str(match.group("scale") or "unit_scale").casefold()
    qualifier = str(match.group("qualifier") or "").strip().rstrip(".").casefold()
    sign = str(match.group("sign") or "")
    currency_code = _currency_code(match)
    if match.group("compact_currency_code") and currency_code not in _COMPACT_CURRENCY_CODES:
        return None
    unit, span_end = _unit_text(match)
    numeric_source = number.replace(",", "") + exponent
    try:
        value = Decimal(numeric_source)
    except InvalidOperation:
        return None
    if sign in {"-", "\u2212"}:
        value = -value
    if scale != "unit_scale":
        value *= _SCALE_FACTORS[scale]
    if match.group("currency_symbol"):
        unit = f"currency_symbol:{match.group('currency_symbol')}"
    elif currency_code:
        unit = currency_code
    if not exponent and not match.group("currency_symbol"):
        parser_literal = ""
        if qualifier:
            parser_literal += (
                "approximately "
                if qualifier in {"approx", "around", "roughly"}
                else qualifier + " "
            )
        parser_literal += ("-" if sign in {"-", "\u2212"} else sign) + number
        if currency_code:
            parser_literal = currency_code + " " + parser_literal
        if scale != "unit_scale":
            parser_literal += " " + scale
        if match.group("percent"):
            parser_literal += "%"
        elif unit and not str(unit).startswith("currency_symbol:"):
            parser_literal += " " + str(unit)
        try:
            parsed = parse_source_bound_numeric_literal(parser_literal)
        except QuantitativeSpecialistProductError:
            parsed = {}
        if parsed:
            value = Decimal(str(parsed["numeric_value_text"]))
            unit = str(parsed.get("unit") or "dimensionless")
    accounting_parentheses = bool(
        (currency_code or match.group("currency_symbol"))
        and match.string[: match.start()].rstrip().endswith("(")
        and match.string[span_end:].lstrip().startswith(")")
    )
    if accounting_parentheses:
        value = -abs(value)
    decimal_places = len(number.split(".", 1)[1]) if "." in number else 0
    precision_class = (
        "approximate_as_reported"
        if qualifier in {"approximately", "approx", "about", "around", "roughly"}
        else "rounded_as_reported"
        if qualifier == "rounded"
        else "exact_as_reported"
    )
    percent_convention = (
        "percent_symbol"
        if match.group("percent")
        else "percent_word"
        if unit == "percent"
        else "basis_points"
        if unit == "basis_points"
        else "percentage_points"
        if unit == "percentage_points"
        else "none"
    )
    sign_posture = (
        "accounting_negative"
        if accounting_parentheses
        else "negative"
        if value < 0
        else "explicit_positive"
        if sign == "+"
        else "implicit_positive"
    )
    notation = "scientific" if exponent else "standard"
    precision_posture = (
        f"{precision_class};decimal_places={decimal_places};notation={notation};"
        f"scale={scale};sign={sign_posture};percent={percent_convention}"
    )
    span_start = match.start("number")
    for group_name in (
        "qualifier",
        "sign",
        "currency_code",
        "compact_currency_code",
        "currency_symbol",
    ):
        if match.group(group_name):
            span_start = min(span_start, match.start(group_name))
    return {
        "span_start": span_start,
        "span_end": span_end,
        "normalized_numeric_value_text": _decimal_text(value),
        "canonical_unit": unit or "dimensionless",
        "precision_posture": precision_posture,
        "scale_posture": scale,
        "sign_posture": sign_posture,
        "percent_convention": percent_convention,
        "notation_posture": notation,
        "parser_version": QUANTITATIVE_FINALIZATION_PARSER_VERSION,
    }


def _parse_cardinal_words(words: Sequence[str]) -> Decimal | None:
    if not words:
        return None
    if len(words) == 1 and words[0] in _ORDINAL_VALUES:
        return Decimal(_ORDINAL_VALUES[words[0]])
    total = 0
    current = 0
    consumed = False
    for word in words:
        if word == "and":
            continue
        if word in _CARDINAL_VALUES:
            current += _CARDINAL_VALUES[word]
            consumed = True
            continue
        if word == "hundred":
            current = max(1, current) * 100
            consumed = True
            continue
        if word in {"thousand", "million", "billion", "trillion"}:
            total += max(1, current) * _TEXT_SCALE_VALUES[word]
            current = 0
            consumed = True
            continue
        return None
    return Decimal(total + current) if consumed else None


def _text_literals(text: str, occupied: Sequence[tuple[int, int]]) -> list[dict[str, Any]]:
    tokens = list(_WORD_TOKEN_RE.finditer(text))
    out: list[dict[str, Any]] = []
    index = 0
    number_words = (
        set(_CARDINAL_VALUES)
        | set(_TEXT_SCALE_VALUES)
        | {"and"}
    )
    while index < len(tokens):
        token = tokens[index]
        word = token.group(0).casefold()
        word_parts = word.split("-")
        if any(start <= token.start() < end for start, end in occupied):
            index += 1
            continue
        unsupported_parts = [
            part
            for part in word_parts
            if part in _UNBOUNDED_QUANTIFIER_WORDS and part not in _ORDINAL_VALUES
        ]
        if unsupported_parts:
            out.append(
                {
                    "span_start": token.start(),
                    "span_end": token.end(),
                    "unsupported_textual_quantifier": unsupported_parts[0],
                    "parser_version": QUANTITATIVE_FINALIZATION_PARSER_VERSION,
                }
            )
            index += 1
            continue
        if any(part not in number_words for part in word_parts) or word == "and":
            index += 1
            continue
        start_index = index
        words: list[str] = []
        while index < len(tokens):
            current = tokens[index]
            current_word = current.group(0).casefold()
            current_words = current_word.split("-")
            if any(part not in number_words for part in current_words):
                break
            if words and text[tokens[index - 1].end() : current.start()].strip(" -"):
                break
            words.extend(current_words)
            index += 1
        value = _parse_cardinal_words(words)
        if value is None:
            index = max(index, start_index + 1)
            continue
        last = tokens[index - 1]
        unit = "dimensionless"
        span_end = last.end()
        if index < len(tokens):
            next_token = tokens[index]
            between = text[last.end() : next_token.start()]
            next_word = next_token.group(0).casefold()
            if not between.strip(" ") and next_word not in _UNIT_STOPWORDS and next_word not in number_words:
                unit = next_word
                span_end = next_token.end()
        out.append(
            {
                "span_start": token.start(),
                "span_end": span_end,
                "normalized_numeric_value_text": _decimal_text(value),
                "canonical_unit": unit,
                "precision_posture": (
                    "exact_as_reported;decimal_places=0;notation="
                    + "textual_cardinal"
                    + ";scale=word_scale;sign=implicit_positive;percent=none"
                ),
                "scale_posture": "word_scale",
                "sign_posture": "implicit_positive",
                "percent_convention": "none",
                "notation_posture": "textual_cardinal",
                "parser_version": QUANTITATIVE_FINALIZATION_PARSER_VERSION,
            }
        )
    return out


def extract_quantitative_literals(text: str) -> list[dict[str, Any]]:
    """Extract bounded quantitative candidates from prose, excluding transport syntax."""

    prose = _strip_nonprose_transport(str(text or ""))
    literals: list[dict[str, Any]] = []
    occupied: list[tuple[int, int]] = []
    for match in _UNSUPPORTED_NUMERIC_SURFACE_RE.finditer(prose):
        surface_kind = next(
            name
            for name, value in match.groupdict().items()
            if value is not None
        )
        literals.append(
            {
                "span_start": match.start(),
                "span_end": match.end(),
                "unsupported_quantitative_surface": surface_kind,
                "parser_version": QUANTITATIVE_FINALIZATION_PARSER_VERSION,
            }
        )
        occupied.append((match.start(), match.end()))
    for match in _DIGIT_LITERAL_RE.finditer(prose):
        numeric_start = match.start("number")
        if any(start <= numeric_start < end for start, end in occupied):
            continue
        if numeric_start and prose[numeric_start - 1] in "_":
            continue
        if (
            numeric_start
            and prose[numeric_start - 1].isalpha()
            and not match.group("compact_currency_code")
        ):
            continue
        literal = _digit_literal(match)
        if literal is None:
            continue
        literals.append(literal)
        occupied.append((int(literal["span_start"]), int(literal["span_end"])))
    text_literals = _text_literals(prose, occupied)
    literals.extend(text_literals)
    occupied.extend(
        (int(item["span_start"]), int(item["span_end"])) for item in text_literals
    )
    for match in _NUMERIC_GLYPH_RE.finditer(prose):
        if any(start <= match.start() < end for start, end in occupied):
            continue
        literals.append(
            {
                "span_start": match.start(),
                "span_end": match.end(),
                "unsupported_quantitative_surface": "unparsed_numeric_surface",
                "parser_version": QUANTITATIVE_FINALIZATION_PARSER_VERSION,
            }
        )
        occupied.append((match.start(), match.end()))
    literals.sort(key=lambda item: (int(item["span_start"]), int(item["span_end"])))
    return literals


def _literal_signature(literal: Mapping[str, Any]) -> str:
    if literal.get("unsupported_textual_quantifier"):
        return "unsupported_text:" + str(literal["unsupported_textual_quantifier"])
    if literal.get("unsupported_quantitative_surface"):
        return "unsupported_surface:" + str(
            literal["unsupported_quantitative_surface"]
        )
    return "|".join(
        str(literal.get(key) or "")
        for key in (
            "normalized_numeric_value_text",
            "canonical_unit",
            "precision_posture",
        )
    )


def _normalized_claim_body(assertion: str, literals: Sequence[Mapping[str, Any]]) -> str:
    pieces: list[str] = []
    cursor = 0
    for literal in literals:
        start = int(literal["span_start"])
        end = int(literal["span_end"])
        if start < cursor:
            continue
        pieces.append(assertion[cursor:start])
        pieces.append(" QUANT[" + _literal_signature(literal) + "] ")
        cursor = end
    pieces.append(assertion[cursor:])
    normalized = "".join(pieces).casefold()
    tokens = re.findall(r"quant\[[^\]]+\]|[a-z0-9]+(?:['’\-][a-z0-9]+)?", normalized)
    return " ".join(tokens)


def semantic_claim_fingerprint(assertion: str) -> str:
    prose = _strip_nonprose_transport(assertion)
    literals = extract_quantitative_literals(prose)
    return _text_digest(_normalized_claim_body(prose, literals))


_SOURCE_EQUIVALENCE_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "are",
        "at",
        "has",
        "have",
        "is",
        "of",
        "the",
        "to",
        "was",
        "were",
    }
)
_SOURCE_EQUIVALENCE_TOKEN_NORMALIZATION = {
    "applications": "application",
    "due": "deadline",
}


def _source_equivalence_core(assertion: str) -> frozenset[str]:
    literals = extract_quantitative_literals(assertion)
    normalized = _normalized_claim_body(assertion, literals)
    normalized = re.sub(r"quant\[[^\]]+\]", " ", normalized)
    tokens: set[str] = set()
    for token in re.findall(r"[a-z0-9]+(?:['â€™\-][a-z0-9]+)?", normalized):
        if token in _SOURCE_EQUIVALENCE_STOPWORDS:
            continue
        tokens.add(_SOURCE_EQUIVALENCE_TOKEN_NORMALIZATION.get(token, token))
    return frozenset(tokens)


def _component_id_tail(value: Any) -> str:
    return str(value or "").strip().rsplit(":", 1)[-1]


def _component_source_lineage_matches(
    admitted_claim: Mapping[str, Any],
    direct_claim: Mapping[str, Any],
) -> bool:
    admitted_ref = _mapping(admitted_claim.get("evidence_or_specialist_ref"))
    observation_ref = _mapping(admitted_ref.get("semantic_observation_ref"))
    coverage_ref = _mapping(admitted_ref.get("component_coverage_ref"))
    evidence_refs = _mapping_sequence(admitted_ref.get("evidence_refs"))
    direct_material_ref = _mapping(direct_claim.get("fap_material_ref"))
    admitted_component = _component_id_tail(
        _mapping(admitted_claim.get("claim_ref")).get("component_id")
    )
    direct_component = _component_id_tail(
        _mapping(direct_claim.get("claim_ref")).get("component_id")
    )
    exact_content_ref = any(
        ref.get("content_ref_id") == direct_material_ref.get("content_ref_id")
        and ref.get("content_digest") == direct_material_ref.get("content_digest")
        for ref in evidence_refs
    )
    exact_coverage_ref = bool(
        coverage_ref.get("coverage_record_id")
        and coverage_ref.get("coverage_record_id")
        == direct_material_ref.get("coverage_record_id")
        and coverage_ref.get("coverage_record_digest")
        == direct_material_ref.get("coverage_record_digest")
    )
    admitted_core = _source_equivalence_core(
        str(admitted_claim.get("claim_text") or "")
    )
    direct_core = _source_equivalence_core(
        str(direct_claim.get("claim_text") or "")
    )
    shared_core = admitted_core & direct_core
    proposition_core_matches = bool(
        len(shared_core) >= 2
        and (admitted_core <= direct_core or direct_core <= admitted_core)
    )
    return bool(
        observation_ref.get("observation_id")
        and observation_ref.get("observation_digest")
        and admitted_component
        and admitted_component == direct_component
        and exact_content_ref
        and exact_coverage_ref
        and proposition_core_matches
    )


def _claim_ref_from_entry(entry: Mapping[str, Any], *, fallback_key: str) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "claim_id": entry.get("claim_id") or entry.get("synthesis_key") or fallback_key,
            "claim_digest": entry.get("claim_digest") or _text_digest(str(entry.get("claim_text") or "")),
            "component_id": entry.get("component_id"),
            "synthesis_key": entry.get("synthesis_key"),
        }.items()
        if value not in (None, "", [], {})
    }


def specialist_quantitative_authority_ref_from_handoff(
    specialist_need_handoff: Mapping[str, Any] | None,
    *,
    applicable_dprime_ref: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Project an exact completed Specialist/D-prime handoff without new authority."""

    from core.specialist_graph_runtime import (
        VALIDATOR_COMPONENT,
        VALIDATOR_SYNTHESIS,
        VALIDATOR_TERMINAL,
        SpecialistGraphRuntimeError,
        validate_specialist_need_handoff,
    )

    try:
        handoff = validate_specialist_need_handoff(
            _mapping(specialist_need_handoff)
        )
    except SpecialistGraphRuntimeError:
        return {}
    result = _mapping(handoff.get("result"))
    result_ref = _mapping(result.get("result_ref"))
    bounded = _mapping(result.get("bounded_result"))
    alignment = _mapping(bounded.get("claim_alignment"))
    alignment_binding = _mapping(alignment.get("literal_binding_ref"))
    dprime_ref = _safe_ref(applicable_dprime_ref)
    target_kind = str(
        _mapping(handoff.get("canonical_target_ref")).get("target_kind") or ""
    )
    expected_consumption = (
        VALIDATOR_COMPONENT
        if target_kind == "component"
        else VALIDATOR_SYNTHESIS
        if target_kind == "synthesis"
        else ""
    )
    canonical_result_unit = _normalized_result_unit(bounded.get("result_unit"))
    legacy_result_unit = _normalized_result_unit(bounded.get("unit"))
    if canonical_result_unit:
        if legacy_result_unit and legacy_result_unit != canonical_result_unit:
            return {}
        result_unit_contract_posture = (
            "canonical_result_unit_with_legacy_agreement"
            if legacy_result_unit
            else "canonical_result_unit"
        )
        result_unit = canonical_result_unit
    elif legacy_result_unit:
        result_unit_contract_posture = "explicit_legacy_unit_compatibility"
        result_unit = legacy_result_unit
    else:
        return {}
    if not (
        handoff.get("handoff_id")
        and handoff.get("handoff_digest")
        and result_ref.get("result_id")
        and result_ref.get("result_digest")
        and result_ref.get("capability_id") == QUANTITATIVE_CAPABILITY_ID
        and result_ref.get("capability_version")
        == QUANTITATIVE_CAPABILITY_VERSION
        and result_ref.get("execution_posture") == "completed"
        and result.get("execution_posture") == "completed"
        and bounded.get("calculation_status") == "computed"
        and bounded.get("numeric_value_text") is not None
        and result_unit
        and bounded.get("precision_posture")
        and alignment.get("posture") == "exact_match"
        and _digest_text_is_valid(alignment_binding.get("source_material_digest"))
        and dprime_ref
        and expected_consumption
        and handoff.get("validator_consumption") == expected_consumption
        and handoff.get("validator_consumption_terminal") == VALIDATOR_TERMINAL
        and handoff.get("validator_validation_status")
        in {"supported", "supported_with_caveats"}
        and _safe_ref(handoff.get("validator_dprime_artifact_ref"))
        == dprime_ref
        and _safe_ref(result_ref.get("canonical_target_ref"))
        == _safe_ref(handoff.get("canonical_target_ref"))
    ):
        return {}
    return {
        "specialist_result_ref": _safe_ref(result_ref),
        "specialist_handoff_ref": {
            "handoff_id": handoff.get("handoff_id"),
            "handoff_digest": handoff.get("handoff_digest"),
            "canonical_target_ref": _safe_ref(handoff.get("canonical_target_ref")),
        },
        "normalized_numeric_value_text": str(bounded.get("numeric_value_text")),
        "canonical_unit": result_unit,
        "precision_posture": str(bounded.get("precision_posture")),
        "result_unit_contract_posture": result_unit_contract_posture,
        "claim_alignment_posture": "exact_match",
        "claim_alignment_ref_digest": _digest(alignment),
        "claim_material_digest": alignment_binding.get("source_material_digest"),
        "applicable_dprime_ref": dprime_ref,
        "applicable_dprime_consumption_ref": {
            "route": (
                "component_dprime"
                if target_kind == "component"
                else "synthesis_dprime"
            ),
            "handoff_id": handoff.get("handoff_id"),
            "handoff_digest": handoff.get("handoff_digest"),
            "dprime_artifact_ref": dprime_ref,
            "consumption_posture": "consumed_by_applicable_dprime",
        },
    }


def _normalized_result_unit(value: Any) -> str:
    unit = _clean_text(value, limit=80)
    if not unit:
        return ""
    literals = extract_quantitative_literals(f"1 {unit}")
    if len(literals) != 1:
        return ""
    return str(literals[0].get("canonical_unit") or "")


def _specialist_ref_is_complete(specialist_ref: Mapping[str, Any]) -> bool:
    result_ref = _mapping(specialist_ref.get("specialist_result_ref"))
    handoff_ref = _mapping(specialist_ref.get("specialist_handoff_ref"))
    target_ref = _mapping(handoff_ref.get("canonical_target_ref"))
    dprime_ref = _mapping(specialist_ref.get("applicable_dprime_ref"))
    consumption_ref = _mapping(
        specialist_ref.get("applicable_dprime_consumption_ref")
    )
    return bool(
        result_ref.get("result_id")
        and result_ref.get("result_digest")
        and result_ref.get("capability_id") == QUANTITATIVE_CAPABILITY_ID
        and result_ref.get("capability_version")
        == QUANTITATIVE_CAPABILITY_VERSION
        and result_ref.get("execution_posture") == "completed"
        and _mapping(result_ref.get("canonical_target_ref")) == target_ref
        and handoff_ref.get("handoff_id")
        and handoff_ref.get("handoff_digest")
        and target_ref.get("target_kind") in {"component", "synthesis"}
        and specialist_ref.get("normalized_numeric_value_text") is not None
        and specialist_ref.get("canonical_unit")
        and specialist_ref.get("precision_posture")
        and specialist_ref.get("result_unit_contract_posture")
        in {
            "canonical_result_unit",
            "canonical_result_unit_with_legacy_agreement",
            "explicit_legacy_unit_compatibility",
        }
        and specialist_ref.get("claim_alignment_posture") == "exact_match"
        and specialist_ref.get("claim_alignment_ref_digest")
        and _digest_text_is_valid(specialist_ref.get("claim_material_digest"))
        and dprime_ref
        and consumption_ref.get("route")
        == f"{target_ref.get('target_kind')}_dprime"
        and consumption_ref.get("handoff_id") == handoff_ref.get("handoff_id")
        and consumption_ref.get("handoff_digest")
        == handoff_ref.get("handoff_digest")
        and consumption_ref.get("consumption_posture")
        == "consumed_by_applicable_dprime"
        and _mapping(consumption_ref.get("dprime_artifact_ref")) == dprime_ref
    )


def _specialist_matches(
    literal: Mapping[str, Any], specialist_ref: Mapping[str, Any]
) -> bool:
    if not _specialist_ref_is_complete(specialist_ref):
        return False
    if (
        str(literal.get("normalized_numeric_value_text"))
        != str(specialist_ref.get("normalized_numeric_value_text"))
        or str(literal.get("canonical_unit"))
        != str(specialist_ref.get("canonical_unit"))
    ):
        return False
    specialist_precision = str(specialist_ref.get("precision_posture") or "")
    return str(literal.get("precision_posture") or "").startswith(
        specialist_precision + ";"
    ) or str(literal.get("precision_posture") or "") == specialist_precision


def _specialist_claim_matches(
    claim_text: str,
    literals: Sequence[Mapping[str, Any]],
    specialist_ref: Mapping[str, Any],
) -> bool:
    return bool(
        specialist_ref.get("claim_material_digest") == _text_digest(claim_text)
        and any(_specialist_matches(literal, specialist_ref) for literal in literals)
    )


def _claim_sources(
    *,
    direct_component_entries: Sequence[Mapping[str, Any]],
    admitted_synthesis_entries: Sequence[Mapping[str, Any]],
    semantic_author_materialization: Mapping[str, Any] | None,
    component_packet_entries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    direct_claims: list[dict[str, Any]] = []
    admitted_claims: list[dict[str, Any]] = []
    for index, raw in enumerate(direct_component_entries, start=1):
        entry = _mapping(raw)
        dprime_ref = _safe_ref(entry.get("dprime_validation_ref"))
        if not (
            entry.get("entry_kind") == "direct_component"
            and entry.get("admission_status") in {"admitted", "admitted_with_caveats"}
            and entry.get("current") is True
            and entry.get("stale") is False
            and _clean_text(entry.get("claim_text"), limit=2000)
            and dprime_ref
        ):
            continue
        admitted_claims.append(
            {
                "source_kind": "admitted_quantitative_claim",
                "claim_text": _clean_text(entry.get("claim_text"), limit=2000),
                "claim_ref": _claim_ref_from_entry(entry, fallback_key=f"direct-{index}"),
                "claim_authority_posture": "current_admitted_component_dprime_supported",
                "applicable_dprime_ref": dprime_ref,
                "applicable_dprime_consumption_ref": dprime_ref,
                "evidence_or_specialist_ref": {
                    "semantic_observation_ref": _safe_ref(entry.get("semantic_observation_ref")),
                    "component_coverage_ref": _safe_ref(entry.get("component_coverage_ref")),
                    "evidence_refs": _safe_value(entry.get("evidence_refs") or []),
                },
                "specialist_ref": _safe_ref(entry.get("specialist_quantitative_authority_ref")),
                "fap_material_ref": {"entry_kind": "direct_component", "entry_index": index},
            }
        )
    for index, raw in enumerate(admitted_synthesis_entries, start=1):
        entry = _mapping(raw)
        carried = _mapping(entry.get("carried_semantic_lineage"))
        dprime_ref = _safe_ref(entry.get("dprime_validation_ref")) or _safe_ref(
            carried.get("prior_synthesis_dprime_ref")
        )
        if not (
            entry.get("entry_kind") == "admitted_synthesis"
            and entry.get("status") == "admitted"
            and entry.get("current") is True
            and entry.get("stale") is False
            and _clean_text(entry.get("claim_text"), limit=2000)
            and dprime_ref
        ):
            continue
        admitted_claims.append(
            {
                "source_kind": "admitted_quantitative_claim",
                "claim_text": _clean_text(entry.get("claim_text"), limit=2000),
                "claim_ref": _claim_ref_from_entry(entry, fallback_key=f"synthesis-{index}"),
                "claim_authority_posture": "current_admitted_synthesis_dprime_supported",
                "applicable_dprime_ref": dprime_ref,
                "applicable_dprime_consumption_ref": _safe_ref(entry.get("runkernel_admission_ref")) or dprime_ref,
                "evidence_or_specialist_ref": {
                    "input_node_refs": _safe_value(entry.get("input_node_refs") or []),
                    "runkernel_admission_ref": _safe_ref(entry.get("runkernel_admission_ref")),
                },
                "specialist_ref": _safe_ref(entry.get("specialist_quantitative_authority_ref")),
                "fap_material_ref": {"entry_kind": "admitted_synthesis", "entry_index": index},
            }
        )
    for index, raw in enumerate(component_packet_entries, start=1):
        entry = _mapping(raw)
        claim_text = _clean_text(entry.get("safe_answer_claim_text"), limit=2000)
        observation_ref = _safe_ref(entry.get("semantic_observation_ref"))
        if not (
            entry.get("supported_safe_claim_allowed") is True
            and entry.get("must_not_answer") is not True
            and claim_text
            and observation_ref
        ):
            continue
        admitted_claims.append(
            {
                "source_kind": "admitted_quantitative_claim",
                "claim_text": claim_text,
                "claim_ref": _safe_ref(entry.get("fap_safe_claim_ref")) or {
                    "component_id": entry.get("component_id"),
                    "claim_digest": _text_digest(claim_text),
                },
                "claim_authority_posture": "hardened_fap_current_admitted_dprime_supported",
                "applicable_dprime_ref": observation_ref,
                "applicable_dprime_consumption_ref": observation_ref,
                "evidence_or_specialist_ref": {
                    "semantic_observation_ref": observation_ref,
                    "component_coverage_ref": _safe_ref(entry.get("component_coverage_ref")),
                },
                "specialist_ref": _safe_ref(entry.get("specialist_quantitative_authority_ref")),
                "source_authority_refs": _safe_value(
                    entry.get("quantitative_source_authority_refs") or []
                ),
                "fap_material_ref": {"entry_kind": "hardened_component", "entry_index": index},
            }
        )
    materialization = _mapping(semantic_author_materialization)
    if materialization.get("available") is True and materialization.get(
        "bounded_material_complete"
    ) is True:
        for material_index, material in enumerate(
            _mapping_sequence(materialization.get("bounded_material_refs")),
            start=1,
        ):
            bounded_text = str(material.get("bounded_text") or "")
            for assertion_index, assertion in enumerate(_assertions(bounded_text), start=1):
                if not extract_quantitative_literals(assertion):
                    continue
                direct_claims.append(
                    {
                        "source_kind": "direct_source_numeric",
                        "claim_text": assertion,
                        "claim_ref": {
                            "component_id": material.get("component_id"),
                            "content_ref_id": material.get("content_ref_id"),
                            "content_digest": material.get("content_digest"),
                            "claim_digest": _text_digest(assertion),
                        },
                        "claim_authority_posture": "current_fap_authorized_source_bound_material",
                        "applicable_dprime_ref": {},
                        "applicable_dprime_consumption_ref": {},
                        "evidence_or_specialist_ref": {
                            "evidence_ref_id": material.get("evidence_ref_id"),
                            "packet_evidence_id": material.get("packet_evidence_id"),
                            "source_id": material.get("source_id"),
                        },
                        "specialist_ref": {},
                        "fap_material_ref": {
                            "material_index": material_index,
                            "assertion_index": assertion_index,
                            "content_ref_id": material.get("content_ref_id"),
                            "content_digest": material.get("content_digest"),
                            "coverage_record_id": material.get("coverage_record_id"),
                            "coverage_record_digest": material.get("coverage_record_digest"),
                        },
                    }
                )
    return [*direct_claims, *admitted_claims]


def _hardened_source_binding(
    claim: Mapping[str, Any],
    *,
    fingerprint: str,
    literals: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    claim_ref = _mapping(claim.get("claim_ref"))
    admitted_ref = _mapping(claim.get("evidence_or_specialist_ref"))
    admitted_observation_ref = _mapping(admitted_ref.get("semantic_observation_ref"))
    admitted_coverage_ref = _mapping(admitted_ref.get("component_coverage_ref"))
    expected_literal_refs = _hardened_literal_signature_refs(literals)
    expected_literal_digest = _digest(expected_literal_refs)
    for raw_ref in _mapping_sequence(claim.get("source_authority_refs")):
        ref = _mapping(raw_ref)
        declared_ref_digest = ref.pop("source_authority_ref_digest", None)
        observation_ref = _mapping(ref.get("semantic_observation_ref"))
        coverage_ref = _mapping(ref.get("component_coverage_ref"))
        content_ref = _mapping(ref.get("content_reference_ref"))
        evidence_ref = _mapping(ref.get("evidence_or_packet_evidence_ref"))
        literal_refs = _mapping_sequence(ref.get("literal_signatures"))
        if not (
            declared_ref_digest
            and declared_ref_digest == _digest(ref)
            and ref.get("source_proposition_fingerprint") == fingerprint
            and ref.get("safe_claim_fingerprint") == fingerprint
            and ref.get("source_safe_claim_relationship") == "exact_claim_fingerprint"
            and ref.get("component_id") == claim_ref.get("component_id")
            and ref.get("component_revision") == claim_ref.get("component_revision")
            and ref.get("component_digest") == claim_ref.get("component_digest")
            and observation_ref.get("observation_id")
            == admitted_observation_ref.get("observation_id")
            and observation_ref.get("observation_digest")
            == admitted_observation_ref.get("observation_digest")
            and coverage_ref.get("coverage_record_id")
            == admitted_coverage_ref.get("coverage_record_id")
            and coverage_ref.get("coverage_record_digest")
            == admitted_coverage_ref.get("coverage_record_digest")
            and content_ref.get("content_ref_id")
            and content_ref.get("content_digest")
            and evidence_ref.get("evidence_ref_id")
            and ref.get("complete_literal_signature_digest") == expected_literal_digest
            and literal_refs == expected_literal_refs
            and ref.get("current") is True
            and ref.get("stale") is False
            and ref.get("currentness_posture") == "current"
            and ref.get("source_proposition_retained") is False
            and ref.get("source_material_retained") is False
        ):
            continue
        return {
            "evidence_or_specialist_ref": {
                "semantic_observation_ref": observation_ref,
                "component_coverage_ref": coverage_ref,
                "content_reference_ref": content_ref,
                "evidence_or_packet_evidence_ref": evidence_ref,
            },
            "fap_material_ref": {
                "entry_kind": "hardened_component_source_authority",
                "component_id": ref.get("component_id"),
                "component_digest": ref.get("component_digest"),
                "source_authority_ref_digest": declared_ref_digest,
                "source_proposition_digest": ref.get("source_proposition_digest"),
                "content_ref_id": content_ref.get("content_ref_id"),
                "content_digest": content_ref.get("content_digest"),
                "coverage_record_id": coverage_ref.get("coverage_record_id"),
                "coverage_record_digest": coverage_ref.get("coverage_record_digest"),
            },
        }
    return None


def _hardened_literal_signature_refs(
    literals: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for ordinal, literal in enumerate(literals, start=1):
        signature = {
            "claim_literal_ordinal": ordinal,
            "normalized_numeric_value_text": literal.get(
                "normalized_numeric_value_text"
            ),
            "canonical_unit": literal.get("canonical_unit"),
            "precision_posture": literal.get("precision_posture"),
        }
        refs.append(
            {
                **signature,
                "literal_signature_digest": _digest(signature),
            }
        )
    return refs


def build_quantitative_finalization_authority_bundle(
    *,
    source_fap_ref: Mapping[str, Any],
    direct_component_entries: Sequence[Mapping[str, Any]] = (),
    admitted_synthesis_entries: Sequence[Mapping[str, Any]] = (),
    semantic_author_materialization: Mapping[str, Any] | None = None,
    component_packet_entries: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build the safe manifest plus transient exact renderings for Author input."""

    claims = _claim_sources(
        direct_component_entries=direct_component_entries,
        admitted_synthesis_entries=admitted_synthesis_entries,
        semantic_author_materialization=semantic_author_materialization,
        component_packet_entries=component_packet_entries,
    )
    authorized: list[dict[str, Any]] = []
    renderings: dict[str, str] = {}
    seen: set[tuple[str, str, int]] = set()
    direct_bindings: dict[
        tuple[str, tuple[tuple[str, int], ...]], dict[str, Any]
    ] = {}
    direct_bindings_by_signature: dict[
        tuple[tuple[str, int], ...], list[dict[str, Any]]
    ] = {}
    for claim in claims:
        if claim.get("source_kind") != "direct_source_numeric":
            continue
        claim_text = str(claim.get("claim_text") or "")
        literals = extract_quantitative_literals(claim_text)
        if not literals:
            continue
        fingerprint = semantic_claim_fingerprint(claim_text)
        signatures = tuple(sorted(Counter(_literal_signature(item) for item in literals).items()))
        direct_bindings.setdefault((fingerprint, signatures), claim)
        direct_bindings_by_signature.setdefault(signatures, []).append(claim)
    for claim_index, claim in enumerate(claims, start=1):
        claim_text = str(claim["claim_text"])
        literals = extract_quantitative_literals(claim_text)
        if not literals or any(
            item.get("unsupported_textual_quantifier")
            or item.get("unsupported_quantitative_surface")
            for item in literals
        ):
            continue
        fingerprint = semantic_claim_fingerprint(claim_text)
        claim_ref = _safe_ref(claim.get("claim_ref"))
        local_claim_key = (
            f"quant-claim-{claim_index:03d}-{fingerprint[:12]}"
        )
        signatures = tuple(
            sorted(Counter(_literal_signature(item) for item in literals).items())
        )
        source_binding = direct_bindings.get((fingerprint, signatures))
        source_binding_posture = (
            "exact_claim_fingerprint"
            if source_binding is not None
            else ""
        )
        if (
            source_binding is None
            and claim.get("source_kind") == "admitted_quantitative_claim"
            and _mapping(claim.get("fap_material_ref")).get("entry_kind")
            == "direct_component"
        ):
            source_binding = next(
                (
                    direct
                    for direct in direct_bindings_by_signature.get(signatures, ())
                    if _component_source_lineage_matches(claim, direct)
                ),
                None,
            )
            if source_binding is not None:
                source_binding_posture = "component_source_lineage_equivalent"
        if (
            source_binding is None
            and claim.get("source_kind") == "admitted_quantitative_claim"
            and _mapping(claim.get("fap_material_ref")).get("entry_kind")
            == "hardened_component"
        ):
            source_binding = _hardened_source_binding(
                claim,
                fingerprint=fingerprint,
                literals=literals,
            )
            if source_binding is not None:
                source_binding_posture = "hardened_exact_source_fingerprint"
        specialist_ref = _safe_ref(claim.get("specialist_ref"))
        specialist_claim_authorized = _specialist_claim_matches(
            claim_text,
            literals,
            specialist_ref,
        )
        claim_authorized = False
        for literal_index, literal in enumerate(literals, start=1):
            authority_kind = str(claim.get("source_kind"))
            evidence_ref = _safe_ref(claim.get("evidence_or_specialist_ref"))
            dprime_ref = _safe_ref(claim.get("applicable_dprime_ref"))
            dprime_consumption_ref = _safe_ref(
                claim.get("applicable_dprime_consumption_ref")
            )
            if specialist_claim_authorized:
                authority_kind = "specialist_derived_numeric"
                evidence_ref = _safe_ref(
                    specialist_ref.get("specialist_result_ref")
                )
                dprime_ref = _safe_ref(specialist_ref.get("applicable_dprime_ref"))
                dprime_consumption_ref = _safe_ref(
                    specialist_ref.get("applicable_dprime_consumption_ref")
                )
            elif authority_kind == "admitted_quantitative_claim":
                if source_binding is None:
                    continue
                authority_kind = "direct_source_numeric"
                evidence_ref = _safe_ref(
                    source_binding.get("evidence_or_specialist_ref")
                )
                dprime_ref = {}
                dprime_consumption_ref = {}
            dedupe_key = (
                fingerprint,
                _literal_signature(literal),
                literal_index,
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            claim_authorized = True
            authorized.append(
                {
                    "local_claim_key": local_claim_key,
                    "claim_literal_ordinal": literal_index,
                    "current_claim_ref": claim_ref,
                    "claim_authority_posture": (
                        "current_fap_authorized_source_bound_material_"
                        + source_binding_posture
                        if source_binding is not None
                        and authority_kind == "direct_source_numeric"
                        else claim.get("claim_authority_posture")
                    ),
                    "authority_kind": authority_kind,
                    "normalized_numeric_value_text": literal.get(
                        "normalized_numeric_value_text"
                    ),
                    "canonical_unit": literal.get("canonical_unit"),
                    "precision_posture": literal.get("precision_posture"),
                    "evidence_or_specialist_ref": evidence_ref,
                    "applicable_dprime_ref": dprime_ref,
                    "applicable_dprime_consumption_ref": dprime_consumption_ref,
                    "admitted_claim_ref": (
                        claim_ref
                        if authority_kind == "specialist_derived_numeric"
                        else {}
                    ),
                    "fap_material_ref": _safe_ref(
                        source_binding.get("fap_material_ref")
                        if authority_kind == "direct_source_numeric"
                        and source_binding is not None
                        else claim.get("fap_material_ref")
                    ),
                    "semantic_claim_fingerprint_or_existing_equivalent": fingerprint,
                    "literal_signature_digest": _text_digest(
                        _literal_signature(literal)
                    ),
                }
            )
        if claim_authorized:
            renderings[local_claim_key] = claim_text
    manifest_base = {
        "schema_version": QUANTITATIVE_FINALIZATION_AUTHORITY_MANIFEST_SCHEMA_VERSION,
        "source_fap_ref": _safe_ref(source_fap_ref),
        "authorized_numeric_claims": authorized,
        "prohibited_transformations": list(_PROHIBITED_TRANSFORMATIONS),
        "claim_scoped": True,
        "value_only_matching_prohibited": True,
        "calculation_performed": False,
        "conversion_performed": False,
        "claim_admission_performed": False,
        "sufficiency_changed": False,
    }
    manifest = {**manifest_base, "manifest_digest": _digest(manifest_base)}
    return {"manifest": manifest, "transient_renderings": renderings}


def build_quantitative_finalization_authority_manifest(
    **kwargs: Any,
) -> dict[str, Any]:
    return dict(build_quantitative_finalization_authority_bundle(**kwargs)["manifest"])


def build_quantitative_author_instruction_block(
    manifest: Mapping[str, Any],
    *,
    transient_renderings: Mapping[str, str] | None = None,
) -> str:
    claims = _mapping_sequence(_mapping(manifest).get("authorized_numeric_claims"))
    renderings = dict(transient_renderings or {})
    lines = [
        "",
        "QUANTITATIVE FINALIZATION AUTHORITY (mandatory; do not mention this block):",
        "- You may render only the exact claim-scoped numeric propositions listed below.",
        "- Preserve each authorized value, unit, sign, scale, percent convention, and precision posture.",
        "- Comma digit grouping is the only numeric surface variation permitted.",
        "- Do not calculate, convert, estimate, interpolate, round, rescale, aggregate, or introduce a new numeric conclusion.",
        "- Do not reuse an authorized value for another subject, metric, comparison, ratio, rate, percentage, or proposition.",
    ]
    keys = list(dict.fromkeys(str(item.get("local_claim_key")) for item in claims))
    if not keys:
        lines.append("- This packet authorizes no quantitative claim; emit no quantitative assertion.")
    else:
        lines.append("- Authorized exact quantitative renderings:")
        for key in keys:
            rendering = _clean_text(renderings.get(key), limit=1200)
            if rendering:
                lines.append(f"  - {key}: {rendering}")
    return "\n".join(lines) + "\n"


def _digest_text_is_valid(value: Any) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", str(value or "")))


def _authorized_claim_row_is_valid(entry: Mapping[str, Any]) -> bool:
    row = dict(entry)
    authority_kind = str(row.get("authority_kind") or "")
    ordinal = row.get("claim_literal_ordinal")
    if (
        set(row) != _AUTHORIZED_CLAIM_FIELDS
        or authority_kind not in _AUTHORITY_KINDS
        or not str(row.get("local_claim_key") or "").startswith("quant-claim-")
        or isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or row.get("normalized_numeric_value_text") in (None, "")
        or not row.get("canonical_unit")
        or not row.get("precision_posture")
        or not row.get("claim_authority_posture")
        or not _digest_text_is_valid(
            row.get("semantic_claim_fingerprint_or_existing_equivalent")
        )
        or not _digest_text_is_valid(row.get("literal_signature_digest"))
    ):
        return False
    for key in _AUTHORIZED_CLAIM_REF_FIELDS:
        value = row.get(key)
        if not isinstance(value, Mapping) or dict(value) != _safe_ref(value):
            return False
    if (
        not row["current_claim_ref"]
        or not row["evidence_or_specialist_ref"]
        or not row["fap_material_ref"]
    ):
        return False
    if authority_kind == "direct_source_numeric":
        return not (
            row["applicable_dprime_ref"]
            or row["applicable_dprime_consumption_ref"]
            or row["admitted_claim_ref"]
        )
    return bool(
        row["applicable_dprime_ref"]
        and row["applicable_dprime_consumption_ref"]
        and row["admitted_claim_ref"]
    )


def _validate_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(manifest)
    declared = safe.get("manifest_digest")
    core = {key: value for key, value in safe.items() if key != "manifest_digest"}
    raw_claims = safe.get("authorized_numeric_claims")
    claims_are_sequence = isinstance(raw_claims, Sequence) and not isinstance(
        raw_claims, str | bytes | bytearray
    )
    claims = _mapping_sequence(raw_claims) if claims_are_sequence else []
    source_fap_ref = safe.get("source_fap_ref")
    if (
        set(safe) != _MANIFEST_FIELDS
        or safe.get("schema_version")
        != QUANTITATIVE_FINALIZATION_AUTHORITY_MANIFEST_SCHEMA_VERSION
        or safe.get("claim_scoped") is not True
        or safe.get("value_only_matching_prohibited") is not True
        or safe.get("calculation_performed") is not False
        or safe.get("conversion_performed") is not False
        or safe.get("claim_admission_performed") is not False
        or safe.get("sufficiency_changed") is not False
        or tuple(safe.get("prohibited_transformations") or ())
        != _PROHIBITED_TRANSFORMATIONS
        or not isinstance(source_fap_ref, Mapping)
        or not source_fap_ref
        or dict(source_fap_ref) != _safe_ref(source_fap_ref)
        or not claims_are_sequence
        or len(claims) != len(raw_claims)
        or any(not _authorized_claim_row_is_valid(item) for item in claims)
        or not declared
        or declared != _digest(core)
    ):
        raise QuantitativeFinalizationAuthorityError(
            "quantitative finalization manifest is invalid",
            diagnostic={
                "schema_version": QUANTITATIVE_FINALIZATION_VALIDATION_SCHEMA_VERSION,
                "status": "rejected",
                "reason_codes": ["invalid_quantitative_authority_manifest"],
                "final_text_included": False,
            },
        )
    return safe


def validate_author_output_quantitative_authority(
    answer_text: str,
    *,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Accept nonquantitative prose or fail closed on any unbound assertion."""

    current = _validate_manifest(manifest)
    claims = _mapping_sequence(current.get("authorized_numeric_claims"))
    by_fingerprint: dict[str, list[dict[str, Any]]] = {}
    for entry in claims:
        fingerprint = str(
            entry.get("semantic_claim_fingerprint_or_existing_equivalent") or ""
        )
        if fingerprint:
            by_fingerprint.setdefault(fingerprint, []).append(entry)

    candidate_count = 0
    matched_claim_keys: list[str] = []
    reasons: list[dict[str, Any]] = []
    for assertion_index, assertion in enumerate(_assertions(str(answer_text or "")), start=1):
        literals = extract_quantitative_literals(assertion)
        if not literals:
            continue
        candidate_count += len(literals)
        assertion_digest = _text_digest(assertion)
        unsupported_words = [
            str(item.get("unsupported_textual_quantifier"))
            for item in literals
            if item.get("unsupported_textual_quantifier")
        ]
        unsupported_surfaces = [
            str(item.get("unsupported_quantitative_surface"))
            for item in literals
            if item.get("unsupported_quantitative_surface")
        ]
        if unsupported_words or unsupported_surfaces:
            marker_values = unsupported_words or unsupported_surfaces
            reason = {
                "assertion_index": assertion_index,
                "assertion_digest": assertion_digest,
                "reason_code": (
                    "unsupported_textual_quantifier"
                    if unsupported_words
                    else "unsupported_quantitative_surface"
                ),
                (
                    "quantifier_digests"
                    if unsupported_words
                    else "surface_marker_digests"
                ): [_text_digest(item) for item in marker_values],
            }
            reasons.append(reason)
            continue
        fingerprint = semantic_claim_fingerprint(assertion)
        authorized_entries = by_fingerprint.get(fingerprint, [])
        candidate_signatures = Counter(_literal_signature(item) for item in literals)
        authorized_signatures = Counter(
            "|".join(
                str(entry.get(key) or "")
                for key in (
                    "normalized_numeric_value_text",
                    "canonical_unit",
                    "precision_posture",
                )
            )
            for entry in authorized_entries
        )
        if not authorized_entries or candidate_signatures != authorized_signatures:
            reasons.append(
                {
                    "assertion_index": assertion_index,
                    "assertion_digest": assertion_digest,
                    "semantic_claim_fingerprint": fingerprint,
                    "reason_code": (
                        "claim_scoped_literal_mismatch"
                        if authorized_entries
                        else "unauthorized_quantitative_proposition"
                    ),
                    "candidate_literal_count": len(literals),
                }
            )
            continue
        matched_claim_keys.extend(
            str(entry.get("local_claim_key")) for entry in authorized_entries
        )

    diagnostic_base = {
        "schema_version": QUANTITATIVE_FINALIZATION_VALIDATION_SCHEMA_VERSION,
        "manifest_digest": current.get("manifest_digest"),
        "candidate_quantitative_literal_count": candidate_count,
        "matched_claim_keys": list(dict.fromkeys(matched_claim_keys)),
        "rejection_count": len(reasons),
        "reason_refs": reasons,
        "claim_scoped_binding": True,
        "model_validator_used": False,
        "answer_rewritten": False,
        "answer_fragment_deleted": False,
        "author_retry_requested": False,
        "final_text_included": False,
    }
    if reasons:
        diagnostic = {**diagnostic_base, "status": "rejected"}
        raise QuantitativeFinalizationAuthorityError(
            "Author output contains an unsupported quantitative proposition",
            diagnostic=diagnostic,
        )
    return {**diagnostic_base, "status": "accepted"}


__all__ = [
    "QUANTITATIVE_FINALIZATION_AUTHORITY_MANIFEST_SCHEMA_VERSION",
    "QUANTITATIVE_FINALIZATION_PARSER_VERSION",
    "QUANTITATIVE_FINALIZATION_VALIDATION_SCHEMA_VERSION",
    "QuantitativeFinalizationAuthorityError",
    "build_quantitative_author_instruction_block",
    "build_quantitative_finalization_authority_bundle",
    "build_quantitative_finalization_authority_manifest",
    "extract_quantitative_literals",
    "semantic_claim_fingerprint",
    "specialist_quantitative_authority_ref_from_handoff",
    "validate_author_output_quantitative_authority",
]
