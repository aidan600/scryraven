"""Inert delegation and task-result contracts.

These records describe possible future delegation surfaces. They contain no
runtime hook, provider hook, model hook, retry loop, or active dispatch method.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class DelegationMode(str, Enum):
    SHADOW = "shadow"
    PASSIVE = "passive"


class TaskResultStatus(str, Enum):
    OBSERVED = "observed"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"


def _copy_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(metadata or {}))


@dataclass(frozen=True)
class DelegationAction:
    """Passive description of a future delegated task candidate."""

    action_id: str
    task_id: str
    target_module_id: str
    reason: str | None = None
    mode: DelegationMode = DelegationMode.SHADOW
    active: bool = False
    metadata: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "task_id": self.task_id,
            "target_module_id": self.target_module_id,
            "reason": self.reason,
            "mode": self.mode.value,
            "active": self.active,
            "metadata": _copy_metadata(self.metadata),
        }


@dataclass(frozen=True)
class TaskResult:
    """Structured passive outcome record for a task."""

    task_id: str
    module_id: str
    status: TaskResultStatus = TaskResultStatus.OBSERVED
    summary: str | None = None
    reason: str | None = None
    metadata: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "module_id": self.module_id,
            "status": self.status.value,
            "summary": self.summary,
            "reason": self.reason,
            "metadata": _copy_metadata(self.metadata),
        }


__all__ = [
    "DelegationAction",
    "DelegationMode",
    "TaskResult",
    "TaskResultStatus",
]
