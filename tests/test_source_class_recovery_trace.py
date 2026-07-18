from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.db import RUN_COLUMNS, execution_jsonl_to_run_row
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig, RunDeps
from core.run_controller import RunController
from core.source_class_recovery_diagnostics import (
    SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY,
)
from core.source_class_recovery_executor import execute_source_class_recovery_action
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle
from tests.controller_diagnostics_contract_utils import (
    assert_execution_trace_payload_contract,
)

RECOVERY_FIELDS = {
    "source_class_recovery_recommended",
    "source_class_recovery_shadow_mode",
    "missing_expected_source_classes",
    "source_class_recovery_reason",
    "source_class_recovery_queries",
    "source_class_recovery_query_count",
    "source_class_recovery_trigger_fields",
}

ACTIVE_RECOVERY_FIELDS = {
    "active_source_class_recovery_considered",
    "active_source_class_recovery_eligible",
    "active_source_class_recovery_used",
    "active_source_class_recovery_reason",
    "active_source_class_recovery_skip_reason",
    "active_source_class_recovery_blockers",
    "active_source_class_recovery_missing_classes",
    "active_source_class_recovery_queries",
    "active_source_class_recovery_result_count",
    "active_source_class_recovery_new_url_count",
    "active_source_class_recovery_provider_role",
    "active_source_class_recovery_search_depth",
    "active_source_class_recovery_attempt_count",
    "recovered_candidate_domain_preview",
    "recovered_source_tier_counts",
    "recovered_source_class_counts",
    "recovered_official_or_primary_count",
    "recovered_accepted_url_count",
    "recovered_promoted_source_count",
    "recovery_source_quality_status",
}

SOURCE_CLASS_OBSERVABILITY_FIELDS = {
    "expected_source_classes_raw",
    "source_class_gap_candidates",
    "source_class_satisfaction_basis",
    "source_class_underfire_shadow",
    "source_class_underfire_reasons",
    "source_class_underfire_blockers",
    "final_official_source_count",
    "final_primary_source_count",
    "final_archival_source_count",
    "final_legal_or_regulatory_source_count",
    "source_class_satisfaction_counts",
    "source_class_satisfaction_status",
    "source_class_satisfaction_strength_counts",
    "source_class_strong_satisfaction_counts",
    "source_class_weak_satisfaction_counts",
    "source_class_secondary_only_counts",
}

SOURCE_CLASS_RECOVERY_CANDIDATE_V2_KEY = "source_class_recovery_candidate_v2"

