from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.ordinary_semantic_producer_runtime import (
    ORDINARY_SEMANTIC_PRODUCER_COMPONENT_CAP,
    SKIP_REASON_COMPONENT_CAP_EXCEEDED,
    OrdinarySemanticProducerHandoffStatus,
)
from core.protocols import NullStatusWriter
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    OfflineOrdinaryPipelineHarness,
    install_handoff_capture,
    offline_balanced_run_config,
    run_offline_ordinary_pipeline,
    scrub_offline_runtime,
)

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_MODULE = ROOT / "core" / "ordinary_semantic_producer_runtime.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
RUNTIME_PROMPT_ASSEMBLY = ROOT / "core" / "runtime_prompt_assembly.py"
RETRIEVAL = ROOT / "core" / "retrieval.py"
RETRIEVAL_DISPATCH = ROOT / "core" / "retrieval_dispatch_runtime.py"
SEARCH_PROVIDERS = ROOT / "core" / "search_providers.py"

MULTIPART_QUERY = (
    "What does the Example Permit API spec say about payload size, support "
    "status, and documented limitation?"
)
CAP_QUERY = (
    "What does the Example Permit API spec say about payload size, support "
    "status, documented limitation, retry behavior, authentication mode, and "
    "renewal period?"
)
RAW_POSITIVE_AUTHOR_RESPONSE = (
    "AG_SEM_MULTI_01_AUTHOR_FINAL_REPORT: Example Permit semantic coverage "
    "supports the payload size, support status, and documented limitation answer."
)
RAW_PARTIAL_AUTHOR_RESPONSE = (
    "AG_SEM_MULTI_01_PARTIAL_AUTHOR_FINAL_REPORT: The legacy path does not claim "
    "complete semantic coverage."
)
MATERIALIZATION_TRACE_REF_KEY = "semantic_author_materialization_trace_ref"


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


class _MultipartPermitHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, tmp_path: Path, *, partial: bool = False, cap: bool = False) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query=CAP_QUERY if cap else MULTIPART_QUERY,
            core_topic=CAP_QUERY if cap else MULTIPART_QUERY,
            primary_entity="Example Permit API",
            researcher_queries=("Example Permit API spec payload support limitation",),
            raw_author_response=(
                RAW_PARTIAL_AUTHOR_RESPONSE if partial else RAW_POSITIVE_AUTHOR_RESPONSE
            ),
            analyst_response="Analysis is limited to retrieved Example Permit sources.",
            logger_name="test_ag_sem_multi_01",
        )
        self.partial = partial
        self.cap = cap

    def build_search_passages(self) -> list[dict[str, Any]]:
        passages = [
            {
                "source_id": 301,
                "title": "Example Permit API payload size specification",
                "url": "https://docs.example/permit-api/payload-size",
                "text": "Example Permit API spec says payload size is 64 KiB.",
                "score": 0.99,
                "credibility": 4,
                "source_tier": "canonical",
                "source_class": "primary_source_documents",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
                "query_ref": "Example Permit API spec payload support limitation",
                "_provider": "offline_fake_search",
            },
            {
                "source_id": 302,
                "title": "Example Permit API support status specification",
                "url": "https://docs.example/permit-api/support-status",
                "text": "Example Permit API spec says support status is active.",
                "score": 0.98,
                "credibility": 4,
                "source_tier": "canonical",
                "source_class": "primary_source_documents",
                "currentness_signal": "current",
                "readable_status": "readable",
                "disposition": "accepted",
                "eligible_for_stronger_obligation": True,
                "query_ref": "Example Permit API spec payload support limitation",
                "_provider": "offline_fake_search",
            },
        ]
        if not self.partial:
            passages.append(
                {
                    "source_id": 303,
                    "title": "Example Permit API documented limitation",
                    "url": "https://docs.example/permit-api/limitation",
                    "text": (
                        "Example Permit API spec says the documented limitation is "
                        "one active client token per account."
                    ),
                    "score": 0.97,
                    "credibility": 4,
                    "source_tier": "canonical",
                    "source_class": "primary_source_documents",
                    "currentness_signal": "current",
                    "readable_status": "readable",
                    "disposition": "accepted",
                    "eligible_for_stronger_obligation": True,
                    "query_ref": "Example Permit API spec payload support limitation",
                    "_provider": "offline_fake_search",
                }
            )
        if self.cap:
            passages.extend(
                {
                    "source_id": source_id,
                    "title": title,
                    "url": f"https://official.example/permit/{slug}",
                    "text": text,
                    "score": 0.95,
                    "credibility": 4,
                    "source_tier": "canonical",
                    "source_class": "primary_source_documents",
                    "currentness_signal": "current",
                    "readable_status": "readable",
                    "disposition": "accepted",
                    "eligible_for_stronger_obligation": True,
                    "_provider": "offline_fake_search",
                }
                for source_id, slug, title, text in (
                    (304, "support", "Example Permit support status", "Support status is active."),
                    (
                        305,
                        "limitation",
                        "Example Permit documented limitation",
                        "Documented limitation is one permit per household.",
                    ),
                    (306, "renewal", "Example Permit renewal period", "Renewal period is annual."),
                )
            )
        return passages


