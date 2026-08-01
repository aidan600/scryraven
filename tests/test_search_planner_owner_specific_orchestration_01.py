from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from scripts import request_provider_proxy_broker as broker_client
from scripts.evaluation.search_planner_owner_specific_authorization import (
    GENERIC_BROKER_TRANSPORT_FACTORY_SPEC,
    SEMANTIC_CALL_ID_PATTERN,
    OwnerSpecificAuthorizationError,
    OwnerSpecificLiveAuthorization,
    TrialScheduleEntry,
    build_canonical_policy_packet,
    canonical_sha256,
    validate_semantic_call_id,
)
from scripts.evaluation.search_planner_owner_specific_orchestration import (
    OwnerSpecificOrchestrationError,
    build_plan_only_packet,
    execute_owner_specific_evaluation,
)
from tests.helpers.search_planner_owner_specific_fakes import (
    OPAQUE_SEMANTIC_CALL_IDS,
    SYNTHETIC_VARIANT_INSTRUCTION,
    FakeOwnerSpecificBrokerFactory,
    authorization_bundle,
)

REPOSITORY_SHA = "".join(
    ("3a76a3a2", "4efef5ee", "4bec2d43", "e301463b", "671f0d80")
)


def _nested_mapping_keys(value) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(value)
        for nested in value.values():
            keys.update(_nested_mapping_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(_nested_mapping_keys(nested))
    return keys


def _retention_flag_values(value) -> list[bool]:
    flags: list[bool] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.endswith("_retained"):
                flags.append(nested)
            flags.extend(_retention_flag_values(nested))
    elif isinstance(value, list):
        for nested in value:
            flags.extend(_retention_flag_values(nested))
    return flags


def _execute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    factory: FakeOwnerSpecificBrokerFactory | None = None,
    required_observations_per_arm: int = 1,
    output_packet_path: str = "output/local/result.json",
):
    authorization, scenario, argv = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
        required_observations_per_arm=required_observations_per_arm,
        output_packet_path=output_packet_path,
    )
    selected_factory = factory or FakeOwnerSpecificBrokerFactory()
    monkeypatch.setenv(
        broker_client.TOKEN_ENV_VAR,
        "synthetic-test-session",
    )
    packet = execute_owner_specific_evaluation(
        authorization=authorization,
        scenario_packet=scenario,
        repository_sha=REPOSITORY_SHA,
        live_addendum_path=(
            authorization.evaluation_identity.live_addendum_path
        ),
        scenario_packet_path=(
            authorization.evaluation_identity.scenario_packet_path
        ),
        output_packet_path=output_packet_path,
        actual_argv=argv,
        repository_root=tmp_path,
        transport_factory=selected_factory,
    )
    return authorization, scenario, selected_factory, packet


