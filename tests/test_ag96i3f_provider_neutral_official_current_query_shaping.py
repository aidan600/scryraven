from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.followup_deliberation import ProviderJobKind
from core.followup_official_current_query_shaping import (
    DISCOVERY_UNCONSTRAINED,
    OFFICIAL_CURRENT_ARTIFACT_DISCOVERY,
    SCOUT_HYPOTHESIS_DISAMBIGUATION,
    build_official_current_query_shaping_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "core" / "followup_official_current_query_shaping.py"


def _packet(
    query: str,
    *,
    provider_job_kind: str = (
        ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value
    ),
    **kwargs: Any,
) -> dict[str, Any]:
    return build_official_current_query_shaping_diagnostics(
        authorized_query=query,
        provider_job_kind=provider_job_kind,
        **kwargs,
    )


def test_irs_scoped_current_query_produces_bounded_artifact_variants() -> None:
    packet = _packet(
        "What is the current IRS standard mileage rate for business use of a "
        "car in 2026, and what official source supports it?"
    )

    assert packet["query_shape_mode"] == OFFICIAL_CURRENT_ARTIFACT_DISCOVERY
    assert packet["acquisition_mode"] == DISCOVERY_UNCONSTRAINED
    assert 1 <= packet["query_variant_count"] <= 4
    assert packet["live_call_authorized"] is False
    assert packet["provider_called"] is False
    joined = " ".join(packet["query_variants"]).casefold()
    for term in ("irs", "2026", "standard mileage rates", "business use", "car"):
        assert term in joined
    for artifact in ("notice", "announcement", "newsroom"):
        assert artifact in joined


def test_irs_variants_do_not_use_domain_corridors_or_invent_answer_values() -> None:
    packet = _packet(
        "What is the current IRS standard mileage rate for business use of a "
        "car in 2026?"
    )
    serialized_variants = json.dumps(packet["query_variants"]).casefold()

    for forbidden in ("site:", "includedomains", "irs.gov", "72.5"):
        assert forbidden not in serialized_variants
    assert packet["prohibited_constraints"]["source_domain_filters_used"] is False
    assert packet["prohibited_constraints"]["hardcoded_source_resolver_used"] is False
    assert packet["domain_constraint_status"] == "not_present"


def test_uscis_fee_query_uses_artifact_terms_without_domain_hardcoding() -> None:
    packet = _packet("What is the current USCIS filing fee for Form I-765 in 2026?")
    joined = " ".join(packet["query_variants"]).casefold()

    for term in ("uscis", "2026", "filing", "fee", "form"):
        assert term in joined
    for artifact in ("fee schedule", "filing fee", "instructions"):
        assert artifact in joined
    assert "uscis.gov" not in joined


def test_osha_dol_rule_query_uses_rule_guidance_and_federal_register_terms() -> None:
    packet = _packet("What is the current OSHA DOL worker safety final rule?")
    joined = " ".join(packet["query_variants"]).casefold()

    for term in ("osha", "dol", "rule", "safety"):
        assert term in joined
    for artifact in ("guidance", "federal register", "final rule"):
        assert artifact in joined
    assert ".gov" not in joined


def test_sec_rule_filing_query_uses_release_and_disclosure_artifacts() -> None:
    packet = _packet("Find the current SEC climate disclosure filing rule.")
    joined = " ".join(packet["query_variants"]).casefold()

    for term in ("sec", "disclosure", "filing", "rule"):
        assert term in joined
    for artifact in ("final rule", "release", "disclosure"):
        assert artifact in joined
    assert "sec.gov" not in joined


def test_fda_recall_safety_query_uses_recall_safety_artifacts_without_domain() -> None:
    packet = _packet("Find the current FDA recall safety alert for 2026.")
    joined = " ".join(packet["query_variants"]).casefold()

    for term in ("fda", "recall", "safety", "2026"):
        assert term in joined
    for artifact in ("recall notice", "safety alert", "enforcement report"):
        assert artifact in joined
    assert "fda.gov" not in joined


def test_ambiguous_poe_patch_produces_hypotheses_without_resolved_subject() -> None:
    packet = _packet("latest PoE patch")

    assert packet["query_shape_mode"] == SCOUT_HYPOTHESIS_DISAMBIGUATION
    assert packet["canonical_subject_status"] == "unresolved"
    assert len(packet["candidate_interpretations"]) >= 4
    joined = " ".join(packet["candidate_interpretations"])
    assert "Path of Exile" in joined
    assert "Power over Ethernet" in joined
    assert packet["query_variant_count"] >= 3


def test_ambiguous_driving_reimbursement_does_not_hard_resolve_to_irs() -> None:
    packet = _packet("funny reimbursement thing for driving")

    assert packet["query_shape_mode"] == SCOUT_HYPOTHESIS_DISAMBIGUATION
    assert packet["canonical_subject_status"] == "unresolved"
    hypotheses = " ".join(packet["candidate_interpretations"]).casefold()
    for term in ("employer", "tax", "government", "vehicle"):
        assert term in hypotheses
    assert "irs" not in hypotheses


def test_caller_resolved_canonical_subject_gets_official_current_shaping() -> None:
    packet = _packet(
        "latest PoE patch",
        canonical_subject="Path of Exile latest patch notes",
        canonical_subject_status="resolved_by_caller",
    )
    joined = " ".join(packet["query_variants"]).casefold()

    assert packet["query_shape_mode"] == OFFICIAL_CURRENT_ARTIFACT_DISCOVERY
    assert packet["canonical_subject_status"] == "resolved_by_caller"
    assert "path" in joined
    assert "exile" in joined
    assert "patch notes" in joined
    assert "release notes" in joined


def test_discovery_unconstrained_marks_source_specific_constraints_invalid() -> None:
    packet = _packet(
        "What is the current IRS standard mileage rate for business use of a car?",
        include_domains=["irs.gov"],
    )

    assert packet["domain_constraint_status"] == "invalid_unearned_domain_constraint"
    assert packet["query_variant_count"] == 0
    assert packet["query_variants"] == []
    assert packet["provider_called"] is False
    assert packet["live_call_authorized"] is False


def test_static_guard_no_provider_imports_or_calls() -> None:
    source = MODULE.read_text(encoding="utf-8")
    imports = _imports(MODULE)
    forbidden_imports = {
        "dotenv",
        "requests",
        "openai",
        "core.search_providers",
        "core.pipeline_orchestrator",
        "core.followup_provider_job_live_validation_runtime",
        "urllib.request",
    }
    assert imports.isdisjoint(forbidden_imports)
    for forbidden in (
        "brave_reconnaissance",
        "search_web_results",
        "search_linkup_results",
        "TAVILY_API_KEY",
        "BRAVE_API_KEY",
        "LINKUP_API_KEY",
        "load_dotenv",
        "urlopen",
        "if domain ==",
    ):
        assert forbidden not in source


def test_static_guard_no_pipeline_orchestrator_domain_logic() -> None:
    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )

    assert "followup_official_current_query_shaping" not in pipeline_source
    assert "official_current_artifact_discovery" not in pipeline_source
    assert "scout_hypothesis_disambiguation" not in pipeline_source


def test_static_guard_no_author_citation_or_product_imports() -> None:
    imports = _imports(MODULE)
    forbidden_imports = {
        "core.author_execution_runtime",
        "core.citation_source_handoff_contract",
        "core.followup_final_answer_packet_runtime",
        "core.final_answer_packet",
        "core.evidence_ledger",
        "core.pipeline_orchestrator",
    }
    assert imports.isdisjoint(forbidden_imports)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
