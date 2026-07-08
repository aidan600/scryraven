"""Current-source component / answer-type binding lineage.

The binding records requested answer meaning for a current-source single-fact
component. It is contract lineage only: not evidence, not source-obligation
satisfaction, not citation eligibility, not answer authority, and not product
correctness.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Mapping, Sequence

CURRENT_SOURCE_COMPONENT_ANSWER_TYPE_BINDING_SCHEMA_VERSION = (
    "current_source_component_answer_type_binding_v1"
)
CURRENT_SOURCE_COMPONENT_ANSWER_TYPE_BINDING_KIND = (
    "current_source_component_answer_type_binding"
)

RAW_PRIVATE_RETENTION_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_source_content_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}

_NON_AUTHORITY_FALSE_FLAGS = {
    "evidence_admitted": False,
    "support_claimed": False,
    "component_coverage_bound": False,
    "source_obligation_satisfied": False,
    "citation_eligibility_created": False,
    "sufficiency_readiness_created": False,
    "final_answer_packet_created": False,
    "author_output_created": False,
    "source_display_opened": False,
    "product_correctness_claimed": False,
}

_NON_AUTHORITY_TRUE_FLAGS = {
    "lineage_only": True,
    "binding_is_contract_lineage": True,
    "binding_is_not_evidence": True,
    "binding_is_not_answer_authority": True,
    "evidence_not_admitted": True,
    "source_obligation_not_satisfied": True,
    "citation_eligibility_not_created": True,
    "product_correctness_not_claimed": True,
}

_FEE_ADJACENT_EXCLUSIONS = (
    "filing_mode",
    "waiver_eligibility",
    "reduced_fee_eligibility",
    "online_discount",
    "process_instructions",
    "contextual_requirements_unless_they_provide_requested_fee_amount",
)


class ComponentAnswerTypeBindingError(ValueError):
    """Raised when a binding would lose required lineage or claim authority."""


def build_current_source_component_answer_type_binding(
    *,
    component_id: Any,
    component_text: Any,
    source_obligation_id: Any,
    source_obligation_text: Any,
    fact_kind: Any,
    claim_under_test: Any,
    component_digest: Any = None,
    current_answer_contract_digest: Any = None,
    expected_value_token_kinds: Sequence[Any] = (),
) -> dict[str, Any]:
    """Build a safe requested-answer meaning binding for one component."""

    component = _clean_text(component_id, limit=320)
    source_obligation = _clean_text(source_obligation_id, limit=320)
    component_body = _clean_text(component_text, limit=500)
    source_obligation_body = _clean_text(source_obligation_text, limit=500)
    fact = _clean_token(fact_kind, limit=80) or "unspecified"
    claim = _clean_text(claim_under_test, limit=700)
    comp_digest = _clean_token(component_digest, limit=128)
    contract_digest = _clean_token(current_answer_contract_digest, limit=128)
    token_kinds = _normalize_value_token_kinds(expected_value_token_kinds)
    if not component:
        raise ComponentAnswerTypeBindingError("component binding requires component_id")
    if not source_obligation:
        raise ComponentAnswerTypeBindingError(
            "component binding requires source_obligation_id"
        )
    if not component_body:
        raise ComponentAnswerTypeBindingError("component binding requires component_text")
    if not source_obligation_body:
        raise ComponentAnswerTypeBindingError(
            "component binding requires source_obligation_text"
        )
    if not claim:
        raise ComponentAnswerTypeBindingError("component binding requires claim")
    if not (comp_digest or contract_digest):
        raise ComponentAnswerTypeBindingError(
            "component binding requires component or contract digest"
        )

    requested_answer_type = _requested_answer_type(fact, component_body)
    expected_value_shape = _expected_value_shape(
        fact,
        component_body,
        expected_value_token_kinds=token_kinds,
    )
    base = {
        "schema_version": CURRENT_SOURCE_COMPONENT_ANSWER_TYPE_BINDING_SCHEMA_VERSION,
        "binding_kind": CURRENT_SOURCE_COMPONENT_ANSWER_TYPE_BINDING_KIND,
        "component_id": component,
        "component_digest": comp_digest,
        "current_answer_contract_digest": contract_digest,
        "component_text": component_body,
        "source_obligation_id": source_obligation,
        "source_obligation_text": source_obligation_body,
        "fact_kind": fact,
        "requested_answer_type": requested_answer_type,
        "claim_under_test": claim,
        "expected_value_shape": expected_value_shape,
        "expected_value_token_kinds": list(token_kinds),
        "adjacent_claim_exclusions": _adjacent_claim_exclusions(
            fact,
            component_body,
            requested_answer_type=requested_answer_type,
        ),
        "adjacent_claims_do_not_satisfy_requested_answer_type": True,
        "raw_private_retention_flags": dict(RAW_PRIVATE_RETENTION_FALSE_FLAGS),
        **_NON_AUTHORITY_TRUE_FLAGS,
        **_NON_AUTHORITY_FALSE_FLAGS,
    }
    binding_digest = _digest_json(base)
    return validate_current_source_component_answer_type_binding(
        {
            **base,
            "binding_id": f"component-answer-type-binding:{binding_digest[:20]}",
            "binding_digest": binding_digest,
        }
    )


def current_source_component_answer_type_binding_from_relation_plan(
    relation_plan: Mapping[str, Any],
    *,
    expected_value_token_kinds: Sequence[Any] = (),
) -> dict[str, Any]:
    """Return the relation-plan binding, or rebuild it from existing plan fields."""

    plan = _safe_mapping(relation_plan)
    existing = _safe_mapping(plan.get("component_answer_type_binding"))
    if existing:
        return validate_current_source_component_answer_type_binding(existing)
    component = _first_mapping(plan.get("components"))
    source_obligation = _first_mapping(plan.get("source_obligations"))
    token_kinds = tuple(expected_value_token_kinds) or tuple(
        _safe_sequence(plan.get("expected_value_token_kinds"))
    )
    return build_current_source_component_answer_type_binding(
        component_id=plan.get("component_id") or component.get("component_id"),
        component_digest=(
            component.get("component_digest")
            or plan.get("component_digest")
            or plan.get("packet_digest")
        ),
        current_answer_contract_digest=plan.get("current_answer_contract_digest"),
        component_text=plan.get("component_text") or component.get("component_text"),
        source_obligation_id=(
            plan.get("source_obligation_id")
            or source_obligation.get("source_obligation_id")
        ),
        source_obligation_text=(
            plan.get("source_obligation_text")
            or source_obligation.get("source_obligation_text")
        ),
        fact_kind=plan.get("fact_kind") or component.get("fact_kind"),
        claim_under_test=(
            plan.get("claim_under_test") or component.get("claim_under_test")
        ),
        expected_value_token_kinds=token_kinds,
    )


def current_source_component_answer_type_binding_ref(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a compact but meaning-bearing safe ref."""

    binding = _safe_mapping(value)
    if not binding:
        return {}
    safe = validate_current_source_component_answer_type_binding(binding)
    return {
        "schema_version": safe["schema_version"],
        "binding_kind": safe["binding_kind"],
        "binding_id": safe["binding_id"],
        "binding_digest": safe["binding_digest"],
        "component_id": safe["component_id"],
        "component_digest": safe.get("component_digest"),
        "current_answer_contract_digest": safe.get("current_answer_contract_digest"),
        "component_text": safe["component_text"],
        "source_obligation_id": safe["source_obligation_id"],
        "source_obligation_text": safe["source_obligation_text"],
        "fact_kind": safe["fact_kind"],
        "requested_answer_type": safe["requested_answer_type"],
        "claim_under_test": safe["claim_under_test"],
        "expected_value_shape": safe["expected_value_shape"],
        "expected_value_token_kinds": list(safe.get("expected_value_token_kinds") or []),
        "adjacent_claim_exclusions": list(safe["adjacent_claim_exclusions"]),
        "adjacent_claims_do_not_satisfy_requested_answer_type": True,
        "raw_private_retention_flags": dict(RAW_PRIVATE_RETENTION_FALSE_FLAGS),
        **_NON_AUTHORITY_TRUE_FLAGS,
        **_NON_AUTHORITY_FALSE_FLAGS,
    }


