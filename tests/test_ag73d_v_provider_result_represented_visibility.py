from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from core.authority_candidate_passport import (
    AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY,
    build_authority_candidate_passport_projection,
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
from core.pipeline import process_search_queries
from core.provider_result_represented_visibility import (
    PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY,
    build_provider_result_represented_visibility_projection,
)
from core.runtime_trace_projection_assembly import (
    attach_passive_runtime_projection_traces,
)

_ROOT = Path(__file__).resolve().parents[1]
_BRIDGE_PATH = _ROOT / "core" / "provider_result_represented_visibility.py"
_PIPELINE_PATH = _ROOT / "core" / "pipeline.py"
_ASSEMBLY_PATH = _ROOT / "core" / "runtime_trace_projection_assembly.py"
_EXPORT_PATH = _ROOT / "core" / "official_canonical_recovery_visibility_export.py"

_REQUIREMENT = "official_current_rules"
_QUERY = "IRS 2026 standard mileage rate official current source"
_IRS_URL = "https://www.irs.gov/newsroom/irs-issues-standard-mileage-rates-for-2026"


def _trace(*, result_count: int = 1) -> dict[str, Any]:
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
            "active_source_class_recovery_result_count": result_count,
            "candidate_acquisition_provider_result_count": result_count,
            "recovered_accepted_url_count": result_count,
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
        accepted_url_count=result_count,
    )
    return trace


def _official_candidate(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "candidate_id": "irs-2026-official",
        "title": "IRS issues standard mileage rates for 2026",
        "url": _IRS_URL,
        "text": "Official IRS current guidance states the 2026 business rate.",
        "source_tier": "official",
        "source_class": _REQUIREMENT,
        "retrieval_stage": "source_class_recovery",
        "_provider_role": "source_class_recovery",
        "provider_name": "offline-fixture",
        "provider_rank_or_position": 1,
        "classification_reason": "declared_source_class",
        "currentness_signal": "2026 observed",
        "claim_value_extraction_status": "extracted",
    }
    candidate.update(overrides)
    return candidate


def _provider_result(**overrides: Any) -> dict[str, Any]:
    result = {
        "provider_result_id": "provider-result-irs-1",
        "provider_name": "offline-provider",
        "provider_role": "source_class_recovery",
        "retrieval_pass_id": "source_class_recovery:1",
        "query_preview": _QUERY,
        "provider_rank_or_position": 1,
        "source_url": _IRS_URL,
        "normalized_domain": "irs.gov",
        "title": "IRS issues standard mileage rates for 2026",
        "source_tier": "official",
        "source_class": _REQUIREMENT,
        "provider_returned": True,
        "diagnostic_only": True,
        "sanitized": True,
        "behavior_changed": False,
    }
    result.update(overrides)
    return result


def _passport_projection(candidate: dict[str, Any]) -> dict[str, Any]:
    return build_authority_candidate_passport_projection(
        lifecycle_trace=_trace(),
        recovered_passages=[candidate],
    )


def test_ag73d_v_provider_result_matches_represented_passport() -> None:
    projection = build_provider_result_represented_visibility_projection(
        runtime_trace={"provider_result_summary_count": 1},
        provider_results=[_provider_result()],
        passport_projection=_passport_projection(
            _official_candidate(fit_state="matched_selected")
        ),
    )
    record = projection["bridge_records"][0]

    assert projection["diagnostic_only"] is True
    assert projection["sanitized"] is True
    assert projection["behavior_changed"] is False
    assert projection["aggregate_reconciliation_status"] == "reconciled"
    assert record["bridge_disposition"] == "represented_passport_matched"
    assert record["passport_candidate_id"] == "irs-2026-official"
    assert record["represented_candidate_visible"] is True
    assert record["passport_visible"] is True
    assert record["first_missing_stage"] == "controller_answer_contract"


def test_ag73d_v_non_represented_provider_result_carries_durable_reason() -> None:
    projection = build_provider_result_represented_visibility_projection(
        runtime_trace={"provider_result_summary_count": 1},
        provider_results=[
            _provider_result(
                provider_result_id="provider-result-duplicate",
                non_representation_reason="duplicate_seen_url",
            )
        ],
        passport_projection={"passports": []},
    )
    record = projection["bridge_records"][0]

    assert record["bridge_disposition"] == "not_represented_with_reason"
    assert record["non_representation_reason"] == "duplicate_seen_url"
    assert record["first_missing_stage"] == "dedupe"
    assert record["represented_candidate_visible"] is False
    assert projection["unobservable_boundary"] is None


