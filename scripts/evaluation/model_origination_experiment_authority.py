"""Experiment identity and calibrated prompt-attribution authority."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from math import isfinite
from statistics import fmean
from typing import Any, Mapping, Sequence

EXPERIMENT_AUTHORITY_SCHEMA_VERSION = "model_origination_experiment_authority_v1"
ATTRIBUTION_STATUSES = frozenset(
    {
        "CAUSAL_SUPPORT_ESTABLISHED",
        "ASSOCIATION_ONLY",
        "NO_EFFECT_ESTABLISHED",
        "CONFOUNDED",
        "INSUFFICIENT_EVIDENCE",
        "REVIEW_REQUIRED",
    }
)
DESIGN_KINDS = frozenset({"SINGLE_PAIR", "DETERMINISTIC_REPLAY", "RANDOMIZED_REPEATED"})


class ExperimentAuthorityError(ValueError):
    """Raised when experiment identity or evidence is internally invalid."""


def _digest(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(rendered.encode("utf-8")).hexdigest()


def _require_digest(value: str, label: str) -> str:
    normalized = str(value or "")
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ExperimentAuthorityError(f"{label} must be one SHA-256 digest")
    return normalized


@dataclass(frozen=True, slots=True)
class PromptIdentity:
    semantic_input_digest: str
    system_prompt_digest: str
    instruction_digest: str
    full_prompt_digest: str

    def __post_init__(self) -> None:
        for label, value in asdict(self).items():
            _require_digest(value, label)


@dataclass(frozen=True, slots=True)
class ExperimentIdentity:
    experiment_id: str
    repository_sha: str
    scenario_id: str
    semantic_input_digest: str
    system_prompt_digest: str
    provider: str
    model: str
    reasoning_effort: str
    output_envelope: str
    product_boundary_version: str
    mechanical_validator_version: str
    semantic_judge_contract_version: str
    authority_policy: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", self.repository_sha):
            raise ExperimentAuthorityError("repository_sha must be one lowercase Git object ID")
        _require_digest(self.semantic_input_digest, "semantic_input_digest")
        _require_digest(self.system_prompt_digest, "system_prompt_digest")
        if self.experiment_id != f"experiment:{_digest(_experiment_material(self))}":
            raise ExperimentAuthorityError(
                "experiment_id does not cover the shared experiment conditions"
            )
        for label in (
            "scenario_id",
            "provider",
            "model",
            "reasoning_effort",
            "output_envelope",
            "product_boundary_version",
            "mechanical_validator_version",
            "semantic_judge_contract_version",
            "authority_policy",
        ):
            if not str(getattr(self, label) or "").strip():
                raise ExperimentAuthorityError(f"{label} must be explicit")


@dataclass(frozen=True, slots=True)
class ExecutionIdentity:
    """Compatibility command identity now owned by experiment authority."""

    repository_sha: str
    evaluation_pass: str
    execution_mode: str
    reasoning_effort: str
    selected_model_roles: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    live_addendum_path: str
    transport_factory_spec: str
    output_packet_path: str
    canonical_argv: tuple[str, ...] = field(repr=False)
    canonical_operator_command: str
    canonical_operator_command_digest: str
    execution_identity_digest: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", self.repository_sha):
            raise ExperimentAuthorityError(
                "execution repository_sha must be one lowercase Git object ID"
            )
        for label in (
            "canonical_operator_command_digest",
            "execution_identity_digest",
        ):
            _require_digest(getattr(self, label), label)
        if (
            self.canonical_operator_command_digest
            != sha256(
                self.canonical_operator_command.encode("utf-8")
            ).hexdigest()
        ):
            raise ExperimentAuthorityError(
                "canonical command digest does not cover the command"
            )
        if self.execution_identity_digest != _digest(
            {
                "repository_sha": self.repository_sha,
                "evaluation_pass": self.evaluation_pass,
                "execution_mode": self.execution_mode,
                "reasoning_effort": self.reasoning_effort,
                "selected_model_roles": self.selected_model_roles,
                "scenario_ids": self.scenario_ids,
                "live_addendum_path": self.live_addendum_path,
                "transport_factory_spec": self.transport_factory_spec,
                "output_packet_path": self.output_packet_path,
                "canonical_operator_command_digest": (
                    self.canonical_operator_command_digest
                ),
            }
        ):
            raise ExperimentAuthorityError(
                "execution identity digest does not cover the command identity"
            )


@dataclass(frozen=True, slots=True)
class ExperimentCallIdentity:
    call_id: str
    experiment: ExperimentIdentity
    instruction_variant: str
    prompt_identity: PromptIdentity
    execution_command_digest: str
    authorization_packet_digest: str
    result_packet_digest: str
    execution_identity_digest: str

    def __post_init__(self) -> None:
        if not str(self.call_id or "").strip():
            raise ExperimentAuthorityError("call_id must be explicit")
        if not str(self.instruction_variant or "").strip():
            raise ExperimentAuthorityError("instruction_variant must be explicit")
        for label in (
            "execution_command_digest",
            "authorization_packet_digest",
            "result_packet_digest",
            "execution_identity_digest",
        ):
            _require_digest(getattr(self, label), label)
        if self.prompt_identity.semantic_input_digest != self.experiment.semantic_input_digest:
            raise ExperimentAuthorityError("call semantic input differs from experiment identity")
        if self.prompt_identity.system_prompt_digest != self.experiment.system_prompt_digest:
            raise ExperimentAuthorityError("call system prompt differs from experiment identity")
        if self.execution_identity_digest != _digest(
            {
                "call_id": self.call_id,
                "experiment_id": self.experiment.experiment_id,
                "instruction_variant": self.instruction_variant,
                "prompt_identity": asdict(self.prompt_identity),
                "execution_command_digest": self.execution_command_digest,
                "authorization_packet_digest": (
                    self.authorization_packet_digest
                ),
                "result_packet_digest": self.result_packet_digest,
            }
        ):
            raise ExperimentAuthorityError(
                "call execution identity does not cover the per-call evidence"
            )


@dataclass(frozen=True, slots=True)
class TrialObservation:
    call_identity: ExperimentCallIdentity
    product_status: str
    mechanical_status: str
    semantic_status: str
    outcome_value: float
    complete: bool = True

    def __post_init__(self) -> None:
        if self.product_status not in {
            "PASS",
            "FAIL",
            "NOT_REACHED",
            "REVIEW_REQUIRED",
        }:
            raise ExperimentAuthorityError(
                "trial product status is unsupported"
            )
        if self.mechanical_status not in {
            "PASS",
            "FAIL",
            "NOT_REACHED",
            "REVIEW_REQUIRED",
        }:
            raise ExperimentAuthorityError(
                "trial mechanical status is unsupported"
            )
        if self.semantic_status not in {
            "MET",
            "NOT_MET",
            "REVIEW_REQUIRED",
            "NOT_RUN",
        }:
            raise ExperimentAuthorityError(
                "trial semantic status is unsupported"
            )
        if not isfinite(float(self.outcome_value)):
            raise ExperimentAuthorityError(
                "trial outcome must be finite"
            )


@dataclass(frozen=True, slots=True)
class ExperimentDesign:
    design_kind: str
    stochastic: bool
    preregistered: bool
    required_observations_per_variant: int
    sampling_policy: str | None = None
    outcome_metric: str | None = None
    decision_statistic: str | None = None
    uncertainty_method: str | None = None
    confidence_multiplier: float | None = None
    error_threshold: float | None = None
    randomized_order: bool = False
    blinded_judging: bool = False
    replication_verified: bool = False
    unplanned_exclusions: int = 0

    def __post_init__(self) -> None:
        if self.design_kind not in DESIGN_KINDS:
            raise ExperimentAuthorityError("design_kind is unsupported")
        if self.required_observations_per_variant <= 0:
            raise ExperimentAuthorityError("required observations must be positive")
        if self.unplanned_exclusions < 0:
            raise ExperimentAuthorityError("unplanned exclusions cannot be negative")
        if self.outcome_metric is not None and not str(
            self.outcome_metric
        ).strip():
            raise ExperimentAuthorityError(
                "outcome_metric must be explicit when supplied"
            )
        if self.error_threshold is not None and (
            not isfinite(float(self.error_threshold))
            or self.error_threshold < 0
        ):
            raise ExperimentAuthorityError(
                "error_threshold must be finite and nonnegative"
            )
        if self.confidence_multiplier is not None and (
            not isfinite(float(self.confidence_multiplier))
            or self.confidence_multiplier <= 0
        ):
            raise ExperimentAuthorityError(
                "confidence_multiplier must be finite and positive"
            )


@dataclass(frozen=True, slots=True)
class AttributionResult:
    schema_version: str
    owner: str
    status: str
    design_kind: str
    design_digest: str
    experiment_ids: tuple[str, ...]
    control_call_ids: tuple[str, ...]
    variant_call_ids: tuple[str, ...]
    compared_instruction_variants: tuple[str, ...]
    observed_effect: float | None
    uncertainty_bound: float | None
    bounded_reasons: tuple[str, ...]
    causal_language_allowed: bool
    real_prompt_effect_proved: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != EXPERIMENT_AUTHORITY_SCHEMA_VERSION:
            raise ExperimentAuthorityError("attribution schema version is unsupported")
        if self.owner != "ModelOriginationExperimentAuthority":
            raise ExperimentAuthorityError("attribution result owner is invalid")
        if self.status not in ATTRIBUTION_STATUSES:
            raise ExperimentAuthorityError("attribution status is unsupported")
        if self.design_kind not in DESIGN_KINDS:
            raise ExperimentAuthorityError("attribution design kind is unsupported")
        _require_digest(self.design_digest, "design_digest")
        if self.observed_effect is not None and not isfinite(
            float(self.observed_effect)
        ):
            raise ExperimentAuthorityError(
                "attribution effect must be finite"
            )
        if self.uncertainty_bound is not None and (
            not isfinite(float(self.uncertainty_bound))
            or self.uncertainty_bound < 0
        ):
            raise ExperimentAuthorityError(
                "attribution uncertainty bound must be finite and nonnegative"
            )
        if self.status in {
            "CAUSAL_SUPPORT_ESTABLISHED",
            "ASSOCIATION_ONLY",
            "NO_EFFECT_ESTABLISHED",
        } and self.observed_effect is None:
            raise ExperimentAuthorityError(
                "effect-bearing attribution status requires an observed effect"
            )
        if self.causal_language_allowed != (
            self.status == "CAUSAL_SUPPORT_ESTABLISHED"
        ):
            raise ExperimentAuthorityError("causal language must follow attribution status")
        if self.causal_language_allowed and self.uncertainty_bound is None:
            raise ExperimentAuthorityError(
                "causal support requires an explicit uncertainty bound"
            )
        if self.causal_language_allowed and (
            len(self.experiment_ids) != 1
            or not self.control_call_ids
            or not self.variant_call_ids
        ):
            raise ExperimentAuthorityError(
                "causal support requires one experiment and both trial arms"
            )
        if self.real_prompt_effect_proved:
            raise ExperimentAuthorityError("offline synthetic evidence cannot prove a real prompt effect")
        if any(not str(reason or "").strip() or len(reason) > 240 for reason in self.bounded_reasons):
            raise ExperimentAuthorityError("attribution reasons must be explicit and bounded")

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


def build_experiment_identity(
    *,
    repository_sha: str,
    scenario_id: str,
    semantic_input_digest: str,
    system_prompt_digest: str,
    provider: str,
    model: str,
    reasoning_effort: str,
    output_envelope: str,
    product_boundary_version: str,
    mechanical_validator_version: str,
    semantic_judge_contract_version: str,
    authority_policy: str,
) -> ExperimentIdentity:
    material = {
        "repository_sha": repository_sha,
        "scenario_id": scenario_id,
        "semantic_input_digest": semantic_input_digest,
        "system_prompt_digest": system_prompt_digest,
        "provider": provider,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "output_envelope": output_envelope,
        "product_boundary_version": product_boundary_version,
        "mechanical_validator_version": mechanical_validator_version,
        "semantic_judge_contract_version": semantic_judge_contract_version,
        "authority_policy": authority_policy,
    }
    return ExperimentIdentity(
        experiment_id=f"experiment:{_digest(material)}",
        **material,
    )


def _experiment_material(
    identity: ExperimentIdentity,
) -> dict[str, Any]:
    return {
        "repository_sha": identity.repository_sha,
        "scenario_id": identity.scenario_id,
        "semantic_input_digest": identity.semantic_input_digest,
        "system_prompt_digest": identity.system_prompt_digest,
        "provider": identity.provider,
        "model": identity.model,
        "reasoning_effort": identity.reasoning_effort,
        "output_envelope": identity.output_envelope,
        "product_boundary_version": identity.product_boundary_version,
        "mechanical_validator_version": (
            identity.mechanical_validator_version
        ),
        "semantic_judge_contract_version": (
            identity.semantic_judge_contract_version
        ),
        "authority_policy": identity.authority_policy,
    }


def build_call_identity(
    *,
    call_id: str,
    experiment: ExperimentIdentity,
    instruction_variant: str,
    prompt_identity: PromptIdentity,
    execution_command: Mapping[str, Any],
    authorization_packet: Mapping[str, Any],
    result_packet: Mapping[str, Any],
) -> ExperimentCallIdentity:
    material = {
        "call_id": call_id,
        "experiment_id": experiment.experiment_id,
        "instruction_variant": instruction_variant,
        "prompt_identity": asdict(prompt_identity),
        "execution_command_digest": _digest(execution_command),
        "authorization_packet_digest": _digest(authorization_packet),
        "result_packet_digest": _digest(result_packet),
    }
    return ExperimentCallIdentity(
        call_id=call_id,
        experiment=experiment,
        instruction_variant=instruction_variant,
        prompt_identity=prompt_identity,
        execution_command_digest=material["execution_command_digest"],
        authorization_packet_digest=material["authorization_packet_digest"],
        result_packet_digest=material["result_packet_digest"],
        execution_identity_digest=_digest(material),
    )


def attribute_prompt_comparison(
    *,
    control: Sequence[TrialObservation],
    variant: Sequence[TrialObservation],
    design: ExperimentDesign,
) -> AttributionResult:
    """Return the strongest conclusion permitted by the supplied evidence."""

    controls = tuple(control)
    variants = tuple(variant)
    all_trials = controls + variants
    base = {
        "schema_version": EXPERIMENT_AUTHORITY_SCHEMA_VERSION,
        "owner": "ModelOriginationExperimentAuthority",
        "design_kind": design.design_kind,
        "design_digest": _digest(asdict(design)),
        "experiment_ids": tuple(sorted({item.call_identity.experiment.experiment_id for item in all_trials})),
        "control_call_ids": tuple(item.call_identity.call_id for item in controls),
        "variant_call_ids": tuple(item.call_identity.call_id for item in variants),
        "compared_instruction_variants": tuple(sorted({item.call_identity.instruction_variant for item in all_trials})),
    }
    if not controls or not variants:
        return _result(
            base,
            "INSUFFICIENT_EVIDENCE",
            None,
            "Both control and variant observations are required.",
        )
    call_ids = [item.call_identity.call_id for item in all_trials]
    execution_ids = [item.call_identity.execution_identity_digest for item in all_trials]
    if len(call_ids) != len(set(call_ids)) or len(execution_ids) != len(set(execution_ids)):
        return _result(
            base,
            "CONFOUNDED",
            None,
            "Independent calls must retain distinct call and execution identities.",
        )
    experiment_ids = {item.call_identity.experiment.experiment_id for item in all_trials}
    if len(experiment_ids) != 1:
        return _result(
            base,
            "CONFOUNDED",
            None,
            "Semantic input, system prompt, route, effort, envelope, or authority policy differs.",
        )
    control_labels = {
        item.call_identity.instruction_variant for item in controls
    }
    variant_labels = {
        item.call_identity.instruction_variant for item in variants
    }
    if (
        len(control_labels) != 1
        or len(variant_labels) != 1
        or control_labels == variant_labels
    ):
        return _result(
            base,
            "CONFOUNDED",
            None,
            "Control and variant require distinct stable predeclared labels.",
        )
    control_full = {item.call_identity.prompt_identity.full_prompt_digest for item in controls}
    variant_full = {item.call_identity.prompt_identity.full_prompt_digest for item in variants}
    if len(control_full) != 1 or len(variant_full) != 1:
        return _result(
            base,
            "CONFOUNDED",
            None,
            "Within-variant full-prompt identity is not stable.",
        )
    if control_full == variant_full:
        if design.stochastic:
            return _result(
                base,
                "CONFOUNDED",
                None,
                "Stochastic comparison labels resolve to the same full prompt.",
            )
        return _result(
            base,
            "NO_EFFECT_ESTABLISHED",
            0.0,
            "Control and variant labels identify the same full prompt.",
        )
    control_instructions = {item.call_identity.prompt_identity.instruction_digest for item in controls}
    variant_instructions = {item.call_identity.prompt_identity.instruction_digest for item in variants}
    if len(control_instructions) != 1 or len(variant_instructions) != 1 or control_instructions == variant_instructions:
        return _result(
            base,
            "CONFOUNDED",
            None,
            "Exactly one stable predeclared instruction variant was not observed.",
        )
    if any(
        not item.complete
        or item.product_status != "PASS"
        or item.mechanical_status != "PASS"
        or item.semantic_status not in {"MET", "NOT_MET", "REVIEW_REQUIRED"}
        for item in all_trials
    ):
        return _result(
            base,
            "INSUFFICIENT_EVIDENCE",
            None,
            "Every trial needs complete product, mechanical, and semantic owner results.",
        )
    if any(
        item.semantic_status == "REVIEW_REQUIRED"
        for item in all_trials
    ):
        return _result(
            base,
            "REVIEW_REQUIRED",
            None,
            "Semantic ambiguity in either trial arm blocks attribution.",
        )
    observed_effect = fmean(item.outcome_value for item in variants) - fmean(item.outcome_value for item in controls)
    if design.unplanned_exclusions:
        return _result(
            base,
            "CONFOUNDED",
            observed_effect,
            "The design contains unplanned exclusions.",
        )
    if (
        len(controls) < design.required_observations_per_variant
        or len(variants) < design.required_observations_per_variant
    ):
        return _result(
            base,
            "INSUFFICIENT_EVIDENCE",
            observed_effect,
            "The predeclared replication count was not reached.",
        )
    if len(controls) == 1 and len(variants) == 1 and design.stochastic:
        return _result(
            base,
            "ASSOCIATION_ONLY",
            observed_effect,
            "One independent stochastic pair supports association only.",
        )
    if design.design_kind == "DETERMINISTIC_REPLAY":
        design_complete = (
            not design.stochastic
            and design.preregistered
            and design.replication_verified
            and bool(design.outcome_metric)
            and design.decision_statistic == "difference_in_means"
            and design.error_threshold is not None
            and design.required_observations_per_variant >= 2
        )
    elif design.design_kind == "RANDOMIZED_REPEATED":
        design_complete = (
            design.stochastic
            and design.preregistered
            and bool(design.sampling_policy)
            and bool(design.outcome_metric)
            and design.decision_statistic == "difference_in_means"
            and design.uncertainty_method
            == "standard_error_of_mean_difference"
            and design.confidence_multiplier is not None
            and design.error_threshold is not None
            and design.randomized_order
            and design.blinded_judging
            and design.required_observations_per_variant >= 2
        )
    else:
        design_complete = False
    if not design_complete:
        return _result(
            base,
            "INSUFFICIENT_EVIDENCE",
            observed_effect,
            "Replication or preregistered randomized-design authority is incomplete.",
        )
    if design.stochastic:
        return _result(
            base,
            "ASSOCIATION_ONLY",
            observed_effect,
            (
                f"Complete stochastic comparison observed {len(controls)} "
                f"control and {len(variants)} variant outcomes; stochastic "
                "causal inference is not installed or licensed."
            ),
        )
    control_values = {
        float(item.outcome_value) for item in controls
    }
    variant_values = {
        float(item.outcome_value) for item in variants
    }
    if len(control_values) != 1 or len(variant_values) != 1:
        return _result(
            base,
            "INSUFFICIENT_EVIDENCE",
            observed_effect,
            "Deterministic replay did not reproduce stable arm outcomes.",
        )
    uncertainty_bound = 0.0
    threshold = float(design.error_threshold or 0.0)
    if abs(observed_effect) <= threshold + uncertainty_bound:
        return _result(
            base,
            "NO_EFFECT_ESTABLISHED",
            observed_effect,
            "The predeclared effect did not exceed the no-effect threshold plus uncertainty.",
            uncertainty_bound=uncertainty_bound,
        )
    return _result(
        base,
        "CAUSAL_SUPPORT_ESTABLISHED",
        observed_effect,
        "The complete synthetic design met its predeclared causal-support rule.",
        uncertainty_bound=uncertainty_bound,
    )


def _result(
    base: Mapping[str, Any],
    status: str,
    effect: float | None,
    *reasons: str,
    uncertainty_bound: float | None = None,
) -> AttributionResult:
    return AttributionResult(
        **dict(base),
        status=status,
        observed_effect=effect,
        uncertainty_bound=uncertainty_bound,
        bounded_reasons=tuple(reason[:240] for reason in reasons),
        causal_language_allowed=(
            status == "CAUSAL_SUPPORT_ESTABLISHED"
        ),
    )


__all__ = [
    "ATTRIBUTION_STATUSES",
    "DESIGN_KINDS",
    "EXPERIMENT_AUTHORITY_SCHEMA_VERSION",
    "AttributionResult",
    "ExecutionIdentity",
    "ExperimentAuthorityError",
    "ExperimentCallIdentity",
    "ExperimentDesign",
    "ExperimentIdentity",
    "PromptIdentity",
    "TrialObservation",
    "attribute_prompt_comparison",
    "build_call_identity",
    "build_experiment_identity",
]
