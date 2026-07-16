from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.query_production_runtime import execute_query_production_action
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.run_authority_contract_runtime import execute_run_contract_synthesis_action
from core.run_kernel import QUERY_PLAN_ADMISSION_STAGE, QUERY_PRODUCTION_STAGE, RunKernel
from core.search_work_plan import (
    EffectiveContractKind,
    ModeMismatchPosture,
    ProviderJobKind,
    QueryShapeKind,
    SearchMode,
    SourceObligationKind,
)
from core.search_work_plan_shadow_runtime import (
    RuntimeShadowSearchWorkPlanInput,
    build_runtime_shadow_search_work_plan_input,
)
from core.search_work_shadow_lane_runtime import run_search_work_shadow_lane

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
CLASSIFIER = ROOT / "core" / "search_work_query_shape_runtime.py"

QUALIFIED = "QUALIFIED"
NOT_STRUCTURED = "NOT_STRUCTURED"
AMBIGUOUS = "AMBIGUOUS"


class _Status:
    def step(self, _message: str) -> None:
        return None


class _Logger:
    def warning(self, _message: str, _error: Exception) -> None:
        return None


def _route_projection(query: str) -> dict[str, Any]:
    return {
        "intent": "general",
        "report_type": "general_research",
        "query_type": "rule",
        "core_topic": query[:100],
        "primary_entity": "ag96e1-fixture",
        "is_academic": False,
    }


def _contract(query: str, *, mode: str = "Balanced") -> tuple[dict[str, Any], dict[str, Any]]:
    route = _route_projection(query)
    kernel = RunKernel.start(run_id=f"ag96e1-contract-{abs(hash((query, mode)))}", request_id="request")
    action = kernel.authorize_run_contract_synthesis(inputs={"query_length": len(query)})
    result = execute_run_contract_synthesis_action(
        action,
        query=query,
        mode=mode,
        current_date="June 15, 2026",
        route_projection=route,
    )
    kernel.reduce(result.observation)
    return dict(kernel.state.run_contract_projection), route


def _construction_input(query: str, *, mode: str = "Balanced") -> Any:
    contract, route = _contract(query, mode=mode)
    return build_runtime_shadow_search_work_plan_input(
        RuntimeShadowSearchWorkPlanInput(
            run_contract_projection=contract,
            route_projection=route,
            requested_mode=mode,
            selected_depth=contract.get("selected_depth"),
            safe_query_preview=query,
            current_date_ref={"id": "current-date:test"},
        )
    )


def _assessment_payload(query: str, *, mode: str = "Balanced") -> dict[str, Any]:
    return _construction_input(query, mode=mode).query_shape_assessment.to_dict()


def _resolution_payload(query: str, *, mode: str = "Balanced") -> dict[str, Any]:
    return _construction_input(query, mode=mode).contract_resolution.to_dict()


def _run_lane(query: str, *, mode: str = "Balanced") -> tuple[RunKernel, dict[str, Any], dict[str, Any]]:
    contract, route = _contract(query, mode=mode)
    kernel = RunKernel.start(run_id=f"ag96e1-lane-{abs(hash((query, mode)))}", request_id="request")
    action = kernel.authorize_run_contract_synthesis(inputs={"fixture": True})
    kernel.reduce(
        execute_run_contract_synthesis_action(
            action,
            query=query,
            mode=mode,
            current_date="June 15, 2026",
            route_projection=route,
        ).observation
    )
    contract = dict(kernel.state.run_contract_projection)
    lane = run_search_work_shadow_lane(
        run_kernel=kernel,
        run_contract_projection=contract,
        route_projection=route,
        requested_mode=mode,
        selected_depth=contract.get("selected_depth"),
        safe_query_preview=query,
        current_date_ref={"id": "current-date:test"},
        metadata={"callsite": "ag96e1-unit-test"},
    )
    return kernel, contract, lane


def _clean_query(value: str) -> str:
    return " ".join(str(value or "").split())[:300]


