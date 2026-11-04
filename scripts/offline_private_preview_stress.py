"""Offline hosted resource probe. No real credentials, identities or provider I/O.

Run with the repository's dev and hosted dependencies installed. The parent uses
loopback HTTP; a separate measured child runs the production application factory,
Waitress and ordinary research/persistence. Only downstream transport replies are
synthetic. All artifacts belong in a new disposable directory outside the repo.
"""

from __future__ import annotations

import argparse
import ctypes
import ipaddress
import json
import os
import platform
import socket
import subprocess
import sys
from collections import Counter
from io import BytesIO
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic, process_time, sleep
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from pdf_fixtures import text_pdf
from PIL import Image
from test_hosted_identity import Response as KeyResponse
from test_hosted_identity import jwks, token
from test_reading_room import Form
from test_research_loop import answer, decision, request
from test_run_settings_integration import response

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.hosted import AccessTokenValidator, HostedConfig
from scryraven.model import OpenAIModel
from scryraven.run_settings import RunSettings
from scryraven.session_store import SQLiteSessionStore


def config(folder):
    return HostedConfig("stress.example.test", "https://offline.cloudflareaccess.com", "offline-stress",
                        "owner@example.test", frozenset({"alice@example.test", "bob@example.test"}),
                        folder, RunSettings("openai", "gpt-6.1-terra", "medium", "gpt-6.1-sol", "medium", "fast", 40))


def loopback_only():
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex

    def permitted(address):
        try:
            return isinstance(address, tuple) and ipaddress.ip_address(address[0]).is_loopback
        except ValueError:
            return False

    def connect(self, address):
        if not permitted(address):
            raise AssertionError("Offline resource probe blocked non-loopback connection")
        return original(self, address)

    def connect_ex(self, address):
        if not permitted(address):
            raise AssertionError("Offline resource probe blocked non-loopback connection")
        return original_ex(self, address)

    socket.socket.connect, socket.socket.connect_ex = connect, connect_ex


def limit_two_cpus():
    if sys.platform == "win32":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        handle = kernel.GetCurrentProcess()
        process_mask, system_mask = ctypes.c_size_t(), ctypes.c_size_t()
        if not kernel.GetProcessAffinityMask(ctypes.c_void_p(handle), ctypes.byref(process_mask), ctypes.byref(system_mask)):
            raise OSError("Cannot obtain child process affinity")
        chosen = sum(1 << i for i in [i for i in range(process_mask.value.bit_length()) if process_mask.value & (1 << i)][:2])
        if not kernel.SetProcessAffinityMask(ctypes.c_void_p(handle), ctypes.c_size_t(chosen)):
            raise OSError("Cannot limit measured child to two CPUs")
        return chosen.bit_count()
    allowed = sorted(os.sched_getaffinity(0))[:2]
    os.sched_setaffinity(0, allowed)
    return len(allowed)


