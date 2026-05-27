from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.official_canonical_recovery_execution_admission import (
    build_official_canonical_recovery_execution_admission,
)
from core.official_canonical_recovery_query_acquisition import (
    apply_official_canonical_recovery_query_acquisition,
)
from core.official_source_obligation_bridge import (
    apply_official_source_obligation_bridge,
)

_ROOT = Path(__file__).resolve().parents[1]
_ADAPTER_PATHS = (
    _ROOT / "core" / "official_source_obligation_bridge.py",
    _ROOT / "core" / "official_canonical_recovery_query_acquisition.py",
    _ROOT / "core" / "official_canonical_recovery_execution_admission.py",
)
_PIPELINE_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _query_acquisition(
    trace: dict[str, Any],
    recommendation: dict[str, Any],
    *,
    existing_blockers: tuple[str, ...] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = apply_official_canonical_recovery_query_acquisition(
        recommendation=recommendation,
        runtime_trace=trace,
        existing_blockers=existing_blockers,
    )
    return result.recommendation, result.trace[
        "OfficialCanonicalRecoveryQueryAcquisition"
    ]


def _bridge(
    trace: dict[str, Any],
    recommendation: dict[str, Any],
    *,
    existing_blockers: tuple[str, ...] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = apply_official_source_obligation_bridge(
        recommendation=recommendation,
        runtime_trace=trace,
        existing_blockers=existing_blockers,
    )
    return result.recommendation, result.trace["OfficialSourceObligationBridge"]


def _admission(
    trace: dict[str, Any],
    recommendation: dict[str, Any],
    *,
    existing_blockers: tuple[str, ...] = (),
) -> tuple[bool, dict[str, Any]]:
    result = build_official_canonical_recovery_execution_admission(
        recommendation=recommendation,
        runtime_trace=trace,
        existing_blockers=existing_blockers,
        prior_recovery_attempt_count=0,
        max_recovery_attempts=1,
    )
    return (
        result.source_class_recovery_execution_admitted,
        result.trace["OfficialCanonicalRecoveryExecutionAdmission"],
    )


def _official_recommendation(source_class: str) -> dict[str, Any]:
    return {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": [source_class],
        "source_class_recovery_queries": [],
    }


def test_ag65d_irs_official_current_requirement_keeps_existing_query_variants() -> None:
    recommendation, trace = _query_acquisition(
        {
            "query_preview": (
                "What is the IRS 2026 standard mileage rate for business use?"
            ),
            "query_type": "official_current_status",
        },
        _official_recommendation("official_current_rules"),
    )

    assert trace["required_source_classes"] == ["official_current_rules"]
    assert trace["generic_query_intent"] == "official_current_source"
    assert recommendation["source_class_recovery_queries"] == [
        "IRS 2026 standard mileage rate business official notice revenue procedure",
        (
            "official current source What is the IRS 2026 standard mileage "
            "rate for business use?"
        ),
    ]


def test_ag65d_ssa_official_current_requirement_keeps_existing_query_variants() -> None:
    recommendation, trace = _query_acquisition(
        {
            "query_preview": (
                "What is the 2026 Social Security taxable maximum wage base?"
            ),
            "query_type": "official_current_status",
        },
        _official_recommendation("official_current_rules"),
    )

    assert trace["required_source_classes"] == ["official_current_rules"]
    assert trace["generic_query_intent"] == "official_current_source"
    assert recommendation["source_class_recovery_queries"] == [
        (
            "SSA 2026 Social Security taxable maximum wage base official "
            "contribution benefit base"
        ),
        (
            "official current source What is the 2026 Social Security taxable "
            "maximum wage base?"
        ),
    ]


def test_ag65d_federal_agency_rule_requirement_keeps_existing_query_variants() -> None:
    recommendation, trace = _query_acquisition(
        {
            "query_preview": (
                "What is the current official eligibility threshold status "
                "rule for a federal benefit in 2026?"
            ),
            "query_type": "official_current_status",
        },
        _official_recommendation("official_current_rules"),
    )

    assert trace["required_source_classes"] == ["official_current_rules"]
    assert trace["generic_query_intent"] == "official_current_source"
    assert recommendation["source_class_recovery_queries"] == [
        (
            "federal agency official current eligibility threshold status rule "
            "What is the current official eligibility threshold status rule "
            "for a federal benefit in 2026?"
        ),
        (
            "official current source What is the current official eligibility "
            "threshold status rule for a federal benefit in 2026?"
        ),
    ]


def test_ag65d_canonical_project_doc_requirement_keeps_existing_query_variants() -> None:
    recommendation, trace = _query_acquisition(
        {
            "query_preview": (
                "Explain how PostgreSQL MVCC works in a database and its "
                "concurrency tradeoff."
            ),
            "query_type": "technical_reference",
        },
        _official_recommendation("primary_source_documents"),
    )

    assert trace["required_source_classes"] == ["primary_source_documents"]
    assert trace["generic_query_intent"] == "canonical_documentation"
    assert recommendation["source_class_recovery_queries"] == [
        (
            "official documentation Explain how PostgreSQL MVCC works in a "
            "database and its concurrency tradeoff."
        ),
        (
            "reference documentation Explain how PostgreSQL MVCC works in a "
            "database and its concurrency tradeoff."
        ),
    ]


def test_ag65d_bridge_output_shape_and_reason_codes_are_preserved() -> None:
    recommendation, trace = _bridge(
        {
            "query_preview": (
                "What is the current official eligibility rule for a federal "
                "benefit in 2026?"
            ),
            "query_type": "official_current_status",
        },
        {
            "source_class_recovery_recommended": False,
            "missing_expected_source_classes": [],
            "source_class_recovery_queries": [],
        },
    )

    assert recommendation == {
        "source_class_recovery_recommended": True,
        "missing_expected_source_classes": ["official_current_rules"],
        "source_class_recovery_queries": [],
        "source_class_recovery_shadow_mode": True,
        "source_class_recovery_reason": (
            "official_source_obligation_bridge:official_current_rules"
        ),
        "source_class_recovery_trigger_fields": [
            "official_source_obligation_trace",
            "official_source_obligation_bridge",
        ],
        "source_class_recovery_query_count": 0,
    }
    assert trace["bridge_used"] is True
    assert trace["bridge_required_source_classes"] == ["official_current_rules"]
    assert trace["bridge_added_missing_source_classes"] == ["official_current_rules"]


def test_ag65d_query_acquisition_status_and_reason_codes_are_preserved() -> None:
    recommendation, trace = _query_acquisition(
        {
            "query_preview": "Explain how database MVCC works.",
            "source_class_satisfaction_status": {
                "primary_source_documents": "satisfied_strong"
            },
        },
        _official_recommendation("primary_source_documents"),
    )

    assert recommendation == _official_recommendation("primary_source_documents")
    assert trace["acquisition_repair_used"] is False
    assert trace["acquisition_repair_skip_reason"] == "existing_source_class_satisfied"


def test_ag65d_admission_status_and_reason_codes_are_preserved() -> None:
    admitted, trace = _admission(
        {
            "query_preview": "Explain how PostgreSQL MVCC works in a database.",
            "query_type": "technical_reference",
        },
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [
                "canonical documentation PostgreSQL MVCC"
            ],
            "source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:gap"
            ),
        },
    )

    assert admitted is True
    assert trace["admission_used"] is True
    assert trace["admission_skip_reason"] is None
    assert trace["required_source_classes"] == ["primary_source_documents"]
    assert trace["unsatisfied_required_source_classes"] == [
        "primary_source_documents"
    ]


