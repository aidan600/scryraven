from __future__ import annotations

import ast
from pathlib import Path

from core.controller_loop_spine import (
    RECOVER_MISSING_SOURCE_CLASS,
    SOURCE_CLASS_RUNNER_DISPATCH_AUTHORITY,
    SOURCE_CLASS_SPINE_TRACE_ROLE,
    build_controller_loop_spine_result,
)

ROOT = Path(__file__).resolve().parents[1]
SPINE_PATH = ROOT / "core" / "controller_loop_spine.py"
RUNNER_PATH = ROOT / "core" / "source_class_recovery_runner.py"
PHASE_DOC_PATH = (
    ROOT
    / "docs"
    / "architecture"
    / "AG95F_CONTROLLER_LOOP_SPINE_SOURCE_CLASS_TRACE_DEMOTION.md"
)


def _source_lifecycle() -> dict[str, object]:
    return {
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_blockers": [],
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_action_envelope": {
            "action_type": RECOVER_MISSING_SOURCE_CLASS,
            "required_source_class": ["official_current_rules"],
            "allowed_action": True,
        },
    }


def test_ag95f_source_class_spine_trace_is_explicitly_diagnostic() -> None:
    result = build_controller_loop_spine_result(
        checkpoint_trace={
            "available": True,
            "decision": None,
            "recommended_action_name": None,
        },
        source_class_lifecycle_trace=_source_lifecycle(),
    )
    packet = result.trace_packet

    assert packet["source_class_executor_dispatched"] is True
    assert packet["source_class_spine_trace_role"] == (
        SOURCE_CLASS_SPINE_TRACE_ROLE
    )
    assert packet["source_class_spine_dispatch_authority"] is False
    assert packet["source_class_runner_dispatch_authority"] == (
        SOURCE_CLASS_RUNNER_DISPATCH_AUTHORITY
    )


def test_ag95f_static_source_class_trace_demoted_from_runner_authority() -> None:
    spine_source = SPINE_PATH.read_text(encoding="utf-8")
    runner_source = RUNNER_PATH.read_text(encoding="utf-8")
    spine_tree = ast.parse(spine_source)

    assert SOURCE_CLASS_SPINE_TRACE_ROLE in spine_source
    assert SOURCE_CLASS_RUNNER_DISPATCH_AUTHORITY in spine_source
    assert "authorized_spine_action" not in runner_source
    assert "authority_lifecycle.recovery_action" in runner_source

    source_class_trace_returns: list[ast.Dict] = []
    for function in ast.walk(spine_tree):
        if not (
            isinstance(function, ast.FunctionDef)
            and function.name == "_build_source_class_checkpoint_gate_trace"
        ):
            continue
        source_class_trace_returns.extend(
            node for node in ast.walk(function) if isinstance(node, ast.Dict)
        )
    trace_keys = {
        key.value
        for node in source_class_trace_returns
        for key in node.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }

    assert "source_class_executor_dispatched" in trace_keys
    assert "source_class_spine_trace_role" in trace_keys
    assert "source_class_spine_dispatch_authority" in trace_keys
    assert "source_class_runner_dispatch_authority" in trace_keys


def test_ag95f_phase_doc_records_demoted_trace_contract() -> None:
    text = PHASE_DOC_PATH.read_text(encoding="utf-8")
    normalized = " ".join(text.split())

    assert "AuthorityLifecycle.recovery_action" in text
    assert "SourceClassRecoveryRunner" in text
    assert "SourceClassRecoveryExecutor" in text
    assert "source_class_spine_trace_role=diagnostic_compatibility" in text
    assert "source_class_spine_dispatch_authority=false" in text
    assert (
        "source_class_runner_dispatch_authority=authority_lifecycle.recovery_action"
        in text
    )
    assert "not runner dispatch authority" in normalized
