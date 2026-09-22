"""Fresh research decisions with ephemeral or durable application-level custody."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass

from core.exa_transport import DiscoveryCandidate, search_exa
from core.linkup_transport import fetch_linkup
from core.transport import FetchedMaterial
from scryraven.research import RunLimits, _run_turn
from scryraven.results import CompletedAnswer
from scryraven.session_store import (
    SessionMetadata,
    SessionState,
    SessionStore,
    SessionTurn,
    SQLiteSessionStore,
)
from scryraven.sources import Evidence


@dataclass(frozen=True)
class _Snapshot:
    state: SessionState
    metadata: SessionMetadata | None = None


class ResearchSession:
    """Sequential ask(question) calls with fresh decisions over a retained corpus.

    Only completed answers commit state (including partial/unable answers).
    Acquisitions are immutable, including full parents of exact targeted views.
    History is copied on inspection so callers cannot mutate historical records.
    The constructor is ephemeral. create/open opt into a SessionStore. Persistent
    state advances in memory only after the store's completed-turn commit succeeds.
    """

    def __init__(
        self, *, model: Callable | None = None,
        search: Callable[..., list[DiscoveryCandidate]] = search_exa,
        fetch: Callable[[str], FetchedMaterial] = fetch_linkup,
        limits: RunLimits = RunLimits(),
        engine: Callable[..., CompletedAnswer] | None = None,
        observe: Callable[[dict], None] | None = None,
    ) -> None:
        self._model, self._search, self._fetch, self._limits = model, search, fetch, limits
        self._engine = engine
        self._observe = observe
        self._snapshot = _Snapshot(SessionState())
        self._store: SessionStore | None = None

    @classmethod
    def create(cls, *, store: SessionStore | None = None, title: str = "", **kwargs) -> ResearchSession:
        """Create a durable session; kwargs are the ordinary constructor options."""
        session = cls(**kwargs)
        session._store = store if store is not None else SQLiteSessionStore()
        saved = session._store.create(title)
        session._snapshot = _Snapshot(saved.state, saved.metadata)
        return session

    @classmethod
    def open(cls, session_id: str, *, store: SessionStore | None = None, **kwargs) -> ResearchSession:
        """Restore without model/provider I/O; kwargs configure future ask calls."""
        session = cls(**kwargs)
        session._store = store if store is not None else SQLiteSessionStore()
        saved = session._store.load(session_id)
        session._snapshot = _Snapshot(saved.state, saved.metadata)
        return session

    @property
    def metadata(self) -> SessionMetadata | None:
        return self._snapshot.metadata

    @property
    def session_id(self) -> str | None:
        return self.metadata.session_id if self.metadata is not None else None

    @property
    def turns(self) -> tuple[SessionTurn, ...]:
        return deepcopy(self._snapshot.state.turns)

    @property
    def acquisitions(self) -> tuple[Evidence, ...]:
        return self._snapshot.state.acquisitions

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.source_id for item in self.acquisitions))

    def ask(self, question: str) -> CompletedAnswer:
        snapshot = self._snapshot
        state = snapshot.state
        # Conversation resolves referents only. Historical Analyst records are not
        # supplied to new research; retained actual acquisitions are Evidence.
        context = {
            "conversation_context": [{"question": turn.question, "answer": turn.answer} for turn in state.turns],
        }
        result = (self._engine or _run_turn)(
            question, model=self._model, search=self._search, fetch=self._fetch, limits=self._limits,
            retained_acquisitions=state.acquisitions, context=context, session_turn=len(state.turns) + 1, observe=self._observe,
        )
        turn = SessionTurn(question, result.answer, None,
                           result.posture, result.stop_reason, result.selected_evidence,
                           result.citations, result.citation_uses)
        staged = SessionState((*state.turns, turn), result.evidence)
        metadata = snapshot.metadata
        if self._store is not None:
            metadata = self._store.commit(metadata.session_id, metadata.revision, staged)
        # Nothing is exposed as completed until all validation and durable I/O succeed.
        self._snapshot = _Snapshot(staged, metadata)
        return result
