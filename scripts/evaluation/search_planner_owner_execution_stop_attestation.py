"""Privacy-safe owner-specific evaluator startup and stop attestation."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationConfigurationError,
    EvaluationTransportError,
)
from scripts.evaluation.search_planner_owner_specific_authorization import (
    OwnerSpecificAuthorizationError,
    OwnerSpecificLiveAuthorization,
    canonical_sha256,
    load_json_object,
    normalize_repository_relative_path,
)
from scripts.evaluation.search_planner_owner_specific_orchestration import (
    OwnerSpecificOrchestrationError,
    validate_owner_specific_result_packet_metadata,
)

STARTUP_HANDSHAKE_ENV_VAR = "SCRYRAVEN_SEARCHPLANNER_OWNER_STARTUP_HANDSHAKE_TRIGGER"
STARTUP_HANDSHAKE_TRIGGER_VALUE = "1"
STARTUP_HANDSHAKE_SCHEMA_VERSION = "search_planner_owner_evaluator_startup_handshake_v1"
STOP_ATTESTATION_SCHEMA_VERSION = "search_planner_owner_execution_stop_attestation_v1"
STARTUP_HANDSHAKE_OWNER = "SearchPlannerOwnerSpecificEvaluationCLI"
STOP_ATTESTATION_OWNER = "SearchPlannerOwnerExecutionStopAttestation"

EVALUATOR_STAGES = frozenset({"EVALUATOR_ENTERED"})
TERMINAL_STATUSES = frozenset(
    {
        "COMPLETE",
        "STOPPED_PRE_CHILD",
        "STOPPED_PRE_EVALUATOR_ENTRY",
        "STOPPED_AFTER_EVALUATOR_ENTRY",
        "STOPPED_AFTER_CHILD_EXIT",
        "STOPPED_DURING_RESULT_VALIDATION",
        "STOPPED_DURING_ATTESTATION_WRITE",
    }
)
OPERATOR_STAGES = frozenset(
    {
        "LAUNCHER_STARTED",
        "REPOSITORY_ROOT_RESOLVED",
        "LIVE_ADDENDUM_PATH_NORMALIZED",
        "LIVE_ADDENDUM_LOADED",
        "AUTHORIZATION_ROUND_TRIPPED",
        "REPOSITORY_SHA_VERIFIED",
        "CANONICAL_COMMAND_VERIFIED",
        "OUTPUT_PATHS_PREPARED",
        "CHILD_PROCESS_CREATED",
        "CHILD_EXIT_RECORDED",
        "RESULT_PACKET_VALIDATED",
        "ATTESTATION_WRITE",
    }
)
EVALUATOR_ENTRY_POSTURES = frozenset({"TRUE", "FALSE", "UNKNOWN"})
BROKER_STARTUP_POSTURES = frozenset({"TRUE", "FALSE", "UNKNOWN"})
MANIFEST_CONSUMPTION_POSTURES = frozenset(
    {
        "EXACT",
        "ZERO_PRE_CHILD",
        "ZERO_PRE_EVALUATOR",
        "UNKNOWN_AFTER_CHILD_CREATION",
        "UNKNOWN_AFTER_EVALUATOR_ENTRY",
    }
)
COST_POSTURES = frozenset(
    {
        "EXACT",
        "EXACT_ZERO_PRE_CHILD",
        "EXACT_ZERO_PRE_EVALUATOR",
        "UNKNOWN_AFTER_CHILD_CREATION",
        "UNKNOWN_AFTER_EVALUATOR_ENTRY",
    }
)
FAILURE_CODES = frozenset(
    {
        "NONE",
        "REPOSITORY_ROOT_RESOLUTION_FAILED",
        "LIVE_ADDENDUM_PATH_REJECTED",
        "LIVE_ADDENDUM_READ_FAILED",
        "AUTHORIZATION_VALIDATION_FAILED",
        "REPOSITORY_SHA_MISMATCH",
        "CANONICAL_COMMAND_DIGEST_MISMATCH",
        "CANONICAL_COMMAND_DECODE_FAILED",
        "CANONICAL_ARGV_SHAPE_INVALID",
        "CANONICAL_ARGV_REBUILD_MISMATCH",
        "HANDSHAKE_PATH_REJECTED",
        "ATTESTATION_PATH_ALREADY_EXISTS",
        "RESULT_PATH_ALREADY_EXISTS",
        "CHILD_PROCESS_CREATE_FAILED",
        "CHILD_PROCESS_NONZERO_EXIT",
        "EVALUATOR_ENTRY_UNATTESTED",
        "EVALUATOR_HANDSHAKE_INVALID",
        "RESULT_PACKET_MISSING",
        "RESULT_PACKET_VALIDATION_FAILED",
        "RESULT_PACKET_DIGEST_FAILED",
        "ATTESTATION_WRITE_FAILED",
        "UNEXPECTED_OPERATOR_EXCEPTION",
    }
)
EXCEPTION_CLASS_CODES = frozenset(
    {
        "OWNER_SPECIFIC_AUTHORIZATION_ERROR",
        "EVALUATION_CONFIGURATION_ERROR",
        "EVALUATION_TRANSPORT_ERROR",
        "OWNER_SPECIFIC_ORCHESTRATION_ERROR",
        "JSON_DECODE_ERROR",
        "OS_ERROR",
        "SUBPROCESS_ERROR",
        "VALUE_ERROR",
        "TYPE_ERROR",
        "UNEXPECTED_EXCEPTION",
        "NONE",
    }
)


class OwnerExecutionStopAttestationError(RuntimeError):
    """A bounded launcher or attestation contract failure."""


class ResultPacketDigestError(OwnerExecutionStopAttestationError):
    """The byte identity of an otherwise safe result could not be computed."""


@dataclass(frozen=True, slots=True)
class DerivedExecutionPaths:
    """Repository-confined paths derived only from validated authority."""

    result_relative: str
    startup_relative: str
    attestation_relative: str
    result_path: Path
    startup_path: Path
    attestation_path: Path


@dataclass(slots=True)
class StopAttestationFacts:
    """Mutable operator facts that become one immutable sanitized packet."""

    terminal_status: str = "STOPPED_PRE_CHILD"
    operator_stage: str = "LAUNCHER_STARTED"
    bounded_failure_code: str = "UNEXPECTED_OPERATOR_EXCEPTION"
    repository_sha: str | None = None
    authorization_sha256: str | None = None
    canonical_command_digest: str | None = None
    child_process_created: bool = False
    evaluator_entry_posture: str = "FALSE"
    highest_evaluator_stage: str | None = None
    child_exit_code: int | None = None
    result_packet_created: bool = False
    result_packet_sha256: str | None = None
    exception_class_code: str = "NONE"
    exception_message_sha256: str | None = None
    elapsed_milliseconds: int = 0
    captured_stdout: bool = False
    captured_stderr: bool = False
    captured_streams_discarded: bool = True
    broker_startup_posture: str = "UNKNOWN"
    manifest_consumption_posture: str = "ZERO_PRE_CHILD"
    planner_calls: int | None = 0
    primary_judge_calls: int | None = 0
    adversarial_judge_calls: int | None = 0
    total_broker_calls: int | None = 0
    cost_posture: str = "EXACT_ZERO_PRE_CHILD"
    observed_cost_usd: str | None = "0"
    raw_prompt_retained: bool = False
    raw_output_retained: bool = False
    provider_payload_retained: bool = False
    private_log_retained: bool = False
    full_trace_retained: bool = False

    def note_child_created(self) -> None:
        self.child_process_created = True
        self.evaluator_entry_posture = "UNKNOWN"
        self.highest_evaluator_stage = None
        self.manifest_consumption_posture = "UNKNOWN_AFTER_CHILD_CREATION"
        self.cost_posture = "UNKNOWN_AFTER_CHILD_CREATION"
        self.planner_calls = None
        self.primary_judge_calls = None
        self.adversarial_judge_calls = None
        self.total_broker_calls = None
        self.observed_cost_usd = None

    def note_evaluator_entry(self, stage: str) -> None:
        if stage not in EVALUATOR_STAGES:
            raise OwnerExecutionStopAttestationError("startup handshake stage is unsupported")
        self.child_process_created = True
        self.evaluator_entry_posture = "TRUE"
        self.highest_evaluator_stage = stage
        self.manifest_consumption_posture = "UNKNOWN_AFTER_EVALUATOR_ENTRY"
        self.cost_posture = "UNKNOWN_AFTER_EVALUATOR_ENTRY"
        self.planner_calls = None
        self.primary_judge_calls = None
        self.adversarial_judge_calls = None
        self.total_broker_calls = None
        self.observed_cost_usd = None

    def note_result_packet_observed(self) -> None:
        """Record only file presence; exact metadata still requires validation."""

        self.result_packet_created = True

    def note_exact_result(
        self,
        *,
        result_packet_sha256: str,
        metadata: Mapping[str, int | str],
    ) -> None:
        self.result_packet_created = True
        self.result_packet_sha256 = result_packet_sha256
        self.manifest_consumption_posture = "EXACT"
        self.cost_posture = "EXACT"
        self.planner_calls = int(metadata["planner_calls"])
        self.primary_judge_calls = int(metadata["primary_judge_calls"])
        self.adversarial_judge_calls = int(metadata["adversarial_judge_calls"])
        self.total_broker_calls = int(metadata["total_broker_calls"])
        self.observed_cost_usd = str(metadata["observed_cost_usd"])
        self.broker_startup_posture = "TRUE" if self.total_broker_calls > 0 else "UNKNOWN"

    def to_packet(self) -> dict[str, Any]:
        packet = {
            "schema_version": STOP_ATTESTATION_SCHEMA_VERSION,
            "owner": STOP_ATTESTATION_OWNER,
            "terminal_status": self.terminal_status,
            "operator_stage": self.operator_stage,
            "bounded_failure_code": self.bounded_failure_code,
            "repository_sha": self.repository_sha,
            "authorization_sha256": self.authorization_sha256,
            "canonical_command_digest": self.canonical_command_digest,
            "child_process_created": self.child_process_created,
            "evaluator_entry_posture": self.evaluator_entry_posture,
            "highest_evaluator_stage": self.highest_evaluator_stage,
            "child_exit_code": self.child_exit_code,
            "result_packet_created": self.result_packet_created,
            "result_packet_sha256": self.result_packet_sha256,
            "exception_class_code": self.exception_class_code,
            "exception_message_sha256": self.exception_message_sha256,
            "elapsed_milliseconds": self.elapsed_milliseconds,
            "captured_stdout": self.captured_stdout,
            "captured_stderr": self.captured_stderr,
            "captured_streams_discarded": self.captured_streams_discarded,
            "broker_startup_posture": self.broker_startup_posture,
            "manifest_consumption_posture": (self.manifest_consumption_posture),
            "planner_calls": self.planner_calls,
            "primary_judge_calls": self.primary_judge_calls,
            "adversarial_judge_calls": self.adversarial_judge_calls,
            "total_broker_calls": self.total_broker_calls,
            "cost_posture": self.cost_posture,
            "observed_cost_usd": self.observed_cost_usd,
            "raw_prompt_retained": self.raw_prompt_retained,
            "raw_output_retained": self.raw_output_retained,
            "provider_payload_retained": self.provider_payload_retained,
            "private_log_retained": self.private_log_retained,
            "full_trace_retained": self.full_trace_retained,
        }
        _validate_stop_attestation_body(packet)
        packet["attestation_sha256"] = canonical_sha256(packet)
        validate_stop_attestation_packet(packet)
        return packet


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _is_repository_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(character in "0123456789abcdef" for character in value)


def _require_exact_keys(
    packet: Mapping[str, Any],
    *,
    expected: set[str],
    label: str,
) -> None:
    if set(packet) != expected:
        raise OwnerExecutionStopAttestationError(f"{label} fields are invalid")


def _require_optional_digest(value: object, *, label: str) -> None:
    if value is not None and not _is_digest(value):
        raise OwnerExecutionStopAttestationError(f"{label} must be one SHA-256 digest or null")


def _require_count(value: object, *, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OwnerExecutionStopAttestationError(f"{label} must be one nonnegative integer or null")
    return value


def _require_cost(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise OwnerExecutionStopAttestationError("observed cost must be one exact decimal or null")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise OwnerExecutionStopAttestationError("observed cost must be one exact decimal or null") from exc
    if not parsed.is_finite() or parsed < 0:
        raise OwnerExecutionStopAttestationError("observed cost must be finite and nonnegative")
    return format(parsed, "f")


def _validate_stop_attestation_body(packet: Mapping[str, Any]) -> None:
    _require_exact_keys(
        packet,
        expected={
            "schema_version",
            "owner",
            "terminal_status",
            "operator_stage",
            "bounded_failure_code",
            "repository_sha",
            "authorization_sha256",
            "canonical_command_digest",
            "child_process_created",
            "evaluator_entry_posture",
            "highest_evaluator_stage",
            "child_exit_code",
            "result_packet_created",
            "result_packet_sha256",
            "exception_class_code",
            "exception_message_sha256",
            "elapsed_milliseconds",
            "captured_stdout",
            "captured_stderr",
            "captured_streams_discarded",
            "broker_startup_posture",
            "manifest_consumption_posture",
            "planner_calls",
            "primary_judge_calls",
            "adversarial_judge_calls",
            "total_broker_calls",
            "cost_posture",
            "observed_cost_usd",
            "raw_prompt_retained",
            "raw_output_retained",
            "provider_payload_retained",
            "private_log_retained",
            "full_trace_retained",
        },
        label="stop attestation",
    )
    if (
        packet["schema_version"] != STOP_ATTESTATION_SCHEMA_VERSION
        or packet["owner"] != STOP_ATTESTATION_OWNER
        or packet["terminal_status"] not in TERMINAL_STATUSES
        or packet["operator_stage"] not in OPERATOR_STAGES
        or packet["bounded_failure_code"] not in FAILURE_CODES
        or packet["exception_class_code"] not in EXCEPTION_CLASS_CODES
    ):
        raise OwnerExecutionStopAttestationError("stop attestation identity is invalid")
    for label in (
        "authorization_sha256",
        "canonical_command_digest",
        "result_packet_sha256",
        "exception_message_sha256",
    ):
        _require_optional_digest(packet[label], label=label)
    if packet["repository_sha"] is not None and not _is_repository_sha(packet["repository_sha"]):
        raise OwnerExecutionStopAttestationError("repository sha must be one lowercase Git object ID or null")
    for label in (
        "child_process_created",
        "result_packet_created",
        "captured_stdout",
        "captured_stderr",
        "captured_streams_discarded",
        "raw_prompt_retained",
        "raw_output_retained",
        "provider_payload_retained",
        "private_log_retained",
        "full_trace_retained",
    ):
        if not isinstance(packet[label], bool):
            raise OwnerExecutionStopAttestationError(f"stop attestation {label} is invalid")
    if packet["evaluator_entry_posture"] not in EVALUATOR_ENTRY_POSTURES:
        raise OwnerExecutionStopAttestationError("evaluator entry posture is invalid")
    if packet["broker_startup_posture"] not in BROKER_STARTUP_POSTURES:
        raise OwnerExecutionStopAttestationError("broker startup posture is invalid")
    if (
        packet["manifest_consumption_posture"] not in (MANIFEST_CONSUMPTION_POSTURES)
        or packet["cost_posture"] not in COST_POSTURES
    ):
        raise OwnerExecutionStopAttestationError("stop attestation consumption posture is invalid")
    if (
        isinstance(packet["elapsed_milliseconds"], bool)
        or not isinstance(packet["elapsed_milliseconds"], int)
        or packet["elapsed_milliseconds"] < 0
    ):
        raise OwnerExecutionStopAttestationError("elapsed milliseconds is invalid")
    if packet["child_exit_code"] is not None and (
        isinstance(packet["child_exit_code"], bool) or not isinstance(packet["child_exit_code"], int)
    ):
        raise OwnerExecutionStopAttestationError("child exit code is invalid")
    stage = packet["highest_evaluator_stage"]
    if stage is not None and stage not in EVALUATOR_STAGES:
        raise OwnerExecutionStopAttestationError("highest evaluator stage is invalid")
    counts = tuple(
        _require_count(packet[label], label=label)
        for label in (
            "planner_calls",
            "primary_judge_calls",
            "adversarial_judge_calls",
            "total_broker_calls",
        )
    )
    cost = _require_cost(packet["observed_cost_usd"])
    if (
        any(
            packet[label]
            for label in (
                "raw_prompt_retained",
                "raw_output_retained",
                "provider_payload_retained",
                "private_log_retained",
                "full_trace_retained",
            )
        )
        or packet["captured_streams_discarded"] is not True
    ):
        raise OwnerExecutionStopAttestationError("stop attestation retention posture is invalid")
    if packet["evaluator_entry_posture"] == "FALSE":
        if packet["child_process_created"] or stage is not None:
            raise OwnerExecutionStopAttestationError("false evaluator entry posture is inconsistent")
    elif not packet["child_process_created"]:
        raise OwnerExecutionStopAttestationError("child creation posture is inconsistent")
    if packet["evaluator_entry_posture"] == "UNKNOWN" and stage is not None:
        raise OwnerExecutionStopAttestationError("unknown evaluator entry cannot name a stage")
    if packet["evaluator_entry_posture"] == "TRUE" and stage is None:
        raise OwnerExecutionStopAttestationError("true evaluator entry requires one exact stage")
    if not packet["child_process_created"] and packet["child_exit_code"] is not None:
        raise OwnerExecutionStopAttestationError("absent child cannot carry one exit code")
    if packet["result_packet_created"] and (
        not packet["child_process_created"] or packet["evaluator_entry_posture"] != "TRUE"
    ):
        raise OwnerExecutionStopAttestationError("result packet presence requires attested evaluator entry")
    result_digest = packet["result_packet_sha256"]
    if not packet["result_packet_created"] and result_digest is not None:
        raise OwnerExecutionStopAttestationError("absent result packet cannot carry a digest")
    exact_metadata = packet["manifest_consumption_posture"] == "EXACT" or packet["cost_posture"] == "EXACT"
    if exact_metadata:
        if (
            not packet["result_packet_created"]
            or result_digest is None
            or packet["manifest_consumption_posture"] != "EXACT"
            or packet["cost_posture"] != "EXACT"
            or any(value is None for value in counts)
            or cost is None
        ):
            raise OwnerExecutionStopAttestationError("exact result posture is invalid")
        if counts[3] != sum(counts[:3]):
            raise OwnerExecutionStopAttestationError("exact broker count is inconsistent")
    elif result_digest is not None:
        raise OwnerExecutionStopAttestationError("result digest requires exact metadata")
    if packet["manifest_consumption_posture"] == "ZERO_PRE_CHILD":
        if (
            packet["child_process_created"]
            or packet["evaluator_entry_posture"] != "FALSE"
            or counts != (0, 0, 0, 0)
            or packet["cost_posture"] != "EXACT_ZERO_PRE_CHILD"
            or cost != "0"
        ):
            raise OwnerExecutionStopAttestationError("pre-child zero posture is invalid")
    if packet["manifest_consumption_posture"] == "ZERO_PRE_EVALUATOR":
        if (
            packet["child_process_created"]
            or packet["evaluator_entry_posture"] != "FALSE"
            or counts != (0, 0, 0, 0)
            or packet["cost_posture"] != "EXACT_ZERO_PRE_EVALUATOR"
            or cost != "0"
        ):
            raise OwnerExecutionStopAttestationError("pre-evaluator zero posture is invalid")
    if packet["manifest_consumption_posture"] in {
        "UNKNOWN_AFTER_CHILD_CREATION",
        "UNKNOWN_AFTER_EVALUATOR_ENTRY",
    } and (any(value is not None for value in counts) or cost is not None):
        raise OwnerExecutionStopAttestationError("unknown consumption cannot imply exact call or cost values")
    if (
        packet["cost_posture"]
        in {
            "UNKNOWN_AFTER_CHILD_CREATION",
            "UNKNOWN_AFTER_EVALUATOR_ENTRY",
        }
        and cost is not None
    ):
        raise OwnerExecutionStopAttestationError("unknown cost posture cannot carry a cost value")


def validate_stop_attestation_packet(packet: Mapping[str, Any]) -> None:
    """Validate one immutable stop-attestation packet and its self-digest."""

    expected = set(
        {
            "schema_version",
            "owner",
            "terminal_status",
            "operator_stage",
            "bounded_failure_code",
            "repository_sha",
            "authorization_sha256",
            "canonical_command_digest",
            "child_process_created",
            "evaluator_entry_posture",
            "highest_evaluator_stage",
            "child_exit_code",
            "result_packet_created",
            "result_packet_sha256",
            "exception_class_code",
            "exception_message_sha256",
            "elapsed_milliseconds",
            "captured_stdout",
            "captured_stderr",
            "captured_streams_discarded",
            "broker_startup_posture",
            "manifest_consumption_posture",
            "planner_calls",
            "primary_judge_calls",
            "adversarial_judge_calls",
            "total_broker_calls",
            "cost_posture",
            "observed_cost_usd",
            "raw_prompt_retained",
            "raw_output_retained",
            "provider_payload_retained",
            "private_log_retained",
            "full_trace_retained",
        }
    )
    expected.add("attestation_sha256")
    _require_exact_keys(
        packet,
        expected=expected,
        label="stop attestation",
    )
    digest = packet.get("attestation_sha256")
    if not _is_digest(digest):
        raise OwnerExecutionStopAttestationError("stop attestation digest is invalid")
    body = dict(packet)
    del body["attestation_sha256"]
    _validate_stop_attestation_body(body)
    if canonical_sha256(body) != digest:
        raise OwnerExecutionStopAttestationError("stop attestation digest does not bind its packet")


def _normalize_output_local_target(
    value: str | Path,
    *,
    repository_root: Path,
    label: str,
) -> tuple[str, Path]:
    relative = normalize_repository_relative_path(
        str(value),
        label=label,
        repository_root=repository_root,
        require_output_local=True,
    )
    return relative, repository_root.resolve() / relative


def derive_evaluator_entry_handshake_path(
    output_packet_path: str | Path,
    *,
    repository_root: Path,
) -> tuple[str, Path]:
    """Derive the only permitted evaluator-entry marker from an output path."""

    result_relative, _ = _normalize_output_local_target(
        output_packet_path,
        repository_root=repository_root,
        label="evaluator output packet path",
    )
    return _normalize_output_local_target(
        result_relative + ".startup.json",
        repository_root=repository_root,
        label="derived startup handshake path",
    )


def derive_execution_paths(
    authorization: OwnerSpecificLiveAuthorization,
    *,
    repository_root: Path,
) -> DerivedExecutionPaths:
    """Derive result, startup, and final paths from valid authority only."""

    result_relative, result_path = _normalize_output_local_target(
        authorization.evaluation_identity.output_packet_path,
        repository_root=repository_root,
        label="authorized result path",
    )
    startup_relative, startup_path = derive_evaluator_entry_handshake_path(
        result_relative,
        repository_root=repository_root,
    )
    attestation_relative, attestation_path = _normalize_output_local_target(
        result_relative + ".stop-attestation.json",
        repository_root=repository_root,
        label="derived stop attestation path",
    )
    return DerivedExecutionPaths(
        result_relative=result_relative,
        startup_relative=startup_relative,
        attestation_relative=attestation_relative,
        result_path=result_path,
        startup_path=startup_path,
        attestation_path=attestation_path,
    )


def _write_new_json_atomically(path: Path, packet: Mapping[str, Any]) -> None:
    """Publish one strict JSON packet without replacing an existing target."""

    if path.exists():
        raise FileExistsError("target already exists")
    rendered = (
        json.dumps(
            packet,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
        + "\n"
    )
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def build_evaluator_entry_handshake() -> dict[str, Any]:
    """Build the sole minimal evaluator-entry marker."""

    packet = {
        "schema_version": STARTUP_HANDSHAKE_SCHEMA_VERSION,
        "owner": STARTUP_HANDSHAKE_OWNER,
        "stage": "EVALUATOR_ENTERED",
        "raw_prompt_retained": False,
        "raw_output_retained": False,
        "provider_payload_retained": False,
        "private_log_retained": False,
        "full_trace_retained": False,
    }
    packet["handshake_sha256"] = canonical_sha256(packet)
    validate_evaluator_entry_handshake(packet)
    return packet


def validate_evaluator_entry_handshake(packet: Mapping[str, Any]) -> None:
    """Validate a bounded marker without retaining its source material."""

    _require_exact_keys(
        packet,
        expected={
            "schema_version",
            "owner",
            "stage",
            "raw_prompt_retained",
            "raw_output_retained",
            "provider_payload_retained",
            "private_log_retained",
            "full_trace_retained",
            "handshake_sha256",
        },
        label="evaluator entry handshake",
    )
    if (
        packet.get("schema_version") != STARTUP_HANDSHAKE_SCHEMA_VERSION
        or packet.get("owner") != STARTUP_HANDSHAKE_OWNER
        or packet.get("stage") not in EVALUATOR_STAGES
        or not _is_digest(packet.get("handshake_sha256"))
    ):
        raise OwnerExecutionStopAttestationError("evaluator entry handshake identity is invalid")
    if any(
        packet.get(label) is not False
        for label in (
            "raw_prompt_retained",
            "raw_output_retained",
            "provider_payload_retained",
            "private_log_retained",
            "full_trace_retained",
        )
    ):
        raise OwnerExecutionStopAttestationError("evaluator entry handshake retention posture is invalid")
    body = dict(packet)
    digest = body.pop("handshake_sha256")
    if canonical_sha256(body) != digest:
        raise OwnerExecutionStopAttestationError("evaluator entry handshake digest is invalid")


def write_evaluator_entry_handshake(
    output_packet_path: str | Path,
    *,
    repository_root: Path,
) -> None:
    """Write the one bounded marker at a path derived from evaluator output."""

    _, target = derive_evaluator_entry_handshake_path(
        output_packet_path,
        repository_root=repository_root,
    )
    _write_new_json_atomically(target, build_evaluator_entry_handshake())


def load_evaluator_entry_handshake(
    path: Path,
    *,
    repository_root: Path,
) -> dict[str, Any]:
    """Load and validate only the marker's fixed safe shape."""

    _, target = _normalize_output_local_target(
        path,
        repository_root=repository_root,
        label="evaluator startup handshake path",
    )
    packet = load_json_object(target)
    validate_evaluator_entry_handshake(packet)
    return packet


