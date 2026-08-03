"""Test-only builders and fake broker transport for owner-specific evaluation."""

from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from core.run_authority_contract import (
    RunContractRequirementKind,
    RunContractStrictness,
)
from scripts.evaluation.model_origination_evaluation_reporting import (
    EVALUATION_REPORT_SCHEMA_VERSION,
)
from scripts.evaluation.model_origination_experiment_authority import (
    EXPERIMENT_AUTHORITY_SCHEMA_VERSION,
)
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationTransportResponse,
)
from scripts.evaluation.search_planner_mechanical_validation import (
    MECHANICAL_VALIDATOR_SCHEMA_VERSION,
)
from scripts.evaluation.search_planner_owner_specific_authorization import (
    BLINDING_POLICY_IDENTITY,
    EVALUATION_KIND,
    GENERIC_BROKER_TRANSPORT_FACTORY_SPEC,
    OUTCOME_METRIC,
    OWNER_SPECIFIC_AUTHORIZATION_SCHEMA_VERSION,
    OWNER_SPECIFIC_ORCHESTRATOR_VERSION,
    RETENTION_POSTURE,
    SCENARIO_PACKET_SCHEMA_VERSION,
    SEMANTIC_EXECUTION_OBSERVATION_VERSION,
    SEMANTIC_REQUIREMENT_PACKET_SCHEMA_VERSION,
    STOCHASTIC_ATTRIBUTION_CEILING,
    TRIAL_SCHEDULE_SCHEMA_VERSION,
    EvaluationIdentityAuthorization,
    InstalledOwnerIdentities,
    OwnerSpecificLiveAuthorization,
    OwnerSpecificScenarioPacket,
    PlannerRouteAuthorization,
    PromptExperimentAuthorization,
    RetentionPolicy,
    ScenarioPacketIdentity,
    SemanticJudgeRouteAuthorization,
    SemanticRequirementPacket,
    TrialScheduleEntry,
    WholeEvaluationCaps,
    build_canonical_execute_command,
    build_canonical_policy_packet,
)
from scripts.evaluation.search_planner_owner_specific_scenario import (
    OwnerSpecificContextRecord,
    OwnerSpecificRouterSpecification,
    OwnerSpecificScenarioSpecification,
    OwnerSpecificSourceObligation,
    build_owner_specific_scenario_packet,
)
from scripts.evaluation.search_planner_product_boundary_observer import (
    CANONICAL_PRODUCT_BOUNDARY_VERSION,
)
from scripts.evaluation.search_planner_prompt_variant import (
    PROMPT_VARIANT_CONTRACT_VERSION,
    PromptVariantSpecification,
)
from scripts.evaluation.search_planner_semantic_judgment import (
    SEMANTIC_JUDGMENT_CONTRACT_VERSION,
    EssentialRequirement,
)
from tests.fixtures.searchos_analystos_offline_scenarios import (
    SCENARIOS,
    planner_payload,
)

SYNTHETIC_VARIANT_INSTRUCTION = (
    "SYNTHETIC SEARCHPLANNER TEST INSTRUCTIONS\n"
    "Return only a contract-valid JSON planning proposal.\n\n"
)

# Fixed opaque literals for the bounded test schedules in this phase. Their
# tuple order allocates identities but their values encode no schedule facts.
OPAQUE_SEMANTIC_CALL_IDS = (
    (
        "semantic-call:"
        "d0daa435"
        "b1727dda"
        "33398f01"
        "480b4215"
        "37bd9594"
        "a8e798f5"
        "1cdae028"
        "aa6d1784"
    ),
    (
        "semantic-call:"
        "505fcc0e"
        "2c2fcbf9"
        "26164626"
        "ea04add6"
        "e914bd51"
        "d815f202"
        "0971d6e8"
        "074abbeb"
    ),
    (
        "semantic-call:"
        "3203bde5"
        "8464a731"
        "c0da1546"
        "1c2b4c78"
        "845c063f"
        "1989e916"
        "57c34aeb"
        "755d15dd"
    ),
    (
        "semantic-call:"
        "69c4bfc4"
        "507e56c0"
        "01ee0605"
        "8b183a3b"
        "ce01cfd2"
        "0e889561"
        "823e5ef0"
        "f3524e15"
    ),
    (
        "semantic-call:"
        "da8df851"
        "f077d616"
        "7c28545e"
        "a4c3de49"
        "dac6a805"
        "a2cb5e15"
        "a51bc1e4"
        "d9a5daf1"
    ),
    (
        "semantic-call:"
        "7b5bb361"
        "a4c985e9"
        "ae638e6b"
        "e52988d1"
        "848bedc7"
        "ec2bb4be"
        "51104eb7"
        "06c707d6"
    ),
    (
        "semantic-call:"
        "e5fbdd7c"
        "983590a3"
        "63b06bb8"
        "6650eed6"
        "b3d94080"
        "a0134031"
        "7eed2821"
        "198d79c1"
    ),
    (
        "semantic-call:"
        "992c334d"
        "b9ff4dd2"
        "38357a3b"
        "3fada521"
        "aa7f8258"
        "9aea5793"
        "6f10900c"
        "1ba53b9e"
    ),
)


