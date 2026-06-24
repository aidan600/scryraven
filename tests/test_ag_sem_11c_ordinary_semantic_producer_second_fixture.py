from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.final_answer_packet import SourceObligationStatus
from core.ordinary_semantic_producer_runtime import (
    SKIP_REASON_BINDABLE_PASSAGE_MISSING,
    OrdinarySemanticProducerHandoffStatus,
    execute_ordinary_semantic_producer_handoff_from_scope,
)
from core.run_kernel import RunKernel
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    OfflineOrdinaryPipelineHarness,
    assert_no_semantic_state,
    run_offline_ordinary_pipeline,
    scrub_offline_runtime,
)

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_MODULE = ROOT / "core" / "ordinary_semantic_producer_runtime.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
FAP = ROOT / "core" / "final_answer_packet.py"
FAP_ADAPTER = ROOT / "core" / "final_answer_runtime_adapter.py"
FAP_RUNTIME = ROOT / "core" / "final_answer_packet_runtime.py"
AUTHOR_RUNTIME = ROOT / "core" / "author_execution_runtime.py"

SECOND_FIXTURE_QUERY = (
    "What is the current official rule for Sample Relief Program?"
)
RAW_AUTHOR_RESPONSE = (
    "AG_SEM_11C_AUTHOR_FINAL_REPORT: Sample Relief Program remains governed by "
    "the retrieved official current rule. The answer cites only packet provided "
    "source identity [[7]](https://official.sample.test/rule)."
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _SecondFixtureHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=SECOND_FIXTURE_QUERY,
            core_topic="Sample Relief Program current official rule",
            primary_entity="Sample Relief Program",
            raw_author_response=RAW_AUTHOR_RESPONSE,
            expander_reasoning="second offline fixture sufficient",
            analyst_response=(
                "Analysis is limited to the retrieved official Sample Relief "
                "Program rule."
            ),
            logger_name="test_ag_sem_11c_second_fixture",
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": 7,
                "title": "Sample Relief Program official rule",
                "url": "https://official.sample.test/rule",
                "text": (
                    "Sample Relief Program official current rule says the "
                    "program uses the active enrollment rule and remains in "
                    "effect."
                ),
                "score": 0.99,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
                "_provider": "offline_fake_search",
            },
            {
                "source_id": 8,
                "title": "Sample Relief Program official implementation note",
                "url": "https://official.sample.test/implementation-note",
                "text": (
                    "Official implementation note confirms the current rule "
                    "and gives supporting context for Sample Relief Program."
                ),
                "score": 0.96,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "currentness_signal": "current",
                "_provider": "offline_fake_search",
            },
        ]


def _run_second_fixture_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], _SecondFixtureHarness, Any]:
    harness = _SecondFixtureHarness(tmp_path)
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-23",
        session_id="ag-sem-11c-session",
        run_id="ag-sem-11c-run",
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    return captured, harness, outcome


def _fresh_kernel_for_handoff(source_kernel: RunKernel) -> RunKernel:
    kernel = RunKernel.start(
        run_id=f"{source_kernel.state.run_id}:handoff-retest",
        request_id=f"{source_kernel.state.request_id}:handoff-retest",
    )
    kernel.state.search_work_plan = deepcopy(source_kernel.state.search_work_plan)
    kernel.state.evidence_ledger = deepcopy(source_kernel.state.evidence_ledger)
    kernel.state.projections = deepcopy(source_kernel.state.projections)
    return kernel


