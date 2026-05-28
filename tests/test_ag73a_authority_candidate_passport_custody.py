from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from core.authority_candidate_passport import (
    assert_authority_candidate_passport_integrity,
    build_authority_candidate_passport_projection,
)
from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)

_ROOT = Path(__file__).resolve().parents[1]
_PASSPORT_PATH = _ROOT / "core" / "authority_candidate_passport.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

_REQUIREMENT = "official_current_rules"
_QUERY = "IRS 2026 standard mileage rate official current source"


def _trace(
    *,
    result_count: int = 1,
    accepted_url_count: int = 1,
) -> dict[str, Any]:
    trace = build_authority_runtime_arbitration(
        requirement_id=_REQUIREMENT,
        required_authority=_REQUIREMENT,
        claim_type="official_current_status",
        required_recovery=True,
        recovery_queries=(_QUERY,),
        required_source_classes=(_REQUIREMENT,),
        recovery_action_allowed=True,
    ).to_trace_fields()
    trace.update(
        {
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:"
                "official_current_rules"
            ),
            "active_source_class_recovery_skip_reason": None,
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_missing_classes": [_REQUIREMENT],
            "active_source_class_recovery_result_count": result_count,
            "recovered_accepted_url_count": accepted_url_count,
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": [_REQUIREMENT],
                "allowed_action": True,
            },
        }
    )
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=result_count,
        recovered_result_count=result_count,
        accepted_url_count=accepted_url_count,
    )
    return trace


def _official_candidate(
    url: str = "https://www.irs.gov/newsroom/irs-issues-standard-mileage-rates-for-2026",
    **overrides: Any,
) -> dict[str, Any]:
    candidate = {
        "candidate_id": "irs-2026-official",
        "title": "IRS issues standard mileage rates for 2026",
        "url": url,
        "text": "Official IRS current guidance states the 2026 business rate.",
        "source_tier": "official",
        "source_class": _REQUIREMENT,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "provider_name": "offline-fixture",
        "provider_rank_or_position": 1,
        "classification_reason": "declared_source_class",
        "currentness_signal": "2026 observed",
        "temporal_anchor_required": "2026 business mileage rate",
        "temporal_anchor_observed": "2026",
        "claim_value_extraction_status": "extracted",
    }
    candidate.update(overrides)
    return candidate


def _secondary_candidate(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "candidate_id": "secondary-2026-rate",
        "title": "Secondary mileage-rate analysis",
        "url": "https://analysis.example/irs-2026-mileage-rate",
        "text": "Secondary discussion of the IRS mileage rate.",
        "source_tier": "secondary",
        "source_class": _REQUIREMENT,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
    }
    candidate.update(overrides)
    return candidate


def _existing_secondary() -> dict[str, Any]:
    return {
        "title": "Existing secondary context",
        "url": "https://analysis.example/existing",
        "text": "Secondary context.",
        "source_tier": "secondary",
    }


def _passport_for(
    candidate: dict[str, Any],
    *,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    projection = build_authority_candidate_passport_projection(
        lifecycle_trace=trace or _trace(),
        recovered_passages=[candidate],
    )
    assert_authority_candidate_passport_integrity(projection)
    return projection["passports"][0]


def _selected_projection(
    candidate: dict[str, Any],
    *,
    surface_visibility: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace = _trace()
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_existing_secondary()],
        recovered_passages=[candidate],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())
    export = build_official_canonical_recovery_visibility_export(trace)
    projection = build_authority_candidate_passport_projection(
        lifecycle_trace=trace,
        recovered_passages=[candidate],
        final_top_evidence=final,
        visibility_export=export,
        surface_visibility=surface_visibility,
    )
    assert_authority_candidate_passport_integrity(projection)
    return projection