def scenario_packet() -> OwnerSpecificScenarioPacket:
    return build_owner_specific_scenario_packet(
        OwnerSpecificScenarioSpecification(
            scenario_id="fictional-owner-specific-case",
            fictional_scenario=True,
            normalized_fictional_user_request=SCENARIOS[0].root_query,
            requested_mode="Balanced",
            current_date="2026-07-30",
            focus_academic=False,
            force_intent_news=False,
            include_domains=(),
            exclude_domains=(),
            news_preferred_domains=(),
            router=OwnerSpecificRouterSpecification(
                intent="general",
                report_type="research_report",
                query_type="factual",
                core_topic="Harbor Cooperative filing route",
                primary_entity="Harbor Cooperative",
                entities=("Harbor Cooperative", "Northstar Bulletin 26"),
            ),
            direct_records=(
                OwnerSpecificContextRecord(
                    record_id="harbor-bulletin",
                    label="Northstar Bulletin 26",
                    information_need="Identify the fictional filing-route constraints.",
                    fictional_summary=(
                        "Fictional current bulletin retained only for planning."
                    ),
                    source_obligation_requirement_id="harbor-bulletin-source",
                ),
            ),
            source_obligations=(
                OwnerSpecificSourceObligation(
                    requirement_id="harbor-bulletin-source",
                    requirement_kind=RunContractRequirementKind.OFFICIAL_CURRENT,
                    strictness=RunContractStrictness.REQUIRED,
                    required_source_class="fictional_official_bulletin",
                    required_source_tier="official",
                    required_currentness="current",
                    satisfaction_rule="direct fictional bulletin required for planning",
                    allowed_lower_tier_use="context_only",
                    cannot_satisfy_with=("secondary_summary",),
                    rationale="fictional direct-premise source obligation",
                ),
            ),
        )
    )


def owner_identities() -> InstalledOwnerIdentities:
    return InstalledOwnerIdentities(
        product_boundary_version=CANONICAL_PRODUCT_BOUNDARY_VERSION,
        mechanical_validator_version=MECHANICAL_VALIDATOR_SCHEMA_VERSION,
        semantic_contract_version=SEMANTIC_JUDGMENT_CONTRACT_VERSION,
        experiment_authority_version=EXPERIMENT_AUTHORITY_SCHEMA_VERSION,
        report_schema_version=EVALUATION_REPORT_SCHEMA_VERSION,
        prompt_variant_contract_version=PROMPT_VARIANT_CONTRACT_VERSION,
        orchestrator_version=OWNER_SPECIFIC_ORCHESTRATOR_VERSION,
        semantic_execution_observation_version=(
            SEMANTIC_EXECUTION_OBSERVATION_VERSION
        ),
    )


