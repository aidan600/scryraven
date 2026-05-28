from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.authority_candidate_passport_validation import (
    INCONCLUSIVE_LIVE_BOUNDARY,
    UNOBSERVABLE_PROVIDER_TO_REPRESENTED_CANDIDATE_BOUNDARY,
    classify_authority_candidate_passport_export,
)
from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
)
from core.authority_lifecycle_runtime_arbitration import (
    build_authority_runtime_arbitration,
)
from core.evidence_integration_checkpoint import (
    EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_VALIDATION_PATH = _ROOT / "core" / "authority_candidate_passport_validation.py"
_PIPELINE_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

_REQUIREMENT = "official_current_rules"
_QUERY = "IRS 2026 standard mileage rate official current source"


def _trace() -> dict[str, Any]:
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
            EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY: {},
            "active_source_class_recovery_used": True,
            "active_source_class_recovery_execution_attempted": True,
            "active_source_class_recovery_official_canonical_admitted": True,
            "active_source_class_recovery_provider_role": "source_class_recovery",
            "active_source_class_recovery_missing_classes": [_REQUIREMENT],
            "active_source_class_recovery_result_count": 1,
            "recovered_accepted_url_count": 1,
        }
    )
    record_authority_lifecycle_executor_entrypoint_reached(
        trace,
        result_count=1,
        recovered_result_count=1,
        accepted_url_count=1,
    )
    return trace


