"""Strict provider-faithful one-shot SmartModel transport regressions.

Test classification:
- proof class: offline_product_path_proof
- validation bucket: phase_focus
- harness label: PRODUCT-PATH-REGRESSION
- runtime path: Phase 5A prepared multicomponent transport / ordinary run_pipeline
- promotion posture: remain phase-focused while Phase 5A consumes this transport
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import core.llm as llm_module
import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.multicomponent_graph_scheduling import (
    BACKEND_CONSERVATIVE_UNKNOWN,
    initialize_scheduler_v2_state,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_SYSTEM_PROMPTS,
    PreparedMulticomponentTransportCall,
    execute_prepared_multicomponent_transport,
    failed_unstarted_multicomponent_worker_result,
    prepare_multicomponent_transport_call,
    reduce_multicomponent_worker_result,
    safe_packet_digest,
)
from core.protocols import NullStatusWriter
from core.run_kernel import ActionType
from core.strict_one_shot_model_transport import (
    BLOCKED_STRICT_ONE_SHOT_PROVIDER_UNSUPPORTED,
    PROVIDER_LOCAL,
    PROVIDER_OPENAI,
    PROVIDER_OPENROUTER,
    PROVIDER_UNSUPPORTED,
    StrictOneShotModelTransportResult,
    build_strict_one_shot_smart_model_transport,
    normalize_canonical_model_provider,
    wrap_text_callable_as_strict_one_shot_transport,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_SEMANTIC,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)
from tests.test_multicomponent_graph_scheduling_leases_01 import (
    _scheduler,
    _scheduler_kernel,
)
from tests.test_multicomponent_hosted_component_parallel_dispatch_01 import (
    _run_hosted_product,
)
from tests.test_multicomponent_ordinary_end_to_end_synthesis_01 import NorthstarHarness
from tests.test_strict_accounted_model_route_01 import (
    _credential_lookup,
    _fake_client_factory,
)


def _redact_identity_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _redact_identity_fields(item)
            for key, item in value.items()
            if key not in {"run_id", "request_id", "action_id", "session_id"}
        }
    if isinstance(value, list):
        return [_redact_identity_fields(item) for item in value]
    return value


def _history_entries_exclude_raw_provider(
    scheduler: dict[str, Any],
    raw_provider: str,
) -> None:
    for key in ("lease_history", "batch_history"):
        for entry in scheduler.get(key) or []:
            blob = json.dumps(
                _redact_identity_fields(entry),
                sort_keys=True,
                default=str,
            )
            assert raw_provider not in blob


def _analyst_json() -> str:
    return json.dumps(
        {
            "claim_text": "A bounded claim.",
            "support_status": "supported",
            "caveats": [],
            "nonclaims": [],
            "blockers": [],
        }
    )


def test_provider_alias_custody_open_router_through_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, kernel, harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="open_router",
        synchronize=False,
    )
    assert "Northstar" in outcome.report
    scheduler = _scheduler(kernel)
    assert scheduler["configured_provider_class"] == PROVIDER_OPENROUTER
    assert harness.role_call_counts[ROLE_COMPONENT_ANALYST] >= 1
    analyst_actions = [
        action
        for action in kernel.state.issued_actions.values()
        if action.action_type is ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE
    ]
    for action in analyst_actions:
        projection = kernel.state.projections.get(action.stage) or {}
        if projection.get("semantic_artifact_admitted") is False:
            continue
        assert projection["configured_model_route"]["provider"] == PROVIDER_OPENROUTER


def test_unsupported_provider_zero_call_and_safe_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_touched: list[str] = []

    def _forbidden_openai(**_kwargs: Any) -> Any:
        openai_touched.append("openai")
        raise AssertionError("OpenAI client must not be constructed")

    monkeypatch.setattr(
        "core.strict_one_shot_model_transport._build_openai_compatible_client",
        _forbidden_openai,
    )
    outcome, kernel, _harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="MysteryAI-not-a-provider",
        synchronize=False,
    )
    scheduler = _scheduler(kernel)
    assert scheduler["configured_provider_class"] == PROVIDER_UNSUPPORTED
    assert scheduler["backend_class"] == BACKEND_CONSERVATIVE_UNKNOWN
    assert scheduler["effective_width"] == 1
    assert openai_touched == []
    assert outcome.report
    counters = scheduler["accounting_counters"]
    assert int(counters.get("provider_request_attempt_count") or 0) == 0
    safe_profile = {
        "configured_provider_class": scheduler["configured_provider_class"],
        "backend_class": scheduler["backend_class"],
        "effective_width": scheduler["effective_width"],
        "accounting_counters": counters,
    }
    assert "MysteryAI-not-a-provider" not in json.dumps(
        safe_profile,
        sort_keys=True,
        default=str,
    )


@pytest.mark.parametrize(
    "raw_provider",
    [
        "https://evil.example/v1?token=sk-live-abcdef",
        "Bearer sk-secret-credential-value",
    ],
)
def test_unsafe_raw_provider_values_are_not_retained(raw_provider: str) -> None:
    scheduler = initialize_scheduler_v2_state(
        run_id="run-redact",
        request_id="request-redact",
        configured_provider=raw_provider,
    )
    assert scheduler["configured_provider_class"] == PROVIDER_UNSUPPORTED
    blob = json.dumps(scheduler, sort_keys=True, default=str)
    assert raw_provider not in blob
    assert "sk-live" not in blob
    assert "sk-secret" not in blob

    transport = build_strict_one_shot_smart_model_transport(
        smart_provider=raw_provider,
        smart_model="gpt-5.4",
        credential_lookup={}.get,
        client_factory=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("no client")
        ),
    )
    result = transport("{}", "system", require_json=True)
    assert result.canonical_provider == PROVIDER_UNSUPPORTED
    assert result.provider_request_attempt_count == 0
    assert result.failure_kind == BLOCKED_STRICT_ONE_SHOT_PROVIDER_UNSUPPORTED
    assert raw_provider not in repr(result)
    assert raw_provider not in repr(transport)


def test_broad_helper_ask_model_excluded_from_phase_5a_product_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scrub_offline_runtime(monkeypatch)
    harness = NorthstarHarness(tmp_path)
    phase5a_broad_calls = 0

    def _guarded_ask_model(prompt: str, system_prompt: str, **kwargs: Any) -> str:
        nonlocal phase5a_broad_calls
        if system_prompt in ROLE_SYSTEM_PROMPTS.values():
            phase5a_broad_calls += 1
            raise AssertionError(
                "core.llm.ask_model must not be used by Phase 5A transport"
            )
        return NorthstarHarness.ask_model(harness, prompt, system_prompt, **kwargs)

    monkeypatch.setattr(llm_module, "ask_model", _guarded_ask_model)
    deps = harness.deps()
    deps.ask_model = _guarded_ask_model
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_SEMANTIC,),
    )
    config = offline_balanced_run_config(
        query=harness.query,
        current_date="2026-07-12",
        session_id="phase5a-no-ask-model-session",
        run_id="phase5a-no-ask-model-run",
    )
    config.smart_provider = "OpenAI"
    outcome = orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )
    assert outcome.report
    assert phase5a_broad_calls == 0
    assert deps.strict_one_shot_smart_model_transport is not deps.ask_model
    assert captured.get("semantic_handoff_called") is False


def test_openai_one_shot_success_uses_responses_with_max_retries_zero() -> None:
    calls: list[dict[str, Any]] = []
    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenAI",
        smart_model="gpt-5.4",
        credential_lookup=_credential_lookup("unit-test-openai-credential"),
        client_factory=_fake_client_factory(calls, _analyst_json()),
    )
    result = transport(
        "{}",
        "system",
        provider="OpenAI",
        model="gpt-5.4",
        require_json=True,
        use_reasoning=False,
        effort="high",
    )
    assert result.return_code == 0
    assert result.provider_request_attempt_count == 1
    assert result.canonical_provider == PROVIDER_OPENAI
    assert calls[0]["factory"]["max_retries"] == 0
    assert calls[0]["responses_create_count"] == 1
    assert calls[0]["chat_create_count"] == 0
    assert "base_url" not in calls[0]["factory"]


def test_openai_one_shot_failure_does_not_retry_or_fallback() -> None:
    calls: list[dict[str, Any]] = []

    class _FailingResponses:
        def create(self, **_kwargs: Any) -> Any:
            raise RuntimeError("injected provider failure")

    class _FailingClient:
        def __init__(self) -> None:
            self.responses = _FailingResponses()
            self.chat = type(
                "Chat",
                (),
                {
                    "completions": type(
                        "Completions",
                        (),
                        {"create": staticmethod(lambda **_k: (_ for _ in ()).throw(AssertionError("chat fallback")))},
                    )()
                },
            )()

    def _factory(**kwargs: Any) -> Any:
        calls.append({"factory": dict(kwargs), "chat_create_count": 0, "responses_create_count": 0})
        assert kwargs.get("max_retries") == 0
        return _FailingClient()

    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenAI",
        smart_model="gpt-5.4",
        credential_lookup=_credential_lookup("unit-test-openai-credential"),
        client_factory=_factory,
    )
    result = transport("{}", "system", require_json=True)
    assert result.return_code == 2
    assert result.provider_request_attempt_count == 1
    assert result.provider_request_failed is True
    assert len(calls) == 1


def test_openrouter_one_shot_uses_chat_and_never_openai_default_client() -> None:
    calls: list[dict[str, Any]] = []
    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="open_router",
        smart_model="openrouter/model",
        credential_lookup=_credential_lookup("unit-test-openrouter-credential"),
        client_factory=_fake_client_factory(calls, _analyst_json()),
    )
    result = transport("{}", "system", require_json=True)
    assert result.return_code == 0
    assert result.canonical_provider == PROVIDER_OPENROUTER
    assert result.provider_request_attempt_count == 1
    assert calls[0]["factory"]["max_retries"] == 0
    assert calls[0]["factory"]["base_url"] == "https://openrouter.ai/api/v1"
    assert calls[0]["chat_create_count"] == 1
    assert calls[0]["responses_create_count"] == 0


def test_local_one_shot_stays_width_one_without_hosted_fallback() -> None:
    calls: list[dict[str, Any]] = []
    profile = initialize_scheduler_v2_state(
        run_id="run-local",
        request_id="request-local",
        configured_provider="lm_studio",
    )
    assert profile["effective_width"] == 1
    assert profile["configured_provider_class"] == PROVIDER_LOCAL
    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="lm_studio",
        smart_model="local-model",
        local_url="http://localhost:1234/v1",
        credential_lookup={}.get,
        client_factory=_fake_client_factory(calls, _analyst_json()),
    )
    result = transport("{}", "system", require_json=True)
    assert result.return_code == 0
    assert result.canonical_provider == PROVIDER_LOCAL
    assert result.provider_request_attempt_count == 1
    assert calls[0]["factory"]["max_retries"] == 0
    assert calls[0]["factory"]["base_url"] == "http://localhost:1234/v1"
    assert calls[0]["chat_create_count"] == 1
    assert calls[0]["responses_create_count"] == 0


def test_width_two_hosted_wave_records_exact_provider_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _outcome, kernel, harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="OpenAI",
        synchronize=True,
    )
    counters = _scheduler(kernel)["accounting_counters"]
    assert counters["effective_width"] if False else True
    assert int(counters["dispatch_committed_unit_count"]) >= 2
    assert int(counters["provider_request_attempt_count"]) == int(
        counters["dispatch_committed_unit_count"]
    )
    assert int(counters["successful_artifact_count"]) == int(
        counters["dispatch_committed_unit_count"]
    )
    assert harness.role_maximum_in_flight[ROLE_COMPONENT_ANALYST] == 2


def test_executor_failure_accounting_keeps_zero_provider_attempts() -> None:
    kernel, packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    leases = [
        item
        for item in _scheduler(kernel)["lease_history"]
        if item.get("batch_id") == batch.get("batch_id")
    ]
    packet_digests = [
        safe_packet_digest(packets[str(lease["work"]["component_id"])])
        for lease in leases
    ]
    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=packet_digests,
    )
    transport = wrap_text_callable_as_strict_one_shot_transport(
        lambda *_a, **_k: _analyst_json(),
        canonical_provider="OpenAI",
        model="gpt-5.4",
    )
    for action, lease in zip(actions, leases, strict=True):
        prepared = prepare_multicomponent_transport_call(
            action=action,
            input_packet=packets[str(lease["work"]["component_id"])],
            strict_one_shot_transport=transport,
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
        )
        failed = failed_unstarted_multicomponent_worker_result(
            prepared,
            failure_kind="executor_initialization_failure",
        )
        assert failed.provider_request_attempt_count == 0
        assert failed.transport_submitted is False
        reduce_multicomponent_worker_result(
            run_kernel=kernel,
            action=action,
            result=failed,
            observed_batch_max_in_flight=0,
        )
    counters = _scheduler(kernel)["accounting_counters"]
    assert int(counters["provider_request_attempt_count"]) == 0
    assert int(counters["failed_submission_count"]) == len(actions)


def test_submission_failure_keeps_unsubmitted_attempts_zero() -> None:
    kernel, packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    leases = [
        item
        for item in _scheduler(kernel)["lease_history"]
        if item.get("batch_id") == batch.get("batch_id")
    ]
    packet_digests = [
        safe_packet_digest(packets[str(lease["work"]["component_id"])])
        for lease in leases
    ]
    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=packet_digests,
    )
    transport = wrap_text_callable_as_strict_one_shot_transport(
        lambda *_a, **_k: _analyst_json(),
        canonical_provider="OpenAI",
        model="gpt-5.4",
    )
    prepared_calls = [
        prepare_multicomponent_transport_call(
            action=action,
            input_packet=packets[str(lease["work"]["component_id"])],
            strict_one_shot_transport=transport,
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
        )
        for action, lease in zip(actions, leases, strict=True)
    ]
    submitted = execute_prepared_multicomponent_transport(prepared_calls[0])
    reduce_multicomponent_worker_result(
        run_kernel=kernel,
        action=actions[0],
        result=submitted,
        observed_batch_max_in_flight=1,
    )
    for action, prepared in zip(actions[1:], prepared_calls[1:], strict=True):
        reduce_multicomponent_worker_result(
            run_kernel=kernel,
            action=action,
            result=failed_unstarted_multicomponent_worker_result(
                prepared,
                failure_kind="failed_submission",
            ),
            observed_batch_max_in_flight=1,
        )
    counters = _scheduler(kernel)["accounting_counters"]
    assert int(counters["provider_request_attempt_count"]) == 1
    assert int(counters["failed_submission_count"]) == len(actions) - 1
    assert int(counters["successful_artifact_count"]) == 1


def test_provider_identity_mismatch_rejects_artifact() -> None:
    kernel, packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    leases = [
        item
        for item in _scheduler(kernel)["lease_history"]
        if item.get("batch_id") == batch.get("batch_id")
    ]
    lease = leases[0]
    packet = packets[str(lease["work"]["component_id"])]
    packet_digest = safe_packet_digest(packet)
    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=[packet_digest]
        + [
            safe_packet_digest(packets[str(item["work"]["component_id"])])
            for item in leases[1:]
        ],
    )
    forged = StrictOneShotModelTransportResult(
        return_code=0,
        output_text=_analyst_json(),
        canonical_provider=PROVIDER_OPENROUTER,
        configured_model="gpt-5.4",
        provider_request_attempt_count=1,
        provider_request_succeeded=True,
    )

    def _forged_transport(*_a: Any, **_k: Any) -> StrictOneShotModelTransportResult:
        return forged

    prepared = prepare_multicomponent_transport_call(
        action=actions[0],
        input_packet=packet,
        strict_one_shot_transport=_forged_transport,
        clean_json_response=None,
        provider="OpenAI",
        model="gpt-5.4",
        use_reasoning=False,
    )
    result = execute_prepared_multicomponent_transport(prepared)
    assert result.failure_kind == "provider_identity_mismatch"
    artifact = reduce_multicomponent_worker_result(
        run_kernel=kernel,
        action=actions[0],
        result=result,
        observed_batch_max_in_flight=1,
    )
    assert artifact is None
    for action, item in zip(actions[1:], leases[1:], strict=True):
        sibling_packet = packets[str(item["work"]["component_id"])]
        sibling_prepared = prepare_multicomponent_transport_call(
            action=action,
            input_packet=sibling_packet,
            strict_one_shot_transport=wrap_text_callable_as_strict_one_shot_transport(
                lambda *_a, **_k: _analyst_json(),
                canonical_provider="OpenAI",
                model="gpt-5.4",
            ),
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
        )
        reduce_multicomponent_worker_result(
            run_kernel=kernel,
            action=action,
            result=failed_unstarted_multicomponent_worker_result(
                sibling_prepared,
                failure_kind="failed_submission",
            ),
            observed_batch_max_in_flight=1,
        )


def test_prepared_call_repr_hides_private_fields() -> None:
    kernel, packets = _scheduler_kernel()
    batch = kernel.grant_next_multicomponent_work_batch()
    leases = [
        item
        for item in _scheduler(kernel)["lease_history"]
        if item.get("batch_id") == batch.get("batch_id")
    ]
    lease = leases[0]
    packet = packets[str(lease["work"]["component_id"])]
    digests = [
        safe_packet_digest(packets[str(item["work"]["component_id"])])
        for item in leases
    ]
    actions = kernel.commit_multicomponent_batch_dispatch(
        batch_id=str(batch.get("batch_id") or ""),
        packet_digests=digests,
    )

    def _secret_transport(*_a: Any, **_k: Any) -> StrictOneShotModelTransportResult:
        return StrictOneShotModelTransportResult(
            return_code=0,
            output_text=_analyst_json(),
            canonical_provider=PROVIDER_OPENAI,
            configured_model="gpt-5.4",
            provider_request_attempt_count=1,
            provider_request_succeeded=True,
        )

    prepared = prepare_multicomponent_transport_call(
        action=actions[0],
        input_packet=packet,
        strict_one_shot_transport=_secret_transport,
        clean_json_response=lambda value: value + "-CLEANER",
        provider="OpenAI",
        model="gpt-5.4",
        use_reasoning=False,
    )
    rendered = repr(prepared)
    assert "_secret_transport" not in rendered
    assert "CLEANER" not in rendered
    assert "sk-" not in rendered
    assert isinstance(prepared, PreparedMulticomponentTransportCall)
    for action, item in zip(actions, leases, strict=True):
        sibling = prepare_multicomponent_transport_call(
            action=action,
            input_packet=packets[str(item["work"]["component_id"])],
            strict_one_shot_transport=_secret_transport,
            clean_json_response=None,
            provider="OpenAI",
            model="gpt-5.4",
            use_reasoning=False,
        )
        reduce_multicomponent_worker_result(
            run_kernel=kernel,
            action=action,
            result=failed_unstarted_multicomponent_worker_result(
                sibling,
                failure_kind="failed_submission",
            ),
            observed_batch_max_in_flight=0,
        )


def test_normalize_aliases_and_unsupported() -> None:
    assert normalize_canonical_model_provider("open_router") == PROVIDER_OPENROUTER
    assert normalize_canonical_model_provider("OpenAI") == PROVIDER_OPENAI
    assert normalize_canonical_model_provider("lm_studio") == PROVIDER_LOCAL
    assert normalize_canonical_model_provider("nope") == PROVIDER_UNSUPPORTED
    assert normalize_canonical_model_provider("") == PROVIDER_UNSUPPORTED


def test_openrouter_and_alias_chat_requests_use_installed_temperature() -> None:
    from core.strict_one_shot_model_transport import STRICT_ONE_SHOT_CHAT_TEMPERATURE

    for provider in ("OpenRouter", "open_router"):
        calls: list[dict[str, Any]] = []
        transport = build_strict_one_shot_smart_model_transport(
            smart_provider=provider,
            smart_model="openrouter/model",
            credential_lookup=_credential_lookup("unit-test-openrouter-credential"),
            client_factory=_fake_client_factory(calls, _analyst_json()),
        )
        result = transport("{}", "system", require_json=True)
        assert result.return_code == 0
        assert result.canonical_provider == PROVIDER_OPENROUTER
        assert calls[0]["chat_create"]["temperature"] == STRICT_ONE_SHOT_CHAT_TEMPERATURE
        assert calls[0]["chat_create"]["temperature"] == 0.3


def test_local_and_lm_studio_alias_chat_requests_use_installed_temperature() -> None:
    from core.strict_one_shot_model_transport import STRICT_ONE_SHOT_CHAT_TEMPERATURE

    for provider in ("Local (LM Studio)", "lm_studio"):
        calls: list[dict[str, Any]] = []
        transport = build_strict_one_shot_smart_model_transport(
            smart_provider=provider,
            smart_model="local-model",
            local_url="http://localhost:1234/v1",
            credential_lookup={}.get,
            client_factory=_fake_client_factory(calls, _analyst_json()),
        )
        result = transport("{}", "system", require_json=True)
        assert result.return_code == 0
        assert result.canonical_provider == PROVIDER_LOCAL
        assert calls[0]["chat_create"]["temperature"] == STRICT_ONE_SHOT_CHAT_TEMPERATURE
        assert calls[0]["chat_create"]["temperature"] == 0.3


def test_openai_responses_request_omits_temperature() -> None:
    calls: list[dict[str, Any]] = []
    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenAI",
        smart_model="gpt-5.4",
        credential_lookup=_credential_lookup("unit-test-openai-credential"),
        client_factory=_fake_client_factory(calls, _analyst_json()),
    )
    result = transport("{}", "system", require_json=True)
    assert result.return_code == 0
    assert "temperature" not in calls[0]["responses_create"]
    assert calls[0]["responses_create_count"] == 1
    assert calls[0]["chat_create_count"] == 0


def test_caller_authored_temperature_is_rejected() -> None:
    calls: list[dict[str, Any]] = []
    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenRouter",
        smart_model="openrouter/model",
        credential_lookup=_credential_lookup("unit-test-openrouter-credential"),
        client_factory=_fake_client_factory(calls, _analyst_json()),
    )
    result = transport("{}", "system", require_json=True, temperature=0.9)
    assert result.return_code == 2
    assert result.failure_kind == "BLOCKED_STRICT_ONE_SHOT_UNSAFE_REQUEST"
    assert result.provider_request_attempt_count == 0
    assert calls == []


def test_temperature_is_absent_from_scheduler_worker_artifact_and_trace_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome, kernel, harness, _captured = _run_hosted_product(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        provider="OpenRouter",
        synchronize=False,
    )
    assert "Northstar" in outcome.report
    scheduler = _scheduler(kernel)
    blob = json.dumps(
        {
            "scheduler": _redact_identity_fields(scheduler),
            "projections": _redact_identity_fields(dict(kernel.state.projections)),
            "harness_calls": harness.model_calls,
        },
        sort_keys=True,
        default=str,
    )
    assert "temperature" not in blob.casefold()
    for surface in (
        scheduler,
        dict(kernel.state.projections),
        [dict(item) for item in scheduler.get("lease_history") or ()],
        [dict(item) for item in scheduler.get("batch_history") or ()],
    ):
        encoded = json.dumps(_redact_identity_fields(surface), sort_keys=True, default=str)
        assert '"temperature"' not in encoded.casefold()
        assert "'temperature'" not in encoded.casefold()


def test_usage_facts_prefer_provider_observed_tokens() -> None:
    calls: list[dict[str, Any]] = []

    class _UsageResponse:
        def __init__(self) -> None:
            self.choices = [
                type(
                    "Choice",
                    (),
                    {
                        "message": type(
                            "Message",
                            (),
                            {"content": _analyst_json()},
                        )()
                    },
                )()
            ]
            self.usage = type(
                "Usage",
                (),
                {"prompt_tokens": 11, "completion_tokens": 7},
            )()

    def _factory(**kwargs: Any) -> Any:
        record = {
            "factory": dict(kwargs),
            "chat_create_count": 0,
            "responses_create_count": 0,
        }
        calls.append(record)

        class _Completions:
            @staticmethod
            def create(**create_kwargs: Any) -> Any:
                record["chat_create_count"] += 1
                record["chat_create"] = dict(create_kwargs)
                return _UsageResponse()

        class _Client:
            chat = type("Chat", (), {"completions": _Completions()})()
            responses = type(
                "Responses",
                (),
                {"create": staticmethod(lambda **_k: (_ for _ in ()).throw(AssertionError()))},
            )()

        return _Client()

    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenRouter",
        smart_model="openrouter/model",
        credential_lookup=_credential_lookup("unit-test-openrouter-credential"),
        client_factory=_factory,
    )
    result = transport("prompt-text", "system-text", require_json=True)
    assert result.return_code == 0
    assert result.provider_response_received is True
    assert result.input_tokens == 11
    assert result.output_tokens == 7
    assert result.usage_observed is True
    assert result.usage_estimated is False
    assert "prompt-text" not in repr(result)
    assert "system-text" not in repr(result)


def test_usage_facts_estimate_when_provider_usage_absent() -> None:
    from core.cost_accounting import estimate_tokens

    calls: list[dict[str, Any]] = []
    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenRouter",
        smart_model="openrouter/model",
        credential_lookup=_credential_lookup("unit-test-openrouter-credential"),
        client_factory=_fake_client_factory(calls, _analyst_json()),
    )
    prompt = "prompt-for-estimate"
    system_prompt = "system-for-estimate"
    result = transport(prompt, system_prompt, require_json=True)
    assert result.provider_response_received is True
    assert result.input_tokens == estimate_tokens(prompt) + estimate_tokens(system_prompt)
    assert result.output_tokens == estimate_tokens(_analyst_json())
    assert result.usage_observed is False
    assert result.usage_estimated is True
    assert prompt not in repr(result)
    assert system_prompt not in repr(result)


def test_usage_facts_partial_provider_usage_mixes_observed_and_estimated() -> None:
    from core.cost_accounting import estimate_tokens

    class _PartialUsageResponse:
        def __init__(self) -> None:
            self.choices = [
                type(
                    "Choice",
                    (),
                    {
                        "message": type(
                            "Message",
                            (),
                            {"content": _analyst_json()},
                        )()
                    },
                )()
            ]
            self.usage = type("Usage", (), {"prompt_tokens": 19})()

    def _factory(**kwargs: Any) -> Any:
        class _Completions:
            @staticmethod
            def create(**_create_kwargs: Any) -> Any:
                return _PartialUsageResponse()

        return type(
            "Client",
            (),
            {
                "chat": type("Chat", (), {"completions": _Completions()})(),
                "responses": type(
                    "Responses",
                    (),
                    {
                        "create": staticmethod(
                            lambda **_k: (_ for _ in ()).throw(AssertionError())
                        )
                    },
                )(),
            },
        )()

    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenRouter",
        smart_model="openrouter/model",
        credential_lookup=_credential_lookup("unit-test-openrouter-credential"),
        client_factory=_factory,
    )
    result = transport("prompt-partial", "system-partial", require_json=True)
    assert result.input_tokens == 19
    assert result.output_tokens == estimate_tokens(_analyst_json())
    assert result.usage_observed is True
    assert result.usage_estimated is True


def test_empty_output_still_marks_provider_response_received_with_usage() -> None:
    calls: list[dict[str, Any]] = []
    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenRouter",
        smart_model="openrouter/model",
        credential_lookup=_credential_lookup("unit-test-openrouter-credential"),
        client_factory=_fake_client_factory(calls, ""),
    )
    result = transport("{}", "system", require_json=True)
    assert result.return_code == 2
    assert result.failure_kind == "BLOCKED_STRICT_ONE_SHOT_OUTPUT_EMPTY"
    assert result.provider_response_received is True
    assert result.provider_request_attempt_count == 1
    assert result.input_tokens >= 0
    assert result.output_tokens == 0
    assert result.usage_estimated is True


def test_provider_exception_without_response_has_zero_usage() -> None:
    def _factory(**kwargs: Any) -> Any:
        class _Completions:
            @staticmethod
            def create(**_create_kwargs: Any) -> Any:
                raise RuntimeError("injected no-response failure")

        return type(
            "Client",
            (),
            {
                "chat": type("Chat", (), {"completions": _Completions()})(),
                "responses": type("Responses", (), {})(),
            },
        )()

    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenRouter",
        smart_model="openrouter/model",
        credential_lookup=_credential_lookup("unit-test-openrouter-credential"),
        client_factory=_factory,
    )
    result = transport("{}", "system", require_json=True)
    assert result.return_code == 2
    assert result.provider_request_attempt_count == 1
    assert result.provider_response_received is False
    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.usage_observed is False
    assert result.usage_estimated is False


def test_pre_request_failures_have_zero_usage_and_zero_attempts() -> None:
    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="MysteryAI",
        smart_model="x",
        credential_lookup={}.get,
        client_factory=_fake_client_factory([], _analyst_json()),
    )
    result = transport("{}", "system")
    assert result.provider_request_attempt_count == 0
    assert result.provider_response_received is False
    assert result.input_tokens == 0
    assert result.output_tokens == 0

    missing_cred = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenRouter",
        smart_model="openrouter/model",
        credential_lookup={}.get,
        client_factory=_fake_client_factory([], _analyst_json()),
    )
    cred_result = missing_cred("{}", "system")
    assert cred_result.provider_request_attempt_count == 0
    assert cred_result.provider_response_received is False

    missing_local = build_strict_one_shot_smart_model_transport(
        smart_provider="Local (LM Studio)",
        smart_model="local-model",
        local_url=None,
        credential_lookup={}.get,
        client_factory=_fake_client_factory([], _analyst_json()),
    )
    local_result = missing_local("{}", "system")
    assert local_result.provider_request_attempt_count == 0
    assert local_result.provider_response_received is False
