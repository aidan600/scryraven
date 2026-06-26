from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from core.mode_policy import (
    initial_subject_budget_policy_for,
    mode_policy_for,
    normalize_mode,
)
from core.validation_observability import (
    build_subject_budget_summary,
    build_validation_observability,
)
from core.validation_profiles import AG_LIVE_MULTI_COMPONENT, get_validation_profile
from scripts import ag_live_bound_01_support as support


def _trace(
    component_ids: list[str],
    *,
    mapped_ids: list[str] | None = None,
    evidenced_ids: list[str] | None = None,
) -> dict[str, object]:
    trace: dict[str, object] = {
        "query_plan_work_shadow_projection": {
            "trace_key": "query_plan_work_shadow_projection",
            "components": [
                {
                    "component_id": component_id,
                    "source_obligation_count": 1,
                    "provider_job_count": 1,
                }
                for component_id in component_ids
            ],
            "work_counts": {"component_count": len(component_ids)},
            "stop_and_follow_up_posture": {
                "follow_up_permission": "conditional",
            },
        },
    }
    if mapped_ids is not None:
        trace["query_plan"] = {
            "search_work_consumption": {
                "search_work_consumed_by_query_plan": True,
                "query_metadata": {
                    f"existing-query-{index}": {
                        "search_work_component_id": component_id,
                    }
                    for index, component_id in enumerate(mapped_ids, start=1)
                },
            },
        }
    if evidenced_ids is not None:
        trace["final_answer_packet"] = {
            "semantic_packet_evidence_bindings": [
                {
                    "component_id": component_id,
                    "packet_evidence_id": f"packet-evidence-{index}",
                    "source_id": f"source-{index}",
                }
                for index, component_id in enumerate(evidenced_ids, start=1)
            ],
        }
    return trace


def _summary(
    component_ids: list[str],
    *,
    mapped_ids: list[str] | None = None,
    evidenced_ids: list[str] | None = None,
) -> dict[str, object]:
    return build_subject_budget_summary(
        validation_profile=get_validation_profile(AG_LIVE_MULTI_COMPONENT),
        trace=_trace(
            component_ids,
            mapped_ids=mapped_ids,
            evidenced_ids=evidenced_ids,
        ),
    )


def _subject_ids(items: object) -> list[str]:
    assert isinstance(items, list)
    return [str(item["subject_id"]) for item in items]


def test_over_cap_subjects_are_detected_selected_and_omitted() -> None:
    subjects = ["PostgreSQL", "MySQL", "Redis", "MongoDB", "Nginx", "Apache"]

    summary = _summary(subjects, mapped_ids=subjects, evidenced_ids=subjects[:5])

    assert summary["subject_budget_enabled"] is True
    assert summary["max_initial_selected_subjects"] == 5
    assert summary["detected_subject_count"] >= 6
    assert summary["selected_subject_count"] == 5
    assert summary["selected_subject_count"] <= 5
    assert summary["omitted_subject_count"] >= 1
    assert summary["subject_cap_exceeded"] is True
    assert _subject_ids(summary["selected_subjects"]) == subjects[:5]
    assert _subject_ids(summary["omitted_subjects"]) == ["Apache"]


def test_under_cap_four_subjects_selects_all_without_omission() -> None:
    subjects = ["PostgreSQL", "MySQL", "Redis", "MongoDB"]

    summary = _summary(subjects, mapped_ids=subjects, evidenced_ids=subjects)

    assert summary["detected_subject_count"] == 4
    assert summary["selected_subject_count"] == 4
    assert summary["omitted_subject_count"] == 0
    assert summary["subject_cap_exceeded"] is False
    assert _subject_ids(summary["selected_subjects"]) == subjects
    assert summary["omitted_subjects"] == []


def test_subject_budget_does_not_pad_to_five() -> None:
    subjects = ["PostgreSQL", "MySQL", "Redis"]

    summary = _summary(subjects, mapped_ids=subjects, evidenced_ids=subjects)

    assert summary["detected_subject_count"] == 3
    assert summary["selected_subject_count"] == 3
    assert _subject_ids(summary["selected_subjects"]) == subjects
    assert summary["omitted_subject_count"] == 0


def test_query_plan_consumption_component_ids_fallback_detects_subjects_without_raw_queries() -> None:
    trace = {
        "query_plan": {
            "search_work_consumption": {
                "search_work_consumed_by_query_plan": True,
                "component_ids_considered": [
                    "PostgreSQL",
                    "MySQL",
                    "Redis",
                    "MongoDB",
                    "Nginx",
                    "Apache",
                ],
                "unfilled_component_ids": ["Apache"],
                "query_metadata": {
                    "RAW QUERY STRING PostgreSQL official docs": {
                        "search_work_component_id": "PostgreSQL",
                    },
                    "RAW QUERY STRING MySQL official docs": {
                        "search_work_component_id": "MySQL",
                    },
                    "RAW QUERY STRING Redis official docs": {
                        "search_work_component_id": "Redis",
                    },
                    "RAW QUERY STRING MongoDB official docs": {
                        "search_work_component_id": "MongoDB",
                    },
                },
            }
        }
    }

    summary = build_subject_budget_summary(
        validation_profile=get_validation_profile(AG_LIVE_MULTI_COMPONENT),
        trace=trace,
    )

    assert summary["detected_subject_count"] >= 6
    assert summary["selected_subject_count"] == 5
    assert summary["selected_subject_count"] <= 5
    assert summary["omitted_subject_count"] >= 1
    assert _subject_ids(summary["omitted_subjects"]) == ["Apache"]
    assert summary["subject_selection_source"] == (
        "query_plan_search_work_consumption_component_ids_considered"
    )
    assert summary["query_mapped_subject_count"] == 4
    assert [
        item.get("query_mapped")
        for item in summary["selected_subjects"]
        if isinstance(item, dict)
    ] == [True, True, True, True, False]
    assert summary["independently_evidenced_subject_count"] is None
    assert "component_scoped_evidence_binding_not_available" in str(
        summary["diagnosis"]
    )

    rendered = json.dumps(summary, sort_keys=True)
    assert "RAW QUERY STRING" not in rendered
    support.reject_forbidden_packet({"subject_budget_summary": summary})


