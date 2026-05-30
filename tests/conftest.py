"""Ensure `pytest tests/` resolves `core` and sibling packages without PYTHONPATH."""

from __future__ import annotations

import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import core.pipeline_orchestrator as _pipeline_orchestrator
import core.runtime_trace_export_attachment as _runtime_trace_export_attachment


class _PipelineOrchestratorCompatModule(types.ModuleType):
    _RT_ATTACHMENT_PROPAGATED_NAMES = {
        "build_controller_diagnostics_payload",
        "build_retrieval_budget_pressure_shadow",
    }

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if name in self._RT_ATTACHMENT_PROPAGATED_NAMES:
            setattr(_runtime_trace_export_attachment, name, value)


_pipeline_orchestrator.__class__ = _PipelineOrchestratorCompatModule
_pipeline_orchestrator.DB_ENABLED = False
_pipeline_orchestrator.build_controller_diagnostics_payload = (
    _runtime_trace_export_attachment.build_controller_diagnostics_payload
)
_pipeline_orchestrator.build_retrieval_budget_pressure_shadow = (
    _runtime_trace_export_attachment.build_retrieval_budget_pressure_shadow
)
_pipeline_orchestrator._build_controller_diagnostics_payload_with_size_guard = (
    _runtime_trace_export_attachment._build_controller_diagnostics_payload_with_size_guard
)
