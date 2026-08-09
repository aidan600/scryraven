"""Focused offline proof for initial-planning safe failure projection.

Mode: BUILD.
Test class: phase_focus / offline_product_path_proof.
No test in this file is integration- or secrets-backed.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import proplex.__main__ as compatibility_cli
from core.initial_query_strategy_failure import (
    INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY,
    InitialQueryStrategyFailureCode,
    InitialQueryStrategyFailureError,
    InitialQueryStrategyFailureOrigin,
    classify_initial_query_strategy_failure,
    invoke_run_kernel_initial_planning,
    project_initial_query_strategy_failure_for_terminal,
    query_strategy_convergence_failure,
    run_kernel_initial_planning_failure,
    scout_disambiguation_runtime_failure,
    search_planner_revision_runtime_failure,
    search_planner_runtime_failure,
)
from core.query_production_runtime import (
    QueryStrategyConvergenceError,
    QueryStrategyConvergenceFailureCode,
)
from core.run_cap_authorization import query_sha256
from core.run_config import RunConfig
from core.run_kernel import RunKernelTransitionError
from core.search_planner_model_adapter import (
    SearchPlannerModelAdapterError,
    SearchPlannerModelAdapterFailureCode,
)
from core.search_planner_runtime import (
    SearchPlannerRuntimeError,
    SearchPlannerRuntimeSafeFailureCode,
)

_ISCLOSE_QUERY = (
    "Does Python's math.isclose use relative tolerance, absolute tolerance, or both?"
)

_PRIVATE_FRAGMENTS = (
    "fictional-raw-exception-message-sentinel",
    "fictional-raw-prompt-sentinel",
    "fictional-provider-payload-sentinel",
    "fictional-raw-model-output-sentinel",
)


def test_owner_authored_safe_codes_are_closed_on_exception_types() -> None:
    assert (
        SearchPlannerRuntimeError.SAFE_FAILURE_CODE
        is SearchPlannerRuntimeSafeFailureCode.SEARCH_PLANNER_RUNTIME_ERROR
    )
    assert SearchPlannerRuntimeError.SAFE_FAILURE_ORIGIN == "planner_runtime"
    assert (
        QueryStrategyConvergenceError.SAFE_FAILURE_CODE
        is QueryStrategyConvergenceFailureCode.QUERY_STRATEGY_CONVERGENCE_ERROR
    )
    assert (
        QueryStrategyConvergenceError.SAFE_FAILURE_ORIGIN
        == "query_strategy_convergence"
    )


def test_classify_projects_closed_origin_and_code_only() -> None:
    runtime = SearchPlannerRuntimeError(
        "private: " + " | ".join(_PRIVATE_FRAGMENTS)
    )
    convergence = QueryStrategyConvergenceError(
        "private: " + " | ".join(_PRIVATE_FRAGMENTS)
    )
    translated = InitialQueryStrategyFailureError(
        run_kernel_initial_planning_failure(operation="search_planner_production")
    )
    adapter = SearchPlannerModelAdapterError(
        "private: " + " | ".join(_PRIVATE_FRAGMENTS),
        failure_code=SearchPlannerModelAdapterFailureCode.MODEL_CALL_FAILED,
        predicate_id=None,
    )

    runtime_failure = classify_initial_query_strategy_failure(runtime)
    assert runtime_failure is not None
    assert runtime_failure == search_planner_runtime_failure()
    assert runtime_failure.to_terminal_projection() == {
        "schema_version": "initial_query_strategy_failure_v1",
        "boundary": "initial_query_strategy",
        "failure_origin": InitialQueryStrategyFailureOrigin.PLANNER_RUNTIME.value,
        "failure_code": (
            InitialQueryStrategyFailureCode.SEARCH_PLANNER_RUNTIME_ERROR.value
        ),
    }

    convergence_failure = classify_initial_query_strategy_failure(convergence)
    assert convergence_failure == query_strategy_convergence_failure()
    assert classify_initial_query_strategy_failure(translated) == translated.failure
    assert classify_initial_query_strategy_failure(adapter) is None
    assert classify_initial_query_strategy_failure(RuntimeError("unknown")) is None
    assert classify_initial_query_strategy_failure(None) is None

    for failure in (
        runtime_failure,
        convergence_failure,
        translated.failure,
        scout_disambiguation_runtime_failure(),
        search_planner_revision_runtime_failure(),
    ):
        projected = failure.to_terminal_projection()
        encoded = json.dumps(projected, sort_keys=True)
        for fragment in _PRIVATE_FRAGMENTS:
            assert fragment not in encoded
        assert set(projected) == {
            "schema_version",
            "boundary",
            "failure_origin",
            "failure_code",
        }


def test_invoke_run_kernel_translates_only_allowlisted_operations() -> None:
    def boom() -> None:
        raise RunKernelTransitionError(
            "private transition detail: " + " | ".join(_PRIVATE_FRAGMENTS)
        )

    with pytest.raises(InitialQueryStrategyFailureError) as caught:
        invoke_run_kernel_initial_planning("query_production", boom)
    assert caught.value.failure == run_kernel_initial_planning_failure(
        operation="query_production"
    )
    encoded = json.dumps(caught.value.to_terminal_projection(), sort_keys=True)
    for fragment in _PRIVATE_FRAGMENTS:
        assert fragment not in encoded

    with pytest.raises(ValueError, match="not allowlisted"):
        run_kernel_initial_planning_failure(operation="not_a_corridor_operation")


def test_bounded_terminal_projects_initial_planning_failure_without_private_material() -> None:
    private_message = "private: " + " | ".join(_PRIVATE_FRAGMENTS)
    cases = (
        SearchPlannerRuntimeError(private_message),
        QueryStrategyConvergenceError(private_message),
        InitialQueryStrategyFailureError(
            run_kernel_initial_planning_failure(
                operation="search_work_plan_construction"
            )
        ),
        InitialQueryStrategyFailureError(scout_disambiguation_runtime_failure()),
        InitialQueryStrategyFailureError(search_planner_revision_runtime_failure()),
    )
    for exc in cases:
        payload = compatibility_cli._bounded_terminal_payload(
            entrypoint="scryraven",
            exc=exc,
            config=RunConfig(query=_ISCLOSE_QUERY),
        )
        terminal = payload["terminal"]
        assert terminal["code"] == "bounded_run_failed"
        assert "search_planner_failure" not in terminal
        assert terminal[INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY] == (
            project_initial_query_strategy_failure_for_terminal(exc)
        )
        encoded = json.dumps(payload, sort_keys=True)
        for fragment in _PRIVATE_FRAGMENTS:
            assert fragment not in encoded


def test_bounded_terminal_preserves_adapter_rich_path_exclusively() -> None:
    adapter = SearchPlannerModelAdapterError(
        "private: " + " | ".join(_PRIVATE_FRAGMENTS),
        failure_code=SearchPlannerModelAdapterFailureCode.MODEL_CALL_FAILED,
        predicate_id=None,
    )
    payload = compatibility_cli._bounded_terminal_payload(
        entrypoint="scryraven",
        exc=adapter,
        config=RunConfig(query=_ISCLOSE_QUERY),
    )
    terminal = payload["terminal"]
    assert "search_planner_failure" in terminal
    assert INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY not in terminal
    encoded = json.dumps(payload, sort_keys=True)
    for fragment in _PRIVATE_FRAGMENTS:
        assert fragment not in encoded


@pytest.mark.parametrize("entrypoint", ["proplex", "scryraven"])
def test_public_bounded_cli_projects_initial_planning_failure_identity(
    entrypoint: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_sha = "e" * 40
    auth_path = tmp_path / "offline-auth.json"
    auth_path.write_text(
        json.dumps(_offline_proof_authorization_document(repository_sha=fixture_sha)),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.run_cap_authorization.resolve_local_repository_identity",
        lambda _repo_root: fixture_sha,
    )
    monkeypatch.setattr(
        compatibility_cli,
        "missing_required_api_keys",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        compatibility_cli,
        "_build_logger",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        compatibility_cli,
        "_build_run_deps",
        lambda _log: SimpleNamespace(),
    )

    private_message = "SearchPlanner fixture failure: " + " | ".join(_PRIVATE_FRAGMENTS)
    failure_to_raise: BaseException = SearchPlannerRuntimeError(private_message)

    def fail_pipeline(*_args: Any, **_kwargs: Any) -> Any:
        raise failure_to_raise

    monkeypatch.setattr(compatibility_cli, "run_pipeline", fail_pipeline)
    argv = [
        _ISCLOSE_QUERY,
        "--mode",
        "Balanced",
        "--include-domains",
        "docs.python.org",
        "--fast-provider",
        "OpenAI",
        "--fast-model",
        "gpt-5.4-mini",
        "--smart-provider",
        "OpenAI",
        "--smart-model",
        "gpt-5.4",
        "--embed-provider",
        "OpenAI",
        "--embed-model",
        "text-embedding-3-small",
        "--bounded-run-authorization",
        str(auth_path),
    ]

    expected_failures: tuple[BaseException, ...] = (
        SearchPlannerRuntimeError(private_message),
        QueryStrategyConvergenceError(private_message),
        InitialQueryStrategyFailureError(
            run_kernel_initial_planning_failure(operation="query_plan_admission")
        ),
    )
    for expected_failure in expected_failures:
        failure_to_raise = expected_failure
        assert compatibility_cli.main(argv, entrypoint=entrypoint) == 1
        output = capsys.readouterr().out
        payload = json.loads(output.strip().splitlines()[-1])
        terminal = payload["terminal"]
        assert terminal["code"] == "bounded_run_failed"
        assert terminal[INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY] == (
            project_initial_query_strategy_failure_for_terminal(expected_failure)
        )
        assert "search_planner_failure" not in terminal
        for fragment in _PRIVATE_FRAGMENTS:
            assert fragment not in json.dumps(payload, sort_keys=True)

    failure_to_raise = RuntimeError(private_message)
    assert compatibility_cli.main(argv, entrypoint=entrypoint) == 1
    generic_payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert generic_payload["terminal"]["code"] == "bounded_run_failed"
    assert INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY not in generic_payload["terminal"]
    assert "search_planner_failure" not in generic_payload["terminal"]
    for fragment in _PRIVATE_FRAGMENTS:
        assert fragment not in json.dumps(generic_payload, sort_keys=True)


def _offline_proof_authorization_document(*, repository_sha: str) -> dict[str, Any]:
    zero = {
        "input_per_million_usd": "0",
        "cached_input_per_million_usd": "0",
        "output_per_million_usd": "0",
        "reasoning_per_million_usd": "0",
        "embedding_per_million_usd": "0",
        "flat_attempt_usd": "0",
    }
    search = {**zero, "flat_attempt_usd": "0.01"}
    read = {**zero, "flat_attempt_usd": "0.01"}
    model = {
        "input_per_million_usd": "1",
        "cached_input_per_million_usd": "1",
        "output_per_million_usd": "2",
        "reasoning_per_million_usd": "3",
        "embedding_per_million_usd": "0",
        "flat_attempt_usd": "0",
    }
    embedding = {
        **zero,
        "embedding_per_million_usd": "1",
    }

    def route(provider: str, name: str, pricing: dict[str, str]) -> dict[str, Any]:
        return {"provider": provider, "route": name, "pricing": pricing}

    return {
        "schema_version": "scryraven_bounded_run_authorization_v1",
        "authorization_id": "offline-isclose-auth-v1",
        "repository_sha": repository_sha,
        "request": {
            "query_sha256": query_sha256(_ISCLOSE_QUERY),
            "mode": "Balanced",
            "include_domains": ["docs.python.org"],
            "exclude_domains": [],
        },
        "pricing_fact_set_id": "offline-isclose-pricing-v1",
        "routes": {
            "fast_model": route("OpenAI", "gpt-5.4-mini", model),
            "smart_model": route("OpenAI", "gpt-5.4", model),
            "embedding": route("OpenAI", "text-embedding-3-small", embedding),
            "search": [
                route("tavily", "search", search),
                route("linkup", "search", search),
                route("exa", "search", search),
                route("brave", "search", search),
                route("serper", "search", search),
            ],
            "read": [
                route("tavily", "extract", read),
                route("linkup", "fetch", read),
            ],
        },
        "limits": {
            "attempts": {
                "model": 32,
                "embedding": 32,
                "search": 32,
                "read": 32,
                "total": 64,
            },
            "tokens": {
                "input": 1_000_000,
                "cached_input": 1_000_000,
                "output": 1_000_000,
                "reasoning": 1_000_000,
                "embedding": 1_000_000,
            },
            "max_retries": 0,
            "max_fallbacks": 0,
            "deadline_seconds": 30,
        },
        "max_run_usd": "50",
    }
