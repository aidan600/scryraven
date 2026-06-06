from __future__ import annotations

import json

import pytest

from core.official_current_source_custody import (
    OfficialCurrentCustodyRecord,
    OfficialCurrentCustodyStatus,
    OfficialCurrentSourceCustodyState,
)
from core.official_source_obligation_bridge import apply_official_source_obligation_bridge


def test_ag89b_custody_status_vocabulary_is_exact() -> None:
    assert {status.value for status in OfficialCurrentCustodyStatus} == {
        "required",
        "search_attempted",
        "candidate_returned",
        "candidate_identity_missing",
        "candidate_aggregate_only",
        "candidate_unreadable",
        "candidate_rejected",
        "candidate_accepted",
        "candidate_partially_accepted",
        "candidate_superseded",
        "candidate_unavailable",
        "requirement_satisfied",
        "requirement_unsatisfied",
        "retry_authorized",
        "stop_insufficient_authorized",
    }


@pytest.mark.parametrize(
    ("status", "kwargs"),
    [
        (OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED, {}),
        (OfficialCurrentCustodyStatus.CANDIDATE_IDENTITY_MISSING, {}),
        (OfficialCurrentCustodyStatus.CANDIDATE_AGGREGATE_ONLY, {}),
    ],
)
def test_ag89b_statuses_enforce_required_identity_fields(
    status: OfficialCurrentCustodyStatus,
    kwargs: dict[str, str],
) -> None:
    with pytest.raises(ValueError):
        OfficialCurrentCustodyRecord(
            requirement_id="official_current_source:official_current_rules",
            status=status,
            **kwargs,
        )


def test_ag89b_custody_serialization_is_json_safe_and_redacted() -> None:
    state = (
        OfficialCurrentSourceCustodyState()
        .require("official_current_rules")
        .record_search_attempted(
            "official_current_source:official_current_rules",
            attempt_id="attempt-1",
            action_id="action-1",
        )
        .record_candidate_aggregate_only(
            "official_current_source:official_current_rules",
            reason="legacy count had no candidate identity",
            metadata={"raw_provider_payload": "secret", "count": 2},
        )
        .record_stop_insufficient_authorized(
            "official_current_source:official_current_rules",
            reason="offline custody test",
        )
    )

    payload = state.to_dict()
    assert json.loads(json.dumps(payload)) == payload
    assert "raw_provider_payload" not in json.dumps(payload)
    assert payload["requirements"] == [
        {
            "requirement_id": "official_current_source:official_current_rules",
            "source_class": "official_current_rules",
            "status": "requirement_unsatisfied",
            "unsatisfied_reason": "no_accepted_or_partially_accepted_candidate_custody",
        }
    ]


def test_ag89b_aggregate_only_observation_does_not_satisfy_requirement() -> None:
    state = (
        OfficialCurrentSourceCustodyState()
        .require("official_current_rules")
        .record_candidate_aggregate_only(
            "official_current_source:official_current_rules",
            reason="source_class_strong_satisfaction_counts_without_candidate_id",
        )
    )

    satisfied, unsatisfied = state.satisfaction_by_source_class()
    assert satisfied == []
    assert unsatisfied == ["official_current_rules"]
    assert state.to_dict()["requirements"][0]["status"] == "requirement_unsatisfied"


def test_ag89b_missing_candidate_identity_does_not_satisfy_requirement() -> None:
    state = (
        OfficialCurrentSourceCustodyState()
        .require("official_current_rules")
        .record_candidate_identity_missing(
            "official_current_source:official_current_rules",
            reason="provider_summary_without_stable_url_or_document_id",
        )
    )

    satisfied, unsatisfied = state.satisfaction_by_source_class()
    assert satisfied == []
    assert unsatisfied == ["official_current_rules"]


def test_ag89b_accepted_candidate_satisfies_requirement() -> None:
    state = (
        OfficialCurrentSourceCustodyState()
        .require("official_current_rules")
        .record_candidate_returned(
            "official_current_source:official_current_rules",
            candidate_id="https://agency.example/rules/2026",
            attempt_id="attempt-1",
        )
        .record_candidate_disposition(
            "official_current_source:official_current_rules",
            status=OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED,
            candidate_id="https://agency.example/rules/2026",
            reason="official_current_candidate_accepted",
        )
    )

    satisfied, unsatisfied = state.satisfaction_by_source_class()
    assert satisfied == ["official_current_rules"]
    assert unsatisfied == []
    assert state.to_dict()["requirements"][0]["status"] == "requirement_satisfied"


def test_ag89b_requirement_unsatisfaction_preserved_without_accepted_candidate() -> None:
    state = (
        OfficialCurrentSourceCustodyState()
        .require("primary_source_documents")
        .record_candidate_disposition(
            "official_current_source:primary_source_documents",
            status=OfficialCurrentCustodyStatus.CANDIDATE_UNREADABLE,
            candidate_id="docs.example/unreadable",
            reason="fetch_unreadable",
        )
        .record_retry_authorized(
            "official_current_source:primary_source_documents",
            reason="retry_remains_permitted_by_existing_budget_owner",
        )
    )

    records = state.to_dict()["records"]
    assert records[-1]["status"] == "requirement_unsatisfied"
    assert "retry_authorized" in {record["status"] for record in records}


def test_ag89b_bridge_consumes_custody_instead_of_aggregate_diagnostics() -> None:
    result = apply_official_source_obligation_bridge(
        runtime_trace={
            "query_preview": "Explain how write-ahead logging works in a database library.",
            "query_type": "technical_reference",
            "source_class_satisfaction_status": {
                "primary_source_documents": "satisfied_strong"
            },
            "source_class_strong_satisfaction_counts": {"primary_source_documents": 4},
        },
        recommendation={"source_class_recovery_recommended": False},
    )
    bridge = result.trace["OfficialSourceObligationBridge"]

    assert bridge["bridge_used"] is True
    assert bridge["bridge_satisfied_source_classes"] == []
    assert result.recommendation["missing_expected_source_classes"] == [
        "primary_source_documents"
    ]
    assert "candidate_aggregate_only" in {
        record["status"]
        for record in bridge["official_current_source_custody"]["records"]
    }


def test_ag89b_bridge_accepts_existing_custody_projection_as_authority() -> None:
    custody = (
        OfficialCurrentSourceCustodyState()
        .require("primary_source_documents")
        .record_candidate_disposition(
            "official_current_source:primary_source_documents",
            status=OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED,
            candidate_id="https://docs.example/wal",
            reason="accepted_official_doc",
        )
        .to_dict()
    )

    result = apply_official_source_obligation_bridge(
        runtime_trace={
            "query_preview": "Explain how write-ahead logging works in a database library.",
            "query_type": "technical_reference",
            "official_current_source_custody": custody,
            "source_class_satisfaction_status": {
                "primary_source_documents": "expected_but_only_secondary"
            },
        },
        recommendation={"source_class_recovery_recommended": False},
    )
    bridge = result.trace["OfficialSourceObligationBridge"]

    assert bridge["bridge_used"] is False
    assert bridge["bridge_skip_reason"] == "existing_source_class_satisfied"
    assert bridge["bridge_satisfied_source_classes"] == ["primary_source_documents"]
    assert "missing_expected_source_classes" not in result.recommendation
