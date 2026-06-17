from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from core.followup_deliberation import ProviderJobKind
from core.followup_provider_result_set_diagnostics import (
    DISCOVERY_UNCONSTRAINED,
    build_official_current_discovery_diagnostics,
    sanitize_result_set_diagnostics,
)
from core.followup_scout_acquisition_handoff import (
    BRIDGE_ONLY_NO_OFFICIAL_CANDIDATE,
    FETCH_READ_CURRENTNESS_VERIFICATION,
    OFFICIAL_CANDIDATE_CURRENTNESS_UNVERIFIED,
    OFFICIAL_CURRENT_VERIFIED_BY_DIAGNOSTIC,
    build_scout_to_acquisition_handoff_diagnostics,
)
from core.followup_search_freshness_policy import (
    build_search_freshness_policy_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_MODULE = ROOT / "core" / "followup_scout_acquisition_handoff.py"
SCRIPT = ROOT / "scripts" / "ag96i3e_brokered_provider_neutral_discovery_validation.py"


def test_serper_like_rank_one_irs_official_unverified_result_becomes_verification_candidate() -> None:
    handoff = _serper_irs_handoff()

    assert handoff["scout_result_outcome"] == OFFICIAL_CANDIDATE_CURRENTNESS_UNVERIFIED
    assert handoff["verification_candidate_count"] == 1
    assert handoff["best_verification_candidate_rank"] == 1
    assert handoff["best_verification_candidate_domain"] == "irs.gov"
    assert handoff["best_verification_candidate_url"] == (
        "https://www.irs.gov/tax-professionals/standard-mileage-rates"
    )
    assert handoff["recommended_next_step"] == FETCH_READ_CURRENTNESS_VERIFICATION
    assert handoff["stop_more_scout_spending_recommended"] is True
    assert handoff["handoff_priority"] == "high"


def test_serper_like_candidate_carries_freshness_policy_context() -> None:
    handoff = _serper_irs_handoff()
    candidate = handoff["verification_candidates"][0]

    assert candidate["freshness_intent"] == "known_year"
    assert candidate["provider_freshness_policy"] == "omit_provider_freshness_filter"
    assert candidate["over_narrow_recent_window_forbidden"] is True
    assert candidate["freshness_window"] == "known_year_or_broad"
    assert "known-year official/current artifacts" in candidate["freshness_rationale"]


def test_verification_candidates_are_not_final_evidence_or_citation_eligible() -> None:
    handoff = _serper_irs_handoff()
    candidate = handoff["verification_candidates"][0]

    assert candidate["final_evidence"] is False
    assert candidate["citation_eligible"] is False
    assert handoff["evidence_boundary"]["verification_candidates_are_final_evidence"] is False
    assert (
        handoff["evidence_boundary"]["verification_candidates_are_citation_eligible"]
        is False
    )


def test_bridge_only_fixture_produces_no_verification_candidates() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "IRS Raises Business Mileage Rate for 2026 - Brady Ware",
                "url": "https://bradyware.com/irs-raises-business-mileage-rate/",
                "domain": "bradyware.com",
            }
        ]
    )

    handoff = build_scout_to_acquisition_handoff_diagnostics(
        provider_result_set_diagnostics=diagnostics,
        freshness_policy_diagnostics=_freshness_policy(),
        authorized_query=_IRS_QUERY,
        provider_name="serper",
        provider_surface_role="candidate_acquisition",
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
    )

    assert handoff["scout_result_outcome"] == BRIDGE_ONLY_NO_OFFICIAL_CANDIDATE
    assert handoff["verification_candidate_count"] == 0
    assert handoff["verification_candidates"] == []
    assert handoff["recommended_next_step"] == "no_verified_official_handoff"
    assert handoff["stop_more_scout_spending_recommended"] is False


