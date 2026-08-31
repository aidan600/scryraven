"""Ordinary product activation for deterministic source-bound calculation.

The module owns the one production Specialist capability, its fixed registry
and policy, deterministic local source catalogs, the closed numeric parser,
and the adapter that maps pure calculation facts into the generic S0 result
contract.  It performs no provider/model/search/retrieval/fetch/read work and
has no admission, Sufficiency, FinalAnswerPacket, Author, citation, or source-
obligation authority.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_analyst_evidence_set import (
    ComponentAnalystEvidenceSetError,
    component_analyst_evidence_member_code_evidence,
    validate_component_analyst_evidence_set,
)
from core.evidence_ledger import source_taxonomy_quality_facts
from core.specialist_graph_runtime import (
    EXECUTION_BLOCKED,
    EXECUTION_COMPLETED,
    EXECUTION_CONTESTED,
    SPECIALIST_CAPABILITY_REQUEST_MAX_BYTES,
    SPECIALIST_CAPABILITY_REQUEST_MAX_DEPTH,
    SPECIALIST_CAPABILITY_REQUEST_MAX_LIST_ITEMS,
    SPECIALIST_CAPABILITY_REQUEST_MAX_MAPPING_KEYS,
    SPECIALIST_CAPABILITY_REQUEST_MAX_STRING_LENGTH,
    SPECIALIST_NEED_SCHEMA_VERSION,
    SpecialistCapabilityRegistry,
    SpecialistCapabilitySpec,
    SpecialistExecutionPolicy,
)
from core.specialist_source_bound_calculation_runtime import (
    SUPPORTED_OPERATORS,
    evaluate_source_bound_calculation,
)

QUANTITATIVE_CAPABILITY_ID = "specialist.source_bound_calculation"
QUANTITATIVE_CAPABILITY_VERSION = "1.0.0"
QUANTITATIVE_CAPABILITY_REQUIREMENT = "source_bound_quantitative_calculation"
QUANTITATIVE_INPUT_SCHEMA_REF = "specialist.source_bound_calculation.request.v1"
QUANTITATIVE_OUTPUT_SCHEMA_REF = "specialist.source_bound_calculation.result.v1"
QUANTITATIVE_SOURCE_CATALOG_SCHEMA = "quantitative_source_catalog.v1"
QUANTITATIVE_RESULT_KIND = "source_bound_quantitative_calculation_result"
NUMERIC_LITERAL_PARSER_VERSION = "source_bound_numeric_literal_parser.v1"
NUMERIC_LITERAL_PARSER_DIGEST = sha256(
    (
        NUMERIC_LITERAL_PARSER_VERSION
        + ":decimal-dot:grouped-comma:explicit-scale:explicit-unit:exact-literal"
    ).encode("utf-8")
).hexdigest()

MAX_OPERANDS = 8
MAX_NUMERIC_LITERAL_LENGTH = 120
QUANTITATIVE_PROPOSAL_CONTRACT_SCHEMA_VERSION = (
    "quantitative_specialist_proposal_contract.v2"
)
QUANTITATIVE_SYNTHESIS_TARGET_KEY_RULE = (
    "must equal one synthesis_key proposed in the same artifact"
)
QUANTITATIVE_PROPOSAL_ALLOWED_FIELDS = (
    "schema_version",
    "local_need_id",
    "capability_requirement",
    "candidate_capability_hint",
    "bounded_question",
    "target",
    "posture",
    "input_schema_ref",
    "expected_output_schema_ref",
    "input_artifact_refs",
    "assumptions",
    "caveats",
    "nonclaims",
    "advisory_budget_posture",
    "recursion_depth",
    "specialist_parent_ref",
    "capability_request",
)
QUANTITATIVE_PROPOSAL_REQUIRED_FIELDS = (
    "schema_version",
    "local_need_id",
    "capability_requirement",
    "candidate_capability_hint",
    "bounded_question",
    "target",
    "posture",
    "input_schema_ref",
    "expected_output_schema_ref",
    "recursion_depth",
    "specialist_parent_ref",
    "capability_request",
)
QUANTITATIVE_REQUEST_ALLOWED_FIELDS = frozenset(
    {
        "request_kind",
        "calculation_kind",
        "formula_label",
        "expected_output_unit",
        "expected_precision_posture",
        "operands",
        "claim_binding",
        "assumptions",
        "caveats",
    }
)
QUANTITATIVE_REQUEST_REQUIRED_FIELDS = frozenset(
    {"request_kind", "calculation_kind", "operands", "claim_binding"}
)
QUANTITATIVE_OPERAND_ALLOWED_FIELDS = frozenset(
    {
        "local_operand_key",
        "label",
        "source_local_key",
        "source_numeric_literal",
        "literal_occurrence",
        "operand_role",
        "pair_key",
    }
)
QUANTITATIVE_OPERAND_REQUIRED_FIELDS = frozenset(
    {
        "local_operand_key",
        "source_local_key",
        "source_numeric_literal",
        "operand_role",
    }
)
QUANTITATIVE_CLAIM_BINDING_FIELDS = frozenset(
    {"proposed_result_literal", "literal_occurrence", "expected_result_unit"}
)
QUANTITATIVE_OPERATOR_ROLE_POLICIES: dict[str, dict[str, Any]] = {
    "sum": {
        "minimum_operands": 2,
        "roles": {"term": "at_least_two"},
        "pair_key": "prohibited",
    },
    "difference": {
        "exact_operands": 2,
        "roles": {"minuend": 1, "subtrahend": 1},
        "pair_key": "prohibited",
    },
    "product": {
        "minimum_operands": 2,
        "roles": {"factor": "at_least_two"},
        "pair_key": "prohibited",
    },
    "ratio": {
        "exact_operands": 2,
        "roles": {"numerator": 1, "denominator": 1},
        "pair_key": "prohibited",
    },
    "percentage": {
        "exact_operands": 2,
        "roles": {"numerator": 1, "denominator": 1},
        "pair_key": "prohibited",
    },
    "percentage_point_difference": {
        "exact_operands": 2,
        "roles": {"minuend": 1, "subtrahend": 1},
        "pair_key": "prohibited",
    },
    "simple_rate": {
        "exact_operands": 2,
        "roles": {"numerator": 1, "denominator": 1},
        "pair_key": "prohibited",
    },
    "weighted_average": {
        "minimum_pair_groups": 2,
        "roles_per_pair": {"value": 1, "weight": 1},
        "pair_key": "required",
    },
}
QUANTITATIVE_PROHIBITED_PROPOSAL_FIELDS = (
    "canonical IDs or digests",
    "action or lease refs",
    "graph or admission refs",
    "provider or model routes",
    "URLs",
    "arbitrary field paths",
    "search or retrieval authority",
)
QUANTITATIVE_PROHIBITED_REQUEST_FIELDS = (
    "numeric_value",
    "parsed values",
    "formulas or expressions",
    "code",
    "estimates",
    "conversions",
    "model-prior numbers",
    "component, node, or graph authority",
    "source URLs",
    "arbitrary JSON or field paths",
    "prompts, responses, provider, search, or retrieval material",
)
_PRECISION_POSTURES = frozenset(
    {"exact_as_reported", "rounded_as_reported", "approximate_as_reported"}
)
_SCALE_FACTORS = {
    "thousand": Decimal("1000"),
    "million": Decimal("1000000"),
    "billion": Decimal("1000000000"),
    "trillion": Decimal("1000000000000"),
}
_ACCEPTABLE_CURRENTNESS = frozenset(
    {"current", "official_current", "current_primary_or_official"}
)
_CLEAR_CONFLICT_POSTURES = frozenset(
    {"none", "clear", "no_conflict", "uncontested"}
)
_LOCAL_KEY_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,79}\Z")
_UNIT_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9_-]{0,31}(?:[/*][A-Za-z][A-Za-z0-9_-]{0,31})*\Z"
)
_NUMBER_RE = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
_LITERAL_RE = re.compile(
    rf"""
    \A\s*
    (?:(?P<qualifier>approximately|about|rounded)\s+)?
    (?P<sign_before>[+-])?\s*
    (?:(?P<currency_code>[A-Za-z]{{3}})\s+|(?P<currency_symbol>[$€£¥])\s*)?
    (?P<sign_after>[+-])?
    (?P<number>{_NUMBER_RE})
    (?:\s+(?P<scale>thousand|million|billion|trillion))?
    (?:(?P<percent>\s*%)|(?:\s+(?P<unit>[A-Za-z][A-Za-z0-9_-]{{0,31}}(?:[/*][A-Za-z][A-Za-z0-9_-]{{0,31}})*)))?
    \s*\Z
    """,
    re.IGNORECASE | re.VERBOSE,
)


class QuantitativeSpecialistProductError(ValueError):
    """A deterministic spent-input blocker for the quantitative adapter."""

    def __init__(self, blocker_kind: str, reason: str) -> None:
        super().__init__(reason)
        self.blocker_kind = blocker_kind
        self.reason = reason


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return list(value)
    return []


def _clean_text(value: Any, *, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    return text[:limit] if text else None


def _required_text(value: Any, *, field: str, limit: int) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        raise QuantitativeSpecialistProductError(
            "invalid_input", f"quantitative request requires {field}"
        )
    return text


def _local_key(value: Any, *, field: str) -> str:
    text = _required_text(value, field=field, limit=80)
    if not _LOCAL_KEY_RE.fullmatch(text):
        raise QuantitativeSpecialistProductError(
            "invalid_input", f"{field} must be one bounded local key"
        )
    return text


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest(value: Any) -> str:
    encoded = json.dumps(
        _json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def quantitative_proposal_runtime_schema_facts() -> dict[str, Any]:
    """Return the declarative product schema also consumed by validation."""

    proposal_required = set(QUANTITATIVE_PROPOSAL_REQUIRED_FIELDS)
    request_required = set(QUANTITATIVE_REQUEST_REQUIRED_FIELDS)
    request_allowed = set(QUANTITATIVE_REQUEST_ALLOWED_FIELDS)
    operand_required = set(QUANTITATIVE_OPERAND_REQUIRED_FIELDS)
    operand_allowed = set(QUANTITATIVE_OPERAND_ALLOWED_FIELDS)
    return {
        "proposal_schema": {
            "allowed_fields": list(QUANTITATIVE_PROPOSAL_ALLOWED_FIELDS),
            "required_fields": list(QUANTITATIVE_PROPOSAL_REQUIRED_FIELDS),
            "optional_fields": [
                field
                for field in QUANTITATIVE_PROPOSAL_ALLOWED_FIELDS
                if field not in proposal_required
            ],
            "fixed_fields": {
                "schema_version": SPECIALIST_NEED_SCHEMA_VERSION,
                "capability_requirement": QUANTITATIVE_CAPABILITY_REQUIREMENT,
                "candidate_capability_hint": QUANTITATIVE_CAPABILITY_ID,
                "input_schema_ref": QUANTITATIVE_INPUT_SCHEMA_REF,
                "expected_output_schema_ref": QUANTITATIVE_OUTPUT_SCHEMA_REF,
                "recursion_depth": 0,
                "specialist_parent_ref": None,
            },
            "locally_selected_fields": [
                field
                for field in QUANTITATIVE_PROPOSAL_ALLOWED_FIELDS
                if field
                not in {
                    "schema_version",
                    "capability_requirement",
                    "candidate_capability_hint",
                    "input_schema_ref",
                    "expected_output_schema_ref",
                    "recursion_depth",
                    "specialist_parent_ref",
                }
            ],
            "prohibited_fields": list(QUANTITATIVE_PROHIBITED_PROPOSAL_FIELDS),
        },
        "capability_request_schema": {
            "allowed_fields": sorted(request_allowed),
            "required_fields": sorted(request_required),
            "optional_fields": sorted(request_allowed - request_required),
            "fixed_fields": {"request_kind": "source_bound_calculation"},
            "operand_schema": {
                "allowed_fields": sorted(operand_allowed),
                "required_fields": sorted(operand_required),
                "optional_fields": sorted(operand_allowed - operand_required),
                "literal_occurrence_rule": (
                    "optional positive one-based integer"
                ),
                "pair_key_rule": "allowed only for weighted_average",
            },
            "claim_binding_schema": {
                "allowed_fields": sorted(QUANTITATIVE_CLAIM_BINDING_FIELDS),
                "required_fields": sorted(QUANTITATIVE_CLAIM_BINDING_FIELDS),
                "literal_occurrence_rule": (
                    "required field; nullable or a positive one-based integer"
                ),
            },
            "supported_operators": sorted(SUPPORTED_OPERATORS),
            "operator_role_rules": deepcopy(QUANTITATIVE_OPERATOR_ROLE_POLICIES),
            "raw_operand_array_order_defines_noncommutative_semantics": False,
            "limits": {
                "maximum_operands": MAX_OPERANDS,
                "maximum_numeric_literal_characters": (
                    MAX_NUMERIC_LITERAL_LENGTH
                ),
                "generic_capability_request_maximum_canonical_json_bytes": (
                    SPECIALIST_CAPABILITY_REQUEST_MAX_BYTES
                ),
                "generic_capability_request_maximum_depth": (
                    SPECIALIST_CAPABILITY_REQUEST_MAX_DEPTH
                ),
                "generic_capability_request_maximum_mapping_keys": (
                    SPECIALIST_CAPABILITY_REQUEST_MAX_MAPPING_KEYS
                ),
                "generic_capability_request_maximum_list_items": (
                    SPECIALIST_CAPABILITY_REQUEST_MAX_LIST_ITEMS
                ),
                "generic_capability_request_maximum_string_characters": (
                    SPECIALIST_CAPABILITY_REQUEST_MAX_STRING_LENGTH
                ),
            },
            "prohibited_fields": list(QUANTITATIVE_PROHIBITED_REQUEST_FIELDS),
        },
    }


QUANTITATIVE_PROPOSAL_CONTRACT_DIGEST = _digest(
    {
        "schema_version": QUANTITATIVE_PROPOSAL_CONTRACT_SCHEMA_VERSION,
        **quantitative_proposal_runtime_schema_facts(),
    }
)


def build_quantitative_specialist_proposal_contract(
    target_kind: str,
    target_key_or_rule: str,
    allowed_source_local_keys: Sequence[str],
) -> dict[str, Any]:
    """Build one model-visible contract from the executable product schema."""

    if target_kind not in {"component", "synthesis"}:
        raise ValueError("quantitative proposal contract target_kind is invalid")
    target_value = _required_text(
        target_key_or_rule, field="target_key_or_rule", limit=360
    )
    source_keys = [
        _local_key(item, field="allowed_source_local_keys")
        for item in allowed_source_local_keys
    ]
    if not source_keys or len(source_keys) != len(set(source_keys)):
        raise ValueError(
            "quantitative proposal contract requires unique source local keys"
        )
    target_contract = {"target_kind": target_kind}
    if target_kind == "component":
        target_contract["target_key"] = target_value
        output_rule = (
            "return the ordinary component fields and, only when needed, one "
            "sibling specialist_need_proposal"
        )
    else:
        target_contract["target_key_rule"] = target_value
        output_rule = (
            "return one top-level object containing synthesis_proposals and, "
            "when needed, one sibling specialist_need_proposal; the Specialist "
            "proposal is not nested inside a synthesis proposal"
        )
    contract = {
        "schema_version": QUANTITATIVE_PROPOSAL_CONTRACT_SCHEMA_VERSION,
        "contract_digest": QUANTITATIVE_PROPOSAL_CONTRACT_DIGEST,
        **quantitative_proposal_runtime_schema_facts(),
        "target_contract": target_contract,
        "allowed_source_local_keys": source_keys,
        "output_rule": output_rule,
    }
    contract["instance_digest"] = _digest(contract)
    return contract


def validate_quantitative_specialist_proposal_contract(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed if a supplied model contract has drifted or been altered."""

    contract = deepcopy(dict(value))
    instance_digest = contract.pop("instance_digest", None)
    contract_fields = {
        "schema_version",
        "contract_digest",
        "proposal_schema",
        "capability_request_schema",
        "target_contract",
        "allowed_source_local_keys",
        "output_rule",
    }
    target_contract = _safe_mapping(contract.get("target_contract"))
    target_kind = target_contract.get("target_kind")
    allowed_source_keys = contract.get("allowed_source_local_keys")
    source_keys = _safe_sequence(allowed_source_keys)
    target_shape_valid = (
        set(target_contract) == {"target_kind", "target_key"}
        if target_kind == "component"
        else set(target_contract) == {"target_kind", "target_key_rule"}
        if target_kind == "synthesis"
        else False
    )
    if (
        set(contract) != contract_fields
        or contract.get("schema_version")
        != QUANTITATIVE_PROPOSAL_CONTRACT_SCHEMA_VERSION
        or contract.get("contract_digest")
        != QUANTITATIVE_PROPOSAL_CONTRACT_DIGEST
        or contract.get("proposal_schema")
        != quantitative_proposal_runtime_schema_facts()["proposal_schema"]
        or contract.get("capability_request_schema")
        != quantitative_proposal_runtime_schema_facts()[
            "capability_request_schema"
        ]
        or instance_digest != _digest(contract)
        or not target_shape_valid
        or not isinstance(allowed_source_keys, list)
        or not source_keys
        or len(source_keys) != len(set(source_keys))
        or any(
            not isinstance(item, str) or not _LOCAL_KEY_RE.fullmatch(item)
            for item in source_keys
        )
    ):
        raise QuantitativeSpecialistProductError(
            "proposal_contract_drift",
            "quantitative Specialist proposal contract does not match runtime",
        )
    return {**contract, "instance_digest": instance_digest}


def validate_quantitative_specialist_proposal_instance(
    value: Mapping[str, Any],
    *,
    proposal_contract: Mapping[str, Any],
    canonical_target_ref: Mapping[str, Any],
    same_artifact_synthesis_keys: Sequence[str] = (),
) -> dict[str, Any]:
    """Validate the exact current S1 proposal before RunKernel admission."""

    contract = validate_quantitative_specialist_proposal_contract(
        proposal_contract
    )
    proposal = deepcopy(dict(value))
    allowed_fields = set(QUANTITATIVE_PROPOSAL_ALLOWED_FIELDS)
    required_fields = set(QUANTITATIVE_PROPOSAL_REQUIRED_FIELDS)
    if set(proposal) - allowed_fields or not required_fields <= set(proposal):
        raise QuantitativeSpecialistProductError(
            "proposal_field_set_mismatch",
            "quantitative proposal has missing or unknown fields",
        )
    fixed_fields = _safe_mapping(
        _safe_mapping(contract.get("proposal_schema")).get("fixed_fields")
    )
    if any(proposal.get(key) != expected for key, expected in fixed_fields.items()):
        raise QuantitativeSpecialistProductError(
            "proposal_fixed_field_mismatch",
            "quantitative proposal fixed fields do not match the current contract",
        )
    target = _safe_mapping(proposal.get("target"))
    canonical_target = _safe_mapping(canonical_target_ref)
    target_contract = _safe_mapping(contract.get("target_contract"))
    if set(target) != {"target_kind", "target_key"} or (
        target.get("target_kind") != canonical_target.get("target_kind")
        or target.get("target_key") != canonical_target.get("target_key")
        or target.get("target_kind") != target_contract.get("target_kind")
    ):
        raise QuantitativeSpecialistProductError(
            "proposal_target_mismatch",
            "quantitative proposal target does not match current authority",
        )
    if target.get("target_kind") == "component":
        if target.get("target_key") != target_contract.get("target_key"):
            raise QuantitativeSpecialistProductError(
                "proposal_target_mismatch",
                "quantitative component target does not match its contract instance",
            )
    elif target.get("target_kind") == "synthesis":
        keys = list(same_artifact_synthesis_keys)
        if (
            not keys
            or len(keys) != len(set(keys))
            or target.get("target_key") not in keys
            or target_contract.get("target_key_rule")
            != QUANTITATIVE_SYNTHESIS_TARGET_KEY_RULE
        ):
            raise QuantitativeSpecialistProductError(
                "proposal_target_mismatch",
                "quantitative synthesis target is not from the same current artifact",
            )
    else:
        raise QuantitativeSpecialistProductError(
            "proposal_target_mismatch",
            "quantitative proposal target kind is unsupported",
        )
    request = _validate_request(_safe_mapping(proposal.get("capability_request")))
    allowed_source_keys = set(contract.get("allowed_source_local_keys") or ())
    if not allowed_source_keys or any(
        operand.get("source_local_key") not in allowed_source_keys
        for operand in request.get("operands") or ()
    ):
        raise QuantitativeSpecialistProductError(
            "proposal_source_alias_mismatch",
            "quantitative proposal source alias is not in the current contract instance",
        )
    return proposal


def _text_digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical_currency(value: Any) -> str | None:
    token = _clean_text(value, limit=3)
    if token and re.fullmatch(r"[A-Za-z]{3}", token):
        return token.upper()
    return None


def _evidence_posture(evidence: Mapping[str, Any]) -> dict[str, Any]:
    custody = _safe_mapping(evidence.get("candidate_custody_ref"))
    evidence_status = str(evidence.get("evidence_status") or "missing").casefold()
    evidence_ref_id = evidence.get("evidence_ref_id")
    custody_candidate_id = custody.get("candidate_id")
    currentness = (
        _clean_text(
            evidence.get("currentness_posture")
            or evidence.get("currentness")
            or custody.get("currentness_signal"),
            limit=120,
        )
        or "unknown"
    )
    source_class = (
        _clean_text(
            evidence.get("source_class_posture")
            or evidence.get("source_class")
            or custody.get("source_class")
            or custody.get("source_class_posture"),
            limit=120,
        )
        or "unknown"
    )
    source_tier = (
        _clean_text(
            evidence.get("source_tier") or custody.get("source_tier"),
            limit=120,
        )
        or "unknown"
    )
    fact_disposition = (
        _clean_text(
            evidence.get("fact_disposition")
            or custody.get("fact_disposition"),
            limit=80,
        )
        or "unknown"
    )
    readability = (
        _clean_text(
            evidence.get("readability_posture")
            or evidence.get("readable_status")
            or custody.get("readable_status"),
            limit=80,
        )
        or "unknown"
    )
    conflict = _clean_text(
        evidence.get("conflict_posture") or custody.get("conflict_posture"),
        limit=80,
    )
    explicit_contradictory = evidence.get("contradictory")
    if not isinstance(explicit_contradictory, bool):
        explicit_contradictory = custody.get("contradictory")
    if not conflict:
        if isinstance(explicit_contradictory, bool):
            conflict = "present" if explicit_contradictory else "none"
        elif fact_disposition.casefold() in {"contradicted", "contested"}:
            conflict = "present"
        else:
            conflict = "unknown"
    taxonomy = source_taxonomy_quality_facts(
        source_class=source_class,
        source_tier=source_tier,
    )
    lineage_complete = bool(
        evidence_status == "available"
        and evidence_ref_id
        and custody_candidate_id
        and evidence_ref_id == custody_candidate_id
    )
    quality_reasons: list[str] = []
    if currentness.casefold() not in _ACCEPTABLE_CURRENTNESS:
        quality_reasons.append("currentness_not_explicitly_acceptable")
    if taxonomy["source_class_strength"] != "strong":
        quality_reasons.append("source_class_not_explicitly_strong")
    if taxonomy["source_tier_strength"] != "strong":
        quality_reasons.append("source_tier_not_explicitly_strong")
    if conflict.casefold() not in _CLEAR_CONFLICT_POSTURES:
        quality_reasons.append("conflict_posture_not_explicitly_clear")
    if not lineage_complete:
        quality_reasons.append("evidence_lineage_incomplete")
    quality_posture = (
        "incomplete_lineage"
        if not lineage_complete
        else "authoritative_current_clear"
        if not quality_reasons
        else "contested_source_posture"
    )
    return {
        "evidence_status": evidence_status,
        "currentness_posture": currentness,
        "source_class_posture": source_class,
        "source_class": taxonomy["source_class"],
        "source_tier": taxonomy["source_tier"],
        "source_class_strength": taxonomy["source_class_strength"],
        "source_tier_strength": taxonomy["source_tier_strength"],
        "fact_disposition": fact_disposition,
        "readability_posture": readability,
        "conflict_posture": conflict,
        "contradictory": (
            explicit_contradictory is True or conflict.casefold() == "present"
        ),
        "source_quality_posture": quality_posture,
        "source_quality_reasons": quality_reasons,
        "evidence_lineage_complete": lineage_complete,
        "canonical_currency_unit": _canonical_currency(
            evidence.get("canonical_currency_unit")
            or custody.get("canonical_currency_unit")
        ),
        "evidence_ref": {
            "evidence_ref_id": evidence_ref_id,
            "candidate_id": custody_candidate_id,
        },
    }


def build_component_quantitative_source_catalog(
    *,
    component_ref: Mapping[str, Any],
    component_evidence_set: Mapping[str, Any],
    include_material: bool = False,
) -> dict[str, Any]:
    """Build one bounded local selector for every exact component member."""

    component = _safe_mapping(component_ref)
    try:
        evidence_set = validate_component_analyst_evidence_set(
            component_evidence_set
        )
    except ComponentAnalystEvidenceSetError as exc:
        raise QuantitativeSpecialistProductError(
            "invalid_component_evidence_set", str(exc)
        ) from exc
    component_lineage_ref = {
        key: component.get(key)
        for key in ("component_id", "component_revision", "component_digest")
        if component.get(key) is not None
    }
    catalog = {
        "schema_version": QUANTITATIVE_SOURCE_CATALOG_SCHEMA,
        "catalog_kind": "component_quantitative_sources",
    }
    for member in evidence_set["members"]:
        evidence = component_analyst_evidence_member_code_evidence(member)
        bounded_text = str(evidence.get("bounded_text") or "")
        posture = _evidence_posture(evidence)
        alias = str(member["local_evidence_alias"])
        entry: dict[str, Any] = {
            "source_local_key": alias,
            "source_binding_kind": "component_evidence_member",
            "allowed_source_field": "bounded_text",
            "bounded_field_digest": _text_digest(bounded_text),
            "bounded_field_present": bool(bounded_text),
            "currentness_posture": posture["currentness_posture"],
            "source_class_posture": posture["source_class_posture"],
            "source_class": posture["source_class"],
            "source_tier": posture["source_tier"],
            "source_class_strength": posture["source_class_strength"],
            "source_tier_strength": posture["source_tier_strength"],
            "fact_disposition": posture["fact_disposition"],
            "readability_posture": posture["readability_posture"],
            "conflict_posture": posture["conflict_posture"],
            "contradictory": posture["contradictory"],
            "source_quality_posture": posture["source_quality_posture"],
            "source_quality_reasons": posture["source_quality_reasons"],
            "component_lineage_ref": component_lineage_ref,
            "evidence_ref": posture["evidence_ref"],
            "lineage_complete": bool(component_lineage_ref)
            and posture["evidence_lineage_complete"],
        }
        if posture["canonical_currency_unit"]:
            entry["canonical_currency_unit"] = posture[
                "canonical_currency_unit"
            ]
        if include_material:
            entry["source_material"] = {"bounded_text": bounded_text}
        catalog[alias] = entry
    catalog["posture_digest"] = _digest(catalog)
    return catalog


def _combined_evidence_posture(
    evidence_members: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Mechanically preserve one or more admitted evidence postures.

    A synthesis source remains the admitted component claim. When that claim
    is bound to more than one Analyst-nominated member, this function does not
    choose a member: it retains exact per-member refs and reports only shared
    scalar facts. A non-shared fact is ``unknown`` rather than a new source,
    currentness, or quality classification.
    """

    postures = [_evidence_posture(item) for item in evidence_members]
    if not postures:
        raise QuantitativeSpecialistProductError(
            "missing_component_evidence",
            "admitted component claim lacks exact nominated evidence",
        )
    if len(postures) == 1:
        return postures[0]

    def common(key: str, *, unknown: Any = "unknown") -> Any:
        values = [item.get(key) for item in postures]
        return values[0] if all(value == values[0] for value in values) else unknown

    reasons: list[str] = []
    for posture in postures:
        for reason in posture.get("source_quality_reasons") or ():
            token = str(reason)
            if token and token not in reasons:
                reasons.append(token)
    return {
        "evidence_status": common("evidence_status"),
        "currentness_posture": common("currentness_posture"),
        "source_class_posture": common("source_class_posture"),
        "source_class": common("source_class"),
        "source_tier": common("source_tier"),
        "source_class_strength": common("source_class_strength"),
        "source_tier_strength": common("source_tier_strength"),
        "fact_disposition": common("fact_disposition"),
        "readability_posture": common("readability_posture"),
        "conflict_posture": common("conflict_posture"),
        "contradictory": any(
            posture.get("contradictory") is True for posture in postures
        ),
        "source_quality_posture": common(
            "source_quality_posture",
            unknown="contested_source_posture",
        ),
        "source_quality_reasons": reasons,
        "evidence_lineage_complete": all(
            posture.get("evidence_lineage_complete") is True
            for posture in postures
        ),
        "canonical_currency_unit": common(
            "canonical_currency_unit", unknown=None
        ),
        "evidence_ref": {},
        "evidence_refs": [
            deepcopy(_safe_mapping(posture.get("evidence_ref")))
            for posture in postures
        ],
    }


def build_synthesis_quantitative_source_catalog(
    *,
    component_nodes: Sequence[Mapping[str, Any]],
    component_analyst_input_packets: Mapping[str, Mapping[str, Any]],
    component_analyst_evidence_sets: Mapping[str, Mapping[str, Any]],
    include_material: bool = False,
) -> dict[str, Any]:
    """Build component_01.. aliases in exact current component order."""

    packets = {
        str(key): _safe_mapping(value)
        for key, value in component_analyst_input_packets.items()
    }
    try:
        evidence_sets = {
            str(component_id): validate_component_analyst_evidence_set(
                _safe_mapping(evidence_set)
            )
            for component_id, evidence_set in component_analyst_evidence_sets.items()
        }
    except ComponentAnalystEvidenceSetError as exc:
        raise QuantitativeSpecialistProductError(
            "invalid_component_evidence_set", str(exc)
        ) from exc
    if set(packets) != set(evidence_sets):
        raise QuantitativeSpecialistProductError(
            "component_evidence_set_packet_mismatch",
            "synthesis source catalog requires the same current component packet and evidence-set targets",
        )
    catalog: dict[str, Any] = {
        "schema_version": QUANTITATIVE_SOURCE_CATALOG_SCHEMA,
        "catalog_kind": "synthesis_quantitative_sources",
    }
    for index, raw_node in enumerate(component_nodes, start=1):
        node = _safe_mapping(raw_node)
        alias = f"component_{index:02d}"
        component_id = str(node.get("component_id") or "")
        claim = _safe_mapping(node.get("admitted_claim_ref"))
        raw_claim_text = claim.get("claim_text") or node.get("claim_text")
        claim_text = str(raw_claim_text) if raw_claim_text is not None else None
        claim_material = claim_text or ""
        graph_evidence_refs = [
            _safe_mapping(item) for item in node.get("evidence_refs") or ()
        ]
        evidence_set = evidence_sets.get(component_id)
        has_exact_component_evidence = bool(
            evidence_set and graph_evidence_refs
        )
        if has_exact_component_evidence:
            selected_evidence_ref_ids = [
                str(item.get("evidence_ref_id") or "")
                for item in graph_evidence_refs
            ]
            members_by_evidence_ref = {
                str(
                    component_analyst_evidence_member_code_evidence(member).get(
                        "evidence_ref_id"
                    )
                    or ""
                ): member
                for member in evidence_set["members"]
            }
            if (
                not selected_evidence_ref_ids
                or any(
                    not evidence_ref_id
                    or evidence_ref_id not in members_by_evidence_ref
                    for evidence_ref_id in selected_evidence_ref_ids
                )
                or len(selected_evidence_ref_ids)
                != len(set(selected_evidence_ref_ids))
            ):
                raise QuantitativeSpecialistProductError(
                    "component_evidence_binding_mismatch",
                    "admitted component claim evidence is not an exact set member",
                )
            selected_evidence = [
                component_analyst_evidence_member_code_evidence(
                    members_by_evidence_ref[evidence_ref_id]
                )
                for evidence_ref_id in selected_evidence_ref_ids
            ]
            evidence_texts = [
                str(evidence.get("bounded_text") or "")
                for evidence in selected_evidence
            ]
            posture = _combined_evidence_posture(selected_evidence)
        else:
            # Cross can be called before an admitted component has an
            # evidence-reference binding (for example, while it is still
            # proposal-only). Preserve the established claim-only catalog in
            # that pre-admission state; it has no evidence-member selector and
            # cannot stand in for the exact-set path above.
            evidence_texts = []
            posture = _evidence_posture({})
        component_lineage_ref = {
            key: node.get(key)
            for key in (
                "component_id",
                "component_revision",
                "component_digest",
                "node_id",
                "node_revision",
                "node_digest",
            )
            if node.get(key) is not None
        }
        entry: dict[str, Any] = {
            "source_local_key": alias,
            "source_binding_kind": "admitted_component_claim",
            "allowed_source_field": "claim_text",
            "bounded_field_digest": _text_digest(claim_material),
            "bounded_field_present": bool(claim_text),
            "underlying_evidence_field_digest": (
                _text_digest("\n".join(evidence_texts))
                if evidence_texts
                else next(
                    (
                        str(item.get("content_digest"))
                        for item in graph_evidence_refs
                        if item.get("content_digest")
                    ),
                    None,
                )
            ),
            "underlying_evidence_present": (
                bool(evidence_texts) and all(evidence_texts)
            ) or (not has_exact_component_evidence and bool(graph_evidence_refs)),
            "admission_status": node.get("admission_status"),
            "current": node.get("current") is True,
            "stale": node.get("stale") is True,
            "currentness_posture": posture["currentness_posture"],
            "source_class_posture": posture["source_class_posture"],
            "source_class": posture["source_class"],
            "source_tier": posture["source_tier"],
            "source_class_strength": posture["source_class_strength"],
            "source_tier_strength": posture["source_tier_strength"],
            "fact_disposition": posture["fact_disposition"],
            "readability_posture": posture["readability_posture"],
            "conflict_posture": posture["conflict_posture"],
            "contradictory": posture["contradictory"],
            "source_quality_posture": posture["source_quality_posture"],
            "source_quality_reasons": posture["source_quality_reasons"],
            "component_lineage_ref": component_lineage_ref,
            "admitted_claim_ref": {
                key: claim.get(key)
                for key in ("claim_id", "claim_digest")
                if claim.get(key) is not None
            },
            "evidence_ref": posture["evidence_ref"],
            "lineage_complete": bool(component_lineage_ref)
            and bool(claim_text)
            and posture["evidence_lineage_complete"],
        }
        if posture["canonical_currency_unit"]:
            entry["canonical_currency_unit"] = posture["canonical_currency_unit"]
        if include_material:
            entry["source_material"] = {
                "claim_text": claim_material,
                "underlying_evidence_texts": evidence_texts,
            }
        catalog[alias] = entry
    nonmaterial_catalog = deepcopy(catalog)
    for value in nonmaterial_catalog.values():
        if isinstance(value, dict):
            value.pop("source_material", None)
    catalog["posture_digest"] = _digest(nonmaterial_catalog)
    return catalog


def _normalize_unit(value: Any, *, required: bool = False) -> str | None:
    if value is not None and not isinstance(value, str):
        raise QuantitativeSpecialistProductError(
            "invalid_unit", "quantitative unit must be a bounded string"
        )
    text = _clean_text(value, limit=100)
    if not text:
        if required:
            raise QuantitativeSpecialistProductError(
                "missing_unit", "quantitative value requires an explicit unit"
            )
        return None
    if text in {"%", "percent", "percentage"}:
        return "percent"
    if not _UNIT_RE.fullmatch(text):
        raise QuantitativeSpecialistProductError(
            "invalid_unit", "quantitative unit is outside the closed unit grammar"
        )
    parts = re.split(r"([/*])", text)
    normalized: list[str] = []
    for part in parts:
        if part in {"/", "*"}:
            normalized.append(part)
            continue
        token = part.casefold()
        if token in _SCALE_FACTORS:
            raise QuantitativeSpecialistProductError(
                "scale_applied_more_than_once",
                "scale words cannot be used as canonical units",
            )
        if token in {"percent", "percentage"}:
            normalized.append("percent")
        elif len(part) == 3 and part.isalpha() and part.isupper():
            normalized.append(part.upper())
        else:
            normalized.append(token)
    return "".join(normalized)


def parse_source_bound_numeric_literal(
    literal: str,
    *,
    canonical_currency_unit: str | None = None,
) -> dict[str, Any]:
    """Parse one exact selected literal directly to Decimal under a closed grammar."""

    if not isinstance(literal, str) or not 1 <= len(literal) <= MAX_NUMERIC_LITERAL_LENGTH:
        raise QuantitativeSpecialistProductError(
            "invalid_numeric_literal", "numeric literal length is invalid"
        )
    match = _LITERAL_RE.fullmatch(literal)
    if match is None:
        raise QuantitativeSpecialistProductError(
            "invalid_numeric_literal", "numeric literal is outside the closed grammar"
        )
    if match.group("sign_before") and match.group("sign_after"):
        raise QuantitativeSpecialistProductError(
            "invalid_numeric_literal", "numeric literal contains multiple signs"
        )
    numeric_text = match.group("number")
    try:
        value = Decimal(numeric_text.replace(",", ""))
    except InvalidOperation as exc:
        raise QuantitativeSpecialistProductError(
            "invalid_numeric_literal", "numeric literal is not Decimal-compatible"
        ) from exc
    if (match.group("sign_before") or match.group("sign_after")) == "-":
        value = -value
    scale = str(match.group("scale") or "unit_scale").casefold()
    if scale != "unit_scale":
        value *= _SCALE_FACTORS[scale]

    currency_code = match.group("currency_code")
    currency_symbol = match.group("currency_symbol")
    suffix_unit = match.group("unit")
    percent = match.group("percent")
    if currency_symbol:
        currency = _canonical_currency(canonical_currency_unit)
        if not currency:
            raise QuantitativeSpecialistProductError(
                "ambiguous_currency_symbol",
                "ambiguous currency symbol lacks a structured catalog currency fact",
            )
        unit = currency
    elif currency_code:
        unit = str(currency_code).upper()
    elif percent:
        unit = "percent"
    else:
        unit = _normalize_unit(suffix_unit)
    if currency_code and suffix_unit:
        suffix = _normalize_unit(suffix_unit)
        if suffix != unit:
            raise QuantitativeSpecialistProductError(
                "incompatible_units", "numeric literal contains conflicting units"
            )
    qualifier = str(match.group("qualifier") or "").casefold()
    precision = (
        "approximate_as_reported"
        if qualifier in {"approximately", "about"}
        else "rounded_as_reported"
        if qualifier == "rounded"
        else "exact_as_reported"
    )
    return {
        "numeric_value": value,
        "numeric_value_text": _decimal_text(value),
        "unit": unit,
        "scale": scale,
        "precision_posture": precision,
        "parser_version": NUMERIC_LITERAL_PARSER_VERSION,
        "parser_digest": NUMERIC_LITERAL_PARSER_DIGEST,
    }


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _literal_occurrences(material: str, literal: str) -> list[tuple[int, int]]:
    right_boundary = (
        r"(?![A-Za-z0-9_]|[.,]\d)"
        if literal.rstrip()[-1].isdigit()
        else r"(?![A-Za-z0-9_])"
    )
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_.,]){re.escape(literal)}{right_boundary}"
    )
    return [match.span() for match in pattern.finditer(material)]


def _bind_operand_literal(
    *,
    entry: Mapping[str, Any],
    source_local_key: str,
    literal: str,
    occurrence: int | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    binding_kind = str(entry.get("source_binding_kind") or "")
    material = _safe_mapping(entry.get("source_material"))
    source_text = str(
        (
            material.get("bounded_text")
            if binding_kind == "component_evidence_member"
            else material.get("claim_text")
        )
        or ""
    )
    matches = _literal_occurrences(source_text, literal)
    if not matches:
        raise QuantitativeSpecialistProductError(
            "source_literal_absent", "selected numeric literal is absent from its source"
        )
    if len(matches) > 1 and occurrence is None:
        raise QuantitativeSpecialistProductError(
            "ambiguous_source_literal",
            "repeated numeric literal requires one-based literal_occurrence",
        )
    selected = occurrence or 1
    if selected < 1 or selected > len(matches):
        raise QuantitativeSpecialistProductError(
            "invalid_literal_occurrence", "literal_occurrence is outside source matches"
        )
    start, end = matches[selected - 1]
    underlying_posture = "not_applicable"
    underlying_digest = None
    if binding_kind == "admitted_component_claim":
        evidence_texts = [
            str(item)
            for item in material.get("underlying_evidence_texts") or ()
            if str(item)
        ]
        matching_evidence_texts = [
            evidence_text
            for evidence_text in evidence_texts
            if _literal_occurrences(evidence_text, literal)
        ]
        if not matching_evidence_texts:
            raise QuantitativeSpecialistProductError(
                "claim_only_numeric_invention",
                "synthesis literal is absent from underlying component evidence",
            )
        if len(matching_evidence_texts) != 1:
            raise QuantitativeSpecialistProductError(
                "ambiguous_underlying_evidence_member",
                "synthesis literal occurs in more than one exact component evidence member",
            )
        underlying_posture = "exact_literal_found_in_underlying_evidence"
        underlying_digest = _text_digest(matching_evidence_texts[0])
    parsed = parse_source_bound_numeric_literal(
        literal,
        canonical_currency_unit=_canonical_currency(
            entry.get("canonical_currency_unit")
        ),
    )
    ref = {
        "source_local_key": source_local_key,
        "source_binding_kind": binding_kind,
        "source_material_digest": _text_digest(source_text),
        "selected_literal_digest": _text_digest(literal),
        "selected_occurrence": selected,
        "bounded_character_span": {"start": start, "end": end},
        "parser_version": NUMERIC_LITERAL_PARSER_VERSION,
        "parser_digest": NUMERIC_LITERAL_PARSER_DIGEST,
        "component_lineage_ref": deepcopy(entry.get("component_lineage_ref") or {}),
        "evidence_ref": deepcopy(entry.get("evidence_ref") or {}),
        "admitted_claim_ref": deepcopy(entry.get("admitted_claim_ref") or {}),
        "underlying_evidence_match_posture": underlying_posture,
    }
    if underlying_digest:
        ref["underlying_evidence_material_digest"] = underlying_digest
    return parsed, ref


def _positive_occurrence(value: Any, *, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise QuantitativeSpecialistProductError(
            "invalid_literal_occurrence", f"{field} must be a positive one-based integer"
        )
    return value


def _text_list(value: Any, *, field: str, maximum: int = 8) -> list[str]:
    values = _safe_sequence(value)
    if len(values) > maximum:
        raise QuantitativeSpecialistProductError(
            "invalid_input", f"{field} exceeds its bounded list limit"
        )
    result: list[str] = []
    for item in values:
        text = _required_text(item, field=field, limit=300)
        if text not in result:
            result.append(text)
    return result


def _validate_request(value: Mapping[str, Any]) -> dict[str, Any]:
    request = _safe_mapping(value)
    if (
        set(request) - QUANTITATIVE_REQUEST_ALLOWED_FIELDS
        or not QUANTITATIVE_REQUEST_REQUIRED_FIELDS <= set(request)
    ):
        raise QuantitativeSpecialistProductError(
            "invalid_input", "quantitative request has missing or unknown fields"
        )
    if request.get("request_kind") != "source_bound_calculation":
        raise QuantitativeSpecialistProductError(
            "not_applicable", "quantitative request_kind is unsupported"
        )
    calculation_kind = str(request.get("calculation_kind") or "").casefold()
    if calculation_kind not in SUPPORTED_OPERATORS:
        raise QuantitativeSpecialistProductError(
            "not_applicable", "quantitative calculation_kind is unsupported"
        )
    formula_label = _clean_text(request.get("formula_label"), limit=160)
    if request.get("formula_label") is not None and not formula_label:
        raise QuantitativeSpecialistProductError(
            "invalid_input", "formula_label must be a bounded nonempty string"
        )
    expected_unit = _normalize_unit(request.get("expected_output_unit"))
    expected_precision = _clean_text(
        request.get("expected_precision_posture"), limit=80
    )
    if request.get("expected_precision_posture") is not None and not expected_precision:
        raise QuantitativeSpecialistProductError(
            "invalid_input",
            "expected_precision_posture must be a bounded nonempty string",
        )
    if expected_precision and expected_precision not in _PRECISION_POSTURES:
        raise QuantitativeSpecialistProductError(
            "invalid_input", "expected_precision_posture is invalid"
        )

    raw_operands = _safe_sequence(request.get("operands"))
    if not 1 <= len(raw_operands) <= MAX_OPERANDS:
        raise QuantitativeSpecialistProductError(
            "invalid_input", "quantitative request requires one to eight operands"
        )
    operands: list[dict[str, Any]] = []
    for raw_operand in raw_operands:
        operand = _safe_mapping(raw_operand)
        if (
            set(operand) - QUANTITATIVE_OPERAND_ALLOWED_FIELDS
            or not QUANTITATIVE_OPERAND_REQUIRED_FIELDS <= set(operand)
        ):
            raise QuantitativeSpecialistProductError(
                "invalid_input", "quantitative operand has missing or unknown fields"
            )
        literal = _required_text(
            operand.get("source_numeric_literal"),
            field="source_numeric_literal",
            limit=MAX_NUMERIC_LITERAL_LENGTH,
        )
        if len(str(operand.get("source_numeric_literal"))) > MAX_NUMERIC_LITERAL_LENGTH:
            raise QuantitativeSpecialistProductError(
                "invalid_numeric_literal", "source_numeric_literal exceeds 120 characters"
            )
        label = _clean_text(operand.get("label"), limit=160)
        if operand.get("label") is not None and not label:
            raise QuantitativeSpecialistProductError(
                "invalid_input", "operand label must be a bounded nonempty string"
            )
        operands.append(
            {
                "local_operand_key": _local_key(
                    operand.get("local_operand_key"), field="local_operand_key"
                ),
                "label": label,
                "source_local_key": _local_key(
                    operand.get("source_local_key"), field="source_local_key"
                ),
                "source_numeric_literal": literal,
                "literal_occurrence": _positive_occurrence(
                    operand.get("literal_occurrence"), field="literal_occurrence"
                ),
                "operand_role": _local_key(
                    operand.get("operand_role"), field="operand_role"
                ).casefold(),
                "pair_key": (
                    _local_key(operand.get("pair_key"), field="pair_key")
                    if operand.get("pair_key") is not None
                    else None
                ),
            }
        )
    keys = [item["local_operand_key"] for item in operands]
    if len(keys) != len(set(keys)):
        raise QuantitativeSpecialistProductError(
            "invalid_input", "local_operand_key values must be unique"
        )
    _validate_operand_roles(calculation_kind, operands)

    claim = _safe_mapping(request.get("claim_binding"))
    if set(claim) != QUANTITATIVE_CLAIM_BINDING_FIELDS:
        raise QuantitativeSpecialistProductError(
            "invalid_input", "claim_binding requires exactly its three bounded fields"
        )
    proposed_result_literal = _required_text(
        claim.get("proposed_result_literal"),
        field="proposed_result_literal",
        limit=MAX_NUMERIC_LITERAL_LENGTH,
    )
    if len(str(claim.get("proposed_result_literal"))) > MAX_NUMERIC_LITERAL_LENGTH:
        raise QuantitativeSpecialistProductError(
            "invalid_numeric_literal", "proposed_result_literal exceeds 120 characters"
        )
    return {
        "request_kind": "source_bound_calculation",
        "calculation_kind": calculation_kind,
        "formula_label": formula_label,
        "expected_output_unit": expected_unit,
        "expected_precision_posture": expected_precision,
        "operands": operands,
        "claim_binding": {
            "proposed_result_literal": proposed_result_literal,
            "literal_occurrence": _positive_occurrence(
                claim.get("literal_occurrence"), field="claim literal_occurrence"
            ),
            "expected_result_unit": _normalize_unit(
                claim.get("expected_result_unit"), required=True
            ),
        },
        "assumptions": _text_list(request.get("assumptions"), field="assumptions"),
        "caveats": _text_list(request.get("caveats"), field="caveats"),
    }


def _validate_operand_roles(
    calculation_kind: str, operands: Sequence[Mapping[str, Any]]
) -> None:
    roles = [str(item.get("operand_role") or "") for item in operands]
    policy = QUANTITATIVE_OPERATOR_ROLE_POLICIES[calculation_kind]
    if policy.get("pair_key") == "prohibited" and any(
        item.get("pair_key") for item in operands
    ):
        raise QuantitativeSpecialistProductError(
            "invalid_operand_roles", "pair_key is only valid for weighted_average"
        )
    if "minimum_operands" in policy:
        expected = next(iter(_safe_mapping(policy.get("roles"))))
        if (
            len(operands) < int(policy["minimum_operands"])
            or set(roles) != {expected}
        ):
            raise QuantitativeSpecialistProductError(
                "invalid_operand_roles",
                f"{calculation_kind} requires at least two {expected} operands",
            )
        return
    if "exact_operands" in policy:
        expected_roles = _safe_mapping(policy.get("roles"))
        if len(operands) != int(policy["exact_operands"]) or any(
            roles.count(role) != int(count)
            for role, count in expected_roles.items()
        ):
            named_roles = list(expected_roles)
            raise QuantitativeSpecialistProductError(
                "invalid_operand_roles",
                f"{calculation_kind} requires exactly one {named_roles[0]} and one {named_roles[1]}",
            )
        return
    pairs: dict[str, list[str]] = {}
    for item in operands:
        pair_key = str(item.get("pair_key") or "")
        role = str(item.get("operand_role") or "")
        if not pair_key or role not in {"value", "weight"}:
            raise QuantitativeSpecialistProductError(
                "invalid_operand_roles",
                "weighted_average requires value/weight roles with pair_key",
            )
        pairs.setdefault(pair_key, []).append(role)
    minimum_pairs = int(policy["minimum_pair_groups"])
    roles_per_pair = _safe_mapping(policy.get("roles_per_pair"))
    if len(pairs) < minimum_pairs or any(
        any(values.count(role) != int(count) for role, count in roles_per_pair.items())
        for values in pairs.values()
    ):
        raise QuantitativeSpecialistProductError(
            "invalid_operand_roles",
            "weighted_average requires at least two complete value/weight pairs",
        )


def _ordered_operands(
    calculation_kind: str, operands: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    role_rank = {
        "minuend": 0,
        "numerator": 0,
        "subtrahend": 1,
        "denominator": 1,
        "value": 0,
        "weight": 1,
    }
    if calculation_kind == "weighted_average":
        return sorted(
            (dict(item) for item in operands),
            key=lambda item: (
                str(item.get("pair_key") or ""),
                role_rank[str(item.get("operand_role") or "")],
                str(item.get("local_operand_key") or ""),
            ),
        )
    if calculation_kind in {"sum", "product"}:
        return sorted(
            (dict(item) for item in operands),
            key=lambda item: str(item.get("local_operand_key") or ""),
        )
    return sorted(
        (dict(item) for item in operands),
        key=lambda item: (
            role_rank[str(item.get("operand_role") or "")],
            str(item.get("local_operand_key") or ""),
        ),
    )


def _derive_result_unit(
    calculation_kind: str,
    parsed_operands: Sequence[Mapping[str, Any]],
) -> str:
    units = [str(_safe_mapping(item.get("parsed")).get("unit") or "") for item in parsed_operands]
    if any(not unit for unit in units):
        raise QuantitativeSpecialistProductError(
            "missing_unit", "every product operand requires an explicit source unit"
        )
    if calculation_kind in {"sum", "difference"}:
        if len(set(units)) != 1:
            raise QuantitativeSpecialistProductError(
                "incompatible_units", f"{calculation_kind} requires exactly matching units"
            )
        return units[0]
    if calculation_kind == "percentage":
        if len(set(units)) != 1:
            raise QuantitativeSpecialistProductError(
                "incompatible_units", "percentage requires matching numerator and denominator units"
            )
        return "percent"
    if calculation_kind == "percentage_point_difference":
        if set(units) != {"percent"}:
            raise QuantitativeSpecialistProductError(
                "incompatible_units",
                "percentage_point_difference requires percentage inputs",
            )
        return "percentage_points"
    if calculation_kind == "ratio":
        return "dimensionless" if units[0] == units[1] else f"{units[0]}/{units[1]}"
    if calculation_kind == "simple_rate":
        return f"{units[0]}/{units[1]}"
    if calculation_kind == "product":
        return "*".join(units)
    value_units = [
        unit
        for unit, item in zip(units, parsed_operands, strict=True)
        if item.get("operand_role") == "value"
    ]
    weight_units = [
        unit
        for unit, item in zip(units, parsed_operands, strict=True)
        if item.get("operand_role") == "weight"
    ]
    if len(set(value_units)) != 1 or len(set(weight_units)) != 1:
        raise QuantitativeSpecialistProductError(
            "incompatible_units",
            "weighted_average requires common value units and compatible weight units",
        )
    return value_units[0]


def _result_precision(parsed_operands: Sequence[Mapping[str, Any]]) -> str:
    postures = {
        str(_safe_mapping(item.get("parsed")).get("precision_posture") or "")
        for item in parsed_operands
    }
    if "approximate_as_reported" in postures:
        return "approximate_as_reported"
    if "rounded_as_reported" in postures:
        return "rounded_as_reported"
    return "exact_as_reported"


def _claim_literal_binding(
    *, claim_text: str, literal: str, occurrence: int | None
) -> tuple[dict[str, Any], str | None]:
    matches = _literal_occurrences(claim_text, literal)
    if not matches:
        return {}, "result_literal_absent"
    if len(matches) > 1 and occurrence is None:
        return {}, "ambiguous_result_literal"
    selected = occurrence or 1
    if selected < 1 or selected > len(matches):
        return {}, "result_literal_absent"
    start, end = matches[selected - 1]
    return (
        {
            "source_binding_kind": "nominated_claim",
            "source_material_digest": _text_digest(claim_text),
            "selected_literal_digest": _text_digest(literal),
            "selected_occurrence": selected,
            "bounded_character_span": {"start": start, "end": end},
            "parser_version": NUMERIC_LITERAL_PARSER_VERSION,
            "parser_digest": NUMERIC_LITERAL_PARSER_DIGEST,
        },
        None,
    )


def _claim_alignment(
    *,
    claim_text: str,
    claim_binding: Mapping[str, Any],
    result_value: Decimal,
    result_unit: str,
    result_precision: str,
) -> dict[str, Any]:
    literal = str(claim_binding.get("proposed_result_literal") or "")
    ref, binding_error = _claim_literal_binding(
        claim_text=claim_text,
        literal=literal,
        occurrence=claim_binding.get("literal_occurrence"),
    )
    if binding_error:
        return {"posture": binding_error, "literal_binding_ref": {}}
    try:
        parsed = parse_source_bound_numeric_literal(literal)
    except QuantitativeSpecialistProductError:
        return {
            "posture": "numeric_mismatch",
            "literal_binding_ref": ref,
            "comparison_reason": "proposed_result_literal_failed_closed_parser",
        }
    expected_result_unit = str(claim_binding.get("expected_result_unit") or "")
    parsed_unit = str(parsed.get("unit") or "")
    if expected_result_unit != result_unit or (
        result_unit == "dimensionless"
        and parsed_unit not in {"", "dimensionless"}
    ) or (result_unit != "dimensionless" and parsed_unit != result_unit):
        return {
            "posture": "unit_mismatch",
            "literal_binding_ref": ref,
            "parsed_result_unit": parsed_unit or None,
        }
    if parsed["numeric_value"] != result_value:
        return {
            "posture": "numeric_mismatch",
            "literal_binding_ref": ref,
            "parsed_numeric_value_text": parsed["numeric_value_text"],
        }
    if parsed["precision_posture"] != result_precision:
        return {
            "posture": "numeric_mismatch",
            "literal_binding_ref": ref,
            "comparison_reason": "precision_posture_mismatch",
        }
    return {"posture": "exact_match", "literal_binding_ref": ref}


def _safe_json_number(value: Decimal) -> int | float | None:
    if value == value.to_integral_value():
        integer = int(value)
        return integer if abs(integer) <= 9_007_199_254_740_991 else None
    projected = float(value)
    if projected in {float("inf"), float("-inf")} or projected != projected:
        return None
    return projected if Decimal(str(projected)) == value else None


def _base_bounded_result(
    *,
    calculation_kind: str | None,
    calculation_status: str,
    blockers: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "result_kind": QUANTITATIVE_RESULT_KIND,
        "schema_version": QUANTITATIVE_OUTPUT_SCHEMA_REF,
        "capability_id": QUANTITATIVE_CAPABILITY_ID,
        "capability_version": QUANTITATIVE_CAPABILITY_VERSION,
        "calculation_kind": calculation_kind,
        "calculation_status": calculation_status,
        "deterministic_operator": calculation_kind,
        "blockers": [deepcopy(dict(item)) for item in blockers],
        "input_provenance": (
            "source_explicit"
            if calculation_status in {"computed", "contested"}
            else "not_established"
        ),
        "nomination_posture": "model_nominated_exact_literal",
        "output_provenance": (
            "derived_deterministic"
            if calculation_status == "computed"
            else "not_produced"
        ),
        "uncertainty_posture": (
            "source_reported_precision_preserved_no_statistical_uncertainty_propagation"
        ),
        "deterministic_arithmetic_applied_to_reported_values": (
            calculation_status == "computed"
        ),
        "unsupported_number_invention": False,
        "arbitrary_formula_execution": False,
        "currency_conversion_performed": False,
        "unit_conversion_performed": False,
        "admission_authority": False,
        "component_coverage_authority": False,
        "sufficiency_authority": False,
        "final_answer_packet_authority": False,
        "author_authority": False,
        "citation_authority": False,
        "source_obligation_authority": False,
    }


def _evaluator_source_class_posture(entry: Mapping[str, Any]) -> str:
    """Map closed product quality to the legacy pure evaluator vocabulary."""

    if entry.get("source_quality_posture") == "authoritative_current_clear":
        return "current_primary_or_official"
    return "weak_secondary"


def _evaluate_quantitative_request(transient: Mapping[str, Any]) -> dict[str, Any]:
    request = _validate_request(_safe_mapping(transient.get("capability_request")))
    target = _safe_mapping(transient.get("canonical_target_ref"))
    target_kind = str(target.get("target_kind") or "")
    catalog = _safe_mapping(transient.get("quantitative_source_catalog"))
    if catalog.get("schema_version") != QUANTITATIVE_SOURCE_CATALOG_SCHEMA:
        raise QuantitativeSpecialistProductError(
            "missing_source_catalog", "current quantitative source catalog is unavailable"
        )
    expected_binding = (
        "component_evidence_member"
        if target_kind == "component"
        else "admitted_component_claim"
        if target_kind == "synthesis"
        else ""
    )
    if not expected_binding:
        raise QuantitativeSpecialistProductError(
            "not_applicable", "quantitative target kind is unsupported"
        )
    parsed_operands: list[dict[str, Any]] = []
    evaluator_inputs: list[dict[str, Any]] = []
    literal_binding_refs: list[dict[str, Any]] = []
    for operand in _ordered_operands(
        request["calculation_kind"], request["operands"]
    ):
        source_local_key = str(operand["source_local_key"])
        entry = _safe_mapping(catalog.get(source_local_key))
        if not entry or entry.get("source_binding_kind") != expected_binding:
            raise QuantitativeSpecialistProductError(
                "unknown_source_local_key",
                "operand source_local_key is absent from the current catalog",
            )
        parsed, literal_ref = _bind_operand_literal(
            entry=entry,
            source_local_key=source_local_key,
            literal=str(operand["source_numeric_literal"]),
            occurrence=operand.get("literal_occurrence"),
        )
        component_ref = _safe_mapping(entry.get("component_lineage_ref"))
        source_bound_ref = {
            "component_ref": component_ref,
            "content_ref": {
                "content_digest": entry.get("underlying_evidence_field_digest")
                or entry.get("bounded_field_digest")
            },
            "reference_ref": {
                "selected_literal_digest": literal_ref["selected_literal_digest"],
                "source_material_digest": literal_ref["source_material_digest"],
            },
        }
        evaluator_inputs.append(
            {
                "label": operand.get("label") or operand["local_operand_key"],
                "numeric_value": parsed["numeric_value"],
                "unit": parsed.get("unit"),
                "scale": parsed.get("scale"),
                "source_bound": entry.get("lineage_complete") is True,
                "fixture_bound": False,
                "source_bound_ref": source_bound_ref,
                "component_id": component_ref.get("component_id"),
                "currentness_posture": entry.get("currentness_posture") or "unknown",
                "source_class_posture": _evaluator_source_class_posture(entry),
                "conflict_posture": entry.get("conflict_posture") or "unknown",
                "contradictory": entry.get("contradictory") is True,
                "role": operand["operand_role"],
                "pair_id": operand.get("pair_key"),
                "caveats": request["caveats"],
            }
        )
        parsed_operands.append({**operand, "parsed": parsed})
        literal_binding_refs.append(literal_ref)

    result_unit = _derive_result_unit(
        request["calculation_kind"], parsed_operands
    )
    if request.get("expected_output_unit") and request["expected_output_unit"] != result_unit:
        raise QuantitativeSpecialistProductError(
            "expected_output_unit_mismatch",
            "advisory expected_output_unit disagrees with repository-derived unit",
        )
    result_precision = _result_precision(parsed_operands)
    if request.get("expected_precision_posture") and request[
        "expected_precision_posture"
    ] != result_precision:
        raise QuantitativeSpecialistProductError(
            "expected_precision_posture_mismatch",
            "advisory precision posture disagrees with selected literals",
        )
    evaluation = evaluate_source_bound_calculation(
        calculation_kind=request["calculation_kind"],
        input_records=evaluator_inputs,
        formula_label=request.get("formula_label"),
        output_unit=result_unit,
        assumptions=request["assumptions"],
        caveats=request["caveats"],
    )
    bounded = _base_bounded_result(
        calculation_kind=request["calculation_kind"],
        calculation_status=str(evaluation["calculation_status"]),
        blockers=evaluation["blockers"],
    )
    bounded.update(
        {
            "formula_label": evaluation.get("formula_label"),
            "formula_ref": {
                "formula_id": evaluation.get("formula_id"),
                "formula_digest": evaluation.get("formula_digest"),
            },
            "result_unit": result_unit,
            "precision_posture": result_precision,
            "rounding_posture": "no_extra_rounding_applied",
            "input_refs": [
                {
                    "local_operand_key": operand["local_operand_key"],
                    "operand_role": operand["operand_role"],
                    "pair_key": operand.get("pair_key"),
                    "input_digest": _safe_mapping(normalized).get("input_digest"),
                    "source_class": _safe_mapping(
                        catalog.get(operand["source_local_key"])
                    ).get("source_class"),
                    "source_tier": _safe_mapping(
                        catalog.get(operand["source_local_key"])
                    ).get("source_tier"),
                    "currentness_posture": _safe_mapping(
                        catalog.get(operand["source_local_key"])
                    ).get("currentness_posture"),
                    "conflict_posture": _safe_mapping(
                        catalog.get(operand["source_local_key"])
                    ).get("conflict_posture"),
                    "source_quality_posture": _safe_mapping(
                        catalog.get(operand["source_local_key"])
                    ).get("source_quality_posture"),
                }
                for operand, normalized in zip(
                    parsed_operands, evaluation["input_records"], strict=True
                )
            ],
            "literal_binding_refs": literal_binding_refs,
            "assumptions": list(request["assumptions"]),
            "caveats": list(request["caveats"]),
        }
    )
    if evaluation["calculation_status"] != "computed":
        return {
            "bounded_result": bounded,
            "execution_posture": (
                EXECUTION_CONTESTED
                if evaluation["calculation_status"] == "contested"
                else EXECUTION_BLOCKED
            ),
            "assumptions": request["assumptions"],
            "caveats": request["caveats"],
            "blockers": [
                str(_safe_mapping(item).get("blocker_kind") or "calculation_blocked")
                for item in evaluation["blockers"]
            ],
            "confidence_posture": "deterministic_spent_outcome",
        }
    result_value = Decimal(str(_safe_mapping(evaluation["result"])["numeric_value_text"]))
    nominated_claim = _safe_mapping(transient.get("nominated_claim"))
    claim_text = str(nominated_claim.get("claim_text") or "")
    if not claim_text:
        raise QuantitativeSpecialistProductError(
            "missing_nominated_claim", "current nominated claim is unavailable"
        )
    alignment = _claim_alignment(
        claim_text=claim_text,
        claim_binding=request["claim_binding"],
        result_value=result_value,
        result_unit=result_unit,
        result_precision=result_precision,
    )
    bounded["numeric_value_text"] = _decimal_text(result_value)
    json_number = _safe_json_number(result_value)
    if json_number is not None:
        bounded["numeric_value"] = json_number
    bounded["claim_alignment"] = alignment
    bounded["calculation_status"] = "computed"
    execution_posture = (
        EXECUTION_COMPLETED
        if alignment["posture"] == "exact_match"
        else EXECUTION_CONTESTED
    )
    return {
        "bounded_result": bounded,
        "execution_posture": execution_posture,
        "assumptions": request["assumptions"],
        "caveats": request["caveats"],
        "blockers": (
            []
            if execution_posture == EXECUTION_COMPLETED
            else [f"claim_alignment:{alignment['posture']}"]
        ),
        "confidence_posture": "deterministic_exact_literal_calculation",
    }


def source_bound_quantitative_calculation_adapter(
    transient_bounded_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate, calculate, and align one transient bounded product request."""

    try:
        return _evaluate_quantitative_request(_safe_mapping(transient_bounded_input))
    except QuantitativeSpecialistProductError as exc:
        request = _safe_mapping(
            _safe_mapping(transient_bounded_input).get("capability_request")
        )
        calculation_kind = _clean_text(request.get("calculation_kind"), limit=80)
        blocker = {"blocker_kind": exc.blocker_kind, "reason": exc.reason}
        return {
            "bounded_result": _base_bounded_result(
                calculation_kind=calculation_kind,
                calculation_status=(
                    "not_applicable"
                    if exc.blocker_kind == "not_applicable"
                    else "invalid_input"
                    if exc.blocker_kind == "invalid_input"
                    else "blocked"
                ),
                blockers=(blocker,),
            ),
            "execution_posture": EXECUTION_BLOCKED,
            "assumptions": [],
            "caveats": [],
            "blockers": [exc.blocker_kind],
            "confidence_posture": "deterministic_spent_outcome",
        }


def build_quantitative_product_specialist_registry() -> SpecialistCapabilityRegistry:
    return SpecialistCapabilityRegistry(
        (
            SpecialistCapabilitySpec(
                capability_id=QUANTITATIVE_CAPABILITY_ID,
                version=QUANTITATIVE_CAPABILITY_VERSION,
                capability_requirement=QUANTITATIVE_CAPABILITY_REQUIREMENT,
                supported_target_kinds=("component", "synthesis"),
                input_schema_ref=QUANTITATIVE_INPUT_SCHEMA_REF,
                output_schema_ref=QUANTITATIVE_OUTPUT_SCHEMA_REF,
                adapter=source_bound_quantitative_calculation_adapter,
                capability_class="source_bound_quantitative_calculation",
                cost_class="zero_model_cost",
            ),
        )
    )


def build_quantitative_product_specialist_policy() -> SpecialistExecutionPolicy:
    return SpecialistExecutionPolicy(
        enabled_capability_ids=(QUANTITATIVE_CAPABILITY_ID,),
        specialist_work_item_limit=1,
        parallelism=False,
        recursion=False,
    )


def compose_quantitative_specialist_product_deps(deps: Any) -> Any:
    """Immutably activate the fixed product registry/policy on official deps."""

    return replace(
        deps,
        specialist_capability_registry=build_quantitative_product_specialist_registry(),
        specialist_execution_policy=build_quantitative_product_specialist_policy(),
    )


__all__ = [
    "MAX_NUMERIC_LITERAL_LENGTH",
    "MAX_OPERANDS",
    "NUMERIC_LITERAL_PARSER_DIGEST",
    "NUMERIC_LITERAL_PARSER_VERSION",
    "QUANTITATIVE_CAPABILITY_ID",
    "QUANTITATIVE_CAPABILITY_REQUIREMENT",
    "QUANTITATIVE_CAPABILITY_VERSION",
    "QUANTITATIVE_INPUT_SCHEMA_REF",
    "QUANTITATIVE_OUTPUT_SCHEMA_REF",
    "QUANTITATIVE_OPERATOR_ROLE_POLICIES",
    "QUANTITATIVE_OPERAND_ALLOWED_FIELDS",
    "QUANTITATIVE_OPERAND_REQUIRED_FIELDS",
    "QUANTITATIVE_PROPOSAL_ALLOWED_FIELDS",
    "QUANTITATIVE_PROPOSAL_CONTRACT_DIGEST",
    "QUANTITATIVE_PROPOSAL_CONTRACT_SCHEMA_VERSION",
    "QUANTITATIVE_PROPOSAL_REQUIRED_FIELDS",
    "QUANTITATIVE_REQUEST_ALLOWED_FIELDS",
    "QUANTITATIVE_REQUEST_REQUIRED_FIELDS",
    "QUANTITATIVE_SOURCE_CATALOG_SCHEMA",
    "QUANTITATIVE_SYNTHESIS_TARGET_KEY_RULE",
    "QuantitativeSpecialistProductError",
    "build_component_quantitative_source_catalog",
    "build_quantitative_specialist_proposal_contract",
    "build_quantitative_product_specialist_policy",
    "build_quantitative_product_specialist_registry",
    "build_synthesis_quantitative_source_catalog",
    "compose_quantitative_specialist_product_deps",
    "parse_source_bound_numeric_literal",
    "quantitative_proposal_runtime_schema_facts",
    "source_bound_quantitative_calculation_adapter",
    "validate_quantitative_specialist_proposal_contract",
    "validate_quantitative_specialist_proposal_instance",
]
