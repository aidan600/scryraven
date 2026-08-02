from __future__ import annotations

from pathlib import Path

import pytest

from scripts.evaluation import (
    search_planner_owner_execution_stop_attestation as attestation,
)


def test_pre_child_stop_is_exact_zero_and_self_binding() -> None:
    facts = attestation.StopAttestationFacts(
        repository_sha="a" * 40,
        bounded_failure_code="CANONICAL_COMMAND_DECODE_FAILED",
        exception_class_code="JSON_DECODE_ERROR",
        exception_message_sha256="a" * 64,
    )

    packet = facts.to_packet()

    attestation.validate_stop_attestation_packet(packet)
    assert packet["child_process_created"] is False
    assert packet["evaluator_entry_posture"] == "FALSE"
    assert packet["manifest_consumption_posture"] == "ZERO_PRE_CHILD"
    assert packet["cost_posture"] == "EXACT_ZERO_PRE_CHILD"
    assert packet["planner_calls"] == 0
    assert packet["primary_judge_calls"] == 0
    assert packet["adversarial_judge_calls"] == 0
    assert packet["total_broker_calls"] == 0
    assert packet["observed_cost_usd"] == "0"


def test_child_created_without_marker_keeps_calls_and_cost_unknown() -> None:
    facts = attestation.StopAttestationFacts(bounded_failure_code="EVALUATOR_ENTRY_UNATTESTED")
    facts.note_child_created()
    facts.terminal_status = "STOPPED_PRE_EVALUATOR_ENTRY"

    packet = facts.to_packet()

    attestation.validate_stop_attestation_packet(packet)
    assert packet["child_process_created"] is True
    assert packet["evaluator_entry_posture"] == "UNKNOWN"
    assert packet["highest_evaluator_stage"] is None
    assert packet["manifest_consumption_posture"] == ("UNKNOWN_AFTER_CHILD_CREATION")
    assert packet["cost_posture"] == "UNKNOWN_AFTER_CHILD_CREATION"
    assert all(
        packet[label] is None
        for label in (
            "planner_calls",
            "primary_judge_calls",
            "adversarial_judge_calls",
            "total_broker_calls",
            "observed_cost_usd",
        )
    )


def test_evaluator_entry_without_result_keeps_calls_and_cost_unknown() -> None:
    facts = attestation.StopAttestationFacts(bounded_failure_code="RESULT_PACKET_MISSING")
    facts.note_child_created()
    facts.note_evaluator_entry("EVALUATOR_ENTERED")
    facts.terminal_status = "STOPPED_AFTER_EVALUATOR_ENTRY"

    packet = facts.to_packet()

    attestation.validate_stop_attestation_packet(packet)
    assert packet["evaluator_entry_posture"] == "TRUE"
    assert packet["highest_evaluator_stage"] == "EVALUATOR_ENTERED"
    assert packet["manifest_consumption_posture"] == ("UNKNOWN_AFTER_EVALUATOR_ENTRY")
    assert packet["cost_posture"] == "UNKNOWN_AFTER_EVALUATOR_ENTRY"
    assert packet["planner_calls"] is None
    assert packet["observed_cost_usd"] is None


def test_validated_result_is_the_only_exact_call_and_cost_source() -> None:
    facts = attestation.StopAttestationFacts(
        terminal_status="COMPLETE",
        bounded_failure_code="NONE",
    )
    facts.note_child_created()
    facts.note_evaluator_entry("EVALUATOR_ENTERED")
    facts.note_exact_result(
        result_packet_sha256="b" * 64,
        metadata={
            "planner_calls": 2,
            "primary_judge_calls": 2,
            "adversarial_judge_calls": 2,
            "total_broker_calls": 6,
            "observed_cost_usd": "0.64",
        },
    )

    packet = facts.to_packet()

    attestation.validate_stop_attestation_packet(packet)
    assert packet["result_packet_created"] is True
    assert packet["manifest_consumption_posture"] == "EXACT"
    assert packet["cost_posture"] == "EXACT"
    assert packet["total_broker_calls"] == 6
    assert packet["observed_cost_usd"] == "0.64"
    assert packet["broker_startup_posture"] == "TRUE"