AUTHOR_DIAGNOSTIC_LEAK_MARKERS = (
    "source_class_recovery",
    "active_source_class_recovery",
    "source_class_recovery_candidate_v2",
    "source_class_recovery_validation_l1",
    "class_intent_catalog",
    "source_class_underfire",
    "source_class_gap_candidates",
    "expected_source_classes_raw",
    "source_class_satisfaction_status",
    "source_class_satisfaction_strength_counts",
    "source_class_strong_satisfaction_counts",
    "source_class_weak_satisfaction_counts",
    "source_class_secondary_only_counts",
    "run_source_class_recovery",
    "blocked_with_reason",
    "no_action",
    "missing_expected_source_class",
    "provider_attempts_by_role",
    "provider_diagnostics",
    "source_class_recovery_queries",
    "controller_diagnostics",
    "planned_vs_observed",
    "task_ledger",
    "quantitative_packet",
    "QUANTITATIVE FRAMEWORK",
    "economist_v1",
)


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("BRAVE_API_KEY", "TAVILY_API_KEY", "LINKUP_API_KEY", "EXA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)


class _TraceHarness:
    def __init__(
        self,
        tmp_path: Path,
        *,
        query: str,
        core_topic: str,
        primary_entity: str,
        researcher_query: str,
        router_intent: str = "general",
        router_report_type: str = "general_research",
        router_query_type: str = "other",
        source_tiers: list[str] | None = None,
        domains: list[str] | None = None,
        source_texts: list[str] | None = None,
        recovery_source_tiers: list[str] | None = None,
        recovery_domains: list[str] | None = None,
        recovery_scores: list[float] | None = None,
    ) -> None:
        self.tmp_path = tmp_path
        self.query = query
        self.core_topic = core_topic
        self.primary_entity = primary_entity
        self.researcher_query = researcher_query
        self.router_intent = router_intent
        self.router_report_type = router_report_type
        self.router_query_type = router_query_type
        self.source_tiers = list(source_tiers or ["secondary", "unknown", "secondary", "unknown"])
        self.domains = list(domains or ["regionalnews.example", "analysis.example"])
        self.source_texts = list(source_texts or [])
        self.recovery_source_tiers = list(recovery_source_tiers or ["official"])
        self.recovery_domains = list(recovery_domains or ["official.gov"])
        self.recovery_scores = list(recovery_scores or [])
        self.search_calls: list[dict[str, Any]] = []
        self.analyst_calls = 0
        self.author_calls = 0
        self.author_prompts: list[str] = []

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt == DEFAULT_SYSTEM["router"]:
            return json.dumps(
                {
                    "intent": self.router_intent,
                    "report_type": self.router_report_type,
                    "image_mode": "none",
                    "core_topic": self.core_topic,
                    "is_academic": False,
                    "query_type": self.router_query_type,
                    "entities": [self.primary_entity],
                    "primary_entity": self.primary_entity,
                }
            )
        if system_prompt == "You are a concise title generator.":
            return f"{self.primary_entity} Trace"
        if system_prompt == DEFAULT_SYSTEM["researcher"]:
            return json.dumps({"queries": [self.researcher_query]})
        if "research gap detector" in system_prompt:
            return json.dumps({"component_queries": [], "reasoning": "sufficient"})
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return json.dumps({"is_sufficient": True, "new_queries": []})
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            self.analyst_calls += 1
            return f"Analysis remains scoped to {self.primary_entity}."
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if kwargs.get("stream"):
            self.author_calls += 1
            self.author_prompts.append(prompt)
            return (
                f"{self.primary_entity} answer based on retrieved secondary evidence. "
                "No diagnostic telemetry is user visible."
            )
        return "ok"

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
        provider_role = kwargs.get("provider_role")
        self.search_calls.append(
            {
                "queries": list(queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "include_domains": list(_args[0] or []) if len(_args) >= 1 else [],
                "exclude_domains": list(_args[1] or []) if len(_args) >= 2 else [],
                "search_providers": list(kwargs.get("search_providers") or []),
                "provider_role": provider_role,
                "exa_domain_filter": list(kwargs.get("exa_domain_filter") or []),
                "linkup_depth_override": kwargs.get("linkup_depth_override"),
            }
        )
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is None and len(_args) >= 4:
            seen_urls = _args[3]

        provider_diagnostics = kwargs.get("provider_diagnostics")
        call_index = len(self.search_calls)
        out: list[dict[str, Any]] = []
        if provider_role == "source_class_recovery":
            tiers = self.recovery_source_tiers
            domains = self.recovery_domains
            url_prefix = "official-recovery"
        else:
            tiers = self.source_tiers
            domains = self.domains
            url_prefix = "story"
        for idx, tier in enumerate(tiers):
            domain = domains[idx % len(domains)]
            url = f"https://{domain}/{url_prefix}-{idx}"
            if seen_urls is not None:
                seen_urls.add(url)
            out.append(
                {
                    "title": f"{self.primary_entity} evidence {idx}",
                    "url": url,
                    "text": (
                        self.source_texts[idx]
                        if idx < len(self.source_texts)
                        else (
                            f"{self.primary_entity} on-topic evidence for {self.core_topic} "
                            f"with enough detail for synthesis chunk {idx}."
                        )
                    ),
                    "score": (
                        self.recovery_scores[idx]
                        if provider_role == "source_class_recovery"
                        and idx < len(self.recovery_scores)
                        else 0.42
                        if provider_role == "source_class_recovery"
                        else 1.0 - (idx * 0.01)
                    ),
                    "credibility": 3,
                    "source_tier": tier,
                    "_provider": "tavily",
                }
            )
        if provider_diagnostics is not None:
            provider_diagnostics.append(
                {
                    "schema_version": "provider_diagnostics_v1",
                    "provider": "tavily",
                    "provider_role": provider_role or "unknown",
                    "cost_phase": "retrieval",
                    "query_count": len(queries),
                    "query_preview": queries[0] if queries else "",
                    "depth": search_depth,
                    "output_type": "searchResults",
                    "max_results": results_per_query,
                    "answer_endpoint_used": False,
                    "raw_content_requested": True,
                    "success": True,
                    "failure_type": None,
                    "result_count": len(out),
                    "image_count": 0,
                    "new_url_count": len(out),
                    "accepted_url_count": len(out),
                    "logical_attempt_count": 1,
                    "new_source_count": len(out),
                    "call_index": call_index,
                }
            )
        return out

    def deps(self) -> RunDeps:
        return RunDeps(
            ask_model=self.ask_model,
            embed_texts=self.embed_texts,
            compute_similarities=lambda *_args, **_kwargs: [1.0],
            process_search_queries=self.process_search_queries,
            filter_top_evidence=lambda passages, *_args, **_kwargs: list(passages),
            is_plausible_domain=lambda _url: True,
            anchor_query_to_topic=lambda q, _topic: q,
            fetch_linkup_precision_block=lambda *_args, **_kwargs: "",
            run_scout=lambda *_args, **_kwargs: {},
            should_skip_quant_scout=lambda *_args, **_kwargs: False,
            clean_json_response=lambda value: value,
            DEFAULT_SYSTEM=DEFAULT_SYSTEM,
            NEWS_PREFERRED_DOMAINS=[],
            ACADEMIC_DOMAINS=[],
            QUANT_REPORT_TYPES={"quantitative_comparison", "benchmark"},
            logger=logging.getLogger("test_source_class_recovery_trace"),
            execution_log_path=self.tmp_path / "execution.jsonl",
            feedback_log_path=self.tmp_path / "feedback.jsonl",
            kb_triggers_path=self.tmp_path / "kb.jsonl",
            policy_state_path=self.tmp_path / "policy.json",
            policy_journal_path=self.tmp_path / "policy_journal.jsonl",
            provider_availability={"tavily": True},
        )


def _execution_event_from_log(path: Path) -> dict[str, Any]:
    return next(
        row
        for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
        if row.get("event") == "execution"
    )


def _run_case(
    tmp_path: Path,
    *,
    mode: str = "Balanced",
    **harness_kwargs: Any,
) -> tuple[Any, _TraceHarness, dict[str, Any]]:
    harness = _TraceHarness(tmp_path, **harness_kwargs)
    outcome = orchestrator.run_pipeline(
        RunConfig(
            query=harness.query,
            mode=mode,
            current_date="2026-05-18",
            use_reasoning=False,
        ),
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )
    log_entry = _execution_event_from_log(tmp_path / "execution.jsonl")
    return outcome, harness, log_entry


def _all_iteration_queries(trace: dict[str, Any]) -> list[str]:
    return [
        query
        for queries in trace["queries_per_iteration"].values()
        for query in queries
    ]


def _recovery_field_projection(trace: dict[str, Any]) -> dict[str, Any]:
    return {field: trace[field] for field in RECOVERY_FIELDS}


def _active_recovery_field_projection(trace: dict[str, Any]) -> dict[str, Any]:
    return {field: trace[field] for field in ACTIVE_RECOVERY_FIELDS}


def _recovered_passages(passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        passage
        for passage in passages
        if passage.get("retrieval_stage") == "source_class_recovery"
    ]


def _assert_recovery_author_diagnostics_do_not_leak(
    *,
    outcome: Any,
    harness: _TraceHarness,
) -> None:
    assert harness.author_prompts
    haystacks = [outcome.report, *harness.author_prompts]
    for text in haystacks:
        for marker in AUTHOR_DIAGNOSTIC_LEAK_MARKERS:
            assert marker not in text


def test_official_current_rules_recovery_executes_once_and_merges_additively(
    tmp_path: Path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    trace = outcome.execution_trace
    assert trace["source_class_recovery_shadow_mode"] is True
    assert trace["source_class_recovery_recommended"] is False
    assert trace["missing_expected_source_classes"] == []
    assert trace["source_class_recovery_queries"] == []
    assert trace["source_class_recovery_query_count"] == 0
    assert trace["active_source_class_recovery_considered"] is True
    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_skip_reason"] is None
    assert trace["active_source_class_recovery_blockers"] == []
    assert trace["active_source_class_recovery_missing_classes"] == [
        "official_current_rules"
    ]
    assert trace["active_source_class_recovery_queries"]
    assert trace["active_source_class_recovery_result_count"] > 0
    assert trace["active_source_class_recovery_new_url_count"] > 0
    assert trace["active_source_class_recovery_provider_role"] == (
        "source_class_recovery"
    )
    assert trace["active_source_class_recovery_search_depth"] == "basic"
    assert trace["active_source_class_recovery_attempt_count"] == 1

    diagnostic_queries = set(trace["active_source_class_recovery_queries"])
    assert diagnostic_queries.isdisjoint(_all_iteration_queries(trace))
    assert diagnostic_queries.isdisjoint(harness.search_calls[0]["queries"])
    assert len(harness.search_calls) == 2
    assert harness.search_calls[0]["search_providers"] == ["tavily"]
    assert harness.search_calls[0]["provider_role"] == "main_retrieval"
    assert harness.search_calls[0]["search_depth"] == "basic"
    assert harness.search_calls[0]["results_per_query"] == 6
    assert harness.search_calls[1]["queries"] == trace[
        "active_source_class_recovery_queries"
    ]
    assert harness.search_calls[1]["search_providers"] == ["tavily"]
    assert harness.search_calls[1]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[1]["search_depth"] == "basic"
    assert harness.search_calls[1]["results_per_query"] == 6
    assert harness.search_calls[1]["linkup_depth_override"] is None
    assert trace["queries_per_iteration"] == {"1": harness.search_calls[0]["queries"]}
    assert trace["pass_providers"] == [["tavily"]]
    assert trace["iterations_run"] == 1
    assert trace["provider_attempts_by_role"]["source_class_recovery"] == 1
    assert any(
        attempt["provider_role"] == "source_class_recovery"
        for attempt in trace["provider_diagnostics"]
    )
    assert trace["official_evidence_found"] is True
    assert trace["source_tier_counts"]["official"] == 1
    assert len(outcome.top_passages) == 5
    recovered = _recovered_passages(outcome.top_passages)
    assert len(recovered) == 1
    assert recovered[0]["source_tier"] == "official"
    assert recovered[0]["score"] == 0.42
    assert any(
        passage.get("retrieval_stage") != "source_class_recovery"
        for passage in outcome.top_passages
    )
    assert trace["supplemental_ran"] is False
    assert trace["weak_corpus_recovery_considered"] is False
    assert trace["weak_corpus_recovery_used"] is False
    assert trace["corpus_weak"] is False
    assert harness.analyst_calls == 1
    assert harness.author_calls == 1
    assert trace["economist_output_used_as_analysis"] is False
    assert trace["analyst_skipped_after_economist"] is False
    _assert_recovery_author_diagnostics_do_not_leak(
        outcome=outcome,
        harness=harness,
    )


def test_ag11_answer_contract_legal_gap_triggers_existing_recovery_path(
    tmp_path: Path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query=(
            "What does the Public Offices Act say about membership rules and "
            "current statutory obligations?"
        ),
        core_topic="Public Offices Act membership rules",
        primary_entity="Public Offices Act",
        researcher_query="Public Offices Act membership rules explainer",
        router_intent="regulatory",
        router_query_type="other",
        source_tiers=["secondary", "secondary", "secondary", "secondary"],
        domains=["analysis.example", "news.example"],
        recovery_source_tiers=["official"],
        recovery_domains=["official.gov"],
    )

    trace = outcome.execution_trace

    assert trace["active_source_class_recovery_considered"] is True
    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_reason"].startswith(
        "answer_contract_legal_text_gap:"
    )
    assert "legal_or_regulatory_text" in trace[
        "active_source_class_recovery_missing_classes"
    ]
    assert trace["active_source_class_recovery_attempt_count"] == 1
    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["queries"] == trace[
        "active_source_class_recovery_queries"
    ]
    assert harness.search_calls[1]["search_providers"] == trace["pass_providers"][-1]
    assert harness.search_calls[1]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[1]["search_depth"] == trace[
        "active_source_class_recovery_search_depth"
    ]
    assert harness.search_calls[1]["linkup_depth_override"] is None


def test_candidate_v2_trace_is_nested_and_active_fields_stay_unchanged(
    tmp_path: Path,
) -> None:
    outcome, harness, log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    trace = outcome.execution_trace
    packet = trace[SOURCE_CLASS_RECOVERY_CANDIDATE_V2_KEY]
    assert packet["schema_version"] == "source_class_recovery_candidate_v2"
    assert packet["shadow_mode"] is True
    assert packet["source_class_recovery_candidate_v2_shadow"] is False
    assert packet["source_class_recovery_candidate_v2_query_count"] == 0
    assert packet["source_class_recovery_candidate_v2_query_source"] == "none"
    assert "active_recovery_already_used" in packet[
        "source_class_recovery_candidate_v2_blockers"
    ]

    assert trace["source_class_recovery_recommended"] is False
    assert trace["missing_expected_source_classes"] == []
    assert trace["source_class_recovery_queries"] == []
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_missing_classes"] == [
        "official_current_rules"
    ]
    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["queries"] == trace[
        "active_source_class_recovery_queries"
    ]

    assert _recovery_field_projection(log_entry["execution_trace"]) == (
        _recovery_field_projection(trace)
    )
    assert _active_recovery_field_projection(log_entry["execution_trace"]) == (
        _active_recovery_field_projection(trace)
    )
    assert SOURCE_CLASS_RECOVERY_CANDIDATE_V2_KEY not in log_entry


def test_issuer_company_materials_without_canonical_permission_does_not_dispatch(
    tmp_path: Path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query=(
            "Use company filings and reported company materials to compare the "
            "company-reported margin metric from the latest quarterly results."
        ),
        core_topic="reported company margin metric",
        primary_entity="ExampleCo",
        researcher_query="ExampleCo margin metric analyst coverage",
        source_tiers=["secondary", "secondary", "unknown"],
        domains=["analysis.example", "marketnews.example"],
        recovery_source_tiers=["official"],
        recovery_domains=["ir.exampleco.com"],
    )

    trace = outcome.execution_trace
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_missing_classes"] == [
        "issuer_filings_or_company_materials"
    ]
    assert trace["source_class_recovery_dispatch_authorized"] is False
    assert trace["source_class_recovery_dispatch_reason"] == (
        "canonical_recovery_not_required"
    )
    assert trace["active_source_class_recovery_result_count"] == 0
    assert trace["active_source_class_recovery_new_url_count"] == 0
    assert len(harness.search_calls) == 1
    assert "source_class_recovery" not in trace["provider_attempts_by_role"]

    recovered = _recovered_passages(outcome.top_passages)
    assert recovered == []


