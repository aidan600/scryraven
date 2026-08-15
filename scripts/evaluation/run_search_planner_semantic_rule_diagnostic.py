"""Closed CLI entrypoint for the six-call SearchPlanner diagnostic."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluation.search_planner_semantic_rule_diagnostic import (
    SearchPlannerSemanticRuleDiagnosticError,
    current_repository_sha,
    execute_search_planner_semantic_rule_diagnostic,
    load_case_inputs,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the separately authorized six-call Planner diagnostic.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required acknowledgement before any brokered model attempt.",
    )
    parser.add_argument("--repository-sha", required=True)
    parser.add_argument("--cases-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--current-date")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.execute:
        raise SearchPlannerSemanticRuleDiagnosticError("execute_acknowledgement_required")
    if os.environ.get("SCRYRAVEN_SEARCH_PLANNER_DIAGNOSTIC_BROKER_SESSION") != "1":
        raise SearchPlannerSemanticRuleDiagnosticError("approved_broker_session_required")
    actual_sha = current_repository_sha(repository_root=ROOT)
    if args.repository_sha != actual_sha:
        raise SearchPlannerSemanticRuleDiagnosticError("repository_sha_differs_from_current_head")
    cases = load_case_inputs(Path(args.cases_file), repository_root=ROOT)
    packet = execute_search_planner_semantic_rule_diagnostic(
        case_inputs=cases,
        repository_sha=actual_sha,
        current_date=args.current_date,
        output_path=Path(args.output),
        repository_root=ROOT,
    )
    print(
        f"search-planner semantic-rule diagnostic completed: {len(packet['call_results'])} retained call observations"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SearchPlannerSemanticRuleDiagnosticError:
        print("search-planner semantic-rule diagnostic failed closed", file=sys.stderr)
        raise SystemExit(2) from None


__all__ = ["main"]
