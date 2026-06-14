from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.fast_official_lane import (
    FAST_OFFICIAL_LANE_TRACE_KEY,
    build_fast_official_lane_plan,
    concrete_bridge_hints_from_diagnostics,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.run_controller import RunController
from core.source_class_recovery_executor import execute_source_class_recovery_action
from core.source_class_recovery_lifecycle import record_source_class_recovery_lifecycle

_ROOT = Path(__file__).resolve().parents[1]
_OFFICIAL_CURRENT = "official_current_rules"
_QUERY = (
    "What official source currently states the filing fee for Form A-100? "
    "Answer from official/current sources and cite the official source."
)
_ANSWER_URL = "https://official.example/forms/a-100-fee"
_GENERIC_URL = "https://official.example/agency"


@dataclass(frozen=True)
class _FakeAttempt:
    passages: list[dict[str, Any]]
    diagnostics: list[dict[str, Any]]


@dataclass(frozen=True)
class _EvalResult:
    lifecycle: dict[str, Any]
    calls: list[dict[str, Any]]
    all_passages: list[dict[str, Any]]
    retrieval_pass_records: list[dict[str, Any]]

    @property
    def lane(self) -> dict[str, Any]:
        return self.lifecycle[FAST_OFFICIAL_LANE_TRACE_KEY]

    @property
    def metrics(self) -> dict[str, Any]:
        bridge_hints = list(self.lane.get("bridge_hints") or [])
        completion = str(self.lane.get("lane_completion_posture") or "")
        return {
            "lane_used": self.lane.get("used"),
            "direct_attempt_used": self.lane.get("direct_attempt_used"),
            "candidate_fit_status": self.lane.get("candidate_fit_status"),
            "candidate_fit_rejection_reasons": list(
                self.lane.get("candidate_fit_rejection_reasons") or []
            ),
            "bridge_hint_count": self.lane.get("bridge_hint_count"),
            "bridge_retry_used": self.lane.get("bridge_retry_used"),
            "retry_candidate_fit_status": self.lane.get(
                "retry_candidate_fit_status"
            ),
            "lane_completion_posture": completion,
            "final_evidence_eligible_bridge_count": sum(
                1 for hint in bridge_hints if hint.get("final_evidence_eligible")
            ),
            "citation_eligible_bridge_count": sum(
                1 for hint in bridge_hints if hint.get("citation_eligible")
            ),
            "total_fake_provider_calls": len(self.calls),
            "budget_exhausted": completion == "recipe_exhausted_fail_closed",
            "sufficiency_reached": completion
            in {
                "candidate_fit_passed_no_retry_requested",
                "candidate_fit_passed_after_retry",
            },
        }

    def selected_recovered_evidence(self) -> tuple[list[dict[str, Any]], Any]:
        return apply_recovered_evidence_visibility_boundary(
            final_top_evidence=[],
            recovered_passages=self.all_passages,
            lifecycle_trace=self.lifecycle,
            max_final_evidence=1,
        )


def _recommendation(*, domains: list[str] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": [_OFFICIAL_CURRENT],
        "source_class_recovery_queries": [
            "Form A-100 filing fee official current fee schedule"
        ],
        "source_class_recovery_reason": (
            "missing_expected_source_class:official_current_rules"
        ),
    }
    if domains is not None:
        payload["source_class_recovery_official_domains"] = list(domains)
        payload["source_class_recovery_domain_constraint_source"] = (
            "official_source_recovery_lane"
        )
        payload["source_class_recovery_authority_acquisition_decision"] = {
            "decision_type": "hard_corridor",
            "provider_domain_constraints_allowed": True,
        }
    return payload


def _controller_and_lifecycle(
    *,
    domains: list[str] | None = None,
) -> tuple[RunController, dict[str, Any]]:
    controller = RunController()
    lifecycle = record_source_class_recovery_lifecycle(
        controller,
        recommendation=_recommendation(domains=domains),
        recommendation_evaluated=True,
        source_class_evidence_signals={"source_tier_counts": {"secondary": 2}},
        corpus_state="HEALTHY",
        corpus_weak=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason=None,
        current_search_depth="basic",
        iteration_budget_available=True,
        official_canonical_source_class_slot_available=True,
    )
    return controller, lifecycle


def _official_candidate(url: str, title: str, text: str) -> dict[str, Any]:
    return {
        "url": url,
        "title": title,
        "text": text,
        "source_tier": "official",
        "source_class": _OFFICIAL_CURRENT,
        "readable_text_available": True,
        "readability_status": "readable",
        "currentness_signal": "current",
    }


def _answer_candidate(url: str = _ANSWER_URL) -> dict[str, Any]:
    return _official_candidate(
        url,
        "Form A-100 filing fee schedule",
        "The official current fee schedule states the Form A-100 filing fee.",
    )


def _generic_candidate(url: str = _GENERIC_URL) -> dict[str, Any]:
    return _official_candidate(
        url,
        "Official agency page",
        "Official agency page with general updates and services.",
    )


def _bridge_diagnostic(
    *,
    provider: str = "tavily",
    title: str = "Form A-100 filing fee schedule",
    url: str = _ANSWER_URL,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "provider_role": "source_class_recovery",
        "output_type": "searchResults",
        "answer_endpoint_used": False,
        "provider_result_summaries": [{"title": title, "url": url}],
    }


def _snippet_only_diagnostic() -> dict[str, Any]:
    return {
        "provider": "tavily",
        "provider_role": "source_class_recovery",
        "provider_result_summaries": [
            {"snippet": "A secondary snippet claims Form A-100 costs $100."}
        ],
    }


def _run_offline_eval(
    attempts: list[_FakeAttempt],
    *,
    search_providers: list[str] | None = None,
    domains: list[str] | None = None,
) -> _EvalResult:
    controller, lifecycle = _controller_and_lifecycle(
        domains=domains or ["official.example"]
    )
    calls: list[dict[str, Any]] = []
    all_passages: list[dict[str, Any]] = []
    retrieval_pass_records: list[dict[str, Any]] = []

    def fake_search(
        queries: list[str],
        _intent: str,
        _complexity: str,
        search_depth: str,
        _results_per_query: int,
        include_domains: list[str],
        exclude_domains: list[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        attempt_index = len(calls)
        attempt = attempts[attempt_index]
        calls.append(
            {
                "queries": list(queries),
                "search_depth": search_depth,
                "include_domains": list(include_domains),
                "exclude_domains": list(exclude_domains),
                "search_providers": list(kwargs["search_providers"]),
                "exa_domain_filter": (
                    list(kwargs["exa_domain_filter"])
                    if kwargs.get("exa_domain_filter") is not None
                    else None
                ),
                "provider_role": kwargs["provider_role"],
            }
        )
        kwargs["provider_diagnostics"].extend(attempt.diagnostics)
        return [dict(passage) for passage in attempt.passages]

    result = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=all_passages,
        intent="general",
        complexity="low",
        results_per_query=5,
        include_domains=[],
        exclude_domains=[],
        query_embedding=[1.0],
        seen_urls=set(),
        collected_images=set(),
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="http://localhost",
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        search_providers=list(search_providers or ["tavily"]),
        exa_domain_filter=None,
        entity_hint="Form A-100 filing fee",
        provider_diagnostics=[],
        retrieval_pass_records=retrieval_pass_records,
    )
    assert result["attempted"] is True
    return _EvalResult(
        lifecycle=lifecycle,
        calls=calls,
        all_passages=all_passages,
        retrieval_pass_records=retrieval_pass_records,
    )


def _assert_bridge_material_ineligible(metrics: dict[str, Any]) -> None:
    assert metrics["final_evidence_eligible_bridge_count"] == 0
    assert metrics["citation_eligible_bridge_count"] == 0


def test_ag96b2_direct_answer_bearing_official_candidate_eval_metrics() -> None:
    eval_result = _run_offline_eval(
        [_FakeAttempt(passages=[_answer_candidate()], diagnostics=[])]
    )
    metrics = eval_result.metrics
    selected, decision = eval_result.selected_recovered_evidence()

    assert metrics["lane_used"] is True
    assert metrics["direct_attempt_used"] == 1
    assert metrics["candidate_fit_status"] == "matched_selected"
    assert metrics["candidate_fit_rejection_reasons"] == []
    assert metrics["bridge_retry_used"] == 0
    assert metrics["total_fake_provider_calls"] == 1
    assert metrics["sufficiency_reached"] is True
    assert eval_result.calls[0]["include_domains"] == ["official.example"]
    assert selected[0]["url"] == _ANSWER_URL
    assert decision.source_fit_status == "matched_selected"


def test_ag96b2_generic_official_candidate_uses_one_concrete_bridge_retry() -> None:
    eval_result = _run_offline_eval(
        [
            _FakeAttempt(
                passages=[_generic_candidate()],
                diagnostics=[_bridge_diagnostic()],
            ),
            _FakeAttempt(passages=[_answer_candidate()], diagnostics=[]),
        ]
    )
    metrics = eval_result.metrics
    selected, decision = eval_result.selected_recovered_evidence()

    assert metrics["candidate_fit_status"] == "no_matching_source_fit"
    assert metrics["candidate_fit_rejection_reasons"] == [
        "official_candidate_not_answer_bearing"
    ]
    assert metrics["bridge_hint_count"] == 1
    assert metrics["bridge_retry_used"] == 1
    assert metrics["retry_candidate_fit_status"] == "matched_selected"
    assert metrics["lane_completion_posture"] == "candidate_fit_passed_after_retry"
    assert metrics["total_fake_provider_calls"] == 2
    _assert_bridge_material_ineligible(metrics)
    assert eval_result.calls[1]["queries"] == ["Form A-100 filing fee schedule"]
    assert selected[0]["url"] == _ANSWER_URL
    assert decision.source_fit_status == "matched_selected"


def test_ag96b2_generic_official_candidate_without_hint_fails_closed() -> None:
    eval_result = _run_offline_eval(
        [
            _FakeAttempt(
                passages=[_generic_candidate()],
                diagnostics=[
                    {
                        "provider": "tavily",
                        "provider_role": "source_class_recovery",
                        "provider_result_summaries": [{}],
                    }
                ],
            )
        ]
    )
    metrics = eval_result.metrics
    selected, decision = eval_result.selected_recovered_evidence()

    assert metrics["candidate_fit_status"] == "no_matching_source_fit"
    assert metrics["bridge_hint_count"] == 0
    assert metrics["bridge_retry_used"] == 0
    assert metrics["total_fake_provider_calls"] == 1
    assert eval_result.lane["retry_posture"] == "skipped_no_concrete_bridge_hint"
    assert selected == []
    assert decision.source_fit_status == "no_matching_source_fit"


def test_ag96b2_retry_exhaustion_stops_after_one_retry() -> None:
    eval_result = _run_offline_eval(
        [
            _FakeAttempt(
                passages=[_generic_candidate()],
                diagnostics=[_bridge_diagnostic()],
            ),
            _FakeAttempt(
                passages=[_generic_candidate("https://official.example/generic-2")],
                diagnostics=[_bridge_diagnostic(title="Another generic page")],
            ),
        ]
    )
    metrics = eval_result.metrics
    selected, decision = eval_result.selected_recovered_evidence()

    assert metrics["bridge_retry_used"] == 1
    assert metrics["retry_candidate_fit_status"] == "no_matching_source_fit"
    assert metrics["lane_completion_posture"] == "recipe_exhausted_fail_closed"
    assert metrics["budget_exhausted"] is True
    assert metrics["total_fake_provider_calls"] == 2
    assert selected == []
    assert decision.source_fit_status == "no_matching_source_fit"


def test_ag96b2_bridge_snippet_claim_cannot_launder_final_support() -> None:
    hints = concrete_bridge_hints_from_diagnostics([_snippet_only_diagnostic()])
    eval_result = _run_offline_eval(
        [
            _FakeAttempt(
                passages=[_generic_candidate()],
                diagnostics=[_snippet_only_diagnostic()],
            )
        ]
    )
    selected, decision = eval_result.selected_recovered_evidence()

    assert hints == []
    assert eval_result.metrics["bridge_hint_count"] == 0
    assert eval_result.metrics["bridge_retry_used"] == 0
    assert eval_result.metrics["total_fake_provider_calls"] == 1
    assert selected == []
    assert decision.source_fit_status == "no_matching_source_fit"


def test_ag96b2_existing_provider_role_boundaries_remain_bridge_or_candidate() -> None:
    plan = build_fast_official_lane_plan(
        lifecycle_trace={
            "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
            "active_source_class_recovery_provider_role": "source_class_recovery",
        },
        complexity="low",
        search_providers=["linkup", "exa", "tavily"],
        official_domain_constraints=["official.example"],
    )
    jobs_by_provider = {job["provider"]: job for job in plan.provider_jobs}
    brave_hints = concrete_bridge_hints_from_diagnostics(
        [
            {
                "provider": "brave",
                "provider_role": "official_scout",
                "provider_result_summaries": [
                    {"title": "Form A-100 filing fee schedule", "url": _ANSWER_URL}
                ],
            }
        ]
    )
    plan_without_exa = build_fast_official_lane_plan(
        lifecycle_trace={
            "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
            "active_source_class_recovery_provider_role": "source_class_recovery",
        },
        complexity="low",
        search_providers=["tavily"],
        official_domain_constraints=["official.example"],
    )

    assert jobs_by_provider["linkup"]["output_type"] == "searchResults"
    assert jobs_by_provider["linkup"]["answer_endpoint_used"] is False
    assert plan.as_trace()["linkup_sourced_answer_selected"] is False
    assert jobs_by_provider["exa"]["job"] == (
        "semantic_recall_or_constrained_candidate_search"
    )
    assert all(job["provider"] != "exa" for job in plan_without_exa.provider_jobs)
    assert jobs_by_provider["tavily"]["job"] == "direct_official_candidate_search"
    assert brave_hints[0].as_trace()["provider_job"] == (
        "early_scout_disambiguation"
    )
    assert brave_hints[0].as_trace()["bridge_only"] is True
    assert brave_hints[0].as_trace()["citation_eligible"] is False
    assert brave_hints[0].as_trace()["final_evidence_eligible"] is False


def test_ag96b2_corridor_preservation_is_eval_visible() -> None:
    hard = build_fast_official_lane_plan(
        lifecycle_trace={
            "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
            "active_source_class_recovery_provider_role": "source_class_recovery",
        },
        complexity="low",
        search_providers=["tavily"],
        official_domain_constraints=["official.example"],
    )
    not_hard = build_fast_official_lane_plan(
        lifecycle_trace={
            "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
            "active_source_class_recovery_provider_role": "source_class_recovery",
        },
        complexity="low",
        search_providers=["tavily"],
        official_domain_constraints=[],
    )

    assert hard.used is True
    assert hard.corridor == "hard_corridor"
    assert not_hard.used is False
    assert not_hard.skip_reason == "not_hard_corridor"
    assert not_hard.as_trace()["soft_corridor_hard_forced"] is False
    assert not_hard.as_trace()["discovery_corridor_us_shortcut"] is False


def test_ag96b2_candidate_fit_and_custody_ownership_static_boundary() -> None:
    fast_lane = (_ROOT / "core" / "fast_official_lane.py").read_text(encoding="utf-8")
    executor = (_ROOT / "core" / "source_class_recovery_executor.py").read_text(
        encoding="utf-8"
    )
    orchestrator = (_ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    fast_lane_imports = _imports_for(fast_lane)
    executor_imports = _imports_for(executor)

    assert "core.recovered_evidence_visibility" not in fast_lane_imports
    assert "core.final_answer_packet" not in fast_lane_imports
    assert "core.evidence_ledger" not in fast_lane_imports
    assert "core.recovered_evidence_visibility" in executor_imports
    assert "apply_recovered_evidence_visibility_boundary" in executor
    assert "fast_official_lane" not in orchestrator
    assert "apply_recovered_evidence_visibility_boundary" not in orchestrator


def _imports_for(source: str) -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports
