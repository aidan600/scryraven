"""Offline mechanical proofs; real candidate loop/Author/session, scripted external I/O."""

import json
import subprocess
import sys
import tempfile
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest

from core.exa_transport import DiscoveryCandidate, ExaTransportError, FetchedMaterial
from scryraven.experimental.attention import Attention, AttentionError
from scryraven.experimental.contracts import (
    CatalogWindow,
    Clarify,
    ExperimentalLimits,
    Inspect,
    InvestigatorDecision,
)
from scryraven.experimental.harness import CandidateHarness, ScriptedModel
from scryraven.experimental.investigator import ClarificationRequired, InvestigatorEngine
from scryraven.model import ModelError, OpenAIModel
from scryraven.research import RunError
from scryraven.session_store import SessionStoreError, SQLiteSessionStore
from scryraven.sources import Evidence, exact_view

QUESTION = "Compare the thresholds and explain their scope."
URL_A, URL_B = "https://example.test/a", "https://example.test/b"
TEXT_A = 'Threshold A is 12 units.\r\nIt applies at rest. Unicode: λ 🪶; "quoted" \\ text.'
TEXT_B = "Threshold B is 18 units. It applies at rest."
SYNTHESIS = "At rest, threshold B is higher than threshold A."


def no_io(*args, **kwargs):
    raise AssertionError("unexpected_external_io")


class Provider:
    def __init__(self, *batches, bodies=None):
        self.batches = iter(batches)
        self.bodies = bodies or {URL_A: TEXT_A, URL_B: TEXT_B}
        self.searches, self.fetches = [], []

    def search(self, query):
        self.searches.append(query)
        batch = next(self.batches)
        if isinstance(batch, Exception):
            raise batch
        return batch

    def fetch(self, url):
        self.fetches.append(url)
        return FetchedMaterial(url, self.bodies[url])


def lead(url=URL_A, text=TEXT_A, *, kind="provider_highlights", omitted=0):
    return DiscoveryCandidate("Synthetic publication", url, text, omitted, kind)


def state(notes=(), qualifications=(), obligations=()):
    return {"interpreted_target": QUESTION, "intellectual_operation": "Comparison and scope explanation",
            "supported_understanding": list(notes), "qualifications_and_conflicts": list(qualifications),
            "unresolved_obligations": list(obligations)}


def note(ref="E1", *, text="A's threshold is established for idle operation.", id="n1"):
    return {"id": id, "text": text, "support_material_refs": [ref]}


def discover():
    return {"kind": "discover", "query": "published thresholds", "evidence_need": QUESTION}


def read(ref="D1"):
    return {"kind": "read", "source_ref": ref, "missing_context": "The full definitions and conditions."}


def inspect(*refs, ranges=(), locate=None, window=None):
    return {"kind": "inspect", "purpose": "Inspect exact context for the requested comparison.",
            "activate_material_refs": list(refs), "exact_ranges": list(ranges),
            "locate": locate, "catalog_window": window}


def finish(*refs, posture="supported", synthesis=SYNTHESIS, qualifications=(), conflicts=(), unresolved=()):
    return {"kind": "finish", "terminal": {
        "interpreted_target": QUESTION, "intellectual_operation": "Comparison and scope explanation",
        "synthesis": synthesis, "qualifications": list(qualifications), "conflicts": list(conflicts),
        "unresolved": list(unresolved), "posture": posture,
        "stop_reason": "Exact received material establishes this analysis; stated gaps remain unresolved.",
        "support_material_refs": list(refs),
    }}


def decision(action, *, memory=None, shelve=()):
    return "investigator", {"state": memory or state(), "shelve_material_refs": list(shelve), "action": action}


def author(answer=SYNTHESIS + " [E1]"):
    return "author", {"answer": answer}


def harness(model, provider=None, **limits):
    return CandidateHarness(model=model, search=provider.search if provider else no_io,
                            fetch=provider.fetch if provider else no_io, limits=ExperimentalLimits(**limits))