def requirement_packet() -> SemanticRequirementPacket:
    return SemanticRequirementPacket(
        schema_version=SEMANTIC_REQUIREMENT_PACKET_SCHEMA_VERSION,
        reference="synthetic-requirements:v1",
        scenario_id="fictional-owner-specific-case",
        essential_requirements=(
            EssentialRequirement(
                requirement_id="requirement:filing-route",
                normalized_requirement=(
                    "The plan must represent the requested filing-route assignment."
                ),
                requirement_kind="FACT",
            ),
            EssentialRequirement(
                requirement_id="requirement:authority",
                normalized_requirement=(
                    "The plan must preserve the current fictional bulletin source need."
                ),
                requirement_kind="AUTHORITY",
            ),
            EssentialRequirement(
                requirement_id="requirement:answer-capability",
                normalized_requirement=(
                    "The plan must support a truthful answer to the whole request."
                ),
                requirement_kind="ANSWER_CAPABILITY",
            ),
        ),
        essential_architecture_constraints=(
            "SearchPlanner proposes; RunKernel governs accepted state.",
            "SearchPlanner does not answer or claim evidence.",
        ),
        prohibited_upgrades_or_shortcuts=(
            "Do not treat planning context as evidence.",
            "Do not grant acquisition or final-answer authority.",
        ),
    )