def _router_state(query: str) -> Any:
    return build_router_query_preparation_state(
        query=query,
        router_text=json.dumps(
            {
                "intent": "general",
                "report_type": "general_research",
                "query_type": "rule",
                "core_topic": query[:100],
                "primary_entity": "ag96e1-fixture",
                "entities": ["ag96e1-fixture"],
                "is_academic": False,
            }
        ),
    )


def _query_production_result(
    kernel: RunKernel,
    *,
    query: str,
    run_contract_projection: Mapping[str, Any],
) -> Any:
    def ask_model(*_args: Any, **_kwargs: Any) -> str:
        return '{"queries":["current official filing fee","effective filing fee"]}'

    action = kernel.authorize_query_production(
        inputs={
            "strategy": "Balanced",
            "run_contract_id": run_contract_projection["contract_id"],
        }
    )
    return execute_query_production_action(
        action,
        router_query_preparation_contract=_router_state(query),
        query=query,
        strategy="Balanced",
        current_date="June 15, 2026",
        focus_academic=False,
        force_intent_news=False,
        include_domains=[],
        news_preferred_domains=["reuters.com"],
        ask_model=ask_model,
        clean_json_response=lambda text: text,
        default_system={
            "researcher": "researcher-system",
            "recon_query_rewriter": "recon-system",
        },
        fast_provider="fast-provider",
        fast_model="fast-model",
        local_url="http://local",
        api_key=None,
        use_reasoning=True,
        measure_context_stage=lambda *_args, **_kwargs: None,
        clean_query=_clean_query,
        cost_accumulator=object(),
        status=_Status(),
        provider_diagnostics=[],
        run_log=_Logger(),
        brave_api_key_available=False,
        run_contract_projection=dict(run_contract_projection),
    )


def _kinds(payload: dict[str, Any]) -> set[str]:
    return set(payload["query_shape_kinds"])


def _obligation_kinds(payload: dict[str, Any]) -> set[str]:
    return {
        item["kind"]
        for item in payload["source_obligation_candidates"]
    }


def _provider_job_kinds(payload: dict[str, Any]) -> set[str]:
    return {
        item["job_kind"]
        for item in payload["provider_job_candidates"]
    }


def _component_obligation_kind_map(payload: dict[str, Any]) -> dict[str, set[str]]:
    obligation_kind_by_candidate_id = {
        item["candidate_id"]: item["kind"]
        for item in payload["source_obligation_candidates"]
    }
    return {
        item["user_facing_subquestion"]: {
            obligation_kind_by_candidate_id[candidate_id]
            for candidate_id in item.get("source_obligation_candidate_ids", [])
            if candidate_id in obligation_kind_by_candidate_id
        }
        for item in payload["component_candidates"]
    }


def _component_questions(payload: dict[str, Any]) -> list[str]:
    return [
        str(item["user_facing_subquestion"])
        for item in payload["component_candidates"]
    ]


def _assert_no_structured_route_authority(query: str) -> None:
    metadata = _assessment_payload(query)["metadata"]

    assert metadata["structured_route_posture"] == AMBIGUOUS
    assert metadata["explicit_factual_component_list"] is False
    assert metadata["requested_synthesis_directive"] is None
    assert metadata["route_qualification_behavior_changed"] is False
    assert metadata["query_plan_behavior_changed"] is False
    assert metadata["provider_search_behavior_changed"] is False


@pytest.mark.parametrize(
    "query",
    [
        (
            "Compare them first. 1. Find the first value. "
            "2. Find the second value. 3. Explain how they relate."
        ),
        (
            "Calculate these first: - Find the first value. "
            "- Find the second value. - Explain the result."
        ),
        (
            "Compare these values: Find the first value; "
            "find the second value; then explain the result."
        ),
        (
            "Find the governing context first. 1. Find the first value. "
            "2. Find the second value. 3. Compare them."
        ),
        (
            "What is the governing context? - Find the first value. "
            "- Find the second value. - Compare them."
        ),
    ],
    ids=(
        "directive-before-numbered",
        "directive-before-bullets",
        "directive-before-colon-imperatives",
        "retrieval-before-numbered",
        "interrogative-before-bullets",
    ),
)
def test_actionable_structured_prefix_cannot_be_discarded(query: str) -> None:
    _assert_no_structured_route_authority(query)


