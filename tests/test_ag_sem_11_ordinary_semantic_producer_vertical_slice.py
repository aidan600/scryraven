from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.ordinary_semantic_producer_runtime import (
    OrdinarySemanticProducerHandoffStatus,
    OrdinarySemanticProducerTransactionError,
    build_ordinary_semantic_producer_bundle,
    execute_ordinary_semantic_producer_handoff_from_scope,
)
from core.protocols import NullStatusWriter
from core.run_authority_sufficiency import RunSufficiencyDecision
from core.run_config import RunConfig, RunDeps
from core.run_kernel import RunKernel

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_MODULE = ROOT / "core" / "ordinary_semantic_producer_runtime.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"

AG_CHECK_01_QUERY = "What is the current official rule for Example Program?"


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


class _OfflineOrdinaryHarness:
    def __init__(self, tmp_path: Path) -> None:
        from core.prompts import DEFAULT_SYSTEM

        self.tmp_path = tmp_path
        self.query = AG_CHECK_01_QUERY
        self.core_topic = "Example Program current official rule"
        self.primary_entity = "Example Program"
        self._DEFAULT_SYSTEM = DEFAULT_SYSTEM
        self.search_calls: list[dict[str, Any]] = []
        self.weakened_evidence = False
        self.stale_readable_official = False

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt == self._DEFAULT_SYSTEM["router"]:
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
        if system_prompt == self._DEFAULT_SYSTEM["researcher"]:
            return json.dumps({"queries": [f"{self.primary_entity} official current rule"]})
        if system_prompt in (self._DEFAULT_SYSTEM["expander"],) or "research gap detector" in system_prompt:
            return json.dumps({"component_queries": [], "reasoning": "offline fixture sufficient"})
        if system_prompt == self._DEFAULT_SYSTEM["evaluator"]:
            return json.dumps({"is_sufficient": True, "new_queries": []})
        if system_prompt == self._DEFAULT_SYSTEM["analyst"]:
            return "Analysis is limited to the retrieved official Example Program rule."
        if system_prompt == self._DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if kwargs.get("stream"):
            return (
                "AG_SEM_11_AUTHOR_FINAL_REPORT: Example Program remains governed by the "
                "retrieved official rule."
            )
        raise AssertionError(f"unexpected model call: {system_prompt!r}")

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
            }
        )
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is None and len(_args) >= 4:
            seen_urls = _args[3]
        passages = [
            {
                "source_id": 1,
                "title": "Example Program official rule",
                "url": "https://official.example/rule",
                "text": (
                    "Example Program official current rule says the program "
                    "uses the current eligibility rule and remains in effect."
                ),
                "score": 0.99,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "_provider": "offline_fake_search",
            }
        ]
        if not self.weakened_evidence:
            passages.append(
                {
                    "source_id": 2,
                    "title": "Example Program implementation memo",
                    "url": "https://official.example/memo",
                    "text": (
                        "Official implementation memo confirms the current rule "
                        "and gives supporting context for Example Program."
                    ),
                    "score": 0.97,
                    "credibility": 4,
                    "source_tier": "official",
                    "source_class": "official_current_rules",
                    "_provider": "offline_fake_search",
                }
            )
        if self.stale_readable_official:
            for passage in passages:
                passage["currentness_signal"] = "stale"
        elif self.weakened_evidence:
            for passage in passages:
                passage["source_tier"] = "weak"
                passage["source_class"] = "contextual_secondary"
                passage["lower_tier"] = True
                passage["currentness_signal"] = "stale"
                passage["readable_status"] = "unreadable"
        if seen_urls is not None:
            for passage in passages:
                seen_urls.add(passage["url"])
        return passages

    def deps(self) -> RunDeps:
        return RunDeps(
            ask_model=self.ask_model,
            embed_texts=self.embed_texts,
            compute_similarities=lambda texts, *_args, **_kwargs: [1.0 for _ in texts],
            process_search_queries=self.process_search_queries,
            filter_top_evidence=lambda passages, *_args, **_kwargs: list(passages),
            is_plausible_domain=lambda _url: True,
            anchor_query_to_topic=lambda query, _topic: query,
            fetch_linkup_precision_block=lambda *_args, **_kwargs: "",
            run_economist_step=lambda *_args, **_kwargs: "",
            run_scout=lambda *_args, **_kwargs: {},
            should_skip_quant_scout=lambda *_args, **_kwargs: True,
            clean_json_response=lambda value: value,
            DEFAULT_SYSTEM=self._DEFAULT_SYSTEM,
            NEWS_PREFERRED_DOMAINS=[],
            ACADEMIC_DOMAINS=[],
            QUANT_REPORT_TYPES=set(),
            logger=logging.getLogger("test_ag_sem_11"),
            execution_log_path=self.tmp_path / "execution.jsonl",
            feedback_log_path=self.tmp_path / "feedback.jsonl",
            kb_triggers_path=self.tmp_path / "kb.jsonl",
            policy_state_path=self.tmp_path / "policy.json",
            policy_journal_path=self.tmp_path / "policy_journal.jsonl",
        )


