"""In-process conversation and acquisition custody. No I/O or semantic decisions."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass

from core.exa_transport import DiscoveryCandidate, FetchedMaterial, fetch_exa, search_exa
from scryraven.research import Analysis, ModelCall, Result, RunLimits, _run_turn
from scryraven.sources import Evidence


@dataclass(frozen=True)
class SessionTurn:
    question: str
    answer: str
    analysis: Analysis
    posture: str
    stop_reason: str


@dataclass(frozen=True)
class _SessionState:
    turns: tuple[SessionTurn, ...] = ()
    acquisitions: tuple[Evidence, ...] = ()


class ResearchSession:
    """Sequential ask(question) calls with fresh decisions over a retained corpus.

    Only successful Results commit state (including partial/unable answers).
    Acquisitions are immutable, including full parents of exact targeted views.
    History is copied on inspection so callers cannot mutate committed analysis.
    Nothing is serialized; dropping this object releases its session state.
    """

    def __init__(
        self, *, model: ModelCall | None = None,
        search: Callable[..., list[DiscoveryCandidate]] = search_exa,
        fetch: Callable[[str], FetchedMaterial] = fetch_exa,
        limits: RunLimits = RunLimits(),
    ) -> None:
        self._model, self._search, self._fetch, self._limits = model, search, fetch, limits
        self._state = _SessionState()

    @property
    def turns(self) -> tuple[SessionTurn, ...]:
        return deepcopy(self._state.turns)

    @property
    def acquisitions(self) -> tuple[Evidence, ...]:
        return self._state.acquisitions

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.source_id for item in self._state.acquisitions))

    def ask(self, question: str) -> Result:
        state = self._state
        # These two history classes are never admitted to the Evidence collection.
        context = {
            "conversation_context": [{"question": turn.question, "answer": turn.answer} for turn in state.turns],
            "semantic_history": [
                {"question": turn.question, "analysis": turn.analysis.model_dump(),
                 "posture": turn.posture, "stop_reason": turn.stop_reason}
                for turn in state.turns
            ],
        }
        result = _run_turn(
            question, model=self._model, search=self._search, fetch=self._fetch, limits=self._limits,
            retained_acquisitions=state.acquisitions, context=context, session_turn=len(state.turns) + 1,
        )
        turn = SessionTurn(question, result.answer, result.analysis.model_copy(deep=True),
                           result.posture, result.stop_reason)
        # One assignment after all model, reference and citation validation succeeds.
        self._state = _SessionState((*state.turns, turn), result.evidence)
        return result
