from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig, RunDeps

CHAIN_CLASSIFICATIONS = {
    "RunAuthorityContract": "canonical_and_consumed",
    "EvidenceLedger": "canonical_and_consumed",
    "SearchJudgment": "canonical_and_consumed",
    "SufficiencyJudgment": "canonical_and_consumed",
    "FinalAnswerPacket": "canonical_and_consumed",
    "ordinary Author execution": "canonical_and_consumed",
    "final RunOutcome/report/post-author state": "canonical_and_consumed",
}
AF_COMPONENT_LANE_RELATIONSHIP = "partially_shared_and_bridgeable"
POST_AUTHOR_CITATION_SURVIVAL_CLASSIFICATION = "trace_or_projection_only"

RAW_AUTHOR_RESPONSE = (
    "AG_CHECK_01_AUTHOR_FINAL_REPORT: Example Program remains governed by the "
    "retrieved official rule. The official evidence says the rule is current, "
    "and this answer cites only packet-provided source identity "
    "[[1]](https://official.example/rule). The answer stays narrow, avoids new "
    "evidence, and leaves any unresolved source obligations caveated."
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
class _OfflineOrdinaryHarness:
    tmp_path: Path
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    search_calls: list[dict[str, Any]] = field(default_factory=list)
    author_prompts: list[str] = field(default_factory=list)
    author_kwargs: list[dict[str, Any]] = field(default_factory=list)
    forbidden_live_calls: list[str] = field(default_factory=list)

    query: str = "What is the current official rule for Example Program?"
    core_topic: str = "Example Program current official rule"
    primary_entity: str = "Example Program"

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
            return json.dumps({"queries": [f"{self.primary_entity} official current rule"]})
        if system_prompt == DEFAULT_SYSTEM["expander"] or "research gap detector" in system_prompt:
            return json.dumps({"component_queries": [], "reasoning": "offline fixture sufficient"})
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return json.dumps({"is_sufficient": True, "new_queries": []})
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            return "Analysis is limited to the retrieved official Example Program rule."
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if kwargs.get("stream"):
            self.author_prompts.append(prompt)
            self.author_kwargs.append(dict(kwargs))
            return RAW_AUTHOR_RESPONSE
        raise AssertionError(f"unexpected model call in offline checkpoint: {system_prompt!r}")

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
            },
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
            fetch_linkup_precision_block=self.forbidden_live_dependency("fetch_linkup_precision_block"),
            run_economist_step=self.forbidden_live_dependency("run_economist_step"),
            run_scout=self.forbidden_live_dependency("run_scout"),
            should_skip_quant_scout=lambda *_args, **_kwargs: True,
            clean_json_response=lambda value: value,
            DEFAULT_SYSTEM=DEFAULT_SYSTEM,
            NEWS_PREFERRED_DOMAINS=[],
            ACADEMIC_DOMAINS=[],
            QUANT_REPORT_TYPES=set(),
            logger=logging.getLogger("test_ag_check_01_offline_ordinary_authority_path"),
            execution_log_path=self.tmp_path / "execution.jsonl",
            feedback_log_path=self.tmp_path / "feedback.jsonl",
            kb_triggers_path=self.tmp_path / "kb.jsonl",
            policy_state_path=self.tmp_path / "policy.json",
            policy_journal_path=self.tmp_path / "policy_journal.jsonl",
        )


def _execution_event_from_log(path: Path) -> dict[str, Any]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return next(row for row in rows if row.get("event") == "execution")


def _install_handoff_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    captured: dict[str, Any] = {
        "packet_handoff_called": False,
        "author_handoff_called": False,
    }
    original_packet = orchestrator.prepare_final_answer_packet_author_handoff_from_scope
    original_author = orchestrator.execute_author_handoff_from_scope

    def packet_wrapper(run_kernel: Any, runtime_scope: dict[str, Any], **kwargs: Any) -> Any:
        captured["packet_handoff_called"] = True
        captured["run_kernel"] = run_kernel
        captured["packet_runtime_scope"] = dict(runtime_scope)
        handoff = original_packet(run_kernel, runtime_scope, **kwargs)
        captured["packet_handoff"] = handoff
        return handoff

    def author_wrapper(run_kernel: Any, runtime_scope: dict[str, Any], **kwargs: Any) -> Any:
        captured["author_handoff_called"] = True
        captured["author_runtime_scope"] = dict(runtime_scope)
        handoff = original_author(run_kernel, runtime_scope, **kwargs)
        captured["author_handoff"] = handoff
        return handoff

    monkeypatch.setattr(
        orchestrator,
        "prepare_final_answer_packet_author_handoff_from_scope",
        packet_wrapper,
    )
    monkeypatch.setattr(orchestrator, "execute_author_handoff_from_scope", author_wrapper)
    return captured