def test_startup_handshake_is_atomic_and_never_overwrites(
    tmp_path: Path,
) -> None:
    root = tmp_path
    output_packet_path = "output/local/result.json"
    path = root / (output_packet_path + ".startup.json")
    path.parent.mkdir(parents=True)

    attestation.write_evaluator_entry_handshake(
        output_packet_path,
        repository_root=root,
    )
    original = path.read_text(encoding="utf-8")

    with pytest.raises(FileExistsError):
        attestation.write_evaluator_entry_handshake(
            output_packet_path,
            repository_root=root,
        )

    assert path.read_text(encoding="utf-8") == original
    packet = attestation.load_evaluator_entry_handshake(
        path,
        repository_root=root,
    )
    assert packet["stage"] == "EVALUATOR_ENTERED"


def test_private_exception_text_is_hashed_but_never_retained() -> None:
    private_sentinel = "fictional-private-exception-sentinel"
    facts = attestation.StopAttestationFacts(
        bounded_failure_code="UNEXPECTED_OPERATOR_EXCEPTION",
        exception_class_code="VALUE_ERROR",
        exception_message_sha256=attestation.exception_message_sha256(ValueError(private_sentinel)),
    )

    packet = facts.to_packet()

    assert private_sentinel not in str(packet)
    assert packet["exception_message_sha256"] is not None
    assert packet["raw_prompt_retained"] is False
    assert packet["raw_output_retained"] is False
    assert packet["provider_payload_retained"] is False
    assert packet["private_log_retained"] is False
    assert packet["full_trace_retained"] is False


def test_observed_but_unvalidated_result_keeps_metadata_unknown() -> None:
    facts = attestation.StopAttestationFacts(
        repository_sha="a" * 40,
        bounded_failure_code="RESULT_PACKET_VALIDATION_FAILED",
        terminal_status="STOPPED_DURING_RESULT_VALIDATION",
    )
    facts.note_child_created()
    facts.note_evaluator_entry("EVALUATOR_ENTERED")
    facts.note_result_packet_observed()

    packet = facts.to_packet()

    attestation.validate_stop_attestation_packet(packet)
    assert packet["result_packet_created"] is True
    assert packet["result_packet_sha256"] is None
    assert packet["manifest_consumption_posture"] == ("UNKNOWN_AFTER_EVALUATOR_ENTRY")
    assert packet["cost_posture"] == "UNKNOWN_AFTER_EVALUATOR_ENTRY"
    assert packet["total_broker_calls"] is None
    assert packet["observed_cost_usd"] is None


def test_final_stop_attestation_is_atomic_and_never_overwrites(
    tmp_path: Path,
) -> None:
    root = tmp_path
    path = root / "output" / "local" / "final.json"
    path.parent.mkdir(parents=True)
    facts = attestation.StopAttestationFacts(
        repository_sha="a" * 40,
        bounded_failure_code="CANONICAL_COMMAND_DECODE_FAILED",
        exception_class_code="JSON_DECODE_ERROR",
        exception_message_sha256="c" * 64,
    )

    first = attestation.write_stop_attestation(
        path,
        repository_root=root,
        facts=facts,
    )
    original = path.read_text(encoding="utf-8")

    with pytest.raises(FileExistsError):
        attestation.write_stop_attestation(
            path,
            repository_root=root,
            facts=facts,
        )

    assert path.read_text(encoding="utf-8") == original
    assert first["attestation_sha256"] in original


def test_schema_rejects_impossible_child_and_exact_result_combinations() -> None:
    childless = attestation.StopAttestationFacts().to_packet()
    childless["child_exit_code"] = 1
    childless_body = dict(childless)
    del childless_body["attestation_sha256"]
    childless["attestation_sha256"] = attestation.canonical_sha256(childless_body)

    with pytest.raises(attestation.OwnerExecutionStopAttestationError):
        attestation.validate_stop_attestation_packet(childless)

    no_result = attestation.StopAttestationFacts()
    no_result.note_child_created()
    no_result.note_evaluator_entry("EVALUATOR_ENTERED")
    no_result_packet = no_result.to_packet()
    no_result_packet["manifest_consumption_posture"] = "EXACT"
    no_result_packet["cost_posture"] = "EXACT"
    no_result_packet["planner_calls"] = 0
    no_result_packet["primary_judge_calls"] = 0
    no_result_packet["adversarial_judge_calls"] = 0
    no_result_packet["total_broker_calls"] = 0
    no_result_packet["observed_cost_usd"] = "0"
    no_result_body = dict(no_result_packet)
    del no_result_body["attestation_sha256"]
    no_result_packet["attestation_sha256"] = attestation.canonical_sha256(no_result_body)

    with pytest.raises(attestation.OwnerExecutionStopAttestationError):
        attestation.validate_stop_attestation_packet(no_result_packet)