def test_ag73a_provider_found_plausible_official_candidate_but_readability_failed() -> None:
    passport = _passport_for(
        _official_candidate(
            candidate_id="irs-unreadable",
            text="",
            readable_text_available=False,
            readability_status="readability_failed",
            claim_value_extraction_status="not_attempted",
        )
    )

    assert passport["provider_returned"] is True
    assert passport["official_domain_signal"] is True
    assert passport["readability_status"] == "readability_failed"
    assert passport["readable_text_available"] is False
    assert passport["first_missing_stage"] == "readability"
    assert passport["final_disposition"] == "rejected"
    assert passport["rejection_reason"] == "readability_failed"


def test_ag73a_readable_official_looking_candidate_was_misclassified() -> None:
    passport = _passport_for(
        _official_candidate(
            candidate_id="irs-misclassified",
            source_class="reputable_secondary",
            classification_reason="classification_mismatch_fixture",
        )
    )

    assert passport["readable_text_available"] is True
    assert passport["official_domain_signal"] is True
    assert passport["source_class"] == "reputable_secondary"
    assert passport["first_missing_stage"] == "source_class_classification"
    assert passport["rejection_reason"] == "source_class_mismatch"
    assert passport["satisfies_authority"] is False


def test_ag73a_classified_official_current_candidate_rejected_by_fit_currentness() -> None:
    passport = _passport_for(
        _official_candidate(
            candidate_id="irs-currentness-mismatch",
            fit_state="no_matching_source_fit",
            rejection_reason="currentness_mismatch_observed_2025_not_2026",
            currentness_signal="observed 2025",
            temporal_anchor_observed="2025",
        )
    )

    assert passport["source_class"] == _REQUIREMENT
    assert passport["first_missing_stage"] == "candidate_fit_currentness"
    assert passport["fit_state"] == "no_matching_source_fit"
    assert passport["rejection_reason"] == (
        "currentness_mismatch_observed_2025_not_2026"
    )


def test_ag73a_accepted_candidate_lost_before_controller_answer_contract() -> None:
    passport = _passport_for(
        _official_candidate(
            candidate_id="irs-accepted-not-controller-visible",
            fit_state="matched_selected",
        )
    )

    assert passport["fit_state"] == "matched_selected"
    assert passport["controller_visible"] == "unknown"
    assert passport["first_missing_stage"] == "controller_answer_contract"
    assert passport["final_disposition"] == (
        "accepted_but_lost_before_controller_answer_contract"
    )


def test_ag73a_final_selected_authority_failed_context_exposure() -> None:
    projection = _selected_projection(
        _official_candidate(
            candidate_id="irs-context-missing",
            context_packet_visible=False,
        ),
        surface_visibility={
            "answer_contract_visible_candidate_ids": ["irs-context-missing"],
            "analyst_visible_candidate_ids": ["irs-context-missing"],
            "author_visible_candidate_ids": ["irs-context-missing"],
            "cited_in_final_answer_candidate_ids": ["irs-context-missing"],
        },
    )
    passport = projection["passports"][0]

    assert passport["fit_state"] == "matched_selected"
    assert passport["answer_contract_visible"] is True
    assert passport["context_packet_visible"] is False
    assert passport["first_missing_stage"] == "context_packet"
    assert passport["final_disposition"] == "final_selected_context_exposure_missing"


def test_ag73a_promoted_candidate_is_citation_eligible_and_cited_when_visible() -> None:
    projection = _selected_projection(
        _official_candidate(candidate_id="irs-promoted"),
        surface_visibility={
            "answer_contract_visible_candidate_ids": ["irs-promoted"],
            "context_packet_visible_candidate_ids": ["irs-promoted"],
            "analyst_visible_candidate_ids": ["irs-promoted"],
            "author_visible_candidate_ids": ["irs-promoted"],
            "cited_in_final_answer_candidate_ids": ["irs-promoted"],
        },
    )
    passport = projection["passports"][0]

    assert passport["final_disposition"] == "promoted_final_authority_evidence"
    assert passport["citation_eligible"] is True
    assert passport["cited_in_final_answer"] is True


