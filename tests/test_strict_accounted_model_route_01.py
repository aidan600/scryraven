"""
Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex
--mvp-single-relation-live-dogfood-run --query "<supported query>"
Runtime consumer: proplex.__main__ ->
proplex.mvp_single_relation_live_dogfood_run ->
core.model_assisted_single_relation_planning.
Why ordinary product-path work cannot be done directly: offline validation must
use fake OpenAI-compatible clients so no live model provider requests occur.
Integration deadline: current phase.
Exit condition: keep while the ordinary single-relation dogfood runner consumes
the strict FastModel route, or merge into a broader cheap product-path sentinel.
Why this is not a shadow product path: tests exercise the product route boundary
and existing planner seam; they do not add a standalone planner command or
alternate answer path.
Forbidden interpretation: fake-client route tests are not live FastModel
validation, product correctness, evidence, support, source authority,
source-obligation satisfaction, citation eligibility, FAP/Author output, or
multi-component execution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import core.model_assisted_single_relation_planning as planning
import core.strict_accounted_model_route as route

ROOT = Path(__file__).resolve().parents[1]
ROUTE_MODULE_PATH = ROOT / "core" / "strict_accounted_model_route.py"


def test_openai_route_success_is_one_responses_attempt_without_secret_serialization() -> None:
    calls: list[dict[str, Any]] = []
    route_callable = route.build_strict_accounted_fast_model_planning_route(
        fast_provider="OpenAI",
        fast_model="fast-planner",
        credential_lookup=_credential_lookup("unit-test-openai-credential"),
        client_factory=_fake_client_factory(
            calls,
            json.dumps(_proposal()),
        ),
    )

    result = route_callable(
        "{}",
        "system",
        provider="OpenAI",
        model="fast-planner",
        require_json=True,
        use_reasoning=False,
        max_tokens=1800,
        effort="low",
    )
    serialized_ref = json.dumps(
        {"route": route_callable.to_ref(), "result": result.to_safe_diagnostic()},
        sort_keys=True,
    )

    assert result.return_code == 0
    assert result.output_text == json.dumps(_proposal())
    assert result.model_calls_attempted == 1
    assert result.model_calls_completed == 1
    assert result.provider_used == "OpenAI"
    assert result.model_used == "fast-planner"
    assert result.configured_endpoint_kind == route.ENDPOINT_KIND_OPENAI_RESPONSES
    assert result.endpoint_used == route.ENDPOINT_KIND_OPENAI_RESPONSES
    assert result.to_safe_diagnostic()["endpoint_switching_allowed"] is False
    assert calls[0]["factory"]["max_retries"] == 0
    assert "base_url" not in calls[0]["factory"]
    assert calls[0]["responses_create_count"] == 1
    assert calls[0]["chat_create_count"] == 0
    assert calls[0]["responses_create"]["text"] == {
        "format": {"type": "json_object"}
    }
    assert calls[0]["responses_create"]["max_output_tokens"] == 1800
    assert calls[0]["responses_create"]["stream"] is False
    assert calls[0]["responses_create"]["store"] is False
    assert calls[0]["responses_create"]["instructions"] == "system"
    assert calls[0]["responses_create"]["input"] == "{}"
    assert "messages" not in calls[0]["responses_create"]
    assert "unit-test-openai-credential" not in serialized_ref
    assert "OPENAI_API_KEY" not in serialized_ref
    assert result.to_safe_diagnostic()["credential_values_retained"] is False


def test_openrouter_and_local_use_provider_specific_config_without_leaking() -> None:
    openrouter_calls: list[dict[str, Any]] = []
    local_calls: list[dict[str, Any]] = []
    openrouter = route.build_strict_accounted_fast_model_planning_route(
        fast_provider="OpenRouter",
        fast_model="or-fast",
        local_url="http://localhost:5678/v1",
        credential_lookup=_credential_lookup("unit-test-openrouter-credential"),
        client_factory=_fake_client_factory(openrouter_calls, json.dumps(_proposal())),
    )
    local = route.build_strict_accounted_fast_model_planning_route(
        fast_provider="Local (LM Studio)",
        fast_model="local-fast",
        local_url="http://localhost:5678/v1",
        credential_lookup={}.get,
        client_factory=_fake_client_factory(local_calls, json.dumps(_proposal())),
    )

    openrouter_result = openrouter(
        "{}",
        "system",
        provider="OpenRouter",
        model="or-fast",
        require_json=True,
    )
    local_result = local(
        "{}",
        "system",
        provider="Local (LM Studio)",
        model="local-fast",
        require_json=True,
    )
    serialized_refs = json.dumps(
        {
            "openrouter": openrouter.to_ref(),
            "openrouter_result": openrouter_result.to_safe_diagnostic(),
            "local": local.to_ref(),
            "local_result": local_result.to_safe_diagnostic(),
        },
        sort_keys=True,
    )

    assert openrouter_result.return_code == 0
    assert local_result.return_code == 0
    assert openrouter_calls[0]["factory"]["base_url"] == route.OPENROUTER_BASE_URL
    assert local_calls[0]["factory"]["base_url"] == "http://localhost:5678/v1"
    assert openrouter_calls[0]["factory"]["max_retries"] == 0
    assert local_calls[0]["factory"]["max_retries"] == 0
    assert openrouter_result.endpoint_used == (
        route.ENDPOINT_KIND_CHAT_COMPLETIONS_COMPATIBLE
    )
    assert local_result.endpoint_used == (
        route.ENDPOINT_KIND_CHAT_COMPLETIONS_COMPATIBLE
    )
    assert openrouter_calls[0]["chat_create_count"] == 1
    assert local_calls[0]["chat_create_count"] == 1
    assert openrouter_calls[0]["responses_create_count"] == 0
    assert local_calls[0]["responses_create_count"] == 0
    assert openrouter_calls[0]["chat_create"]["response_format"] == (
        {"type": "json_object"}
    )
    assert local_calls[0]["chat_create"]["response_format"] == {"type": "json_object"}
    assert "unit-test-openrouter-credential" not in serialized_refs
    assert "OPENROUTER_API_KEY" not in serialized_refs
    assert "http://localhost:5678/v1" not in serialized_refs
    assert openrouter.to_ref()["configured_local_url_posture"] == (
        "local_configured_not_retained"
    )
    assert local.to_ref()["configured_local_url_posture"] == (
        "local_configured_not_retained"
    )


def test_openai_responses_exception_is_one_attempt_no_retry_or_fallback() -> None:
    calls: list[dict[str, Any]] = []
    route_callable = route.build_strict_accounted_fast_model_planning_route(
        fast_provider="OpenAI",
        fast_model="fast-planner",
        credential_lookup=_credential_lookup("unit-test-openai-credential"),
        client_factory=_fake_client_factory(calls, RuntimeError("provider down")),
    )

    result = route_callable(
        "{}",
        "system",
        provider="OpenAI",
        model="fast-planner",
        require_json=True,
    )

    assert result.return_code == 2
    assert result.blocker == route.BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_CALL_FAILED
    assert result.model_calls_attempted == 1
    assert result.model_calls_completed == 0
    assert result.endpoint_used == route.ENDPOINT_KIND_OPENAI_RESPONSES
    assert len(calls) == 1
    assert calls[0]["responses_create_count"] == 1
    assert calls[0]["chat_create_count"] == 0


def test_switching_attempts_fail_before_provider_request() -> None:
    unsupported_calls: list[dict[str, Any]] = []
    provider_switch_calls: list[dict[str, Any]] = []
    model_switch_calls: list[dict[str, Any]] = []
    endpoint_switch_calls: list[dict[str, Any]] = []
    unsupported = route.build_strict_accounted_fast_model_planning_route(
        fast_provider="MysteryAI",
        fast_model="fast-planner",
        credential_lookup={}.get,
        client_factory=_fake_client_factory(unsupported_calls, json.dumps(_proposal())),
    )
    provider_strict = route.build_strict_accounted_fast_model_planning_route(
        fast_provider="OpenAI",
        fast_model="fast-planner",
        credential_lookup=_credential_lookup("unit-test-openai-credential"),
        client_factory=_fake_client_factory(
            provider_switch_calls,
            json.dumps(_proposal()),
        ),
    )
    model_strict = route.build_strict_accounted_fast_model_planning_route(
        fast_provider="OpenAI",
        fast_model="fast-planner",
        credential_lookup=_credential_lookup("unit-test-openai-credential"),
        client_factory=_fake_client_factory(
            model_switch_calls,
            json.dumps(_proposal()),
        ),
    )
    endpoint_strict = route.build_strict_accounted_fast_model_planning_route(
        fast_provider="OpenAI",
        fast_model="fast-planner",
        credential_lookup=_credential_lookup("unit-test-openai-credential"),
        client_factory=_fake_client_factory(
            endpoint_switch_calls,
            json.dumps(_proposal()),
        ),
    )

    unsupported_result = unsupported(
        "{}",
        "system",
        provider="MysteryAI",
        model="fast-planner",
        require_json=True,
    )
    provider_switch_result = provider_strict(
        "{}",
        "system",
        provider="OpenRouter",
        model="fast-planner",
        require_json=True,
    )
    model_switch_result = model_strict(
        "{}",
        "system",
        provider="OpenAI",
        model="different-fast-planner",
        require_json=True,
    )
    endpoint_switch_result = endpoint_strict(
        "{}",
        "system",
        provider="OpenAI",
        model="fast-planner",
        endpoint_kind=route.ENDPOINT_KIND_CHAT_COMPLETIONS_COMPATIBLE,
        require_json=True,
    )

    assert unsupported_result.blocker == (
        route.BLOCKED_STRICT_ACCOUNTED_FASTMODEL_PROVIDER_UNSUPPORTED
    )
    assert unsupported_result.model_calls_attempted == 0
    assert provider_switch_result.blocker == (
        route.BLOCKED_STRICT_ACCOUNTED_FASTMODEL_UNSAFE_REQUEST
    )
    assert model_switch_result.blocker == (
        route.BLOCKED_STRICT_ACCOUNTED_FASTMODEL_UNSAFE_REQUEST
    )
    assert endpoint_switch_result.blocker == (
        route.BLOCKED_STRICT_ACCOUNTED_FASTMODEL_UNSAFE_REQUEST
    )
    assert provider_switch_result.model_calls_attempted == 0
    assert model_switch_result.model_calls_attempted == 0
    assert endpoint_switch_result.model_calls_attempted == 0
    assert unsupported_calls == []
    assert provider_switch_calls == []
    assert model_switch_calls == []
    assert endpoint_switch_calls == []


def test_invalid_json_blocks_in_reducer_without_second_provider_call() -> None:
    calls: list[dict[str, Any]] = []
    route_callable = route.build_strict_accounted_fast_model_planning_route(
        fast_provider="OpenAI",
        fast_model="fast-planner",
        credential_lookup=_credential_lookup("unit-test-openai-credential"),
        client_factory=_fake_client_factory(calls, "not json"),
    )

    packet = planning.build_model_assisted_single_relation_planning_packet(
        planning_context_kind=planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        context_state={"sanitized_query": "What is the current example fee?"},
        planner_callable=route_callable,
        strict_model_route_ref=route_callable.to_ref(),
        clean_json_response=lambda text: text,
    )

    assert packet["blocker"] == planning.BLOCKED_MODEL_ASSISTED_PLANNING_MODEL_OUTPUT_INVALID
    assert packet["model_calls_attempted"] == 1
    assert packet["model_calls_completed"] == 1
    assert packet["strict_model_route_result_ref"]["return_code"] == 0
    assert packet["strict_model_route_result_ref"]["endpoint_used"] == (
        route.ENDPOINT_KIND_OPENAI_RESPONSES
    )
    assert len(calls) == 1
    assert calls[0]["responses_create_count"] == 1
    assert calls[0]["chat_create_count"] == 0


def test_static_route_does_not_use_broad_llm_helper_or_fallback_surfaces() -> None:
    text = ROUTE_MODULE_PATH.read_text(encoding="utf-8")

    assert "core.llm" not in text
    assert "ask_model" not in text.replace("core.llm.ask_model", "")
    assert ".responses.create" in text
    assert ".chat.completions.create" in text
    assert "retry_with_backoff" not in text
    assert "for attempt" not in text


def _proposal() -> dict[str, Any]:
    return {
        "planning_context_kind": planning.PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        "component_count_hypothesis": "single",
        "expected_source_class": "official source of record",
        "official_or_source_of_record_artifact_hypotheses": ["official fee page"],
        "preferred_acquisition_query": "official current example fee",
    }


def _fake_client_factory(
    calls: list[dict[str, Any]],
    response_or_exc: str | Exception,
) -> Any:
    def factory(**kwargs: Any) -> _FakeClient:
        record = {
            "factory": dict(kwargs),
            "create_count": 0,
            "chat_create_count": 0,
            "responses_create_count": 0,
        }
        calls.append(record)
        return _FakeClient(record, response_or_exc)

    return factory


def _credential_lookup(value: str) -> Any:
    def lookup(_name: str) -> str:
        return value

    return lookup


class _FakeClient:
    def __init__(self, record: dict[str, Any], response_or_exc: str | Exception) -> None:
        self.chat = _FakeChat(record, response_or_exc)
        self.responses = _FakeResponses(record, response_or_exc)


class _FakeChat:
    def __init__(self, record: dict[str, Any], response_or_exc: str | Exception) -> None:
        self.completions = _FakeCompletions(record, response_or_exc)


class _FakeCompletions:
    def __init__(self, record: dict[str, Any], response_or_exc: str | Exception) -> None:
        self._record = record
        self._response_or_exc = response_or_exc

    def create(self, **kwargs: Any) -> Any:
        self._record["create_count"] += 1
        self._record["chat_create_count"] += 1
        self._record["chat_create"] = dict(kwargs)
        if isinstance(self._response_or_exc, Exception):
            raise self._response_or_exc
        return _FakeChatResponse(self._response_or_exc)


class _FakeResponses:
    def __init__(self, record: dict[str, Any], response_or_exc: str | Exception) -> None:
        self._record = record
        self._response_or_exc = response_or_exc

    def create(self, **kwargs: Any) -> Any:
        self._record["create_count"] += 1
        self._record["responses_create_count"] += 1
        self._record["responses_create"] = dict(kwargs)
        if isinstance(self._response_or_exc, Exception):
            raise self._response_or_exc
        return _FakeResponsesResponse(self._response_or_exc)


class _FakeChatResponse:
    def __init__(self, text: str) -> None:
        self.choices = [_FakeChoice(text)]


class _FakeResponsesResponse:
    def __init__(self, text: str) -> None:
        self.output_text = text


class _FakeChoice:
    def __init__(self, text: str) -> None:
        self.message = _FakeMessage(text)


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = text
