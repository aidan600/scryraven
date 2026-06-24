"""AG-SEM-12C2 Author payload FAP manifest trace-ref tests."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

from core.author_execution_runtime import execute_author_action
from core.final_answer_packet import (
    FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_EVIDENCE_MANIFEST_REF_SCHEMA_VERSION,
    FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION,
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
from core.final_answer_runtime_adapter import (
    build_final_answer_packet,
    derive_author_input_payload,
)
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

SEMANTIC_DIGEST = "e" * 64
SEMANTIC_SCHEMA = "sufficiency_semantic_state_consumption_ag_sem_09_v1"
TRACE_REF_KEY = "semantic_evidence_authority_manifest_trace_ref"

FORBIDDEN_TRACE_REF_KEYS = (
    "semantic_evidence_authority_manifest",
    "evidence_ids",
    "excluded_evidence_ids",
    "citation_source_ids",
    "source_obligation_status_summary",
    "deferred_ref_fields",
    "semantic_content_coverage_ref_projection",
    "sanitized_content_ref_ids",
    "content_ref_digests",
    "coverage_record_ids",
    "coverage_record_digests",
    "coverage_record_refs",
    "semantic_observation_refs",
    "component_refs",
    "semantic_ref_evidence_ids",
    "source_obligation_refs",
    "raw_source_text",
    "bounded_text",
    "component_summaries",
    "amendment_summaries",
    "prompt_text",
    "provider_payload",
    "model_response",
    "final_prose",
    "db_row",
    "cache",
    "secret",
    "token",
)

FORBIDDEN_TRACE_REF_VALUE_TOKENS = (
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
    "evidence_ids",
    "citation_source_ids",
    "source_obligation_status_summary",
    "semantic_content_coverage_ref_projection",
    "sanitized_content_ref_ids",
    "coverage_record_ids",
    "coverage_record_refs",
    "semantic_observation_refs",
    "component_refs",
    "semantic_ref_evidence_ids",
    "source_obligation_refs",
)


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


def _manual_packet(
    *,
    semantic_authority_ref: dict[str, Any] | None = None,
    semantic_content_coverage_ref_projection: dict[str, Any] | None = None,
) -> FinalAnswerPacket:
    return FinalAnswerPacket(
        packet_id="ag-sem-12c2-manual",
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
        semantic_content_coverage_ref_projection=(
            semantic_content_coverage_ref_projection or {}
        ),
    )


def _semantic_content_coverage_ref_projection() -> dict[str, Any]:
    return {
        "schema_version": (
            FINAL_ANSWER_PACKET_SEMANTIC_CONTENT_COVERAGE_REF_PROJECTION_SCHEMA_VERSION
        ),
        "available": True,
        "source_authority": "RunAuthoritySufficiency.semantic_ref_projection",
        "source_schema_version": "sufficiency_semantic_ref_projection_ag_sem_proj_01_v1",
        "source_projection_digest": "f" * 64,
        "semantic_state_facts_digest": SEMANTIC_DIGEST,
        "accepted_contract_digest": "a" * 64,
        "component_refs": [
            {"component_id": "component:one", "component_digest": "b" * 64}
        ],
        "coverage_record_refs": [
            {
                "coverage_record_id": "coverage:one",
                "coverage_record_digest": "c" * 64,
                "answer_component_id": "component:one",
            }
        ],
        "semantic_observation_refs": [
            {"observation_id": "observation:one", "observation_digest": "d" * 64}
        ],
        "sanitized_content_ref_ids": ["content:one"],
        "content_ref_digests": ["e" * 64],
        "semantic_ref_evidence_ids": ["evidence:one"],
        "source_obligation_refs": ["source-obligation:one"],
        "content_refs_available": True,
        "coverage_refs_available": True,
        "raw_content_included": False,
        "bounded_text_included": False,
        "prompt_visible": False,
        "author_payload_visible": False,
        "model_request_visible": False,
        "final_text_included": False,
    }


def _semantic_sufficiency_projection() -> dict[str, Any]:
    return RunSufficiencyJudgment(
        judgment_id="ag-sem-12c2:judgment",
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
    kernel = RunKernel.start(run_id="ag-sem-12c2-runtime", request_id="req")
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


def _expected_trace_ref(packet: FinalAnswerPacket) -> dict[str, Any]:
    manifest = packet.semantic_evidence_authority_manifest
    return {
        "schema_version": (
            FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_EVIDENCE_MANIFEST_REF_SCHEMA_VERSION
        ),
        "available": True,
        "source_packet_id": packet.packet_id,
        "source_packet_schema_version": packet.schema_version,
        "semantic_evidence_authority_manifest_schema_version": (
            FINAL_ANSWER_SEMANTIC_EVIDENCE_AUTHORITY_MANIFEST_SCHEMA_VERSION
        ),
        "semantic_evidence_authority_manifest_digest": _expected_digest(manifest),
        "semantic_authority_ref_digest": manifest["semantic_authority_ref_digest"],
        "semantic_state_facts_digest": manifest["semantic_state_facts_digest"],
        "content_refs_available": bool(manifest.get("content_refs_available")),
        "coverage_refs_available": bool(manifest.get("coverage_refs_available")),
        "prompt_visible": False,
        "author_payload_content_included": False,
        "model_request_visible": False,
        "final_text_included": False,
        "raw_content_included": False,
        "bounded_text_included": False,
        "raw_prompt_included": False,
        "provider_payload_included": False,
    }


def _assert_trace_ref_sealed(trace_ref: dict[str, Any]) -> None:
    for key in FORBIDDEN_TRACE_REF_KEYS:
        assert key not in trace_ref

    encoded_values = json.dumps(list(trace_ref.values()), sort_keys=True)
    for token in FORBIDDEN_TRACE_REF_VALUE_TOKENS:
        assert token not in encoded_values


def test_author_payload_manifest_trace_ref_schema_and_digest() -> None:
    packet = _manual_packet()
    manifest = packet.semantic_evidence_authority_manifest
    payload = packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )

    trace_ref = dict(payload.semantic_evidence_authority_manifest_trace_ref)

    assert manifest
    assert trace_ref == _expected_trace_ref(packet)
    assert trace_ref["semantic_evidence_authority_manifest_digest"] == (
        _expected_digest(manifest)
    )
    assert payload.to_trace_ref()[TRACE_REF_KEY] == trace_ref
    _assert_trace_ref_sealed(trace_ref)


def test_author_payload_manifest_trace_ref_reports_availability_without_refs() -> None:
    packet = _manual_packet(
        semantic_content_coverage_ref_projection=(
            _semantic_content_coverage_ref_projection()
        )
    )
    payload = packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )

    trace_ref = dict(payload.semantic_evidence_authority_manifest_trace_ref)

    assert packet.semantic_evidence_authority_manifest["content_refs_available"] is True
    assert packet.semantic_evidence_authority_manifest["coverage_refs_available"] is True
    assert trace_ref == _expected_trace_ref(packet)
    assert trace_ref["content_refs_available"] is True
    assert trace_ref["coverage_refs_available"] is True
    assert trace_ref["semantic_evidence_authority_manifest_digest"]
    _assert_trace_ref_sealed(trace_ref)


def test_author_payload_manifest_trace_ref_empty_when_manifest_empty() -> None:
    packet = _manual_packet(semantic_authority_ref={})
    payload = packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert packet.semantic_evidence_authority_manifest == {}
    assert payload.semantic_evidence_authority_manifest_trace_ref == {}
    assert TRACE_REF_KEY not in payload.to_trace_ref()

    incomplete_packet = _manual_packet(
        semantic_authority_ref=_semantic_ref(semantic_state_facts_digest="")
    )
    incomplete_payload = incomplete_packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert incomplete_packet.semantic_evidence_authority_manifest == {}
    assert incomplete_payload.semantic_evidence_authority_manifest_trace_ref == {}
    assert TRACE_REF_KEY not in incomplete_payload.to_trace_ref()


def test_author_payload_manifest_trace_ref_merges_into_packet_author_input_refs() -> None:
    packet = _manual_packet()
    manifest = packet.semantic_evidence_authority_manifest
    semantic_authority_ref = dict(packet.semantic_authority_ref)
    payload = packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert TRACE_REF_KEY not in packet.author_input_refs
    packet_with_payload = packet.with_author_input_payload(payload)

    assert packet_with_payload.author_input_refs[TRACE_REF_KEY] == (
        payload.to_trace_ref()[TRACE_REF_KEY]
    )
    assert packet.semantic_evidence_authority_manifest == manifest
    assert packet.semantic_authority_ref == semantic_authority_ref
    assert packet_with_payload.semantic_evidence_authority_manifest == manifest
    assert packet_with_payload.semantic_authority_ref == semantic_authority_ref
    assert TRACE_REF_KEY not in packet.semantic_evidence_authority_manifest
    assert TRACE_REF_KEY not in packet.semantic_authority_ref


def test_manifest_trace_ref_propagates_through_packet_runtime_and_run_kernel() -> None:
    kernel, action, result = _prepare_packet_runtime_result()
    trace_ref = dict(result.author_payload.semantic_evidence_authority_manifest_trace_ref)
    manifest = result.packet.semantic_evidence_authority_manifest

    assert action.action_type is ActionType.FINAL_ANSWER_PACKET_PREPARE
    assert trace_ref == _expected_trace_ref(result.packet)
    assert result.observation.payload["author_payload_ref"][TRACE_REF_KEY] == trace_ref
    assert result.observation.payload["packet_projection"][
        "semantic_evidence_authority_manifest"
    ] == manifest
    assert TRACE_REF_KEY not in PACKET_RUNTIME.read_text(encoding="utf-8")

    kernel.reduce(result.observation)

    assert kernel.state.final_answer_authority_projection["author_payload_ref"][
        TRACE_REF_KEY
    ] == trace_ref
    assert kernel.state.final_answer_packet["semantic_evidence_authority_manifest"] == (
        manifest
    )
    assert TRACE_REF_KEY not in RUN_KERNEL.read_text(encoding="utf-8")


def test_manifest_trace_ref_does_not_change_author_surfaces_or_model_args() -> None:
    packet = build_final_answer_packet(
        run_id="ag-sem-12c2-nondelta",
        final_evidence=[_passage(source_id=101)],
        author_evidence=[_passage(source_id=101)],
        sufficiency_judgment_projection=_semantic_sufficiency_projection(),
    )
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
    assert with_payload.citation_source_ids == without_payload.citation_source_ids
    assert with_payload.missing_source_obligations == (
        without_payload.missing_source_obligations
    )
    assert TRACE_REF_KEY not in with_payload.prompt
    assert TRACE_REF_KEY not in with_payload.authority_payload

    runtime_kernel, _runtime_action, runtime_result = _prepare_packet_runtime_result()
    runtime_kernel.reduce(runtime_result.observation)
    author_action = runtime_kernel.authorize_author_execution(inputs={})
    payload_without_trace_ref = replace(
        runtime_result.author_payload,
        semantic_evidence_authority_manifest_trace_ref={},
    )
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_ask_model(*args: Any, **kwargs: Any):
        calls.append((args, kwargs))
        return iter(["RAW MODEL FINAL ANSWER [101]"])

    with_trace_result = execute_author_action(
        author_action,
        author_payload=runtime_result.author_payload,
        ask_model=fake_ask_model,
        system_prompt_registry={"author": "AUTHOR SYSTEM"},
        base_url="http://local",
        api_key=None,
        query="ordinary query",
    )
    without_trace_result = execute_author_action(
        author_action,
        author_payload=payload_without_trace_ref,
        ask_model=fake_ask_model,
        system_prompt_registry={"author": "AUTHOR SYSTEM"},
        base_url="http://local",
        api_key=None,
        query="ordinary query",
    )

    assert calls[0] == calls[1]
    assert TRACE_REF_KEY not in with_trace_result.observation.payload
    assert TRACE_REF_KEY not in without_trace_result.observation.payload


def test_manifest_trace_ref_raw_leakage_scan() -> None:
    packet = _manual_packet()
    payload = packet.to_author_input_payload(
        prompt="BASE AUTHOR PROMPT",
        author_system_prompt_key="author",
        author_effort="low",
    )
    trace_ref = payload.to_trace_ref()[TRACE_REF_KEY]

    _assert_trace_ref_sealed(trace_ref)
    assert "semantic_evidence_authority_manifest_digest" in trace_ref
    assert "semantic_evidence_authority_manifest" not in trace_ref


def test_static_guard_manifest_trace_ref_stays_out_of_closed_surfaces() -> None:
    assert TRACE_REF_KEY not in AUTHOR_RUNTIME.read_text(encoding="utf-8")
    assert TRACE_REF_KEY not in PACKET_RUNTIME.read_text(encoding="utf-8")
    assert TRACE_REF_KEY not in RUN_KERNEL.read_text(encoding="utf-8")
    assert TRACE_REF_KEY not in ADAPTER.read_text(encoding="utf-8")

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
    ):
        region = packet_source[start:end]
        assert TRACE_REF_KEY not in region, region_name

    for path in (
        ROOT / "core" / "retrieval.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "search_providers.py",
    ):
        assert TRACE_REF_KEY not in path.read_text(encoding="utf-8")


def test_static_guard_no_historical_author_harness_or_semantic_history_reads() -> None:
    packet_source = PACKET.read_text(encoding="utf-8")
    manifest_ref_region = packet_source[
        packet_source.index(
            "def _semantic_evidence_authority_manifest_trace_ref("
        ) : packet_source.index("def to_author_authority_block(")
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
        assert token not in manifest_ref_region

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