def test_second_offline_fixture_reaches_semantic_sufficiency_and_fap_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, harness, outcome = _run_second_fixture_pipeline(tmp_path, monkeypatch)

    assert captured["semantic_handoff_called"] is True
    assert captured["semantic_handoff_result"].status is (
        OrdinarySemanticProducerHandoffStatus.COMMITTED
    )
    assert captured["sufficiency_handoff_called"] is True
    assert captured["packet_handoff_called"] is True
    assert captured["author_handoff_called"] is True
    assert harness.search_calls
    assert harness.forbidden_live_calls == []
    assert len(harness.author_prompts) == 1
    assert len(harness.author_kwargs) == 1
    assert harness.author_kwargs[0]["provider"] == "offline-fake-provider"
    assert harness.author_kwargs[0]["model"] == "offline-fake-fast-model"
    assert harness.author_kwargs[0]["base_url"] == "http://offline.invalid/v1"
    assert harness.author_kwargs[0]["api_key"] == ""
    assert harness.author_kwargs[0]["stream"] is True
    assert harness.author_kwargs[0]["use_reasoning"] is False
    assert harness.author_kwargs[0]["cost_phase"] == "model"

    kernel = captured["run_kernel"]
    state = kernel.state
    assert len(state.initial_answer_contract["accepted_answer_component_refs"]) == 1
    assert len(state.semantic_observation_admission_history) == 1
    assert len(state.component_coverage_history) == 1

    component_ref = state.initial_answer_contract["accepted_answer_component_refs"][0]
    assert component_ref["component_id"].startswith("component:")
    assert component_ref.get("source_obligation_candidate_ids")
    assert "obligation:official_current" in component_ref[
        "source_obligation_candidate_ids"
    ]

    admission = state.semantic_observation_admission_history[-1]
    assert admission["canonical_state"] is True
    assert admission["trace_only"] is False
    assert admission["content_ref_records"]

    coverage = state.component_coverage_history[-1]
    assert coverage["canonical_state"] is True
    assert coverage["trace_only"] is False
    assert coverage["coverage_state"] == "satisfied"
    assert coverage["source_obligation_status"] == "satisfied"
    assert coverage["evidence_ledger_binding"]["source_requirement_ids"]

    sufficiency_projection = captured["sufficiency_projection"]
    assert sufficiency_projection["owner"] == "RunKernel.RunAuthoritySufficiencyJudgment"
    assert sufficiency_projection["canonical_state"] is True
    assert sufficiency_projection["trace_only"] is False
    semantic_consumption = sufficiency_projection["semantic_consumption"]
    semantic_summary = sufficiency_projection["semantic_state_facts_summary"]
    assert semantic_consumption["schema_version"]
    assert semantic_consumption["required_component_count"] == 1
    assert semantic_consumption["covered_component_count"] == 1
    assert semantic_summary["semantic_state_facts_digest"]

    packet_handoff = captured["packet_handoff"]
    packet = packet_handoff.packet
    semantic_ref = packet.semantic_authority_ref
    assert semantic_ref["available"] is True
    assert semantic_ref["sufficiency_semantic_consumed"] is True
    assert semantic_ref["semantic_state_facts_digest"] == semantic_summary[
        "semantic_state_facts_digest"
    ]
    assert state.final_answer_packet["semantic_authority_ref"] == semantic_ref

    manifest = packet.semantic_evidence_authority_manifest
    assert manifest["available"] is True
    assert manifest["semantic_state_facts_digest"] == semantic_ref[
        "semantic_state_facts_digest"
    ]
    assert manifest["content_refs_available"] is False
    assert manifest["coverage_refs_available"] is False
    assert "sanitized_content_ref_ids" not in manifest
    assert "content_ref_digests" not in manifest
    assert "coverage_record_ids" not in manifest
    assert "coverage_record_digests" not in manifest
    assert state.final_answer_packet["semantic_evidence_authority_manifest"] == manifest

    expected_status_summary = {item.value: 0 for item in SourceObligationStatus}
    for record in packet.source_obligations:
        expected_status_summary[record.status.value] += 1
    assert manifest["source_obligation_status_summary"] == expected_status_summary

    assert harness.author_prompts == [packet_handoff.author_prompt]
    assert "FINAL ANSWER PACKET AUTHORITY" in harness.author_prompts[0]
    assert "semantic_authority_ref" not in harness.author_prompts[0]
    assert "semantic_evidence_authority_manifest" not in harness.author_prompts[0]
    assert captured["author_runtime_scope"]["final_answer_author_payload"] is (
        packet_handoff.author_payload
    )
    assert state.author_observation["owner"] == "RunKernel.AuthorExecutor"
    assert state.author_observation["packet_id"] == packet.packet_id
    assert state.author_observation["authority_payload_ref"] == (
        packet_handoff.author_payload.authority_payload
    )
    assert state.author_observation["citation_source_ids"] == list(
        packet_handoff.author_payload.citation_source_ids
    )
    assert "semantic_authority_ref" not in state.author_observation
    assert "semantic_authority_trace_ref" not in state.author_observation

    assert outcome.report == RAW_AUTHOR_RESPONSE
    canonical_trace = json.dumps(kernel.to_trace_fragment(), sort_keys=True)
    execution_trace = json.dumps(outcome.execution_trace, sort_keys=True)
    assert RAW_AUTHOR_RESPONSE not in canonical_trace
    assert harness.author_prompts[0] not in canonical_trace
    assert harness.author_prompts[0] not in execution_trace


def test_second_fixture_missing_evidence_skips_without_orphan_semantic_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, _harness, _outcome = _run_second_fixture_pipeline(tmp_path, monkeypatch)
    source_kernel = captured["run_kernel"]
    kernel = _fresh_kernel_for_handoff(source_kernel)
    scope = dict(captured["sufficiency_runtime_scope"])
    scope["final_top_evidence"] = []

    result = execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)

    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == SKIP_REASON_BINDABLE_PASSAGE_MISSING
    assert_no_semantic_state(kernel)


def test_ag_sem_11c_static_guards_keep_second_fixture_out_of_closed_surfaces() -> None:
    producer_source = PRODUCER_MODULE.read_text(encoding="utf-8")
    assert "Sample Relief Program" not in producer_source
    assert "Example Program" not in producer_source

    tree = ast.parse(producer_source)
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.retrieval_dispatch_runtime",
        "core.retrieval",
        "openai",
        "requests",
        "httpx",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert imported.isdisjoint(forbidden_imports)

    assert PIPELINE.read_text(encoding="utf-8").count(
        "execute_ordinary_semantic_producer_handoff_from_scope("
    ) == 1
    for closed_file in (FAP, FAP_ADAPTER, FAP_RUNTIME, AUTHOR_RUNTIME):
        source = closed_file.read_text(encoding="utf-8")
        assert "AG-SEM-11C" not in source
        assert "Sample Relief Program" not in source
