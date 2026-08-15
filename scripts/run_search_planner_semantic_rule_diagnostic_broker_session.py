"""Run one bounded six-request broker session for the Planner diagnostic.

The helper never opens the private environment file. It passes that path only
to the tracked broker child, and passes the one-session token only to the
broker and evaluator children through separate minimal environments.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import request_provider_proxy_broker as broker_client
from scripts import run_provider_proxy_broker_once as broker_helper

EVALUATOR_ENTRYPOINT = ROOT / "scripts" / "evaluation" / "run_search_planner_semantic_rule_diagnostic.py"
MAXIMUM_REQUESTS = 6
CHILD_TIMEOUT_SECONDS = 1_400.0


class SearchPlannerDiagnosticBrokerSessionError(ValueError):
    """Closed public configuration error for the single broker session."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run exactly one six-request Planner diagnostic broker session.")
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--repository-sha", required=True)
    parser.add_argument("--cases-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--current-date")
    parser.add_argument(
        "--confirm-live-evaluation",
        action="store_true",
        help="Required acknowledgement before the broker can start.",
    )
    return parser


def _broker_port() -> int:
    parsed = urlparse(broker_client.DEFAULT_BROKER_URL)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port is None:
        raise SearchPlannerDiagnosticBrokerSessionError("fixed_loopback_broker_url_required")
    return parsed.port


def _evaluator_argv(args: argparse.Namespace) -> list[str]:
    argv = [
        sys.executable,
        str(EVALUATOR_ENTRYPOINT),
        "--execute",
        "--repository-sha",
        args.repository_sha,
        "--cases-file",
        args.cases_file,
        "--output",
        args.output,
    ]
    if args.current_date:
        argv.extend(["--current-date", args.current_date])
    return argv


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    broker_process: subprocess.Popen[bytes] | None = None
    token: str | None = None
    try:
        if not args.confirm_live_evaluation:
            raise SearchPlannerDiagnosticBrokerSessionError("provider_call_confirmation_required")
        if not EVALUATOR_ENTRYPOINT.is_file():
            raise SearchPlannerDiagnosticBrokerSessionError("evaluator_entrypoint_unavailable")
        env_file_path = broker_helper.normalize_environment_file_path(args.env_file)
        token = broker_helper.generate_temporary_broker_token()
        broker_process = broker_helper.start_tracked_broker(
            broker_env=broker_helper.broker_environment(
                token=token,
                env_file_path=env_file_path,
                maximum_requests=MAXIMUM_REQUESTS,
                process_env=os.environ,
            ),
            port=_broker_port(),
        )
        broker_helper.wait_for_broker_readiness(
            broker_process,
            broker_url=broker_client.DEFAULT_BROKER_URL,
            timeout_seconds=broker_helper.READINESS_TIMEOUT_SECONDS,
        )
        client_env = broker_helper.client_environment(
            token=token,
            process_env=os.environ,
        )
        client_env["SCRYRAVEN_SEARCH_PLANNER_DIAGNOSTIC_BROKER_SESSION"] = "1"
        completed = subprocess.run(
            _evaluator_argv(args),
            cwd=ROOT,
            env=client_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=CHILD_TIMEOUT_SECONDS,
        )
        if completed.returncode != 0:
            raise SearchPlannerDiagnosticBrokerSessionError("evaluator_child_failed_closed")
    except (
        SearchPlannerDiagnosticBrokerSessionError,
        broker_helper.ProviderExecutionOperatorError,
        OSError,
        subprocess.SubprocessError,
    ):
        print("search-planner diagnostic broker session failed closed", file=sys.stderr)
        return 2
    finally:
        if broker_process is not None:
            broker_helper.stop_tracked_broker(broker_process)
        token = None

    print("search-planner diagnostic broker session completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CHILD_TIMEOUT_SECONDS",
    "EVALUATOR_ENTRYPOINT",
    "MAXIMUM_REQUESTS",
    "SearchPlannerDiagnosticBrokerSessionError",
    "main",
]
