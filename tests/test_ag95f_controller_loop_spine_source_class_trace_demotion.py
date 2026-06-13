from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPINE_PATH = ROOT / "core" / "controller_loop_spine.py"
RUNNER_PATH = ROOT / "core" / "source_class_recovery_runner.py"
PHASE_DOC_PATH = (
    ROOT
    / "docs"
    / "architecture"
    / "AG95F_CONTROLLER_LOOP_SPINE_SOURCE_CLASS_TRACE_DEMOTION.md"
)

RETIRED_SOURCE_CLASS_PACKET_FIELDS = {
    "source_class_executor_dispatched",
    "official_canonical_dispatch_fallback",
    "source_class_spine_trace_role",
    "source_class_spine_dispatch_authority",
    "source_class_runner_dispatch_authority",
}


def test_ag95f_static_source_class_trace_fields_retired_from_runtime() -> None:
    spine_source = SPINE_PATH.read_text(encoding="utf-8")
    runner_source = RUNNER_PATH.read_text(encoding="utf-8")

    assert "authorized_spine_action" not in runner_source
    assert "authority_lifecycle.recovery_action" in runner_source
    assert "controller_loop_spine" not in runner_source

    for field in RETIRED_SOURCE_CLASS_PACKET_FIELDS:
        assert field not in spine_source
        assert field not in runner_source

    for shared_active_gate_field in ("executor_dispatched", "executed_action_name"):
        assert shared_active_gate_field not in runner_source


def test_ag95f_phase_doc_routes_current_contract_to_ag95i() -> None:
    text = PHASE_DOC_PATH.read_text(encoding="utf-8")
    normalized = " ".join(text.split())

    assert "AuthorityLifecycle.recovery_action" in text
    assert "SourceClassRecoveryRunner" in text
    assert "SourceClassRecoveryExecutor" in text
    assert "AG-95I" in text
    assert "not runner dispatch authority" in normalized
