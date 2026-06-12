from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.controller_loop_spine import build_controller_loop_spine_result
from core.controller_provider_search_allocation import (
    PROVIDER_SEARCH_ALLOCATION_ACTION,
    PROVIDER_SEARCH_ALLOCATION_TRACE_KEY,
)
from core.controller_recovery_decision import (
    REQUEST_PROVIDER_SEARCH_REVIEW,
    RETRY_RECOVERY,
    STOP_INSUFFICIENT,
    build_controller_recovery_decision,
)
from core.run_controller import RetrievalAction, RunController
from core.source_class_recovery_runner import (
    SourceClassRecoveryRunnerContext,
    run_source_class_recovery_dispatch,
)

_ROOT = Path(__file__).resolve().parents[1]
_CORE = _ROOT / "core"
_RUNNER_PATH = _CORE / "source_class_recovery_runner.py"
_EXECUTOR_PATH = _CORE / "source_class_recovery_executor.py"
_ORCHESTRATOR_PATH = _CORE / "pipeline_orchestrator.py"

_LEGAL_PRIMARY = "legal_or_regulatory_text"
_OFFICIAL_CURRENT = "official_current_rules"
_SOURCE_CLASSES = [_LEGAL_PRIMARY, _OFFICIAL_CURRENT]
_RECOVERY_QUERIES = [
    "Denmark infant formula additives official legal text current rules",
    "Danish competent authority infant formula permitted additives regulation",
]
_EXECUTOR_UNEXECUTABLE = "source_class_recovery_executor_action_unexecutable"


def _canonical_lifecycle(**overrides: Any) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "required_source_classes": list(_SOURCE_CLASSES),
        "unsatisfied_required_source_classes": list(_SOURCE_CLASSES),
        "source_obligation_status": "official_current_required_unmet",
        "active_source_class_recovery_considered": True,
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_used": False,
        "active_source_class_recovery_execution_attempted": False,
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_reason": (
            "missing_expected_source_class:legal_or_regulatory_text"
        ),
        "active_source_class_recovery_skip_reason": None,
        "active_source_class_recovery_blockers": [],
        "active_source_class_recovery_missing_classes": list(_SOURCE_CLASSES),
        "active_source_class_recovery_queries": list(_RECOVERY_QUERIES),
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_search_depth": "basic",
        "active_source_class_recovery_attempt_count": 1,
        "active_source_class_recovery_action_envelope": {
            "action_type": RECOVER_MISSING_SOURCE_CLASS,
            "required_source_class": list(_SOURCE_CLASSES),
            "allowed_action": True,
            "blockers": [],
        },
        "authority_lifecycle_required_recovery_allowed": True,
        "authority_lifecycle_execution_attempted": False,
        "authority_lifecycle_execution_blocked": False,
        "recovery_slot_available": True,
        "candidate_return_status": "not_attempted",
        "candidate_acquisition_considered": False,
        "candidate_acquisition_eligible": False,
        "candidate_acquisition_used": False,
        "acquisition_attempted": False,
        "authority_lifecycle": {
            "requirement_id": "ag95d-source-class-dispatch",
            "required_authority": _OFFICIAL_CURRENT,
            "recovery_needed": "required",
            "recovery_action": {
                "action_type": RECOVER_MISSING_SOURCE_CLASS,
                "approved": True,
            },
            "execution_state": {"state": "approved_pending_execution"},
            "explicit_blockers": [],
            "final_posture": "pending_recovery",
        },
    }
    for key, value in overrides.items():
        trace[key] = value
    return trace


def _controller_with_action(
    *,
    queries: list[str] | None = None,
    search_depth: str | None = "basic",
    provider_role: str | None = "source_class_recovery",
    envelope: dict[str, Any] | None = None,
) -> RunController:
    controller = RunController()
    controller.state.active_source_class_recovery_eligible = True
    metadata: dict[str, Any] = {}
    if envelope is not None:
        metadata["controller_action_envelope"] = dict(envelope)
    else:
        metadata["controller_action_envelope"] = {
            "action_type": RECOVER_MISSING_SOURCE_CLASS,
            "allowed_action": True,
            "required_source_class": list(_SOURCE_CLASSES),
        }
    controller.record_retrieval_action(
        RetrievalAction(
            name="source_class_recovery",
            queries=list(_RECOVERY_QUERIES if queries is None else queries),
            provider_role=provider_role,
            search_depth=search_depth,
            active=True,
            shadow=False,
            signals={
                "active_source_class_recovery_missing_classes": list(_SOURCE_CLASSES)
            },
            metadata=metadata,
        )
    )
    return controller


def _context(
    *,
    lifecycle: dict[str, Any],
    controller: RunController | None = None,
    controller_recovery_decision: Any | None = None,
    process_search_queries: Any = None,
    search_providers: list[str] | None = None,
    all_passages: list[dict[str, Any]] | None = None,
    seen_urls: set[str] | None = None,
    provider_diagnostics: list[dict[str, Any]] | None = None,
    retrieval_pass_records: list[dict[str, Any]] | None = None,
) -> SourceClassRecoveryRunnerContext:
    def fail_search(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("AG-95D fixture must not run provider/search")

    return SourceClassRecoveryRunnerContext(
        controller=controller or _controller_with_action(),
        controller_recovery_decision=controller_recovery_decision,
        lifecycle_trace=lifecycle,
        process_search_queries=(
            fail_search if process_search_queries is None else process_search_queries
        ),
        all_passages=all_passages if all_passages is not None else [],
        intent="general",
        complexity="medium",
        results_per_query=5,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[],
        seen_urls=seen_urls if seen_urls is not None else set(),
        collected_images=set(),
        embed_provider="fixture",
        embed_model="fixture",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        search_providers=(
            ["offline-fixture"] if search_providers is None else search_providers
        ),
        exa_domain_filter=None,
        entity_hint="Denmark infant formula additives",
        provider_diagnostics=(
            provider_diagnostics if provider_diagnostics is not None else []
        ),
        retrieval_pass_records=(
            retrieval_pass_records if retrieval_pass_records is not None else []
        ),
    )


def _search_recorder(calls: list[list[str]]) -> Any:
    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        _search_depth: str,
        _results_per_query: int,
        _include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        seen_urls: set[str],
        _collected_images: set[str],
        *_args: Any,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        calls.append(list(queries))
        seen_urls.add("https://agency.example/ag95d-current-rule")
        return [
            {
                "title": "Official current rule",
                "url": "https://agency.example/ag95d-current-rule",
                "text": "Offline official current regulatory fixture.",
                "source_tier": "official",
                "source_class": _OFFICIAL_CURRENT,
            }
        ]

    return fake_search


def _without_canonical_permission(**overrides: Any) -> dict[str, Any]:
    lifecycle = _canonical_lifecycle(
        authority_lifecycle=None,
        authority_lifecycle_required_recovery_allowed=True,
        active_source_class_recovery_eligible=True,
        active_source_class_recovery_official_canonical_admitted=True,
        admission_used=True,
        source_class_recovery_execution_admitted=True,
        source_class_recovery_attempt_expected=True,
        report_source_class_recovery_used=True,
        export_source_class_recovery_used=True,
        diagnostic_recovery_projection="recover_missing_source_class",
    )
    lifecycle.update(overrides)
    return lifecycle


def test_ag95d_positive_canonical_recovery_dispatches_exactly_once() -> None:
    lifecycle = _canonical_lifecycle()
    calls: list[list[str]] = []
    all_passages: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    first = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            process_search_queries=_search_recorder(calls),
            all_passages=all_passages,
            seen_urls=seen_urls,
        )
    )
    assert lifecycle["source_class_recovery_dispatch_authorized"] is True
    assert lifecycle["source_class_recovery_dispatch_reason"] == (
        "canonical_authority_lifecycle_recovery_action"
    )

    second = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            process_search_queries=_search_recorder(calls),
            all_passages=all_passages,
            seen_urls=seen_urls,
        )
    )

    assert first.source_class_recovery_execution == {
        "attempted": True,
        "result_count": 1,
        "new_url_count": 1,
    }
    assert second.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert calls == [list(_RECOVERY_QUERIES)]
    assert len(all_passages) == 1
    assert lifecycle["source_class_recovery_dispatch_authority"] == (
        "authority_lifecycle.recovery_action"
    )
    assert lifecycle["source_class_recovery_dispatch_authorized"] is False
    assert lifecycle["source_class_recovery_dispatch_reason"] == (
        "canonical_recovery_already_attempted"
    )
    assert lifecycle["authority_lifecycle_execution_state"] == "attempted"
    assert lifecycle["active_source_class_recovery_used"] is True


