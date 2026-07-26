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
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from core.multicomponent_role_runtime import ROLE_SYSTEM_PROMPTS
from core.search_planner_model_prompt import SEARCH_PLANNER_MODEL_SYSTEM_PROMPT
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    CLASSIFICATIONS,
    LIVE_ADDENDUM_SCHEMA_VERSION,
    BoundaryInjectionController,
    ClassificationEvidence,
    EvaluationConfigurationError,
    EvaluationRequest,
    EvaluationTransportError,
    EvaluationTransportResponse,
    LiveAuthorization,
    PairedProbeEvidence,
    ScenarioRunResult,
    build_call_manifest,
    classify_result,
    paired_probe_demonstrates_prompt_causality,
    project_and_score_role_output,
    proposed_live_addendum_template,
    reject_forbidden_packet_material,
    resolve_request,
    run_evaluation,
    sample_classification_packet,
)
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

REPOSITORY_SHA = "0719c70982b22a65f7688f2fbda5b0be8e653f95"


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.next_output: dict[str, Any] = {}
        self.credentials_accessed = False

    def __call__(self, **kwargs: Any) -> EvaluationTransportResponse:
        self.calls.append({key: value for key, value in kwargs.items() if key not in {"prompt", "system_prompt"}})
        return EvaluationTransportResponse(
            output=dict(self.next_output),
            input_tokens=10,
            output_tokens=10,
            cost=0.0,
            credentials_accessed=False,
        )


class FactoryCensus:
    def __init__(self) -> None:
        self.calls = 0
        self.transport = FakeTransport()

    def __call__(self, _authorization: LiveAuthorization) -> FakeTransport:
        self.calls += 1
        return self.transport


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


def _authorization(
    request: EvaluationRequest,
    *,
    output: str,
    retry_cap: int = 0,
    maximum_model_calls: int | None = None,
) -> LiveAuthorization:
    resolved = resolve_request(request)
    manifest = build_call_manifest(resolved, retry_allowance=retry_cap)
    return LiveAuthorization(
        schema_version=LIVE_ADDENDUM_SCHEMA_VERSION,
        reference="synthetic-authorization",
        repository_sha=REPOSITORY_SHA,
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
        output_packet_path=output,
        decision="Decide whether this synthetic boundary is ready.",
        stop_condition="Stop when any exact cap is exhausted.",
        raw_retention_posture="sanitized_only",
    )


def _planner_output(scenario_id: str) -> dict[str, Any]:
    output = planner_payload(SCENARIO_BY_ID[scenario_id])
    output.pop("planner_model_metadata", None)
    return output


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
                    "accepted_contract_ref": {"digest": "synthetic-contract"},
                    "component_evidence": {"evidence_ref_id": "synthetic-evidence"},
                }
            )
        else:
            transport.next_output = _cross_output(call)
            system_prompt = ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
            prompt = json.dumps(
                {
                    "accepted_component_refs": [{"component_id": "synthetic-component"}],
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
        output=str(tmp_path / "result.json"),
    )
    with pytest.raises(EvaluationConfigurationError, match="live addendum"):
        run_evaluation(
            request,
            repository_sha=REPOSITORY_SHA,
            transport_factory=factory,
        )
    assert factory.calls == 0


def test_over_cap_authorization_fails_before_transport(tmp_path: Path) -> None:
    output = str(tmp_path / "result.json")
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
    output = str(tmp_path / f"{evaluation_pass}-{len(roles)}.json")
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
    output = str(tmp_path / "extra-call.json")
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
        with pytest.raises(EvaluationTransportError, match="unmanifested"):
            controller.invoke(
                role=ROLE_SEARCH_PLANNER,
                prompt="{}",
                system_prompt="synthetic",
                provider=authorization.provider,
                model=authorization.model,
            )
        assert len(factory.transport.calls) == calls_before
        return result

    packet = run_evaluation(
        request,
        repository_sha=REPOSITORY_SHA,
        authorization=authorization,
        transport_factory=factory,
        scenario_runner=runner,
    )
    assert packet["call_counts"]["model_calls"] == 1


def test_incomplete_boundary_packet_is_classified_before_transport(
    tmp_path: Path,
) -> None:
    output = str(tmp_path / "incomplete-packet.json")
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
        transport_factory=factory,
        scenario_runner=runner,
    )
    assert packet["primary_failure_attribution"] == "PACKET"
    assert packet["call_counts"]["model_calls"] == 0
    assert factory.transport.calls == []


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
    output = str(tmp_path / "authority-violation.json")
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
    output = str(tmp_path / "redacted.json")
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
    paired = PairedProbeEvidence(
        scenario_id=CASE_3,
        provider="synthetic-provider",
        model="synthetic-model",
        semantic_input_facts_digest="a" * 64,
        instruction_difference="Remove only the dependency-order instruction.",
        control_instruction_digest="b" * 64,
        variant_instruction_digest="c" * 64,
        control_semantic_status="wrong",
        variant_semantic_status="met",
        maximum_physical_calls_each=1,
        retry_allowance_each=0,
        deterministic_comparison_criteria=("dependency set equality",),
    )
    assert paired_probe_demonstrates_prompt_causality(paired) is True
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
    assert paired_probe_demonstrates_prompt_causality(incomplete_probe) is False
    assert (
        classify_result(
            ClassificationEvidence(
                True,
                True,
                True,
                "wrong",
                False,
                incomplete_probe,
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
        "operator_command",
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