def _classification_report(captured: dict[str, Any], outcome: Any) -> dict[str, Any]:
    kernel = captured["run_kernel"]
    state = kernel.state
    return {
        "chain_classifications": dict(CHAIN_CLASSIFICATIONS),
        "af_component_lane_relationship": AF_COMPONENT_LANE_RELATIONSHIP,
        "post_author_citation_survival_classification": (POST_AUTHOR_CITATION_SURVIVAL_CLASSIFICATION),
        "runtime_consumer_observed": {
            "FinalAnswerPacket": "AuthorExecutor",
            "ordinary Author execution": "RunKernel.AuthorObservation",
            "final RunOutcome/report/post-author state": "build_run_outcome_from_scope",
        },
        "authority_owners_observed": {
            "RunAuthorityContract": state.run_contract_projection.get("owner"),
            "EvidenceLedger": state.evidence_ledger.to_projection().to_dict().get("owner"),
            "SearchJudgment": state.search_judgment_projection.get("owner"),
            "SufficiencyJudgment": state.sufficiency_judgment_projection.get("owner"),
            "FinalAnswerPacket": state.final_answer_authority_projection.get("owner"),
            "ordinary Author execution": state.final_answer_outcome.get("owner"),
        },
        "ordinary_author_implementation": "core.author_execution_runtime.execute_author_action",
        "report_hash_observed": state.final_answer_outcome.get("report_hash"),
        "run_outcome_report_observed": bool(outcome.report),
    }


