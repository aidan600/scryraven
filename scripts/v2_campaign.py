"""Development-only campaign caller; public JSON lines go through the doorman.

This invokes the ordinary session API. It never wraps provider requests, supplies
research decisions, or passes evaluation rubrics into the product runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

REPOSITORY = Path(__file__).resolve().parents[1]
MANIFEST = REPOSITORY / "docs" / "operator" / "V2_CAMPAIGN.md"
START = "<!-- v2-campaign-manifest:start -->"
END = "<!-- v2-campaign-manifest:end -->"
TOKEN_FIELDS = (
    "input_tokens", "cached_input_tokens", "cache_write_tokens",
    "output_tokens", "reasoning_tokens",
)


def load_manifest(path: Path = MANIFEST) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    block = text.split(START, 1)[1].split(END, 1)[0].strip()
    if not block.startswith("```json\n") or not block.endswith("```"):
        raise ValueError("invalid_campaign_manifest")
    manifest = json.loads(block[len("```json\n"):-3])
    frozen = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return manifest, hashlib.sha256(frozen.encode("utf-8")).hexdigest()


def _emit(kind: str, **data) -> None:
    print(json.dumps({"kind": kind, **data}, ensure_ascii=True), flush=True)


def _runtime() -> SimpleNamespace:
    # A script launched by absolute path still imports the exact approved checkout.
    if str(REPOSITORY) not in sys.path:
        sys.path.insert(0, str(REPOSITORY))
    from scryraven import research
    from scryraven.model import ModelConfig, ModelRole, OpenAIModel
    from scryraven.research import RunError
    from scryraven.session import ResearchSession
    from scryraven.session_store import SessionStoreError, SQLiteSessionStore

    return SimpleNamespace(
        limits=research.RunLimits,
        model=OpenAIModel, config=ModelConfig, role=ModelRole,
        session=ResearchSession, store=SQLiteSessionStore,
        run_error=RunError, store_error=SessionStoreError,
    )


def _usage_row(usage) -> dict:
    # Cache keys/families and provider objects deliberately remain outside capture.
    return {
        "stage": usage.stage, "phase": usage.phase, "model": usage.model,
        **{name: getattr(usage, name) for name in TOKEN_FIELDS},
    }


def _usage_summary(rows: list[dict]) -> dict:
    return {
        "semantic_attempts_observed": len(rows),
        **{
            name: sum(row[name] for row in rows)
            if rows and all(row[name] is not None for row in rows) else None
            for name in TOKEN_FIELDS
        },
    }


def _code_hashes() -> dict[str, str]:
    paths = [
        "scripts/v2_campaign.py", "scryraven/research.py", "scryraven/model.py",
        "scryraven/__main__.py", "scryraven/errors.py", "scryraven/historical.py",
        "scryraven/session.py", "scryraven/session_store.py",
        "scryraven/sources.py", "scryraven/results.py", "scryraven/acquisition.py", "core/exa_transport.py",
    ]
    return {
        name: hashlib.sha256((REPOSITORY / name).read_bytes()).hexdigest()
        for name in paths if (REPOSITORY / name).is_file()
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", required=True, dest="cases",
                        help="Frozen case ID. Repeat F01 then F02 for one retained session.")
    parser.add_argument("--manifest", type=Path,
                        help="Absolute external frozen campaign manifest; defaults to V2_CAMPAIGN.md.")
    parser.add_argument("--revision", required=True, help="Tested Git revision; source hashes are also recorded.")
    parser.add_argument("--semantic-attempts", type=int, default=12)
    parser.add_argument("--external-attempts", type=int, default=16)
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--database", type=Path, help="Explicit external durable-session database.")
    parser.add_argument("--resume", help="Resume a session whose last completed question is frozen F01.")
    return parser


def _selected_cases(parser: argparse.ArgumentParser, args, manifest: dict) -> list[dict]:
    cases = {case["id"]: case for case in manifest["cases"]}
    if any(case_id not in cases for case_id in args.cases):
        parser.error("--case must name an ID in the frozen campaign manifest.")
    if not 2 <= args.semantic_attempts <= 20:
        parser.error("--semantic-attempts must be between 2 and the authorized maximum 20.")
    if not 0 <= args.external_attempts <= 24:
        parser.error("--external-attempts must be between 0 and the authorized maximum 24.")
    if not 0 < args.seconds <= 300:
        parser.error("--seconds must be positive and at most the authorized maximum 300.")
    if args.database is not None:
        if not args.database.is_absolute() or args.database.resolve().is_relative_to(REPOSITORY):
            parser.error("--database must be an absolute path outside the repository.")
        if not args.database.parent.is_dir():
            parser.error("--database must have an existing parent directory.")
    if args.resume and (args.database is None or args.cases != ["F02"]):
        parser.error("--resume requires --database and exactly --case F02.")
    selected = [cases[case_id] for case_id in args.cases]
    for index, case in enumerate(selected):
        if case["follows"] and not args.resume:
            if not index or selected[index - 1]["id"] != case["follows"]:
                parser.error("F02 must immediately follow F01 in this invocation or use --resume.")
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    manifest_path = args.manifest or MANIFEST
    if args.manifest is not None:
        if not manifest_path.is_absolute() or manifest_path.resolve().is_relative_to(REPOSITORY):
            parser.error("--manifest must be an absolute path outside the repository.")
    try:
        manifest, manifest_hash = load_manifest(manifest_path)
    except (OSError, ValueError):
        parser.error("--manifest must contain a valid frozen campaign manifest.")
    selected = _selected_cases(parser, args, manifest)
    runtime = _runtime()
    usage_rows: list[dict] = []
    active_case_id: str | None = None

    def observe(event: dict) -> None:
        # The engine owns its safe normalized event contract; do not inspect I/O.
        _emit("observation", case_id=active_case_id, event=event)

    def record_usage(usage) -> None:
        usage_rows.append(_usage_row(usage))

    role = runtime.role("gpt-5.6-luna", "medium")
    limits = runtime.limits(
        semantic_attempts=args.semantic_attempts,
        external_attempts=args.external_attempts,
        seconds=args.seconds,
        attention_characters=128_000,
    )
    model = runtime.model(runtime.config(research=role, answer=role), usage_observer=record_usage)
    options = {"observe": observe, "model": model, "limits": limits}
    _emit(
        "campaign_invocation", campaign_id=manifest["campaign_id"], manifest_sha256=manifest_hash,
        revision=args.revision, source_sha256=_code_hashes(), case_ids=args.cases,
        configuration={"model": role.model, "reasoning": role.reasoning, "limits": asdict(limits)},
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    session = None
    submissions_started = 0
    store = runtime.store(args.database) if args.database is not None else None
    if args.resume:
        try:
            session = runtime.session.open(args.resume, store=store, **options)
            seed_question = next(case["question"] for case in manifest["cases"] if case["id"] == "F01")
            if not session.turns or session.turns[-1].question != seed_question:
                _emit("campaign_failure", code="resume_requires_frozen_seed", submissions_started=0)
                return 1
        except runtime.store_error as exc:
            _emit("campaign_failure", code=exc.code, submissions_started=0)
            return 1

    for case in selected:
        active_case_id = case["id"]
        usage_rows.clear()
        started = monotonic()
        try:
            if case["follows"] is None:
                session = (runtime.session.create(store=store, **options) if store is not None
                           else runtime.session(**options))
            entering = session.acquisitions
            _emit(
                "submission_started", case_id=case["id"], question=case["question"],
                session_id=session.session_id, session_turn=len(session.turns) + 1,
                entering_acquisitions=[asdict(item) for item in entering],
            )
            submissions_started += 1
            result = session.ask(case["question"])
            _emit(
                "submission_completed", case_id=case["id"], question=case["question"],
                session_id=session.session_id, answer=result.answer, posture=result.posture,
                stop_reason=result.stop_reason,
                evidence=[asdict(item) for item in result.evidence],
                selected_evidence=[asdict(item) for item in result.selected_evidence],
                citations=[asdict(item) for item in result.citations],
                citation_uses=[asdict(item) for item in result.citation_uses],
                trace=result.trace, usage=usage_rows, counters=_usage_summary(usage_rows),
                elapsed_seconds=round(monotonic() - started, 3),
            )
        except runtime.run_error as exc:
            _emit(
                "submission_failed", case_id=case["id"], question=case["question"],
                stage=exc.stage, code=exc.code, trace=exc.trace,
                usage=usage_rows, counters=_usage_summary(usage_rows),
                elapsed_seconds=round(monotonic() - started, 3),
                submissions_started=submissions_started,
            )
            return 1
        except runtime.store_error as exc:
            _emit("campaign_failure", case_id=case["id"], code=exc.code,
                  submissions_started=submissions_started)
            return 1
        except Exception:
            # Never publish an arbitrary exception repr from a credentialed process.
            _emit("campaign_failure", case_id=case["id"], code="unexpected_runtime_failure",
                  usage=usage_rows, counters=_usage_summary(usage_rows),
                  submissions_started=submissions_started)
            return 1
    _emit("campaign_completed", submissions_started=submissions_started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
