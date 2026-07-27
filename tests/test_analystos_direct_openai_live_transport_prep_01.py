"""Phase-focus proof for the no-live direct OpenAI origination preparation.

Test path/node id:
``tests/test_analystos_direct_openai_live_transport_prep_01.py``.
Proof class: component_harness_proof.
Validation bucket: phase_focus.
Surface guarded: evaluation-only OpenAI Responses transport construction,
strict timeout/failure handling, safe observed accounting, and deterministic
live-addendum-v2 preparation.
High-custody or closed-this-phase surface: live provider execution, credentials,
broker access, production routing, and post-merge authorization remain closed.
Runtime/product path guarded: the installed AnalystOS evaluator's injected
EvaluationTransport seam and its canonical request/manifest/identity owners.
Expected cost: deterministic, offline, and sub-second apart from imports.
Promotion posture: remain phase_focus until the separately licensed acceptance
evaluation is complete.
Demotion/retirement condition: retain only the durable transport contract after
the acceptance operator is retired.
Why not fast_pr: this is detailed no-live preparation machinery, not a broad
product sentinel.
"""

from __future__ import annotations

import gc
import json
import os
import subprocess
import weakref
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from core.search_planner_model_prompt import SEARCH_PLANNER_MODEL_SYSTEM_PROMPT
from scripts.evaluation import openai_responses_origination_transport as transport_module
from scripts.evaluation import prepare_analystos_gpt54_live_evaluation as preparation
from scripts.evaluation.run_analystos_model_origination_evaluation import (
    LIVE_ADDENDUM_SCHEMA_VERSION,
    EvaluationConfigurationError,
    EvaluationRequest,
    EvaluationTransportError,
    LiveAuthorization,
    ScenarioRunResult,
    build_call_manifest,
    build_execution_identity,
    current_repository_sha,
    resolve_request,
    run_evaluation,
    validate_canonical_cli_invocation,
    validate_live_authorization,
)
from tests.fixtures.analystos_model_origination_expectations import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SEARCH_PLANNER,
)
from tests.fixtures.searchos_analystos_offline_scenarios import (
    CASE_3,
    SCENARIO_BY_ID,
)

ROOT = Path(__file__).resolve().parents[1]


class FakeTimeoutError(Exception):
    """Offline stand-in for openai.APITimeoutError."""


class FakeResponse:
    def __init__(
        self,
        *,
        output_text: str | None = '{"status":"ok"}',
        input_tokens: int | None = 123,
        output_tokens: int | None = 45,
    ) -> None:
        self.output_text = output_text
        self.usage = type(
            "Usage",
            (),
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        )()