@pytest.mark.parametrize(
    "query",
    [
        (
            "1. Find the first value. 2. Find the second value. "
            "3. Compare them and what is the third value?"
        ),
        (
            "1. Find the first value. 2. Find the second value. "
            "Compare them. Who publishes the governing rule?"
        ),
        (
            "1. Find the first value. 2. Find the second value. "
            "3. Explain how they relate; where is the third source?"
        ),
    ],
    ids=("and-what", "sentence-who", "semicolon-where"),
)
def test_interrogative_component_cannot_be_hidden_in_directive(
    query: str,
) -> None:
    _assert_no_structured_route_authority(query)


@pytest.mark.parametrize(
    ("query", "expected_syntax_kind"),
    [
        (
            "For the fictional Northstar program: 1. Find the first value. "
            "2. Find the second value. 3. Compare them.",
            "numbered_imperative",
        ),
        (
            "For the fictional Northstar program: - Find the first value. "
            "- Find the second value. - Compare them.",
            "bullet_imperative",
        ),
        (
            "For the fictional Northstar program: Find the first value; "
            "find the second value; then compare them.",
            "imperative_clauses",
        ),
    ],
    ids=("numbered", "bullets", "imperative-clauses"),
)
def test_benign_contextual_preamble_remains_qualified(
    query: str,
    expected_syntax_kind: str,
) -> None:
    metadata = _assessment_payload(query)["metadata"]

    assert metadata["structured_route_posture"] == QUALIFIED
    assert metadata["structured_route_syntax_kind"] == expected_syntax_kind
    assert metadata["explicit_factual_component_list"] is True


@pytest.mark.parametrize(
    "directive",
    [
        "Compare them and explain what the difference means.",
        (
            "Compare them, calculate the difference, and convert both values "
            "to USD."
        ),
    ],
    ids=("explain-what", "calculate-and-convert"),
)
def test_legitimate_combined_directive_remains_complete(
    directive: str,
) -> None:
    query = (
        "1. Find the first value. 2. Find the second value. 3. "
        f"{directive}"
    )
    metadata = _assessment_payload(query)["metadata"]

    assert metadata["structured_route_posture"] == QUALIFIED
    assert metadata["requested_synthesis_directive"] == directive


@pytest.mark.parametrize(
    (
        "query",
        "expected_questions",
        "expected_directive",
        "expected_syntax_kind",
        "expected_behavior_changed",
    ),
    [
        (
            "For the fictional program: - What is the first value? "
            "- What is the second value? Then explain how these facts relate.",
            [
                "Answer the first value component.",
                "Answer the second value component.",
            ],
            "Then explain how these facts relate.",
            "bullet_interrogative",
            False,
        ),
        (
            "1. What is the first value? 2. What is the second value? "
            "3. Compare them and explain the difference.",
            [
                "Answer the first value component.",
                "Answer the second value component.",
            ],
            "Compare them and explain the difference.",
            "numbered_interrogative",
            True,
        ),
        (
            "1) Find the first reported value. 2) Find the second reported value. "
            "3) Calculate the difference.",
            [
                "Answer the first reported value component.",
                "Answer the second reported value component.",
            ],
            "Calculate the difference.",
            "numbered_imperative",
            True,
        ),
        (
            "1. Find the first value. 2. Find the second value. "
            "Convert both values to the requested unit and compare them.",
            [
                "Answer the first value component.",
                "Answer the second value component.",
            ],
            "Convert both values to the requested unit and compare them.",
            "numbered_imperative",
            True,
        ),
        (
            "For the fictional program: - Identify the first value. "
            "- Locate the second value. - Show how they relate.",
            [
                "Answer the first value component.",
                "Answer the second value component.",
            ],
            "Show how they relate.",
            "bullet_imperative",
            True,
        ),
        (
            "Find the first official value; find the second official value; "
            "then compare them and calculate the difference.",
            [
                "Answer the first official value component.",
                "Answer the second official value component.",
            ],
            "then compare them and calculate the difference.",
            "imperative_clauses",
            True,
        ),
    ],
)
def test_explicit_structured_route_matrix_uses_one_authoritative_result(
    query: str,
    expected_questions: list[str],
    expected_directive: str,
    expected_syntax_kind: str,
    expected_behavior_changed: bool,
) -> None:
    assessment = _assessment_payload(query)
    repeated_assessment = _assessment_payload(query)
    metadata = assessment["metadata"]
    construction = _construction_input(query)

    assert metadata["structured_route_posture"] == QUALIFIED
    assert metadata["structured_route_syntax_kind"] == expected_syntax_kind
    assert metadata["explicit_factual_component_list"] is True
    assert metadata["requested_synthesis_directive"] == expected_directive
    assert (
        metadata["route_qualification_behavior_changed"]
        is expected_behavior_changed
    )
    assert metadata["behavior_changed"] is False
    assert metadata["query_plan_behavior_changed"] is False
    assert metadata["provider_search_behavior_changed"] is False
    assert _component_questions(assessment) == expected_questions
    assert (
        repeated_assessment["component_candidates"]
        == assessment["component_candidates"]
    )
    assert all(
        expected_directive not in question
        for question in _component_questions(assessment)
    )
    assert (
        construction.metadata["route_qualification_behavior_changed"]
        is expected_behavior_changed
    )
    assert construction.metadata["query_plan_behavior_changed"] is False
    assert construction.metadata["provider_search_behavior_changed"] is False