def test_full_fake_schedule_reaches_real_product_and_every_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization, _, factory, packet = _execute(
        tmp_path,
        monkeypatch,
    )

    assert len(factory.factory_routes) == 2
    assert [call["role"] for call in factory.calls] == [
        "search_planner",
        "search_planner_semantic_judge",
        "search_planner_semantic_judge",
        "search_planner",
        "search_planner_semantic_judge",
        "search_planner_semantic_judge",
    ]
    expected_semantic_ids = tuple(
        call_id
        for entry in authorization.prompt_experiment.trial_schedule
        for call_id in (
            entry.primary_judge_call_id,
            entry.adversarial_judge_call_id,
        )
    )
    observed_semantic_ids = tuple(
        call["correlation_id"]
        for call in factory.calls
        if call["role"] == "search_planner_semantic_judge"
    )
    assert observed_semantic_ids == expected_semantic_ids
    assert len(observed_semantic_ids) == 4
    assert len(set(observed_semantic_ids)) == 4
    assert all(
        SEMANTIC_CALL_ID_PATTERN.fullmatch(call_id)
        for call_id in observed_semantic_ids
    )
    assert len(packet["trial_results"]) == 2
    for trial, scheduled in zip(
        packet["trial_results"],
        authorization.prompt_experiment.trial_schedule,
    ):
        assert (
            trial["product_boundary_result"]["boundary_status"]
            == "PASS"
        )
        assert (
            trial["mechanical_validation_result"]["overall_posture"]
            == "PASS"
        )
        semantic = trial["semantic_judgment_result"]
        assert semantic["final_status"] == "MET"
        assert semantic["provider_selected"] is False
        assert semantic["model_selected"] is False
        assert semantic["live_call_count"] == 0
        execution = trial["semantic_execution_observation"]
        assert execution["semantic_judge_call_cap_consumption"] == {
            "primary_calls": 1,
            "adversarial_calls": 1,
            "total_calls": 2,
        }
        assert execution["primary_pass"]["pass_kind"] == "primary"
        assert execution["adversarial_pass"]["pass_kind"] == (
            "adversarial"
        )
        assert execution["primary_pass"]["call_id"] == (
            scheduled.primary_judge_call_id
        )
        assert execution["adversarial_pass"]["call_id"] == (
            scheduled.adversarial_judge_call_id
        )
        assert not {
            "trial_id",
            "trial_order",
            "schedule_index",
            "arm_id",
            "control",
            "variant",
        }.intersection(_nested_mapping_keys(execution))
        passive = trial["passive_evaluation_report"]
        assert passive["semantic_judgment_result"] == semantic
        assert (
            passive["combined_result"]["semantic_status"]
            == semantic["final_status"]
        )
    control, variant = packet["trial_results"]
    assert (
        control["prompt_variant_dispatch_observation"][
            "control_bytes_unchanged"
        ]
        is True
    )
    assert (
        variant["prompt_variant_dispatch_observation"][
            "transformation_posture"
        ]
        == "INSTRUCTION_PREFIX_REPLACED"
    )
    assert (
        control["prompt_variant_dispatch_observation"][
            "dispatched_semantic_input_digest"
        ]
        == variant["prompt_variant_dispatch_observation"][
            "dispatched_semantic_input_digest"
        ]
    )
    assert (
        packet["experiment_attribution_result"]["status"]
        == "ASSOCIATION_ONLY"
    )
    assert packet["causal_language_allowed"] is False
    assert packet["real_prompt_effect_proved"] is False
    assert packet["prompt_quality_winner"] is None
    assert packet["terminal_orchestration_posture"] == "COMPLETED"
    assert packet["budget_and_cap_consumption"][
        "attempted_call_count"
    ] == 6
    assert packet["budget_and_cap_consumption"][
        "unused_authorized_call_ids"
    ] == []
    assert (
        packet["canonical_experiment_policy_packet"]
        == authorization.canonical_policy_packet.to_packet()
    )
    assert packet["authority_policy"] == (
        f"owner-specific-policy:{packet['policy_packet_sha256']}"
    )
    output = tmp_path / "output" / "local" / "result.json"
    assert json.loads(output.read_text(encoding="utf-8")) == packet
    rendered = output.read_text(encoding="utf-8")
    assert SYNTHETIC_VARIANT_INSTRUCTION not in rendered
    assert "synthetic-test-session" not in rendered
    assert _retention_flag_values(packet)
    assert not any(_retention_flag_values(packet))


