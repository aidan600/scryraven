"""Focused offline proof for initial-planning safe failure projection.

Mode: BUILD.
Test class: phase_focus / offline_product_path_proof.
No test in this file is integration- or secrets-backed.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import proplex.__main__ as compatibility_cli
from core.initial_query_strategy_failure import (
    INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY,
    InitialQueryStrategyFailure,
    InitialQueryStrategyFailureCode,
    InitialQueryStrategyFailureError,
    InitialQueryStrategyFailureOrigin,
    classify_initial_query_strategy_failure,
    invoke_run_kernel_initial_planning,
    project_initial_query_strategy_failure_for_terminal,
    run_kernel_initial_planning_failure,
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
    accept_planner_model_output,
)
from core.search_planner_runtime import (
    SearchPlannerRuntimeError,
    SearchPlannerRuntimeSafeFailureCode,
)
from core.search_planner_semantic_compiler import (
    SearchPlannerBranchFieldSetDetail,
    SearchPlannerSemanticProposalSubtype,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ISCLOSE_QUERY = (
    "Does Python's math.isclose use relative tolerance, absolute tolerance, or both?"
)
_PRIVATE_FRAGMENTS = (
    "fictional-raw-exception-message-sentinel",
    "fictional-raw-prompt-sentinel",
    "fictional-provider-payload-sentinel",
    "fictional-raw-model-output-sentinel",
)


def _raise_failure_codes(path: Path, exception_name: str) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    codes: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        func = node.exc.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name != exception_name:
            continue
        code_value: str | None = None
        for keyword in node.exc.keywords:
            if keyword.arg != "failure_code":
                continue
            value = keyword.value
            if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
                code_value = value.attr
            break
        if code_value is None:
            raise AssertionError(
                f"{path.name}:{node.lineno} {exception_name} raise lacks failure_code="
            )
        codes.append(code_value)
    return codes


def test_every_ordinary_reachable_runtime_raise_supplies_closed_code() -> None:
    path = _REPO_ROOT / "core" / "search_planner_runtime.py"
    codes = _raise_failure_codes(path, "SearchPlannerRuntimeError")
    assert codes
    allowed = {member.name for member in SearchPlannerRuntimeSafeFailureCode}
    assert set(codes) == allowed


def test_every_ordinary_reachable_convergence_raise_supplies_closed_code() -> None:
    path = _REPO_ROOT / "core" / "query_production_runtime.py"
    codes = _raise_failure_codes(path, "QueryStrategyConvergenceError")
    assert codes
    allowed = {member.name for member in QueryStrategyConvergenceFailureCode}
    assert set(codes) <= allowed
    assert set(codes) == allowed


def test_materially_different_runtime_categories_project_different_codes() -> None:
    first = SearchPlannerRuntimeError(
        "private: " + _PRIVATE_FRAGMENTS[0],
        failure_code=SearchPlannerRuntimeSafeFailureCode.ADAPTER_UNAVAILABLE,
    )
    second = SearchPlannerRuntimeError(
        "private: " + _PRIVATE_FRAGMENTS[0],
        failure_code=SearchPlannerRuntimeSafeFailureCode.PROPOSAL_DIGEST_MISMATCH,
    )
    first_proj = project_initial_query_strategy_failure_for_terminal(first)
    second_proj = project_initial_query_strategy_failure_for_terminal(second)
    assert first_proj is not None and second_proj is not None
    assert first_proj["failure_origin"] == "planner_runtime"
    assert second_proj["failure_origin"] == "planner_runtime"
    assert first_proj["failure_code"] == "adapter_unavailable"
    assert second_proj["failure_code"] == "proposal_digest_mismatch"
    assert first_proj["failure_code"] != second_proj["failure_code"]


def test_materially_different_convergence_categories_project_different_codes() -> None:
    first = QueryStrategyConvergenceError(
        "private: " + _PRIVATE_FRAGMENTS[0],
        failure_code=(
            QueryStrategyConvergenceFailureCode.ANSWER_CONTRACT_BINDING_MISSING
        ),
    )
    second = QueryStrategyConvergenceError(
        "private: " + _PRIVATE_FRAGMENTS[0],
        failure_code=(
            QueryStrategyConvergenceFailureCode.QUESTION_MEANING_RECORD_MISSING
        ),
    )
    first_proj = project_initial_query_strategy_failure_for_terminal(first)
    second_proj = project_initial_query_strategy_failure_for_terminal(second)
    assert first_proj is not None and second_proj is not None
    assert first_proj["failure_code"] == "answer_contract_binding_missing"
    assert second_proj["failure_code"] == "question_meaning_record_missing"
    assert first_proj["failure_code"] != second_proj["failure_code"]


def test_classifier_consumes_owner_authored_code_not_generic_rebuild() -> None:
    runtime = SearchPlannerRuntimeError(
        "private runtime",
        failure_code=SearchPlannerRuntimeSafeFailureCode.DUPLICATE_PROPOSAL,
    )
    convergence = QueryStrategyConvergenceError(
        "private convergence",
        failure_code=QueryStrategyConvergenceFailureCode.ALLOCATION_POLICY_REQUIRED,
    )
    runtime_failure = classify_initial_query_strategy_failure(runtime)
    convergence_failure = classify_initial_query_strategy_failure(convergence)
    assert runtime_failure is not None
    assert convergence_failure is not None
    assert runtime_failure.failure_origin is InitialQueryStrategyFailureOrigin.PLANNER_RUNTIME
    assert (
        convergence_failure.failure_origin
        is InitialQueryStrategyFailureOrigin.QUERY_STRATEGY_CONVERGENCE
    )
    assert runtime_failure.failure_code == runtime.failure_code.value
    assert convergence_failure.failure_code == convergence.failure_code.value
    assert runtime_failure.failure_code != "search_planner_runtime_error"
    assert convergence_failure.failure_code != "query_strategy_convergence_error"


def test_carrier_rejects_arbitrary_and_cross_origin_codes() -> None:
    with pytest.raises(ValueError, match="not licensed"):
        InitialQueryStrategyFailure(
            failure_origin=InitialQueryStrategyFailureOrigin.PLANNER_RUNTIME,
            failure_code="fictional-private-code",
        )
    with pytest.raises(ValueError, match="not licensed"):
        InitialQueryStrategyFailure(
            failure_origin=InitialQueryStrategyFailureOrigin.QUERY_STRATEGY_CONVERGENCE,
            failure_code="fictional-private-code",
        )
    with pytest.raises(ValueError, match="not licensed"):
        InitialQueryStrategyFailure(
            failure_origin=InitialQueryStrategyFailureOrigin.PLANNER_RUNTIME,
            failure_code=(
                QueryStrategyConvergenceFailureCode.INITIAL_STRATEGIES_EMPTY.value
            ),
        )
    with pytest.raises(ValueError, match="not licensed"):
        InitialQueryStrategyFailure(
            failure_origin=InitialQueryStrategyFailureOrigin.QUERY_STRATEGY_CONVERGENCE,
            failure_code=(
                SearchPlannerRuntimeSafeFailureCode.PROPOSAL_DIGEST_MISMATCH.value
            ),
        )
    with pytest.raises(ValueError, match="not licensed"):
        InitialQueryStrategyFailure(
            failure_origin=InitialQueryStrategyFailureOrigin.RUN_KERNEL,
            failure_code=(
                QueryStrategyConvergenceFailureCode.INITIAL_STRATEGIES_EMPTY.value
            ),
        )


def test_carrier_licenses_every_owner_enum_value_for_its_origin_only() -> None:
    for member in SearchPlannerRuntimeSafeFailureCode:
        failure = InitialQueryStrategyFailure(
            failure_origin=InitialQueryStrategyFailureOrigin.PLANNER_RUNTIME,
            failure_code=member.value,
        )
        assert failure.failure_code == member.value
        with pytest.raises(ValueError, match="not licensed"):
            InitialQueryStrategyFailure(
                failure_origin=(
                    InitialQueryStrategyFailureOrigin.QUERY_STRATEGY_CONVERGENCE
                ),
                failure_code=member.value,
            )

    for member in QueryStrategyConvergenceFailureCode:
        failure = InitialQueryStrategyFailure(
            failure_origin=(
                InitialQueryStrategyFailureOrigin.QUERY_STRATEGY_CONVERGENCE
            ),
            failure_code=member.value,
        )
        assert failure.failure_code == member.value
        with pytest.raises(ValueError, match="not licensed"):
            InitialQueryStrategyFailure(
                failure_origin=InitialQueryStrategyFailureOrigin.PLANNER_RUNTIME,
                failure_code=member.value,
            )


def test_carrier_licenses_run_kernel_exact_codes() -> None:
    run_kernel_codes = {
        InitialQueryStrategyFailureCode.SEARCH_PLANNER_PRODUCTION_TRANSITION,
        InitialQueryStrategyFailureCode.INITIAL_ANSWER_CONTRACT_ACCEPTANCE_TRANSITION,
        InitialQueryStrategyFailureCode.CONTRACT_AMENDMENT_ADMISSION_TRANSITION,
        InitialQueryStrategyFailureCode.CONTRACT_AMENDMENT_APPLICATION_TRANSITION,
        InitialQueryStrategyFailureCode.QUERY_PLAN_ADMISSION_TRANSITION,
    }
    for member in run_kernel_codes:
        failure = InitialQueryStrategyFailure(
            failure_origin=InitialQueryStrategyFailureOrigin.RUN_KERNEL,
            failure_code=member.value,
        )
        assert failure.to_terminal_projection()["failure_code"] == member.value
        with pytest.raises(ValueError, match="not licensed"):
            InitialQueryStrategyFailure(
                failure_origin=InitialQueryStrategyFailureOrigin.PLANNER_RUNTIME,
                failure_code=member.value,
            )


def test_unknown_runtime_subclass_remains_generic_without_leaks() -> None:
    class _UnlicensedPlannerRuntimeFailure(SearchPlannerRuntimeError):
        """Fixture subclass without a licensed owner-authored safe code."""

    private_message = "private subclass: " + " | ".join(_PRIVATE_FRAGMENTS)
    exc = _UnlicensedPlannerRuntimeFailure(private_message)
    assert classify_initial_query_strategy_failure(exc) is None
    assert project_initial_query_strategy_failure_for_terminal(exc) is None

    # CLI recognizes SearchPlannerRuntimeError subclasses, but projection stays
    # generic unless the typed owner-authored safe code is present and licensed.
    payload = compatibility_cli._bounded_terminal_payload(
        entrypoint="scryraven",
        exc=exc,
        config=RunConfig(query=_ISCLOSE_QUERY),
    )
    terminal = payload["terminal"]
    assert terminal["code"] == "bounded_run_failed"
    assert INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY not in terminal
    assert "search_planner_failure" not in terminal
    encoded = json.dumps(payload, sort_keys=True)
    assert type(exc).__name__ not in encoded
    assert "_UnlicensedPlannerRuntimeFailure" not in encoded
    for fragment in _PRIVATE_FRAGMENTS:
        assert fragment not in encoded


def test_run_kernel_projection_unchanged() -> None:
    translated = InitialQueryStrategyFailureError(
        run_kernel_initial_planning_failure(operation="search_planner_production")
    )
    assert translated.to_terminal_projection() == {
        "schema_version": "initial_query_strategy_failure_v1",
        "boundary": "initial_query_strategy",
        "failure_origin": "run_kernel",
        "failure_code": "search_planner_production_transition",
    }
    assert (
        InitialQueryStrategyFailureCode.SEARCH_PLANNER_PRODUCTION_TRANSITION.value
        == "search_planner_production_transition"
    )


def test_invoke_run_kernel_translates_only_allowlisted_operations() -> None:
    def boom() -> None:
        raise RunKernelTransitionError(
            "private transition detail: " + " | ".join(_PRIVATE_FRAGMENTS)
        )

    with pytest.raises(InitialQueryStrategyFailureError) as caught:
        invoke_run_kernel_initial_planning("query_plan_admission", boom)
    assert caught.value.failure == run_kernel_initial_planning_failure(
        operation="query_plan_admission"
    )
    encoded = json.dumps(caught.value.to_terminal_projection(), sort_keys=True)
    for fragment in _PRIVATE_FRAGMENTS:
        assert fragment not in encoded


def test_bounded_terminal_projects_owner_codes_without_private_material() -> None:
    private_message = "private: " + " | ".join(_PRIVATE_FRAGMENTS)
    cases = (
        SearchPlannerRuntimeError(
            private_message,
            failure_code=SearchPlannerRuntimeSafeFailureCode.ADAPTER_PROPOSAL_EMPTY,
        ),
        QueryStrategyConvergenceError(
            private_message,
            failure_code=(
                QueryStrategyConvergenceFailureCode.INITIAL_STRATEGIES_EMPTY
            ),
        ),
        InitialQueryStrategyFailureError(
            run_kernel_initial_planning_failure(
                operation="query_plan_admission"
            )
        ),
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
    assert terminal["search_planner_failure"] == {
        "failure_stage": adapter.failure_stage.value,
        "failure_code": adapter.failure_code.value,
        "mechanical_rule_id": adapter.mechanical_rule_id,
        "predicate_registry_version": adapter.predicate_registry_version,
        "predicate_id": None,
        "provider_completion_posture": None,
        "strict_parse_subtype": None,
        "semantic_proposal_subtype": None,
        "branch_field_set_detail": None,
        "cleaner_modified": None,
    }
    assert INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY not in terminal
    assert classify_initial_query_strategy_failure(adapter) is None
    encoded = json.dumps(payload, sort_keys=True)
    for fragment in _PRIVATE_FRAGMENTS:
        assert fragment not in encoded


def test_bounded_terminal_projects_closed_branch_field_detail_without_model_material() -> None:
    rejected_field = "fictional-branch-field-sentinel"
    rejected_value = "fictional-model-value-sentinel"
    raw_query = "fictional-raw-query-sentinel"
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        accept_planner_model_output(
            {
                "disposition": "direct_simple",
                rejected_field: rejected_value,
            },
            user_query_text=raw_query,
            requested_mode="Balanced",
        )
    assert caught.value.failure_code is SearchPlannerModelAdapterFailureCode.INVALID_SEMANTIC_PROPOSAL
    assert caught.value.semantic_proposal_subtype is SearchPlannerSemanticProposalSubtype.BRANCH_FIELD_SET
    assert caught.value.branch_field_set_detail is (
        SearchPlannerBranchFieldSetDetail.DIRECT_SIMPLE_DISALLOWED_TOP_LEVEL
    )

    payload = compatibility_cli._bounded_terminal_payload(
        entrypoint="scryraven",
        exc=caught.value,
        config=RunConfig(query=_ISCLOSE_QUERY),
    )
    failure = payload["terminal"]["search_planner_failure"]
    assert failure["semantic_proposal_subtype"] == "branch_field_set"
    assert failure["branch_field_set_detail"] == "direct_simple_disallowed_top_level"
    encoded = json.dumps(payload, sort_keys=True)
    for private_fragment in (
        rejected_field,
        rejected_value,
        raw_query,
        *_PRIVATE_FRAGMENTS,
    ):
        assert private_fragment not in encoded


def test_unknown_failure_remains_generic_without_attribution() -> None:
    payload = compatibility_cli._bounded_terminal_payload(
        entrypoint="scryraven",
        exc=None,
        config=RunConfig(query=_ISCLOSE_QUERY),
    )
    assert payload["terminal"]["code"] == "bounded_run_failed"
    assert INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY not in payload["terminal"]
    assert "search_planner_failure" not in payload["terminal"]
    assert classify_initial_query_strategy_failure(RuntimeError("unknown")) is None


@pytest.mark.parametrize("entrypoint", ["proplex", "scryraven"])
def test_public_bounded_cli_projects_decision_grade_failure_identity(
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
    failure_to_raise: BaseException = SearchPlannerRuntimeError(
        private_message,
        failure_code=SearchPlannerRuntimeSafeFailureCode.SCHEMA_BINDING_INVALID,
    )

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
        SearchPlannerRuntimeError(
            private_message,
            failure_code=SearchPlannerRuntimeSafeFailureCode.SCHEMA_BINDING_INVALID,
        ),
        QueryStrategyConvergenceError(
            private_message,
            failure_code=QueryStrategyConvergenceFailureCode.INITIAL_STRATEGIES_EMPTY,
        ),
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
