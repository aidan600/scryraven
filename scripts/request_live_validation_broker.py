from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib import error, request

DEFAULT_BROKER_URL = "http://127.0.0.1:8765/run"
TOKEN_ENV_VAR = "SCRYRAVEN_BROKER_TOKEN"
TOKEN_HEADER = "X-ScryRaven-Broker-Token"
LIVE_SPEND_WARNING = (
    "This request may spend one live provider/search call if accepted by the broker."
)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    token = args.token or os.environ.get(TOKEN_ENV_VAR)
    if not token:
        print(
            f"refusing to request brokered live validation: provide --token or {TOKEN_ENV_VAR}",
            file=sys.stderr,
        )
        return 2
    if not args.confirm_live_provider_call:
        print(
            "refusing to request brokered live validation: pass "
            "--confirm-live-provider-call to acknowledge live-call spend",
            file=sys.stderr,
        )
        return 2

    output_path = Path(args.output) if args.output else None
    if output_path is not None and not _is_gitignored(output_path):
        print(
            f"refusing to write broker response to non-ignored path: {output_path}",
            file=sys.stderr,
        )
        return 2

    print(LIVE_SPEND_WARNING)
    payload = {"job_id": args.job_id, "confirm_live": True}
    status, broker_json = _post_broker_json(args.broker_url, token, payload)
    rendered = json.dumps(broker_json, indent=2, sort_keys=True)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote sanitized broker response to {output_path}")
    print(rendered)

    if status < 200 or status >= 300:
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Request an explicitly authorized local live-validation broker run.",
    )
    parser.add_argument(
        "--broker-url",
        default=DEFAULT_BROKER_URL,
        help=f"Local broker endpoint. Default: {DEFAULT_BROKER_URL}",
    )
    parser.add_argument(
        "--job-id",
        required=True,
        help="Allowlisted broker job id to request.",
    )
    parser.add_argument(
        "--token",
        help=f"One-shot broker token. Alternatively set {TOKEN_ENV_VAR}.",
    )
    parser.add_argument(
        "--confirm-live-provider-call",
        action="store_true",
        help="Acknowledge that the broker may spend one live provider/search call.",
    )
    parser.add_argument(
        "--output",
        help="Optional ignored path for the sanitized broker JSON response.",
    )
    return parser


def _post_broker_json(
    broker_url: str,
    token: str,
    payload: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    broker_request = request.Request(
        broker_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            TOKEN_HEADER: token,
        },
        method="POST",
    )
    try:
        with request.urlopen(broker_request, timeout=30) as response:
            return response.status, _decode_json_response(
                response.status,
                response.read(),
            )
    except error.HTTPError as exc:
        return exc.code, _decode_json_response(exc.code, exc.read())
    except error.URLError as exc:
        return 1, {
            "error": "broker_request_failed",
            "detail": _safe_error_detail(exc),
        }


def _decode_json_response(status: int, response_body: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "error": "broker_returned_non_json_response",
            "status": status,
        }
    if isinstance(decoded, dict):
        return decoded
    return {
        "error": "broker_returned_non_object_json_response",
        "status": status,
    }


def _safe_error_detail(exc: error.URLError) -> str:
    reason = getattr(exc, "reason", exc)
    return reason.__class__.__name__


def _is_gitignored(path: Path) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


if __name__ == "__main__":
    raise SystemExit(main())
