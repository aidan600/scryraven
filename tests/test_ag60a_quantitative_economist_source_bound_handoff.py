from __future__ import annotations

import inspect
import json
from typing import Any

from core.answer_contract_controller import (
    AnswerContractFamily,
    EvidenceReference,
    EvidenceStateSummary,
    build_answer_contract,
    build_answer_contract_fulfillment,
    build_answer_controller_state,
)
from core.pipeline import (
    _quant_retrieval_sufficiency_shadow_telemetry,
    build_quantitative_packet_shadow,
    execute_economist_calculations_shadow,
    run_economist_step,
    validate_economist_schema_v1,
    validate_economist_source_bindings,
    validate_high_stakes_quantitative_shadow,
    validate_target_metric_shadow,
)
from core.pipeline_orchestrator import _analyst_quant_packet_payload
from core.prompts import DEFAULT_SYSTEM
from core.thin_quant import parse_thin_quant_data_unavailable
from tests import test_source_hierarchy_answer_contract_invariants_ag57a as ag57a


def _alpha_beta_passages() -> list[dict[str, Any]]:
    return [
        {
            "source_id": 1,
            "url": "https://alpha.example/fy2025",
            "title": "Alpha fiscal 2025 results",
            "text": "Alpha reported fiscal 2025 revenue of USD 100 million.",
        },
        {
            "source_id": 2,
            "url": "https://beta.example/fy2025",
            "title": "Beta fiscal 2025 results",
            "text": "Beta reported fiscal 2025 revenue of USD 150 million.",
        },
    ]


def _alpha_beta_source_bound_values() -> list[dict[str, Any]]:
    return [
        {
            "name": "alpha_fy2025_revenue",
            "entity": "Alpha",
            "metric": "revenue",
            "period": "fiscal 2025",
            "value": "100",
            "unit": "USD millions",
            "source_id": "1",
        },
        {
            "name": "beta_fy2025_revenue",
            "entity": "Beta",
            "metric": "revenue",
            "period": "fiscal 2025",
            "value": "150",
            "unit": "USD millions",
            "source_id": "2",
        },
    ]


