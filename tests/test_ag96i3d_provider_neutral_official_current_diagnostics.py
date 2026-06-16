from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.followup_deliberation import ProviderJobKind
from core.followup_provider_result_set_diagnostics import (
    DISCOVERY_UNCONSTRAINED,
    HARD_CORRIDOR_DOMAIN_CONSTRAINED,
    SANITIZED_RESULT_KEYS,
    build_official_current_discovery_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "core" / "followup_provider_result_set_diagnostics.py"


def _diagnostics(
    results: list[dict[str, Any]],
    *,
    provider_name: str = "fixture_provider",
    provider_job_kind: str = (
        ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value
    ),
    acquisition_mode: str = DISCOVERY_UNCONSTRAINED,
    include_domains: list[str] | None = None,
    domain_constraints: list[str] | None = None,
    authority_decision_present: bool = False,
) -> dict[str, Any]:
    return build_official_current_discovery_diagnostics(
        results,
        provider_name=provider_name,
        provider_surface_role="candidate_acquisition",
        provider_job_kind=provider_job_kind,
        acquisition_mode=acquisition_mode,
        authorized_query_ref="query.ref.ag96i3d.official.current",
        authorized_query=(
            "Find the current official rule and supporting authority for the "
            "fixture scenario."
        ),
        include_domains=include_domains,
        domain_constraints=domain_constraints,
        authority_decision_present=authority_decision_present,
    )


def test_discovery_unconstrained_refuses_source_specific_domain_constraints() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "IRS current official guidance for 2026",
                "url": "https://www.irs.gov/newsroom/current-official-guidance-2026",
            }
        ],
        include_domains=["irs.gov"],
    )

    assert diagnostics["acquisition_mode"] == "discovery_unconstrained"
    assert diagnostics["domain_constraint_status"] == (
        "invalid_unearned_domain_constraint"
    )
    assert diagnostics["authority_decision_required"] is False
    assert diagnostics["authority_decision_present"] is False
    assert diagnostics["selected_candidate_rank"] is None
    assert diagnostics["selected_candidate_domain"] is None
    assert diagnostics["bridge_only"] is True
    assert diagnostics["first_failure_layer"] == "domain_constraint_authority"
    assert diagnostics["selected_candidate_reason"] == (
        "discovery_unconstrained_refused_source_specific_domain_constraint"
    )


def test_discovery_unconstrained_selects_rank_two_official_current_candidate() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "Immigration filing explainer",
                "url": "https://legalclarity.org/uscis-filing-guide",
                "domain": "legalclarity.org",
                "snippet": "raw bridge snippet must be stripped",
                "payload": {"raw": "blocked_bridge_payload"},
            },
            {
                "title": "USCIS current filing fee rule for 2026",
                "url": "https://www.uscis.gov/forms/filing-fees/current-2026",
                "domain": "uscis.gov",
                "snippet": "raw official snippet must be stripped",
                "raw_text": "blocked official text",
            },
        ]
    )

    assert diagnostics["provider_result_count"] == 2
    assert diagnostics["sanitized_result_count"] == 2
    assert diagnostics["official_current_candidate_count"] == 1
    assert diagnostics["selected_candidate_rank"] == 2
    assert diagnostics["selected_candidate_domain"] == "uscis.gov"
    assert diagnostics["selected_candidate_source_class"] == "official_government"
    assert diagnostics["selected_candidate_reason"] == (
        "official_current_candidate_selected"
    )
    assert diagnostics["first_failure_layer"] == "none"
    assert diagnostics["bridge_only"] is False
    assert set(diagnostics["sanitized_results"][0]) == SANITIZED_RESULT_KEYS


def test_no_official_current_result_reports_lacked_candidate_and_bridge_only() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "Workplace safety checklist",
                "url": "https://driversnote.com/safety-checklist",
                "domain": "driversnote.com",
            },
            {
                "title": "Consultant summary of new workplace rules",
                "url": "https://ustax.tools/workplace-summary",
                "domain": "ustax.tools",
            },
        ]
    )

    assert diagnostics["official_current_candidate_count"] == 0
    assert diagnostics["selected_candidate_rank"] is None
    assert diagnostics["selected_candidate_domain"] is None
    assert diagnostics["selected_candidate_reason"] == (
        "provider_result_set_lacked_official_current_candidate"
    )
    assert diagnostics["first_failure_layer"] == (
        "provider_result_set_lacked_official_current_candidate"
    )
    assert diagnostics["bridge_only"] is True
    assert diagnostics["bridge_hint_domain"] == "driversnote.com"


def test_multiple_official_candidates_selects_first_and_counts_nonselected() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "Securities filing overview",
                "url": "https://example.com/securities-filing-overview",
            },
            {
                "title": "SEC current filing rule 2026",
                "url": "https://www.sec.gov/rules/current-filing-rule-2026",
                "domain": "sec.gov",
            },
            {
                "title": "FDA current final guidance 2026",
                "url": "https://www.fda.gov/regulatory-information/current-guidance-2026",
                "domain": "fda.gov",
            },
        ]
    )

    assert diagnostics["official_current_candidate_count"] == 2
    assert diagnostics["official_current_nonselected_count"] == 1
    assert diagnostics["selected_candidate_rank"] == 2
    assert diagnostics["selected_candidate_domain"] == "sec.gov"
    assert [
        item["domain"]
        for item in diagnostics["sanitized_results"]
        if item["candidate_fit_status"] == "official_current_candidate_fit"
    ] == ["sec.gov", "fda.gov"]


