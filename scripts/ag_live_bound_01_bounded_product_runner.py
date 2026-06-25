from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ag_live_bound_01_support import (  # noqa: E402
    DEFAULT_OUTPUT,
    AgLiveBoundPreflightError,
    build_dry_run_packet,
    build_fail_closed_live_packet,
    build_preflight_context,
    live_execution_blockers,
    parse_domains,
    resolve_output_path,
    validate_caps_requested,
    write_packet,
)

LIVE_SPEND_WARNING = (
    "AG-LIVE-BOUND-01 may spend live provider/model/search/fetch calls when enabled."
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    try:
        caps = validate_caps_requested(_caps_from_args(args))
        output_path = resolve_output_path(ROOT, args.output)
        context = build_preflight_context(
            root=ROOT,
            query=args.query,
            mode=args.mode,
            include_domains=parse_domains(args.include_domains),
            output_path=output_path,
            caps=caps,
            run_id=args.run_id,
            confirm_live_product_run=args.confirm_live_product_run,
            approved_backup_query=args.approved_backup_query,
        )
    except AgLiveBoundPreflightError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.confirm_live_product_run:
        return _fail_closed_live(context)

    packet = build_dry_run_packet(context)
    write_packet(context.output_path, packet)
    print(f"wrote sanitized AG-LIVE-BOUND dry-run packet to {context.output_path}")
    return 0


def _fail_closed_live(context) -> int:
    print(LIVE_SPEND_WARNING, file=sys.stderr)
    stop_reasons = live_execution_blockers()
    packet = build_fail_closed_live_packet(context, stop_reasons=stop_reasons)
    write_packet(context.output_path, packet)
    print(
        "refusing live product execution: "
        f"{packet['primary_stop_reason']}",
        file=sys.stderr,
    )
    return 2


def _caps_from_args(args: argparse.Namespace) -> dict[str, int]:
    return {
        "max_scryraven_runs": args.max_scryraven_runs,
        "max_search_dispatches": args.max_search_dispatches,
        "max_fetch_read_operations": args.max_fetch_read_operations,
        "max_author_model_calls": args.max_author_model_calls,
        "max_smart_search_judgment_model_calls": (
            args.max_smart_search_judgment_model_calls
        ),
        "max_independent_manual_source_checks": (
            args.max_independent_manual_source_checks
        ),
        "max_retries": args.max_retries,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run-first bounded ordinary product runner for AG-LIVE-BOUND-01. "
            "Live execution is not enabled in AG-LIVE-BRIDGE-01."
        ),
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Exact AG-LIVE-BOUND-01 query candidate.",
    )
    parser.add_argument(
        "--mode",
        default="Balanced",
        choices=["Balanced"],
        help="Pipeline mode (AG-LIVE-BOUND-01 requires Balanced).",
    )
    parser.add_argument(
        "--include-domains",
        required=True,
        metavar="DOMAINS",
        help="Comma-separated domain allowlist (must include docs.python.org).",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Sanitized packet output path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument("--run-id", help="Optional run id (UUID generated if omitted).")
    parser.add_argument(
        "--max-scryraven-runs",
        type=int,
        default=1,
        help="Planned cap: ScryRaven runs (must remain 1).",
    )
    parser.add_argument(
        "--max-search-dispatches",
        type=int,
        default=2,
        help="Planned cap: search dispatches (must remain 2).",
    )
    parser.add_argument(
        "--max-fetch-read-operations",
        type=int,
        default=3,
        help="Planned cap: fetch/read operations (must remain 3).",
    )
    parser.add_argument(
        "--max-author-model-calls",
        type=int,
        default=1,
        help="Planned cap: Author model calls (must remain 1).",
    )
    parser.add_argument(
        "--max-smart-search-judgment-model-calls",
        type=int,
        default=0,
        help="Planned cap: smart SearchJudgment model calls (must remain 0).",
    )
    parser.add_argument(
        "--max-independent-manual-source-checks",
        type=int,
        default=1,
        help="Planned cap: independent manual source checks (must remain 1).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=0,
        help="Planned cap: retries (must remain 0).",
    )
    parser.add_argument(
        "--approved-backup-query",
        action="store_true",
        help="Allow the AG-LIVE-PLAN-01 backup query candidate.",
    )
    parser.add_argument(
        "--confirm-live-product-run",
        action="store_true",
        help=(
            "Request live ordinary product execution. AG-LIVE-BRIDGE-01 fails closed "
            "before any live dispatch."
        ),
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
