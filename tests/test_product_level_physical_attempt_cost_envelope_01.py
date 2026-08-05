"""PRODUCT-PATH-REGRESSION: physical attempt/cost envelope and shared CLI.

Mode: REPAIR.
Test class: phase_focus / offline_product_path_proof.
Promotion posture: remain phase_focus until the bounded public pulse is run.
No test in this file is integration- or secrets-backed.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

import core.cap_enforcement as cap_module
import core.llm as llm
import core.pipeline_orchestrator as orchestrator
import core.search_providers as search_providers
import proplex.__main__ as compatibility_cli
from core.acquisition_adapters import AcquisitionTransports, dispatch_acquisition
from core.acquisition_contracts import (
    AcquisitionExecutionStatus,
    AcquisitionRequest,
)
from core.cap_enforcement import (
    DEFAULT_EXTERNAL_TIMEOUT_SECONDS,
    AttemptLifecycle,
    ExternalAttemptSpec,
    ExternalCallFamily,
    RoutePricing,
    RunCapEnvelope,
    RunCapExceeded,
    RunCapPolicy,
    TokenUsage,
    conservative_text_token_upper_bound,
    embedding_usage_bound,
    mark_cap_aware,
    model_usage_bound,
)
from core.cost_accounting import estimate_tokens
from core.routing import (
    AcquisitionCapability,
    ProviderCapabilityRequest,
    route_provider_capability,
)
from core.run_authority_search_judgment_runtime import (
    execute_run_authority_search_judgment_action,
)
from core.run_config import RunConfig, RunDeps
from core.strict_one_shot_model_transport import (
    build_strict_one_shot_smart_model_transport,
)
from tests.helpers.offline_ordinary_pipeline import PostRetirementOrdinaryPipelineHarness
from tests.test_runauthority_iterative_search_judgment_ag92b import (
    _input as search_judgment_input,
)
from tests.test_runauthority_iterative_search_judgment_ag92b import (
    _kernel_with_official_contract,
)


def _pricing(
    *,
    flat: str = "0.01",
    input_rate: str = "1",
    output_rate: str = "2",
    reasoning_rate: str = "3",
    embedding_rate: str = "1",
) -> RoutePricing:
    return RoutePricing(
        pricing_key="fixture.route",
        input_per_million_usd=Decimal(input_rate),
        cached_input_per_million_usd=Decimal(input_rate),
        output_per_million_usd=Decimal(output_rate),
        reasoning_per_million_usd=Decimal(reasoning_rate),
        embedding_per_million_usd=Decimal(embedding_rate),
        flat_attempt_usd=Decimal(flat),
    )


def _envelope(
    *,
    deadline_seconds: float = 30.0,
    max_total_attempts: int = 64,
    model_attempts: int = 32,
    search_attempts: int = 32,
    max_retries: int = 0,
    max_fallbacks: int = 0,
    max_per_attempt_usd: str = "25",
    max_run_usd: str = "50",
) -> RunCapEnvelope:
    all_usage = TokenUsage(
        input_tokens=1_000_000,
        cached_input_tokens=1_000_000,
        output_tokens=1_000_000,
        reasoning_tokens=1_000_000,
        embedding_tokens=1_000_000,
    )
    return RunCapEnvelope(
        profile_name="fixture-v1",
        profile_digest="0123456789abcdef",
        pricing_version="fixture-pricing-v1",
        deadline_seconds=deadline_seconds,
        max_total_attempts=max_total_attempts,
        max_attempts_by_family={
            ExternalCallFamily.MODEL: model_attempts,
            ExternalCallFamily.EMBEDDING: 32,
            ExternalCallFamily.SEARCH: search_attempts,
            ExternalCallFamily.READ: 32,
        },
        max_tokens=all_usage,
        max_tokens_by_family={family: all_usage for family in ExternalCallFamily},
        max_per_attempt_usd=Decimal(max_per_attempt_usd),
        max_run_usd=Decimal(max_run_usd),
        max_retries=max_retries,
        max_fallbacks=max_fallbacks,
    )


def _fixture_route_pricing() -> dict[tuple[ExternalCallFamily, str, str], RoutePricing]:
    """Explicit fictional prices for offline fixture policies only."""

    model_fast = RoutePricing(
        pricing_key="fixture.openai.gpt-5.4-mini",
        input_per_million_usd=Decimal("1"),
        cached_input_per_million_usd=Decimal("1"),
        output_per_million_usd=Decimal("2"),
        reasoning_per_million_usd=Decimal("3"),
    )
    model_smart = RoutePricing(
        pricing_key="fixture.openai.gpt-5.4",
        input_per_million_usd=Decimal("1"),
        cached_input_per_million_usd=Decimal("1"),
        output_per_million_usd=Decimal("2"),
        reasoning_per_million_usd=Decimal("3"),
    )
    embedding = RoutePricing(
        pricing_key="fixture.openai.text-embedding-3-small",
        embedding_per_million_usd=Decimal("1"),
    )
    search = RoutePricing(
        pricing_key="fixture.search",
        flat_attempt_usd=Decimal("0.01"),
    )
    read = RoutePricing(
        pricing_key="fixture.read",
        flat_attempt_usd=Decimal("0.01"),
    )
    return {
        (ExternalCallFamily.MODEL, "openai", "gpt-5.4-mini"): model_fast,
        (ExternalCallFamily.MODEL, "openai", "gpt-5.4"): model_smart,
        (ExternalCallFamily.EMBEDDING, "openai", "text-embedding-3-small"): embedding,
        (ExternalCallFamily.SEARCH, "tavily", "search"): search,
        (ExternalCallFamily.SEARCH, "linkup", "search"): search,
        (ExternalCallFamily.SEARCH, "exa", "search"): search,
        (ExternalCallFamily.SEARCH, "brave", "search"): search,
        (ExternalCallFamily.SEARCH, "serper", "search"): search,
        (ExternalCallFamily.SEARCH, "fixture", "route"): search,
        (ExternalCallFamily.SEARCH, "fixture", "search"): search,
        (ExternalCallFamily.READ, "linkup", "fetch"): read,
        (ExternalCallFamily.READ, "tavily", "extract"): read,
        (ExternalCallFamily.READ, "fixture", "route"): read,
        (ExternalCallFamily.READ, "fixture", "fetch"): read,
        (ExternalCallFamily.MODEL, "fixture", "route"): model_fast,
        (ExternalCallFamily.EMBEDDING, "fixture", "route"): embedding,
    }


def _policy(**envelope_kwargs: Any) -> RunCapPolicy:
    route_pricing = envelope_kwargs.pop("route_pricing", None)
    activate = bool(envelope_kwargs.pop("activate", True))
    policy = RunCapPolicy(
        max_retries=int(envelope_kwargs.get("max_retries", 0)),
        envelope=_envelope(**envelope_kwargs),
        route_pricing=route_pricing if route_pricing is not None else _fixture_route_pricing(),
    )
    if activate:
        policy.activate(run_id="run-fixture", request_id="request-fixture")
    return policy


def _spec(
    *,
    family: ExternalCallFamily = ExternalCallFamily.SEARCH,
    logical_call_id: str = "logical:1",
    usage: TokenUsage | None = None,
    retry: bool = False,
    fallback: bool = False,
    timeout: float = 10.0,
    pricing: RoutePricing | None = None,
) -> ExternalAttemptSpec:
    return ExternalAttemptSpec(
        family=family,
        provider="fixture",
        route="route",
        operation="dispatch",
        logical_call_id=logical_call_id,
        max_usage=usage or TokenUsage(),
        pricing=pricing or _pricing(),
        requested_timeout_seconds=timeout,
        is_retry=retry,
        is_fallback=fallback,
    )


def test_explicit_policies_are_independent_and_reject_unknown_routes() -> None:
    first = _policy(activate=False)
    second = _policy(activate=False)

    assert first is not second
    assert first.envelope.profile_digest == second.envelope.profile_digest
    assert first.envelope.max_total_attempts == second.envelope.max_total_attempts
    first.activate(run_id="policy-run-one", request_id="policy-request-one")
    assert first.physical_snapshot()["activated"] is True
    assert second.physical_snapshot()["activated"] is False
    assert second.physical_snapshot()["logical_calls"] == 0

    with pytest.raises(RunCapExceeded) as exc:
        first.resolve_route_pricing(ExternalCallFamily.MODEL, "openai", "unpriced-model")
    assert exc.value.reason_code == "unsupported_route_pricing"

    with pytest.raises(ValueError, match="explicit immutable route_pricing map"):
        RunCapPolicy(envelope=_envelope(), route_pricing=None)


def test_conservative_text_bound_dominates_common_token_units() -> None:
    samples = [
        "",
        "ASCII words and punctuation.",
        "math.isclose(rel_tol=1e-09, abs_tol=0.0)",
        "Unicode: café, 東京, and 🐦.",
    ]
    for sample in samples:
        bound = conservative_text_token_upper_bound(sample)
        assert bound >= len(sample)
        assert bound >= len(sample.encode("utf-8")) // 4
        assert bound >= estimate_tokens(sample)


def test_thread_safe_reservations_have_unique_physical_ordinals() -> None:
    policy = _policy(search_attempts=24, max_total_attempts=24)

    def dispatch_once(_index: int) -> str:
        reservation = policy.reserve_attempt(_spec(logical_call_id="search:shared"))
        reservation.mark_dispatched()
        reservation.settle_observed(TokenUsage())
        return reservation.attempt_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        attempt_ids = list(pool.map(dispatch_once, range(24)))

    assert len(set(attempt_ids)) == 24
    snapshot = policy.physical_snapshot()
    assert snapshot["physical_attempts"] == 24
    assert snapshot["physical_attempts_by_family"]["search"] == 24
    assert snapshot["active_attempts"] == 0
    assert sorted(attempt["physical_ordinal"] for attempt in snapshot["attempts"]) == list(range(1, 25))

    duplicate_policy = _policy()
    duplicate_use = duplicate_policy.reserve_attempt(_spec(logical_call_id="search:duplicate-use"))
    duplicate_use.mark_dispatched()
    with pytest.raises(RuntimeError, match="not dispatchable"):
        duplicate_use.mark_dispatched()
    duplicate_use.settle_observed(TokenUsage())


def test_observed_and_ambiguous_settlement_use_distinct_cost_postures() -> None:
    policy = _policy()
    maximum = TokenUsage(
        input_tokens=1_000,
        output_tokens=500,
        reasoning_tokens=250,
    )
    observed = policy.reserve_attempt(
        _spec(
            family=ExternalCallFamily.MODEL,
            logical_call_id="model:observed",
            usage=maximum,
        )
    )
    observed.mark_dispatched()
    observed.settle_observed(
        TokenUsage(
            input_tokens=100,
            cached_input_tokens=25,
            output_tokens=20,
            reasoning_tokens=10,
        )
    )
    ambiguous = policy.reserve_attempt(
        _spec(
            family=ExternalCallFamily.MODEL,
            logical_call_id="model:ambiguous",
            usage=maximum,
        )
    )
    ambiguous.mark_dispatched()
    ambiguous.settle_observed(None)

    snapshot = policy.physical_snapshot()
    assert snapshot["lifecycle_counts"]["settled_observed"] == 1
    assert snapshot["lifecycle_counts"]["settled_conservative"] == 1
    assert snapshot["observed_tokens"]["cached_input_tokens"] == 25
    assert snapshot["observed_tokens"]["reasoning_tokens"] == 10
    assert snapshot["conservative_cost_usd"] > 0
    assert snapshot["committed_cost_usd"] < snapshot["reserved_cost_usd"]

    exceeded_policy = _policy()
    exceeded = exceeded_policy.reserve_attempt(
        _spec(
            family=ExternalCallFamily.MODEL,
            logical_call_id="model:observed-overflow",
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        )
    )
    exceeded.mark_dispatched()
    with pytest.raises(RunCapExceeded) as exceeded_exc:
        exceeded.settle_observed(TokenUsage(input_tokens=11, output_tokens=5))
    assert exceeded_exc.value.reason_code == "observed_usage_exceeded_reservation"
    exceeded_snapshot = exceeded_policy.physical_snapshot()
    assert exceeded_snapshot["lifecycle_counts"]["settled_conservative"] == 1
    assert exceeded_snapshot["active_attempts"] == 0


def test_attempt_retry_fallback_token_cost_and_deadline_denials_are_predispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt_policy = _policy(search_attempts=2, max_total_attempts=2)
    first = attempt_policy.reserve_attempt(_spec())
    first.mark_dispatched()
    first.settle_observed(TokenUsage())
    assert attempt_policy.physical_snapshot()["physical_attempts"] == 1
    second = attempt_policy.reserve_attempt(_spec(logical_call_id="logical:2"))
    second.mark_dispatched()
    second.settle_observed(TokenUsage())
    assert attempt_policy.physical_snapshot()["physical_attempts"] == 2
    with pytest.raises(RunCapExceeded) as attempt_exc:
        attempt_policy.reserve_attempt(_spec(logical_call_id="logical:3"))
    assert attempt_exc.value.reason_code == "total_attempt_cap"
    assert attempt_policy.physical_snapshot()["physical_attempts"] == 2

    retry_policy = _policy()
    with pytest.raises(RunCapExceeded) as retry_exc:
        retry_policy.reserve_attempt(_spec(retry=True))
    assert retry_exc.value.reason_code == "retry_cap"
    with pytest.raises(RunCapExceeded) as fallback_exc:
        retry_policy.reserve_attempt(_spec(logical_call_id="logical:fallback", fallback=True))
    assert fallback_exc.value.reason_code == "fallback_cap"

    token_policy = _policy()
    huge = TokenUsage(input_tokens=1_000_001)
    with pytest.raises(RunCapExceeded) as token_exc:
        token_policy.reserve_attempt(
            _spec(
                family=ExternalCallFamily.MODEL,
                usage=huge,
            )
        )
    assert token_exc.value.reason_code == "run_token_cap"

    cost_policy = _policy(max_run_usd="0.005")
    with pytest.raises(RunCapExceeded) as cost_exc:
        cost_policy.reserve_attempt(_spec())
    assert cost_exc.value.reason_code == "run_cost_cap"

    per_attempt_policy = _policy(max_per_attempt_usd="0.005")
    with pytest.raises(RunCapExceeded) as per_attempt_exc:
        per_attempt_policy.reserve_attempt(_spec())
    assert per_attempt_exc.value.reason_code == "per_attempt_cost_cap"

    clock = [100.0]
    monkeypatch.setattr(cap_module.time, "monotonic", lambda: clock[0])
    deadline_policy = _policy(deadline_seconds=5.0, activate=False)
    deadline_policy.activate(run_id="deadline-run", request_id="deadline-request")
    clock[0] = 103.0
    clipped = deadline_policy.reserve_attempt(_spec(timeout=30.0))
    assert 1.99 <= clipped.timeout_seconds <= 2.0
    clipped.cancel_pre_dispatch()
    clock[0] = 106.0
    with pytest.raises(RunCapExceeded) as deadline_exc:
        deadline_policy.reserve_attempt(_spec(logical_call_id="deadline:late"))
    assert deadline_exc.value.reason_code == "deadline_exhausted"
    assert deadline_policy.physical_snapshot()["physical_attempts"] == 0


def test_model_transport_reserves_once_disables_sdk_retry_and_settles_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = _policy()
    calls: list[dict[str, Any]] = []
    options: list[dict[str, Any]] = []

    class Chat:
        def create(self, **kwargs: Any) -> Any:
            snapshot = policy.physical_snapshot()
            assert snapshot["lifecycle_counts"]["dispatched"] == 1
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="bounded answer"))],
                usage=SimpleNamespace(
                    prompt_tokens=20,
                    completion_tokens=5,
                    prompt_tokens_details=SimpleNamespace(cached_tokens=3),
                    completion_tokens_details=SimpleNamespace(reasoning_tokens=2),
                ),
            )

    class Client:
        chat = SimpleNamespace(completions=Chat())

        def with_options(self, **kwargs: Any) -> Client:
            options.append(kwargs)
            return self

    monkeypatch.setattr(llm, "get_openai_client", lambda: Client())
    result = llm.ask_model(
        "question",
        "system",
        provider="OpenAI",
        model="gpt-5.4-mini",
        cap_policy=policy,
        logical_call_id="model:test",
    )

    assert result == "bounded answer"
    assert len(calls) == 1
    assert calls[0]["max_completion_tokens"] > 0
    assert options[0]["max_retries"] == 0
    assert 0 < options[0]["timeout"] <= 30
    snapshot = policy.physical_snapshot()
    assert snapshot["physical_attempts_by_family"]["model"] == 1
    assert snapshot["lifecycle_counts"]["settled_observed"] == 1
    assert snapshot["observed_tokens"]["cached_input_tokens"] == 3
    assert snapshot["observed_tokens"]["reasoning_tokens"] == 2


def test_model_transport_failure_has_no_retry_or_endpoint_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = _policy()
    calls = 0

    class Chat:
        def create(self, **_kwargs: Any) -> Any:
            nonlocal calls
            calls += 1
            raise TimeoutError("private provider detail")

    class Responses:
        def create(self, **_kwargs: Any) -> Any:
            raise AssertionError("bounded endpoint fallback is forbidden")

    class Client:
        chat = SimpleNamespace(completions=Chat())
        responses = Responses()

        def with_options(self, **_kwargs: Any) -> Client:
            return self

    monkeypatch.setattr(llm, "get_openai_client", lambda: Client())
    with pytest.raises(TimeoutError):
        llm.ask_model(
            "question",
            "system",
            provider="OpenAI",
            model="gpt-5.4-mini",
            cap_policy=policy,
            logical_call_id="model:no-fallback",
        )

    assert calls == 1
    snapshot = policy.physical_snapshot()
    assert snapshot["retry_attempts"] == 0
    assert snapshot["fallback_attempts"] == 0
    assert snapshot["lifecycle_counts"]["settled_conservative"] == 1


def test_strict_multicomponent_transport_consumes_the_shared_ledger() -> None:
    policy = _policy()
    factory_calls: list[dict[str, Any]] = []
    provider_calls = 0

    class Responses:
        def create(self, **_kwargs: Any) -> Any:
            nonlocal provider_calls
            provider_calls += 1
            assert policy.physical_snapshot()["lifecycle_counts"]["dispatched"] == 1
            return SimpleNamespace(
                output_text='{"status":"ok"}',
                usage=SimpleNamespace(
                    input_tokens=10,
                    output_tokens=2,
                    input_tokens_details=SimpleNamespace(cached_tokens=1),
                    output_tokens_details=SimpleNamespace(reasoning_tokens=1),
                ),
            )

    def client_factory(**kwargs: Any) -> Any:
        factory_calls.append(dict(kwargs))
        return SimpleNamespace(responses=Responses())

    transport = build_strict_one_shot_smart_model_transport(
        smart_provider="OpenAI",
        smart_model="gpt-5.4",
        credential_lookup=lambda _name: "offline-fake-key",
        client_factory=client_factory,
        cap_policy=policy,
    )
    result = transport(
        "question",
        "system",
        provider="OpenAI",
        model="gpt-5.4",
        effort="high",
        require_json=True,
        use_reasoning=True,
        logical_call_id="strict:component-one",
    )

    assert result.provider_request_succeeded is True
    assert provider_calls == 1
    assert factory_calls[0]["max_retries"] == 0
    assert 0 < factory_calls[0]["timeout"] <= 30
    snapshot = policy.physical_snapshot()
    assert snapshot["physical_attempts_by_family"]["model"] == 1
    assert snapshot["lifecycle_counts"]["settled_observed"] == 1
    assert snapshot["observed_tokens"]["reasoning_tokens"] == 1


def test_search_adapter_retry_is_zero_only_for_bounded_posture() -> None:
    ordinary_calls = 0

    @search_providers.retry_with_backoff(max_retries=2, base_delay=0)
    def ordinary_flaky(*, _physical_retry_index: int = 0) -> str:
        nonlocal ordinary_calls
        ordinary_calls += 1
        if _physical_retry_index == 0:
            raise TimeoutError("ordinary retry fixture")
        return "recovered"

    assert ordinary_flaky() == "recovered"
    assert ordinary_calls == 2

    bounded_calls = 0

    @search_providers.retry_with_backoff(max_retries=3, base_delay=0)
    def bounded_failure(
        *,
        cap_policy: RunCapPolicy,
        _physical_retry_index: int = 0,
    ) -> None:
        nonlocal bounded_calls
        bounded_calls += 1
        assert _physical_retry_index == 0
        raise TimeoutError("bounded retry fixture")

    with pytest.raises(TimeoutError):
        bounded_failure(cap_policy=_policy())
    assert bounded_calls == 1


def test_stream_and_concurrent_predispatch_deadlines_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [200.0]
    monkeypatch.setattr(cap_module.time, "monotonic", lambda: clock[0])
    policy = _policy(deadline_seconds=2.0, activate=False)
    policy.activate(run_id="stream-deadline-run", request_id="stream-deadline-request")
    options: list[dict[str, Any]] = []

    class ResponseStream:
        closed = False

        def __iter__(self) -> Any:
            clock[0] = 203.0
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="late"))])

        def close(self) -> None:
            self.closed = True

    response_stream = ResponseStream()

    class Chat:
        def create(self, **_kwargs: Any) -> ResponseStream:
            return response_stream

    class Client:
        chat = SimpleNamespace(completions=Chat())

        def with_options(self, **kwargs: Any) -> Client:
            options.append(kwargs)
            return self

    monkeypatch.setattr(llm, "get_openai_client", lambda: Client())
    stream = llm.ask_model(
        "question",
        "system",
        provider="OpenAI",
        model="gpt-5.4-mini",
        stream=True,
        cap_policy=policy,
        logical_call_id="model:stream-deadline",
    )
    with pytest.raises(RunCapExceeded) as stream_exc:
        list(stream)
    assert stream_exc.value.reason_code == "deadline_exhausted"
    assert options[0]["max_retries"] == 0
    assert options[0]["timeout"] == 2.0
    assert response_stream.closed is True
    assert policy.physical_snapshot()["lifecycle_counts"]["settled_conservative"] == 1

    clock[0] = 300.0
    concurrent = _policy(deadline_seconds=5.0, activate=False)
    concurrent.activate(
        run_id="concurrent-deadline-run",
        request_id="concurrent-deadline-request",
    )
    reservations = [concurrent.reserve_attempt(_spec(logical_call_id=f"near-deadline:{index}")) for index in range(2)]
    clock[0] = 306.0

    def dispatch_after_deadline(reservation: Any) -> str:
        with pytest.raises(RunCapExceeded) as exc:
            reservation.mark_dispatched()
        return exc.value.reason_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        reasons = list(pool.map(dispatch_after_deadline, reservations))
    assert reasons == ["deadline_exhausted", "deadline_exhausted"]
    concurrent_snapshot = concurrent.physical_snapshot()
    assert concurrent_snapshot["physical_attempts"] == 0
    assert concurrent_snapshot["lifecycle_counts"]["cancelled_pre_dispatch"] == 2
    concurrent.finalize_active_attempts()
    with pytest.raises(RunCapExceeded) as completion_exc:
        concurrent.ensure_within_deadline()
    assert completion_exc.value.reason_code == "deadline_exhausted"


def test_embedding_batches_and_tavily_search_each_reserve_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embed_policy = _policy()
    embedding_calls = 0

    class Embeddings:
        def create(self, *, model: str, input: list[str]) -> Any:
            nonlocal embedding_calls
            embedding_calls += 1
            assert model == "text-embedding-3-small"
            assert embed_policy.physical_snapshot()["lifecycle_counts"]["dispatched"] == 1
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[1.0, 0.0]) for _ in input],
                usage=SimpleNamespace(prompt_tokens=len(input)),
            )

    class EmbedClient:
        embeddings = Embeddings()

        def with_options(self, **_kwargs: Any) -> EmbedClient:
            return self

    monkeypatch.setattr(llm, "get_openai_client", lambda: EmbedClient())
    embeddings = llm.embed_texts(
        ["bounded text" for _ in range(101)],
        cap_policy=embed_policy,
        logical_call_id="embedding:test",
    )
    assert len(embeddings) == 101
    assert embedding_calls == 2
    assert embed_policy.physical_snapshot()["physical_attempts_by_family"]["embedding"] == 2

    search_policy = _policy()
    monkeypatch.setenv("TAVILY_API_KEY", "offline-fake-key")

    class HttpResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "results": [
                    {
                        "url": "https://docs.example.test/result",
                        "title": "Result",
                        "content": "Official result",
                        "raw_content": "Official result material",
                    }
                ],
                "images": [],
            }

    def fake_post(*_args: Any, **kwargs: Any) -> HttpResponse:
        assert search_policy.physical_snapshot()["lifecycle_counts"]["dispatched"] == 1
        assert 0 < kwargs["timeout"] <= search_providers.TAVILY_SEARCH_TIMEOUT_SEC
        return HttpResponse()

    monkeypatch.setattr(search_providers.requests, "post", fake_post)
    results, _images = search_providers.search_web_results(
        "official docs",
        cap_policy=search_policy,
        logical_call_id="search:test",
    )
    assert results
    assert search_policy.physical_snapshot()["physical_attempts_by_family"]["search"] == 1


def test_bounded_exa_uses_deadline_clipped_http_not_orphanable_sdk_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = _policy()
    monkeypatch.setenv("EXA_API_KEY", "offline-fake-key")

    def forbidden_sdk() -> Any:
        raise AssertionError("bounded Exa SDK client must not be constructed")

    class HttpResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "results": [
                    {
                        "url": "https://docs.example.test/exa",
                        "title": "Exa result",
                        "text": "Official Exa result",
                        "score": 0.9,
                    }
                ]
            }

    monkeypatch.setattr(search_providers, "get_exa_client", forbidden_sdk)
    monkeypatch.setattr(
        search_providers.requests,
        "post",
        lambda *_args, **_kwargs: HttpResponse(),
    )
    results, _images = search_providers.search_exa_results(
        "official docs",
        cap_policy=policy,
        logical_call_id="search:exa",
    )
    assert results[0]["_exa_score"] == 0.9
    assert policy.physical_snapshot()["physical_attempts"] == 1


def test_read_adapter_marks_fake_transport_dispatched_and_settles_once() -> None:
    policy = _policy()
    route = route_provider_capability(
        ProviderCapabilityRequest(capability=AcquisitionCapability.READ),
        {"linkup": False, "tavily": True},
    )
    request = AcquisitionRequest(
        acquisition_job_id="read-fixture",
        route_decision=route,
        selected_urls=("https://docs.example.test/read",),
    )
    fake_calls = 0

    def fake_extract(payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal fake_calls
        fake_calls += 1
        assert policy.physical_snapshot()["lifecycle_counts"]["dispatched"] == 1
        return {
            "results": [
                {
                    "url": payload["urls"],
                    "attempted_url": payload["urls"],
                    "raw_content": "Readable official material.",
                }
            ],
            "failed_results": [],
        }

    def reserve_read() -> Any:
        pricing = policy.resolve_route_pricing(
            ExternalCallFamily.READ,
            "tavily",
            "extract",
        )
        return policy.reserve_attempt(
            ExternalAttemptSpec(
                family=ExternalCallFamily.READ,
                provider="tavily",
                route="extract",
                operation="extract",
                logical_call_id="read:test",
                max_usage=TokenUsage(),
                pricing=pricing,
                requested_timeout_seconds=10,
            )
        )

    result = dispatch_acquisition(
        request,
        transports=AcquisitionTransports(tavily_extract=fake_extract),
        before_transport=reserve_read,
    )
    assert result.status is AcquisitionExecutionStatus.SUCCEEDED
    assert fake_calls == 1
    snapshot = policy.physical_snapshot()
    assert snapshot["physical_attempts_by_family"]["read"] == 1
    assert snapshot["lifecycle_counts"]["settled_observed"] == 1


def test_search_judgment_cap_denial_is_not_converted_to_fallback() -> None:
    kernel, contract = _kernel_with_official_contract()
    action = kernel.authorize_search_judgment(inputs={"phase": "cap-terminal"})

    def denied(*_args: Any, **_kwargs: Any) -> str:
        raise RunCapExceeded(
            "model_attempt_cap",
            family=ExternalCallFamily.MODEL,
        )

    with pytest.raises(RunCapExceeded) as exc:
        execute_run_authority_search_judgment_action(
            action,
            judgment_input=search_judgment_input(
                contract,
                kernel.state.evidence_ledger.to_projection().to_dict(),
            ),
            ask_model=denied,
            clean_json_response=lambda value: value,
            smart_model_enabled=True,
            provider="OpenAI",
            model="gpt-5.4",
        )
    assert exc.value.terminal_payload()["code"] == "bounded_run_cap_reached"


_ISCLOSE_QUERY = (
    "According to the official Python 3 documentation, what are the default "
    "values for rel_tol and abs_tol in math.isclose()?"
)
_ISCLOSE_URL = "https://docs.python.org/3/library/math.html"


def _bounded_model_fake(
    base: Callable[..., str],
    policy: RunCapPolicy,
) -> Callable[..., str]:
    @mark_cap_aware
    def wrapped(prompt: str, system_prompt: str, **kwargs: Any) -> str:
        active_policy = kwargs.get("cap_policy")
        assert active_policy is policy
        provider = str(kwargs.get("provider") or "OpenAI")
        model = str(kwargs.get("model") or "gpt-5.4-mini")
        logical_call_id = str(kwargs.get("logical_call_id") or policy.new_logical_call_id("offline-model"))
        reservation = policy.reserve_attempt(
            ExternalAttemptSpec(
                family=ExternalCallFamily.MODEL,
                provider=provider.casefold(),
                route=model,
                operation="model",
                logical_call_id=logical_call_id,
                max_usage=model_usage_bound(prompt, system_prompt),
                pricing=policy.resolve_route_pricing(
                    ExternalCallFamily.MODEL,
                    provider,
                    model,
                ),
                requested_timeout_seconds=DEFAULT_EXTERNAL_TIMEOUT_SECONDS,
            )
        )
        reservation.mark_dispatched()
        try:
            result = base(prompt, system_prompt, **kwargs)
        except BaseException:
            reservation.settle_conservative("offline_fake_model_failed")
            raise
        reservation.settle_observed(
            TokenUsage(
                input_tokens=estimate_tokens(prompt) + estimate_tokens(system_prompt),
                output_tokens=estimate_tokens(str(result)),
            )
        )
        return result

    return wrapped


def _bounded_embedding_fake(
    base: Callable[..., list[list[float]]],
    policy: RunCapPolicy,
) -> Callable[..., list[list[float]]]:
    @mark_cap_aware
    def wrapped(texts: list[str], **kwargs: Any) -> list[list[float]]:
        material = list(texts)
        active_policy = kwargs.get("cap_policy")
        assert active_policy is policy
        provider = str(kwargs.get("provider") or "OpenAI")
        model = str(kwargs.get("model") or "text-embedding-3-small")
        reservation = policy.reserve_attempt(
            ExternalAttemptSpec(
                family=ExternalCallFamily.EMBEDDING,
                provider=provider.casefold(),
                route=model,
                operation="embedding",
                logical_call_id=str(kwargs.get("logical_call_id") or policy.new_logical_call_id("offline-embedding")),
                max_usage=embedding_usage_bound(material),
                pricing=policy.resolve_route_pricing(
                    ExternalCallFamily.EMBEDDING,
                    provider,
                    model,
                ),
                requested_timeout_seconds=DEFAULT_EXTERNAL_TIMEOUT_SECONDS,
            )
        )
        reservation.mark_dispatched()
        try:
            result = base(material, **kwargs)
        except BaseException:
            reservation.settle_conservative("offline_fake_embedding_failed")
            raise
        reservation.settle_observed(TokenUsage(embedding_tokens=sum(estimate_tokens(text) for text in material)))
        return result

    return wrapped


def _bounded_search_fake(
    base: Callable[..., list[dict[str, Any]]],
    policy: RunCapPolicy,
) -> Callable[..., list[dict[str, Any]]]:
    @mark_cap_aware
    def wrapped(
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        *args: Any,
        cap_policy: RunCapPolicy | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        assert cap_policy is policy
        reservations = []
        try:
            for query in queries:
                digest = sha256(str(query).encode("utf-8")).hexdigest()[:16]
                reservations.append(
                    policy.reserve_attempt(
                        ExternalAttemptSpec(
                            family=ExternalCallFamily.SEARCH,
                            provider="tavily",
                            route="search",
                            operation="search",
                            logical_call_id=f"offline-search:{digest}",
                            max_usage=TokenUsage(),
                            pricing=policy.resolve_route_pricing(
                                ExternalCallFamily.SEARCH,
                                "tavily",
                                "search",
                            ),
                            requested_timeout_seconds=(DEFAULT_EXTERNAL_TIMEOUT_SECONDS),
                        )
                    )
                )
        except BaseException:
            for reservation in reservations:
                reservation.cancel_pre_dispatch("search_batch_not_dispatched")
            raise
        for reservation in reservations:
            reservation.mark_dispatched()
        try:
            result = base(
                queries,
                intent,
                complexity,
                search_depth,
                results_per_query,
                *args,
                cap_policy=cap_policy,
                **kwargs,
            )
        except BaseException:
            for reservation in reservations:
                reservation.settle_conservative("offline_fake_search_failed")
            raise
        for reservation in reservations:
            reservation.settle_observed(TokenUsage())
        return result

    return wrapped


def _bounded_strict_fake(
    base: Callable[..., Any],
    policy: RunCapPolicy,
) -> Callable[..., Any]:
    @mark_cap_aware
    def wrapped(prompt: str, system_prompt: str, **kwargs: Any) -> Any:
        provider = str(kwargs.get("provider") or "OpenAI")
        model = str(kwargs.get("model") or "gpt-5.4")
        reservation = policy.reserve_attempt(
            ExternalAttemptSpec(
                family=ExternalCallFamily.MODEL,
                provider=provider.casefold(),
                route=model,
                operation="strict-model",
                logical_call_id=str(kwargs.get("logical_call_id") or policy.new_logical_call_id("offline-strict")),
                max_usage=model_usage_bound(prompt, system_prompt),
                pricing=policy.resolve_route_pricing(
                    ExternalCallFamily.MODEL,
                    provider,
                    model,
                ),
                requested_timeout_seconds=DEFAULT_EXTERNAL_TIMEOUT_SECONDS,
            )
        )
        reservation.mark_dispatched()
        try:
            result = base(prompt, system_prompt, **kwargs)
        except BaseException:
            reservation.settle_conservative("offline_fake_strict_model_failed")
            raise
        if bool(getattr(result, "provider_request_succeeded", False)):
            reservation.settle_observed(
                TokenUsage(
                    input_tokens=int(getattr(result, "input_tokens", 0) or 0),
                    output_tokens=int(getattr(result, "output_tokens", 0) or 0),
                )
            )
        else:
            reservation.settle_conservative("offline_fake_strict_model_ambiguous")
        return result

    return wrapped


def _bounded_harness_deps(
    harness: PostRetirementOrdinaryPipelineHarness,
    policy: RunCapPolicy,
) -> RunDeps:
    deps = harness.deps()
    assert deps.strict_one_shot_smart_model_transport is not None
    assert deps.searchos_read_acquisition_transports is not None
    read_transport = deps.searchos_read_acquisition_transports.tavily_extract
    assert read_transport is not None

    def bounded_read_transport(payload: dict[str, Any]) -> dict[str, Any]:
        snapshot = policy.physical_snapshot()
        assert snapshot["lifecycle_counts"][AttemptLifecycle.DISPATCHED.value] >= 1
        return read_transport(payload)

    return replace(
        deps,
        ask_model=_bounded_model_fake(harness.ask_model, policy),
        embed_texts=_bounded_embedding_fake(harness.embed_texts, policy),
        process_search_queries=_bounded_search_fake(
            harness.process_search_queries,
            policy,
        ),
        strict_one_shot_smart_model_transport=_bounded_strict_fake(
            harness.strict_one_shot_smart_model_transport,
            policy,
        ),
        searchos_read_acquisition_transports=AcquisitionTransports(tavily_extract=bounded_read_transport),
    )


def _isclose_harness(tmp_path: Path) -> PostRetirementOrdinaryPipelineHarness:
    evidence_rows = [
        {
            "title": "Python math.isclose documentation",
            "url": _ISCLOSE_URL,
            "text": (
                "According to the official Python 3 documentation, "
                "math.isclose defines default tolerances. The defaults are "
                "rel_tol=0.000000001 and abs_tol=0.0."
            ),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        },
        {
            "title": "Python floating point arithmetic documentation",
            "url": "https://docs.python.org/3.14/library/math.html",
            "text": (
                "According to the official Python 3 documentation, "
                "math.isclose defines default tolerances. The defaults are "
                "rel_tol=0.000000001 and abs_tol=0.0."
            ),
            "credibility": 4,
            "source_tier": "official",
            "source_class": "primary_source_documents",
            "currentness_signal": "current",
            "readable_status": "readable",
            "disposition": "accepted",
        },
    ]
    answer = f"The defaults are rel_tol=0.000000001 and abs_tol=0.0. [[1]]({_ISCLOSE_URL})"
    return PostRetirementOrdinaryPipelineHarness(
        tmp_path=tmp_path,
        query=_ISCLOSE_QUERY,
        core_topic="Python math.isclose default tolerances",
        primary_entity="Python",
        researcher_queries=(_ISCLOSE_QUERY,),
        analyst_response="The defaults are rel_tol=0.000000001 and abs_tol=0.0.",
        raw_author_response=answer,
        evidence_rows=evidence_rows,
        read_assessment_decision="REQUEST_READ_PAGE",
        read_content_by_url={
            **{row["url"]: row["text"] for row in evidence_rows},
        },
    )


def test_unbounded_cli_config_keeps_the_default_no_policy_posture() -> None:
    args = compatibility_cli._parse_args([_ISCLOSE_QUERY])
    config = compatibility_cli._build_run_config(args)

    assert config.cap_policy is None


def test_unbounded_cli_does_not_render_a_bounded_cap_terminal(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = RunCapExceeded("fixture_unbounded_exception")
    monkeypatch.setattr(
        compatibility_cli,
        "_build_logger",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        compatibility_cli,
        "missing_required_api_keys",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        compatibility_cli,
        "_build_run_deps",
        lambda _log: SimpleNamespace(),
    )
    monkeypatch.setattr(
        compatibility_cli,
        "run_pipeline",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(expected),
    )

    with pytest.raises(RunCapExceeded) as exc:
        compatibility_cli.main([_ISCLOSE_QUERY])

    assert exc.value is expected
    assert "bounded_product_cli_terminal_v1" not in capsys.readouterr().out



def test_public_cli_rejects_bounded_product_profile_flag() -> None:
    with pytest.raises(SystemExit):
        compatibility_cli._parse_args(
            [_ISCLOSE_QUERY, "--bounded-product-profile", "public-cli-v1"]
        )
    with pytest.raises(SystemExit):
        compatibility_cli._parse_args([_ISCLOSE_QUERY, "--bounded-product-profile"])


def test_bounded_terminal_helpers_require_explicit_policy() -> None:
    with pytest.raises(RuntimeError, match="explicit bounded policy"):
        compatibility_cli._bounded_terminal_payload(
            entrypoint="proplex",
            exc=RunCapExceeded("fixture"),
            config=None,
        )
    policy = _policy()
    config = RunConfig(query=_ISCLOSE_QUERY, cap_policy=policy)
    payload = compatibility_cli._bounded_terminal_payload(
        entrypoint="scryraven",
        exc=RunCapExceeded("total_attempt_cap"),
        config=config,
    )
    assert payload["schema_version"] == "bounded_product_cli_terminal_v1"
    assert payload["entrypoint"] == "scryraven"
    assert payload["profile_name"] == "fixture-v1"
    assert payload["physical_envelope"]["physical_attempts"] == 0
    assert payload["terminal"]["owner"] == "core.cap_enforcement.RunCapPolicy"


@pytest.mark.parametrize("entrypoint", ["proplex", "scryraven"])
def test_ordinary_pipeline_executes_bounded_isclose_with_explicit_policy(
    entrypoint: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Internal ordinary-pipeline proof with an explicit fictional policy.

    Gate 1 temporary proof boundary: public CLI no longer selects a bounded
    posture. Gate 2 restores the authorization-backed public-CLI proof.
    """

    harness = _isclose_harness(tmp_path / entrypoint)
    policy = _policy(activate=False)
    config = RunConfig(
        query=_ISCLOSE_QUERY,
        mode="Balanced",
        include_domains=["docs.python.org"],
        fast_provider="OpenAI",
        fast_model="gpt-5.4-mini",
        smart_provider="OpenAI",
        smart_model="gpt-5.4",
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        cap_policy=policy,
    )
    deps = _bounded_harness_deps(harness, policy)

    def forbidden_persistence(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("bounded path reached a persistence or raw-log path")

    monkeypatch.setattr(
        orchestrator,
        "execute_persistence_side_effects",
        forbidden_persistence,
    )
    monkeypatch.setattr(orchestrator, "load_policy_state", forbidden_persistence)
    monkeypatch.setattr(
        orchestrator,
        "recent_recurring_kb_hints",
        forbidden_persistence,
    )
    monkeypatch.setattr(orchestrator, "log_run_started", forbidden_persistence)
    monkeypatch.setattr(orchestrator, "log_run_failed", forbidden_persistence)

    from core.cost_accounting import CostAccumulator
    from core.protocols import NullStatusWriter

    outcome = orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )
    assert outcome.report
    assert "0.000000001" in outcome.report or "rel_tol" in outcome.report
    physical = policy.physical_snapshot()
    assert physical["enforcement"] == "physical_attempt_envelope"
    assert physical["retry_attempts"] == 0
    assert physical["fallback_attempts"] == 0
    assert physical["active_attempts"] == 0
    assert all(
        physical["physical_attempts_by_family"][family.value] > 0
        for family in ExternalCallFamily
    )
    assert harness.forbidden_live_calls == []
    success = compatibility_cli._bounded_success_payload(
        entrypoint=entrypoint,
        config=config,
        outcome=outcome,
    )
    assert success["entrypoint"] == entrypoint
    assert success["answer_present"] is True
    assert success["physical_envelope"]["physical_attempts"] > 0
