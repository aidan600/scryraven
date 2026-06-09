from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import core.post_author_output_projection as post_author_projection
from core.author_execution_runtime import execute_author_action
from core.evidence_ledger import EvidenceLedger
from core.final_answer_packet import (
    EvidenceAuthorityStatus,
    FinalAnswerPacket,
    FinalAnswerReadinessStatus,
    FinalEvidenceRecord,
)
from core.final_answer_packet_runtime import execute_final_answer_packet_prepare_action
from core.run_kernel import (
    AUTHOR_EXECUTION_STAGE,
    FINAL_ANSWER_PACKET_STAGE,
    ActionType,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"
PACKET_RUNTIME = ROOT / "core" / "final_answer_packet_runtime.py"
AUTHOR_RUNTIME = ROOT / "core" / "author_execution_runtime.py"
SESSION_OUTPUT = ROOT / "core" / "session_output_projection.py"


def _official_requirement() -> dict[str, Any]:
    return {
        "requirement_id": "official_current_source:official_current_rules",
        "requirement_kind": "official_current",
        "required_source_class": "official_current_rules",
        "required_source_tier": "official",
        "required_currentness": "current",
    }


def _passage(**overrides: Any) -> dict[str, Any]:
    passage = {
        "source_id": 101,
        "url": "https://example.gov/current-rule",
        "title": "Current rule",
        "text": "Official current rule excerpt.",
        "source_tier": "official",
        "source_class": "official_current_rules",
    }
    passage.update(overrides)
    return passage


def _ledger_projection_with_gap() -> dict[str, Any]:
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        {
            "observation_id": "obs-ag91k",
            "observation_source": "final_evidence_bundle",
            "requirements": [_official_requirement()],
            "final_evidence": [_passage()],
        }
    )
    return ledger.to_projection().to_dict()


def _prepare_packet(
    *,
    kernel: RunKernel | None = None,
    final_top_evidence: list[dict[str, Any]] | None = None,
    evidence_ledger_projection: dict[str, Any] | None = None,
    answer_contract_projection: dict[str, Any] | None = None,
):
    kernel = kernel or RunKernel.start(run_id="ag91k", request_id="req-ag91k")
    final_top_evidence = final_top_evidence if final_top_evidence is not None else [_passage()]
    action = kernel.authorize_final_answer_packet_prepare(
        inputs={"candidate_count": len(final_top_evidence)}
    )
    result = execute_final_answer_packet_prepare_action(
        action,
        run_id=kernel.state.run_id,
        query="What is the current official rule?",
        intent="research",
        report_type="general",
        query_type="general",
        core_topic="current official rule",
        primary_entity="Example Agency",
        anchor_packet_telemetry={},
        final_top_evidence=final_top_evidence,
        author_evidence=final_top_evidence[:1],
        ordered_sources=["- [101] [Current rule](https://example.gov/current-rule)"],
        unique_source_urls={"https://example.gov/current-rule": 101},
        query_lineage_refs={"query_plan": {"plan_id": "qp-ag91k"}},
        corpus_weak=False,
        failure_card_payload={"show": False, "reason": None},
        conflicts_present=False,
        synth_was_insufficient=False,
        author_notes="",
        author_prompt="BASE AUTHOR PROMPT",
        default_system={"author": "AUTHOR SYSTEM"},
        analyst_effort="medium",
        estimate_from_priors_author=False,
        relevance_low=False,
        strategy="Balanced",
        fast_provider="fast-provider",
        fast_model="fast-model",
        smart_provider="smart-provider",
        smart_model="smart-model",
        evidence_ledger_projection=evidence_ledger_projection,
        answer_contract_projection=answer_contract_projection,
    )
    return kernel, action, result


