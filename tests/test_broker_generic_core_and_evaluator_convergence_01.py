from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

import pytest

from scripts import provider_execution_broker as broker
from scripts import request_provider_proxy_broker as client
from scripts.evaluation import brokered_model_origination_transport as evaluator_transport
from scripts.evaluation.model_cost_policy import GPT54_MODEL_ID
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    LIVE_ADDENDUM_SCHEMA_VERSION,
    EvaluationConfigurationError,
    EvaluationTransportError,
    LiveAuthorization,
)
from scripts.provider_execution_contract import (
    FALSE_RETENTION_FLAGS,
    MODEL_GENERATE_OPERATION,
    REQUEST_KIND,
    RESPONSE_KIND,
    SCHEMA_VERSION,
    SEARCH_QUERY_OPERATION,
    ProviderExecutionContractError,
    build_failure_response,
    build_model_proof,
    build_model_request,
    build_search_request,
    build_success_response,
    validate_provider_execution_request,
    validate_provider_execution_response,
)

ROOT = Path(__file__).resolve().parents[1]


def test_broker_server_entrypoint_executes_as_a_tracked_script() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "provider_execution_broker.py"),
            "--help",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "provider broker" in completed.stdout


def test_broker_client_entrypoint_executes_as_a_tracked_script() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "request_provider_proxy_broker.py"),
            "--help",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "local provider broker" in completed.stdout


def _search_request(
    provider: str = "serper",
    *,
    retry_cap: int = 0,
    requested_route_alias: str | None = None,
) -> dict[str, Any]:
    return build_search_request(
        provider=provider,
        query="site:docs.python.org exact test",
        max_results=3,
        timeout_seconds=12,
        retry_cap=retry_cap,
        requested_route_alias=requested_route_alias,
    )


def _model_request() -> dict[str, Any]:
    return build_model_request(
        provider="openai",
        model=GPT54_MODEL_ID,
        system_instructions="Return JSON.",
        input_prompt='Return {"status":"ok"}.',
        reasoning_effort="medium",
        max_output_tokens=128,
        timeout_seconds=120,
        retry_cap=0,
        correlation_id="model-smoke",
    )


def _authorization(**updates: Any) -> LiveAuthorization:
    authorization = LiveAuthorization(
        schema_version=LIVE_ADDENDUM_SCHEMA_VERSION,
        reference="synthetic-brokered-transport",
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
        timeout_seconds=120.0,
        maximum_input_tokens=1_000,
        maximum_output_tokens=128,
        cost_ceiling=0.01,
        output_packet_path="output/local/synthetic.json",
        decision="Synthetic offline transport proof.",
        stop_condition="Stop after any failure.",
        raw_retention_posture="sanitized_only",
        transport_factory_spec=evaluator_transport.TRANSPORT_FACTORY_SPEC,
        canonical_operator_command='["synthetic"]',
        canonical_operator_command_digest="b" * 64,
    )
    return replace(authorization, **updates)


def _completed_response(
    request_payload: Mapping[str, Any],
    *,
    output_text: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    reasoning_tokens: int = 0,
    physical_attempt_count: int = 1,
    provider_elapsed_milliseconds_total: int = 7,
) -> dict[str, Any]:
    return build_success_response(
        request_payload,
        physical_attempt_count=physical_attempt_count,
        provider_elapsed_milliseconds_total=(
            provider_elapsed_milliseconds_total
        ),
        output_text=output_text,
        generation_status="completed",
        usage_observed=True,
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        total_tokens=input_tokens + output_tokens,
    )


def test_one_versioned_operation_tagged_request_response_family() -> None:
    search = _search_request()
    model = _model_request()
    assert search["schema_version"] == model["schema_version"] == SCHEMA_VERSION
    assert search["request_kind"] == model["request_kind"] == REQUEST_KIND
    assert search["operation"] == SEARCH_QUERY_OPERATION
    assert model["operation"] == MODEL_GENERATE_OPERATION
    assert "model" not in search
    assert "query" not in model
    assert model["store"] is False
    for payload in (search, model):
        assert all(payload[flag] is False for flag in FALSE_RETENTION_FLAGS)

    bad = dict(search)
    bad["command"] = "blocked"
    with pytest.raises(ProviderExecutionContractError, match="forbidden_request"):
        validate_provider_execution_request(bad)
    bad = dict(model)
    bad["query"] = "wrong union"
    with pytest.raises(ProviderExecutionContractError, match="unsupported_request"):
        validate_provider_execution_request(bad)