def material_items(request):
    return [part for row in request["evidence"] for part in row.get("materials", [row])]


@pytest.fixture
def database():
    root = Path(tempfile.gettempdir()).resolve()
    assert not root.is_relative_to(Path(__file__).resolve().parents[1])
    with tempfile.TemporaryDirectory(prefix="scryraven-investigator-", dir=root) as directory:
        yield Path(directory) / "synthetic.sqlite3"


def test_custody_shelving_unchanged_note_reactivation_and_exact_author_material():
    provider = Provider([lead(), lead(URL_B, TEXT_B)])
    memory = state([note()])
    model = ScriptedModel(
        decision(discover()),
        decision(inspect("E2"), memory=memory, shelve=["E1"]),
        decision(inspect("E1"), memory=memory),
        decision(finish("E1", "E2", qualifications=["Both thresholds apply at rest."]), memory=memory),
        author(SYNTHESIS + " [E2] [E1] [E2]"),
    )
    result = harness(model, provider).run(QUESTION)
    shelved_input = model.calls[2][1]
    assert json.dumps(TEXT_A, ensure_ascii=False) not in json.dumps(shelved_input, ensure_ascii=False)
    assert shelved_input["investigation_state_not_evidence"] == memory
    assert [item["id"] for item in material_items(shelved_input)] == ["E2"]
    assert shelved_input["catalog"]["items"][0]["exposed"] is True
    reactivated = {item["id"]: item for item in material_items(model.calls[3][1])}
    assert reactivated["E1"]["content"].encode() == TEXT_A.encode()
    assert [item.content for item in result.evidence] == [TEXT_A, TEXT_B]
    assert material_items(model.calls[-1][1]) == [item.material() for item in result.selected_evidence]
    assert SYNTHESIS in model.calls[-1][1]["coverage"][0]["findings"][0]["text"]
    assert "Qualification: Both thresholds apply at rest." in result.analysis.findings[0].text
    assert [c.source_id for c in result.citations] == ["E2", "E1"]
    assert result.answer.endswith("[1] [2] [1]")
    assert provider.fetches == [] and len(provider.searches) == 1


@pytest.mark.parametrize("kind,omitted,text", [
    ("navigation", 0, "Navigation description is not source Evidence."),
    ("provider_highlights", 1000, "Provider material omitted by size guard; acquire this URL for context."),
    ("provider_highlights", 0, "  "),
    ("summary", 0, "A generated summary."),
])
def test_discovery_metadata_and_omissions_never_enter_custody(kind, omitted, text):
    attention = Attention((), ExperimentalLimits())
    attention.discover([lead(text=text, kind=kind, omitted=omitted)])
    assert attention.acquisitions == [] and attention.active == {}
    assert attention.catalog()["items"][0]["acquisition"] == "navigation"
    assert "content" not in attention.catalog()["items"][0]


def test_large_parent_repeated_local_views_identity_and_no_refetch():
    body = TEXT_A + "\n\n" + ("Unrelated ballast. " * 3000) + "\n\n" + TEXT_B
    first_end, last_start = len(TEXT_A), len(body) - len(TEXT_B)
    first_ref, last_ref = f"E2@0:{first_end}", f"E2@{last_start}:{len(body)}"
    provider = Provider([lead()], bodies={URL_A: body})
    model = ScriptedModel(
        decision(discover()), decision(read()),
        decision(inspect(ranges=[{"parent_ref": "E2", "start_char": 0, "end_char": first_end}])),
        decision(inspect(ranges=[{"parent_ref": "E2", "start_char": last_start, "end_char": len(body)}]),
                 shelve=[first_ref]),
        decision(read("E2")),
        decision(inspect(first_ref)),
        decision(finish(first_ref, last_ref)), author(),
    )
    result = harness(model, provider, active_evidence_target_chars=500).run(QUESTION)
    assert provider.fetches == [URL_A]
    assert model.calls[2][1]["action_result"]["activated"] is False
    assert model.calls[5][1]["action_result"]["local"] is True
    assert body not in json.dumps([request for _, request in model.calls])
    assert result.evidence[1].content == body
    assert result.selected_evidence == (exact_view(result.evidence[1], 0, first_end),
                                        exact_view(result.evidence[1], last_start, len(body)))
    assert {item.source_id for item in result.evidence + result.selected_evidence} == {"E1"}
    assert result.analysis.support_refs == ["E1"]
    assert len(result.citations) == 1 and result.citations[0].materials == result.selected_evidence
    author_material = model.calls[-1][1]["evidence"]
    assert len(author_material) == 1 and author_material[0]["id"] == "E1"
    assert author_material[0]["materials"] == [item.material() for item in result.selected_evidence]


def test_bounded_catalog_lexical_miss_does_not_remove_direct_addressing():
    retained = tuple(Evidence(f"E{i}", f"https://example.test/{i}", "Catalog entry", f"Source body {i} λ")
                     for i in range(1, 8))
    attention = Attention(retained, ExperimentalLimits(catalog_page_size=2, region_page_size=1))
    assert len(attention.catalog()["items"]) == 2 and attention.catalog()["next_offset"] == 2
    attention.window = CatalogWindow(offset=6, query="")
    assert [item["id"] for item in attention.catalog()["items"]] == ["E7"]
    action = Inspect.model_validate(inspect("E7", window={"offset": 0, "query": "no such metadata"},
                                           locate={"material_ref": "E1", "query": "nonexistent token", "start_char": 0}))
    result = attention.inspect(action)
    assert result["located_regions"] == [] and attention.catalog()["items"] == []
    assert attention.active["E7"] == retained[-1]
    view = attention.resolve("E1@0:5")
    assert view == exact_view(retained[0], 0, 5)
    attention.shelve(["E7"])
    assert attention.activate([attention.resolve("E7")])
    assert attention.active["E7"].content.encode() == retained[-1].content.encode()
    assert attention.acquisitions == list(retained)


def test_local_locator_is_bounded_and_does_not_expose_source_bodies():
    body = ("Repeated match token. " * 2000) + TEXT_B
    attention = Attention((Evidence("E1", URL_A, "Long source", body),),
                          ExperimentalLimits(region_page_size=2, active_evidence_target_chars=200))
    result = attention.inspect(Inspect.model_validate(inspect(locate={
        "material_ref": "E1", "query": "Repeated match token", "start_char": 0})))
    assert result["matching_region_count"] > 2 and len(result["located_regions"]) == 2
    assert attention.active == {}
    assert "content" not in json.dumps(result)
    assert body not in json.dumps(attention.catalog())


@pytest.mark.parametrize("ref,expected", [("E99", "unknown_material_reference"),
                                         ("E1", "note_support_not_exposed"),
                                         ("E1@0:5", "note_support_not_exposed"),
                                         ("n1", "unknown_material_reference")])
def test_new_note_cannot_use_unknown_notes_or_unexposed_exact_material(ref, expected):
    model = ScriptedModel(decision(inspect("E1"), memory=state([note(ref)])))
    with pytest.raises(RunError, match=expected):
        InvestigatorEngine()(QUESTION, model=model, search=no_io, fetch=no_io,
                             retained_acquisitions=(Evidence("E1", URL_A, "A", TEXT_A),))
    assert len(model.calls) == 1  # Inspect in the same response cannot backdate exposure.


@pytest.mark.parametrize("category", ["supported_understanding", "qualifications_and_conflicts"])
def test_revised_note_requires_reactivation_in_the_reasoning_input(category):
    memory = state()
    memory[category] = [note()]
    revised = deepcopy(memory)
    revised[category][0]["text"] = "A revised qualification or relationship."
    model = ScriptedModel(decision(discover()), decision(inspect(), memory=memory, shelve=["E1"]),
                          decision(inspect("E1"), memory=revised))
    with pytest.raises(RunError, match="note_support_not_exposed"):
        harness(model, Provider([lead()])).run(QUESTION)


@pytest.mark.parametrize("same_response_shelve", [False, True])
def test_terminal_relationship_requires_exact_support_active_now(same_response_shelve):
    steps = [decision(discover())]
    if not same_response_shelve:
        steps.append(decision(inspect(), memory=state([note()]), shelve=["E1"]))
    steps.append(decision(finish("E1"), memory=state([note()]),
                          shelve=["E1"] if same_response_shelve else []))
    with pytest.raises(RunError, match="terminal_support_not_active"):
        harness(ScriptedModel(*steps), Provider([lead()])).run(QUESTION)


def test_terminal_cannot_substitute_active_parent_for_selected_unexposed_view():
    provider = Provider([lead(kind="navigation")])
    model = ScriptedModel(decision(discover()), decision(read()), decision(finish("E1@0:5")))
    with pytest.raises(RunError, match="terminal_support_not_active"):
        harness(model, provider).run(QUESTION)


def test_reactivated_material_permits_new_relational_synthesis_after_shelving():
    model = ScriptedModel(
        decision(discover()), decision(inspect(), memory=state([note()]), shelve=["E1"]),
        decision(inspect("E1"), memory=state([note()])),
        decision(finish("E1", "E2"), memory=state([
            note(), {"id": "relationship", "text": SYNTHESIS, "support_material_refs": ["E1", "E2"]}])), author(),
    )
    result = harness(model, Provider([lead(), lead(URL_B, TEXT_B)])).run(QUESTION)
    assert result.posture == "supported"
    assert [item.id for item in result.selected_evidence] == ["E1", "E2"]


def test_attention_target_rejects_activation_atomically_without_eviction_or_truncation():
    retained = (Evidence("E1", URL_A, "A", TEXT_A), Evidence("E2", URL_B, "B", TEXT_B))
    attention = Attention(retained, ExperimentalLimits(active_evidence_target_chars=len(TEXT_A)))
    assert attention.activate([retained[0]])
    assert not attention.activate([retained[1]])
    assert list(attention.active) == ["E1"]
    assert attention.acquisitions == list(retained)
    attention.shelve(["E1"])
    assert attention.activate([retained[1]])


@pytest.mark.parametrize("field", ["trigger", "answer_impact", "next_action"])
def test_obligation_requires_structural_justification(field):
    obligation = {"id": "o1", "trigger": "Two scopes differ.", "answer_impact": "Comparison could be invalid.",
                  "next_action": "Read the definition."}
    obligation[field] = " "
    model = ScriptedModel(decision(discover(), memory=state(obligations=[obligation])))
    with pytest.raises(RunError, match="incomplete_obligation"):
        harness(model).run(QUESTION)


@pytest.mark.parametrize("cycles,external", [(1, 9), (4, 1), (0, 3)])
def test_envelopes_configurable_global_and_exhaustion_cannot_fabricate_support(cycles, external):
    def repeating(request):
        used = cycles - request["envelope"]["nonterminal_cycles_remaining"]
        obligation = {"id": f"new-{used}", "trigger": "A scope question remains.",
                      "answer_impact": "It might qualify the answer.", "next_action": "Inspect another publication."}
        return decision(discover(), memory=state(obligations=[obligation]))[1]

    # One final terminal-only response; nonterminal requests there execute no I/O.
    count = min(cycles, external + 1) + 1
    model = ScriptedModel(*[("investigator", repeating)] * count, author("This bounded run did not establish an answer."))
    provider = Provider(*([[]] * min(cycles, external)))
    result = harness(model, provider, max_nonterminal_cycles=cycles, max_external_acquisitions=external).run(QUESTION)
    assert result.posture == "unable" and not result.analysis.findings
    assert "envelope was exhausted" in result.analysis.explanation
    assert "does not establish nonexistence" in result.analysis.coverage[-1].limitation
    assert len(provider.searches) == min(cycles, external)
    assert model.calls[-2][1]["envelope"]["terminal_only"] is True
    assert not model.steps


