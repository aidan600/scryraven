"""Ordinary CLI. Answers on stdout; optional compact JSON observations on stderr."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from scryraven.presentation import render_cli, render_html
from scryraven.research import Result, RunError, run
from scryraven.session import ResearchSession
from scryraven.session_store import SessionStoreError, SQLiteSessionStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research a public-web factual question with acquired sources.")
    parser.add_argument("question", nargs="?")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--session", action="store_true", help="Ask follow-ups in this process; blank input finishes.")
    modes.add_argument("--create-session", action="store_true", help="Start and save a local research session.")
    modes.add_argument("--resume", metavar="ID", help="Open a saved session; omit question to read its transcript.")
    modes.add_argument("--list-sessions", action="store_true", help="List saved session IDs and labels.")
    parser.add_argument("--database", type=Path, metavar="PATH", help="Use an explicit session database path.")
    parser.add_argument("--html", type=Path, metavar="PATH", help="Save a local answer view with inspectable sources.")
    parser.add_argument("--trace", action="store_true", help="Write safe structured diagnostics to stderr.")
    parser.add_argument(
        "--trace-evidence", action="store_true",
        help="Also include selected acquired source text in stderr diagnostics for support inspection.",
    )
    args = parser.parse_args(argv)
    persistent = args.create_session or args.resume is not None or args.list_sessions
    interactive = args.session or args.create_session or args.resume is not None
    if (interactive or args.list_sessions) and args.html:
        parser.error("--html supports a single isolated answer; omit it when using session options.")
    if args.database and not persistent:
        parser.error("--database requires --create-session, --resume or --list-sessions.")
    if args.list_sessions and args.question is not None:
        parser.error("--list-sessions does not take a question.")
    if args.question is None and not (args.resume or args.list_sessions):
        parser.error("a question is required.")
    try:
        if persistent:
            store = SQLiteSessionStore(args.database)
            if args.list_sessions:
                for item in store.list_sessions():
                    print(f"{item.session_id}\t{item.updated_at}\t{item.revision} turns\t"
                          f"{' '.join(item.title.split()) or 'Untitled session'}")
                return 0
            session = (ResearchSession.open(args.resume, store=store) if args.resume
                       else ResearchSession.create(store=store))
            print(f"Session: {session.session_id}", file=sys.stderr)
            if args.question is None:
                for turn in session.turns:
                    print(f"Question: {turn.question}\n{render_cli(turn)}\n")
                return 0
            ask = session.ask
        else:
            ask = ResearchSession().ask if args.session else run
    except SessionStoreError as exc:
        print(f"ScryRaven session error: {exc.code}", file=sys.stderr)
        return 1
    question = args.question
    while True:
        try:
            result = ask(question)
        except SessionStoreError as exc:
            print(f"ScryRaven session error: {exc.code}", file=sys.stderr)
            return 1
        except RunError as exc:
            if args.trace or args.trace_evidence:
                print(json.dumps({"trace": exc.trace}, ensure_ascii=True), file=sys.stderr)
            print(f"ScryRaven failed at {exc.stage}: {exc.code}", file=sys.stderr)
            return 1
        _print_result(result, trace=args.trace, trace_evidence=args.trace_evidence)
        if args.html:
            try:
                args.html.write_text(render_html(question, result), encoding="utf-8")
            except OSError:
                print("ScryRaven could not write the local answer view; the answer is above.", file=sys.stderr)
                return 1
        if not interactive:
            return 0
        try:
            question = input("Follow-up (blank to finish): ")
        except (EOFError, KeyboardInterrupt):
            return 0
        if not question.strip():
            return 0


def _print_result(result: Result, *, trace: bool, trace_evidence: bool) -> None:
    if trace or trace_evidence:
        diagnostics = {"trace": result.trace}
        if trace_evidence:
            diagnostics["selected_evidence"] = [
                asdict(item) for item in result.selected_evidence
            ]
            diagnostics["citations"] = [
                {"number": item.number, "source_id": item.source_id, "title": item.title, "url": item.url,
                 "material_ids": [material.id for material in item.materials]}
                for item in result.citations
            ]
            diagnostics["citation_uses"] = [asdict(item) for item in result.citation_uses]
        print(json.dumps(diagnostics, ensure_ascii=True), file=sys.stderr)
    print(render_cli(result))


if __name__ == "__main__":
    raise SystemExit(main())
