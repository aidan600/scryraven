from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

import pytest

import core.runtime_trace_projection_assembly as projection_assembly
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.ordinary_continuation_candidate import (
    EVALUATOR_NEXT_QUERIES,
    EXPANDER_COMPONENT_QUERIES,
    ORDINARY_CONTINUATION_TRACE_KEY,
    SCOUT_DIRECTED_QUERIES,
)
from core.retrieval_batch_projection import (
    ORDINARY_EVALUATOR_GAP_QUERIES,
    ORDINARY_EXPANDER_COMPONENT_QUERIES,
    ORDINARY_SCOUT_DIRECTED_QUERIES,
    RETRIEVAL_BATCH_PROJECTION_TRACE_KEY,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)
from tests.test_retrieval_batch_projection_ag46b import (
    _checkpoint,
    _inner,
    _ordinary,
)
from tests.test_targeted_retrieval_runtime_ag43b import _run_passive_case

_ROOT = Path(__file__).resolve().parents[1]
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"
_ASSEMBLY_PATH = _ROOT / "core" / "runtime_trace_projection_assembly.py"
_SPINE_PATH = _ROOT / "core" / "controller_loop_spine.py"


def _execution_trace(
    source_path: str = EVALUATOR_NEXT_QUERIES,
    queries: tuple[str, ...] = ("Acme Widget support matrix",),
) -> dict[str, Any]:
    return {
        "run_id": "ag46c",
        "unrelated_trace": {"kept": True},
        EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: _checkpoint(),
        ORDINARY_CONTINUATION_TRACE_KEY: _ordinary(source_path, queries),
    }


def _runtime_case(
    tmp_path: Path,
    source_path: str,
) -> tuple[dict[str, Any], Any]:
    if source_path == EVALUATOR_NEXT_QUERIES:
        outcome, harness = _run_passive_case(
            tmp_path,
            evaluator_responses=[
                {
                    "is_sufficient": False,
                    "new_queries": ["Acme Widget migration timeline"],
                }
            ],
        )
    elif source_path == EXPANDER_COMPONENT_QUERIES:
        outcome, harness = _run_passive_case(
            tmp_path,
            expander_queries=("Acme Widget component warranty evidence",),
        )
    else:
        outcome, harness = _run_passive_case(
            tmp_path,
            router_report_type="quantitative_comparison",
            scout_queries=("Acme Widget benchmark adoption data",),
        )
    return outcome.execution_trace, harness


def test_ag46c_helper_attaches_retrieval_batch_projection_trace() -> None:
    execution_trace = _execution_trace()

    returned = attach_passive_runtime_projection_traces(execution_trace)
    projection = _inner(returned[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY])

    assert returned is execution_trace
    assert projection["selected_lane"] == ORDINARY_EVALUATOR_GAP_QUERIES
    assert projection["batch_status"] == "authorized"
    assert projection["runtime_behavior_changed"] is False


def test_ag46c_helper_mirrors_projection_into_checkpoint_trace() -> None:
    execution_trace = _execution_trace()

    attach_passive_runtime_projection_traces(execution_trace)

    projection_trace = execution_trace[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY]
    checkpoint = execution_trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]
    assert checkpoint[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY] == projection_trace