@pytest.mark.parametrize(
    ("query", "expected_posture"),
    [
        ("1. Find the first value. 2. Compare it.", AMBIGUOUS),
        (
            "1. Find value one. 2. Find value two. 3. Find value three. "
            "4. Find value four. 5. Find value five. 6. Find value six. "
            "7. Compare them.",
            AMBIGUOUS,
        ),
        ("1. Find the first value. 2. Find the second value.", AMBIGUOUS),
        ("1. Open the app. 2. Click settings. 3. Save the form.", AMBIGUOUS),
        (
            "1. Find the first value. 3. Find the second value. 4. Compare them.",
            AMBIGUOUS,
        ),
        (
            "2. Find the first value. 3. Find the second value. 4. Compare them.",
            AMBIGUOUS,
        ),
        (
            "1. Find the first value. 2. Compare them. 3. Find the second value.",
            AMBIGUOUS,
        ),
        (
            "1. Find the first value. 2. Find the first value. 3. Compare them.",
            AMBIGUOUS,
        ),
        (
            "1. Find the first value. 2. 3. Find the second value. 4. Compare them.",
            AMBIGUOUS,
        ),
        (
            "- Program values: - Find the first value. - Find the second value. "
            "- Compare them.",
            AMBIGUOUS,
        ),
        (
            "The release is version 1.2.3, costs $3.50, and changed by 4.5 percent.",
            NOT_STRUCTURED,
        ),
        (
            "On 2026-07-16 the value was $1.50 and the rate was 25.0%.",
            NOT_STRUCTURED,
        ),
        ("See citations [1] and [2] for the two values.", NOT_STRUCTURED),
        ("1 Find the first value and 2 find the second value.", NOT_STRUCTURED),
        ("Find the current rule and summarize it.", NOT_STRUCTURED),
        ("Convert 10 USD to EUR.", NOT_STRUCTURED),
        (
            "1. Find the first value and compare it. 2. Find the second value. "
            "3. Explain the result.",
            AMBIGUOUS,
        ),
        (
            "1. Find the first value. 2. Find the second value. "
            "3. Compare them and find a third value.",
            AMBIGUOUS,
        ),
    ],
)
def test_rejected_or_unstructured_requests_never_gain_route_authority(
    query: str,
    expected_posture: str,
) -> None:
    assessment = _assessment_payload(query)
    metadata = assessment["metadata"]

    assert metadata["structured_route_posture"] == expected_posture
    assert metadata["explicit_factual_component_list"] is False
    assert metadata["requested_synthesis_directive"] is None
    assert metadata["route_qualification_behavior_changed"] is False
    assert metadata["query_plan_behavior_changed"] is False
    assert metadata["provider_search_behavior_changed"] is False


