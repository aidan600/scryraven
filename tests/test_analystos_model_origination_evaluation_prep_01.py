"""Phase-focus proof for the offline AnalystOS origination evaluator.

Test path/node id:
``tests/test_analystos_model_origination_evaluation_prep_01.py``.
Proof class: component_harness_proof.
Validation bucket: phase_focus.
Surface guarded: no-live model-boundary selection, call census, deterministic
scoring, sanitized packets, and fail-closed authorization.
High-custody or closed-this-phase surface: production prompts, routes, model
selection, recovery policy, D-prime, SearchOS, RunKernel, FAP, and Author are
closed.
Runtime/product path guarded: evaluation-only operator plus exact reuse of the
merged ordinary-path fixture by its default execute runner.
Expected cost: deterministic and sub-second apart from module import.
Promotion posture: remain phase_focus; the merged integration gate owns the
durable product-path proof.
Demotion/retirement condition: retire or narrow after the separately licensed
live acceptance decision.
Why not fast_pr: this is detailed phase machinery, not a cheap broad product
sentinel.
"""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.multicomponent_role_runtime import ROLE_SYSTEM_PROMPTS
from core.search_planner_model_prompt import SEARCH_PLANNER_MODEL_SYSTEM_PROMPT
from scripts.evaluation import run_analystos_model_origination_evaluation as evaluator
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    CLASSIFICATIONS,
    LIVE_ADDENDUM_SCHEMA_VERSION,
    BoundaryCallObservation,
    BoundaryInjectionController,
    ClassificationEvidence,
    EvaluationConfigurationError,
    EvaluationRequest,
    EvaluationRouteAttestationError,
    EvaluationTransportError,
    EvaluationTransportResponse,
    ExecutionIdentity,
    IncompleteModelBoundaryPacketError,
    LiveAuthorization,
    PairedProbeEvidence,
    ScenarioRunResult,
    build_call_manifest,
    build_execution_identity,
    classify_result,
    current_repository_sha,
    main,
    paired_probe_demonstrates_prompt_causality,
    project_and_score_role_output,
    proposed_live_addendum_template,
    reject_forbidden_packet_material,
    resolve_request,
    run_evaluation,
    sample_classification_packet,
)
from tests.fixtures import searchos_analystos_offline_scenarios as offline_corpus
from tests.fixtures.analystos_model_origination_expectations import (
    MODEL_ROLES,
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SEARCH_PLANNER,
    SCENARIO_EXPECTATIONS,
)
from tests.fixtures.searchos_analystos_offline_scenarios import (
    BOUNDED_LIMIT,
    CASE_1,
    CASE_3,
    CASE_4,
    CASE_5,
    CASE_6,
    CASE_7,
    SCENARIO_BY_ID,
    SCENARIOS,
    planner_payload,
)

REPOSITORY_SHA = "0719c70982b22a65f7688f2fbda5b0be8e653f95"  # pragma: allowlist secret
SYNTHETIC_LIVE_ADDENDUM_PATH = "tests/fixtures/analystos_model_origination_synthetic_live_addendum.json"
SYNTHETIC_TRANSPORT_FACTORY_SPEC = "test_analystos_model_origination_evaluation_prep_01:cli_fake_transport_factory"


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.next_output: dict[str, Any] = {}
        self.credentials_accessed = False
        self.canonical_provider_used: str | None = None
        self.canonical_model_used: str | None = None
        self.input_tokens = 10
        self.output_tokens = 10
        self.cost = 0.0
        self.provider_request_attempt_count = 1
        self.failure: Exception | None = None

    def __call__(self, **kwargs: Any) -> EvaluationTransportResponse:
        self.calls.append({key: value for key, value in kwargs.items() if key not in {"prompt", "system_prompt"}})
        if self.failure is not None:
            raise self.failure
        return EvaluationTransportResponse(
            output=dict(self.next_output),
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cost=self.cost,
            canonical_provider_used=(self.canonical_provider_used or str(kwargs["provider"])),
            canonical_model_used=(self.canonical_model_used or str(kwargs["model"])),
            provider_request_attempt_count=self.provider_request_attempt_count,
            credentials_accessed=False,
        )


class FactoryCensus:
    def __init__(
        self,
        *,
        transport: FakeTransport | OrdinaryFixtureFakeTransport | None = None,
        transport_factory_spec: str = SYNTHETIC_TRANSPORT_FACTORY_SPEC,
    ) -> None:
        self.calls = 0
        self.transport = transport or FakeTransport()
        self.transport_factory_spec = transport_factory_spec

    def __call__(
        self,
        _authorization: LiveAuthorization,
    ) -> FakeTransport | OrdinaryFixtureFakeTransport:
        self.calls += 1
        return self.transport


CLI_FACTORY_CENSUS = FactoryCensus()


def cli_fake_transport_factory(
    _authorization: LiveAuthorization,
) -> FakeTransport:
    CLI_FACTORY_CENSUS.calls += 1
    return CLI_FACTORY_CENSUS.transport


setattr(
    cli_fake_transport_factory,
    "transport_factory_spec",
    SYNTHETIC_TRANSPORT_FACTORY_SPEC,
)


def _request(
    evaluation_pass: str,
    *,
    execution_mode: str = "plan_only",
    scenario_ids: tuple[str, ...] = (CASE_1,),
    roles: tuple[str, ...] = (),
    output: str | None = None,
) -> EvaluationRequest:
    return EvaluationRequest(
        evaluation_pass=evaluation_pass,
        execution_mode=execution_mode,
        scenario_ids=scenario_ids,
        selected_model_roles=roles,
        output_packet_path=output,
    )


def _repo_output_path(tmp_path: Path, filename: str) -> str:
    """Return a collision-resistant ignored path inside the repository."""

    return str(Path("output") / "analystos_evaluation_tests" / tmp_path.parent.name / tmp_path.name / filename)


def _authorization(
    request: EvaluationRequest,
    *,
    output: str,
    retry_cap: int = 0,
    maximum_model_calls: int | None = None,
    repository_sha: str = REPOSITORY_SHA,
    live_addendum_path: str = SYNTHETIC_LIVE_ADDENDUM_PATH,
    transport_factory_spec: str = SYNTHETIC_TRANSPORT_FACTORY_SPEC,
) -> LiveAuthorization:
    resolved = resolve_request(request)
    assert resolved.output_packet_path == output
    execution_identity = build_execution_identity(
        resolved,
        repository_sha=repository_sha,
        live_addendum_path=live_addendum_path,
        transport_factory_spec=transport_factory_spec,
    )
    manifest = build_call_manifest(resolved, retry_allowance=retry_cap)
    return LiveAuthorization(
        schema_version=LIVE_ADDENDUM_SCHEMA_VERSION,
        reference="synthetic-authorization",
        repository_sha=repository_sha,
        provider="synthetic-provider",
        model="synthetic-model",
        allowed_evaluation_pass=resolved.evaluation_pass,
        allowed_model_roles=resolved.selected_model_roles,
        allowed_scenario_ids=resolved.scenario_ids,
        maximum_model_calls=(
            manifest.total_maximum_physical_model_calls if maximum_model_calls is None else maximum_model_calls
        ),
        maximum_scryraven_runs=manifest.maximum_scryraven_runs,
        retry_cap=retry_cap,
        maximum_input_tokens=4_000,
        maximum_output_tokens=2_000,
        cost_ceiling=1.0,
        output_packet_path=execution_identity.output_packet_path,
        decision="Decide whether this synthetic boundary is ready.",
        stop_condition="Stop when any exact cap is exhausted.",
        raw_retention_posture="sanitized_only",
        transport_factory_spec=execution_identity.transport_factory_spec,
        canonical_operator_command=(execution_identity.canonical_operator_command),
        canonical_operator_command_digest=(execution_identity.canonical_operator_command_digest),
    )


def _execution_identity(
    request: EvaluationRequest,
    *,
    repository_sha: str = REPOSITORY_SHA,
    live_addendum_path: str = SYNTHETIC_LIVE_ADDENDUM_PATH,
    transport_factory_spec: str = SYNTHETIC_TRANSPORT_FACTORY_SPEC,
) -> ExecutionIdentity:
    return build_execution_identity(
        request,
        repository_sha=repository_sha,
        live_addendum_path=live_addendum_path,
        transport_factory_spec=transport_factory_spec,
    )


