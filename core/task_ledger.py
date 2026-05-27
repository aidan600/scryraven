"""Passive task-ledger contracts for observed stage facts.

TaskLedger records facts supplied by callers. It does not gate, skip, recover,
retry, dispatch, schedule, or execute anything.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class TaskStatus(str, Enum):
    PLANNED = "planned"
    STARTED = "started"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple((str(key), _freeze_value(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    return deepcopy(value)


def _thaw_value(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], str)
            for item in value
        ):
            return {key: _thaw_value(item) for key, item in value}
        return [_thaw_value(item) for item in value]
    return deepcopy(value)


def _freeze_metadata(
    metadata: Mapping[str, Any] | None,
) -> tuple[tuple[str, Any], ...]:
    return tuple(
        (str(key), _freeze_value(value))
        for key, value in (metadata or {}).items()
    )


def _thaw_metadata(metadata: tuple[tuple[str, Any], ...]) -> dict[str, Any]:
    return {key: _thaw_value(value) for key, value in metadata}


@dataclass(frozen=True)
class TaskRecord:
    """One observed or planned task fact."""

    task_id: str
    module_id: str
    status: TaskStatus
    reason: str | None = None
    metadata: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "module_id": self.module_id,
            "status": self.status.value,
            "reason": self.reason,
            "metadata": _thaw_metadata(self.metadata),
        }


@dataclass(frozen=True)
class TaskLedger:
    """Append-only passive ledger for task lifecycle observations."""

    records: tuple[TaskRecord, ...] = ()

    @classmethod
    def empty(cls) -> TaskLedger:
        return cls()

    def record(
        self,
        *,
        task_id: str,
        module_id: str,
        status: TaskStatus | str,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TaskLedger:
        clean_status = status if isinstance(status, TaskStatus) else TaskStatus(status)
        return TaskLedger(
            records=(
                *self.records,
                TaskRecord(
                    task_id=str(task_id),
                    module_id=str(module_id),
                    status=clean_status,
                    reason=None if reason is None else str(reason),
                    metadata=_freeze_metadata(metadata),
                ),
            )
        )

    def record_planned(
        self,
        *,
        task_id: str,
        module_id: str,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TaskLedger:
        return self.record(
            task_id=task_id,
            module_id=module_id,
            status=TaskStatus.PLANNED,
            reason=reason,
            metadata=metadata,
        )

    def record_started(
        self,
        *,
        task_id: str,
        module_id: str,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TaskLedger:
        return self.record(
            task_id=task_id,
            module_id=module_id,
            status=TaskStatus.STARTED,
            reason=reason,
            metadata=metadata,
        )

    def record_completed(
        self,
        *,
        task_id: str,
        module_id: str,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TaskLedger:
        return self.record(
            task_id=task_id,
            module_id=module_id,
            status=TaskStatus.COMPLETED,
            reason=reason,
            metadata=metadata,
        )

    def record_skipped(
        self,
        *,
        task_id: str,
        module_id: str,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TaskLedger:
        return self.record(
            task_id=task_id,
            module_id=module_id,
            status=TaskStatus.SKIPPED,
            reason=reason,
            metadata=metadata,
        )

    def record_blocked(
        self,
        *,
        task_id: str,
        module_id: str,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TaskLedger:
        return self.record(
            task_id=task_id,
            module_id=module_id,
            status=TaskStatus.BLOCKED,
            reason=reason,
            metadata=metadata,
        )

    def record_failed(
        self,
        *,
        task_id: str,
        module_id: str,
        reason: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TaskLedger:
        return self.record(
            task_id=task_id,
            module_id=module_id,
            status=TaskStatus.FAILED,
            reason=reason,
            metadata=metadata,
        )

    def records_for(self, task_id: str) -> tuple[TaskRecord, ...]:
        return tuple(record for record in self.records if record.task_id == task_id)

    def status_counts(self) -> dict[str, int]:
        counts = {status.value: 0 for status in TaskStatus}
        for record in self.records:
            counts[record.status.value] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": [record.to_dict() for record in self.records],
            "status_counts": self.status_counts(),
        }


__all__ = [
    "TaskLedger",
    "TaskRecord",
    "TaskStatus",
]
