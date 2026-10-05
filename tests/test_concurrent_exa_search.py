"""Concurrent generic Exa Search transports; admission stays in request order."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

import pytest
from test_exa_transport import Response
from test_research_loop import Script, answer, decision, no_fetch, request

from core import exa_transport as exa
from core.exa_transport import DiscoveryCandidate, ExaTransportError
from core.transport import FetchedMaterial
from scryraven.acquisition import AcquisitionLibrary
from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.research import ANSWER_PROMPT, RESEARCH_PROMPT, RunLimits, run
from scryraven.sources import Evidence

ALPHA = "Alpha fact is seven."
BETA = "Beta fact is nine."
URL_A = "https://example.org/a"
URL_B = "https://example.org/b"


def lead(title, url, text):
    return DiscoveryCandidate(title, url, text, context_kind="provider_highlights")


def payload(query):
    return request(query=query)


def unable():
    return answer("The material does not establish this.", "unable")


def identity(items):
    return [(item.id, item.source_id, item.url, item.title, item.content, item.acquisition)
            for item in items]


def novelty_of(result):
    return {key: value for key, value in result.items() if key == "search_novelty_receipt"} | {
        "status": result["status"], "code": result.get("code"),
        "material_ids": result["material_ids"], "candidate_refs": result["candidate_refs"],
    }


def serial_library(batches, queries):
    library = AcquisitionLibrary(search=lambda query: list(batches[query]))
    results = [library.execute(payload(query), before_external=lambda: None) for query in queries]
    return library, results


def test_prompt_and_decision_contracts_stay_byte_stable():
    assert hashlib.sha256(RESEARCH_PROMPT.encode()).hexdigest() == (
        "dffa58c64c759c28200f2d65c181fe1d70a44f038604a5f58e60529354a51487"  # pragma: allowlist secret
    )
    assert hashlib.sha256(ANSWER_PROMPT.encode()).hexdigest() == (
        "6a7eff715c2030be461b81a21aed21c646de464f5d2b4570ba0ca5ed47ba217b"  # pragma: allowlist secret
    )


def test_two_search_workers_enter_transport_together_and_out_of_order_completion_keeps_ids():
    batches = {
        "one": [lead("Alpha", URL_A, ALPHA)],
        "two": [lead("Beta", URL_B, BETA)],
    }
    entered = Barrier(2, timeout=2)
    second_done = Event()

    def search(query):
        entered.wait()
        if query == "two":
            second_done.set()
        else:
            assert second_done.wait(timeout=2)
        return list(batches[query])

    model = Script(
        decision(requests=[request(query="one"), request(query="two")]),
        decision("answer", ["E1"]),
        answer(f"{ALPHA} [E1]", readings=[{"evidence_ref": "E1", "passages": [ALPHA]}]),
    )
    result = run("What is the alpha fact?", model=model, search=search, fetch=no_fetch)
    library, serial = serial_library(batches, ("one", "two"))
    assert identity(result.evidence) == identity(library.acquisitions)
    assert result.evidence[0].content == ALPHA
    assert result.evidence[1].content == BETA
    assert result.citations[0].materials[0].id == "E1"
    route = model.calls[1][2]["last_route"]
    assert [item["material_ids"] for item in route] == [item["material_ids"] for item in serial]
    assert [item["candidate_refs"] for item in route] == [item["candidate_refs"] for item in serial]
    assert [item["id"] for item in model.calls[1][2]["evidence"]] == ["E1", "E2"]
    receipts = [event["result"]["search_novelty_receipt"] for event in result.trace
                if event["action"] == "acquisition_result"]
    assert receipts == [item["search_novelty_receipt"] for item in serial]
    group = next(event for event in result.trace if event["action"] == "search_concurrency_group")
    assert group["request_count"] == 2 and group["successful_request_count"] == 2
    assert "one" not in json.dumps(group) and URL_A not in json.dumps(group)
    assert result.trace[-1]["budget"]["external_attempts"] == 2


def test_concurrent_transport_plus_serial_admission_matches_ordinary_execution():
    batches = {
        "one": [lead("Alpha", URL_A, ALPHA)],
        "two": [lead("Alpha", URL_A, ALPHA), lead("Beta", URL_B, BETA)],
        "three": [lead("Alpha", URL_A, "Alpha fact is seven. A later qualification.")],
    }
    queries = ("one", "two", "three")
    serial_lib, serial = serial_library(batches, queries)
    entered = Barrier(3, timeout=2)
    release = Event()

    def search(query):
        entered.wait()
        if query == "three":
            release.set()
        else:
            assert release.wait(timeout=2)
        return list(batches[query])

    library = AcquisitionLibrary(search=search)
    plans = [library.plan_generic_search(payload(query)) for query in queries]
    with ThreadPoolExecutor(max_workers=3) as pool:
        outcomes = list(pool.map(lambda plan: _transport(library, plan), plans))
    concurrent = [library.admit_transported_search(plan, outcome) for plan, outcome in zip(plans, outcomes)]
    assert library.acquisitions == serial_lib.acquisitions
    assert library.materials == serial_lib.materials
    assert library.candidates == serial_lib.candidates
    assert library.catalog() == serial_lib.catalog()
    assert [novelty_of(item) for item in concurrent] == [novelty_of(item) for item in serial]
    assert [item.source_id for item in library.acquisitions] == ["E1", "E2", "E1"]
    assert serial[1]["search_novelty_receipt"]["exact_reused_material_count"] == 1
    assert serial[1]["search_novelty_receipt"]["known_candidate_count"] == 1
    assert serial[2]["search_novelty_receipt"]["new_candidate_count"] == 0
    assert serial[2]["search_novelty_receipt"]["new_material_count"] == 1


def _transport(library, plan):
    started = 0.0
    try:
        leads = library.search(plan["query"])
    except Exception as exc:  # pragma: no cover - this fixture does not fail
        return {"code": "search_failed", "leads": None, "started_at": started, "ended_at": 1.0,
                "detail": str(exc)}
    return {"code": None, "leads": list(leads), "started_at": started, "ended_at": 1.0}


def test_failure_keeps_its_position_and_does_not_cancel_the_other_search():
    entered = Barrier(2, timeout=2)
    failed = Event()

    def search(query):
        entered.wait()
        if query == "one":
            assert failed.wait(timeout=2)
            raise RuntimeError("SECRET provider body https://secret.example/raw")
        failed.set()
        return [lead("Beta", URL_B, BETA)]

    model = Script(decision(requests=[request(query="one"), request(query="two")]),
                   decision("answer"), unable())
    result = run("Value?", model=model, search=search, fetch=no_fetch)
    route = model.calls[1][2]["last_route"]
    assert [item["status"] for item in route] == ["error", "ok"]
    assert route[0]["code"] == "search_failed"
    assert route[1]["material_ids"] == ["E1"]
    assert result.evidence == (Evidence("E1", URL_B, "Beta", BETA, "provider_highlights"),)
    rendered = json.dumps(result.trace)
    assert "SECRET" not in rendered and "secret.example" not in rendered
    assert result.trace[-1]["budget"]["external_attempts"] == 2


def test_configuration_missing_stays_a_fixed_code_beside_a_success(monkeypatch):
    entered = Barrier(2, timeout=2)

    def search(query):
        entered.wait()
        if query == "one":
            raise ExaTransportError("exa_configuration_missing")
        return [lead("Beta", URL_B, BETA)]

    model = Script(decision(requests=[request(query="one"), request(query="two")]),
                   decision("answer"), unable())
    result = run("Value?", model=model, search=search, fetch=no_fetch)
    route = model.calls[1][2]["last_route"]
    assert [item.get("code") for item in route] == ["exa_configuration_missing", None]
    assert result.evidence[0].id == "E1"


def test_deep_is_preassigned_before_dispatch_even_when_auto_finishes_first(monkeypatch):
    monkeypatch.setenv(exa.EXA_API_KEY_ENV, "offline-test-value")
    entered = Barrier(2, timeout=2)
    release_deep = Event()
    payloads = []
    gate = Lock()

    def post(url, **kwargs):
        query = kwargs["json"]["query"]
        with gate:
            payloads.append((query, kwargs["json"]["type"]))
        entered.wait()
        if query == "second":
            release_deep.set()
        else:
            assert release_deep.wait(timeout=2)
        slug = "first" if query == "first" else "second"
        return Response({"results": [{"url": f"https://example.test/{slug}", "title": slug,
                                      "highlights": [f"The {slug} stated value."]}]})

    monkeypatch.setattr(exa.requests, "post", post)
    model = Script(decision(requests=[request(query="first"), request(query="second")]),
                   decision("answer"), unable())
    result = run("Value?", model=model)
    assert sorted(payloads) == [("first", "deep"), ("second", "auto")]
    assert [item.url for item in result.evidence] == [
        "https://example.test/first", "https://example.test/second",
    ]
    timings = [event for event in result.trace if event["action"] == "acquisition_timing"]
    assert [event["provider_search_type"] for event in timings] == ["deep", "auto"]
    assert [event["request_index"] for event in timings] == [1, 2]


def test_failed_deep_still_consumes_bootstrap_when_auto_finishes_first(monkeypatch):
    monkeypatch.setenv(exa.EXA_API_KEY_ENV, "offline-test-value")
    entered = Barrier(2, timeout=2)
    release_deep = Event()
    payloads = []
    gate = Lock()

    def post(url, **kwargs):
        query = kwargs["json"]["query"]
        with gate:
            payloads.append((query, kwargs["json"]["type"]))
        if query == "later":
            return Response({"results": [{"url": "https://example.test/later",
                                          "highlights": ["Later value."]}]})
        entered.wait()
        if query == "second":
            release_deep.set()
            return Response({"results": [{"url": "https://example.test/second",
                                          "highlights": ["Second value."]}]})
        assert release_deep.wait(timeout=2)
        raise OSError("SECRET deep failure")

    monkeypatch.setattr(exa.requests, "post", post)
    model = Script(decision(requests=[request(query="first"), request(query="second")]),
                   decision(requests=[request(query="later")]),
                   decision("answer"), unable())
    result = run("Value?", model=model)
    assert ("first", "deep") in payloads
    assert ("second", "auto") in payloads
    assert ("later", "auto") in payloads
    first_route = model.calls[1][2]["last_route"]
    assert [item["status"] for item in first_route] == ["error", "ok"]
    assert first_route[0]["code"] == "search_failed"
    assert "SECRET" not in json.dumps(result.trace)
    assert [item.url for item in result.evidence] == [
        "https://example.test/second", "https://example.test/later",
    ]


def test_consumed_bootstrap_assigns_auto_to_the_whole_group(monkeypatch):
    monkeypatch.setenv(exa.EXA_API_KEY_ENV, "offline-test-value")
    types = []
    gate = Lock()

    def post(url, **kwargs):
        with gate:
            types.append(kwargs["json"]["type"])
        return Response({"results": [{"url": "https://example.test/fact",
                                      "highlights": ["The stated value is seven."]}]})

    monkeypatch.setattr(exa.requests, "post", post)
    model = Script(decision(requests=[request(query="one"), request(query="two")]),
                   decision("answer"), unable())
    run("Value?", model=model, session_turn=2)
    assert types == ["auto", "auto"] or sorted(types) == ["auto", "auto"]


@pytest.mark.parametrize(("attempts", "queries", "expected_calls", "expected_external"), [
    (2, ("one", "two"), {"one", "two"}, 2),
    (1, ("one", "two", "three"), ["one"], 1),
    (0, ("one", "two", "three"), [], 0),
])
def test_group_reservation_does_not_overspend_external_attempts(
    attempts, queries, expected_calls, expected_external, monkeypatch,
):
    calls = []
    gate = Lock()

    def search(query):
        with gate:
            calls.append(query)
        return [lead(query, f"https://example.org/{query}", f"The {query} value.")]

    def fail_pool(*args, **kwargs):
        if attempts < 2:
            raise AssertionError("concurrent executor")
        return ThreadPoolExecutor(*args, **kwargs)

    monkeypatch.setattr("scryraven.research.ThreadPoolExecutor", fail_pool)
    model = Script(decision(requests=[request(query=query) for query in queries]),
                   decision("answer"), unable())
    result = run("Value?", model=model, search=search, fetch=no_fetch,
                 limits=RunLimits(external_attempts=attempts))
    assert set(calls) == set(expected_calls)
    assert len(calls) == len(expected_calls)
    assert result.trace[-1]["budget"]["external_attempts"] == expected_external
    if attempts == 1:
        assert [item["code"] for item in model.calls[1][2]["last_route"][1:]] == [
            "external_attempts", "external_attempts",
        ]


def test_expired_deadline_does_not_dispatch_the_group():
    now = {"t": 0.0}

    def expire(_packet):
        now["t"] = 10.0
        return decision(requests=[request(query="one"), request(query="two")])

    def search(query):
        raise AssertionError("provider called")

    result = run("Value?", model=Script(expire), search=search, fetch=no_fetch,
                 limits=RunLimits(seconds=5), clock=lambda: now["t"])
    assert result.posture == "unable"
    assert not any(event["action"] == "search_concurrency_group" for event in result.trace)


def test_mixed_operations_do_not_use_the_concurrent_executor(monkeypatch):
    monkeypatch.setattr(
        "scryraven.research.ThreadPoolExecutor",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("concurrent executor")),
    )
    state = {"in_flight": 0, "max": 0}
    gate = Lock()

    def enter():
        with gate:
            state["in_flight"] += 1
            state["max"] = max(state["max"], state["in_flight"])

    def leave():
        with gate:
            state["in_flight"] -= 1

    def search(query):
        enter()
        try:
            return [lead("Alpha", URL_A, ALPHA)]
        finally:
            leave()

    def lexical(query):
        enter()
        try:
            return [lead("Lex", "https://example.org/lex", "Lexical navigation")]
        finally:
            leave()

    def fetch(url):
        enter()
        try:
            return FetchedMaterial(url, "Fetched source text.")
        finally:
            leave()

    routes = [
        ([request(query="one"), request("read", query="", target="C1")], ["search", "read"]),
        ([request(query="one"), request("search_lexical", query="literal phrase")], ["search", "search_lexical"]),
        ([request("read", query="", target=URL_A), request("read", query="", target=URL_B)], ["read", "read"]),
        ([request("find", query="alpha"), request("find", query="alpha")], ["find", "find"]),
        ([request(query="one"), request("read", query="", target="C1"), request(query="two")],
         ["search", "read", "search"]),
    ]
    for requests, kinds in routes:
        state["max"] = 0
        model = Script(decision(requests=requests), decision("answer"), unable())
        result = run(f"Read {URL_A} and {URL_B}", model=model, search=search,
                     lexical_search=lexical, fetch=fetch)
        assert state["max"] <= 1
        assert [event["kind"] for event in result.trace if event["action"] == "acquisition_timing"] == kinds
        assert not any(event["action"] == "search_concurrency_group" for event in result.trace)


def test_find_then_search_pair_overlaps_only_the_searches():
    entered = Barrier(2, timeout=2)

    def search(query):
        entered.wait()
        return [lead(query, f"https://example.org/{query}", f"The {query} value.")]

    model = Script(
        decision(requests=[request("find", query="missing"), request(query="one"), request(query="two")]),
        decision("answer"), unable(),
    )
    result = run("Value?", model=model, search=search, fetch=no_fetch)
    timings = [event for event in result.trace if event["action"] == "acquisition_timing"]
    assert [event["kind"] for event in timings] == ["find", "search", "search"]
    group = next(event for event in result.trace if event["action"] == "search_concurrency_group")
    assert (group["first_request_index"], group["last_request_index"], group["request_count"]) == (2, 3, 2)


def test_group_larger_than_three_never_submits_more_than_three_workers(monkeypatch):
    real = ThreadPoolExecutor
    pools = []

    class RecordingExecutor:
        def __init__(self, max_workers):
            self.max_workers = max_workers
            self.submits = 0
            self._pool = real(max_workers=max_workers)
            pools.append(self)

        def submit(self, fn, *args, **kwargs):
            self.submits += 1
            return self._pool.submit(fn, *args, **kwargs)

        def __enter__(self):
            self._pool.__enter__()
            return self

        def __exit__(self, *args):
            return self._pool.__exit__(*args)

    monkeypatch.setattr("scryraven.research.ThreadPoolExecutor", RecordingExecutor)
    calls = []
    call_gate = Lock()
    entered = Barrier(3, timeout=2)

    def search(query):
        with call_gate:
            calls.append(query)
        if query in {"q1", "q2", "q3"}:
            entered.wait()
        return [lead(query, f"https://example.org/{query}", f"The {query} value.")]

    requests = [request(query=f"q{index}") for index in range(1, 5)]
    model = Script(decision(requests=requests), decision("answer"), unable())
    result = run("Value?", model=model, search=search, fetch=no_fetch)
    assert calls[:3] and set(calls) == {"q1", "q2", "q3", "q4"}
    assert [(pool.max_workers, pool.submits) for pool in pools] == [(3, 3)]
    assert [item.id for item in result.evidence] == ["E1", "E2", "E3", "E4"]
    assert [item.url.rsplit("/", 1)[-1] for item in result.evidence] == ["q1", "q2", "q3", "q4"]


def test_five_searches_form_a_bounded_second_group(monkeypatch):
    real = ThreadPoolExecutor
    pools = []

    class RecordingExecutor:
        def __init__(self, max_workers):
            self.max_workers = max_workers
            self.submits = 0
            self._pool = real(max_workers=max_workers)
            pools.append(self)

        def submit(self, fn, *args, **kwargs):
            self.submits += 1
            return self._pool.submit(fn, *args, **kwargs)

        def __enter__(self):
            self._pool.__enter__()
            return self

        def __exit__(self, *args):
            return self._pool.__exit__(*args)

    monkeypatch.setattr("scryraven.research.ThreadPoolExecutor", RecordingExecutor)

    def search(query):
        return [lead(query, f"https://example.org/{query}", f"The {query} value.")]

    model = Script(decision(requests=[request(query=f"q{index}") for index in range(1, 6)]),
                   decision("answer"), unable())
    result = run("Value?", model=model, search=search, fetch=no_fetch)
    assert [(pool.max_workers, pool.submits) for pool in pools] == [(3, 3), (2, 2)]
    assert [item.id for item in result.evidence] == [f"E{index}" for index in range(1, 6)]


def test_observer_failure_does_not_change_evidence_or_the_answer():
    batches = {
        "one": [lead("Alpha", URL_A, ALPHA)],
        "two": [lead("Beta", URL_B, BETA)],
    }

    def search(query):
        return list(batches[query])

    def script():
        return Script(decision(requests=[request(query="one"), request(query="two")]),
                      decision("answer", ["E1"]),
                      answer(f"{ALPHA} [E1]", readings=[{"evidence_ref": "E1", "passages": [ALPHA]}]))

    control = run("What is the alpha fact?", model=script(), search=search, fetch=no_fetch)

    def observe(event):
        raise RuntimeError("diagnostic observer failed")

    result = run("What is the alpha fact?", model=script(), search=search, fetch=no_fetch, observe=observe)
    assert result.evidence == control.evidence
    assert result.answer == control.answer
    assert result.posture == control.posture
    assert result.citations == control.citations


def test_dogfood_keeps_only_body_free_concurrency_fields():
    diagnostics = TurnDiagnostics()
    diagnostics.observe({
        "stage": "research", "action": "search_concurrency_group",
        "route_index": 1, "first_request_index": 1, "last_request_index": 2,
        "request_count": 2, "successful_request_count": 2,
        "started_elapsed_seconds": 1, "ended_elapsed_seconds": 2.5,
        "group_span_seconds": 1.5, "summed_transport_seconds": 3,
        "overlap_seconds": 1.5, "query": "SECRET objective",
        "url": "https://secret.example/item", "provider_payload": {"raw": True},
    })
    saved = diagnostics.search_concurrency_groups[0]
    rendered = json.dumps(saved)
    assert "SECRET" not in rendered and "secret.example" not in rendered and "provider_payload" not in saved
    assert saved["overlap_seconds"] == 1.5
    record = diagnostics.record(session_id=None, revision_before=0, revision_after=None)
    assert record["search_concurrency_groups"] == [saved]


def test_concurrent_exa_calls_share_the_timeout_snapshotted_at_dispatch(monkeypatch):
    monkeypatch.setenv(exa.EXA_API_KEY_ENV, "offline-test-value")
    entered = Barrier(2, timeout=2)
    timeouts = []
    gate = Lock()
    now = {"t": 0.0}

    def post(url, **kwargs):
        with gate:
            timeouts.append(kwargs["timeout"])
        entered.wait()
        if kwargs["json"]["query"] == "first":
            now["t"] = 40.0
        return Response({"results": [{"url": "https://example.test/fact",
                                      "highlights": ["The stated value is seven."]}]})

    monkeypatch.setattr(exa.requests, "post", post)
    model = Script(decision(requests=[request(query="first"), request(query="second")]),
                   decision("answer"), unable())
    run("Value?", model=model, clock=lambda: now["t"], limits=RunLimits(seconds=300))
    assert timeouts == [300.0, 300.0]