def authorization_bundle(
    *,
    repository_root: Path,
    repository_sha: str,
    required_observations_per_arm: int = 1,
    schedule_arm_order: tuple[str, ...] | None = None,
    output_packet_path: str = "output/local/owner-specific-result.json",
    live_addendum_path: str = "authorizations/owner-specific-live.json",
    scenario_packet_path: str = "scenarios/fictional-owner-specific.json",
) -> tuple[
    OwnerSpecificLiveAuthorization,
    OwnerSpecificScenarioPacket,
    tuple[str, ...],
]:
    scenario = scenario_packet()
    control = "installed-control"
    variant = "synthetic-prefix-variant"
    order = schedule_arm_order or tuple(
        arm
        for _ in range(required_observations_per_arm)
        for arm in (control, variant)
    )
    semantic_id_count = len(order) * 2
    if semantic_id_count > len(OPAQUE_SEMANTIC_CALL_IDS):
        raise ValueError(
            "test schedule exceeds its predeclared opaque semantic identities"
        )
    semantic_call_ids = iter(
        OPAQUE_SEMANTIC_CALL_IDS[:semantic_id_count]
    )
    schedule = tuple(
        TrialScheduleEntry(
            trial_id=f"trial-{index:02d}",
            arm_id=arm,
            planner_call_id=f"planner-call-{index:02d}",
            primary_judge_call_id=next(semantic_call_ids),
            adversarial_judge_call_id=next(semantic_call_ids),
        )
        for index, arm in enumerate(order, start=1)
    )
    prompt_variant = PromptVariantSpecification(
        contract_version=PROMPT_VARIANT_CONTRACT_VERSION,
        control_arm_id=control,
        variant_arm_id=variant,
        variant_instruction_text=SYNTHETIC_VARIANT_INSTRUCTION,
        variant_instruction_sha256=sha256(
            SYNTHETIC_VARIANT_INSTRUCTION.encode("utf-8")
        ).hexdigest(),
        maximum_instruction_characters=1000,
    )
    placeholder_policy = f"owner-specific-policy:{'0' * 64}"
    experiment = PromptExperimentAuthorization(
        trial_schedule_schema_version=TRIAL_SCHEDULE_SCHEMA_VERSION,
        control_arm_id=control,
        variant_arm_id=variant,
        trial_schedule=schedule,
        required_observations_per_arm=required_observations_per_arm,
        design_kind=(
            "SINGLE_PAIR"
            if required_observations_per_arm == 1
            else "RANDOMIZED_REPEATED"
        ),
        sampling_policy="maintainer_precommitted_schedule_v1",
        randomized_order=required_observations_per_arm > 1,
        blinded_judging=True,
        outcome_metric=OUTCOME_METRIC,
        experiment_policy_identity=placeholder_policy,
        blinding_policy_identity=BLINDING_POLICY_IDENTITY,
        stochastic_attribution_ceiling=STOCHASTIC_ATTRIBUTION_CEILING,
        prompt_variant_specification=prompt_variant,
    )
    planner_route = PlannerRouteAuthorization(
        role="search_planner",
        provider="synthetic-provider",
        model="synthetic-planner-model",
        reasoning_effort="synthetic-fixed",
        maximum_input_tokens=20000,
        maximum_output_tokens=8000,
        timeout_seconds=30,
        retry_cap=0,
        per_call_cost_ceiling_usd="0.10",
        maximum_planner_calls=len(schedule),
    )
    judge_route = SemanticJudgeRouteAuthorization(
        role="search_planner_semantic_judge",
        provider="synthetic-provider",
        model="synthetic-judge-model",
        reasoning_effort="synthetic-fixed",
        maximum_input_tokens=30000,
        maximum_output_tokens=4000,
        timeout_seconds=30,
        retry_cap=0,
        per_call_cost_ceiling_usd="0.05",
        maximum_primary_judge_calls=len(schedule),
        maximum_adversarial_judge_calls=len(schedule),
    )
    requirements = requirement_packet()
    owners = owner_identities()
    policy = build_canonical_policy_packet(
        semantic_judge_route=judge_route,
        requirement_packet=requirements,
        prompt_experiment=experiment,
        owner_identities=owners,
    )
    experiment = replace(
        experiment,
        experiment_policy_identity=policy.authority_policy,
    )
    # The authority-policy value is outside the schedule packet, so replacing
    # it does not change the canonical policy digest.
    policy = build_canonical_policy_packet(
        semantic_judge_route=judge_route,
        requirement_packet=requirements,
        prompt_experiment=experiment,
        owner_identities=owners,
    )
    argv, command, command_digest = build_canonical_execute_command(
        repository_sha=repository_sha,
        live_addendum_path=live_addendum_path,
        scenario_packet_path=scenario_packet_path,
        output_packet_path=output_packet_path,
        repository_root=repository_root,
    )
    evaluation_identity = EvaluationIdentityAuthorization(
        schema_version=OWNER_SPECIFIC_AUTHORIZATION_SCHEMA_VERSION,
        reference="synthetic-owner-specific-live-authorization",
        repository_sha=repository_sha,
        scenario_id=scenario.scenario_id,
        evaluation_kind=EVALUATION_KIND,
        decision="AUTHORIZED_FOR_EXACT_SYNTHETIC_TEST",
        stop_condition="Stop on any authority, infrastructure, or cap failure.",
        output_packet_path=output_packet_path,
        retention_posture=RETENTION_POSTURE,
        live_addendum_path=live_addendum_path,
        scenario_packet_path=scenario_packet_path,
        transport_factory_spec=GENERIC_BROKER_TRANSPORT_FACTORY_SPEC,
        canonical_operator_command=command,
        canonical_operator_command_digest=command_digest,
    )
    total_cost = (
        required_observations_per_arm
        * 2
        * (0.10 + 0.05 + 0.05)
    )
    authorization = OwnerSpecificLiveAuthorization(
        schema_version=OWNER_SPECIFIC_AUTHORIZATION_SCHEMA_VERSION,
        evaluation_identity=evaluation_identity,
        scenario_packet_identity=ScenarioPacketIdentity(
            schema_version=SCENARIO_PACKET_SCHEMA_VERSION,
            scenario_id=scenario.scenario_id,
            scenario_packet_path=scenario_packet_path,
            scenario_packet_sha256=scenario.sha256,
        ),
        prompt_experiment=experiment,
        planner_route=planner_route,
        semantic_judge_route=judge_route,
        whole_evaluation_caps=WholeEvaluationCaps(
            maximum_planner_boundary_runs=len(schedule),
            maximum_total_broker_calls=len(schedule) * 3,
            maximum_total_observed_cost_usd=f"{total_cost:.2f}",
            maximum_wall_clock_seconds=300,
        ),
        retention_policy=RetentionPolicy(
            store=False,
            background=False,
            retained_live_artifacts=False,
            retain_raw_prompts=False,
            retain_raw_outputs=False,
            retain_query_text=False,
        ),
        owner_identities=owners,
        semantic_requirement_packet=requirements,
        canonical_policy_packet=policy,
        policy_packet_sha256=policy.sha256,
        authority_policy=policy.authority_policy,
    )
    return authorization, scenario, argv


