from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.live_search_validation_invocation_runtime import (  # noqa: E402
    LiveSearchValidationInvocationError,
    build_output_packet,
    dumps_packet,
    validate_request_packet,
    validate_safe_output_packet_path,
)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        request_packet = _load_request_packet(args.request)
        validate_request_packet(request_packet, root=ROOT)
        if args.output:
            validate_safe_output_packet_path(args.output, root=ROOT)
    except (LiveSearchValidationInvocationError, OSError, json.JSONDecodeError) as exc:
        print(f"refusing direct live-search validation request: {exc}", file=sys.stderr)
        return 2

    if not args.confirm_live_provider_call:
        packet = build_output_packet(
            request_packet=request_packet,
            validation_state=None,
            budget_exhausted=False,
            decision_made_by_run="direct_runner_dry_run_no_live_provider_call",
        )
        print(dumps_packet(packet), end="")
        return 0

    print(
        "refusing direct live-search validation request: PR2 scaffold has no "
        "provider transport; use an injected trusted operator adapter in a "
        "separately licensed live phase",
        file=sys.stderr,
    )
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an AG-LIVE-XAXIS-VALIDATION-01A PR2 search request packet "
            "without calling a live provider."
        )
    )
    parser.add_argument(
        "--request",
        required=True,
        help="Sanitized request packet path under output/.",
    )
    parser.add_argument(
        "--output",
        help="Optional sanitized output packet path under output/.",
    )
    parser.add_argument(
        "--confirm-live-provider-call",
        action="store_true",
        help="Required before any future trusted local provider call.",
    )
    return parser


def _load_request_packet(raw_path: str) -> dict[str, Any]:
    path = validate_safe_output_packet_path(raw_path, root=ROOT)
    decoded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise LiveSearchValidationInvocationError(
            "request packet must be a JSON object"
        )
    return decoded


if __name__ == "__main__":
    raise SystemExit(main())