def test_primary_source_documents_recovery_is_additive_without_boosting_or_pinning(
    tmp_path: Path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query="Find primary sources and primary documents for the policy change.",
        core_topic="policy change evidence",
        primary_entity="Policy Change",
        researcher_query="Policy Change analysis background",
        source_tiers=["secondary", "secondary", "secondary"],
        domains=["analysis.example", "news.example"],
        recovery_source_tiers=["secondary"],
        recovery_domains=["archives.example"],
        recovery_scores=[0.24],
    )

    trace = outcome.execution_trace
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_missing_classes"] == [
        "primary_source_documents"
    ]
    assert trace["active_source_class_recovery_result_count"] == 1
    assert trace["active_source_class_recovery_new_url_count"] == 1
    assert len(harness.search_calls) == 2
    assert harness.search_calls[1]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[1]["search_providers"] == trace["pass_providers"][-1]
    assert harness.search_calls[1]["search_depth"] == trace[
        "active_source_class_recovery_search_depth"
    ]
    assert harness.search_calls[1]["linkup_depth_override"] is None

    recovered = _recovered_passages(outcome.top_passages)
    originals = [
        passage
        for passage in outcome.top_passages
        if passage.get("retrieval_stage") != "source_class_recovery"
    ]
    assert len(recovered) == 1
    assert len(originals) == 3
    assert [passage["score"] for passage in originals] == [1.0, 0.99, 0.98]
    assert recovered[0]["score"] == 0.24
    assert outcome.top_passages[-1] == recovered[0]
    assert [passage["source_id"] for passage in outcome.top_passages] == [1, 2, 3, 4]
    assert all("source_id" in passage for passage in outcome.top_passages)


