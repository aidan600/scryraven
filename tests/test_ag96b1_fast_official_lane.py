from __future__ import annotations

import ast
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

_OFFICIAL_CURRENT = "official_current_rules"
_QUERY = (
    "What official source currently states the filing fee for Form A-100? "
    "Answer from official/current sources and cite the official source."
)
_ANSWER_URL = "https://official.example/forms/a-100-fee"
_GENERIC_URL = "https://official.example/agency"
_ROOT = Path(__file__).resolve().parents[1]


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
        payload["source_class_recovery_official_domains"] = domains
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


def _run_executor(
    fake_search: Any,
    *,
    complexity: str = "low",
    search_providers: list[str] | None = None,
    domains: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    controller, lifecycle = _controller_and_lifecycle(domains=domains or ["official.example"])
    all_passages: list[dict[str, Any]] = []
    provider_diagnostics: list[dict[str, Any]] = []
    retrieval_pass_records: list[dict[str, Any]] = []
    result = execute_source_class_recovery_action(
        controller,
        lifecycle_trace=lifecycle,
        process_search_queries=fake_search,
        all_passages=all_passages,
        intent="general",
        complexity=complexity,
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
        provider_diagnostics=provider_diagnostics,
        retrieval_pass_records=retrieval_pass_records,
    )
    assert result["attempted"] is True
    return lifecycle, result, all_passages, retrieval_pass_records


def test_fast_hard_corridor_answer_bearing_direct_candidate_spends_no_retry() -> None:
    calls: list[list[str]] = []

    def fake_search(queries: list[str], *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        calls.append(list(queries))
        return [
            _official_candidate(
                _ANSWER_URL,
                "Form A-100 filing fee schedule",
                "The official current fee schedule states the Form A-100 filing fee.",
            )
        ]

    lifecycle, _result, all_passages, _records = _run_executor(fake_search)
    lane = lifecycle[FAST_OFFICIAL_LANE_TRACE_KEY]

    assert len(calls) == 1
    assert lane["used"] is True
    assert lane["direct_attempt_used"] == 1
    assert lane["bridge_retry_used"] == 0
    assert lane["candidate_fit_status"] == "matched_selected"
    assert lane["retry_posture"] == "skipped_candidate_fit_passed"
    assert all_passages[0]["url"] == _ANSWER_URL


def test_fast_hard_corridor_generic_candidate_authorizes_one_bridge_retry() -> None:
    calls: list[list[str]] = []

    def fake_search(
        queries: list[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        calls.append(list(queries))
        diagnostics = kwargs["provider_diagnostics"]
        if len(calls) == 1:
            diagnostics.append(
                {
                    "provider": "tavily",
                    "provider_role": "source_class_recovery",
                    "output_type": "searchResults",
                    "answer_endpoint_used": False,
                    "provider_result_summaries": [
                        {
                            "title": "Form A-100 filing fee schedule",
                            "url": _ANSWER_URL,
                        }
                    ],
                }
            )
            return [
                _official_candidate(
                    _GENERIC_URL,
                    "Official agency page",
                    "Official agency page with general updates and services.",
                )
            ]
        return [
            _official_candidate(
                _ANSWER_URL,
                "Form A-100 filing fee schedule",
                "The official current fee schedule states the Form A-100 filing fee.",
            )
        ]

    lifecycle, result, all_passages, records = _run_executor(fake_search)
    lane = lifecycle[FAST_OFFICIAL_LANE_TRACE_KEY]

    assert result["result_count"] == 2
    assert len(calls) == 2
    assert lane["candidate_fit_status"] == "no_matching_source_fit"
    assert lane["candidate_fit_rejection_reasons"] == [
        "official_candidate_not_answer_bearing"
    ]
    assert lane["bridge_retry_used"] == 1
    assert lane["retry_candidate_fit_status"] == "matched_selected"
    assert lane["lane_completion_posture"] == "candidate_fit_passed_after_retry"
    assert lane["bridge_hints"][0]["bridge_only"] is True
    assert lane["bridge_hints"][0]["citation_eligible"] is False
    assert lane["bridge_hints"][0]["final_evidence_eligible"] is False
    assert [passage["url"] for passage in all_passages] == [_GENERIC_URL, _ANSWER_URL]
    assert records[0]["fast_official_lane"]["bridge_retry_used"] == 1


def test_bridge_hint_remains_ineligible_until_underlying_official_candidate_passes() -> None:
    hints = concrete_bridge_hints_from_diagnostics(
        [
            {
                "provider": "tavily",
                "provider_role": "source_class_recovery",
                "provider_result_summaries": [
                    {"title": "Form A-100 filing fee schedule", "url": _ANSWER_URL}
                ],
            }
        ]
    )
    bridge = hints[0].as_trace()

    assert bridge["official_url"] == _ANSWER_URL
    assert bridge["bridge_only"] is True
    assert bridge["citation_eligible"] is False
    assert bridge["final_evidence_eligible"] is False

    controller, lifecycle = _controller_and_lifecycle(domains=["official.example"])
    lifecycle["active_source_class_recovery_used"] = True
    selected, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=[],
        lifecycle_trace=lifecycle,
        max_final_evidence=1,
    )
    assert selected == []
    assert decision.source_fit_status == "no_candidates"


def test_bridge_snippet_without_concrete_official_hint_cannot_create_support() -> None:
    calls: list[list[str]] = []

    def fake_search(
        queries: list[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        calls.append(list(queries))
        kwargs["provider_diagnostics"].append(
            {
                "provider": "tavily",
                "provider_role": "source_class_recovery",
                "provider_result_summaries": [{"claim": "secondary snippet only"}],
            }
        )
        return [
            _official_candidate(
                _GENERIC_URL,
                "Official agency page",
                "Official agency page with general updates and services.",
            )
        ]

    lifecycle, _result, all_passages, _records = _run_executor(fake_search)
    lane = lifecycle[FAST_OFFICIAL_LANE_TRACE_KEY]
    selected, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[],
        recovered_passages=all_passages,
        lifecycle_trace=lifecycle,
        max_final_evidence=1,
    )

    assert len(calls) == 1
    assert lane["bridge_retry_used"] == 0
    assert lane["retry_posture"] == "skipped_no_concrete_bridge_hint"
    assert selected == []
    assert decision.source_fit_status == "no_matching_source_fit"


def test_fast_hard_corridor_budget_exhaustion_stops_after_one_retry() -> None:
    calls: list[list[str]] = []

    def fake_search(
        queries: list[str],
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        calls.append(list(queries))
        kwargs["provider_diagnostics"].append(
            {
                "provider": "tavily",
                "provider_role": "source_class_recovery",
                "provider_result_summaries": [
                    {
                        "title": f"Generic official page {len(calls)}",
                        "url": f"https://official.example/generic-{len(calls)}",
                    }
                ],
            }
        )
        return [
            _official_candidate(
                f"https://official.example/generic-candidate-{len(calls)}",
                "Official agency page",
                "Official agency page with general updates and services.",
            )
        ]

    lifecycle, _result, _all_passages, _records = _run_executor(fake_search)
    lane = lifecycle[FAST_OFFICIAL_LANE_TRACE_KEY]

    assert len(calls) == 2
    assert lane["bridge_retry_used"] == 1
    assert lane["retry_candidate_fit_status"] == "no_matching_source_fit"
    assert lane["lane_completion_posture"] == "recipe_exhausted_fail_closed"


def test_linkup_fast_lane_uses_search_results_not_sourced_answer_or_deep() -> None:
    calls: list[dict[str, Any]] = []

    def fake_search(queries: list[str], *_args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        calls.append({"queries": list(queries), "kwargs": dict(kwargs)})
        return [
            _official_candidate(
                _ANSWER_URL,
                "Form A-100 filing fee schedule",
                "The official current fee schedule states the Form A-100 filing fee.",
            )
        ]

    lifecycle, _result, _all_passages, _records = _run_executor(
        fake_search,
        search_providers=["linkup"],
    )
    lane = lifecycle[FAST_OFFICIAL_LANE_TRACE_KEY]

    assert len(calls) == 1
    assert calls[0]["kwargs"].get("linkup_depth_override") is None
    assert lane["linkup_sourced_answer_selected"] is False
    assert lane["provider_jobs_planned"] == [
        {
            "provider": "linkup",
            "job": "direct_official_candidate_search",
            "bridge_only": False,
            "candidate_surface": True,
            "output_type": "searchResults",
            "answer_endpoint_used": False,
        }
    ]


def test_brave_bridge_hints_are_scout_only_and_ineligible() -> None:
    hints = concrete_bridge_hints_from_diagnostics(
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

    assert hints[0].as_trace()["provider_job"] == "early_scout_disambiguation"
    assert hints[0].as_trace()["bridge_only"] is True
    assert hints[0].as_trace()["citation_eligible"] is False
    assert hints[0].as_trace()["final_evidence_eligible"] is False


def test_exa_is_job_capability_not_unconditional_fallback() -> None:
    plan_without_exa = build_fast_official_lane_plan(
        lifecycle_trace={
            "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
            "active_source_class_recovery_provider_role": "source_class_recovery",
        },
        complexity="low",
        search_providers=["tavily"],
        official_domain_constraints=["official.example"],
    )
    plan_with_exa = build_fast_official_lane_plan(
        lifecycle_trace={
            "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
            "active_source_class_recovery_provider_role": "source_class_recovery",
        },
        complexity="low",
        search_providers=["exa"],
        official_domain_constraints=["official.example"],
    )

    assert all(job["provider"] != "exa" for job in plan_without_exa.provider_jobs)
    assert plan_with_exa.provider_jobs[0]["job"] == (
        "semantic_recall_or_constrained_candidate_search"
    )


def test_soft_and_discovery_corridors_are_not_hard_forced_by_hints() -> None:
    plan = build_fast_official_lane_plan(
        lifecycle_trace={
            "active_source_class_recovery_missing_classes": [_OFFICIAL_CURRENT],
            "active_source_class_recovery_provider_role": "source_class_recovery",
        },
        complexity="low",
        search_providers=["tavily"],
        official_domain_constraints=[],
    )

    assert plan.used is False
    assert plan.skip_reason == "not_hard_corridor"
    assert plan.as_trace()["soft_corridor_hard_forced"] is False
    assert plan.as_trace()["discovery_corridor_us_shortcut"] is False


def test_static_guards_no_provider_integration_or_source_specific_resolver() -> None:
    fast_lane = (_ROOT / "core" / "fast_official_lane.py").read_text(encoding="utf-8")
    executor = (_ROOT / "core" / "source_class_recovery_executor.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(fast_lane)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert imports.isdisjoint(
        {
            "core.search_providers",
            "core.pipeline",
            "core.pipeline_orchestrator",
            "requests",
            "httpx",
            "exa_py",
        }
    )
    combined = f"{fast_lane}\n{executor}".casefold()
    assert "uscis.gov" not in combined
    assert "ssa.gov" not in combined
    assert "irs.gov" not in combined
    assert "sourcedanswer" not in fast_lane.casefold()
    assert "deep" not in fast_lane.casefold()