def test_local_reads_and_inspects_do_not_consume_external_allowance():
    parent = Evidence("E1", URL_A, "A", TEXT_A)
    model = ScriptedModel(decision(read("E1")), decision(inspect("E1")), decision(finish("E1")), author())
    result = InvestigatorEngine(ExperimentalLimits(max_external_acquisitions=0, max_nonterminal_cycles=3))(
        QUESTION, model=model, search=no_io, fetch=no_io, retained_acquisitions=(parent,))
    assert result.posture == "supported"
    assert all(request["envelope"]["external_acquisitions_remaining"] == 0
               for stage, request in model.calls if stage == "investigator")


def test_final_bounded_step_can_preserve_explicit_partial_analysis():
    gap = {"portion": "Operating scope", "limitation": "The allowed investigation did not establish the scope."}
    model = ScriptedModel(decision(discover()),
                          decision(finish("E1", posture="partial", unresolved=[gap])),
                          author("Threshold A is 12 units [E1]. Its scope remains unresolved in this run."))
    result = harness(model, Provider([lead()]), max_nonterminal_cycles=1).run(QUESTION)
    assert result.posture == "partial" and result.analysis.coverage[-1].limitation == gap["limitation"]


def test_terminal_only_step_does_not_upgrade_supported_request_at_exhaustion():
    model = ScriptedModel(decision(discover()), decision(finish("E1")),
                          author("This bounded investigation did not complete a supported answer."))
    result = harness(model, Provider([lead()]), max_nonterminal_cycles=1).run(QUESTION)
    assert result.posture == "unable" and result.selected_evidence == ()
    assert result.evidence[0].content == TEXT_A
    assert "cycle envelope was exhausted" in result.analysis.explanation


@pytest.mark.parametrize("patch,code", [
    ({"support_material_refs": ["E99"]}, "unknown_material_reference"),
    ({"support_material_refs": []}, "terminal_analysis_missing_support"),
    ({"synthesis": " "}, "terminal_analysis_missing_support"),
    ({"posture": "partial"}, "terminal_posture_mismatch"),
    ({"posture": "unable"}, "unable_with_claims_or_without_limitation"),
    ({"unresolved": [{"portion": "Requested scope", "limitation": "Unknown"}]}, "terminal_posture_mismatch"),
])
def test_invalid_terminal_contracts_fail_without_author(patch, code):
    action = finish("E1")
    action["terminal"].update(patch)
    model = ScriptedModel(decision(discover()), decision(action))
    with pytest.raises(RunError, match=code):
        harness(model, Provider([lead()])).run(QUESTION)
    assert all(stage == "investigator" for stage, _ in model.calls)


def test_terminal_adapter_preserves_relational_analysis_conflicts_and_requested_gaps():
    gap = {"portion": "Scope outside idle conditions", "limitation": "Neither received text establishes that scope."}
    action = finish("E1", "E2", posture="partial", qualifications=["This comparison applies at rest only."],
                    conflicts=["The two texts leave applicability to a common revision unresolved."], unresolved=[gap])
    model = ScriptedModel(decision(discover()), decision(action), author(SYNTHESIS + " [E1, E2] Scope is limited."))
    result = harness(model, Provider([lead(), lead(URL_B, TEXT_B)])).run(QUESTION)
    author_input = model.calls[-1][1]
    composite = author_input["coverage"][0]
    assert action["terminal"]["interpreted_target"] in composite["need"]
    assert action["terminal"]["intellectual_operation"] in composite["need"]
    text = composite["findings"][0]["text"]
    assert SYNTHESIS in text
    assert all(value in text for value in action["terminal"]["qualifications"] + action["terminal"]["conflicts"])
    assert author_input["explanation"] == action["terminal"]["stop_reason"]
    assert author_input["coverage"][1]["need"] == gap["portion"]
    assert author_input["coverage"][1]["limitation"] == gap["limitation"]
    assert material_items(author_input) == [item.material() for item in result.selected_evidence]