def test_official_but_currentness_unclear_is_not_over_upgraded() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "OSHA occupational safety topic page",
                "url": "https://www.osha.gov/safety-management",
                "domain": "osha.gov",
            }
        ]
    )

    result = diagnostics["sanitized_results"][0]
    assert result["source_class"] == "official_government"
    assert result["currentness_signal"] == "currentness_not_verified_by_diagnostic"
    assert result["candidate_fit_status"] == "official_currentness_unverified"
    assert diagnostics["official_current_candidate_count"] == 0
    assert diagnostics["selected_candidate_rank"] is None
    assert diagnostics["bridge_only"] is True


def test_scout_bridge_mode_records_hints_only_even_for_official_result() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "DOL current wage rule 2026",
                "url": "https://www.dol.gov/agencies/whd/current-wage-rule-2026",
                "domain": "dol.gov",
            }
        ],
        provider_job_kind=ProviderJobKind.SCOUT_DISAMBIGUATION.value,
    )

    assert diagnostics["official_current_candidate_count"] == 1
    assert diagnostics["selected_candidate_rank"] is None
    assert diagnostics["selected_candidate_domain"] is None
    assert diagnostics["selected_candidate_reason"] == (
        "scout_bridge_hint_recorded_not_official_current_satisfaction"
    )
    assert diagnostics["bridge_only"] is True
    assert diagnostics["bridge_hint_domain"] == "dol.gov"


def test_hard_corridor_mode_requires_explicit_authority_decision() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "IRS current official guidance for 2026",
                "url": "https://www.irs.gov/newsroom/current-official-guidance-2026",
            }
        ],
        acquisition_mode=HARD_CORRIDOR_DOMAIN_CONSTRAINED,
        domain_constraints=["irs.gov"],
        authority_decision_present=False,
    )

    assert diagnostics["domain_constraint_status"] == (
        "invalid_missing_authority_decision"
    )
    assert diagnostics["authority_decision_required"] is True
    assert diagnostics["authority_decision_present"] is False
    assert diagnostics["selected_candidate_rank"] is None
    assert diagnostics["first_failure_layer"] == "hard_corridor_authority_decision_missing"


def test_hard_corridor_mode_with_authority_decision_records_earned_constraints_only() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "IRS current official guidance for 2026",
                "url": "https://www.irs.gov/newsroom/current-official-guidance-2026",
            }
        ],
        acquisition_mode=HARD_CORRIDOR_DOMAIN_CONSTRAINED,
        domain_constraints=["irs.gov"],
        authority_decision_present=True,
    )

    assert diagnostics["domain_constraint_status"] == "earned_domain_constraint"
    assert diagnostics["domain_constraints"] == ["irs.gov"]
    assert diagnostics["authority_decision_required"] is True
    assert diagnostics["authority_decision_present"] is True
    assert diagnostics["selected_candidate_rank"] == 1
    assert diagnostics["selected_candidate_domain"] == "irs.gov"
    assert diagnostics["raw_private_payload_redaction_posture"][
        "raw_provider_payloads_retained"
    ] is False


def test_diagnostics_contract_includes_required_fields() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "USCIS current filing fee rule for 2026",
                "url": "https://www.uscis.gov/forms/filing-fees/current-2026",
            }
        ],
        provider_name="generic_search_fixture",
    )

    for key in (
        "provider_result_count",
        "sanitized_result_count",
        "official_current_candidate_count",
        "selected_candidate_rank",
        "selected_candidate_domain",
        "selected_candidate_reason",
        "first_failure_layer",
        "acquisition_mode",
    ):
        assert key in diagnostics
    assert diagnostics["provider_name"] == "generic_search_fixture"
    assert diagnostics["provider_surface_role"] == "candidate_acquisition"
    assert diagnostics["provider_job_kind"] == (
        ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value
    )


def test_diagnostics_exclude_raw_private_payload_surfaces() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "FDA current final guidance 2026",
                "url": "https://www.fda.gov/regulatory-information/current-guidance-2026",
                "snippet": "blocked raw snippet",
                "raw_content": "blocked raw content",
                "raw_page_text": "blocked raw page text",
                "prompt": "blocked raw prompt",
                "model_output": "blocked model output",
                "payload": {"private_payload_marker": "blocked payload"},
                "env": "blocked env value",
                "db_row": "blocked db row",
                "cache_row": "blocked cache row",
                "private_log": "blocked private log",
                "full_trace": "blocked full trace",
            }
        ]
    )

    serialized = json.dumps(diagnostics, sort_keys=True)
    for forbidden in (
        "raw_content",
        "blocked raw snippet",
        "blocked raw page text",
        "blocked raw prompt",
        "blocked model output",
        "blocked payload",
        "blocked env value",
        "blocked db row",
        "blocked cache row",
        "blocked private log",
        "blocked full trace",
    ):
        assert forbidden not in serialized


def test_static_guard_no_provider_direct_calls_or_imports_added() -> None:
    source = MODULE.read_text(encoding="utf-8")
    imports = _imports(MODULE)
    forbidden_imports = {
        "dotenv",
        "requests",
        "openai",
        "core.search_providers",
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
        "core.followup_final_answer_packet_runtime",
        "core.followup_provider_job_live_validation_runtime",
        "urllib.request",
    }
    assert imports.isdisjoint(forbidden_imports)
    for forbidden in (
        "brave_reconnaissance",
        "tavily",
        "linkup",
        "exa",
        "OPENAI",
        "BRAVE_API_KEY",
        "load_dotenv",
        "urlopen",
        "includeDomains = [\"irs.gov\"]",
        "if provider_name == \"brave",
        "if domain == \"irs.gov\"",
    ):
        assert forbidden not in source


def test_static_guard_no_pipeline_orchestrator_domain_logic() -> None:
    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )

    assert "followup_provider_result_set_diagnostics" not in pipeline_source
    assert "hard_corridor_domain_constrained" not in pipeline_source
    assert "provider_result_set_lacked_official_current_candidate" not in pipeline_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
