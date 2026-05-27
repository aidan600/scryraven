from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.official_canonical_recovery_candidate_acquisition import (
    UNKNOWN,
    build_official_canonical_recovery_candidate_acquisition_trace,
)
from core.official_canonical_recovery_visibility_export import (
    build_official_canonical_recovery_visibility_export,
)

_ROOT = Path(__file__).resolve().parents[1]
_ACQUISITION_PATH = (
    _ROOT / "core" / "official_canonical_recovery_candidate_acquisition.py"
)
_EXPORT_PATH = _ROOT / "core" / "official_canonical_recovery_visibility_export.py"
_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _admission_trace() -> dict[str, Any]:
    return {
        "official_canonical_recovery_execution_admission_trace": {
            "OfficialCanonicalRecoveryExecutionAdmission": {
                "admission_considered": True,
                "admission_eligible": True,
                "admission_used": True,
                "recovery_query_count": 1,
                "recovery_query_previews": ["canonical documentation topic"],
            }
        }
    }


def _executed_lifecycle(**overrides: Any) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "active_source_class_recovery_eligible": True,
        "active_source_class_recovery_used": True,
        "active_source_class_recovery_execution_attempted": True,
        "active_source_class_recovery_official_canonical_admitted": True,
        "active_source_class_recovery_provider_role": "source_class_recovery",
        "active_source_class_recovery_queries": ["canonical documentation topic"],
        "active_source_class_recovery_result_count": 0,
        "active_source_class_recovery_blockers": [],
    }
    trace.update(overrides)
    return trace


def _provider_attempt(
    *,
    result_count: int,
    accepted_url_count: int,
    success: bool = True,
) -> dict[str, Any]:
    return {
        "provider": "fixture_provider",
        "provider_role": "source_class_recovery",
        "success": success,
        "result_count": result_count,
        "accepted_url_count": accepted_url_count,
        "new_source_count": accepted_url_count,
    }


def test_ag52b_true_zero_candidate_classification_is_provider_zero() -> None:
    trace = build_official_canonical_recovery_candidate_acquisition_trace(
        lifecycle_trace=_executed_lifecycle(),
        provider_diagnostics=[_provider_attempt(result_count=0, accepted_url_count=0)],
    )
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **_executed_lifecycle(), **trace}
    )

    assert trace["candidate_acquisition_result_status"] == (
        "provider_returned_zero_results"
    )
    assert trace["candidate_visibility_export_status"] == "not_visible"
    assert trace["candidate_return_status"] == "zero_candidates"
    assert trace["zero_candidate_blocker_kind"] == "provider_returned_zero_results"
    assert export["candidate_return_status"] == "zero_candidates"
    assert export["zero_candidate_blocker_kind"] == "provider_returned_zero_results"
    assert export["likely_next_failure_layer"] == "provider_returned_zero_results"
    assert export["next_failure_layer"] == "execution_attempted_zero_candidates"


def test_ag52b_provider_results_hidden_are_not_reported_as_zero_candidates() -> None:
    trace = build_official_canonical_recovery_candidate_acquisition_trace(
        lifecycle_trace=_executed_lifecycle(raw_provider_payload="do not leak"),
        provider_diagnostics=[
            {
                **_provider_attempt(result_count=4, accepted_url_count=0),
                "raw_payload": "do not leak",
            }
        ],
    )
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **_executed_lifecycle(), **trace}
    )
    payload = json.dumps(export, sort_keys=True)

    assert trace["recovered_result_count"] == 0
    assert trace["candidate_acquisition_provider_result_count"] == 4
    assert trace["candidate_acquisition_result_status"] == "provider_results_returned"
    assert trace["candidate_visibility_export_status"] == (
        "candidate_visibility_not_exported"
    )
    assert trace["candidate_return_status"] == "candidate_visibility_not_exported"
    assert trace["zero_candidate_blocker_kind"] == UNKNOWN
    assert export["candidate_acquisition_provider_result_count"] == 4
    assert export["candidate_return_status"] == "candidate_visibility_not_exported"
    assert export["candidate_visibility_blocker_kind"] == (
        "candidate_visibility_not_exported"
    )
    assert export["likely_next_failure_layer"] == "candidate_visibility_not_exported"
    assert export["next_failure_layer"] == (
        "execution_attempted_candidate_visibility_not_exported"
    )
    assert "do not leak" not in payload