def test_failed_acquisition_consumes_allowance_and_reports_only_fixed_diagnostic():
    model = ScriptedModel(decision(discover()), decision(discover()), decision(discover()),
                          author("This run did not establish an answer."))
    provider = Provider(ExaTransportError("untrusted transport detail"))
    result = harness(model, provider, max_external_acquisitions=1).run(QUESTION)
    assert len(provider.searches) == 1 and result.posture == "unable"
    assert model.calls[1][1]["action_result"]["status"] == "acquisition_failed"
    assert "untrusted transport detail" not in json.dumps(result.trace)


def test_successful_candidate_custody_fresh_followup_reopen_and_historical_exactness(database):
    model = ScriptedModel(decision(discover()), decision(finish("E1")), author())
    session = harness(model, Provider([lead(), lead(URL_B, TEXT_B)])).create(store=SQLiteSessionStore(database))
    first = session.ask(QUESTION)
    assert len(first.evidence) == 2 and len(first.selected_evidence) == 1
    old_turn, old_corpus, session_id = session.turns[0], session.acquisitions, session.session_id
    # A separate interpreter restores the actual serialized schema, with no model/provider invocation.
    code = """import json, sys
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
s = ResearchSession.open(sys.argv[2], store=SQLiteSessionStore(sys.argv[1]))
print(json.dumps({'ids': [x.id for x in s.acquisitions], 'answer': s.turns[0].answer}))
"""
    restored = subprocess.run([sys.executable, "-c", code, str(database), session_id],
                              cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True)
    assert json.loads(restored.stdout) == {"ids": ["E1", "E2"], "answer": first.answer}
    del session
    followup = ScriptedModel(decision(inspect("E2")), decision(finish("E2")), author("B's threshold is 18 units. [E2]"))
    session = harness(followup).open(session_id, store=SQLiteSessionStore(database))
    assert session.turns[0] == old_turn and session.acquisitions == old_corpus
    second = session.ask("What about the other threshold?")
    initial = followup.calls[0][1]
    assert initial["investigation_state_not_evidence"] is None and initial["active_material_refs"] == []
    assert initial["evidence"] == [] and "semantic_history" not in initial
    assert not any(row.get("exposed") for row in initial["catalog"]["items"])
    assert initial["conversation_context"] == [{"question": QUESTION, "answer": first.answer}]
    assert second.evidence == old_corpus and session.turns[0] == old_turn
    completed = next(event for event in second.trace if event["action"] == "turn_completed")
    assert completed["reused_source_ids"] == ["E2"] and completed["new_acquisition_count"] == 0
    assert session.turns[1].citations[0].number == 1
    later_model = ScriptedModel(decision(discover()), decision(finish("E3")), author("A's new threshold is 14 units. [E1]"))
    later = harness(later_model, Provider([lead(text="Threshold A is now 14 units.")])).open(
        session_id, store=SQLiteSessionStore(database))
    third = later.ask("What changed?")
    assert third.evidence[2].id == "E3" and third.evidence[2].source_id == "E1"
    assert third.citations[0].materials == (third.evidence[2],)
    assert later.turns[0] == old_turn and later.acquisitions[:2] == old_corpus
    final = harness(ScriptedModel()).open(session_id, store=SQLiteSessionStore(database))
    assert final.turns == later.turns and final.acquisitions == third.evidence
    # Only existing successful-turn wire data; no attention, windows, semantic notes or indexes.
    import sqlite3
    with closing(sqlite3.connect(database)) as connection:
        payload = connection.execute("SELECT payload FROM sessions").fetchone()[0]
    assert not any(name in payload for name in ("investigation_state", "shelve_material_refs", "unresolved_obligations",
                                                "catalog_window", "SourceIndex", "prompt_cache"))


