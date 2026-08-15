"""Phase-focus proof for provider-execution schema 2 generation telemetry.

Classification: phase_focus.
Proof class: live_component_proof with fake-provider offline coverage.
Runtime seam: tracked broker -> generic contract -> caller-owned projection.
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

import pytest

from scripts import provider_execution_broker as broker
from scripts import request_provider_proxy_broker as broker_client
from scripts.evaluation import brokered_model_origination_transport
from scripts.evaluation.model_cost_policy import (
    GPT54_MINI_MODEL_ID,
    GPT54_MODEL_ID,
    ModelCostPolicy,
    resolve_model_cost_policy,
    route_priced_cost_decimal,
)
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    LIVE_ADDENDUM_SCHEMA_VERSION,
    EvaluationTransportError,
    LiveAuthorization,
)
from scripts.provider_execution_contract import (
    MAX_PROVIDER_ELAPSED_MILLISECONDS_TOTAL,
    MODEL_PROOF_KIND,
    REQUEST_KIND,
    RESPONSE_KIND,
    SCHEMA_VERSION,
    SEARCH_PROOF_KIND,
    ProviderExecutionContractError,
    build_failure_response,
    build_model_proof,
    build_model_request,
    build_search_request,
    build_success_response,
    validate_provider_execution_response,
)


def _request(*, reasoning_effort: str = "medium") -> dict[str, Any]:
    return build_model_request(
        provider="openai",
        model=GPT54_MODEL_ID,
        system_instructions="Return JSON.",
        input_prompt="Return one bounded object.",
        reasoning_effort=reasoning_effort,
        max_output_tokens=512,
        timeout_seconds=120,
        retry_cap=0,
    )


def _response(
    *,
    status: str = "completed",
    reason: str | None = None,
    output_text: str = '{"status":"ok"}',
    usage_observed: bool = True,
    input_tokens: Any = 100,
    cached_input_tokens: Any = 40,
    output_tokens: Any = 20,
    reasoning_tokens: Any = 5,
    total_tokens: Any = 120,
) -> dict[str, Any]:
    return build_success_response(
        _request(),
        physical_attempt_count=1,
        provider_elapsed_milliseconds_total=13,
        output_text=output_text,
        generation_status=status,
        generation_incomplete_reason=reason,
        usage_observed=usage_observed,
        input_tokens=input_tokens if usage_observed else None,
        cached_input_tokens=(cached_input_tokens if usage_observed else None),
        output_tokens=output_tokens if usage_observed else None,
        reasoning_tokens=reasoning_tokens if usage_observed else None,
        total_tokens=total_tokens if usage_observed else None,
    )


def _authorization(**updates: Any) -> LiveAuthorization:
    value = LiveAuthorization(
        schema_version=LIVE_ADDENDUM_SCHEMA_VERSION,
        reference="synthetic-v2-telemetry",
        repository_sha="a" * 40,
        provider="openai",
        model=GPT54_MODEL_ID,
        reasoning_effort="medium",
        allowed_evaluation_pass="planner_only",
        allowed_model_roles=("search_planner",),
        allowed_scenario_ids=("case_03_pure_depth_two",),
        maximum_model_calls=1,
        maximum_scryraven_runs=1,
        retry_cap=0,
        timeout_seconds=120,
        maximum_input_tokens=512,
        maximum_output_tokens=512,
        cost_ceiling=0.01,
        output_packet_path="output/local/synthetic-v2.json",
        decision="offline",
        stop_condition="stop",
        raw_retention_posture="sanitized_only",
        transport_factory_spec=(brokered_model_origination_transport.TRANSPORT_FACTORY_SPEC),
        canonical_operator_command='["synthetic"]',
        canonical_operator_command_digest="b" * 64,
    )
    return replace(value, **updates)


def test_exact_schema_2_family_and_proof_kinds() -> None:
    assert SCHEMA_VERSION == "2"
    assert REQUEST_KIND == "scryraven_provider_execution_request_v2"
    assert RESPONSE_KIND == "scryraven_provider_execution_response_v2"
    assert MODEL_PROOF_KIND == "scryraven_model_generation_proof_v2"
    assert SEARCH_PROOF_KIND == "scryraven_search_query_proof_v2"


@pytest.mark.parametrize("reasoning_tokens", (5, 0))
def test_completed_usage_normalizes_all_exact_derivations(
    reasoning_tokens: int,
) -> None:
    response = _response(reasoning_tokens=reasoning_tokens)
    assert response["generation_status"] == "completed"
    assert response["generation_incomplete_reason"] is None
    assert response["max_output_tokens_reached"] is False
    assert response["output_text_present"] is True
    assert response["provider_elapsed_milliseconds_total"] == 13
    assert response["usage"] == {
        "usage_observed": True,
        "input_tokens": 100,
        "cached_input_tokens": 40,
        "uncached_input_tokens": 60,
        "output_tokens": 20,
        "reasoning_tokens": reasoning_tokens,
        "non_reasoning_output_tokens": 20 - reasoning_tokens,
        "total_tokens": 120,
    }


@pytest.mark.parametrize(
    ("updates", "failure"),
    (
        ({"cached_input_tokens": 101}, "cached_input_tokens_exceed"),
        ({"reasoning_tokens": 21}, "reasoning_tokens_exceed"),
        ({"total_tokens": 121}, "total_tokens_mismatch"),
        (
            {"input_tokens": -1},
            "cached_input_tokens_exceed|missing_or_invalid_input_tokens",
        ),
        ({"output_tokens": 1.5}, "missing_or_invalid_output_tokens"),
    ),
)
def test_invalid_usage_fails_closed(
    updates: Mapping[str, Any],
    failure: str,
) -> None:
    with pytest.raises(ProviderExecutionContractError, match=failure):
        _response(**updates)


def test_unobserved_usage_contains_no_invented_counts() -> None:
    response = _response(usage_observed=False)
    assert response["usage"] == {"usage_observed": False}


@pytest.mark.parametrize(
    ("reason", "output_text", "exhausted"),
    (
        ("max_output_tokens", '{"partial":true}', True),
        ("max_output_tokens", "", True),
        ("content_filter", "", False),
    ),
)
def test_incomplete_completion_telemetry(
    reason: str,
    output_text: str,
    exhausted: bool,
) -> None:
    response = _response(
        status="incomplete",
        reason=reason,
        output_text=output_text,
    )
    assert response["generation_status"] == "incomplete"
    assert response["generation_incomplete_reason"] == reason
    assert response["max_output_tokens_reached"] is exhausted
    assert response["output_text_present"] is bool(output_text)


def test_completion_rules_fail_closed_without_inference_from_token_count() -> None:
    with pytest.raises(
        ProviderExecutionContractError,
        match="completed_generation_requires_output_text",
    ):
        _response(output_text="")
    with pytest.raises(
        ProviderExecutionContractError,
        match="unsupported_generation_incomplete_reason",
    ):
        _response(status="incomplete", reason="unknown")

    response = _response(output_tokens=512, total_tokens=612)
    assert response["max_output_tokens_reached"] is False


def test_exact_cached_pricing_and_durable_nonretention() -> None:
    policy = resolve_model_cost_policy("openai", GPT54_MODEL_ID)
    assert policy == ModelCostPolicy(
        provider="openai",
        model=GPT54_MODEL_ID,
        ordinary_input_price_usd_per_million=Decimal("2.50"),
        cached_input_price_usd_per_million=Decimal("0.25"),
        output_price_usd_per_million=Decimal("15.00"),
    )
    assert not hasattr(policy, "reasoning_effort")
    assert route_priced_cost_decimal(
        60,
        40,
        20,
        policy=policy,
    ) == Decimal("0.00046")
    proof = build_model_proof(
        _response(),
        request_payload=_request(),
        maximum_input_tokens=512,
        ordinary_input_price_usd_per_million="2.50",
        cached_input_price_usd_per_million="0.25",
        output_price_usd_per_million="15.00",
        cost_ceiling_usd="0.01",
        expected_json_status="ok",
    )
    assert proof["caller_calculated_route_priced_cost_usd"] == "0.00046"
    assert proof["cost_posture"] == "exact"
    assert proof["output_token_utilization"] == "0.0390625"
    assert proof["reasoning_token_share"] == "0.25"
    assert "output_text" not in proof
    assert json.dumps(proof).find('{"status":"ok"}') == -1


def test_exact_gpt54_mini_policy_supports_the_bounded_planner_route() -> None:
    policy = resolve_model_cost_policy("openai", GPT54_MINI_MODEL_ID)

    assert policy == ModelCostPolicy(
        provider="openai",
        model=GPT54_MINI_MODEL_ID,
        ordinary_input_price_usd_per_million=Decimal("0.75"),
        cached_input_price_usd_per_million=Decimal("0.075"),
        output_price_usd_per_million=Decimal("4.50"),
    )
    assert route_priced_cost_decimal(
        16_000,
        0,
        4_096,
        policy=policy,
    ) == Decimal("0.030432")


def test_unknown_usage_proof_has_unknown_cost_and_may_be_billable() -> None:
    proof = build_model_proof(
        _response(
            status="incomplete",
            reason="content_filter",
            output_text="",
            usage_observed=False,
        ),
        request_payload=_request(),
        maximum_input_tokens=512,
        ordinary_input_price_usd_per_million="2.50",
        cached_input_price_usd_per_million="0.25",
        output_price_usd_per_million="15.00",
        cost_ceiling_usd="0.01",
    )
    assert proof["usage_observed"] is False
    assert proof["cost_posture"] == "unknown"
    assert proof["request_may_still_be_billable"] is True
    assert "input_tokens" not in proof
    assert "caller_calculated_route_priced_cost_usd" not in proof


def test_elapsed_time_sums_fake_attempts_and_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter((0, 5_000_000, 10_000_000, 17_000_000))
    monkeypatch.setattr(broker.time, "monotonic_ns", lambda: next(values))
    calls = 0

    def failing(
        _payload: Mapping[str, Any],
        _credential: str,
    ) -> Mapping[str, Any]:
        nonlocal calls
        calls += 1
        raise broker.BrokerExecutionError(
            "provider_timeout",
            physical_attempt_count=1,
        )

    request = dict(_request())
    request["retry_cap"] = 1
    with pytest.raises(broker.BrokerExecutionError) as raised:
        broker.execute_provider_request(
            request,
            credentials={"OPENAI_API_KEY": "opaque"},  # pragma: allowlist secret
            adapters={("openai", "model.generate"): failing},
        )
    assert calls == 2
    assert raised.value.physical_attempt_count == 2
    assert raised.value.provider_elapsed_milliseconds_total == 12
    assert 12 <= MAX_PROVIDER_ELAPSED_MILLISECONDS_TOTAL


def test_openai_adapter_extracts_only_safe_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    usage = types.SimpleNamespace(
        input_tokens=100,
        input_tokens_details=types.SimpleNamespace(cached_tokens=40),
        output_tokens=20,
        output_tokens_details=types.SimpleNamespace(reasoning_tokens=5),
        total_tokens=120,
    )
    raw_response = types.SimpleNamespace(
        id="private-response-id",
        status="completed",
        incomplete_details=None,
        output_text='{"status":"ok"}',
        output=[{"reasoning": "private"}],
        usage=usage,
    )

    class FakeResponses:
        def create(self, **_kwargs: Any) -> Any:
            return raw_response

    class FakeOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.responses = FakeResponses()

    monkeypatch.setitem(
        sys.modules,
        "openai",
        types.SimpleNamespace(OpenAI=FakeOpenAI),
    )
    normalized = broker._call_openai_model(_request(), "opaque")
    assert normalized == {
        "generation_status": "completed",
        "generation_incomplete_reason": None,
        "output_text": '{"status":"ok"}',
        "usage_observed": True,
        "input_tokens": 100,
        "cached_input_tokens": 40,
        "output_tokens": 20,
        "reasoning_tokens": 5,
        "total_tokens": 120,
    }
    rendered = json.dumps(normalized)
    assert "private-response-id" not in rendered
    assert "private" not in rendered


def test_openai_adapter_missing_detail_objects_marks_usage_unobserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_response = types.SimpleNamespace(
        status="incomplete",
        incomplete_details=types.SimpleNamespace(reason="content_filter"),
        output_text="",
        usage=types.SimpleNamespace(
            input_tokens=100,
            input_tokens_details=None,
            output_tokens=20,
            output_tokens_details=None,
            total_tokens=120,
        ),
    )

    class FakeResponses:
        def create(self, **_kwargs: Any) -> Any:
            return raw_response

    class FakeOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.responses = FakeResponses()

    monkeypatch.setitem(
        sys.modules,
        "openai",
        types.SimpleNamespace(OpenAI=FakeOpenAI),
    )
    normalized = broker._call_openai_model(_request(), "opaque")
    assert normalized["usage_observed"] is False
    assert "input_tokens" not in normalized


def test_reasoning_effort_is_exact_authorization_not_cost_policy() -> None:
    with pytest.raises(
        ProviderExecutionContractError,
        match="unsupported_reasoning_effort",
    ):
        _request(reasoning_effort="minimal")
    authorization = _authorization(reasoning_effort="medium")

    def mismatched_effort(
        _url: str,
        _token: str,
        _request_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return {**_response(), "reasoning_effort": "high"}

    transport = brokered_model_origination_transport._create_brokered_model_origination_transport(
        authorization,
        broker_url="http://127.0.0.1:8765/run",
        session_token="temporary",
        request_function=mismatched_effort,
    )
    with pytest.raises(EvaluationTransportError, match="attestation"):
        transport(
            role="search_planner",
            prompt="transient",
            system_prompt="transient",
            provider="openai",
            model=GPT54_MODEL_ID,
            maximum_input_tokens=512,
            maximum_output_tokens=512,
        )


@pytest.mark.parametrize(
    ("failure_class", "physical_attempt_count", "elapsed_milliseconds"),
    (
        ("missing_configuration", 0, 0),
        ("provider_timeout", 1, 17),
    ),
)
def test_model_failure_attestation_survives_broker_client_and_evaluator(
    monkeypatch: pytest.MonkeyPatch,
    failure_class: str,
    physical_attempt_count: int,
    elapsed_milliseconds: int,
) -> None:
    request_payload = _request()
    failure = build_failure_response(
        request_payload=request_payload,
        failure_class=failure_class,
        physical_attempt_count=physical_attempt_count,
        provider_elapsed_milliseconds_total=elapsed_milliseconds,
    )
    assert failure["provider"] == "openai"
    assert failure["operation"] == "model.generate"
    assert failure["model"] == GPT54_MODEL_ID
    assert failure["reasoning_effort"] == "medium"
    assert failure["failure_class"] == failure_class
    assert failure["physical_attempt_count"] == physical_attempt_count
    assert failure["provider_elapsed_milliseconds_total"] == elapsed_milliseconds
    assert (
        validate_provider_execution_response(
            failure,
            request_payload=request_payload,
        )["failure_class"]
        == failure_class
    )

    def fake_post(
        _broker_url: str,
        _token: str,
        observed_request: Mapping[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        return 502, build_failure_response(
            request_payload=observed_request,
            failure_class=failure_class,
            physical_attempt_count=physical_attempt_count,
            provider_elapsed_milliseconds_total=elapsed_milliseconds,
        )

    monkeypatch.setattr(broker_client, "_post_broker_json", fake_post)
    with pytest.raises(
        broker_client.ProviderExecutionClientError,
        match=f"^{failure_class}$",
    ) as client_error:
        broker_client.request_provider_execution(
            broker_url=broker_client.DEFAULT_BROKER_URL,
            token="temporary",
            request_payload=request_payload,
        )
    assert client_error.value.failure_class == failure_class

    authorization = _authorization()

    def evaluator_request(
        broker_url: str,
        token: str,
        observed_request: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return broker_client.request_provider_execution(
            broker_url=broker_url,
            token=token,
            request_payload=observed_request,
        )

    transport = brokered_model_origination_transport._create_brokered_model_origination_transport(
        authorization,
        broker_url=broker_client.DEFAULT_BROKER_URL,
        session_token="temporary",
        request_function=evaluator_request,
    )
    with pytest.raises(
        EvaluationTransportError,
        match=f"failed closed: {failure_class}$",
    ) as evaluator_error:
        transport(
            role="search_planner",
            prompt="transient prompt material",
            system_prompt="transient system material",
            provider="openai",
            model=GPT54_MODEL_ID,
            maximum_input_tokens=512,
            maximum_output_tokens=512,
        )
    assert str(evaluator_error.value) == (f"brokered model origination transport failed closed: {failure_class}")

    rendered = (json.dumps(failure, sort_keys=True) + str(evaluator_error.value)).casefold()
    for forbidden in (
        "return json",
        "return one bounded object",
        "transient prompt material",
        "transient system material",
        "api_key",
        "authorization",
        "provider error",
        "output_text",
        "raw_payload",
        "reasoning_content",
    ):
        assert forbidden not in rendered


def test_failure_reasoning_attestation_tamper_fails_exactly() -> None:
    request_payload = _request()
    failure = build_failure_response(
        request_payload=request_payload,
        failure_class="provider_timeout",
        physical_attempt_count=1,
        provider_elapsed_milliseconds_total=17,
    )
    with pytest.raises(
        ProviderExecutionContractError,
        match="^route_attestation_mismatch$",
    ):
        validate_provider_execution_response(
            {**failure, "reasoning_effort": "high"},
            request_payload=request_payload,
        )


def test_search_failure_envelope_omits_reasoning_effort_and_remains_valid() -> None:
    request_payload = build_search_request(
        provider="serper",
        query="bounded search failure proof",
        max_results=1,
        timeout_seconds=30,
        retry_cap=0,
    )
    failure = build_failure_response(
        request_payload=request_payload,
        failure_class="missing_configuration",
        physical_attempt_count=0,
    )
    assert "reasoning_effort" not in failure
    assert (
        validate_provider_execution_response(
            failure,
            request_payload=request_payload,
        )["failure_class"]
        == "missing_configuration"
    )


def test_broker_source_contains_no_pricing_or_dollar_policy() -> None:
    source = Path(broker.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "price_usd",
        "cost_ceiling",
        "caller_calculated_route_priced_cost",
    ):
        assert forbidden not in source
