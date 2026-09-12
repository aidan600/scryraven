"""Public, synthetic Reading Room inputs; only model/provider I/O is scripted.

These are presentation fixtures, not research claims. No production module imports
this file. The optional local acceptance server uses an explicit external database.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from threading import local
from time import sleep

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_research_session import Script, assess, inspect, select_packet
from test_source_acquisition import use
from test_walking_skeleton import analysis, author, done, orient, relevance, search_for

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.reading_room import create_app, serve
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore

QUESTION = "How does a city’s tree canopy cool its streets?"
FOLLOWUP = "What changes on a humid day?"
THIRD = "Where does shade make the biggest difference?"
URL = "https://example.org/canopy-field-notes"
OTHER_URL = "https://example.org/designing-for-shade"
EARLY = ("Synthetic field note, initial edition. Trees shade the ground and release water vapour through their "
         "leaves. Shade reduces the solar energy reaching streets and pavements.")
LATER = ("Synthetic full publication, later acquisition. On a humid day the air has less capacity to take up "
         "additional water vapour, so evaporative cooling can be reduced. Shade remains useful.\n\n"
         + "Field observation: canopy shape, water availability and street geometry all affect the local result.\n\n" * 20
         + "END OF COMPLETE SAVED MATERIAL — humidity qualification retained.")
LARGE = ("# Shade along a walking route\nSynthetic design guidance. Shade matters where people spend time: "
         "footpaths, bus stops and places to sit.\n\n"
         + ("# Appendix\nSynthetic measurements and planting records. " + "Survey background. " * 350 + "\n\n") * 12)
DRAFT = """Trees cool a street in two complementary ways: **they keep sunlight off its surfaces**, and they move water from the soil into the air. [E1]

## A cooler place to walk

A canopy changes the experience of a street before it changes a whole neighbourhood’s temperature. By interrupting direct sunlight, it reduces the heat absorbed by the pavement and the radiant heat a person feels. [E1]

| Mechanism | What happens | Where you notice it |
| --- | --- | --- |
| Shade | Leaves intercept sunlight | Pavements and places to sit |
| Evaporation | Water takes up heat as it becomes vapour | Around the canopy |

## More than a number on a thermometer

The practical question is how the street feels at the time people use it. A useful reading of the material keeps several things in view:

- **Location:** shade should reach the places people walk and wait.
- **Conditions:** water availability and the surrounding air matter.
- **Time:** a tree’s shadow moves over the course of a day. [E1]

> The value of a canopy is experienced at street level, one shaded stretch at a time.

This is synthetic material for testing the Reading Room. The ordinary numeric text [1] here is not a citation.
"""


def no_io(*args, **kwargs):
    raise AssertionError("Unexpected external I/O")


def first_script(draft=DRAFT):
    return (orient(QUESTION), search_for(QUESTION), use("C1"), assess(QUESTION, EARLY, "E1"), author(draft))


def source_search(question):
    return [DiscoveryCandidate("Canopy field notes · sample publication", URL, EARLY,
                               context_kind="provider_highlights")]


def prepared_session(store):
    """Three real committed turns, including later same-URL and exact-view material."""
    session = ResearchSession.create(store=store, model=Script(*first_script()), search=source_search, fetch=no_io)
    session.ask(QUESTION)
    gap = analysis("research_needed", refs=("E1",), next_need="How humidity changes evaporation")
    session = ResearchSession.open(session.session_id, store=store, search=no_io,
        fetch=lambda url: FetchedMaterial(url, LATER), model=Script(
            orient(FOLLOWUP), use("C1"), gap, inspect("C1", need=FOLLOWUP), relevance("E2"),
            assess(FOLLOWUP, LATER[:250], "E1"),
            author("Humidity can reduce evaporative cooling. **Shade remains useful.** [E1]\n\n"
                   "The full material adds a qualification to the earlier field note: local conditions matter. [E1]")))
    session.ask(FOLLOWUP)
    session = ResearchSession.open(session.session_id, store=store,
        search=lambda q: [DiscoveryCandidate("Designing for shade · sample publication", OTHER_URL, "Navigation")],
        fetch=lambda url: FetchedMaterial(url, LARGE), model=Script(
            orient(THIRD), search_for(THIRD), inspect("C3", need=THIRD), select_packet,
            assess(THIRD, "Shade matters along walking routes and at places to wait.", "E3"),
            author("Start with the places where people spend time: **walking routes, bus stops and seating.** [E3]\n\n"
                   "A continuous shaded route can matter more to a pedestrian than isolated patches of canopy. [E3]")))
    session.ask(THIRD)
    return session


class AcceptanceModel:
    """Choose explicit scripted I/O scenarios for manual form submissions."""

    def __init__(self):
        self.current = local()

    def __call__(self, stage, prompt, material, schema):
        if material.get("phase") == "orientation":
            question = material["question"]
            sleep(3)  # A visible, deterministic request-in-progress interval.
            if "failure" in question.lower():
                raise RuntimeError("SYNTHETIC_PRIVATE_EXCEPTION_PATH_AND_PAYLOAD")
            if "unable" in question.lower():
                replies = (orient(question), done(), analysis("unable", refs=()),
                           author("The available material did not establish an answer to this question."))
            else:
                start = (use("C1"),) if material["conversation_context"] else (search_for(question), use("C1"))
                verdict = analysis("unable", refs=("E1",)) if "partial" in question.lower() else assess(question, EARLY, "E1")
                replies = (orient(question), *start, verdict,
                           author("The available material establishes that trees provide shade. [E1]\n\n"
                                  "Some aspects remain unresolved." if "partial" in question.lower() else DRAFT))
            self.current.script = Script(*replies)
        return self.current.script(stage, prompt, material, schema)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic Reading Room browser acceptance (no live I/O).")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--port", type=int, default=7332)
    args = parser.parse_args()
    if args.database.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("Use a disposable database outside the repository.")
    store = SQLiteSessionStore(args.database)
    if not store.list_sessions():
        prepared_session(store)
        empty = ResearchSession.create(store=store, title="A long research title that should fit quietly in the sidebar without widening it",
            model=Script(orient("Unresolved question"), done(), analysis("unable", refs=()),
                         author("The available material did not establish this answer.")), search=no_io, fetch=no_io)
        empty.ask("Unresolved question")
    print("Synthetic acceptance data only. All model and provider I/O is replaced.", flush=True)
    serve(create_app(store=store, session_options={"model": AcceptanceModel(), "search": source_search, "fetch": no_io}),
          port=args.port)