def test_mechanical_failure_skips_both_judges_and_remains_a_trial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rejected_value = "planner-rejected-private-value-sentinel"
    defaults = FakeOwnerSpecificBrokerFactory().planner_outputs
    rejected_payload = json.loads(defaults[0])
    rejected_payload["answer_components"][0]["partial_answer_policy"] = (
        rejected_value
    )
    rejected_response = json.dumps(rejected_payload)
    rejected_error_argument = (
        f"unsupported partial answer policy: {rejected_value}"
    )
    rejected_error_digest = sha256(
        rejected_error_argument.encode("utf-8")
    ).hexdigest()
    factory = FakeOwnerSpecificBrokerFactory(
        planner_outputs=[rejected_response, defaults[0]],
    )

    authorization, _, factory, packet = _execute(
        tmp_path,
        monkeypatch,
        factory=factory,
    )

    assert [call["role"] for call in factory.calls] == [
        "search_planner",
        "search_planner",
        "search_planner_semantic_judge",
        "search_planner_semantic_judge",
    ]
    failed = packet["trial_results"][0]
    product_failure = failed["product_boundary_result"]
    assert (
        product_failure["schema_version"]
        == "search_planner_product_boundary_observer_v2"
    )
    assert product_failure["boundary_status"] == "FAIL"
    assert product_failure["parser_posture"] == "PASS"
    assert product_failure["validator_posture"] == "FAIL"
    assert product_failure["runtime_projection_posture"] == "NOT_REACHED"
    assert product_failure["raw_prompt_retained"] is False
    assert product_failure["raw_response_retained"] is False
    assert product_failure["raw_provider_payload_retained"] is False
    assert product_failure["canonical_failure_rule_ids"] == ["M02"]
    assert (
        product_failure["canonical_failure_predicate_registry_version"]
        == "search_planner_model_adapter_predicate_registry_v1"
    )
    assert (
        product_failure["canonical_failure_predicate_id"]
        == "ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_ENUM"
    )
    assert product_failure["bounded_failure_reason"] == (
        "SearchPlannerModelAdapterError:"
        "failure_stage=MODEL_OUTPUT_VALIDATION:"
        "failure_code=INVALID_ENUM_OR_BOUNDED_VALUE:"
        "mechanical_rule_id=M02:"
        "predicate_registry_version="
        "search_planner_model_adapter_predicate_registry_v1:"
        "predicate_id=ANSWER_COMPONENT_PARTIAL_ANSWER_POLICY_ENUM:"
        "message_sha256="
        f"{rejected_error_digest}"
    )
    assert (
        failed["mechanical_validation_result"]["overall_posture"]
        == "FAIL"
    )
    mechanical_rules = {
        item["rule_id"]: item
        for item in failed["mechanical_validation_result"]["rule_results"]
    }
    assert mechanical_rules["M02"]["posture"] == "FAIL"
    assert mechanical_rules["M03"]["posture"] == "NOT_REACHED"
    assert failed["semantic_judgment_result"] is None
    assert failed["semantic_execution_observation"] is None
    assert failed["trial_observation"]["semantic_status"] == "NOT_RUN"
    assert failed["trial_observation"]["complete"] is False
    failed_semantic_call_ids = {
        authorization.prompt_experiment.trial_schedule[
            0
        ].primary_judge_call_id,
        authorization.prompt_experiment.trial_schedule[
            0
        ].adversarial_judge_call_id,
    }
    assert not any(
        call["role"] == "search_planner_semantic_judge"
        and call["correlation_id"] in failed_semantic_call_ids
        for call in factory.calls
    )
    serialized_packet = json.dumps(packet, sort_keys=True)
    for forbidden in (
        rejected_value,
        rejected_response,
        rejected_error_argument,
        factory.calls[0]["prompt"],
        factory.calls[0]["system_prompt"],
    ):
        assert forbidden not in serialized_packet
    assert not any(_retention_flag_values(packet))
    assert len(packet["trial_results"]) == 2
    assert (
        packet["experiment_attribution_result"]["status"]
        == "INSUFFICIENT_EVIDENCE"
    )
    assert packet["terminal_orchestration_posture"] == (
        "COMPLETED_WITH_MODEL_FAILURES"
    )
    assert set(
        packet["budget_and_cap_consumption"][
            "unused_authorized_call_ids"
        ]
    ) == {
        authorization.prompt_experiment.trial_schedule[
            0
        ].primary_judge_call_id,
        authorization.prompt_experiment.trial_schedule[
            0
        ].adversarial_judge_call_id,
    }