def test_ag95d_canonical_permission_absence_blocks_demoted_authorizers() -> None:
    lifecycle = _without_canonical_permission()
    decision = build_controller_recovery_decision(lifecycle)
    spine = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": {"action_name": RECOVER_MISSING_SOURCE_CLASS},
            "recommended_action_name": RECOVER_MISSING_SOURCE_CLASS,
        },
        source_class_lifecycle_trace=lifecycle,
    )
    calls: list[list[str]] = []

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            controller_recovery_decision=decision,
            process_search_queries=_search_recorder(calls),
        )
    )

    assert decision.decision == RETRY_RECOVERY
    assert spine.authorized_dispatch == RECOVER_MISSING_SOURCE_CLASS
    assert spine.source_class_executor_dispatched is True
    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is False
    assert calls == []
    assert lifecycle["recovery_decision"] == RETRY_RECOVERY
    assert lifecycle["recovery_decision_diagnostic_only"] is True
    assert lifecycle["source_class_recovery_dispatch_authority"] == (
        "authority_lifecycle.recovery_action"
    )
    assert lifecycle["source_class_recovery_dispatch_reason"] == (
        "canonical_authority_lifecycle_absent"
    )


@pytest.mark.parametrize(
    ("name", "mutate", "expected_reason"),
    [
        (
            "recovery not required",
            lambda lifecycle: lifecycle["authority_lifecycle"].update(
                {"recovery_needed": "not_required"}
            ),
            "canonical_recovery_not_required",
        ),
        (
            "wrong action type",
            lambda lifecycle: lifecycle["authority_lifecycle"]["recovery_action"].update(
                {"action_type": "recover_weak_corpus"}
            ),
            "canonical_recovery_action_absent",
        ),
        (
            "action not approved",
            lambda lifecycle: lifecycle["authority_lifecycle"]["recovery_action"].update(
                {"approved": False}
            ),
            "canonical_recovery_action_not_approved",
        ),
        (
            "execution blocked",
            lambda lifecycle: lifecycle["authority_lifecycle"].update(
                {"execution_state": {"state": "blocked"}}
            ),
            "canonical_recovery_execution_blocked",
        ),
        (
            "already attempted",
            lambda lifecycle: lifecycle.update(
                {"active_source_class_recovery_execution_attempted": True}
            ),
            "canonical_recovery_already_attempted",
        ),
    ],
)
def test_ag95d_canonical_denial_blocks_source_class_recovery(
    name: str,
    mutate: Any,
    expected_reason: str,
) -> None:
    lifecycle = _canonical_lifecycle()
    mutate(lifecycle)
    calls: list[list[str]] = []

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            process_search_queries=_search_recorder(calls),
        )
    )

    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }, name
    assert calls == [], name
    assert lifecycle["source_class_recovery_dispatch_authorized"] is False, name
    assert lifecycle["source_class_recovery_dispatch_reason"] == expected_reason, name