def test_multiple_official_unverified_candidates_are_bounded_and_sorted_by_rank() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "Official unverified third",
                "url": "https://www.dol.gov/rates",
                "domain": "dol.gov",
                "source_tier": "official",
                "source_class": "official_government",
                "currentness_signal": "currentness_not_verified_by_diagnostic",
            },
            {
                "title": "Official unverified first",
                "url": "https://www.irs.gov/rates",
                "domain": "irs.gov",
                "source_tier": "official",
                "source_class": "official_government",
                "currentness_signal": "currentness_not_verified_by_diagnostic",
            },
            {
                "title": "Official unverified second",
                "url": "https://www.ftc.gov/rates",
                "domain": "ftc.gov",
                "source_tier": "official",
                "source_class": "official_government",
                "currentness_signal": "currentness_not_verified_by_diagnostic",
            },
        ]
    )

    handoff = build_scout_to_acquisition_handoff_diagnostics(
        provider_result_set_diagnostics=diagnostics,
        freshness_policy_diagnostics=_freshness_policy(),
        max_verification_candidates=2,
    )

    assert handoff["verification_candidate_count"] == 2
    assert [candidate["rank"] for candidate in handoff["verification_candidates"]] == [
        1,
        2,
    ]
    assert [candidate["domain"] for candidate in handoff["verification_candidates"]] == [
        "dol.gov",
        "irs.gov",
    ]


def test_existing_official_current_candidate_is_not_downgraded_to_unverified() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "IRS current official notice 2026",
                "url": "https://www.irs.gov/newsroom/current-notice-2026",
                "domain": "irs.gov",
                "source_tier": "official",
                "source_class": "official_government",
                "currentness_signal": "current_candidate_signal",
            }
        ]
    )

    handoff = build_scout_to_acquisition_handoff_diagnostics(
        provider_result_set_diagnostics=diagnostics,
        freshness_policy_diagnostics=_freshness_policy(),
    )

    assert handoff["scout_result_outcome"] == OFFICIAL_CURRENT_VERIFIED_BY_DIAGNOSTIC
    assert handoff["verification_candidates"][0]["candidate_fit_status"] == (
        "official_current_candidate_fit"
    )


def test_ag96i3e_build_validation_packet_includes_handoff_diagnostics() -> None:
    runner = _load_runner_module()

    packet = runner.build_validation_packet(
        provider="serper",
        query=_IRS_QUERY,
        job_id="ag96i3i-serper-irs-official-unverified",
        max_results=5,
        raw_results=_SERPER_IRS_RESULTS,
        provider_search_call_count=1,
        freshness_policy_diagnostics=_freshness_policy(),
    )

    handoff = packet["scout_to_acquisition_handoff_diagnostics"]
    assert handoff["schema_version"] == (
        "ag96i3i_scout_to_acquisition_handoff_diagnostics_v1"
    )
    assert handoff["scout_result_outcome"] == OFFICIAL_CANDIDATE_CURRENTNESS_UNVERIFIED
    assert handoff["best_verification_candidate_domain"] == "irs.gov"


def test_ag96i3e_provider_result_set_diagnostics_shape_remains_backward_compatible() -> None:
    runner = _load_runner_module()

    packet = runner.build_validation_packet(
        provider="serper",
        query=_IRS_QUERY,
        job_id="ag96i3i-serper-irs-official-unverified",
        max_results=5,
        raw_results=_SERPER_IRS_RESULTS,
        provider_search_call_count=1,
        freshness_policy_diagnostics=_freshness_policy(),
    )
    diagnostics = packet["provider_result_set_diagnostics"]

    assert diagnostics["schema_version"] == (
        "ag96i3d_provider_neutral_result_set_diagnostics_v1"
    )
    assert diagnostics["record_type"] == (
        "provider_neutral_official_current_result_set_diagnostics"
    )
    assert diagnostics["official_current_candidate_count"] == 0
    assert diagnostics["first_failure_layer"] == (
        "provider_result_set_lacked_official_current_candidate"
    )
    assert diagnostics["sanitized_results"][0]["candidate_fit_status"] == (
        "official_currentness_unverified"
    )


