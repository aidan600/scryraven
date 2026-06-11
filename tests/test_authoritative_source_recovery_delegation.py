from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.source_class_recovery import (
    _evaluate_source_class_satisfaction_with_authority_kernel,
    apply_answer_contract_source_class_recovery_gap_trigger,
    build_source_class_observability_telemetry,
    build_source_class_recovery_recommendation,
)

_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_CLASS_RECOVERY_PATH = _ROOT / "core" / "source_class_recovery.py"
_PIPELINE_ORCHESTRATOR_PATH = _ROOT / "core" / "pipeline_orchestrator.py"


def _observability(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query": "What does the example official source say?",
        "intent": "general",
        "report_type": "general_research",
        "query_type": "other",
        "core_topic": "example topic",
        "primary_entity": "Example",
        "anchor_packet": None,
        "final_top_evidence": [],
        "final_answer_source_ids": [],
    }
    base.update(overrides)
    return build_source_class_observability_telemetry(**base)


def _recommendation(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "query": "What are the current official rules for the care program?",
        "current_date": "2026-05-26",
        "intent": "general",
        "report_type": "general_research",
        "query_type": "current_events",
        "core_topic": "care program current official rules",
        "primary_entity": "care program",
        "anchor_packet": None,
        "source_tier_counts": {"secondary": 2},
        "source_domain_counts": {"analysis.example": 2},
        "top_source_domains": [{"domain": "analysis.example", "count": 2}],
        "official_evidence_found": False,
    }
    base.update(overrides)
    return build_source_class_recovery_recommendation(**base)


def _delegated_status(
    source_class: str,
    *,
    strong: int = 0,
    weak: int = 0,
    secondary_only: int = 0,
) -> tuple[dict[str, str], list[str]]:
    return _evaluate_source_class_satisfaction_with_authority_kernel(
        [source_class],
        strong_counts={source_class: strong},
        weak_counts={source_class: weak},
        secondary_only_counts={source_class: secondary_only},
    )


def test_canonical_docs_parity_through_delegated_satisfaction() -> None:
    out = _observability(
        query="Use official PostgreSQL documentation for MVCC behavior.",
        core_topic="PostgreSQL MVCC official documentation",
        primary_entity="PostgreSQL",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "PostgreSQL Documentation MVCC",
                "url": "https://www.postgresql.org/docs/current/mvcc.html",
                "text": "Official documentation reference manual for MVCC.",
                "source_tier": "official",
            }
        ],
    )

    assert out["expected_source_classes_raw"] == ["primary_source_documents"]
    assert out["source_class_satisfaction_status"] == {
        "primary_source_documents": "satisfied_strong"
    }
    assert out["source_class_gap_candidates"] == []


def test_official_current_parity_through_delegated_satisfaction() -> None:
    out = _observability(
        query="What does the agency officially say about the current advisory?",
        core_topic="agency current advisory",
        primary_entity="agency",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Official agency advisory",
                "url": "https://agency.gov/advisory",
                "text": "Official current agency advisory and guidance.",
                "source_tier": "official",
            }
        ],
    )

    assert out["source_class_satisfaction_status"] == {
        "official_current_rules": "satisfied_strong"
    }
    assert out["source_class_underfire_shadow"] is False


def test_legal_current_primary_representation_delegates_without_behavior_change() -> None:
    status, gaps = _delegated_status("legal_or_regulatory_text", strong=1)

    assert status == {"legal_or_regulatory_text": "satisfied_strong"}
    assert gaps == []


def test_ordinary_conceptual_negative_control_stays_unclassified() -> None:
    out = _observability(
        query="Explain the history of this regulatory idea, not current rules.",
        core_topic="regulatory concept history",
        primary_entity="regulatory concept",
        final_top_evidence=[
            {
                "source_id": 1,
                "title": "Conceptual background",
                "url": "https://analysis.example/background",
                "text": "A conceptual historical explanation.",
                "source_tier": "secondary",
            }
        ],
    )

    assert out["expected_source_classes_raw"] == ["none"]
    assert out["source_class_gap_candidates"] == []
    assert out["source_class_underfire_blockers"] == ["no_expected_source_class"]


def test_weak_and_no_good_evidence_remain_legacy_partial_or_unsatisfied() -> None:
    weak_status, weak_gaps = _delegated_status("official_current_rules", weak=1)
    missing_status, missing_gaps = _delegated_status("official_current_rules")

    assert weak_status == {"official_current_rules": "satisfied_weak"}
    assert weak_gaps == ["official_current_rules"]
    assert missing_status == {"official_current_rules": "unsatisfied"}
    assert missing_gaps == ["official_current_rules"]


def test_lower_tier_evidence_cannot_satisfy_stronger_obligations() -> None:
    for source_class in (
        "official_current_rules",
        "legal_or_regulatory_text",
        "primary_source_documents",
        "academic_literature",
        "sourced_numeric_values",
    ):
        status, gaps = _delegated_status(source_class, secondary_only=1)
        assert status[source_class] == "expected_but_only_secondary"
        assert gaps == [source_class]


def test_public_recommendation_helper_output_shape_and_reason_codes_are_preserved() -> None:
    out = _recommendation()

    assert list(out) == [
        "source_class_recovery_recommended",
        "source_class_recovery_shadow_mode",
        "missing_expected_source_classes",
        "source_class_recovery_reason",
        "source_class_recovery_queries",
        "source_class_recovery_query_count",
        "source_class_recovery_trigger_fields",
    ]
    assert out["missing_expected_source_classes"] == ["official_current_rules"]
    assert out["source_class_recovery_reason"] == (
        "missing_expected_source_class:official_current_rules"
    )
    assert out["source_class_recovery_shadow_mode"] is True
    assert "provider" not in out
    assert "search_depth" not in out


def test_answer_contract_gap_reason_codes_are_preserved() -> None:
    out = apply_answer_contract_source_class_recovery_gap_trigger(
        recommendation={
            "source_class_recovery_recommended": False,
            "missing_expected_source_classes": [],
            "source_class_recovery_queries": [],
            "source_class_recovery_reason": None,
        },
        answer_contract_family="legal_or_regulatory_primary_text",
        answer_contract_source_classes_missing=["legal_or_regulatory_text"],
        answer_contract_unfulfilled_items=[],
        answer_contract_partial_items=[],
        query="What does the current legal text require?",
        core_topic="current legal requirements",
        primary_entity="Legal Text",
    )

    assert out["missing_expected_source_classes"] == ["legal_or_regulatory_text"]
    assert out["source_class_recovery_reason"] == (
        "answer_contract_legal_text_gap:legal_or_regulatory_text"
    )
    assert out["source_class_recovery_shadow_mode"] is True


def test_static_guard_keeps_runtime_wiring_and_orchestrator_out_of_delegation() -> None:
    tree = ast.parse(_SOURCE_CLASS_RECOVERY_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imports.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.pipeline",
        "core.prompts",
        "core.followup",
        "core.source_class_recovery_executor",
        "core.search_providers",
        "core.db",
        "openai",
        "requests",
    }
    assert imports.isdisjoint(forbidden_imports)

    orchestrator_source = _PIPELINE_ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    assert "authoritative_source_obligations" not in orchestrator_source
