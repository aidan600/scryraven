from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.validation_profiles import (  # noqa: E402
    AG_LIVE_SMOKE,
    get_validation_profile,
    validation_profile_names,
)

OUTPUT_DIR = ROOT / "output"
DEFAULT_BROKER_URL = "http://127.0.0.1:8765/run"
TOKEN_ENV_VAR = "SCRYRAVEN_BROKER_TOKEN"
TOKEN_HEADER = "X-ScryRaven-Broker-Token"
LIVE_SPEND_WARNING = (
    "This request may spend the selected validation profile's bounded "
    "provider/model/search/fetch/read budget if accepted by the broker."
)
BUDGET_SUMMARY_FIELDS = (
    "max_scryraven_runs",
    "max_search_dispatches",
    "max_fetch_read_operations",
    "max_author_model_calls",
    "max_smart_search_judgment_model_calls",
    "max_retries",
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
    if not _is_loopback_broker_url(args.broker_url):
        print(
            "refusing to send broker token to non-local broker URL: "
            f"{args.broker_url}",
            file=sys.stderr,
        )
        return 2

    output_path = _resolve_output_path(args.output) if args.output else None
    if output_path is not None and not _is_allowed_output_path(output_path):
        print(
            "refusing to write broker response outside ignored repo output/ "
            f"path: {output_path}",
            file=sys.stderr,
        )
        return 2

    profile = get_validation_profile(args.profile)
    print(LIVE_SPEND_WARNING)
    print(_profile_budget_summary_line(profile.name))
    payload = _build_profile_request_payload(args.job_id, args.profile)
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
        "--profile",
        default=AG_LIVE_SMOKE,
        choices=validation_profile_names(),
        help=f"Approved product validation profile to request (default: {AG_LIVE_SMOKE}).",
    )
    parser.add_argument(
        "--token",
        help=f"One-shot broker token. Alternatively set {TOKEN_ENV_VAR}.",
    )
    parser.add_argument(
        "--confirm-live-provider-call",
        action="store_true",
        help=(
            "Acknowledge that the broker may spend the selected validation "
            "profile's bounded provider/model/search/fetch/read budget."
        ),
    )
    parser.add_argument(
        "--output",
        help="Optional ignored path for the sanitized broker JSON response.",
    )
    return parser


def _build_profile_request_payload(job_id: str, profile_name: str) -> dict[str, Any]:
    profile = get_validation_profile(profile_name)
    return {
        "job_id": job_id,
        "confirm_live": True,
        "request_kind": "approved_validation_profile",
        "profile_request": profile.broker_request_shape(),
    }


def _profile_budget_summary_line(profile_name: str) -> str:
    profile = get_validation_profile(profile_name)
    caps = profile.cap_policy.as_requested_dict()
    summary = ", ".join(f"{field}={caps[field]}" for field in BUDGET_SUMMARY_FIELDS)
    return f"Selected validation profile budget: profile={profile.name}, {summary}"


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


def _is_loopback_broker_url(broker_url: str) -> bool:
    parsed = parse.urlparse(broker_url)
    return (
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    )


def _resolve_output_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _is_allowed_output_path(path: Path) -> bool:
    try:
        path.relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        return False
    return _is_gitignored(path)


def _is_gitignored(path: Path) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(path)],
        check=False,
        capture_output=True,
        cwd=ROOT,
        text=True,
    )
    return result.returncode == 0


if __name__ == "__main__":
    raise SystemExit(main())