def _run_multipart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    partial: bool = False,
    cap: bool = False,
    allow_blocked_packet: bool = False,
) -> tuple[dict[str, Any], _MultipartPermitHarness, Any]:
    harness = _MultipartPermitHarness(tmp_path, partial=partial, cap=cap)
    capture_stages = (
        HANDOFF_SEMANTIC,
        HANDOFF_SUFFICIENCY,
        HANDOFF_PACKET,
        HANDOFF_AUTHOR,
    )
    if allow_blocked_packet:
        captured = install_handoff_capture(monkeypatch, capture_stages=capture_stages)
        try:
            outcome = orchestrator.run_pipeline(
                offline_balanced_run_config(
                    query=harness.query,
                    current_date="2026-06-24",
                    session_id="ag-sem-multi-01-session",
                    run_id="ag-sem-multi-01-run",
                ),
                harness.deps(),
                NullStatusWriter(),
                CostAccumulator(),
            )
        except ValueError as exc:
            if "blocked FinalAnswerPacket cannot produce Author input" not in str(exc):
                raise
            captured["blocked_packet_error"] = str(exc)
            outcome = None
        return captured, harness, outcome
    captured, outcome = run_offline_ordinary_pipeline(
        harness,
        monkeypatch,
        current_date="2026-06-24",
        session_id="ag-sem-multi-01-session",
        run_id="ag-sem-multi-01-run",
        capture_stages=capture_stages,
    )
    return captured, harness, outcome


def _assert_author_kwargs_unchanged(harness: _MultipartPermitHarness) -> None:
    assert len(harness.author_kwargs) == 1
    assert harness.author_kwargs[0]["provider"] == "offline-fake-provider"
    assert harness.author_kwargs[0]["model"] == "offline-fake-fast-model"
    assert harness.author_kwargs[0]["base_url"] == "http://offline.invalid/v1"
    assert harness.author_kwargs[0]["api_key"] == ""
    assert harness.author_kwargs[0]["stream"] is True
    assert harness.author_kwargs[0]["use_reasoning"] is False
    assert harness.author_kwargs[0]["cost_phase"] == "model"


def _assert_no_trace_leakage(
    *,
    kernel: Any,
    packet: Any,
    author_payload_trace_ref: dict[str, Any],
    author_prompt: str | None,
) -> None:
    serialized = json.dumps(
        {
            "packet_projection": kernel.state.final_answer_packet,
            "author_payload_trace_ref": author_payload_trace_ref,
            "author_observation": kernel.state.author_observation,
            "kernel_trace_fragment": kernel.to_trace_fragment(),
            "packet_dict": packet.to_dict(),
        },
        sort_keys=True,
    )
    for forbidden in (
        "CONTROLLED SEMANTIC CONTEXT",
        "FINAL ANSWER PACKET AUTHORITY",
        author_prompt or "",
        RAW_POSITIVE_AUTHOR_RESPONSE,
        RAW_PARTIAL_AUTHOR_RESPONSE,
        '"raw_prompt_retained": true',
        '"raw_prompt_included": true',
        '"provider_payload_retained": true',
        '"raw_content_included": true',
        "semantic_packet_evidence_bindings",
        "full semantic rows",
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
    ):
        if forbidden:
            assert forbidden not in serialized


