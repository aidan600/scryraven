"""Phase-focus proof for model-origination experiment attribution.

Proof class: CONTRACT-INVARIANT. Surface guarded: four digest layers,
experiment/call identity, comparability, replication, and calibrated causality.
Closed surface: all evidence is synthetic and offline; no real prompt effect is
claimed. Expected cost: tiny deterministic unit proof.
"""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import pytest

from scripts.evaluation.model_origination_experiment_authority import (
    ExperimentAuthorityError,
    ExperimentDesign,
    PromptIdentity,
    TrialObservation,
    attribute_prompt_comparison,
    build_call_identity,
    build_experiment_identity,
)

REPOSITORY_SHA = "cd7a33731ff501456ba97fcfd15e423fd2676e1f"


def _hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _experiment(**overrides: str):
    values = {
        "repository_sha": REPOSITORY_SHA,
        "scenario_id": "case_03_pure_depth_two",
        "semantic_input_digest": _hex("semantic-input"),
        "system_prompt_digest": _hex("system-prompt"),
        "provider": "synthetic-provider",
        "model": "synthetic-model",
        "reasoning_effort": "fixed",
        "output_envelope": "strict-json-v1",
        "product_boundary_version": "canonical-boundary-v1",
        "mechanical_validator_version": "mechanical-v1",
        "semantic_judge_contract_version": "semantic-v1",
        "authority_policy": "offline-synthetic-only",
    }
    values.update(overrides)
    return build_experiment_identity(**values)


def _trial(
    *,
    call_id: str,
    variant: str,
    experiment=None,
    outcome: float,
    index: int,
    full_prompt_label: str | None = None,
    complete: bool = True,
) -> TrialObservation:
    experiment = experiment or _experiment()
    prompt = PromptIdentity(
        semantic_input_digest=experiment.semantic_input_digest,
        system_prompt_digest=experiment.system_prompt_digest,
        instruction_digest=_hex(f"instruction:{variant}"),
        full_prompt_digest=_hex(full_prompt_label or f"full-prompt:{variant}"),
    )
    identity = build_call_identity(
        call_id=call_id,
        experiment=experiment,
        instruction_variant=variant,
        prompt_identity=prompt,
        execution_command={"call_id": call_id, "index": index},
        authorization_packet={"authorized": True, "call_id": call_id},
        result_packet={"complete": complete, "index": index},
    )
    return TrialObservation(
        call_identity=identity,
        product_status="PASS",
        mechanical_status="PASS",
        semantic_status="MET" if outcome >= 0.5 else "NOT_MET",
        outcome_value=outcome,
        complete=complete,
    )


def _single_pair_design(*, stochastic: bool = True) -> ExperimentDesign:
    return ExperimentDesign(
        design_kind="SINGLE_PAIR",
        stochastic=stochastic,
        preregistered=False,
        required_observations_per_variant=1,
    )


def test_one_independent_stochastic_pair_is_association_only() -> None:
    control = (
        _trial(
            call_id="control:1",
            variant="control",
            outcome=0.0,
            index=1,
        ),
    )
    variant = (
        _trial(
            call_id="variant:1",
            variant="variant",
            outcome=1.0,
            index=2,
        ),
    )
    result = attribute_prompt_comparison(
        control=control,
        variant=variant,
        design=_single_pair_design(),
    )
    assert result.status == "ASSOCIATION_ONLY"
    assert result.causal_language_allowed is False
    assert result.real_prompt_effect_proved is False
    excluded = attribute_prompt_comparison(
        control=control,
        variant=variant,
        design=replace(
            _single_pair_design(),
            unplanned_exclusions=1,
        ),
    )
    assert excluded.status == "CONFOUNDED"


