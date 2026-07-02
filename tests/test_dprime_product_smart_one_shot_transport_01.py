"""INTEGRATION-STAGING: D-prime strict product smart model route.

Harness label: INTEGRATION-STAGING
Ordinary product path guarded or fed: DPrimeOneShotModelReviewAdapter consumed
by proplex.live_semantic_coverage_status
Runtime consumer: DPRIME-REAL-MODEL-REVIEW-RUN-01 one approved product
smart model-review run.
Why ordinary product-path work cannot be done directly: the real run is not
licensed in this phase; fake OpenAI SDK clients prove the product route under a
strict one-shot D-prime policy without spending the single approved
provider/model attempt.
Integration deadline: next phase, DPRIME-REAL-MODEL-REVIEW-RUN-01.
Exit condition: keep as PRODUCT-PATH-REGRESSION after the real run consumes the
transport, or retire if the approved product smart route changes.
Why this is not a shadow product path: tests inject the transport through the
existing DPrimeOneShotModelReviewAdapter and product status builder, not a
parallel model-review runner.
Forbidden interpretation: fake SDK responses are not live validation, semantic
support admission, citation eligibility, answer readiness, answer text, or
product correctness.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import core.dprime_assessment_validation as assessment_validation
import core.dprime_one_shot_provider_boundary as provider_boundary
import core.dprime_product_smart_one_shot_transport as route_transport
import core.dprime_support_proposal_schema as dprime
from core.dprime_one_shot_model_review_adapter import (
    invoke_dprime_one_shot_model_review_adapter,
    validate_dprime_one_shot_model_review_adapter,
)
from core.run_config import RunConfig
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    QUERY,
    _passport_retained_repo,
)
from tests.test_dprime_model_review_assessment_slice_01 import _assessment_payload

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT_MODULE = (
    ROOT / "core" / "dprime_product_smart_one_shot_transport.py"
)


def test_product_route_metadata_names_smart_dprime_task() -> None:
    ref = route_transport.product_smart_model_route_ref(
        smart_provider="OpenAI",
        smart_model="gpt-5.4",
    )

    assert ref["model_task"] == "dprime_model_review_assessment"
    assert ref["product_model_role"] == "smart"
    assert ref["product_route_kind"] == "smart_model_route"
    assert ref["configured_smart_provider"] == "OpenAI"
    assert ref["configured_smart_model"] == "gpt-5.4"
    assert ref["default_provider"] == "OpenAI"
    assert ref["default_model"] == "gpt-5.4"
    assert ref["approved_provider"] == "OpenAI"
    assert ref["approved_model"] == "gpt-5.4"
    assert ref["provider_model_approval_ref"] == (
        "human-approved:dprime-real-model-review-run-01:"
        "product-smart-model-route"
    )
    assert ref["product_config_initialization_boundary"] == (
        "core.product_model_route_config.initialize_product_model_route_config"
    )
    assert "product model-route config initialization boundary" in ref[
        "credential_source"
    ]
    assert ref["execution_policy"] == "strict_one_shot"
    assert ref["retry_policy"] == "forbidden"
    assert ref["fallback_policy"] == "forbidden"
    assert ref["provider_switching_allowed"] is False


def test_product_smart_route_defaults_match_phase_approved_resolution() -> None:
    config = RunConfig(query="fixture")

    assert config.smart_provider == route_transport.APPROVED_PROVIDER
    assert config.smart_model == route_transport.APPROVED_MODEL


def test_openai_sdk_client_uses_environment_lookup_and_disables_retries() -> None:
    calls: list[dict[str, Any]] = []

    class FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    client = route_transport.build_openai_sdk_env_client(
        openai_client_cls=FakeOpenAI,
    )

    assert isinstance(client, FakeOpenAI)
    assert calls == [{"max_retries": 0, "timeout": 60.0}]


def test_transport_invokes_approved_product_route_once_without_fallback() -> None:
    fake_client = FakeOpenAIClient(json.dumps(_assessment_payload()))
    transport = route_transport.build_dprime_product_smart_one_shot_transport(
        openai_client_factory=lambda: fake_client,
        smart_provider=RunConfig(query="fixture").smart_provider,
        smart_model=RunConfig(query="fixture").smart_model,
    )

    output = transport("prompt", system_prompt="system")

    assert json.loads(output)["support_relation"] == "directly_supports"
    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["model"] == RunConfig(query="fixture").smart_model
    assert call["response_format"] == {"type": "json_object"}
    assert call["stream"] is False
    assert "provider" not in call
    assert "fallback" not in call
    assert "api_key" not in call


def test_transport_internal_fuse_blocks_second_direct_call() -> None:
    fake_client = FakeOpenAIClient(json.dumps(_assessment_payload()))
    transport = route_transport.build_dprime_product_smart_one_shot_transport(
        openai_client_factory=lambda: fake_client
    )

    transport("prompt", system_prompt="system")

    try:
        transport("prompt", system_prompt="system")
    except route_transport.DPrimeProductSmartOneShotError as exc:
        assert exc.blocker == route_transport.BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE
    else:
        raise AssertionError("second product smart one-shot call did not fail closed")
    assert len(fake_client.calls) == 1


def test_missing_openai_credential_maps_to_safe_blocker() -> None:
    def missing_credential_factory() -> Any:
        raise RuntimeError("api_key client option must be set")

    transport = route_transport.build_dprime_product_smart_one_shot_transport(
        openai_client_factory=missing_credential_factory
    )

    try:
        transport("prompt", system_prompt="system")
    except route_transport.DPrimeProductSmartOneShotError as exc:
        assert exc.blocker == route_transport.BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE
        assert str(exc) == route_transport.BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE
    else:
        raise AssertionError("missing OpenAI credential did not fail closed")


def test_approved_model_rejection_maps_to_safe_blocker() -> None:
    fake_client = FakeOpenAIClient(
        json.dumps(_assessment_payload()),
        exc=FakeOpenAIError(
            "model does not exist",
            status_code=404,
            code="model_not_found",
        ),
    )
    transport = route_transport.build_dprime_product_smart_one_shot_transport(
        openai_client_factory=lambda: fake_client
    )

    try:
        transport("prompt", system_prompt="system")
    except route_transport.DPrimeProductSmartOneShotError as exc:
        assert exc.blocker == route_transport.BLOCKED_APPROVED_MODEL_UNAVAILABLE
        assert str(exc) == route_transport.BLOCKED_APPROVED_MODEL_UNAVAILABLE
    else:
        raise AssertionError("model rejection did not fail closed")


def test_route_mismatch_blocks_as_cannot_enforce_dprime_one_shot() -> None:
    transport = route_transport.DPrimeProductSmartOneShotTransport(
        openai_client_factory=lambda: FakeOpenAIClient(json.dumps(_assessment_payload())),
        smart_model="wrong-model",
    )

    try:
        transport("prompt", system_prompt="system")
    except route_transport.DPrimeProductSmartOneShotError as exc:
        assert exc.blocker == (
            route_transport.BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT
        )
    else:
        raise AssertionError("route mismatch did not fail closed")


def test_unapproved_product_smart_provider_blocks_before_provider_call() -> None:
    fake_client = FakeOpenAIClient(json.dumps(_assessment_payload()))
    transport = route_transport.DPrimeProductSmartOneShotTransport(
        openai_client_factory=lambda: fake_client,
        smart_provider="OpenRouter",
        smart_model="gpt-5.4",
    )

    try:
        transport("prompt", system_prompt="system")
    except route_transport.DPrimeProductSmartOneShotError as exc:
        assert exc.blocker == (
            route_transport.BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT
        )
    else:
        raise AssertionError("unapproved smart provider did not fail closed")
    assert fake_client.calls == []


def test_transport_blocker_propagates_through_dprime_adapter() -> None:
    adapter = route_transport.build_dprime_product_smart_model_review_adapter(
        provider_boundary_ref="boundary-ref",
        openai_client_factory=lambda: FakeOpenAIClient(
            json.dumps(_assessment_payload()),
            exc=FakeOpenAIError(
                "model not found",
                status_code=404,
                code="model_not_found",
            ),
        ),
    )

    result = invoke_dprime_one_shot_model_review_adapter(
        adapter,
        prompt="prompt",
        input_packet={"packet": "safe"},
        system_prompt="system",
        license_ref={"license": "safe"},
        one_shot_provider_boundary_ref={"status": "approved"},
        one_shot_model_review_adapter_ref={"status": "configured"},
    )

    assert result.ok is False
    assert result.call_count == 1
    assert result.error_type == route_transport.BLOCKED_APPROVED_MODEL_UNAVAILABLE


def test_route_adapter_is_configured_without_provider_model_metadata() -> None:
    adapter = route_transport.build_dprime_product_smart_model_review_adapter(
        provider_boundary_ref="boundary-ref",
        openai_client_factory=lambda: FakeOpenAIClient(
            json.dumps(_assessment_payload())
        ),
    )

    validation = validate_dprime_one_shot_model_review_adapter(adapter)

    assert validation.status == "configured"
    ref = validation.adapter_ref
    assert ref["provider_model_approval_ref"] == (
        route_transport.DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF
    )
    assert ref["provider_model_selection_detail_present"] is False
    assert "provider" not in ref
    assert "model" not in ref


def test_product_path_consumes_product_route_transport_via_dprime_adapter(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _passport_retained_repo(tmp_path)
    fake_client = FakeOpenAIClient(json.dumps(_assessment_payload()))
    boundary = _approved_route_boundary()
    adapter = route_transport.build_dprime_product_smart_model_review_adapter(
        provider_boundary_ref=boundary["boundary_id"],
        openai_client_factory=lambda: fake_client,
        smart_provider="OpenAI",
        smart_model="gpt-5.4",
    )

    result = build_live_semantic_coverage_status(
        query=QUERY,
        repo_root=repo_root,
        smart_provider="OpenAI",
        smart_model="gpt-5.4",
        dprime_one_shot_provider_boundary=boundary,
        dprime_one_shot_model_review_adapter=adapter,
        dprime_model_review_license=_route_license(),
    )

    assert len(fake_client.calls) == 1
    assert result.decision == (
        dprime.BLOCKED_DPRIME_SEMANTIC_OBSERVATION_NOT_LICENSED
    )
    assert "phase: DPRIME-APPROVED-PROVIDER-ONE-SHOT-TRANSPORT-01" in result.output
    dprime_status = result.payload["dprime_status"]
    assert (
        dprime_status["phase"]
        == "DPRIME-APPROVED-PROVIDER-ONE-SHOT-TRANSPORT-01"
    )
    assert dprime_status["model_review_ref"]["phase"] == (
        "DPRIME-APPROVED-PROVIDER-ONE-SHOT-TRANSPORT-01"
    )
    assert dprime_status["model_review_ref"]["input_packet_ref"]["phase"] == (
        "DPRIME-APPROVED-PROVIDER-ONE-SHOT-TRANSPORT-01"
    )
    route_ref = dprime_status["product_model_route_ref"]
    assert dprime_status["run_kernel_admission_decision_status"] == (
        dprime.DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
    )
    assert route_ref["model_task"] == "dprime_model_review_assessment"
    assert route_ref["product_model_role"] == "smart"
    assert route_ref["configured_smart_provider"] == "OpenAI"
    assert route_ref["configured_smart_model"] == "gpt-5.4"
    assert route_ref["provider_model_approval_ref"] == (
        route_transport.DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF
    )
    assert route_ref["execution_policy"] == "strict_one_shot"
    assert dprime_status["model_review_call_count"] == 1
    assert dprime_status["assessment_validation_status"] == (
        assessment_validation.ASSESSMENT_SCHEMA_VALID
    )
    assert (
        dprime_status["proposal_validation_status"]
        == dprime.DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
    )
    assert (
        dprime_status["run_kernel_support_admission_status"]
        == dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    )
    assert dprime_status["run_kernel_support_admission_request_ref"][
        "request_status"
    ] == dprime.DPRIME_RUN_KERNEL_ADMISSION_REQUEST_READY
    assert dprime_status["validated_support_proposal_available"] is True
    assert dprime_status["objects_created"]["validated_support_proposal"] is True
    assert dprime_status["objects_created"][
        "run_kernel_support_proposal_admission_request"
    ] is True
    assert dprime_status["objects_created"]["semantic_observation"] is False
    assert dprime_status["objects_created"]["component_coverage"] is False


def test_transport_module_avoids_broad_helpers_and_search_surfaces() -> None:
    forbidden_imports = {
        "core.llm",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.routing_runtime",
        "core.search_providers",
        "core.search_planner_model_adapter",
        "dotenv",
        "requests",
        "subprocess",
    }

    assert _imports(TRANSPORT_MODULE).isdisjoint(forbidden_imports)
    call_names = _call_names(TRANSPORT_MODULE)
    assert "ask_model" not in call_names
    assert "core.llm.ask_model" not in call_names
    assert "responses.create" not in call_names


def test_documentation_guard_exists_for_product_config_boundary() -> None:
    doc = (
        ROOT
        / "docs"
        / "architecture"
        / "DPRIME_PRODUCT_MODEL_ROUTE_CONFIG_BOUNDARY.md"
    ).read_text(encoding="utf-8")

    assert "product's shared route/config boundary" in doc
    assert "must not create a separate provider selector" in doc
    assert "credential loader" in doc
    assert "Retries and fallbacks are forbidden" in doc
    assert "attempt ledger" in doc


class FakeOpenAIError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, client: FakeOpenAIClient) -> None:
        self._client = client

    def create(self, **kwargs: Any) -> FakeResponse:
        self._client.calls.append(kwargs)
        if self._client.exc is not None:
            raise self._client.exc
        return FakeResponse(self._client.content)


class FakeChat:
    def __init__(self, client: FakeOpenAIClient) -> None:
        self.completions = FakeCompletions(client)


class FakeOpenAIClient:
    def __init__(self, content: str, *, exc: Exception | None = None) -> None:
        self.content = content
        self.exc = exc
        self.calls: list[dict[str, Any]] = []
        self.chat = FakeChat(self)


def _approved_route_boundary() -> dict[str, Any]:
    return {
        "boundary_id": "dprime-one-shot-provider-boundary:analyst-smart-route:v1",
        "phase": provider_boundary.DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE,
        "enabled": True,
        "default_disabled": False,
        "test_only": False,
        "provider_model_selection_status": "approval_ref_present",
        "provider_model_approval_ref": (
            route_transport.DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF
        ),
        "max_provider_attempts": 1,
        "retry_policy": "forbidden",
        "fallback_policy": "forbidden",
        "timeout_policy": "fail_closed",
        "raw_prompt_retention": False,
        "raw_model_response_retention": False,
        "provider_payload_retention": False,
        "real_call_authorized": True,
        "call_count": 0,
        "provider_switching_allowed": False,
        "one_shot_adapter_proven": True,
        "one_shot_adapter_ref": (
            route_transport.DPRIME_PRODUCT_SMART_ADAPTER_REF
        ),
        "closed_surface_flags": provider_boundary.default_closed_surface_flags(),
    }


def _route_license() -> dict[str, Any]:
    return {
        "license_id": (
            route_transport.DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF
        ),
        "enabled": True,
        "test_only": False,
        "callable_kind": "real_one_shot",
        "max_model_review_calls": 1,
        "retry_policy": "forbidden",
        "timeout_policy": "fail_closed",
        "one_shot_adapter_ref": (
            route_transport.DPRIME_PRODUCT_SMART_ADAPTER_REF
        ),
    }


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _expression_name(node.func)
            if call_name:
                calls.add(call_name)
    return calls


def _expression_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expression_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""