def test_internal_followups_are_exempt_from_initial_subject_cap() -> None:
    summary = _summary(
        ["PostgreSQL", "MySQL", "Redis", "MongoDB"],
        mapped_ids=["PostgreSQL"],
    )

    assert summary["subject_budget_scope"] == "initial_independent_subjects_only"
    assert summary["applies_to_internal_followups"] is False
    followups = summary["followup_budget_policy"]
    assert isinstance(followups, dict)
    assert followups["initial_subject_cap_applies_to_internal_followups"] is False
    assert followups["internal_followups_governed_by"] == "existing_mode_resource_caps"
    assert followups["observation_status"] == (
        "internal_followups_exempt_but_not_independently_observed"
    )
    assert followups["observed_follow_up_permission"] == "conditional"


def test_query_mapping_counts_present_mapping_and_reports_unknown_when_absent() -> None:
    subjects = ["PostgreSQL", "MySQL", "Redis", "MongoDB"]

    mapped = _summary(subjects, mapped_ids=subjects[:3])
    assert mapped["query_mapped_subject_count"] == 3
    assert [
        item.get("query_mapped")
        for item in mapped["selected_subjects"]
        if isinstance(item, dict)
    ] == [True, True, True, False]

    unknown = _summary(subjects)
    assert unknown["query_mapped_subject_count"] is None
    assert "query_component_mapping_not_available" in str(unknown["diagnosis"])


def test_evidence_is_not_faked_when_component_binding_is_absent() -> None:
    subjects = ["PostgreSQL", "MySQL", "Redis", "MongoDB"]

    unknown = _summary(subjects, mapped_ids=subjects)

    assert unknown["independently_evidenced_subject_count"] is None
    assert unknown["subjects_without_evidence"] == []
    assert "component_scoped_evidence_binding_not_available" in str(
        unknown["diagnosis"]
    )

    partial = _summary(subjects, mapped_ids=subjects, evidenced_ids=subjects[:2])
    assert partial["independently_evidenced_subject_count"] == 2
    assert _subject_ids(partial["subjects_without_evidence"]) == ["Redis", "MongoDB"]
    assert [
        item.get("independently_evidenced")
        for item in partial["selected_subjects"]
        if isinstance(item, dict)
    ] == [True, True, False, False]


def test_subject_budget_summary_is_sanitized_in_observability_packet() -> None:
    subjects = ["PostgreSQL", "MySQL", "Redis", "MongoDB", "Nginx", "Apache"]
    trace = _trace(subjects, mapped_ids=subjects[:5], evidenced_ids=subjects[:4])
    trace["raw_prompt"] = "RAW_PROMPT_SENTINEL"
    trace["provider_payload"] = {"raw_response": "RAW_RESPONSE_SENTINEL"}
    outcome = SimpleNamespace(
        report="No final answer from offline fake trace.",
        top_passages=[],
        seen_urls=[],
        execution_trace=trace,
    )

    observability = build_validation_observability(
        validation_profile=get_validation_profile(AG_LIVE_MULTI_COMPONENT),
        outcome=outcome,
    )

    summary = observability["subject_budget_summary"]
    assert summary["selected_subject_count"] == 5
    assert summary["omitted_subject_count"] == 1
    rendered = json.dumps(observability, sort_keys=True)
    assert "RAW_PROMPT_SENTINEL" not in rendered
    assert "RAW_RESPONSE_SENTINEL" not in rendered
    assert "existing-query-1" not in rendered
    support.reject_forbidden_packet({"validation_observability": observability})


def test_mode_subject_budget_scaffold_does_not_change_existing_mode_caps() -> None:
    assert mode_policy_for("Fast").to_dict()["max_queries"] == 2
    assert mode_policy_for("Balanced").to_dict()["results_per_query"] == 6
    assert mode_policy_for("Deep").to_dict()["max_iterations"] == 3

    fast = initial_subject_budget_policy_for("Fast").to_dict()
    balanced = initial_subject_budget_policy_for("Balanced").to_dict()
    deep = initial_subject_budget_policy_for("Deep").to_dict()
    instant = initial_subject_budget_policy_for("Instant").to_dict()
    pro = initial_subject_budget_policy_for("Pro").to_dict()

    assert fast["max_initial_selected_subjects"] == 5
    assert fast["policy_status"] == "planned"
    assert balanced["max_initial_selected_subjects"] == 5
    assert balanced["internal_followups_exempt"] is True
    assert deep["max_initial_selected_subjects"] is None
    assert deep["policy_status"] == "undecided"
    assert instant["mode_exists"] is False
    assert instant["max_initial_selected_subjects"] is None
    assert pro["mode_exists"] is False
    assert pro["policy_status"] == "not_existing_mode_future_note"

    with pytest.raises(ValueError):
        normalize_mode("Instant")