def test_ag52b_candidates_returned_visibility_exports_safe_counts() -> None:
    lifecycle = _executed_lifecycle(
        active_source_class_recovery_result_count=2,
        recovered_accepted_url_count=2,
        recovered_candidate_domain_preview=["docs.example"],
        recovered_source_tier_counts={"canonical": 1},
        recovered_source_class_counts={"primary_source_documents": 1},
    )
    trace = build_official_canonical_recovery_candidate_acquisition_trace(
        lifecycle_trace=lifecycle,
        provider_diagnostics=[_provider_attempt(result_count=2, accepted_url_count=2)],
    )
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **lifecycle, **trace}
    )

    assert trace["candidate_acquisition_result_status"] == "provider_results_returned"
    assert trace["candidate_visibility_export_status"] == "visible"
    assert trace["candidate_return_status"] == "candidates_returned"
    assert export["recovered_result_count"] == 2
    assert export["candidate_acquisition_provider_result_count"] == 2
    assert export["recovered_candidate_domain_preview"] == ["docs.example"]
    assert export["candidate_return_status"] == "candidates_returned"
    assert export["official_canonical_candidate_visible"] is True


def test_ag52b_official_canonical_candidate_visibility_uses_safe_counts() -> None:
    lifecycle = _executed_lifecycle(
        active_source_class_recovery_result_count=1,
        recovered_source_tier_counts={"official": 1},
        recovered_source_class_counts={"official_current_rules": 1},
    )
    trace = build_official_canonical_recovery_candidate_acquisition_trace(
        lifecycle_trace=lifecycle,
        provider_diagnostics=[_provider_attempt(result_count=1, accepted_url_count=1)],
    )
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **lifecycle, **trace}
    )

    assert trace["official_canonical_candidate_visible"] is True
    assert export["candidate_official_or_canonical_count"] == 1
    assert export["recovered_source_tier_counts"] == {"official": 1}
    assert export["recovered_source_class_counts"] == {"official_current_rules": 1}


def test_ag52b_preserves_ag52a_source_fit_handoff_fields() -> None:
    lifecycle = _executed_lifecycle(
        active_source_class_recovery_result_count=1,
        recovered_source_class_counts={"primary_source_documents": 1},
        recovered_visibility_source_fit_status="matched_selected",
        recovered_visibility_source_fit_candidate_count=1,
        recovered_visibility_source_fit_selected_count=1,
        recovered_visibility_source_fit_rejection_reasons=[],
    )
    trace = build_official_canonical_recovery_candidate_acquisition_trace(
        lifecycle_trace=lifecycle,
        provider_diagnostics=[_provider_attempt(result_count=1, accepted_url_count=1)],
    )
    export = build_official_canonical_recovery_visibility_export(
        {**_admission_trace(), **lifecycle, **trace}
    )

    assert export["recovered_candidate_source_fit_status"] == "matched_selected"
    assert export["recovered_candidate_source_fit_count"] == 1
    assert export["recovered_candidate_selected_readable_count"] == 1
    assert export["accepted_or_readable_official_or_canonical_count"] == 1


def test_ag52b_no_admitted_slot_remains_not_observable() -> None:
    export = build_official_canonical_recovery_visibility_export({})

    assert export["admission_used"] == UNKNOWN
    assert export["candidate_acquisition_result_status"] == UNKNOWN
    assert export["candidate_visibility_export_status"] == UNKNOWN
    assert export["candidate_return_status"] == UNKNOWN
    assert export["likely_next_failure_layer"] == "not_observable"


def test_ag52b_static_protected_surface_guard() -> None:
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
    protected_terms = {
        "select_providers",
        "choose_supplemental_search_depth",
        "author_prompt",
        "rank_sources",
        "source_classifier",
    }

    violations: list[str] = []
    for path in (_ACQUISITION_PATH, _EXPORT_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
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
        violations.extend(
            f"{path.name}:{name}"
            for name in imported
            for prefix in forbidden_import_prefixes
            if name == prefix or name.startswith(prefix + ".")
        )

    helper_and_export = (
        _ACQUISITION_PATH.read_text(encoding="utf-8")
        + "\n"
        + _EXPORT_PATH.read_text(encoding="utf-8")
    ).casefold()
    assert violations == []
    assert protected_terms.isdisjoint(helper_and_export.split())
    assert "ag52b" not in _ORCHESTRATOR_PATH.read_text(encoding="utf-8").casefold()