def test_ag73d_v_lower_tier_result_does_not_satisfy_official_obligation() -> None:
    secondary = _official_candidate(
        candidate_id="secondary-mileage-analysis",
        url="https://analysis.example/irs-mileage",
        source_tier="secondary",
        source_class="secondary",
    )
    projection = build_provider_result_represented_visibility_projection(
        runtime_trace={"provider_result_summary_count": 1},
        provider_results=[
            _provider_result(
                source_url="https://analysis.example/irs-mileage",
                normalized_domain="analysis.example",
                source_tier="secondary",
                source_class="secondary",
            )
        ],
        passport_projection=_passport_projection(secondary),
    )
    record = projection["bridge_records"][0]

    assert record["bridge_disposition"] == "lower_tier_not_authority_satisfying"
    assert record["non_representation_reason"] == (
        "lower_tier_or_secondary_not_satisfying_official_current_obligation"
    )
    assert record["first_missing_stage"] == "source_class_or_tier"
    assert record["passport_visible"] is True


def test_ag73d_v_aggregate_only_provider_result_remains_unobservable() -> None:
    projection = build_provider_result_represented_visibility_projection(
        runtime_trace={"candidate_acquisition_provider_result_count": 2},
        provider_results=[],
        passport_projection={"passports": []},
    )

    assert projection["bridge_record_count"] == 0
    assert projection["aggregate_reconciliation_status"] == (
        "aggregate_provider_count_exceeds_visible_bridge_records"
    )
    assert projection["unobservable_boundary"] == (
        "provider-result to represented authority candidate"
    )


def test_ag73d_v_runtime_trace_and_visibility_export_expose_bridge() -> None:
    trace = {
        **_trace(),
        "provider_diagnostics": [
            {
                "provider": "offline-provider",
                "provider_role": "source_class_recovery",
                "query_preview": _QUERY,
                "provider_result_summary_count": 1,
                "provider_result_summaries": [_provider_result()],
            }
        ],
    }
    attach_passive_runtime_projection_traces(
        trace,
        recovered_passages=[_official_candidate()],
        final_top_evidence=[],
    )
    bridge = trace[PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY][
        "ProviderResultRepresentedCandidateBridge"
    ]
    export = build_official_canonical_recovery_visibility_export(trace)

    assert bridge["bridge_record_count"] == 1
    assert bridge["bridge_records"][0]["bridge_disposition"] == (
        "represented_passport_matched"
    )
    assert (
        trace[EVIDENCE_INTEGRATION_CHECKPOINT_TRACE_KEY][
            PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY
        ]
        == trace[PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY]
    )
    assert export["provider_result_bridge_available"] is True
    assert export["provider_result_bridge_record_count"] == 1
    assert export["provider_result_bridge_aggregate_reconciliation_status"] == (
        "reconciled"
    )
    assert export["provider_result_represented_candidate_bridge"][
        "bridge_records"
    ] == bridge["bridge_records"]


def test_ag73d_v_provider_result_summaries_are_sanitized_and_behavior_neutral() -> None:
    diagnostics: list[dict[str, object]] = []
    first = {
        "title": "Official IRS source",
        "url": _IRS_URL,
        "snippet": "snippet body must not leak",
        "raw_content": "raw body must not leak " * 12,
        "raw_provider_payload": "provider payload must not leak",
        "credibility": 3,
    }
    duplicate = dict(first)

    with patch("core.pipeline.search_web_results", return_value=([first, duplicate], [])):
        passages = process_search_queries(
            [_QUERY],
            "general",
            "low",
            "basic",
            6,
            [],
            [],
            None,
            set(),
            set(),
            "OpenAI",
            "text-embedding-3-small",
            "http://localhost",
            lambda *_args, **_kwargs: [],
            lambda *_args, **_kwargs: [],
            status_container=MagicMock(),
            search_providers=["tavily"],
            provider_diagnostics=diagnostics,
            provider_role="source_class_recovery",
            iteration=1,
        )

    payload = json.dumps(diagnostics, sort_keys=True)
    summaries = diagnostics[0]["provider_result_summaries"]

    assert [passage["url"] for passage in passages] == [_IRS_URL]
    assert diagnostics[0]["accepted_url_count"] == 1
    assert diagnostics[0]["provider_result_summary_count"] == 2
    assert summaries[0]["non_representation_reason"] is None
    assert summaries[1]["non_representation_reason"] == "duplicate_provider_url"
    assert "snippet body must not leak" not in payload
    assert "raw body must not leak" not in payload
    assert "provider payload must not leak" not in payload


def test_ag73d_v_static_guards_keep_closed_surfaces_closed() -> None:
    for path in (_BRIDGE_PATH, _ASSEMBLY_PATH, _EXPORT_PATH):
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
                "core.pipeline_orchestrator",
                "core.prompts",
                "core.provider",
                "core.providers",
                "core.routing",
                "core.run_logging",
                "core.search_providers",
                "core.source_classifier",
            }
        )

    bridge_source = _BRIDGE_PATH.read_text(encoding="utf-8")
    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "select_providers" not in bridge_source
    assert "search_web_results(" not in bridge_source
    assert "build_provider_attempt_diagnostic" in pipeline_source
    assert AUTHORITY_CANDIDATE_PASSPORT_TRACE_KEY != (
        PROVIDER_RESULT_REPRESENTED_VISIBILITY_TRACE_KEY
    )
