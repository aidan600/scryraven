"""CLI for the default-closed owner-specific SearchPlanner evaluation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationConfigurationError,
    EvaluationTransportError,
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

ROOT = Path(__file__).resolve().parents[2]


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
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute the owner-specific SearchPlanner evaluation."
        )
    )
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
        raise OwnerSpecificAuthorizationError(
            "CLI invocation must include the evaluator entrypoint"
        )
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
            raise OwnerSpecificAuthorizationError(
                "plan_only repository SHA differs from the exact checkout"
            )
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
        raise OwnerSpecificAuthorizationError(
            "execute repository SHA differs from the exact checkout"
        )
    addendum_path = normalize_repository_relative_path(
        args.live_addendum,
        label="live addendum path",
        repository_root=ROOT,
    )
    scenario_path = normalize_repository_relative_path(
        args.scenario_packet,
        label="scenario packet path",
        repository_root=ROOT,
    )
    authorization = OwnerSpecificLiveAuthorization.from_mapping(
        load_json_object(ROOT / addendum_path)
    )
    scenario = OwnerSpecificScenarioPacket.from_mapping(
        load_json_object(ROOT / scenario_path)
    )
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
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


__all__ = [
    "current_repository_sha",
    "main",
]
