"""Bounded live caller for Latency Consumption 01 through the Reading Room.

The fixed public questions enter the ordinary HTTP -> ResearchSession -> SQLite
path. The caller supplies only the approved model execution arm and, for Stage C,
the prior-cited initial exposure toggle. It never supplies sources, routes,
rubrics, or expected answers. Run it through the repository credential doorman.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from scryraven.model import ModelConfig, ModelRole, OpenAIModel  # noqa: E402
from scryraven.reading_room import create_app  # noqa: E402
from scryraven.session_store import SQLiteSessionStore  # noqa: E402

R1 = (
    "Assume a household needs 60 million Btu of useful heat per year, a gas furnace "
    "is 90% AFUE, gas costs $1.20 per therm, electricity costs $0.18 per kWh, and a "
    "heat pump has a seasonal COP of 2.5. Under only those assumptions, what is the "
    "annual operating energy cost for each system? Exclude capital costs and emissions."
)
R2A = (
    "According to the BIPM, which four SI prefixes were added in 2022, and what are "
    "their symbols and powers of ten?"
)
R2B = (
    "Which two of those represent factors smaller than one, and how do their "
    "magnitudes compare?"
)
R3 = (
    "Does Anker's published capacity for the Prime Power Bank (27K, 250W), by itself, "
    "establish that it falls under the FAA's 100 Wh no-airline-approval threshold?"
)
R4 = (
    "What takeoff-thrust range does GE publish for the base engine NASA and GE "
    "modified for their hybrid-electric engine demonstration?"
)
R5 = "What are the qualifications of the new executive director of St. Dorothy’s Rest?"
PARKRUN_SEED = (
    "Under the current parkrun rules, when may a child under 11 participate in a 5k "
    "parkrun or a junior parkrun without an adult staying within arm’s reach? Explain "
    "the age limits and any material exceptions."
)
PARKRUN_FOLLOWUP = (
    "So for a 10-year-old specifically, compare what the rule requires at a 5k parkrun "
    "versus a junior parkrun."
)
EUCLID_FOLLOWUP = (
    "According to the BIPM material already discussed, set that aside for now: what "
    "is the launch date of ESA's Euclid mission?"
)

STAGE_A_CASES = {
    "R1": (R1,),
    "R2": (R2A, R2B),
    "R3": (R3,),
    "R4": (R4,),
    "R5": (R5,),
}
STAGE_B_CASES = {"FST1": R1, "FST2": R4, "FST3": R5}
STAGE_C_SEEDS = {"BIPM": R2A, "PARKRUN": PARKRUN_SEED}
STAGE_C_FOLLOWUPS = {
    "BIPM": R2B,
    "PARKRUN": PARKRUN_FOLLOWUP,
    "EUCLID": EUCLID_FOLLOWUP,
}
STAGE_C_SOURCE = {"BIPM": "BIPM", "PARKRUN": "PARKRUN", "EUCLID": "BIPM"}
SOURCE_FILES = (
    "scripts/latency_consumption_01.py", "scryraven/model.py", "scryraven/research.py",
    "scryraven/acquisition.py", "scryraven/session.py", "scryraven/session_store.py",
    "scryraven/reading_room.py", "scryraven/dogfood_diagnostics.py",
    "scryraven/presentation.py",
)
SESSION_ID = re.compile(r"[0-9a-f]{32}\Z")
MATERIAL_ID = re.compile(r"E[1-9][0-9]*(?:@[0-9]+:[0-9]+)?\Z")
SAFE_CODES = re.compile(r"[a-z][a-z0-9_]{0,80}\Z")


def _emit(kind: str, **fields) -> None:
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=True,
                     separators=(",", ":"), allow_nan=False), flush=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hashes() -> dict[str, str]:
    return {name: _sha256(REPOSITORY / name) for name in SOURCE_FILES}


def _safe_refs(values) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and MATERIAL_ID.fullmatch(value)]


def _trajectory_event(event: dict) -> dict | None:
    """Keep only public decision/navigation fields; never serialize an event."""
    if not isinstance(event, dict):
        return None
    action = event.get("action")
    if action == "model_started":
        exposed = event.get("exposed")
        return {
            "action": action,
            "contract": event.get("contract") if event.get("contract") in {"research", "answer"} else None,
            "attempt": event.get("attempt") if type(event.get("attempt")) is int else None,
            "exposed_ids": _safe_refs([item.get("id") for item in exposed if isinstance(item, dict)])
            if isinstance(exposed, list) else [],
        }
    if action == "research_decision":
        decision = event.get("decision")
        if not isinstance(decision, dict):
            return None
        requests = decision.get("requests")
        return {
            "action": action,
            "decision_action": decision.get("action") if decision.get("action") in {"research", "answer"} else None,
            "requests": [{
                "kind": item.get("kind"), "query": item.get("query"),
                "target": item.get("target"), "focus": item.get("focus"),
                "mode": item.get("mode"), "scope": _safe_refs(item.get("scope")),
                "start_char": item.get("start_char"), "end_char": item.get("end_char"),
            } for item in requests if isinstance(item, dict)] if isinstance(requests, list) else [],
            "retain": _safe_refs(decision.get("retain")),
            "answer_evidence_refs": _safe_refs(decision.get("answer_evidence_refs")),
        }
    if action == "acquisition_result":
        result = event.get("result")
        if not isinstance(result, dict):
            return None
        code = result.get("code")
        return {
            "action": action,
            "request_kind": result.get("kind") if result.get("kind") in {
                "search", "search_lexical", "read", "find",
            } else None,
            "status": result.get("status") if result.get("status") in {"ok", "error"} else None,
            "code": code if isinstance(code, str) and SAFE_CODES.fullmatch(code) else None,
            "material_ids": _safe_refs(result.get("material_ids")),
            "new_acquisition_ids": _safe_refs(result.get("new_acquisition_ids")),
        }
    if action == "answer_decision":
        decision = event.get("decision")
        if not isinstance(decision, dict):
            return None
        return {
            "action": action,
            "posture": decision.get("posture") if decision.get("posture") in {
                "supported", "partial", "unable",
            } else None,
            "support_basis": decision.get("support_basis") if decision.get("support_basis") in {
                "evidence", "user_premises", "none",
            } else None,
            "has_missing_information": bool(decision.get("missing_information")),
            "source_reading_refs": _safe_refs(event.get("source_reading_refs")),
        }
    return None


class _AskForm(HTMLParser):
    def __init__(self, action: str):
        super().__init__()
        self.action = action
        self.active = False
        self.token: str | None = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form":
            self.active = attributes.get("action") == self.action
        elif self.active and tag == "input" and attributes.get("name") == "form_token":
            self.token = attributes.get("value")

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False


def _model(effort: str, tier: str) -> OpenAIModel:
    # Explicit Standard prevents project-level auto processing from confounding
    # Research and keeps the Answer control on Sol/medium/Standard in every arm.
    return OpenAIModel(ModelConfig(
        fast=ModelRole("gpt-6-luna", effort, tier),
        smart=ModelRole("gpt-6-sol", "medium", "default"),
    ))


def _submit(client, question: str, session_id: str | None) -> tuple[int, str | None]:
    page_path = f"/sessions/{session_id}" if session_id else "/"
    action = f"/sessions/{session_id}/ask" if session_id else "/ask"
    page = client.get(page_path)
    if page.status_code != 200:
        return page.status_code, None
    form = _AskForm(action)
    form.feed(page.get_data(as_text=True))
    if not form.token:
        return 0, None
    response = client.post(action, data={"form_token": form.token, "question": question})
    if response.status_code != 303:
        return response.status_code, None
    parts = urlsplit(response.location)
    match = re.fullmatch(r"/sessions/([0-9a-f]{32})", parts.path)
    return response.status_code, match.group(1) if match else None


def _turn_public(store: SQLiteSessionStore, session_id: str) -> dict:
    saved = store.load(session_id)
    turn = saved.state.turns[-1]
    return {
        "session_id": session_id,
        "revision_after": saved.metadata.revision,
        "answer": turn.answer,
        "posture": turn.posture,
        "stop_reason": turn.stop_reason,
        "citations": [{
            "number": item.number, "source_id": item.source_id,
            "title": item.title, "url": item.url,
            "material_ids": [material.id for material in item.materials],
        } for item in turn.citations],
        "selected_evidence": [{
            "id": item.id, "source_id": item.source_id,
            "content_characters": len(item.content),
            "content_sha256": hashlib.sha256(item.content.encode("utf-8")).hexdigest(),
        } for item in turn.selected_evidence],
        "retained_acquisitions": len(saved.state.acquisitions),
    }


def _append_trajectory(path: Path, case_id: str, session_id: str | None,
                       turn_number: int, events: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as target:
        target.write(json.dumps({
            "case_id": case_id, "session_id": session_id,
            "attempted_turn": turn_number, "events": events,
        }, ensure_ascii=True, separators=(",", ":")) + "\n")


def _run_questions(*, root: Path, directory: str, database_name: str,
                   cases: list[tuple[str, str]], effort: str, tier: str,
                   preexposed: bool = False, existing_session_id: str | None = None) -> bool:
    arm_dir = root / directory
    arm_dir.mkdir(parents=True, exist_ok=True)
    database = arm_dir / database_name
    dogfood = arm_dir / "turns.jsonl"
    trajectory = arm_dir / "trajectory.jsonl"
    if existing_session_id is None and database.exists():
        _emit("campaign_failure", code="database_already_exists", directory=directory,
              database_name=database_name)
        return False
    store = SQLiteSessionStore(database)
    captured: list[dict] = []

    def observe(event: dict) -> None:
        projected = _trajectory_event(event)
        if projected is not None:
            captured.append(projected)

    options = {"model": _model(effort, tier), "observe": observe}
    if preexposed:
        options["preexpose_prior_cited"] = True
    app = create_app(store=store, session_options=options, dogfood_log=dogfood)
    client = app.test_client()
    session_id = existing_session_id
    for index, (case_id, question) in enumerate(cases, 1):
        captured.clear()
        attempted_turn = (store.load(session_id).metadata.revision + 1) if session_id else 1
        _emit("submission_started", case_id=case_id, directory=directory,
              session_id=session_id, attempted_turn=attempted_turn,
              research_effort=effort, research_service_tier=tier)
        started = monotonic()
        status, returned_session_id = _submit(client, question, session_id)
        elapsed = round(monotonic() - started, 6)
        _append_trajectory(trajectory, case_id, returned_session_id or session_id,
                           attempted_turn, captured)
        if status != 303 or returned_session_id is None:
            _emit("submission_failed", case_id=case_id, directory=directory,
                  http_status=status, session_id=session_id,
                  attempted_turn=attempted_turn, elapsed_seconds=elapsed,
                  database=str(database), dogfood_log=str(dogfood),
                  trajectory_log=str(trajectory))
            return False
        if session_id is not None and session_id != returned_session_id:
            _emit("campaign_failure", code="session_identity_changed", case_id=case_id)
            return False
        session_id = returned_session_id
        result = _turn_public(store, session_id)
        if result["revision_after"] != attempted_turn:
            _emit("campaign_failure", code="unexpected_session_revision", case_id=case_id)
            return False
        _emit("submission_completed", case_id=case_id, directory=directory,
              elapsed_seconds=elapsed, database=str(database),
              dogfood_log=str(dogfood), trajectory_log=str(trajectory), **result)
    return True


def _seed_file(root: Path, source: str) -> Path:
    return root / "stage-c-seed" / f"{source.lower()}.sqlite3"


def _copy_seed(root: Path, case_id: str, directory: str) -> tuple[Path, str] | None:
    source_id = STAGE_C_SOURCE[case_id]
    source = _seed_file(root, source_id)
    if not source.is_file():
        _emit("campaign_failure", code="seed_database_missing", case_id=case_id)
        return None
    # The store uses short, closed connections and no WAL policy. A sidecar means
    # the byte-for-byte source snapshot is not safe to copy as a single file.
    if any(Path(str(source) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        _emit("campaign_failure", code="seed_database_has_sidecar", case_id=case_id)
        return None
    seed_store = SQLiteSessionStore(source)
    sessions = seed_store.list_sessions()
    if len(sessions) != 1 or sessions[0].revision != 1:
        _emit("campaign_failure", code="seed_session_shape_invalid", case_id=case_id)
        return None
    session_id = sessions[0].session_id
    seed = seed_store.load(session_id)
    if len(seed.state.turns) != 1 or seed.state.turns[0].question != STAGE_C_SEEDS[source_id]:
        _emit("campaign_failure", code="seed_question_invalid", case_id=case_id)
        return None
    target_dir = root / directory
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{case_id.lower()}.sqlite3"
    if target.exists():
        _emit("campaign_failure", code="campaign_database_already_exists", case_id=case_id)
        return None
    shutil.copyfile(source, target)
    source_hash, target_hash = _sha256(source), _sha256(target)
    if source_hash != target_hash:
        _emit("campaign_failure", code="seed_copy_mismatch", case_id=case_id)
        return None
    _emit("seed_copied", case_id=case_id, directory=directory,
          seed_sha256=source_hash, copy_sha256=target_hash,
          seed_database=str(source), campaign_database=str(target), session_id=session_id)
    return target, session_id


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=("a", "b", "c"))
    parser.add_argument("--arm", required=True)
    parser.add_argument("--case", action="append", dest="cases", help="Case or case group; repeat to select a subset.")
    parser.add_argument("--root", type=Path, required=True,
                        help="Absolute isolated artifact directory outside the repository.")
    parser.add_argument("--revision", required=True, help="Git revision being tested.")
    parser.add_argument("--effort", choices=("high", "medium"),
                        help="Stage A winner, required for Stages B and C.")
    parser.add_argument("--tier", choices=("default", "fast"),
                        help="Stage B winner, required for Stage C.")
    return parser


def _selected(parser, args, choices):
    cases = args.cases or list(choices)
    if len(cases) != len(set(cases)) or any(case not in choices for case in cases):
        parser.error("--case must name distinct cases in the selected stage.")
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.root.is_absolute() or args.root.resolve().is_relative_to(REPOSITORY):
        parser.error("--root must be an absolute path outside the repository.")
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("--revision must be a full 40-character Git SHA.")
    if args.stage == "a":
        if args.arm not in {"high", "medium"} or args.effort or args.tier:
            parser.error("Stage A requires --arm high|medium and no --effort or --tier.")
        cases = _selected(parser, args, STAGE_A_CASES)
    elif args.stage == "b":
        if args.arm not in {"pair", "standard", "fast"} or args.effort is None or args.tier:
            parser.error("Stage B requires --arm pair|standard|fast and --effort.")
        cases = _selected(parser, args, STAGE_B_CASES)
    else:
        if args.arm not in {"seed", "control", "preexposed"} or args.effort is None or args.tier is None:
            parser.error("Stage C requires --arm seed|control|preexposed, --effort and --tier.")
        cases = _selected(parser, args, STAGE_C_SEEDS if args.arm == "seed" else STAGE_C_FOLLOWUPS)
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    _emit("campaign_invocation", stage=args.stage, arm=args.arm, case_ids=cases,
          revision=args.revision, source_sha256=_source_hashes(),
          root=str(root), research_effort=args.arm if args.stage == "a" else args.effort,
          research_service_tier="default" if args.stage == "a" else args.tier,
          answer_model="gpt-6-sol", answer_effort="medium", answer_service_tier="default",
          started_at=datetime.now(timezone.utc).isoformat())
    try:
        if args.stage == "a":
            for case_id in cases:
                questions = [(case_id if len(STAGE_A_CASES[case_id]) == 1 else f"{case_id}{suffix}", question)
                             for suffix, question in zip(("a", "b"), STAGE_A_CASES[case_id])]
                if not _run_questions(root=root, directory=f"stage-a-{args.arm}",
                                      database_name=f"{case_id.lower()}.sqlite3",
                                      cases=questions, effort=args.arm, tier="default"):
                    return 1
        elif args.stage == "b":
            arms = ("standard", "fast") if args.arm == "pair" else (args.arm,)
            for case_id in cases:
                for arm in arms:
                    if not _run_questions(root=root, directory=f"stage-b-{arm}",
                                          database_name=f"{case_id.lower()}.sqlite3",
                                          cases=[(case_id, STAGE_B_CASES[case_id])],
                                          effort=args.effort,
                                          tier="default" if arm == "standard" else "fast"):
                        return 1
        elif args.arm == "seed":
            for case_id in cases:
                if not _run_questions(root=root, directory="stage-c-seed",
                                      database_name=f"{case_id.lower()}.sqlite3",
                                      cases=[(f"{case_id}-seed", STAGE_C_SEEDS[case_id])],
                                      effort=args.effort, tier=args.tier):
                    return 1
        else:
            directory = f"stage-c-{args.arm}"
            for case_id in cases:
                copied = _copy_seed(root, case_id, directory)
                if copied is None:
                    return 1
                _, session_id = copied
                if not _run_questions(root=root, directory=directory,
                                      database_name=f"{case_id.lower()}.sqlite3",
                                      cases=[(case_id, STAGE_C_FOLLOWUPS[case_id])],
                                      effort=args.effort, tier=args.tier,
                                      preexposed=args.arm == "preexposed",
                                      existing_session_id=session_id):
                    return 1
    except (OSError, ValueError, RuntimeError):
        # Brokered output must never carry exception messages or private paths.
        _emit("campaign_failure", code="caller_operational_failure")
        return 1
    _emit("campaign_completed", stage=args.stage, arm=args.arm, case_ids=cases,
          submissions_started=sum(len(STAGE_A_CASES[case]) for case in cases) if args.stage == "a"
          else len(cases) * (2 if args.stage == "b" and args.arm == "pair" else 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
