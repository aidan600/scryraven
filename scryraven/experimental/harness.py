"""Explicit developer/test entrypoint. The executable demo uses synthetic I/O only.

python -m scryraven.experimental.harness

CandidateHarness requires injected model/search/fetch callables. create/open require
an explicit SessionStore; no experiment implicitly opens the user's real database.
"""

from __future__ import annotations

import json
from copy import deepcopy

from core.exa_transport import DiscoveryCandidate
from scryraven.experimental.contracts import Clarify, ExperimentalLimits
from scryraven.experimental.investigator import ClarificationRequired, InvestigatorEngine
from scryraven.research import Result
from scryraven.session import ResearchSession
from scryraven.session_store import SessionStore


class ScriptedModel:
    """Deterministic model replacement; call snapshots are local test data only.

    Steps are (stage, dictionary) or (stage, callable(material) -> dictionary).
    The engine still validates every response against its real structured contract.
    """

    def __init__(self, *steps) -> None:
        self.steps = list(steps)
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, stage, prompt, material, schema):
        self.calls.append((stage, deepcopy(material)))
        if not self.steps:
            raise AssertionError("script_exhausted")
        expected, reply = self.steps.pop(0)
        if expected != stage:
            raise AssertionError("unexpected_model_stage")
        return json.dumps(reply(deepcopy(material)) if callable(reply) else reply, ensure_ascii=False)


class CandidateHarness:
    def __init__(self, *, model, search, fetch, limits: ExperimentalLimits = ExperimentalLimits()) -> None:
        self.options = {"model": model, "search": search, "fetch": fetch, "engine": InvestigatorEngine(limits)}

    def run(self, question: str) -> Result | Clarify:
        try:
            return self.session().ask(question)
        except ClarificationRequired as exc:
            return exc.signal

    def session(self) -> ResearchSession:
        return ResearchSession(**self.options)

    def create(self, *, store: SessionStore, title: str = "") -> ResearchSession:
        return ResearchSession.create(store=store, title=title, **self.options)

    def open(self, session_id: str, *, store: SessionStore) -> ResearchSession:
        return ResearchSession.open(session_id, store=store, **self.options)


def main() -> None:
    question = "Compare the two published thresholds."
    state = {"interpreted_target": question, "intellectual_operation": "Compare",
             "supported_understanding": [], "qualifications_and_conflicts": [], "unresolved_obligations": []}
    source_text = "Threshold A is 12 units. Threshold B is 18 units. Both apply at rest."
    terminal = {"interpreted_target": question, "intellectual_operation": "Compare",
                "synthesis": "At rest, threshold B (18 units) is higher than threshold A (12 units).",
                "qualifications": ["Both thresholds apply at rest."], "conflicts": [], "unresolved": [],
                "posture": "supported", "stop_reason": "The received text supports the requested comparison.",
                "support_material_refs": ["E1"]}
    model = ScriptedModel(
        ("investigator", {"state": state, "shelve_material_refs": [],
                          "action": {"kind": "discover", "query": "published thresholds", "evidence_need": question}}),
        ("investigator", {"state": state, "shelve_material_refs": [],
                          "action": {"kind": "finish", "terminal": terminal}}),
        ("author", {"answer": terminal["synthesis"] + " [E1]"}),
    )

    def no_fetch(url):
        raise AssertionError("demo_does_not_fetch")

    result = CandidateHarness(model=model, fetch=no_fetch, search=lambda query: [
        DiscoveryCandidate("Synthetic thresholds", "https://example.test/thresholds", source_text,
                           context_kind="provider_highlights"),
    ]).run(question)
    print(result.answer)
    print("Synthetic I/O only; production defaults unchanged.")


if __name__ == "__main__":
    main()
