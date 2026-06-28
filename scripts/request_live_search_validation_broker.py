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
    build_broker_request_envelope,
    dumps_packet,
    validate_request_packet,
    validate_safe_output_packet_path,
)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        request_packet = _load_request_packet(args.request)
        validate_request_packet(request_packet, root=ROOT)
    except (LiveSearchValidationInvocationError, OSError, json.JSONDecodeError) as exc:
        print(f"refusing brokered live-search validation request: {exc}", file=sys.stderr)
        return 2

    if not args.confirm_live_provider_call:
        print(
            "refusing brokered live-search validation request: pass "
            "--confirm-live-provider-call before emitting a broker live-search "
            "request envelope",
            file=sys.stderr,
        )
        return 2

    envelope = build_broker_request_envelope(
        request_packet,
        root=ROOT,
        confirm_live_provider_call=True,
    )
    print(dumps_packet(envelope), end="")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Emit an AG-LIVE-XAXIS-VALIDATION-01A PR2 broker request envelope "
            "without calling a broker job."
        )
    )
    parser.add_argument(
        "--request",
        required=True,
        help="Sanitized request packet path under output/.",
    )
    parser.add_argument(
        "--confirm-live-provider-call",
        action="store_true",
        help="Required before emitting the broker-facing live-search request.",
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
