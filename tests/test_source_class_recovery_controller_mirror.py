from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.run_controller import RunController
from core.source_class_recovery import build_source_class_recovery_recommendation
from core.source_class_recovery_controller_mirror import (
    record_source_class_recovery_recommendation,
)

_ROOT = Path(__file__).resolve().parents[1]
_MIRROR_HELPER_PATH = _ROOT / "core" / "source_class_recovery_controller_mirror.py"


def _source_class_evidence_signals() -> dict[str, Any]:
    return {
        "source_tier_counts": {"secondary": 2, "unknown": 1},
        "source_domain_counts": {"regionalnews.example": 2, "analysis.example": 1},
        "top_source_domains": [{"domain": "regionalnews.example", "count": 2}],
        "unique_source_domain_count": 2,
        "on_domain_source_count": 0,
        "off_domain_source_count": 3,
        "official_evidence_found": False,
        "community_signal_found": False,
        "low_trust_sources_found": False,
        "pollution_detected": False,
    }


def _official_current_rules_missing_telemetry() -> dict[str, Any]:
    return build_source_class_recovery_recommendation(
        query="What are the current eligibility requirements and official rules for the care program?",
        current_date="2026-05-18",
        intent="general",
        report_type="general_research",
        query_type="other",
        core_topic="care program current eligibility requirements",
        primary_entity="Care Program",
        anchor_packet={},
        source_tier_counts={"secondary": 2, "unknown": 1},
        source_domain_counts={"regionalnews.example": 2, "analysis.example": 1},
        top_source_domains=[{"domain": "regionalnews.example", "count": 2}],
        official_evidence_found=False,
    )


def _latest_news_no_recovery_telemetry() -> dict[str, Any]:
    return build_source_class_recovery_recommendation(
        query="What is the latest news about the governor race?",
        current_date="2026-05-18",
        intent="news",
        report_type="general_research",
        query_type="news",
        core_topic="governor race latest news",
        primary_entity="governor race",
        anchor_packet={},
        source_tier_counts={"secondary": 3},
        source_domain_counts={"regionalnews.example": 2, "politics.example": 1},
        top_source_domains=[{"domain": "regionalnews.example", "count": 2}],
        official_evidence_found=False,
    )


def test_source_class_recovery_controller_mirror_records_passive_decision_and_action() -> None:
    telemetry = _official_current_rules_missing_telemetry()
    controller = RunController()

    returned = record_source_class_recovery_recommendation(
        controller,
        source_class_recovery_telemetry=telemetry,
        source_class_evidence_signals=_source_class_evidence_signals(),
    )

    ledger = controller.snapshot_ledger()
    decision = ledger["decision_records"][0]
    action = ledger["retrieval_actions"][0]

    assert returned is controller
    assert len(ledger["decision_records"]) == 1
    assert decision["name"] == "source_class_recovery"
    assert decision["active"] is False
    assert decision["shadow"] is True
    assert decision["reason"] == telemetry["source_class_recovery_reason"]
    assert decision["signals"]["missing_expected_source_classes"] == [
        "official_current_rules"
    ]
    assert "query" in decision["signals"]["source_class_recovery_trigger_fields"]
    assert decision["signals"]["source_tier_counts"] == {
        "secondary": 2,
        "unknown": 1,
    }
    assert decision["signals"]["official_evidence_found"] is False

    assert len(ledger["retrieval_actions"]) == 1
    assert action["name"] == "source_class_recovery_recommendation"
    assert action["active"] is False
    assert action["shadow"] is True
    assert action["provider"] is None
    assert action["provider_role"] is None
    assert action["search_depth"] is None
    assert action["results_per_query"] is None
    assert action["queries"] == telemetry["source_class_recovery_queries"]
    assert decision["recommended_actions"][0]["queries"] == action["queries"]


def test_source_class_recovery_controller_mirror_no_recovery_has_no_action() -> None:
    telemetry = _latest_news_no_recovery_telemetry()
    controller = RunController()

    record_source_class_recovery_recommendation(
        controller,
        source_class_recovery_telemetry=telemetry,
        source_class_evidence_signals=_source_class_evidence_signals(),
    )

    ledger = controller.snapshot_ledger()
    decision = ledger["decision_records"][0]

    assert len(ledger["decision_records"]) == 1
    assert ledger["retrieval_actions"] == []
    assert decision["name"] == "source_class_recovery"
    assert decision["active"] is False
    assert decision["shadow"] is True
    assert decision["reason"] is None
    assert decision["signals"]["missing_expected_source_classes"] == []
    assert decision["recommended_actions"] == []


def test_source_class_recovery_controller_mirror_static_import_guard() -> None:
    tree = ast.parse(_MIRROR_HELPER_PATH.read_text(encoding="utf-8"))
    forbidden_import_prefixes = (
        "streamlit",
        "openai",
        "anthropic",
        "requests",
        "httpx",
        "sqlite3",
        "core.llm",
        "core.prompts",
        "core.search_providers",
        "core.db",
        "core.storage",
        "core.run_logging",
        "core.pipeline",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.routing",
        "core.scout",
        "core.weak_corpus_recovery",
    )
    forbidden_function_prefixes = (
        "decide_",
        "should_",
        "run_",
        "recover_",
        "select_",
    )

    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

    violations = [
        name
        for name in imported_names
        for prefix in forbidden_import_prefixes
        if name == prefix or name.startswith(prefix + ".")
    ]
    active_function_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith(forbidden_function_prefixes)
    ]

    assert violations == []
    assert active_function_names == []
