from __future__ import annotations

import json

from core.official_current_source_custody import OfficialCurrentSourceCustodyState
from core.query_plan import (
    QUERY_PLAN_TRACE_KEY,
    QueryPlan,
    QueryPlanRole,
    QueryPlanStatus,
    authorize_recency_merge,
    authorize_retrieval_queries,
)
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.retrieval_quality import finalize_retrieval_queries


def _clean(value: str) -> str:
    return " ".join((value or "").strip().split())


def test_ag89c_query_plan_status_and_role_vocabulary() -> None:
    assert QueryPlanStatus.OBSERVED_MODEL_QUERY.value == "observed_model_query"
    assert QueryPlanStatus.FINALIZED.value == "finalized"
    assert QueryPlanStatus.OFFICIAL_BIAS_APPLIED.value == "official_bias_applied"
    assert QueryPlanStatus.RECOVERY_ADMITTED.value == "recovery_admitted"
    assert QueryPlanStatus.REJECTED_EMPTY.value == "rejected_empty"
    assert QueryPlanStatus.PROVIDER_POLICY_UNCHANGED.value == "provider_policy_unchanged"
    assert QueryPlanStatus.DEPTH_POLICY_UNCHANGED.value == "depth_policy_unchanged"
    assert QueryPlanRole.RECON_REWRITE.value == "recon_rewrite"
    assert QueryPlanRole.DISAMBIGUATION.value == "disambiguation"
    assert QueryPlanRole.REMEDIATION.value == "remediation"


def test_ag89c_query_plan_serialization_is_json_safe_and_redacted() -> None:
    plan = QueryPlan(plan_id="qp-test").append(
        origin="researcher",
        role=QueryPlanRole.INITIAL,
        status=QueryPlanStatus.FINALIZED,
        original_query="openai pricing",
        authorized_query="OpenAI pricing",
        metadata={
            "raw_prompt": "do not expose",
            "nested": {"provider_payload": {"secret": "x"}},
            "tuple_value": ("ok",),
        },
    )

    payload = plan.to_dict()
    json.dumps(payload)
    metadata = payload["items"][0]["metadata"]
    assert metadata["raw_prompt"] == "[redacted]"
    assert metadata["nested"]["provider_payload"] == "[redacted]"
    assert metadata["tuple_value"] == ["ok"]


def test_ag89c_deterministic_finalization_parity_with_legacy_facade() -> None:
    inputs = ["Druid upcoming patch", "Shaman balance changes", "Druid upcoming patch", ""]
    plan, authorized = authorize_retrieval_queries(
        inputs,
        primary_entity="Path of Exile 2",
        entities_list=["Path of Exile 2", "POE 2"],
        core_topic="Path of Exile 2",
        user_query="poe 2 upcoming patch notes",
        intent="general",
        clean=_clean,
        include_official_bias=True,
    )
    legacy = finalize_retrieval_queries(
        inputs,
        primary_entity="Path of Exile 2",
        entities_list=["Path of Exile 2", "POE 2"],
        core_topic="Path of Exile 2",
        user_query="poe 2 upcoming patch notes",
        intent="general",
        clean=_clean,
        include_official_bias=True,
    )

    assert authorized == legacy
    statuses = [item["status"] for item in plan.to_dict()["items"]]
    assert "rejected_empty" in statuses
    assert "rejected_duplicate" in statuses
    assert "official_bias_applied" in statuses