def test_durable_large_parent_new_views_on_followup_keep_historical_exact_snapshots(database):
    body = TEXT_A + "\n\n" + "Mechanical ballast. " * 2000 + "\n\n" + TEXT_B
    first_ref = f"E1@0:{len(TEXT_A)}"
    last_ref = f"E1@{len(body) - len(TEXT_B)}:{len(body)}"
    provider = Provider([lead(kind="navigation")], bodies={URL_A: body})
    model = ScriptedModel(decision(discover()), decision(read()), decision(inspect(first_ref)),
                          decision(finish(first_ref)), author())
    session = harness(model, provider, active_evidence_target_chars=300).create(store=SQLiteSessionStore(database))
    first = session.ask(QUESTION)
    old_turn, session_id = session.turns[0], session.session_id
    assert first.evidence[0].content == body
    assert first.selected_evidence == (exact_view(first.evidence[0], 0, len(TEXT_A)),)
    followup = ScriptedModel(decision(inspect(last_ref)), decision(finish(last_ref)), author())
    reopened = harness(followup, active_evidence_target_chars=300, max_external_acquisitions=0).open(
        session_id, store=SQLiteSessionStore(database))
    second = reopened.ask("Inspect the other region.")
    assert second.evidence == first.evidence
    assert second.selected_evidence == (exact_view(first.evidence[0], len(body) - len(TEXT_B), len(body)),)
    assert reopened.turns[0] == old_turn and reopened.turns[0].citations == first.citations
    restored = harness(ScriptedModel()).open(session_id, store=SQLiteSessionStore(database))
    assert restored.turns == reopened.turns and restored.acquisitions == first.evidence
    assert provider.fetches == [URL_A]


def test_stale_candidate_commit_preserves_other_writer_and_its_own_completed_snapshot(database):
    store = SQLiteSessionStore(database)
    session = harness(ScriptedModel(decision(discover()), decision(finish("E1")), author()),
                      Provider([lead()])).create(store=store)
    session.ask(QUESTION)
    old = session.turns, session.acquisitions, session.metadata
    stale = harness(ScriptedModel(decision(inspect("E1")), decision(finish("E1")), author())).open(
        session.session_id, store=SQLiteSessionStore(database))
    session._model = ScriptedModel(decision(inspect("E1")), decision(finish("E1")), author())
    session.ask("A follow-up")
    with pytest.raises(SessionStoreError, match="session_conflict"):
        stale.ask("A competing follow-up")
    assert (stale.turns, stale.acquisitions, stale.metadata) == old
    assert store.load(session.session_id).state.turns == session.turns


@pytest.mark.parametrize("failure", ["model", "action", "citations", "commit"])
def test_failed_candidate_paths_preserve_durable_and_memory_state(database, monkeypatch, failure):
    store = SQLiteSessionStore(database)
    session = harness(ScriptedModel(decision(discover()), decision(finish("E1")), author()),
                      Provider([lead()])).create(store=store)
    session.ask(QUESTION)
    before = session.turns, session.acquisitions, session.metadata
    provider = Provider([lead(URL_B, TEXT_B)])
    if failure == "model":
        def failing(request):
            raise ModelError("model_transport_failed")
        model = ScriptedModel(decision(discover()), ("investigator", failing))
    elif failure == "action":
        model = ScriptedModel(decision(discover()), decision(inspect("E999")))
    elif failure == "citations":
        model = ScriptedModel(decision(discover()), decision(finish("E2")), author("Unsupported alias [E999]"))
    else:
        model = ScriptedModel(decision(discover()), decision(finish("E2")), author("A current finding [E2]"))
        def failed_commit(*args):
            raise SessionStoreError("session_store_unavailable")
        monkeypatch.setattr(store, "commit", failed_commit)
    session._model, session._search, session._fetch = model, provider.search, provider.fetch
    with pytest.raises((RunError, SessionStoreError)):
        session.ask("A new question")
    assert (session.turns, session.acquisitions, session.metadata) == before
    persisted = store.load(session.session_id)
    assert persisted.state.turns == before[0] and persisted.state.acquisitions == before[1]
    assert persisted.metadata == before[2]


