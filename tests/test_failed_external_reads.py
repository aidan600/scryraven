"""Turn-local operational history, exercised with offline scripted decisions."""

import json
import math
from functools import partial

import pytest
import requests
from test_research_loop import Script, answer, decision, request

from core.exa_transport import DiscoveryCandidate
from core.linkup_transport import LINKUP_FAILURE_CODES, LinkupTransportError, fetch_linkup
from core.transport import FetchedMaterial
from scryraven.acquisition import AcquisitionLibrary
from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.forensic_log import ForensicLog
from scryraven.research import RunLimits, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore

URL = "https://example.test/failed"


def test_receipts_survive_routes_and_focus_changes_without_suppressing_retries():
    now, fetches = [0.0], []

    def fetch(url):
        fetches.append(url)
        now[0] += 2.25
        if url != URL + "/success":
            raise LinkupTransportError("linkup_timeout")
        return FetchedMaterial(url, "The recovered fact.")

    model = Script(
        decision(requests=[request("read", target="C1", mode="full", focus="first focus"),
                           request("read", target="C2", mode="full"),
                           request("read", target="C3", mode="local")]),
        decision(),
        decision(requests=[request("read", target="E1", mode="full", focus="different focus"),
                           request("read", target="C3", mode="full")]),
        decision(requests=[request("find", query="recovered")]),
        decision("answer", ["E2"]),
        answer("The recovered fact. [E2]", readings=[
            {"evidence_ref": "E2", "passages": ["The recovered fact."]}]),
    )
    result = run(
        f"Compare {URL} and {URL}/second and {URL}/success", model=model,
        search=lambda query: [DiscoveryCandidate("First", URL, "Search text.",
                                                 context_kind="provider_highlights")],
        fetch=fetch, clock=lambda: now[0],
    )
    packets = [packet for stage, _, packet, _ in model.calls if stage == "research"]
    assert [len(p["failed_external_reads"]) for p in packets] == [0, 2, 2, 3, 3]
    assert packets[2]["last_route"][0]["kind"] == "search"
    assert packets[2]["last_route"][0]["status"] == "ok"
    assert packets[4]["last_route"][0]["kind"] == "find"
    receipts = packets[-1]["failed_external_reads"]
    assert [r["candidate_ref"] for r in receipts] == ["C1", "C2", "C1"]
    assert receipts[0] == receipts[2] == {
        "candidate_ref": "C1", "provider": "linkup", "strategy": "static_fetch",
        "requested_mode": "full", "code": "linkup_timeout", "duration_seconds": 2.25,
    }
    assert all(type(r["duration_seconds"]) is float and math.isfinite(r["duration_seconds"])
               for r in receipts)
    assert fetches == [URL, URL + "/second", URL, URL + "/success"]
    assert packets[1]["last_route"][2]["code"] == "local_material_unavailable"
    assert "failed_external_read" not in packets[1]["last_route"][2]
    assert "failed_external_read" not in packets[3]["last_route"][1]
    assert result.evidence[-1].content == "The recovered fact."
    answer_packet = model.calls[-1][2]
    assert "failed_external_read" not in json.dumps(answer_packet)
    assert result.trace[-1]["budget"]["external_attempts"] == 5
    assert result.trace[-1]["budget"]["semantic_attempts"] == 6
    assert result.posture == "supported"