def test_ambiguous_explicit_structure_may_retain_fallback_components_without_route_authority() -> None:
    query = (
        "- Find the first value and compare it; - Find the second value; "
        "Then explain how they relate."
    )
    assessment = _assessment_payload(query)
    metadata = assessment["metadata"]

    assert metadata["structured_route_posture"] == AMBIGUOUS
    assert metadata["explicit_factual_component_list"] is False
    assert metadata["requested_synthesis_directive"] is None
    assert len(assessment["component_candidates"]) > 1


@pytest.mark.parametrize(
    "query",
    [
        (
            "1. What is the first value? 2. What is the second value? "
            "3. Compare them and explain the difference."
        ),
        (
            "Find the first official value; find the second official value; "
            "then compare them and calculate the difference."
        ),
    ],
)
def test_fast_balanced_deep_share_identical_structured_route_assessment(
    query: str,
) -> None:
    payloads = [
        _assessment_payload(query, mode=mode)
        for mode in ("Fast", "Balanced", "Deep")
    ]
    route_views = [
        {
            "structured_route_posture": payload["metadata"][
                "structured_route_posture"
            ],
            "structured_route_syntax_kind": payload["metadata"][
                "structured_route_syntax_kind"
            ],
            "component_questions": _component_questions(payload),
            "explicit_factual_component_list": payload["metadata"][
                "explicit_factual_component_list"
            ],
            "requested_synthesis_directive": payload["metadata"][
                "requested_synthesis_directive"
            ],
            "route_qualification_behavior_changed": payload["metadata"][
                "route_qualification_behavior_changed"
            ],
        }
        for payload in payloads
    ]

    assert route_views[0] == route_views[1] == route_views[2]


def test_structured_route_parser_has_one_mode_neutral_implementation() -> None:
    tree = ast.parse(CLASSIFIER.read_text(encoding="utf-8"))
    parsers = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_assess_structured_multicomponent_shape"
    ]
    parser_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_assess_structured_multicomponent_shape"
    ]

    assert len(parsers) == 1
    assert len(parser_calls) == 1
    parser_names = {
        node.id for node in ast.walk(parsers[0]) if isinstance(node, ast.Name)
    }
    assert parser_names.isdisjoint(
        {"requested_mode", "SearchMode", "FAST", "BALANCED", "DEEP"}
    )


def test_simple_lookup_produces_one_simple_component_without_strict_official_or_legal() -> None:
    assessment = _assessment_payload("Who founded SQLite?")

    assert _kinds(assessment) == {QueryShapeKind.SIMPLE_LOOKUP.value}
    assert len(assessment["component_candidates"]) == 1
    assert SourceObligationKind.OFFICIAL_CURRENT.value not in _obligation_kinds(assessment)
    assert SourceObligationKind.LEGAL_CURRENT_PRIMARY.value not in _obligation_kinds(assessment)


def test_official_current_query_derives_official_obligation_and_acquisition_hint() -> None:
    assessment = _assessment_payload("What is the current official filing fee for Form I-130?")

    assert QueryShapeKind.OFFICIAL_CURRENT_LOOKUP.value in _kinds(assessment)
    assert SourceObligationKind.OFFICIAL_CURRENT.value in _obligation_kinds(assessment)
    assert ProviderJobKind.OFFICIAL_CANDIDATE_ACQUISITION.value in _provider_job_kinds(assessment)


def test_legal_current_primary_query_derives_legal_obligation_and_currentness_hints() -> None:
    assessment = _assessment_payload("What is the current California legal deadline to appeal?")

    assert QueryShapeKind.LEGAL_CURRENT_PRIMARY.value in _kinds(assessment)
    assert SourceObligationKind.LEGAL_CURRENT_PRIMARY.value in _obligation_kinds(assessment)
    assert ProviderJobKind.CANONICAL_EXTRACTION.value in _provider_job_kinds(assessment)
    assert ProviderJobKind.CONFLICT_CURRENTNESS_CHECK.value in _provider_job_kinds(assessment)