@pytest.mark.parametrize(
    ("name", "context_overrides", "controller", "expected_blocker"),
    [
        (
            "missing process_search_queries callable",
            {"process_search_queries": "not-callable"},
            _controller_with_action(),
            "missing_process_search_queries",
        ),
        (
            "missing search providers",
            {"search_providers": []},
            _controller_with_action(),
            "missing_search_providers",
        ),
        (
            "missing executor queries",
            {"process_search_queries": lambda *_args, **_kwargs: []},
            _controller_with_action(queries=[]),
            "missing_executor_queries",
        ),
        (
            "missing executor search depth",
            {"process_search_queries": lambda *_args, **_kwargs: []},
            _controller_with_action(search_depth=None),
            "missing_executor_search_depth",
        ),
    ],
)
def test_ag95d_mechanical_executor_skip_reasons_block_without_controller_policy_veto(
    name: str,
    context_overrides: dict[str, Any],
    controller: RunController,
    expected_blocker: str,
) -> None:
    lifecycle = _canonical_lifecycle()

    result = run_source_class_recovery_dispatch(
        _context(lifecycle=lifecycle, controller=controller, **context_overrides)
    )

    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }, name
    assert lifecycle["source_class_recovery_dispatch_authorized"] is True, name
    assert lifecycle["source_class_recovery_dispatch_reason"] == (
        "canonical_authority_lifecycle_recovery_action"
    ), name
    assert expected_blocker in lifecycle["active_source_class_recovery_blockers"], name
    assert lifecycle["active_source_class_recovery_skip_reason"] in {
        expected_blocker,
        _EXECUTOR_UNEXECUTABLE,
    }, name
    assert "recovery_decision" not in lifecycle, name
    assert "recovery_decision_trace" not in lifecycle, name


@pytest.mark.parametrize(
    ("name", "controller", "expected_message"),
    [
        (
            "invalid action envelope",
            _controller_with_action(envelope={}),
            "source_class_recovery action has unexpected action envelope",
        ),
        (
            "unexpected provider role",
            _controller_with_action(provider_role="main_retrieval"),
            "source_class_recovery action has unexpected provider role",
        ),
    ],
)
def test_ag95d_invalid_executor_action_shapes_fail_mechanically(
    name: str,
    controller: RunController,
    expected_message: str,
) -> None:
    lifecycle = _canonical_lifecycle()
    calls: list[list[str]] = []

    with pytest.raises(RuntimeError, match=expected_message):
        run_source_class_recovery_dispatch(
            _context(
                lifecycle=lifecycle,
                controller=controller,
                process_search_queries=_search_recorder(calls),
            )
        )

    assert calls == [], name
    assert lifecycle["source_class_recovery_dispatch_authorized"] is True, name
    assert lifecycle["source_class_recovery_dispatch_reason"] == (
        "canonical_authority_lifecycle_recovery_action"
    ), name
    assert "recovery_decision" not in lifecycle, name
    assert "recovery_decision_trace" not in lifecycle, name


@pytest.mark.parametrize(
    ("name", "fields"),
    [
        (
            "official admission booleans",
            {
                "active_source_class_recovery_official_canonical_admitted": True,
                "admission_used": True,
                "source_class_recovery_execution_admitted": True,
            },
        ),
        (
            "source class lifecycle eligibility booleans",
            {
                "active_source_class_recovery_eligible": True,
                "source_class_recovery_eligible": True,
                "active_source_class_recovery_queries": list(_RECOVERY_QUERIES),
            },
        ),
        (
            "report export diagnostic fields",
            {
                "source_class_recovery_recommended": True,
                "source_class_recovery_used": True,
                "source_survival_final_evidence_official_or_canonical_count": 1,
                "source_survival_final_citation_official_or_canonical_count": 1,
                "controller_recovery_decision": RETRY_RECOVERY,
            },
        ),
    ],
)
def test_ag95d_demoted_fields_cannot_authorize_without_canonical_action(
    name: str,
    fields: dict[str, Any],
) -> None:
    lifecycle = _without_canonical_permission(**fields)
    calls: list[list[str]] = []

    result = run_source_class_recovery_dispatch(
        _context(lifecycle=lifecycle, process_search_queries=_search_recorder(calls))
    )

    assert result.source_class_recovery_execution["attempted"] is False, name
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is False, name
    assert calls == [], name
    assert lifecycle["source_class_recovery_dispatch_reason"] == (
        "canonical_authority_lifecycle_absent"
    ), name


def test_ag95d_controller_recovery_decision_cannot_veto_canonical_action() -> None:
    lifecycle = _canonical_lifecycle(
        active_source_class_recovery_blockers=[
            "blocked_by_provider_policy_change_required"
        ]
    )
    decision = build_controller_recovery_decision(deepcopy(lifecycle))
    calls: list[list[str]] = []

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            controller_recovery_decision=decision,
            process_search_queries=_search_recorder(calls),
        )
    )

    assert decision.decision == STOP_INSUFFICIENT
    assert result.source_class_recovery_execution["attempted"] is True
    assert calls == [list(_RECOVERY_QUERIES)]
    assert lifecycle["recovery_decision"] == STOP_INSUFFICIENT
    assert lifecycle["recovery_decision_diagnostic_only"] is True
    assert lifecycle["source_class_recovery_dispatch_authorized"] is True


