"""Bounded QuantWorkUnit runtime packets for source-bound numeric evidence.

This module consumes passive SearchWork ``QuantWorkUnit`` projections and
already-custodied EvidenceLedger candidate refs. It does not call providers,
search, retrieval, prompts, models, process spawning, or arbitrary code execution.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse, urlunparse

QUANT_WORK_UNIT_PACKET_SCHEMA_VERSION = "quant_work_unit_packet_ag96h1_v1"
QUANT_WORK_UNIT_PACKET_TRACE_KEY = "quant_work_unit_packets"

_ALLOWED_CALCULATIONS = frozenset(
    {"identity", "direct_value", "difference", "ratio", "percent_change", "sum", "average"}
)
_IDENTITY_CALCULATIONS = frozenset({"identity", "direct_value"})
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_text",
        "full_trace",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "source_text",
        "text",
        "token",
    }
)
_FACT_FIELDS = ("numeric_facts", "source_bound_values", "extracted_values")
_COMPACT_TEXT_FIELDS = ("compact_passage_text", "safe_passage_text", "fixture_passage_text")


def build_quant_work_unit_packets(
    *,
    quant_work_units: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
    evidence_ledger_projection: Mapping[str, Any] | None,
    candidate_records: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return trace-safe quant packets for passive QuantWorkUnit projections."""

    units = _sequence_of_mappings(quant_work_units)
    ledger = _mapping(evidence_ledger_projection)
    custody = _custody_index(ledger)
    fixture_candidates = _candidate_fixture_index(candidate_records)
    packets = [
        _packet_for_unit(unit, custody=custody, fixture_candidates=fixture_candidates)
        for unit in units
    ]
    return tuple(packets)


