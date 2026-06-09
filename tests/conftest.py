"""Ensure `pytest tests/` resolves `core` and sibling packages without PYTHONPATH."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import core.pipeline_orchestrator as _pipeline_orchestrator
except ImportError:
    _pipeline_orchestrator = None

if _pipeline_orchestrator is not None:
    _pipeline_orchestrator.DB_ENABLED = False
