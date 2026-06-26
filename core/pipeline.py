import concurrent.futures
import json
import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional

from core.calculations import ALLOWED_CALCULATIONS, sanitize_to_float
from core.cost_accounting import CostAccumulator
from core.nutrition_lookup import (
    NUTRITION_MACRO_METRICS as NUTRITION_MACRO_METRICS,
)
from core.nutrition_lookup import (
    NUTRITION_METRIC_TERMS as NUTRITION_METRIC_TERMS,
)
from core.nutrition_lookup import (
    detect_nutrition_lookup_telemetry as detect_nutrition_lookup_telemetry,
)
from core.nutrition_lookup import (
    nutrition_lookup_telemetry_defaults as nutrition_lookup_telemetry_defaults,
)
from core.prompts import (
    KB_REVIEW_AGENT_HYBRID_SYSTEM,
    KB_REVIEW_AGENT_SYSTEM,
    economist_budget_for_complexity,
)
from core.provider_diagnostics import build_provider_attempt_diagnostic
from core.retrieval import (
    chunk_text,
    fetch_page,
    get_news_date_window,
    is_plausible_domain,
    normalize_domain,
    rrf_merge,
)
from core.retrieval_quality import jaccard_similarity, passage_mentions_entity_full_phrase
from core.routing import should_allow_linkup_provider
from core.run_logging import log_provider_error, log_retrieval_timeout
from core.scout import (
    QUANT_REPORT_TYPES as QUANT_REPORT_TYPES,
)
from core.scout import (
    run_scout as run_scout,
)
from core.scout import (
    should_skip_quant_scout as should_skip_quant_scout,
)
from core.search_providers import (
    retrieval_timeout_seconds,
    search_exa_results,
    search_linkup_results,
    search_web_results,
)
from core.source_classifier import classify_source, normalize_source_domain
from core.thin_quant import (
    parse_thin_quant_data_unavailable as parse_thin_quant_data_unavailable,
)
from core.thin_quant import (
    thin_quant_preflight_missing_entities as thin_quant_preflight_missing_entities,
)

logger = logging.getLogger(__name__)


class _NoopStatusContainer:
    def write(self, text: str) -> None:
        return


_NOOP_STATUS_CONTAINER = _NoopStatusContainer()


ECONOMIST_CODE_EXECUTION_DISABLED_REASON = "dynamic_code_execution_disabled"
ECONOMIST_SCHEMA_VERSION = "economist_v1"
ECONOMIST_SCHEMA_REQUIRED_KEYS = {
    "schema_version",
    "variables",
    "source_bound_values",
    "assumptions",
    "calculations_requested",
    "confidence",
    "unsupported_values",
}


TARGET_METRIC_BUCKETS: dict[str, tuple[str, ...]] = {
    "price_cost_rate": (
        "price",
        "cost",
        "fee",
        "rate",
        "charge",
        "paid",
        "expense",
        "unit cost",
        "cheap",
        "cheaper",
    ),
    "growth_change": (
        "growth",
        "change",
        "increase",
        "decrease",
        "delta",
        "percent change",
    ),
    "ratio_margin_share": (
        "ratio",
        "margin",
        "percentage",
        "share",
        "rate",
    ),
    "financial_line_item": (
        "revenue",
        "revenues",
        "total revenue",
        "total revenues",
        "operating revenue",
        "net sales",
        "net income",
    ),
    "count_volume_capacity": (
        "count",
        "number",
        "volume",
        "capacity",
        "units",
    ),
    "date_duration_timeline": (
        "date",
        "duration",
        "timeline",
        "launch timing",
    ),
    "performance_speed_throughput": (
        "performance",
        "speed",
        "latency",
        "throughput",
        "efficiency",
        "faster",
        "slower",
    ),
    "comparative_terms": (
        "better",
        "worse",
        "cheaper",
        "faster",
        "slower",
        "higher",
        "lower",
        "vs",
        "versus",
        "compared",
        "comparison",
    ),
}

TARGET_METRIC_CALCULATION_BUCKETS: dict[str, tuple[str, ...]] = {
    "growth_change": ("percent_change", "difference"),
    "ratio_margin_share": ("ratio",),
}

DERIVED_COMPARISON_CALCULATION_TERMS: dict[str, tuple[str, ...]] = {
    "difference": (
        "difference",
        "gap",
        "delta",
        "variance",
        "more than",
        "less than",
    ),
    "percent_change": (
        "percent change",
        "percentage change",
        "growth",
        "change",
    ),
    "ratio": (
        "ratio",
        "multiple",
        "times",
        "as much",
    ),
}

FINANCIAL_LINE_ITEM_DERIVED_VALUE_TERMS = (
    "growth",
    "change",
    "increase",
    "decrease",
    "percent change",
    "percentage change",
    "percentage",
    "ratio",
    "margin",
    "share",
    "rate",
    "gap",
    "difference",
    "delta",
    "variance",
    "multiple",
    "times",
    "per share",
    "per unit",
)

TARGET_METRIC_PRICE_COST_SUPPORT_TERMS = (
    "price",
    "cost",
    "fee",
    "charge",
    "expense",
    "paid",
    "unit cost",
)

TARGET_METRIC_PRICE_COST_CURRENCY_TERMS = (
    "$",
    "usd",
    "eur",
    "gbp",
    "jpy",
    "dollar",
    "dollars",
    "currency",
)

TARGET_METRIC_DURATION_SUPPORT_TERMS = (
    "latency",
    "response time",
    "duration",
    "seconds",
    "milliseconds",
    "ms",
    "s",
)

TARGET_METRIC_BOUND_BUCKETS = {
    "price_cost_rate",
    "growth_change",
    "ratio_margin_share",
    "financial_line_item",
    "count_volume_capacity",
    "date_duration_timeline",
    "performance_speed_throughput",
}

CALCULATION_ARG_ALIASES: dict[str, dict[str, str]] = {
    "difference": {
        "minuend": "a",
        "subtrahend": "b",
    },
}


HIGH_STAKES_MEDICAL_DOMAIN_TERMS = (
    "clinical",
    "medical",
    "patient",
    "treatment",
    "therapy",
    "medication",
    "drug",
    "dose",
    "dosage",
    "diagnosis",
    "symptom",
    "adverse event",
    "side effect",
    "mortality",
    "hospitalization",
    "trial",
    "placebo",
)

HIGH_STAKES_CLINICAL_METRIC_TERMS = (
    "efficacy",
    "effectiveness",
    "outcome",
    "risk",
    "reduction",
    "a1c",
    "hba1c",
    "blood pressure",
    "systolic",
    "diastolic",
    "ldl",
    "survival",
    "mortality",
    "remission",
    "response rate",
    "adverse events",
)

HIGH_STAKES_DECISION_COMPARISON_TERMS = (
    "better",
    "worse",
    "safer",
    "riskier",
    "more effective",
    "less effective",
    "compare",
    "versus",
    "vs",
    "lower",
    "higher",
    "reduce",
    "increase",
)

HIGH_STAKES_PATIENT_CONTEXT_PATTERNS = (
    re.compile(r"\b(?:adult|adults|patient|patients|people|person)\s+with\b", re.IGNORECASE),
    re.compile(r"\b(?:diagnosed|diagnosis)\s+with\b", re.IGNORECASE),
)


def economist_target_metric_telemetry_defaults() -> dict[str, Any]:
    return {
        "target_metric_detected": False,
        "target_metric_names": [],
        "target_metric_evidence_found": False,
        "target_metric_bound_value_refs": [],
        "target_metric_calculation_refs": [],
        "target_metric_missing": [],
        "target_metric_shadow_would_block": False,
        "target_metric_gate_reason": "not_quantitative_target",
        "target_metric_shadow_mode": True,
    }


def economist_high_stakes_quant_telemetry_defaults() -> dict[str, Any]:
    return {
        "high_stakes_quant_detected": False,
        "high_stakes_quant_domain": None,
        "high_stakes_quant_reasons": [],
        "high_stakes_quant_requires_analyst": False,
        "high_stakes_quant_shadow_mode": True,
        "high_stakes_quant_future_direct_use_allowed": True,
        "high_stakes_quant_gate_reason": "not_high_stakes_quantitative",
    }


def economist_quantitative_packet_telemetry_defaults() -> dict[str, Any]:
    return {
        "quantitative_packet_present": False,
        "quantitative_packet_valid": False,
        "quantitative_packet_validation_errors": [],
        "quantitative_packet_direct_use_eligible": False,
        "quantitative_packet_requires_analyst": True,
        "quantitative_packet_shadow_mode": True,
        "quantitative_packet_gate_reason": "packet_not_built",
        "quantitative_packet": None,
    }


def quant_retrieval_sufficiency_telemetry_defaults() -> dict[str, Any]:
    return {
        "quant_retrieval_target_detected": False,
        "quant_retrieval_entities": [],
        "quant_retrieval_metrics": [],
        "quant_retrieval_timeframes": [],
        "quant_retrieval_comparison_subjects": [],
        "quant_retrieval_entity_coverage_valid": False,
        "quant_retrieval_metric_coverage_valid": False,
        "quant_retrieval_timeframe_coverage_valid": False,
        "quant_retrieval_comparison_coverage_valid": False,
        "quant_retrieval_source_diversity_count": 0,
        "quant_retrieval_exact_value_binding_valid": False,
        "quant_retrieval_proxy_metric_detected": False,
        "quant_retrieval_value_source_ids": [],
        "quant_retrieval_sufficiency_valid": False,
        "quant_retrieval_sufficiency_blockers": [],
        "quant_retrieval_sufficiency_gate_reason": "not_quantitative_target",
        "quant_retrieval_sufficiency_shadow_mode": True,
    }


def economist_schema_telemetry_defaults() -> dict[str, Any]:
    return {
        "economist_schema_version": None,
        "economist_schema_valid": False,
        "economist_invalid_fields": [],
        "unsupported_values_count": 0,
        "economist_shadow_mode": True,
        **economist_source_binding_telemetry_defaults(),
        **economist_calculation_telemetry_defaults(),
        **economist_target_metric_telemetry_defaults(),
        **economist_high_stakes_quant_telemetry_defaults(),
        **economist_quantitative_packet_telemetry_defaults(),
    }


def economist_source_binding_telemetry_defaults(
    allowed_source_ids: set[str] | None = None,
) -> dict[str, Any]:
    return {
        "source_binding_valid": False,
        "source_bound_value_count": 0,
        "source_binding_invalid_fields": [],
        "source_binding_missing_source_id_count": 0,
        "source_binding_unknown_source_id_count": 0,
        "source_binding_malformed_count": 0,
        "source_ids_seen": sorted(allowed_source_ids or set()),
        "source_ids_used": [],
        "economist_evidence_source_ids_seen": [],
        "economist_evidence_source_ids_used": [],
        "economist_source_ids_used_outside_evidence_window": [],
        "source_binding_shadow_mode": True,
    }


def economist_calculation_telemetry_defaults() -> dict[str, Any]:
    return {
        "calculation_requests_count": 0,
        "calculation_success_count": 0,
        "calculation_error_count": 0,
        "unsupported_calculation_names": [],
        "calculation_input_binding_valid": False,
        "calculation_input_binding_error_count": 0,
        "calculation_unresolved_input_refs": [],
        "calculation_results_count": 0,
        "calculation_results_shadow_mode": True,
        "calculation_results": [],
        "calculation_error_summaries": [],
    }


def _normalize_calculation_ref(value: Any) -> str:
    return str(value).strip().casefold()


def _canonical_calculation_arg_name(calculation_name: str, arg_name: Any) -> str:
    text = str(arg_name).strip()
    aliases = CALCULATION_ARG_ALIASES.get(calculation_name, {})
    return aliases.get(text.casefold(), text)


def _target_metric_text_matches(text: str, terms: tuple[str, ...]) -> bool:
    normalized = str(text or "").replace("_", " ").replace("-", " ").casefold()
    for term in terms:
        term_text = str(term).strip().casefold()
        if not term_text:
            continue
        if not any(char.isalnum() for char in term_text):
            if term_text in normalized:
                return True
            continue
        if " " in term_text:
            if term_text in normalized:
                return True
            continue
        if re.search(rf"\b{re.escape(term_text)}\b", normalized):
            return True
    return False


def _target_metric_matched_terms(text: str, terms: tuple[str, ...]) -> set[str]:
    normalized = str(text or "").replace("_", " ").replace("-", " ").casefold()
    matches: set[str] = set()
    for term in terms:
        term_text = str(term).strip().casefold()
        if not term_text:
            continue
        if not any(char.isalnum() for char in term_text):
            if term_text in normalized:
                matches.add(term_text)
            continue
        if " " in term_text:
            if term_text in normalized:
                matches.add(term_text)
            continue
        if re.search(rf"\b{re.escape(term_text)}\b", normalized):
            matches.add(term_text)
    return matches


def _is_qualitative_rate_request(query: str) -> bool:
    text = str(query or "").replace("_", " ").replace("-", " ").casefold()
    if not re.search(r"\brate\s+(?:the|this|that|a|an)\s+\w+", text):
        return False
    return not (
        _target_metric_text_matches(text, TARGET_METRIC_PRICE_COST_SUPPORT_TERMS)
        or _target_metric_text_matches(text, TARGET_METRIC_PRICE_COST_CURRENCY_TERMS)
    )


def _has_price_cost_rate_context(query: str) -> bool:
    text = str(query or "").replace("_", " ").replace("-", " ").casefold()
    if _target_metric_text_matches(text, TARGET_METRIC_PRICE_COST_SUPPORT_TERMS):
        return True
    if _target_metric_text_matches(text, TARGET_METRIC_PRICE_COST_CURRENCY_TERMS):
        return True
    return bool(re.search(r"\b(?:hourly|daily|monthly|annual|unit)\s+rate\b", text))


def _has_explicit_timeline_context(query: str) -> bool:
    text = str(query or "").replace("_", " ").replace("-", " ").casefold()
    return bool(
        re.search(
            r"\b(?:when|launch(?:ed)?|launch date|timeline for|duration|how long|time to)\b",
            text,
        )
    )


