from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

import core.retrieval_dispatch_runtime as retrieval_runtime
import proplex.__main__ as compatibility_cli
from core.retrieval_dispatch_runtime import (
    RecordedRetrievalDispatch,
    RetrievalDispatchDeps,
    RetrievalPostMaterialDispatchError,
    RetrievalPostMaterialFailureSubtype,
    build_retrieval_pass_record,
    execute_main_retrieval_pass_from_scope,
    execute_recorded_retrieval_dispatch,
)
from core.retrieval_scheduler import (
    RetrievalScheduleInput,
    schedule_main_retrieval_action,
)
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.run_config import RunConfig
from core.run_kernel import MAIN_RETRIEVAL_STAGE, RunKernel

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "core" / "retrieval_dispatch_runtime.py"
ORCHESTRATOR = ROOT / "core" / "pipeline_orchestrator.py"


def _deps(fake_process: Any, seen_urls: set[str], collected_images: set[str]):
    return RetrievalDispatchDeps(
        process_search_queries=fake_process,
        query_embedding=[0.1, 0.2],
        seen_urls=seen_urls,
        collected_images=collected_images,
        embed_provider="embed-provider",
        embed_model="embed-model",
        local_url="http://local",
        embed_texts=lambda texts, **kwargs: texts,
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        provider_diagnostics=[],
    )


def test_builds_existing_pass_record_shape_for_representative_stage() -> None:
    record = build_retrieval_pass_record(
        stage="disambiguation_retry",
        iteration=2,
        queries=("q1", "q2"),
        providers=("exa", "tavily"),
        provider_role="disambiguation_retry",
        search_depth="advanced",
        results_per_query=7,
    )

    assert record == {
        "stage": "disambiguation_retry",
        "iteration": 2,
        "queries": ["q1", "q2"],
        "providers": ["exa", "tavily"],
        "provider_role": "disambiguation_retry",
        "search_depth": "advanced",
        "results_per_query": 7,
    }