def test_explicit_route_unknown_provider_operation_and_base_url_rejection() -> None:
    base = _search_request()
    for key, expected in (
        ("provider", "missing_provider"),
        ("operation", "missing_operation"),
    ):
        bad = dict(base)
        bad.pop(key)
        with pytest.raises(ProviderExecutionContractError, match=expected):
            validate_provider_execution_request(bad)
    bad = dict(base, provider="unknown")
    with pytest.raises(ProviderExecutionContractError, match="unsupported_provider"):
        validate_provider_execution_request(bad)
    bad = dict(base, operation="search.other")
    with pytest.raises(ProviderExecutionContractError, match="unsupported_operation"):
        validate_provider_execution_request(bad)
    with pytest.raises(ProviderExecutionContractError, match="invalid_base_url"):
        build_model_request(
            provider="openai",
            model=GPT54_MODEL_ID,
            base_url="https://example.com/v1",
            system_instructions="",
            input_prompt="hello",
            reasoning_effort=None,
            max_output_tokens=10,
            timeout_seconds=10,
            retry_cap=0,
        )


@pytest.mark.parametrize("provider", ["serper", "tavily"])
def test_search_migration_normalizes_attestation_and_attempts(provider: str) -> None:
    calls: list[tuple[dict[str, Any], str]] = []

    def fake_adapter(payload: Mapping[str, Any], credential: str) -> Mapping[str, Any]:
        calls.append((dict(payload), credential))
        return {
            "results": [
                {
                    "title": "Exact result",
                    "url": "https://docs.python.org/3/library/math.html",
                    "content": "Bounded snippet",
                    "raw_content": "Bounded extracted text",
                }
            ]
        }

    credential_name = "SERPER_API_KEY" if provider == "serper" else "TAVILY_API_KEY"
    response = broker.execute_provider_request(
        _search_request(provider, requested_route_alias="fast"),
        credentials={credential_name: "opaque-credential"},
        adapters={(provider, SEARCH_QUERY_OPERATION): fake_adapter},
    )
    assert response["response_kind"] == RESPONSE_KIND
    assert response["provider"] == provider
    assert response["operation"] == SEARCH_QUERY_OPERATION
    assert response["physical_attempt_count"] == 1
    assert response["requested_route_alias"] == "fast"
    assert len(calls) == 1
    assert calls[0][0]["provider"] == provider
    assert calls[0][1] == "opaque-credential"
    result = response["results"][0]
    assert result["provider"] == provider
    assert result["operation"] == SEARCH_QUERY_OPERATION
    assert result["provider_call_index"] == 1
    if provider == "tavily":
        assert result["provider_extracted_text"] == "Bounded extracted text"
    else:
        assert "provider_extracted_text" not in result


def test_alias_attestation_never_changes_exact_route() -> None:
    observed: list[tuple[str, str]] = []

    def fake_adapter(payload: Mapping[str, Any], _credential: str) -> Mapping[str, Any]:
        observed.append((payload["provider"], payload["operation"]))
        return {"results": []}

    for alias in ("fast", "smart", "embed"):
        response = broker.execute_provider_request(
            _search_request(requested_route_alias=alias),
            credentials={"SERPER_API_KEY": "opaque"},  # pragma: allowlist secret
            adapters={("serper", SEARCH_QUERY_OPERATION): fake_adapter},
        )
        assert response["requested_route_alias"] == alias
    assert observed == [("serper", SEARCH_QUERY_OPERATION)] * 3


def test_openai_model_generate_normalizes_exact_usage_and_discards_raw() -> None:
    observed: dict[str, Any] = {}

    def fake_adapter(payload: Mapping[str, Any], credential: str) -> Mapping[str, Any]:
        observed.update(payload)
        assert credential == "opaque"
        return {
            "output_text": '{"status":"ok"}',
            "generation_status": "completed",
            "usage_observed": True,
            "input_tokens": 12,
            "cached_input_tokens": 2,
            "output_tokens": 5,
            "reasoning_tokens": 3,
            "total_tokens": 17,
            "raw_ignored_by_adapter": "never returned",
        }

    request_payload = _model_request()
    response = broker.execute_provider_request(
        request_payload,
        credentials={"OPENAI_API_KEY": "opaque"},  # pragma: allowlist secret
        adapters={("openai", MODEL_GENERATE_OPERATION): fake_adapter},
    )
    assert response["provider"] == "openai"
    assert response["model"] == GPT54_MODEL_ID
    assert response["usage"] == {
        "usage_observed": True,
        "input_tokens": 12,
        "cached_input_tokens": 2,
        "uncached_input_tokens": 10,
        "output_tokens": 5,
        "reasoning_tokens": 3,
        "non_reasoning_output_tokens": 2,
        "total_tokens": 17,
    }
    assert response["physical_attempt_count"] == 1
    assert response["output_text"] == '{"status":"ok"}'
    assert observed["timeout_seconds"] == 120.0
    assert observed["retry_cap"] == 0
    assert all(response[flag] is False for flag in FALSE_RETENTION_FLAGS)
    rendered = json.dumps(response)
    assert "opaque" not in rendered
    assert "raw_ignored_by_adapter" not in rendered