def maybe_current_source_component_answer_type_binding_ref(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Best-effort binding ref for optional downstream lineage surfaces."""

    try:
        return current_source_component_answer_type_binding_ref(value)
    except ComponentAnswerTypeBindingError:
        return {}


def validate_current_source_component_answer_type_binding(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the binding keeps lineage and non-authority posture."""

    safe = _safe_mapping(value)
    if (
        safe.get("schema_version")
        != CURRENT_SOURCE_COMPONENT_ANSWER_TYPE_BINDING_SCHEMA_VERSION
    ):
        raise ComponentAnswerTypeBindingError("binding schema mismatch")
    if safe.get("binding_kind") != CURRENT_SOURCE_COMPONENT_ANSWER_TYPE_BINDING_KIND:
        raise ComponentAnswerTypeBindingError("binding kind mismatch")
    for key in (
        "component_id",
        "component_text",
        "source_obligation_id",
        "source_obligation_text",
        "fact_kind",
        "requested_answer_type",
        "claim_under_test",
        "expected_value_shape",
    ):
        if not _clean_text(safe.get(key), limit=700):
            raise ComponentAnswerTypeBindingError(f"binding requires {key}")
    if not (
        _clean_token(safe.get("component_digest"), limit=128)
        or _clean_token(safe.get("current_answer_contract_digest"), limit=128)
    ):
        raise ComponentAnswerTypeBindingError(
            "binding requires component_digest or current_answer_contract_digest"
        )
    exclusions = tuple(
        item
        for item in (
            _clean_token(raw, limit=120)
            for raw in _safe_sequence(safe.get("adjacent_claim_exclusions"))
        )
        if item
    )
    if not exclusions:
        raise ComponentAnswerTypeBindingError(
            "binding requires adjacent_claim_exclusions"
        )
    if safe.get("adjacent_claims_do_not_satisfy_requested_answer_type") is not True:
        raise ComponentAnswerTypeBindingError(
            "binding must mark adjacent claims as non-satisfying"
        )
    flags = _safe_mapping(safe.get("raw_private_retention_flags"))
    if flags != RAW_PRIVATE_RETENTION_FALSE_FLAGS:
        raise ComponentAnswerTypeBindingError(
            "binding raw/private retention flags must remain false"
        )
    for key, expected in _NON_AUTHORITY_TRUE_FLAGS.items():
        if safe.get(key) is not expected:
            raise ComponentAnswerTypeBindingError(f"binding posture flag invalid: {key}")
    for key, expected in _NON_AUTHORITY_FALSE_FLAGS.items():
        if safe.get(key) is not expected:
            raise ComponentAnswerTypeBindingError(
                f"binding authority flag must remain false: {key}"
            )
    binding_digest = _clean_token(safe.get("binding_digest"), limit=128)
    binding_id = _clean_token(safe.get("binding_id"), limit=260)
    if not binding_id or not binding_digest:
        raise ComponentAnswerTypeBindingError("binding id/digest missing")
    digest_payload = _safe_mapping(safe)
    digest_payload.pop("binding_id", None)
    digest_payload.pop("binding_digest", None)
    if binding_digest != _digest_json(digest_payload):
        raise ComponentAnswerTypeBindingError("binding digest mismatch")
    if binding_id != f"component-answer-type-binding:{binding_digest[:20]}":
        raise ComponentAnswerTypeBindingError("binding id mismatch")
    return _json_safe(safe)


def _requested_answer_type(fact_kind: str, component_text: str) -> str:
    fact = _normalize_key(fact_kind)
    lowered = component_text.casefold()
    if fact == "fee":
        return "fee_amount_current_standard_value"
    if fact == "deadline":
        return "deadline_date"
    if fact == "requirement":
        return "requirement_action"
    if fact == "status":
        return "status_value"
    if fact == "current_value":
        if "rate" in lowered:
            return "current_standard_rate"
        if "maximum" in lowered or "limit" in lowered or "threshold" in lowered:
            return "current_standard_limit"
        return "current_standard_value"
    return "unspecified_single_fact_value"


def _expected_value_shape(
    fact_kind: str,
    component_text: str,
    *,
    expected_value_token_kinds: Sequence[str],
) -> str:
    fact = _normalize_key(fact_kind)
    token_kinds = set(expected_value_token_kinds)
    lowered = component_text.casefold()
    if fact == "fee":
        return "currency_amount"
    if fact == "deadline":
        return "date_or_date_range"
    if fact == "requirement":
        return "requirement_statement"
    if fact == "status":
        return "status_statement"
    if "currency" in token_kinds:
        return "currency_amount"
    if "date_like" in token_kinds:
        return "date_or_date_range"
    if "percent" in token_kinds:
        return "percentage"
    if "number" in token_kinds:
        return "numeric_value"
    if "rate" in lowered:
        return "numeric_or_currency_rate"
    return "unknown_or_unspecified_value_shape"


def _adjacent_claim_exclusions(
    fact_kind: str,
    component_text: str,
    *,
    requested_answer_type: str,
) -> list[str]:
    del requested_answer_type
    fact = _normalize_key(fact_kind)
    lowered = component_text.casefold()
    if fact == "fee":
        exclusions = list(_FEE_ADJACENT_EXCLUSIONS)
        if "paper" in lowered:
            exclusions.append("non_paper_filing_mode_value")
        return exclusions
    if fact == "deadline":
        return [
            "eligibility_description",
            "process_instructions",
            "historical_dates",
            "unrelated_conditions_without_requested_date",
        ]
    if fact == "requirement":
        return [
            "fee_amount",
            "unrelated_eligibility",
            "historical_process_notes",
            "cost_or_value_without_required_action",
        ]
    if fact == "status":
        return [
            "process_instructions",
            "historical_status",
            "eligibility_conditions_without_requested_status",
            "fee_amount",
        ]
    if fact == "current_value":
        return [
            "reduced_or_exception_value",
            "discount_value",
            "eligibility_condition",
            "process_instructions",
            "historical_values",
            "unrelated_amounts",
        ]
    return [
        "adjacent_context",
        "process_instructions",
        "historical_values",
        "unrelated_conditions",
    ]


def _normalize_value_token_kinds(values: Sequence[Any]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = _normalize_key(value)
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return tuple(out)


def _first_mapping(value: Any) -> dict[str, Any]:
    seq = _safe_sequence(value)
    return _safe_mapping(seq[0]) if seq else {}


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "CURRENT_SOURCE_COMPONENT_ANSWER_TYPE_BINDING_KIND",
    "CURRENT_SOURCE_COMPONENT_ANSWER_TYPE_BINDING_SCHEMA_VERSION",
    "ComponentAnswerTypeBindingError",
    "RAW_PRIVATE_RETENTION_FALSE_FLAGS",
    "build_current_source_component_answer_type_binding",
    "current_source_component_answer_type_binding_from_relation_plan",
    "current_source_component_answer_type_binding_ref",
    "maybe_current_source_component_answer_type_binding_ref",
    "validate_current_source_component_answer_type_binding",
]
