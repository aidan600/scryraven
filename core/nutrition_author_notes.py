import re
from typing import Any

from core.nutrition_lookup import NUTRITION_MACRO_METRICS

_NUTRITION_AUTHOR_METRIC_LABELS = {
    "calories": "Calories",
    "protein": "Protein",
    "fat": "Fat",
    "carbohydrates": "Carbohydrates",
}


def _nutrition_passage_is_proxy(passage: dict[str, Any]) -> bool:
    text = " ".join(
        str(passage.get(key, ""))
        for key in ("title", "text", "snippet", "summary", "evidence_status", "match_type")
    )
    return bool(re.search(r"\b(proxy|indirect)\b", text, flags=re.I))


def _nutrition_metric_regexes(metric: str) -> tuple[re.Pattern[str], ...]:
    number = r"\d+(?:\.\d+)?"
    per_unit = r"(?:\s*(?:per|/)\s*100\s*(?:g|grams?))?"
    if metric == "calories":
        return (
            re.compile(rf"\b{number}\s*(?:calories|kcal|kilocalories)\b{per_unit}", re.I),
            re.compile(rf"\b(?:calories|kcal|kilocalories)\b[^\d]{{0,24}}{number}{per_unit}", re.I),
        )
    if metric == "protein":
        return (
            re.compile(rf"\b{number}\s*g(?:rams?)?\s*(?:of\s+)?protein\b{per_unit}", re.I),
            re.compile(rf"\bprotein\b[^\d]{{0,24}}{number}\s*g(?:rams?)?{per_unit}", re.I),
        )
    if metric == "fat":
        return (
            re.compile(rf"\b{number}\s*g(?:rams?)?\s*(?:of\s+)?(?:total\s+)?fat\b{per_unit}", re.I),
            re.compile(rf"\b(?:total\s+)?fat\b[^\d]{{0,24}}{number}\s*g(?:rams?)?{per_unit}", re.I),
        )
    if metric == "carbohydrates":
        return (
            re.compile(
                rf"\b{number}\s*g(?:rams?)?\s*(?:of\s+)?(?:carbohydrates?|carbs?|total carbohydrate)\b{per_unit}",
                re.I,
            ),
            re.compile(
                rf"\b(?:carbohydrates?|carbs?|total carbohydrate)\b[^\d]{{0,24}}{number}\s*g(?:rams?)?{per_unit}",
                re.I,
            ),
        )
    return ()


def _nutrition_metric_from_passage(
    metric: str,
    passage: dict[str, Any],
) -> tuple[bool, str]:
    text = " ".join(
        str(passage.get(key, ""))
        for key in ("title", "text", "snippet", "summary")
    )
    for pattern in _nutrition_metric_regexes(metric):
        match = pattern.search(text)
        if match:
            return True, " ".join(match.group(0).split())
    return False, ""


def _format_nutrition_partial_evidence_author_note(
    *,
    nutrition_lookup_telemetry: dict[str, Any] | None,
    quant_retrieval_sufficiency_telemetry: dict[str, Any] | None,
    final_top_evidence: list[Any],
) -> str:
    if not isinstance(nutrition_lookup_telemetry, dict) or not nutrition_lookup_telemetry.get(
        "nutrition_lookup_detected"
    ):
        return ""

    requested = [
        str(metric)
        for metric in nutrition_lookup_telemetry.get("nutrition_lookup_metrics_requested", [])
        if str(metric) in NUTRITION_MACRO_METRICS
    ]
    requested = list(dict.fromkeys(requested))
    macro_field_requested = any(metric in requested for metric in ("protein", "fat", "carbohydrates"))
    if len(requested) < 2 and not macro_field_requested:
        return ""

    passages = [item for item in final_top_evidence or [] if isinstance(item, dict)]
    rows: list[tuple[str, str, str]] = []
    missing_found = False
    proxy_found = False
    direct_found = False

    for metric in NUTRITION_MACRO_METRICS:
        found = False
        proxy = False
        snippet = ""
        for passage in passages:
            found, snippet = _nutrition_metric_from_passage(metric, passage)
            if found:
                proxy = _nutrition_passage_is_proxy(passage)
                break
        if found:
            if proxy:
                proxy_found = True
                status = "Found proxy/indirect"
            else:
                direct_found = True
                status = "Found direct"
        else:
            missing_found = True
            status = "Not found in retrieved evidence"
            snippet = "Do not estimate or infer this field."
        rows.append((_NUTRITION_AUTHOR_METRIC_LABELS[metric], status, snippet))

    sufficiency_valid = bool(
        isinstance(quant_retrieval_sufficiency_telemetry, dict)
        and quant_retrieval_sufficiency_telemetry.get("quant_retrieval_sufficiency_valid")
    )
    if sufficiency_valid and not missing_found and not proxy_found:
        return ""
    if not missing_found and not proxy_found and direct_found:
        return ""

    row_text = "\n".join(
        f"| {label} | {status} | {snippet} |" for label, status, snippet in rows
    )
    return (
        "\n\nNOTE FOR AUTHOR - NUTRITION PARTIAL MACRO EVIDENCE:\n"
        "I found partial nutrition evidence, not a complete macro panel.\n"
        "In the final answer, include a compact nutrition table or structured bullet list with "
        "Calories, Protein, Fat, and Carbohydrates. Use these evidence statuses exactly; do not "
        "invent protein, fat, or carbohydrate values, and do not say the macros were fully answered.\n"
        "| Metric | Evidence status | Retrieved value/evidence |\n"
        "| --- | --- | --- |\n"
        f"{row_text}\n"
    )