@pytest.mark.parametrize("reopen", [False, True])
def test_failed_read_history_resets_next_session_turn_and_is_not_persisted(tmp_path, reopen):
    def failed(url):
        raise LinkupTransportError("linkup_connection_failed")

    model = Script(decision(requests=[request("read", target="C1", mode="full")]),
                   decision("answer"), answer("Not established.", "unable"),
                   decision("answer"), answer("Still unknown.", "unable"))
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = ResearchSession.create(store=store, model=model, fetch=failed)
    session.ask(f"Read {URL}")
    assert model.calls[1][2]["failed_external_reads"][0]["code"] == "linkup_connection_failed"
    # The final failed route's receipt is filtered out even when Answer receives
    # the existing mechanical acquisition_limitations projection.
    assert "failed_external_read" not in json.dumps(model.calls[2][2])
    saved = store.load(session.metadata.session_id)
    assert "failed_external_read" not in repr(saved.state)
    assert "linkup_connection_failed" not in repr(saved.state)
    if reopen:
        session = ResearchSession.open(session.metadata.session_id, store=store, model=model, fetch=failed)
    session.ask("What about the follow-up?")
    assert model.calls[3][2]["failed_external_reads"] == []
    assert session.metadata.revision == 2


def test_budget_denial_is_not_a_failed_external_read_receipt():
    fetches = []
    model = Script(decision(requests=[request("read", target="C1", mode="full")]),
                   decision("answer"), answer("Unavailable.", "unable"))
    result = run(f"Read {URL}", model=model, limits=RunLimits(external_attempts=0),
                 fetch=lambda url: fetches.append(url))
    assert not fetches
    assert model.calls[1][2]["last_route"][0]["code"] == "external_attempts"
    assert model.calls[1][2]["failed_external_reads"] == []
    assert result.trace[-1]["budget"]["external_attempts"] == 0


def test_successful_fetch_with_invalid_local_range_is_not_failed_materialization():
    library = AcquisitionLibrary(fetch=lambda url: FetchedMaterial(url, "Short body."))
    library.allow_question_urls(URL)
    result = library.execute({"kind": "read", "target": URL, "start_char": 100, "end_char": 200},
                             before_external=lambda: None)
    assert result["status"] == "error"
    assert "failed_external_read" not in result
    assert len(library.acquisitions) == 1


@pytest.mark.parametrize("code", sorted(LINKUP_FAILURE_CODES))
def test_all_safe_linkup_codes_survive_body_free_diagnostics(code):
    diagnostics = TurnDiagnostics()
    diagnostics.observe({"stage": "research", "action": "acquisition_timing",
                         "kind": "read", "provider": "linkup", "mode": "full",
                         "status": "error", "code": code, "duration_seconds": 1.25,
                         "url": URL, "raw_body": "PRIVATE BODY", "headers": "PRIVATE HEADERS"})
    assert diagnostics.acquisitions[0]["code"] == code
    assert diagnostics.acquisitions[0]["duration_seconds"] == 1.25
    assert URL not in json.dumps(diagnostics.acquisitions)
    assert "PRIVATE" not in json.dumps(diagnostics.acquisitions)


def test_transport_to_forensics_keeps_fixed_code_and_body_free_projection(tmp_path):
    private = "SYNTHETIC_RAW_EXCEPTION_PAYLOAD"

    def post(*args, **kwargs):
        raise requests.exceptions.Timeout(private)

    diagnostics = TurnDiagnostics()
    forensic = ForensicLog(tmp_path / "forensic.jsonl")

    def observe(event):
        diagnostics.observe(event)
        forensic.append(event, session_id=None, revision_before=0)

    model = Script(decision(requests=[request("read", target=URL, mode="full")]),
                   decision("answer"), answer("No material recovered.", "unable"))
    result = run(f"PRIVATE QUESTION {URL}", model=model, observe=observe,
                 fetch=partial(fetch_linkup, api_key="offline", post=post))  # pragma: allowlist secret
    forensic_text = forensic.path.read_text(encoding="utf-8")
    body_free = json.dumps(diagnostics.record(session_id=None, revision_before=0,
                                             revision_after=1, result=result))
    assert "linkup_timeout" in forensic_text and "static_fetch" in forensic_text
    assert URL in forensic_text  # existing source-bearing request surface
    assert "linkup_timeout" in body_free
    assert URL not in body_free and "PRIVATE QUESTION" not in body_free
    assert private not in forensic_text + body_free + json.dumps(result.trace)