def test_positive_bounded_n_multipart_semantic_path_reaches_fap_and_author(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, harness, outcome = _run_multipart(tmp_path, monkeypatch)

    assert captured["semantic_handoff_result"].status is (
        OrdinarySemanticProducerHandoffStatus.COMMITTED
    )
    _assert_author_kwargs_unchanged(harness)
    assert harness.forbidden_live_calls == []

    kernel = captured["run_kernel"]
    state = kernel.state
    component_refs = state.initial_answer_contract["accepted_answer_component_refs"]
    assert len(component_refs) == 3
    assert len({ref["component_id"] for ref in component_refs}) == 3
    assert len(state.semantic_observation_admission_history) == 3
    assert len(state.component_coverage_history) == 3
    assert {
        coverage["answer_component_id"] for coverage in state.component_coverage_history
    } == {ref["component_id"] for ref in component_refs}
    assert all(
        coverage["coverage_state"] == "satisfied"
        and coverage["evidence_custody_status"] == "custodied"
        for coverage in state.component_coverage_history
    )

    semantic_consumption = captured["sufficiency_projection"]["semantic_consumption"]
    assert semantic_consumption["required_component_count"] == 3
    assert semantic_consumption["covered_component_count"] == 3
    assert semantic_consumption["missing_component_count"] == 0
    assert semantic_consumption["semantic_ref_projection"]["available"] is True

    packet = captured["packet_handoff"].packet
    fap_projection = packet.semantic_content_coverage_ref_projection
    assert fap_projection["available"] is True
    assert len(fap_projection["component_refs"]) == 3
    assert len(fap_projection["coverage_record_refs"]) == 3
    assert len(fap_projection["semantic_observation_refs"]) == 3
    assert len(fap_projection["sanitized_content_ref_ids"]) == 3
    bindings = tuple(dict(row) for row in packet.semantic_packet_evidence_bindings)
    assert len(bindings) == 3
    assert len({row["component_id"] for row in bindings}) == 3
    assert len({row["origin_evidence_ref_id"] for row in bindings}) >= 2

    author_payload_trace_ref = captured["packet_handoff"].author_payload.to_trace_ref()
    materialization = author_payload_trace_ref[MATERIALIZATION_TRACE_REF_KEY]
    assert materialization["component_count"] == 3
    assert materialization["semantic_packet_evidence_binding_count"] == 3
    assert "CONTROLLED SEMANTIC CONTEXT" in harness.author_prompts[0]
    assert "3 required components are supported" in harness.author_prompts[0]
    assert "Bounded semantic excerpt from" not in harness.author_prompts[0]
    assert outcome.report == RAW_POSITIVE_AUTHOR_RESPONSE
    _assert_no_trace_leakage(
        kernel=kernel,
        packet=packet,
        author_payload_trace_ref=author_payload_trace_ref,
        author_prompt=harness.author_prompts[0],
    )


def test_partial_missing_bounded_n_semantic_path_fails_closed_without_overclaim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, harness, outcome = _run_multipart(
        tmp_path,
        monkeypatch,
        partial=True,
        allow_blocked_packet=True,
    )

    assert captured["semantic_handoff_result"].status is (
        OrdinarySemanticProducerHandoffStatus.COMMITTED
    )
    kernel = captured["run_kernel"]
    state = kernel.state
    assert len(state.initial_answer_contract["accepted_answer_component_refs"]) == 3
    assert len(state.component_coverage_history) == 2

    sufficiency_projection = captured["sufficiency_projection"]
    semantic_consumption = sufficiency_projection["semantic_consumption"]
    assert semantic_consumption["required_component_count"] == 3
    assert semantic_consumption["covered_component_count"] == 2
    assert semantic_consumption["missing_component_count"] == 1
    assert semantic_consumption["direct_answer_blocked"] is True
    assert "missing_required_component_coverage" in semantic_consumption["blocker_codes"]
    assert semantic_consumption["semantic_ref_projection"]["available"] is False

    assert captured["blocked_packet_error"] == (
        "blocked FinalAnswerPacket cannot produce Author input"
    )
    assert captured["packet_handoff_called"] is True
    assert captured["author_handoff_called"] is False
    assert harness.author_prompts == []
    assert harness.author_kwargs == []
    assert outcome is None


def test_component_cap_exceeded_skips_semantic_production_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, harness, _outcome = _run_multipart(tmp_path, monkeypatch, cap=True)

    assert ORDINARY_SEMANTIC_PRODUCER_COMPONENT_CAP == 5
    assert captured["semantic_handoff_result"].status is (
        OrdinarySemanticProducerHandoffStatus.SKIPPED
    )
    assert captured["semantic_handoff_result"].skipped_reason == (
        SKIP_REASON_COMPONENT_CAP_EXCEEDED
    )
    kernel = captured["run_kernel"]
    assert not kernel.state.initial_answer_contract
    assert not kernel.state.semantic_observation_admission_history
    assert not kernel.state.component_coverage_history
    packet = captured["packet_handoff"].packet
    assert packet.semantic_content_coverage_ref_projection.get("available") is not True
    assert tuple(packet.semantic_packet_evidence_bindings) == ()
    if harness.author_prompts:
        assert "CONTROLLED SEMANTIC CONTEXT" not in harness.author_prompts[0]


def test_ag_sem_multi_01_static_closed_surface_and_import_guards() -> None:
    producer_source = PRODUCER_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(producer_source)
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
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
    assert "ask_model(" not in producer_source
    assert "fetch_linkup_precision_block" not in producer_source
    assert "run_scout" not in producer_source
    pipeline_source = PIPELINE.read_text(encoding="utf-8")
    assert (
        pipeline_source.count("execute_ordinary_semantic_producer_handoff_from_scope(")
        == 2
    )
    assert (
        "if not run_kernel.state.initial_answer_contract:\n"
        "            final_top_evidence = list(all_passages)\n"
        "            execute_ordinary_semantic_producer_handoff_from_scope("
        in pipeline_source
    )
    for closed_file in (
        PIPELINE,
        RUNTIME_PROMPT_ASSEMBLY,
        RETRIEVAL,
        RETRIEVAL_DISPATCH,
        SEARCH_PROVIDERS,
    ):
        source = closed_file.read_text(encoding="utf-8")
        assert "AG-SEM-MULTI-01" not in source
        assert "Example Permit" not in source
