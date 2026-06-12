from __future__ import annotations

from pathlib import Path

from core.controller_loop_spine import (
    SOURCE_CLASS_RUNNER_DISPATCH_AUTHORITY,
    SOURCE_CLASS_SPINE_TRACE_ROLE,
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


def test_ag95f_static_source_class_trace_demoted_from_runner_authority() -> None:
    spine_source = SPINE_PATH.read_text(encoding="utf-8")
    runner_source = RUNNER_PATH.read_text(encoding="utf-8")

    assert SOURCE_CLASS_SPINE_TRACE_ROLE in spine_source
    assert SOURCE_CLASS_RUNNER_DISPATCH_AUTHORITY in spine_source
    assert "authorized_spine_action" not in runner_source
    assert "authority_lifecycle.recovery_action" in runner_source

    assert '"source_class_executor_dispatched"' in spine_source
    assert '"source_class_spine_trace_role"' in spine_source
    assert '"source_class_spine_dispatch_authority"' in spine_source
    assert '"source_class_runner_dispatch_authority"' in spine_source


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
