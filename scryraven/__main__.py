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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research a public-web factual question with acquired sources.")
    parser.add_argument("question")
    parser.add_argument("--session", action="store_true", help="Ask follow-ups in this process; blank input finishes.")
    parser.add_argument("--html", type=Path, metavar="PATH", help="Save a local answer view with inspectable sources.")
    parser.add_argument("--trace", action="store_true", help="Write safe structured diagnostics to stderr.")
    parser.add_argument(
        "--trace-evidence", action="store_true",
        help="Also include selected acquired source text in stderr diagnostics for support inspection.",
    )
    args = parser.parse_args(argv)
    if args.session and args.html:
        parser.error("--html supports a single answer; omit it when using --session.")
    ask = ResearchSession().ask if args.session else run
    question = args.question
    while True:
        try:
            result = ask(question)
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
        if not args.session:
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