def test_run_kernel_authorizes_and_reduces_final_answer_packet_preparation() -> None:
    kernel, action, result = _prepare_packet(
        evidence_ledger_projection=_ledger_projection_with_gap(),
        answer_contract_projection={"unfulfilled_source_classes": ["legal_or_regulatory_text"]},
    )

    assert action.action_type is ActionType.FINAL_ANSWER_PACKET_PREPARE
    assert action.stage == FINAL_ANSWER_PACKET_STAGE
    assert action.expected_observation_type is ObservationType.FINAL_ANSWER_PACKET_PREPARED
    assert result.observation.observation_type is ObservationType.FINAL_ANSWER_PACKET_PREPARED
    assert result.packet.official_current_custody_summary["custody_authority"] == (
        "RunKernel.EvidenceLedger"
    )
    assert result.packet.official_current_custody_summary[
        "final_evidence_compatibility_gap_count"
    ] == 1
    assert "official_current_unsatisfied:official_current_rules" in result.packet.mandatory_caveats
    assert "missing_required_source:legal_or_regulatory_text" in result.packet.mandatory_caveats
    assert "do_not_treat_uncustodied_final_evidence_as_ledger_proof" in (
        result.packet.prohibited_upgrades
    )
    assert result.author_payload.author_provider == "fast-provider"
    assert result.author_payload.author_model == "fast-model"
    assert "FINAL ANSWER PACKET AUTHORITY" in result.author_payload.prompt
    assert "official_current_unsatisfied" in result.author_payload.prompt
    assert "legal_or_regulatory_text" in result.author_payload.prompt

    kernel.reduce(result.observation)

    assert kernel.state.final_answer_packet["packet_id"] == result.packet.packet_id
    assert kernel.state.final_answer_packet["readiness_status"] == (
        FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED.value
    )
    projection = kernel.state.final_answer_authority_projection
    assert projection["owner"] == "RunKernel.FinalAnswerPacket"
    assert projection["canonical_state"] is True
    assert projection["author_payload_ref"]["packet_id"] == result.packet.packet_id
    assert projection["author_payload_ref"]["prompt_text_included"] is False
    assert projection["author_payload_ref"]["author_provider"] == "fast-provider"
    assert projection["missing_source_obligation_count"] == 2
    assert kernel.state.projections[FINAL_ANSWER_PACKET_STAGE] == projection

    serialized = json.dumps(kernel.to_trace_fragment(), sort_keys=True)
    assert "BASE AUTHOR PROMPT" not in serialized
    assert "AUTHOR SYSTEM" not in serialized


def test_run_kernel_refuses_author_execution_before_packet_readiness() -> None:
    kernel = RunKernel.start(run_id="ag91k-block", request_id="req")

    with pytest.raises(RunKernelTransitionError, match="FinalAnswerPacket"):
        kernel.authorize_author_execution()

    wrong_action = kernel.authorize_final_answer_packet_prepare(inputs={})
    _, _, prepared = _prepare_packet(kernel=kernel)
    with pytest.raises(ValueError, match="authorized action type"):
        execute_author_action(
            wrong_action,
            author_payload=prepared.author_payload,
            ask_model=lambda *_args, **_kwargs: "unused",
            system_prompt_registry={"author": "AUTHOR SYSTEM"},
            base_url=None,
            api_key=None,
            query="q",
        )


def test_author_executor_consumes_packet_payload_and_reduces_author_observation() -> None:
    kernel, _packet_action, prepared = _prepare_packet()
    kernel.reduce(prepared.observation)
    action = kernel.authorize_author_execution(inputs={})
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    displayed: list[str] = []

    def fake_ask_model(*args: Any, **kwargs: Any):
        calls.append((args, kwargs))
        return iter(["RAW MODEL FINAL ", "ANSWER [101]"])

    def fake_display(chunks):
        displayed.extend(list(chunks))

    result = execute_author_action(
        action,
        author_payload=prepared.author_payload,
        ask_model=fake_ask_model,
        system_prompt_registry={"author": "AUTHOR SYSTEM"},
        base_url="http://local",
        api_key=None,
        query="ordinary query",
        stream_display=fake_display,
    )

    assert calls[0][0] == (prepared.author_payload.prompt, "AUTHOR SYSTEM")
    assert calls[0][1] == {
        "provider": "fast-provider",
        "model": "fast-model",
        "effort": "medium",
        "base_url": "http://local",
        "api_key": None,
        "stream": True,
        "use_reasoning": False,
    }
    assert "FINAL ANSWER PACKET AUTHORITY" in calls[0][0][0]
    assert displayed == ["RAW MODEL FINAL ", "ANSWER [101]"]
    assert result.report == "RAW MODEL FINAL ANSWER [101]"
    assert result.observation.observation_type is ObservationType.AUTHOR_OUTPUT_OBSERVED

    kernel.reduce(result.observation)

    assert kernel.state.author_observation["packet_id"] == prepared.packet.packet_id
    assert kernel.state.final_answer_outcome["owner"] == "RunKernel.AuthorObservation"
    assert kernel.state.final_answer_outcome["final_text_included"] is False
    assert kernel.state.final_answer_outcome["report_hash"]
    assert kernel.state.projections[AUTHOR_EXECUTION_STAGE]["packet_id"] == (
        prepared.packet.packet_id
    )
    serialized = json.dumps(kernel.to_trace_fragment(), sort_keys=True)
    assert "RAW MODEL FINAL ANSWER" not in serialized
    assert "BASE AUTHOR PROMPT" not in serialized