class FakeOwnerSpecificBrokerFactory:
    """Test-only broker factory; never imported by production modules."""

    test_only = True

    def __init__(
        self,
        *,
        planner_outputs: list[str] | None = None,
        semantic_outputs: list[str] | None = None,
        usage_observed: bool = True,
        cost_usd: str = "0.01",
    ) -> None:
        default_packet = planner_payload(SCENARIOS[0])
        default_packet.pop("planner_model_metadata", None)
        for obligation in default_packet["source_obligation_candidates"]:
            obligation["obligation_kind"] = "official_current"
            obligation["strictness"] = "required"
        default_payload = json.dumps(default_packet)
        self.planner_outputs = list(
            planner_outputs
            if planner_outputs is not None
            else [default_payload] * 20
        )
        self.semantic_outputs = list(semantic_outputs or [])
        self.usage_observed = usage_observed
        self.cost_usd = cost_usd
        self.factory_routes: list[Mapping[str, Any]] = []
        self.calls: list[dict[str, Any]] = []

    def __call__(self, route: Any):
        self.factory_routes.append(
            {
                "provider": route.provider,
                "model": route.model,
                "allowed_model_roles": route.allowed_model_roles,
                "require_observed_usage": route.require_observed_usage,
            }
        )

        def transport(
            *,
            role: str,
            prompt: str,
            system_prompt: str,
            provider: str,
            model: str,
            maximum_input_tokens: int,
            maximum_output_tokens: int,
            correlation_id: str,
        ) -> EvaluationTransportResponse:
            self.calls.append(
                {
                    "role": role,
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "provider": provider,
                    "model": model,
                    "maximum_input_tokens": maximum_input_tokens,
                    "maximum_output_tokens": maximum_output_tokens,
                    "correlation_id": correlation_id,
                }
            )
            if role == "search_planner":
                if not self.planner_outputs:
                    raise AssertionError("no fake Planner output remains")
                output = self.planner_outputs.pop(0)
            else:
                output = (
                    self.semantic_outputs.pop(0)
                    if self.semantic_outputs
                    else _semantic_met_output(prompt)
                )
            return _transport_response(
                output=output,
                provider=provider,
                model=model,
                reasoning_effort=route.reasoning_effort,
                usage_observed=self.usage_observed,
                cost_usd=self.cost_usd,
            )

        return transport


def _semantic_met_output(prompt: str) -> str:
    packet = json.loads(prompt)
    request = packet["semantic_judgment_request"]
    proposed_plan = request["proposed_plan"]
    proposal_path = (
        "/answer_components/0"
        if proposed_plan.get("answer_components")
        else "/question_meaning_summary"
    )
    mappings = [
        {
            "requirement_id": item["requirement_id"],
            "proposal_paths": [proposal_path],
            "bounded_explanation": (
                "The canonical plan contains bounded material for this requirement."
            ),
        }
        for item in request["essential_requirements"]
    ]
    return json.dumps(
        {
            "status": "MET",
            "requirement_mappings": mappings,
            "issues": [],
            "ambiguities": [],
        }
    )


def _transport_response(
    *,
    output: str,
    provider: str,
    model: str,
    reasoning_effort: str,
    usage_observed: bool,
    cost_usd: str,
) -> EvaluationTransportResponse:
    return EvaluationTransportResponse(
        output=output,
        reasoning_effort=reasoning_effort,
        generation_status="completed",
        generation_incomplete_reason=None,
        max_output_tokens_reached=False,
        output_text_present=bool(output),
        output_text_character_count=len(output),
        output_text_digest=sha256(output.encode("utf-8")).hexdigest(),
        usage_observed=usage_observed,
        input_tokens=100 if usage_observed else None,
        cached_input_tokens=0 if usage_observed else None,
        uncached_input_tokens=100 if usage_observed else None,
        output_tokens=50 if usage_observed else None,
        reasoning_tokens=10 if usage_observed else None,
        non_reasoning_output_tokens=40 if usage_observed else None,
        total_tokens=150 if usage_observed else None,
        caller_calculated_route_priced_cost_usd=(
            cost_usd if usage_observed else None
        ),
        cost_posture="exact" if usage_observed else "unknown",
        output_token_utilization="0.01" if usage_observed else None,
        reasoning_token_share="0.2" if usage_observed else None,
        provider_elapsed_milliseconds_total=12,
        canonical_provider_used=provider,
        canonical_model_used=model,
        provider_request_attempt_count=1,
        raw_material_retained=False,
        credentials_accessed=True,
    )


__all__ = [
    "FakeOwnerSpecificBrokerFactory",
    "OPAQUE_SEMANTIC_CALL_IDS",
    "SYNTHETIC_VARIANT_INSTRUCTION",
    "authorization_bundle",
    "owner_identities",
    "requirement_packet",
    "scenario_packet",
]