def write_stop_attestation(
    path: Path,
    *,
    repository_root: Path,
    facts: StopAttestationFacts,
) -> dict[str, Any]:
    """Write one self-binding final packet at a derived output-local path."""

    _, target = _normalize_output_local_target(
        path,
        repository_root=repository_root,
        label="stop attestation path",
    )
    packet = facts.to_packet()
    _write_new_json_atomically(target, packet)
    return packet


def load_validated_result_metadata(
    path: Path,
    *,
    authorization: OwnerSpecificLiveAuthorization,
    repository_sha: str,
) -> tuple[str, dict[str, int | str]]:
    """Return byte identity and exact safe totals from a normal result packet."""

    try:
        packet = load_json_object(path)
    except OwnerSpecificAuthorizationError as exc:
        raise OwnerExecutionStopAttestationError("result packet cannot be read as strict JSON") from exc
    try:
        metadata = validate_owner_specific_result_packet_metadata(
            packet,
            authorization=authorization,
            repository_sha=repository_sha,
        )
    except OwnerSpecificOrchestrationError as exc:
        raise OwnerExecutionStopAttestationError("result packet is not one validated normal packet") from exc
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ResultPacketDigestError("result packet digest could not be computed") from exc
    return digest, metadata


def exception_class_code(exc: BaseException | None) -> str:
    """Return one allowlisted diagnostic class without retaining a message."""

    if exc is None:
        return "NONE"
    if isinstance(exc, json.JSONDecodeError):
        return "JSON_DECODE_ERROR"
    if isinstance(exc, EvaluationConfigurationError):
        return "EVALUATION_CONFIGURATION_ERROR"
    if isinstance(exc, EvaluationTransportError):
        return "EVALUATION_TRANSPORT_ERROR"
    if isinstance(exc, subprocess.SubprocessError):
        return "SUBPROCESS_ERROR"
    if isinstance(exc, OwnerSpecificAuthorizationError):
        return "OWNER_SPECIFIC_AUTHORIZATION_ERROR"
    if isinstance(exc, OwnerSpecificOrchestrationError):
        return "OWNER_SPECIFIC_ORCHESTRATION_ERROR"
    if isinstance(exc, OSError):
        return "OS_ERROR"
    if isinstance(exc, ValueError):
        return "VALUE_ERROR"
    if isinstance(exc, TypeError):
        return "TYPE_ERROR"
    return "UNEXPECTED_EXCEPTION"