def test_ag_check_01_offline_run_pipeline_consumes_packet_constrained_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_handoff_capture(monkeypatch)
    harness = _OfflineOrdinaryHarness(tmp_path)

    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode="Balanced",
            current_date="2026-06-22",
            session_id="ag-check-01-session",
            run_id="ag-check-01-run",
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
    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")

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
    packet_handoff = captured["packet_handoff"]
    author_handoff = captured["author_handoff"]
    author_scope = captured["author_runtime_scope"]
    packet_scope = captured["packet_runtime_scope"]

    assert outcome.run_id == "ag-check-01-run"
    assert outcome.report == RAW_AUTHOR_RESPONSE
    assert log_entry["execution_trace"]["final_output_preview"].startswith("AG_CHECK_01_AUTHOR_FINAL_REPORT")
    assert author_handoff.report == RAW_AUTHOR_RESPONSE
    assert state.final_answer_outcome["report_hash"]
    assert state.final_answer_outcome["final_text_included"] is False
    assert state.final_answer_outcome["packet_id"] == packet_handoff.packet.packet_id

    assert state.run_contract_projection["owner"] == "RunKernel.RunAuthorityContract"
    assert state.run_contract_projection["canonical_state"] is True
    assert state.run_contract_projection["trace_only"] is False
    assert state.run_contract_projection["storage_only"] is False
    assert state.run_contract_projection["contract_id"]

    ledger_projection = state.evidence_ledger.to_projection().to_dict()
    assert ledger_projection["owner"] == "RunKernel.EvidenceLedger"
    assert ledger_projection["candidate_count"] > 0
    assert packet_scope["evidence_ledger_projection"]["owner"] == "RunKernel.EvidenceLedger"

    assert state.search_judgment_projection["owner"] == "RunKernel.RunAuthoritySearchJudgment"
    assert state.search_judgment_projection["canonical_state"] is True
    assert state.search_judgment_projection["trace_only"] is False
    assert state.sufficiency_judgment_projection["owner"] == ("RunKernel.RunAuthoritySufficiencyJudgment")
    assert state.sufficiency_judgment_projection["canonical_state"] is True
    assert state.sufficiency_judgment_projection["trace_only"] is False
    assert state.sufficiency_judgment_projection["decision"]
    assert state.sufficiency_judgment_projection["decision"] == (state.final_answer_packet["sufficiency_decision"])

    assert packet_handoff.packet.packet_id == state.final_answer_packet["packet_id"]
    assert packet_handoff.author_payload.packet_id == state.final_answer_packet["packet_id"]
    assert state.final_answer_authority_projection["owner"] == "RunKernel.FinalAnswerPacket"
    assert state.final_answer_authority_projection["canonical_state"] is True
    assert state.final_answer_authority_projection["trace_only"] is False
    assert state.final_answer_authority_projection["author_payload_ref"]["packet_id"] == (
        packet_handoff.packet.packet_id
    )
    assert state.final_answer_authority_projection["author_payload_ref"]["prompt_text_included"] is False

    assert "FINAL ANSWER PACKET AUTHORITY" in harness.author_prompts[0]
    assert author_scope["final_answer_packet_action"] is packet_handoff.action
    assert author_scope["final_answer_author_payload"] is packet_handoff.author_payload
    assert state.author_observation["owner"] == "RunKernel.AuthorExecutor"
    assert state.author_observation["packet_id"] == packet_handoff.packet.packet_id
    assert state.author_observation["authority_payload_ref"] == (packet_handoff.author_payload.authority_payload)
    assert state.author_observation["sufficiency_decision"] == (packet_handoff.author_payload.sufficiency_decision)
    assert state.author_observation["citation_source_ids"] == list(packet_handoff.author_payload.citation_source_ids)
    assert state.author_observation["prompt_text_included"] is False
    assert state.author_observation["final_text_included"] is False

    trace_packet = outcome.execution_trace["final_answer_packet"]
    assert trace_packet["packet_id"] == packet_handoff.packet.packet_id
    assert trace_packet["canonical_state"] is True
    assert trace_packet["trace_mode"] == "run_kernel_final_answer_packet_projection"
    assert outcome.execution_trace["final_answer_source_ids_used"] == ["1"]
    assert "final_authority_citation_survival" in outcome.execution_trace

    for attr in (
        "followup_author_evidence_content_bridge_state",
        "followup_author_invocation_construction_state",
        "followup_author_model_request_assembly_state",
        "followup_author_execution_from_af4d_state",
        "followup_author_response_finalization_state",
    ):
        assert getattr(state, attr) == {}

    canonical_trace = json.dumps(kernel.to_trace_fragment(), sort_keys=True)
    execution_trace = json.dumps(outcome.execution_trace, sort_keys=True)
    for forbidden in (
        harness.author_prompts[0],
        "FINAL ANSWER PACKET AUTHORITY",
        "provider_payload_text",
        "OPENAI_API_KEY",
        "TAVILY_API_KEY",
    ):
        assert forbidden not in canonical_trace
    assert state.initial_answer_contract
    assert state.semantic_observation_admission_history
    assert state.component_coverage_history
    assert "bounded_excerpt" in canonical_trace
    assert RAW_AUTHOR_RESPONSE not in canonical_trace
    assert harness.author_prompts[0] not in execution_trace
    for retained_flag in (
        '"prompt_text_retained": true',
        '"model_response_text_retained": true',
        '"provider_payload_retained": true',
        '"raw_provider_payloads_retained": true',
    ):
        assert retained_flag not in canonical_trace
        assert retained_flag not in execution_trace

    diagnostic = _classification_report(captured, outcome)
    assert diagnostic["chain_classifications"] == CHAIN_CLASSIFICATIONS
    assert diagnostic["af_component_lane_relationship"] == AF_COMPONENT_LANE_RELATIONSHIP
    assert diagnostic["post_author_citation_survival_classification"] == (POST_AUTHOR_CITATION_SURVIVAL_CLASSIFICATION)
    assert diagnostic["authority_owners_observed"] == {
        "RunAuthorityContract": "RunKernel.RunAuthorityContract",
        "EvidenceLedger": "RunKernel.EvidenceLedger",
        "SearchJudgment": "RunKernel.RunAuthoritySearchJudgment",
        "SufficiencyJudgment": "RunKernel.RunAuthoritySufficiencyJudgment",
        "FinalAnswerPacket": "RunKernel.FinalAnswerPacket",
        "ordinary Author execution": "RunKernel.AuthorObservation",
    }