def _probe_observation() -> BoundaryCallObservation:
    return BoundaryCallObservation(
        execution_identity_digest="e" * 64,
        evaluation_id="f" * 64,
        scenario_id=CASE_3,
        call_id=f"{CASE_3}:cross_component_analyst:1",
        role=ROLE_CROSS_COMPONENT_ANALYST,
        provider="synthetic-provider",
        model="synthetic-model",
        safe_input_packet_digest="a" * 64,
        licensed_maximum_physical_calls=1,
        licensed_maximum_input_tokens=4_000,
        licensed_maximum_output_tokens=2_000,
        licensed_retry_cap=0,
        physical_calls=1,
        retries=0,
        packet_complete=True,
        parser_consumable=True,
        semantic_status="wrong",
        safe_semantic_projection={"synthetic": True},
        proposal_only=True,
        authority_boundary_respected=True,
    )


def _matching_probe(
    observation: BoundaryCallObservation | None = None,
) -> PairedProbeEvidence:
    observed = observation or _probe_observation()
    return PairedProbeEvidence(
        execution_identity_digest=observed.execution_identity_digest,
        evaluation_id=observed.evaluation_id,
        scenario_id=observed.scenario_id,
        call_id=observed.call_id,
        model_role=observed.role,
        provider=observed.provider,
        model=observed.model,
        semantic_input_facts_digest=observed.safe_input_packet_digest,
        instruction_difference="Remove only the dependency-order instruction.",
        controlled_instruction_dimension="dependency_order_instruction",
        control_instruction_digest="b" * 64,
        variant_instruction_digest="c" * 64,
        control_semantic_status="wrong",
        variant_semantic_status="met",
        maximum_physical_calls_each=observed.licensed_maximum_physical_calls,
        maximum_input_tokens_each=observed.licensed_maximum_input_tokens,
        maximum_output_tokens_each=observed.licensed_maximum_output_tokens,
        retry_cap_each=observed.licensed_retry_cap,
        deterministic_comparison_criteria=("dependency set equality",),
        same_scenario=True,
        same_route=True,
        same_semantic_facts=True,
        exactly_one_controlled_instruction_dimension_differs=True,
    )


def _planner_output(scenario_id: str) -> dict[str, Any]:
    output = planner_payload(SCENARIO_BY_ID[scenario_id])
    output.pop("planner_model_metadata", None)
    output["requested_output"] = SCENARIO_BY_ID[scenario_id].root_query
    for obligation in output["source_obligation_candidates"]:
        obligation["obligation_kind"] = "official_current"
    evaluator.validate_and_sanitize_model_output(output)
    return output


class OrdinaryFixtureFakeTransport:
    """Fake selected model boundaries while reusing the merged responder."""

    def __init__(
        self,
        *,
        scenario_id: str,
        tmp_path: Path,
        planner_output: Mapping[str, Any] | None = None,
    ) -> None:
        self.scenario = SCENARIO_BY_ID[scenario_id]
        self.responder = offline_corpus.SearchOSAnalystOSHarness(
            tmp_path,
            self.scenario,
        )
        self.planner_output = (
            deepcopy(dict(planner_output)) if planner_output is not None else _planner_output(scenario_id)
        )
        self.calls: list[dict[str, Any]] = []
        self.credentials_accessed = False
        self.component_call_index = 0

    def __call__(self, **kwargs: Any) -> EvaluationTransportResponse:
        role = str(kwargs["role"])
        self.calls.append({key: value for key, value in kwargs.items() if key not in {"prompt", "system_prompt"}})
        if role == ROLE_SEARCH_PLANNER:
            output: Any = deepcopy(self.planner_output)
        elif role == ROLE_COMPONENT_ANALYST:
            concept = SCENARIO_EXPECTATIONS[self.scenario.scenario_id].component_call_concepts[
                self.component_call_index
            ]
            self.component_call_index += 1
            output = _component_output(
                concept,
                self.scenario.scenario_id,
            )
        else:
            output = json.loads(
                self.responder.ask_model(
                    str(kwargs["prompt"]),
                    str(kwargs["system_prompt"]),
                    provider=str(kwargs["provider"]),
                    model=str(kwargs["model"]),
                    use_reasoning=True,
                )
            )
            evaluator.role_runtime._normalize_semantic_output(  # noqa: SLF001
                role,
                evaluator.role_runtime._parse_role_output(  # noqa: SLF001
                    output,
                    clean_json_response=None,
                ),
                output_schema_variant=(
                    evaluator.SELECTIVE_CROSS_COMPONENT_SCHEMA
                    if (
                        role == ROLE_CROSS_COMPONENT_ANALYST
                        and kwargs["system_prompt"] == evaluator.SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT
                    )
                    else None
                ),
            )
        return EvaluationTransportResponse(
            output=output,
            input_tokens=10,
            output_tokens=10,
            cost=0.0,
            canonical_provider_used=str(kwargs["provider"]),
            canonical_model_used=str(kwargs["model"]),
            credentials_accessed=False,
        )


def _component_output(concept: str, scenario_id: str) -> dict[str, Any]:
    alias = SCENARIO_EXPECTATIONS[scenario_id].concept_aliases[concept][1]
    return {
        "claim_text": f"Current fictional evidence directly supports {alias}.",
        "support_status": "supported",
        "caveats": [],
        "nonclaims": [],
        "blockers": [],
    }


def _cross_output(call: Any) -> dict[str, Any]:
    expected = SCENARIO_EXPECTATIONS[call.scenario_id].cross_calls[call.expected_cross_call_index - 1]
    relationship = (
        expected.relationship_aliases[0].replace(" ", "_")
        if expected.relationship_aliases
        else "pending_searchable_premise"
    )
    return {
        "synthesis_proposals": [
            {
                "synthesis_key": expected.target_concept,
                "claim_text": f"Synthetic proposal for {expected.target_concept}.",
                "relationship_type": relationship,
                "component_inputs": list(expected.dependency_concepts) or ["pending"],
                "synthesis_inputs": [],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            }
        ]
    }


def _synthetic_scenario_runner(
    *,
    scenario_id: str,
    controller: BoundaryInjectionController,
) -> ScenarioRunResult:
    transport = controller.transport
    assert isinstance(transport, FakeTransport)
    calls = [item for item in controller.manifest.calls if item.scenario_id == scenario_id]
    for call in calls:
        if call.model_role == ROLE_SEARCH_PLANNER:
            transport.next_output = _planner_output(scenario_id)
            system_prompt = SEARCH_PLANNER_MODEL_SYSTEM_PROMPT
            prompt = (
                "Synthetic boundary fixture.\nSanitized planner input JSON:\n" + SCENARIO_BY_ID[scenario_id].root_query
            )
        elif call.model_role == ROLE_COMPONENT_ANALYST:
            transport.next_output = _component_output(
                str(call.expected_concept),
                scenario_id,
            )
            system_prompt = ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]
            prompt = json.dumps(
                {
                    "component_ref": {
                        "component_id": call.expected_concept,
                    },
                    "run_binding": {
                        "run_id": "synthetic-run",
                        "request_id": "synthetic-request",
                    },
                    "component_evidence": {"evidence_ref_id": "synthetic-evidence"},
                }
            )
        else:
            transport.next_output = _cross_output(call)
            system_prompt = ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
            prompt = json.dumps(
                {
                    "accepted_component_refs": [{"component_id": "synthetic-component"}],
                    "accepted_contract_ref": {"digest": "synthetic-contract"},
                    "graph_ref": {"graph_digest": "synthetic-graph"},
                    "requested_synthesis_directive": (SCENARIO_BY_ID[scenario_id].root_query),
                }
            )
        controller.invoke(
            role=call.model_role,
            prompt=prompt,
            system_prompt=system_prompt,
            provider=controller.authorization.provider,
            model=controller.authorization.model,
        )
    return ScenarioRunResult(
        scenario_id=scenario_id,
        ordinary_downstream_terminal_posture=(SCENARIO_EXPECTATIONS[scenario_id].expected_terminal_posture),
        operating_system_transition_reached=True,
    )


@pytest.mark.parametrize("evaluation_pass", ("planner_only", "analyst_only", "combined"))
def test_plan_only_is_independent_from_evaluation_pass_and_zero_live(
    evaluation_pass: str,
) -> None:
    factory = FactoryCensus()
    packet = run_evaluation(
        _request(
            evaluation_pass,
            scenario_ids=tuple(item.scenario_id for item in SCENARIOS),
        ),
        repository_sha=REPOSITORY_SHA,
        transport_factory=factory,
    )
    assert packet["evaluation_pass"] == evaluation_pass
    assert packet["execution_mode"] == "plan_only"
    assert packet["transport_created"] is False
    assert packet["credentials_accessed"] is False
    assert packet["external_calls"] == 0
    assert packet["call_counts"] == {
        "model_calls": 0,
        "scryraven_runs": 0,
        "provider_calls": 0,
        "search_calls": 0,
        "retrieval_calls": 0,
        "read_calls": 0,
        "navigation_calls": 0,
        "map_calls": 0,
        "crawl_calls": 0,
        "external_calls": 0,
        "fictional_search_operations": 0,
        "fictional_read_operations": 0,
    }
    assert packet["retry_counts"] == {"total": 0}
    assert packet["primary_failure_attribution"] == "NOT_RUN"
    assert factory.calls == 0
    assert factory.transport.calls == []


