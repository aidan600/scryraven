"""AG-91C ProviderPlan parity tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.pipeline_orchestrator import (
    choose_retrieval_search_depth,
    choose_supplemental_search_depth,
)
from core.provider_plan import ProviderAvailabilitySnapshot, ProviderPlan
from core.retrieval_dispatch_runtime import (
    RecordedRetrievalDispatch,
    RetrievalDispatchDeps,
    execute_recorded_retrieval_dispatch,
)
from core.routing import merge_search_provider_overrides, select_providers

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "core" / "provider_plan.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _all_on() -> dict[str, bool]:
    return {"tavily": True, "linkup": True, "exa": True}


def _deps(process_search_queries, seen_urls: set[str]) -> RetrievalDispatchDeps:
    return RetrievalDispatchDeps(
        process_search_queries=process_search_queries,
        query_embedding=[0.1],
        seen_urls=seen_urls,
        collected_images=set(),
        embed_provider="embed-provider",
        embed_model="embed-model",
        local_url=None,
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=None,
        provider_diagnostics=[],
    )


def test_provider_availability_snapshot_shape_matches_existing_selector_input() -> None:
    snapshot = ProviderAvailabilitySnapshot.from_mapping(
        {"tavily": "present", "linkup": "", "exa": object(), "brave": True}
    )

    assert snapshot.to_available_keys() == {"tavily": True, "linkup": False, "exa": True}
    assert snapshot.to_trace() == {"tavily": True, "linkup": False, "exa": True}


def test_main_loop_search_depth_selection_parity_representative_cases() -> None:
    cases = [
        ("low", "basic", 1),
        ("medium", "basic", 2),
        ("medium", "advanced", 1),
        ("high", "basic", 1),
        ("high", None, 3),
    ]

    for complexity, base_depth, iteration in cases:
        plan = ProviderPlan.from_available_keys(_all_on())
        record = plan.record_main_retrieval(
            query_type="other",
            intent="research",
            complexity=complexity,
            report_type="general_research",
            is_academic=False,
            suppress_tavily=False,
            base_search_depth=base_depth,
            iteration=iteration,
            primary_override=None,
            scout_override=None,
            choose_search_depth=choose_retrieval_search_depth,
        )

        assert record.search_depth == choose_retrieval_search_depth(
            complexity, base_depth, iteration
        )


def test_provider_override_merge_and_selection_order_parity() -> None:
    available_keys = _all_on()
    plan = ProviderPlan.from_available_keys(available_keys)
    primary = ["linkup", "exa"]
    scout = ["exa", "tavily"]

    record = plan.record_main_retrieval(
        query_type="product",
        intent="research",
        complexity="medium",
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        base_search_depth="basic",
        iteration=1,
        primary_override=primary,
        scout_override=scout,
        choose_search_depth=choose_retrieval_search_depth,
    )

    expected_override = merge_search_provider_overrides(
        primary, scout, available_keys, complexity="medium"
    )
    expected_providers = select_providers(
        "product",
        "research",
        "medium",
        available_keys,
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        override=expected_override,
    )
    assert list(record.provider_override or ()) == expected_override
    assert record.providers_list() == expected_providers


def test_scout_expander_internal_override_behavior_unchanged_when_selected_directly() -> None:
    assert select_providers(
        "other",
        "general",
        "medium",
        _all_on(),
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        override=["exa", "linkup"],
        override_is_user=False,
    ) == ["exa"]
    assert select_providers(
        "other",
        "general",
        "high",
        _all_on(),
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        override=["exa", "linkup"],
        override_is_user=False,
    ) == ["exa", "linkup"]


def test_scout_continuation_provider_plan_override_parity_cases() -> None:
    cases = [
        ("medium", _all_on()),
        ("high", _all_on()),
        ("high", {"tavily": True, "linkup": False, "exa": True}),
        ("medium", {"tavily": True, "linkup": True, "exa": False}),
        ("high", {"tavily": False, "linkup": False, "exa": False}),
    ]

    for complexity, available_keys in cases:
        plan = ProviderPlan.from_available_keys(available_keys)
        record = plan.record_continuation(
            role="scout_continuation",
            query_type="other",
            intent="general",
            complexity=complexity,
            report_type="general_research",
            is_academic=False,
            suppress_tavily=False,
            override=["exa", "linkup"],
            override_is_user=False,
        )

        expected = select_providers(
            "other",
            "general",
            complexity,
            available_keys,
            report_type="general_research",
            is_academic=False,
            suppress_tavily=False,
            override=["exa", "linkup"],
            override_is_user=False,
        )
        assert record.providers_list() == expected


def test_expander_continuation_provider_plan_default_selection_parity_cases() -> None:
    cases = [
        ("medium", _all_on(), "general_research", False, False),
        ("high", _all_on(), "general_research", False, False),
        ("high", _all_on(), "benchmark", False, False),
        ("medium", {"tavily": False, "linkup": True, "exa": True}, "general_research", True, False),
        ("high", {"tavily": True, "linkup": True, "exa": True}, "general_research", False, True),
    ]

    for complexity, available_keys, report_type, is_academic, suppress_tavily in cases:
        plan = ProviderPlan.from_available_keys(available_keys)
        record = plan.record_continuation(
            role="expander_continuation",
            query_type="other",
            intent="research",
            complexity=complexity,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            override=None,
            override_is_user=True,
        )

        expected = select_providers(
            "other",
            "research",
            complexity,
            available_keys,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            override=None,
        )
        assert record.providers_list() == expected


def test_continuation_provider_plan_trace_projection_matches_consumed_values() -> None:
    plan = ProviderPlan.from_available_keys(_all_on())
    scout_record = plan.record_continuation(
        role="scout_continuation",
        query_type="other",
        intent="general",
        complexity="high",
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        override=["exa", "linkup"],
        override_is_user=False,
    )
    expander_record = plan.record_continuation(
        role="expander_continuation",
        query_type="other",
        intent="research",
        complexity="medium",
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        override=None,
        override_is_user=True,
    )

    trace_records = plan.to_trace()["records"]
    assert trace_records[0]["role"] == "scout_continuation"
    assert trace_records[0]["providers"] == scout_record.providers_list()
    assert trace_records[0]["provider_override"] == ["exa", "linkup"]
    assert trace_records[1]["role"] == "expander_continuation"
    assert trace_records[1]["providers"] == expander_record.providers_list()
    assert "provider_override" not in trace_records[1]


def test_continuation_dispatch_receives_same_providers_after_main_loop_merge() -> None:
    available_keys = _all_on()
    plan = ProviderPlan.from_available_keys(available_keys)
    continuation_record = plan.record_continuation(
        role="scout_continuation",
        query_type="other",
        intent="general",
        complexity="high",
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        override=["exa", "linkup"],
        override_is_user=False,
    )
    main_record = plan.record_main_retrieval(
        query_type="other",
        intent="general",
        complexity="high",
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        base_search_depth="basic",
        iteration=2,
        primary_override=None,
        scout_override=continuation_record.providers_list(),
        choose_search_depth=choose_retrieval_search_depth,
    )

    legacy_force_component_providers = select_providers(
        "other",
        "general",
        "high",
        available_keys,
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        override=["exa", "linkup"],
        override_is_user=False,
    )
    legacy_merged_override = merge_search_provider_overrides(
        None, legacy_force_component_providers, available_keys, complexity="high"
    )
    legacy_dispatch_providers = select_providers(
        "other",
        "general",
        "high",
        available_keys,
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        override=legacy_merged_override,
    )

    assert continuation_record.providers_list() == legacy_force_component_providers
    assert main_record.providers_list() == legacy_dispatch_providers


def test_supplemental_depth_provider_injection_parity_when_legacy_stage_is_untouched() -> None:
    available_keys = _all_on()
    assert choose_supplemental_search_depth("medium", "basic") == "basic"
    assert choose_supplemental_search_depth("high", "basic") == "advanced"
    assert select_providers(
        "news",
        "research",
        "high",
        available_keys,
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        override=None,
    ) == ["tavily", "linkup"]


def test_provider_plan_trace_projection_matches_consumed_values() -> None:
    plan = ProviderPlan.from_available_keys(_all_on())
    record = plan.record_main_retrieval(
        query_type="quantitative_comparison",
        intent="research",
        complexity="high",
        report_type="benchmark",
        is_academic=True,
        suppress_tavily=False,
        base_search_depth="basic",
        iteration=2,
        primary_override=None,
        scout_override=None,
        choose_search_depth=choose_retrieval_search_depth,
    )

    trace = plan.to_trace()
    record_trace = trace["records"][0]
    assert record_trace["providers"] == record.providers_list()
    assert record_trace["search_depth"] == record.search_depth
    assert record_trace["available_keys"] == plan.available_keys()


def test_dispatch_receives_same_providers_and_depth_from_provider_plan_record() -> None:
    seen_urls: set[str] = set()
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_process(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        calls.append((args, kwargs))
        seen_urls.add("https://example.com")
        return [{"url": "https://example.com", "text": "ok"}]

    plan = ProviderPlan.from_available_keys(_all_on())
    record = plan.record_main_retrieval(
        query_type="product",
        intent="research",
        complexity="high",
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        base_search_depth="basic",
        iteration=1,
        primary_override=None,
        scout_override=None,
        choose_search_depth=choose_retrieval_search_depth,
    )
    expected_providers = select_providers(
        "product", "research", "high", _all_on(), report_type="general_research"
    )
    expected_depth = choose_retrieval_search_depth("high", "basic", 1)

    execute_recorded_retrieval_dispatch(
        RecordedRetrievalDispatch(
            stage="main_retrieval",
            queries=["q"],
            intent="research",
            complexity="high",
            search_depth=record.search_depth or "basic",
            results_per_query=3,
            include_domains=[],
            exclude_domains=[],
            providers=record.providers,
            provider_role="main_retrieval",
            iteration=1,
        ),
        _deps(fake_process, seen_urls),
    )

    args, kwargs = calls[0]
    assert args[3] == expected_depth
    assert kwargs["search_providers"] == expected_providers


def test_static_guard_provider_plan_is_not_provider_or_search_brain() -> None:
    source = _read_text(HELPER)
    forbidden = [
        "ask_model",
        "process_search_queries",
        "embed_texts",
        "brave_reconnaissance",
        "core.prompts",
        "core.search_providers",
        "core.citation",
        "core.final_evidence",
        "core.project_sources",
        "core.cache",
        "DEFAULT_SYSTEM",
    ]
    for token in forbidden:
        assert token not in source
    for provider in ("serpapi", "perplexity", "google"):
        assert provider not in source.lower()


def test_pipeline_consumes_provider_plan_for_main_loop_selection() -> None:
    source = _read_text(PIPELINE)
    scheduler_source = _read_text(ROOT / "core" / "retrieval_scheduler.py")
    assert "provider_plan = ProviderPlan.from_available_keys" in source
    assert "schedule_main_retrieval_from_kernel_action" in source
    assert "provider_record = provider_plan.record_main_retrieval" in scheduler_source
    assert "provider_record = provider_plan.record_continuation" in scheduler_source
    assert "main_retrieval_action_values(retrieval_scheduled_action)" in source


def test_supplemental_provider_plan_record_matches_legacy_depth_and_provider_selection() -> None:
    cases = [
        ("medium", "basic", _all_on()),
        ("high", "basic", _all_on()),
        ("high", "advanced", {"tavily": True, "linkup": False, "exa": True}),
        ("medium", "advanced", {"tavily": False, "linkup": True, "exa": True}),
    ]

    for complexity, base_depth, available_keys in cases:
        plan = ProviderPlan.from_available_keys(available_keys)
        record = plan.record_supplemental_retrieval(
            query_type="news",
            intent="research",
            complexity=complexity,
            report_type="general_research",
            is_academic=False,
            suppress_tavily=False,
            base_search_depth=base_depth,
            choose_search_depth=choose_supplemental_search_depth,
        )

        assert record.search_depth == choose_supplemental_search_depth(complexity, base_depth)
        assert record.providers_list() == select_providers(
            "news",
            "research",
            complexity,
            available_keys,
            report_type="general_research",
            is_academic=False,
            suppress_tavily=False,
            override=None,
        )


def test_scrutineer_remediation_provider_plan_record_matches_legacy_selection() -> None:
    cases = [
        ("high", _all_on(), "general_research", False, False),
        ("high", {"tavily": True, "linkup": False, "exa": True}, "general_research", False, False),
        ("high", {"tavily": False, "linkup": True, "exa": True}, "benchmark", True, False),
        ("high", _all_on(), "general_research", False, True),
    ]

    for complexity, available_keys, report_type, is_academic, suppress_tavily in cases:
        plan = ProviderPlan.from_available_keys(available_keys)
        record = plan.record_scrutineer_remediation(
            query_type="other",
            intent="research",
            complexity=complexity,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            search_depth="advanced",
        )

        assert record.search_depth == "advanced"
        assert record.providers_list() == select_providers(
            "other",
            "research",
            complexity,
            available_keys,
            report_type=report_type,
            is_academic=is_academic,
            suppress_tavily=suppress_tavily,
            override=None,
        )


def test_pipeline_consumes_provider_plan_for_supplemental_and_scrutineer_selection() -> None:
    source = _read_text(PIPELINE)
    legacy_source = _read_text(ROOT / "core" / "legacy_review_runtime_stage.py")

    assert "provider_plan = ProviderPlan.from_available_keys" in source
    assert "supplemental_provider_record = provider_plan.record_supplemental_retrieval" in legacy_source
    assert "supp_search_depth = supplemental_provider_record.search_depth" in legacy_source
    assert "supp_providers = supplemental_provider_record.providers_list()" in legacy_source
    assert "remediation_provider_record = provider_plan.record_scrutineer_remediation" in legacy_source
    assert "remed_providers = remediation_provider_record.providers_list()" in legacy_source
