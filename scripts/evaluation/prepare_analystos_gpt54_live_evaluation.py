"""Prepare three ignored, nonauthoritative AnalystOS live-addendum packets.

This operator is offline.  It reads the current Git object identity, delegates
all request/call/command derivation to the installed evaluator, validates every
packet, and writes the three packets only after the complete set is proven.
It never constructs a model transport and never executes a generated command.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.multicomponent_role_runtime import (  # noqa: E402
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
)
from scripts.evaluation.openai_responses_origination_transport import (  # noqa: E402
    REQUEST_TIMEOUT_SECONDS,
    SDK_MAX_RETRIES,
    SUPPORTED_MODEL,
    SUPPORTED_PROVIDER,
    TRANSPORT_FACTORY_SPEC,
    conservative_cost_decimal,
)
from scripts.evaluation.run_analystos_model_origination_evaluation import (  # noqa: E402
    LIVE_ADDENDUM_SCHEMA_VERSION,
    EvaluationConfigurationError,
    EvaluationRequest,
    ExecutionIdentity,
    LiveAuthorization,
    build_call_manifest,
    build_execution_identity,
    current_repository_sha,
    resolve_request,
    validate_canonical_cli_invocation,
    validate_live_authorization,
)
from tests.fixtures.analystos_model_origination_expectations import (  # noqa: E402
    ROLE_SEARCH_PLANNER,
)

OUTPUT_ROOT = Path("output/local/analystos-live-origination-01")
MAXIMUM_INPUT_TOKENS = 16_000
MAXIMUM_OUTPUT_TOKENS = 8_000
PER_CALL_COST_CEILING = Decimal("0.16")
WHOLE_PHASE_COST_CEILING = Decimal("3.20")

FINAL_DECISION_VOCABULARY = (
    "ACCEPT_ORIGINATION_BASELINE, MODEL_ORIGINATION_LIMITATION, "
    "REVIEW_REQUIRED, or HARNESS_OR_ARCHITECTURE_FAILURE"
)
STOP_CONDITION = (
    "Stop this stage and all remaining stages immediately for PACKET, "
    "PARSER_CONTRACT, OPERATING_SYSTEM, PROMPT, any EvaluationTransportError "
    "or subtype, any call, retry, token, route, or cost-cap failure, "
    "output-packet publication failure, or raw-material or credential "
    "exposure. PROMPT is impossible because no paired probe is licensed and "
    "therefore indicates a harness defect. A 600-second OpenAI request timeout "
    "is potentially billable and requires explicit maintainer reauthorization "
    "before any rerun."
)


@dataclass(frozen=True, slots=True)
class StageDefinition:
    label: str
    addendum_filename: str
    result_filename: str
    evaluation_pass: str
    roles: tuple[str, ...]
    scenarios: tuple[str, ...]
    expected_calls: int
    expected_runs: int
    expected_cost: Decimal
    decision: str


@dataclass(frozen=True, slots=True)
class PreparedAddendum:
    definition: StageDefinition
    request: EvaluationRequest
    manifest_packet: Mapping[str, Any]
    execution_identity: ExecutionIdentity
    authorization: LiveAuthorization
    addendum_path: str
    addendum_digest: str

    def to_summary(self) -> dict[str, Any]:
        manifest_census = {
            key: self.manifest_packet[key]
            for key in (
                "evaluation_pass",
                "execution_mode",
                "selected_model_roles",
                "scenario_ids",
                "maximum_scryraven_runs",
                "total_maximum_physical_model_calls",
                "retry_allowance",
                "calls_by_role",
                "calls_by_scenario",
                "calls_by_pass",
                "conditional_call_ids",
            )
        }
        return {
            "stage": self.definition.label,
            "addendum_path": self.addendum_path,
            "addendum_digest": self.addendum_digest,
            "result_path": self.authorization.output_packet_path,
            "resolved_request": asdict(self.request),
            "manifest_census": manifest_census,
            "execution_identity": {
                "digest": self.execution_identity.execution_identity_digest,
                "canonical_operator_command": (
                    self.execution_identity.canonical_operator_command
                ),
                "canonical_operator_command_digest": (
                    self.execution_identity.canonical_operator_command_digest
                ),
            },
            "cost_ceiling": self.authorization.cost_ceiling,
        }


def _stage_definitions(output_root: Path) -> tuple[StageDefinition, ...]:
    result_prefix = output_root.as_posix().rstrip("/")
    return (
        StageDefinition(
            label="A",
            addendum_filename="planner-addendum.json",
            result_filename="planner-result.json",
            evaluation_pass="planner_only",
            roles=(ROLE_SEARCH_PLANNER,),
            scenarios=(
                "case_03_pure_depth_two",
                "case_04_nested_serial_recovery",
                "case_06_root_query_retention",
                "case_07_honest_nonclosure",
            ),
            expected_calls=4,
            expected_runs=4,
            expected_cost=Decimal("0.64"),
            decision=(
                "Measure the isolated SearchPlanner origination boundary. Stage "
                "B is an independent isolated measurement and may proceed after "
                "Stage A produces MODEL or REVIEW_REQUIRED. Use only "
                f"{FINAL_DECISION_VOCABULARY} for the eventual final decision. "
                f"Publish the sanitized result only to {result_prefix}/planner-result.json."
            ),
        ),
        StageDefinition(
            label="B",
            addendum_filename="analyst-addendum.json",
            result_filename="analyst-result.json",
            evaluation_pass="analyst_only",
            roles=(ROLE_COMPONENT_ANALYST, ROLE_CROSS_COMPONENT_ANALYST),
            scenarios=(
                "case_04_nested_serial_recovery",
                "case_07_honest_nonclosure",
            ),
            expected_calls=9,
            expected_runs=2,
            expected_cost=Decimal("1.44"),
            decision=(
                "Measure the isolated Component Analyst and Cross-Component "
                "Analyst boundaries. Stage C is prohibited unless every "
                "scenario result from reviewed Stages A and B is PASS. Use only "
                f"{FINAL_DECISION_VOCABULARY} for the eventual final decision. "
                f"Publish the sanitized result only to {result_prefix}/analyst-result.json."
            ),
        ),
        StageDefinition(
            label="C",
            addendum_filename="combined-addendum.json",
            result_filename="combined-result.json",
            evaluation_pass="combined",
            roles=(
                ROLE_SEARCH_PLANNER,
                ROLE_COMPONENT_ANALYST,
                ROLE_CROSS_COMPONENT_ANALYST,
            ),
            scenarios=("case_06_root_query_retention",),
            expected_calls=7,
            expected_runs=1,
            expected_cost=Decimal("1.12"),
            decision=(
                "Measure the combined boundary only after a maintainer reviews "
                "every Stage A and B scenario as PASS. Use only "
                f"{FINAL_DECISION_VOCABULARY} for the final decision. Publish "
                f"the sanitized result only to {result_prefix}/combined-result.json."
            ),
        ),
    )


def _prove_paths_ignored(
    repository_root: Path,
    paths: Sequence[str],
) -> None:
    for path in paths:
        completed = subprocess.run(
            ["git", "check-ignore", "--quiet", "--", path],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise EvaluationConfigurationError(
                f"refusing to prepare addenda because Git does not ignore {path}"
            )


def _packet_for(
    *,
    definition: StageDefinition,
    repository_sha: str,
    request: EvaluationRequest,
    identity: ExecutionIdentity,
    maximum_model_calls: int,
    maximum_scryraven_runs: int,
    cost_ceiling: Decimal,
) -> dict[str, Any]:
    return {
        "schema_version": LIVE_ADDENDUM_SCHEMA_VERSION,
        "reference": (
            "ANALYSTOS-DIRECT-OPENAI-LIVE-TRANSPORT-AND-ADDENDUM-PREP-01:"
            f"stage-{definition.label}:{repository_sha}"
        ),
        "repository_sha": repository_sha,
        "provider": SUPPORTED_PROVIDER,
        "model": SUPPORTED_MODEL,
        "allowed_evaluation_pass": request.evaluation_pass,
        "allowed_model_roles": list(request.selected_model_roles),
        "allowed_scenario_ids": list(request.scenario_ids),
        "maximum_model_calls": maximum_model_calls,
        "maximum_scryraven_runs": maximum_scryraven_runs,
        "retry_cap": SDK_MAX_RETRIES,
        "maximum_input_tokens": MAXIMUM_INPUT_TOKENS,
        "maximum_output_tokens": MAXIMUM_OUTPUT_TOKENS,
        "cost_ceiling": float(cost_ceiling),
        "output_packet_path": identity.output_packet_path,
        "decision": definition.decision,
        "stop_condition": STOP_CONDITION,
        "raw_retention_posture": "sanitized_only",
        "transport_factory_spec": identity.transport_factory_spec,
        "canonical_operator_command": identity.canonical_operator_command,
        "canonical_operator_command_digest": (
            identity.canonical_operator_command_digest
        ),
    }


def prepare_live_addenda(
    *,
    repository_root: Path = ROOT,
    output_root: Path = OUTPUT_ROOT,
) -> tuple[PreparedAddendum, ...]:
    """Derive, validate, and write the three current-HEAD addenda."""

    exact_root = repository_root.resolve()
    repository_sha = current_repository_sha(exact_root)
    definitions = _stage_definitions(output_root)
    if conservative_cost_decimal(
        MAXIMUM_INPUT_TOKENS,
        MAXIMUM_OUTPUT_TOKENS,
    ) != PER_CALL_COST_CEILING:
        raise EvaluationConfigurationError(
            "fixed per-call Decimal cost ceiling is inconsistent"
        )

    derived: list[
        tuple[
            StageDefinition,
            EvaluationRequest,
            Mapping[str, Any],
            ExecutionIdentity,
            LiveAuthorization,
            str,
            bytes,
        ]
    ] = []
    for definition in definitions:
        requested = EvaluationRequest(
            evaluation_pass=definition.evaluation_pass,
            execution_mode="execute",
            scenario_ids=definition.scenarios,
            selected_model_roles=definition.roles,
            output_packet_path=(
                output_root / definition.result_filename
            ).as_posix(),
        )
        resolved = resolve_request(requested)
        manifest = build_call_manifest(resolved, retry_allowance=SDK_MAX_RETRIES)
        if resolved.selected_model_roles != definition.roles:
            raise EvaluationConfigurationError(
                f"Stage {definition.label} role order differs from the installed evaluator"
            )
        if resolved.scenario_ids != definition.scenarios:
            raise EvaluationConfigurationError(
                f"Stage {definition.label} scenario order differs from the installed evaluator"
            )
        if (
            manifest.total_maximum_physical_model_calls
            != definition.expected_calls
        ):
            raise EvaluationConfigurationError(
                f"Stage {definition.label} call census differs from the installed evaluator"
            )
        if manifest.maximum_scryraven_runs != definition.expected_runs:
            raise EvaluationConfigurationError(
                f"Stage {definition.label} run census differs from the installed evaluator"
            )
        stage_cost = (
            Decimal(manifest.total_maximum_physical_model_calls)
            * PER_CALL_COST_CEILING
        )
        if stage_cost != definition.expected_cost:
            raise EvaluationConfigurationError(
                f"Stage {definition.label} Decimal cost ceiling is inconsistent"
            )

        addendum_path = (
            output_root / definition.addendum_filename
        ).as_posix()
        identity = build_execution_identity(
            resolved,
            repository_sha=repository_sha,
            live_addendum_path=addendum_path,
            transport_factory_spec=TRANSPORT_FACTORY_SPEC,
            repository_root=exact_root,
        )
        packet = _packet_for(
            definition=definition,
            repository_sha=repository_sha,
            request=resolved,
            identity=identity,
            maximum_model_calls=(
                manifest.total_maximum_physical_model_calls
            ),
            maximum_scryraven_runs=manifest.maximum_scryraven_runs,
            cost_ceiling=stage_cost,
        )
        authorization = LiveAuthorization.from_mapping(packet)
        validated_manifest = validate_live_authorization(
            resolved,
            authorization,
            repository_sha=repository_sha,
            execution_identity=identity,
        )
        if validated_manifest.to_packet() != manifest.to_packet():
            raise EvaluationConfigurationError(
                f"Stage {definition.label} validated manifest changed during preparation"
            )
        validate_canonical_cli_invocation(
            identity,
            identity.canonical_argv,
        )
        rendered = (
            json.dumps(packet, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        derived.append(
            (
                definition,
                resolved,
                manifest.to_packet(),
                identity,
                authorization,
                addendum_path,
                rendered,
            )
        )

    total_cost = sum(
        (item[0].expected_cost for item in derived),
        start=Decimal("0"),
    )
    if total_cost != WHOLE_PHASE_COST_CEILING:
        raise EvaluationConfigurationError(
            "whole-phase Decimal cost ceiling is inconsistent"
        )
    _prove_paths_ignored(
        exact_root,
        tuple(
            path
            for item in derived
            for path in (
                item[5],
                item[4].output_packet_path,
            )
        ),
    )

    prepared: list[PreparedAddendum] = []
    for (
        definition,
        resolved,
        manifest_packet,
        identity,
        authorization,
        addendum_path,
        rendered,
    ) in derived:
        target = exact_root / addendum_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(rendered)
        prepared.append(
            PreparedAddendum(
                definition=definition,
                request=resolved,
                manifest_packet=manifest_packet,
                execution_identity=identity,
                authorization=authorization,
                addendum_path=addendum_path,
                addendum_digest=sha256(rendered).hexdigest(),
            )
        )
    return tuple(prepared)


def main() -> int:
    prepared = prepare_live_addenda()
    summary = {
        "repository_sha": prepared[0].authorization.repository_sha,
        "provider": SUPPORTED_PROVIDER,
        "model": SUPPORTED_MODEL,
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "retry_cap": SDK_MAX_RETRIES,
        "total_maximum_model_calls": sum(
            item.authorization.maximum_model_calls for item in prepared
        ),
        "total_maximum_scryraven_runs": sum(
            item.authorization.maximum_scryraven_runs for item in prepared
        ),
        "whole_phase_cost_ceiling": float(WHOLE_PHASE_COST_CEILING),
        "live_commands_executed": False,
        "authoritative_for_live_use": False,
        "post_merge_regeneration_required": True,
        "notice": (
            "These branch-generated packets are validation artifacts only. "
            "Regenerate from a clean synchronized merged main before review or "
            "live authorization."
        ),
        "stages": [item.to_summary() for item in prepared],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvaluationConfigurationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


__all__ = [
    "MAXIMUM_INPUT_TOKENS",
    "MAXIMUM_OUTPUT_TOKENS",
    "OUTPUT_ROOT",
    "PER_CALL_COST_CEILING",
    "PreparedAddendum",
    "StageDefinition",
    "WHOLE_PHASE_COST_CEILING",
    "prepare_live_addenda",
]