def test_semantic_review_required_blocks_attribution() -> None:
    control = _trial(
        call_id="control:review",
        variant="control",
        outcome=0.0,
        index=1,
    )
    variant = replace(
        _trial(
            call_id="variant:review",
            variant="variant",
            outcome=1.0,
            index=2,
        ),
        semantic_status="REVIEW_REQUIRED",
    )
    result = attribute_prompt_comparison(
        control=(control,),
        variant=(variant,),
        design=_single_pair_design(),
    )
    assert result.status == "REVIEW_REQUIRED"
    assert result.observed_effect is None
    assert result.causal_language_allowed is False


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("semantic_input_digest", _hex("different-input")),
        ("system_prompt_digest", _hex("different-system-prompt")),
        ("provider", "different-provider"),
        ("model", "different-model"),
        ("reasoning_effort", "different-effort"),
        ("output_envelope", "different-envelope"),
    ),
)
def test_mismatched_invariant_is_confounded(
    field: str,
    value: str,
) -> None:
    control_experiment = _experiment()
    variant_experiment = _experiment(**{field: value})
    result = attribute_prompt_comparison(
        control=(
            _trial(
                call_id="control:1",
                variant="control",
                experiment=control_experiment,
                outcome=0.0,
                index=1,
            ),
        ),
        variant=(
            _trial(
                call_id="variant:1",
                variant="variant",
                experiment=variant_experiment,
                outcome=1.0,
                index=2,
            ),
        ),
        design=_single_pair_design(),
    )
    assert result.status == "CONFOUNDED"
    assert result.causal_language_allowed is False


def test_missing_replication_is_insufficient_evidence() -> None:
    design = ExperimentDesign(
        design_kind="DETERMINISTIC_REPLAY",
        stochastic=False,
        preregistered=True,
        required_observations_per_variant=2,
        outcome_metric="bounded_semantic_outcome",
        decision_statistic="difference_in_means",
        error_threshold=0.1,
        replication_verified=True,
    )
    result = attribute_prompt_comparison(
        control=(
            _trial(
                call_id="control:1",
                variant="control",
                outcome=0.0,
                index=1,
            ),
        ),
        variant=(
            _trial(
                call_id="variant:1",
                variant="variant",
                outcome=1.0,
                index=2,
            ),
        ),
        design=design,
    )
    assert result.status == "INSUFFICIENT_EVIDENCE"


def test_identical_full_prompts_mislabeled_as_variants_establish_no_effect() -> None:
    result = attribute_prompt_comparison(
        control=(
            _trial(
                call_id="control:1",
                variant="control",
                outcome=0.0,
                index=1,
                full_prompt_label="same-full-prompt",
            ),
        ),
        variant=(
            _trial(
                call_id="variant:1",
                variant="variant",
                outcome=1.0,
                index=2,
                full_prompt_label="same-full-prompt",
            ),
        ),
        design=_single_pair_design(),
    )
    assert result.status == "NO_EFFECT_ESTABLISHED"
    assert result.observed_effect == 0.0


def test_shared_execution_identity_is_rejected_before_attribution() -> None:
    control = _trial(
        call_id="control:1",
        variant="control",
        outcome=0.0,
        index=1,
    )
    variant = _trial(
        call_id="variant:1",
        variant="variant",
        outcome=1.0,
        index=2,
    )
    with pytest.raises(
        ExperimentAuthorityError,
        match="per-call evidence",
    ):
        replace(
            variant.call_identity,
            execution_identity_digest=(
                control.call_identity.execution_identity_digest
            ),
        )


def test_complete_deterministic_replication_permits_only_synthetic_causal_support() -> None:
    control = tuple(
        _trial(
            call_id=f"control:{index}",
            variant="control",
            outcome=0.0,
            index=index,
        )
        for index in (1, 2)
    )
    variant = tuple(
        _trial(
            call_id=f"variant:{index}",
            variant="variant",
            outcome=1.0,
            index=index + 2,
        )
        for index in (1, 2)
    )
    design = ExperimentDesign(
        design_kind="DETERMINISTIC_REPLAY",
        stochastic=False,
        preregistered=True,
        required_observations_per_variant=2,
        outcome_metric="bounded_semantic_outcome",
        decision_statistic="difference_in_means",
        error_threshold=0.1,
        replication_verified=True,
    )
    result = attribute_prompt_comparison(
        control=control,
        variant=variant,
        design=design,
    )
    assert result.status == "CAUSAL_SUPPORT_ESTABLISHED"
    assert result.causal_language_allowed is True
    assert result.real_prompt_effect_proved is False


