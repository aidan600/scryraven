"""PRODUCT-PATH-REGRESSION: model-assisted single-relation planning.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-single-relation-live-dogfood-run --query "<supported query>"
Runtime consumer: proplex.mvp_single_relation_live_dogfood_run.
Why ordinary product-path work cannot be done directly: offline validation must
use fake injected planner/provider/D-prime callables so no live provider,
broker, fetch/read, retrieval, or model calls occur.
Integration deadline: current phase.
Exit condition: keep while the ordinary single-relation dogfood runner consumes
model-assisted planning packets, or replace with a broader product-path
regression after strict live FastModel routing is available.
Why this is not a shadow product path: tests call the shared planning reducer
and the ordinary dogfood builder; there is no standalone planner command or
alternate answer path.
Forbidden interpretation: fake-model planner tests are not live FastModel
validation, product correctness, evidence, semantic support, source authority,
source-obligation satisfaction, citation eligibility, FAP/Author output, or
multi-component execution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

import core.model_assisted_single_relation_planning as planning
from core.generic_product_provider_acquisition import (
    build_generic_product_provider_acquisition_runner,
)
from proplex.mvp_single_relation_live_dogfood_run import (
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED,
    BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED,
    BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE,
    DEFAULT_OUTPUT_DIR,
    GenericLiveFetchReadResult,
    build_generic_single_relation_live_dogfood_run_output,
)
from tests.test_generic_single_relation_live_dprime_non_support_repair_01 import (
    _assessment_payload,
)

ROOT = Path(__file__).resolve().parents[1]
PLANNER_MODULE_PATH = ROOT / "core" / "model_assisted_single_relation_planning.py"
DOGFOOD_MODULE_PATH = ROOT / "proplex" / "mvp_single_relation_live_dogfood_run.py"
SMALL_CLAIMS_QUERY = (
    "What is the current filing fee for small claims in Example County?"
)
AMBIGUOUS_QUERY = "What is the current filing fee for the form?"
UNSUPPORTED_QUERY = "What does Reddit say about this paint?"
ANSWER_CLAIM = "Example County small claims filing fee is $42."


def test_unsupported_query_blocks_before_fastmodel_planning(tmp_path: Path) -> None:
    provider_calls: list[dict[str, Any]] = []
    planner_calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=UNSUPPORTED_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="model-planning-unsupported-query",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        product_provider_acquisition_runner=_product_runner(provider_calls),
        fast_model_planner_callable=_planner(planner_calls),
        fast_model_planner_strict_route_ref=_strict_route_ref(),
        require_model_assisted_planning=True,
        dprime_model_review_callable=_must_not_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    serialized = json.dumps(result.packet, sort_keys=True)
    assert result.return_code == 2
    assert result.packet["relation_plan_consumed"] is False
    assert result.packet["fast_planner_model_calls_attempted"] == 0
    assert result.packet["model_assisted_planning_packet"] == {}
    assert result.packet["model_assisted_planning_context_kinds_exercised"] == []
    assert provider_calls == []
    assert planner_calls == []
    assert UNSUPPORTED_QUERY not in serialized


def test_required_live_model_planning_blocks_without_strict_route(
    tmp_path: Path,
) -> None:
    provider_calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="model-planning-strict-route-unavailable",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        product_provider_acquisition_runner=_product_runner(provider_calls),
        fast_provider="OpenRouter",
        fast_model="configured-fast-planner",
        fast_model_local_url="http://localhost:4321/v1",
        require_model_assisted_planning=True,
        dprime_model_review_callable=_must_not_review,
        environ={
            "PYTEST_CURRENT_TEST": "test",
            "TEST_SENTINEL": "fixture-marker-must-not-serialize",
        },
    )

    serialized = json.dumps(result.packet, sort_keys=True)
    route_ref = result.packet["model_assisted_planning_packet"][
        "strict_model_route_ref"
    ]
    assert result.return_code == 2
    assert (
        result.decision
        == BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE
    )
    assert result.packet["model_assisted_planning_required"] is True
    assert result.packet["model_assisted_planning_configured_fast_provider"] == (
        "OpenRouter"
    )
    assert result.packet["model_assisted_planning_configured_fast_model"] == (
        "configured-fast-planner"
    )
    assert result.packet["model_assisted_planning_configured_local_url_present"] is True
    assert result.packet["model_assisted_planning_configured_local_url_posture"] == (
        "local_configured_not_retained"
    )
    assert route_ref["configured_fast_provider"] == "OpenRouter"
    assert route_ref["configured_fast_model"] == "configured-fast-planner"
    assert route_ref["configured_endpoint_kind"] == "chat_completions_compatible"
    assert route_ref["configured_local_url_present"] is True
    assert route_ref["configured_local_url_posture"] == "local_configured_not_retained"
    assert route_ref["strict_one_shot"] is False
    assert route_ref["max_model_calls"] == 0
    assert route_ref["retry_policy"] == "unavailable"
    assert route_ref["fallback_policy"] == "unavailable"
    assert route_ref["endpoint_switching_allowed"] is False
    assert result.packet["model_assisted_planning_strict_model_route_valid"] is False
    assert result.packet["failure_attribution_bucket"] == (
        "fast_model_planner_strict_route_unavailable"
    )
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["dprime_model_review_calls_attempted"] == 0
    assert result.packet["fast_planner_model_calls_attempted"] == 0
    assert result.packet["model_assisted_planning_raw_private_retention_false"] is True
    assert result.packet["model_assisted_planning_closed_surfaces_preserved"] is True
    assert "fixture-marker-must-not-serialize" not in serialized
    assert "http://localhost:4321/v1" not in serialized
    assert provider_calls == []


@pytest.mark.parametrize(
    "context_kind",
    [
        planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        planning.PLANNING_CONTEXT_ACQUISITION,
        planning.PLANNING_CONTEXT_DISAMBIGUATION,
        planning.PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY,
    ],
)
def test_shared_module_accepts_all_planning_context_kinds(context_kind: str) -> None:
    planner_calls: list[dict[str, Any]] = []
    packet = planning.build_model_assisted_single_relation_planning_packet(
        planning_context_kind=context_kind,
        context_state=_context_state(),
        planner_callable=_planner(planner_calls, proposal=_proposal(context_kind)),
        strict_model_route_ref=_strict_route_ref(),
    )

    assert packet["planning_context_kind"] == context_kind
    assert packet["shared_planner_surface"].endswith(
        "build_model_assisted_single_relation_planning_packet"
    )
    assert packet["model_calls_attempted"] == 1
    assert packet["model_calls_completed"] == 1
    assert packet["proposal_reduced"] is True
    assert packet["raw_prompt_retained"] is False
    assert packet["raw_model_response_retained"] is False
    assert packet["raw_provider_payload_retained"] is False
    assert len(planner_calls) == 1
    assert planner_calls[0]["planning_context_kind"] == context_kind


def test_reducer_bounds_drops_unknowns_rejects_private_and_closed_claims() -> None:
    packet = planning.reduce_model_assisted_single_relation_proposal(
        {
            **_proposal(
                planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
                normalized_user_question="x" * 900,
            ),
            "unknown_untrusted_field": "drop me",
        },
        planning_context_kind=planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        context_state=_context_state(),
    )

    assert len(packet["normalized_user_question"]) == 500
    assert "unknown_untrusted_field" not in packet
    assert packet["unknown_fields_dropped"] is True
    assert packet["planner_output_is_evidence"] is False
    assert packet["planner_output_citation_eligible"] is False
    assert packet["closed_surface_flags"]["evidence_created"] is False

    uncertain = planning.reduce_model_assisted_single_relation_proposal(
        _proposal(
            planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
            reduced_status=None,
            source_class_uncertainty="official source class may be ambiguous",
            official_or_source_of_record_artifact_hypotheses=[],
            preferred_acquisition_query="",
        ),
        planning_context_kind=planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        context_state=_context_state(),
    )
    assert uncertain["reduced_status"] == "source_class_uncertain"
    assert uncertain["source_class_uncertainty"] == (
        "official source class may be ambiguous"
    )

    with pytest.raises(planning.ModelAssistedSingleRelationPlanningError):
        planning.reduce_model_assisted_single_relation_proposal(
            {"planning_context_kind": "initial_single_relation_planning", "raw_prompt": "x"},
            planning_context_kind=planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        )
    with pytest.raises(planning.ModelAssistedSingleRelationPlanningError):
        planning.reduce_model_assisted_single_relation_proposal(
            {
                "planning_context_kind": "initial_single_relation_planning",
                "answer_text": "The answer is 42.",
            },
            planning_context_kind=planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        )
    with pytest.raises(planning.ModelAssistedSingleRelationPlanningError):
        planning.reduce_model_assisted_single_relation_proposal(
            {
                "planning_context_kind": "initial_single_relation_planning",
                "citation_eligible": True,
            },
            planning_context_kind=planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        )


def test_multi_component_hypothesis_blocks_without_opening_execution(
    tmp_path: Path,
) -> None:
    provider_calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="model-planning-multi-component-closed",
        confirm_live_dogfood=True,
        product_provider_acquisition_runner=_product_runner(provider_calls),
        fast_model_planner_callable=_planner(
            [],
            proposal=_proposal(
                planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
                component_count_hypothesis="likely_multi_component",
                reduced_status="likely_multi_component_currently_closed",
            ),
        ),
        fast_model_planner_strict_route_ref=_strict_route_ref(),
        require_model_assisted_planning=True,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert result.return_code == 2
    assert result.packet["provider_calls_attempted"] == 0
    assert result.packet["fast_planner_model_calls_attempted"] == 1
    assert result.packet["model_assisted_planning_component_count_hypothesis"] == (
        "likely_multi_component"
    )
    assert result.packet["model_assisted_planning_reduced_status"] == (
        "likely_multi_component_currently_closed"
    )
    assert result.packet["run_kernel_dag_scheduling_required"] is False
    assert result.packet["model_assisted_planning_packet"]["closed_surface_flags"][
        "multi_component_execution_opened"
    ] is False
    assert provider_calls == []


def test_acquisition_query_consumes_model_official_artifact_hypotheses(
    tmp_path: Path,
) -> None:
    provider_calls: list[dict[str, Any]] = []
    planner_calls: list[dict[str, Any]] = []
    preferred_query = (
        "Example County official small claims fee schedule current filing fee"
    )

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="model-planning-acquisition-consumed",
        confirm_live_dogfood=True,
        product_provider_acquisition_runner=_product_runner(provider_calls),
        smart_provider="SmartProvider",
        smart_model="smart-dprime-model",
        fast_provider="ConfiguredFastProvider",
        fast_model="configured-fast-planner-model",
        fast_model_local_url="http://localhost:9876/v1",
        fast_model_planner_callable=_planner(
            planner_calls,
            proposal=_proposal(
                planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
                preferred_acquisition_query=preferred_query,
                official_or_source_of_record_artifact_hypotheses=[
                    "official small claims fee schedule",
                    "court filing fee table",
                ],
            ),
        ),
        fast_model_planner_strict_route_ref=_strict_route_ref(),
        require_model_assisted_planning=True,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert result.decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    assert planner_calls[0]["provider"] == "ConfiguredFastProvider"
    assert planner_calls[0]["model"] == "configured-fast-planner-model"
    assert planner_calls[0]["provider"] != "SmartProvider"
    assert planner_calls[0]["model"] != "smart-dprime-model"
    assert provider_calls[0]["query"] == preferred_query
    assert result.packet["model_assisted_planning_configured_fast_provider"] == (
        "ConfiguredFastProvider"
    )
    assert result.packet["model_assisted_planning_configured_fast_model"] == (
        "configured-fast-planner-model"
    )
    assert result.packet["model_assisted_planning_provider_used"] == (
        "ConfiguredFastProvider"
    )
    assert result.packet["model_assisted_planning_model_used"] == (
        "configured-fast-planner-model"
    )
    assert result.packet["model_assisted_planning_configured_endpoint_kind"] == (
        "openai_responses_api"
    )
    assert result.packet["model_assisted_planning_endpoint_used"] == (
        "openai_responses_api"
    )
    assert result.packet["model_assisted_planning_strict_one_shot"] is True
    assert result.packet["model_assisted_planning_retry_policy"] == "forbidden"
    assert result.packet["model_assisted_planning_fallback_policy"] == "forbidden"
    assert result.packet["model_assisted_planning_provider_switching_allowed"] is False
    assert result.packet["model_assisted_planning_endpoint_switching_allowed"] is False
    assert result.packet["initial_model_assisted_planning_packet"][
        "strict_model_route_result_ref"
    ]["model_calls_attempted"] == 1
    assert result.packet["initial_model_assisted_planning_packet"][
        "strict_model_route_result_ref"
    ]["model_calls_completed"] == 1
    assert result.packet["model_assisted_planning_consumed_by_acquisition"] is True
    assert result.packet["acquisition_query_after_model_assisted_planning"] == (
        preferred_query
    )
    assert result.packet["acquisition_query_before_model_assisted_planning"] != (
        preferred_query
    )
    assert "official small claims fee schedule" in result.packet[
        "official_artifact_hypotheses"
    ]
    assert result.packet["provider_calls_attempted"] == 1
    assert result.packet["dprime_model_review_calls_attempted"] == 0


def test_disambiguation_hints_use_scout_without_evidence_claim(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    result = build_generic_single_relation_live_dogfood_run_output(
        query=AMBIGUOUS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="model-planning-disambiguation-consumed",
        confirm_live_dogfood=True,
        product_provider_acquisition_runner=_product_runner(calls, scout=True),
        fetch_read_runner=_fetch_read_must_not_run,
        fast_model_planner_callable=_planner(
            [],
            proposal=_proposal(
                planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
                disambiguation_status="ambiguous_needs_disambiguation",
                disambiguation_reason="question omits the form or venue",
            ),
        ),
        fast_model_planner_strict_route_ref=_strict_route_ref(),
        require_model_assisted_planning=True,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert [call["provider"] for call in calls] == ["serper", "tavily"]
    assert result.packet["model_assisted_planning_consumed_by_disambiguation"] is True
    assert result.packet["serper_scout_calls_attempted"] == 1
    assert result.packet["serper_output_recorded_as_non_evidence"] is True
    assert result.packet["serper_output_used_as_evidence"] is False
    assert result.packet["disambiguation_record"]["observations"][0]["not_evidence"] is True
    assert result.packet["fast_planner_output"]["model_assisted_planning_consumed"] is True


def test_recovery_context_planning_alters_recovery_query_without_authority(
    tmp_path: Path,
) -> None:
    provider_calls: list[dict[str, Any]] = []
    planner_calls: list[dict[str, Any]] = []
    recovery_query = "Example County official court small claims fee schedule amount"

    result = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="model-planning-recovery-consumed",
        confirm_live_dogfood=True,
        confirm_live_dprime_review=True,
        confirm_live_source_challenge_recovery=True,
        product_provider_acquisition_runner=_product_runner(
            provider_calls,
            recovery_results=_official_answer_bearing_recovery_results(),
        ),
        fetch_read_runner=_fetch_read_must_not_run,
        fast_model_planner_callable=_planner(
            planner_calls,
            proposals=[
                _proposal(planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION),
                _proposal(
                    planning.PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY,
                    reduced_status="recovery_hypotheses_available",
                    preferred_recovery_query=recovery_query,
                    recovery_query_variants=[recovery_query],
                    official_or_source_of_record_artifact_hypotheses=[
                        "official court small claims fee schedule"
                    ],
                ),
            ],
        ),
        fast_model_planner_strict_route_ref=_strict_route_ref(),
        require_model_assisted_planning=True,
        dprime_model_review_callable=_weak_or_overclaim_review,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert result.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED
    )
    assert [call["planning_context_kind"] for call in planner_calls] == [
        planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        planning.PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY,
    ]
    assert len(provider_calls) == 2
    assert provider_calls[1]["query"] == recovery_query
    assert result.packet["model_assisted_planning_consumed_by_recovery"] is True
    assert result.packet["recovery_model_assisted_planning_calls_attempted"] == 1
    assert result.packet["fast_planner_model_calls_attempted"] == 2
    assert result.packet["source_challenge_recovery_query_before_model_assisted_planning"]
    assert result.packet["source_challenge_recovery_query_after_model_assisted_planning"] == (
        recovery_query
    )
    assert result.packet["source_challenge_recovery_official_artifact_hypotheses"] == [
        "official court small claims fee schedule"
    ]
    assert result.packet["source_challenge_recovery_material_acquired"] is True
    assert result.packet["source_challenge_recovery_support_created"] is False
    assert result.packet["source_challenge_recovery_source_authority_adjudicated"] is False
    assert result.packet["source_challenge_recovery_source_obligation_satisfied"] is False
    assert result.packet["source_challenge_recovery_result"]["citation_eligible"] is False
    assert result.packet["answer_text_present"] is False


def test_failure_attribution_buckets_cover_downstream_stages(
    tmp_path: Path,
) -> None:
    provider_calls: list[dict[str, Any]] = []
    no_results = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="model-planning-provider-bucket",
        confirm_live_dogfood=True,
        product_provider_acquisition_runner=_product_runner(
            provider_calls,
            first_stage_results=[],
        ),
        fast_model_planner_callable=_planner([]),
        fast_model_planner_strict_route_ref=_strict_route_ref(),
        require_model_assisted_planning=True,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )
    selector_block = build_generic_single_relation_live_dogfood_run_output(
        query=SMALL_CLAIMS_QUERY,
        repo_root=tmp_path,
        output_dir=tmp_path / DEFAULT_OUTPUT_DIR,
        run_id="model-planning-selector-bucket",
        confirm_live_dogfood=True,
        product_provider_acquisition_runner=_product_runner(
            [],
            first_stage_results=[
                {
                    "title": "Example County Empty Official Fee Page",
                    "url": "https://example-county.gov/court/fees",
                    "snippet": "Official fee page with no retained amount.",
                    "rank": 1,
                }
            ],
        ),
        fetch_read_runner=_empty_fetch_runner,
        fast_model_planner_callable=_planner([]),
        fast_model_planner_strict_route_ref=_strict_route_ref(),
        require_model_assisted_planning=True,
        environ={"PYTEST_CURRENT_TEST": "test"},
    )

    assert no_results.packet["failure_attribution_bucket"] == "provider_acquisition"
    assert selector_block.decision == (
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES
    )
    assert selector_block.packet["failure_attribution_bucket"] == "selector_or_window"


def test_no_direct_model_client_or_us_specific_planning_hardcode() -> None:
    planner_text = PLANNER_MODULE_PATH.read_text(encoding="utf-8")
    dogfood_text = DOGFOOD_MODULE_PATH.read_text(encoding="utf-8")

    forbidden_imports = (
        "from core.llm import",
        "import core.llm",
        "openai",
        "anthropic",
        "requests",
        "search_web_results",
        "search_scout_results",
    )
    assert all(text not in planner_text for text in forbidden_imports)
    assert "ask_model(" not in dogfood_text
    assert "fast_model_planner_callable=ask_model" not in dogfood_text
    assert "USCIS" not in planner_text
    assert "N-400" not in planner_text
    assert "G-1055" not in planner_text
    assert "IRS" not in planner_text


def _strict_route_ref() -> dict[str, Any]:
    return {
        "model_task": planning.MODEL_ASSISTED_PLANNING_MODEL_TASK,
        "product_model_role": planning.MODEL_ASSISTED_PLANNING_PRODUCT_MODEL_ROLE,
        "product_route_kind": "strict_one_shot_model_route",
        "configured_fast_provider": "FakeFast",
        "configured_fast_model": "fake-fast",
        "configured_endpoint_kind": "openai_responses_api",
        "max_model_calls": 1,
        "retry_policy": "forbidden",
        "fallback_policy": "forbidden",
        "timeout_policy": "fail_closed",
        "provider_switching_allowed": False,
        "endpoint_switching_allowed": False,
        "strict_one_shot": True,
        "call_count": 0,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "provider_payload_retained": False,
    }


def _context_state() -> dict[str, Any]:
    return {
        "sanitized_query": SMALL_CLAIMS_QUERY,
        "normalized_user_question": SMALL_CLAIMS_QUERY,
        "relation_plan_id": "plan:test",
        "source_class": "official source of record",
        "current_failure_diagnostics": {
            "provider_calls_attempted": 1,
            "source_obligation_recovery_required": True,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "raw_provider_payload_retained": False,
        },
    }


def _proposal(context_kind: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "planning_context_kind": context_kind,
        "normalized_user_question": SMALL_CLAIMS_QUERY,
        "component_count_hypothesis": "likely_single",
        "single_relation_lane_eligible": True,
        "relation_or_component_hypothesis": "current filing fee relation",
        "likely_fact_kind": "current_fee",
        "source_obligation_hypothesis": "source-of-record official fee schedule",
        "expected_source_class": "official local court website",
        "source_class_uncertainty": "",
        "official_or_source_of_record_artifact_hypotheses": [
            "official small claims fee schedule"
        ],
        "likely_official_domains": ["example-county.gov"],
        "likely_official_path_or_page_hints": ["court fees"],
        "acquisition_query_variants": [
            "Example County official small claims filing fee schedule"
        ],
        "preferred_acquisition_query": (
            "Example County official small claims filing fee schedule"
        ),
        "disambiguation_status": "clear",
        "disambiguation_reason": "",
        "disambiguation_questions_or_hints": [],
        "recovery_query_variants": [
            "Example County court official fee schedule small claims"
        ],
        "preferred_recovery_query": "",
        "recovery_reasoning_summary": "",
        "answer_bearing_material_criteria": [
            "official current amount for small claims filing fee"
        ],
        "answer_bearing_anchor_terms": ["small claims", "filing fee"],
        "expected_value_token_kinds": ["currency"],
        "currentness_hints": ["current fee schedule"],
        "uncertainty_notes": [],
        "planner_caveats": ["planning metadata only"],
        "reduced_status": "acquisition_hypotheses_available",
    }
    payload.update(overrides)
    return {key: value for key, value in payload.items() if value is not None}


def _planner(
    calls: list[dict[str, Any]],
    *,
    proposal: Mapping[str, Any] | None = None,
    proposals: list[Mapping[str, Any]] | None = None,
) -> Any:
    proposal_queue = list(proposals or ([] if proposal is None else [proposal]))

    def fake_planner(_prompt: str, _system_prompt: str, **kwargs: Any) -> str:
        context_kind = str(kwargs["planning_context_kind"])
        calls.append(
            {
                "planning_context_kind": context_kind,
                "provider": kwargs.get("provider"),
                "model": kwargs.get("model"),
                "require_json": kwargs.get("require_json"),
                "max_tokens": kwargs.get("max_tokens"),
                "use_reasoning": kwargs.get("use_reasoning"),
            }
        )
        next_proposal = (
            dict(proposal_queue.pop(0))
            if proposal_queue
            else _proposal(context_kind)
        )
        next_proposal.setdefault("planning_context_kind", context_kind)
        return json.dumps(next_proposal)

    return fake_planner


def _product_runner(
    calls: list[dict[str, Any]],
    *,
    scout: bool = False,
    first_stage_results: list[dict[str, Any]] | None = None,
    recovery_results: list[dict[str, Any]] | None = None,
) -> Any:
    call_index = 0

    def fake_tavily(**kwargs: Any) -> tuple[list[dict[str, Any]], list[Any]]:
        nonlocal call_index
        call_index += 1
        calls.append({"provider": "tavily", **kwargs})
        if call_index == 1:
            return (
                first_stage_results
                if first_stage_results is not None
                else _first_stage_results()
            ), []
        return (recovery_results or _official_answer_bearing_recovery_results()), []

    def fake_scout(**kwargs: Any) -> list[dict[str, Any]]:
        if not scout:
            raise AssertionError("scout must not run for this test")
        calls.append({"provider": "serper", **kwargs})
        return [
            {
                "title": "Example County court fees",
                "url": "https://example-county.gov/court/fees",
                "domain": "example-county.gov",
                "snippet": "Directionality only scout result.",
                "position": 1,
            }
        ]

    return build_generic_product_provider_acquisition_runner(
        tavily_product_provider_callable=fake_tavily,
        scout_product_provider_callable=fake_scout,
    )


def _first_stage_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example County Filing Fee Guide",
            "url": "https://example-law.invalid/small-claims-fees",
            "snippet": "Non-official current filing fee explainer.",
            "raw_content": (
                "Example County small claims filing fee guide. The current "
                "small claims filing fee is $42 in this non-official explainer."
            ),
            "rank": 1,
        },
        {
            "title": "Example County Court Fees",
            "url": "https://example-county.gov/court/fees",
            "snippet": "Official fee schedule overview.",
            "raw_content": (
                "Example County official court fee schedule and filing fee "
                "overview without the current small claims amount."
            ),
            "rank": 2,
        },
    ]


def _official_answer_bearing_recovery_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example County Official Small Claims Fee Schedule",
            "url": "https://example-county.gov/court/small-claims-fee-schedule",
            "snippet": "Official current small claims fee schedule.",
            "raw_content": (
                "Example County official small claims fee schedule. The current "
                "small claims filing fee is $42."
            ),
            "rank": 1,
        }
    ]


def _official_generic_recovery_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example County Official Small Claims Filing",
            "url": "https://example-county.gov/court/small-claims",
            "snippet": "Official filing instructions.",
            "raw_content": (
                "Example County official small claims filing instructions, "
                "eligibility, and courthouse hours."
            ),
            "rank": 1,
        }
    ]


def _weak_or_overclaim_review(*_args: Any, **kwargs: Any) -> dict[str, Any]:
    payload = _assessment_payload(
        kwargs["input_packet"],
        support_relation="weak_or_overclaim_risk",
        claim=ANSWER_CLAIM,
    )
    payload["challenge_recommended"] = True
    payload["non_support_reason_when_not_direct"] = (
        "The answer-bearing material is not source-of-record confirmation."
    )
    return payload


def _must_not_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    raise AssertionError("D-prime review must not run")


def _fetch_read_must_not_run(_url: str) -> GenericLiveFetchReadResult:
    raise AssertionError("fetch/read must not run")


def _empty_fetch_runner(url: str) -> GenericLiveFetchReadResult:
    return GenericLiveFetchReadResult(
        attempted_url=url,
        final_url=url,
        final_domain="example-county.gov",
        status_code=200,
        status_class="2xx",
        content_type="text/html",
        fetched_byte_count=0,
        sanitized_text="",
        content_title="Empty official fee page",
        redirect_count=0,
        retrieved_or_observed_at="2026-07-03T00:00:00+00:00",
    )