def test_ag65d_lower_tier_evidence_does_not_satisfy_official_current_authority() -> None:
    recommendation, bridge = _bridge(
        {
            "query_preview": (
                "What is the current official eligibility rule for a federal "
                "benefit in 2026?"
            ),
            "query_type": "official_current_status",
            "source_class_satisfaction_status": {
                "official_current_rules": "expected_but_only_secondary"
            },
        },
        {"source_class_recovery_recommended": False},
    )

    assert bridge["bridge_used"] is True
    assert bridge["bridge_satisfied_source_classes"] == []
    assert bridge["bridge_required_source_classes"] == ["official_current_rules"]
    assert recommendation["missing_expected_source_classes"] == [
        "official_current_rules"
    ]


def test_ag65d_lower_tier_evidence_does_not_satisfy_canonical_doc_authority() -> None:
    admitted, trace = _admission(
        {
            "query_preview": "Explain how PostgreSQL MVCC works in a database.",
            "query_type": "technical_reference",
            "source_class_satisfaction_status": {
                "primary_source_documents": "expected_but_only_secondary"
            },
        },
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [
                "canonical documentation PostgreSQL MVCC"
            ],
            "source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:gap"
            ),
        },
    )

    assert admitted is True
    assert trace["unsatisfied_required_source_classes"] == [
        "primary_source_documents"
    ]


