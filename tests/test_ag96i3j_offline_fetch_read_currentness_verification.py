from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.followup_deliberation import ProviderJobKind
from core.followup_fetch_read_currentness_verification import (
    FETCH_READ_FAILED,
    OFFICIAL_BUT_CURRENTNESS_UNCLEAR,
    OFFICIAL_BUT_REQUIRED_TERMS_MISSING,
    VERIFIED_OFFICIAL_CURRENT_RELEVANCE,
    build_fetch_read_currentness_verification_diagnostics,
)
from core.followup_provider_result_set_diagnostics import (
    DISCOVERY_UNCONSTRAINED,
    build_official_current_discovery_diagnostics,
    sanitize_result_set_diagnostics,
)
from core.followup_scout_acquisition_handoff import (
    build_scout_to_acquisition_handoff_diagnostics,
)
from core.followup_search_freshness_policy import (
    build_search_freshness_policy_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_MODULE = ROOT / "core" / "followup_fetch_read_currentness_verification.py"


def test_irs_style_handoff_candidate_verifies_without_hardcoded_rate_value() -> None:
    handoff = _handoff(
        url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
        domain="irs.gov",
        title="Standard mileage rates | Internal Revenue Service",
        query="IRS 2026 standard mileage rates business use car notice announcement",
        freshness_intent="known_year",
    )

    packet = build_fetch_read_currentness_verification_diagnostics(
        scout_to_acquisition_handoff_diagnostics=handoff,
        read_observation=_read(
            url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            domain="irs.gov",
            text=(
                "Standard mileage rates from the Internal Revenue Service. "
                "The 2026 table includes business use of a car and current "
                "standard mileage rate categories for taxpayers."
            ),
        ),
        verification_requirements={
            "source_obligation": "official_current",
            "required_terms": [
                "Standard mileage rates",
                "Internal Revenue Service",
                "business use",
                "car",
            ],
            "required_years": [2026],
            "currentness_terms": ["current", "table"],
            "expected_domain": "irs.gov",
        },
    )

    assert packet["verification_status"] == VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    assert packet["candidate_accounting_status"] == "used_for_verification"
    assert packet["recommended_next_step"] == "evidence_ledger_admission_review"
    assert packet["candidate_url"] == (
        "https://www.irs.gov/tax-professionals/standard-mileage-rates"
    )
    assert "70" not in json.dumps(packet)


def test_uscis_fee_fixture_verifies_through_generic_terms() -> None:
    packet = _verify_candidate(
        url="https://www.uscis.gov/forms/filing-fees",
        domain="uscis.gov",
        title="Filing Fees | USCIS",
        text=(
            "USCIS filing fee information for each form is kept on this current "
            "fee schedule page. The page was updated in 2026 for form filing."
        ),
        requirements={
            "required_terms": ["USCIS", "filing fee", "form"],
            "required_years": [2026],
            "currentness_terms": ["current", "updated"],
            "expected_domain": "uscis.gov",
        },
    )

    assert packet["verification_status"] == VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    assert packet["required_terms_found"] == ["USCIS", "filing fee", "form"]


def test_sec_rule_release_fixture_verifies_through_generic_terms() -> None:
    packet = _verify_candidate(
        url="https://www.sec.gov/rules-regulations/final-rules/disclosure-release",
        domain="sec.gov",
        title="Final Rule Release | SEC",
        text=(
            "The SEC final rule release addresses disclosure and filing "
            "requirements. This release page includes current compliance dates."
        ),
        requirements={
            "required_terms": ["SEC", "final rule", "release", "disclosure", "filing"],
            "currentness_terms": ["current", "release"],
            "expected_domain": "sec.gov",
        },
    )

    assert packet["verification_status"] == VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    assert "sec.gov" == packet["candidate_domain"]


def test_fda_recall_safety_fixture_verifies_through_generic_terms() -> None:
    packet = _verify_candidate(
        url="https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts/example-product",
        domain="fda.gov",
        title="Recall and Safety Alert | FDA",
        text=(
            "FDA recall and safety alert for Example Product from Example "
            "Manufacturer. The current alert explains product risks and actions."
        ),
        requirements={
            "required_terms": [
                "FDA",
                "recall",
                "safety alert",
                "Example Product",
                "Example Manufacturer",
            ],
            "currentness_terms": ["current", "safety alert"],
            "expected_domain": "fda.gov",
        },
    )

    assert packet["verification_status"] == VERIFIED_OFFICIAL_CURRENT_RELEVANCE


def test_software_release_notes_fixture_verifies_through_generic_terms() -> None:
    packet = _verify_candidate(
        url="https://docs.example.com/product/release-notes",
        domain="docs.example.com",
        title="Release Notes",
        text=(
            "Official product release notes for version 4.2. The latest update "
            "documents a patch and compatibility improvements."
        ),
        requirements={
            "required_terms": ["release notes", "version", "update", "patch"],
            "currentness_terms": ["latest", "update"],
            "expected_domain": "docs.example.com",
        },
    )

    assert packet["verification_status"] == VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    assert packet["source_identity_status"] == "candidate_url_match"


def test_official_page_missing_required_terms_returns_required_terms_missing() -> None:
    packet = _verify_candidate(
        url="https://www.example.gov/current",
        domain="example.gov",
        title="Official page",
        text="Example agency current operating status and general notices.",
        requirements={
            "required_terms": ["filing fee", "form"],
            "currentness_terms": ["current"],
            "expected_domain": "example.gov",
        },
    )

    assert packet["verification_status"] == OFFICIAL_BUT_REQUIRED_TERMS_MISSING
    assert packet["candidate_accounting_status"] == "rejected_with_reason"
    assert packet["recommended_next_step"] == "seek_better_official_source"


def test_official_relevant_page_missing_year_or_currentness_is_unclear() -> None:
    packet = _verify_candidate(
        url="https://www.example.gov/rules/fees",
        domain="example.gov",
        title="Official fee page",
        text="Example agency fee page for form filing requirements.",
        requirements={
            "required_terms": ["fee", "form", "filing"],
            "required_years": [2026],
            "currentness_terms": ["current", "updated"],
            "expected_domain": "example.gov",
        },
    )

    assert packet["verification_status"] == OFFICIAL_BUT_CURRENTNESS_UNCLEAR
    assert packet["recommended_next_step"] == "targeted_fetch_read_retry"
    assert packet["required_years_missing"] == ["2026"]


def test_explicit_currentness_terms_missing_are_unclear_even_when_year_is_present() -> None:
    packet = _verify_candidate(
        url="https://www.example.gov/rules/fees-2026",
        domain="example.gov",
        title="Official 2026 fee page",
        text="Example agency fee page for 2026 form filing requirements.",
        requirements={
            "required_terms": ["fee", "form", "filing"],
            "required_years": [2026],
            "currentness_terms": ["current", "updated"],
            "expected_domain": "example.gov",
        },
    )

    assert packet["verification_status"] == OFFICIAL_BUT_CURRENTNESS_UNCLEAR
    assert packet["recommended_next_step"] == "targeted_fetch_read_retry"
    assert packet["required_years_found"] == ["2026"]
    assert packet["currentness_terms_found"] == []


def test_fetch_read_failed_returns_fetch_read_failed() -> None:
    packet = _verify_candidate(
        url="https://www.example.gov/rules/current",
        domain="example.gov",
        title="Official page",
        read_observation={
            "attempted_url": "https://www.example.gov/rules/current",
            "resolved_url": "https://www.example.gov/rules/current",
            "domain": "example.gov",
            "fetch_status": "failed",
            "read_status": "unreadable",
        },
        requirements={
            "required_terms": ["rule"],
            "currentness_terms": ["current"],
            "expected_domain": "example.gov",
        },
    )

    assert packet["verification_status"] == FETCH_READ_FAILED
    assert packet["candidate_accounting_status"] == "not_attempted"
    assert packet["recommended_next_step"] == "targeted_fetch_read_retry"


def test_url_or_domain_mismatch_returns_mismatch_status() -> None:
    packet = _verify_candidate(
        url="https://www.example.gov/rules/current",
        domain="example.gov",
        title="Official page",
        read_observation=_read(
            url="https://mirror.example.com/rules/current",
            domain="mirror.example.com",
            text="Example agency current rule page.",
        ),
        requirements={
            "required_terms": ["rule"],
            "currentness_terms": ["current"],
            "expected_domain": "example.gov",
        },
    )

    assert packet["verification_status"] in {
        "candidate_url_mismatch",
        "candidate_domain_mismatch",
    }
    assert packet["candidate_accounting_status"] == "rejected_with_reason"


def test_output_does_not_retain_raw_page_text_or_payload_markers() -> None:
    long_text = (
        "Release notes version update patch are current. "
        "payload_marker blocked raw provider payload marker. "
        "raw page text should not survive as an output fragment. "
    ) * 80
    packet = _verify_candidate(
        url="https://docs.example.com/product/release-notes",
        domain="docs.example.com",
        title="Release Notes",
        text=long_text,
        requirements={
            "required_terms": ["release notes", "version", "update", "patch"],
            "currentness_terms": ["current"],
            "expected_domain": "docs.example.com",
        },
        max_supported_excerpt_chars=80,
    )
    serialized = json.dumps(packet, sort_keys=True)

    assert packet["verification_status"] == VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    assert "payload_marker" not in serialized
    assert "blocked raw provider payload marker" not in serialized
    assert "raw page text should not survive" not in serialized
    assert all(len(fragment) <= 80 for fragment in packet["supported_excerpt_fragments"])
    assert packet["raw_private_payload_redaction_posture"]["raw_page_text_retained"] is False


def test_verified_output_still_not_final_evidence_or_citation_eligible() -> None:
    packet = _verify_candidate(
        url="https://docs.example.com/product/release-notes",
        domain="docs.example.com",
        title="Release Notes",
        text="Release notes version update patch are current.",
        requirements={
            "required_terms": ["release notes", "version", "update", "patch"],
            "currentness_terms": ["current"],
            "expected_domain": "docs.example.com",
        },
    )

    assert packet["verification_status"] == VERIFIED_OFFICIAL_CURRENT_RELEVANCE
    assert packet["final_evidence"] is False
    assert packet["citation_eligible"] is False
    assert packet["evidence_ledger_admitted"] is False
    assert packet["author_activation_allowed"] is False
    assert packet["evidence_boundary"]["evidence_ledger_admission_performed"] is False


def test_freshness_policy_context_from_handoff_is_preserved_compactly() -> None:
    handoff = _handoff(
        url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
        domain="irs.gov",
        title="Standard mileage rates | Internal Revenue Service",
        query="IRS 2026 standard mileage rates business use car notice announcement",
        freshness_intent="known_year",
    )

    packet = build_fetch_read_currentness_verification_diagnostics(
        scout_to_acquisition_handoff_diagnostics=handoff,
        read_observation=_read(
            url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            domain="irs.gov",
            text=(
                "Internal Revenue Service standard mileage rates 2026 current "
                "business use car table."
            ),
        ),
        verification_requirements={
            "required_terms": ["Internal Revenue Service", "standard mileage rates"],
            "required_years": [2026],
            "currentness_terms": ["current"],
            "expected_domain": "irs.gov",
        },
    )

    context = packet["freshness_policy_context"]
    assert context["freshness_intent"] == "known_year"
    assert context["provider_freshness_policy"] == "omit_provider_freshness_filter"
    assert context["over_narrow_recent_window_forbidden"] is True
    assert "known-year official/current artifacts" in context["freshness_rationale"]


def test_static_guard_no_provider_imports_or_calls_in_verifier_helper() -> None:
    source = VERIFIER_MODULE.read_text(encoding="utf-8")
    imports = _imports(VERIFIER_MODULE)
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
        "load_dotenv",
        "os.environ",
    ):
        assert forbidden not in source