def test_deterministic_replay_requires_stable_arm_replication() -> None:
    design = ExperimentDesign(
        design_kind="DETERMINISTIC_REPLAY",
        stochastic=False,
        preregistered=True,
        required_observations_per_variant=2,
        outcome_metric="bounded_semantic_outcome",
        decision_statistic="difference_in_means",
        error_threshold=0.1,
        replication_verified=True,
    )
    result = attribute_prompt_comparison(
        control=(
            _trial(
                call_id="control:stable:1",
                variant="control",
                outcome=0.0,
                index=1,
            ),
            _trial(
                call_id="control:unstable:2",
                variant="control",
                outcome=0.1,
                index=2,
            ),
        ),
        variant=(
            _trial(
                call_id="variant:stable:1",
                variant="variant",
                outcome=1.0,
                index=3,
            ),
            _trial(
                call_id="variant:stable:2",
                variant="variant",
                outcome=1.0,
                index=4,
            ),
        ),
        design=design,
    )
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.uncertainty_bound is None


def test_complete_preregistered_randomized_design_can_support_synthetic_causality() -> None:
    control = tuple(
        _trial(
            call_id=f"control:{index}",
            variant="control",
            outcome=0.0,
            index=index,
        )
        for index in (1, 2, 3)
    )
    variant = tuple(
        _trial(
            call_id=f"variant:{index}",
            variant="variant",
            outcome=1.0,
            index=index + 3,
        )
        for index in (1, 2, 3)
    )
    design = ExperimentDesign(
        design_kind="RANDOMIZED_REPEATED",
        stochastic=True,
        preregistered=True,
        required_observations_per_variant=3,
        sampling_policy="blocked randomized order with fixed sample size",
        outcome_metric="bounded_semantic_outcome",
        decision_statistic="difference_in_means",
        uncertainty_method="standard_error_of_mean_difference",
        confidence_multiplier=2.0,
        error_threshold=0.2,
        randomized_order=True,
        blinded_judging=True,
    )
    result = attribute_prompt_comparison(
        control=control,
        variant=variant,
        design=design,
    )
    assert result.status == "CAUSAL_SUPPORT_ESTABLISHED"
    assert result.causal_language_allowed is True
    assert result.uncertainty_bound == 0.0
    assert result.real_prompt_effect_proved is False


def test_unplanned_exclusion_confounds_replicated_design() -> None:
    design = ExperimentDesign(
        design_kind="DETERMINISTIC_REPLAY",
        stochastic=False,
        preregistered=True,
        required_observations_per_variant=2,
        outcome_metric="bounded_semantic_outcome",
        decision_statistic="difference_in_means",
        error_threshold=0.1,
        replication_verified=True,
        unplanned_exclusions=1,
    )
    result = attribute_prompt_comparison(
        control=tuple(
            _trial(
                call_id=f"control:{index}",
                variant="control",
                outcome=0.0,
                index=index,
            )
            for index in (1, 2)
        ),
        variant=tuple(
            _trial(
                call_id=f"variant:{index}",
                variant="variant",
                outcome=1.0,
                index=index + 2,
            )
            for index in (1, 2)
        ),
        design=design,
    )
    assert result.status == "CONFOUNDED"


def test_complete_design_below_threshold_establishes_no_effect() -> None:
    design = ExperimentDesign(
        design_kind="DETERMINISTIC_REPLAY",
        stochastic=False,
        preregistered=True,
        required_observations_per_variant=2,
        outcome_metric="bounded_semantic_outcome",
        decision_statistic="difference_in_means",
        error_threshold=0.2,
        replication_verified=True,
    )
    result = attribute_prompt_comparison(
        control=tuple(
            _trial(
                call_id=f"control:{index}",
                variant="control",
                outcome=0.5,
                index=index,
            )
            for index in (1, 2)
        ),
        variant=tuple(
            _trial(
                call_id=f"variant:{index}",
                variant="variant",
                outcome=0.6,
                index=index + 2,
            )
            for index in (1, 2)
        ),
        design=design,
    )
    assert result.status == "NO_EFFECT_ESTABLISHED"
    assert result.causal_language_allowed is False