def _install_handoff_capture(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    original_packet = orchestrator.prepare_final_answer_packet_author_handoff_from_scope
    original_sufficiency = orchestrator.execute_sufficiency_judgment_handoff_from_scope

    def packet_wrapper(run_kernel: Any, runtime_scope: dict[str, Any], **kwargs: Any) -> Any:
        captured["run_kernel"] = run_kernel
        captured["packet_runtime_scope"] = dict(runtime_scope)
        return original_packet(run_kernel, runtime_scope, **kwargs)

    def sufficiency_wrapper(run_kernel: Any, runtime_scope: dict[str, Any], **kwargs: Any) -> Any:
        captured["sufficiency_runtime_scope"] = dict(runtime_scope)
        handoff = original_sufficiency(run_kernel, runtime_scope, **kwargs)
        captured["sufficiency_projection"] = dict(run_kernel.state.sufficiency_judgment_projection)
        return handoff

    monkeypatch.setattr(
        orchestrator,
        "prepare_final_answer_packet_author_handoff_from_scope",
        packet_wrapper,
    )
    monkeypatch.setattr(
        orchestrator,
        "execute_sufficiency_judgment_handoff_from_scope",
        sufficiency_wrapper,
    )
    return captured


def _run_offline_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    weakened_evidence: bool = False,
    stale_readable_official: bool = False,
) -> dict[str, Any]:
    captured = _install_handoff_capture(monkeypatch)
    harness = _OfflineOrdinaryHarness(tmp_path)
    harness.weakened_evidence = weakened_evidence
    harness.stale_readable_official = stale_readable_official
    orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode="Balanced",
            current_date="2026-06-22",
            session_id="ag-sem-11-session",
            run_id="ag-sem-11-run",
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
    return captured


def test_offline_run_pipeline_transactional_semantic_chain_reaches_real_sufficiency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _run_offline_pipeline(tmp_path, monkeypatch)
    kernel = captured["run_kernel"]
    state = kernel.state

    assert state.initial_answer_contract
    assert state.semantic_observation_admission_history
    assert state.component_coverage_history

    component_ref = state.initial_answer_contract["accepted_answer_component_refs"][0]
    assert component_ref.get("source_obligation_candidate_ids")
    assert "obligation:official_current" in component_ref["source_obligation_candidate_ids"]

    coverage = state.component_coverage_history[-1]
    assert coverage.get("source_obligation_status") == "satisfied"
    ledger_binding = coverage.get("evidence_ledger_binding") or {}
    assert ledger_binding.get("source_requirement_ids")

    sufficiency_projection = captured["sufficiency_projection"]
    assert sufficiency_projection.get("semantic_consumption")
    assert sufficiency_projection.get("semantic_state_facts_summary")
    assert sufficiency_projection["semantic_consumption"].get("schema_version")
    assert sufficiency_projection["semantic_state_facts_summary"].get(
        "semantic_state_facts_digest"
    )


def test_stale_readable_official_evidence_blocks_satisfied_source_obligation_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _run_offline_pipeline(tmp_path, monkeypatch, stale_readable_official=True)
    kernel = captured["run_kernel"]
    state = kernel.state

    assert not state.initial_answer_contract
    assert not state.semantic_observation_admission_history
    assert not state.component_coverage_history

    decision = captured["sufficiency_projection"].get("decision")
    assert decision != RunSufficiencyDecision.READY_DIRECT.value


def test_unqualified_or_stale_evidence_blocks_ready_direct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _run_offline_pipeline(tmp_path, monkeypatch, weakened_evidence=True)
    kernel = captured["run_kernel"]
    state = kernel.state

    assert not state.initial_answer_contract
    assert not state.semantic_observation_admission_history
    assert not state.component_coverage_history

    decision = captured["sufficiency_projection"].get("decision")
    assert decision != RunSufficiencyDecision.READY_DIRECT.value


def test_prerequisites_absent_leaves_no_orphan_initial_answer_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _run_offline_pipeline(tmp_path, monkeypatch)
    source_kernel = captured["run_kernel"]
    kernel = RunKernel.start(run_id="run:sem-11-absent", request_id="request:sem-11-absent")
    kernel.state.search_work_plan = dict(source_kernel.state.search_work_plan or {})
    scope = dict(captured["sufficiency_runtime_scope"])
    scope["final_top_evidence"] = []
    result = execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)
    assert result.status is OrdinarySemanticProducerHandoffStatus.SKIPPED
    assert result.skipped_reason == "preflight_failed"
    assert not kernel.state.initial_answer_contract
    assert not kernel.state.semantic_observation_admission_history
    assert not kernel.state.component_coverage_history