def test_canonical_documentation_query_derives_canonical_obligation() -> None:
    assessment = _assessment_payload("What does the OpenAI Responses API parameter stream mean in the current docs?")

    assert QueryShapeKind.CANONICAL_DOCUMENTATION.value in _kinds(assessment)
    assert SourceObligationKind.CANONICAL_DOCUMENTATION.value in _obligation_kinds(assessment)
    assert ProviderJobKind.CANONICAL_EXTRACTION.value in _provider_job_kinds(assessment)


def test_source_bound_numeric_query_derives_numeric_obligation_and_fetch_read_hint() -> None:
    assessment = _assessment_payload("What is the current numeric rate and how is it calculated?")

    assert QueryShapeKind.SOURCE_BOUND_NUMERIC.value in _kinds(assessment)
    assert SourceObligationKind.SOURCE_BOUND_NUMERIC.value in _obligation_kinds(assessment)
    assert ProviderJobKind.FETCH_READ_EXTRACT.value in _provider_job_kinds(assessment)


def test_multipart_query_produces_multiple_components_in_lane_projection() -> None:
    query = "What are the current official fee, legal deadline, and API parameter?"
    kernel, _contract, lane = _run_lane(query)
    query_plan_shadow = lane["query_plan_work_shadow_projection"]

    assert lane["implements_query_shape_classifier"] is True
    assert lane["implements_contract_resolver"] is True
    assert lane["search_work_plan_fallback_reason"] is None
    assert kernel.state.search_work_plan_projection["component_count"] >= 3
    assert query_plan_shadow["work_counts"]["component_count"] >= 3
    assert len(query_plan_shadow["candidate_work_groups"]) >= 3
    metadata = _assessment_payload(query)["metadata"]
    assert metadata["structured_route_posture"] == NOT_STRUCTURED
    assert metadata["explicit_factual_component_list"] is False
    assert metadata["requested_synthesis_directive"] is None
    assert metadata["route_qualification_behavior_changed"] is False


def test_multipart_component_obligations_are_component_local() -> None:
    query = "What are the current official fee, legal deadline, and API parameter?"
    assessment = _assessment_payload(query)
    obligation_map = _component_obligation_kind_map(assessment)
    strict_obligations = {
        SourceObligationKind.OFFICIAL_CURRENT.value,
        SourceObligationKind.LEGAL_CURRENT_PRIMARY.value,
        SourceObligationKind.CANONICAL_DOCUMENTATION.value,
    }

    assert len(obligation_map) >= 3
    fee_kinds = next(
        kinds for question, kinds in obligation_map.items() if "fee" in question
    )
    legal_kinds = next(
        kinds for question, kinds in obligation_map.items() if "legal deadline" in question
    )
    api_kinds = next(
        kinds for question, kinds in obligation_map.items() if "API parameter" in question
    )

    assert SourceObligationKind.OFFICIAL_CURRENT.value in fee_kinds
    assert SourceObligationKind.LEGAL_CURRENT_PRIMARY.value in legal_kinds
    assert SourceObligationKind.CANONICAL_DOCUMENTATION.value in api_kinds
    assert SourceObligationKind.LEGAL_CURRENT_PRIMARY.value not in fee_kinds
    assert SourceObligationKind.CANONICAL_DOCUMENTATION.value not in fee_kinds
    assert SourceObligationKind.OFFICIAL_CURRENT.value not in legal_kinds
    assert SourceObligationKind.CANONICAL_DOCUMENTATION.value not in legal_kinds
    assert SourceObligationKind.OFFICIAL_CURRENT.value not in api_kinds
    assert SourceObligationKind.LEGAL_CURRENT_PRIMARY.value not in api_kinds
    assert all(
        not strict_obligations.issubset(kinds)
        for kinds in obligation_map.values()
    )