def test_source_class_recovery_controller_mirror_is_passive_and_trace_compatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    original_record = orchestrator.record_source_class_recovery_recommendation

    def forbidden_trace_fragment(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("RunController.to_trace_fragment must stay unused")

    def capture_record(*args: Any, **kwargs: Any) -> Any:
        result = original_record(*args, **kwargs)
        controller = args[0]
        captured["controller"] = controller.to_dict()
        captured["telemetry"] = deepcopy(
            dict(kwargs["source_class_recovery_telemetry"])
        )
        captured["evidence_signals"] = deepcopy(
            dict(kwargs["source_class_evidence_signals"])
        )
        return result

    monkeypatch.setattr(orchestrator.RunController, "to_trace_fragment", forbidden_trace_fragment)
    monkeypatch.setattr(
        orchestrator,
        "record_source_class_recovery_recommendation",
        capture_record,
    )

    outcome, harness, log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    controller = captured["controller"]
    decision = next(
        record
        for record in controller["ledger"]["decision_records"]
        if record["name"] == "source_class_recovery"
    )
    lifecycle_decision = next(
        record
        for record in controller["ledger"]["decision_records"]
        if record["name"] == "run_source_class_recovery"
    )
    lifecycle_action = next(
        record
        for record in controller["ledger"]["retrieval_actions"]
        if record["name"] == "source_class_recovery"
    )
    legacy_recovery_fields = {
        field: captured["telemetry"][field] for field in RECOVERY_FIELDS
    }

    assert decision["name"] == "source_class_recovery"
    assert decision["active"] is False
    assert decision["shadow"] is True
    assert decision["reason"] is None
    assert decision["signals"]["missing_expected_source_classes"] == []
    assert decision["signals"]["source_tier_counts"] == captured["evidence_signals"][
        "source_tier_counts"
    ]
    assert decision["recommended_actions"] == []
    assert lifecycle_decision["active"] is True
    assert lifecycle_decision["shadow"] is False
    assert lifecycle_decision["reason"] == (
        "missing_expected_source_class:official_current_rules"
    )
    assert lifecycle_decision["metadata"]["execution"] == "minimal_active_controller"
    assert lifecycle_decision["metadata"]["decision"] == "run_source_class_recovery"
    assert lifecycle_action["active"] is True
    assert lifecycle_action["shadow"] is False
    assert lifecycle_action["provider_role"] == "source_class_recovery"
    assert lifecycle_action["search_depth"] == "basic"
    assert lifecycle_action["queries"] == outcome.execution_trace[
        "active_source_class_recovery_queries"
    ]
    assert lifecycle_action["metadata"]["execution"] == (
        "orchestrator_adapter_executed"
    )
    assert lifecycle_action["metadata"]["result_count"] == 1
    assert lifecycle_action["metadata"]["new_url_count"] == 1

    fact_records = controller["ledger"]["fact_records"]
    active_facts = {
        record["name"]: record["value"]
        for record in fact_records
        if record["stage"] == "source_class_recovery"
        and record["metadata"].get("source") == "orchestrator_adapter"
    }
    assert active_facts == {
        "execution_attempted": True,
        "result_count": 1,
        "new_url_count": 1,
        "provider_role": "source_class_recovery",
        "search_depth": "basic",
    }
    provider_records = [
        record
        for record in controller["ledger"]["provider_records"]
        if record["stage"] == "source_class_recovery"
    ]
    assert len(provider_records) == 1
    assert provider_records[0]["provider"] == "tavily"
    assert provider_records[0]["provider_role"] == "source_class_recovery"
    assert provider_records[0]["metadata"]["search_depth"] == "basic"
    assert provider_records[0]["metadata"]["queries"] == outcome.execution_trace[
        "active_source_class_recovery_queries"
    ]

    assert _recovery_field_projection(outcome.execution_trace) == legacy_recovery_fields
    assert _recovery_field_projection(log_entry["execution_trace"]) == legacy_recovery_fields
    assert len(harness.search_calls) == 2
    assert harness.search_calls[0]["provider_role"] == "main_retrieval"
    assert harness.search_calls[0]["search_depth"] == "basic"
    assert harness.search_calls[0]["results_per_query"] == 6
    assert harness.search_calls[1]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[1]["search_depth"] == "basic"
    assert harness.search_calls[1]["results_per_query"] == 6
    assert_execution_trace_payload_contract(outcome.execution_trace)
    assert_execution_trace_payload_contract(log_entry["execution_trace"])


def test_polling_average_recovery_recommendation_without_canonical_permission_does_not_dispatch(
    tmp_path: Path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query="For the governor race, separate the latest poll from broader polling averages.",
        core_topic="governor race polling",
        primary_entity="governor race",
        researcher_query="governor race polling news",
        router_query_type="other",
        source_tiers=["secondary", "secondary", "secondary", "secondary"],
        domains=["regionalnews.example", "politics.example"],
        recovery_source_tiers=["secondary"],
        recovery_domains=["polling.example"],
    )

    trace = outcome.execution_trace
    assert trace["source_class_recovery_recommended"] is True
    assert trace["missing_expected_source_classes"] == ["polling_data_or_aggregator"]
    assert trace["source_class_recovery_queries"]
    assert trace["active_source_class_recovery_considered"] is True
    assert trace["active_source_class_recovery_eligible"] is True
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_missing_classes"] == [
        "polling_data_or_aggregator"
    ]
    assert trace["source_class_recovery_dispatch_authorized"] is False
    assert trace["source_class_recovery_dispatch_reason"] == (
        "canonical_recovery_not_required"
    )
    assert trace["active_source_class_recovery_result_count"] == 0
    assert trace["active_source_class_recovery_new_url_count"] == 0
    assert len(harness.search_calls) == 1
    assert trace["queries_per_iteration"] == {"1": harness.search_calls[0]["queries"]}
    assert "source_class_recovery" not in trace["provider_attempts_by_role"]
    assert trace["weak_corpus_recovery_used"] is False
    assert trace["supplemental_ran"] is False
    assert trace["iterations_run"] == 1


