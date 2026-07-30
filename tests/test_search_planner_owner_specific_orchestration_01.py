from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from scripts import request_provider_proxy_broker as broker_client
from scripts.evaluation.search_planner_owner_specific_authorization import (
    GENERIC_BROKER_TRANSPORT_FACTORY_SPEC,
    OwnerSpecificAuthorizationError,
    OwnerSpecificLiveAuthorization,
    build_canonical_policy_packet,
    canonical_sha256,
)
from scripts.evaluation.search_planner_owner_specific_orchestration import (
    OwnerSpecificOrchestrationError,
    build_plan_only_packet,
    execute_owner_specific_evaluation,
)
from tests.helpers.search_planner_owner_specific_fakes import (
    SYNTHETIC_VARIANT_INSTRUCTION,
    FakeOwnerSpecificBrokerFactory,
    authorization_bundle,
)

REPOSITORY_SHA = "3a76a3a24efef5ee4bec2d43e301463b671f0d80"


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
    assert len(packet["trial_results"]) == 2
    for trial in packet["trial_results"]:
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


def test_mechanical_failure_skips_both_judges_and_remains_a_trial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = FakeOwnerSpecificBrokerFactory(
        planner_outputs=["{}", None],
    )
    # Restore the second default Planner output without exposing a production
    # fake. The helper constructor supplies its own bounded fixture queue.
    defaults = FakeOwnerSpecificBrokerFactory().planner_outputs
    factory.planner_outputs[1] = defaults[0]

    _, _, factory, packet = _execute(
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
    assert failed["product_boundary_result"]["boundary_status"] == "FAIL"
    assert (
        failed["mechanical_validation_result"]["overall_posture"]
        == "FAIL"
    )
    assert failed["semantic_judgment_result"] is None
    assert failed["semantic_execution_observation"] is None
    assert failed["trial_observation"]["semantic_status"] == "NOT_RUN"
    assert failed["trial_observation"]["complete"] is False
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
    ) == {"primary-call-01", "adversarial-call-01"}


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
    if context_mutation == "repository":
        repository_sha = "1" * 40
    elif context_mutation == "command":
        actual_argv = tuple(reversed(argv))
    elif context_mutation == "scenario":
        scenario = replace(
            scenario,
            scenario_id="another-fictional-scenario",
        )
    else:
        authorization = replace(
            authorization,
            scenario_packet_identity=replace(
                authorization.scenario_packet_identity,
                scenario_packet_sha256="1" * 64,
            ),
        )
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
                authorization.evaluation_identity.output_packet_path
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