def test_compare_query_marks_conflict_and_official_current_work_hints() -> None:
    assessment = _assessment_payload("Compare X and Y using official current sources.")

    assert QueryShapeKind.COMPARATIVE.value in _kinds(assessment)
    assert QueryShapeKind.CONFLICT_LIKELY.value in _kinds(assessment)
    assert SourceObligationKind.OFFICIAL_CURRENT.value in _obligation_kinds(assessment)
    assert SourceObligationKind.CONFLICT_RESOLUTION.value in _obligation_kinds(assessment)
    assert ProviderJobKind.CONFLICT_CURRENTNESS_CHECK.value in _provider_job_kinds(assessment)
    assert assessment["metadata"]["structured_route_posture"] == NOT_STRUCTURED
    assert assessment["metadata"]["explicit_factual_component_list"] is False
    assert assessment["metadata"]["requested_synthesis_directive"] is None


def test_fast_balanced_deep_modes_resolve_answer_contracts_without_queryplan_consumption() -> None:
    query = "What is the current official filing fee for Form I-130?"

    fast = _resolution_payload(query, mode="Fast")
    balanced = _resolution_payload(query, mode="Balanced")
    deep = _resolution_payload(query, mode="Deep")

    assert fast["requested_mode"] == SearchMode.FAST.value
    assert fast["effective_contract"] == EffectiveContractKind.DIRECT_CONSTRAINED.value
    assert balanced["requested_mode"] == SearchMode.BALANCED.value
    assert balanced["effective_contract"] == EffectiveContractKind.EXPLANATORY.value
    assert deep["requested_mode"] == SearchMode.DEEP.value
    assert deep["effective_contract"] == EffectiveContractKind.RESEARCH_RECONCILIATION.value

    kernel, _contract, lane = _run_lane(query, mode="Fast")
    assert lane["runtime_consumed_by_query_plan"] is False
    assert kernel.state.search_work_plan_projection["runtime_consumed_by_query_plan"] is False
    assert QUERY_PRODUCTION_STAGE not in kernel.state.stage_statuses
    assert QUERY_PLAN_ADMISSION_STAGE not in kernel.state.stage_statuses


def test_complexity_mismatch_is_shadow_recorded_without_mutating_selected_mode() -> None:
    query = "What are the current official fee, legal deadline, and API parameter?"
    resolution = _resolution_payload(query, mode="Fast")
    kernel, contract, lane = _run_lane(query, mode="Fast")

    assert resolution["requested_mode"] == SearchMode.FAST.value
    assert resolution["effective_contract"] == EffectiveContractKind.DIRECT_CONSTRAINED.value
    assert (
        resolution["mode_mismatch_posture"]
        == ModeMismatchPosture.SELECTED_MODE_INSUFFICIENT.value
    )
    assert contract["selected_depth"] == "Fast"
    assert lane["query_plan_behavior_changed"] is False
    assert lane["query_text_generated"] is False


def test_query_production_output_remains_unchanged_with_real_shadow_path() -> None:
    query = "What is the current official filing fee for Form I-130?"
    baseline_contract, baseline_route = _contract(query)
    shadow_contract, shadow_route = _contract(query)
    baseline_kernel = RunKernel.start(run_id="ag96e1-baseline", request_id="request")
    shadow_kernel = RunKernel.start(run_id="ag96e1-shadow", request_id="request")

    baseline = _query_production_result(
        baseline_kernel,
        query=query,
        run_contract_projection=baseline_contract,
    )
    action = shadow_kernel.authorize_run_contract_synthesis(inputs={"fixture": True})
    shadow_kernel.reduce(
        execute_run_contract_synthesis_action(
            action,
            query=query,
            mode="Balanced",
            current_date="June 15, 2026",
            route_projection=shadow_route,
        ).observation
    )
    shadow_contract = dict(shadow_kernel.state.run_contract_projection)
    run_search_work_shadow_lane(
        run_kernel=shadow_kernel,
        run_contract_projection=shadow_contract,
        route_projection=shadow_route,
        requested_mode="Balanced",
        selected_depth=shadow_contract.get("selected_depth"),
        safe_query_preview=query,
        current_date_ref={"id": "current-date:test"},
    )
    with_lane = _query_production_result(
        shadow_kernel,
        query=query,
        run_contract_projection=shadow_contract,
    )

    assert with_lane.candidate_queries == baseline.candidate_queries
    assert with_lane.candidate_source == baseline.candidate_source
    assert with_lane.contract_source_requirement_hints == baseline.contract_source_requirement_hints


