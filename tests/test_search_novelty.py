"""Mechanical Search accounting and turn-local navigation history."""
import json

import pytest
from test_research_loop import Script, answer, decision, request

from core.exa_transport import DiscoveryCandidate
from scryraven.acquisition import SEARCH_NOVELTY_COUNTS, AcquisitionLibrary
from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.research import RunLimits, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore


def lead(number, text="The stated value is seven."):
    return DiscoveryCandidate("Title", f"https://example.test/{number}", text,
                              context_kind="provider_highlights")


def execute(library, kind="search"):
    return library.execute({"kind": kind, "query": "PRIVATE QUERY"}, before_external=lambda: None)


def test_unique_candidates_and_material_versions_reconcile():
    batches = iter([
        [lead(n) for n in range(6)],
        [lead(0), lead(1, "Changed highlights."), lead(2), lead(3), lead(6), lead(7, "")],
        [lead(1, "Changed highlights."), lead(1, "Changed highlights."), lead(8),
         lead(8), lead(8, "Second version in the same request."),
         DiscoveryCandidate("Bad", "file:///private", "text"),
         DiscoveryCandidate("Bad", "https://user:pass@example.test", "text"),  # pragma: allowlist secret
         DiscoveryCandidate("Bad", "not a URL", "text"), None],
    ])
    library = AcquisitionLibrary(search=lambda q: next(batches))
    expected = [(6, 6, 0, 6, 6, 6, 0, 0), (6, 2, 4, 5, 2, 1, 1, 3), (2, 1, 1, 3, 2, 2, 0, 1)]
    for counts in expected:
        result = execute(library)
        receipt = result["search_novelty_receipt"]
        assert receipt == dict(provider="exa", kind="search", **dict(zip(SEARCH_NOVELTY_COUNTS, counts)))
        assert receipt["returned_material_count"] == len(result["material_ids"])
        assert receipt["new_material_count"] == len(result["new_acquisition_ids"])
        assert receipt["returned_candidate_count"] == len(result["candidate_refs"])
        assert receipt["new_material_count"] + receipt["exact_reused_material_count"] == len(result["material_ids"])


def test_prior_navigation_and_visible_links_are_known_before_search():
    library = AcquisitionLibrary(search=lambda q: [lead(0), lead(1), lead(2)])
    library.allow_question_urls("https://example.test/0")
    item = library._retain("https://example.test/parent", "Parent", "https://example.test/1", "fetched_source")
    library.expose([item.id])
    receipt = execute(library)["search_novelty_receipt"]
    assert receipt["new_candidate_count"] == 1
    assert receipt["refreshed_known_candidate_material_count"] == 2
    assert receipt["new_candidate_material_count"] == 1


def test_lexical_remains_navigation_only_and_empty_search_has_receipt():
    batches = iter([[lead(0), lead(0), lead(1)], [lead(1), lead(2)], []])
    library = AcquisitionLibrary(lexical_search=lambda q: next(batches))
    for expected in [(2, 2, 0), (2, 1, 1), (0, 0, 0)]:
        result = execute(library, "search_lexical")
        receipt = result["search_novelty_receipt"]
        assert [receipt[k] for k in SEARCH_NOVELTY_COUNTS[:3]] == list(expected)
        assert all(receipt[k] == 0 for k in SEARCH_NOVELTY_COUNTS[3:])
        assert receipt["provider"] == "serper"
        assert result["material_ids"] == result["new_acquisition_ids"] == []
    assert not library.acquisitions


@pytest.mark.parametrize("bad", [None, "invalid"])
def test_failed_search_has_no_success_receipt(bad):
    library = AcquisitionLibrary(search=lambda q: bad)
    assert "search_novelty_receipt" not in execute(library)


def test_history_survives_local_routes_and_all_known_search_allows_continuation():
    batches = iter([[lead(0)], [lead(0, "Changed highlights.")], [lead(0, "Changed highlights.")]])
    diagnostics = TurnDiagnostics()
    model = Script(
        decision(),
        decision(requests=[request("read", target="E1", mode="local")]),
        decision(),
        decision(requests=[request("find", query="Changed")]),
        decision(),
        decision("answer", ["E1"]), answer(),
    )
    result = run("Value?", model=model, search=lambda q: next(batches), observe=diagnostics.observe)
    packets = [p for stage, _, p, _ in model.calls if stage == "research"]
    assert [len(p["search_novelty_receipts"]) for p in packets] == [0, 1, 1, 2, 2, 3]
    receipts = packets[-1]["search_novelty_receipts"]
    assert [r["new_candidate_count"] for r in receipts] == [1, 0, 0]
    assert receipts[1]["refreshed_known_candidate_material_count"] == 1
    assert receipts[2]["exact_reused_material_count"] == 1
    assert result.trace[-1]["budget"]["external_attempts"] == 3
    assert result.trace[-1]["budget"]["semantic_attempts"] == 7
    assert "search_novelty" not in json.dumps(model.calls[-1][2])
    assert [a["search_novelty_receipt"] for a in diagnostics.acquisitions
            if "search_novelty_receipt" in a] == receipts


@pytest.mark.parametrize("reopen", [False, True])
def test_next_turn_resets_history_and_persistence_excludes_it(tmp_path, reopen):
    model = Script(decision(), decision("answer", ["E1"]), answer(),
                   decision(), decision("answer", ["E1"]), answer())
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=lambda q: [lead(0)])
    session.ask("Value?")
    assert len(model.calls[1][2]["search_novelty_receipts"]) == 1
    assert "search_novelty" not in repr(store.load(session.metadata.session_id).state)
    if reopen:
        session = ResearchSession.open(session.metadata.session_id, store=store,
                                       model=model, search=lambda q: [lead(0)])
    session.ask("Value again?")
    assert model.calls[3][2]["search_novelty_receipts"] == []
    assert model.calls[4][2]["search_novelty_receipts"][0]["exact_reused_material_count"] == 1
    assert all("search_novelty" not in json.dumps(p) for stage, _, p, _ in model.calls if stage == "answer")


def test_budget_denial_does_not_append_receipt():
    model = Script(decision(), decision("answer"), answer("Unknown.", "unable"))
    result = run("Value?", model=model, limits=RunLimits(external_attempts=0))
    assert model.calls[1][2]["search_novelty_receipts"] == []
    assert result.trace[-1]["budget"]["external_attempts"] == 0


def test_body_free_diagnostics_allow_only_fixed_counts_and_enums():
    events = []
    library = AcquisitionLibrary(search=lambda q: [lead(0)])
    result = library.execute({"kind": "search", "query": "PRIVATE QUERY"},
                             before_external=lambda: None, observe_operation=events.append)
    assert events[0]["search_novelty_receipt"] == result["search_novelty_receipt"]
    assert "PRIVATE" not in json.dumps(events) and "example.test" not in json.dumps(events)
    receipt = {**result["search_novelty_receipt"], "query": "PRIVATE", "url": "PRIVATE",
               "provider": "PRIVATE", "kind": "PRIVATE", "new_material_count": "PRIVATE",
               "known_candidate_count": True, "new_candidate_count": -1}
    diagnostics = TurnDiagnostics()
    diagnostics.observe({**events[0], "stage": "research", "action": "acquisition_timing",
                         "search_novelty_receipt": receipt})
    saved = diagnostics.acquisitions[0]["search_novelty_receipt"]
    assert set(saved) == {"provider", "kind", *SEARCH_NOVELTY_COUNTS}
    assert "PRIVATE" not in json.dumps(saved)
    assert all(saved[key] is None for key in ["provider", "kind", "new_material_count",
                                             "known_candidate_count", "new_candidate_count"])
