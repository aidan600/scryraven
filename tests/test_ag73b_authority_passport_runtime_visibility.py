from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.authority_candidate_passport import (
    AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY,
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
    OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY,
    append_official_canonical_recovery_diagnostics_section,
    build_official_canonical_recovery_visibility_export,
)
from core.recovered_evidence_visibility import (
    apply_recovered_evidence_visibility_boundary,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_ASSEMBLY_PATH = _ROOT / "core" / "runtime_trace_projection_assembly.py"
_EXPORT_PATH = _ROOT / "core" / "official_canonical_recovery_visibility_export.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"

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
            "active_source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:"
                "official_current_rules"
            ),
            "active_source_class_recovery_skip_reason": None,
            "active_source_class_recovery_blockers": [],
            "active_source_class_recovery_missing_classes": [_REQUIREMENT],
            "active_source_class_recovery_result_count": 1,
            "recovered_accepted_url_count": 1,
            "active_source_class_recovery_action_envelope": {
                "action_type": "recover_missing_source_class",
                "required_source_class": [_REQUIREMENT],
                "allowed_action": True,
            },
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
        "text": "Readable fixture body must stay out of passport exports.",
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


def _existing_secondary() -> dict[str, Any]:
    return {
        "title": "Existing secondary context",
        "url": "https://analysis.example/existing",
        "text": "Secondary context.",
        "source_tier": "secondary",
    }


def _attach_selected_candidate(
    *,
    surface_visibility: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    trace = _trace()
    candidate = _official_candidate()
    final, decision = apply_recovered_evidence_visibility_boundary(
        final_top_evidence=[_existing_secondary()],
        recovered_passages=[candidate],
        lifecycle_trace=trace,
        max_final_evidence=4,
    )
    trace.update(decision.to_trace_fields())
    final_snapshot = deepcopy(final)

    returned = attach_passive_runtime_projection_traces(
        trace,
        recovered_passages=[candidate],
        final_top_evidence=final,
        surface_visibility=surface_visibility,
    )

    assert final == final_snapshot
    return returned, final, candidate


def _passport_projection(trace: dict[str, Any]) -> dict[str, Any]:
    packet = trace[AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY]
    return packet["AuthorityCandidatePassportProjection"]


def test_ag73b_runtime_attachment_exposes_passport_trace_and_checkpoint() -> None:
    trace, _final, _candidate = _attach_selected_candidate(
        surface_visibility={
            "answer_contract_visible_candidate_ids": ["irs-2026-official"],
            "context_packet_visible_candidate_ids": ["irs-2026-official"],
            "analyst_visible_candidate_ids": ["irs-2026-official"],
            "author_visible_candidate_ids": ["irs-2026-official"],
            "cited_in_final_answer_candidate_ids": ["irs-2026-official"],
        }
    )
    projection = _passport_projection(trace)
    passport = projection["passports"][0]

    assert projection["diagnostic_only"] is True
    assert projection["sanitized"] is True
    assert projection["behavior_changed"] is False
    assert projection["passport_count"] == 1
    assert passport["candidate_id"] == "irs-2026-official"
    assert passport["final_disposition"] == "promoted_final_authority_evidence"
    assert passport["first_missing_stage"] is None
    assert (
        trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY
        ]
        == trace[AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY]
    )


def test_ag73b_visibility_export_includes_disposition_and_first_missing_stage() -> None:
    trace = _trace()
    candidate = _official_candidate(
        candidate_id="irs-unreadable",
        text="",
        readable_text_available=False,
        readability_status="readability_failed",
    )

    attach_passive_runtime_projection_traces(
        trace,
        recovered_passages=[candidate],
        final_top_evidence=[],
    )
    export = build_official_canonical_recovery_visibility_export(trace)
    rendered = append_official_canonical_recovery_diagnostics_section("", trace)

    assert export["authority_candidate_passport_available"] is True
    assert export["authority_candidate_passport_count"] == 1
    assert export["authority_candidate_passport_integrity_status"] == "complete"
    assert export["authority_candidate_passport_final_dispositions"] == ["rejected"]
    assert export["authority_candidate_passport_first_missing_stages"] == [
        "readability"
    ]
    assert (
        export["authority_candidate_passport_projection"]["passports"][0][
            "first_missing_stage"
        ]
        == "readability"
    )
    assert "`authority_candidate_passport_available`: true" in rendered
    assert "`authority_candidate_passport_first_missing_stages`: readability" in rendered


def test_ag73b_official_visibility_trace_carries_passport_export_projection() -> None:
    trace, _final, _candidate = _attach_selected_candidate()
    visibility = trace[OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY][
        "OfficialCanonicalRecoveryVisibility"
    ]

    assert visibility["authority_candidate_passport_available"] is True
    assert visibility["authority_candidate_passport_count"] == 1
    assert visibility["authority_candidate_passport_projection"]["passports"] == (
        _passport_projection(trace)["passports"]
    )
    assert visibility["authority_candidate_passport_projection"][
        "passport_integrity_status"
    ] == "complete"
    assert visibility["behavior_changed"] is False


def test_ag73b_passport_runtime_export_does_not_leak_protected_material() -> None:
    trace = {
        **_trace(),
        "raw_provider_payload": "provider payload must not leak",
        "raw_prompt": "raw prompt must not leak",
        "api_" + "key": "credential marker must not leak",
        "db_row": {"private": "db row must not leak"},
        "full_trace": {"private": "full trace must not leak"},
    }
    candidate = _official_candidate(
        raw_provider_payload="provider payload must not leak",
        raw_prompt="raw prompt must not leak",
        **{"sec" + "ret": "credential marker must not leak"},
    )

    attach_passive_runtime_projection_traces(
        trace,
        recovered_passages=[candidate],
        final_top_evidence=[],
    )
    payload = json.dumps(
        {
            "passport": trace[AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY],
            "visibility": trace[OFFICIAL_CANONICAL_RECOVERY_VISIBILITY_TRACE_KEY],
        },
        sort_keys=True,
    )

    assert "provider payload must not leak" not in payload
    assert "raw prompt must not leak" not in payload
    assert "credential marker must not leak" not in payload
    assert "db row must not leak" not in payload
    assert "full trace must not leak" not in payload
    assert "Readable fixture body must stay out of passport exports." not in payload


def test_ag73b_static_guards_keep_behavior_surfaces_closed() -> None:
    for path in (_ASSEMBLY_PATH, _EXPORT_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
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

    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "build_authority_candidate_passport" not in pipeline_source
    assert "AUTHORITY_CANDIDATE_PASSPORT" not in pipeline_source
    assert "select_providers" not in (
        _ROOT / "core" / "authority_candidate_passport.py"
    ).read_text(encoding="utf-8")
