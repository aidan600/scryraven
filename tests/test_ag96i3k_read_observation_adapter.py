from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from core.followup_deliberation import ProviderJobKind
from core.followup_fetch_read_currentness_verification import (
    VERIFIED_OFFICIAL_CURRENT_RELEVANCE,
    build_fetch_read_currentness_verification_diagnostics,
)
from core.followup_provider_result_set_diagnostics import (
    DISCOVERY_UNCONSTRAINED,
    build_official_current_discovery_diagnostics,
    sanitize_result_set_diagnostics,
)
from core.followup_read_observation_adapter import (
    CANDIDATE_DOMAIN_MISMATCH,
    CANDIDATE_URL_MATCH,
    CANDIDATE_URL_MISMATCH,
    EMPTY_EXTRACTED_TEXT,
    FETCH_FAILED,
    FETCH_READ_CURRENTNESS_VERIFICATION,
    NOT_ATTEMPTED,
    READ_OBSERVATION_READY,
    READ_UNAVAILABLE,
    REJECT_CANDIDATE,
    RESOLVED_URL_DIFFERS_SAME_DOMAIN,
    SCOUT_OR_QUERY_REPAIR,
    TARGETED_FETCH_READ_RETRY,
    as_fetch_read_currentness_verification_input,
    build_sanitized_read_observation,
)
from core.followup_scout_acquisition_handoff import (
    build_scout_to_acquisition_handoff_diagnostics,
)
from core.followup_search_freshness_policy import (
    build_search_freshness_policy_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_MODULE = ROOT / "core" / "followup_read_observation_adapter.py"

_RAW_SENTINEL = "ag96i3k-unique-raw-sentinel-zzz"


def test_successful_read_with_matching_url_is_ready_for_verification() -> None:
    observation = build_sanitized_read_observation(
        scout_to_acquisition_handoff_diagnostics=_handoff(
            url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            domain="irs.gov",
        ),
        fetch_read_material=_material(
            attempted_url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            resolved_url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            domain="irs.gov",
            text="Standard mileage rates current table for business use of a car.",
        ),
    )

    assert observation["url_domain_comparison_posture"] == CANDIDATE_URL_MATCH
    assert observation["read_posture"] == READ_OBSERVATION_READY
    assert observation["recommended_next_step"] == FETCH_READ_CURRENTNESS_VERIFICATION
    assert observation["verifier_input"]["text"].startswith("Standard mileage rates")


def test_resolved_url_differs_same_domain_is_conservatively_acceptable() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={
            "url": "https://example.gov/rules",
            "domain": "example.gov",
        },
        fetch_read_material=_material(
            attempted_url="https://example.gov/rules",
            resolved_url="https://example.gov/rules/current-2026",
            domain="example.gov",
            text="Example agency current rules for 2026.",
        ),
    )

    assert observation["url_domain_comparison_posture"] == RESOLVED_URL_DIFFERS_SAME_DOMAIN
    assert observation["read_posture"] == READ_OBSERVATION_READY
    assert observation["recommended_next_step"] == FETCH_READ_CURRENTNESS_VERIFICATION
    assert observation["durable_projection"]["url_domain_comparison_acceptable"] is True


def test_candidate_url_mismatch_same_domain_is_rejected() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={
            "url": "https://example.gov/rules/fees",
            "domain": "example.gov",
        },
        fetch_read_material=_material(
            attempted_url="https://example.gov/unrelated/other-page",
            resolved_url="https://example.gov/unrelated/other-page",
            domain="example.gov",
            text="Unrelated page content.",
        ),
    )

    assert observation["url_domain_comparison_posture"] == CANDIDATE_URL_MISMATCH
    assert observation["read_posture"] == CANDIDATE_URL_MISMATCH
    assert observation["recommended_next_step"] == REJECT_CANDIDATE


def test_candidate_domain_mismatch_returns_to_acquisition() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={
            "url": "https://example.gov/rules/current",
            "domain": "example.gov",
        },
        fetch_read_material=_material(
            attempted_url="https://mirror.example.com/rules/current",
            resolved_url="https://mirror.example.com/rules/current",
            domain="mirror.example.com",
            text="Mirror copy of the rules page.",
        ),
    )

    assert observation["url_domain_comparison_posture"] == CANDIDATE_DOMAIN_MISMATCH
    assert observation["read_posture"] == CANDIDATE_DOMAIN_MISMATCH
    assert observation["recommended_next_step"] == SCOUT_OR_QUERY_REPAIR