def quant_work_packet_trace_fragment(
    packets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return a compact trace fragment for already-built QuantWorkUnit packets."""

    safe_packets = [_safe_json(packet) for packet in packets]
    resolved = [
        packet
        for packet in safe_packets
        if isinstance(packet, Mapping) and packet.get("calculation_status") == "succeeded"
    ]
    unresolved = [
        packet
        for packet in safe_packets
        if isinstance(packet, Mapping) and packet.get("calculation_status") != "succeeded"
    ]
    return {
        QUANT_WORK_UNIT_PACKET_TRACE_KEY: safe_packets,
        "quant_work_unit_packet_count": len(safe_packets),
        "resolved_quant_work_unit_count": len(resolved),
        "unresolved_quant_work_unit_count": len(unresolved),
        "behavior_boundary_flags": _behavior_flags(any_resolved=bool(resolved)),
    }


def _packet_for_unit(
    unit: Mapping[str, Any],
    *,
    custody: Mapping[str, Any],
    fixture_candidates: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    quant_unit_id = _clean_token(unit.get("quant_unit_id")) or "quant_unit_unknown"
    component_ids = _text_list(unit.get("component_ids"))
    metadata = _mapping(unit.get("metadata"))
    source_obligation_ids = _text_list(
        unit.get("source_obligation_ids")
        or metadata.get("source_obligation_ids")
        or metadata.get("obligation_ids")
    )
    requirement_ids = _text_list(
        unit.get("requirement_ids")
        or metadata.get("requirement_ids")
        or metadata.get("source_requirement_ids")
    )
    required_variables = _text_list(
        unit.get("required_variables") or unit.get("source_bound_values_needed")
    )
    allowed_calculation = _allowed_calculation(unit)
    expected_units = _expected_units(unit)
    strict_candidate_ids = _custodied_candidate_ids(
        custody,
        component_ids=component_ids,
        source_obligation_ids=source_obligation_ids,
        requirement_ids=requirement_ids,
    )
    facts = _facts_for_unit(
        required_variables=required_variables,
        candidate_ids=strict_candidate_ids,
        custody=custody,
        fixture_candidates=fixture_candidates,
    )
    extracted, unresolved_values, blocked_reasons = _resolve_required_values(
        required_variables=required_variables,
        facts=facts,
        expected_units=expected_units,
    )
    extraction_status = _extraction_status(
        extracted=extracted,
        unresolved_values=unresolved_values,
        blocked_reasons=blocked_reasons,
    )
    calculation, calculation_status, calculation_blockers = _calculate(
        calculation_kind=allowed_calculation,
        required_variables=required_variables,
        extracted_values=extracted,
        unresolved_values=unresolved_values,
        expected_units=expected_units,
    )
    blocked_reasons.extend(calculation_blockers)
    source_refs = _source_refs(extracted)
    packet = {
        "schema_version": QUANT_WORK_UNIT_PACKET_SCHEMA_VERSION,
        "trace_key": QUANT_WORK_UNIT_PACKET_TRACE_KEY,
        "owner": "QuantWorkUnitRuntime",
        "quant_unit_id": quant_unit_id,
        "component_ids": component_ids,
        "source_obligation_ids": source_obligation_ids,
        "requirement_ids": requirement_ids,
        "required_variables": required_variables,
        "source_bound_values_needed": _text_list(unit.get("source_bound_values_needed"))
        or required_variables,
        "extracted_values": list(extracted.values()),
        "unresolved_values": unresolved_values,
        "allowed_calculation_kind": allowed_calculation,
        "calculation_result": calculation,
        "source_refs": source_refs,
        "extraction_status": extraction_status,
        "calculation_status": calculation_status,
        "blocked_reasons": list(dict.fromkeys(blocked_reasons)),
        "high_stakes_quant": bool(unit.get("high_stakes_quant")),
        "direct_use_eligible": bool(
            unit.get("direct_use_eligible")
            and calculation_status == "succeeded"
            and not unresolved_values
        ),
        "behavior_boundary_flags": _behavior_flags(
            any_resolved=calculation_status == "succeeded"
        ),
    }
    if bool(unit.get("high_stakes_quant")) and unresolved_values:
        packet["blocked_reasons"] = list(
            dict.fromkeys([*packet["blocked_reasons"], "high_stakes_quant_requires_exact_values"])
        )
        packet["calculation_status"] = "blocked"
    return _safe_json(packet)


def _facts_for_unit(
    *,
    required_variables: Sequence[str],
    candidate_ids: Sequence[str],
    custody: Mapping[str, Any],
    fixture_candidates: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    wanted = {_var_key(variable): variable for variable in required_variables}
    out: dict[str, list[dict[str, Any]]] = {variable: [] for variable in required_variables}
    ledger_candidates = _mapping(custody.get("candidate_records"))
    for candidate_id in candidate_ids:
        candidate = dict(ledger_candidates.get(candidate_id) or {})
        fixture = dict(fixture_candidates.get(candidate_id) or {})
        if not candidate:
            continue
        if _truthy(candidate.get("lower_tier")) or _truthy(candidate.get("contextual_only")):
            continue
        fact_payloads = _candidate_fact_payloads(fixture, candidate_id=candidate_id)
        for fact in fact_payloads:
            key = _var_key(fact.get("variable"))
            required_name = wanted.get(key)
            if not required_name:
                continue
            normalized = _normalized_fact(fact, candidate=candidate)
            if normalized:
                out.setdefault(required_name, []).append(normalized)
    return out


def _candidate_fact_payloads(
    candidate: Mapping[str, Any],
    *,
    candidate_id: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for field in _FACT_FIELDS:
        value = candidate.get(field)
        if isinstance(value, Mapping):
            for key, item in value.items():
                if isinstance(item, Mapping):
                    out.append({"variable": key, **dict(item), "candidate_id": candidate_id})
                else:
                    out.append({"variable": key, "value": item, "candidate_id": candidate_id})
        else:
            for item in _sequence_of_mappings(value):
                out.append({**item, "candidate_id": item.get("candidate_id") or candidate_id})
    for field in _COMPACT_TEXT_FIELDS:
        text = _clean_text(candidate.get(field), limit=500)
        if not text:
            continue
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        for fact in _parse_compact_fixture_text(text):
            out.append({**fact, "candidate_id": candidate_id, "text_hash": text_hash, "text_length": len(text)})
    return out


def _parse_compact_fixture_text(text: str) -> list[dict[str, Any]]:
    """Parse tiny fixture clauses like ``rate=12.5 percent`` only."""

    facts: list[dict[str, Any]] = []
    for raw_part in text.replace(";", "\n").splitlines():
        part = raw_part.strip()
        if "=" not in part:
            continue
        name, raw_value = part.split("=", 1)
        variable = _clean_token(name)
        pieces = raw_value.strip().split()
        if not variable or not pieces:
            continue
        value = _decimal_value(pieces[0])
        if value is None:
            continue
        unit = _clean_token(" ".join(pieces[1:]), limit=80)
        facts.append({"variable": variable, "value": value, "unit": unit})
    return facts


def _normalized_fact(
    fact: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
) -> dict[str, Any] | None:
    variable = _clean_token(
        fact.get("variable") or fact.get("metric") or fact.get("name"),
        limit=120,
    )
    value = _decimal_value(fact.get("value") or fact.get("numeric_value"))
    if not variable or value is None:
        return None
    candidate_id = _ledger_token(fact.get("candidate_id")) or _ledger_token(candidate.get("candidate_id"))
    if not candidate_id:
        return None
    unit = _clean_token(fact.get("unit"), limit=80)
    return _compact(
        {
            "variable": variable,
            "value": value,
            "unit": unit,
            "candidate_id": candidate_id,
            "source_id": candidate.get("source_id"),
            "url": candidate.get("url"),
            "domain": candidate.get("domain"),
            "title": candidate.get("title"),
            "source_class": candidate.get("source_class"),
            "source_tier": candidate.get("source_tier"),
            "text_hash": fact.get("text_hash"),
            "text_length": fact.get("text_length"),
        }
    )


def _resolve_required_values(
    *,
    required_variables: Sequence[str],
    facts: Mapping[str, Sequence[Mapping[str, Any]]],
    expected_units: Mapping[str, str],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[str]]:
    extracted: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    blockers: list[str] = []
    for variable in required_variables:
        variable_facts = [dict(item) for item in facts.get(variable, ())]
        if not variable_facts:
            unresolved.append({"variable": variable, "reason": "missing_source_bound_value"})
            continue
        distinct = {
            (
                str(item.get("value")),
                _unit_key(item.get("unit")),
                _clean_token(item.get("candidate_id")),
            )
            for item in variable_facts
        }
        value_unit_pairs = {(value, unit) for value, unit, _candidate in distinct}
        if len(value_unit_pairs) > 1:
            unresolved.append(
                {
                    "variable": variable,
                    "reason": "ambiguous_or_conflicting_source_bound_values",
                    "candidate_ids": sorted(
                        candidate for _value, _unit, candidate in distinct if candidate
                    ),
                }
            )
            blockers.append("ambiguous_or_conflicting_numeric_values")
            continue
        fact = variable_facts[0]
        expected_unit = _clean_token(expected_units.get(_var_key(variable)), limit=80)
        actual_unit = _clean_token(fact.get("unit"), limit=80)
        if expected_unit and actual_unit and _unit_key(expected_unit) != _unit_key(actual_unit):
            unresolved.append(
                {
                    "variable": variable,
                    "reason": "unit_mismatch",
                    "expected_unit": expected_unit,
                    "actual_unit": actual_unit,
                }
            )
            blockers.append("unit_mismatch")
            continue
        if expected_unit and not actual_unit:
            unresolved.append(
                {
                    "variable": variable,
                    "reason": "missing_required_unit",
                    "expected_unit": expected_unit,
                }
            )
            blockers.append("missing_required_unit")
            continue
        extracted[variable] = fact
    return extracted, unresolved, blockers


def _calculate(
    *,
    calculation_kind: str,
    required_variables: Sequence[str],
    extracted_values: Mapping[str, Mapping[str, Any]],
    unresolved_values: Sequence[Mapping[str, Any]],
    expected_units: Mapping[str, str],
) -> tuple[dict[str, Any] | None, str, list[str]]:
    if calculation_kind not in _ALLOWED_CALCULATIONS:
        return None, "blocked", ["calculation_kind_not_whitelisted"]
    if unresolved_values:
        return None, "unresolved", ["missing_required_variables"]
    if not required_variables:
        return None, "blocked", ["no_required_variables_declared"]
    values = [_decimal_value(extracted_values[variable].get("value")) for variable in required_variables]
    if any(value is None for value in values):
        return None, "blocked", ["non_numeric_source_bound_value"]
    decimals = [value for value in values if value is not None]
    unit_blocker = _unit_blocker(
        calculation_kind=calculation_kind,
        required_variables=required_variables,
        extracted_values=extracted_values,
        expected_units=expected_units,
    )
    if unit_blocker:
        return None, "blocked", [unit_blocker]
    try:
        if calculation_kind in _IDENTITY_CALCULATIONS:
            result = decimals[0]
        elif calculation_kind == "difference":
            if len(decimals) != 2:
                return None, "blocked", ["difference_requires_two_variables"]
            result = decimals[0] - decimals[1]
        elif calculation_kind == "ratio":
            if len(decimals) != 2:
                return None, "blocked", ["ratio_requires_two_variables"]
            if decimals[1] == 0:
                return None, "blocked", ["division_by_zero"]
            result = decimals[0] / decimals[1]
        elif calculation_kind == "percent_change":
            if len(decimals) != 2:
                return None, "blocked", ["percent_change_requires_two_variables"]
            if decimals[0] == 0:
                return None, "blocked", ["percent_change_base_zero"]
            result = ((decimals[1] - decimals[0]) / decimals[0]) * Decimal("100")
        elif calculation_kind == "sum":
            result = sum(decimals, Decimal("0"))
        elif calculation_kind == "average":
            result = sum(decimals, Decimal("0")) / Decimal(len(decimals))
        else:
            return None, "blocked", ["calculation_kind_not_whitelisted"]
    except (InvalidOperation, ZeroDivisionError):
        return None, "blocked", ["calculation_failed"]
    return (
        {
            "kind": calculation_kind,
            "value": _decimal_to_json(result),
            "input_variables": list(required_variables),
            "unit": _result_unit(calculation_kind, required_variables, extracted_values),
        },
        "succeeded",
        [],
    )


def _unit_blocker(
    *,
    calculation_kind: str,
    required_variables: Sequence[str],
    extracted_values: Mapping[str, Mapping[str, Any]],
    expected_units: Mapping[str, str],
) -> str | None:
    units = [
        _clean_token(extracted_values[variable].get("unit"), limit=80)
        or _clean_token(expected_units.get(_var_key(variable)), limit=80)
        for variable in required_variables
    ]
    if calculation_kind in _IDENTITY_CALCULATIONS:
        return None
    if any(not unit for unit in units):
        return "missing_required_unit"
    unit_keys = {_unit_key(unit) for unit in units if unit}
    if calculation_kind in {"difference", "sum", "average", "percent_change"} and len(unit_keys) > 1:
        return "unit_mismatch"
    return None


def _custody_index(ledger: Mapping[str, Any]) -> dict[str, Any]:
    candidate_records = {
        _clean_token(item.get("candidate_id")): dict(item)
        for item in _sequence_of_mappings(ledger.get("candidate_records"))
        if _clean_token(item.get("candidate_id"))
    }
    requirements = [
        dict(item)
        for item in _sequence_of_mappings(ledger.get("source_requirements"))
        if _clean_token(item.get("requirement_id"))
    ]
    return {"candidate_records": candidate_records, "requirements": requirements}


def _custodied_candidate_ids(
    custody: Mapping[str, Any],
    *,
    component_ids: Sequence[str],
    source_obligation_ids: Sequence[str],
    requirement_ids: Sequence[str],
) -> tuple[str, ...]:
    component_keys = {_ref_key(value) for value in component_ids}
    obligation_keys = {_ref_key(value) for value in source_obligation_ids}
    requirement_keys = {_ref_key(value) for value in requirement_ids}
    out: list[str] = []
    for requirement in _sequence_of_mappings(custody.get("requirements")):
        if _clean_token(requirement.get("status")) != "satisfied":
            continue
        if _kind_family(requirement) != "source_bound_numeric":
            continue
        req_key = _ref_key(requirement.get("requirement_id"))
        component_key = _ref_key(requirement.get("component_id"))
        obligation_key = _ref_key(requirement.get("source_obligation_id"))
        if requirement_keys and req_key not in requirement_keys:
            continue
        if component_keys and component_key and component_key not in component_keys:
            continue
        if obligation_keys and obligation_key and obligation_key not in obligation_keys:
            continue
        for candidate_id in _text_list(requirement.get("linked_candidate_ids")):
            if candidate_id not in out:
                out.append(candidate_id)
    return tuple(out)


def _candidate_fixture_index(
    candidate_records: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(_runtime_record_items(candidate_records), start=1):
        candidate_id = _runtime_candidate_id(item, index=index)
        if candidate_id:
            out[candidate_id] = dict(item)
    return out


def _runtime_record_items(value: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        direct_items: list[Mapping[str, Any]] = []
        for key in ("candidates", "candidate_records", "results", "records", "retrieval_records"):
            direct_items.extend(_sequence_of_mappings(value.get(key)))
        return tuple(direct_items)
    return tuple(_sequence_of_mappings(value))


def _runtime_candidate_id(record: Mapping[str, Any], *, index: int) -> str | None:
    explicit = _ledger_token(record.get("candidate_id"))
    if explicit:
        return explicit
    if source_id := _clean_token(record.get("source_id")):
        return f"provider_job_candidate:source:{source_id}"
    identity = _normalize_identity(
        record.get("url")
        or record.get("source_url")
        or record.get("normalized_source_identity")
        or record.get("source_identity")
        or record.get("title")
    )
    if identity:
        return f"provider_job_candidate:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"
    return f"provider_job_candidate:runtime:{index}"


def _allowed_calculation(unit: Mapping[str, Any]) -> str:
    metadata = _mapping(unit.get("metadata"))
    explicit = _clean_token(
        unit.get("allowed_calculation_kind")
        or unit.get("calculation_kind")
        or metadata.get("allowed_calculation_kind")
        or metadata.get("calculation_kind")
    )
    if explicit:
        return explicit
    allowed = _text_list(unit.get("allowed_calculations"))
    if allowed:
        return allowed[0]
    target = _clean_text(unit.get("target_metric"), limit=200) or ""
    target_key = target.casefold().replace("-", "_").replace(" ", "_")
    if len(_text_list(unit.get("required_variables"))) == 1:
        return "identity"
    for candidate in ("percent_change", "difference", "ratio", "average", "sum"):
        if candidate in target_key:
            return candidate
    return "identity"


def _expected_units(unit: Mapping[str, Any]) -> dict[str, str]:
    metadata = _mapping(unit.get("metadata"))
    raw = _mapping(unit.get("variable_units") or metadata.get("variable_units"))
    return {
        _var_key(key): _clean_token(value, limit=80)
        for key, value in raw.items()
        if _var_key(key) and _clean_token(value, limit=80)
    }


def _source_refs(extracted: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for variable, fact in extracted.items():
        refs.append(
            _compact(
                {
                    "variable": variable,
                    "candidate_id": fact.get("candidate_id"),
                    "source_id": fact.get("source_id"),
                    "url": fact.get("url"),
                    "domain": fact.get("domain"),
                    "title": fact.get("title"),
                    "source_class": fact.get("source_class"),
                    "source_tier": fact.get("source_tier"),
                }
            )
        )
    return refs


def _extraction_status(
    *,
    extracted: Mapping[str, Mapping[str, Any]],
    unresolved_values: Sequence[Mapping[str, Any]],
    blocked_reasons: Sequence[str],
) -> str:
    if any(reason == "ambiguous_or_conflicting_numeric_values" for reason in blocked_reasons):
        return "conflict"
    if unresolved_values:
        return "unresolved"
    if extracted:
        return "succeeded"
    return "unresolved"


def _result_unit(
    calculation_kind: str,
    required_variables: Sequence[str],
    extracted_values: Mapping[str, Mapping[str, Any]],
) -> str | None:
    units = [
        _clean_token(extracted_values[variable].get("unit"), limit=80)
        for variable in required_variables
        if _clean_token(extracted_values[variable].get("unit"), limit=80)
    ]
    if not units:
        return None
    if calculation_kind == "percent_change":
        return "percent"
    if calculation_kind == "ratio" and len(units) == 2 and _unit_key(units[0]) != _unit_key(units[1]):
        return f"{units[0]}_per_{units[1]}"
    return units[0]


def _behavior_flags(*, any_resolved: bool) -> dict[str, bool]:
    return {
        "provider_search_behavior_changed": False,
        "provider_selected": False,
        "search_executed": False,
        "retrieval_executed": False,
        "model_called": False,
        "prompt_behavior_changed": False,
        "citation_behavior_changed": False,
        "author_prose_behavior_changed": False,
        "arbitrary_code_execution_used": False,
        "quant_extraction_executed": True,
        "calculation_executed": bool(any_resolved),
    }


def _kind_family(requirement: Mapping[str, Any]) -> str:
    raw = _ref_key(
        requirement.get("requirement_kind")
        or requirement.get("kind")
        or requirement.get("required_source_class")
    )
    if raw in {"source_bound", "source_bound_numeric", "sourced_numeric_values"}:
        return "source_bound_numeric"
    return raw or "general"


def _decimal_value(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _decimal_to_json(value: Decimal) -> int | float | str:
    if value == value.to_integral_value():
        return int(value)
    normalized = value.normalize()
    text = format(normalized, "f")
    try:
        return float(text)
    except ValueError:
        return text


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence_of_mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
    if value is None or isinstance(value, str | bytes):
        return ()
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _text_list(value: Any) -> list[str]:
    if value is None or isinstance(value, str | bytes):
        values = () if value is None else (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        values = (value,)
    out: list[str] = []
    for item in values:
        token = _clean_token(item)
        if token and token not in out:
            out.append(token)
    return out


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _var_key(value: Any) -> str:
    return _ref_key(value)


def _unit_key(value: Any) -> str:
    return _ref_key(value)


def _ref_key(value: Any) -> str:
    text = _clean_token(value)
    return text.casefold().replace("-", "_").replace(":", "_").replace(" ", "_") if text else ""


def _ledger_token(value: Any) -> str:
    text = _clean_token(value)
    return text.casefold().replace("-", "_").replace(" ", "_") if text else ""


def _normalize_identity(value: Any) -> str:
    text = _clean_text(value, limit=500) or ""
    if not text:
        return ""
    parsed = urlparse(text)
    if not parsed.netloc:
        return text.casefold()
    return urlunparse(
        (
            parsed.scheme.casefold() or "https",
            parsed.netloc.casefold(),
            parsed.path.rstrip("/"),
            "",
            parsed.query,
            "",
        )
    )


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, [], {})}


def _safe_json(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[redacted]"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Decimal):
        return _decimal_to_json(value)
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_token(key, limit=100)
            if not key_text or _is_sensitive_key(key_text):
                continue
            out[key_text] = _safe_json(item, depth=depth + 1)
        return out
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_safe_json(item, depth=depth + 1) for item in value]
    return _clean_text(value, limit=300)


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().casefold()
    return normalized.startswith("raw_") or normalized in _SENSITIVE_KEYS


def _clean_text(value: Any, *, limit: int = 300) -> str | None:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


__all__ = [
    "QUANT_WORK_UNIT_PACKET_SCHEMA_VERSION",
    "QUANT_WORK_UNIT_PACKET_TRACE_KEY",
    "build_quant_work_unit_packets",
    "quant_work_packet_trace_fragment",
]
