"""StatusWriter protocol + Streamlit-free implementations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StatusWriter(Protocol):
    def update(self, label: str) -> None: ...
    def step(self, text: str) -> None: ...
    def done(self) -> None: ...


class NullStatusWriter:
    """For headless CLI and tests — drops all status calls."""
    def update(self, label: str) -> None: pass
    def step(self, text: str) -> None: pass
    def done(self) -> None: pass
    # Backward-compat alias: pipeline.py internals call .write() on status_container
    def write(self, text: str) -> None: pass


class ListStatusWriter:
    """For unit tests — collects calls for inspection."""
    def __init__(self) -> None:
        self.log: list[tuple[str, str]] = []

    def update(self, label: str) -> None:
        self.log.append(("update", label))

    def step(self, text: str) -> None:
        self.log.append(("step", text))

    def done(self) -> None:
        self.log.append(("done", ""))

    # Backward-compat alias: pipeline.py internals call .write() on status_container
    def write(self, text: str) -> None:
        self.log.append(("step", text))