def test_ag89c_max_len_cap_is_owned_by_query_plan() -> None:
    plan, authorized = authorize_retrieval_queries(
        ["launch details", "pricing update", "support policy"],
        primary_entity="Acme Widget",
        entities_list=["Acme Widget"],
        core_topic="Acme Widget",
        user_query="Acme Widget overview",
        intent="general",
        clean=_clean,
        include_official_bias=False,
        max_len=2,
    )

    assert authorized == ['"Acme Widget" launch details', '"Acme Widget" pricing update']
    trace = plan.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    items = trace["items"]
    finalized = [item for item in items if item["status"] == "finalized"]
    over_budget = [item for item in items if item["status"] == "rejected_over_budget"]
    assert [item["authorized_query"] for item in finalized] == authorized
    assert '"Acme Widget" support policy' not in [
        item["authorized_query"] for item in finalized
    ]
    assert len(over_budget) == 1
    assert over_budget[0]["authorized_query"] == '"Acme Widget" support policy'
    assert over_budget[0]["admission_reason"] == "rejected_over_budget"
    assert over_budget[0]["metadata"]["would_have_status"] == "finalized"

def test_ag89c_recency_merge_preserves_existing_order() -> None:
    plan = QueryPlan(plan_id="qp-recency")
    current = ["Acme Widget pricing", "Acme Widget deployment"]
    plan, merged = authorize_recency_merge(
        plan,
        current,
        recency_query="Acme Widget 2026 news",
        max_queries=3,
    )

    assert merged == ["Acme Widget 2026 news", "Acme Widget pricing", "Acme Widget deployment"]
    record = plan.to_dict()["items"][0]
    assert record["status"] == "recency_merged"
    assert record["metadata"]["output_order"] == merged


def test_ag89c_official_bias_records_mutation_without_custody_satisfaction() -> None:
    plan, authorized = authorize_retrieval_queries(
        ["pricing update"],
        primary_entity="Acme Widget",
        entities_list=["Acme Widget"],
        core_topic="Acme Widget pricing",
        user_query="Acme Widget pricing",
        intent="general",
        clean=_clean,
        include_official_bias=True,
    )
    assert authorized[0] == '"Acme Widget" official pricing'
    official_records = [
        item for item in plan.to_dict()["items"]
        if item.get("role") == "official_bias"
    ]
    assert official_records
    assert official_records[-1]["metadata"]["custody_satisfied"] is False

    custody = OfficialCurrentSourceCustodyState.for_required_source_classes(
        ["official_current_rules"]
    )
    satisfied, unsatisfied = custody.satisfaction_by_source_class()
    assert satisfied == []
    assert unsatisfied == ["official_current_rules"]


def test_ag89c_duplicate_and_empty_handling_are_represented() -> None:
    plan, authorized = authorize_retrieval_queries(
        ["", "Acme Widget", "Acme Widget"],
        primary_entity="Acme Widget",
        entities_list=["Acme Widget"],
        core_topic="Acme Widget",
        user_query="Acme Widget overview",
        intent="general",
        clean=_clean,
        include_official_bias=False,
    )

    assert authorized == ["Acme Widget"]
    statuses = [item["status"] for item in plan.to_dict()["items"]]
    assert "rejected_empty" in statuses
    assert "rejected_duplicate" in statuses


def test_ag89c_trace_projection_is_derived_from_query_plan_state() -> None:
    plan = QueryPlan(plan_id="qp-trace").admit_execution_queries(
        ["q1", "q2"],
        phase="retrieval_execution",
        iteration=1,
        role=QueryPlanRole.FINALIZED,
        origin="retrieval_loop",
    )
    trace = plan.to_trace_fragment()

    assert set(trace) == {QUERY_PLAN_TRACE_KEY}
    assert trace[QUERY_PLAN_TRACE_KEY]["authorized_queries_by_iteration"] == {"1": ["q1", "q2"]}
    assert trace[QUERY_PLAN_TRACE_KEY]["items"][0]["status"] == "ordered"


def _adapter() -> object:
    return build_query_plan_runtime_adapter(
        run_id="ag91b",
        primary_entity="Acme Widget",
        entities_list=["Acme Widget", "AW"],
        core_topic="Acme Widget deployment",
        user_query="Acme Widget deployment official current status",
        intent="general",
        clean=_clean,
    )