def test_packet_blocks_missing_citation_authority_and_blocked_readiness() -> None:
    packet_without_citation_authority = FinalAnswerPacket(
        packet_id="manual-missing-citations",
        evidence_records=(
            FinalEvidenceRecord(
                evidence_id="e1",
                status=EvidenceAuthorityStatus.EVIDENCE_ALLOWED,
                source_id=1,
                url="https://example.test",
            ),
        ),
        citation_records=(),
    )

    with pytest.raises(ValueError, match="citation eligibility"):
        packet_without_citation_authority.to_author_input_payload(
            prompt="prompt",
            author_system_prompt_key="author",
            author_effort="low",
        )

    blocked = FinalAnswerPacket(
        packet_id="manual-blocked",
        readiness_status=FinalAnswerReadinessStatus.BLOCKED,
        readiness_reasons=("citation_authority_unavailable",),
    )
    with pytest.raises(ValueError, match="blocked FinalAnswerPacket"):
        blocked.to_author_input_payload(
            prompt="prompt",
            author_system_prompt_key="author",
            author_effort="low",
        )


def test_citation_ineligible_evidence_is_not_passed_as_author_citable() -> None:
    _kernel, _action, result = _prepare_packet(
        final_top_evidence=[_passage(source_id=None, url="https://example.gov/no-id")]
    )

    assert result.author_payload.citation_source_ids == ()
    assert result.author_payload.citation_ineligible_refs[0]["reason"] == (
        "source_id_missing"
    )
    assert "Do not cite citation-ineligible evidence" in result.author_payload.prompt
    assert "source_id_missing" in result.author_payload.prompt


def test_post_author_projection_consumes_runkernel_final_answer_state() -> None:
    kernel, _packet_action, prepared = _prepare_packet()
    kernel.reduce(prepared.observation)

    ref = post_author_projection._run_kernel_final_answer_ref(kernel, prepared.packet)

    assert ref == {
        "source": "RunKernel.final_answer_packet",
        "canonical_state": True,
        "packet_id": prepared.packet.packet_id,
        "readiness_status": "author_ready",
        "author_payload_status": "author_input_ready",
        "citation_eligible_source_ids": [101],
        "trace_only": False,
        "storage_only": False,
    }

    divergent = FinalAnswerPacket(packet_id="other-packet")
    with pytest.raises(ValueError, match="diverges from RunKernel"):
        post_author_projection._run_kernel_final_answer_ref(kernel, divergent)


def test_static_guards_for_ag91k_final_answer_authority_migration() -> None:
    pipeline = PIPELINE.read_text()
    run_kernel = RUN_KERNEL.read_text()
    packet_runtime = PACKET_RUNTIME.read_text()
    author_runtime = AUTHOR_RUNTIME.read_text()
    session_output = SESSION_OUTPUT.read_text()

    assert "FINAL_ANSWER_PACKET_STAGE" in run_kernel
    assert "AUTHOR_EXECUTION_STAGE" in run_kernel
    assert "FINAL_ANSWER_PACKET_PREPARE" in run_kernel
    assert "AUTHOR_EXECUTE" in run_kernel
    assert "final_answer_packet: dict[str, Any]" in run_kernel
    assert "author_observation: dict[str, Any]" in run_kernel
    assert "final_answer_outcome: dict[str, Any]" in run_kernel

    assert "ActionType.FINAL_ANSWER_PACKET_PREPARE" in packet_runtime
    assert "ObservationType.FINAL_ANSWER_PACKET_PREPARED" in packet_runtime
    assert "assemble_final_answer_author_runtime(" in packet_runtime
    assert "ActionType.AUTHOR_EXECUTE" in author_runtime
    assert "ObservationType.AUTHOR_OUTPUT_OBSERVED" in author_runtime
    assert "ask_model(" in author_runtime
    assert "author_payload.prompt" in author_runtime

    assert "run_kernel.authorize_final_answer_packet_prepare(" in pipeline
    assert "execute_final_answer_packet_prepare_action_from_scope(" in pipeline
    assert "run_kernel.reduce(final_answer_author_runtime.observation)" in pipeline
    assert "run_kernel.authorize_author_execution(" in pipeline
    assert "execute_author_action(" in pipeline
    assert "run_kernel.reduce(author_execution.observation)" in pipeline
    assert "ask_model(\n        author_prompt, _author_system," not in pipeline
    assert "select_author_system_prompt(" not in pipeline
    assert "_post_analyst_author_system_prompt_key" in pipeline

    author_region = pipeline[
        pipeline.index("final_answer_packet_action =")
        : pipeline.index("final_answer_source_telemetry =")
    ]
    assert "ask_model(" not in author_region
    assert "if strategy in (\"Fast\", \"Balanced\")" not in author_region
    assert "_author_chunks" not in author_region

    assert "_final_answer_packet_trace_fragment_from_state" in session_output
    assert "run_kernel_final_answer_ref" in (
        ROOT / "core" / "final_answer_runtime_assembly.py"
    ).read_text()