def memory_bytes():
    if sys.platform == "win32":
        class Counters(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage",
                "PeakPagefileUsage", "PrivateUsage")]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        stats = Counters()
        stats.cb = ctypes.sizeof(stats)
        if not ctypes.WinDLL("psapi").GetProcessMemoryInfo(ctypes.c_void_p(kernel.GetCurrentProcess()),
                                                         ctypes.byref(stats), stats.cb):
            raise OSError("Cannot measure child process memory")
        return {"resident_bytes": stats.WorkingSetSize, "private_bytes": stats.PrivateUsage,
                "os_peak_resident_bytes": stats.PeakWorkingSetSize, "os_peak_commit_bytes": stats.PeakPagefileUsage}
    import resource
    pages = int(Path("/proc/self/statm").read_text().split()[1])
    return {"resident_bytes": pages * os.sysconf("SC_PAGE_SIZE"),
            "os_peak_resident_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def child(folder):
    from waitress import server as waitress_server
    from waitress import wasyncore

    from scryraven.wsgi import create_application

    loopback_only()
    cpu_count = limit_two_cpus()
    settings = config(folder)
    keyset = json.loads((folder / "public-jwks.json").read_text())
    lock, stop = Lock(), Event()
    stats = {"requests": [], "sources": [], "answer_barriers": [], "errors": []}
    models = []

    def search(query):
        name = query.split()[0]
        return [DiscoveryCandidate(f"Synthetic source {i}", f"https://example.test/{name}/{i}", "Navigation only.")
                for i in range(3)]

    def fetch(url):
        # Three 31,000-character original sources reach each Answer, plus a
        # 32,000-character exact attached-document view: 125,000 source chars.
        name = urlsplit(url).path.split("/")[1]
        content = (f"Synthetic {name} source: the stated value is seven. " * 800)[:31_000]
        with lock:
            stats["sources"].append({"name": name, "characters": len(content)})
        return FetchedMaterial(url, content)

    def factory(selected):
        call = 0
        seen = []

        def synthetic_post(url, **kwargs):
            nonlocal call
            assert url == "https://api.openai.com/v1/responses"
            # Include ordinary JSON encode/decode work, without a network call.
            encoded = json.dumps(kwargs["json"])
            payload = json.loads(encoded)
            message = next(message for message in payload["input"] if message.get("role") == "user")
            raw = "".join(block.get("text", "") for block in message["content"])
            packet = json.loads(raw)
            name = packet["question"].split()[0]
            stage = payload["text"]["format"]["name"]
            images = sum(block["type"] == "input_image" for message in payload["input"]
                         for block in message.get("content", []))
            assert images == 1
            for item in packet["evidence"]:
                if item["id"] not in seen:
                    seen.append(item["id"])
                assert item.get("source_kind") == "user_document" or f"/{name}/" in item["url"]
            with lock:
                stats["requests"].append({"name": name, "stage": stage, "wire_bytes": len(encoded.encode()),
                    "source_characters": sum(len(item["content"]) for item in packet["evidence"]), "image_count": images,
                    "model": payload["model"], "service_tier": payload.get("service_tier")})
            if stage == "research":
                if call == 0:
                    output = decision(requests=[request(query=name)])
                elif call == 1:
                    reads = [request("read", target=f"C{i}", mode="full") for i in range(1, 4)]
                    reads.append({**request("read", target="D1", mode="local"), "start_char": 0, "end_char": 32_000})
                    output = decision(requests=reads)
                else:
                    output = decision("return", seen)
                call += 1
            else:
                assert sum(len(item["content"]) for item in packet["evidence"]) >= 120_000
                with lock:
                    stats["answer_barriers"].append(name)
                (folder / (name + ".ready")).write_text("ready")
                deadline = monotonic() + 90
                while not (folder / (name + ".release")).exists():
                    assert monotonic() < deadline, "Synthetic provider barrier timed out"
                    sleep(0.025)
                refs = ", ".join(item["id"] for item in packet["evidence"])
                output = answer(f"The synthetic {name} sources state seven. [{refs}]")
            return response(payload, output)

        def post(url, **kwargs):
            try:
                return synthetic_post(url, **kwargs)
            except Exception:
                import traceback
                with lock:
                    stats["errors"].append("synthetic_transport_exception")
                traceback.print_exc()
                raise

        model = OpenAIModel(selected.model_config(), backend="api", post=post)
        models.append(model)
        return model

    app = create_application(config=settings,
        identity_validator=AccessTokenValidator(settings, get=lambda *_args, **_kwargs: KeyResponse(keyset)),
        run_model_factory=factory,
        session_options={"search": search, "fetch": fetch, "lexical_search": search})
    server = waitress_server.create_server(app, host="127.0.0.1", port=0, threads=8, url_scheme="https",
        clear_untrusted_proxy_headers=True, expose_tracebacks=False, asyncore_loop_timeout=0.1, map={})
    started_wall, started_cpu = monotonic(), process_time()
    samples = []

    def sample():
        while not stop.wait(0.1):
            samples.append({"wall_seconds": monotonic() - started_wall,
                            "cpu_seconds": process_time() - started_cpu, **memory_bytes()})

    sampler = Thread(target=sample, daemon=True)
    worker = Thread(target=server.run, daemon=True)
    sampler.start()
    worker.start()
    (folder / "listening.json").write_text(json.dumps({"port": int(server.effective_port)}))
    try:
        while not (folder / "stop").exists():
            sleep(0.05)
    finally:
        manager = app.extensions["research_jobs"]
        for name in stats["answer_barriers"]:
            (folder / (name + ".release")).touch()
        assert manager.wait_idle(30)
        manager.shutdown()
        app.extensions["hosted_diagnostics"].close()
        server.task_dispatcher.shutdown()
        server.close()
        wasyncore.close_all(map=server._map)
        worker.join(5)
        stop.set()
        sampler.join(5)
        samples.append({"wall_seconds": monotonic() - started_wall, "cpu_seconds": process_time() - started_cpu,
                        **memory_bytes()})
        stats.update({"samples": samples, "affinity_cpus": cpu_count, "logical_host_cpus": os.cpu_count(),
            "platform": platform.platform(), "python": sys.version.split()[0], "model_instances": len(models),
            "distinct_model_instances": len({id(item) for item in models}),
            "final_states": dict(Counter(job.state for job in manager.list())),
            "database_bytes": settings.database.stat().st_size,
            "wall_seconds": monotonic() - started_wall, "cpu_seconds": process_time() - started_cpu})
        (folder / "child-result.json").write_text(json.dumps(stats, indent=2))


def wait_for(predicate, timeout=30):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        value = predicate()
        if value:
            return value
        sleep(0.025)
    raise AssertionError("Offline stress condition timed out")


def run_probe(folder):
    folder.mkdir(parents=True, exist_ok=False)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    (folder / "public-jwks.json").write_text(json.dumps(jwks(key)))
    settings = config(folder)
    env = {name: os.environ[name] for name in ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "PYTHONPATH") if name in os.environ}
    env.update({"OPENAI_API_KEY": "synthetic-offline-stress-placeholder", "PYTHONDONTWRITEBYTECODE": "1"})  # pragma: allowlist secret
    with (folder / "child.stdout.txt").open("w") as stdout, (folder / "child.stderr.txt").open("w") as stderr:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--child", "--output", str(folder)],
                                   cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        try:
            wait_for(lambda: (folder / "listening.json").exists() or process.poll() is not None)
            assert process.poll() is None, "Measured child failed startup; inspect synthetic child.stderr.txt"
            port = json.loads((folder / "listening.json").read_text())["port"]
            base = f"http://127.0.0.1:{port}"
            client = requests.Session()
            client.trust_env = False
            loopback_only()
            users = {name: {"Host": settings.hostname, "Cf-Access-Jwt-Assertion": token(settings, key, email=name + "@example.test")}
                     for name in ("alice", "bob")}
            # Compressible enough to stay below the ordinary 8 MB limit, but
            # representative high-resolution image decode/base64 work remains.
            image = BytesIO()
            Image.frombytes("RGB", (1536, 1024), __import__("random").Random(7).randbytes(1536 * 1024 * 3)).save(image, "PNG")
            image_bytes = image.getvalue()
            document = text_pdf([("Synthetic attached context. The stated value is seven. " * 1200) for _ in range(6)])
            transitions = []
            paths = {}

            def status(owner):
                reply = client.get(base + "/jobs/status", headers=users[owner], timeout=10)
                assert reply.status_code == 200
                return reply.json()["jobs"]

            def submit(name, owner):
                page = client.get(base + "/", headers=users[owner], timeout=10)
                fields = Form(page.text, "/ask").fields
                fields["question"] = name + " What value do the synthetic sources and attached context state?"
                reply = client.post(base + "/ask", headers={**users[owner], "Origin": settings.origin}, data=fields,
                    files=[("files", (name + ".pdf", document, "application/pdf")),
                           ("files", (name + ".png", image_bytes, "image/png"))], allow_redirects=False, timeout=30)
                assert reply.status_code == 303, (reply.status_code, reply.text[-1200:])
                paths[name] = (owner, reply.headers["Location"])

            for label, owners in (("same", ["alice"] * 5), ("mixed", ["alice", "bob", "alice", "bob", "bob"])):
                names = [f"{label}_{i}" for i in range(5)]
                for name, owner in zip(names[:4], owners[:4], strict=True):
                    submit(name, owner)
                    wait_for(lambda: (folder / (name + ".ready")).exists())
                store = SQLiteSessionStore(settings.database)
                active = {job.question.split()[0]: job.state for job in store.list_jobs() if job.question.split()[0] in names}
                assert list(active.values()).count("researching") == 4, active
                transitions.append({"scenario": label, "event": "four_overlapping", "states": active})
                submit(names[4], owners[4])
                active = {job.question.split()[0]: job.state for job in store.list_jobs() if job.question.split()[0] in names}
                assert active[names[4]] == "queued" and list(active.values()).count("researching") == 4, active
                transitions.append({"scenario": label, "event": "fifth_queued", "states": active})
                for owner in set(owners):
                    visible = {row["session_id"] for row in status(owner)}
                    assert all(path.split("/")[2].split("#")[0] in visible for who, path in paths.values() if who == owner)
                    assert all(path.split("/")[2].split("#")[0] not in visible for who, path in paths.values() if who != owner)
                # A later ordinary submission cannot stop any of the first four.
                sleep(0.5)
                assert all(store.get_job(job.job_id).state == "researching" for job in store.list_jobs()
                           if job.question.split()[0] in names[:4])
                (folder / (names[0] + ".release")).touch()
                wait_for(lambda: (folder / (names[4] + ".ready")).exists())
                active = {job.question.split()[0]: job.state for job in store.list_jobs() if job.question.split()[0] in names}
                assert active[names[0]] == "completed" and list(active.values()).count("researching") == 4, active
                transitions.append({"scenario": label, "event": "queued_started_automatically", "states": active})
                for name in names:
                    (folder / (name + ".release")).touch()
                wait_for(lambda: all(job.state == "completed" for job in store.list_jobs()))
                for name in names:
                    owner, path = paths[name]
                    page = client.get(base + path, headers=users[owner], timeout=20)
                    assert page.status_code == 200 and f"synthetic {name} sources state seven" in page.text
                    job, = [job for job in store.list_jobs() if job.question.startswith(name + " ")]
                    saved = store.load(job.session_id)
                    assert len(saved.documents) == len(saved.images) == 1
                    assert saved.documents[0].original_pdf == document and saved.images[0].original_image == image_bytes
                    assert len(saved.state.turns) == 1 and len(saved.state.turns[0].citations) == 4
                    assert job.run_settings == settings.run_settings and job.run_receipt["requests"]
                transitions.append({"scenario": label, "event": "all_completed", "count": 5})
            client.close()
            (folder / "stop").touch()
            assert process.wait(30) == 0
            result = json.loads((folder / "child-result.json").read_text())
            samples = result.pop("samples")
            (folder / "samples.json").write_text(json.dumps(samples, indent=2))
            peaks = {key: max(row.get(key, 0) for row in samples) for key in samples[0] if key.endswith("bytes")}
            intervals = [(right["cpu_seconds"] - left["cpu_seconds"]) / (right["wall_seconds"] - left["wall_seconds"]) * 100
                         for left, right in zip(samples, samples[1:]) if right["wall_seconds"] > left["wall_seconds"]]
            rolling = [(right["cpu_seconds"] - left["cpu_seconds"]) / (right["wall_seconds"] - left["wall_seconds"]) * 100
                       for left in samples for right in samples if 0.9 < right["wall_seconds"] - left["wall_seconds"] < 1.1]
            result.update({"peaks": peaks, "peak_sample_cpu_percent_one_core": max(intervals),
                "peak_about_one_second_cpu_percent_one_core": max(rolling),
                "average_cpu_percent_one_core": result["cpu_seconds"] / result["wall_seconds"] * 100,
                "transitions": transitions, "pdf_bytes_per_job": len(document), "pdf_pages_per_job": 6,
                "pdf_text_characters_per_job": 6 * len("Synthetic attached context. The stated value is seven. " * 1200),
                "image_bytes_per_job": len(image_bytes), "image_dimensions": [1536, 1024], "external_connections": 0,
                "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "working_tree_has_changes": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())})
            assert result["distinct_model_instances"] == result["model_instances"] == 10
            assert result["final_states"] == {"completed": 10}
            (folder / "result.json").write_text(json.dumps(result, indent=2))
            print(json.dumps({key: result[key] for key in ("peaks", "peak_sample_cpu_percent_one_core",
                "peak_about_one_second_cpu_percent_one_core", "average_cpu_percent_one_core", "cpu_seconds",
                "wall_seconds", "final_states", "database_bytes")}, indent=2))
        finally:
            (folder / "stop").touch()
            if process.poll() is None:
                for ready in folder.glob("*.ready"):
                    ready.with_suffix(".release").touch()
                try:
                    process.wait(15)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    folder = args.output.resolve()
    if folder.is_relative_to(ROOT):
        parser.error("Use a new disposable output directory outside the repository")
    child(folder) if args.child else run_probe(folder)
