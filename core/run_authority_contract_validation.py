"""Deterministic validation and repair for RunAuthority contracts."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence

from core.run_authority_contract import (
    ContractSynthesisMode,
    ContractSynthesisStatus,
    RunAuthorityContract,
    RunContractRequirementKind,
    RunContractSourceRequirement,
    RunContractStrictness,
    RunContractValidationResult,
    clean_token,
    stable_hash,
)

_PROTECTED_KINDS = frozenset(
    {
        RunContractRequirementKind.OFFICIAL_CURRENT,
        RunContractRequirementKind.LEGAL_PRIMARY,
        RunContractRequirementKind.CANONICAL_DOCS,
        RunContractRequirementKind.SOURCE_BOUND_NUMERIC,
        RunContractRequirementKind.USER_DOCUMENT,
    }
)
_WEAK_SOURCE_CLASSES = frozenset(
    {
        "reputable_secondary",
        "secondary",
        "secondary_analysis",
        "trusted_community",
        "social_signal",
        "social_or_forum",
        "community",
        "forum",
    }
)
_WEAK_SOURCE_TIERS = frozenset(
    {"secondary", "trusted_community", "social_or_forum", "community", "context"}
)
_REQUIRED_WEAK_EXCLUSIONS = (
    "social_signal",
    "social_or_forum",
    "trusted_community",
    "aggregate_count_only",
    "helper_assessment_only",
)


def _req_key(requirement: RunContractSourceRequirement) -> tuple[str | None, str]:
    return (
        clean_token(requirement.required_source_class),
        requirement.requirement_kind.value,
    )


def _is_protected(requirement: RunContractSourceRequirement) -> bool:
    return (
        requirement.requirement_kind in _PROTECTED_KINDS
        or requirement.strictness is RunContractStrictness.REQUIRED
        and (
            clean_token(requirement.required_source_tier) in {"official", "primary", "canonical"}
            or clean_token(requirement.required_currentness) in {"current", "official_current"}
        )
    )


def _candidate_by_key(
    contract: RunAuthorityContract,
) -> dict[tuple[str | None, str], RunContractSourceRequirement]:
    return {_req_key(requirement): requirement for requirement in contract.source_requirements}


def _merge_exclusions(
    requirement: RunContractSourceRequirement,
) -> RunContractSourceRequirement:
    cannot = list(requirement.cannot_satisfy_with)
    for value in _REQUIRED_WEAK_EXCLUSIONS:
        if value not in cannot:
            cannot.append(value)
    return replace(requirement, cannot_satisfy_with=tuple(cannot))


def _repair_requirement_against_baseline(
    candidate: RunContractSourceRequirement | None,
    baseline: RunContractSourceRequirement,
    reasons: list[str],
) -> RunContractSourceRequirement:
    if candidate is None:
        reasons.append(f"restored_missing_required_requirement:{baseline.requirement_id}")
        return _merge_exclusions(baseline)
    if not _is_protected(baseline):
        return candidate

    repaired = candidate
    if candidate.strictness_rank < baseline.strictness_rank:
        repaired = replace(repaired, strictness=baseline.strictness)
        reasons.append(f"restored_strictness:{baseline.requirement_id}")
    if clean_token(candidate.required_source_class) in _WEAK_SOURCE_CLASSES:
        repaired = replace(repaired, required_source_class=baseline.required_source_class)
        reasons.append(f"blocked_secondary_only_source_class:{baseline.requirement_id}")
    if clean_token(candidate.required_source_tier) in _WEAK_SOURCE_TIERS:
        repaired = replace(repaired, required_source_tier=baseline.required_source_tier)
        reasons.append(f"blocked_lower_tier_requirement:{baseline.requirement_id}")
    if baseline.required_currentness and not clean_token(candidate.required_currentness):
        repaired = replace(repaired, required_currentness=baseline.required_currentness)
        reasons.append(f"restored_currentness:{baseline.requirement_id}")
    if baseline.required_source_tier and not clean_token(candidate.required_source_tier):
        repaired = replace(repaired, required_source_tier=baseline.required_source_tier)
        reasons.append(f"restored_source_tier:{baseline.requirement_id}")
    if baseline.required_source_class and not clean_token(candidate.required_source_class):
        repaired = replace(repaired, required_source_class=baseline.required_source_class)
        reasons.append(f"restored_source_class:{baseline.requirement_id}")
    return _merge_exclusions(repaired)


def _dedupe_requirements(
    requirements: Sequence[RunContractSourceRequirement],
) -> tuple[RunContractSourceRequirement, ...]:
    out: list[RunContractSourceRequirement] = []
    seen: set[tuple[str | None, str]] = set()
    for requirement in requirements:
        key = _req_key(requirement)
        if key in seen:
            continue
        out.append(requirement)
        seen.add(key)
    return tuple(out)


def _validate_required_fields(contract: RunAuthorityContract) -> list[str]:
    reasons: list[str] = []
    if not contract.contract_id:
        reasons.append("missing_contract_id")
    if not contract.selected_template_ids:
        reasons.append("missing_selected_template_ids")
    if not contract.source_requirements:
        reasons.append("missing_source_requirements")
    for requirement in contract.source_requirements:
        if not clean_token(requirement.requirement_id):
            reasons.append("missing_requirement_id")
        if requirement.is_required and not clean_token(requirement.required_source_class):
            reasons.append(f"missing_required_source_class:{requirement.requirement_id}")
    return reasons


def validate_or_fallback_contract(
    candidate: RunAuthorityContract | Mapping[str, Any] | None,
    *,
    deterministic_contract: RunAuthorityContract,
    model_attempted: bool = False,
    prompt_hash: str | None = None,
    prompt_length: int = 0,
    provider: str | None = None,
    model: str | None = None,
    effort: str | None = None,
    use_reasoning: bool | None = None,
    fallback_reason: str | None = None,
) -> tuple[RunAuthorityContract, RunContractValidationResult]:
    """Validate a model-adapted contract and repair/fallback safely."""

    if candidate is None:
        reason = fallback_reason or "missing_model_contract"
        return (
            replace(
                deterministic_contract,
                synthesis_mode=ContractSynthesisMode.FALLBACK,
            ),
            RunContractValidationResult(
                status=ContractSynthesisStatus.FALLBACK,
                reasons=(reason,),
                fallback_used=True,
                deterministic_template_ids=deterministic_contract.selected_template_ids,
                model_attempted=model_attempted,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
            ),
        )
    try:
        model_contract = (
            RunAuthorityContract.from_mapping(candidate)
            if isinstance(candidate, Mapping)
            else candidate
        )
    except Exception as exc:
        return (
            replace(
                deterministic_contract,
                synthesis_mode=ContractSynthesisMode.FALLBACK,
            ),
            RunContractValidationResult(
                status=ContractSynthesisStatus.FALLBACK,
                reasons=(fallback_reason or f"invalid_model_contract:{type(exc).__name__}",),
                fallback_used=True,
                deterministic_template_ids=deterministic_contract.selected_template_ids,
                model_attempted=model_attempted,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
            ),
        )

    invalid_reasons = _validate_required_fields(model_contract)
    if invalid_reasons:
        return (
            replace(
                deterministic_contract,
                synthesis_mode=ContractSynthesisMode.FALLBACK,
            ),
            RunContractValidationResult(
                status=ContractSynthesisStatus.FALLBACK,
                reasons=tuple(invalid_reasons),
                fallback_used=True,
                deterministic_template_ids=deterministic_contract.selected_template_ids,
                model_attempted=model_attempted,
                prompt_hash=prompt_hash,
                prompt_length=prompt_length,
                provider=provider,
                model=model,
                effort=effort,
                use_reasoning=use_reasoning,
            ),
        )

    reasons: list[str] = []
    candidate_requirements = _candidate_by_key(model_contract)
    repaired_requirements: list[RunContractSourceRequirement] = []
    for baseline in deterministic_contract.source_requirements:
        repaired_requirements.append(
            _repair_requirement_against_baseline(
                candidate_requirements.get(_req_key(baseline)),
                baseline,
                reasons,
            )
        )
    baseline_keys = {_req_key(requirement) for requirement in deterministic_contract.source_requirements}
    for requirement in model_contract.source_requirements:
        if _req_key(requirement) not in baseline_keys:
            repaired_requirements.append(
                _merge_exclusions(requirement) if _is_protected(requirement) else requirement
            )

    numeric_policy = dict(model_contract.numeric_policy or {})
    if deterministic_contract.numeric_policy.get("source_bound_required"):
        if numeric_policy.get("source_bound_required") is not True:
            reasons.append("restored_source_bound_numeric_policy")
        numeric_policy["source_bound_required"] = True
        numeric_policy["unsupported_values_unknown"] = True
        numeric_policy.setdefault("calculations_allowed_from_sourced_values", True)

    inference_policy = dict(model_contract.inference_policy or {})
    inference_laundering_attempt = (
        deterministic_contract.inference_policy.get("policy") == "direct_only"
        and inference_policy.get("policy") == "directly_sourced_inference_allowed"
    )
    if inference_laundering_attempt:
        reasons.append("blocked_inference_laundering_policy")
        inference_policy["policy"] = "direct_only"
    if not inference_laundering_attempt and "policy" not in inference_policy:
        inference_policy = dict(deterministic_contract.inference_policy or {})

    final_posture_policy = dict(model_contract.final_posture_policy or {})
    baseline_posture = deterministic_contract.final_posture_policy or {}
    if deterministic_contract.source_requirements and not final_posture_policy.get(
        "prohibited_upgrades"
    ):
        final_posture_policy["prohibited_upgrades"] = baseline_posture.get(
            "prohibited_upgrades",
            (),
        )
        reasons.append("restored_prohibited_upgrades")
    if deterministic_contract.source_requirements and not final_posture_policy.get(
        "mandatory_caveats"
    ):
        final_posture_policy["mandatory_caveats"] = baseline_posture.get(
            "mandatory_caveats",
            (),
        )
        reasons.append("restored_mandatory_caveats")

    status = (
        ContractSynthesisStatus.REPAIRED
        if reasons
        else ContractSynthesisStatus.VALID
    )
    mode = (
        ContractSynthesisMode.SMART_MODEL_ADAPTED
        if not reasons
        else ContractSynthesisMode.SMART_MODEL_ADAPTED
    )
    contract_id = model_contract.contract_id
    if not contract_id.startswith("run-contract-"):
        contract_id = "run-contract-" + stable_hash(
            {
                "model_contract_id": model_contract.contract_id,
                "baseline": deterministic_contract.contract_id,
            }
        )[:16]
    committed = replace(
        model_contract,
        contract_id=contract_id,
        synthesis_mode=mode,
        selected_template_ids=deterministic_contract.selected_template_ids,
        user_query_ref=deterministic_contract.user_query_ref,
        selected_depth=deterministic_contract.selected_depth,
        route_facts_used=deterministic_contract.route_facts_used,
        source_requirements=_dedupe_requirements(repaired_requirements),
        numeric_policy=numeric_policy,
        inference_policy=inference_policy,
        final_posture_policy=final_posture_policy,
    )
    return (
        committed,
        RunContractValidationResult(
            status=status,
            reasons=tuple(reasons),
            repaired=bool(reasons),
            fallback_used=False,
            deterministic_template_ids=deterministic_contract.selected_template_ids,
            model_attempted=model_attempted,
            prompt_hash=prompt_hash,
            prompt_length=prompt_length,
            provider=provider,
            model=model,
            effort=effort,
            use_reasoning=use_reasoning,
        ),
    )


__all__ = ["validate_or_fallback_contract"]
