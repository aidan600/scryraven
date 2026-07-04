"""PRODUCT-PATH-REGRESSION: RunKernel-shaped source-obligation recovery gate.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-single-relation-live-dogfood-run --query "<supported query>"
Runtime consumer: proplex.mvp_single_relation_live_dogfood_run consuming
core.single_relation_source_obligation_recovery_authorization.
Why ordinary product-path work cannot be done directly: offline validation uses
fake provider and D-prime callables so no live provider, broker, fetch/read,
retrieval, browser, or model call occurs.
Integration deadline: current phase.
Exit condition: keep while generic single-relation source-obligation recovery
authorization feeds the ordinary dogfood runner, or replace with a broader
product-path guard after live validation.
Why this is not a shadow product path: tests call the ordinary dogfood builder
and the product-owned provider acquisition adapter, then assert the packet
consumed by the existing product path.
Forbidden interpretation: this does not prove source authority, citation
eligibility, source-obligation satisfaction, product correctness, FAP/Author,
provider comparison, or live validation.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Mapping

from core.generic_query_to_relation_planning import build_generic_query_relation_plan
from core.run_kernel import (
    SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE,
    ActionType,
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.single_relation_source_obligation_recovery_authorization import (
    AUTHORIZATION_STATUS_NOT_REQUIRED,
    AUTHORIZATION_STATUS_RECOVERY_CALL_AUTHORIZED,
    AUTHORIZATION_STATUS_RECOVERY_REQUIRED_CONFIRMATION_REQUIRED,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_NOT_CONFIRMED,
    DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
    DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED,
    SINGLE_RELATION_SOURCE_OBLIGATION_CONTRACT_REDUCER_KIND,
    SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_OWNER,
    build_single_relation_source_obligation_recovery_authorization,
)
from proplex.mvp_single_relation_live_dogfood_run import (
    DEFAULT_OUTPUT_DIR,
    build_generic_single_relation_live_dogfood_run_output,
)
from tests.test_generic_single_relation_live_dprime_non_support_repair_01 import (
    _assessment_payload,
)
from tests.test_generic_single_relation_official_source_challenge_recovery_01 import (
    ANSWER_CLAIM,
    SMALL_CLAIMS_QUERY,
    _fetch_read_must_not_run,
    _official_answer_bearing_recovery_results,
    _product_runner,
)

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "proplex" / "mvp_single_relation_live_dogfood_run.py"
CORE_PATH = ROOT / "core" / "single_relation_source_obligation_recovery_authorization.py"
RUN_KERNEL_PATH = ROOT / "core" / "run_kernel.py"


def test_core_authorization_blocks_non_official_direct_support() -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)

    authorization = build_single_relation_source_obligation_recovery_authorization(
        relation_plan=plan,
        acquisition_plan=_acquisition_plan(plan),
        selected_candidate_diagnostic=_candidate_diagnostic(
            domain="example-law.invalid",
            official=False,
            answer_bearing=True,
            selected=True,
        ),
        candidate_diagnostics=[
            _candidate_diagnostic(
                domain="example-law.invalid",
                official=False,
                answer_bearing=True,
                selected=True,
            ),
            _candidate_diagnostic(
                domain="example-county.gov",
                official=True,
                answer_bearing=False,
                selected=False,
            ),
        ],
        dprime_status=_dprime_status("directly_supports", "assessed"),
        recovery_confirmation_authorized=False,
    )
    packet = authorization.to_dict()

    assert packet["authorization_owner"] == (
        SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_OWNER
    )
    assert packet["authorization_status"] == (
        AUTHORIZATION_STATUS_RECOVERY_REQUIRED_CONFIRMATION_REQUIRED
    )
    assert packet["authorization_blocker"] == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_NOT_CONFIRMED
    )
    assert packet["dprime_assessment_status"] == "assessed"
    assert packet["dprime_support_relation"] == "directly_supports"
    assert packet["source_obligation_status"] == "unsatisfied"
    assert packet["source_obligation_requires_source_of_record"] is True
    assert packet["selected_material_answer_bearing_by_safe_diagnostics"] is True
    assert packet["selected_material_official_source_of_record_looking"] is False
    assert packet["recovery_required"] is True
    assert packet["recovery_confirmation_required"] is True
    assert packet["recovery_call_policy_authorized"] is False
    assert packet["support_admission_blocked"] is True
    assert packet["answer_display_blocked"] is True
    assert packet["source_display_blocked"] is True
    assert packet["run_kernel_support_admission_decision_status"] == (
        DPRIME_RUN_KERNEL_ADMISSION_DECISION_CHALLENGED
    )
    assert packet["provider_neutral_domain_constraints"] == ["example-county.gov"]
    recovery_plan = packet["source_challenge_recovery_plan"]
    contract_projection = packet["current_answer_contract_projection"]
    contract_state = packet["updated_contract_state"]
    assert recovery_plan["domain_constraints"] == ["example-county.gov"]
    assert recovery_plan["include_domains"] == ["example-county.gov"]
    assert recovery_plan["source_of_record_domain_constraints"] == [
        "example-county.gov"
    ]
    assert recovery_plan["closed_surface_flags"]["support_created"] is False
    assert recovery_plan["closed_surface_flags"]["source_authority_adjudicated"] is False
    assert recovery_plan["closed_surface_flags"]["source_obligation_satisfied"] is False
    assert recovery_plan["closed_surface_flags"]["citation_eligible"] is False
    assert recovery_plan["closed_surface_flags"]["answer_created"] is False
    assert packet["raw_private_retention"] is False
    assert contract_projection["contract_owner"] == "RunKernel"
    assert contract_projection["contract_reducer_kind"] == (
        SINGLE_RELATION_SOURCE_OBLIGATION_CONTRACT_REDUCER_KIND
    )
    assert contract_projection["supported_query_class"] == (
        plan["supported_query_class_id"]
    )
    assert contract_projection["component_ref"]["component_id"] == plan["component_id"]
    assert contract_projection["search_requirement_ref"]["search_requirement_id"] == (
        plan["search_requirement_id"]
    )
    assert contract_projection["source_obligation_ref"]["source_obligation_id"] == (
        plan["source_obligation_id"]
    )
    assert contract_projection["selected_candidate_window_ref"]["domain"] == (
        "example-law.invalid"
    )
    assert contract_projection["dprime_support_relation"] == "directly_supports"
    assert contract_projection["source_obligation_status"] == "unsatisfied"
    assert contract_projection["support_admission_status"] == (
        "blocked_by_source_obligation_recovery_authorization"
    )
    assert contract_projection["answer_display_status"] == (
        "answer_display_blocked_by_source_obligation_contract_reducer"
    )
    assert contract_projection["source_display_status"] == (
        "source_display_blocked_by_source_obligation_contract_reducer"
    )
    assert contract_state["state_owner"] == "RunKernel"
    assert contract_state["state_transition"] == (
        "source_obligation_recovery_authorization_reduced"
    )
    assert contract_state["support_admission_allowed"] is False
    assert contract_state["answer_display_allowed"] is False
    assert contract_state["source_display_allowed"] is False


def test_runkernel_reduces_authorization_into_runstate_projection() -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)
    kernel = RunKernel.start(
        run_id="source-obligation-recovery-run",
        request_id="source-obligation-recovery-request",
    )
    action = kernel.authorize_single_relation_source_obligation_recovery(
        inputs={
            "authorization_request_kind": (
                "single_relation_source_obligation_recovery"
            ),
            "component_id": plan["component_id"],
            "source_obligation_id": plan["source_obligation_id"],
        }
    )
    observation_payload = {
        "relation_plan": plan,
        "acquisition_plan": _acquisition_plan(plan),
        "selected_candidate_diagnostic": _candidate_diagnostic(
            domain="example-law.invalid",
            official=False,
            answer_bearing=True,
            selected=True,
        ),
        "candidate_diagnostics": [
            _candidate_diagnostic(
                domain="example-county.gov",
                official=True,
                answer_bearing=False,
                selected=False,
            )
        ],
        "dprime_status": _dprime_status("directly_supports", "assessed"),
        "provider_acquisition_attempt_counts": {
            "provider_calls_attempted": 1,
            "provider_calls_completed": 1,
            "provider_results_returned": 1,
        },
        "recovery_confirmation_authorized": False,
    }
    observation = Observation.from_action(
        action,
        observation_type=(
            ObservationType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZED
        ),
        status=RunStageStatus.COMPLETED,
        payload=observation_payload,
    )

    kernel.reduce(observation)

    projection = kernel.state.projections[
        SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE
    ]
    contract_projection = projection["current_answer_contract_projection"]
    contract_state = projection["updated_contract_state"]
    assert action.action_type is (
        ActionType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZE
    )
    assert action.expected_observation_type is (
        ObservationType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZED
    )
    assert observation.observation_type is (
        ObservationType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZED
    )
    assert action.action_id in kernel.state.reduced_action_ids
    assert kernel.state.stage_statuses[
        SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE
    ] is RunStageStatus.COMPLETED
    assert len(kernel.state.observations) == 1
    assert projection["run_kernel_reduced"] is True
    assert projection["run_state_projection_key"] == (
        SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE
    )
    assert projection["run_kernel_action_ref"]["action_type"] == (
        ActionType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZE.value
    )
    assert projection["run_kernel_observation_ref"]["observation_type"] == (
        ObservationType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZED.value
    )
    assert projection["authorization_owner"] == "RunKernel"
    assert projection["dprime_support_relation"] == "directly_supports"
    assert projection["recovery_required"] is True
    assert projection["support_admission_blocked"] is True
    assert projection["answer_display_blocked"] is True
    assert projection["source_display_blocked"] is True
    assert contract_projection["run_kernel_reduced"] is True
    assert contract_projection["dprime_support_relation"] == "directly_supports"
    assert contract_state["run_kernel_reduced"] is True
    assert contract_state["support_admission_allowed"] is False
    assert contract_state["answer_display_allowed"] is False
    assert contract_state["source_display_allowed"] is False


def test_core_authorization_challenge_relation_still_requires_recovery() -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)

    authorization = build_single_relation_source_obligation_recovery_authorization(
        relation_plan=plan,
        acquisition_plan=_acquisition_plan(plan),
        selected_candidate_diagnostic=_candidate_diagnostic(
            domain="example-law.invalid",
            official=False,
            answer_bearing=True,
            selected=True,
        ),
        candidate_diagnostics=[
            _candidate_diagnostic(
                domain="example-county.gov",
                official=True,
                answer_bearing=False,
                selected=False,
            )
        ],
        dprime_status=_dprime_status("weak_or_overclaim_risk", "challenge-recommended"),
        recovery_confirmation_authorized=False,
    )
    packet = authorization.to_dict()

    assert packet["recovery_required"] is True
    assert packet["authorization_blocker"] == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED
    )
    assert "challenge" in packet["recovery_reason"].casefold()
    assert packet["support_admission_blocked"] is True
    assert packet["answer_display_blocked"] is True
    assert packet["source_display_blocked"] is True


def test_core_authorization_does_not_trigger_for_official_or_non_answer_source() -> None:
    plan = build_generic_query_relation_plan(SMALL_CLAIMS_QUERY)

    official = build_single_relation_source_obligation_recovery_authorization(
        relation_plan=plan,
        acquisition_plan=_acquisition_plan(plan),
        selected_candidate_diagnostic=_candidate_diagnostic(
            domain="example-county.gov",
            official=True,
            answer_bearing=True,
            selected=True,
        ),
        candidate_diagnostics=[],
        dprime_status=_dprime_status("directly_supports", "assessed"),
        recovery_confirmation_authorized=False,
    ).to_dict()
    non_answer = build_single_relation_source_obligation_recovery_authorization(
        relation_plan=plan,
        acquisition_plan=_acquisition_plan(plan),
        selected_candidate_diagnostic=_candidate_diagnostic(
            domain="example-law.invalid",
            official=False,
            answer_bearing=False,
            selected=True,
        ),
        candidate_diagnostics=[],
        dprime_status=_dprime_status("directly_supports", "assessed"),
        recovery_confirmation_authorized=False,
    ).to_dict()

    assert official["authorization_status"] == AUTHORIZATION_STATUS_NOT_REQUIRED
    assert official["recovery_required"] is False
    assert official["run_kernel_support_admission_decision_status"] == (
        DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    )
    assert non_answer["authorization_status"] == AUTHORIZATION_STATUS_NOT_REQUIRED
    assert non_answer["recovery_required"] is False
    assert non_answer["support_admission_blocked"] is False


def test_non_official_direct_support_cannot_reach_pass_default_off(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="direct-support-non-official-default-off",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        product_provider_acquisition_runner=_product_runner(calls),
        fetch_read_runner=_fetch_read_must_not_run,
        dprime_model_review_callable=_direct_support_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    authorization = packet["source_obligation_recovery_authorization"]
    contract_projection = packet["single_relation_answer_contract_projection"]
    contract_state = packet["single_relation_answer_contract_state"]
    dprime_status = packet["semantic_status_payload"]["dprime_status"]

    assert len(calls) == 1
    assert result.return_code == 2
    assert result.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_NOT_CONFIRMED
    )
    assert packet["answer_text_present"] is False
    assert packet["product_answer_text"] == ""
    assert packet["source_display_entries"] == []
    assert packet["source_challenge_recovery_provider_calls_attempted"] == 0
    assert packet["source_obligation_recovery_required"] is True
    assert packet["source_obligation_recovery_confirmation_required"] is True
    assert packet["source_obligation_recovery_call_policy_authorized"] is False
    assert packet["source_obligation_recovery_support_admission_blocked"] is True
    assert packet["source_obligation_recovery_answer_display_blocked"] is True
    assert packet["source_obligation_recovery_source_display_blocked"] is True
    assert authorization["authorization_owner"] == (
        SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_OWNER
    )
    assert authorization["run_kernel_reduced"] is True
    assert authorization["run_state_projection_key"] == (
        SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE
    )
    assert authorization["run_kernel_action_ref"]["action_type"] == (
        ActionType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZE.value
    )
    assert authorization["run_kernel_observation_ref"]["observation_type"] == (
        ObservationType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZED.value
    )
    assert contract_projection["contract_owner"] == "RunKernel"
    assert contract_projection["run_kernel_reduced"] is True
    assert contract_projection["component_ref"]["component_id"] == (
        packet["component_id"]
    )
    assert contract_projection["source_obligation_ref"]["source_obligation_id"] == (
        packet["source_obligation_id"]
    )
    assert contract_projection["dprime_support_relation"] == "directly_supports"
    assert contract_projection["support_admission_status"] == (
        "blocked_by_source_obligation_recovery_authorization"
    )
    assert contract_state["state_owner"] == "RunKernel"
    assert contract_state["run_kernel_reduced"] is True
    assert contract_state["support_admission_allowed"] is False
    assert contract_state["answer_display_allowed"] is False
    assert contract_state["source_display_allowed"] is False
    assert authorization["dprime_support_relation"] == "directly_supports"
    assert authorization["selected_material_answer_bearing_by_safe_diagnostics"] is True
    assert authorization["selected_material_official_source_of_record_looking"] is False
    assert dprime_status["assessment_status"] == "assessed"
    assert dprime_status["support_relation"] == "directly_supports"
    assert dprime_status["validated_support_proposal_available"] is True
    assert dprime_status["run_kernel_admission_decision_status"] == "challenged"
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False
    assert dprime_status["objects_created"].get("final_answer_packet") is not True
    assert dprime_status["objects_created"].get("author_answer") is not True
    assert dprime_status["objects_created"].get("citation_source_display") is not True
    assert packet["source_challenge_recovery_source_obligation_satisfied"] is False
    assert packet["candidate_selection_citation_eligible"] is False
    assert packet["product_correctness_claimed"] is False
    assert packet["fap_author_opened"] is False


def test_confirmed_fake_recovery_for_direct_support_stops_before_rereview(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="direct-support-non-official-confirmed-recovery",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_live_source_challenge_recovery=True,
        product_provider_acquisition_runner=_product_runner(
            calls,
            recovery_results=_official_answer_bearing_recovery_results(),
        ),
        fetch_read_runner=_fetch_read_must_not_run,
        dprime_model_review_callable=_direct_support_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    packet = result.packet
    plan = packet["source_challenge_recovery_plan"]
    recovery = packet["source_challenge_recovery_result"]
    contract_projection = packet["single_relation_answer_contract_projection"]

    assert len(calls) == 2
    assert calls[1]["include_domains"] == ["example-county.gov"]
    assert calls[1]["query"] == plan["recovery_query"]
    assert packet["source_obligation_recovery_call_policy_authorized"] is True
    assert packet["source_obligation_recovery_authorization_status"] == (
        AUTHORIZATION_STATUS_RECOVERY_CALL_AUTHORIZED
    )
    assert packet["source_obligation_recovery_authorization"][
        "run_kernel_reduced"
    ] is True
    assert packet["source_obligation_recovery_authorization"][
        "run_kernel_action_ref"
    ]["action_type"] == (
        ActionType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZE.value
    )
    assert packet["source_challenge_recovery_provider_calls_attempted"] == 1
    assert packet["source_challenge_recovery_provider_calls_completed"] == 1
    assert contract_projection["recovery_attempt_refs"][0]["provider_calls_attempted"] == 1
    assert contract_projection["recovery_attempt_counts"]["provider_calls_attempted"] == 1
    assert packet["source_challenge_recovery_material_acquired"] is True
    assert recovery["official_answer_bearing_material_acquired"] is True
    assert recovery["source_authority_adjudicated"] is False
    assert recovery["source_obligation_satisfied"] is False
    assert recovery["citation_eligible"] is False
    assert recovery["answer_created"] is False
    assert result.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED
    )
    assert packet["dprime_model_review_calls_attempted"] == 1
    assert packet["answer_text_present"] is False
    assert packet["source_display_entries"] == []
    assert packet["product_correctness_claimed"] is False
    assert packet["fap_author_opened"] is False


def test_cli_runner_consumes_core_authorization_without_owning_policy() -> None:
    runner_text = RUNNER_PATH.read_text(encoding="utf-8")
    core_text = CORE_PATH.read_text(encoding="utf-8")
    run_kernel_text = RUN_KERNEL_PATH.read_text(encoding="utf-8")
    runner_tree = ast.parse(runner_text)
    imported = _imports(runner_tree)
    functions = {
        node.name for node in ast.walk(runner_tree) if isinstance(node, ast.FunctionDef)
    }

    assert "core.single_relation_source_obligation_recovery_authorization" in imported
    assert "core.run_kernel" in imported
    assert "source_obligation_recovery_authorization" in runner_text
    assert "RunKernel.start" in runner_text
    assert "authorize_single_relation_source_obligation_recovery" in runner_text
    assert "Observation.from_action" in runner_text
    assert "run_kernel.reduce(observation)" in runner_text
    assert "build_single_relation_source_obligation_recovery_authorization" not in (
        runner_text
    )
    assert "class SourceObligationRecoveryAuthorization" in core_text
    assert "current_answer_contract_projection" in core_text
    assert "updated_contract_state" in core_text
    assert SINGLE_RELATION_SOURCE_OBLIGATION_CONTRACT_REDUCER_KIND in core_text
    assert "SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZE" in run_kernel_text
    assert "SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZED" in run_kernel_text
    assert (
        "def authorize_single_relation_source_obligation_recovery"
        in run_kernel_text
    )
    assert (
        "build_single_relation_source_obligation_recovery_authorization("
        in run_kernel_text
    )
    assert (
        "self.state.projections[action.stage] = deepcopy(\n"
        "                authorization_projection\n"
        "            )"
        in run_kernel_text
    )
    assert "_source_challenge_recovery_trigger_eligible" not in functions
    assert "_build_source_challenge_recovery_plan" not in functions
    assert "_source_obligation_confirmation_satisfied" not in functions
    assert "validated_support_proposal_available" not in runner_text
    assert "run_provider_proxy_helper_once" not in core_text
    assert "LinkUp" not in core_text
    assert "Brave" not in core_text
    assert "Exa" not in core_text
    assert "source_authority_adjudicated\": True" not in core_text
    assert "citation_eligible\": True" not in core_text
    assert "source_obligation_satisfied\": True" not in core_text
    assert "product_correctness_claimed\": True" not in core_text


def _direct_support_review(*_args: Any, **kwargs: Any) -> dict[str, Any]:
    return _assessment_payload(
        kwargs["input_packet"],
        support_relation="directly_supports",
        claim=ANSWER_CLAIM,
    )


def _acquisition_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "test_acquisition_plan_v1",
        "relation_plan_id": plan["plan_id"],
        "component_id": plan["component_id"],
        "search_requirement_id": plan["search_requirement_id"],
        "source_obligation_id": plan["source_obligation_id"],
        "acquisition_query": plan["search_query_seeds"][0],
        "answer_bearing_anchor_terms": ["small claims", "filing fee"],
        "artifact_source_terms": ["fee schedule"],
        "extraction_provider": "tavily",
        "provider_operation": "search",
    }


def _dprime_status(support_relation: str, assessment_status: str) -> dict[str, Any]:
    return {
        "assessment_status": assessment_status,
        "support_relation": support_relation,
        "validated_support_proposal_available": (
            support_relation == "directly_supports"
        ),
        "source_obligation_satisfaction_claimed": False,
        "citation_eligibility_claimed": False,
    }


def _candidate_diagnostic(
    *,
    domain: str,
    official: bool,
    answer_bearing: bool,
    selected: bool,
) -> dict[str, Any]:
    status = (
        "answer_bearing_candidate_window_established"
        if answer_bearing
        else "answer_bearing_candidate_window_not_established"
    )
    return {
        "candidate_id": f"candidate:{domain}",
        "result_rank": 1,
        "title": f"{domain} fee page",
        "domain": domain,
        "url": f"https://{domain}/small-claims-fees",
        "answer_bearing_candidate_window_selected": selected,
        "answer_bearing_candidate_window_status": status,
        "matched_value_token_kinds": ["currency"] if answer_bearing else [],
        "matched_anchor_count": 2 if answer_bearing else 0,
        "official_or_source_record_looking_http_candidate": official,
        "candidate_selection_features": {
            "source_of_record_domain_signal": official,
            "official_domain_signal": official,
            "public_agency_domain_signal": official,
            "features_satisfy_source_obligation": False,
        },
    }


def _imports(tree: ast.AST) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