def detect_target_metric_buckets(query: str) -> list[str]:
    text = str(query or "")
    qualitative_rate_request = _is_qualitative_rate_request(text)
    price_cost_rate_context = _has_price_cost_rate_context(text)
    buckets: list[str] = []
    for bucket, terms in TARGET_METRIC_BUCKETS.items():
        matched_terms = _target_metric_matched_terms(text, terms)
        if qualitative_rate_request and matched_terms == {"rate"}:
            continue
        if bucket == "price_cost_rate" and matched_terms == {"rate"} and not price_cost_rate_context:
            continue
        if bucket == "ratio_margin_share" and matched_terms == {"rate"} and price_cost_rate_context:
            continue
        if bucket == "date_duration_timeline" and matched_terms == {"timeline"}:
            if not _has_explicit_timeline_context(text):
                continue
        if matched_terms:
            buckets.append(bucket)
    return buckets


def _append_unique(items: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _source_bound_value_declares_unsupported(item: Any) -> bool:
    if not isinstance(item, dict):
        return True
    if item.get("supported") is False:
        return True
    provenance_text = " ".join(
        str(item.get(key) or "")
        for key in (
            "support",
            "status",
            "provenance",
            "basis",
            "source_type",
            "derivation",
        )
    )
    return _target_metric_text_matches(
        provenance_text,
        (
            "unsupported",
            "model derived",
            "model-derived",
            "assumption derived",
            "assumption-derived",
            "inferred",
            "estimated",
            "projected",
        ),
    )


def _source_bound_value_matches_bucket(item: Any, bucket: str) -> bool:
    if not isinstance(item, dict):
        return False
    if _source_bound_value_declares_unsupported(item):
        return False
    if bucket not in TARGET_METRIC_BOUND_BUCKETS:
        return False
    if bucket == "price_cost_rate":
        return _source_bound_value_supports_price_cost_rate(item)
    terms = TARGET_METRIC_BUCKETS.get(bucket, ())
    haystack = " ".join(
        str(item.get(key) or "") for key in ("name", "metric", "label", "unit")
    )
    if bucket == "financial_line_item" and _target_metric_text_matches(
        haystack,
        FINANCIAL_LINE_ITEM_DERIVED_VALUE_TERMS,
    ):
        return False
    return _target_metric_text_matches(haystack, terms)


def _source_bound_value_supports_price_cost_rate(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    if _source_bound_value_declares_unsupported(item):
        return False
    haystack = " ".join(
        str(item.get(key) or "") for key in ("name", "metric", "label", "unit")
    )
    unit = str(item.get("unit") or "")
    return _target_metric_text_matches(
        haystack,
        TARGET_METRIC_PRICE_COST_SUPPORT_TERMS,
    ) or _target_metric_text_matches(unit, TARGET_METRIC_PRICE_COST_CURRENCY_TERMS)


def _source_bound_value_supports_duration(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    if _source_bound_value_declares_unsupported(item):
        return False
    haystack = " ".join(
        str(item.get(key) or "") for key in ("name", "metric", "label", "unit")
    )
    return _target_metric_text_matches(haystack, TARGET_METRIC_DURATION_SUPPORT_TERMS)


def _calculation_result_matches_bucket(result: Any, bucket: str) -> bool:
    if not isinstance(result, dict):
        return False
    name = str(result.get("name") or "").strip()
    compatible_names = TARGET_METRIC_CALCULATION_BUCKETS.get(bucket, ())
    return bool(name and name in compatible_names)


def _calculation_directly_compares_bound_values(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    name = str(result.get("name") or "").strip()
    if name not in {"difference", "percent_change", "ratio"}:
        return False
    input_refs = result.get("input_refs")
    if not isinstance(input_refs, dict):
        return False
    unique_refs = {str(ref).strip() for ref in input_refs.values() if str(ref).strip()}
    return len(unique_refs) >= 2


def _unsupported_value_covered_by_calculation(
    value: Any,
    calculation_results: list[Any],
) -> bool:
    text = str(value or "")
    if not text.strip():
        return False
    for result in calculation_results:
        if not _calculation_directly_compares_bound_values(result):
            continue
        name = str(result.get("name") or "").strip()
        terms = DERIVED_COMPARISON_CALCULATION_TERMS.get(name, ())
        if terms and _target_metric_text_matches(text, terms):
            return True
    return False


def _unsupported_value_describes_derived_comparison(value: Any) -> bool:
    text = str(value or "")
    if not text.strip():
        return False
    terms: list[str] = []
    for calculation_terms in DERIVED_COMPARISON_CALCULATION_TERMS.values():
        terms.extend(calculation_terms)
    return _target_metric_text_matches(text, tuple(_quant_unique(terms)))


def _unsupported_value_blocks_target_bucket(
    value: Any,
    *,
    bucket: str,
    calculation_results: list[Any],
) -> bool:
    if not _target_metric_text_matches(
        str(value or ""),
        TARGET_METRIC_BUCKETS.get(bucket, ()),
    ):
        return False
    if _unsupported_value_covered_by_calculation(value, calculation_results):
        return False
    return not (
        bucket == "financial_line_item"
        and _unsupported_value_describes_derived_comparison(value)
    )


def _calculation_compares_duration_bound_values(
    result: Any,
    source_bound_values: list[Any],
) -> bool:
    if not _calculation_directly_compares_bound_values(result):
        return False
    input_refs = result.get("input_refs")
    if not isinstance(input_refs, dict):
        return False
    values_by_name = {
        _normalize_calculation_ref(item.get("name")): item
        for item in source_bound_values
        if isinstance(item, dict)
    }
    duration_refs = {
        str(ref).strip()
        for ref in input_refs.values()
        if _source_bound_value_supports_duration(
            values_by_name.get(_normalize_calculation_ref(ref))
        )
    }
    return len(duration_refs) >= 2


def validate_target_metric_shadow(
    *,
    query: str,
    payload: Any,
    schema_telemetry: dict[str, Any],
    source_binding_telemetry: dict[str, Any],
    calculation_telemetry: dict[str, Any],
) -> dict[str, Any]:
    telemetry = economist_target_metric_telemetry_defaults()
    target_names = detect_target_metric_buckets(query)
    telemetry["target_metric_names"] = target_names
    telemetry["target_metric_detected"] = bool(target_names)
    if not target_names:
        return telemetry

    if (
        schema_telemetry.get("economist_schema_valid") is not True
        or source_binding_telemetry.get("source_binding_valid") is not True
    ):
        telemetry["target_metric_missing"] = target_names
        telemetry["target_metric_shadow_would_block"] = True
        telemetry["target_metric_gate_reason"] = "schema_or_source_binding_invalid"
        return telemetry

    source_bound_values = payload.get("source_bound_values") if isinstance(payload, dict) else []
    if not isinstance(source_bound_values, list):
        source_bound_values = []
    calculation_results = calculation_telemetry.get("calculation_results")
    if not isinstance(calculation_results, list):
        calculation_results = []

    bound_matches: dict[str, list[str]] = {bucket: [] for bucket in target_names}
    calculation_matches: dict[str, list[str]] = {bucket: [] for bucket in target_names}
    requested_bound_matches: dict[str, list[str]] = {bucket: [] for bucket in target_names}
    requested_bound_applies: dict[str, bool] = {bucket: False for bucket in target_names}
    requested_bound_valid: dict[str, bool] = {bucket: False for bucket in target_names}
    for bucket in target_names:
        for item in source_bound_values:
            if _source_bound_value_matches_bucket(item, bucket):
                _append_unique(bound_matches[bucket], item.get("name"))
        for result in calculation_results:
            if _calculation_result_matches_bucket(result, bucket):
                _append_unique(calculation_matches[bucket], result.get("name"))
            if (
                bucket == "performance_speed_throughput"
                and _calculation_compares_duration_bound_values(
                    result,
                    source_bound_values,
                )
                ):
                    _append_unique(calculation_matches[bucket], result.get("name"))
        applies, refs, valid = _target_metric_requested_bound_value_refs(
            query=query,
            bucket=bucket,
            source_bound_values=[
                item for item in source_bound_values if isinstance(item, dict)
            ],
        )
        requested_bound_applies[bucket] = applies
        requested_bound_valid[bucket] = valid
        requested_bound_matches[bucket] = refs

    primary_targets = [bucket for bucket in target_names if bucket != "comparative_terms"]
    required_targets = primary_targets or target_names

    if not primary_targets and "comparative_terms" in target_names:
        for result in calculation_results:
            if _calculation_directly_compares_bound_values(result):
                _append_unique(calculation_matches["comparative_terms"], result.get("name"))

    unsupported_values = payload.get("unsupported_values") if isinstance(payload, dict) else []
    if not isinstance(unsupported_values, list):
        unsupported_values = []

    missing: list[str] = []
    for bucket in required_targets:
        unsupported_mentions_uncovered_target = any(
            _unsupported_value_blocks_target_bucket(
                value,
                bucket=bucket,
                calculation_results=calculation_results,
            )
            for value in unsupported_values
        )
        if requested_bound_applies.get(bucket):
            has_bound_support = requested_bound_valid.get(bucket) is True
        else:
            has_bound_support = bool(bound_matches.get(bucket))
        has_support = bool(has_bound_support or calculation_matches.get(bucket))
        if not has_support or unsupported_mentions_uncovered_target:
            missing.append(bucket)

    for bucket in required_targets:
        refs = (
            requested_bound_matches.get(bucket, [])
            if requested_bound_applies.get(bucket)
            else bound_matches.get(bucket, [])
        )
        for ref in refs:
            _append_unique(telemetry["target_metric_bound_value_refs"], ref)
        for ref in calculation_matches.get(bucket, []):
            _append_unique(telemetry["target_metric_calculation_refs"], ref)

    telemetry["target_metric_missing"] = missing
    telemetry["target_metric_evidence_found"] = bool(required_targets) and not missing
    telemetry["target_metric_shadow_would_block"] = (
        telemetry["target_metric_detected"] is True
        and telemetry["target_metric_evidence_found"] is False
    )
    if telemetry["target_metric_evidence_found"]:
        if telemetry["target_metric_calculation_refs"]:
            telemetry["target_metric_gate_reason"] = "target_metric_supported_by_calculation"
        else:
            telemetry["target_metric_gate_reason"] = "target_metric_supported_by_bound_value"
    elif not calculation_results and (
        not primary_targets or any(bucket in {"growth_change"} for bucket in required_targets)
    ):
        telemetry["target_metric_gate_reason"] = "no_calculation_results"
    else:
        telemetry["target_metric_gate_reason"] = "missing_target_metric_evidence"
    return telemetry


def _query_has_explicit_quantitative_metric_signal(query: str) -> bool:
    text = str(query or "")
    if _target_metric_text_matches(text, HIGH_STAKES_CLINICAL_METRIC_TERMS):
        return True
    if _target_metric_text_matches(text, HIGH_STAKES_DECISION_COMPARISON_TERMS):
        return True
    return bool(re.search(r"(?:\b\d+(?:\.\d+)?\b|%)", text))


def _query_has_patient_context_signal(query: str) -> bool:
    text = str(query or "")
    return any(pattern.search(text) for pattern in HIGH_STAKES_PATIENT_CONTEXT_PATTERNS)


def classify_high_stakes_quantitative_claim(
    *,
    query: str,
    payload: Any,
    calculation_telemetry: dict[str, Any],
    target_metric_telemetry: dict[str, Any],
) -> dict[str, Any]:
    text = str(query or "")
    medical_domain_signal = _target_metric_text_matches(
        text,
        HIGH_STAKES_MEDICAL_DOMAIN_TERMS,
    )
    clinical_metric_signal = _target_metric_text_matches(
        text,
        HIGH_STAKES_CLINICAL_METRIC_TERMS,
    )
    decision_or_comparison_signal = _target_metric_text_matches(
        text,
        HIGH_STAKES_DECISION_COMPARISON_TERMS,
    )
    patient_context_signal = _query_has_patient_context_signal(text)
    inferred_medical_domain_signal = clinical_metric_signal and patient_context_signal
    medical_domain_detected = medical_domain_signal or inferred_medical_domain_signal
    quantitative_or_comparative_signal = (
        clinical_metric_signal or decision_or_comparison_signal
    )

    calculation_requests = payload.get("calculations_requested") if isinstance(payload, dict) else []
    calculation_requested = isinstance(calculation_requests, list) and bool(calculation_requests)
    calculation_result_present = bool(calculation_telemetry.get("calculation_results_count")) or bool(
        calculation_telemetry.get("calculation_results")
    )
    target_metric_detected = target_metric_telemetry.get("target_metric_detected") is True
    explicit_metric_signal = _query_has_explicit_quantitative_metric_signal(text)
    quantitative_target_signal = (
        target_metric_detected
        or calculation_requested
        or calculation_result_present
        or explicit_metric_signal
    )

    reasons: list[str] = []
    if medical_domain_signal:
        reasons.append("medical_domain_signal")
    if patient_context_signal:
        reasons.append("patient_context_signal")
    if inferred_medical_domain_signal:
        reasons.append("clinical_metric_patient_context_signal")
    if clinical_metric_signal:
        reasons.append("clinical_metric_signal")
    if decision_or_comparison_signal:
        reasons.append("decision_or_comparison_signal")
    if target_metric_detected:
        reasons.append("target_metric_detected")
    if calculation_requested:
        reasons.append("calculation_requested")
    if calculation_result_present:
        reasons.append("calculation_result_present")
    if explicit_metric_signal and not target_metric_detected:
        reasons.append("explicit_quantitative_metric_signal")

    return {
        "detected": bool(
            medical_domain_detected
            and quantitative_or_comparative_signal
            and quantitative_target_signal
        ),
        "domain": "medical" if medical_domain_detected else None,
        "reasons": reasons,
    }


def validate_high_stakes_quantitative_shadow(
    *,
    query: str,
    payload: Any,
    schema_telemetry: dict[str, Any],
    source_binding_telemetry: dict[str, Any],
    calculation_telemetry: dict[str, Any],
    target_metric_telemetry: dict[str, Any],
) -> dict[str, Any]:
    telemetry = economist_high_stakes_quant_telemetry_defaults()
    _ = schema_telemetry, source_binding_telemetry
    classification = classify_high_stakes_quantitative_claim(
        query=query,
        payload=payload,
        calculation_telemetry=calculation_telemetry,
        target_metric_telemetry=target_metric_telemetry,
    )
    if not classification["detected"]:
        return telemetry

    telemetry.update(
        {
            "high_stakes_quant_detected": True,
            "high_stakes_quant_domain": classification["domain"],
            "high_stakes_quant_reasons": classification["reasons"],
            "high_stakes_quant_requires_analyst": True,
            "high_stakes_quant_shadow_mode": True,
            "high_stakes_quant_future_direct_use_allowed": False,
            "high_stakes_quant_gate_reason": "medical_quantitative_requires_analyst",
        }
    )
    return telemetry


def validate_high_stakes_quantitative_query_shadow(*, query: str) -> dict[str, Any]:
    return validate_high_stakes_quantitative_shadow(
        query=query,
        payload=None,
        schema_telemetry=economist_schema_telemetry_defaults(),
        source_binding_telemetry=economist_source_binding_telemetry_defaults(),
        calculation_telemetry=economist_calculation_telemetry_defaults(),
        target_metric_telemetry=economist_target_metric_telemetry_defaults(),
    )


def _compact_source_bound_values(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    source_bound_values = payload.get("source_bound_values")
    if not isinstance(source_bound_values, list):
        return []

    compact: list[dict[str, Any]] = []
    for item in source_bound_values:
        if not isinstance(item, dict):
            continue
        out: dict[str, Any] = {}
        for key in (
            "name",
            "metric",
            "entity",
            "subject",
            "company",
            "label",
            "value",
            "unit",
            "source_id",
            "timeframe",
            "period",
            "date",
            "year",
        ):
            if key in item:
                out[key] = item.get(key)
        if out:
            compact.append(out)
    return compact


def _compact_unsupported_values(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    unsupported_values = payload.get("unsupported_values")
    if not isinstance(unsupported_values, list):
        return []
    compact: list[str] = []
    for item in unsupported_values[:12]:
        text = str(item or "").strip()
        if text:
            compact.append(text[:240])
    return compact


def build_quantitative_packet_shadow(
    *,
    query: str,
    payload: Any,
    schema_telemetry: dict[str, Any],
    source_binding_telemetry: dict[str, Any],
    calculation_telemetry: dict[str, Any],
    target_metric_telemetry: dict[str, Any],
    high_stakes_telemetry: dict[str, Any],
) -> dict[str, Any]:
    telemetry = economist_quantitative_packet_telemetry_defaults()

    if target_metric_telemetry.get("target_metric_detected") is not True:
        telemetry["quantitative_packet_gate_reason"] = "not_quantitative"
        return telemetry

    validation_errors: list[str] = []
    if schema_telemetry.get("economist_schema_valid") is not True:
        validation_errors.append("schema_invalid")
    if source_binding_telemetry.get("source_binding_valid") is not True:
        validation_errors.append("source_binding_invalid")
    if target_metric_telemetry.get("target_metric_evidence_found") is not True:
        validation_errors.append("target_metric_evidence_missing")
    if int(calculation_telemetry.get("calculation_error_count") or 0) > 0:
        validation_errors.append("calculation_errors_present")
    if (
        int(calculation_telemetry.get("calculation_requests_count") or 0) > 0
        and calculation_telemetry.get("calculation_input_binding_valid") is not True
    ):
        validation_errors.append("calculation_input_binding_invalid")

    calculation_results = calculation_telemetry.get("calculation_results")
    if not isinstance(calculation_results, list):
        calculation_results = []

    source_ids_used = source_binding_telemetry.get("source_ids_used")
    if not isinstance(source_ids_used, list):
        source_ids_used = []

    target_metric_names = target_metric_telemetry.get("target_metric_names")
    if not isinstance(target_metric_names, list):
        target_metric_names = []

    target_metric_bound_value_refs = target_metric_telemetry.get(
        "target_metric_bound_value_refs"
    )
    if not isinstance(target_metric_bound_value_refs, list):
        target_metric_bound_value_refs = []

    target_metric_calculation_refs = target_metric_telemetry.get(
        "target_metric_calculation_refs"
    )
    if not isinstance(target_metric_calculation_refs, list):
        target_metric_calculation_refs = []

    packet_valid = not validation_errors
    high_stakes_detected = high_stakes_telemetry.get("high_stakes_quant_detected") is True
    direct_use_eligible = packet_valid and not high_stakes_detected
    requires_analyst = not direct_use_eligible
    if packet_valid and high_stakes_detected:
        gate_reason = "high_stakes_requires_analyst"
    elif packet_valid:
        gate_reason = "valid_non_high_stakes_packet"
    else:
        gate_reason = "packet_validation_failed"

    packet = {
        "schema_version": "quantitative_packet_v1",
        "query": str(query or ""),
        "economist_schema_version": schema_telemetry.get("economist_schema_version"),
        "source_ids_used": list(source_ids_used),
        "source_bound_values": _compact_source_bound_values(payload),
        "unsupported_values": _compact_unsupported_values(payload),
        "calculation_results": list(calculation_results),
        "target_metric_names": list(target_metric_names),
        "target_metric_bound_value_refs": list(target_metric_bound_value_refs),
        "target_metric_calculation_refs": list(target_metric_calculation_refs),
        "unsupported_values_count": int(
            schema_telemetry.get("unsupported_values_count") or 0
        ),
        "high_stakes_quant_detected": high_stakes_detected,
        "high_stakes_quant_domain": high_stakes_telemetry.get(
            "high_stakes_quant_domain"
        ),
        "requires_analyst": requires_analyst,
        "direct_use_eligible": direct_use_eligible,
        "validation_errors": list(validation_errors),
    }

    telemetry.update(
        {
            "quantitative_packet_present": True,
            "quantitative_packet_valid": packet_valid,
            "quantitative_packet_validation_errors": list(validation_errors),
            "quantitative_packet_direct_use_eligible": direct_use_eligible,
            "quantitative_packet_requires_analyst": requires_analyst,
            "quantitative_packet_shadow_mode": True,
            "quantitative_packet_gate_reason": gate_reason,
            "quantitative_packet": packet,
        }
    )
    return telemetry


def execute_economist_calculations_shadow(
    payload: Any,
    *,
    source_binding_valid: bool,
) -> dict[str, Any]:
    telemetry = economist_calculation_telemetry_defaults()
    if not isinstance(payload, dict):
        return telemetry

    requested = payload.get("calculations_requested")
    if not isinstance(requested, list):
        if "calculations_requested" in payload:
            telemetry["calculation_error_count"] += 1
            telemetry["calculation_input_binding_error_count"] += 1
            telemetry["calculation_error_summaries"].append("type:calculations_requested")
        return telemetry

    source_bound_values = payload.get("source_bound_values")
    if not isinstance(source_bound_values, list):
        if requested:
            telemetry["calculation_error_count"] += len(requested)
            telemetry["calculation_input_binding_error_count"] += 1
            telemetry["calculation_error_summaries"].append("type:source_bound_values")
        return telemetry

    values_by_name: dict[str, dict[str, Any]] = {}
    duplicate_names: set[str] = set()
    for item in source_bound_values:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        normalized = _normalize_calculation_ref(name)
        if not normalized:
            continue
        if normalized in values_by_name:
            duplicate_names.add(normalized)
            values_by_name.pop(normalized, None)
            continue
        if normalized not in duplicate_names:
            values_by_name[normalized] = item

    if duplicate_names:
        telemetry["calculation_input_binding_error_count"] += len(duplicate_names)
        for name in sorted(duplicate_names):
            telemetry["calculation_error_summaries"].append(f"duplicate_input_ref:{name}")

    if not source_binding_valid:
        if requested:
            telemetry["calculation_error_count"] += len(requested)
            telemetry["calculation_error_summaries"].append("source_binding_invalid")
        return telemetry

    for request in requested:
        telemetry["calculation_requests_count"] += 1
        if not isinstance(request, dict):
            telemetry["calculation_error_count"] += 1
            telemetry["calculation_input_binding_error_count"] += 1
            telemetry["calculation_error_summaries"].append("malformed:calculation_request")
            continue

        name = request.get("name")
        calculation_name = str(name).strip() if name is not None else ""
        function = ALLOWED_CALCULATIONS.get(calculation_name)
        if not function:
            telemetry["calculation_error_count"] += 1
            if calculation_name:
                telemetry["unsupported_calculation_names"].append(calculation_name)
            telemetry["calculation_error_summaries"].append("unsupported_calculation_name")
            continue

        args = request.get("args")
        if not isinstance(args, dict):
            telemetry["calculation_error_count"] += 1
            telemetry["calculation_input_binding_error_count"] += 1
            telemetry["calculation_error_summaries"].append("type:calculation_args")
            continue

        resolved_args: dict[str, float] = {}
        input_refs: dict[str, str] = {}
        unresolved_refs: list[str] = []
        duplicate_arg = ""
        for arg_name, ref in args.items():
            canonical_arg_name = _canonical_calculation_arg_name(
                calculation_name,
                arg_name,
            )
            if canonical_arg_name in input_refs:
                duplicate_arg = canonical_arg_name
                break
            ref_text = str(ref).strip() if ref is not None else ""
            input_refs[canonical_arg_name] = ref_text
            item = values_by_name.get(_normalize_calculation_ref(ref))
            if item is None:
                unresolved_refs.append(ref_text)
                continue
            try:
                resolved_args[canonical_arg_name] = sanitize_to_float(item.get("value"))
            except (TypeError, ValueError) as exc:
                telemetry["calculation_error_count"] += 1
                telemetry["calculation_input_binding_error_count"] += 1
                telemetry["calculation_error_summaries"].append(f"sanitize:{type(exc).__name__}")
                unresolved_refs = []
                break

        if duplicate_arg:
            telemetry["calculation_error_count"] += 1
            telemetry["calculation_input_binding_error_count"] += 1
            telemetry["calculation_error_summaries"].append(
                f"duplicate_calculation_arg:{duplicate_arg}"
            )
            continue
        if unresolved_refs:
            telemetry["calculation_error_count"] += 1
            telemetry["calculation_input_binding_error_count"] += len(unresolved_refs)
            telemetry["calculation_unresolved_input_refs"].extend(unresolved_refs)
            telemetry["calculation_error_summaries"].append("unresolved_input_ref")
            continue
        if len(resolved_args) != len(args):
            continue

        try:
            result = function(**resolved_args)
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            telemetry["calculation_error_count"] += 1
            telemetry["calculation_error_summaries"].append(
                str(exc) or type(exc).__name__
            )
            continue

        telemetry["calculation_success_count"] += 1
        telemetry["calculation_results"].append(
            {
                "name": calculation_name,
                "result": result,
                "input_refs": input_refs,
                **(
                    {"result_basis": "per_100g"}
                    if calculation_name == "normalize_per_100g"
                    else {}
                ),
            }
        )

    telemetry["calculation_results_count"] = len(telemetry["calculation_results"])
    telemetry["calculation_input_binding_valid"] = (
        telemetry["calculation_requests_count"] > 0
        and source_binding_valid
        and telemetry["calculation_input_binding_error_count"] == 0
        and not telemetry["calculation_unresolved_input_refs"]
    )
    return telemetry


def _economist_safety_telemetry(*, requested: bool) -> dict[str, Any]:
    return {
        "economist_code_execution_requested": requested,
        "economist_code_execution_blocked": requested,
        "economist_safety_status": "code_execution_disabled",
        "economist_skip_reason": ECONOMIST_CODE_EXECUTION_DISABLED_REASON if requested else None,
    }


def _economist_payload_requests_code(payload: dict[str, Any]) -> bool:
    code_keys = {
        "python_code",
        "code",
        "script",
        "shell",
        "shell_command",
        "bash",
        "executable_code",
    }

    def _value_requests_code(value: Any) -> bool:
        if isinstance(value, str):
            text = value.casefold()
            if "```" in text or text.lstrip().startswith("#!"):
                return True
            command_flag = "-" + "c"
            dynamic_call_patterns = [
                "subprocess",
                r"os\.system",
                r"eval\s*\(",
                r"exec\s*\(",
                rf"python\s+{re.escape(command_flag)}",
                rf"bash\s+{re.escape(command_flag)}",
                rf"sh\s+{re.escape(command_flag)}",
            ]
            return bool(re.search("|".join(dynamic_call_patterns), text))
        if isinstance(value, dict):
            return any(_item_requests_code(k, v) for k, v in value.items())
        if isinstance(value, list):
            return any(_value_requests_code(item) for item in value)
        return False

    def _item_requests_code(key: Any, value: Any) -> bool:
        key_text = str(key).strip().casefold()
        if key_text in code_keys and str(value or "").strip():
            return True
        return _value_requests_code(value)

    return any(_item_requests_code(key, value) for key, value in payload.items())


def collect_allowed_source_ids(all_passages: list) -> set[str]:
    source_ids: set[str] = set()
    for passage in all_passages or []:
        if not isinstance(passage, dict) or "source_id" not in passage:
            continue
        source_id = passage.get("source_id")
        source_id_text = str(source_id).strip() if source_id is not None else ""
        if source_id_text:
            source_ids.add(source_id_text)
    return source_ids


def economist_evidence_source_window_telemetry(
    evidence_passages: list,
    source_ids_used: list[str] | set[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    evidence_source_ids = collect_allowed_source_ids(evidence_passages)
    used_ids = {
        str(source_id).strip()
        for source_id in (source_ids_used or [])
        if str(source_id).strip()
    }
    return {
        "economist_evidence_source_ids_seen": sorted(evidence_source_ids),
        "economist_evidence_source_ids_used": sorted(used_ids & evidence_source_ids),
        "economist_source_ids_used_outside_evidence_window": sorted(
            used_ids - evidence_source_ids
        ),
    }


BOUNDED_QUANT_RETRIEVAL_REPORT_TYPES = frozenset(
    {
        "quantitative_comparison",
        "benchmark",
    }
)

QUANT_RETRIEVAL_PROXY_METRIC_TERMS = (
    "load factor",
    "revenue",
    "sales",
    "profit",
    "margin",
    "earnings",
    "volume",
    "capacity",
    "usage",
    "users",
    "share",
    "rating",
    "rank",
    "score",
)

def _quant_value_text(value: Any) -> str:
    return str(value or "").strip()


def _quant_unique(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _quant_value_text(item)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def _quant_passage_get(passage: Any, key: str) -> Any:
    if isinstance(passage, dict):
        return passage.get(key)
    return getattr(passage, key, None)


def _quant_passage_text(passage: Any) -> str:
    fields = (
        _quant_passage_get(passage, "title"),
        _quant_passage_get(passage, "text"),
        _quant_passage_get(passage, "snippet"),
        _quant_passage_get(passage, "url"),
        _quant_passage_get(passage, "domain"),
    )
    return " ".join(_quant_value_text(field) for field in fields if _quant_value_text(field))


def _quant_source_bound_values(
    *,
    economist_safety_telemetry: dict[str, Any] | None,
    source_bound_values: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if isinstance(source_bound_values, list):
        return [item for item in source_bound_values if isinstance(item, dict)]

    packet = None
    if isinstance(economist_safety_telemetry, dict):
        packet = economist_safety_telemetry.get("quantitative_packet")
    if not isinstance(packet, dict):
        return []
    values = packet.get("source_bound_values")
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)]


def _quant_source_value_text(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    parts: list[str] = []
    for key in (
        "name",
        "metric",
        "unit",
        "entity",
        "subject",
        "company",
        "label",
        "timeframe",
        "period",
        "date",
        "year",
        "value",
    ):
        value = item.get(key)
        if isinstance(value, (str, int, float)):
            parts.append(str(value))
    return " ".join(parts)


def _quant_source_value_subjects(source_bound_values: list[dict[str, Any]]) -> list[str]:
    subjects: list[str] = []
    for item in source_bound_values:
        for key in ("entity", "subject", "company", "label"):
            value = _quant_value_text(item.get(key))
            if value:
                subjects.append(value)
    return _quant_unique(subjects)


def _quant_metric_terms() -> tuple[str, ...]:
    terms: list[str] = []
    for bucket_terms in TARGET_METRIC_BUCKETS.values():
        terms.extend(bucket_terms)
    terms.extend(QUANT_RETRIEVAL_PROXY_METRIC_TERMS)
    return tuple(_quant_unique(terms))


def _quant_subject_context_start(text: str) -> int | None:
    patterns = (
        r"\b(?:on|for|in|during|over|through|by)\s+"
        r"(?:(?:fiscal|calendar)\s+year\s+|(?:fiscal|calendar)\s+|fy\s*)?"
        r"(?:19|20)\d{2}\b",
        r"\b(?:on|for|in|during|over|through|by)\s+"
        r"(?:q[1-4]\s*(?:fy\s*)?(?:19|20)\d{2}|(?:19|20)\d{2}\s*q[1-4])\b",
        r"\bas\s+of\s+(?:19|20)\d{2}\b",
        r"\b(?:on|for|in|during|over|through|by)\s+"
        r"(?:last|past|previous|trailing)\s+\d+\s+"
        r"(?:quarters?|years?|months?)\b",
    )
    starts = [
        match.start()
        for pattern in patterns
        for match in re.finditer(pattern, text, flags=re.I)
    ]
    return min(starts) if starts else None


def _quant_clean_subject(candidate: str) -> str:
    text = re.sub(r"\s+", " ", _quant_value_text(candidate).strip(" \t\r\n'\""))
    text = re.sub(r"^(?:compare|benchmark|between|the|a|an)\s+", "", text, flags=re.I)
    metric_terms = _quant_metric_terms()
    earliest: int | None = None
    for term in metric_terms:
        if not term:
            continue
        m = re.search(rf"\b{re.escape(term)}\b", text, flags=re.I)
        if m and (earliest is None or m.start() < earliest):
            earliest = m.start()
    context_start = _quant_subject_context_start(text)
    if context_start is not None and (
        earliest is None or context_start < earliest
    ):
        earliest = context_start
    if earliest is not None:
        text = text[:earliest]
    text = re.sub(
        r"\b(?:on|for|by|in|over|during|using|based|across|against|with)\s*$",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\b(?:(?:fiscal|calendar)\s+year\s+|(?:fiscal|calendar)\s+|fy\s*)?(?:19|20)\d{2}\s*$",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\b(?:q[1-4]|fy|fiscal|calendar|year|quarter|quarters?)\s*$", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" ,.;:!?()[]{}")
    if not text or len(text.split()) > 8:
        return ""
    if re.fullmatch(r"(?:and|or|vs\.?|versus|with|against)", text, flags=re.I):
        return ""
    return text


def _quant_query_comparison_subjects(query: str) -> list[str]:
    text = _quant_value_text(query)
    if not text:
        return []

    patterns = (
        r"\bcompare\s+(.+?)\s+(?:vs\.?|versus|against|with|and)\s+(.+?)(?:[?.;,]|$)",
        r"\bbenchmark\s+(.+?)\s+(?:vs\.?|versus|against|with|and)\s+(.+?)(?:[?.;,]|$)",
        r"\bbetween\s+(.+?)\s+and\s+(.+?)(?:[?.;,]|$)",
        r"^(.+?)\s+(?:vs\.?|versus)\s+(.+?)(?:[?.;,]|$)",
    )
    subjects: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if not match:
            continue
        left = _quant_clean_subject(match.group(1))
        right = _quant_clean_subject(match.group(2))
        if left and right:
            subjects.extend([left, right])
            break
    return _quant_unique(subjects)


def _quant_requested_metrics(
    *,
    query: str,
    economist_safety_telemetry: dict[str, Any] | None,
    target_metric_names: list[str] | None,
) -> list[str]:
    metrics: list[str] = []
    if isinstance(target_metric_names, list):
        metrics.extend(str(item) for item in target_metric_names)
    if isinstance(economist_safety_telemetry, dict):
        existing = economist_safety_telemetry.get("target_metric_names")
        if isinstance(existing, list):
            metrics.extend(str(item) for item in existing)
        packet = economist_safety_telemetry.get("quantitative_packet")
        if isinstance(packet, dict):
            packet_metrics = packet.get("target_metric_names")
            if isinstance(packet_metrics, list):
                metrics.extend(str(item) for item in packet_metrics)
    if not _quant_unique(metrics):
        metrics.extend(detect_target_metric_buckets(query))
    return _quant_unique(metrics)


def _quant_metric_bucket_covered(
    *,
    metric: str,
    evidence_text: str,
    source_bound_values: list[dict[str, Any]],
) -> bool:
    metric_key = _quant_value_text(metric)
    if not metric_key:
        return False
    if metric_key in TARGET_METRIC_BUCKETS:
        if any(
            _quant_source_bound_value_matches_metric(item, metric_key)
            for item in source_bound_values
        ):
            return True
        return _target_metric_text_matches(evidence_text, TARGET_METRIC_BUCKETS[metric_key])
    if metric_key in NUTRITION_METRIC_TERMS:
        terms = NUTRITION_METRIC_TERMS[metric_key]
        if any(
            _target_metric_text_matches(_quant_source_value_text(item), terms)
            for item in source_bound_values
        ):
            return True
        return _target_metric_text_matches(evidence_text, terms)
    return _target_metric_text_matches(evidence_text, (metric_key,))


def _quant_source_bound_value_matches_metric(item: Any, bucket: str) -> bool:
    if not isinstance(item, dict):
        return False
    if bucket == "price_cost_rate":
        haystack = " ".join(
            str(item.get(key) or "") for key in ("name", "metric", "label", "unit")
        )
        return _target_metric_text_matches(
            haystack,
            TARGET_METRIC_PRICE_COST_SUPPORT_TERMS,
        )
    return _source_bound_value_matches_bucket(item, bucket)


def _quant_metric_source_bound_values(
    *,
    metrics: list[str],
    source_bound_values: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    requested = [metric for metric in metrics if metric != "comparative_terms"]
    if not requested:
        return list(source_bound_values)
    return [
        item
        for item in source_bound_values
        if any(
            _quant_source_bound_value_matches_metric(item, metric)
            for metric in requested
        )
    ]


def _quant_metric_coverage(
    *,
    metrics: list[str],
    evidence_text: str,
    source_bound_values: list[dict[str, Any]],
) -> tuple[bool, bool]:
    requested = [metric for metric in metrics if metric != "comparative_terms"] or list(metrics)
    if not requested:
        return False, False

    covered = [
        metric
        for metric in requested
        if _quant_metric_bucket_covered(
            metric=metric,
            evidence_text=evidence_text,
            source_bound_values=source_bound_values,
        )
    ]
    valid = len(covered) == len(requested)
    proxy_detected = False
    if not valid:
        requested_set = {metric for metric in requested}
        proxy_terms: list[str] = list(QUANT_RETRIEVAL_PROXY_METRIC_TERMS)
        for bucket, terms in TARGET_METRIC_BUCKETS.items():
            if bucket not in requested_set and bucket != "comparative_terms":
                proxy_terms.extend(terms)
        proxy_detected = _target_metric_text_matches(evidence_text, tuple(_quant_unique(proxy_terms)))
    return valid, proxy_detected


def _quant_normalized_haystack(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(text or "").casefold()))


def _quant_phrase_in_text(phrase: str, text: str) -> bool:
    phrase_tokens = re.findall(r"[a-z0-9]+", str(phrase or "").casefold())
    if not phrase_tokens:
        return False
    haystack = _quant_normalized_haystack(text)
    phrase_text = " ".join(phrase_tokens)
    if len(phrase_tokens) == 1:
        return bool(re.search(rf"\b{re.escape(phrase_text)}\b", haystack))
    return phrase_text in haystack


def _quant_normalize_timeframe(value: str) -> str:
    text = _quant_value_text(value).casefold()
    text = re.sub(r"\s+", " ", text)
    m = re.fullmatch(r"q([1-4])\s*(?:fy\s*)?((?:19|20)\d{2})", text)
    if m:
        return f"q{m.group(1)} {m.group(2)}"
    m = re.fullmatch(r"((?:19|20)\d{2})\s*q([1-4])", text)
    if m:
        return f"q{m.group(2)} {m.group(1)}"
    m = re.fullmatch(
        r"(?:fy|fiscal(?: year)?|calendar(?: year)?|annual|year)\s*((?:19|20)\d{2})",
        text,
    )
    if m:
        return m.group(1)
    return text


def _quant_extract_timeframes(text: str) -> list[str]:
    raw = _quant_value_text(text).replace("_", " ")
    if not raw:
        return []

    ranges = re.findall(
        r"\b(?:19|20)\d{2}\s*(?:-|to|through|thru|\u2013|\u2014)\s*(?:19|20)\d{2}\b",
        raw,
        flags=re.I,
    )
    quarters = re.findall(
        r"\b(?:q[1-4]\s*(?:fy\s*)?(?:19|20)\d{2}|(?:19|20)\d{2}\s*q[1-4])\b",
        raw,
        flags=re.I,
    )
    relatives = re.findall(
        r"\b(?:last|past|previous|trailing)\s+\d+\s+(?:quarters?|years?|months?)\b",
        raw,
        flags=re.I,
    )
    if ranges or quarters or relatives:
        return _quant_unique(
            [_quant_normalize_timeframe(item) for item in ranges + quarters + relatives]
        )
    annuals = re.findall(
        r"\b(?:fy|fiscal(?:\s+year)?|calendar(?:\s+year)?|annual|year)?\s*((?:19|20)\d{2})\b",
        raw,
        flags=re.I,
    )
    return _quant_unique(annuals)


def _quant_source_value_timeframe_text(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    return " ".join(
        _quant_value_text(item.get(key)).replace("_", " ")
        for key in ("timeframe", "period", "year", "date", "name")
        if _quant_value_text(item.get(key))
    )


def _quant_timeframe_is_annual_year(timeframe: str) -> bool:
    return bool(re.fullmatch(r"(?:19|20)\d{2}", _quant_normalize_timeframe(timeframe)))


def _quant_timeframe_is_quarter(timeframe: str) -> bool:
    return bool(re.fullmatch(r"q[1-4]\s+(?:19|20)\d{2}", _quant_normalize_timeframe(timeframe)))


def _quant_source_value_matches_timeframe(item: Any, timeframe: str) -> bool:
    requested = _quant_normalize_timeframe(timeframe)
    text = _quant_source_value_timeframe_text(item)
    if not requested or not text:
        return False
    if _quant_timeframe_is_quarter(requested):
        return requested in _quant_extract_timeframes(text)
    if _quant_timeframe_is_annual_year(requested):
        quarter_for_year = re.search(
            rf"\b(?:q[1-4]\s*(?:fy\s*)?{re.escape(requested)}|"
            rf"{re.escape(requested)}\s*q[1-4])\b",
            text,
            flags=re.I,
        )
        if quarter_for_year:
            return False
        return bool(
            re.search(
                rf"\b(?:(?:fy|fiscal(?:\s+year)?|calendar(?:\s+year)?|annual|year)\s*)?"
                rf"{re.escape(requested)}\b",
                text,
                flags=re.I,
            )
        )
    return requested in _quant_extract_timeframes(text)


def _quant_source_value_matches_subject(item: Any, subject: str) -> bool:
    return _quant_phrase_in_text(subject, _quant_source_value_text(item))


def _source_bound_value_has_numeric_value(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    value = item.get("value")
    try:
        sanitize_to_float(value)
        return True
    except ValueError:
        pass
    text = _quant_value_text(value)
    if not text:
        return False
    if re.search(r"\d\s*(?:-|to|through|thru|\u2013|\u2014)\s*\d", text, flags=re.I):
        return False
    return bool(re.search(r"\d", text))


def _source_bound_value_is_requested_candidate(item: Any, bucket: str) -> bool:
    if not isinstance(item, dict):
        return False
    if _source_bound_value_declares_unsupported(item):
        return False
    if not _quant_value_text(item.get("source_id")):
        return False
    if not _quant_value_text(item.get("value")):
        return False
    if not _quant_source_bound_value_matches_metric(item, bucket):
        return False
    if bucket != "date_duration_timeline" and not _source_bound_value_has_numeric_value(item):
        return False
    return True


def _target_metric_requested_bound_value_refs(
    *,
    query: str,
    bucket: str,
    source_bound_values: list[dict[str, Any]],
) -> tuple[bool, list[str], bool]:
    if bucket not in TARGET_METRIC_BOUND_BUCKETS:
        return False, [], False
    subjects = _quant_query_comparison_subjects(query)
    if len(subjects) < 2:
        subjects = []
    timeframes = _quant_extract_timeframes(query)
    if not subjects and not timeframes:
        return False, [], False

    subject_requirements = subjects or [""]
    timeframe_requirements = timeframes or [""]
    refs: list[str] = []
    required_slot_count = len(subject_requirements) * len(timeframe_requirements)
    for subject in subject_requirements:
        for timeframe in timeframe_requirements:
            slot_refs: list[str] = []
            for item in source_bound_values:
                if not _source_bound_value_is_requested_candidate(item, bucket):
                    continue
                if subject and not _quant_source_value_matches_subject(item, subject):
                    continue
                if timeframe and not _quant_source_value_matches_timeframe(item, timeframe):
                    continue
                _append_unique(slot_refs, item.get("name"))
            if not slot_refs:
                return True, refs, False
            for ref in slot_refs:
                _append_unique(refs, ref)

    return True, refs, len(refs) >= required_slot_count


def _quant_source_bound_timeframe_coverage(
    *,
    query_timeframes: list[str],
    subjects: list[str],
    source_bound_values: list[dict[str, Any]],
) -> bool:
    if not query_timeframes:
        return True
    values_with_timeframes = [
        item
        for item in source_bound_values
        if _quant_source_value_timeframe_text(item)
    ]
    if not values_with_timeframes:
        return False

    subject_scoped = (
        [
            subject
            for subject in subjects
            if any(
                _quant_source_value_matches_subject(item, subject)
                for item in values_with_timeframes
            )
        ]
        if subjects
        else []
    )
    if subject_scoped:
        return all(
            all(
                any(
                    _quant_source_value_matches_subject(item, subject)
                    and _quant_source_value_matches_timeframe(item, timeframe)
                    for item in values_with_timeframes
                )
                for timeframe in query_timeframes
            )
            for subject in subjects
        )
    return all(
        any(
            _quant_source_value_matches_timeframe(item, timeframe)
            for item in values_with_timeframes
        )
        for timeframe in query_timeframes
    )


def _quant_evidence_source_maps(passages: list[Any]) -> tuple[set[str], dict[str, str]]:
    source_ids: set[str] = set()
    domains_by_source_id: dict[str, str] = {}
    for passage in passages or []:
        source_id = _quant_passage_get(passage, "source_id")
        source_id_text = _quant_value_text(source_id)
        if not source_id_text:
            continue
        source_ids.add(source_id_text)
        url = _quant_value_text(_quant_passage_get(passage, "url"))
        domain = _quant_value_text(_quant_passage_get(passage, "domain"))
        domains_by_source_id[source_id_text] = (
            normalize_source_domain(url) or domain.casefold() or source_id_text
        )
    return source_ids, domains_by_source_id


def _quant_value_source_binding(
    *,
    passages: list[Any],
    source_bound_values: list[dict[str, Any]],
) -> tuple[bool, list[str], int]:
    evidence_source_ids, domains_by_source_id = _quant_evidence_source_maps(passages)
    value_source_ids: list[str] = []
    source_domains: list[str] = []
    binding_missing = False

    for item in source_bound_values:
        source_id = _quant_value_text(item.get("source_id"))
        if not source_id:
            binding_missing = True
            continue
        value_source_ids.append(source_id)
        if source_id not in evidence_source_ids:
            binding_missing = True
        domain = domains_by_source_id.get(source_id) or _quant_value_text(item.get("domain"))
        url = _quant_value_text(item.get("url"))
        if not domain and url:
            domain = normalize_source_domain(url)
        if domain:
            source_domains.append(domain)

    unique_source_ids = _quant_unique(value_source_ids)
    if source_domains:
        source_diversity_count = len({domain.casefold() for domain in source_domains if domain})
    else:
        source_diversity_count = len(unique_source_ids)
    exact_binding_valid = bool(source_bound_values) and bool(unique_source_ids) and not binding_missing
    return exact_binding_valid, unique_source_ids, source_diversity_count


def _quant_retrieval_sufficiency_gate_reason(blockers: list[str]) -> str:
    if not blockers:
        return "sufficient_shadow_only"
    if "nutrition_value_source_binding_missing" in blockers:
        return "blocked_by_nutrition_value_source_binding"
    if (
        "nutrition_metrics_missing" in blockers
        or "nutrition_partial_macro_coverage" in blockers
    ):
        return "blocked_by_nutrition_metric_coverage"
    if "proxy_metric_only" in blockers:
        return "blocked_by_proxy_metric"
    if "value_source_binding_missing" in blockers:
        return "blocked_by_value_source_binding"
    if "timeframe_missing" in blockers:
        return "blocked_by_missing_timeframe_coverage"
    if "missing_comparison_coverage" in blockers or "comparison_subjects_unknown" in blockers:
        return "blocked_by_missing_comparison_coverage"
    if "missing_entity_coverage" in blockers:
        return "blocked_by_missing_entity_coverage"
    if "missing_metric_coverage" in blockers:
        return "blocked_by_missing_metric_coverage"
    if "low_source_diversity" in blockers:
        return "blocked_by_low_source_diversity"
    return "blocked_by_multiple_reasons"


def _quant_retrieval_sufficiency_shadow_telemetry(
    *,
    query: str,
    report_type: str,
    final_top_evidence: list[Any],
    economist_safety_telemetry: dict[str, Any] | None = None,
    source_bound_values: list[dict[str, Any]] | None = None,
    target_metric_names: list[str] | None = None,
    nutrition_lookup_telemetry: dict[str, Any] | None = None,
    nutrition_lookup_entity: str | None = None,
    router_entities: list[str] | None = None,
) -> dict[str, Any]:
    telemetry = quant_retrieval_sufficiency_telemetry_defaults()
    normalized_report_type = str(report_type or "").strip().lower()
    if normalized_report_type not in BOUNDED_QUANT_RETRIEVAL_REPORT_TYPES:
        return telemetry

    passages = list(final_top_evidence or [])
    values = _quant_source_bound_values(
        economist_safety_telemetry=economist_safety_telemetry,
        source_bound_values=source_bound_values,
    )
    passage_text = " ".join(_quant_passage_text(passage) for passage in passages)
    value_text = " ".join(_quant_source_value_text(item) for item in values)
    coverage_text = f"{passage_text} {value_text}".strip()

    nutrition_lookup = (
        nutrition_lookup_telemetry
        if isinstance(nutrition_lookup_telemetry, dict)
        else detect_nutrition_lookup_telemetry(query)
    )
    nutrition_lookup_detected = bool(nutrition_lookup.get("nutrition_lookup_detected"))
    nutrition_metrics = [
        str(item)
        for item in nutrition_lookup.get("nutrition_lookup_metrics_requested", [])
        if str(item or "").strip()
    ]

    router_subjects = _quant_unique(
        [
            cleaned
            for item in (router_entities or [])
            if (cleaned := _quant_clean_subject(str(item)))
        ]
    )
    query_subjects = (
        router_subjects
        if len(router_subjects) >= 2
        else _quant_query_comparison_subjects(query)
    )
    value_subjects = _quant_source_value_subjects(values)
    nutrition_subjects = [nutrition_lookup_entity] if nutrition_lookup_entity else []
    subjects = _quant_unique(query_subjects + value_subjects + nutrition_subjects)
    metrics = _quant_requested_metrics(
        query=query,
        economist_safety_telemetry=economist_safety_telemetry,
        target_metric_names=target_metric_names,
    )
    if nutrition_lookup_detected and nutrition_metrics:
        metrics = _quant_unique(nutrition_metrics)
    query_timeframes = _quant_extract_timeframes(query)
    metric_coverage_valid, proxy_metric_detected = _quant_metric_coverage(
        metrics=metrics,
        evidence_text=coverage_text,
        source_bound_values=values,
    )
    entity_coverage_valid = bool(subjects) and all(
        _quant_phrase_in_text(subject, coverage_text) for subject in subjects
    )
    comparison_coverage_valid = True if nutrition_lookup_detected else entity_coverage_valid
    metric_values = _quant_metric_source_bound_values(
        metrics=metrics,
        source_bound_values=values,
    )
    timeframe_values = metric_values or values
    timeframe_coverage_valid = (
        True
        if query_timeframes and not entity_coverage_valid
        else (
            _quant_source_bound_timeframe_coverage(
                query_timeframes=query_timeframes,
                subjects=subjects,
                source_bound_values=timeframe_values,
            )
            if query_timeframes
            and timeframe_values
            else (
                all(
                    timeframe in _quant_extract_timeframes(coverage_text)
                    for timeframe in query_timeframes
                )
                if query_timeframes
                else True
            )
        )
    )
    exact_binding_valid, value_source_ids, source_diversity_count = (
        _quant_value_source_binding(passages=passages, source_bound_values=values)
    )

    blockers: list[str] = []
    if nutrition_lookup_detected:
        if not entity_coverage_valid:
            blockers.append("missing_entity_coverage")
    elif not subjects:
        blockers.append("comparison_subjects_unknown")
    elif not entity_coverage_valid:
        blockers.append("missing_entity_coverage")
        blockers.append("missing_comparison_coverage")
    if not metric_coverage_valid:
        if nutrition_lookup_detected:
            blockers.append("nutrition_metrics_missing")
            blockers.append("nutrition_partial_macro_coverage")
        else:
            blockers.append("missing_metric_coverage")
        if proxy_metric_detected:
            blockers.append("proxy_metric_only")
    if query_timeframes and not timeframe_coverage_valid:
        blockers.append("timeframe_missing")
    if not exact_binding_valid:
        blockers.append(
            "nutrition_value_source_binding_missing"
            if nutrition_lookup_detected
            else "value_source_binding_missing"
        )
    if len(subjects) >= 2 and value_source_ids and source_diversity_count <= 1:
        blockers.append("low_source_diversity")

    blockers = _quant_unique(blockers)
    sufficiency_valid = not blockers
    telemetry.update(
        {
            "quant_retrieval_target_detected": True,
            "quant_retrieval_entities": list(subjects),
            "quant_retrieval_metrics": list(metrics),
            "quant_retrieval_timeframes": list(query_timeframes),
            "quant_retrieval_comparison_subjects": (
                [] if nutrition_lookup_detected else list(subjects)
            ),
            "quant_retrieval_entity_coverage_valid": entity_coverage_valid,
            "quant_retrieval_metric_coverage_valid": metric_coverage_valid,
            "quant_retrieval_timeframe_coverage_valid": timeframe_coverage_valid,
            "quant_retrieval_comparison_coverage_valid": comparison_coverage_valid,
            "quant_retrieval_source_diversity_count": source_diversity_count,
            "quant_retrieval_exact_value_binding_valid": exact_binding_valid,
            "quant_retrieval_proxy_metric_detected": proxy_metric_detected,
            "quant_retrieval_value_source_ids": list(value_source_ids),
            "quant_retrieval_sufficiency_valid": sufficiency_valid,
            "quant_retrieval_sufficiency_blockers": blockers,
            "quant_retrieval_sufficiency_gate_reason": (
                _quant_retrieval_sufficiency_gate_reason(blockers)
            ),
            "quant_retrieval_sufficiency_shadow_mode": True,
        }
    )
    return telemetry


def validate_economist_schema_v1(payload: Any) -> dict[str, Any]:
    telemetry = economist_schema_telemetry_defaults()
    invalid_fields: list[str] = []

    if not isinstance(payload, dict):
        invalid_fields.append("schema_error:not_object")
        telemetry["economist_invalid_fields"] = invalid_fields
        return telemetry

    version = payload.get("schema_version")
    if version == ECONOMIST_SCHEMA_VERSION:
        telemetry["economist_schema_version"] = ECONOMIST_SCHEMA_VERSION
    else:
        invalid_fields.append("schema_version")

    missing = sorted(ECONOMIST_SCHEMA_REQUIRED_KEYS - set(payload.keys()))
    invalid_fields.extend(f"missing:{key}" for key in missing)

    field_type_checks = {
        "schema_version": str,
        "variables": list,
        "source_bound_values": list,
        "assumptions": list,
        "calculations_requested": list,
        "confidence": str,
        "unsupported_values": list,
    }
    for field, expected_type in field_type_checks.items():
        if field in payload and not isinstance(payload.get(field), expected_type):
            invalid_fields.append(f"type:{field}")

    confidence = payload.get("confidence")
    if isinstance(confidence, str) and confidence not in {"low", "medium", "high"}:
        invalid_fields.append("value:confidence")

    unsupported_values = payload.get("unsupported_values")
    if isinstance(unsupported_values, list):
        telemetry["unsupported_values_count"] = len(unsupported_values)

    telemetry["economist_schema_valid"] = not invalid_fields
    telemetry["economist_invalid_fields"] = invalid_fields
    return telemetry


def validate_economist_source_bindings(
    payload: Any,
    allowed_source_ids: set[str],
) -> dict[str, Any]:
    allowed = {str(source_id).strip() for source_id in (allowed_source_ids or set())}
    allowed.discard("")
    telemetry = economist_source_binding_telemetry_defaults(allowed)
    invalid_fields: list[str] = []
    source_ids_used: set[str] = set()
    missing_source_id_count = 0
    unknown_source_id_count = 0
    malformed_count = 0

    if not isinstance(payload, dict):
        invalid_fields.append("schema_error:not_object")
        telemetry["source_binding_invalid_fields"] = invalid_fields
        return telemetry

    source_bound_values = payload.get("source_bound_values")
    if not isinstance(source_bound_values, list):
        invalid_fields.append("type:source_bound_values")
        telemetry["source_binding_invalid_fields"] = invalid_fields
        return telemetry

    telemetry["source_bound_value_count"] = len(source_bound_values)
    for idx, item in enumerate(source_bound_values):
        item_path = f"source_bound_values[{idx}]"
        if not isinstance(item, dict):
            malformed_count += 1
            invalid_fields.append(f"malformed:{item_path}")
            continue

        for field in ("name", "value"):
            value = item.get(field)
            if value is None or not str(value).strip():
                invalid_fields.append(f"missing:{item_path}.{field}")

        source_id = item.get("source_id")
        source_id_text = str(source_id).strip() if source_id is not None else ""
        if not source_id_text:
            missing_source_id_count += 1
            invalid_fields.append(f"missing:{item_path}.source_id")
            continue

        source_ids_used.add(source_id_text)
        if source_id_text not in allowed:
            unknown_source_id_count += 1
            invalid_fields.append(f"unknown_source_id:{item_path}.source_id")

    telemetry["source_binding_valid"] = not invalid_fields
    telemetry["source_binding_invalid_fields"] = invalid_fields
    telemetry["source_binding_missing_source_id_count"] = missing_source_id_count
    telemetry["source_binding_unknown_source_id_count"] = unknown_source_id_count
    telemetry["source_binding_malformed_count"] = malformed_count
    telemetry["source_ids_used"] = sorted(source_ids_used)
    return telemetry


def run_economist_code(python_code: str, timeout: int = 10) -> dict:
    requested = bool(str(python_code or "").strip())
    if requested:
        logger.warning("[ECONOMIST] Dynamic code execution blocked")
    return {
        "computed": {},
        "error": ECONOMIST_CODE_EXECUTION_DISABLED_REASON if requested else None,
        "economist_code_execution_requested": requested,
        "economist_code_execution_blocked": requested,
        "economist_safety_status": "code_execution_disabled",
        "economist_skip_reason": ECONOMIST_CODE_EXECUTION_DISABLED_REASON if requested else None,
    }


def _economist_response_is_abort(raw: str, cleaned: str) -> bool:
    for fragment in (raw, cleaned):
        t = (fragment or "").strip().strip('"').strip("'")
        if t == "ABORT_ECONOMIST":
            return True
    return False


def run_economist_step(
    core_topic: str,
    all_passages: list,
    current_date: str,
    ask_model: Callable[..., str],
    clean_json_response: Callable[[str], str],
    default_system: Dict[str, str],
    provider: str = "OpenAI",
    model: str = "gpt-5.4-mini",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    scout_context: Optional[dict] = None,
    complexity: str = "medium",
    corpus_weak: bool = False,
    corpus_state: Optional[str] = None,
    safety_telemetry: Optional[dict[str, Any]] = None,
    user_query: Optional[str] = None,
) -> Optional[str]:
    allowed_source_ids = collect_allowed_source_ids(all_passages)
    economist_evidence_passages = list((all_passages or [])[:20])
    economist_evidence_telemetry = economist_evidence_source_window_telemetry(
        economist_evidence_passages
    )
    if safety_telemetry is not None:
        safety_telemetry.update(_economist_safety_telemetry(requested=False))
        safety_telemetry.update(economist_schema_telemetry_defaults())
        safety_telemetry.update(economist_source_binding_telemetry_defaults(allowed_source_ids))
        safety_telemetry.update(economist_evidence_telemetry)
        safety_telemetry.update(economist_calculation_telemetry_defaults())
        safety_telemetry.update(economist_high_stakes_quant_telemetry_defaults())
        safety_telemetry.update(economist_quantitative_packet_telemetry_defaults())

    _cs = (corpus_state or "").strip()
    if corpus_weak or _cs == "ESTIMATE_FROM_PRIORS":
        return None

    evidence_snippet = "\n".join(
        f"- [{p.get('source_id', '?')}] {(p.get('snippet') or p.get('text') or '')[:200]}"
        for p in economist_evidence_passages
    )
    scout_block = ""
    if scout_context:
        normalization_requirements = scout_context.get("normalization_inputs", [])
        if not normalization_requirements and scout_context.get("normalization_requirements"):
            normalization_requirements = [
                {
                    "variable": item.get("variable", ""),
                    "reason": item.get("reason", ""),
                }
                for item in scout_context.get("normalization_requirements", [])
                if isinstance(item, dict)
            ]
        hidden_dependencies = scout_context.get("hidden_dependencies", [])
        if not hidden_dependencies and scout_context.get("primary_variables_present"):
            hidden_dependencies = scout_context.get("primary_variables_present", [])
        data_vintage = scout_context.get("data_vintage", scout_context.get("time_period", "not specified"))
        assumption_risks = scout_context.get("assumption_risks", scout_context.get("validity_risks", []))
        scout_block = (
            "\nSCOUT ANALYSIS (pre-validated evidence requirements):\n"
            f"- Normalization required: {normalization_requirements}\n"
            f"- Hidden dependencies: {hidden_dependencies}\n"
            f"- Data vintage: {data_vintage}\n"
            f"- Assumption risks if missing: {assumption_risks}\n\n"
            "Use the above to validate your model assumptions. If required normalization inputs are absent from the evidence, "
            "declare that assumption explicitly and flag the output as ASSUMPTION-DEPENDENT.\n"
        )
    _cx = (complexity or "medium").strip().lower() or "medium"
    _budget = economist_budget_for_complexity(_cx)
    # Tier-tune reasoning effort to research complexity instead of fixing at "medium".
    # gpt-5.x reasoning tokens are the dominant economist latency driver; tying effort
    # to complexity is the cleanest single-knob control.
    _economist_effort = {"low": "low", "medium": "medium", "high": "high"}.get(_cx, "medium")
    economist_prompt = (
        f"Today: {current_date}\n"
        f"Query topic: {core_topic}\n\n"
        f"Available evidence snippets:\n{evidence_snippet}\n\n"
        f"{scout_block}"
        "Follow your system instructions: if the snippets justify a quant model, produce the JSON schema; "
        "if not (per the ABORT rule), respond with exactly ABORT_ECONOMIST.\n\n"
        f"--- OUTPUT DEPTH (research complexity: {_cx}) ---\n{_budget}"
    )
    raw = ask_model(
        economist_prompt,
        default_system["economist"],
        provider=provider,
        model=model,
        effort=_economist_effort,
        base_url=base_url,
        api_key=api_key,
        require_json=False,
    )
    cleaned_for_parse = clean_json_response(raw)
    if _economist_response_is_abort(raw, cleaned_for_parse):
        return None
    try:
        econ_data = json.loads(cleaned_for_parse)
    except (json.JSONDecodeError, TypeError):
        logger.warning("[ECONOMIST] Failed to parse economist JSON response")
        if safety_telemetry is not None:
            schema_telemetry = economist_schema_telemetry_defaults()
            schema_telemetry["economist_invalid_fields"] = ["parse_error"]
            source_binding_telemetry = economist_source_binding_telemetry_defaults(allowed_source_ids)
            source_binding_telemetry.update(economist_evidence_telemetry)
            calculation_telemetry = economist_calculation_telemetry_defaults()
            target_metric_telemetry = economist_target_metric_telemetry_defaults()
            high_stakes_telemetry = validate_high_stakes_quantitative_shadow(
                query=user_query or core_topic,
                payload=None,
                schema_telemetry=schema_telemetry,
                source_binding_telemetry=source_binding_telemetry,
                calculation_telemetry=calculation_telemetry,
                target_metric_telemetry=target_metric_telemetry,
            )
            packet_telemetry = build_quantitative_packet_shadow(
                query=user_query or core_topic,
                payload=None,
                schema_telemetry=schema_telemetry,
                source_binding_telemetry=source_binding_telemetry,
                calculation_telemetry=calculation_telemetry,
                target_metric_telemetry=target_metric_telemetry,
                high_stakes_telemetry=high_stakes_telemetry,
            )
            safety_telemetry.update(schema_telemetry)
            safety_telemetry.update(source_binding_telemetry)
            safety_telemetry.update(calculation_telemetry)
            safety_telemetry.update(target_metric_telemetry)
            safety_telemetry.update(high_stakes_telemetry)
            safety_telemetry.update(packet_telemetry)
        return None

    schema_telemetry = validate_economist_schema_v1(econ_data)
    source_binding_telemetry = validate_economist_source_bindings(econ_data, allowed_source_ids)
    source_binding_telemetry.update(
        economist_evidence_source_window_telemetry(
            economist_evidence_passages,
            source_binding_telemetry.get("source_ids_used"),
        )
    )
    if safety_telemetry is not None:
        safety_telemetry.update(schema_telemetry)
        safety_telemetry.update(source_binding_telemetry)

    code_requested = isinstance(econ_data, dict) and _economist_payload_requests_code(econ_data)
    if safety_telemetry is not None:
        safety_telemetry.update(_economist_safety_telemetry(requested=code_requested))
    if code_requested:
        calculation_telemetry = economist_calculation_telemetry_defaults()
        target_metric_telemetry = validate_target_metric_shadow(
            query=user_query or core_topic,
            payload=econ_data,
            schema_telemetry=schema_telemetry,
            source_binding_telemetry=source_binding_telemetry,
            calculation_telemetry=calculation_telemetry,
        )
        high_stakes_telemetry = validate_high_stakes_quantitative_shadow(
            query=user_query or core_topic,
            payload=econ_data,
            schema_telemetry=schema_telemetry,
            source_binding_telemetry=source_binding_telemetry,
            calculation_telemetry=calculation_telemetry,
            target_metric_telemetry=target_metric_telemetry,
        )
        packet_telemetry = build_quantitative_packet_shadow(
            query=user_query or core_topic,
            payload=econ_data,
            schema_telemetry=schema_telemetry,
            source_binding_telemetry=source_binding_telemetry,
            calculation_telemetry=calculation_telemetry,
            target_metric_telemetry=target_metric_telemetry,
            high_stakes_telemetry=high_stakes_telemetry,
        )
        if safety_telemetry is not None:
            safety_telemetry.update(calculation_telemetry)
            safety_telemetry.update(target_metric_telemetry)
            safety_telemetry.update(high_stakes_telemetry)
            safety_telemetry.update(packet_telemetry)
        run_economist_code(str(econ_data.get("python_code", "")))
        return None

    calculation_telemetry = economist_calculation_telemetry_defaults()
    if (
        isinstance(econ_data, dict)
        and schema_telemetry.get("economist_schema_valid") is True
        and source_binding_telemetry.get("source_binding_valid") is True
    ):
        calculation_telemetry = execute_economist_calculations_shadow(
            econ_data,
            source_binding_valid=True,
        )
        if safety_telemetry is not None:
            safety_telemetry.update(calculation_telemetry)
    elif safety_telemetry is not None:
        safety_telemetry.update(calculation_telemetry)

    target_metric_telemetry = validate_target_metric_shadow(
        query=user_query or core_topic,
        payload=econ_data,
        schema_telemetry=schema_telemetry,
        source_binding_telemetry=source_binding_telemetry,
        calculation_telemetry=calculation_telemetry,
    )
    if safety_telemetry is not None:
        safety_telemetry.update(target_metric_telemetry)

    high_stakes_telemetry = validate_high_stakes_quantitative_shadow(
        query=user_query or core_topic,
        payload=econ_data,
        schema_telemetry=schema_telemetry,
        source_binding_telemetry=source_binding_telemetry,
        calculation_telemetry=calculation_telemetry,
        target_metric_telemetry=target_metric_telemetry,
    )
    if safety_telemetry is not None:
        safety_telemetry.update(high_stakes_telemetry)

    packet_telemetry = build_quantitative_packet_shadow(
        query=user_query or core_topic,
        payload=econ_data,
        schema_telemetry=schema_telemetry,
        source_binding_telemetry=source_binding_telemetry,
        calculation_telemetry=calculation_telemetry,
        target_metric_telemetry=target_metric_telemetry,
        high_stakes_telemetry=high_stakes_telemetry,
    )
    if safety_telemetry is not None:
        safety_telemetry.update(packet_telemetry)

    return None

def fetch_linkup_precision_block(
    core_topic: str,
    intent: str,
    complexity: str,
    include_domains: List[str],
    exclude_domains: List[str],
    cost_accumulator: CostAccumulator | None = None,
    cost_phase: str = "retrieval",
    provider_diagnostics: list[dict[str, Any]] | None = None,
) -> str:
    if complexity != "high":
        return ""
    try:
        from_date, to_date = get_news_date_window(complexity) if intent == "news" else (None, None)
        results, _ = search_linkup_results(
            query=core_topic,
            depth="deep",
            output_type="sourcedAnswer",
            intent=intent,
            max_results=8,
            include_domains=include_domains or None,
            exclude_domains=exclude_domains or None,
            from_date=from_date,
            to_date=to_date,
            cost_accumulator=cost_accumulator,
            cost_phase=cost_phase,
        )
        accepted_url_count = len({str(r.get("url") or "") for r in results if r.get("url")})
        if provider_diagnostics is not None:
            provider_diagnostics.append(
                build_provider_attempt_diagnostic(
                    provider="linkup",
                    provider_role="linkup_precision_sourced_answer",
                    cost_phase=cost_phase,
                    query=core_topic,
                    depth="deep",
                    output_type="sourcedAnswer",
                    max_results=8,
                    answer_endpoint_used=True,
                    raw_content_requested=True,
                    success=True,
                    result_count=len(results),
                    image_count=0,
                    new_url_count=accepted_url_count,
                    accepted_url_count=accepted_url_count,
                )
            )
        if results:
            answer = results[0].get("raw_content", "")
            source_lines = "\n".join(f"  - [{r['title']}]({r['url']})" for r in results[:5] if r.get("url"))
            return (
                f"\n\nLINKUP PRECISION CONTEXT (independent deep search on core topic):\n"
                f"{answer}\n\nSources consulted by Linkup:\n{source_lines}\n"
            )
    except Exception as e:
        logger.warning(f"Linkup precision block failed: {e}. Continuing without it.")
        log_provider_error(
            provider="linkup",
            error=str(e),
            query_preview=(core_topic or "")[:200],
            phase="retrieval",
            logger=logger,
        )
        if provider_diagnostics is not None:
            provider_diagnostics.append(
                build_provider_attempt_diagnostic(
                    provider="linkup",
                    provider_role="linkup_precision_sourced_answer",
                    cost_phase=cost_phase,
                    query=core_topic,
                    depth="deep",
                    output_type="sourcedAnswer",
                    max_results=8,
                    answer_endpoint_used=True,
                    raw_content_requested=True,
                    success=False,
                    failure_type=type(e).__name__,
                )
            )
    return ""


def _is_retrieval_timeout_error(exc: Exception) -> bool:
    """True when the failure is a client wait/read/connect timeout (distinct from HTTP errors or auth)."""
    try:
        from requests.exceptions import ConnectTimeout, ReadTimeout
        from requests.exceptions import Timeout as RequestsTimeout

        if isinstance(exc, (RequestsTimeout, ReadTimeout, ConnectTimeout)):
            return True
    except ImportError:
        pass
    try:
        import httpx

        if isinstance(exc, (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout)):
            return True
    except ImportError:
        pass
    return False


def get_followup_search_params(complexity: str, pipeline_search_depth: Optional[str] = None) -> Dict[str, object]:
    """
    Map the thread's main-run tier to follow-up search budgets (single web pass).
    Aligns with main pipeline: low = fast snippets, medium ≈ second-iteration / supplemental depth, high = advanced + deep linkup.
    """
    c = (complexity or "low").lower()
    psd = (pipeline_search_depth or "basic").lower()
    if c == "low":
        return {
            "search_depth": "basic",
            "max_results": 6,
            "top_passage_count": 8,
            "max_queries": 2,
            "linkup_depth_override": None,
        }
    if c == "medium":
        # Stored depth is often "basic" for iter 1; one-shot follow-up uses advanced for stronger retrieval.
        depth = "advanced" if psd == "basic" else psd
        if depth not in ("basic", "advanced"):
            depth = "advanced"
        return {
            "search_depth": depth,
            "max_results": 6,
            "top_passage_count": 12,
            "max_queries": 3,
            "linkup_depth_override": None,
        }
    return {
        "search_depth": "advanced",
        "max_results": 8,
        "top_passage_count": 16,
        "max_queries": 4,
        "linkup_depth_override": "deep",
    }


def _diagnostic_urls(results: list[dict]) -> list[str]:
    return [
        str(item.get("url") or "")
        for item in results
        if str(item.get("url") or "")
    ]


def _diagnostic_domains(urls: set[str]) -> set[str]:
    return {domain for url in urls if (domain := normalize_domain(url))}


def _max_query_similarity(query: Any, prior_queries: list[str] | None) -> float | None:
    if not prior_queries:
        return None
    return max((jaccard_similarity([str(query or "")], [str(prior)]) for prior in prior_queries), default=0.0)


def _provider_result_summary(
    *,
    provider: str,
    provider_role: str,
    query: Any,
    iteration: int | None,
    rank: int,
    result: dict,
    accepted: bool,
    non_representation_reason: str | None,
) -> dict[str, Any]:
    url = str(result.get("url") or "")[:240]
    title = " ".join(str(result.get("title") or "").strip().split())[:180]
    return {
        "provider_result_id": (
            f"{provider_role}:{iteration if iteration is not None else 'unknown'}:"
            f"{provider}:{rank}"
        ),
        "provider_name": provider,
        "provider_role": provider_role,
        "retrieval_pass_id": (
            f"{provider_role}:{iteration if iteration is not None else 'unknown'}"
        ),
        "query_preview": str(query or "")[:140],
        "provider_rank_or_position": rank,
        "source_url": url,
        "normalized_domain": normalize_domain(url),
        "title": title,
        "provider_returned": True,
        "accepted_url": url if accepted else "",
        "non_representation_reason": non_representation_reason,
        "diagnostic_only": True,
        "sanitized": True,
        "behavior_changed": False,
    }


_SNIPPET_ONLY_MATERIAL = "snippet_only"
_FULL_PAGE_FETCHED_MATERIAL = "full_page_fetched"


def _source_custody_policy_enabled(policy: Any | None) -> bool:
    if policy is None:
        return False
    enabled = getattr(policy, "enabled", None)
    if callable(enabled):
        return bool(enabled())
    return bool(getattr(policy, "require_official_full_fetch_read", False))


def _source_custody_policy_domains(
    policy: Any | None,
    include_domains: list[str] | tuple[str, ...] | None,
) -> tuple[str, ...]:
    raw_domains = getattr(policy, "preferred_domains", ()) if policy else ()
    if not raw_domains:
        raw_domains = include_domains or ()
    domains: list[str] = []
    for value in raw_domains:
        domain = str(value or "").strip().lower()
        domain = domain.removeprefix("https://").removeprefix("http://")
        domain = domain.split("/", 1)[0].lstrip(".").rstrip(".")
        if domain and domain not in domains:
            domains.append(domain)
    return tuple(domains)


def _host_matches_source_custody_domain(host: str, domain: str) -> bool:
    host = (host or "").lower().rstrip(".")
    domain = (domain or "").lower().lstrip(".").rstrip(".")
    return bool(host and domain and (host == domain or host.endswith("." + domain)))


def _source_custody_domain_allowed(url: Any, domains: tuple[str, ...]) -> bool:
    host = normalize_source_domain(str(url or ""))
    return any(_host_matches_source_custody_domain(host, domain) for domain in domains)


def _source_custody_candidate_tier(
    result: dict[str, Any],
    *,
    entity_hint: str | None,
) -> str:
    explicit = str(result.get("source_tier") or "").strip()
    if explicit:
        return explicit
    snippet = (result.get("snippet") or result.get("raw_content") or "")[:2000]
    return classify_source(
        result.get("url", "") or "",
        result.get("title", "") or "",
        snippet,
        source_context=entity_hint or "",
    )


def _select_source_custody_fetch_candidate(
    candidates: list[dict[str, Any]],
    *,
    policy: Any,
    include_domains: list[str],
    entity_hint: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    domains = _source_custody_policy_domains(policy, include_domains)
    first_official: tuple[dict[str, Any], str] | None = None
    for result in candidates:
        if not isinstance(result, dict) or not str(result.get("url") or "").strip():
            continue
        if result.get("_linkup_sourced_answer") is True:
            continue
        tier = _source_custody_candidate_tier(result, entity_hint=entity_hint)
        if domains and _source_custody_domain_allowed(result.get("url"), domains):
            return result, tier
        if first_official is None and tier == "official":
            first_official = (result, tier)
    return first_official or (None, None)


def _annotate_source_custody_fetch_candidate(
    result: dict[str, Any],
    *,
    policy: Any,
    source_tier: str | None,
) -> None:
    result["_source_custody_policy_forced_fetch_read"] = True
    result["source_custody_requirement_id"] = getattr(
        policy,
        "requirement_id",
        "source-custody:official-full-fetch-read",
    )
    result["required_source_class"] = getattr(
        policy,
        "required_source_class",
        "primary_source_documents",
    )
    result["required_source_tier"] = getattr(policy, "required_source_tier", "official")
    result["required_currentness"] = getattr(policy, "required_currentness", "current")
    result["required_evidence_material_type"] = getattr(
        policy,
        "required_evidence_material_type",
        _FULL_PAGE_FETCHED_MATERIAL,
    )
    result["source_custody_admission_reason"] = getattr(
        policy,
        "admission_reason",
        "source_custody_policy_full_fetch_read",
    )
    result["source_class"] = result.get("source_class") or result["required_source_class"]
    result["source_tier"] = result.get("source_tier") or source_tier or result[
        "required_source_tier"
    ]
    result["currentness_signal"] = (
        result.get("currentness_signal") or result["required_currentness"]
    )
    result["eligible_for_stronger_obligation"] = True


def _apply_source_custody_fetch_read_policy(
    *,
    to_fetch: list[dict[str, Any]],
    to_snippet: list[dict[str, Any]],
    source_custody_policy: Any | None,
    include_domains: list[str],
    entity_hint: str | None,
) -> None:
    if not _source_custody_policy_enabled(source_custody_policy):
        return
    if int(getattr(source_custody_policy, "max_forced_fetch_reads", 1) or 0) < 1:
        return
    candidates = [*to_fetch, *to_snippet]
    selected, source_tier = _select_source_custody_fetch_candidate(
        candidates,
        policy=source_custody_policy,
        include_domains=include_domains,
        entity_hint=entity_hint,
    )
    if selected is None:
        return
    _annotate_source_custody_fetch_candidate(
        selected,
        policy=source_custody_policy,
        source_tier=source_tier,
    )
    if selected in to_fetch:
        return
    to_snippet[:] = [result for result in to_snippet if result is not selected]
    to_fetch.append(selected)


def _material_fields(material_type: str) -> dict[str, Any]:
    return {
        "evidence_material_type": material_type,
        "source_material_type": material_type,
        "full_page_fetched": material_type == _FULL_PAGE_FETCHED_MATERIAL,
        "snippet_only": material_type == _SNIPPET_ONLY_MATERIAL,
    }


def _source_custody_passage_fields(source: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in (
        "source_class",
        "currentness_signal",
        "source_custody_requirement_id",
        "required_source_class",
        "required_source_tier",
        "required_currentness",
        "required_evidence_material_type",
        "eligible_for_stronger_obligation",
        "source_custody_admission_reason",
    ):
        value = source.get(key)
        if value not in (None, "", [], {}):
            fields[key] = value
    return fields


def process_search_queries(
    queries_list,
    intent,
    complexity,
    search_depth,
    max_results,
    include_domains,
    exclude_domains,
    query_embedding,
    seen_urls_set,
    collected_images_set,
    embed_provider,
    embed_model,
    local_url,
    embed_texts: Callable,
    compute_similarities: Callable,
    status_container=_NOOP_STATUS_CONTAINER,
    search_providers=None,
    linkup_depth_override=None,
    exa_domain_filter=None,
    entity_hint: Optional[str] = None,
    cost_accumulator: CostAccumulator | None = None,
    cost_phase: str = "retrieval",
    provider_diagnostics: list[dict[str, Any]] | None = None,
    provider_role: str = "main_retrieval",
    iteration: int | None = None,
    prior_queries_for_similarity: list[str] | None = None,
    query_similarity_basis: str | None = None,
    cap_policy: Any | None = None,
    source_custody_policy: Any | None = None,
):
    if search_providers is None:
        search_providers = ["tavily"]
        if os.getenv("LINKUP_API_KEY") and should_allow_linkup_provider(complexity):
            search_providers.append("linkup")
        if os.getenv("EXA_API_KEY") and intent == "general":
            search_providers.append("exa")

    linkup_depth_map = {"low": "fast", "medium": "standard", "high": "standard"}
    linkup_depth = linkup_depth_override or linkup_depth_map.get(complexity, "standard")
    from_date, to_date = get_news_date_window(complexity) if intent == "news" else (None, None)
    provider_buckets: dict[str, list[dict]] = {}
    new_urls_this_pass = set()
    pre_pass_seen_urls = set(seen_urls_set)
    pre_pass_seen_domains = _diagnostic_domains(pre_pass_seen_urls)
    attempt_diagnostics: list[tuple[dict[str, Any], set[str]]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(queries_list) * len(search_providers))) as executor:
        futures = {}
        for q in queries_list:
            if "tavily" in search_providers:
                futures[executor.submit(
                    search_web_results,
                    q,
                    intent=intent,
                    complexity=complexity,
                    max_results=max_results,
                    search_depth=search_depth,
                    include_domains=include_domains,
                    exclude_domains=exclude_domains,
                    cost_accumulator=cost_accumulator,
                    cost_phase=cost_phase,
                )] = ("tavily", q)
            if "linkup" in search_providers and os.getenv("LINKUP_API_KEY"):
                futures[executor.submit(
                    search_linkup_results,
                    q,
                    depth=linkup_depth,
                    output_type="searchResults",
                    intent=intent,
                    max_results=max_results,
                    include_domains=include_domains,
                    exclude_domains=exclude_domains,
                    from_date=from_date,
                    to_date=to_date,
                    cost_accumulator=cost_accumulator,
                    cost_phase=cost_phase,
                )] = ("linkup", q)
            if "exa" in search_providers and os.getenv("EXA_API_KEY"):
                exa_domains = exa_domain_filter if exa_domain_filter else include_domains
                futures[executor.submit(
                    search_exa_results,
                    q,
                    intent=intent,
                    max_results=max_results,
                    include_domains=exa_domains,
                    exclude_domains=exclude_domains,
                    from_date=from_date,
                    to_date=to_date,
                    cost_accumulator=cost_accumulator,
                    cost_phase=cost_phase,
                )] = ("exa", q)

        for future in concurrent.futures.as_completed(futures):
            provider, q = futures[future]
            success = True
            failure_type = None
            try:
                results, imgs = future.result()
            except Exception as e:
                success = False
                failure_type = type(e).__name__
                logger.warning(f"[SEARCH] {provider} failed for '{q}': {e}")
                q_preview = (str(q) if q is not None else "")[:200]
                if _is_retrieval_timeout_error(e):
                    log_retrieval_timeout(
                        provider=provider,
                        query=str(q),
                        timeout_seconds=retrieval_timeout_seconds(provider),
                        logger=logger,
                    )
                else:
                    log_provider_error(
                        provider=provider,
                        error=str(e),
                        query_preview=q_preview,
                        phase="retrieval",
                        logger=logger,
                    )
                results, imgs = [], []

            provider_buckets.setdefault(provider, [])
            provider_seen_urls = set()
            attempt_new_urls: set[str] = set()
            accepted_urls: set[str] = set()
            accepted_url_count = 0
            raw_urls = _diagnostic_urls(results)
            raw_unique_urls = set(raw_urls)
            raw_domains = _diagnostic_domains(raw_unique_urls)
            raw_url_overlap_count = len(raw_unique_urls & pre_pass_seen_urls)
            raw_domain_overlap_count = len(raw_domains & pre_pass_seen_domains)
            provider_result_summaries: list[dict[str, Any]] = []
            for rank, item in enumerate(results, start=1):
                url = item.get("url", "")
                plausible = is_plausible_domain(url)
                accepted = (
                    plausible
                    and url not in seen_urls_set
                    and url not in provider_seen_urls
                )
                non_representation_reason = None
                if plausible and url in seen_urls_set:
                    non_representation_reason = "duplicate_seen_url"
                elif plausible and url in provider_seen_urls:
                    non_representation_reason = "duplicate_provider_url"
                elif not plausible and url:
                    non_representation_reason = "non_plausible_url"
                if url:
                    provider_result_summaries.append(
                        _provider_result_summary(
                            provider=provider,
                            provider_role=provider_role,
                            query=q,
                            iteration=iteration,
                            rank=rank,
                            result=item,
                            accepted=accepted,
                            non_representation_reason=non_representation_reason,
                        )
                    )
                if plausible and url not in seen_urls_set:
                    attempt_new_urls.add(url)
                if accepted:
                    item["_provider"] = provider
                    item["_query"] = q
                    provider_buckets[provider].append(item)
                    provider_seen_urls.add(url)
                    new_urls_this_pass.add(url)
                    accepted_urls.add(url)
                    accepted_url_count += 1
            if imgs:
                for img in imgs:
                    if is_plausible_domain(img):
                        collected_images_set.add(img)
            if provider_diagnostics is not None:
                accepted_domains = _diagnostic_domains(accepted_urls)
                diagnostic = build_provider_attempt_diagnostic(
                    provider=provider,
                    provider_role=provider_role,
                    cost_phase=cost_phase,
                    iteration=iteration,
                    query=q,
                    depth=(
                        search_depth
                        if provider == "tavily"
                        else linkup_depth
                        if provider == "linkup"
                        else None
                    ),
                    output_type="searchResults",
                    max_results=max_results,
                    answer_endpoint_used=False,
                    raw_content_requested=provider in {"tavily", "exa"},
                    success=success,
                    failure_type=failure_type,
                    result_count=len(results),
                    image_count=len(imgs or []),
                    new_url_count=len(attempt_new_urls),
                    accepted_url_count=accepted_url_count,
                    raw_url_count=len(raw_urls),
                    raw_unique_url_count=len(raw_unique_urls),
                    raw_url_overlap_count=raw_url_overlap_count,
                    raw_domain_count=len(raw_domains),
                    raw_domain_overlap_count=raw_domain_overlap_count,
                    # Raw overlap is pre-acceptance provider output; accepted overlap only covers URLs admitted below.
                    accepted_url_overlap_count=len(accepted_urls & pre_pass_seen_urls),
                    accepted_domain_count=len(accepted_domains),
                    new_domain_count=len(accepted_domains - pre_pass_seen_domains),
                    new_source_count=0,
                    query_similarity_max=_max_query_similarity(q, prior_queries_for_similarity),
                    query_similarity_basis=query_similarity_basis,
                    provider_overlap_diagnostics_available=success,
                    provider_result_summaries=provider_result_summaries,
                )
                provider_diagnostics.append(diagnostic)
                attempt_diagnostics.append((diagnostic, set(accepted_urls)))

    seen_urls_set.update(new_urls_this_pass)
    all_raw_results = rrf_merge(provider_buckets, k=60) if len(provider_buckets) > 1 else (list(provider_buckets.values())[0] if provider_buckets else [])
    search_results = all_raw_results
    status_container.write(f"Fetched {len(search_results)} new unique URLs.")

    new_passages = []
    to_fetch, to_snippet = [], []
    if complexity == "low":
        to_snippet = search_results[:10]
    elif complexity == "medium":
        to_snippet = search_results[:25]
    else:
        for r in search_results[:40]:
            if r.get("credibility", 0) >= 3 and not r.get("_linkup_sourced_answer", False):
                to_fetch.append(r)
            else:
                to_snippet.append(r)

    _apply_source_custody_fetch_read_policy(
        to_fetch=to_fetch,
        to_snippet=to_snippet,
        source_custody_policy=source_custody_policy,
        include_domains=include_domains,
        entity_hint=entity_hint,
    )

    if to_snippet:
        status_container.write(f"Extracting snippets from {len(to_snippet)} sources (bypassing full fetch)...")
        for r in to_snippet:
            if r.get("credibility", 0) < -1:
                continue
            text_content = (r.get("raw_content") or r.get("snippet") or "")[:20000]
            if len(text_content) > 150:
                _tier_snip = (r.get("snippet") or r.get("raw_content") or "")[:2000]
                _source_tier = classify_source(
                    r.get("url", "") or "",
                    r.get("title", "") or "",
                    _tier_snip,
                    source_context=entity_hint or "",
                )
                for chunk in chunk_text(text_content, chunk_size=1200):
                    if len(chunk) < 150:
                        continue
                    prefix = "[SNIPPET] " if complexity == "high" else ""
                    new_passages.append(
                        {
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "domain": r.get("domain", ""),
                            "credibility": r.get("credibility", 0),
                            "text": prefix + chunk,
                            "score": 0,
                            "rrf_score": r.get("rrf_score", 0.0),
                            "_provider": r.get("_provider", ""),
                            "source_tier": _source_tier,
                            **_material_fields(_SNIPPET_ONLY_MATERIAL),
                            **_source_custody_passage_fields(r),
                        }
                    )

    if to_fetch:
        status_container.write(f"Selectively fetching {len(to_fetch)} high-credibility pages...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for item in enumerate(to_fetch, 1):
                if cap_policy is not None:
                    cap_policy.mark_fetch_read_operation()
                futures.append(executor.submit(fetch_page, item))
            fetched_results = [future.result() for future in futures]
        docs = [d for d in fetched_results if d is not None]
        for doc in docs:
            _tier_snip = (doc.get("text") or "")[:2000]
            _source_tier = classify_source(
                doc.get("url", "") or "",
                doc.get("title", "") or "",
                _tier_snip,
                source_context=entity_hint or "",
            )
            if doc.get("_source_custody_policy_forced_fetch_read") is True:
                _source_tier = doc.get("source_tier") or _source_tier
            for chunk in chunk_text(doc["text"], chunk_size=2000):
                if len(chunk) < 150:
                    continue
                prefix = "[FULL_PAGE] " if complexity == "high" else ""
                new_passages.append(
                    {
                        "title": doc["title"],
                        "url": doc["url"],
                        "domain": doc["domain"],
                        "credibility": doc["credibility"],
                        "text": prefix + chunk,
                        "score": 0,
                        "rrf_score": doc.get("rrf_score", 0.0),
                        "_provider": doc.get("_provider", ""),
                        "source_tier": _source_tier,
                        **_material_fields(_FULL_PAGE_FETCHED_MATERIAL),
                        **_source_custody_passage_fields(doc),
                    }
                )

    if new_passages and query_embedding is not None:
        status_container.write(f"Embedding {len(new_passages)} text chunks using {embed_provider}...")
        new_embeddings = embed_texts(
            [p["text"][:8000] for p in new_passages],
            provider=embed_provider,
            model=embed_model,
            base_url=local_url,
            cost_accumulator=cost_accumulator,
            cost_phase="embedding",
        )
        sim_scores = compute_similarities(query_embedding, new_embeddings)
        _hint = (entity_hint or "").strip()
        filtered_passages = []
        for i, passage in enumerate(new_passages):
            similarity = float(sim_scores[i])
            credibility = passage.get("credibility", 0)
            if credibility < -1:
                continue
            rrf = passage.get("rrf_score", 0.0)
            rrf_normalized = min(rrf / 0.05, 1.0)
            blended_score = (0.75 * similarity) + (0.15 * rrf_normalized) + (0.10 * (credibility / 10.0))
            # Core-topic-only embeddings can under-rank on-topic text (e.g. "boycott" vs "Galloway controversy").
            if _hint and passage_mentions_entity_full_phrase(passage, _hint):
                blended_score = max(blended_score, 0.185)
            if blended_score < 0.15:
                continue
            passage["score"] = blended_score
            filtered_passages.append(passage)
        new_passages = filtered_passages

    if attempt_diagnostics:
        passage_urls = {
            str(passage.get("url") or "")
            for passage in new_passages
            if is_plausible_domain(str(passage.get("url") or ""))
        }
        for diagnostic, accepted_urls in attempt_diagnostics:
            diagnostic["new_source_count"] = len(accepted_urls & passage_urls)

    return new_passages


def kb_review_agent(
    ask_model: Callable[..., str],
    clean_json_response: Callable[[str], str],
    flags: dict,
    execution: dict,
    output_preview: str,
    fast_provider: str,
    fast_model: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """Generates a KB entry for a flagged run. Non-fatal — caller should try/except."""
    system_prompt = KB_REVIEW_AGENT_SYSTEM
    exec_slice = {k: execution.get(k) for k in (
        "intent", "report_type", "iterations_run", "scout_fired", "synth_was_insufficient",
    ) if k in execution}
    user_message = (
        f"Flags: {json.dumps(flags, ensure_ascii=True)}\n\n"
        f"Execution: {json.dumps(exec_slice, ensure_ascii=True, indent=2)}\n\n"
        f"Output preview (first 400 chars): {(output_preview or '')[:400]}\n"
    )
    try:
        response = ask_model(
            user_message,
            system_prompt,
            provider=fast_provider,
            model=fast_model,
            effort="low",
            base_url=base_url,
            api_key=api_key,
            require_json=True,
            use_reasoning=False,
        )
        cleaned = clean_json_response(response)
        return json.loads(cleaned.strip())
    except Exception as e:
        logger.warning(f"[KB] kb_review_agent failed: {e}")
        return None


def kb_review_agent_positive(
    ask_model: Callable[..., str],
    clean_json_response: Callable[[str], str],
    execution: dict,
    output_preview: str,
    feedback_slice: dict,
    fast_provider: str,
    fast_model: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """Lightweight positive-outcome pattern capture for the KB. Returns JSON or None."""
    system_prompt = (
        "You document what went well in a research run so the team can reproduce good outcomes. "
        "Return JSON only:\n"
        "{\n"
        '  "positive_pattern": "1-2 sentences: what conditions, modes, and evidence flow produced a strong result",\n'
        '  "hypothesis": "why this run succeeded (concrete, not generic)",\n'
        '  "confidence": "low|medium|high"\n'
        "}\n"
    )
    exec_slice = {k: execution.get(k) for k in ("intent", "report_type", "iterations_run", "scout_fired", "mode")}
    user_message = (
        f"User rating dimensions: {json.dumps({k: feedback_slice.get(k) for k in ('answer_completeness', 'evidence_quality', 'output_precision', 'scout_contribution', 'overall', 'overall_auto') if feedback_slice.get(k) is not None}, ensure_ascii=True)}\n\n"
        f"Execution: {json.dumps(exec_slice, ensure_ascii=True, indent=2)}\n\n"
        f"Output preview (first 400 chars): {(output_preview or '')[:400]}\n"
    )
    try:
        response = ask_model(
            user_message,
            system_prompt,
            provider=fast_provider,
            model=fast_model,
            effort="low",
            base_url=base_url,
            api_key=api_key,
            require_json=True,
            use_reasoning=False,
        )
        cleaned = clean_json_response(response)
        return json.loads(cleaned.strip())
    except Exception as e:
        logger.warning(f"[KB] kb_review_agent_positive failed: {e}")
        return None


def kb_review_agent_hybrid(
    ask_model: Callable[..., str],
    clean_json_response: Callable[[str], str],
    execution: dict,
    output_preview: str,
    feedback_slice: dict,
    fast_provider: str,
    fast_model: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """Builds a structured KB entry from execution + negative user feedback."""
    system_prompt = KB_REVIEW_AGENT_HYBRID_SYSTEM
    exec_slice = {
        k: execution.get(k)
        for k in (
            "intent",
            "report_type",
            "complexity",
            "iterations_run",
            "synth_was_insufficient",
            "supplemental_ran",
            "utilization_rate",
            "corpus_state",
            "corpus_weak",
            "useful_content",
            "useful_content_reason",
            "final_output_preview",
            "total_chunks_embedded",
            "scout_fired",
            "scrutineer_flag_count",
        )
        if k in execution
    }
    fb_slice = {
        k: feedback_slice.get(k)
        for k in (
            "answer_completeness",
            "evidence_quality",
            "output_precision",
            "overall",
            "overall_auto",
            "scout_contribution",
            "user_notes",
        )
        if feedback_slice.get(k) is not None
    }
    user_message = (
        f"Execution: {json.dumps(exec_slice, ensure_ascii=True, indent=2)}\n\n"
        f"User feedback: {json.dumps(fb_slice, ensure_ascii=True, indent=2)}\n\n"
        f"Output preview (first 400 chars): {(output_preview or '')[:400]}\n"
    )
    try:
        response = ask_model(
            user_message,
            system_prompt,
            provider=fast_provider,
            model=fast_model,
            effort="low",
            base_url=base_url,
            api_key=api_key,
            require_json=True,
            use_reasoning=False,
        )
        cleaned = clean_json_response(response)
        return json.loads(cleaned.strip())
    except Exception as e:
        logger.warning(f"[KB] kb_review_agent_hybrid failed: {e}")
        return None