def test_ag95d_provider_review_path_remains_protected_without_canonical_action() -> None:
    lifecycle = _without_canonical_permission(
        active_source_class_recovery_execution_attempted=True,
        active_source_class_recovery_result_count=0,
        candidate_return_status="zero_candidates",
        recovery_slot_available=False,
    )
    decision = build_controller_recovery_decision(lifecycle)
    calls: list[list[str]] = []

    result = run_source_class_recovery_dispatch(
        _context(
            lifecycle=lifecycle,
            controller=_controller_with_action(queries=["official current fixture"]),
            controller_recovery_decision=decision,
            process_search_queries=_search_recorder(calls),
        )
    )

    assert decision.decision == REQUEST_PROVIDER_SEARCH_REVIEW
    assert result.source_class_recovery_execution == {
        "attempted": False,
        "result_count": 0,
        "new_url_count": 0,
    }
    assert result.provider_search_allocation is not None
    assert result.provider_search_allocation.allocated is True
    assert result.provider_search_allocation.reason == PROVIDER_SEARCH_ALLOCATION_ACTION
    assert PROVIDER_SEARCH_ALLOCATION_TRACE_KEY in lifecycle
    assert calls == [["official current fixture"]]
    assert lifecycle["source_class_recovery_dispatch_authority"] == (
        "authority_lifecycle.recovery_action"
    )
    assert lifecycle["source_class_recovery_dispatch_authorized"] is False


def test_ag95d_static_dispatch_ownership_guards() -> None:
    runner_source = _RUNNER_PATH.read_text(encoding="utf-8")
    executor_source = _EXECUTOR_PATH.read_text(encoding="utf-8")

    assert {
        field.name for field in fields(SourceClassRecoveryRunnerContext)
    }.isdisjoint({"authorized_spine_action"})
    assert "authorized_spine_action == RECOVER_MISSING_SOURCE_CLASS" not in (
        runner_source
    )
    assert "authorized_spine_action" not in runner_source
    assert "build_controller_recovery_decision" not in executor_source
    assert "controller_recovery_executor_allows_attempt" not in executor_source
    assert "authority_lifecycle.recovery_action" in runner_source


def test_ag95d_report_export_visibility_modules_cannot_build_dispatch_decision() -> None:
    modules = [
        path
        for path in _CORE.glob("*.py")
        if any(
            token in path.stem
            for token in ("report", "export", "visibility", "projection")
        )
    ]
    assert modules

    violations: dict[str, list[str]] = {}
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if (
                    node.module == "core.controller_recovery_decision"
                    and any(
                        alias.name == "build_controller_recovery_decision"
                        for alias in node.names
                    )
                ):
                    names.append("import build_controller_recovery_decision")
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    call_name = func.id
                elif isinstance(func, ast.Attribute):
                    call_name = func.attr
                else:
                    call_name = ""
                if call_name == "build_controller_recovery_decision":
                    names.append("call build_controller_recovery_decision")
        if names:
            violations[path.name] = names

    assert violations == {}


def test_ag95d_pipeline_does_not_reintroduce_source_class_spine_policy_branch() -> None:
    source = _ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    violations: list[int] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        left_is_spine_action = (
            isinstance(node.left, ast.Name)
            and node.left.id == "authorized_spine_action"
        )
        compares_to_source_class_recovery = any(
            (
                isinstance(comparator, ast.Name)
                and comparator.id == "RECOVER_MISSING_SOURCE_CLASS"
            )
            or (
                isinstance(comparator, ast.Constant)
                and comparator.value == RECOVER_MISSING_SOURCE_CLASS
            )
            for comparator in node.comparators
        )
        if left_is_spine_action and compares_to_source_class_recovery:
            violations.append(node.lineno)

    assert violations == []
    assert source.count("run_source_class_recovery_dispatch(") == 1
    assert "source_class_executor_dispatched" not in source
