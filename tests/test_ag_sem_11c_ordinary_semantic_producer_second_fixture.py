from __future__ import annotations

import ast
import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.final_answer_packet import SourceObligationStatus
from core.ordinary_semantic_producer_runtime import (
    SKIP_REASON_BINDABLE_PASSAGE_MISSING,
    OrdinarySemanticProducerHandoffStatus,
    execute_ordinary_semantic_producer_handoff_from_scope,
)
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig, RunDeps
from core.run_kernel import RunKernel

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
    for key in (
        "BRAVE_API_KEY",
        "TAVILY_API_KEY",
        "LINKUP_API_KEY",
        "EXA_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)
    monkeypatch.setattr(orchestrator, "kb_review_agent", lambda *_args, **_kwargs: {})


@dataclass
class _SecondFixtureHarness:
    tmp_path: Path
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    search_calls: list[dict[str, Any]] = field(default_factory=list)
    author_prompts: list[str] = field(default_factory=list)
    author_kwargs: list[dict[str, Any]] = field(default_factory=list)
    forbidden_live_calls: list[str] = field(default_factory=list)

    query: str = SECOND_FIXTURE_QUERY
    core_topic: str = "Sample Relief Program current official rule"
    primary_entity: str = "Sample Relief Program"

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        self.model_calls.append(
            {
                "system_prompt": system_prompt,
                "stream": bool(kwargs.get("stream")),
                "provider": kwargs.get("provider"),
                "model": kwargs.get("model"),
                "use_reasoning": kwargs.get("use_reasoning"),
            }
        )
        if system_prompt == DEFAULT_SYSTEM["router"]:
            return json.dumps(
                {
                    "intent": "general",
                    "report_type": "general_research",
                    "image_mode": "none",
                    "core_topic": self.core_topic,
                    "is_academic": False,
                    "query_type": "other",
                    "entities": [self.primary_entity],
                    "primary_entity": self.primary_entity,
                }
            )
        if system_prompt == "You are a concise title generator.":
            return f"{self.primary_entity} Rule"
        if system_prompt == DEFAULT_SYSTEM["researcher"]:
            return json.dumps(
                {"queries": [f"{self.primary_entity} official current rule"]}
            )
        if system_prompt == DEFAULT_SYSTEM["expander"] or (
            "research gap detector" in system_prompt
        ):
            return json.dumps(
                {
                    "component_queries": [],
                    "reasoning": "second offline fixture sufficient",
                }
            )
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return json.dumps({"is_sufficient": True, "new_queries": []})
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            return (
                "Analysis is limited to the retrieved official Sample Relief "
                "Program rule."
            )
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if kwargs.get("stream"):
            self.author_prompts.append(prompt)
            self.author_kwargs.append(dict(kwargs))
            return RAW_AUTHOR_RESPONSE
        raise AssertionError(f"unexpected model call in 11C fixture: {system_prompt!r}")

    def embed_texts(self, texts: list[str], **_kwargs: Any) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    def process_search_queries(
        self,
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self.search_calls.append(
            {
                "queries": list(queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "provider_role": kwargs.get("provider_role"),
                "search_providers": list(kwargs.get("search_providers") or []),
            }
        )
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is None and len(_args) >= 4:
            seen_urls = _args[3]
        passages = [
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
        if seen_urls is not None:
            for passage in passages:
                seen_urls.add(passage["url"])
        return passages

    def forbidden_live_dependency(self, name: str) -> Callable[..., Any]:
        def _called(*_args: Any, **_kwargs: Any) -> Any:
            self.forbidden_live_calls.append(name)
            if name == "run_scout":
                return {}
            return ""

        return _called

    def deps(self) -> RunDeps:
        return RunDeps(
            ask_model=self.ask_model,
            embed_texts=self.embed_texts,
            compute_similarities=lambda texts, *_args, **_kwargs: [1.0 for _ in texts],
            process_search_queries=self.process_search_queries,
            filter_top_evidence=lambda passages, *_args, **_kwargs: list(passages),
            is_plausible_domain=lambda _url: True,
            anchor_query_to_topic=lambda query, _topic: query,
            fetch_linkup_precision_block=self.forbidden_live_dependency(
                "fetch_linkup_precision_block"
            ),
            run_economist_step=self.forbidden_live_dependency("run_economist_step"),
            run_scout=self.forbidden_live_dependency("run_scout"),
            should_skip_quant_scout=lambda *_args, **_kwargs: True,
            clean_json_response=lambda value: value,
            DEFAULT_SYSTEM=DEFAULT_SYSTEM,
            NEWS_PREFERRED_DOMAINS=[],
            ACADEMIC_DOMAINS=[],
            QUANT_REPORT_TYPES=set(),
            logger=logging.getLogger("test_ag_sem_11c_second_fixture"),
            execution_log_path=self.tmp_path / "execution.jsonl",
            feedback_log_path=self.tmp_path / "feedback.jsonl",
            kb_triggers_path=self.tmp_path / "kb.jsonl",
            policy_state_path=self.tmp_path / "policy.json",
            policy_journal_path=self.tmp_path / "policy_journal.jsonl",
        )


def _install_handoff_capture(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {
        "semantic_handoff_called": False,
        "sufficiency_handoff_called": False,
        "packet_handoff_called": False,
        "author_handoff_called": False,
    }
    original_semantic = orchestrator.execute_ordinary_semantic_producer_handoff_from_scope
    original_sufficiency = orchestrator.execute_sufficiency_judgment_handoff_from_scope
    original_packet = orchestrator.prepare_final_answer_packet_author_handoff_from_scope
    original_author = orchestrator.execute_author_handoff_from_scope

    def semantic_wrapper(
        run_kernel: Any,
        runtime_scope: dict[str, Any],
    ) -> Any:
        captured["semantic_handoff_called"] = True
        captured["semantic_runtime_scope"] = dict(runtime_scope)
        result = original_semantic(run_kernel, runtime_scope)
        captured["semantic_handoff_result"] = result
        return result

    def sufficiency_wrapper(
        run_kernel: Any,
        runtime_scope: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        captured["sufficiency_handoff_called"] = True
        captured["sufficiency_runtime_scope"] = dict(runtime_scope)
        handoff = original_sufficiency(run_kernel, runtime_scope, **kwargs)
        captured["sufficiency_handoff"] = handoff
        captured["sufficiency_projection"] = dict(
            run_kernel.state.sufficiency_judgment_projection
        )
        return handoff

    def packet_wrapper(
        run_kernel: Any,
        runtime_scope: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        captured["packet_handoff_called"] = True
        captured["run_kernel"] = run_kernel
        captured["packet_runtime_scope"] = dict(runtime_scope)
        handoff = original_packet(run_kernel, runtime_scope, **kwargs)
        captured["packet_handoff"] = handoff
        return handoff

    def author_wrapper(
        run_kernel: Any,
        runtime_scope: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        captured["author_handoff_called"] = True
        captured["author_runtime_scope"] = dict(runtime_scope)
        handoff = original_author(run_kernel, runtime_scope, **kwargs)
        captured["author_handoff"] = handoff
        return handoff

    monkeypatch.setattr(
        orchestrator,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        semantic_wrapper,
    )
    monkeypatch.setattr(
        orchestrator,
        "execute_sufficiency_judgment_handoff_from_scope",
        sufficiency_wrapper,
    )
    monkeypatch.setattr(
        orchestrator,
        "prepare_final_answer_packet_author_handoff_from_scope",
        packet_wrapper,
    )
    monkeypatch.setattr(orchestrator, "execute_author_handoff_from_scope", author_wrapper)
    return captured


def _run_second_fixture_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], _SecondFixtureHarness, Any]:
    captured = _install_handoff_capture(monkeypatch)
    harness = _SecondFixtureHarness(tmp_path)
    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode="Balanced",
            current_date="2026-06-23",
            session_id="ag-sem-11c-session",
            run_id="ag-sem-11c-run",
            fast_provider="offline-fake-provider",
            fast_model="offline-fake-fast-model",
            smart_provider="offline-fake-provider",
            smart_model="offline-fake-smart-model",
            local_url="http://offline.invalid/v1",
            or_api_key="",
            use_reasoning=False,
            run_authority_contract_smart_model=False,
            run_authority_search_judgment_smart_model=False,
            run_authority_sufficiency_smart_model=False,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
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


def _assert_no_semantic_state(kernel: RunKernel) -> None:
    assert not kernel.state.initial_answer_contract
    assert not kernel.state.semantic_observation_admission_history
    assert not kernel.state.component_coverage_history


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
    _assert_no_semantic_state(kernel)


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
