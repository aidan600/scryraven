import re
from typing import Any

NUTRITION_MACRO_METRICS = ("calories", "protein", "fat", "carbohydrates")
NUTRITION_METRIC_TERMS: dict[str, tuple[str, ...]] = {
    "calories": ("calories", "kcal", "kilocalories", "energy"),
    "protein": ("protein",),
    "fat": ("fat", "total fat"),
    "carbohydrates": ("carbohydrates", "carbs", "carb", "total carbohydrate"),
}


def nutrition_lookup_telemetry_defaults() -> dict[str, Any]:
    return {
        "nutrition_lookup_detected": False,
        "nutrition_lookup_reason": None,
        "nutrition_lookup_metrics_requested": [],
        "nutrition_lookup_unit": None,
        "nutrition_lookup_shadow_mode": True,
    }


def _nutrition_lookup_unique(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def detect_nutrition_lookup_telemetry(query: str) -> dict[str, Any]:
    telemetry = nutrition_lookup_telemetry_defaults()
    text = " ".join(str(query or "").casefold().split())
    if not text:
        return telemetry

    has_per_100g_normalization = bool(
        re.search(r"(?:\bper\s+100\s*(?:g|grams)\b|/100\s*g\b)", text)
    )
    if not has_per_100g_normalization:
        return telemetry

    metrics: list[str] = []
    if re.search(r"\b(?:macros?|nutrition\s+facts?)\b", text):
        metrics.extend(NUTRITION_MACRO_METRICS)
    if re.search(r"\b(?:calories|kcal)\b", text):
        metrics.append("calories")
    if re.search(r"\bprotein\b", text):
        metrics.append("protein")
    if re.search(r"\bfat\b", text):
        metrics.append("fat")
    if re.search(r"\b(?:carbs?|carbohydrates)\b", text):
        metrics.append("carbohydrates")

    metrics = _nutrition_lookup_unique(metrics)
    if not metrics:
        return telemetry

    telemetry.update(
        {
            "nutrition_lookup_detected": True,
            "nutrition_lookup_reason": "nutrition_metric_per_100g",
            "nutrition_lookup_metrics_requested": metrics,
            "nutrition_lookup_unit": "per_100g",
            "nutrition_lookup_shadow_mode": True,
        }
    )
    return telemetry