def _recency_adapter(
    *,
    primary_entity: str = "Acme Widget",
    core_topic: str = "Acme Widget deployment",
    user_query: str = "latest Acme Widget news",
    intent: str = "news",
) -> object:
    return build_query_plan_runtime_adapter(
        run_id="ag91e-recency",
        primary_entity=primary_entity,
        entities_list=[primary_entity] if primary_entity else [],
        core_topic=core_topic,
        user_query=user_query,
        intent=intent,
        clean=_clean,
    )


def test_ag91b_initial_researcher_queries_finalize_to_legacy_consumed_list() -> None:
    inputs = ["deployment status", "support policy", "deployment status", ""]
    adapter = _adapter()

    consumed = adapter.finalize(
        inputs,
        origin="researcher",
        role=QueryPlanRole.INITIAL,
        phase="initial_researcher_queries",
    )
    legacy = finalize_retrieval_queries(
        inputs,
        primary_entity="Acme Widget",
        entities_list=["Acme Widget", "AW"],
        core_topic="Acme Widget deployment",
        user_query="Acme Widget deployment official current status",
        intent="general",
        clean=_clean,
        include_official_bias=True,
    )

    assert consumed == legacy
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    assert [
        item["authorized_query"]
        for item in trace["items"]
        if item["status"] in {"finalized", "official_bias_applied"}
    ] == consumed


def test_ag91b_recon_seeded_queries_finalize_to_legacy_consumed_list() -> None:
    inputs = ["Acme Widget release notes", "AW deployment timeline"]
    adapter = _adapter()

    consumed = adapter.finalize(
        inputs,
        origin="recon_rewriter",
        role=QueryPlanRole.RECON_REWRITE,
        phase="recon_seeded_queries",
    )
    legacy = finalize_retrieval_queries(
        inputs,
        primary_entity="Acme Widget",
        entities_list=["Acme Widget", "AW"],
        core_topic="Acme Widget deployment",
        user_query="Acme Widget deployment official current status",
        intent="general",
        clean=_clean,
        include_official_bias=True,
    )

    assert consumed == legacy
    assert [item["origin"] for item in adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]["items"][:2]] == [
        "recon_rewriter",
        "recon_rewriter",
    ]


def test_ag91b_recency_merge_then_admission_preserves_consumed_order() -> None:
    adapter = _adapter()
    finalized = adapter.finalize(
        ["deployment status", "support policy"],
        include_official_bias=False,
    )

    merged = adapter.merge_recency(
        finalized,
        recency_query="Acme Widget 2026 news",
        max_queries=3,
    )
    consumed = adapter.finalize(merged, max_len=3, include_official_bias=False)
    admitted = adapter.admit_execution_queries(
        consumed,
        iteration=1,
        recovery_active=False,
    )

    assert merged == [
        "Acme Widget 2026 news",
        '"Acme Widget" deployment status',
        '"Acme Widget" support policy',
    ]
    assert consumed == merged
    assert admitted == consumed
    assert adapter.queries_by_iteration()[1] == consumed


def test_ag91e_adapter_owns_recency_gate_year_anchor_and_metadata() -> None:
    adapter = _recency_adapter()
    finalized = adapter.finalize(
        ["deployment status", "support policy"],
        include_official_bias=False,
    )

    projection = adapter.apply_initial_recency_merge(
        finalized,
        query_type="product",
        current_date="June 8, 2026",
        max_queries=3,
    )

    assert projection.recency_merge_used is True
    assert projection.recency_merge_query == "Acme Widget 2026 news"
    assert projection.current_queries == [
        "Acme Widget 2026 news",
        '"Acme Widget" deployment status',
        '"Acme Widget" support policy',
    ]
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    recency_records = [
        item for item in trace["items"]
        if item["status"] == "recency_merged"
    ]
    assert recency_records[-1]["authorized_query"] == projection.recency_merge_query
    assert recency_records[-1]["metadata"]["output_order"] == projection.current_queries
    assert recency_records[-1]["metadata"]["max_queries"] == 3