def test_fetch_attempted_but_failed_recommends_retry() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={"url": "https://example.gov/page", "domain": "example.gov"},
        fetch_read_material={
            "attempted_url": "https://example.gov/page",
            "resolved_url": "https://example.gov/page",
            "domain": "example.gov",
            "fetch_status": "failed",
            "read_status": "unreadable",
            "http_status": 503,
        },
    )

    assert observation["read_posture"] == FETCH_FAILED
    assert observation["recommended_next_step"] == TARGETED_FETCH_READ_RETRY


def test_read_unavailable_recommends_retry() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={"url": "https://example.gov/page", "domain": "example.gov"},
        fetch_read_material={
            "attempted_url": "https://example.gov/page",
            "resolved_url": "https://example.gov/page",
            "domain": "example.gov",
            "fetch_status": "fetched",
            "read_status": "unreadable",
            "http_status": 200,
            "text": "this text should be ignored because read is unavailable",
        },
    )

    assert observation["read_posture"] == READ_UNAVAILABLE
    assert observation["recommended_next_step"] == TARGETED_FETCH_READ_RETRY


def test_empty_extracted_text_recommends_retry() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={"url": "https://example.gov/page", "domain": "example.gov"},
        fetch_read_material={
            "attempted_url": "https://example.gov/page",
            "resolved_url": "https://example.gov/page",
            "domain": "example.gov",
            "fetch_status": "fetched",
            "read_status": "readable",
            "http_status": 200,
            "text": "   ",
        },
    )

    assert observation["read_posture"] == EMPTY_EXTRACTED_TEXT
    assert observation["recommended_next_step"] == TARGETED_FETCH_READ_RETRY
    assert observation["verifier_input"]["text"] == ""
    assert observation["durable_projection"]["extracted_text_present"] is False


def test_oversized_extracted_text_is_truncated_and_bounded() -> None:
    long_text = ("current rules page for 2026 official content. " + _RAW_SENTINEL + " ") * 400
    observation = build_sanitized_read_observation(
        handoff_candidate={"url": "https://example.gov/page", "domain": "example.gov"},
        fetch_read_material=_material(
            attempted_url="https://example.gov/page",
            resolved_url="https://example.gov/page",
            domain="example.gov",
            text=long_text,
        ),
        max_extracted_text_chars=500,
    )

    durable = observation["durable_projection"]
    assert len(observation["verifier_input"]["text"]) == 500
    assert durable["extracted_text_truncated"] is True
    assert durable["sanitized_text_char_count"] == 500
    assert durable["extracted_text_char_count"] > 500


def test_caller_supplied_metadata_is_preserved_in_sanitized_form() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={"url": "https://example.gov/page", "domain": "example.gov"},
        fetch_read_material={
            "attempted_url": "https://example.gov/page",
            "resolved_url": "https://example.gov/page",
            "domain": "example.gov",
            "fetch_status": "fetched",
            "read_status": "readable",
            "http_status": 200,
            "content_type": "text/html; charset=utf-8",
            "title": "  Official   page   title  ",
            "detected_publication_date": "2026-01-02",
            "detected_updated_date": "2026-03-04",
            "text": "Official current page content for 2026.",
        },
    )

    assert observation["http_status"] == 200
    assert observation["content_type"] == "text/html; charset=utf-8"
    assert observation["media_type"] == "text/html"
    assert observation["title"] == "Official page title"
    durable = observation["durable_projection"]
    assert durable["detected_publication_date"] == "2026-01-02"
    assert durable["detected_updated_date"] == "2026-03-04"
    assert observation["verifier_input"]["detected_updated_date"] == "2026-03-04"


def test_no_attempt_returns_not_attempted_posture() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={"url": "https://example.gov/page", "domain": "example.gov"},
        fetch_read_material=None,
    )

    assert observation["read_posture"] == NOT_ATTEMPTED
    assert observation["fetch_status"] == NOT_ATTEMPTED
    assert observation["recommended_next_step"] == TARGETED_FETCH_READ_RETRY


def test_explicit_not_attempted_fetch_status_is_not_attempted() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={"url": "https://example.gov/page", "domain": "example.gov"},
        fetch_read_material={
            "attempted_url": "https://example.gov/page",
            "fetch_status": "not_attempted",
        },
    )

    assert observation["read_posture"] == NOT_ATTEMPTED
    assert observation["recommended_next_step"] == TARGETED_FETCH_READ_RETRY


