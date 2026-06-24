"""AG-SEM-12C1 FAP semantic/evidence authority manifest tests."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

from core.author_execution_runtime import execute_author_action
from core.final_answer_packet import (
    FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION,
    FINAL_ANSWER_SEMANTIC_EVIDENCE_AUTHORITY_MANIFEST_SCHEMA_VERSION,
    CitationEligibilityRecord,
    CitationEligibilityStatus,
    CitationRequirementStatus,
    EvidenceAuthorityStatus,
    FinalAnswerPacket,
    FinalEvidenceRecord,
    SourceObligationRecord,
    SourceObligationStatus,
    _safe_json,
)
from core.final_answer_packet_runtime import execute_final_answer_packet_prepare_action
from core.final_answer_runtime_adapter import build_final_answer_packet, derive_author_input_payload
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    SufficiencyPosture,
)
from core.run_kernel import ActionType, RunKernel

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "core" / "final_answer_packet.py"
ADAPTER = ROOT / "core" / "final_answer_runtime_adapter.py"
PACKET_RUNTIME = ROOT / "core" / "final_answer_packet_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"
AUTHOR_RUNTIME = ROOT / "core" / "author_execution_runtime.py"

SEMANTIC_DIGEST = "d" * 64
SEMANTIC_SCHEMA = "sufficiency_semantic_state_consumption_ag_sem_09_v1"


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


def _semantic_ref(**overrides: Any) -> dict[str, Any]:
    ref = {
        "schema_version": FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION,
        "available": True,
        "sufficiency_semantic_consumed": True,
        "authority_owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "semantic_state_facts_digest": SEMANTIC_DIGEST,
        "semantic_summary_schema_version": SEMANTIC_SCHEMA,
        "required_component_count": 2,
        "covered_component_count": 1,
        "missing_component_count": 1,
    }
    ref.update(overrides)
    return ref


def _manual_packet(*, semantic_authority_ref: dict[str, Any] | None = None) -> FinalAnswerPacket:
    return FinalAnswerPacket(
        packet_id="ag-sem-12c1-manual",
        semantic_authority_ref=(
            _semantic_ref()
            if semantic_authority_ref is None
            else semantic_authority_ref
        ),
        evidence_records=(
            FinalEvidenceRecord(
                evidence_id="ev-allowed-1",
                status=EvidenceAuthorityStatus.EVIDENCE_ALLOWED,
                source_id=101,
                url="https://example.gov/current-rule",
            ),
            FinalEvidenceRecord(
                evidence_id="ev-allowed-2",
                status=EvidenceAuthorityStatus.EVIDENCE_ALLOWED,
                source_id=102,
                url="https://example.gov/current-rule-2",
            ),
            FinalEvidenceRecord(
                evidence_id="ev-excluded",
                status=EvidenceAuthorityStatus.EVIDENCE_EXCLUDED,
                source_id=201,
                url="https://example.gov/excluded",
                reason="not_selected_for_final_answer",
            ),
        ),
        citation_records=(
            CitationEligibilityRecord(
                citation_id="cit-1",
                evidence_id="ev-allowed-1",
                status=CitationEligibilityStatus.CITATION_ELIGIBLE,
                requirement=CitationRequirementStatus.CITATION_REQUIRED,
                source_id=101,
            ),
            CitationEligibilityRecord(
                citation_id="cit-2",
                evidence_id="ev-allowed-2",
                status=CitationEligibilityStatus.CITATION_ELIGIBLE,
                requirement=CitationRequirementStatus.CITATION_OPTIONAL,
                source_id=102,
            ),
            CitationEligibilityRecord(
                citation_id="cit-ineligible",
                evidence_id="ev-excluded",
                status=CitationEligibilityStatus.CITATION_INELIGIBLE,
                requirement=CitationRequirementStatus.CITATION_OPTIONAL,
                source_id=201,
                reason="excluded_evidence",
            ),
        ),
        source_obligations=(
            SourceObligationRecord(
                obligation_id="obl-satisfied",
                source_class="official_current_rules",
                status=SourceObligationStatus.SATISFIED,
            ),
            SourceObligationRecord(
                obligation_id="obl-missing",
                source_class="regulatory_text",
                status=SourceObligationStatus.MISSING_REQUIRED_SOURCE,
            ),
        ),
    )


def _semantic_sufficiency_projection() -> dict[str, Any]:
    return RunSufficiencyJudgment(
        judgment_id="ag-sem-12c1:judgment",
        decision=RunSufficiencyDecision.READY_DIRECT,
        final_answer_posture=SufficiencyPosture.DIRECT_ANSWER,
        final_answer_allowed=True,
        semantic_consumption={
            "schema_version": SEMANTIC_SCHEMA,
            "semantic_state_facts_digest": SEMANTIC_DIGEST,
            "blocker_count": 0,
            "blocker_codes": [],
            "direct_answer_blocked": False,
            "finalization_blocked": False,
            "required_component_count": 1,
            "covered_component_count": 1,
        },
    ).to_projection()


def _expected_digest(value: Any) -> str:
    return sha256(
        json.dumps(
            _safe_json(value),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _prepare_packet_runtime_result():
    kernel = RunKernel.start(run_id="ag-sem-12c1-runtime", request_id="req")
    action = kernel.authorize_final_answer_packet_prepare(inputs={"candidate_count": 1})
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
        final_top_evidence=[_passage()],
        author_evidence=[_passage()],
        ordered_sources=["- [101] [Current rule](https://example.gov/current-rule)"],
        unique_source_urls={"https://example.gov/current-rule": 101},
        query_lineage_refs={},
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
        sufficiency_judgment_projection=_semantic_sufficiency_projection(),
    )
    return kernel, action, result


def test_manifest_schema_direct_packet_projection() -> None:
    packet = _manual_packet()

    manifest = packet.semantic_evidence_authority_manifest

    assert manifest["schema_version"] == (
        FINAL_ANSWER_SEMANTIC_EVIDENCE_AUTHORITY_MANIFEST_SCHEMA_VERSION
    )
    assert manifest["available"] is True
    assert manifest["source_packet_id"] == packet.packet_id
    assert manifest["source_packet_schema_version"] == packet.schema_version
    assert manifest["semantic_authority_ref_schema_version"] == (
        FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION
    )
    assert manifest["semantic_authority_ref_digest"] == _expected_digest(
        packet.semantic_authority_ref
    )
    assert manifest["semantic_state_facts_digest"] == SEMANTIC_DIGEST
    assert manifest["required_component_count"] == 2
    assert manifest["covered_component_count"] == 1
    assert manifest["missing_component_count"] == 1
    assert manifest["evidence_ids"] == ["ev-allowed-1", "ev-allowed-2"]
    assert manifest["excluded_evidence_ids"] == ["ev-excluded"]
    assert manifest["citation_source_ids"] == [101, 102]
    assert manifest["source_obligation_status_summary"] == {
        "source_obligation_satisfied": 1,
        "source_obligation_partial": 0,
        "missing_required_source": 1,
        "official_current_unsatisfied": 0,
        "source_bound_value_missing": 0,
        "source_obligation_state_unavailable": 0,
    }
    assert manifest["content_refs_available"] is False
    assert manifest["coverage_refs_available"] is False
    assert manifest["deferred_ref_fields"] == [
        "sanitized_content_ref_ids",
        "content_ref_digests",
        "coverage_record_ids",
        "coverage_record_digests",
    ]
    assert "sanitized_content_ref_ids" not in manifest
    assert "content_ref_digests" not in manifest
    assert "coverage_record_ids" not in manifest
    assert "coverage_record_digests" not in manifest
    assert packet.to_dict()["semantic_evidence_authority_manifest"] == manifest
    assert packet.to_trace_fragment()["final_answer_packet"][
        "semantic_evidence_authority_manifest"
    ] == manifest


def test_manifest_empty_when_semantic_authority_ref_empty() -> None:
    packet = _manual_packet(semantic_authority_ref={})

    assert packet.semantic_authority_ref == {}
    assert packet.semantic_evidence_authority_manifest == {}
    assert "semantic_evidence_authority_manifest" not in packet.to_dict()


def test_manifest_omits_unavailable_component_counts() -> None:
    packet = _manual_packet(
        semantic_authority_ref=_semantic_ref(
            required_component_count=None,
            covered_component_count="",
            missing_component_count=[],
        )
    )

    manifest = packet.semantic_evidence_authority_manifest

    assert "required_component_count" not in manifest
    assert "covered_component_count" not in manifest
    assert "missing_component_count" not in manifest


def test_manifest_propagates_through_existing_packet_runtime_and_run_kernel() -> None:
    kernel, action, result = _prepare_packet_runtime_result()

    assert action.action_type is ActionType.FINAL_ANSWER_PACKET_PREPARE
    manifest = result.packet.semantic_evidence_authority_manifest
    assert manifest
    assert result.observation.payload["packet_projection"][
        "semantic_evidence_authority_manifest"
    ] == manifest
    assert "semantic_evidence_authority_manifest" not in PACKET_RUNTIME.read_text(
        encoding="utf-8"
    )

    kernel.reduce(result.observation)

    assert kernel.state.final_answer_packet[
        "semantic_evidence_authority_manifest"
    ] == manifest
    assert "semantic_evidence_authority_manifest" not in RUN_KERNEL.read_text(
        encoding="utf-8"
    )


def test_manifest_does_not_change_author_payload_prompt_or_execution_surfaces() -> None:
    packet = build_final_answer_packet(
        run_id="ag-sem-12c1-nondelta",
        final_evidence=[_passage(source_id=101)],
        author_evidence=[_passage(source_id=101)],
        sufficiency_judgment_projection=_semantic_sufficiency_projection(),
    )
    assert packet.semantic_evidence_authority_manifest
    packet_without_manifest = replace(packet, semantic_authority_ref={})

    with_packet, with_payload = derive_author_input_payload(
        packet,
        prompt="unchanged author prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )
    without_packet, without_payload = derive_author_input_payload(
        packet_without_manifest,
        prompt="unchanged author prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert with_payload.prompt == without_payload.prompt
    assert with_payload.authority_payload == without_payload.authority_payload
    assert with_payload.authority_block == without_payload.authority_block
    assert with_packet.citation_records == without_packet.citation_records
    assert with_packet.source_obligations == without_packet.source_obligations
    assert "semantic_evidence_authority_manifest" not in with_payload.to_trace_ref()
    assert "semantic_evidence_authority_manifest" not in with_payload.prompt
    assert "semantic_evidence_authority_manifest" not in with_payload.authority_payload
    assert "semantic_evidence_authority_manifest" not in (
        with_payload.semantic_authority_trace_ref
    )

    runtime_kernel, _runtime_action, runtime_result = _prepare_packet_runtime_result()
    runtime_kernel.reduce(runtime_result.observation)
    author_action = runtime_kernel.authorize_author_execution(inputs={})
    payload_without_semantic_ref = replace(
        runtime_result.author_payload,
        semantic_authority_trace_ref={},
    )
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_ask_model(*args: Any, **kwargs: Any):
        calls.append((args, kwargs))
        return iter(["RAW MODEL FINAL ANSWER [101]"])

    execute_author_action(
        author_action,
        author_payload=runtime_result.author_payload,
        ask_model=fake_ask_model,
        system_prompt_registry={"author": "AUTHOR SYSTEM"},
        base_url="http://local",
        api_key=None,
        query="ordinary query",
    )
    execute_author_action(
        author_action,
        author_payload=payload_without_semantic_ref,
        ask_model=fake_ask_model,
        system_prompt_registry={"author": "AUTHOR SYSTEM"},
        base_url="http://local",
        api_key=None,
        query="ordinary query",
    )

    assert calls[0] == calls[1]


def test_manifest_raw_leakage_scan() -> None:
    packet = _manual_packet()
    encoded = json.dumps(packet.semantic_evidence_authority_manifest, sort_keys=True)

    for forbidden in (
        "raw_prompt",
        "prompt_text",
        "provider_payload",
        "raw_provider_payload",
        "model_response",
        "raw_model_response",
        "final_prose",
        "final_text",
        "bounded_text",
        "component_summaries",
        "amendment_summaries",
        "db_row",
        "cache",
        "secret",
        "token",
    ):
        assert forbidden not in encoded


def test_static_guard_manifest_not_in_forbidden_author_surfaces() -> None:
    assert "semantic_evidence_authority_manifest" not in AUTHOR_RUNTIME.read_text(
        encoding="utf-8"
    )

    packet_source = PACKET.read_text(encoding="utf-8")
    for region_name, start, end in (
        (
            "to_authority_payload",
            packet_source.index("def to_authority_payload("),
            packet_source.index("def to_author_input_payload("),
        ),
        (
            "to_author_authority_block",
            packet_source.index("def to_author_authority_block("),
            packet_source.index("def to_legacy_citation_handoff_inputs("),
        ),
        (
            "FinalAnswerAuthorInputPayload",
            packet_source.index("class FinalAnswerAuthorInputPayload"),
            packet_source.index("class FinalAnswerPacket"),
        ),
    ):
        region = packet_source[start:end]
        assert "semantic_evidence_authority_manifest" not in region, region_name


def test_static_guard_no_direct_semantic_history_or_af_reads_for_manifest() -> None:
    packet_source = PACKET.read_text(encoding="utf-8")
    manifest_region = packet_source[
        packet_source.index("def semantic_evidence_authority_manifest(") : packet_source.index(
            "def with_author_input_payload("
        )
    ]
    for token in (
        "initial_answer_contract",
        "semantic_observation_admission_history",
        "component_coverage_history",
        "ordinary_semantic_producer",
        "final_top_evidence",
        "author_evidence",
        "followup_author",
        "AF4B2",
        "AF4D",
        "AF5A",
        "AF5B",
    ):
        assert token not in manifest_region

    adapter_source = ADAPTER.read_text(encoding="utf-8")
    assert "semantic_evidence_authority_manifest" not in adapter_source
    for token in (
        "initial_answer_contract",
        "semantic_observation_admission_history",
        "component_coverage_history",
        "ordinary_semantic_producer",
        "followup_author",
        "AF4B2",
        "AF4D",
        "AF5A",
        "AF5B",
    ):
        assert token not in adapter_source


def test_static_guard_no_manifest_provider_search_or_af_imports() -> None:
    for path in (
        ROOT / "core" / "retrieval.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "search_providers.py",
    ):
        assert "semantic_evidence_authority_manifest" not in path.read_text(
            encoding="utf-8"
        )

    for path in (PACKET, ADAPTER):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        for module in imported:
            assert "followup_" not in module
            assert "offline_golden_harness" not in module