def test_ag65d_admission_fails_closed_when_requirement_missing_or_blocked() -> None:
    missing_requirement_admitted, missing_requirement_trace = _admission(
        {},
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": [],
            "source_class_recovery_queries": [
                "canonical documentation PostgreSQL MVCC"
            ],
            "source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:gap"
            ),
        },
    )
    blocked_admitted, blocked_trace = _admission(
        {
            "query_preview": "Explain how PostgreSQL MVCC works in a database.",
            "query_type": "technical_reference",
        },
        {
            "source_class_recovery_recommended": True,
            "missing_expected_source_classes": ["primary_source_documents"],
            "source_class_recovery_queries": [
                "canonical documentation PostgreSQL MVCC"
            ],
            "source_class_recovery_reason": (
                "official_canonical_recovery_query_acquisition:gap"
            ),
        },
        existing_blockers=("terminal_stop_approved",),
    )

    assert missing_requirement_admitted is False
    assert missing_requirement_trace["admission_skip_reason"] == (
        "obligation_unknown"
    )
    assert blocked_admitted is False
    assert blocked_trace["admission_skip_reason"] == "existing_runtime_blocker"
    assert blocked_trace["admission_blockers"] == ["terminal_stop_approved"]


def test_ag65d_query_previews_and_public_helper_fields_stay_stable() -> None:
    recommendation, trace = _query_acquisition(
        {
            "query_preview": "Explain how database WAL mode works.",
            "query_type": "technical_reference",
        },
        _official_recommendation("primary_source_documents"),
    )

    assert set(recommendation) == {
        "source_class_recovery_recommended",
        "source_class_recovery_shadow_mode",
        "missing_expected_source_classes",
        "source_class_recovery_queries",
        "source_class_recovery_query_count",
        "source_class_recovery_reason",
        "source_class_recovery_trigger_fields",
    }
    assert trace["added_recovery_query_previews"] == [
        "official documentation Explain how database WAL mode works.",
        "reference documentation Explain how database WAL mode works.",
    ]
    assert trace["added_recovery_query_count"] == 2


def test_ag65d_static_guard_kernel_only_enters_adapter_layer() -> None:
    forbidden_imports = {
        "core.answer_contract_runtime_handoff",
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
    for path in _ADAPTER_PATHS:
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
        assert "core.authoritative_source_obligations" in imported
        assert imported.isdisjoint(forbidden_imports)

        source = path.read_text(encoding="utf-8").casefold()
        for forbidden in (
            "select_providers",
            "choose_supplemental_search_depth",
            "ranking_policy",
            "author_prompt",
            "build_author_prompt",
            "scrutineer_policy",
            "followup_prompt",
        ):
            assert forbidden not in source

    pipeline_source = _PIPELINE_PATH.read_text(encoding="utf-8")
    assert "authoritative_source_obligations" not in pipeline_source