def test_fallback_path_is_tagged_when_deterministic_records_fail(monkeypatch: Any) -> None:
    import core.search_work_plan_shadow_runtime as shadow_runtime

    def fail_records(*_args: Any, **_kwargs: Any) -> None:
        raise ValueError("forced failure")

    monkeypatch.setattr(
        shadow_runtime,
        "build_deterministic_search_work_runtime_records",
        fail_records,
    )
    construction = _construction_input("What is the current official filing fee for Form I-130?")

    metadata = construction.metadata
    assert metadata["runtime_shadow_scaffolding"] is True
    assert metadata["implements_query_shape_classifier"] is False
    assert metadata["implements_contract_resolver"] is False
    assert metadata["fallback_reason"] == "deterministic_ag96e1_failed:ValueError"


def test_redaction_preserves_sensitive_key_boundary() -> None:
    contract, route = _contract("What is the current official filing fee for Form I-130?")
    construction = build_runtime_shadow_search_work_plan_input(
        RuntimeShadowSearchWorkPlanInput(
            run_contract_projection={
                **contract,
                "raw_prompt": "RAW_PROMPT_SENTINEL",
                "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
                "raw_model_response": "RAW_MODEL_SENTINEL",
            },
            route_projection={
                **route,
                "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
                "token": "TOKEN_SENTINEL",
            },
            requested_mode="Balanced",
            selected_depth=contract.get("selected_depth"),
            safe_query_preview="What is the current official filing fee for Form I-130?",
            metadata={
                "db_row": "DB_ROW_SENTINEL",
                "full_trace": "TRACE_SENTINEL",
            },
        )
    )
    encoded = json.dumps(construction.to_dict(), sort_keys=True)

    for field_name in (
        "raw_prompt",
        "raw_provider_payload",
        "raw_model_response",
        "secret",
        "token",
        "db_row",
        "full_trace",
    ):
        assert field_name not in encoded
    for sentinel in (
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "RAW_MODEL_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "TRACE_SENTINEL",
    ):
        assert sentinel not in encoded


def test_pipeline_remains_one_pass_through_lane_call_without_classifier_logic() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_search_work_shadow_lane"
    ]

    assert len(calls) == 1
    assert "build_deterministic_search_work_runtime_records" not in source
    assert "QueryShapeAssessment" not in source
    assert "ContractResolutionRecord" not in source
    assert "ProviderJobCandidate" not in source


def test_static_import_guards_for_classifier_and_closed_modules() -> None:
    closed_paths = (
        ROOT / "core" / "query_plan.py",
        ROOT / "core" / "query_plan_runtime_adapter.py",
        ROOT / "core" / "query_production_runtime.py",
        ROOT / "core" / "mode_policy.py",
        ROOT / "core" / "prompts.py",
        ROOT / "core" / "search_providers.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "retrieval_scheduler.py",
        ROOT / "core" / "final_answer_runtime_adapter.py",
        ROOT / "core" / "final_evidence_bundle_builder.py",
    )
    forbidden_classifier_imports = {
        "core.search_work_query_shape_runtime",
        "search_work_query_shape_runtime",
    }
    for path in closed_paths:
        imported = _imports(path)
        assert imported.isdisjoint(forbidden_classifier_imports), path

    classifier_imports = _imports(CLASSIFIER)
    forbidden_closed_imports = {
        "core.pipeline_orchestrator",
        "core.query_plan",
        "core.query_plan_runtime_adapter",
        "core.query_production_runtime",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.runtime_prompt_assembly",
        "core.prompts",
        "core.final_answer_runtime_adapter",
        "core.final_evidence_bundle_builder",
    }
    assert classifier_imports.isdisjoint(forbidden_closed_imports)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
    return imported_names
