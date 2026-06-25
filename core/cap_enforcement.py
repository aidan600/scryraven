"""Optional ordinary-run cap enforcement for bounded validation prep."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class RunCapExceeded(RuntimeError):
    """Raised before an operation that would exceed an explicit run cap."""


@dataclass(slots=True)
class RunCapPolicy:
    """Mutable per-run cap policy consumed by ordinary product execution."""

    max_search_dispatches: int
    max_fetch_read_operations: int
    max_author_model_calls: int
    max_smart_search_judgment_model_calls: int
    max_retries: int
    search_dispatches: int = 0
    fetch_read_operations: int = 0
    author_model_calls: int = 0
    smart_search_judgment_model_calls: int = 0
    retries: int = 0
    facts: list[str] = field(default_factory=list)

    def mark_search_dispatch(self) -> None:
        self._mark("search_dispatches", self.max_search_dispatches)

    def mark_fetch_read_operation(self) -> None:
        self._mark("fetch_read_operations", self.max_fetch_read_operations)

    def mark_author_model_call(self) -> None:
        self._mark("author_model_calls", self.max_author_model_calls)

    def mark_smart_search_judgment_model_call(self) -> None:
        self._mark(
            "smart_search_judgment_model_calls",
            self.max_smart_search_judgment_model_calls,
        )

    def mark_retry(self) -> None:
        self._mark("retries", self.max_retries)

    def should_disable_utilization_retry(self) -> bool:
        return self.max_retries == 0

    def record_fact(self, fact: str) -> None:
        clean = str(fact or "").strip()
        if clean and clean not in self.facts:
            self.facts.append(clean)

    def observed_counts(self, *, enforcement: str = "active") -> dict[str, Any]:
        return {
            "search_dispatches": self.search_dispatches,
            "fetch_read_operations": self.fetch_read_operations,
            "author_model_calls": self.author_model_calls,
            "smart_search_judgment_model_calls": (
                self.smart_search_judgment_model_calls
            ),
            "retries": self.retries,
            "enforcement": enforcement,
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {
            "run_cap_enforcement": {
                **self.observed_counts(),
                "max_search_dispatches": self.max_search_dispatches,
                "max_fetch_read_operations": self.max_fetch_read_operations,
                "max_author_model_calls": self.max_author_model_calls,
                "max_smart_search_judgment_model_calls": (
                    self.max_smart_search_judgment_model_calls
                ),
                "max_retries": self.max_retries,
                "facts": list(self.facts),
            }
        }

    def _mark(self, attr: str, maximum: int) -> None:
        next_value = int(getattr(self, attr)) + 1
        if next_value > int(maximum):
            raise RunCapExceeded(f"{attr} cap exceeded")
        setattr(self, attr, next_value)