def test_latest_news_race_query_does_not_recommend_recovery(tmp_path: Path) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query="What is the latest news about the governor race?",
        core_topic="governor race latest news",
        primary_entity="governor race",
        researcher_query="governor race latest news",
        router_intent="news",
        router_query_type="news",
        source_tiers=["secondary", "secondary", "secondary", "secondary"],
        domains=["regionalnews.example", "politics.example"],
    )

    trace = outcome.execution_trace
    assert trace["source_class_recovery_recommended"] is False
    assert trace["missing_expected_source_classes"] == []
    assert trace["source_class_recovery_reason"] is None
    assert trace["source_class_recovery_queries"] == []
    assert trace["source_class_recovery_query_count"] == 0
    assert trace["active_source_class_recovery_considered"] is True
    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_skip_reason"] == "not_recommended"
    assert trace["active_source_class_recovery_attempt_count"] == 0
    assert trace["active_source_class_recovery_provider_role"] is None
    assert len(harness.search_calls) == 1
    assert "source_class_recovery" not in trace["provider_attempts_by_role"]


def test_healthy_official_evidence_blocks_active_source_class_recovery(
    tmp_path: Path,
) -> None:
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
        source_tiers=["official", "secondary", "secondary", "unknown"],
        domains=["official.gov", "regionalnews.example"],
    )

    trace = outcome.execution_trace
    assert trace["official_evidence_found"] is True
    assert trace["source_class_recovery_recommended"] is False
    assert trace["active_source_class_recovery_considered"] is True
    assert trace["active_source_class_recovery_eligible"] is False
    assert trace["active_source_class_recovery_used"] is False
    assert trace["active_source_class_recovery_skip_reason"] == "not_recommended"
    assert trace["active_source_class_recovery_attempt_count"] == 0
    assert len(harness.search_calls) == 1
    assert "source_class_recovery" not in trace["provider_attempts_by_role"]