def test_zero_retry_and_physical_attempt_accounting() -> None:
    calls = 0

    def failing(_payload: Mapping[str, Any], _credential: str) -> Mapping[str, Any]:
        nonlocal calls
        calls += 1
        raise broker.BrokerExecutionError(
            "provider_timeout",
            physical_attempt_count=1,
        )

    with pytest.raises(broker.BrokerExecutionError) as zero:
        broker.execute_provider_request(
            _search_request(retry_cap=0),
            credentials={"SERPER_API_KEY": "opaque"},  # pragma: allowlist secret
            adapters={("serper", SEARCH_QUERY_OPERATION): failing},
        )
    assert calls == 1
    assert zero.value.physical_attempt_count == 1

    calls = 0
    with pytest.raises(broker.BrokerExecutionError) as retried:
        broker.execute_provider_request(
            _search_request(retry_cap=1),
            credentials={"SERPER_API_KEY": "opaque"},  # pragma: allowlist secret
            adapters={("serper", SEARCH_QUERY_OPERATION): failing},
        )
    assert calls == 2
    assert retried.value.physical_attempt_count == 2


def test_missing_configuration_is_zero_attempt_sanitized_failure() -> None:
    with pytest.raises(broker.BrokerExecutionError) as raised:
        broker.execute_provider_request(
            _search_request(),
            credentials={},
            adapters={
                ("serper", SEARCH_QUERY_OPERATION): lambda *_args: {
                    "results": []
                }
            },
        )
    assert raised.value.failure_class == "missing_configuration"
    assert raised.value.physical_attempt_count == 0


def test_broker_session_mechanical_request_fuse_is_policy_free() -> None:
    session = broker.BrokerSessionState.create(
        token="temporary",
        credentials={},
        maximum_requests=2,
        adapters={},
    )
    assert session.reserve_request() is True
    assert session.reserve_request() is True
    assert session.reserve_request() is False
    assert not hasattr(session, "job_id")
    assert not hasattr(session, "validation_profile")


def test_model_proof_retains_digest_length_usage_cost_but_not_output() -> None:
    request_payload = _model_request()
    response = _completed_response(
        request_payload,
        physical_attempt_count=1,
        output_text='{"status":"BROKER_MODEL_OK"}',
        input_tokens=25,
        output_tokens=9,
    )
    proof = build_model_proof(
        response,
        request_payload=request_payload,
        maximum_input_tokens=1_000,
        ordinary_input_price_usd_per_million="2.50",
        cached_input_price_usd_per_million="0.25",
        output_price_usd_per_million="15.00",
        cost_ceiling_usd="0.01",
        expected_json_status="BROKER_MODEL_OK",
    )
    assert proof["output_character_count"] == len('{"status":"BROKER_MODEL_OK"}')
    assert len(proof["output_digest"]) == 64
    assert proof["input_tokens"] == 25
    assert proof["output_tokens"] == 9
    assert proof["output_text_retained"] is False
    assert proof["parsed_status"] == "BROKER_MODEL_OK"
    assert "output_text" not in proof


def test_model_proof_rejects_non_exact_json_status_without_retaining_output() -> None:
    request_payload = _model_request()
    response = _completed_response(
        request_payload,
        physical_attempt_count=1,
        output_text='{"status":"wrong","extra":true}',
        input_tokens=5,
        output_tokens=5,
    )
    with pytest.raises(
        ProviderExecutionContractError,
        match="model_output_json_status_invalid",
    ):
        build_model_proof(
            response,
            request_payload=request_payload,
            maximum_input_tokens=1_000,
            ordinary_input_price_usd_per_million="2.50",
            cached_input_price_usd_per_million="0.25",
            output_price_usd_per_million="15.00",
            cost_ceiling_usd="0.01",
            expected_json_status="BROKER_MODEL_OK",
        )