def test_clarify_is_harness_signal_without_completed_session_or_lifecycle(database):
    action = {"kind": "clarify", "question": "Which of the two named standards do you mean?",
              "target_difference": "They govern different systems and require different evidence."}
    signal = harness(ScriptedModel(decision(action))).run("Explain that standard.")
    assert isinstance(signal, Clarify) and signal.question == action["question"]
    store = SQLiteSessionStore(database)
    session = harness(ScriptedModel(decision(discover()), decision(action)), Provider([lead()])).create(store=store)
    before = session.turns, session.acquisitions, session.metadata
    with pytest.raises(ClarificationRequired) as caught:
        session.ask("Explain that standard.")
    assert caught.value.signal == signal
    assert (session.turns, session.acquisitions, session.metadata) == before
    assert store.load(session.session_id).state.acquisitions == ()
    assert store.load(session.session_id).state.turns == ()


def test_candidate_transport_is_lossless_stateless_and_does_not_cache_shelved_bodies(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    scripted = ScriptedModel(decision(discover()), decision(inspect(), shelve=["E1"]),
                             decision(inspect("E1")), decision(finish("E1")), author())
    payloads = []

    class Response:
        def __init__(self, raw):
            self.raw = raw

        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "completed", "output": [{"type": "message", "phase": "final_answer",
                    "content": [{"type": "output_text", "text": self.raw}]}]}

    def post(url, **kwargs):
        payload = kwargs["json"]
        payloads.append(payload)
        material = json.loads("".join(block["text"] for block in payload["input"][1]["content"]))
        return Response(scripted(payload["text"]["format"]["name"], "", material, {}))

    result = harness(OpenAIModel(post=post), Provider([lead()])).run(QUESTION)
    assert result.posture == "supported"
    assert TEXT_A == material_items(scripted.calls[1][1])[0]["content"]
    assert TEXT_A == material_items(scripted.calls[3][1])[0]["content"]
    assert not material_items(scripted.calls[2][1])
    assert json.dumps(TEXT_A, ensure_ascii=False) not in "".join(
        block["text"] for message in payloads[2]["input"] for block in message["content"])
    for payload, (_, request) in zip(payloads, scripted.calls):
        assert json.loads("".join(block["text"] for block in payload["input"][1]["content"])) == request
        assert payload["store"] is False and "tools" not in payload
        assert payload["text"]["format"]["strict"] is True
        assert payload["prompt_cache_options"]["mode"] == "explicit"
        assert "previous_response_id" not in payload
    schema = payloads[0]["text"]["format"]["schema"]
    assert schema == InvestigatorDecision.model_json_schema()
    for definition in [schema, *schema["$defs"].values()]:
        if definition.get("type") == "object":
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])


def test_actual_input_safety_guard_fails_before_call_without_silent_omission():
    model = ScriptedModel()
    with pytest.raises(RunError, match="model_input_size_exceeded"):
        harness(model, max_model_input_chars=100).run(QUESTION)
    assert not model.calls


def test_state_remains_compact_without_summary_service():
    memory = state()
    memory["interpreted_target"] = "x" * 1000
    with pytest.raises(RunError, match="state_size_exceeded"):
        harness(ScriptedModel(decision(discover(), memory=memory)), max_state_chars=500).run(QUESTION)


@pytest.mark.parametrize("changes", [{"max_nonterminal_cycles": -1}, {"max_external_acquisitions": True},
                                    {"active_evidence_target_chars": 0}, {"catalog_page_size": 0}])
def test_invalid_experimental_knobs_rejected(changes):
    with pytest.raises(ValueError, match="invalid_experimental_limits"):
        ExperimentalLimits(**changes)


def test_exact_view_invalid_bounds_and_identity_are_not_repaired():
    attention = Attention((Evidence("E1", URL_A, "A", TEXT_A),), ExperimentalLimits())
    for ref in ("E1@0:999999", "E1@5:2", "E1@01:3", "E2@0:5"):
        with pytest.raises(AttentionError):
            attention.resolve(ref)