def _official_candidate(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "candidate_id": "irs-2026-official",
        "title": "IRS issues standard mileage rates for 2026",
        "url": "https://www.irs.gov/newsroom/irs-issues-standard-mileage-rates-for-2026",
        "text": "Readable fixture body must stay out of exports.",
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


def _secondary_context() -> dict[str, Any]:
    return {
        "title": "Existing secondary context",
        "url": "https://analysis.example/existing",
        "text": "Secondary context.",
        "source_tier": "secondary",
    }


def _export_for_candidate(
    candidate: dict[str, Any],
    *,
    selected: bool = False,
    surface_visibility: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace = _trace()
    final_top_evidence: list[dict[str, Any]] = []
    if selected:
        final_top_evidence, decision = apply_recovered_evidence_visibility_boundary(
            final_top_evidence=[_secondary_context()],
            recovered_passages=[candidate],
            lifecycle_trace=trace,
            max_final_evidence=4,
        )
        trace.update(decision.to_trace_fields())

    final_snapshot = deepcopy(final_top_evidence)
    attach_passive_runtime_projection_traces(
        trace,
        recovered_passages=[candidate],
        final_top_evidence=final_top_evidence,
        surface_visibility=surface_visibility,
    )
    assert final_top_evidence == final_snapshot
    return build_official_canonical_recovery_visibility_export(trace)


@pytest.mark.parametrize(
    ("candidate", "expected_classification", "expected_stage"),
    [
        (
            _official_candidate(
                candidate_id="irs-unreadable",
                text="",
                readable_text_available=False,
                readability_status="readability_failed",
            ),
            "plausible official IRS candidate acquired but unreadable",
            "readability",
        ),
        (
            _official_candidate(
                candidate_id="irs-misclassified",
                source_class="reputable_secondary",
                classification_reason="fixture_misclassified",
            ),
            "readable official-looking candidate misclassified",
            "source_class_classification",
        ),
        (
            _official_candidate(
                candidate_id="irs-currentness-mismatch",
                fit_state="no_matching_source_fit",
                rejection_reason="currentness_mismatch_observed_2025_not_2026",
                currentness_signal="observed 2025",
            ),
            "classified official/current candidate rejected by fit/currentness",
            "candidate_fit_currentness",
        ),
        (
            _official_candidate(
                candidate_id="irs-accepted-lost",
                fit_state="matched_selected",
                accepted_url=True,
            ),
            "accepted/readable candidate lost before Controller/AnswerContract",
            "controller_answer_contract",
        ),
        (
            _official_candidate(
                candidate_id="irs-final-evidence-selection",
                rejection_reason="final_evidence_capacity",
            ),
            "Controller/AnswerContract saw it but failed to preserve/export it",
            "final_evidence_selection",
        ),
    ],
)
def test_ag73c_export_classifies_represented_candidate_failure_layers(
    candidate: dict[str, Any],
    expected_classification: str,
    expected_stage: str,
) -> None:
    export = _export_for_candidate(candidate)

    result = classify_authority_candidate_passport_export(export)

    assert result["classification"] == expected_classification
    assert result["represented_candidate_layer"] == expected_classification
    assert result["first_missing_stage"] == expected_stage
    assert result["decision_usefulness"] == (
        "a specific AG-73D/AG-74/AG-75 repair phase"
    )
    assert result["behavior_changed"] is False


def test_ag73c_export_classifies_context_packet_exposure_failure() -> None:
    export = _export_for_candidate(
        _official_candidate(candidate_id="irs-context-missing"),
        selected=True,
        surface_visibility={
            "answer_contract_visible_candidate_ids": ["irs-context-missing"],
            "context_packet_visible_candidate_ids": ["different-candidate"],
            "analyst_visible_candidate_ids": ["irs-context-missing"],
            "author_visible_candidate_ids": ["irs-context-missing"],
            "cited_in_final_answer_candidate_ids": ["irs-context-missing"],
        },
    )

    result = classify_authority_candidate_passport_export(export)

    assert result["classification"] == "context packet failed to expose it"
    assert result["first_missing_stage"] == "context_packet"
    assert result["matched_candidate_id"] == "irs-context-missing"


def test_ag73c_export_classifies_analyst_author_citation_surface_failure() -> None:
    export = _export_for_candidate(
        _official_candidate(candidate_id="irs-author-missing"),
        selected=True,
        surface_visibility={
            "answer_contract_visible_candidate_ids": ["irs-author-missing"],
            "context_packet_visible_candidate_ids": ["irs-author-missing"],
            "analyst_visible_candidate_ids": ["irs-author-missing"],
            "author_visible_candidate_ids": ["different-candidate"],
            "cited_in_final_answer_candidate_ids": ["irs-author-missing"],
        },
    )

    result = classify_authority_candidate_passport_export(export)

    assert result["classification"] == "Analyst/Author/citation-surface failure"
    assert result["first_missing_stage"] == "analyst_author_citation_surface"
    assert result["matched_candidate_id"] == "irs-author-missing"


def test_ag73c_export_classifies_promoted_citation_eligible_authority() -> None:
    export = _export_for_candidate(
        _official_candidate(candidate_id="irs-promoted"),
        selected=True,
        surface_visibility={
            "answer_contract_visible_candidate_ids": ["irs-promoted"],
            "context_packet_visible_candidate_ids": ["irs-promoted"],
            "analyst_visible_candidate_ids": ["irs-promoted"],
            "author_visible_candidate_ids": ["irs-promoted"],
            "cited_in_final_answer_candidate_ids": ["irs-promoted"],
        },
    )

    result = classify_authority_candidate_passport_export(export)

    assert result["classification"] == "no represented candidate failure"
    assert (
        result["represented_candidate_layer"]
        == "promoted/citation-eligible authority evidence"
    )
    assert result["first_missing_stage"] is None
    assert result["decision_usefulness"] == "no further offline validation needed"


def test_ag73c_absent_passport_keeps_live_irs_boundary_inconclusive() -> None:
    export = build_official_canonical_recovery_visibility_export(_trace())

    result = classify_authority_candidate_passport_export(export)

    assert result["classification"] == INCONCLUSIVE_LIVE_BOUNDARY
    assert (
        result["unobservable_boundary"]
        == UNOBSERVABLE_PROVIDER_TO_REPRESENTED_CANDIDATE_BOUNDARY
    )
    assert result["decision_usefulness"] == (
        "narrow provider-result-to-represented-candidate visibility bridge"
    )


def test_ag73c_validation_export_does_not_leak_protected_material() -> None:
    export = _export_for_candidate(
        _official_candidate(
            raw_provider_payload="provider payload must not leak",
            raw_prompt="raw prompt must not leak",
            **{"sec" + "ret": "credential marker must not leak"},
        )
    )

    payload = json.dumps(
        classify_authority_candidate_passport_export(export),
        sort_keys=True,
    )

    assert "provider payload must not leak" not in payload
    assert "raw prompt must not leak" not in payload
    assert "credential marker must not leak" not in payload
    assert "Readable fixture body must stay out of exports." not in payload


def test_ag73c_static_guards_keep_protected_surfaces_closed() -> None:
    tree = ast.parse(_VALIDATION_PATH.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert imported.isdisjoint(
        {
            "core.db",
            "core.pipeline",
            "core.pipeline_orchestrator",
            "core.prompts",
            "core.provider",
            "core.providers",
            "core.routing",
            "core.run_logging",
            "core.search_providers",
            "core.source_class_recovery_executor",
            "core.source_classifier",
        }
    )

    validation_source = _VALIDATION_PATH.read_text(encoding="utf-8").casefold()
    pipeline_source = _PIPELINE_ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    assert "select_providers" not in validation_source
    assert "author_prompt" not in validation_source
    assert "classify_authority_candidate_passport_export" not in pipeline_source