def test_static_guard_no_requests_httpx_or_runtime_fetch_calls_in_verifier_helper() -> None:
    source = VERIFIER_MODULE.read_text(encoding="utf-8")

    for forbidden in (
        "requests.",
        "httpx.",
        "fetch_url_text(",
        "fetch_page(",
        "BeautifulSoup",
        ".get(" "http",
    ):
        assert forbidden not in source


def test_static_guard_no_pipeline_orchestrator_domain_logic() -> None:
    source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")

    assert "followup_fetch_read_currentness_verification" not in source
    assert "fetch_read_currentness_verification_diagnostics" not in source
    assert "ag96i3j" not in source.casefold()


def test_static_guard_no_author_citation_or_product_imports() -> None:
    imports = _imports(VERIFIER_MODULE)
    forbidden_imports = {
        "core.author_execution_runtime",
        "core.citation_source_handoff_contract",
        "core.followup_final_answer_packet_runtime",
        "core.final_answer_packet",
        "core.evidence_ledger",
        "core.pipeline_orchestrator",
    }

    assert imports.isdisjoint(forbidden_imports)


def _verify_candidate(
    *,
    url: str,
    domain: str,
    title: str,
    text: str | None = None,
    read_observation: dict[str, Any] | None = None,
    requirements: dict[str, Any],
    max_supported_excerpt_chars: int = 160,
) -> dict[str, Any]:
    handoff = _handoff(
        url=url,
        domain=domain,
        title=title,
        query=f"{title} official current",
        freshness_intent="current_or_stable",
    )
    return build_fetch_read_currentness_verification_diagnostics(
        scout_to_acquisition_handoff_diagnostics=handoff,
        read_observation=read_observation or _read(url=url, domain=domain, text=text or ""),
        verification_requirements={
            "source_obligation": "official_current",
            **requirements,
        },
        max_supported_excerpt_chars=max_supported_excerpt_chars,
    )