def test_repeated_stochastic_schedule_cannot_exceed_association(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, factory, packet = _execute(
        tmp_path,
        monkeypatch,
        required_observations_per_arm=2,
    )

    assert len(factory.calls) == 12
    attribution = packet["experiment_attribution_result"]
    assert attribution["status"] == "ASSOCIATION_ONLY"
    assert attribution["causal_language_allowed"] is False
    assert attribution["real_prompt_effect_proved"] is False
    assert packet["prompt_quality_winner"] is None


def test_plan_only_constructs_no_transport_or_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BombEnvironment(dict):
        def get(self, *_args, **_kwargs):
            raise AssertionError("plan_only touched credentials")

    monkeypatch.setattr(
        "scripts.evaluation.search_planner_owner_specific_orchestration.os.environ",
        BombEnvironment(),
    )
    packet = build_plan_only_packet(repository_sha=REPOSITORY_SHA)

    assert packet["execution_mode"] == "plan_only"
    assert set(packet["owner_results"].values()) == {"NOT_RUN"}
    assert packet["call_counts"]["broker_calls"] == 0
    assert packet["transport_created"] is False
    assert packet["credentials_accessed"] is False
    assert packet["raw_material_retained"] is False
    assert packet["call_manifest"]["status"] == (
        "AUTHORIZATION_REQUIRED"
    )
    assert packet["cap_manifest"]["status"] == (
        "AUTHORIZATION_REQUIRED"
    )
    assert (
        packet["future_authorization_requirements"][
            "provider_selected"
        ]
        is False
    )
    assert (
        packet["future_authorization_requirements"]["model_selected"]
        is False
    )


def test_valid_opaque_semantic_call_ids_pass_unchanged() -> None:
    primary, adversarial = OPAQUE_SEMANTIC_CALL_IDS[:2]

    assert validate_semantic_call_id(primary) == primary
    assert validate_semantic_call_id(adversarial) == adversarial
    entry = TrialScheduleEntry(
        trial_id="trial-fixture",
        arm_id="fixture-arm",
        planner_call_id="planner-call-fixture",
        primary_judge_call_id=primary,
        adversarial_judge_call_id=adversarial,
    )
    assert entry.primary_judge_call_id == primary
    assert entry.adversarial_judge_call_id == adversarial


@pytest.mark.parametrize(
    "call_id",
    (
        "primary-call-01",
        "adversarial-call-02",
        "semantic-call-01",
        "trial-01-primary",
        "judge-trial-2",
        OPAQUE_SEMANTIC_CALL_IDS[0] + "-01",
        "control-primary-call",
        "variant-adversarial-call",
        "semantic-call-control-" + ("a" * 64),
        "semantic-call-variant-" + ("a" * 64),
        "primary:" + ("a" * 64),
        "adversarial:" + ("a" * 64),
        "semantic-primary:" + ("a" * 64),
        "semantic-adversarial:" + ("a" * 64),
        "semantic-call:" + ("A" * 64),
        "semantic-call:" + ("a" * 63),
        "semantic-call:" + ("a" * 65),
        "semantic-call:" + ("g" * 64),
        " " + OPAQUE_SEMANTIC_CALL_IDS[0],
        OPAQUE_SEMANTIC_CALL_IDS[0] + " ",
        "semantic-call:",
    ),
)
def test_nonopaque_semantic_call_ids_fail(call_id: str) -> None:
    with pytest.raises(
        OwnerSpecificAuthorizationError,
        match="64 lowercase hex",
    ):
        validate_semantic_call_id(call_id)


@pytest.mark.parametrize(
    "collision_kind",
    (
        "within_trial",
        "between_trials",
        "with_planner",
    ),
)
def test_semantic_call_identity_collisions_fail(
    tmp_path: Path,
    collision_kind: str,
) -> None:
    authorization, _, _ = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )
    packet = deepcopy(authorization.to_packet())
    schedule = packet["prompt_experiment"]["trial_schedule"]
    first_semantic_id = schedule[0]["primary_judge_call_id"]
    if collision_kind == "within_trial":
        schedule[0]["adversarial_judge_call_id"] = first_semantic_id
    elif collision_kind == "between_trials":
        schedule[1]["primary_judge_call_id"] = first_semantic_id
    else:
        schedule[0]["planner_call_id"] = first_semantic_id

    with pytest.raises(
        OwnerSpecificAuthorizationError,
        match="call-identity collision",
    ):
        OwnerSpecificLiveAuthorization.from_mapping(packet)


