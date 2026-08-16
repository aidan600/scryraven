"""Offline proof for the bounded current-v8 SearchPlanner diagnostic.

Mode: REPAIR.
Test class: phase_focus / offline_evaluator_boundary.
No test in this file makes a provider, search, READ, or retrieval call.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

import pytest

import core.query_production_runtime as query_runtime
import scripts.evaluation.search_planner_semantic_rule_diagnostic as diagnostic
from scripts import request_provider_proxy_broker as broker_client
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationTransportResponse,
)
from scripts.evaluation.search_planner_semantic_rule_diagnostic import (
    CURRENT_MAIN_V8_ONLY,
    PLANNER_ROLE,
    SCHEDULE,
    execute_search_planner_semantic_rule_diagnostic,
)

_SHA = "a" * 40
_Q1 = "QUERY_SENTRY_Q1_0123456789"
_Q2 = "QUERY_SENTRY_Q2_0123456789"
_REJECTED_FIELD = "planner-rejected-field-sentinel"
_REJECTED_VALUE = "planner-rejected-value-sentinel"


class _Factory:
    """Test-only transport that retains no prompt or response text."""

    test_only = True

    def __init__(self, outputs: list[str], *, retention: bool = False) -> None:
        self._outputs = list(outputs)
        self.retention = retention
        self.routes: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []

    def __call__(self, route: Any):
        self.routes.append(
            {
                "provider": route.provider,
                "model": route.model,
                "roles": route.allowed_model_roles,
                "retry_cap": route.retry_cap,
                "input_cap": route.maximum_input_tokens,
                "output_cap": route.maximum_output_tokens,
            }
        )

        def transport(**kwargs: Any) -> EvaluationTransportResponse:
            assert kwargs["role"] == PLANNER_ROLE
            assert _Q1 in kwargs["prompt"] or _Q2 in kwargs["prompt"]
            assert not kwargs["system_prompt"].startswith("synthetic variant")
            self.calls.append(
                {
                    "role": kwargs["role"],
                    "call_id": kwargs["correlation_id"],
                    "provider": kwargs["provider"],
                    "model": kwargs["model"],
                    "input_cap": kwargs["maximum_input_tokens"],
                    "output_cap": kwargs["maximum_output_tokens"],
                }
            )
            output = self._outputs.pop(0)
            return EvaluationTransportResponse(
                output=output,
                reasoning_effort=route.reasoning_effort,
                generation_status="completed",
                generation_incomplete_reason=None,
                max_output_tokens_reached=False,
                output_text_present=bool(output),
                output_text_character_count=len(output),
                output_text_digest=sha256(output.encode("utf-8")).hexdigest(),
                usage_observed=True,
                input_tokens=12,
                cached_input_tokens=0,
                uncached_input_tokens=12,
                output_tokens=6,
                reasoning_tokens=2,
                non_reasoning_output_tokens=4,
                total_tokens=18,
                caller_calculated_route_priced_cost_usd="0.01",
                cost_posture="exact",
                output_token_utilization="0.01",
                reasoning_token_share="0.2",
                provider_elapsed_milliseconds_total=1,
                canonical_provider_used=kwargs["provider"],
                canonical_model_used=kwargs["model"],
                provider_request_attempt_count=1,
                raw_material_retained=self.retention,
                credentials_accessed=True,
            )

        return transport


def _run(factory: _Factory) -> dict[str, Any]:
    return execute_search_planner_semantic_rule_diagnostic(
        case_inputs={"Q1": _Q1, "Q2": _Q2},
        repository_sha=_SHA,
        current_date="2026-08-15",
        transport_factory=factory,
    )


def test_default_broker_route_uses_protocol_token_without_changing_product_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(broker_client.TOKEN_ENV_VAR, "test-session-token")

    route = diagnostic._route()
    transport = diagnostic.create_brokered_model_route_transport(route)

    assert diagnostic.REQUIRED_PRODUCT_PROVIDER == "OpenAI"
    assert route.provider == "openai"
    assert route.model == "gpt-5.4-mini"
    assert callable(transport)


def test_exact_interleaved_six_call_schedule_carries_typed_rule_without_raw_material() -> None:
    rejected = json.dumps(
        {
            "disposition": "direct_simple",
            _REJECTED_FIELD: _REJECTED_VALUE,
        }
    )
    factory = _Factory([rejected] * 6)
    packet = _run(factory)

    assert packet["terminal_posture"] == "COMPLETED_SIX_CALL_PACKET"
    assert packet["prompt_arm_id"] == CURRENT_MAIN_V8_ONLY
    assert packet["scheduled_call_order"] == [entry.call_id for entry in SCHEDULE]
    assert [call["call_id"] for call in factory.calls] == [
        "Q1-1",
        "Q2-1",
        "Q1-2",
        "Q2-2",
        "Q1-3",
        "Q2-3",
    ]
    assert len(factory.calls) == 6
    assert factory.routes == [
        {
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "roles": (PLANNER_ROLE,),
            "retry_cap": 0,
            "input_cap": 16_000,
            "output_cap": 4_096,
        }
    ]
    assert packet["aggregate_physical_attempt_counts"] == {
        "planner_model_attempts": 6,
        "total_model_attempts": 6,
        "maximum_authorized_model_attempts": 6,
        "retry_count": 0,
        "fallback_count": 0,
        "replacement_call_count": 0,
        "embedding_attempts": 0,
        "search_attempts": 0,
        "read_attempts": 0,
    }
    for result in packet["call_results"]:
        assert result["accepted"] is False
        assert result["failure_code"] == "INVALID_SEMANTIC_PROPOSAL"
        assert result["semantic_proposal_subtype"] == "branch_field_set"
        assert result["semantic_validation_rule_id"] == "direct_simple_disallowed_top_level"
        assert result["branch_field_set_detail"] == "direct_simple_disallowed_top_level"
        assert result["provider_completion_posture"] == "completed"
        assert result["physical_attempt_counts"]["retry_count"] == 0
        assert result["downstream_zero_attestation"]["query_plan_execution"] == 0
        assert result["downstream_zero_attestation"]["author"] == 0
        assert all(value is False for value in result["raw_retention_false_attestation"].values())
    assert packet["stability_screening"] == {
        "Q1": "STABLE_RULE_SPECIFIC_CONFORMANCE_FAILURE_PLAUSIBLE",
        "Q2": "STABLE_RULE_SPECIFIC_CONFORMANCE_FAILURE_PLAUSIBLE",
    }
    encoded = json.dumps(packet, sort_keys=True)
    for private_value in (_Q1, _Q2, _REJECTED_FIELD, _REJECTED_VALUE):
        assert private_value not in encoded
    assert "output_digest" not in encoded
    assert "bounded_failure_reason" not in encoded


def test_accepted_output_nulls_all_failure_fields() -> None:
    factory = _Factory([json.dumps({"disposition": "direct_simple"})] * 6)
    packet = _run(factory)

    assert len(packet["call_results"]) == 6
    for result in packet["call_results"]:
        assert result["accepted"] is True
        assert result["failure_code"] is None
        assert result["semantic_proposal_subtype"] is None
        assert result["semantic_validation_rule_id"] is None
        assert result["branch_field_set_detail"] is None
    assert packet["stability_screening"] == {
        "Q1": "NO_STABLE_RULE_SPECIFIC_SIGNAL",
        "Q2": "NO_STABLE_RULE_SPECIFIC_SIGNAL",
    }


def test_shared_prefix_poison_proves_queryplan_derivation_and_admission_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def poison(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("downstream poison must remain unreachable")

    monkeypatch.setattr(
        query_runtime,
        "initial_query_strategies_from_planner_state",
        poison,
    )
    monkeypatch.setattr(query_runtime, "execute_query_plan_admission_action", poison)
    factory = _Factory([json.dumps({"disposition": "direct_simple"})] * 6)

    packet = _run(factory)

    assert packet["terminal_posture"] == "COMPLETED_SIX_CALL_PACKET"
    assert len(factory.calls) == 6
    assert all(
        result["downstream_zero_attestation"]["stop_after_initial_answer_contract_acceptance"]
        for result in packet["call_results"]
    )


def test_post_acceptance_reduction_guard_proves_all_downstream_stages_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allowed_observation_types = {
        diagnostic.ObservationType.RUN_CONTRACT_SYNTHESIZED,
        diagnostic.ObservationType.SEARCH_PLANNER_PRODUCED,
        diagnostic.ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
    }
    original_reduce = diagnostic.RunKernel.reduce
    observed: list[diagnostic.ObservationType] = []

    def guarded_reduce(self: Any, observation: Any) -> Any:
        assert observation.observation_type in allowed_observation_types
        observed.append(observation.observation_type)
        return original_reduce(self, observation)

    monkeypatch.setattr(diagnostic.RunKernel, "reduce", guarded_reduce)
    factory = _Factory([json.dumps({"disposition": "direct_simple"})] * 6)

    packet = _run(factory)

    assert packet["terminal_posture"] == "COMPLETED_SIX_CALL_PACKET"
    assert (
        observed
        == [
            diagnostic.ObservationType.RUN_CONTRACT_SYNTHESIZED,
            diagnostic.ObservationType.SEARCH_PLANNER_PRODUCED,
            diagnostic.ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
        ]
        * 6
    )


def test_retention_or_route_integrity_failure_stops_without_replacement() -> None:
    factory = _Factory(
        [json.dumps({"disposition": "direct_simple"})],
        retention=True,
    )

    packet = _run(factory)

    assert packet["terminal_posture"] == "INVALID_EVIDENCE"
    assert packet["invalid_evidence_code"] == "EVALUATOR_INTEGRITY_FAILURE"
    assert packet["call_results"] == []
    assert packet["aggregate_physical_attempt_counts"]["planner_model_attempts"] == 1
    assert len(factory.calls) == 1