class FakeResponses:
    def __init__(
        self,
        *,
        response: FakeResponse | None = None,
        failure: Exception | None = None,
    ) -> None:
        self._response_values = (
            None
            if response is None
            else (
                response.output_text,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )
        )
        self.failure = failure
        self.calls: list[dict[str, Any]] = []
        self.response_ref: weakref.ReferenceType[FakeResponse] | None = None

    def create(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(dict(kwargs))
        if self.failure is not None:
            raise self.failure
        assert self._response_values is not None
        response = FakeResponse(
            output_text=self._response_values[0],
            input_tokens=self._response_values[1],
            output_tokens=self._response_values[2],
        )
        self.response_ref = weakref.ref(response)
        return response


class FakeOpenAIConstructor:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(dict(kwargs))
        return type("FakeOpenAIClient", (), {"responses": self.responses})()


def _authorization(
    *,
    provider: str = transport_module.SUPPORTED_PROVIDER,
    model: str = transport_module.SUPPORTED_MODEL,
    retry_cap: int = 0,
    maximum_input_tokens: int = 16_000,
    maximum_output_tokens: int = 8_000,
) -> LiveAuthorization:
    return LiveAuthorization(
        schema_version=LIVE_ADDENDUM_SCHEMA_VERSION,
        reference="synthetic-direct-openai-authorization",
        repository_sha="a" * 40,
        provider=provider,
        model=model,
        allowed_evaluation_pass="planner_only",
        allowed_model_roles=(ROLE_SEARCH_PLANNER,),
        allowed_scenario_ids=(CASE_3,),
        maximum_model_calls=1,
        maximum_scryraven_runs=1,
        retry_cap=retry_cap,
        maximum_input_tokens=maximum_input_tokens,
        maximum_output_tokens=maximum_output_tokens,
        cost_ceiling=0.16,
        output_packet_path="output/local/synthetic/result.json",
        decision="Synthetic offline contract proof.",
        stop_condition="Stop after any failure.",
        raw_retention_posture="sanitized_only",
        transport_factory_spec=transport_module.TRANSPORT_FACTORY_SPEC,
        canonical_operator_command='["synthetic"]',
        canonical_operator_command_digest="b" * 64,
    )


def _output_root(tmp_path: Path) -> Path:
    return (
        Path("output/local/analystos-live-origination-01-tests")
        / tmp_path.parent.name
        / tmp_path.name
    )


def test_direct_transport_uses_exact_client_and_responses_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = FakeResponses(response=FakeResponse())
    constructor = FakeOpenAIConstructor(responses)
    monkeypatch.setattr(
        transport_module,
        "_load_openai_sdk",
        lambda: (constructor, FakeTimeoutError),
    )

    def forbidden_getenv(*_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("offline transport proof must not read the environment")

    monkeypatch.setattr(os, "getenv", forbidden_getenv)
    authorization = _authorization()
    transport = transport_module.create_openai_responses_transport(authorization)
    result = transport(
        role=ROLE_SEARCH_PLANNER,
        prompt="exact boundary prompt",
        system_prompt="exact installed system prompt",
        provider=authorization.provider,
        model=authorization.model,
        maximum_input_tokens=authorization.maximum_input_tokens,
        maximum_output_tokens=authorization.maximum_output_tokens,
    )

    assert constructor.calls == [{"max_retries": 0, "timeout": 600.0}]
    assert responses.calls == [
        {
            "model": "gpt-5.4-2026-03-05",
            "instructions": "exact installed system prompt",
            "input": "exact boundary prompt",
            "reasoning": {"effort": "medium"},
            "max_output_tokens": 8_000,
            "store": False,
        }
    ]
    create_kwargs = responses.calls[0]
    for forbidden in (
        "tools",
        "temperature",
        "timeout",
        "max_retries",
        "api_key",
    ):
        assert forbidden not in create_kwargs
    assert result.output == '{"status":"ok"}'
    assert result.input_tokens == 123
    assert result.output_tokens == 45
    assert Decimal(str(result.cost)) == transport_module.conservative_cost_decimal(
        123,
        45,
    )
    assert result.canonical_provider_used == "openai"
    assert result.canonical_model_used == "gpt-5.4-2026-03-05"
    assert result.provider_request_attempt_count == 1
    assert result.credentials_accessed is True
    assert result.raw_material_retained is False
    assert transport.credentials_accessed is True
    gc.collect()
    assert responses.response_ref is not None
    assert responses.response_ref() is None
    assert "exact boundary prompt" not in repr(transport)
    assert "exact installed system prompt" not in repr(transport)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    (
        ("provider", "OpenAI", "only provider openai"),
        ("model", "gpt-5.4", "only model gpt-5.4-2026-03-05"),
        ("retry_cap", 1, "retry cap 0"),
    ),
)
def test_factory_rejects_any_route_or_retry_variation_before_sdk_construction(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    value: str | int,
    message: str,
) -> None:
    sdk_loads = 0

    def forbidden_sdk_load() -> tuple[Any, Any]:
        nonlocal sdk_loads
        sdk_loads += 1
        raise AssertionError("SDK must not load for an invalid authorization")

    monkeypatch.setattr(
        transport_module,
        "_load_openai_sdk",
        forbidden_sdk_load,
    )
    authorization = replace(_authorization(), **{field_name: value})
    with pytest.raises(EvaluationConfigurationError, match=message):
        transport_module.create_openai_responses_transport(authorization)
    assert sdk_loads == 0


@pytest.mark.parametrize(
    ("response", "message"),
    (
        (
            FakeResponse(output_text=None),
            transport_module.OUTPUT_ERROR_MESSAGE,
        ),
        (
            FakeResponse(input_tokens=None),
            transport_module.USAGE_ERROR_MESSAGE,
        ),
        (
            FakeResponse(output_tokens=None),
            transport_module.USAGE_ERROR_MESSAGE,
        ),
    ),
)
def test_transport_never_invents_output_usage_or_cost(
    monkeypatch: pytest.MonkeyPatch,
    response: FakeResponse,
    message: str,
) -> None:
    responses = FakeResponses(response=response)
    constructor = FakeOpenAIConstructor(responses)
    monkeypatch.setattr(
        transport_module,
        "_load_openai_sdk",
        lambda: (constructor, FakeTimeoutError),
    )
    authorization = _authorization()
    transport = transport_module.create_openai_responses_transport(authorization)
    with pytest.raises(EvaluationTransportError, match=f"^{message}$"):
        transport(
            role=ROLE_SEARCH_PLANNER,
            prompt="prompt",
            system_prompt="system",
            provider=authorization.provider,
            model=authorization.model,
            maximum_input_tokens=authorization.maximum_input_tokens,
            maximum_output_tokens=authorization.maximum_output_tokens,
        )
    assert len(responses.calls) == 1


def test_timeout_is_one_attempt_typed_constant_and_writes_no_packet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_exception_text = (
        "private prompt, credential, header, request, and payload material"
    )
    responses = FakeResponses(
        failure=FakeTimeoutError(raw_exception_text),
    )
    constructor = FakeOpenAIConstructor(responses)
    monkeypatch.setattr(
        transport_module,
        "_load_openai_sdk",
        lambda: (constructor, FakeTimeoutError),
    )

    root = _output_root(tmp_path)
    output_path = (root / "planner-result.json").as_posix()
    addendum_path = (root / "planner-addendum.json").as_posix()
    request = resolve_request(
        EvaluationRequest(
            evaluation_pass="planner_only",
            execution_mode="execute",
            scenario_ids=(CASE_3,),
            selected_model_roles=(ROLE_SEARCH_PLANNER,),
            output_packet_path=output_path,
        )
    )
    repository_sha = current_repository_sha()
    identity = build_execution_identity(
        request,
        repository_sha=repository_sha,
        live_addendum_path=addendum_path,
        transport_factory_spec=transport_module.TRANSPORT_FACTORY_SPEC,
    )
    manifest = build_call_manifest(request, retry_allowance=0)
    authorization = LiveAuthorization(
        schema_version=LIVE_ADDENDUM_SCHEMA_VERSION,
        reference="synthetic-timeout-proof",
        repository_sha=repository_sha,
        provider=transport_module.SUPPORTED_PROVIDER,
        model=transport_module.SUPPORTED_MODEL,
        allowed_evaluation_pass=request.evaluation_pass,
        allowed_model_roles=request.selected_model_roles,
        allowed_scenario_ids=request.scenario_ids,
        maximum_model_calls=manifest.total_maximum_physical_model_calls,
        maximum_scryraven_runs=manifest.maximum_scryraven_runs,
        retry_cap=0,
        maximum_input_tokens=16_000,
        maximum_output_tokens=8_000,
        cost_ceiling=0.16,
        output_packet_path=identity.output_packet_path,
        decision="Stop on timeout.",
        stop_condition="Unknown billing requires maintainer reauthorization.",
        raw_retention_posture="sanitized_only",
        transport_factory_spec=identity.transport_factory_spec,
        canonical_operator_command=identity.canonical_operator_command,
        canonical_operator_command_digest=(
            identity.canonical_operator_command_digest
        ),
    )

    def runner(
        *,
        scenario_id: str,
        controller: Any,
    ) -> ScenarioRunResult:
        controller.invoke(
            role=ROLE_SEARCH_PLANNER,
            prompt=(
                "Synthetic boundary fixture.\nSanitized planner input JSON:\n"
                + SCENARIO_BY_ID[scenario_id].root_query
            ),
            system_prompt=SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
            provider=authorization.provider,
            model=authorization.model,
        )
        raise AssertionError("a timed-out request must not return to the runner")

    target = ROOT / output_path
    target.unlink(missing_ok=True)
    with pytest.raises(EvaluationTransportError) as raised:
        run_evaluation(
            request,
            repository_sha=repository_sha,
            authorization=authorization,
            execution_identity=identity,
            transport_factory=(
                transport_module.create_openai_responses_transport
            ),
            scenario_runner=runner,
        )
    assert str(raised.value) == transport_module.TIMEOUT_ERROR_MESSAGE
    assert raw_exception_text not in str(raised.value)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert constructor.calls == [{"max_retries": 0, "timeout": 600.0}]
    assert len(responses.calls) == 1
    assert "timeout" not in responses.calls[0]
    assert "max_retries" not in responses.calls[0]
    assert not target.exists()
    assert not (ROOT / root / "analyst-result.json").exists()
    assert not (ROOT / root / "combined-result.json").exists()


def test_preparation_derives_and_validates_all_three_current_head_addenda(
    tmp_path: Path,
) -> None:
    output_root = _output_root(tmp_path)
    prepared = preparation.prepare_live_addenda(
        repository_root=ROOT,
        output_root=output_root,
    )
    repository_sha = current_repository_sha()
    assert tuple(item.definition.label for item in prepared) == ("A", "B", "C")
    assert [item.authorization.maximum_model_calls for item in prepared] == [
        4,
        9,
        7,
    ]
    assert [item.authorization.maximum_scryraven_runs for item in prepared] == [
        4,
        2,
        1,
    ]
    assert [
        Decimal(str(item.authorization.cost_ceiling)) for item in prepared
    ] == [
        Decimal("0.64"),
        Decimal("1.44"),
        Decimal("1.12"),
    ]
    assert sum(
        item.authorization.maximum_model_calls for item in prepared
    ) == 20
    assert sum(
        item.authorization.maximum_scryraven_runs for item in prepared
    ) == 7
    assert sum(
        (
            Decimal(str(item.authorization.cost_ceiling))
            for item in prepared
        ),
        start=Decimal("0"),
    ) == Decimal("3.20")

    expected_roles = (
        (ROLE_SEARCH_PLANNER,),
        (ROLE_COMPONENT_ANALYST, ROLE_CROSS_COMPONENT_ANALYST),
        (
            ROLE_SEARCH_PLANNER,
            ROLE_COMPONENT_ANALYST,
            ROLE_CROSS_COMPONENT_ANALYST,
        ),
    )
    expected_scenarios = (
        (
            "case_03_pure_depth_two",
            "case_04_nested_serial_recovery",
            "case_06_root_query_retention",
            "case_07_honest_nonclosure",
        ),
        (
            "case_04_nested_serial_recovery",
            "case_07_honest_nonclosure",
        ),
        ("case_06_root_query_retention",),
    )
    for item, roles, scenarios in zip(
        prepared,
        expected_roles,
        expected_scenarios,
        strict=True,
    ):
        target = ROOT / item.addendum_path
        packet = json.loads(target.read_text(encoding="utf-8"))
        parsed = LiveAuthorization.from_mapping(packet)
        assert parsed == item.authorization
        assert parsed.repository_sha == repository_sha
        assert parsed.provider == "openai"
        assert parsed.model == "gpt-5.4-2026-03-05"
        assert parsed.allowed_model_roles == roles
        assert parsed.allowed_scenario_ids == scenarios
        assert parsed.retry_cap == 0
        assert parsed.maximum_input_tokens == 16_000
        assert parsed.maximum_output_tokens == 8_000
        assert parsed.raw_retention_posture == "sanitized_only"
        assert parsed.transport_factory_spec == (
            transport_module.TRANSPORT_FACTORY_SPEC
        )
        manifest = validate_live_authorization(
            item.request,
            parsed,
            repository_sha=repository_sha,
            execution_identity=item.execution_identity,
        )
        assert manifest.to_packet() == item.manifest_packet
        canonical_argv = json.loads(parsed.canonical_operator_command)
        validate_canonical_cli_invocation(
            item.execution_identity,
            canonical_argv,
        )
        assert not (ROOT / parsed.output_packet_path).exists()
        ignored = subprocess.run(
            [
                "git",
                "check-ignore",
                "--quiet",
                "--",
                item.addendum_path,
            ],
            cwd=ROOT,
            check=False,
        )
        assert ignored.returncode == 0
        assert len(item.execution_identity.execution_identity_digest) == 64


def test_preparation_main_labels_branch_packets_nonauthoritative(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    prepared = preparation.prepare_live_addenda(
        repository_root=ROOT,
        output_root=_output_root(tmp_path),
    )
    monkeypatch.setattr(
        preparation,
        "prepare_live_addenda",
        lambda: prepared,
    )
    assert preparation.main() == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["live_commands_executed"] is False
    assert summary["authoritative_for_live_use"] is False
    assert summary["post_merge_regeneration_required"] is True
    assert summary["request_timeout_seconds"] == 600.0
    assert summary["retry_cap"] == 0
    assert summary["total_maximum_model_calls"] == 20
    assert summary["total_maximum_scryraven_runs"] == 7
    assert Decimal(str(summary["whole_phase_cost_ceiling"])) == Decimal(
        "3.20"
    )
    assert len(summary["stages"]) == 3
    assert all(
        "manifest_census" in stage and "manifest" not in stage
        for stage in summary["stages"]
    )
    assert "Regenerate" in summary["notice"]


def test_plan_only_does_not_load_sdk_or_access_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk_loads = 0

    def forbidden_sdk_load() -> tuple[Any, Any]:
        nonlocal sdk_loads
        sdk_loads += 1
        raise AssertionError("plan_only must not load the provider SDK")

    monkeypatch.setattr(
        transport_module,
        "_load_openai_sdk",
        forbidden_sdk_load,
    )
    packet = run_evaluation(
        EvaluationRequest(
            evaluation_pass="planner_only",
            execution_mode="plan_only",
            scenario_ids=(CASE_3,),
        ),
        repository_sha="c" * 40,
        transport_factory=(
            transport_module.create_openai_responses_transport
        ),
    )
    assert sdk_loads == 0
    assert packet["transport_created"] is False
    assert packet["credentials_accessed"] is False
    assert packet["call_counts"]["external_calls"] == 0


def test_transport_source_has_no_credential_or_environment_reader() -> None:
    source = Path(transport_module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "os.getenv",
        "os.environ",
        "load_dotenv",
        "dotenv_values",
        "api_key=",
    ):
        assert forbidden not in source