def test_authorization_opaque_call_ids_round_trip_unchanged(
    tmp_path: Path,
) -> None:
    authorization, _, _ = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )
    serialized = authorization.to_packet()
    reparsed = OwnerSpecificLiveAuthorization.from_mapping(
        deepcopy(serialized)
    )

    assert reparsed.to_packet() == serialized
    original_ids = tuple(
        call_id
        for entry in authorization.prompt_experiment.trial_schedule
        for call_id in (
            entry.primary_judge_call_id,
            entry.adversarial_judge_call_id,
        )
    )
    reparsed_ids = tuple(
        call_id
        for entry in reparsed.prompt_experiment.trial_schedule
        for call_id in (
            entry.primary_judge_call_id,
            entry.adversarial_judge_call_id,
        )
    )
    assert reparsed_ids == original_ids
    assert all(
        SEMANTIC_CALL_ID_PATTERN.fullmatch(call_id)
        for call_id in reparsed_ids
    )


@pytest.mark.parametrize(
    "mutation,match",
    (
        (
            lambda packet: packet.update({"unknown": True}),
            "unknown fields",
        ),
        (
            lambda packet: packet.pop("owner_identities"),
            "missing fields",
        ),
        (
            lambda packet: packet["owner_identities"].update(
                {"orchestrator_version": "wrong"}
            ),
            "owner identity mismatch",
        ),
        (
            lambda packet: packet["planner_route"].update(
                {"retry_cap": 1}
            ),
            "outside its exact bound",
        ),
        (
            lambda packet: packet["evaluation_identity"].update(
                {
                    "transport_factory_spec": (
                        "scripts.evaluation.openai_responses_origination_transport:"
                        "create_openai_responses_transport"
                    )
                }
            ),
            "generic loopback broker",
        ),
        (
            lambda packet: packet["evaluation_identity"].update(
                {"canonical_operator_command_digest": "1" * 64}
            ),
            "command digest does not cover",
        ),
        (
            lambda packet: packet["retention_policy"].update(
                {"retain_raw_outputs": True}
            ),
            "retention flag false",
        ),
        (
            lambda packet: packet["planner_route"].update(
                {"maximum_planner_calls": 99}
            ),
            "exactly match",
        ),
        pytest.param(
            lambda packet: packet["prompt_experiment"][
                "trial_schedule"
            ][0].update(
                {"primary_judge_call_id": "control-primary-call"}
            ),
            "64 lowercase hex",
            id="<lambda>-arm-blind",
        ),
        (
            lambda packet: packet["prompt_experiment"].update(
                {
                    "trial_schedule": list(
                        reversed(
                            packet["prompt_experiment"][
                                "trial_schedule"
                            ]
                        )
                    )
                }
            ),
            "policy packet differs",
        ),
        (
            lambda packet: packet["whole_evaluation_caps"].update(
                {"maximum_total_observed_cost_usd": "99"}
            ),
            "complete maximum budget",
        ),
        (
            lambda packet: packet.update(
                {"authority_policy": f"owner-specific-policy:{'f' * 64}"}
            ),
            "does not bind",
        ),
    ),
)
def test_authorization_mapping_rejects_every_unlicensed_shape(
    tmp_path: Path,
    mutation,
    match: str,
) -> None:
    authorization, _, _ = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )
    packet = deepcopy(authorization.to_packet())
    mutation(packet)

    with pytest.raises(
        (OwnerSpecificAuthorizationError, ValueError),
        match=match,
    ):
        OwnerSpecificLiveAuthorization.from_mapping(packet)


