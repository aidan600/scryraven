"""Offline subprocess and selection checks for the ordinary external Read race."""

import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from core import dual_read
from core.transport import FetchedMaterial

URL = "https://example.org/article?section=methods"
LINKUP_TEXT = "# Original equipment report\n\nThe tested compressor controls its outlet pressure."
EXA_TEXT = "# Original equipment report\n\nObserved flow rates match the specified conditions."
CHALLENGE = "# A required part of this site couldn’t load.\n\nYour browser is unsupported."


@pytest.fixture
def endpoint(monkeypatch):
    """Exercise real workers, both production transports and one local HTTP endpoint."""
    calls = []
    responses = {}
    lock = threading.Lock()
    processes = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            size = int(self.headers["Content-Length"])
            payload = json.loads(self.rfile.read(size))
            provider = self.path.removeprefix("/")
            with lock:
                calls.append((provider, payload, time.perf_counter()))
            delay, status, text = responses[provider]
            time.sleep(delay)
            content = ({"markdown": text} if provider == "linkup"
                       else {"results": [{"id": URL, "text": text}]})
            body = json.dumps(content).encode()
            try:
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                pass  # Deliberate local cancellation can close the socket first.

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def command(provider):
        return [sys.executable, "-c", (
            "import core.dual_read as worker\n"
            "from core import exa_transport, linkup_transport\n"
            f"linkup_transport.LINKUP_FETCH_URL = {base + '/linkup'!r}\n"
            f"exa_transport.EXA_CONTENTS_URL = {base + '/exa'!r}\n"
            f"worker._worker({provider!r})\n"
        )]

    real_popen = subprocess.Popen

    def record_process(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(dual_read, "_worker_command", command)
    monkeypatch.setattr(dual_read.subprocess, "Popen", record_process)
    monkeypatch.setenv("LINKUP_API_KEY", "local-test-only")
    monkeypatch.setenv("EXA_API_KEY", "local-test-only")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setattr(dual_read, "PEER_SECONDS", 0.2)
    try:
        yield calls, responses, processes
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
        assert all(process.poll() is not None for process in processes)


def fetch(seconds=3.5, providers=("linkup", "exa")):
    return dual_read.fetch_dual(URL, timeout_seconds=seconds, providers=providers)


@pytest.mark.parametrize("winner", ["linkup", "exa"])
def test_concurrent_exact_url_preserves_first_when_peer_has_no_clear_upgrade(endpoint, winner):
    calls, responses, _ = endpoint
    responses["linkup"] = (0 if winner == "linkup" else 0.1, 200, LINKUP_TEXT)
    responses["exa"] = (0 if winner == "exa" else 0.1, 200, EXA_TEXT)
    result = fetch()
    assert result.provider == result.first_usable_provider == winner
    assert result.selection == "first_usable"
    assert result.material == FetchedMaterial(URL, LINKUP_TEXT if winner == "linkup" else EXA_TEXT)
    assert [(a.provider, a.status, a.dispatched, a.charged) for a in result.attempts] == [
        ("linkup", "usable", True, True), ("exa", "usable", True, True),
    ]
    payloads = {provider: payload for provider, payload, _ in calls}
    assert payloads["linkup"] == {"url": URL}
    assert payloads["exa"] == {
        "ids": [URL], "text": {"verbosity": "full"}, "highlights": False, "maxAgeHours": 0,
    }
    assert len(calls) == 2
    linkup, exa = result.attempts
    assert abs(linkup.dispatch_offset_seconds - exa.dispatch_offset_seconds) < 0.15


def test_challenge_does_not_start_peer_timer_and_late_exa_is_retained(endpoint):
    _, responses, _ = endpoint
    responses.update(linkup=(0, 200, CHALLENGE), exa=(0.4, 200, EXA_TEXT))
    result = fetch()
    assert result.provider == result.first_usable_provider == "exa"
    assert result.material == FetchedMaterial(URL, EXA_TEXT)
    assert result.attempts[0].code == "read_access_challenge"


def test_clear_subset_replaced_with_single_broader_original(endpoint):
    _, responses, _ = endpoint
    original = "\n".join(
        f"Observation {i}: rotor vane angle {i + 5} controls the measured pressure."
        for i in range(30)
    )
    continuation = "\n".join(
        f"Control {i}: valve area {i + 7} sets the minimum observed flow."
        for i in range(15)
    )
    extended = original + "\n\n" + continuation
    responses.update(linkup=(0, 200, original), exa=(0.08, 200, extended))
    result = fetch()
    assert result.first_usable_provider == "linkup"
    assert result.provider == "exa"
    assert result.selection == "broader_original"
    assert result.material == FetchedMaterial(URL, extended)


def test_later_nasa_like_prose_beats_spurious_single_word_cells(endpoint):
    _, responses, _ = endpoint
    clean = "\n\n".join(
        f"Experiment {i} used an adjustable flow valve while the radial compressor feedback "
        f"was tested at threshold {i + 1} under a finite disturbance."
        for i in range(30)
    )
    broken = "| " + " | ".join(clean.split()) + " |"
    responses.update(linkup=(0.08, 200, clean), exa=(0, 200, broken))
    result = fetch()
    assert result.first_usable_provider == "exa"
    assert result.provider == "linkup"
    assert result.selection == "cleaner_structure"
    assert result.material == FetchedMaterial(URL, clean)


@pytest.mark.parametrize("provider", ["linkup", "exa"])
def test_configured_singleton_uses_ordinary_request_without_peer(endpoint, monkeypatch, provider):
    calls, responses, _ = endpoint
    peer_key = "EXA_API_KEY" if provider == "linkup" else "LINKUP_API_KEY"
    monkeypatch.delenv(peer_key)
    responses[provider] = (0, 200, LINKUP_TEXT)
    assert dual_read.configured_read_providers() == (provider,)
    result = fetch(providers=(provider,))
    assert result.provider == provider
    assert len(calls) == len(result.attempts) == 1
    assert result.attempts[0].status == "usable"


def test_provider_disappearing_after_plan_does_not_charge_undispatched_arm(endpoint, monkeypatch):
    calls, responses, _ = endpoint
    monkeypatch.delenv("EXA_API_KEY")
    responses["linkup"] = (0, 200, LINKUP_TEXT)
    result = fetch()
    assert len(calls) == 1
    assert result.provider == "linkup"
    assert result.attempts[1].code == "exa_configuration_missing"
    assert not result.attempts[1].dispatched and not result.attempts[1].charged


def test_both_fail_with_separate_safe_receipts(endpoint):
    _, responses, _ = endpoint
    responses.update(linkup=(0, 500, "sensitive test marker"), exa=(0, 200, ""))
    result = fetch()
    assert result.provider is result.material is result.first_usable_provider is None
    assert result.selection == "no_usable_material"
    assert [a.code for a in result.attempts] == [
        "linkup_endpoint_server_failed", "contents_material_unavailable",
    ]
    assert all(a.dispatched and a.charged for a in result.attempts)
    assert "sensitive test marker" not in repr(result)


def test_cancel_losing_post_and_reap_before_return(endpoint):
    _, responses, processes = endpoint
    responses.update(linkup=(0, 200, LINKUP_TEXT), exa=(5, 200, EXA_TEXT))
    started = time.perf_counter()
    result = fetch()
    assert time.perf_counter() - started < 3.5
    assert result.provider == "linkup"
    assert result.attempts[1].status == "cancelled"
    assert result.attempts[1].code == "read_peer_window_elapsed"
    assert result.attempts[1].dispatched and result.attempts[1].charged
    assert all(process.poll() is not None for process in processes)


def test_wall_deadline_kills_workers_despite_pending_socket_and_keeps_charges(endpoint):
    _, responses, processes = endpoint
    responses.update(linkup=(5, 200, LINKUP_TEXT), exa=(5, 200, EXA_TEXT))
    started = time.perf_counter()
    result = fetch(seconds=1.75)
    assert time.perf_counter() - started < 2.1
    assert result.material is None
    assert [(a.status, a.dispatched, a.charged) for a in result.attempts] == [
        ("deadline", True, True), ("deadline", True, True),
    ]
    assert all(process.poll() is not None for process in processes)


def test_no_turn_runway_keeps_noncharged_deadline_receipts(endpoint):
    calls, _, processes = endpoint
    result = fetch(seconds=0)
    assert not calls and not processes
    assert [(a.status, a.charged) for a in result.attempts] == [
        ("deadline", False), ("deadline", False),
    ]


def test_early_error_keeps_valid_36_second_result_with_remaining_turn_time(monkeypatch):
    """Virtualize time to cover the old 35-second boundary without a live wait."""
    now = 100.0
    events = []

    def launch(attempt, messages):
        events.append((100.01, attempt, {"kind": "ready"}))

    def release(attempt, url, deadline, release_at):
        events.append((release_at, attempt, {"kind": "dispatch", "time": release_at}))
        completed = release_at + (1 if attempt.provider == "linkup" else 36)
        message = {"kind": "result", "time": completed, "code": None}
        if attempt.provider == "linkup":
            message["code"] = "linkup_endpoint_server_failed"
        else:
            message["text"] = EXA_TEXT
        events.append((completed, attempt, message))
        attempt.released = True

    def next_event(messages, deadline):
        nonlocal now
        events.sort(key=lambda event: event[0])
        if not events or events[0][0] > deadline:
            now = deadline
            return None
        now, attempt, message = events.pop(0)
        return attempt, message

    monkeypatch.setattr(dual_read, "_clock", lambda: now)
    monkeypatch.setattr(dual_read, "_next_event", next_event)
    monkeypatch.setattr(dual_read._Attempt, "launch", launch)
    monkeypatch.setattr(dual_read._Attempt, "release", release)
    result = fetch(seconds=50)
    assert result.provider == "exa"
    assert result.material == FetchedMaterial(URL, EXA_TEXT)
    assert result.attempts[1].elapsed_seconds == 36


@pytest.mark.parametrize("material,code", [
    (FetchedMaterial(URL, " "), "unusable_fetch_material"),
    (FetchedMaterial("https://example.com/unrelated", LINKUP_TEXT), "read_identity_mismatch"),
    (FetchedMaterial(URL, CHALLENGE), "read_access_challenge"),
    (FetchedMaterial(URL, "# Error 404\n\nReturn to the homepage."), "read_landing_page"),
    (FetchedMaterial(URL, "You need to enable JavaScript to run this app."), "read_landing_page"),
    (FetchedMaterial(URL, "# Cloudflare outage report\n\n## Access denied\n\n"
                          "Many users saw a Cloudflare Ray ID."), None),
    (FetchedMaterial(URL, "§ 404. Administrative review."), None),
])
def test_validation_rejects_recognizable_interstitials_and_identity_mismatch(material, code):
    assert dual_read.validate_read_material(URL, material) == code


def test_no_upgrade_for_unrelated_text_or_navigation_bloat():
    assert dual_read._upgrade(LINKUP_TEXT, EXA_TEXT * 40) is None
    assert dual_read._upgrade(
        LINKUP_TEXT, LINKUP_TEXT + "\n" + "[More](/home) [Catalog](/products)\n" * 50,
    ) is None


def test_whitespace_pipes_do_not_stall_structural_comparison():
    # Four sparse cells previously caused the pipe-run regex to backtrack.
    blank = ("|" + " " * 100) * 4
    process = subprocess.run(
        [sys.executable, "-c", f"from core.dual_read import _cell_noise; print(_cell_noise({blank!r}))"],
        capture_output=True, text=True, check=True, timeout=3,
    )
    assert process.stdout.strip() == "0"


def test_comparison_abandons_malformed_markdown_when_time_expires(monkeypatch):
    # Repeated unterminated openers must not cause repeated long suffix scans.
    text = "](" * 499_000
    clock = iter((0.0, 0.0, 1.0))
    monkeypatch.setattr(dual_read, "_clock", lambda: next(clock))
    assert dual_read._upgrade(text, text + "x", deadline=0.1) is None
    with pytest.raises(StopIteration):
        next(clock)


def test_cleanup_timeout_schedules_final_reap_and_closes_parent_pipe():
    reaped = threading.Event()
    wait_calls = []

    class Process:
        stdin = type("Stdin", (), {"close": lambda self: wait_calls.append("closed")})()

        def wait(self, timeout=None):
            if timeout is not None:
                wait_calls.append("bounded")
                raise subprocess.TimeoutExpired("worker", timeout)
            wait_calls.append("reaped")
            reaped.set()

    attempt = dual_read._Attempt("linkup")
    attempt.process = Process()
    with pytest.raises(subprocess.TimeoutExpired):
        attempt.reap(time.perf_counter())
    assert reaped.wait(timeout=1)
    assert wait_calls[0] == "bounded"
    assert set(wait_calls[1:]) == {"reaped", "closed"}
