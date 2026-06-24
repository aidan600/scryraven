from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256
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
    _safe_json,
)
from core.final_answer_packet_runtime import execute_final_answer_packet_prepare_action
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    SufficiencyPosture,
)
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
INVOCATION_MANIFEST_SCHEMA_VERSION = (
    "author_invocation_authority_manifest_ag_auth_invoke_01_v1"
)


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


def _semantic_sufficiency_projection() -> dict[str, Any]:
    return RunSufficiencyJudgment(
        judgment_id="ag-sem-12b:judgment",
        decision=RunSufficiencyDecision.READY_DIRECT,
        final_answer_posture=SufficiencyPosture.DIRECT_ANSWER,
        final_answer_allowed=True,
        semantic_consumption={
            "schema_version": "sufficiency_semantic_state_consumption_ag_sem_09_v1",
            "semantic_state_facts_digest": "c" * 64,
            "blocker_count": 0,
            "blocker_codes": [],
            "direct_answer_blocked": False,
            "finalization_blocked": False,
            "required_component_count": 1,
            "covered_component_count": 1,
        },
    ).to_projection()


def _stable_safe_digest(value: Any) -> str:
    return sha256(
        json.dumps(
            _safe_json(value),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _prepare_packet(
    *,
    kernel: RunKernel | None = None,
    final_top_evidence: list[dict[str, Any]] | None = None,
    evidence_ledger_projection: dict[str, Any] | None = None,
    answer_contract_projection: dict[str, Any] | None = None,
    sufficiency_judgment_projection: dict[str, Any] | None = None,
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
        sufficiency_judgment_projection=sufficiency_judgment_projection,
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


def test_ag_sem_12b_packet_prep_runtime_propagates_semantic_trace_ref() -> None:
    kernel, _action, result = _prepare_packet(
        sufficiency_judgment_projection=_semantic_sufficiency_projection(),
    )
    semantic_trace_ref = result.author_payload.semantic_authority_trace_ref

    assert semantic_trace_ref
    assert result.observation.payload["author_payload_ref"][
        "semantic_authority_trace_ref"
    ] == semantic_trace_ref
    assert result.observation.payload["packet_projection"]["semantic_authority_ref"] == (
        result.packet.semantic_authority_ref
    )
    assert "semantic_authority_trace_ref" not in PACKET_RUNTIME.read_text(
        encoding="utf-8"
    )

    kernel.reduce(result.observation)

    assert kernel.state.final_answer_authority_projection["author_payload_ref"][
        "semantic_authority_trace_ref"
    ] == semantic_trace_ref
    assert "semantic_authority_trace_ref" not in RUN_KERNEL.read_text(encoding="utf-8")


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
    expected_digest = _stable_safe_digest(prepared.author_payload.to_trace_ref())
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

    assert len(calls) == 1
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
    assert action.inputs["expected_author_payload_ref_digest"] == expected_digest
    assert action.inputs["packet_id"] == prepared.packet.packet_id
    serialized_action_inputs = json.dumps(action.inputs, sort_keys=True)
    assert "BASE AUTHOR PROMPT" not in serialized_action_inputs
    assert "AUTHOR SYSTEM" not in serialized_action_inputs

    manifest = result.observation.payload["author_invocation_authority_manifest"]
    assert manifest["schema_version"] == INVOCATION_MANIFEST_SCHEMA_VERSION
    assert manifest["available"] is True
    assert manifest["packet_id"] == prepared.packet.packet_id
    assert manifest["author_payload_ref_digest"] == expected_digest
    assert manifest["expected_author_payload_ref_digest"] == expected_digest
    assert manifest["prompt_hash"] == result.observation.payload["prompt_hash"]
    assert manifest["prompt_length"] == len(prepared.author_payload.prompt)
    assert manifest["system_prompt_hash"] == result.observation.payload["system_prompt_hash"]
    assert manifest["system_prompt_length"] == len("AUTHOR SYSTEM")
    assert manifest["authority_block_hash"] == result.observation.payload[
        "authority_block_hash"
    ]
    assert manifest["authority_block_length"] == len(
        prepared.author_payload.authority_block
    )
    assert manifest["author_provider"] == "fast-provider"
    assert manifest["author_model"] == "fast-model"
    assert manifest["author_effort"] == "medium"
    assert manifest["semantic_materialization_available"] is False
    assert manifest["semantic_materialization_digest"] is None
    assert manifest["semantic_materialization_block_hash"] is None
    assert manifest["semantic_materialization_block_length"] == 0
    assert manifest["semantic_materialization_component_count"] == 0
    assert manifest["semantic_materialization_excerpt_count"] == 0
    assert manifest["prompt_visible"] is False
    assert manifest["model_request_visible"] is False
    assert manifest["prompt_text_included"] is False
    assert manifest["system_prompt_text_included"] is False
    assert manifest["model_request_raw_payload_retained"] is False
    assert manifest["provider_payload_retained"] is False
    assert manifest["raw_prompt_included"] is False
    assert manifest["raw_content_included"] is False
    assert manifest["bounded_text_included"] is False
    assert manifest["bounded_text_retained"] is False
    assert manifest["final_text_included"] is False
    serialized_manifest = json.dumps(manifest, sort_keys=True)
    assert "BASE AUTHOR PROMPT" not in serialized_manifest
    assert "AUTHOR SYSTEM" not in serialized_manifest
    assert "RAW MODEL FINAL ANSWER" not in serialized_manifest
    raw_leakage_scan = json.dumps(
        [
            action.inputs,
            prepared.author_payload.to_trace_ref(),
            result.observation.payload,
            manifest,
        ],
        sort_keys=True,
    )
    for forbidden in (
        "BASE AUTHOR PROMPT",
        "FINAL ANSWER PACKET AUTHORITY",
        "AUTHOR SYSTEM",
        "RAW MODEL FINAL ANSWER",
        "Official current rule excerpt.",
        "SENTINEL_RAW_PROMPT",
        "SENTINEL_SYSTEM_PROMPT",
        "SENTINEL_PROVIDER_PAYLOAD",
        "SENTINEL_RAW_PROVIDER_PAYLOAD",
        "SENTINEL_RAW_CONTENT",
        "SENTINEL_BOUNDED_TEXT",
        "SENTINEL_FINAL_TEXT",
        "SENTINEL_MODEL_RESPONSE",
        "SENTINEL_DB_ROW",
        "SENTINEL_CACHE_ROW",
        "SENTINEL_FULL_TRACE",
        "SENTINEL_SECRET_TOKEN",
    ):
        assert forbidden not in raw_leakage_scan

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


def test_ag_sem_12b_author_execution_accountability_preserves_model_request() -> None:
    kernel, _packet_action, prepared = _prepare_packet(
        sufficiency_judgment_projection=_semantic_sufficiency_projection(),
    )
    assert prepared.author_payload.semantic_authority_trace_ref
    kernel.reduce(prepared.observation)
    action = kernel.authorize_author_execution(inputs={})
    expected_digest = _stable_safe_digest(prepared.author_payload.to_trace_ref())
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_ask_model(*args: Any, **kwargs: Any):
        calls.append((args, kwargs))
        return iter(["RAW MODEL FINAL ANSWER [101]"])

    result = execute_author_action(
        action,
        author_payload=prepared.author_payload,
        ask_model=fake_ask_model,
        system_prompt_registry={"author": "AUTHOR SYSTEM"},
        base_url="http://local",
        api_key=None,
        query="ordinary query",
    )

    assert len(calls) == 1
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
    assert "semantic_authority_trace_ref" not in action.inputs
    assert action.inputs["expected_author_payload_ref_digest"] == expected_digest
    assert "semantic_authority_trace_ref" not in result.observation.payload
    manifest = result.observation.payload["author_invocation_authority_manifest"]
    assert manifest["author_payload_ref_digest"] == expected_digest
    assert manifest["expected_author_payload_ref_digest"] == expected_digest
    assert manifest["semantic_authority_trace_ref_digest"] == _stable_safe_digest(
        prepared.author_payload.semantic_authority_trace_ref
    )
    assert manifest["semantic_packet_evidence_binding_available"] is False
    assert manifest["semantic_materialization_available"] is False
    assert manifest["prompt_visible"] is False
    assert manifest["model_request_visible"] is False


def test_author_execution_rejects_tampered_semantic_payload_before_model() -> None:
    kernel, _packet_action, prepared = _prepare_packet(
        sufficiency_judgment_projection=_semantic_sufficiency_projection(),
    )
    kernel.reduce(prepared.observation)
    action = kernel.authorize_author_execution(inputs={})
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_ask_model(*args: Any, **kwargs: Any):
        calls.append((args, kwargs))
        return iter(["unreachable"])

    tampered_payload = replace(
        prepared.author_payload,
        semantic_authority_trace_ref={
            **dict(prepared.author_payload.semantic_authority_trace_ref),
            "semantic_state_facts_digest": "9" * 64,
        },
    )

    with pytest.raises(ValueError, match="payload ref digest"):
        execute_author_action(
            action,
            author_payload=tampered_payload,
            ask_model=fake_ask_model,
            system_prompt_registry={"author": "AUTHOR SYSTEM"},
            base_url="http://local",
            api_key=None,
            query="ordinary query",
        )

    assert calls == []


def test_author_execution_rejects_mismatched_expected_digest_before_model() -> None:
    kernel, _packet_action, prepared = _prepare_packet()
    kernel.reduce(prepared.observation)
    action = kernel.authorize_author_execution(inputs={})
    mismatched_action = replace(
        action,
        inputs={**dict(action.inputs), "expected_author_payload_ref_digest": "0" * 64},
    )
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_ask_model(*args: Any, **kwargs: Any):
        calls.append((args, kwargs))
        return iter(["unreachable"])

    with pytest.raises(ValueError, match="payload ref digest"):
        execute_author_action(
            mismatched_action,
            author_payload=prepared.author_payload,
            ask_model=fake_ask_model,
            system_prompt_registry={"author": "AUTHOR SYSTEM"},
            base_url="http://local",
            api_key=None,
            query="ordinary query",
        )

    assert calls == []


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

    assert "prepare_final_answer_packet_author_handoff_from_scope(" in pipeline
    assert "run_kernel.authorize_final_answer_packet_prepare(" in packet_runtime
    assert "run_kernel.reduce(preparation.observation)" in packet_runtime
    assert "execute_author_handoff_from_scope(" in pipeline
    assert "run_kernel.authorize_author_execution(" in author_runtime
    assert "run_kernel.reduce(execution.observation)" in author_runtime
    assert "ask_model(\n        author_prompt, _author_system," not in pipeline
    assert "select_author_system_prompt(" not in pipeline
    assert "_post_analyst_author_system_prompt_key" in pipeline

    author_region = pipeline[
        pipeline.index("final_answer_packet_handoff =")
        : pipeline.index("authority_citation_survival =")
    ]
    assert "ask_model(" not in author_region
    assert "if strategy in (\"Fast\", \"Balanced\")" not in author_region
    assert "_author_chunks" not in author_region

    assert "_final_answer_packet_trace_fragment_from_state" in session_output
    assert "run_kernel_final_answer_ref" in (
        ROOT / "core" / "final_answer_runtime_assembly.py"
    ).read_text()