def test_dispatch_delegates_exact_argument_mapping_and_records_deltas() -> None:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    seen_urls = {"https://already.example"}
    collected_images = {"old-image"}

    def fake_process(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        calls.append((args, kwargs))
        args[8].add("https://new.example")
        args[9].add("new-image")
        return [{"url": "https://new.example", "text": "chunk"}]

    records: list[dict[str, Any]] = []
    queries = ["first query", "second query"]
    dispatch = RecordedRetrievalDispatch(
        stage="disambiguation_retry",
        queries=queries,
        intent="research",
        complexity="high",
        search_depth="deep",
        results_per_query=5,
        include_domains=["include.example"],
        exclude_domains=["exclude.example"],
        providers=["exa", "linkup"],
        provider_role="disambiguation_retry",
        iteration=3,
        exa_domain_filter=["edu"],
        entity_hint="Entity",
    )

    outcome = execute_recorded_retrieval_dispatch(
        dispatch,
        _deps(fake_process, seen_urls, collected_images),
        retrieval_pass_records=records,
    )

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[:7] == (
        ["first query", "second query"],
        "research",
        "high",
        "deep",
        5,
        ["include.example"],
        ["exclude.example"],
    )
    assert args[7] == [0.1, 0.2]
    assert args[8] is seen_urls
    assert args[9] is collected_images
    assert args[10:13] == ("embed-provider", "embed-model", "http://local")
    assert kwargs["search_providers"] == ["exa", "linkup"]
    assert kwargs["exa_domain_filter"] == ["edu"]
    assert kwargs["entity_hint"] == "Entity"
    assert kwargs["provider_role"] == "disambiguation_retry"
    assert kwargs["iteration"] == 3
    assert kwargs["provider_diagnostics"] == []
    assert outcome.seen_url_delta == 1
    assert outcome.chunk_delta == 1
    assert records == [outcome.pass_record]
    assert records[0]["queries"] == queries
    assert records[0]["providers"] == ["exa", "linkup"]


def test_helper_does_not_mutate_queries_or_replace_caller_owned_collections() -> None:
    seen_urls: set[str] = set()
    collected_images: set[str] = set()
    original_queries = ["alpha", "beta"]

    def fake_process(*args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        args[8].add("https://delta.example")
        return []

    dispatch = RecordedRetrievalDispatch(
        stage="supplemental_search",
        queries=original_queries,
        intent="research",
        complexity="medium",
        search_depth="standard",
        results_per_query=3,
        include_domains=[],
        exclude_domains=[],
        providers=["tavily"],
        provider_role="supplemental_search",
    )

    outcome = execute_recorded_retrieval_dispatch(
        dispatch,
        _deps(fake_process, seen_urls, collected_images),
    )

    assert original_queries == ["alpha", "beta"]
    assert seen_urls == {"https://delta.example"}
    assert collected_images == set()
    assert outcome.seen_url_delta == 1
    assert outcome.chunk_delta == 0


def test_static_guard_retrieval_dispatch_helper_is_not_policy_brain() -> None:
    source = HELPER.read_text()
    assert "select_providers" not in source
    assert "ask_model" not in source
    assert "core.prompts" not in source
    assert "choose_retrieval_search_depth" not in source
    assert "choose_supplemental_search_depth" not in source


def test_static_guard_orchestrator_direct_search_calls_moved_to_helper() -> None:
    helper_source = HELPER.read_text()
    orchestrator_source = ORCHESTRATOR.read_text()
    assert "process_search_queries(" in helper_source
    assert "process_search_queries(" not in orchestrator_source
    assert "execute_main_retrieval_pass_from_scope" in orchestrator_source
    assert len(orchestrator_source.splitlines()) <= 6922


def test_static_guard_helper_imports_no_provider_prompt_or_model_modules() -> None:
    tree = ast.parse(HELPER.read_text())
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
    assert "core.routing" not in imported_modules
    assert "core.prompts" not in imported_modules
    assert "core.llm" not in imported_modules


def test_embedding_action_record_preserves_exact_embedding_call_fields() -> None:
    from core.retrieval_dispatch_runtime import EmbeddingActionRecord, execute_embedding_action

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_embed(*args: Any, **kwargs: Any) -> list[list[float]]:
        calls.append((args, kwargs))
        return [[0.5, 0.25]]

    action = EmbeddingActionRecord(
        topic_text="Exact Topic",
        provider="embed-provider",
        model="embed-model",
        base_url="http://local",
    )

    assert execute_embedding_action(action, fake_embed) == [0.5, 0.25]
    assert calls == [((['Exact Topic'],), {"provider": "embed-provider", "model": "embed-model", "base_url": "http://local"})]
    assert action.action_role == "pre_retrieval_topic_embedding"


def test_retrieval_dispatch_action_preserves_exact_authorized_fields() -> None:
    dispatch = RecordedRetrievalDispatch(
        stage="main_retrieval",
        queries=("q1", "q2"),
        intent="research",
        complexity="high",
        search_depth="advanced",
        results_per_query=8,
        include_domains=("include.example",),
        exclude_domains=("exclude.example",),
        providers=("tavily", "linkup"),
        provider_role="main_retrieval",
        iteration=2,
        exa_domain_filter=("edu",),
        linkup_depth_override="deep",
        entity_hint="Entity",
        prior_queries_for_similarity=("old q",),
        query_similarity_basis="previous_main_retrieval_iteration",
    )

    assert list(dispatch.queries) == ["q1", "q2"]
    assert list(dispatch.providers) == ["tavily", "linkup"]
    assert dispatch.search_depth == "advanced"
    assert dispatch.results_per_query == 8
    assert list(dispatch.include_domains) == ["include.example"]
    assert list(dispatch.exclude_domains) == ["exclude.example"]
    assert dispatch.provider_role == "main_retrieval"
    assert dispatch.iteration == 2
    assert list(dispatch.exa_domain_filter or ()) == ["edu"]
    assert dispatch.linkup_depth_override == "deep"
    assert dispatch.entity_hint == "Entity"


def test_main_retrieval_dispatch_consumes_scheduler_action_over_legacy_locals() -> None:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    seen_urls: set[str] = set()

    def fake_process(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        calls.append((args, kwargs))
        args[8].add("https://scheduled.example")
        return [{"url": "https://scheduled.example", "text": "scheduled"}]

    class _Deps:
        @staticmethod
        def compute_similarities(*_args: Any, **_kwargs: Any) -> list[Any]:
            return []

    kernel = RunKernel.start(run_id="run-1", request_id="request-1")
    main_retrieval_kernel_action = kernel.authorize_main_retrieval_pass(
        inputs={"iteration": 2, "query_count": 1}
    )
    scheduled_action = schedule_main_retrieval_action(
        RetrievalScheduleInput(
            stage="main_retrieval",
            current_queries=["scheduled query"],
            iteration=2,
            provider_role="weak_corpus_recovery",
            search_depth="advanced",
            providers=["scheduled-provider"],
            recovery_active=True,
        )
    )
    scope = {
        "iteration": 2,
        "router_query_preparation_contract": build_router_query_preparation_state(
            query="topic", router_text=None
        ),
        "main_retrieval_kernel_action": main_retrieval_kernel_action,
        "retrieval_scheduled_action": scheduled_action,
        "current_queries": ["legacy local query"],
        "loop_providers": ["legacy-provider"],
        "current_search_depth": "legacy-depth",
        "retrieval_provider_role": "legacy-role",
        "results_per_query": 4,
        "top_chunks": 8,
        "max_iterations": 3,
        "intent": "research",
        "complexity": "high",
        "include_domains": ["include.example"],
        "exclude_domains": ["exclude.example"],
        "ACADEMIC_DOMAINS": ["edu"],
        "is_academic": False,
        "entity_hint_for_retrieval": "Entity",
        "retrieval_stop_active_telemetry": {},
        "run_id": "run-1",
        "retrieval_batch_dispatch_trace": {"authorized": True},
        "active_source_class_recovery_lifecycle": {},
        "weak_corpus_recovery_used": True,
        "weak_corpus_recovery_attempted": True,
        "weak_corpus_recovery_decision": "approved",
        "retrieval_loop_contract_state": None,
        "similarity_prior_queries": ["prior query"],
        "query_similarity_basis": "previous_main_retrieval_iteration",
        "process_search_queries": fake_process,
        "query_embedding": [0.1],
        "seen_urls": seen_urls,
        "collected_images": set(),
        "embed_provider": "embed-provider",
        "embed_model": "embed-model",
        "local_url": None,
        "embed_texts": lambda *_args, **_kwargs: [],
        "deps": _Deps(),
        "status": object(),
        "provider_diagnostics": [],
    }

    records: list[dict[str, Any]] = []
    outcome = execute_main_retrieval_pass_from_scope(
        scope,
        retrieval_pass_records=records,
    )

    args, kwargs = calls[0]
    assert args[:7] == (
        ["scheduled query"],
        "research",
        "high",
        "advanced",
        4,
        ["include.example"],
        ["exclude.example"],
    )
    assert kwargs["search_providers"] == ["scheduled-provider"]
    assert kwargs["provider_role"] == "weak_corpus_recovery"
    assert kwargs["iteration"] == 2
    assert outcome.descriptor.current_queries == ("scheduled query",)
    assert outcome.descriptor.provider_list == ("scheduled-provider",)
    assert outcome.descriptor.search_depth == "advanced"
    assert outcome.observation.action_id == main_retrieval_kernel_action.action_id
    kernel.reduce(outcome.observation)
    assert kernel.state.projections[MAIN_RETRIEVAL_STAGE]["chunk_delta"] == 1
    assert records[0]["queries"] == ["scheduled query"]
    assert records[0]["providers"] == ["scheduled-provider"]


def _post_material_test_scope() -> tuple[dict[str, Any], RunKernel]:
    class _Deps:
        @staticmethod
        def compute_similarities(*_args: Any, **_kwargs: Any) -> list[Any]:
            return []

    kernel = RunKernel.start(run_id="run-post-material", request_id="request-post-material")
    action = kernel.authorize_main_retrieval_pass(
        inputs={"iteration": 1, "query_count": 1}
    )
    scheduled_action = schedule_main_retrieval_action(
        RetrievalScheduleInput(
            stage="main_retrieval",
            current_queries=["fixture query"],
            iteration=1,
            provider_role="main_retrieval",
            search_depth="basic",
            providers=["fixture-provider"],
        )
    )

    def fake_process(*args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        args[8].add("https://fixture.invalid/result")
        return [{"url": "https://fixture.invalid/result", "text": "fixture"}]

    return (
        {
            "iteration": 1,
            "router_query_preparation_contract": build_router_query_preparation_state(
                query="fixture topic", router_text=None
            ),
            "main_retrieval_kernel_action": action,
            "retrieval_scheduled_action": scheduled_action,
            "results_per_query": 4,
            "top_chunks": 8,
            "max_iterations": 3,
            "intent": "research",
            "complexity": "medium",
            "include_domains": [],
            "exclude_domains": [],
            "ACADEMIC_DOMAINS": ["edu"],
            "is_academic": False,
            "entity_hint_for_retrieval": None,
            "retrieval_stop_active_telemetry": {},
            "run_id": "run-post-material",
            "retrieval_batch_dispatch_trace": {"authorized": True},
            "active_source_class_recovery_lifecycle": {},
            "weak_corpus_recovery_used": False,
            "weak_corpus_recovery_attempted": False,
            "weak_corpus_recovery_decision": "not_attempted",
            "retrieval_loop_contract_state": None,
            "similarity_prior_queries": None,
            "query_similarity_basis": None,
            "process_search_queries": fake_process,
            "query_embedding": [0.1],
            "seen_urls": set(),
            "collected_images": set(),
            "embed_provider": "embed-provider",
            "embed_model": "embed-model",
            "local_url": None,
            "embed_texts": lambda *_args, **_kwargs: [],
            "deps": _Deps(),
            "status": object(),
            "provider_diagnostics": [],
        },
        kernel,
    )


_PRIVATE_FAILURE_FRAGMENTS = (
    "private raw prompt",
    "private provider payload",
    "https://private.invalid/source",
    "private model response",
    "private traceback",
)


@pytest.mark.parametrize(
    ("boundary", "expected_subtype"),
    (
        (
            "identity",
            RetrievalPostMaterialFailureSubtype.SOURCE_RESULT_IDENTITY_SET_PROJECTION,
        ),
        (
            "telemetry",
            RetrievalPostMaterialFailureSubtype.DISCOVERY_RESULT_TELEMETRY_PROJECTION,
        ),
        (
            "observation",
            RetrievalPostMaterialFailureSubtype.RETRIEVAL_PASS_OBSERVATION_CONSTRUCTION,
        ),
        (
            "outcome",
            RetrievalPostMaterialFailureSubtype.MAIN_RETRIEVAL_OUTCOME_CONSTRUCTION,
        ),
        (
            "unclassified",
            RetrievalPostMaterialFailureSubtype.POST_MATERIAL_UNCLASSIFIED,
        ),
    ),
)
def test_post_material_failures_project_only_closed_bounded_causes(
    boundary: str,
    expected_subtype: RetrievalPostMaterialFailureSubtype,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope, kernel = _post_material_test_scope()
    private_message = " | ".join(_PRIVATE_FAILURE_FRAGMENTS)

    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(private_message)

    if boundary in {"identity", "telemetry"}:
        original_store_mapping = retrieval_runtime._store_mapping

        def selective_store_failure(
            store: Any, *method_names: str
        ) -> dict[str, Any] | None:
            if method_names[0] == (
                "identity_set_ref" if boundary == "identity" else "telemetry"
            ):
                fail()
            return original_store_mapping(store, *method_names)

        monkeypatch.setattr(
            retrieval_runtime,
            "_store_mapping",
            selective_store_failure,
        )
    elif boundary == "observation":
        monkeypatch.setattr(retrieval_runtime.Observation, "from_action", fail)
    elif boundary == "outcome":
        monkeypatch.setattr(retrieval_runtime, "MainRetrievalPassOutcome", fail)
    else:
        monkeypatch.setattr(
            retrieval_runtime,
            "summarize_retrieval_pass_result",
            fail,
        )

    with pytest.raises(RetrievalPostMaterialDispatchError) as caught:
        execute_main_retrieval_pass_from_scope(scope, retrieval_pass_records=[])

    assert caught.value.subtype is expected_subtype
    assert MAIN_RETRIEVAL_STAGE not in kernel.state.projections
    payload = compatibility_cli._bounded_terminal_payload(
        entrypoint="scryraven",
        exc=caught.value,
        config=RunConfig(query="fixture query"),
    )
    terminal = payload["terminal"]
    assert payload["terminal_status"] == "stopped"
    assert terminal["code"] == "bounded_run_failed"
    assert terminal["owner"] == "core.pipeline_orchestrator.run_pipeline"
    assert terminal["classification"] == "pipeline_failure"
    assert terminal["cause_owner"] == (
        "core.retrieval_dispatch_runtime.execute_main_retrieval_pass_from_scope"
    )
    assert terminal["cause_classification"] == "retrieval_post_material_failure"
    assert terminal["cause_subtype"] == expected_subtype.value
    assert payload["answer_present"] is False
    assert payload["citation_count"] == 0
    encoded = json.dumps(payload, sort_keys=True).casefold()
    assert "traceback" not in encoded
    for fragment in _PRIVATE_FAILURE_FRAGMENTS:
        assert fragment.casefold() not in encoded


def test_invalid_retrieval_lineage_is_not_laundered_into_post_material_failure() -> None:
    scope, _kernel = _post_material_test_scope()
    scope["main_retrieval_kernel_action"] = object()

    with pytest.raises(ValueError, match="AuthorizedAction") as caught:
        execute_main_retrieval_pass_from_scope(scope, retrieval_pass_records=[])

    assert not isinstance(caught.value, RetrievalPostMaterialDispatchError)


def test_pipeline_embedding_and_main_retrieval_consume_action_records() -> None:
    source = ORCHESTRATOR.read_text()
    helper_source = HELPER.read_text()

    assert "embedding_action = EmbeddingActionRecord" in source
    assert "query_embedding = execute_embedding_action(embedding_action, embed_texts)" in source
    assert "main_retrieval_kernel_action = run_kernel.authorize_main_retrieval_pass" in source
    assert '"retrieval_scheduled_action"' in helper_source
    assert '"main_retrieval_kernel_action"' in helper_source
    assert "scheduled_action: RetrievalScheduledAction" in helper_source
    assert "dispatch_action = RecordedRetrievalDispatch" in helper_source
    assert "current_queries=dispatch_action.queries" in helper_source
    assert "provider_list=dispatch_action.providers" in helper_source
    assert "search_depth=dispatch_action.search_depth" in helper_source
