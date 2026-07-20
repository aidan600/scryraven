"""Offline product-path proof for ordinary DISCOVER candidate convergence.

Test class: phase_focus / offline_product_path_proof / PRODUCT-PATH-REGRESSION.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import core.pipeline as pipeline
import core.pipeline_orchestrator as orchestrator
from core.db import execution_jsonl_to_run_row
from core.discovery_source_result import (
    DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP,
    DISCOVERY_RESULT_MATERIAL_CHAR_CAP,
    DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP,
    DISCOVERY_SOURCE_RESULT_IDENTITY_CANONICAL_BYTE_CAP,
    DISCOVERY_SOURCE_RESULT_IDENTITY_RUN_CAP,
    DiscoveryResultMaterialStore,
    DiscoverySourceResultError,
)
from core.legacy_review_runtime_stage import LegacyReviewRuntimeDeps
from core.ordinary_discovery_candidate_handoff_runtime import (
    ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY,
    OrdinaryDiscoveryAuthoritySnapshot,
    OrdinaryDiscoveryCandidateHandoffError,
    build_ordinary_discovery_authority_snapshot,
    build_ordinary_discovery_candidate_action_inputs,
    execute_ordinary_discovery_candidate_handoff_action,
    prepare_ordinary_discovery_selection,
    validate_ordinary_discovery_candidate_reduction,
)
from core.provider_plan import ProviderPlan, ProviderPlanRecord
from core.query_plan import QueryPlan
from core.retrieval_dispatch_runtime import (
    RecordedRetrievalDispatch,
    RetrievalDispatchDeps,
    execute_recorded_retrieval_dispatch,
    execute_scrutineer_remediation_from_scope,
    execute_supplemental_search_from_scope,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.search_executor_handoff_runtime import (
    SEARCH_EXECUTOR_HANDOFF_ORIGIN_ORDINARY_QUERY_PROVIDER,
    contract_ref_from_contract,
)
from core.search_result_candidate_packet import (
    ORDINARY_SEARCH_RESULT_CANDIDATE_SNIPPET_MAX_CHARS,
    SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER,
    SEARCH_RESULT_CANDIDATE_PACKET_OWNER,
    SearchResultCandidatePacketError,
    validate_ordinary_search_result_candidate_packet,
)
from tests.helpers.offline_ordinary_pipeline import (
    execution_event_from_log,
    run_post_retirement_ordinary_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
CLI = ROOT / "proplex" / "__main__.py"


def _digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _function_node(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def _called_names(node: ast.AST) -> set[str]:
    calls: set[str] = set()
    for item in ast.walk(node):
        if not isinstance(item, ast.Call):
            continue
        if isinstance(item.func, ast.Name):
            calls.add(item.func.id)
        elif isinstance(item.func, ast.Attribute):
            calls.add(item.func.attr)
    return calls


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _canonical_bytes(value: Mapping[str, Any]) -> int:
    return len(
        json.dumps(
            _plain(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    )


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _plain(value),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _recompute_projection_bytes(projection: dict[str, Any]) -> None:
    projection["canonical_result_ref_state_bytes"] = 0
    while True:
        measured = _canonical_bytes(projection)
        if projection["canonical_result_ref_state_bytes"] == measured:
            return
        projection["canonical_result_ref_state_bytes"] = measured


def _provider_result(
    url: str,
    *,
    title: str = "Official current rule",
    credibility: int = 4,
    material: str | None = None,
) -> dict[str, Any]:
    body = material or ("Provider-returned current rule material. " * 20)
    return {
        "title": title,
        "url": url,
        "domain": url.split("/", 3)[2],
        "credibility": credibility,
        "snippet": body[:500],
        "raw_content": body,
    }


@dataclass
class _AuthorityFixture:
    run_id: str
    request_id: str
    queries: tuple[str, ...]
    query_plan: QueryPlan
    provider_plan: ProviderPlan
    provider_records: dict[str, ProviderPlanRecord]
    snapshot: OrdinaryDiscoveryAuthoritySnapshot
    kernel: RunKernel
    retrieval_action_ref: dict[str, Any]

    def _provider_context(self, provider: str) -> dict[str, Any]:
        record = self.provider_records[provider]
        route = record.route_decision
        return {
            "provider": provider,
            "provider_plan_record_ref": record.to_ref(),
            "provider_route_ref": record.route_ref(),
            "provider_capability": _enum_value(route.capability),
            "provider_qualifier": _enum_value(route.qualifier),
            "provider_operation": str(route.operation or ""),
            "provider_variant": str(route.variant or ""),
            "provider_output_type": str(route.output_type or ""),
        }

    def result_context(
        self,
        *,
        provider: str = "tavily",
        query_index: int = 0,
    ) -> dict[str, Any]:
        query_ref = self.query_plan.execution_item_refs(1)[query_index]
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "stage": "main_retrieval",
            "iteration": 1,
            "retrieval_role": "main_retrieval",
            "query_role": query_ref["query_plan_role"],
            "retrieval_action_ref": dict(self.retrieval_action_ref),
            "query_plan_ref": self.query_plan.to_ref(),
            "query_plan_item_ref": query_ref,
            "provider_plan_ref": self.provider_plan.to_ref(),
            **self._provider_context(provider),
        }

    def dispatch_context(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "stage": "main_retrieval",
            "iteration": 1,
            "retrieval_role": "main_retrieval",
            "retrieval_action_ref": dict(self.retrieval_action_ref),
            "query_plan_ref": self.query_plan.to_ref(),
            "query_plan_item_refs": self.query_plan.execution_item_refs(1),
            "provider_plan_ref": self.provider_plan.to_ref(),
            "provider_contexts": {provider: self._provider_context(provider) for provider in self.provider_records},
        }


def _authority(
    *,
    queries: Sequence[str] = ("official current rule",),
    providers: Sequence[str] = ("tavily",),
    run_id: str = "run-discover-handoff",
    request_id: str = "request-discover-handoff",
) -> _AuthorityFixture:
    ordered_queries = tuple(str(query) for query in queries)
    query_plan = QueryPlan(plan_id=f"query-plan:{run_id}").admit_execution_queries(
        ordered_queries,
        phase="main_retrieval",
        iteration=1,
    )
    available = {provider: provider in providers for provider in ("tavily", "linkup", "exa")}
    provider_plan = ProviderPlan.from_available_keys(
        available,
        plan_id=f"provider-plan:{run_id}",
    )
    provider_records: dict[str, ProviderPlanRecord] = {}
    for provider in providers:
        provider_records[provider] = provider_plan.record_main_retrieval(
            query_type="other",
            intent="general",
            complexity="low",
            report_type="general_research",
            is_academic=False,
            suppress_tavily=False,
            base_search_depth="basic",
            iteration=1,
            primary_override=[provider],
            scout_override=None,
            choose_search_depth=lambda _complexity, base, _iteration: base or "basic",
        )
    snapshot = build_ordinary_discovery_authority_snapshot(
        query_plan=query_plan,
        provider_plan=provider_plan,
    )
    kernel = RunKernel.start(run_id=run_id, request_id=request_id)
    retrieval_action = kernel.authorize_main_retrieval_pass()
    retrieval_action_ref = {
        "action_id": retrieval_action.action_id,
        "action_type": retrieval_action.action_type.value,
        "stage": retrieval_action.stage,
        "sequence": retrieval_action.sequence,
    }
    kernel.reduce(
        Observation.from_action(
            retrieval_action,
            observation_type=ObservationType.RETRIEVAL_PASS_RESULT,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    return _AuthorityFixture(
        run_id=run_id,
        request_id=request_id,
        queries=ordered_queries,
        query_plan=query_plan,
        provider_plan=provider_plan,
        provider_records=provider_records,
        snapshot=snapshot,
        kernel=kernel,
        retrieval_action_ref=retrieval_action_ref,
    )


def _admit(
    store: DiscoveryResultMaterialStore,
    authority: _AuthorityFixture,
    *,
    provider: str = "tavily",
    query_index: int = 0,
    call_ordinal: int = 1,
    result_rank: int = 1,
    url: str = "https://official.example.test/current-rule",
    material: str = "Provider-returned current rule material. " * 20,
    title: str = "Official current rule",
) -> Any:
    return store.admit_result(
        context=authority.result_context(
            provider=provider,
            query_index=query_index,
        ),
        provider=provider,
        call_ordinal=call_ordinal,
        result_rank=result_rank,
        result=_provider_result(url, material=material, title=title),
        material_text=material,
        material_class="provider_returned_excerpt",
    )


def _run_process_search_queries(
    *,
    authority: _AuthorityFixture,
    max_results: int,
    complexity: str,
    store: DiscoveryResultMaterialStore,
    query_embedding: list[float] | None = None,
) -> list[dict[str, Any]]:
    return pipeline.process_search_queries(
        list(authority.queries),
        "general",
        complexity,
        "advanced" if complexity == "high" else "basic",
        max_results,
        [],
        [],
        query_embedding,
        set(),
        set(),
        "offline-embed-provider",
        "offline-embed-model",
        None,
        lambda texts, **_kwargs: [[1.0, 0.0] for _ in texts],
        lambda _query, embeddings: [0.8 for _ in embeddings],
        search_providers=list(authority.provider_records),
        provider_role="main_retrieval",
        iteration=1,
        discovery_result_context=authority.dispatch_context(),
        discovery_result_store=store,
    )


def _selection(
    authority: _AuthorityFixture,
    store: DiscoveryResultMaterialStore,
    identities: Sequence[Any],
) -> Any:
    return prepare_ordinary_discovery_selection(
        final_top_evidence=[
            {
                "url": identity.normalized_url,
                "score": 1.0 - (index / 1_000),
                "rrf_score": 0.04,
                "credibility": 4,
                "chunk_digest": _digest(f"chunk:{index}"),
                "source_result_ref": identity.ref(),
                "source_material_ref": dict(identity.material_ref),
            }
            for index, identity in enumerate(identities, start=1)
        ],
        discovery_result_store=store,
        selected_candidate_cap=40,
        authority_snapshot=authority.snapshot,
    )


def _execute_selection(
    authority: _AuthorityFixture,
    store: DiscoveryResultMaterialStore,
    identities: Sequence[Any],
    *,
    answer_contract_ref: Mapping[str, Any] | None = None,
) -> tuple[Any, Any, Any]:
    selection = _selection(authority, store, identities)
    inputs = build_ordinary_discovery_candidate_action_inputs(
        run_id=authority.run_id,
        request_id=authority.request_id,
        source_result_identity_set_ref=store.identity_set_ref(),
        selection=selection,
        answer_contract_ref=answer_contract_ref,
    )
    action = authority.kernel.authorize_ordinary_discovery_candidate_handoff(inputs=inputs)
    execution = execute_ordinary_discovery_candidate_handoff_action(
        action=action,
        selection=selection,
        discovery_result_store=store,
        authority_snapshot=authority.snapshot,
        answer_contract_ref=answer_contract_ref,
    )
    return inputs, action, execution


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key).casefold() for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, (list, tuple)):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def test_identity_is_stable_and_binds_real_pre_chunk_authority() -> None:
    authority = _authority()
    first_store = DiscoveryResultMaterialStore()
    second_store = DiscoveryResultMaterialStore()
    first = _admit(first_store, authority, call_ordinal=3, result_rank=7)
    second = _admit(second_store, authority, call_ordinal=3, result_rank=7)

    assert first is not None and second is not None
    assert first.ref() == second.ref()
    assert dict(first.query_plan_ref) == authority.query_plan.to_ref()
    canonical_item_ref = authority.query_plan.execution_item_refs(1)[0]
    assert dict(first.query_plan_item_ref) == {
        key: canonical_item_ref[key]
        for key in (
            "query_plan_item_id",
            "query_plan_item_digest",
            "query_digest",
        )
    }
    assert dict(first.provider_plan_ref) == authority.provider_plan.to_ref()
    assert dict(first.provider_plan_record_ref) == (authority.provider_records["tavily"].to_ref())
    assert dict(first.provider_route_ref) == (authority.provider_records["tavily"].route_ref())
    assert first.retrieval_role == "main_retrieval"
    assert first.retrieval_action_ref["action_id"] == (authority.retrieval_action_ref["action_id"])
    assert first.capability == "DISCOVER"
    assert first.provider_call_ordinal == 3
    assert first.result_rank == 7
    assert first.canonical_bytes <= (DISCOVERY_SOURCE_RESULT_IDENTITY_CANONICAL_BYTE_CAP)
    identity = first.to_dict()
    assert not _collect_keys(identity) & {
        "text",
        "title",
        "snippet",
        "raw_content",
        "chunks",
        "embedding",
    }
    closed_flags = {
        key: value
        for key, value in identity.items()
        if isinstance(value, bool)
        and (
            key.endswith("_executed")
            or key.endswith("_retained")
            or key.endswith("_authority")
            or key.endswith("_created")
            or key.endswith("_charged")
            or key.endswith("_satisfied")
            or key.endswith("_decided")
            or key.endswith("_claimed")
        )
    }
    assert closed_flags
    assert set(closed_flags.values()) == {False}

    missing_role = authority.result_context()
    missing_role.pop("retrieval_role")
    with pytest.raises(DiscoverySourceResultError, match="retrieval_role"):
        first_store.admit_result(
            context=missing_role,
            provider="tavily",
            call_ordinal=4,
            result_rank=1,
            result=_provider_result("https://official.example.test/missing-role"),
            material_text="bounded material",
            material_class="provider_returned_excerpt",
        )


def test_store_enforces_80_4096_20000_and_8_caps_stable_first() -> None:
    authority = _authority()
    run_cap_store = DiscoveryResultMaterialStore()
    admitted = [
        _admit(
            run_cap_store,
            authority,
            call_ordinal=index,
            url=f"https://official.example.test/result-{index}",
            material="m",
        )
        for index in range(1, DISCOVERY_SOURCE_RESULT_IDENTITY_RUN_CAP + 2)
    ]
    assert DISCOVERY_SOURCE_RESULT_IDENTITY_RUN_CAP == 80
    assert all(item is not None for item in admitted[:-1])
    assert admitted[-1] is None
    assert run_cap_store.telemetry()["source_result_identity_run_cap_overflow_count"] == 1

    byte_store = DiscoveryResultMaterialStore()
    oversized = _admit(
        byte_store,
        authority,
        url="https://official.example.test/?" + ("x" * 4_000),
        material="m",
    )
    assert DISCOVERY_SOURCE_RESULT_IDENTITY_CANONICAL_BYTE_CAP == 4_096
    assert oversized is None
    assert byte_store.telemetry()["source_result_identity_byte_cap_overflow_count"] == 1

    material_store = DiscoveryResultMaterialStore()
    material_identity = _admit(
        material_store,
        authority,
        material="z" * 21_000,
    )
    assert material_identity is not None
    material_record = material_store.material_for_ref(material_identity.ref())
    assert material_record is not None
    assert DISCOVERY_RESULT_MATERIAL_CHAR_CAP == 20_000
    assert material_record.retained_chars == DISCOVERY_RESULT_MATERIAL_CHAR_CAP
    assert material_record.original_chars == 21_000
    assert material_record.truncated is True

    contributor_store = DiscoveryResultMaterialStore()
    duplicate_url = "https://official.example.test/shared"
    duplicate_identities = [
        _admit(
            contributor_store,
            authority,
            call_ordinal=index,
            result_rank=index,
            url=duplicate_url,
            material=f"material-{index}",
        )
        for index in range(1, DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP + 3)
    ]
    contributor_facts = contributor_store.contributors_for_url(duplicate_url)
    assert DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP == 8
    assert len({item.source_result_id for item in duplicate_identities}) == len(duplicate_identities)
    assert contributor_facts["contributor_count"] == len(duplicate_identities)
    assert contributor_facts["contributing_source_result_refs"] == [
        identity.ref() for identity in duplicate_identities[:DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP]
    ]
    assert contributor_facts["contributor_overflow_count"] == 2


@pytest.mark.parametrize(
    ("complexity", "per_call_limit"),
    [("low", 5), ("medium", 6), ("high", 8)],
)
def test_provider_call_caps_apply_before_result_reduction(
    monkeypatch: pytest.MonkeyPatch,
    complexity: str,
    per_call_limit: int,
) -> None:
    results = [_provider_result(f"https://official.example.test/result-{index}") for index in range(1, 11)]
    monkeypatch.setattr(
        pipeline,
        "search_web_results",
        lambda *_args, **_kwargs: (results, []),
    )
    authority = _authority()
    store = DiscoveryResultMaterialStore()
    _run_process_search_queries(
        authority=authority,
        max_results=per_call_limit,
        complexity=complexity,
        store=store,
    )

    telemetry = store.telemetry()
    assert telemetry["provider_results_returned_count"] == 10
    assert telemetry["provider_results_within_call_limit_count"] == per_call_limit
    assert telemetry["provider_call_result_overflow_count"] == 10 - per_call_limit
    assert [identity.result_rank for identity in store.identities()] == list(range(1, per_call_limit + 1))


def test_delayed_completion_preserves_submission_ordinals_and_contributors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queries = ("alpha rule", "beta rule")
    authority = _authority(queries=queries, providers=("tavily", "linkup"))
    release_by_query = {query: threading.Event() for query in queries}
    completion_order: list[tuple[str, str]] = []
    shared_url = "https://official.example.test/shared#provider-fragment"

    def result_for(provider: str, query: str) -> tuple[list[dict[str, Any]], list[str]]:
        completion_order.append((provider, query))
        return [
            _provider_result(
                shared_url,
                title=f"{provider} result for {query}",
                material=f"{provider} material for {query}. " * 20,
            )
        ], []

    def delayed_tavily(
        query: str,
        **_kwargs: Any,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        assert release_by_query[query].wait(timeout=2)
        return result_for("tavily", query)

    def early_linkup(
        query: str,
        **_kwargs: Any,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        release_by_query[query].set()
        return result_for("linkup", query)

    monkeypatch.setenv(
        "LINKUP_API_KEY", "offline-placeholder"  # pragma: allowlist secret
    )
    monkeypatch.setattr(pipeline, "search_web_results", delayed_tavily)
    monkeypatch.setattr(pipeline, "search_linkup_results", early_linkup)
    store = DiscoveryResultMaterialStore()
    passages = _run_process_search_queries(
        authority=authority,
        max_results=5,
        complexity="low",
        store=store,
    )

    for query in queries:
        assert completion_order.index(("linkup", query)) < completion_order.index(("tavily", query))
    identities = store.identities()
    assert [identity.provider_call_ordinal for identity in identities] == [1, 2, 3, 4]
    assert [identity.provider for identity in identities] == [
        "tavily",
        "linkup",
        "tavily",
        "linkup",
    ]
    assert [identity.query_digest for identity in identities] == [
        _digest("alpha rule"),
        _digest("alpha rule"),
        _digest("beta rule"),
        _digest("beta rule"),
    ]
    assert len({identity.source_result_id for identity in identities}) == 4
    assert len(passages) == 1
    contributor_facts = store.contributors_for_url(shared_url)
    assert contributor_facts["contributor_count"] == 4
    assert contributor_facts["contributing_source_result_refs"] == [identity.ref() for identity in identities]


def test_chunks_keep_source_and_material_lineage_without_rank_overwrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "search_web_results",
        lambda *_args, **_kwargs: (
            [_provider_result("https://official.example.test/current-rule")],
            [],
        ),
    )
    authority = _authority()
    store = DiscoveryResultMaterialStore()
    passages = _run_process_search_queries(
        authority=authority,
        max_results=5,
        complexity="low",
        store=store,
        query_embedding=[1.0, 0.0],
    )

    assert passages
    passage = passages[0]
    identity = store.identities()[0]
    assert passage["source_result_ref"] == identity.ref()
    assert passage["source_material_ref"] == dict(identity.material_ref)
    assert passage["material_label"] == identity.material_class
    assert passage["chunk_index"] == 1
    assert passage["chunk_digest"] == hashlib.sha256(passage["text"].encode("utf-8")).hexdigest()
    assert passage["provider_call_ordinal"] == 1
    assert passage["provider_rank_or_position"] == 1
    assert passage["score"] == pytest.approx(0.64)
    assert passage["full_page_fetched"] is False
    assert passage["product_fetch_read_executed"] is False
    assert "raw_content" not in passage


def test_valid_packet_and_runkernel_reduce_use_ordinary_origin_only() -> None:
    authority = _authority()
    store = DiscoveryResultMaterialStore()
    identity = _admit(
        store,
        authority,
        call_ordinal=3,
        result_rank=7,
        material="Bounded provider candidate snippet. " * 80,
    )
    assert identity is not None
    _inputs, _action, execution = _execute_selection(
        authority,
        store,
        [identity],
    )
    authority.kernel.reduce(execution.observation)

    packet = validate_ordinary_search_result_candidate_packet(execution.packet)
    record = packet["candidate_records"][0]
    assert packet["owner"] == SEARCH_RESULT_CANDIDATE_PACKET_OWNER
    assert packet["origin_kind"] == (SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER)
    assert execution.handoff["origin_kind"] == (SEARCH_EXECUTOR_HANDOFF_ORIGIN_ORDINARY_QUERY_PROVIDER)
    assert record["provider_result_rank"] == 7
    assert record["selected_candidate_rank"] == 1
    assert len(record["snippet"]) <= (ORDINARY_SEARCH_RESULT_CANDIDATE_SNIPPET_MAX_CHARS)
    serialized = json.dumps(
        {"packet": packet, "handoff": execution.handoff},
        sort_keys=True,
    ).casefold()
    assert "search_planner" not in serialized
    assert "live_search_validation" not in serialized
    assert "question_meaning_record" not in serialized
    assert packet.get("answer_contract_ref", {}) == {}

    projection = authority.kernel.state.projections[ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY]
    assert projection["canonical_result_ref_state_bytes"] == _canonical_bytes(projection)
    assert projection["canonical_result_ref_state_bytes"] <= (DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP)
    assert not _collect_keys(projection) & {
        "text",
        "snippet",
        "excerpt",
        "raw_content",
        "embedding",
        "chunks",
    }
    assert projection["acquisition_need_proposal_created"] is False
    assert projection["read_work_order_created"] is False
    assert projection["focused_extract_work_order_created"] is False
    assert projection["exact_url_transport_executed"] is False
    assert projection["exact_url_cap_charged"] is False
    assert projection["urls_fetched"] == 0
    assert not authority.kernel.state.acquisition_control_state


def test_packet_identity_binds_ordered_candidate_records() -> None:
    authority = _authority(
        run_id="run-packet-record-binding",
        request_id="request-packet-record-binding",
    )
    store = DiscoveryResultMaterialStore()
    identity = _admit(store, authority)
    assert identity is not None
    _inputs, _action, execution = _execute_selection(
        authority,
        store,
        [identity],
    )

    packet = _plain(execution.packet)
    original_packet_digest = packet["packet_digest"]
    original_record_digest = packet["candidate_records"][0]["record_digest"]
    record = packet["candidate_records"][0]
    record["normalized_url"] = "https://forged.example/redirected"
    record["domain"] = "forged.example"
    record_payload = dict(record)
    record_payload.pop("record_digest")
    record["record_digest"] = _canonical_digest(record_payload)
    assert record["record_digest"] != original_record_digest
    assert packet["packet_digest"] == original_packet_digest

    with pytest.raises(
        SearchResultCandidatePacketError,
        match="ordered candidate-record digest mismatch",
    ):
        validate_ordinary_search_result_candidate_packet(packet)


def test_40_candidate_projection_is_bounded_and_reports_overflow() -> None:
    authority = _authority(run_id="run-forty", request_id="request-forty")
    store = DiscoveryResultMaterialStore()
    identities = [
        _admit(
            store,
            authority,
            call_ordinal=index,
            url=f"https://official.example.test/result-{index}",
        )
        for index in range(1, 41)
    ]
    assert all(identity is not None for identity in identities)
    _inputs, _action, execution = _execute_selection(
        authority,
        store,
        identities,
    )
    authority.kernel.reduce(execution.observation)

    projection = execution.projection
    assert len(execution.packet["candidate_records"]) == 40
    assert projection["selected_candidate_count"] == 40
    assert projection["selected_source_result_refs_retained_count"] == 8
    assert projection["selected_source_result_ref_overflow_count"] == 32
    assert projection["canonical_result_ref_state_bytes"] == _canonical_bytes(projection)
    assert projection["canonical_result_ref_state_bytes"] <= 16 * 1_024


def test_stale_queryplan_and_providerplan_membership_blocks() -> None:
    authority = _authority()
    store = DiscoveryResultMaterialStore()
    identity = _admit(store, authority)
    assert identity is not None
    evidence = [
        {
            "url": identity.normalized_url,
            "score": 1.0,
            "source_result_ref": identity.ref(),
            "source_material_ref": dict(identity.material_ref),
        }
    ]

    stale_query = _authority(
        queries=("different authorized query",),
        run_id=authority.run_id,
        request_id=authority.request_id,
    )
    with pytest.raises(
        OrdinaryDiscoveryCandidateHandoffError,
        match="QueryPlan item is stale or absent",
    ):
        prepare_ordinary_discovery_selection(
            final_top_evidence=evidence,
            discovery_result_store=store,
            selected_candidate_cap=40,
            authority_snapshot=stale_query.snapshot,
        )

    stale_provider = _authority(
        providers=("linkup",),
        run_id=authority.run_id,
        request_id=authority.request_id,
    )
    with pytest.raises(
        OrdinaryDiscoveryCandidateHandoffError,
        match="provider route is stale or mismatched",
    ):
        prepare_ordinary_discovery_selection(
            final_top_evidence=evidence,
            discovery_result_store=store,
            selected_candidate_cap=40,
            authority_snapshot=stale_provider.snapshot,
        )


def test_current_contract_revision_blocks_at_authorize_and_reduce() -> None:
    authority = _authority(run_id="run-contract", request_id="request-contract")
    store = DiscoveryResultMaterialStore()
    identity = _admit(store, authority)
    assert identity is not None
    selection = _selection(authority, store, [identity])
    current_contract = {
        "contract_version": "answer-contract:v2",
        "contract_digest": _digest("answer-contract:v2"),
    }
    stale_contract_ref = {
        "source": "current_answer_contract",
        "contract_version": "answer-contract:v1",
        "contract_digest": _digest("answer-contract:v1"),
    }
    authority.kernel.state.current_answer_contract = dict(current_contract)
    stale_inputs = build_ordinary_discovery_candidate_action_inputs(
        run_id=authority.run_id,
        request_id=authority.request_id,
        source_result_identity_set_ref=store.identity_set_ref(),
        selection=selection,
        answer_contract_ref=stale_contract_ref,
    )
    with pytest.raises(RunKernelTransitionError, match="AnswerContract ref is stale"):
        authority.kernel.authorize_ordinary_discovery_candidate_handoff(inputs=stale_inputs)

    current_ref = contract_ref_from_contract(
        current_contract,
        source="current_answer_contract",
    )
    inputs = build_ordinary_discovery_candidate_action_inputs(
        run_id=authority.run_id,
        request_id=authority.request_id,
        source_result_identity_set_ref=store.identity_set_ref(),
        selection=selection,
        answer_contract_ref=current_ref,
    )
    action = authority.kernel.authorize_ordinary_discovery_candidate_handoff(inputs=inputs)
    execution = execute_ordinary_discovery_candidate_handoff_action(
        action=action,
        selection=selection,
        discovery_result_store=store,
        authority_snapshot=authority.snapshot,
        answer_contract_ref=current_ref,
    )
    authority.kernel.state.current_answer_contract = {
        "contract_version": "answer-contract:v3",
        "contract_digest": _digest("answer-contract:v3"),
    }
    with pytest.raises(
        RunKernelTransitionError,
        match="AnswerContract ref became stale",
    ):
        authority.kernel.reduce(execution.observation)


def test_duplicate_action_replay_is_rejected() -> None:
    authority = _authority(run_id="run-replay", request_id="request-replay")
    store = DiscoveryResultMaterialStore()
    identity = _admit(store, authority)
    assert identity is not None
    _inputs, _action, execution = _execute_selection(
        authority,
        store,
        [identity],
    )
    authority.kernel.reduce(execution.observation)
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        authority.kernel.reduce(execution.observation)


def test_invalid_observation_surface_and_packet_ref_are_rejected() -> None:
    authority = _authority(run_id="run-invalid", request_id="request-invalid")
    store = DiscoveryResultMaterialStore()
    identity = _admit(store, authority)
    assert identity is not None
    inputs, action, execution = _execute_selection(
        authority,
        store,
        [identity],
    )

    unknown_payload = _plain(execution.observation.payload)
    unknown_payload["unexpected_surface"] = {}
    with pytest.raises(
        OrdinaryDiscoveryCandidateHandoffError,
        match="unknown surface",
    ):
        validate_ordinary_discovery_candidate_reduction(
            action_inputs=inputs,
            observation_payload=unknown_payload,
            run_id=authority.run_id,
            request_id=authority.request_id,
            action_id=action.action_id,
        )

    invalid_payload = _plain(execution.observation.payload)
    projection = invalid_payload[ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY]
    packet_ref = projection["search_result_candidate_packet_ref"]
    packet_ref["packet_id"] = "search-result-candidate-packet:invalid"
    packet_ref["packet_digest"] = "0" * 64
    nested_ref = projection["discovery_result_state"]["search_result_candidate_packet_ref"]
    nested_ref["packet_id"] = packet_ref["packet_id"]
    nested_ref["packet_digest"] = packet_ref["packet_digest"]
    _recompute_projection_bytes(projection)
    with pytest.raises(OrdinaryDiscoveryCandidateHandoffError):
        validate_ordinary_discovery_candidate_reduction(
            action_inputs=inputs,
            observation_payload=invalid_payload,
            run_id=authority.run_id,
            request_id=authority.request_id,
            action_id=action.action_id,
        )


def test_serper_and_lightweight_disambiguation_remain_outside_ordinary_packet() -> None:
    process_source = inspect.getsource(pipeline.process_search_queries).casefold()
    assert "serper" not in process_source
    assert "search_serper" not in process_source
    assert "fetch_linkup_precision_block" not in process_source

    authority = _authority()
    store = DiscoveryResultMaterialStore()
    identity = _admit(store, authority)
    assert identity is not None
    _inputs, _action, execution = _execute_selection(
        authority,
        store,
        [identity],
    )
    packet_text = json.dumps(execution.packet, sort_keys=True).casefold()
    assert "serper" not in packet_text
    assert "lightweight_disambiguation" not in packet_text

    cli_source = CLI.read_text(encoding="utf-8")
    cli_tree = ast.parse(cli_source)
    main_node = next(node for node in cli_tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    main_source = ast.get_source_segment(cli_source, main_node) or ""
    assert "RunConfig(" in main_source
    assert "RunDeps(" in main_source
    assert "process_search_queries=process_search_queries" in main_source
    assert "outcome = run_pipeline(config, deps, status, accumulator)" in main_source
    assert "discover-result-candidate-handoff" not in main_source.casefold()


def test_recorded_dispatch_with_store_and_providers_requires_lineage_before_call() -> None:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def incompatible_call(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        calls.append((args, kwargs))
        return []

    store = DiscoveryResultMaterialStore()
    dispatch = RecordedRetrievalDispatch(
        stage="source_class_recovery",
        queries=("already authorized recovery query",),
        intent="general",
        complexity="low",
        search_depth="basic",
        results_per_query=5,
        include_domains=(),
        exclude_domains=(),
        providers=("tavily",),
        provider_role="source_class_recovery",
        iteration=1,
        discovery_result_context=None,
        discovery_result_store=store,
    )
    deps = RetrievalDispatchDeps(
        process_search_queries=incompatible_call,
        query_embedding=None,
        seen_urls=set(),
        collected_images=set(),
        embed_provider="offline",
        embed_model="offline",
        local_url=None,
        embed_texts=lambda *_args, **_kwargs: [],
        compute_similarities=lambda *_args, **_kwargs: [],
        status_container=object(),
        provider_diagnostics=[],
        discovery_result_store=store,
    )

    with pytest.raises(ValueError, match="result store but no exact lineage"):
        execute_recorded_retrieval_dispatch(dispatch, deps)
    assert calls == []


def test_every_ordinary_dispatch_family_binds_canonical_result_context() -> None:
    dispatch_runtime = CORE / "retrieval_dispatch_runtime.py"
    orchestrator_runtime = CORE / "pipeline_orchestrator.py"
    recovery_runner = CORE / "source_class_recovery_runner.py"
    provider_allocation = CORE / "controller_provider_search_allocation.py"

    scope_dispatch_owners = {
        "execute_disambiguation_retry_from_scope",
        "execute_supplemental_search_from_scope",
        "execute_scrutineer_remediation_from_scope",
    }
    for owner in scope_dispatch_owners:
        assert "_execute_scope_dispatch" in _called_names(_function_node(dispatch_runtime, owner))
    assert {
        "_recorded_discovery_context_from_scope",
        "execute_recorded_retrieval_dispatch",
    }.issubset(_called_names(_function_node(dispatch_runtime, "_execute_scope_dispatch")))

    assert "_bind_ordinary_discovery_process" in _called_names(
        _function_node(dispatch_runtime, "_ordinary_discovery_process_binder")
    )
    assert "_ordinary_discovery_process_binder" in _called_names(
        _function_node(dispatch_runtime, "source_class_recovery_context_from_scope")
    )
    assert "_bind_ordinary_discovery_process" in _called_names(
        _function_node(dispatch_runtime, "execute_conflict_resolution_from_scope")
    )

    recovery_calls = _called_names(_function_node(recovery_runner, "run_source_class_recovery_dispatch"))
    assert "bind_process_search_queries" in recovery_calls
    assert "record_provider_search_allocation_if_authority_authorized" in (recovery_calls)
    assert "bind_process_search_queries" in _called_names(
        _function_node(
            provider_allocation,
            "execute_provider_search_allocation_if_authority_authorized",
        )
    )

    product_owner_calls = _called_names(_function_node(orchestrator_runtime, "_run_pipeline_inner"))
    assert {
        "execute_disambiguation_retry_from_scope",
        "source_class_recovery_context_from_scope",
        "execute_conflict_resolution_from_scope",
        "LegacyReviewRuntimeDeps",
        "execute_legacy_review_runtime_stage_from_scope",
    }.issubset(product_owner_calls)
    review_fields = LegacyReviewRuntimeDeps.__dataclass_fields__
    assert review_fields["execute_supplemental_search"].default is (execute_supplemental_search_from_scope)
    assert review_fields["execute_scrutineer_remediation"].default is (execute_scrutineer_remediation_from_scope)


def test_pre_snapshot_disambiguation_result_can_rank_first_into_revision_one_packet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = DiscoveryResultMaterialStore()
    completion_order: list[str] = []
    later_retry_completed = threading.Event()
    monkeypatch.setattr(
        orchestrator,
        "DiscoveryResultMaterialStore",
        lambda **_kwargs: store,
    )

    def fake_tavily(
        query: str,
        **_kwargs: Any,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        if "explained overview" in query:
            completion_order.append("retry-provider-call-ordinal-3")
            later_retry_completed.set()
            return [
                _provider_result(
                    "https://alpha.example/retry-completed-first",
                    title="Alpha supporting overview",
                    credibility=4,
                    material=(
                        "Alpha supporting overview material from the authorized "
                        "disambiguation retry. "
                    )
                    * 14,
                )
            ], []
        if "2026 news" in query:
            assert later_retry_completed.wait(timeout=2)
            completion_order.append("retry-provider-call-ordinal-2")
            return [
                _provider_result(
                    "https://alpha.example/retry-ranked-first",
                    title="Alpha official current operating policy",
                    credibility=10,
                    material=(
                        "Alpha current official operating policy remains active "
                        "under the published rule. "
                    )
                    * 14,
                )
            ], []
        completion_order.append("main-provider-call-ordinal-1")
        return [
            _provider_result(
                "https://alpha.example/main-lower-relevance",
                title="Unrelated Gadget operating summary",
                credibility=0,
                material=(
                    "Unrelated Gadget operating summary with no requested subject "
                    "match. "
                )
                * 14,
            )
        ], []

    monkeypatch.setattr(pipeline, "search_web_results", fake_tavily)
    monkeypatch.setattr(
        pipeline,
        "search_linkup_results",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Linkup must not run in the offline Tavily proof")
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "search_exa_results",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Exa must not run in the offline Tavily proof")
        ),
    )

    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Fast",
        query="What is Alpha's current official operating policy?",
        core_topic="Alpha current official operating policy",
        primary_entity="Alpha",
        researcher_queries=["Alpha official current operating policy"],
        raw_author_response=(
            "Alpha's current official operating policy remains active. "
            "[[1]](https://alpha.example/retry-ranked-first)"
        ),
        deps_overrides={
            "process_search_queries": pipeline.process_search_queries,
            "provider_availability": {
                "tavily": True,
                "linkup": False,
                "exa": False,
                "serper": False,
            },
        },
        environment_overrides={
            "TAVILY_API_KEY": "offline-placeholder"  # pragma: allowlist secret
        },
    )

    assert not harness.forbidden_live_calls
    identities = {item.normalized_url: item for item in store.identities()}
    main_identity = identities["https://alpha.example/main-lower-relevance"]
    retry_identity = identities["https://alpha.example/retry-ranked-first"]
    later_retry_identity = identities[
        "https://alpha.example/retry-completed-first"
    ]
    assert store.material_for_ref(main_identity.ref()) is not None
    assert [
        main_identity.provider_call_ordinal,
        retry_identity.provider_call_ordinal,
        later_retry_identity.provider_call_ordinal,
    ] == [1, 2, 3]
    assert completion_order.index("retry-provider-call-ordinal-3") < (
        completion_order.index("retry-provider-call-ordinal-2")
    )

    trace = outcome.execution_trace
    packet = validate_ordinary_search_result_candidate_packet(
        trace["search_result_candidate_packet"]
    )
    record = packet["candidate_records"][0]
    handoff_ref = packet["search_executor_handoff_ref"]
    assert packet["owner"] == SEARCH_RESULT_CANDIDATE_PACKET_OWNER
    assert packet["packet_revision"] == 1
    assert packet["origin_kind"] == (
        SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER
    )
    assert handoff_ref["origin_kind"] == (
        SEARCH_EXECUTOR_HANDOFF_ORIGIN_ORDINARY_QUERY_PROVIDER
    )
    assert handoff_ref["query_plan_ref"] == dict(retry_identity.query_plan_ref)
    assert handoff_ref["selected_query_plan_item_refs"][0] == dict(
        retry_identity.query_plan_item_ref
    )
    assert retry_identity.query_role == "disambiguation"
    assert handoff_ref["provider_plan_ref"] == dict(
        retry_identity.provider_plan_ref
    )
    assert handoff_ref["provider_plan_record_refs"][0] == dict(
        retry_identity.provider_plan_record_ref
    )
    assert handoff_ref["provider_route_refs"][0] == dict(
        retry_identity.provider_route_ref
    )
    assert handoff_ref["retrieval_action_refs"][0] == dict(
        retry_identity.retrieval_action_ref
    )
    assert record["provider_used"] == retry_identity.provider == "tavily"
    assert record["provider_call_ordinal"] == (
        retry_identity.provider_call_ordinal
    )
    assert record["provider_result_rank"] == retry_identity.result_rank == 1
    assert record["source_result_ref"] == retry_identity.ref()
    assert record["source_material_ref"] == {
        "source_material_id": retry_identity.material_ref["material_id"],
        "source_material_digest": retry_identity.material_ref[
            "material_digest"
        ],
        "material_class": retry_identity.material_class,
    }
    assert record["selected_candidate_rank"] == 1
    assert record["normalized_url"] == retry_identity.normalized_url
    assert record["scoring_provenance"] == {
        "ranking_method": "existing_discovery_passage_ranking",
        "relevance_score": record["relevance_score"],
        "rrf_score": 0.0,
        "credibility": 10.0,
        "chunk_digest": record["scoring_provenance"]["chunk_digest"],
    }
    assert len(record["scoring_provenance"]["chunk_digest"]) == 64
    assert record["relevance_score"] > next(
        item["relevance_score"]
        for item in packet["candidate_records"]
        if item["source_result_ref"] == later_retry_identity.ref()
    )

    qualifying_retry_item = next(
        item
        for item in trace["query_plan"]["items"]
        if item.get("item_id")
        == retry_identity.query_plan_item_ref["query_plan_item_id"]
    )
    assert qualifying_retry_item["status"] == "finalized"
    assert retry_identity.query_plan_item_ref["query_plan_item_digest"] == (
        _canonical_digest(
            {
                "query_plan_id": trace["query_plan"]["plan_id"],
                "item": qualifying_retry_item,
            }
        )
    )
    assert retry_identity.query_digest == hashlib.sha256(
        qualifying_retry_item["authorized_query"].encode("utf-8")
    ).hexdigest()
    assert qualifying_retry_item["admission_reason"] == (
        "recorded_from_existing_dispatch_authority"
    )
    assert qualifying_retry_item["metadata"] == {
        "authority_source": "main_retrieval_disambiguation_retry",
        "authority_ref_digest": qualifying_retry_item["metadata"][
            "authority_ref_digest"
        ],
        "query_text_unchanged": True,
    }
    assert len(qualifying_retry_item["metadata"]["authority_ref_digest"]) == 64
    selected_provider_record = next(
        item
        for item in trace["provider_plan"]["records"]
        if item.get("provider_plan_record_ref")
        == dict(retry_identity.provider_plan_record_ref)
    )
    assert selected_provider_record["route_decision_ref"] == dict(
        retry_identity.provider_route_ref
    )

    serialized_packet = json.dumps(packet, sort_keys=True).casefold()
    handoff = trace[ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY]
    assert "searchplanner" not in serialized_packet
    assert "search_planner" not in serialized_packet
    assert "live_search_validation" not in serialized_packet
    assert "source_obligation_ref" not in serialized_packet
    assert all(
        item["not_source_obligation_satisfaction"] is True
        for item in packet["candidate_records"]
    )
    assert packet["answer_contract_ref"]["source"] == "initial_answer_contract"
    assert len(packet["answer_contract_ref"]["contract_digest"]) == 64
    assert handoff["acquisition_need_proposal_created"] is False
    assert handoff["read_work_order_created"] is False
    assert handoff["focused_extract_work_order_created"] is False
    assert handoff["exact_url_cap_charged"] is False
    assert handoff["exact_url_transport_executed"] is False
    assert handoff["urls_fetched"] == trace["urls_fetched"] == 0


def test_pipeline_search_wrapper_rejects_injected_callable_without_lineage_kwargs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def injected_without_lineage_kwargs(
        queries: list[str],
        _intent: str,
        _complexity: str,
        _search_depth: str,
        _results_per_query: int,
        _include_domains: list[str],
        _exclude_domains: list[str],
        _query_embedding: Any,
        _seen_urls: set[str],
        _collected_images: set[str],
        _embed_provider: str,
        _embed_model: str,
        _local_url: str | None,
        _embed_texts: Any,
        _compute_similarities: Any,
        *,
        status_container: Any,
        search_providers: list[str],
        provider_diagnostics: list[dict[str, Any]] | None = None,
        provider_role: str = "main_retrieval",
        iteration: int | None = None,
    ) -> list[dict[str, Any]]:
        del (
            status_container,
            search_providers,
            provider_diagnostics,
            provider_role,
            iteration,
        )
        calls.append(list(queries))
        return []

    with pytest.raises(
        orchestrator.PipelineError,
        match="cannot consume canonical result lineage/store",
    ):
        run_post_retirement_ordinary_pipeline(
            tmp_path,
            monkeypatch,
            mode="Fast",
            query="What is Alpha's current official operating policy?",
            core_topic="Alpha current official operating policy",
            primary_entity="Alpha",
            researcher_queries=["Alpha official current operating policy"],
            deps_overrides={
                "process_search_queries": injected_without_lineage_kwargs,
                "provider_availability": {
                    "tavily": True,
                    "linkup": False,
                    "exa": False,
                    "serper": False,
                },
            },
            environment_overrides={
                "TAVILY_API_KEY": "offline-placeholder"  # pragma: allowlist secret
            },
        )
    assert calls == []


@pytest.mark.parametrize("mode", ["Fast", "Balanced", "Deep"])
def test_unflagged_offline_modes_create_packet_without_transport_and_persist_trace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: str,
) -> None:
    provider_calls: list[dict[str, Any]] = []

    def fake_tavily(
        query: str,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        provider_calls.append({"query": query, **dict(kwargs)})
        return [
            _provider_result(
                "https://alpha.example/report-1",
                title="Alpha official operating report",
                material=("The current official Alpha operating policy remains active under the published rule. ") * 12,
            )
        ], []

    monkeypatch.setattr(pipeline, "search_web_results", fake_tavily)
    monkeypatch.setattr(
        pipeline,
        "search_linkup_results",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Linkup must not run in the offline Tavily proof")
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "search_exa_results",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Exa must not run in the offline Tavily proof")),
    )
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode=mode,
        query="What is Alpha's current official operating policy?",
        core_topic="Alpha current official operating policy",
        primary_entity="Alpha",
        researcher_queries=["Alpha official current operating policy"],
        raw_author_response=(
            "Alpha's current official operating policy remains active. [[1]](https://alpha.example/report-1)"
        ),
        deps_overrides={
            "process_search_queries": pipeline.process_search_queries,
            "provider_availability": {
                "tavily": True,
                "linkup": False,
                "exa": False,
                "serper": False,
            },
        },
        environment_overrides={
            "TAVILY_API_KEY": "offline-placeholder"  # pragma: allowlist secret
        },
    )

    assert provider_calls
    assert not harness.forbidden_live_calls
    trace = outcome.execution_trace
    telemetry = trace["discovery_result_telemetry"]
    packet = validate_ordinary_search_result_candidate_packet(trace["search_result_candidate_packet"])
    handoff = trace[ORDINARY_DISCOVERY_CANDIDATE_HANDOFF_TRACE_KEY]
    assert telemetry["source_result_identities_created"] >= 1
    assert telemetry["candidate_packets_created"] == 1
    assert telemetry["selected_candidates_handed_off"] >= 1
    assert packet["origin_kind"] == (SEARCH_RESULT_CANDIDATE_ORIGIN_ORDINARY_QUERY_PROVIDER)
    assert handoff["acquisition_need_proposal_created"] is False
    assert handoff["read_work_order_created"] is False
    assert handoff["focused_extract_work_order_created"] is False
    assert handoff["exact_url_transport_executed"] is False
    assert handoff["exact_url_cap_charged"] is False
    assert handoff["urls_fetched"] == 0
    assert trace["urls_fetched"] == 0
    assert trace["discover_candidate_urls_admitted"] >= 1
    assert (
        trace.get("ordinary_live_candidate_handoff", {}).get(
            "enabled",
            False,
        )
        is False
    )

    execution_event = execution_event_from_log(tmp_path / "execution.jsonl")
    normalized_trace = json.loads(json.dumps(trace))
    assert execution_event["execution_trace"] == normalized_trace
    sqlite_row = execution_jsonl_to_run_row(execution_event)
    assert sqlite_row is not None
    assert (
        sqlite_row["discover_candidate_urls_admitted"]
        == (execution_event["discover_candidate_urls_admitted"])
        == trace["discover_candidate_urls_admitted"]
    )
    assert sqlite_row["urls_fetched"] == execution_event["urls_fetched"] == 0