@pytest.mark.parametrize(
    "context_mutation,match",
    (
        ("repository", "repository SHA"),
        ("command", "CLI invocation"),
        ("scenario", "exact scenario"),
        ("scenario_digest", "scenario packet digest"),
        ("output", "path identity"),
    ),
)
def test_context_mismatch_fails_before_transport_factory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    context_mutation: str,
    match: str,
) -> None:
    authorization, scenario, argv = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )
    repository_sha = REPOSITORY_SHA
    actual_argv = argv
    output_packet_path = (
        authorization.evaluation_identity.output_packet_path
    )
    if context_mutation == "repository":
        repository_sha = "1" * 40
    elif context_mutation == "command":
        actual_argv = tuple(reversed(argv))
    elif context_mutation == "scenario":
        scenario = replace(
            scenario,
            scenario_id="another-fictional-scenario",
        )
    elif context_mutation == "scenario_digest":
        authorization = replace(
            authorization,
            scenario_packet_identity=replace(
                authorization.scenario_packet_identity,
                scenario_packet_sha256="1" * 64,
            ),
        )
    else:
        output_packet_path = "output/local/another-result.json"
    monkeypatch.setenv(
        broker_client.TOKEN_ENV_VAR,
        "synthetic-test-session",
    )
    factory = FakeOwnerSpecificBrokerFactory()

    with pytest.raises(
        OwnerSpecificAuthorizationError,
        match=match,
    ):
        execute_owner_specific_evaluation(
            authorization=authorization,
            scenario_packet=scenario,
            repository_sha=repository_sha,
            live_addendum_path=(
                authorization.evaluation_identity.live_addendum_path
            ),
            scenario_packet_path=(
                authorization.evaluation_identity.scenario_packet_path
            ),
            output_packet_path=(
                output_packet_path
            ),
            actual_argv=actual_argv,
            repository_root=tmp_path,
            transport_factory=factory,
        )
    assert factory.factory_routes == []
    assert factory.calls == []


def test_missing_session_and_output_collision_fail_before_factory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization, scenario, argv = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )
    factory = FakeOwnerSpecificBrokerFactory()
    monkeypatch.delenv(broker_client.TOKEN_ENV_VAR, raising=False)

    with pytest.raises(
        OwnerSpecificAuthorizationError,
        match="temporary loopback broker session",
    ):
        execute_owner_specific_evaluation(
            authorization=authorization,
            scenario_packet=scenario,
            repository_sha=REPOSITORY_SHA,
            live_addendum_path=(
                authorization.evaluation_identity.live_addendum_path
            ),
            scenario_packet_path=(
                authorization.evaluation_identity.scenario_packet_path
            ),
            output_packet_path=(
                authorization.evaluation_identity.output_packet_path
            ),
            actual_argv=argv,
            repository_root=tmp_path,
            transport_factory=factory,
        )
    assert factory.factory_routes == []

    output = tmp_path / authorization.evaluation_identity.output_packet_path
    output.parent.mkdir(parents=True)
    output.write_text("collision", encoding="utf-8")
    monkeypatch.setenv(
        broker_client.TOKEN_ENV_VAR,
        "synthetic-test-session",
    )
    with pytest.raises(
        OwnerSpecificAuthorizationError,
        match="already exists",
    ):
        execute_owner_specific_evaluation(
            authorization=authorization,
            scenario_packet=scenario,
            repository_sha=REPOSITORY_SHA,
            live_addendum_path=(
                authorization.evaluation_identity.live_addendum_path
            ),
            scenario_packet_path=(
                authorization.evaluation_identity.scenario_packet_path
            ),
            output_packet_path=(
                authorization.evaluation_identity.output_packet_path
            ),
            actual_argv=argv,
            repository_root=tmp_path,
            transport_factory=factory,
        )
    assert factory.factory_routes == []


def test_unknown_usage_and_per_call_cost_breach_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for suffix, factory, match in (
        (
            "unknown",
            FakeOwnerSpecificBrokerFactory(usage_observed=False),
            "unknown usage",
        ),
        (
            "cost",
            FakeOwnerSpecificBrokerFactory(cost_usd="1.00"),
            "exceeds its cap",
        ),
    ):
        authorization, scenario, argv = authorization_bundle(
            repository_root=tmp_path,
            repository_sha=REPOSITORY_SHA,
            output_packet_path=f"output/local/{suffix}.json",
        )
        monkeypatch.setenv(
            broker_client.TOKEN_ENV_VAR,
            "synthetic-test-session",
        )
        with pytest.raises(
            OwnerSpecificOrchestrationError,
            match=match,
        ):
            execute_owner_specific_evaluation(
                authorization=authorization,
                scenario_packet=scenario,
                repository_sha=REPOSITORY_SHA,
                live_addendum_path=(
                    authorization.evaluation_identity.live_addendum_path
                ),
                scenario_packet_path=(
                    authorization.evaluation_identity.scenario_packet_path
                ),
                output_packet_path=(
                    authorization.evaluation_identity.output_packet_path
                ),
                actual_argv=argv,
                repository_root=tmp_path,
                transport_factory=factory,
            )


