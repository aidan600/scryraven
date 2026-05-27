from __future__ import annotations

import json

from core.controller_action_envelope import RECOVER_MISSING_SOURCE_CLASS
from core.source_class_recovery_diagnostics import (
    SOURCE_CLASS_RECOVERY_VALIDATION_SCHEMA_VERSION,
    build_source_class_recovery_validation_packet,
)


def _base_trace() -> dict[str, object]:
    return {
        "source_class_recovery_recommended": True,
        "source_class_recovery_official_domains": [
            "https://www.ecfr.gov/current/title-29",
            "federalregister.gov",
        ],
        "source_class_recovery_domain_constraint_source": (
            "official_source_recovery_lane"
        ),
        "active_source_class_recovery_considered": True,
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_reason": "answer_contract_legal_text_gap:legal_or_regulatory_text",
        "active_source_class_recovery_skip_reason": None,
        "active_source_class_recovery_blockers": [],
        "active_source_class_recovery_missing_classes": [
            "legal_or_regulatory_text"
        ],
        "active_source_class_recovery_queries": [
            "Care Program official legal requirements current text site:ecfr.gov"
        ],
        "active_source_class_recovery_result_count": 2,
        "active_source_class_recovery_new_url_count": 2,
        "recovered_accepted_url_count": 2,
        "recovered_source_tier_counts": {"official": 1, "secondary": 1},
        "recovered_source_class_counts": {"legal_or_regulatory_text": 1},
        "recovered_official_or_primary_count": 1,
        "recovered_promoted_source_count": 0,
        "recovery_source_quality_status": "official_or_primary_found",
        "recovered_visibility_considered": True,
        "recovered_visibility_eligible": True,
        "recovered_visibility_used": False,
        "recovered_visibility_reason": "max_final_evidence_reached",
        "recovered_visibility_reserved_count": 0,
        "final_answer_source_ids_used": ["1"],
        "final_official_source_count": 0,
        "final_legal_or_regulatory_source_count": 0,
        "final_primary_source_count": 0,
        "provider_diagnostics": [
            {
                "provider": "tavily",
                "provider_role": "source_class_recovery",
                "depth": "basic",
                "max_results": 6,
                "query_count": 1,
                "success": True,
                "result_count": 2,
                "new_url_count": 2,
                "accepted_url_count": 2,
            },
            {
                "provider": "tavily",
                "provider_role": "main_retrieval",
                "depth": "basic",
                "max_results": 6,
            },
        ],
    }


def test_l1_packet_builds_sanitized_official_legal_recovery_fields() -> None:
    packet = build_source_class_recovery_validation_packet(
        _base_trace(),
        evidence_bundle_source_class_counts={"legal_or_regulatory_text": 1},
    )

    assert packet["schema_version"] == SOURCE_CLASS_RECOVERY_VALIDATION_SCHEMA_VERSION
    assert packet["diagnostic_only"] is True
    assert packet["sanitized"] is True
    assert packet["ag25_action"]["name"] == RECOVER_MISSING_SOURCE_CLASS
    assert packet["ag25_action"]["status"] == "approved"
    assert packet["ag25_action"]["authority"] == "active"
    assert packet["ag25_action"]["side_effect_class"] == "retrieval"
    assert packet["recovery_considered"] is True
    assert packet["recovery_eligible"] is True
    assert packet["recovery_used"] is True
    assert packet["missing_source_classes"] == ["legal_or_regulatory_text"]
    assert packet["official_domain_constraints"] == [
        "ecfr.gov",
        "federalregister.gov",
    ]
    assert packet["jurisdiction_constraints"] == ["us"]
    assert packet["provider_attempts"] == [
        {
            "provider": "tavily",
            "provider_role": "source_class_recovery",
            "depth": "basic",
            "max_results": 6,
            "query_count": 1,
            "success": True,
            "failure_type": None,
            "result_count": 2,
            "new_url_count": 2,
            "accepted_url_count": 2,
            "logical_attempt_count": 1,
        }
    ]
    assert packet["accepted_url_count"] == 2
    assert packet["recovered_source_class_counts"] == {
        "legal_or_regulatory_text": 1
    }
    assert packet["recovered_visibility_decision"]["used"] is False
    assert packet["recovery_bottleneck_status"] == "accepted_not_visible"