def test_ag91e_adapter_skips_recency_merge_when_gate_not_admitted() -> None:
    adapter = _recency_adapter(
        user_query="Acme Widget deployment status",
        intent="general",
    )

    projection = adapter.apply_initial_recency_merge(
        ["q1", "q2"],
        query_type="product",
        current_date="June 8, 2026",
        max_queries=2,
    )

    assert projection.current_queries == ["q1", "q2"]
    assert projection.recency_merge_used is False
    assert projection.recency_merge_query is None
    assert "recency_merged" not in [
        item["status"] for item in adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]["items"]
    ]


def test_ag91e_adapter_skips_recency_merge_with_missing_anchor() -> None:
    adapter = _recency_adapter(primary_entity="", core_topic="")

    projection = adapter.apply_initial_recency_merge(
        ["q1"],
        query_type="news",
        current_date="June 8, 2026",
        max_queries=2,
    )

    assert projection.current_queries == ["q1"]
    assert projection.recency_merge_used is False
    assert projection.recency_merge_query is None


def test_ag91e_adapter_preserves_recency_max_query_cap_and_year_fallback() -> None:
    adapter = _recency_adapter()

    projection = adapter.apply_initial_recency_merge(
        ["q1", "q2", "q3"],
        query_type="news",
        current_date="next Tuesday",
        max_queries=2,
    )

    assert projection.recency_merge_query == "Acme Widget 2026 news"
    assert projection.current_queries == ["Acme Widget 2026 news", "q1"]


def test_ag91b_official_current_canonical_bias_insertion_remains_queryplan_separated() -> None:
    adapter = build_query_plan_runtime_adapter(
        run_id="ag91b-official",
        primary_entity="Acme Widget",
        entities_list=["Acme Widget", "AW"],
        core_topic="Acme Widget pricing",
        user_query="Acme Widget pricing",
        intent="general",
        clean=_clean,
    )

    consumed = adapter.finalize(["pricing"], include_official_bias=True)
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    official_records = [item for item in trace["items"] if item.get("role") == "official_bias"]

    assert consumed == ['"Acme Widget" official pricing', '"Acme Widget" pricing']
    assert official_records[-1]["authorized_query"] == consumed[0]
    assert official_records[-1]["metadata"]["custody_satisfied"] is False
    assert trace["custody_satisfaction_owner"] == "official_current_source_custody"


def test_ag91b_max_query_cap_preserves_consumed_list_and_rejected_records() -> None:
    adapter = _adapter()

    consumed = adapter.finalize(
        ["deployment", "pricing", "support"],
        max_len=2,
        include_official_bias=False,
    )
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    over_budget = [item for item in trace["items"] if item["status"] == "rejected_over_budget"]

    assert consumed == ['"Acme Widget" deployment', '"Acme Widget" pricing']
    assert [item["authorized_query"] for item in over_budget] == ['"Acme Widget" support']
    assert over_budget[0]["metadata"]["max_len"] == 2


def test_ag91b_retrieval_loop_consumes_queries_recorded_by_queryplan() -> None:
    adapter = _adapter()
    current_queries = adapter.finalize(
        ["deployment", "pricing"],
        include_official_bias=False,
    )

    current_queries = adapter.admit_execution_queries(
        current_queries,
        iteration=1,
        recovery_active=False,
    )

    assert current_queries == adapter.authorized_queries_for_iteration(1)
    assert current_queries == adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY][
        "authorized_queries_by_iteration"
    ]["1"]


def test_ag91b_queries_by_iteration_is_queryplan_projection_not_local_reconstruction() -> None:
    adapter = _adapter()
    local_mirror = {1: ["stale local mirror"]}
    current_queries = adapter.finalize(["deployment"], include_official_bias=False)
    adapter.admit_execution_queries(current_queries, iteration=1, recovery_active=False)

    assert adapter.queries_by_iteration() != local_mirror
    assert adapter.queries_by_iteration() == {1: ['"Acme Widget" deployment']}


