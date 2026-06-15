"""Deterministic validation and repair for RunAuthority sufficiency judgments."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

from core.run_authority_search_judgment import RunSearchJudgmentDecision
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    RunSufficiencyJudgmentInput,
    SufficiencyJudgmentMode,
    SufficiencyPosture,
    SufficiencyRequirementAssessment,
    SufficiencyValidationResult,
    SufficiencyValidationStatus,
    clean_text,
    clean_token,
    stable_hash,
)

_PROTECTED_KINDS = frozenset(
    {
        "official_current",
        "legal_primary",
        "canonical_docs",
        "source_bound_numeric",
        "user_document",
    }
)
_PROTECTED_SOURCE_CLASSES = frozenset(
    {
        "official_current_rules",
        "current_primary_or_official",
        "legal_or_regulatory_text",
        "primary_source_documents",
        "archival_primary_text",
        "canonical_docs",
        "source_bound_numeric",
        "source_bound",
        "user_document",
    }
)
_REQUIRED_SOURCE_TIERS = frozenset(
    {"official", "primary", "canonical", "academic", "user_document"}
)
_MISSING_LEDGER_STATUSES = frozenset(
    {"unsatisfied", "unknown", "not_observable", "partially_satisfied"}
)
_KIND_FAMILIES = {
    "official_current": "official_current",
    "official": "official_current",
    "current": "official_current",
    "legal_primary": "legal",
    "legal_current_primary": "legal",
    "legal": "legal",
    "canonical_docs": "canonical",
    "canonical_documentation": "canonical",
    "canonical": "canonical",
    "source_bound": "source_bound_numeric",
    "source_bound_numeric": "source_bound_numeric",
    "sourced_numeric_values": "source_bound_numeric",
}
_SOURCE_CLASS_FAMILIES = {
    "official_current_rules": "official_current",
    "current_primary_or_official": "official_current",
    "legal_or_regulatory_text": "legal",
    "primary_source_documents": "canonical",
    "canonical_docs": "canonical",
    "sourced_numeric_values": "source_bound_numeric",
    "source_bound_numeric": "source_bound_numeric",
    "source_bound": "source_bound_numeric",
}
_SOURCE_BOUND_EXTRACTION_FLAGS = (
    "source_bound_numeric_values_extracted",
    "source_bound_numeric_extraction_executed",
    "quant_extraction_executed",
    "calculation_executed",
)


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _list(value):
        token = clean_token(item)
        if token and token not in out:
            out.append(token)
    return out


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _req_key(value: Any) -> str | None:
    token = clean_token(value)
    if not token:
        return None
    return token.casefold().replace("-", "_").replace(":", "_").replace(" ", "_")


def _field(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        token = clean_token(payload.get(key))
        if token:
            return token
    return None


def _ref_field(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        token = _req_key(payload.get(key))
        if token:
            return token
    return None


def _kind_family(requirement: Mapping[str, Any]) -> str:
    kind = _req_key(requirement.get("requirement_kind") or requirement.get("kind"))
    if kind in _KIND_FAMILIES:
        return _KIND_FAMILIES[kind]
    source_class = _req_key(
        requirement.get("required_source_class") or requirement.get("source_class")
    )
    if source_class in _SOURCE_CLASS_FAMILIES:
        return _SOURCE_CLASS_FAMILIES[source_class]
    return kind or "general"


def _source_class_family(requirement: Mapping[str, Any]) -> str | None:
    source_class = _req_key(
        requirement.get("required_source_class") or requirement.get("source_class")
    )
    if not source_class:
        return None
    return _SOURCE_CLASS_FAMILIES.get(source_class, source_class)


def _lineage_refs(requirement: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for key in (
        "component_id",
        "source_obligation_id",
        "obligation_id",
        "provider_job_id",
        "provider_job_ref",
        "origin_ref",
    ):
        token = _req_key(requirement.get(key))
        if token:
            refs.add(token)
    refs.update(_provider_job_requirement_parts(requirement).values())
    return {ref for ref in refs if ref}


def _provider_job_requirement_parts(
    requirement: Mapping[str, Any],
) -> dict[str, str]:
    req_id = _req_key(requirement.get("requirement_id"))
    if not req_id or not req_id.startswith("provider_job_requirement_"):
        return {}
    tail = req_id.removeprefix("provider_job_requirement_").split("_")
    try:
        obligation_index = tail.index("obligation")
        provider_index = tail.index("provider", obligation_index + 1)
    except ValueError:
        return {}
    if obligation_index <= 0 or provider_index <= obligation_index:
        return {}
    return {
        "component_id": "_".join(tail[:obligation_index]),
        "source_obligation_id": "_".join(tail[obligation_index:provider_index]),
        "provider_job_id": "_".join(tail[provider_index:]),
    }


def _ledger_requirements(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in _list(projection.get("source_requirements"))
        if isinstance(item, Mapping)
    ]


def _required_contract_requirements(
    projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for item in _list(projection.get("source_requirements")):
        if not isinstance(item, Mapping):
            continue
        kind = clean_token(item.get("requirement_kind")) or "general"
        strictness = clean_token(item.get("strictness")) or "contextual"
        source_class = clean_token(item.get("required_source_class"))
        source_tier = clean_token(item.get("required_source_tier"))
        currentness = clean_token(item.get("required_currentness"))
        protected = (
            kind in _PROTECTED_KINDS
            or source_class in _PROTECTED_SOURCE_CLASSES
            or source_tier in _REQUIRED_SOURCE_TIERS
            or currentness in {"current", "official_current"}
        )
        if strictness != "required" and not protected:
            continue
        req_id = clean_token(item.get("requirement_id"))
        if not req_id:
            continue
        requirements.append(
            {
                "requirement_id": req_id,
                "requirement_kind": kind,
                "required_source_class": source_class,
                "required_source_tier": source_tier,
                "required_currentness": currentness,
                "strictness": strictness,
                "component_id": clean_token(item.get("component_id")),
                "source_obligation_id": clean_token(
                    item.get("source_obligation_id") or item.get("obligation_id")
                ),
                "provider_job_id": clean_token(item.get("provider_job_id")),
                "origin_ref": clean_token(item.get("origin_ref")),
            }
        )
    return requirements


def _preferred_contract_requirements(
    projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for item in _list(projection.get("source_requirements")):
        if not isinstance(item, Mapping):
            continue
        if clean_token(item.get("strictness")) != "preferred":
            continue
        req_id = clean_token(item.get("requirement_id"))
        if not req_id:
            continue
        requirements.append(
            {
                "requirement_id": req_id,
                "requirement_kind": clean_token(item.get("requirement_kind"))
                or "general",
                "required_source_class": clean_token(item.get("required_source_class")),
                "required_source_tier": clean_token(item.get("required_source_tier")),
                "required_currentness": clean_token(
                    item.get("required_currentness")
                ),
                "strictness": "preferred",
                "component_id": clean_token(item.get("component_id")),
                "source_obligation_id": clean_token(
                    item.get("source_obligation_id") or item.get("obligation_id")
                ),
                "provider_job_id": clean_token(item.get("provider_job_id")),
                "origin_ref": clean_token(item.get("origin_ref")),
            }
        )
    return requirements


def _exact_requirement_match(
    requirement: Mapping[str, Any],
    ledger_requirement: Mapping[str, Any],
) -> bool:
    req_id = _req_key(requirement.get("requirement_id"))
    ledger_id = _req_key(ledger_requirement.get("requirement_id"))
    return bool(req_id and ledger_id and req_id == ledger_id)


def _compatible_kind_and_class(
    requirement: Mapping[str, Any],
    ledger_requirement: Mapping[str, Any],
) -> bool:
    required_family = _kind_family(requirement)
    ledger_family = _kind_family(ledger_requirement)
    if required_family != ledger_family:
        return False
    if required_family == "source_bound_numeric":
        return True
    required_class = _source_class_family(requirement)
    ledger_class = _source_class_family(ledger_requirement)
    if required_class and ledger_class and required_class != ledger_class:
        return False
    required_tier = _req_key(requirement.get("required_source_tier"))
    ledger_tier = _req_key(ledger_requirement.get("required_source_tier"))
    if required_tier and ledger_tier and required_tier != ledger_tier:
        return False
    required_currentness = _req_key(requirement.get("required_currentness"))
    ledger_currentness = _req_key(ledger_requirement.get("required_currentness"))
    if (
        required_currentness
        and ledger_currentness
        and required_currentness != ledger_currentness
    ):
        return False
    return True


def _match_rank(ledger_requirement: Mapping[str, Any]) -> int:
    status = clean_token(ledger_requirement.get("status"))
    score = 0
    if any(
        _field(ledger_requirement, key)
        for key in ("component_id", "source_obligation_id", "provider_job_id")
    ) or (
        clean_token(ledger_requirement.get("origin_ref")) or ""
    ).startswith("provider_job_execution:"):
        score += 300
    if status == "satisfied":
        score += 200
    elif status == "partially_satisfied":
        score += 100
    return score


def _best_match(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    best: tuple[int, dict[str, Any]] = (-1, {})
    for candidate in candidates:
        score = _match_rank(candidate)
        if score > best[0]:
            best = (score, dict(candidate))
    return best[1]


def _find_ledger_requirement(
    requirement: Mapping[str, Any],
    ledger_requirements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    exact = [
        item
        for item in ledger_requirements
        if _exact_requirement_match(requirement, item)
    ]
    if exact:
        return _best_match(exact)

    compatible = [
        item
        for item in ledger_requirements
        if _compatible_kind_and_class(requirement, item)
    ]
    requirement_lineage_refs = _lineage_refs(requirement)
    if requirement_lineage_refs:
        ref_matches = [
            item
            for item in compatible
            if requirement_lineage_refs & _lineage_refs(item)
        ]
        return _best_match(ref_matches) if ref_matches else {}

    return dict(compatible[0]) if len(compatible) == 1 else {}


def _assessment(
    requirement: Mapping[str, Any],
    *,
    status: str,
    reason: str | None,
    ledger_requirement: Mapping[str, Any] | None = None,
) -> SufficiencyRequirementAssessment:
    ledger = _mapping(ledger_requirement)
    provider_job_parts = _provider_job_requirement_parts(ledger)
    return SufficiencyRequirementAssessment(
        requirement_id=str(
            requirement.get("requirement_id")
            or ledger.get("requirement_id")
            or "requirement"
        ),
        requirement_kind=str(
            requirement.get("requirement_kind")
            or ledger.get("requirement_kind")
            or "general"
        ),
        required_source_class=clean_token(
            requirement.get("required_source_class")
            or ledger.get("required_source_class")
        ),
        required_source_tier=clean_token(
            requirement.get("required_source_tier")
            or ledger.get("required_source_tier")
        ),
        required_currentness=clean_token(
            requirement.get("required_currentness")
            or ledger.get("required_currentness")
        ),
        component_id=_ref_field(requirement, "component_id")
        or _ref_field(ledger, "component_id")
        or provider_job_parts.get("component_id"),
        source_obligation_id=_ref_field(
            requirement,
            "source_obligation_id",
            "obligation_id",
        )
        or _ref_field(ledger, "source_obligation_id", "obligation_id")
        or provider_job_parts.get("source_obligation_id"),
        provider_job_id=_ref_field(requirement, "provider_job_id", "provider_job_ref")
        or _ref_field(ledger, "provider_job_id", "provider_job_ref")
        or provider_job_parts.get("provider_job_id"),
        origin_ref=_field(requirement, "origin_ref") or _field(ledger, "origin_ref"),
        status=status,
        reason=reason or clean_text(ledger.get("reason"), limit=260),
        satisfied_candidate_ids=tuple(
            _string_list(ledger.get("linked_candidate_ids"))
            if status == "satisfied"
            else ()
        ),
    )


def _contract_items(projection: Mapping[str, Any], key: str) -> tuple[str, ...]:
    policy = _mapping(projection.get("final_posture_policy"))
    return tuple(_string_list(policy.get(key)))


def _partial_allowed(projection: Mapping[str, Any]) -> bool:
    policy = _mapping(projection.get("final_posture_policy"))
    return bool(policy.get("partial_allowed_if")) or not bool(
        projection.get("source_requirements")
    )


def _search_stopped_insufficient(projection: Mapping[str, Any]) -> bool:
    return (
        clean_token(projection.get("decision"))
        == RunSearchJudgmentDecision.STOP_INSUFFICIENT.value
    )


def _search_stopped_satisfied(projection: Mapping[str, Any]) -> bool:
    return (
        clean_token(projection.get("decision"))
        == RunSearchJudgmentDecision.STOP_SATISFIED.value
    )


def _recovery_exhausted(
    search_projection: Mapping[str, Any],
    budget: Mapping[str, Any],
) -> bool:
    if _search_stopped_insufficient(search_projection):
        return True
    if _truthy(budget.get("recovery_exhausted")):
        return True
    if _truthy(budget.get("budget_exhausted")):
        return True
    iteration = _int_value(budget.get("iteration") or budget.get("iterations_run"))
    max_iterations = _int_value(budget.get("max_iterations"))
    return max_iterations > 0 and iteration >= max_iterations


def _answer_contract_missing(
    projection: Mapping[str, Any],
) -> tuple[SufficiencyRequirementAssessment, ...]:
    assessments: list[SufficiencyRequirementAssessment] = []
    for source_class in _string_list(
        projection.get("unfulfilled_source_classes")
        or projection.get("missing_source_classes")
    ):
        assessments.append(
            SufficiencyRequirementAssessment(
                requirement_id=f"answer-contract:{source_class}",
                requirement_kind="answer_contract_source_class",
                required_source_class=source_class,
                status="missing",
                reason="answer_contract_unfulfilled_source_obligation",
            )
        )
    for source_class in _string_list(projection.get("partial_source_classes")):
        assessments.append(
            SufficiencyRequirementAssessment(
                requirement_id=f"answer-contract:partial:{source_class}",
                requirement_kind="answer_contract_source_class",
                required_source_class=source_class,
                status="partial",
                reason="answer_contract_partial_source_obligation",
            )
        )
    for source_class in _string_list(
        projection.get("source_bound_numeric_obligations")
        or projection.get("source_bound_numeric_unknowns")
    ):
        assessments.append(
            SufficiencyRequirementAssessment(
                requirement_id=f"answer-contract:source-bound:{source_class}",
                requirement_kind="source_bound_numeric",
                required_source_class=source_class,
                status="missing",
                reason="answer_contract_source_bound_numeric_missing",
            )
        )
    return tuple(assessments)


def _conflict_reasons(facts: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    if _truthy(facts.get("unresolved_central_conflict")):
        reasons.append("unresolved_central_conflict")
    if _truthy(facts.get("authoritative_posture_blocked")):
        reasons.append("authoritative_posture_blocked_by_conflict")
    if _truthy(facts.get("conflicts_present")) and clean_token(
        facts.get("conflict_posture")
    ) in {"unresolved", "central_unresolved", "blocking"}:
        reasons.append("unresolved_conflict_present")
    activation = _mapping(facts.get("source_conflict_answer_posture_activation"))
    if activation:
        if _truthy(activation.get("authoritative_posture_blocked")):
            reasons.append("authoritative_posture_blocked_by_conflict")
        if _int_value(activation.get("source_bound_unresolved_value_count")) > 0:
            reasons.append("source_bound_value_unresolved_by_conflict")
    return tuple(dict.fromkeys(reasons))


def _source_bound_unknowns(
    missing: Sequence[SufficiencyRequirementAssessment],
    partial: Sequence[SufficiencyRequirementAssessment],
    satisfied: Sequence[SufficiencyRequirementAssessment],
    final_evidence: Mapping[str, Any],
    conflict_facts: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    unknowns: list[dict[str, Any]] = []
    resolved_keys = _resolved_quant_requirement_keys(final_evidence)
    quant_packet_unknowns = _quant_packet_unknowns(final_evidence)
    for item in (*missing, *partial):
        if item.requirement_kind == "source_bound_numeric":
            unknowns.append(
                {
                    "requirement_id": item.requirement_id,
                    "source_class": item.required_source_class,
                    "reason": item.reason or "source_bound_numeric_missing",
                }
            )
    extraction_executed = any(
        _truthy(final_evidence.get(flag)) for flag in _SOURCE_BOUND_EXTRACTION_FLAGS
    )
    if not extraction_executed:
        for item in satisfied:
            if item.requirement_kind == "source_bound_numeric" and (
                item.provider_job_id
                or (item.origin_ref or "").startswith("provider_job_execution:")
                or item.required_source_class == "sourced_numeric_values"
            ):
                if _assessment_quant_keys(item) & resolved_keys:
                    continue
                unknowns.append(
                    {
                        "requirement_id": item.requirement_id,
                        "source_class": item.required_source_class,
                        "satisfied_candidate_ids": list(
                            item.satisfied_candidate_ids
                        ),
                        "reason": "source_bound_numeric_extraction_deferred",
                    }
                )
    unknowns.extend(quant_packet_unknowns)
    activation = _mapping(conflict_facts.get("source_conflict_answer_posture_activation"))
    if _int_value(activation.get("source_bound_unresolved_value_count")) > 0:
        unknowns.append(
            {
                "requirement_id": "conflict:source_bound_numeric",
                "reason": "source_bound_value_unresolved_by_conflict",
            }
        )
    if _truthy(conflict_facts.get("source_bound_value_unresolved")):
        unknowns.append(
            {
                "requirement_id": "conflict:source_bound_numeric",
                "reason": "source_bound_value_unresolved",
            }
        )
    return tuple(unknowns)


def _quant_packets(final_evidence: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    packets = final_evidence.get("quant_work_unit_packets") or final_evidence.get(
        "source_bound_numeric_packets"
    )
    return tuple(item for item in _list(packets) if isinstance(item, Mapping))


def _assessment_quant_keys(item: SufficiencyRequirementAssessment) -> set[str]:
    return {
        key
        for key in {
            _req_key(item.requirement_id),
            _req_key(item.component_id),
            _req_key(item.source_obligation_id),
            _req_key(item.provider_job_id),
        }
        if key
    }


def _packet_quant_keys(packet: Mapping[str, Any]) -> set[str]:
    keys: set[str] = set()
    for key in ("requirement_ids", "source_obligation_ids", "component_ids"):
        keys.update(_req_key(item) for item in _list(packet.get(key)))
    keys.add(_req_key(packet.get("quant_unit_id")))
    return {key for key in keys if key}


def _resolved_quant_requirement_keys(final_evidence: Mapping[str, Any]) -> set[str]:
    keys: set[str] = set()
    for packet in _quant_packets(final_evidence):
        if clean_token(packet.get("calculation_status")) != "succeeded":
            continue
        if clean_token(packet.get("extraction_status")) != "succeeded":
            continue
        keys.update(_packet_quant_keys(packet))
    return keys


def _source_bound_resolutions(
    final_evidence: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    resolutions: list[dict[str, Any]] = []
    for packet in _quant_packets(final_evidence):
        if clean_token(packet.get("calculation_status")) != "succeeded":
            continue
        if clean_token(packet.get("extraction_status")) != "succeeded":
            continue
        resolutions.append(
            {
                "quant_unit_id": clean_token(packet.get("quant_unit_id")),
                "component_ids": _string_list(packet.get("component_ids")),
                "source_obligation_ids": _string_list(packet.get("source_obligation_ids")),
                "requirement_ids": _string_list(packet.get("requirement_ids")),
                "required_variables": _string_list(packet.get("required_variables")),
                "extracted_values": [
                    _mapping(item)
                    for item in _list(packet.get("extracted_values"))
                    if isinstance(item, Mapping)
                ],
                "calculation_result": _mapping(packet.get("calculation_result")),
                "source_refs": [
                    _mapping(item)
                    for item in _list(packet.get("source_refs"))
                    if isinstance(item, Mapping)
                ],
                "high_stakes_quant": _truthy(packet.get("high_stakes_quant")),
                "reason": "source_bound_numeric_extraction_and_calculation_succeeded",
            }
        )
    return tuple(resolutions)


def _quant_packet_unknowns(final_evidence: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    unknowns: list[dict[str, Any]] = []
    for packet in _quant_packets(final_evidence):
        if clean_token(packet.get("calculation_status")) == "succeeded" and clean_token(
            packet.get("extraction_status")
        ) == "succeeded":
            continue
        unknowns.append(
            {
                "requirement_id": (
                    next(iter(_string_list(packet.get("requirement_ids"))), None)
                    or clean_token(packet.get("quant_unit_id"))
                    or "source_bound_numeric"
                ),
                "quant_unit_id": clean_token(packet.get("quant_unit_id")),
                "source_class": "sourced_numeric_values",
                "unresolved_values": [
                    _mapping(item)
                    for item in _list(packet.get("unresolved_values"))
                    if isinstance(item, Mapping)
                ],
                "blocked_reasons": _string_list(packet.get("blocked_reasons")),
                "reason": (
                    next(iter(_string_list(packet.get("blocked_reasons"))), None)
                    or "source_bound_numeric_quant_work_unresolved"
                ),
            }
        )
    return tuple(unknowns)


def _indirect_claims(facts: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    claims: list[dict[str, Any]] = []
    if _int_value(facts.get("inferred_claim_count")) > 0 or _truthy(
        facts.get("requires_inference_label")
    ):
        claims.append(
            {
                "claim_id": clean_token(facts.get("claim_id")) or "inferred_claim",
                "requires_inference_label": True,
                "reason": "indirect_inference_claim_requires_labeling",
            }
        )
    for item in _list(facts.get("claims") or facts.get("path_effects")):
        if not isinstance(item, Mapping):
            continue
        if _truthy(item.get("requires_inference_label")) or (
            clean_token(item.get("answer_posture"))
            == "inferred_from_sourced_premises"
        ):
            claims.append(
                {
                    "claim_id": clean_token(item.get("target_claim_id"))
                    or clean_token(item.get("claim_id"))
                    or "inferred_claim",
                    "requires_inference_label": True,
                    "reason": "indirect_inference_claim_requires_labeling",
                }
            )
    return tuple(claims)


def _weak_reasons(facts: Mapping[str, Any], final_evidence: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    if _truthy(facts.get("corpus_weak")):
        reasons.append(
            clean_token(facts.get("weak_corpus_reason")) or "weak_corpus"
        )
    if _truthy(facts.get("synth_was_insufficient")):
        reasons.append("synthesis_insufficient")
    if _int_value(final_evidence.get("final_evidence_count")) <= 0:
        reasons.append("no_final_evidence_available")
    if _truthy(final_evidence.get("thin_evidence")):
        reasons.append("thin_final_evidence")
    return tuple(dict.fromkeys(reasons))


def _failure_card_authorized(facts: Mapping[str, Any]) -> bool:
    payload = _mapping(facts.get("failure_card"))
    return _truthy(facts.get("failure_card_authorized")) or _truthy(
        payload.get("show")
    )


def _failure_card_reason(facts: Mapping[str, Any]) -> str:
    payload = _mapping(facts.get("failure_card"))
    return (
        clean_token(facts.get("failure_card_reason"))
        or clean_token(payload.get("reason"))
        or "failure_card"
    )


def _readiness_reasons(
    *,
    missing: Sequence[SufficiencyRequirementAssessment],
    partial: Sequence[SufficiencyRequirementAssessment],
    conflicts: Sequence[str],
    inferred: Sequence[Mapping[str, Any]],
    unknowns: Sequence[Mapping[str, Any]],
    weak: Sequence[str],
    failure_card: bool,
    search_insufficient: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if missing:
        reasons.append("required_obligations_missing")
    if partial:
        reasons.append("required_obligations_partial")
    if conflicts:
        reasons.append("unresolved_conflicts_present")
    if inferred:
        reasons.append("indirect_inference_requires_labeling")
    if unknowns:
        reasons.append("source_bound_numeric_unknown")
    if weak:
        reasons.extend(weak)
    if failure_card:
        reasons.append("failure_card_authorized")
    if search_insufficient:
        reasons.append("search_judgment_stop_insufficient")
    return tuple(dict.fromkeys(reasons))


def _mandatory_caveats(
    *,
    contract: Mapping[str, Any],
    missing: Sequence[SufficiencyRequirementAssessment],
    partial: Sequence[SufficiencyRequirementAssessment],
    conflicts: Sequence[str],
    inferred: Sequence[Mapping[str, Any]],
    unknowns: Sequence[Mapping[str, Any]],
    weak: Sequence[str],
    failure_card: bool,
    failure_card_reason: str,
) -> tuple[str, ...]:
    caveats: list[str] = []
    for item in missing:
        if item.requirement_kind == "official_current":
            caveats.append(f"official_current_unsatisfied:{item.required_source_class}")
        elif item.requirement_kind == "source_bound_numeric":
            caveats.append(
                f"source_bound_value_missing:{item.required_source_class}"
            )
        else:
            caveats.append(f"missing_required_source:{item.required_source_class}")
        if item.reason == "aggregate_counts_cannot_satisfy_custody":
            caveats.append("aggregate_only_evidence_ledger_custody_insufficient")
        if item.reason == "no_linked_candidate_satisfies_requirement":
            caveats.append("candidate_level_custody_does_not_satisfy_requirement")
    for item in partial:
        caveats.append(f"partial_source_obligation:{item.required_source_class}")
    if missing or partial or unknowns:
        caveats.extend(_contract_items(contract, "mandatory_caveats"))
    for reason in conflicts:
        caveats.append(f"unresolved_conflict_must_be_caveated:{reason}")
    if inferred:
        caveats.append("inferred_conclusion_must_not_be_presented_as_directly_sourced")
    if unknowns:
        caveats.append("missing_source_bound_numeric_value_remains_unknown")
    for reason in weak:
        if reason == "synthesis_insufficient":
            caveats.append("synthesis_insufficient_must_be_caveated")
        elif reason == "no_final_evidence_available":
            caveats.append("no_final_evidence_must_be_caveated")
        else:
            caveats.append("weak_corpus_must_be_caveated")
    if failure_card:
        caveats.append(f"failure_card_authorized:{failure_card_reason}")
    return tuple(dict.fromkeys(item for item in caveats if item))


def _prohibited_upgrades(
    *,
    contract: Mapping[str, Any],
    missing: Sequence[SufficiencyRequirementAssessment],
    conflicts: Sequence[str],
    inferred: Sequence[Mapping[str, Any]],
    unknowns: Sequence[Mapping[str, Any]],
    weak: Sequence[str],
    failure_card: bool,
) -> tuple[str, ...]:
    prohibited = [
        "do_not_infer_source_obligation_satisfaction_from_citation_presence",
        "do_not_treat_aggregate_counts_as_evidence_ledger_custody",
    ]
    prohibited.extend(_contract_items(contract, "prohibited_upgrades"))
    if missing:
        prohibited.append(
            "do_not_treat_lower_tier_stale_or_off_topic_evidence_as_required_custody"
        )
    if conflicts:
        prohibited.append("do_not_flatten_unresolved_conflicts_into_direct_claims")
    if inferred:
        prohibited.append("do_not_launder_inference_as_direct_source_claim")
    if unknowns:
        prohibited.append("do_not_present_source_bound_numeric_unknown_as_known")
    if weak or failure_card:
        prohibited.append("do_not_upgrade_weak_or_failure_card_posture_to_direct")
    return tuple(dict.fromkeys(item for item in prohibited if item))


def _decision_and_posture(
    *,
    contract: Mapping[str, Any],
    missing: Sequence[SufficiencyRequirementAssessment],
    partial: Sequence[SufficiencyRequirementAssessment],
    conflicts: Sequence[str],
    inferred: Sequence[Mapping[str, Any]],
    unknowns: Sequence[Mapping[str, Any]],
    weak: Sequence[str],
    failure_card: bool,
    recovery_exhausted: bool,
    search_satisfied: bool,
    final_evidence_count: int,
) -> tuple[RunSufficiencyDecision, SufficiencyPosture, bool, str]:
    if failure_card:
        return (
            RunSufficiencyDecision.INSUFFICIENT_EVIDENCE,
            SufficiencyPosture.FAILURE_CARD,
            True,
            "failure_card_authorized_by_runtime_state",
        )
    if conflicts:
        return (
            RunSufficiencyDecision.CONFLICT_BLOCKED,
            SufficiencyPosture.ANSWER_WITH_CAVEATS,
            True,
            "unresolved_conflict_blocks_overconfident_posture",
        )
    if unknowns:
        return (
            RunSufficiencyDecision.SOURCE_BOUND_NUMERIC_UNKNOWN,
            SufficiencyPosture.PARTIAL_ANSWER
            if final_evidence_count > 0
            else SufficiencyPosture.INSUFFICIENT_ANSWER,
            True,
            "source_bound_numeric_value_remains_unknown",
        )
    if recovery_exhausted and (missing or partial):
        return (
            RunSufficiencyDecision.RECOVERY_REQUIRED_BUT_EXHAUSTED,
            SufficiencyPosture.INSUFFICIENT_ANSWER,
            True,
            "search_or_recovery_exhausted_with_required_gaps",
        )
    if missing:
        if _partial_allowed(contract):
            return (
                RunSufficiencyDecision.PARTIAL_ANSWER_AUTHORIZED,
                SufficiencyPosture.PARTIAL_ANSWER,
                True,
                "required_obligations_missing_but_partial_answer_authorized",
            )
        return (
            RunSufficiencyDecision.INSUFFICIENT_EVIDENCE,
            SufficiencyPosture.INSUFFICIENT_ANSWER,
            True,
            "required_obligations_missing",
        )
    if inferred:
        return (
            RunSufficiencyDecision.INFERENCE_ONLY_WITH_LABELING,
            SufficiencyPosture.ANSWER_WITH_CAVEATS,
            True,
            "inferred_conclusion_requires_labeling",
        )
    if partial:
        return (
            RunSufficiencyDecision.READY_WITH_CAVEATS,
            SufficiencyPosture.ANSWER_WITH_CAVEATS,
            True,
            "partial_or_preferred_obligations_require_caveats",
        )
    if weak:
        return (
            RunSufficiencyDecision.READY_WITH_CAVEATS,
            SufficiencyPosture.ANSWER_WITH_CAVEATS,
            True,
            "weak_or_thin_evidence_requires_caveats",
        )
    if search_satisfied or final_evidence_count > 0:
        return (
            RunSufficiencyDecision.READY_DIRECT,
            SufficiencyPosture.DIRECT_ANSWER,
            True,
            "required_obligations_satisfied_by_evidence_ledger",
        )
    return (
        RunSufficiencyDecision.INSUFFICIENT_EVIDENCE,
        SufficiencyPosture.INSUFFICIENT_ANSWER,
        True,
        "no_final_evidence_available",
    )


def build_deterministic_sufficiency_judgment(
    judgment_input: RunSufficiencyJudgmentInput,
) -> RunSufficiencyJudgment:
    """Apply conservative deterministic RunAuthority final sufficiency logic."""

    contract = _mapping(judgment_input.contract_projection)
    ledger = _mapping(judgment_input.evidence_ledger_projection)
    search = _mapping(judgment_input.search_judgment_projection)
    answer_contract = _mapping(judgment_input.answer_contract_projection)
    final_evidence = _mapping(judgment_input.final_evidence_facts)
    conflict_facts = _mapping(judgment_input.conflict_facts)
    inference_facts = _mapping(judgment_input.indirect_inference_facts)
    weak_facts = _mapping(judgment_input.weak_failure_facts)
    budget = _mapping(judgment_input.budget)

    ledger_requirements = _ledger_requirements(ledger)
    missing: list[SufficiencyRequirementAssessment] = []
    partial: list[SufficiencyRequirementAssessment] = []
    satisfied: list[SufficiencyRequirementAssessment] = []
    for requirement in _required_contract_requirements(contract):
        ledger_requirement = _find_ledger_requirement(
            requirement,
            ledger_requirements,
        )
        status = clean_token(ledger_requirement.get("status"))
        if status == "satisfied":
            satisfied.append(
                _assessment(
                    requirement,
                    status="satisfied",
                    reason="evidence_ledger_requirement_satisfied",
                    ledger_requirement=ledger_requirement,
                )
            )
        elif status == "partially_satisfied":
            partial.append(
                _assessment(
                    requirement,
                    status="partial",
                    reason="evidence_ledger_requirement_partially_satisfied",
                    ledger_requirement=ledger_requirement,
                )
            )
        elif status in _MISSING_LEDGER_STATUSES or not status:
            missing.append(
                _assessment(
                    requirement,
                    status="missing",
                    reason=(
                        clean_text(ledger_requirement.get("reason"), limit=260)
                        or "required_evidence_ledger_gap"
                    ),
                    ledger_requirement=ledger_requirement,
                )
            )

    for item in _answer_contract_missing(answer_contract):
        if not any(
            existing.required_source_class == item.required_source_class
            and existing.requirement_kind == item.requirement_kind
            for existing in (*missing, *partial)
        ):
            if item.status == "partial":
                partial.append(item)
            else:
                missing.append(item)

    for requirement in _preferred_contract_requirements(contract):
        ledger_requirement = _find_ledger_requirement(
            requirement,
            ledger_requirements,
        )
        if clean_token(ledger_requirement.get("status")) == "satisfied":
            satisfied.append(
                _assessment(
                    requirement,
                    status="satisfied",
                    reason="preferred_evidence_ledger_requirement_satisfied",
                    ledger_requirement=ledger_requirement,
                )
            )
        elif requirement.get("required_source_class"):
            partial.append(
                _assessment(
                    requirement,
                    status="partial",
                    reason="preferred_source_obligation_not_satisfied",
                    ledger_requirement=ledger_requirement,
                )
            )

    conflicts = _conflict_reasons(conflict_facts)
    inferred = _indirect_claims(inference_facts)
    unknowns = _source_bound_unknowns(
        missing,
        partial,
        satisfied,
        final_evidence,
        conflict_facts,
    )
    quant_resolutions = _source_bound_resolutions(final_evidence)
    weak = _weak_reasons(weak_facts, final_evidence)
    failure_card = _failure_card_authorized(weak_facts)
    failure_reason = _failure_card_reason(weak_facts)
    search_insufficient = _search_stopped_insufficient(search)
    recovery_exhausted = _recovery_exhausted(search, budget)
    search_satisfied = _search_stopped_satisfied(search)
    final_evidence_count = _int_value(final_evidence.get("final_evidence_count"))
    if final_evidence_count <= 0:
        final_evidence_count = _int_value(final_evidence.get("author_evidence_count"))

    decision, posture, final_allowed, rationale = _decision_and_posture(
        contract=contract,
        missing=missing,
        partial=partial,
        conflicts=conflicts,
        inferred=inferred,
        unknowns=unknowns,
        weak=weak,
        failure_card=failure_card,
        recovery_exhausted=recovery_exhausted,
        search_satisfied=search_satisfied,
        final_evidence_count=final_evidence_count,
    )
    readiness_reasons = _readiness_reasons(
        missing=missing,
        partial=partial,
        conflicts=conflicts,
        inferred=inferred,
        unknowns=unknowns,
        weak=weak,
        failure_card=failure_card,
        search_insufficient=search_insufficient,
    )
    mandatory = _mandatory_caveats(
        contract=contract,
        missing=missing,
        partial=partial,
        conflicts=conflicts,
        inferred=inferred,
        unknowns=unknowns,
        weak=weak,
        failure_card=failure_card,
        failure_card_reason=failure_reason,
    )
    prohibited = _prohibited_upgrades(
        contract=contract,
        missing=missing,
        conflicts=conflicts,
        inferred=inferred,
        unknowns=unknowns,
        weak=weak,
        failure_card=failure_card,
    )
    required_satisfied = not missing and not any(
        item.status == "partial" and item.requirement_kind != "reputable_secondary"
        for item in partial
    )
    if not _required_contract_requirements(contract) and final_evidence_count > 0:
        required_satisfied = True

    return RunSufficiencyJudgment(
        judgment_id=f"sufficiency:{stable_hash(judgment_input.to_model_payload())[:16]}",
        decision=decision,
        mode=SufficiencyJudgmentMode.DETERMINISTIC,
        final_answer_posture=posture,
        contract_id=clean_token(contract.get("contract_id")),
        selected_template_ids=tuple(_string_list(contract.get("selected_template_ids"))),
        contract_fulfilled=bool(required_satisfied and not conflicts and not unknowns),
        required_obligations_satisfied=bool(required_satisfied),
        missing_required_obligations=tuple(missing),
        partial_obligations=tuple(partial),
        satisfied_obligations=tuple(satisfied),
        unresolved_conflicts=conflicts,
        indirect_inference_claims=inferred,
        source_bound_numeric_unknowns=unknowns,
        source_bound_numeric_resolutions=quant_resolutions,
        weak_or_thin_evidence=weak,
        failure_card_authorized=failure_card,
        final_answer_allowed=final_allowed,
        mandatory_caveats=mandatory,
        prohibited_upgrades=prohibited,
        readiness_reasons=readiness_reasons,
        rationale=rationale,
    )


def _unsafe_direct_model_posture(
    model: RunSufficiencyJudgment,
    deterministic: RunSufficiencyJudgment,
) -> str | None:
    direct = (
        model.decision is RunSufficiencyDecision.READY_DIRECT
        or model.final_answer_posture is SufficiencyPosture.DIRECT_ANSWER
    )
    if not direct:
        return None
    if deterministic.missing_required_obligations:
        return "model_ready_direct_with_required_evidence_ledger_gaps"
    if deterministic.partial_obligations:
        return "model_ready_direct_with_partial_obligations"
    if deterministic.source_bound_numeric_unknowns:
        return "model_ready_direct_with_source_bound_numeric_unknowns"
    if deterministic.unresolved_conflicts:
        return "model_ready_direct_with_unresolved_conflicts"
    if deterministic.indirect_inference_claims:
        return "model_ready_direct_launders_inference"
    if deterministic.weak_or_thin_evidence or deterministic.failure_card_authorized:
        return "model_ready_direct_ignores_weak_or_failure_posture"
    return None


def _with_model_metadata(
    judgment: RunSufficiencyJudgment,
    *,
    mode: SufficiencyJudgmentMode,
    validation: SufficiencyValidationResult,
    prompt_hash: str | None,
    prompt_length: int,
    provider: str | None,
    model: str | None,
    effort: str | None,
    use_reasoning: bool | None,
) -> RunSufficiencyJudgment:
    return replace(
        judgment,
        mode=mode,
        validation=validation.to_dict(),
        prompt_hash=prompt_hash,
        prompt_length=prompt_length,
        model_identity={
            "provider": provider,
            "model": model,
            "effort": effort,
            "use_reasoning": use_reasoning,
        },
    )


def validate_or_repair_sufficiency_judgment(
    payload: Mapping[str, Any] | None,
    *,
    deterministic_judgment: RunSufficiencyJudgment,
    model_attempted: bool,
    prompt_hash: str | None = None,
    prompt_length: int = 0,
    provider: str | None = None,
    model: str | None = None,
    effort: str | None = None,
    use_reasoning: bool | None = None,
    fallback_reason: str | None = None,
) -> tuple[RunSufficiencyJudgment, SufficiencyValidationResult]:
    if payload is None:
        reasons = (fallback_reason or "model_sufficiency_payload_unavailable",)
        validation = SufficiencyValidationResult(
            status=SufficiencyValidationStatus.FALLBACK,
            reasons=reasons,
            fallback_used=True,
            model_attempted=model_attempted,
            deterministic_decision=deterministic_judgment.decision.value,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            provider=provider,
            model=model,
            effort=effort,
            use_reasoning=use_reasoning,
        )
        return (
            _with_model_metadata(
                deterministic_judgment,
                mode=SufficiencyJudgmentMode.FALLBACK,
                validation=validation,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
            ),
            validation,
        )

    try:
        model_judgment = RunSufficiencyJudgment.from_mapping(payload)
    except Exception as exc:
        return validate_or_repair_sufficiency_judgment(
            None,
            deterministic_judgment=deterministic_judgment,
            model_attempted=model_attempted,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            provider=provider,
            model=model,
            effort=effort,
            use_reasoning=use_reasoning,
            fallback_reason=f"model_sufficiency_invalid:{type(exc).__name__}",
        )

    repair_reason = _unsafe_direct_model_posture(model_judgment, deterministic_judgment)
    if repair_reason is not None:
        validation = SufficiencyValidationResult(
            status=SufficiencyValidationStatus.REPAIRED,
            reasons=(repair_reason,),
            fallback_used=False,
            model_attempted=model_attempted,
            deterministic_decision=deterministic_judgment.decision.value,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            provider=provider,
            model=model,
            effort=effort,
            use_reasoning=use_reasoning,
        )
        return (
            _with_model_metadata(
                deterministic_judgment,
                mode=SufficiencyJudgmentMode.REPAIRED,
                validation=validation,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
            ),
            validation,
        )

    reasons: list[str] = []
    mandatory = list(dict.fromkeys(
        tuple(model_judgment.mandatory_caveats)
        + tuple(deterministic_judgment.mandatory_caveats)
    ))
    prohibited = list(dict.fromkeys(
        tuple(model_judgment.prohibited_upgrades)
        + tuple(deterministic_judgment.prohibited_upgrades)
    ))
    if tuple(mandatory) != model_judgment.mandatory_caveats:
        reasons.append("restored_required_mandatory_caveats")
    if tuple(prohibited) != model_judgment.prohibited_upgrades:
        reasons.append("restored_required_prohibited_upgrades")

    required_missing = deterministic_judgment.missing_required_obligations
    required_partial = deterministic_judgment.partial_obligations
    unknowns = deterministic_judgment.source_bound_numeric_unknowns
    resolutions = deterministic_judgment.source_bound_numeric_resolutions
    conflicts = deterministic_judgment.unresolved_conflicts
    inferred = deterministic_judgment.indirect_inference_claims
    weak = deterministic_judgment.weak_or_thin_evidence
    failure_card = deterministic_judgment.failure_card_authorized
    if required_missing and not model_judgment.missing_required_obligations:
        reasons.append("restored_required_missing_obligations")
    if required_partial and not model_judgment.partial_obligations:
        reasons.append("restored_partial_obligations")
    if unknowns and not model_judgment.source_bound_numeric_unknowns:
        reasons.append("restored_source_bound_numeric_unknowns")
    if resolutions and not model_judgment.source_bound_numeric_resolutions:
        reasons.append("restored_source_bound_numeric_resolutions")
    if conflicts and not model_judgment.unresolved_conflicts:
        reasons.append("restored_unresolved_conflicts")
    if inferred and not model_judgment.indirect_inference_claims:
        reasons.append("restored_indirect_inference_labels")
    if weak and not model_judgment.weak_or_thin_evidence:
        reasons.append("restored_weak_or_thin_evidence")
    if failure_card and not model_judgment.failure_card_authorized:
        reasons.append("restored_failure_card_authorization")

    if reasons:
        repaired = replace(
            model_judgment,
            mode=SufficiencyJudgmentMode.REPAIRED,
            missing_required_obligations=(
                model_judgment.missing_required_obligations or required_missing
            ),
            partial_obligations=model_judgment.partial_obligations or required_partial,
            satisfied_obligations=(
                model_judgment.satisfied_obligations
                or deterministic_judgment.satisfied_obligations
            ),
            source_bound_numeric_unknowns=(
                model_judgment.source_bound_numeric_unknowns or unknowns
            ),
            source_bound_numeric_resolutions=(
                model_judgment.source_bound_numeric_resolutions or resolutions
            ),
            unresolved_conflicts=model_judgment.unresolved_conflicts or conflicts,
            indirect_inference_claims=model_judgment.indirect_inference_claims
            or inferred,
            weak_or_thin_evidence=model_judgment.weak_or_thin_evidence or weak,
            failure_card_authorized=model_judgment.failure_card_authorized
            or failure_card,
            mandatory_caveats=tuple(mandatory),
            prohibited_upgrades=tuple(prohibited),
            readiness_reasons=tuple(
                dict.fromkeys(
                    tuple(model_judgment.readiness_reasons)
                    + tuple(deterministic_judgment.readiness_reasons)
                )
            ),
            final_packet_inputs={},
        )
        validation = SufficiencyValidationResult(
            status=SufficiencyValidationStatus.REPAIRED,
            reasons=tuple(reasons),
            fallback_used=False,
            model_attempted=model_attempted,
            deterministic_decision=deterministic_judgment.decision.value,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            provider=provider,
            model=model,
            effort=effort,
            use_reasoning=use_reasoning,
        )
        return (
            _with_model_metadata(
                repaired,
                mode=SufficiencyJudgmentMode.REPAIRED,
                validation=validation,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
            ),
            validation,
        )

    validation = SufficiencyValidationResult(
        status=SufficiencyValidationStatus.VALID,
        reasons=(),
        fallback_used=False,
        model_attempted=model_attempted,
        deterministic_decision=deterministic_judgment.decision.value,
        prompt_hash=prompt_hash,
        prompt_length=prompt_length,
        provider=provider,
        model=model,
        effort=effort,
        use_reasoning=use_reasoning,
    )
    return (
        _with_model_metadata(
            model_judgment,
            mode=SufficiencyJudgmentMode.SMART_MODEL_ADAPTED,
            validation=validation,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            provider=provider,
            model=model,
            effort=effort,
            use_reasoning=use_reasoning,
        ),
        validation,
    )


__all__ = [
    "build_deterministic_sufficiency_judgment",
    "validate_or_repair_sufficiency_judgment",
]
