"""CLI for the default-closed owner-specific SearchPlanner evaluation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationConfigurationError,
    EvaluationTransportError,
)
from scripts.evaluation.search_planner_owner_execution_stop_attestation import (
    STARTUP_HANDSHAKE_ENV_VAR,
    STARTUP_HANDSHAKE_TRIGGER_VALUE,
    OwnerExecutionStopAttestationError,
    write_evaluator_entry_handshake,
)
from scripts.evaluation.search_planner_owner_specific_authorization import (
    OwnerSpecificAuthorizationError,
    OwnerSpecificLiveAuthorization,
    OwnerSpecificScenarioPacket,
    load_json_object,
    normalize_repository_relative_path,
)
from scripts.evaluation.search_planner_owner_specific_orchestration import (
    OwnerSpecificOrchestrationError,
    build_plan_only_packet,
    execute_owner_specific_evaluation,
)


def current_repository_sha(
    *,
    repository_root: Path = ROOT,
) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=("Plan or execute the owner-specific SearchPlanner evaluation."))
    parser.add_argument(
        "--execution-mode",
        choices=("plan_only", "execute"),
        default="plan_only",
    )
    parser.add_argument("--repository-sha")
    parser.add_argument("--live-addendum")
    parser.add_argument("--scenario-packet")
    parser.add_argument("--output")
    return parser.parse_args(argv)


def _write_evaluator_entry_handshake_if_requested(
    *,
    output_packet_path: str,
    authorization: OwnerSpecificLiveAuthorization,
    live_addendum_path: str,
) -> None:
    """Publish a derived marker only for the launcher-owned trigger."""

    trigger = os.environ.get(STARTUP_HANDSHAKE_ENV_VAR)
    if trigger is None:
        return
    if trigger != STARTUP_HANDSHAKE_TRIGGER_VALUE:
        raise OwnerExecutionStopAttestationError("evaluator startup handshake trigger is invalid")
    requested_output_packet_path = normalize_repository_relative_path(
        output_packet_path,
        label="output packet path",
        repository_root=ROOT,
        require_output_local=True,
    )
    if (
        authorization.evaluation_identity.live_addendum_path != live_addendum_path
        or authorization.evaluation_identity.output_packet_path != requested_output_packet_path
    ):
        raise OwnerExecutionStopAttestationError(
            "evaluator startup handshake authority does not match the exact authorization"
        )
    write_evaluator_entry_handshake(
        authorization.evaluation_identity.output_packet_path,
        repository_root=ROOT,
    )


def main(argv: Sequence[str] | None = None) -> int:
    actual_argv = (
        tuple(argv)
        if argv is not None
        else (
            normalize_repository_relative_path(
                sys.argv[0],
                label="owner-specific evaluator entrypoint",
                repository_root=ROOT,
            ),
            *sys.argv[1:],
        )
    )
    if not actual_argv:
        raise OwnerSpecificAuthorizationError("CLI invocation must include the evaluator entrypoint")
    args = _parse_args(actual_argv[1:])
    exact_sha = current_repository_sha()
    if args.execution_mode == "plan_only":
        if any(
            (
                args.live_addendum,
                args.scenario_packet,
                args.output,
            )
        ):
            raise OwnerSpecificAuthorizationError(
                "plan_only rejects execute-only addendum, scenario, and output options"
            )
        if args.repository_sha and args.repository_sha != exact_sha:
            raise OwnerSpecificAuthorizationError("plan_only repository SHA differs from the exact checkout")
        packet = build_plan_only_packet(repository_sha=exact_sha)
        print(json.dumps(packet, indent=2, sort_keys=True))
        return 0

    if not all(
        (
            args.repository_sha,
            args.live_addendum,
            args.scenario_packet,
            args.output,
        )
    ):
        raise OwnerSpecificAuthorizationError(
            "execute requires repository SHA, live addendum, scenario packet, and output path"
        )
    if args.repository_sha != exact_sha:
        raise OwnerSpecificAuthorizationError("execute repository SHA differs from the exact checkout")
    addendum_path = normalize_repository_relative_path(
        args.live_addendum,
        label="live addendum path",
        repository_root=ROOT,
    )
    authorization = OwnerSpecificLiveAuthorization.from_mapping(load_json_object(ROOT / addendum_path))
    _write_evaluator_entry_handshake_if_requested(
        output_packet_path=args.output,
        authorization=authorization,
        live_addendum_path=addendum_path,
    )
    scenario_path = normalize_repository_relative_path(
        args.scenario_packet,
        label="scenario packet path",
        repository_root=ROOT,
    )
    scenario = OwnerSpecificScenarioPacket.from_mapping(load_json_object(ROOT / scenario_path))
    packet = execute_owner_specific_evaluation(
        authorization=authorization,
        scenario_packet=scenario,
        repository_sha=exact_sha,
        live_addendum_path=addendum_path,
        scenario_packet_path=scenario_path,
        output_packet_path=args.output,
        actual_argv=actual_argv,
        repository_root=ROOT,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        EvaluationConfigurationError,
        EvaluationTransportError,
        OwnerSpecificAuthorizationError,
        OwnerSpecificOrchestrationError,
        OwnerExecutionStopAttestationError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


__all__ = [
    "current_repository_sha",
    "main",
]
