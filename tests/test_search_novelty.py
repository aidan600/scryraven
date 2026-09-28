"""Mechanical Search diagnostics without changing model or session contracts."""
import json

import pytest
from test_research_loop import Script, answer, decision, request

from core.exa_transport import DiscoveryCandidate
from scryraven.acquisition import SEARCH_NOVELTY_COUNTS, AcquisitionLibrary
from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.research import run
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


@pytest.mark.parametrize("reopen", [False, True])
def test_diagnostic_accounting_does_not_change_model_packets_or_session_state(tmp_path, monkeypatch, reopen):
    def exercise(name):
        model = Script(
            decision(requests=[request(query="PRIVATE initial query")]),
            decision(requests=[request("read", target="E1", mode="local")]),
            decision(requests=[request("search_lexical", query="PRIVATE lexical query")]),
            decision(requests=[request("find", query="seven")]),
            decision(requests=[request(query="PRIVATE repeated query")]),
            decision("answer", ["E1"]), answer(),
            decision("answer", ["E1"]), answer(),
        )
        diagnostics = TurnDiagnostics()
        events = []

        def observe(event):
            events.append(event)
            diagnostics.observe(event)

        store = SQLiteSessionStore(tmp_path / f"{name}.sqlite3")
        options = dict(model=model, search=lambda q: [lead(0)],
                       lexical_search=lambda q: [lead(0), lead(1)], observe=observe,
                       engine=lambda *args, **kwargs: run(*args, **kwargs, clock=lambda: 0.0))
        session = ResearchSession.create(store=store, **options)
        session.ask("Value?")
        if reopen:
            session = ResearchSession.open(session.metadata.session_id, store=store, **options)
        session.ask("Value again?")
        state = store.load(session.metadata.session_id).state
        return model.calls, state, diagnostics, events

    calls, state, diagnostics, events = exercise("instrumented")
    for stage, _, packet, _ in calls:
        serialized = json.dumps(packet)
        assert "search_route_receipts" not in serialized
        assert "search_novelty" not in serialized
        assert not any(field in serialized for field in SEARCH_NOVELTY_COUNTS)
        if stage == "research":
            assert set(packet) == {
                "question", "current_date", "conversation_context", "phase", "working_understanding",
                "evidence", "catalog", "pending_delivery", "last_route", "failed_external_reads",
                "answer_missing_information", "budget", "output_correction",
            }
        else:
            assert "PRIVATE" not in serialized
    assert "PRIVATE" not in repr(state)
    assert "search_novelty" not in repr(state) and "search_route_receipts" not in repr(state)
    assert "PRIVATE" not in json.dumps(diagnostics.acquisitions)
    receipts = [event["search_novelty_receipt"] for event in diagnostics.acquisitions
                if "search_novelty_receipt" in event]
    assert [r["provider"] for r in receipts] == ["exa", "serper", "exa"]
    assert [r["new_candidate_count"] for r in receipts] == [1, 1, 0]
    assert receipts[-1]["exact_reused_material_count"] == 1
    assert sum(e["action"] == "acquisition_timing" for e in events) == 5
    assert next(e for e in events if e["action"] == "completed")["budget"]["external_attempts"] == 3
    forensic_results = [e["result"] for e in events if e["action"] == "acquisition_result"]
    assert [r["search_novelty_receipt"] for r in forensic_results
            if "search_novelty_receipt" in r] == receipts

    # Compare every Research/Answer packet and persisted source/answer snapshot
    # with the same acquisition results before diagnostic metadata was added.
    execute_with_diagnostics = AcquisitionLibrary.execute

    def without_metadata(self, *args, **kwargs):
        result = execute_with_diagnostics(self, *args, **kwargs)
        result.pop("search_novelty_receipt", None)
        return result

    monkeypatch.setattr(AcquisitionLibrary, "execute", without_metadata)
    old_calls, old_state, _, _ = exercise("without_metadata")
    assert calls == old_calls
    assert state == old_state


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
