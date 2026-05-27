"""Streamlit adapters for core status protocols (UI layer only)."""


class StreamlitStatusWriter:
    """Adapts ``st.status`` to the StatusWriter protocol."""

    def __init__(self, st_status: object) -> None:
        self._status = st_status

    def update(self, label: str) -> None:
        self._status.update(label=label, state="running")

    def step(self, text: str) -> None:
        self._status.write(text)

    def done(self) -> None:
        self._status.update(label="Pipeline complete", state="complete")

    # Backward-compat alias used by core/pipeline.py internals
    def write(self, text: str) -> None:
        self._status.write(text)