def _packet_telemetry(
    *,
    payload: dict[str, Any],
    query: str = "Compare Alpha vs Beta on fiscal 2025 revenue.",
    passages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    active_passages = passages or _alpha_beta_passages()
    schema = validate_economist_schema_v1(payload)
    source_bindings = validate_economist_source_bindings(
        payload,
        {str(item["source_id"]) for item in active_passages},
    )
    calculations = execute_economist_calculations_shadow(
        payload,
        source_binding_valid=source_bindings["source_binding_valid"],
    )
    target_metric = validate_target_metric_shadow(
        query=query,
        payload=payload,
        schema_telemetry=schema,
        source_binding_telemetry=source_bindings,
        calculation_telemetry=calculations,
    )
    high_stakes = validate_high_stakes_quantitative_shadow(
        query=query,
        payload=payload,
        schema_telemetry=schema,
        source_binding_telemetry=source_bindings,
        calculation_telemetry=calculations,
        target_metric_telemetry=target_metric,
    )
    telemetry: dict[str, Any] = {}
    for block in (schema, source_bindings, calculations, target_metric, high_stakes):
        telemetry.update(block)
    telemetry.update(
        build_quantitative_packet_shadow(
            query=query,
            payload=payload,
            schema_telemetry=schema,
            source_binding_telemetry=source_bindings,
            calculation_telemetry=calculations,
            target_metric_telemetry=target_metric,
            high_stakes_telemetry=high_stakes,
        )
    )
    return telemetry


def _valid_economist_payload(
    *,
    source_bound_values: list[dict[str, Any]] | None = None,
    calculations_requested: list[dict[str, Any]] | None = None,
    unsupported_values: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "economist_v1",
        "variables": [],
        "source_bound_values": source_bound_values or _alpha_beta_source_bound_values(),
        "assumptions": [],
        "calculations_requested": calculations_requested or [],
        "confidence": "medium",
        "unsupported_values": unsupported_values or [],
    }


def test_ag60a_economist_no_numeric_anchors_aborts_without_packet() -> None:
    captured: dict[str, str] = {}
    telemetry: dict[str, Any] = {}

    def ask_model(prompt: str, system: str, **_kwargs: Any) -> str:
        captured["prompt"] = prompt
        captured["system"] = system
        return "ABORT_ECONOMIST"

    result = run_economist_step(
        core_topic="Compare Alpha vs Beta on operating efficiency.",
        all_passages=[
            {
                "source_id": 1,
                "url": "https://alpha.example/strategy",
                "title": "Alpha strategy note",
                "text": "Alpha described a refreshed operating strategy without metrics.",
            }
        ],
        current_date="2026-05-26",
        ask_model=ask_model,
        clean_json_response=lambda text: text,
        default_system=DEFAULT_SYSTEM,
        safety_telemetry=telemetry,
        user_query="Compare Alpha vs Beta on operating efficiency.",
    )

    assert result is None
    assert "ABORT_ECONOMIST" in captured["system"]
    assert "do not contain any hard numeric or statistical material" in (
        captured["system"]
    )
    assert telemetry["quantitative_packet_present"] is False
    assert telemetry["quantitative_packet"] is None
    assert telemetry["source_bound_value_count"] == 0
    assert telemetry["source_ids_used"] == []


def test_ag60a_source_bound_and_unsupported_values_survive_analyst_handoff() -> None:
    unsupported_values = [
        "Beta defect rate is unavailable from source-bound evidence",
        "Model-derived revenue gap estimate must not be cited as sourced",
    ]
    telemetry = _packet_telemetry(
        payload=_valid_economist_payload(unsupported_values=unsupported_values)
    )

    assert telemetry["quantitative_packet_valid"] is True
    packet = telemetry["quantitative_packet"]
    assert packet["source_bound_values"] == _alpha_beta_source_bound_values()
    assert packet["unsupported_values"] == unsupported_values
    assert packet["unsupported_values_count"] == len(unsupported_values)

    handoff, analyst_packet = _analyst_quant_packet_payload(telemetry)
    assert handoff["analyst_quant_packet_injected"] is True
    assert analyst_packet is not None
    assert analyst_packet["source_bound_values"] == _alpha_beta_source_bound_values()
    assert analyst_packet["unsupported_values"] == unsupported_values
    assert "Model-derived revenue gap estimate" in json.dumps(analyst_packet)


def test_ag60a_missing_metric_for_one_entity_stays_invalid_not_filled() -> None:
    telemetry = _quant_retrieval_sufficiency_shadow_telemetry(
        query="Compare Alpha vs Beta on fiscal 2025 revenue.",
        report_type="quantitative_comparison",
        final_top_evidence=_alpha_beta_passages()[:1],
        source_bound_values=_alpha_beta_source_bound_values()[:1],
        router_entities=["Alpha", "Beta"],
    )

    assert telemetry["quant_retrieval_sufficiency_valid"] is False
    assert "missing_entity_coverage" in telemetry["quant_retrieval_sufficiency_blockers"]
    assert "missing_comparison_coverage" in telemetry[
        "quant_retrieval_sufficiency_blockers"
    ]

    packet = _packet_telemetry(
        payload=_valid_economist_payload(
            source_bound_values=_alpha_beta_source_bound_values()[:1]
        ),
        passages=_alpha_beta_passages()[:1],
    )["quantitative_packet"]
    assert packet["validation_errors"] == ["target_metric_evidence_missing"]
    assert packet["source_bound_values"] == _alpha_beta_source_bound_values()[:1]


def test_ag60a_mixed_year_and_mismatched_metric_values_do_not_normalize_confidently() -> None:
    mixed_year_values = [
        _alpha_beta_source_bound_values()[0],
        {
            "name": "beta_fy2024_revenue",
            "entity": "Beta",
            "metric": "revenue",
            "period": "fiscal 2024",
            "value": "140",
            "unit": "USD millions",
            "source_id": "2",
        },
    ]
    mixed_year = _packet_telemetry(
        payload=_valid_economist_payload(source_bound_values=mixed_year_values)
    )
    assert mixed_year["quantitative_packet_valid"] is False
    assert "target_metric_evidence_missing" in mixed_year[
        "quantitative_packet_validation_errors"
    ]

    mismatched_metric = _packet_telemetry(
        payload=_valid_economist_payload(
            source_bound_values=[
                _alpha_beta_source_bound_values()[0],
                {
                    "name": "beta_fy2025_revenue_growth",
                    "entity": "Beta",
                    "metric": "revenue growth",
                    "period": "fiscal 2025",
                    "value": "8",
                    "unit": "percent",
                    "source_id": "2",
                },
            ]
        )
    )
    assert mismatched_metric["quantitative_packet_valid"] is False
    assert "beta_fy2025_revenue_growth" not in mismatched_metric[
        "target_metric_bound_value_refs"
    ]


def test_ag60a_unsupported_calculation_request_is_not_presented_as_sourced() -> None:
    telemetry = _packet_telemetry(
        payload=_valid_economist_payload(
            calculations_requested=[
                {
                    "name": "forecast_from_priors",
                    "args": {
                        "baseline": "alpha_fy2025_revenue",
                        "comparison": "beta_fy2025_revenue",
                    },
                }
            ],
            unsupported_values=["forecast_from_priors result is unsupported"],
        )
    )

    assert telemetry["unsupported_calculation_names"] == ["forecast_from_priors"]
    assert telemetry["calculation_results"] == []
    assert telemetry["quantitative_packet_valid"] is False
    assert "calculation_errors_present" in telemetry[
        "quantitative_packet_validation_errors"
    ]


def test_ag60a_model_derived_values_cannot_masquerade_as_source_bound() -> None:
    telemetry = _packet_telemetry(
        payload=_valid_economist_payload(
            source_bound_values=[
                {
                    **_alpha_beta_source_bound_values()[0],
                    "name": "alpha_model_derived_revenue",
                    "provenance": "model-derived",
                },
                _alpha_beta_source_bound_values()[1],
            ],
            unsupported_values=["Alpha revenue estimate is model-derived"],
        )
    )

    assert telemetry["target_metric_evidence_found"] is False
    assert telemetry["quantitative_packet_valid"] is False
    assert "alpha_model_derived_revenue" not in telemetry[
        "target_metric_bound_value_refs"
    ]


def test_ag60a_analyst_and_author_prompts_preserve_quantitative_distinctions() -> None:
    analyst_prompt = DEFAULT_SYSTEM["analyst"].casefold()
    author_prompt = DEFAULT_SYSTEM["author"].casefold()

    assert "source_bound_values" in analyst_prompt
    assert "unsupported_values" in analyst_prompt
    assert "model-derived values distinctly from sourced values" in analyst_prompt
    assert "unsupported numeric" in author_prompt
    assert "model-derived figures" in author_prompt
    assert "not sourced from external evidence" in author_prompt


def test_ag60a_estimate_from_priors_remains_labeled_model_derived() -> None:
    analyst_estimate_prompt = DEFAULT_SYSTEM["analyst_estimate_from_priors"]
    author_estimate_prompt = DEFAULT_SYSTEM["author_estimate_from_priors"]

    assert "MODEL-DERIVED" in analyst_estimate_prompt
    assert "SOURCED vs MODEL-DERIVED" in analyst_estimate_prompt
    assert "MODEL-DERIVED figures" in author_estimate_prompt
    assert "not sourced from external evidence" in author_estimate_prompt


def test_ag60a_thin_quant_data_unavailable_contract_remains_protected() -> None:
    ok, items = parse_thin_quant_data_unavailable(
        "DATA_UNAVAILABLE: ['Alpha fiscal 2025 defect rate', 'Beta fiscal 2025 defect rate']"
    )

    assert ok is True
    assert items == [
        "Alpha fiscal 2025 defect rate",
        "Beta fiscal 2025 defect rate",
    ]


def test_ag60a_raw_quantitative_material_does_not_leak_public_handoff() -> None:
    contract = build_answer_contract(
        family=AnswerContractFamily.QUANTITATIVE_COMPARISON_OR_MODEL,
        user_intent_interpretation="User asks for a quantitative comparison.",
        answer_goal="Compare Alpha and Beta from sourced values.",
    )
    handoff = build_answer_contract_fulfillment(
        build_answer_controller_state(
            contract,
            evidence_state_summary=EvidenceStateSummary(
                evidence_available=True,
                partial_obligations=("state assumptions",),
                unfulfilled_obligations=("missing sourced numeric values",),
            ),
        ),
        evidence_used=(
            EvidenceReference(
                reference="raw_prompt provider_payload",
                source_class="sourced_numeric_values",
                summary="quantitative_packet economist_v1 source_bound_values",
                supports=("calculations_requested",),
            ),
        ),
        warnings_to_Analyst_or_Author=(
            "Do not expose full_trace or local packet internals.",
        ),
    )
    payload = json.dumps(handoff.to_dict(), sort_keys=True)

    for marker in (
        "raw_prompt",
        "provider_payload",
        "quantitative_packet",
        "economist_v1",
        "source_bound_values",
        "calculations_requested",
        "full_trace",
        "local packet",
    ):
        assert marker not in payload
        assert marker.casefold() not in payload.casefold()
    assert "[redacted protected material]" in payload


def test_ag60a_mixed_canonical_academic_xfail_remains_preserved() -> None:
    marks = getattr(
        ag57a.test_ag57a_mixed_canonical_and_academic_obligation_needs_multi_source_contract,
        "pytestmark",
        [],
    )

    xfail_marks = [mark for mark in marks if mark.name == "xfail"]
    assert len(xfail_marks) == 1
    assert xfail_marks[0].kwargs["strict"] is True
    assert "mixed canonical plus academic representation gap" in xfail_marks[0].kwargs[
        "reason"
    ]


def test_ag60a_protected_surface_static_guard() -> None:
    prompts = DEFAULT_SYSTEM

    assert "controller posture" not in prompts["economist"].casefold()
    assert "source-obligation posture" not in prompts["scrutineer"].casefold()
    helper_source = inspect.getsource(_analyst_quant_packet_payload)
    assert "select_providers(" not in helper_source
    assert "choose_supplemental_search_depth(" not in helper_source