def test_active_recovery_reuses_last_provider_list_without_new_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    select_calls: list[dict[str, Any]] = []
    original_select_providers = orchestrator.select_providers

    def capture_select_providers(*args: Any, **kwargs: Any) -> list[str]:
        select_calls.append({"args": args, "kwargs": kwargs})
        return original_select_providers(*args, **kwargs)

    monkeypatch.setattr(orchestrator, "select_providers", capture_select_providers)
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    trace = outcome.execution_trace
    assert trace["active_source_class_recovery_used"] is True
    assert len(select_calls) == 1
    assert harness.search_calls[1]["search_providers"] == trace["pass_providers"][-1]
    assert harness.search_calls[1]["search_depth"] == trace[
        "active_source_class_recovery_search_depth"
    ]
    assert harness.search_calls[1]["search_depth"] == "basic"
    assert harness.search_calls[1]["linkup_depth_override"] is None


def test_deep_active_recovery_reuses_advanced_depth_without_linkup_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    depth_calls: list[dict[str, Any]] = []
    original_choose_depth = orchestrator.choose_retrieval_search_depth

    def capture_choose_depth(*args: Any, **kwargs: Any) -> str:
        depth_calls.append({"args": args, "kwargs": kwargs})
        return original_choose_depth(*args, **kwargs)

    monkeypatch.setattr(
        orchestrator,
        "choose_retrieval_search_depth",
        capture_choose_depth,
    )
    outcome, harness, _log_entry = _run_case(
        tmp_path,
        mode="Deep",
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    trace = outcome.execution_trace
    assert trace["active_source_class_recovery_used"] is True
    assert trace["active_source_class_recovery_search_depth"] == "advanced"
    assert harness.search_calls[0]["search_depth"] == "advanced"
    assert harness.search_calls[1]["search_depth"] == "advanced"
    assert harness.search_calls[1]["provider_role"] == "source_class_recovery"
    assert harness.search_calls[1]["linkup_depth_override"] is None
    assert harness.search_calls[1]["search_providers"] == trace["pass_providers"][-1]
    assert all(
        not call["kwargs"].get("explicit_escalation_reason")
        for call in depth_calls
    )


def test_source_class_recovery_adapter_executes_at_most_once() -> None:
    controller = RunController()
    lifecycle = record_source_class_recovery_lifecycle(
        controller,
        recommendation={
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["official_current_rules"],
            "source_class_recovery_queries": ["Care Program official rules"],
            "source_class_recovery_reason": (
                "missing_expected_source_class:official_current_rules"
            ),
        },
        recommendation_evaluated=True,
        source_class_evidence_signals={},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=True,
    )
    calls: list[list[str]] = []
    all_passages: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    collected_images: set[str] = set()
    provider_diagnostics: list[dict[str, Any]] = []
    retrieval_pass_records: list[dict[str, Any]] = []

    def fake_process_search_queries(
        queries: list[str],
        _intent: str,
        _complexity: str,
        search_depth: str,
        _results_per_query: int,
        _include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        seen: set[str],
        _images: set[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        calls.append(list(queries))
        seen.add("https://official.gov/recovered")
        provider_diagnostics.append(
            {
                "provider": "tavily",
                "provider_role": kwargs["provider_role"],
                "depth": search_depth,
                "success": True,
                "logical_attempt_count": 1,
            }
        )
        return [
            {
                "title": "Recovered official rule",
                "url": "https://official.gov/recovered",
                "text": "Care Program current official requirements.",
                "score": 0.31,
                "source_tier": "official",
            }
        ]

    first = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_process_search_queries,
        all_passages=all_passages,
        intent="general",
        complexity="medium",
        results_per_query=6,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[1.0],
        seen_urls=seen_urls,
        collected_images=collected_images,
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=NullStatusWriter(),
        search_providers=["tavily"],
        exa_domain_filter=None,
        entity_hint="Care Program",
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )
    second = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_process_search_queries,
        all_passages=all_passages,
        intent="general",
        complexity="medium",
        results_per_query=6,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[1.0],
        seen_urls=seen_urls,
        collected_images=collected_images,
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=NullStatusWriter(),
        search_providers=["tavily"],
        exa_domain_filter=None,
        entity_hint="Care Program",
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )

    assert first == {"attempted": True, "result_count": 1, "new_url_count": 1}
    assert second == {"attempted": False, "result_count": 1, "new_url_count": 1}
    assert calls == [["Care Program official rules"]]
    assert lifecycle["active_source_class_recovery_used"] is True
    assert lifecycle["active_source_class_recovery_result_count"] == 1
    assert lifecycle["active_source_class_recovery_new_url_count"] == 1
    assert len(all_passages) == 1
    assert all_passages[0]["retrieval_stage"] == "source_class_recovery"
    assert all_passages[0]["score"] == 0.31
    assert len(retrieval_pass_records) == 1


def test_recovery_trace_persists_only_nested_and_not_sqlite_compact_mapping(
    tmp_path: Path,
) -> None:
    outcome, _harness, log_entry = _run_case(
        tmp_path,
        query="What are the current eligibility requirements and official rules for the care program?",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        researcher_query="Care Program eligibility requirements",
        router_query_type="other",
    )

    assert RECOVERY_FIELDS <= set(outcome.execution_trace)
    assert RECOVERY_FIELDS <= set(log_entry["execution_trace"])
    assert ACTIVE_RECOVERY_FIELDS <= set(outcome.execution_trace)
    assert ACTIVE_RECOVERY_FIELDS <= set(log_entry["execution_trace"])
    assert SOURCE_CLASS_OBSERVABILITY_FIELDS <= set(outcome.execution_trace)
    assert SOURCE_CLASS_OBSERVABILITY_FIELDS <= set(log_entry["execution_trace"])
    assert SOURCE_CLASS_RECOVERY_CANDIDATE_V2_KEY in outcome.execution_trace
    assert SOURCE_CLASS_RECOVERY_CANDIDATE_V2_KEY in log_entry["execution_trace"]
    assert SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY in outcome.execution_trace
    assert SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY in log_entry["execution_trace"]
    assert SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY in log_entry
    assert (
        log_entry[SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY]
        == log_entry["execution_trace"][SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY]
    )
    assert RECOVERY_FIELDS.isdisjoint(log_entry)
    assert ACTIVE_RECOVERY_FIELDS.isdisjoint(log_entry)
    assert SOURCE_CLASS_OBSERVABILITY_FIELDS.isdisjoint(log_entry)
    assert SOURCE_CLASS_RECOVERY_CANDIDATE_V2_KEY not in log_entry

    row = execution_jsonl_to_run_row(log_entry)
    assert row is not None
    assert set(row) == set(RUN_COLUMNS)
    assert RECOVERY_FIELDS.isdisjoint(row)
    assert ACTIVE_RECOVERY_FIELDS.isdisjoint(row)
    assert SOURCE_CLASS_OBSERVABILITY_FIELDS.isdisjoint(row)
    assert SOURCE_CLASS_RECOVERY_CANDIDATE_V2_KEY not in row
    assert SOURCE_CLASS_RECOVERY_VALIDATION_TRACE_KEY not in row