def test_policy_packet_is_deterministic_and_every_bound_field_matters(
    tmp_path: Path,
) -> None:
    authorization, _, _ = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )
    policy = authorization.canonical_policy_packet
    rebuilt = build_canonical_policy_packet(
        semantic_judge_route=authorization.semantic_judge_route,
        requirement_packet=authorization.semantic_requirement_packet,
        prompt_experiment=authorization.prompt_experiment,
        owner_identities=authorization.owner_identities,
    )
    assert rebuilt.to_packet() == policy.to_packet()
    assert rebuilt.sha256 == policy.sha256
    assert authorization.authority_policy == (
        f"owner-specific-policy:{policy.sha256}"
    )

    base = policy.to_packet()
    mutations = {
        "semantic_judge_route_identity_sha256": "1" * 64,
        "semantic_requirement_packet_sha256": "2" * 64,
        "outcome_metric": "another_metric",
        "trial_schedule_sha256": "3" * 64,
        "prompt_variant_contract_version": "another_variant_contract",
        "orchestrator_version": "another_orchestrator",
        "semantic_judge_execution_observation_version": (
            "another_observation"
        ),
        "blinding_policy_identity": "another_blinding_policy",
        "stochastic_attribution_ceiling": "another_ceiling",
        "canonicalization_version": "another_canonicalization",
    }
    for field_name, value in mutations.items():
        changed = {**base, field_name: value}
        assert canonical_sha256(changed) != policy.sha256


def test_non_test_execute_identity_is_fixed_to_generic_broker(
    tmp_path: Path,
) -> None:
    authorization, _, _ = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )

    assert (
        authorization.evaluation_identity.transport_factory_spec
        == GENERIC_BROKER_TRANSPORT_FACTORY_SPEC
    )


def test_nonloopback_endpoint_and_unmarked_factory_fail_before_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization, scenario, argv = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )
    factory = FakeOwnerSpecificBrokerFactory()
    monkeypatch.setenv(
        broker_client.TOKEN_ENV_VAR,
        "synthetic-test-session",
    )
    monkeypatch.setattr(
        broker_client,
        "DEFAULT_BROKER_URL",
        "https://broker.invalid",
    )

    with pytest.raises(
        OwnerSpecificAuthorizationError,
        match="fixed loopback broker endpoint",
    ):
        execute_owner_specific_evaluation(
            authorization=authorization,
            scenario_packet=scenario,
            repository_sha=REPOSITORY_SHA,
            live_addendum_path=(
                authorization.evaluation_identity.live_addendum_path
            ),
            scenario_packet_path=(
                authorization.evaluation_identity.scenario_packet_path
            ),
            output_packet_path=(
                authorization.evaluation_identity.output_packet_path
            ),
            actual_argv=argv,
            repository_root=tmp_path,
            transport_factory=factory,
        )
    assert factory.factory_routes == []

    monkeypatch.setattr(
        broker_client,
        "DEFAULT_BROKER_URL",
        "http://127.0.0.1:8765/run",
    )
    unmarked_factory_calls: list[object] = []

    def unmarked_factory(route):
        unmarked_factory_calls.append(route)
        raise AssertionError("unmarked factory was constructed")

    with pytest.raises(
        OwnerSpecificAuthorizationError,
        match="confined to explicit test doubles",
    ):
        execute_owner_specific_evaluation(
            authorization=authorization,
            scenario_packet=scenario,
            repository_sha=REPOSITORY_SHA,
            live_addendum_path=(
                authorization.evaluation_identity.live_addendum_path
            ),
            scenario_packet_path=(
                authorization.evaluation_identity.scenario_packet_path
            ),
            output_packet_path=(
                authorization.evaluation_identity.output_packet_path
            ),
            actual_argv=argv,
            repository_root=tmp_path,
            transport_factory=unmarked_factory,
        )
    assert unmarked_factory_calls == []