def _handoff(
    *,
    url: str,
    domain: str,
    title: str,
    query: str,
    freshness_intent: str,
) -> dict[str, Any]:
    freshness = build_search_freshness_policy_diagnostics(
        authorized_query=query,
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
        query_shape_mode="official_current_artifact_discovery",
        freshness_intent=freshness_intent,
        current_year=2026,
    )
    diagnostics = build_official_current_discovery_diagnostics(
        [
            {
                "title": title,
                "url": url,
                "domain": domain,
                "source_tier": "official",
                "source_class": "official_government",
                "currentness_signal": "currentness_not_verified_by_diagnostic",
            }
        ],
        provider_name="serper",
        provider_surface_role="candidate_acquisition",
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
        authorized_query_ref="ag96i3j:fixture",
        authorized_query=query,
    )
    return build_scout_to_acquisition_handoff_diagnostics(
        provider_result_set_diagnostics=sanitize_result_set_diagnostics(
            diagnostics,
            provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
            provider_name="serper",
            provider_surface_role="candidate_acquisition",
            acquisition_mode=DISCOVERY_UNCONSTRAINED,
        ),
        freshness_policy_diagnostics=freshness,
        authorized_query=query,
        provider_name="serper",
        provider_surface_role="candidate_acquisition",
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
    )


def _read(*, url: str, domain: str, text: str) -> dict[str, Any]:
    return {
        "attempted_url": url,
        "resolved_url": url,
        "domain": domain,
        "fetch_status": "fetched",
        "read_status": "readable",
        "http_status": 200,
        "content_type": "text/html",
        "text": text,
        "title": "sanitized fixture title",
    }


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
