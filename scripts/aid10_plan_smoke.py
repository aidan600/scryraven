"""One control/hardened AID-10 development pair on the existing local personal plan."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

# A fresh interpreter uses -I. Resolve this checkout explicitly, even when the
# interpreter and its installed packages belong to the ordinary user's venv.
ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))

import requests

from core.exa_transport import DiscoveryCandidate
from core.transport import FetchedMaterial
from scripts.aid10_luna import ARMS, clean_revision, prompts
from scryraven import research
from scryraven.acquisition import AcquisitionError
from scryraven.chatgpt_plan.auth import Auth
from scryraven.chatgpt_plan.http import JWKS, RESPONSES, TOKEN, PlanError, PublicHTTP
from scryraven.errors import RunError
from scryraven.model import ModelError, OpenAIModel
from scryraven.run_settings import RunSettings
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore

BRANCH = "codex/aid-10-luna-harness-reliability"
FIXTURE = ROOT / "scripts" / "fixtures" / "aid10_plan_smoke.json"
SETTINGS = RunSettings("chatgpt_plan", "gpt-6-luna", "high", "gpt-6.2-sol", "medium", None,
                       physical_request_limit=6, external_attempt_limit=5, seconds_limit=90)
PROCESS_SECONDS = 100
PLAN_ROUTES = {
    ("POST", RESPONSES): ("plan_responses", SETTINGS.physical_request_limit),
    ("POST", TOKEN): ("plan_refresh", 1),
    ("GET", JWKS): ("plan_jwks", 1),
}
CHILD_ENV = ("SystemRoot", "WINDIR", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "TEMP", "TMP",
             "HOMEDRIVE", "HOMEPATH")


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class FrozenProviders:
    """Case-only Search leads and exact-URL Read excerpts, with no I/O."""

    def __init__(self, sources: list[dict]):
        self.sources = sources

    def search(self, query: str) -> list[DiscoveryCandidate]:
        terms = set(re.findall(r"[a-z0-9]+", query.casefold()))
        years = {term for term in terms if re.fullmatch(r"(?:19|20)[0-9]{2}", term)}
        if "passport" not in terms or years - {"2024"}:
            raise AcquisitionError("fixture_search_outside_case")
        kinds = set()
        if terms & {"honda", "suv"}:
            kinds.add("honda")
        if terms & {"ge", "aerospace", "bombardier", "aircraft", "turbofan"}:
            kinds.add("ge")
        if not kinds and not terms & {"engine", "engines"}:
            raise AcquisitionError("fixture_search_outside_case")
        return [DiscoveryCandidate(row["title"], row["url"], "")
                for row in self.sources if not kinds or row["kind"] in kinds]

    def read(self, url: str) -> FetchedMaterial:
        for row in self.sources:
            if row["url"] == url:
                return FetchedMaterial(url, row["text"])
        raise AcquisitionError("fixture_read_unknown_url")

    @staticmethod
    def deny(*_args, **_kwargs):
        raise AcquisitionError("fixture_provider_disabled")

    def session_options(self) -> dict:
        return {"search": self.search, "lexical_search": self.search, "fetch": self.read,
                "scholarly_search": self.deny, "scholarly_fetch": self.deny, "venue_lookup": self.deny}


def append_json(path: Path, value) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=True) + "\n")


@contextmanager
def plan_only_http(http: PublicHTTP, record):
    """Only the personal-plan adapter's own session can perform capped HTTP."""
    original_send = requests.Session.send
    counts = Counter()

    def send(session, request, **kwargs):
        route = PLAN_ROUTES.get((request.method, request.url))
        if session is not http.session or route is None or kwargs.get("allow_redirects") is not False:
            record({"status": "blocked", "reason": "network_route_denied"})
            raise PlanError("model_request_rejected", reason="pilot_network_route_denied")
        name, ceiling = route
        if counts[name] >= ceiling:
            record({"status": "blocked", "route": name, "reason": "request_limit"})
            raise PlanError("model_request_rejected", reason="pilot_request_limit")
        counts[name] += 1
        record({"status": "dispatch_started", "route": name, "number": counts[name]})
        return original_send(session, request, **kwargs)

    with patch.object(requests.Session, "send", send):
        yield


def model_receipt(usage) -> dict:
    return {name: getattr(usage, name) for name in (
        "stage", "model", "returned_model", "returned_service_tier", "input_tokens",
        "cached_input_tokens", "output_tokens", "reasoning_tokens",
    )}


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    # A terminated child can leave an incomplete last line.
    complete, _, _ = path.read_text(encoding="utf-8").rpartition("\n")
    return [json.loads(line) for line in complete.splitlines()]