def test_handoff_retains_no_raw_snippets_payloads_page_text_or_env_values() -> None:
    diagnostics = _diagnostics(
        [
            {
                "title": "Standard mileage rates | Internal Revenue Service",
                "url": "https://www.irs.gov/tax-professionals/standard-mileage-rates",
                "domain": "irs.gov",
                "source_tier": "official",
                "source_class": "official_government",
                "currentness_signal": "currentness_not_verified_by_diagnostic",
                "snippet": "blocked raw snippet marker",
                "raw_provider_payload": {"payload_marker": "blocked raw payload marker"},
                "page_text": "blocked page text marker",
                "env_value": "blocked env marker",
            }
        ]
    )

    handoff = build_scout_to_acquisition_handoff_diagnostics(
        provider_result_set_diagnostics=diagnostics,
        freshness_policy_diagnostics=_freshness_policy(),
    )
    serialized = json.dumps(handoff, sort_keys=True)

    for forbidden in (
        "blocked raw snippet marker",
        "blocked raw payload marker",
        "blocked page text marker",
        "blocked env marker",
    ):
        assert forbidden not in serialized
    redaction = handoff["raw_private_payload_redaction_posture"]
    assert redaction["raw_provider_payloads_retained"] is False
    assert redaction["raw_snippets_retained"] is False
    assert redaction["raw_page_text_retained"] is False
    assert redaction["env_values_retained"] is False


def test_static_guard_no_provider_imports_or_calls_in_handoff_helper() -> None:
    source = HANDOFF_MODULE.read_text(encoding="utf-8")
    imports = _imports(HANDOFF_MODULE)
    forbidden_imports = {
        "core.search_providers",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
    }

    assert imports.isdisjoint(forbidden_imports)
    for forbidden in (
        "search_scout_results",
        "_dispatch_provider",
        "requests.",
        "httpx.",
        "urlopen",
        ".read(",
        "load_dotenv",
        "os.environ",
    ):
        assert forbidden not in source


def test_static_guard_no_pipeline_orchestrator_domain_logic() -> None:
    source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")

    assert "followup_scout_acquisition_handoff" not in source
    assert "scout_to_acquisition_handoff_diagnostics" not in source
    assert "ag96i3i" not in source.casefold()


def test_static_guard_no_author_citation_or_product_imports() -> None:
    imports = _imports(HANDOFF_MODULE)
    forbidden_imports = {
        "core.author_execution_runtime",
        "core.citation_source_handoff_contract",
        "core.followup_final_answer_packet_runtime",
        "core.final_answer_packet",
        "core.evidence_ledger",
        "core.pipeline_orchestrator",
    }

    assert imports.isdisjoint(forbidden_imports)


_IRS_QUERY = "IRS 2026 standard mileage rates business use car notice announcement"
_SERPER_IRS_RESULTS = [
    {
        "title": "Standard mileage rates | Internal Revenue Service",
        "url": "https://www.irs.gov/tax-professionals/standard-mileage-rates",
        "domain": "irs.gov",
        "source_class": "official_government",
        "source_tier": "official",
        "currentness_signal": "currentness_not_verified_by_diagnostic",
    },
    {
        "title": "IRS Raises Business Mileage Rate for 2026 - Brady Ware",
        "url": "https://bradyware.com/irs-raises-business-mileage-rate/",
        "domain": "bradyware.com",
        "candidate_fit_status": "bridge_hint_only",
    },
]


def _serper_irs_handoff() -> dict[str, Any]:
    return build_scout_to_acquisition_handoff_diagnostics(
        provider_result_set_diagnostics=_diagnostics(_SERPER_IRS_RESULTS),
        freshness_policy_diagnostics=_freshness_policy(),
        authorized_query=_IRS_QUERY,
        query_variant_ref="ag96i3f:irs-mileage-notice-announcement",
        provider_name="serper",
        provider_surface_role="candidate_acquisition",
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
    )


def _diagnostics(results: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostics = build_official_current_discovery_diagnostics(
        results,
        provider_name="serper",
        provider_surface_role="candidate_acquisition",
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
        authorized_query_ref="ag96i3i:serper-irs-fixture",
        authorized_query=_IRS_QUERY,
        include_domains=None,
        domain_constraints=None,
        authority_decision_present=False,
    )
    return sanitize_result_set_diagnostics(
        diagnostics,
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        provider_name="serper",
        provider_surface_role="candidate_acquisition",
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
    )


def _freshness_policy() -> dict[str, Any]:
    return build_search_freshness_policy_diagnostics(
        authorized_query=_IRS_QUERY,
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
        query_shape_mode="official_current_artifact_discovery",
        freshness_intent="known_year",
        current_year=2026,
    )


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _load_runner_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "ag96i3e_brokered_provider_neutral_discovery_validation",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