def exception_message_sha256(exc: BaseException | None) -> str | None:
    """Bind exception identity without storing its potentially private text."""

    if exc is None:
        return None
    return hashlib.sha256(str(exc).encode("utf-8")).hexdigest()


__all__ = [
    "BROKER_STARTUP_POSTURES",
    "COST_POSTURES",
    "DerivedExecutionPaths",
    "EVALUATOR_ENTRY_POSTURES",
    "EVALUATOR_STAGES",
    "EXCEPTION_CLASS_CODES",
    "FAILURE_CODES",
    "MANIFEST_CONSUMPTION_POSTURES",
    "OPERATOR_STAGES",
    "OwnerExecutionStopAttestationError",
    "ResultPacketDigestError",
    "STARTUP_HANDSHAKE_ENV_VAR",
    "STARTUP_HANDSHAKE_TRIGGER_VALUE",
    "STARTUP_HANDSHAKE_SCHEMA_VERSION",
    "STOP_ATTESTATION_SCHEMA_VERSION",
    "StopAttestationFacts",
    "TERMINAL_STATUSES",
    "build_evaluator_entry_handshake",
    "derive_evaluator_entry_handshake_path",
    "derive_execution_paths",
    "exception_class_code",
    "exception_message_sha256",
    "load_evaluator_entry_handshake",
    "load_validated_result_metadata",
    "validate_evaluator_entry_handshake",
    "validate_stop_attestation_packet",
    "write_evaluator_entry_handshake",
    "write_stop_attestation",
]