def test_l1_packet_classifies_visible_not_final_cited() -> None:
    trace = _base_trace()
    trace.update(
        {
            "recovered_visibility_used": True,
            "recovered_visibility_reason": "reserved_replace",
            "recovered_visibility_reserved_count": 1,
            "recovered_promoted_source_count": 1,
        }
    )

    packet = build_source_class_recovery_validation_packet(
        trace,
        evidence_bundle_source_class_counts={"legal_or_regulatory_text": 1},
    )

    assert packet["final_cited_counts_available"] is True
    assert packet["final_cited_official_legal_current_primary_counts"][
        "legal_or_regulatory_text"
    ] == 0
    assert packet["evidence_bundle_official_legal_current_primary_counts"][
        "legal_or_regulatory_text"
    ] == 1
    assert packet["recovery_bottleneck_status"] == "visible_not_final_cited"


def test_l1_packet_treats_empty_final_citation_ids_as_available_zero_counts() -> None:
    trace = _base_trace()
    trace.update(
        {
            "final_answer_source_ids_used": [],
            "recovered_visibility_used": True,
            "recovered_visibility_reason": "reserved_replace",
            "recovered_visibility_reserved_count": 1,
            "recovered_promoted_source_count": 1,
        }
    )

    packet = build_source_class_recovery_validation_packet(
        trace,
        evidence_bundle_source_class_counts={"legal_or_regulatory_text": 1},
    )

    assert packet["final_cited_counts_available"] is True
    assert packet["final_cited_official_legal_current_primary_counts"] == {
        "official_current_rules": 0,
        "legal_or_regulatory_text": 0,
        "primary_source_documents": 0,
        "archival_primary_text": 0,
        "current_primary_or_official_proxy": 0,
    }
    assert packet["recovery_bottleneck_status"] == "visible_not_final_cited"


def test_l1_packet_absent_final_citation_ids_does_not_satisfy_from_bundle() -> None:
    trace = _base_trace()
    trace.pop("final_answer_source_ids_used", None)
    trace.update(
        {
            "recovered_visibility_used": True,
            "recovered_visibility_reason": "reserved_replace",
            "recovered_visibility_reserved_count": 1,
            "recovered_promoted_source_count": 1,
        }
    )

    packet = build_source_class_recovery_validation_packet(
        trace,
        evidence_bundle_source_class_counts={"legal_or_regulatory_text": 1},
    )

    assert packet["final_cited_counts_available"] is False
    assert packet["final_cited_official_legal_current_primary_counts"] == {
        "official_current_rules": None,
        "legal_or_regulatory_text": None,
        "primary_source_documents": None,
        "archival_primary_text": None,
        "current_primary_or_official_proxy": None,
    }
    assert packet["evidence_bundle_official_legal_current_primary_counts"][
        "legal_or_regulatory_text"
    ] == 1
    assert packet["recovery_bottleneck_status"] == "unknown"


def test_l1_packet_handles_absent_historical_fields() -> None:
    packet = build_source_class_recovery_validation_packet({})

    assert packet["ag25_action"]["status"] == "skipped"
    assert packet["recovery_considered"] is False
    assert packet["recovery_recommended"] is False
    assert packet["provider_attempts"] == []
    assert packet["recovery_query_previews"] == []
    assert packet["recovery_bottleneck_status"] == "not_triggered"


def test_l1_packet_does_not_leak_raw_or_secret_material() -> None:
    trace = _base_trace()
    trace.update(
        {
            "raw_prompt": "RAW_PROMPT_SHOULD_NOT_LEAK",
            "provider_payload": {"secret": "RAW_PROVIDER_SHOULD_NOT_LEAK"},  # pragma: allowlist secret
            "active_source_class_recovery_queries": [
                "official rules api_key=REDACTION_SENTINEL_API_KEY_VALUE site:ecfr.gov"
            ],
            "provider_diagnostics": [
                {
                    "provider": "tavily",
                    "provider_role": "source_class_recovery",
                    "depth": "basic",
                    "max_results": 6,
                    "query_preview": "RAW_PROVIDER_SHOULD_NOT_LEAK",
                    "raw_provider_payload": "RAW_PROVIDER_SHOULD_NOT_LEAK",
                    "failure_type": "secret=REDACTION_SENTINEL_SECRET_VALUE",
                    "success": False,
                }
            ],
        }
    )

    packet = build_source_class_recovery_validation_packet(trace)
    encoded = json.dumps(packet, sort_keys=True)

    assert "RAW_PROMPT_SHOULD_NOT_LEAK" not in encoded
    assert "RAW_PROVIDER_SHOULD_NOT_LEAK" not in encoded
    assert "REDACTION_SENTINEL_API_KEY_VALUE" not in encoded
    assert "REDACTION_SENTINEL_SECRET_VALUE" not in encoded
    assert "raw_provider_payload" not in encoded
    assert "provider_payload" not in encoded
    assert "raw_prompt" not in encoded
