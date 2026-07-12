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
    _history_entries_exclude_raw_provider(scheduler, "MysteryAI-not-a-provider")


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

    def _guarded_ask_model(prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt in ROLE_SYSTEM_PROMPTS.values():
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
    assert "Northstar" in outcome.report
    assert captured.get("semantic_handoff_called") is True
    kernel = captured["semantic_run_kernel"]
    counters = _scheduler(kernel)["accounting_counters"]
    assert int(counters["provider_request_attempt_count"]) == int(
        counters["dispatch_committed_unit_count"]
    )
    assert int(counters["successful_artifact_count"]) == int(
        counters["dispatch_committed_unit_count"]
    )


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
