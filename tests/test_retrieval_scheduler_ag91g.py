from __future__ import annotations

from pathlib import Path

from core.pipeline_orchestrator import choose_retrieval_search_depth
from core.provider_plan import ProviderPlan
from core.retrieval_scheduler import (
    RetrievalScheduleInput,
    RetrievalScheduleReason,
    schedule_continuation_action,
    schedule_main_retrieval_action,
    schedule_weak_corpus_recovery_action,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEDULER = ROOT / "core" / "retrieval_scheduler.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
SOURCE_CLASS_EXECUTOR = ROOT / "core" / "source_class_recovery_executor.py"


def _all_on() -> dict[str, bool]:
    return {"tavily": True, "linkup": True, "exa": True}


def test_main_scheduler_consumes_provider_plan_without_changing_fields() -> None:
    plan = ProviderPlan.from_available_keys(_all_on())
    provider_record = plan.record_main_retrieval(
        query_type="other",
        intent="research",
        complexity="high",
        report_type="general_research",
        is_academic=False,
        suppress_tavily=False,
        base_search_depth="basic",
        iteration=2,
        primary_override=None,
        scout_override=["exa", "linkup"],
        choose_search_depth=choose_retrieval_search_depth,
    )

    action = schedule_main_retrieval_action(
        RetrievalScheduleInput(
            stage="main_retrieval",
            current_queries=["first query", "second query"],
            iteration=2,
            provider_role="main_retrieval",
            provider_record=provider_record,
            metadata={"force_component_providers_consumed": ["exa", "linkup"]},
        )
    )

    assert action.current_queries == ("first query", "second query")
    assert action.providers == provider_record.providers
    assert action.search_depth == provider_record.search_depth
    assert action.force_component_providers == ()
    assert action.reason is RetrievalScheduleReason.MAIN_PASS_SCHEDULED
    assert action.continue_retrieval is True


def test_continuation_scheduler_preserves_query_order_and_forced_providers() -> None:
    plan = ProviderPlan.from_available_keys(_all_on())
    provider_record = plan.record_continuation(
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

    action = schedule_continuation_action(
        RetrievalScheduleInput(
            stage="scout_directed_continuation",
            current_queries=["component A", "component B"],
            iteration=2,
            provider_role="scout_continuation",
            provider_record=provider_record,
            continuation_authorized=True,
        )
    )

    assert action.current_queries == ("component A", "component B")
    assert action.force_component_providers == provider_record.providers
    assert action.providers == provider_record.providers
    assert action.reason is RetrievalScheduleReason.CONTINUATION_SCHEDULED


def test_evaluator_continuation_scheduler_preserves_empty_force_provider_posture() -> None:
    action = schedule_continuation_action(
        RetrievalScheduleInput(
            stage="evaluator_next_queries",
            current_queries=["follow-up one", "follow-up two"],
            iteration=3,
            provider_role="evaluator_continuation",
            search_depth="advanced",
            continuation_authorized=True,
        )
    )

    assert action.current_queries == ("follow-up one", "follow-up two")
    assert action.force_component_providers == ()
    assert action.providers == ()
    assert action.search_depth == "advanced"


def test_weak_corpus_scheduler_preserves_recovery_posture_and_query_order() -> None:
    action = schedule_weak_corpus_recovery_action(
        RetrievalScheduleInput(
            stage="weak_corpus_recovery",
            current_queries=["official recovery", "background recovery"],
            iteration=2,
            provider_role="weak_corpus_recovery",
            search_depth="basic",
            providers=["tavily", "exa"],
            continuation_authorized=True,
            recovery_active=True,
        )
    )

    assert action.current_queries == ("official recovery", "background recovery")
    assert action.providers == ("tavily", "exa")
    assert action.search_depth == "basic"
    assert action.recovery_active is True
    assert action.reason is RetrievalScheduleReason.WEAK_CORPUS_RECOVERY_SCHEDULED


def test_scheduler_static_guard_has_no_provider_or_query_policy_imports() -> None:
    source = SCHEDULER.read_text()
    forbidden = [
        "select_providers",
        "choose_retrieval_search_depth",
        "authorize_retrieval_queries",
        "process_search_queries",
        "ask_model",
        "core.prompts",
        "core.routing",
        "core.search_providers",
    ]
    for token in forbidden:
        assert token not in source


def test_pipeline_continuation_branches_consume_scheduler_output() -> None:
    source = PIPELINE.read_text()
    assert "schedule_main_retrieval_action" in source
    assert "schedule_continuation_action" in source
    assert "schedule_weak_corpus_recovery_action" in source
    assert "retrieval_scheduled_action = schedule_main_retrieval_action" in source
    assert "current_queries = list(authorized_scout_queries)" not in source
    assert "current_queries = list(authorized_expander_queries)" not in source
    assert "current_queries = list(authorized_evaluator_queries)" not in source
    assert "current_queries = weak_corpus_recovery_queries" not in source


def test_source_class_recovery_remains_controller_action_owned_not_query_plan_owned() -> None:
    executor = SOURCE_CLASS_EXECUTOR.read_text()
    pipeline = PIPELINE.read_text()

    assert 'queries = list(getattr(action, "queries", None) or [])' in executor
    assert "from core.query_plan" not in executor
    assert "source_class_recovery_scope = {" in pipeline
    assert "source_class_recovery_context_from_scope(\n            locals()," not in pipeline