def test_role_selection_is_exact_and_dprime_stays_deterministic() -> None:
    component = build_call_manifest(
        _request(
            "analyst_only",
            roles=(ROLE_COMPONENT_ANALYST,),
            scenario_ids=(CASE_3,),
        )
    )
    cross = build_call_manifest(
        _request(
            "analyst_only",
            roles=(ROLE_CROSS_COMPONENT_ANALYST,),
            scenario_ids=(CASE_3,),
        )
    )
    combined = build_call_manifest(_request("combined", scenario_ids=(CASE_3,)))
    assert set(component.calls_by_role) == MODEL_ROLES
    assert component.calls_by_role[ROLE_COMPONENT_ANALYST] == 3
    assert component.calls_by_role[ROLE_CROSS_COMPONENT_ANALYST] == 0
    assert component.calls_by_role[ROLE_SEARCH_PLANNER] == 0
    assert cross.calls_by_role[ROLE_COMPONENT_ANALYST] == 0
    assert cross.calls_by_role[ROLE_CROSS_COMPONENT_ANALYST] == 2
    assert cross.calls_by_role[ROLE_SEARCH_PLANNER] == 0
    assert combined.calls_by_role == {
        ROLE_COMPONENT_ANALYST: 3,
        ROLE_CROSS_COMPONENT_ANALYST: 2,
        ROLE_SEARCH_PLANNER: 1,
    }
    assert "component_dprime" in combined.deterministic_roles
    assert "synthesis_dprime" in combined.deterministic_roles
    assert not {
        "component_dprime",
        "synthesis_dprime",
    }.intersection(combined.selected_model_roles)


@pytest.mark.parametrize(
    ("evaluation_pass", "roles"),
    (
        ("planner_only", (ROLE_COMPONENT_ANALYST,)),
        ("analyst_only", (ROLE_SEARCH_PLANNER,)),
        (
            "combined",
            (ROLE_SEARCH_PLANNER, ROLE_COMPONENT_ANALYST),
        ),
    ),
)
def test_incompatible_role_selections_fail_before_transport(
    evaluation_pass: str,
    roles: tuple[str, ...],
) -> None:
    with pytest.raises(EvaluationConfigurationError):
        build_call_manifest(
            _request(
                evaluation_pass,
                roles=roles,
            )
        )


def test_all_scenario_call_census_is_exact() -> None:
    scenario_ids = tuple(item.scenario_id for item in SCENARIOS)
    planner = build_call_manifest(_request("planner_only", scenario_ids=scenario_ids))
    analyst = build_call_manifest(_request("analyst_only", scenario_ids=scenario_ids))
    combined = build_call_manifest(_request("combined", scenario_ids=scenario_ids))
    assert planner.calls_by_role == {
        ROLE_COMPONENT_ANALYST: 0,
        ROLE_CROSS_COMPONENT_ANALYST: 0,
        ROLE_SEARCH_PLANNER: 7,
    }
    assert analyst.calls_by_role == {
        ROLE_COMPONENT_ANALYST: 16,
        ROLE_CROSS_COMPONENT_ANALYST: 13,
        ROLE_SEARCH_PLANNER: 0,
    }
    assert combined.calls_by_role == {
        ROLE_COMPONENT_ANALYST: 16,
        ROLE_CROSS_COMPONENT_ANALYST: 13,
        ROLE_SEARCH_PLANNER: 7,
    }
    assert planner.total_maximum_physical_model_calls == 7
    assert analyst.total_maximum_physical_model_calls == 29
    assert combined.total_maximum_physical_model_calls == 36
    assert combined.maximum_scryraven_runs == 7
    assert combined.calls_by_pass == {"combined": 36}
    assert combined.retry_allowance == 0
    assert combined.conditional_call_ids


def test_case_5_balanced_and_deep_serial_policy_are_unchanged() -> None:
    case_5 = SCENARIO_EXPECTATIONS[CASE_5]
    assert SCENARIO_BY_ID[CASE_5].mode == "Balanced"
    assert case_5.expected_status == BOUNDED_LIMIT
    assert case_5.expected_search_generations == 1
    assert case_5.rejected_search_generation == 2
    assert case_5.component_call_concepts == (
        "solace_regional_flag",
        "solace_certificate",
    )
    assert case_5.cross_calls[1].classification == "searched_premise"
    assert case_5.cross_calls[1].conditional_skip_reason

    for scenario_id in (CASE_3, CASE_4, CASE_6, CASE_7):
        expectation = SCENARIO_EXPECTATIONS[scenario_id]
        assert SCENARIO_BY_ID[scenario_id].mode == "Deep"
        inferred_depths = [
            item.semantic_inference_depth
            for item in expectation.cross_calls
            if item.classification == "inferred_conclusion"
        ]
        assert all(depth <= 2 for depth in inferred_depths)
        for prior, later in zip(
            expectation.cross_calls,
            expectation.cross_calls[1:],
            strict=False,
        ):
            if later.semantic_inference_depth:
                assert later.conditional_skip_reason or prior.semantic_inference_depth


def test_execute_without_complete_authorization_fails_before_transport(
    tmp_path: Path,
) -> None:
    factory = FactoryCensus()
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=_repo_output_path(tmp_path, "result.json"),
    )
    with pytest.raises(EvaluationConfigurationError, match="live addendum"):
        run_evaluation(
            request,
            repository_sha=REPOSITORY_SHA,
            transport_factory=factory,
        )
    assert factory.calls == 0


def test_over_cap_authorization_fails_before_transport(tmp_path: Path) -> None:
    output = _repo_output_path(tmp_path, "result.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    factory = FactoryCensus()
    authorization = _authorization(
        request,
        output=output,
        maximum_model_calls=0,
    )
    with pytest.raises(EvaluationConfigurationError, match="maximum model calls"):
        run_evaluation(
            request,
            repository_sha=REPOSITORY_SHA,
            authorization=authorization,
            execution_identity=_execution_identity(request),
            transport_factory=factory,
        )
    assert factory.calls == 0


@pytest.mark.parametrize(
    ("evaluation_pass", "roles", "expected_roles"),
    (
        (
            "planner_only",
            (),
            {ROLE_SEARCH_PLANNER},
        ),
        (
            "analyst_only",
            (ROLE_COMPONENT_ANALYST,),
            {ROLE_COMPONENT_ANALYST},
        ),
        (
            "analyst_only",
            (ROLE_CROSS_COMPONENT_ANALYST,),
            {ROLE_CROSS_COMPONENT_ANALYST},
        ),
        (
            "analyst_only",
            (),
            {ROLE_COMPONENT_ANALYST, ROLE_CROSS_COMPONENT_ANALYST},
        ),
        (
            "combined",
            (),
            MODEL_ROLES,
        ),
    ),
)
def test_synthetic_execute_invokes_only_selected_model_boundaries(
    tmp_path: Path,
    evaluation_pass: str,
    roles: tuple[str, ...],
    expected_roles: set[str],
) -> None:
    output = _repo_output_path(tmp_path, f"{evaluation_pass}-{len(roles)}.json")
    request = _request(
        evaluation_pass,
        execution_mode="execute",
        scenario_ids=(CASE_3,),
        roles=roles,
        output=output,
    )
    authorization = _authorization(request, output=output)
    factory = FactoryCensus()
    packet = run_evaluation(
        request,
        repository_sha=REPOSITORY_SHA,
        authorization=authorization,
        execution_identity=_execution_identity(request),
        transport_factory=factory,
        scenario_runner=_synthetic_scenario_runner,
    )
    assert factory.calls == 1
    assert {item["role"] for item in factory.transport.calls} == expected_roles
    assert ROLE_SEARCH_PLANNER not in expected_roles or all(
        item["role"] != ROLE_COMPONENT_ANALYST for item in factory.transport.calls if evaluation_pass == "planner_only"
    )
    assert packet["call_counts"]["model_calls"] == len(factory.transport.calls)
    assert packet["call_counts"]["search_calls"] == 0
    assert packet["call_counts"]["retrieval_calls"] == 0
    assert packet["call_counts"]["read_calls"] == 0
    assert packet["call_counts"]["navigation_calls"] == 0
    assert packet["retry_counts"] == {"total": 0}
    assert packet["credentials_accessed"] is False
    assert Path(output).is_file()


def test_unmanifested_extra_call_is_blocked_before_transport(
    tmp_path: Path,
) -> None:
    output = _repo_output_path(tmp_path, "extra-call.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    authorization = _authorization(request, output=output)
    factory = FactoryCensus()

    def runner(
        *,
        scenario_id: str,
        controller: BoundaryInjectionController,
    ) -> ScenarioRunResult:
        result = _synthetic_scenario_runner(
            scenario_id=scenario_id,
            controller=controller,
        )
        calls_before = len(factory.transport.calls)
        with pytest.raises(EvaluationTransportError) as local_error:
            controller.invoke(
                role=ROLE_SEARCH_PLANNER,
                prompt="{}",
                system_prompt="synthetic",
                provider=authorization.provider,
                model=authorization.model,
            )
        assert not isinstance(
            local_error.value,
            IncompleteModelBoundaryPacketError,
        )
        assert len(factory.transport.calls) == calls_before
        return result

    Path(output).unlink(missing_ok=True)
    with pytest.raises(EvaluationTransportError) as raised:
        run_evaluation(
            request,
            repository_sha=REPOSITORY_SHA,
            authorization=authorization,
            execution_identity=_execution_identity(request),
            transport_factory=factory,
            scenario_runner=runner,
        )
    assert not isinstance(raised.value, IncompleteModelBoundaryPacketError)
    assert len(factory.transport.calls) == 1
    assert not Path(output).exists()


@pytest.mark.parametrize(
    "failure_kind",
    (
        "first_call_provider_failure",
        "input_token_cap",
        "output_token_cap",
        "cost_ceiling",
        "provider_retry_accounting",
    ),
)
def test_execution_envelope_failure_propagates_without_result_packet(
    tmp_path: Path,
    failure_kind: str,
) -> None:
    output = _repo_output_path(tmp_path, f"{failure_kind}.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    authorization = _authorization(request, output=output)
    transport = FakeTransport()
    transport.next_output = {
        "private_transient_provider_material": "must never reach a packet",
    }
    if failure_kind == "first_call_provider_failure":
        transport.failure = RuntimeError("synthetic provider failure")
    elif failure_kind == "input_token_cap":
        transport.input_tokens = authorization.maximum_input_tokens + 1
    elif failure_kind == "output_token_cap":
        transport.output_tokens = authorization.maximum_output_tokens + 1
    elif failure_kind == "cost_ceiling":
        transport.cost = authorization.cost_ceiling + 0.01
    else:
        transport.provider_request_attempt_count = 2
    factory = FactoryCensus(transport=transport)

    Path(output).unlink(missing_ok=True)
    with pytest.raises(EvaluationTransportError) as raised:
        run_evaluation(
            request,
            repository_sha=REPOSITORY_SHA,
            authorization=authorization,
            execution_identity=_execution_identity(request),
            transport_factory=factory,
            scenario_runner=_synthetic_scenario_runner,
        )

    assert not isinstance(raised.value, IncompleteModelBoundaryPacketError)
    assert factory.calls == 1
    assert len(transport.calls) == 1
    assert not Path(output).exists()


def test_retry_exhaustion_propagates_without_result_packet(
    tmp_path: Path,
) -> None:
    output = _repo_output_path(tmp_path, "retry-exhaustion.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    authorization = _authorization(
        request,
        output=output,
        retry_cap=1,
    )
    transport = FakeTransport()
    transport.failure = RuntimeError("synthetic retryable provider failure")

    Path(output).unlink(missing_ok=True)
    with pytest.raises(EvaluationTransportError):
        run_evaluation(
            request,
            repository_sha=REPOSITORY_SHA,
            authorization=authorization,
            execution_identity=_execution_identity(request),
            transport_factory=FactoryCensus(transport=transport),
            scenario_runner=_synthetic_scenario_runner,
        )

    assert len(transport.calls) == 2
    assert not Path(output).exists()


def test_call_budget_exhaustion_propagates_without_result_packet(
    tmp_path: Path,
) -> None:
    output = _repo_output_path(tmp_path, "call-budget-exhaustion.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    authorization = _authorization(request, output=output)
    transport = FakeTransport()

    def runner(
        *,
        scenario_id: str,
        controller: BoundaryInjectionController,
    ) -> ScenarioRunResult:
        controller.budget_ledger.physical_calls = authorization.maximum_model_calls
        controller.invoke(
            role=ROLE_SEARCH_PLANNER,
            prompt=(
                "Sanitized planner input JSON: "
                + json.dumps(
                    {
                        "scenario_id": scenario_id,
                        "root_query": SCENARIO_BY_ID[scenario_id].root_query,
                    }
                )
            ),
            system_prompt=SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
            provider=authorization.provider,
            model=authorization.model,
        )
        pytest.fail("exhausted call budget returned to the scenario runner")

    Path(output).unlink(missing_ok=True)
    with pytest.raises(EvaluationTransportError):
        run_evaluation(
            request,
            repository_sha=REPOSITORY_SHA,
            authorization=authorization,
            execution_identity=_execution_identity(request),
            transport_factory=FactoryCensus(transport=transport),
            scenario_runner=runner,
        )

    assert transport.calls == []
    assert not Path(output).exists()


def test_incomplete_boundary_packet_is_classified_before_transport(
    tmp_path: Path,
) -> None:
    output = _repo_output_path(tmp_path, "incomplete-packet.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    authorization = _authorization(request, output=output)
    factory = FactoryCensus()

    def runner(
        *,
        scenario_id: str,
        controller: BoundaryInjectionController,
    ) -> ScenarioRunResult:
        del scenario_id
        controller.invoke(
            role=ROLE_SEARCH_PLANNER,
            prompt="Sanitized planner input JSON: {}",
            system_prompt=SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
            provider=authorization.provider,
            model=authorization.model,
        )
        raise AssertionError("incomplete packet must fail closed")

    packet = run_evaluation(
        request,
        repository_sha=REPOSITORY_SHA,
        authorization=authorization,
        execution_identity=_execution_identity(request),
        transport_factory=factory,
        scenario_runner=runner,
    )
    assert packet["primary_failure_attribution"] == "PACKET"
    assert packet["call_counts"]["model_calls"] == 0
    assert factory.transport.calls == []
    scenario_packet = packet["observed_safe_semantic_projection"][0]
    assert scenario_packet["runner_failure_type"] == "IncompleteModelBoundaryPacketError"
    assert scenario_packet["observed_safe_semantic_projection"][0]["physical_calls"] == 0
    assert Path(output).is_file()


def test_semantic_scorer_checks_root_retention_and_distractor_resistance() -> None:
    call = build_call_manifest(
        _request(
            "planner_only",
            scenario_ids=(CASE_6,),
        )
    ).calls[0]
    valid = _planner_output(CASE_6)
    projection, status = project_and_score_role_output(
        ROLE_SEARCH_PLANNER,
        valid,
        call=call,
    )
    assert status == "met"
    assert projection["checks"]["root_query_interpretation"] is True
    assert projection["checks"]["distractor_resistance"] is True

    distracted = dict(valid)
    distracted["requested_output"] = f"{distracted['requested_output']} using the 2025 Atlantic price per litre"
    projection, status = project_and_score_role_output(
        ROLE_SEARCH_PLANNER,
        distracted,
        call=call,
    )
    assert status == "wrong"
    assert projection["checks"]["distractor_resistance"] is False


def test_model_authored_canonical_authority_is_not_a_pass(
    tmp_path: Path,
) -> None:
    output = _repo_output_path(tmp_path, "authority-violation.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    authorization = _authorization(request, output=output)
    factory = FactoryCensus()

    def runner(
        *,
        scenario_id: str,
        controller: BoundaryInjectionController,
    ) -> ScenarioRunResult:
        factory.transport.next_output = {
            **_planner_output(scenario_id),
            "canonical_state": {"admitted": True},
        }
        controller.invoke(
            role=ROLE_SEARCH_PLANNER,
            prompt=(
                "Synthetic boundary fixture.\nSanitized planner input JSON:\n" + SCENARIO_BY_ID[scenario_id].root_query
            ),
            system_prompt=SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
            provider=authorization.provider,
            model=authorization.model,
        )
        return ScenarioRunResult(
            scenario_id=scenario_id,
            ordinary_downstream_terminal_posture="synthetic_not_admitted",
            operating_system_transition_reached=False,
        )

    packet = run_evaluation(
        request,
        repository_sha=REPOSITORY_SHA,
        authorization=authorization,
        execution_identity=_execution_identity(request),
        transport_factory=factory,
        scenario_runner=runner,
    )
    assert packet["primary_failure_attribution"] == "MODEL"
    assert packet["structural_score"]["status"] == "FAIL"
    assert (
        packet["observed_safe_semantic_projection"][0]["observed_safe_semantic_projection"][0][
            "authority_boundary_respected"
        ]
        is False
    )
    assert "canonical_state" not in json.dumps(packet)


def test_raw_prompts_and_responses_never_enter_result_packet(
    tmp_path: Path,
) -> None:
    output = _repo_output_path(tmp_path, "redacted.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    authorization = _authorization(request, output=output)
    packet = run_evaluation(
        request,
        repository_sha=REPOSITORY_SHA,
        authorization=authorization,
        execution_identity=_execution_identity(request),
        transport_factory=FactoryCensus(),
        scenario_runner=_synthetic_scenario_runner,
    )
    serialized = json.dumps(packet, sort_keys=True).casefold()
    for forbidden in (
        '"raw_prompt"',
        '"raw_model_response"',
        '"provider_payload"',
        '"prompt_text"',
        '"model_response"',
        '"api_key"',
        '"secret"',
        '"chain_of_thought"',
    ):
        assert forbidden not in serialized
    reject_forbidden_packet_material(packet)


def test_every_primary_classification_and_prompt_counterfactual_rule() -> None:
    observation = _probe_observation()
    paired = _matching_probe(observation)
    assert (
        paired_probe_demonstrates_prompt_causality(
            paired,
            observation=observation,
        )
        is True
    )
    cases = {
        "PASS": ClassificationEvidence(True, True, True, "met", True),
        "MODEL": ClassificationEvidence(True, True, True, "wrong", False),
        "PACKET": ClassificationEvidence(True, False, False, "ambiguous", False),
        "PROMPT": ClassificationEvidence(
            True,
            True,
            True,
            "wrong",
            False,
            paired,
            boundary_observation=observation,
        ),
        "PARSER_CONTRACT": ClassificationEvidence(
            True,
            True,
            False,
            "met",
            False,
        ),
        "OPERATING_SYSTEM": ClassificationEvidence(
            True,
            True,
            True,
            "met",
            False,
        ),
        "REVIEW_REQUIRED": ClassificationEvidence(
            True,
            True,
            True,
            "ambiguous",
            False,
        ),
        "NOT_RUN": ClassificationEvidence(
            False,
            True,
            True,
            "met",
            False,
            not_run_reason="execution_mode=plan_only",
        ),
    }
    assert set(cases) == CLASSIFICATIONS
    assert {name: classify_result(value) for name, value in cases.items()} == {name: name for name in cases}
    wrong_without_counterfactual = ClassificationEvidence(
        True,
        True,
        True,
        "wrong",
        False,
    )
    assert classify_result(wrong_without_counterfactual) == "MODEL"
    incomplete_probe = replace(paired, variant_semantic_status="wrong")
    assert (
        paired_probe_demonstrates_prompt_causality(
            incomplete_probe,
            observation=observation,
        )
        is False
    )
    assert (
        classify_result(
            ClassificationEvidence(
                True,
                True,
                True,
                "wrong",
                False,
                incomplete_probe,
                boundary_observation=observation,
            )
        )
        == "MODEL"
    )


def test_ambiguous_mapping_returns_review_required() -> None:
    assert (
        classify_result(
            ClassificationEvidence(
                call_ran=True,
                packet_complete=True,
                parser_consumable=True,
                semantic_status="ambiguous",
                operating_system_transition_reached=False,
            )
        )
        == "REVIEW_REQUIRED"
    )


def test_sample_packets_cover_every_classification_and_are_sanitized() -> None:
    packets = {classification: sample_classification_packet(classification) for classification in CLASSIFICATIONS}
    assert {item["primary_failure_attribution"] for item in packets.values()} == CLASSIFICATIONS
    for packet in packets.values():
        reject_forbidden_packet_material(packet)
        assert packet["redaction_posture"]["raw_prompts_retained"] is False
        assert packet["redaction_posture"]["raw_model_responses_retained"] is False


def test_proposed_live_addendum_has_every_required_placeholder() -> None:
    template = proposed_live_addendum_template(
        repository_sha=REPOSITORY_SHA,
        output_packet_path="output/analystos-model-origination.json",
    )
    assert template["repository_sha"] == REPOSITORY_SHA
    assert template["retry_cap"] == 0
    assert template["raw_retention_posture"] == "sanitized_only"
    for field in (
        "provider",
        "model",
        "allowed_evaluation_pass",
        "allowed_model_roles",
        "allowed_scenario_ids",
        "maximum_model_calls",
        "maximum_scryraven_runs",
        "maximum_input_tokens",
        "maximum_output_tokens",
        "cost_ceiling",
        "transport_factory_spec",
        "canonical_operator_command",
        "canonical_operator_command_digest",
        "output_packet_path",
        "decision",
        "stop_condition",
    ):
        assert field in template


def test_operator_source_has_no_environment_or_provider_route_lookup() -> None:
    source = Path("scripts/evaluation/run_analystos_model_origination_evaluation.py").read_text(encoding="utf-8")
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "load_dotenv" not in source
    assert "OPENAI_API_KEY" not in source
    assert "OPENROUTER_API_KEY" not in source
    assert "search_providers" not in source
    assert "acquisition_transports" not in source
    assert "ROLE_COMPONENT_DPRIME" not in source
    assert "ROLE_SYNTHESIS_DPRIME" not in source


def test_expectations_reuse_all_seven_merged_scenarios() -> None:
    assert tuple(SCENARIO_EXPECTATIONS) == tuple(item.scenario_id for item in SCENARIOS)
    assert SCENARIO_EXPECTATIONS[CASE_6].distractor_concepts
    assert SCENARIO_EXPECTATIONS[CASE_7].honest_nonclosure is True


def _write_cli_addendum(
    tmp_path: Path,
    *,
    evaluation_pass: str = "planner_only",
    scenario_ids: tuple[str, ...] = (CASE_1,),
    roles: tuple[str, ...] = (),
    transport_factory_spec: str = SYNTHETIC_TRANSPORT_FACTORY_SPEC,
) -> tuple[EvaluationRequest, LiveAuthorization, ExecutionIdentity, Path]:
    output = _repo_output_path(tmp_path, "canonical-result.json")
    addendum_path = Path(_repo_output_path(tmp_path, "live-addendum.json"))
    request = _request(
        evaluation_pass,
        execution_mode="execute",
        scenario_ids=scenario_ids,
        roles=roles,
        output=output,
    )
    repository_sha = current_repository_sha()
    authorization = _authorization(
        request,
        output=output,
        repository_sha=repository_sha,
        live_addendum_path=str(addendum_path),
        transport_factory_spec=transport_factory_spec,
    )
    identity = _execution_identity(
        request,
        repository_sha=repository_sha,
        live_addendum_path=str(addendum_path),
        transport_factory_spec=transport_factory_spec,
    )
    addendum_path.parent.mkdir(parents=True, exist_ok=True)
    addendum_path.write_text(
        json.dumps(asdict(authorization), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return request, authorization, identity, addendum_path


def test_live_addendum_rejects_unknown_and_missing_execution_identity_fields(
    tmp_path: Path,
) -> None:
    _, authorization, _, _ = _write_cli_addendum(tmp_path)
    value = asdict(authorization)
    with pytest.raises(EvaluationConfigurationError, match="unknown field"):
        LiveAuthorization.from_mapping({**value, "unlicensed_alias": "forbidden"})
    for field in (
        "transport_factory_spec",
        "canonical_operator_command",
        "canonical_operator_command_digest",
    ):
        incomplete = dict(value)
        incomplete.pop(field)
        with pytest.raises(EvaluationConfigurationError, match="incomplete"):
            LiveAuthorization.from_mapping(incomplete)


@pytest.mark.parametrize(
    "field",
    (
        "allowed_model_roles",
        "allowed_scenario_ids",
    ),
)
def test_live_addendum_rejects_duplicate_ordered_selectors(
    tmp_path: Path,
    field: str,
) -> None:
    _, authorization, _, _ = _write_cli_addendum(tmp_path)
    value = asdict(authorization)
    value[field] = [*value[field], value[field][0]]
    with pytest.raises(EvaluationConfigurationError, match="duplicates"):
        LiveAuthorization.from_mapping(value)


@pytest.mark.parametrize(
    "field",
    (
        "allowed_model_roles",
        "allowed_scenario_ids",
    ),
)
def test_live_addendum_rejects_unordered_selectors(
    tmp_path: Path,
    field: str,
) -> None:
    request, authorization, identity, _ = _write_cli_addendum(
        tmp_path,
        evaluation_pass="combined",
        scenario_ids=(CASE_3, CASE_4),
    )
    reordered = replace(
        authorization,
        **{field: tuple(reversed(getattr(authorization, field)))},
    )
    with pytest.raises(EvaluationConfigurationError, match="set/order"):
        evaluator.validate_live_authorization(
            request,
            reordered,
            repository_sha=current_repository_sha(),
            execution_identity=identity,
        )


def test_canonical_licensed_cli_and_factory_succeed_with_fake_transport(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, _, identity, _ = _write_cli_addendum(tmp_path)
    CLI_FACTORY_CENSUS.calls = 0
    CLI_FACTORY_CENSUS.transport = FakeTransport()
    CLI_FACTORY_CENSUS.transport.next_output = _planner_output(CASE_1)

    assert main(identity.canonical_argv) == 0

    packet = json.loads(capsys.readouterr().out)
    assert CLI_FACTORY_CENSUS.calls == 1
    assert packet["execution_identity_digest"] == identity.execution_identity_digest
    assert packet["canonical_operator_command_digest"] == identity.canonical_operator_command_digest
    assert packet["transport_factory_spec"] == SYNTHETIC_TRANSPORT_FACTORY_SPEC
    assert packet["primary_failure_attribution"] == "PASS"


def test_cli_transport_failure_is_nonzero_and_writes_no_result_packet(
    tmp_path: Path,
) -> None:
    module_stem = "analystos_cli_failure_" + "".join(
        character if character.isalnum() else "_" for character in tmp_path.name
    )
    module_path = Path("output") / f"{module_stem}.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    factory_spec = f"output.{module_stem}:provider_failure_factory"
    private_sentinel = "PRIVATE_TRANSIENT_PROVIDER_FAILURE_MATERIAL"
    module_path.write_text(
        "\n".join(
            (
                "class ProviderFailureTransport:",
                "    credentials_accessed = False",
                "",
                "    def __call__(self, **_kwargs):",
                f"        raise RuntimeError({private_sentinel!r})",
                "",
                "",
                "def provider_failure_factory(_authorization):",
                "    return ProviderFailureTransport()",
                "",
            )
        ),
        encoding="utf-8",
    )
    request, _, identity, _ = _write_cli_addendum(
        tmp_path,
        transport_factory_spec=factory_spec,
    )
    assert request.output_packet_path is not None
    output = Path(request.output_packet_path)
    output.unlink(missing_ok=True)

    try:
        completed = subprocess.run(
            [sys.executable, *identity.canonical_argv],
            cwd=Path.cwd(),
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        module_path.unlink(missing_ok=True)

    assert completed.returncode == 2, completed.stdout
    assert completed.stdout == ""
    assert completed.stderr.startswith("ERROR: ")
    assert private_sentinel not in completed.stderr
    assert not output.exists()


def test_direct_script_accepts_package_typed_transport_response(
    tmp_path: Path,
) -> None:
    module_stem = "analystos_cli_package_response_" + "".join(
        character if character.isalnum() else "_" for character in tmp_path.name
    )
    module_path = Path("output") / f"{module_stem}.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    factory_spec = f"output.{module_stem}:package_typed_transport_factory"
    planner_output = json.dumps(
        _planner_output(CASE_1),
        separators=(",", ":"),
    )
    module_path.write_text(
        "\n".join(
            (
                "from scripts.evaluation.run_analystos_model_origination_evaluation import EvaluationTransportResponse",
                "",
                "",
                "class PackageTypedTransport:",
                "    credentials_accessed = False",
                "",
                "    def __call__(self, **kwargs):",
                "        return EvaluationTransportResponse(",
                f"            output={planner_output!r},",
                "            input_tokens=10,",
                "            output_tokens=10,",
                "            cost=0.0,",
                "            canonical_provider_used=str(kwargs['provider']),",
                "            canonical_model_used=str(kwargs['model']),",
                "            credentials_accessed=False,",
                "        )",
                "",
                "",
                "def package_typed_transport_factory(_authorization):",
                "    return PackageTypedTransport()",
                "",
            )
        ),
        encoding="utf-8",
    )
    request, _, identity, _ = _write_cli_addendum(
        tmp_path,
        transport_factory_spec=factory_spec,
    )
    assert request.output_packet_path is not None
    output = Path(request.output_packet_path)
    output.unlink(missing_ok=True)

    try:
        completed = subprocess.run(
            [sys.executable, *identity.canonical_argv],
            cwd=Path.cwd(),
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        module_path.unlink(missing_ok=True)

    assert completed.returncode == 0, completed.stderr
    packet = json.loads(completed.stdout)
    assert packet["primary_failure_attribution"] == "PASS"
    assert packet["call_counts"]["model_calls"] == 1
    assert output.exists()


def test_direct_script_catches_package_typed_factory_failure(
    tmp_path: Path,
) -> None:
    module_stem = "analystos_cli_package_failure_" + "".join(
        character if character.isalnum() else "_" for character in tmp_path.name
    )
    module_path = Path("output") / f"{module_stem}.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    factory_spec = f"output.{module_stem}:package_typed_failure_factory"
    module_path.write_text(
        "\n".join(
            (
                "from scripts.evaluation.run_analystos_model_origination_evaluation import EvaluationTransportError",
                "",
                "",
                "def package_typed_failure_factory(_authorization):",
                "    raise EvaluationTransportError('sanitized construction failure')",
                "",
            )
        ),
        encoding="utf-8",
    )
    request, _, identity, _ = _write_cli_addendum(
        tmp_path,
        transport_factory_spec=factory_spec,
    )
    assert request.output_packet_path is not None
    output = Path(request.output_packet_path)
    output.unlink(missing_ok=True)

    try:
        completed = subprocess.run(
            [sys.executable, *identity.canonical_argv],
            cwd=Path.cwd(),
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        module_path.unlink(missing_ok=True)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "ERROR: sanitized construction failure\n"
    assert not output.exists()


def test_different_transport_factory_fails_before_import_or_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, identity, _ = _write_cli_addendum(tmp_path)
    unauthorized = "test_analystos_model_origination_evaluation_prep_01:unauthorized_transport_factory"
    actual = list(identity.canonical_argv)
    actual[actual.index(SYNTHETIC_TRANSPORT_FACTORY_SPEC)] = unauthorized
    import_attempts = 0

    def reject_import(_module: str) -> None:
        nonlocal import_attempts
        import_attempts += 1
        raise AssertionError("factory import must remain unreachable")

    monkeypatch.setattr(evaluator.importlib, "import_module", reject_import)
    CLI_FACTORY_CENSUS.calls = 0
    with pytest.raises(EvaluationConfigurationError, match="transport factory spec"):
        main(actual)
    assert import_attempts == 0
    assert CLI_FACTORY_CENSUS.calls == 0


def test_noncanonical_selector_commands_fail_before_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, identity, _ = _write_cli_addendum(
        tmp_path,
        evaluation_pass="combined",
        scenario_ids=(CASE_3, CASE_4),
    )
    canonical = list(identity.canonical_argv)
    scenario_start = canonical.index("--scenario")
    addendum_start = canonical.index("--live-addendum")
    reordered = (
        canonical[:scenario_start]
        + canonical[scenario_start + 2 : addendum_start]
        + canonical[scenario_start : scenario_start + 2]
        + canonical[addendum_start:]
    )
    omitted = canonical[:scenario_start] + canonical[scenario_start + 2 :]
    added = canonical[:addendum_start] + ["--scenario", CASE_3] + canonical[addendum_start:]
    changed = list(canonical)
    changed[scenario_start + 1] = CASE_6
    changed_entrypoint = list(canonical)
    changed_entrypoint[0] = "scripts/evaluation/another_operator.py"

    monkeypatch.setattr(
        evaluator.importlib,
        "import_module",
        lambda _module: pytest.fail("factory import must remain unreachable"),
    )
    CLI_FACTORY_CENSUS.calls = 0
    for actual in (reordered, omitted, added, changed, changed_entrypoint):
        with pytest.raises(EvaluationConfigurationError):
            main(actual)
    assert CLI_FACTORY_CENSUS.calls == 0


def test_direct_factory_implementation_must_match_execution_identity(
    tmp_path: Path,
) -> None:
    output = _repo_output_path(tmp_path, "direct-factory.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    authorization = _authorization(request, output=output)
    factory = FactoryCensus(
        transport_factory_spec=("test_analystos_model_origination_evaluation_prep_01:different_factory")
    )
    with pytest.raises(EvaluationConfigurationError, match="implementation"):
        run_evaluation(
            request,
            repository_sha=REPOSITORY_SHA,
            authorization=authorization,
            execution_identity=_execution_identity(request),
            transport_factory=factory,
        )
    assert factory.calls == 0


@pytest.mark.parametrize(
    ("attestation_field", "wrong_value"),
    (
        ("canonical_provider_used", "another-provider"),
        ("canonical_model_used", "another-model"),
    ),
)
def test_transport_route_attestation_mismatch_fails_closed(
    tmp_path: Path,
    attestation_field: str,
    wrong_value: str,
) -> None:
    output = _repo_output_path(tmp_path, f"{attestation_field}.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        output=output,
    )
    authorization = _authorization(request, output=output)
    transport = FakeTransport()
    transport.next_output = _planner_output(CASE_1)
    setattr(transport, attestation_field, wrong_value)
    factory = FactoryCensus(transport=transport)
    Path(output).unlink(missing_ok=True)
    with pytest.raises(EvaluationRouteAttestationError, match="attested"):
        run_evaluation(
            request,
            repository_sha=REPOSITORY_SHA,
            authorization=authorization,
            execution_identity=_execution_identity(request),
            transport_factory=factory,
            scenario_runner=_synthetic_scenario_runner,
        )
    assert factory.calls == 1
    assert len(transport.calls) == 1
    assert not Path(output).exists()


@pytest.mark.parametrize(
    ("field", "different_value"),
    (
        ("execution_identity_digest", "0" * 64),
        ("evaluation_id", "1" * 64),
        ("scenario_id", CASE_4),
        ("call_id", f"{CASE_3}:search_planner:99"),
        ("model_role", ROLE_SEARCH_PLANNER),
        ("provider", "another-provider"),
        ("model", "another-model"),
        ("semantic_input_facts_digest", "2" * 64),
        ("maximum_physical_calls_each", 2),
        ("maximum_input_tokens_each", 3_999),
        ("maximum_output_tokens_each", 1_999),
        ("retry_cap_each", 1),
        ("same_scenario", False),
        ("same_route", False),
        ("same_semantic_facts", False),
        ("exactly_one_controlled_instruction_dimension_differs", False),
        ("deterministic_comparison_criteria", ()),
        ("variant_semantic_status", "wrong"),
    ),
)
def test_inexact_paired_probe_cannot_reclassify_model_failure_as_prompt(
    field: str,
    different_value: Any,
) -> None:
    observation = _probe_observation()
    probe = replace(_matching_probe(observation), **{field: different_value})
    evidence = ClassificationEvidence(
        call_ran=True,
        packet_complete=True,
        parser_consumable=True,
        semantic_status="wrong",
        operating_system_transition_reached=False,
        paired_probe=probe,
        boundary_observation=observation,
    )
    assert (
        paired_probe_demonstrates_prompt_causality(
            probe,
            observation=observation,
        )
        is False
    )
    assert classify_result(evidence) == "MODEL"


@pytest.mark.parametrize(
    ("changes", "expected"),
    (
        ({"packet_complete": False}, "PACKET"),
        (
            {
                "parser_consumable": False,
                "semantic_status": "met",
            },
            "PARSER_CONTRACT",
        ),
        ({"authority_boundary_respected": False}, "MODEL"),
        (
            {
                "semantic_status": "met",
                "operating_system_transition_reached": False,
            },
            "OPERATING_SYSTEM",
        ),
    ),
)
def test_attribution_precedence_cannot_be_overridden_by_probe(
    changes: dict[str, Any],
    expected: str,
) -> None:
    observation = _probe_observation()
    values: dict[str, Any] = {
        "call_ran": True,
        "packet_complete": True,
        "parser_consumable": True,
        "semantic_status": "wrong",
        "operating_system_transition_reached": False,
        "paired_probe": _matching_probe(observation),
        "authority_boundary_respected": True,
        "boundary_observation": observation,
    }
    values.update(changes)
    assert classify_result(ClassificationEvidence(**values)) == expected


@pytest.mark.parametrize(
    ("semantic_status", "expected"),
    (
        ("met", "PARSER_CONTRACT"),
        ("wrong", "MODEL"),
        ("ambiguous", "REVIEW_REQUIRED"),
    ),
)
def test_parser_attribution_uses_the_semantic_status_matrix(
    semantic_status: str,
    expected: str,
) -> None:
    observation = replace(
        _probe_observation(),
        parser_consumable=False,
        semantic_status=semantic_status,
    )
    assert (
        classify_result(
            ClassificationEvidence(
                call_ran=True,
                packet_complete=True,
                parser_consumable=False,
                semantic_status=semantic_status,
                operating_system_transition_reached=False,
                paired_probe=_matching_probe(observation),
                authority_boundary_respected=True,
                boundary_observation=observation,
            )
        )
        == expected
    )


@pytest.mark.parametrize(
    "semantic_status",
    (
        "met",
        "wrong",
        "ambiguous",
    ),
)
def test_authority_violation_remains_model_with_any_parser_posture(
    semantic_status: str,
) -> None:
    observation = replace(
        _probe_observation(),
        parser_consumable=False,
        semantic_status=semantic_status,
        authority_boundary_respected=False,
    )
    assert (
        classify_result(
            ClassificationEvidence(
                call_ran=True,
                packet_complete=True,
                parser_consumable=False,
                semantic_status=semantic_status,
                operating_system_transition_reached=False,
                paired_probe=_matching_probe(observation),
                authority_boundary_respected=False,
                boundary_observation=observation,
            )
        )
        == "MODEL"
    )


def test_only_fully_matching_probe_produces_prompt() -> None:
    observation = _probe_observation()
    assert (
        classify_result(
            ClassificationEvidence(
                call_ran=True,
                packet_complete=True,
                parser_consumable=True,
                semantic_status="wrong",
                operating_system_transition_reached=False,
                paired_probe=_matching_probe(observation),
                boundary_observation=observation,
            )
        )
        == "PROMPT"
    )


def test_exact_probe_cannot_reclassify_an_unrelated_call_failure() -> None:
    matched_observation = _probe_observation()
    unrelated_observation = replace(
        matched_observation,
        call_id=f"{CASE_3}:cross_component_analyst:2",
    )
    classification, per_call = evaluator._classification_from_observations(  # noqa: SLF001
        (matched_observation, unrelated_observation),
        operating_system_transition_reached=False,
        runner_failed=False,
        paired_probes_by_call_id={
            matched_observation.call_id: _matching_probe(matched_observation),
        },
    )
    assert classification == "MODEL"
    assert [item["primary_failure_attribution"] for item in per_call] == [
        "PROMPT",
        "MODEL",
    ]
    assert [item["paired_probe_supplied"] for item in per_call] == [
        True,
        False,
    ]


@pytest.mark.parametrize(
    (
        "evaluation_pass",
        "scenario_id",
        "roles",
        "expected_selected_roles",
    ),
    (
        (
            "planner_only",
            CASE_3,
            (),
            {ROLE_SEARCH_PLANNER},
        ),
        (
            "analyst_only",
            CASE_4,
            (),
            {ROLE_COMPONENT_ANALYST, ROLE_CROSS_COMPONENT_ANALYST},
        ),
        (
            "combined",
            CASE_6,
            (),
            MODEL_ROLES,
        ),
        (
            "combined",
            CASE_7,
            (),
            MODEL_ROLES,
        ),
    ),
)
def test_default_runner_enters_merged_ordinary_fixture_with_fake_transport(
    tmp_path: Path,
    evaluation_pass: str,
    scenario_id: str,
    roles: tuple[str, ...],
    expected_selected_roles: set[str],
) -> None:
    output = _repo_output_path(
        tmp_path,
        f"default-{evaluation_pass}-{scenario_id}.json",
    )
    request = _request(
        evaluation_pass,
        execution_mode="execute",
        scenario_ids=(scenario_id,),
        roles=roles,
        output=output,
    )
    authorization = _authorization(request, output=output)
    transport = OrdinaryFixtureFakeTransport(
        scenario_id=scenario_id,
        tmp_path=tmp_path,
    )
    factory = FactoryCensus(transport=transport)

    packet = run_evaluation(
        request,
        repository_sha=REPOSITORY_SHA,
        authorization=authorization,
        execution_identity=_execution_identity(request),
        transport_factory=factory,
    )
    scenario_packet = packet["observed_safe_semantic_projection"][0]

    expectation = SCENARIO_EXPECTATIONS[scenario_id]
    expected_calls = (
        (1 if ROLE_SEARCH_PLANNER in expected_selected_roles else 0)
        + (len(expectation.component_call_concepts) if ROLE_COMPONENT_ANALYST in expected_selected_roles else 0)
        + (len(expectation.cross_calls) if ROLE_CROSS_COMPONENT_ANALYST in expected_selected_roles else 0)
    )
    assert scenario_packet["runner_failure_type"] is None, scenario_packet
    assert factory.calls == 1
    assert packet["call_counts"]["ordinary_model_boundary_dispatches"] > 0, packet["call_counts"]
    assert packet["call_counts"]["ordinary_component_analyst_dispatches"] > 0, packet["call_counts"]
    assert packet["call_counts"]["ordinary_selected_role_dispatches"] > 0, packet["call_counts"]
    assert set(packet["selected_model_roles"]) == expected_selected_roles
    assert all(item["packet_complete"] for item in scenario_packet["observed_safe_semantic_projection"]), [
        (
            item["role"],
            item["call_id"],
            item["packet_complete"],
            {
                field
                for field, present in item["safe_semantic_projection"].get("safe_required_field_presence", {}).items()
                if not present
            },
        )
        for item in scenario_packet["observed_safe_semantic_projection"]
        if not item["packet_complete"]
    ]
    assert all(item["parser_consumable"] for item in scenario_packet["observed_safe_semantic_projection"]), [
        (
            item["role"],
            item["call_id"],
            item["parser_failure_kind"],
            item["safe_semantic_projection"],
        )
        for item in scenario_packet["observed_safe_semantic_projection"]
        if not item["parser_consumable"]
    ]
    assert packet["call_counts"]["model_calls"] > 0, packet["call_counts"]
    wrong_semantics = [
        {
            "role": item["role"],
            "call_id": item["call_id"],
            "semantic_status": item["semantic_status"],
            **{
                key: item["safe_semantic_projection"].get(key)
                for key in (
                    "classification",
                    "expected_target_concept",
                    "matched_target_concepts",
                    "expected_dependency_concepts",
                    "matched_dependency_concepts",
                    "relationship_type",
                    "checks",
                )
            },
        }
        for item in scenario_packet["observed_safe_semantic_projection"]
        if item["semantic_status"] != "met"
    ]
    assert all(item["semantic_status"] == "met" for item in scenario_packet["observed_safe_semantic_projection"]), (
        json.dumps(wrong_semantics, sort_keys=True)
    )
    assert {item["role"] for item in transport.calls} == expected_selected_roles, packet["call_counts"]
    assert len(transport.calls) == expected_calls
    assert packet["primary_failure_attribution"] == "PASS", scenario_packet
    assert packet["ordinary_downstream_terminal_posture"] == {scenario_id: expectation.expected_terminal_posture}
    assert packet["call_counts"]["model_calls"] == expected_calls
    assert authorization.maximum_model_calls == build_call_manifest(request).total_maximum_physical_model_calls
    assert packet["call_counts"]["ordinary_fixture_runs"] == 1
    deterministic_roles = set(packet["exact_role_call_manifest"]["deterministic_roles"])
    assert MODEL_ROLES - expected_selected_roles <= deterministic_roles
    assert {
        "component_dprime",
        "synthesis_dprime",
        "searchos_fictional_acquisition_corpus",
    } <= deterministic_roles
    assert packet["call_counts"]["ordinary_selected_role_dispatches"] == expected_calls
    assert (
        packet["call_counts"]["deterministic_component_analyst_calls"] == 0
        if ROLE_COMPONENT_ANALYST in expected_selected_roles
        else packet["call_counts"]["deterministic_component_analyst_calls"] > 0
    )
    assert (
        packet["call_counts"]["deterministic_cross_component_analyst_calls"] == 0
        if ROLE_CROSS_COMPONENT_ANALYST in expected_selected_roles
        else packet["call_counts"]["deterministic_cross_component_analyst_calls"] > 0
    )
    assert packet["call_counts"]["fictional_search_operations"] == 1 + expectation.expected_search_generations
    assert packet["call_counts"]["fictional_read_operations"] == len(SCENARIO_BY_ID[scenario_id].direct_facts) + (
        0 if SCENARIO_BY_ID[scenario_id].unavailable_recovery else expectation.expected_search_generations
    )
    assert packet["call_counts"]["deterministic_component_dprime_calls"] > 0
    assert packet["call_counts"]["deterministic_synthesis_dprime_calls"] > 0
    assert packet["retry_counts"] == {"total": 0}
    assert packet["credentials_accessed"] is False
    for call_kind in (
        "search_calls",
        "retrieval_calls",
        "read_calls",
        "navigation_calls",
        "map_calls",
        "crawl_calls",
    ):
        assert packet["call_counts"][call_kind] == 0
    assert packet["transport_route_attestation"] == {
        "canonical_provider_used": authorization.provider,
        "canonical_model_used": authorization.model,
        "attested_call_count": expected_calls,
        "all_responses_matched_license": True,
    }
    reject_forbidden_packet_material(packet)


def _replace_planner_component_ids(
    value: Any,
    replacements: Mapping[str, str],
) -> Any:
    if isinstance(value, Mapping):
        return {key: _replace_planner_component_ids(child, replacements) for key, child in value.items()}
    if isinstance(value, list):
        return [_replace_planner_component_ids(child, replacements) for child in value]
    if isinstance(value, str):
        return replacements.get(value, value)
    return deepcopy(value)


def test_default_runner_accepts_semantically_equivalent_planner_local_ids(
    tmp_path: Path,
) -> None:
    canonical = _planner_output(CASE_3)
    replacements = {
        str(item["component_id"]): f"planner_local_component_{index}"
        for index, item in enumerate(canonical["answer_components"], start=1)
    }
    local_output = _replace_planner_component_ids(canonical, replacements)
    output = _repo_output_path(tmp_path, "planner-local-ids.json")
    request = _request(
        "planner_only",
        execution_mode="execute",
        scenario_ids=(CASE_3,),
        output=output,
    )
    authorization = _authorization(request, output=output)
    transport = OrdinaryFixtureFakeTransport(
        scenario_id=CASE_3,
        tmp_path=tmp_path,
        planner_output=local_output,
    )

    packet = run_evaluation(
        request,
        repository_sha=REPOSITORY_SHA,
        authorization=authorization,
        execution_identity=_execution_identity(request),
        transport_factory=FactoryCensus(transport=transport),
    )

    scenario_packet = packet["observed_safe_semantic_projection"][0]
    observation = scenario_packet["observed_safe_semantic_projection"][0]
    bridge = scenario_packet["evaluation_only_mapping_metadata"]
    assert packet["primary_failure_attribution"] == "PASS", json.dumps(
        {
            "scenario_classification": scenario_packet["primary_failure_attribution"],
            "runner_failure_type": scenario_packet["runner_failure_type"],
            "mapping": bridge,
            "observation": observation,
        },
        sort_keys=True,
    )
    assert scenario_packet["primary_failure_attribution"] == "PASS"
    assert scenario_packet["ordinary_downstream_terminal_posture"] == "depth_two_inferred_closure"
    assert observation["safe_semantic_projection"]["semantic_concept_to_observed_component_id"] == replacements
    projection_text = json.dumps(observation["safe_semantic_projection"])
    assert all(current_id in projection_text for current_id in replacements.values())
    assert bridge["concept_to_current_component_id"] == replacements
    assert bridge["scenario_id"] == CASE_3
    assert bridge["derived_after_installed_parser"] is True
    assert bridge["derived_after_answer_contract_acceptance"] is True
    assert bridge["scenario_bounded"] is True
    assert bridge["canonical"] is False
    assert bridge["production_available"] is False
    assert bridge["manufactures_missing_semantics_or_refs"] is False
    assert packet["call_counts"]["ordinary_fixture_runs"] == 1
    assert packet["call_counts"]["model_calls"] == 1
    assert {item["role"] for item in transport.calls} == {ROLE_SEARCH_PLANNER}
    reject_forbidden_packet_material(packet)