def test_call_identity_preserves_four_distinct_prompt_digest_layers() -> None:
    trial = _trial(
        call_id="control:identity",
        variant="control",
        outcome=1.0,
        index=1,
    )
    prompt = trial.call_identity.prompt_identity
    assert (
        len(
            {
                prompt.semantic_input_digest,
                prompt.system_prompt_digest,
                prompt.instruction_digest,
                prompt.full_prompt_digest,
            }
        )
        == 4
    )
    assert trial.call_identity.call_id == "control:identity"
    assert trial.call_identity.execution_identity_digest


def test_nonfinite_outcome_and_threshold_are_rejected() -> None:
    with pytest.raises(
        ExperimentAuthorityError,
        match="outcome must be finite",
    ):
        _trial(
            call_id="control:nan",
            variant="control",
            outcome=float("nan"),
            index=1,
        )
    with pytest.raises(
        ExperimentAuthorityError,
        match="finite and nonnegative",
    ):
        ExperimentDesign(
            design_kind="RANDOMIZED_REPEATED",
            stochastic=True,
            preregistered=True,
            required_observations_per_variant=2,
            error_threshold=-0.1,
        )


def test_unblinded_randomized_design_cannot_establish_causality() -> None:
    control = tuple(
        _trial(
            call_id=f"control:unblinded:{index}",
            variant="control",
            outcome=0.0,
            index=index,
        )
        for index in (1, 2)
    )
    variant = tuple(
        _trial(
            call_id=f"variant:unblinded:{index}",
            variant="variant",
            outcome=1.0,
            index=index + 2,
        )
        for index in (1, 2)
    )
    result = attribute_prompt_comparison(
        control=control,
        variant=variant,
        design=ExperimentDesign(
            design_kind="RANDOMIZED_REPEATED",
            stochastic=True,
            preregistered=True,
            required_observations_per_variant=2,
            sampling_policy="fixed blocked randomization",
            outcome_metric="bounded_semantic_outcome",
            decision_statistic="difference_in_means",
            uncertainty_method="standard_error_of_mean_difference",
            confidence_multiplier=2.0,
            error_threshold=0.1,
            randomized_order=True,
            blinded_judging=False,
        ),
    )
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.causal_language_allowed is False


def test_randomized_uncertainty_bound_blocks_weak_effect() -> None:
    result = attribute_prompt_comparison(
        control=tuple(
            _trial(
                call_id=f"control:uncertainty:{index}",
                variant="control",
                outcome=outcome,
                index=index,
            )
            for index, outcome in enumerate((0.0, 1.0), start=1)
        ),
        variant=tuple(
            _trial(
                call_id=f"variant:uncertainty:{index}",
                variant="variant",
                outcome=outcome,
                index=index + 2,
            )
            for index, outcome in enumerate((1.0, 2.0), start=1)
        ),
        design=ExperimentDesign(
            design_kind="RANDOMIZED_REPEATED",
            stochastic=True,
            preregistered=True,
            required_observations_per_variant=2,
            sampling_policy="fixed blocked randomization",
            outcome_metric="bounded_semantic_outcome",
            decision_statistic="difference_in_means",
            uncertainty_method="standard_error_of_mean_difference",
            confidence_multiplier=2.0,
            error_threshold=0.1,
            randomized_order=True,
            blinded_judging=True,
        ),
    )
    assert result.status == "NO_EFFECT_ESTABLISHED"
    assert result.observed_effect == 1.0
    assert result.uncertainty_bound is not None
    assert result.uncertainty_bound > result.observed_effect


def test_experiment_and_call_digests_reject_identity_substitution() -> None:
    experiment = _experiment()
    with pytest.raises(
        ExperimentAuthorityError,
        match="shared experiment conditions",
    ):
        replace(
            experiment,
            experiment_id=f"experiment:{'0' * 64}",
        )
    trial = _trial(
        call_id="control:substitution",
        variant="control",
        outcome=0.0,
        index=1,
    )
    with pytest.raises(
        ExperimentAuthorityError,
        match="per-call evidence",
    ):
        replace(
            trial.call_identity,
            execution_identity_digest="0" * 64,
        )