def test_ag91b_static_guard_queryplan_boundary_avoids_closed_surfaces() -> None:
    from pathlib import Path

    queryplan_sources = "\n".join(
        Path(path).read_text()
        for path in ("core/query_plan.py", "core/query_plan_runtime_adapter.py")
    )
    closed_tokens = [
        "ask_model(",
        "brave_reconnaissance(",
        "embed_texts(",
        "select_providers(",
        "choose_retrieval_search_depth(",
        "choose_supplemental_search_depth(",
        "DEFAULT_SYSTEM",
        "final_evidence",
        "format_citation",
    ]

    assert all(token not in queryplan_sources for token in closed_tokens)
    orchestrator_source = Path("core/pipeline_orchestrator.py").read_text()
    query_runtime_source = Path("core/query_production_runtime.py").read_text()
    assert "def _finalize_retrieval_queries" not in orchestrator_source
    assert "current_queries = query_authority.admit_execution_queries" in orchestrator_source
    assert "execute_query_plan_admission_action(" in orchestrator_source
    assert "run_kernel.authorize_query_plan_admission(" in orchestrator_source
    assert "recency_projection = query_authority.apply_initial_recency_merge" in query_runtime_source
    assert "should_merge_recency_queries(" not in orchestrator_source
    assert '_clean_query(f"{_anchor} {y} news")' not in orchestrator_source


def test_ag91d_recon_admission_method_preserves_candidate_order_and_origin() -> None:
    adapter = _adapter()
    candidates = ["Acme Widget release notes", "AW deployment timeline"]

    consumed = adapter.admit_recon_candidates(candidates)
    legacy = finalize_retrieval_queries(
        candidates,
        primary_entity="Acme Widget",
        entities_list=["Acme Widget", "AW"],
        core_topic="Acme Widget deployment",
        user_query="Acme Widget deployment official current status",
        intent="general",
        clean=_clean,
        include_official_bias=True,
    )

    assert consumed == legacy
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    assert {item["origin"] for item in trace["items"][: len(candidates)]} == {"recon_rewriter"}
    assert {item["phase"] for item in trace["items"][: len(candidates)]} == {"recon_seeded_queries"}


def test_ag91d_researcher_admission_method_preserves_candidate_order_and_origin() -> None:
    adapter = _adapter()
    candidates = ["deployment status", "support policy", "deployment status", ""]

    consumed = adapter.admit_researcher_candidates(candidates)
    legacy = finalize_retrieval_queries(
        candidates,
        primary_entity="Acme Widget",
        entities_list=["Acme Widget", "AW"],
        core_topic="Acme Widget deployment",
        user_query="Acme Widget deployment official current status",
        intent="general",
        clean=_clean,
        include_official_bias=True,
    )

    assert consumed == legacy
    trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    assert trace["items"][0]["origin"] == "researcher"
    assert trace["items"][0]["phase"] == "initial_researcher_queries"


def test_ag91i_pipeline_demotes_pre_retrieval_candidates_before_consumption() -> None:
    from pathlib import Path

    source = Path("core/pipeline_orchestrator.py").read_text()
    query_runtime_source = Path("core/query_production_runtime.py").read_text()
    assert "run_kernel.authorize_query_production(" in source
    assert "execute_query_production_action(" in source
    assert "run_kernel.reduce(query_production_result.observation)" in source
    assert "query_plan_admission_inputs_from_query_production_projection(" in source
    assert "candidate_queries=query_plan_inputs.candidate_queries" in source
    assert "execute_query_plan_admission_action(" in source
    assert "queries = query_authority.admit_recon_candidates(candidate_queries)" in query_runtime_source
    assert 'candidate_source in {"researcher", "fallback"}' in query_runtime_source
    assert "queries = query_authority.finalize(queries, include_official_bias=True)" not in source
    assert "pre_retrieval_query_candidates" not in source
    assert "query_admission_candidates" not in source