def test_durable_projection_excludes_raw_text_and_sentinel() -> None:
    text = (
        "Standard mileage rates current table for business use of a car. "
        + _RAW_SENTINEL
        + " Internal Revenue Service 2026."
    )
    observation = build_sanitized_read_observation(
        scout_to_acquisition_handoff_diagnostics=_handoff(
            url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            domain="irs.gov",
        ),
        fetch_read_material=_material(
            attempted_url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            resolved_url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            domain="irs.gov",
            text=text,
        ),
    )

    durable_serialized = json.dumps(observation["durable_projection"], sort_keys=True)
    assert _RAW_SENTINEL not in durable_serialized
    assert "business use of a car" not in durable_serialized
    assert observation["durable_projection"]["raw_page_text_retained"] is False
    # The sentinel only survives inside the explicitly ephemeral verifier input.
    assert _RAW_SENTINEL in observation["verifier_input"]["text"]
    posture = observation["raw_private_payload_redaction_posture"]
    assert posture["durable_projection_retains_raw_page_text"] is False
    assert posture["verifier_input_text_is_ephemeral"] is True


def test_output_is_never_final_evidence_or_admitted() -> None:
    observation = build_sanitized_read_observation(
        handoff_candidate={"url": "https://example.gov/page", "domain": "example.gov"},
        fetch_read_material=_material(
            attempted_url="https://example.gov/page",
            resolved_url="https://example.gov/page",
            domain="example.gov",
            text="Official current page content.",
        ),
    )

    assert observation["final_evidence"] is False
    assert observation["citation_eligible"] is False
    assert observation["evidence_ledger_admitted"] is False
    assert observation["author_activation_allowed"] is False
    boundary = observation["evidence_boundary"]
    assert boundary["evidence_ledger_admission_performed"] is False
    assert boundary["evidence_ledger_admission_review_performed"] is False
    assert boundary["author_or_final_answer_activation_allowed"] is False


def test_adapter_is_deterministic() -> None:
    kwargs: dict[str, Any] = {
        "handoff_candidate": {"url": "https://example.gov/page", "domain": "example.gov"},
        "fetch_read_material": _material(
            attempted_url="https://example.gov/page",
            resolved_url="https://example.gov/page",
            domain="example.gov",
            text="Official current page content for 2026.",
        ),
    }
    first = build_sanitized_read_observation(**kwargs)
    second = build_sanitized_read_observation(**kwargs)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_verifier_input_feeds_ag96i3j_verifier() -> None:
    handoff = _handoff(
        url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
        domain="irs.gov",
    )
    observation = build_sanitized_read_observation(
        scout_to_acquisition_handoff_diagnostics=handoff,
        fetch_read_material=_material(
            attempted_url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            resolved_url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            domain="irs.gov",
            text=(
                "Standard mileage rates from the Internal Revenue Service. "
                "The 2026 table includes business use of a car and current "
                "standard mileage rate categories for taxpayers."
            ),
        ),
    )

    verifier_input = as_fetch_read_currentness_verification_input(observation)
    assert verifier_input == observation["verifier_input"]

    packet = build_fetch_read_currentness_verification_diagnostics(
        scout_to_acquisition_handoff_diagnostics=handoff,
        read_observation=verifier_input,
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
    assert packet["final_evidence"] is False
    assert packet["evidence_ledger_admitted"] is False


def test_static_guard_no_provider_fetch_or_product_imports() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    imports = _imports(ADAPTER_MODULE)
    forbidden_imports = {
        "core.search_providers",
        "core.pipeline_orchestrator",
        "core.evidence_ledger",
        "core.author_execution_runtime",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
    }

    assert imports.isdisjoint(forbidden_imports)
    for forbidden in (
        "requests.",
        "httpx.",
        "urlopen",
        "load_dotenv",
        "os.environ",
        "BeautifulSoup",
    ):
        assert forbidden not in source


def test_static_guard_no_pipeline_orchestrator_reference() -> None:
    source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")

    assert "followup_read_observation_adapter" not in source
    assert "build_sanitized_read_observation" not in source
    assert "ag96i3k" not in source.casefold()


def _handoff(*, url: str, domain: str) -> dict[str, Any]:
    query = "official current artifact discovery query"
    freshness = build_search_freshness_policy_diagnostics(
        authorized_query=query,
        provider_job_kind=ProviderJobKind.OFFICIAL_CURRENT_CANDIDATE_ACQUISITION.value,
        acquisition_mode=DISCOVERY_UNCONSTRAINED,
        query_shape_mode="official_current_artifact_discovery",
        freshness_intent="known_year",
        current_year=2026,
    )
    diagnostics = build_official_current_discovery_diagnostics(
        [
            {
                "title": "Official candidate page",
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
        authorized_query_ref="ag96i3k:fixture",
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


def _material(
    *,
    attempted_url: str,
    resolved_url: str,
    domain: str,
    text: str,
) -> dict[str, Any]:
    return {
        "attempted_url": attempted_url,
        "resolved_url": resolved_url,
        "domain": domain,
        "fetch_status": "fetched",
        "read_status": "readable",
        "http_status": 200,
        "content_type": "text/html",
        "title": "sanitized fixture title",
        "text": text,
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
