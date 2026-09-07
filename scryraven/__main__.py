"""Ordinary CLI. Answers on stdout; optional compact JSON observations on stderr."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from scryraven.research import RunError, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research a public-web factual question with acquired sources.")
    parser.add_argument("question")
    parser.add_argument("--trace", action="store_true", help="Write safe structured diagnostics to stderr.")
    parser.add_argument(
        "--trace-evidence", action="store_true",
        help="Also include selected acquired source text in stderr diagnostics for support inspection.",
    )
    args = parser.parse_args(argv)
    try:
        result = run(args.question)
    except RunError as exc:
        if args.trace or args.trace_evidence:
            print(json.dumps({"trace": exc.trace}, ensure_ascii=True), file=sys.stderr)
        print(f"ScryRaven failed at {exc.stage}: {exc.code}", file=sys.stderr)
        return 1
    if args.trace or args.trace_evidence:
        diagnostics = {"trace": result.trace}
        if args.trace_evidence:
            diagnostics["selected_evidence"] = [
                asdict(item) for item in result.evidence if item.id in result.analysis.support_refs
            ]
        print(json.dumps(diagnostics, ensure_ascii=True), file=sys.stderr)
    print(result.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