def test_ag46c_helper_projection_exception_is_non_fatal(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    execution_trace = _execution_trace()

    def _raise_projection_error(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("projection boom")

    monkeypatch.setattr(
        projection_assembly,
        "build_retrieval_batch_projection_trace",
        _raise_projection_error,
    )

    with caplog.at_level(
        logging.WARNING,
        logger="core.runtime_trace_projection_assembly",
    ):
        returned = attach_passive_runtime_projection_traces(execution_trace)

    assert returned is execution_trace
    assert RETRIEVAL_BATCH_PROJECTION_TRACE_KEY not in execution_trace
    assert "Non-fatal retrieval-batch passive projection omitted" in caplog.text


def test_ag46c_helper_preserves_unrelated_trace_contents() -> None:
    execution_trace = _execution_trace()
    unrelated = execution_trace["unrelated_trace"]

    returned = attach_passive_runtime_projection_traces(execution_trace)

    assert returned is execution_trace
    assert returned["unrelated_trace"] is unrelated
    assert returned["unrelated_trace"] == {"kept": True}


@pytest.mark.parametrize(
    ("name", "source_path", "expected_lane"),
    [
        ("evaluator", EVALUATOR_NEXT_QUERIES, ORDINARY_EVALUATOR_GAP_QUERIES),
        ("expander", EXPANDER_COMPONENT_QUERIES, ORDINARY_EXPANDER_COMPONENT_QUERIES),
        ("scout", SCOUT_DIRECTED_QUERIES, ORDINARY_SCOUT_DIRECTED_QUERIES),
    ],
)
def test_ag46c_runtime_continuation_projection_shape_matches_ag46b(
    tmp_path: Path,
    name: str,
    source_path: str,
    expected_lane: str,
) -> None:
    trace, _harness = _runtime_case(tmp_path / name, source_path)
    projection_trace = trace[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY]
    projection = _inner(projection_trace)
    checkpoint = trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY]

    assert checkpoint[RETRIEVAL_BATCH_PROJECTION_TRACE_KEY] == projection_trace
    assert projection_trace["schema_version"] == "retrieval_batch_projection_ag46b_v1"
    assert projection_trace["trace_mode"] == "passive_runtime_visibility"
    assert projection["selected_lane"] == expected_lane
    assert projection["batch_status"] == "authorized"
    assert projection["authorization"]["dispatch_authorized"] is True
    assert projection["provider_policy_unchanged"] is True
    assert projection["depth_policy_unchanged"] is True
    assert projection["query_generation_unchanged"] is True
    assert projection["prompt_unchanged"] is True
    assert projection["runtime_behavior_changed"] is False
    assert projection["targeted_retrieval_executor_dispatched"] is False
    assert projection["retrieve_targeted_provider_role_used"] is False


def test_ag46c_runtime_dispatch_surfaces_remain_unchanged(
    tmp_path: Path,
) -> None:
    trace, harness = _runtime_case(tmp_path, EVALUATOR_NEXT_QUERIES)

    assert len(harness.search_calls) == 2
    assert [call["provider_role"] for call in harness.search_calls] == [
        "main_retrieval",
        "main_retrieval",
    ]
    assert [call["search_depth"] for call in harness.search_calls] == [
        "basic",
        "basic",
    ]
    assert [call["queries"] for call in harness.search_calls] == [
        trace["queries_per_iteration"]["1"],
        trace["queries_per_iteration"]["2"],
    ]
    assert trace["final_output_preview"]
    assert trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
        "targeted_retrieval_executor_dispatched"
    ] is False
    assert "retrieve_targeted" not in {
        call["provider_role"] for call in harness.search_calls
    }


def test_ag46c_static_pipeline_uses_projection_assembly_boundary() -> None:
    source = _PIPELINE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.setdefault(node.module, set()).update(
                alias.name for alias in node.names
            )

    assert "attach_runtime_trace_export_compatibility_payloads" in imported.get(
        "core.runtime_trace_export_attachment",
        set(),
    )
    assert "attach_passive_runtime_projection_traces(" not in source
    assert "build_retrieval_batch_projection_trace" not in source
    assert "RETRIEVAL_BATCH_PROJECTION_TRACE_KEY" not in source

    attachment_source = (
        _PIPELINE_PATH.parent / "runtime_trace_export_attachment.py"
    ).read_text(encoding="utf-8")
    attachment_tree = ast.parse(attachment_source)
    attachment_imported: dict[str, set[str]] = {}
    for node in ast.walk(attachment_tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            attachment_imported.setdefault(node.module, set()).update(
                alias.name for alias in node.names
            )
    assert "attach_passive_runtime_projection_traces" in attachment_imported.get(
        "core.runtime_trace_projection_assembly",
        set(),
    )


def test_ag46c_static_projection_assembly_keeps_protected_imports_out() -> None:
    source = _ASSEMBLY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {
        "core.pipeline_orchestrator",
        "core.providers",
        "core.prompts",
        "core.db",
        "core.cache",
        "core.output",
        "core.secrets",
        "core.source_class_recovery_executor",
        "core.conflict_resolution_executor",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert forbidden.isdisjoint(imported)
    assert "process_search_queries" not in source
    assert "run_pipeline" not in source
    assert "provider_role = \"retrieve_targeted\"" not in source


def test_ag46c_static_controller_loop_spine_remains_outside_projection_assembly() -> None:
    assembly_source = _ASSEMBLY_PATH.read_text(encoding="utf-8")
    spine_source = _SPINE_PATH.read_text(encoding="utf-8")

    assert "controller_loop_spine" not in assembly_source
    assert "runtime_trace_projection_assembly" not in spine_source