def test_ag73a_aggregate_counts_reconcile_with_existing_visibility_export() -> None:
    projection = _selected_projection(_official_candidate())

    assert projection["passport_counts_reconcile"] is True
    assert projection["aggregate_counts"]["represented_candidate_count"] == 1
    assert projection["aggregate_counts"][
        "accepted_readable_authority_evidence_count"
    ] == 1
    assert projection["aggregate_counts"][
        "final_selected_authority_evidence_count"
    ] == 1


def test_ag73a_secondary_lower_tier_candidate_does_not_satisfy_official_obligation() -> None:
    passport = _passport_for(_secondary_candidate())

    assert passport["source_tier"] == "secondary"
    assert passport["required_source_class"] == _REQUIREMENT
    assert passport["satisfies_authority"] is False
    assert passport["final_disposition"] == "rejected"
    assert passport["rejection_reason"] == (
        "secondary_or_lower_tier_not_satisfying_authority"
    )


def test_ag73a_duplicate_and_claim_extraction_rejections_are_durable() -> None:
    duplicate = _passport_for(
        _official_candidate(
            candidate_id="irs-duplicate",
            rejection_reason="duplicate_recovered_source",
            deduped_against_candidate_id="irs-original",
        )
    )
    missing_claim = _passport_for(
        _official_candidate(
            candidate_id="irs-missing-claim",
            claim_value_extraction_status="missing_required_value",
            rejection_reason="claim_value_extraction_missing",
        )
    )

    assert duplicate["first_missing_stage"] == "dedupe"
    assert duplicate["deduped_against_candidate_id"] == "irs-original"
    assert missing_claim["claim_value_extraction_status"] == (
        "missing_required_value"
    )
    assert missing_claim["rejection_reason"] == "claim_value_extraction_missing"


def test_ag73a_represented_candidate_without_durable_reason_is_flagged() -> None:
    projection = build_authority_candidate_passport_projection(
        lifecycle_trace=_trace(),
        recovered_passages=[
            {
                "candidate_id": "silent-drop",
                "title": "Unclassified candidate",
                "url": "https://example.com/candidate",
                "text": "Readable but not classified or dispositioned.",
                "source_tier": "unknown",
                "source_class": "unknown",
                "official_domain_signal": False,
            }
        ],
    )

    assert projection["passport_integrity_status"] == "silent_drop_detected"
    assert projection["silent_drop_candidate_ids"] == ["silent-drop"]
    with pytest.raises(AssertionError, match="silent-drop"):
        assert_authority_candidate_passport_integrity(projection)


def test_ag73a_projection_is_sanitized_and_does_not_leak_protected_material() -> None:
    projection = build_authority_candidate_passport_projection(
        lifecycle_trace={
            **_trace(),
            "raw_provider_payload": "do not leak",
            "raw_prompt": "do not leak",
        },
        recovered_passages=[
            _official_candidate(
                raw_provider_payload="do not leak",
                raw_prompt="do not leak",
                api_key="sk-do-not-leak",
            )
        ],
    )
    payload = json.dumps(projection, sort_keys=True)

    assert "do not leak" not in payload
    assert "sk-do-not-leak" not in payload
    assert projection["behavior_changed"] is False


def test_ag73a_static_guard_keeps_protected_surfaces_closed() -> None:
    forbidden_import_prefixes = {
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.db",
        "core.llm",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.provider",
        "core.providers",
        "core.routing",
        "core.search_providers",
        "core.source_classifier",
        "core.author",
        "core.economist",
        "core.final_answer",
    }
    tree = ast.parse(_PASSPORT_PATH.read_text(encoding="utf-8"))
    imported = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    imported.extend(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    violations = [
        name
        for name in imported
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]

    passport_source = _PASSPORT_PATH.read_text(encoding="utf-8").casefold()
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8").casefold()
    assert violations == []
    assert "select_providers" not in passport_source
    assert "author_prompt" not in passport_source
    assert "authority_candidate_passport" not in pipeline_source