def run_arm(arm: str, directory: Path, *, auth_factory=Auth) -> None:
    fixture = load_fixture()
    providers = FrozenProviders(fixture["sources"])
    route_log = directory / "dispatch.jsonl"
    events = directory / "events.jsonl"
    receipts = directory / "receipts.jsonl"
    selected_prompts = prompts("diagnostic-development", arm)
    append_json(events, {"action": "arm_started", "case_id": fixture["case_id"],
                         "settings": SETTINGS.to_dict(),
                         "prompt_hashes": {key: sha256(value.encode()).hexdigest()
                                           for key, value in selected_prompts.items()}})
    outcome, failure = None, None

    def record_route(value):
        append_json(route_log, value)

    def deny_api(*_args, **_kwargs):
        record_route({"status": "blocked", "reason": "api_fallback_denied"})
        raise ModelError("model_request_rejected")

    try:
        with requests.Session() as transport_session:
            http = PublicHTTP(transport_session)
            with plan_only_http(http, record_route), patch.multiple(research, **selected_prompts):
                model = OpenAIModel(
                    SETTINGS.model_config(), backend="chatgpt_plan", plan_account="personal",
                    plan_auth=auth_factory(http=http), post=deny_api, timeout_seconds=45,
                    usage_observer=lambda usage: append_json(receipts, model_receipt(usage)),
                )
                session = ResearchSession.create(
                    store=SQLiteSessionStore(directory / "session.sqlite3"),
                    model=model, limits=SETTINGS.limits(), observe=lambda event: append_json(events, event),
                    **providers.session_options(),
                )
                answer = session.ask(fixture["question"])
                outcome = {"answer": answer.answer, "posture": answer.posture, "stop_reason": answer.stop_reason,
                           "citations": [asdict(citation) for citation in answer.citations],
                           "citation_uses": [asdict(use) for use in answer.citation_uses]}
    except RunError as exc:
        failure = {"stage": exc.stage, "code": exc.code}
    except PlanError as exc:
        failure = {"stage": "plan", "code": str(exc)}
    except Exception:
        failure = {"stage": "runtime", "code": "pilot_worker_failed"}
    append_json(directory / "outcome.jsonl", {"outcome": outcome, "failure": failure})


def summary(arm: str, directory: Path, worker_status: str) -> dict:
    receipts = read_rows(directory / "receipts.jsonl")
    dispatches = read_rows(directory / "dispatch.jsonl")
    turn = next(iter(read_rows(directory / "outcome.jsonl")), {})
    outcome = turn.get("outcome")
    roles = {"research": SETTINGS.research_model, "answer": SETTINGS.answer_model}
    responses = sum(row.get("route") == "plan_responses" and row["status"] == "dispatch_started"
                    for row in dispatches)
    exact = (responses == len(receipts) and {row["stage"] for row in receipts} == roles.keys()
             and all(row["model"] == row["returned_model"] == roles[row["stage"]] for row in receipts))
    visible_receipts = [{"stage": row["stage"], "requested_model": row["model"],
                         "returned_model": row["returned_model"],
                         "returned_tier": row["returned_service_tier"]}
                        for row in receipts]
    blocked = [row["reason"] for row in dispatches if row["status"] == "blocked"]
    return {"arm": arm, "worker_status": worker_status, "processing": "plan-default",
            "acquisition": "frozen_fixture",
            "responses_dispatched": responses, "receipts": visible_receipts, "exact_models_observed": exact,
            "posture": outcome["posture"] if outcome else None,
            "stop_reason": outcome["stop_reason"] if outcome else None,
            "citation_count": len(outcome["citations"]) if outcome else 0,
            "failure": turn.get("failure"), "blocked_transport": blocked}


def run_pair(directory: Path) -> int:
    env = {name: os.environ[name] for name in CHILD_ENV if name in os.environ}
    complete = True
    for arm in ARMS:
        arm_dir = directory / arm
        arm_dir.mkdir()
        argv = [sys.executable, "-I", str(Path(__file__).resolve()), "--run-personal-plan-smoke",
                "--worker", arm, str(arm_dir)]
        try:
            process = subprocess.run(argv, cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, timeout=PROCESS_SECONDS, check=False)
            status = "finished" if process.returncode == 0 else "worker_failed"
        except subprocess.TimeoutExpired:
            status = "worker_timeout"
        except OSError:
            status = "worker_launch_failed"
        receipt = summary(arm, arm_dir, status)
        append_json(directory / "summary.jsonl", receipt)
        print(json.dumps(receipt), flush=True)
        complete &= status == "finished" and receipt["posture"] is not None and receipt["exact_models_observed"]
        if set(receipt["blocked_transport"]) & {"network_route_denied", "api_fallback_denied"}:
            return 1
    return 0 if complete else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-personal-plan-smoke", action="store_true")
    parser.add_argument("--worker", nargs=2, metavar=("ARM", "DIRECTORY"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.run_personal_plan_smoke or sys.platform != "win32":
        parser.error("requires explicit --run-personal-plan-smoke on the signed-in Windows desktop")
    if args.worker:
        arm, destination = args.worker
        directory = Path(destination)
        if arm not in ARMS or not directory.is_dir() or any(directory.iterdir()):
            parser.error("worker requires its own new run directory and a known arm")
        run_arm(arm, directory)
        return 0

    try:
        revision = clean_revision()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
        if branch != BRANCH:
            raise ValueError
        fixture = load_fixture()
        output_root = Path(os.environ["LOCALAPPDATA"]) / "ScryRaven-aid10-plan-smokes"
        output_root.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="d07-", dir=output_root))
        metadata = {"case_id": fixture["case_id"], "revision": revision, "processing": "plan-default",
                    "acquisition": "frozen_fixture",
                    "source_sha256": sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest(),
                    "run_directory": str(directory)}
        append_json(directory / "run.jsonl", metadata)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError):
        parser.error("use the clean AID-10 branch and a writable LOCALAPPDATA directory")
    print(json.dumps(metadata), flush=True)
    return run_pair(directory)


if __name__ == "__main__":
    raise SystemExit(main())
