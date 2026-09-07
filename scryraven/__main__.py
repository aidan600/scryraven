"""Ordinary CLI. Answers on stdout; optional compact JSON observations on stderr."""

from __future__ import annotations

import argparse
import json
import sys

from scryraven.research import RunError, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research a public-web factual question with acquired sources.")
    parser.add_argument("question")
    parser.add_argument("--trace", action="store_true", help="Write safe structured diagnostics to stderr.")
    args = parser.parse_args(argv)
    try:
        result = run(args.question)
    except RunError as exc:
        if args.trace:
            print(json.dumps({"trace": exc.trace}, ensure_ascii=True), file=sys.stderr)
        print(f"ScryRaven failed at {exc.stage}: {exc.code}", file=sys.stderr)
        return 1
    if args.trace:
        print(json.dumps({"trace": result.trace}, ensure_ascii=True), file=sys.stderr)
    print(result.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
