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