def test_failure_response_sanitizes_malformed_route_attestation() -> None:
    response = build_failure_response(
        request_payload={
            "provider": ["invalid"],
            "operation": {"invalid": True},
            "correlation_id": "c" * 1_000,
            "resolved_route_config_digest": "not-a-digest",
        },
        failure_class="invalid_request",
        physical_attempt_count=0,
    )
    assert response["status"] == "failed"
    assert response["failure_class"] == "invalid_request"
    assert "provider" not in response
    assert "operation" not in response
    assert "correlation_id" not in response
    assert "resolved_route_config_digest" not in response


def test_brokered_evaluator_transport_interoperability_and_cost() -> None:
    authorization = _authorization()
    observed: dict[str, Any] = {}

    def fake_request(
        broker_url: str,
        token: str,
        request_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        observed.update(url=broker_url, token=token, request=dict(request_payload))
        return _completed_response(
            request_payload,
            physical_attempt_count=1,
            output_text='{"proposal":"bounded"}',
            input_tokens=100,
            output_tokens=20,
        )

    transport = evaluator_transport._create_brokered_model_origination_transport(
        authorization,
        broker_url=client.DEFAULT_BROKER_URL,
        session_token="temporary-session",
        request_function=fake_request,
    )
    response = transport(
        role="search_planner",
        prompt="transient prompt",
        system_prompt="transient system",
        provider=authorization.provider,
        model=authorization.model,
        maximum_input_tokens=authorization.maximum_input_tokens,
        maximum_output_tokens=authorization.maximum_output_tokens,
    )
    assert response.output == '{"proposal":"bounded"}'
    assert response.input_tokens == 100
    assert response.output_tokens == 20
    assert Decimal(
        response.caller_calculated_route_priced_cost_usd
    ) == Decimal("0.00055")
    assert response.reasoning_effort == "medium"
    assert response.generation_status == "completed"
    assert response.canonical_provider_used == "openai"
    assert response.canonical_model_used == GPT54_MODEL_ID
    assert response.provider_request_attempt_count == 1
    assert response.raw_material_retained is False
    assert response.credentials_accessed is True
    assert observed["token"] == "temporary-session"
    assert observed["request"]["timeout_seconds"] == 120.0
    assert observed["request"]["retry_cap"] == 0
    assert "transient prompt" not in repr(transport)
    assert "temporary-session" not in repr(transport)


def test_brokered_evaluator_enforces_exact_live_authorization() -> None:
    with pytest.raises(EvaluationConfigurationError, match="retry cap 0"):
        evaluator_transport._create_brokered_model_origination_transport(
            _authorization(retry_cap=1),
            broker_url=client.DEFAULT_BROKER_URL,
            session_token="temporary",
            request_function=lambda *_args: {},
        )
    with pytest.raises(EvaluationConfigurationError, match="loopback"):
        evaluator_transport._create_brokered_model_origination_transport(
            _authorization(),
            broker_url="https://example.com/run",
            session_token="temporary",
            request_function=lambda *_args: {},
        )
    with pytest.raises(EvaluationConfigurationError, match="temporary broker"):
        evaluator_transport._create_brokered_model_origination_transport(
            _authorization(),
            broker_url=client.DEFAULT_BROKER_URL,
            session_token="",
            request_function=lambda *_args: {},
        )

    transport = evaluator_transport._create_brokered_model_origination_transport(
        _authorization(),
        broker_url=client.DEFAULT_BROKER_URL,
        session_token="temporary",
        request_function=lambda *_args: {},
    )
    with pytest.raises(EvaluationTransportError, match="route"):
        transport(
            role="search_planner",
            prompt="blocked",
            system_prompt="blocked",
            provider="other",
            model=GPT54_MODEL_ID,
            maximum_input_tokens=1_000,
            maximum_output_tokens=128,
        )
    with pytest.raises(EvaluationTransportError, match="role"):
        transport(
            role="unauthorized_role",
            prompt="blocked",
            system_prompt="blocked",
            provider="openai",
            model=GPT54_MODEL_ID,
            maximum_input_tokens=1_000,
            maximum_output_tokens=128,
        )


def test_brokered_evaluator_requires_usage_attempt_and_retention_posture() -> None:
    authorization = _authorization()

    def missing_usage(
        _url: str,
        _token: str,
        request_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        response = _completed_response(
            request_payload,
            physical_attempt_count=1,
            output_text="{}",
            input_tokens=1,
            output_tokens=1,
        )
        response.pop("usage")
        return response

    transport = evaluator_transport._create_brokered_model_origination_transport(
        authorization,
        broker_url=client.DEFAULT_BROKER_URL,
        session_token="temporary",
        request_function=missing_usage,
    )
    with pytest.raises(EvaluationTransportError, match="usage"):
        transport(
            role="search_planner",
            prompt="transient",
            system_prompt="transient",
            provider=authorization.provider,
            model=authorization.model,
            maximum_input_tokens=authorization.maximum_input_tokens,
            maximum_output_tokens=authorization.maximum_output_tokens,
        )


def test_brokered_evaluator_enforces_observed_token_and_cost_caps() -> None:
    authorization = _authorization()

    def excessive_input(
        _url: str,
        _token: str,
        request_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return _completed_response(
            request_payload,
            physical_attempt_count=1,
            output_text="{}",
            input_tokens=1_001,
            output_tokens=1,
        )

    transport = evaluator_transport._create_brokered_model_origination_transport(
        authorization,
        broker_url=client.DEFAULT_BROKER_URL,
        session_token="temporary",
        request_function=excessive_input,
    )
    with pytest.raises(EvaluationTransportError, match="token caps"):
        transport(
            role="search_planner",
            prompt="transient",
            system_prompt="transient",
            provider=authorization.provider,
            model=authorization.model,
            maximum_input_tokens=authorization.maximum_input_tokens,
            maximum_output_tokens=authorization.maximum_output_tokens,
        )

    cost_authorization = _authorization(cost_ceiling=0.0001)

    def over_cost(
        _url: str,
        _token: str,
        request_payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return _completed_response(
            request_payload,
            physical_attempt_count=1,
            output_text="{}",
            input_tokens=100,
            output_tokens=20,
        )

    transport = evaluator_transport._create_brokered_model_origination_transport(
        cost_authorization,
        broker_url=client.DEFAULT_BROKER_URL,
        session_token="temporary",
        request_function=over_cost,
    )
    with pytest.raises(EvaluationTransportError, match="cost ceiling"):
        transport(
            role="search_planner",
            prompt="transient",
            system_prompt="transient",
            provider=cost_authorization.provider,
            model=cost_authorization.model,
            maximum_input_tokens=cost_authorization.maximum_input_tokens,
            maximum_output_tokens=cost_authorization.maximum_output_tokens,
        )


def test_broker_response_validator_rejects_credential_header_and_route_drift() -> None:
    request_payload = _model_request()
    response = _completed_response(
        request_payload,
        physical_attempt_count=1,
        output_text="{}",
        input_tokens=1,
        output_tokens=1,
    )
    response["authorization"] = "blocked"
    with pytest.raises(ProviderExecutionContractError, match="forbidden_response"):
        validate_provider_execution_response(
            response,
            request_payload=request_payload,
        )
    response = _completed_response(
        request_payload,
        physical_attempt_count=1,
        output_text="{}",
        input_tokens=1,
        output_tokens=1,
    )
    response["model"] = "different"
    with pytest.raises(ProviderExecutionContractError, match="attestation"):
        validate_provider_execution_response(
            response,
            request_payload=request_payload,
        )


def test_environment_file_parser_is_owned_only_by_tracked_broker(tmp_path: Path) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text(
        "OPENAI_API_KEY=one\nSERPER_API_KEY=two\nTAVILY_API_KEY=three\nUNRELATED=four\n",
        encoding="utf-8",
    )
    values = broker.load_private_environment_file(env_file)
    assert values == {
        "OPENAI_API_KEY": "one",  # pragma: allowlist secret
        "SERPER_API_KEY": "two",  # pragma: allowlist secret
        "TAVILY_API_KEY": "three",  # pragma: allowlist secret
    }
    helper_source = (ROOT / "scripts" / "run_provider_proxy_broker_once.py").read_text()
    client_source = (ROOT / "scripts" / "request_provider_proxy_broker.py").read_text()
    for source in (helper_source, client_source):
        assert "OPENAI_API_KEY" not in source
        assert "SERPER_API_KEY" not in source
        assert "TAVILY_API_KEY" not in source
        assert ".read_text(" not in source


def test_direct_openai_transport_has_zero_active_preparation_operator_callsites() -> None:
    active_paths = [
        ROOT / "scripts",
        ROOT / "proplex",
        ROOT / "docs" / "operator",
        ROOT / "docs" / "codex",
    ]
    offenders: list[str] = []
    for root in active_paths:
        for path in root.rglob("*"):
            if (
                not path.is_file()
                or path.suffix not in {".py", ".md"}
                or path.name == "openai_responses_origination_transport.py"
            ):
                continue
            text = path.read_text(encoding="utf-8")
            if (
                "create_openai_responses_transport" in text
                or "scripts.evaluation.openai_responses_origination_transport:"
                in text
            ):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