def test_preflight_bundle_builds_for_ag_check_01_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _run_offline_pipeline(tmp_path, monkeypatch)
    kernel = captured["run_kernel"]
    scope = captured["sufficiency_runtime_scope"]
    bundle = build_ordinary_semantic_producer_bundle(
        search_work_plan=kernel.state.search_work_plan,
        route_projection=kernel.state.projections.get("route_request"),
        run_contract_projection=scope["run_contract_projection"],
        final_top_evidence=scope["final_top_evidence"],
        evidence_ledger_projection=scope["evidence_ledger_projection"],
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        query=scope["query"],
        requested_mode=scope.get("strategy"),
    )
    assert bundle is not None
    assert bundle.question_meaning_record.record_id.startswith("qmr:")
    component = bundle.question_meaning_record.answer_components[0]
    assert component.source_obligation_candidate_ids
    assert "obligation:official_current" in component.source_obligation_candidate_ids
    assert bundle.component_coverage_record.coverage_state.value == "satisfied"
    assert bundle.component_coverage_record.source_obligation_status.value == "satisfied"
    assert bundle.component_coverage_record.evidence_ledger_binding.source_requirement_ids


def test_static_guard_no_new_run_kernel_semantic_authority() -> None:
    source = RUN_KERNEL.read_text(encoding="utf-8")
    forbidden = (
        "semantic_producer_history",
        "pre_sufficiency_semantic",
        "semantic_ledger_bridge",
        "ordinary_semantic_producer",
    )
    for token in forbidden:
        assert token not in source


def test_static_guard_no_pre_sufficiency_semantic_bridge() -> None:
    source = PRODUCER_MODULE.read_text(encoding="utf-8")
    assert "semantic_producer_history" not in source
    assert "pre_sufficiency_semantic" not in source
    assert "semantic_ledger_bridge" not in source
    assert "execute_ordinary_semantic_producer_handoff_from_scope" in source


def test_static_guard_producer_module_import_boundary() -> None:
    source = PRODUCER_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_roots = {
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
    assert imported.isdisjoint(forbidden_roots)


def test_static_guard_orchestrator_at_most_one_semantic_callsite() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    assert (
        source.count("execute_ordinary_semantic_producer_handoff_from_scope(") == 1
    )


def test_static_guard_no_compensating_rollback_paths() -> None:
    tree = ast.parse(PRODUCER_MODULE.read_text(encoding="utf-8"))
    forbidden_tokens = ("rollback", "revert", "undo_semantic", "cleanup_reduce")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.casefold()
            for token in forbidden_tokens:
                assert token not in lowered
        if isinstance(node, ast.Name):
            assert node.id.casefold() not in {"rollback", "revert", "undo_semantic"}


def test_transactional_handoff_raises_on_mid_chain_failure() -> None:
    from dataclasses import dataclass

    from core.ordinary_semantic_producer_runtime import OrdinarySemanticProducerBundle

    @dataclass
    class _FakeRecord:
        record_id: str
        record_digest: str

        def to_dict(self) -> dict[str, str]:
            return {"record_id": self.record_id, "record_digest": self.record_digest}

    @dataclass
    class _FakeObservation:
        observation_id: str
        observation_digest: str

        def to_dict(self) -> dict[str, str]:
            return {
                "observation_id": self.observation_id,
                "observation_digest": self.observation_digest,
            }

    kernel = RunKernel.start(run_id="run:sem-11-txn", request_id="request:sem-11-txn")
    kernel.state.search_work_plan = {
        "metadata": {
            "construction_metadata": {"implements_query_shape_classifier": True},
        }
    }
    bundle = OrdinarySemanticProducerBundle(
        question_meaning_record=_FakeRecord("qmr:test", "d" * 64),
        semantic_observation=_FakeObservation("observation:test", "e" * 64),
        sanitized_content_references=(),
        component_coverage_record=_FakeRecord("coverage:test", "f" * 64),
        dry_run_accepted_contract={},
        dry_run_admission_projection={},
    )
    scope = {
        "query": AG_CHECK_01_QUERY,
        "strategy": "Balanced",
        "run_contract_projection": {},
        "final_top_evidence": [{"url": "https://example.test", "text": "bounded", "title": "t"}],
        "evidence_ledger_projection": {},
    }
    with patch(
        "core.ordinary_semantic_producer_runtime.build_ordinary_semantic_producer_bundle",
        return_value=bundle,
    ):
        with patch.object(
            kernel,
            "authorize_initial_answer_contract_acceptance",
            side_effect=OrdinarySemanticProducerTransactionError("forced"),
        ):
            with pytest.raises(OrdinarySemanticProducerTransactionError):
                execute_ordinary_semantic_producer_handoff_from_scope(kernel, scope)
