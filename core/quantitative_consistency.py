"""Deterministic diagnostics for narrow two-item normalized comparisons."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

_NUMBER = r"(?:\d+(?:\.\d*)?|\.\d+)"
_CALORIE_UNIT = r"(?:cal(?:orie|ories)?|kcal|kilocalories?)"
_GRAM_UNIT = r"(?:g|grams?)"
_QUERY_PAIR_RE = re.compile(
    rf"(?P<value>{_NUMBER})\s*-?\s*(?P<unit>{_CALORIE_UNIT})\b"
    rf"[^\d]{{0,18}}(?P<grams>{_NUMBER})\s*-?\s*{_GRAM_UNIT}\b",
    re.IGNORECASE,
)
_WINNER_CUE_RE = re.compile(
    r"\b(?:more|most|higher|highest|greater|greatest)\b"
    r"[^.?!\n]{0,80}\b(?:dense|density|per\s*(?:g|gram)|calories?\s*/\s*g)\b"
    r"|\bdenser\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _NormalizedItem:
    item_id: str
    value: float
    value_unit: str
    denominator: float
    denominator_unit: str
    normalized_value: float
    basis: str


def quantitative_consistency_defaults() -> dict[str, Any]:
    """Return trace-safe defaults for the quantitative consistency diagnostic."""
    return {
        "quantitative_consistency_shadow_mode": True,
        "quantitative_consistency_check_attempted": False,
        "quantitative_consistency_status": "not_applicable",
        "quantitative_consistency_reason": "not_two_item_normalized_comparison",
        "quantitative_consistency_contradiction_flag": False,
        "quantitative_consistency_computed_winner": None,
        "quantitative_consistency_stated_winner": None,
        "quantitative_consistency_normalized_values": [],
    }


def quantitative_consistency_guard_defaults(
    *,
    original_status: str | None = None,
) -> dict[str, Any]:
    """Return trace-safe defaults for the deterministic final-output guard."""
    return {
        "quantitative_consistency_guard_applied": False,
        "quantitative_consistency_guard_reason": "not_evaluated",
        "quantitative_consistency_guard_output_mode": "unchanged",
        "quantitative_consistency_original_status": original_status,
        "quantitative_consistency_guard_final_answer_replaced": False,
    }


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip().replace(",", "")
    if not re.fullmatch(_NUMBER, text):
        return None
    return float(text)


def _unit_text(value: Any) -> str:
    return str(value or "").strip().casefold()


def _is_calorie_unit(unit: str) -> bool:
    return bool(re.fullmatch(_CALORIE_UNIT, unit, flags=re.IGNORECASE))


def _is_gram_unit(unit: str) -> bool:
    return bool(re.fullmatch(_GRAM_UNIT, unit, flags=re.IGNORECASE))


def _items_from_query(query: str) -> list[_NormalizedItem]:
    items: list[_NormalizedItem] = []
    for match in _QUERY_PAIR_RE.finditer(query or ""):
        value = _as_float(match.group("value"))
        denominator = _as_float(match.group("grams"))
        unit = _unit_text(match.group("unit"))
        if value is None or denominator is None or denominator <= 0:
            continue
        if not _is_calorie_unit(unit):
            continue
        item_id = f"item_{chr(ord('a') + len(items))}"
        items.append(
            _NormalizedItem(
                item_id=item_id,
                value=value,
                value_unit="calories",
                denominator=denominator,
                denominator_unit="g",
                normalized_value=value / denominator,
                basis="query_pair",
            )
        )
        if len(items) > 2:
            break
    return items if len(items) == 2 else []


def is_two_item_calorie_gram_comparison_candidate(query: str) -> bool:
    """Return True for the narrow query shape that may need guarded streaming."""
    return len(_items_from_query(query)) == 2


def _bound_values_by_name(values: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        return {}
    out: dict[str, Mapping[str, Any]] = {}
    for item in values:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            out[name] = item
    return out


def _input_ref(input_refs: Mapping[str, Any], *names: str) -> str:
    for name in names:
        value = str(input_refs.get(name) or "").strip()
        if value:
            return value
    return ""


def _items_from_structured(
    *,
    calculation_results: Any,
    source_bound_values: Any,
) -> list[_NormalizedItem]:
    if not isinstance(calculation_results, list):
        return []
    values_by_name = _bound_values_by_name(source_bound_values)
    items: list[_NormalizedItem] = []
    for result in calculation_results:
        if not isinstance(result, Mapping):
            continue
        if str(result.get("name") or "").strip() != "normalize_per_100g":
            continue
        input_refs = result.get("input_refs")
        if not isinstance(input_refs, Mapping):
            continue
        value_ref = _input_ref(input_refs, "value", "numerator", "metric_value")
        grams_ref = _input_ref(input_refs, "serving_grams", "grams", "denominator")
        value_source = values_by_name.get(value_ref)
        grams_source = values_by_name.get(grams_ref)
        if value_source is None or grams_source is None:
            continue
        value = _as_float(value_source.get("value"))
        denominator = _as_float(grams_source.get("value"))
        value_unit = _unit_text(value_source.get("unit"))
        grams_unit = _unit_text(grams_source.get("unit"))
        if (
            value is None
            or denominator is None
            or denominator <= 0
            or not _is_calorie_unit(value_unit)
            or not _is_gram_unit(grams_unit)
        ):
            continue
        item_id = str(result.get("item_id") or result.get("item") or "").strip()
        if not item_id:
            item_id = f"item_{chr(ord('a') + len(items))}"
        items.append(
            _NormalizedItem(
                item_id=item_id,
                value=value,
                value_unit="calories",
                denominator=denominator,
                denominator_unit="g",
                normalized_value=value / denominator,
                basis="structured_calculation",
            )
        )
        if len(items) > 2:
            break
    return items if len(items) == 2 else []


def _number_pattern(value: float) -> str:
    if value.is_integer():
        return rf"{int(value)}(?:\.0+)?"
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return re.escape(text)


def _item_regex(item: _NormalizedItem) -> re.Pattern[str]:
    value = _number_pattern(item.value)
    denominator = _number_pattern(item.denominator)
    forward = (
        rf"{value}\s*-?\s*{_CALORIE_UNIT}\b[^\d]{{0,24}}"
        rf"{denominator}\s*-?\s*{_GRAM_UNIT}\b"
    )
    reverse = (
        rf"{denominator}\s*-?\s*{_GRAM_UNIT}\b[^\d]{{0,24}}"
        rf"{value}\s*-?\s*{_CALORIE_UNIT}\b"
    )
    return re.compile(rf"(?:{forward})|(?:{reverse})", re.IGNORECASE)


def _sentences(text: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", (text or "")[:1200])
        if part.strip()
    ]


def _stated_winner(
    *,
    final_answer: str,
    items: list[_NormalizedItem],
) -> str | None:
    item_patterns = {item.item_id: _item_regex(item) for item in items}
    for sentence in _sentences(final_answer):
        cue = _WINNER_CUE_RE.search(sentence)
        if cue is None:
            continue
        positions: list[tuple[str, int]] = []
        for item_id, pattern in item_patterns.items():
            match = pattern.search(sentence)
            if match is not None:
                positions.append((item_id, match.start()))
        if not positions:
            continue
        before_cue = [
            (item_id, position)
            for item_id, position in positions
            if position <= cue.start()
        ]
        if before_cue:
            return max(before_cue, key=lambda item: item[1])[0]
        if len(positions) == 1:
            return positions[0][0]
    return None


def _serialized_values(items: list[_NormalizedItem]) -> list[dict[str, Any]]:
    return [
        {
            "item_id": item.item_id,
            "value": item.value,
            "value_unit": item.value_unit,
            "denominator": item.denominator,
            "denominator_unit": item.denominator_unit,
            "normalized_value": round(item.normalized_value, 6),
            "normalized_unit": f"{item.value_unit}/g",
            "basis": item.basis,
        }
        for item in items
    ]


def _items_from_diagnostic_values(values: Any) -> list[_NormalizedItem]:
    if not isinstance(values, list) or len(values) != 2:
        return []
    items: list[_NormalizedItem] = []
    seen_ids: set[str] = set()
    for idx, value in enumerate(values):
        if not isinstance(value, Mapping):
            return []
        item_id = str(value.get("item_id") or "").strip()
        if not item_id or item_id in seen_ids:
            return []
        item_value = _as_float(value.get("value"))
        denominator = _as_float(value.get("denominator"))
        value_unit = _unit_text(value.get("value_unit"))
        denominator_unit = _unit_text(value.get("denominator_unit"))
        normalized_value = _as_float(value.get("normalized_value"))
        if (
            item_value is None
            or denominator is None
            or normalized_value is None
            or denominator <= 0
            or not isfinite(item_value)
            or not isfinite(denominator)
            or not isfinite(normalized_value)
            or not _is_calorie_unit(value_unit)
            or not _is_gram_unit(denominator_unit)
        ):
            return []
        items.append(
            _NormalizedItem(
                item_id=item_id,
                value=item_value,
                value_unit="calories",
                denominator=denominator,
                denominator_unit="g",
                normalized_value=item_value / denominator,
                basis=str(value.get("basis") or f"diagnostic_item_{idx + 1}")[:80],
            )
        )
        seen_ids.add(item_id)
    if not all(isfinite(item.normalized_value) for item in items):
        return []
    return items


def _format_compact_number(value: float, *, places: int = 3) -> str:
    if abs(value - round(value)) < 10 ** -(places + 1):
        return str(int(round(value)))
    return f"{value:.{places}f}".rstrip("0").rstrip(".")


def _item_display(item: _NormalizedItem) -> str:
    return (
        f"{_format_compact_number(item.value)} calories / "
        f"{_format_compact_number(item.denominator)} g"
    )


def _guarded_corrected_answer(
    *,
    items: list[_NormalizedItem],
    computed_winner: str,
) -> str:
    item_by_id = {item.item_id: item for item in items}
    winner = item_by_id[computed_winner]
    loser = next(item for item in items if item.item_id != computed_winner)
    winner_rate = winner.normalized_value
    loser_rate = loser.normalized_value
    diff_per_g = abs(winner_rate - loser_rate)
    diff_per_100g = diff_per_g * 100.0
    relative_pct = (
        (diff_per_g / abs(loser_rate)) * 100.0 if loser_rate != 0 else None
    )
    item_lines = "\n".join(
        (
            f"- {_item_display(item)} = "
            f"{_format_compact_number(item.normalized_value)} cal/g = "
            f"{_format_compact_number(item.normalized_value * 100.0, places=1)} cal/100g."
        )
        for item in items
    )
    relative_note = ""
    if relative_pct is not None and isfinite(relative_pct):
        relative_note = (
            f" That is about {_format_compact_number(relative_pct, places=1)}% higher "
            f"than {_item_display(loser)}."
        )
    return (
        "Using the figures you provided:\n"
        f"{item_lines}\n\n"
        f"The {_item_display(winner)} item is more calorie-dense. "
        f"The absolute difference is {_format_compact_number(diff_per_g)} cal/g, "
        f"or {_format_compact_number(diff_per_100g, places=1)} cal/100g."
        f"{relative_note}"
    )


def build_two_item_normalized_consistency_diagnostic(
    *,
    query: str,
    final_answer: str,
    quantitative_packet: Mapping[str, Any] | None = None,
    calculation_results: Any = None,
    source_bound_values: Any = None,
) -> dict[str, Any]:
    """Detect winner/prose contradictions for simple two-item normalized comparisons."""
    out = quantitative_consistency_defaults()
    packet = quantitative_packet if isinstance(quantitative_packet, Mapping) else {}
    packet_calculations = packet.get("calculation_results")
    packet_values = packet.get("source_bound_values")
    items = _items_from_structured(
        calculation_results=calculation_results if calculation_results is not None else packet_calculations,
        source_bound_values=source_bound_values if source_bound_values is not None else packet_values,
    )
    if not items:
        items = _items_from_query(query)
    if len(items) != 2:
        return out

    out["quantitative_consistency_check_attempted"] = True
    out["quantitative_consistency_normalized_values"] = _serialized_values(items)

    first, second = items
    if abs(first.normalized_value - second.normalized_value) < 1e-12:
        out["quantitative_consistency_status"] = "not_applicable"
        out["quantitative_consistency_reason"] = "normalized_values_tie"
        return out

    computed_winner = (
        first.item_id
        if first.normalized_value > second.normalized_value
        else second.item_id
    )
    stated_winner = _stated_winner(final_answer=final_answer, items=items)
    out["quantitative_consistency_computed_winner"] = computed_winner
    out["quantitative_consistency_stated_winner"] = stated_winner
    if stated_winner is None:
        out["quantitative_consistency_status"] = "not_applicable"
        out["quantitative_consistency_reason"] = "no_stated_winner_detected"
        return out
    if stated_winner != computed_winner:
        out["quantitative_consistency_status"] = "contradiction_detected"
        out["quantitative_consistency_reason"] = "stated_winner_contradicts_normalized_values"
        out["quantitative_consistency_contradiction_flag"] = True
        return out

    out["quantitative_consistency_status"] = "consistent"
    out["quantitative_consistency_reason"] = "stated_winner_matches_normalized_values"
    return out


def apply_quantitative_consistency_guard(
    *,
    query: str,
    final_answer: str,
    diagnostic: Mapping[str, Any] | None = None,
    quantitative_packet: Mapping[str, Any] | None = None,
    calculation_results: Any = None,
    source_bound_values: Any = None,
) -> tuple[str, dict[str, Any]]:
    """Replace narrow contradictory normalized-comparison prose deterministically."""
    active_diagnostic = (
        diagnostic
        if isinstance(diagnostic, Mapping)
        else build_two_item_normalized_consistency_diagnostic(
            query=query,
            final_answer=final_answer,
            quantitative_packet=quantitative_packet,
            calculation_results=calculation_results,
            source_bound_values=source_bound_values,
        )
    )
    original_status = str(
        active_diagnostic.get("quantitative_consistency_status") or ""
    )
    telemetry = quantitative_consistency_guard_defaults(
        original_status=original_status or None,
    )
    if original_status != "contradiction_detected":
        telemetry["quantitative_consistency_guard_reason"] = "status_not_contradiction"
        return final_answer, telemetry

    computed_winner = str(
        active_diagnostic.get("quantitative_consistency_computed_winner") or ""
    ).strip()
    stated_winner = str(
        active_diagnostic.get("quantitative_consistency_stated_winner") or ""
    ).strip()
    if not computed_winner or not stated_winner:
        telemetry["quantitative_consistency_guard_reason"] = "winner_missing"
        return final_answer, telemetry
    if computed_winner == stated_winner:
        telemetry["quantitative_consistency_guard_reason"] = "winners_match"
        return final_answer, telemetry

    items = _items_from_diagnostic_values(
        active_diagnostic.get("quantitative_consistency_normalized_values")
    )
    if len(items) != 2:
        telemetry["quantitative_consistency_guard_reason"] = (
            "exactly_two_normalized_items_unavailable"
        )
        return final_answer, telemetry
    item_ids = {item.item_id for item in items}
    if computed_winner not in item_ids or stated_winner not in item_ids:
        telemetry["quantitative_consistency_guard_reason"] = "winner_not_in_items"
        return final_answer, telemetry
    if abs(items[0].normalized_value - items[1].normalized_value) < 1e-12:
        telemetry["quantitative_consistency_guard_reason"] = "normalized_values_tie"
        return final_answer, telemetry

    guarded_answer = _guarded_corrected_answer(
        items=items,
        computed_winner=computed_winner,
    )
    telemetry.update(
        {
            "quantitative_consistency_guard_applied": True,
            "quantitative_consistency_guard_reason": (
                "deterministic_normalized_winner_replacement"
            ),
            "quantitative_consistency_guard_output_mode": (
                "deterministic_corrected_answer"
            ),
            "quantitative_consistency_guard_final_answer_replaced": True,
        }
    )
    return guarded_answer, telemetry
