from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.evidence_ledger_admission_review_diagnostics import (
    AdmissionReviewBlockerCode,
    AdmissionReviewStatus,
    RecommendedNextStep,
    as_admission_review_read_projection,
    build_evidence_ledger_admission_review_candidate,
)
from core.followup_deliberation import ProviderJobKind
from core.followup_fetch_read_currentness_verification import (
    build_fetch_read_currentness_verification_diagnostics,
)
from core.followup_provider_result_set_diagnostics import (
    DISCOVERY_UNCONSTRAINED,
    build_official_current_discovery_diagnostics,
    sanitize_result_set_diagnostics,
)
from core.followup_read_observation_adapter import (
    build_sanitized_read_observation,
)
from core.followup_scout_acquisition_handoff import (
    build_scout_to_acquisition_handoff_diagnostics,
)
from core.followup_search_freshness_policy import (
    build_search_freshness_policy_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]
ADMISSION_REVIEW_MODULE = (
    ROOT / "core" / "evidence_ledger_admission_review_diagnostics.py"
)
_RAW_SENTINEL = "ag96i3l-raw-verifier-sentinel-zzz"


def test_verified_official_current_relevant_projection_becomes_ready_candidate() -> None:
    verification, observation = _verified_observation()
    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=as_admission_review_read_projection(
            observation
        ),
        review_requirements={"source_class_required": "official_government"},
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.ADMISSION_REVIEW_CANDIDATE_READY.value
    )
    assert packet["admission_review_candidate_ready"] is True
    assert packet["blocker_codes"] == []
    assert packet["recommended_next_step"] == (
        RecommendedNextStep.EVIDENCE_LEDGER_INTAKE_REVIEW_LATER.value
    )
    assert packet["candidate_identity_summary"]["candidate_domain"] == "irs.gov"
    assert packet["verification_summary"]["currentness_posture"] == (
        "currentness_supported"
    )
    assert packet["read_observation_summary"]["read_posture"] == (
        "read_observation_ready"
    )
    assert packet["custody_metadata_complete"] is True


def test_verified_observation_with_missing_durable_projection_is_blocked() -> None:
    verification, _observation = _verified_observation()

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.READ_OBSERVATION_UNAVAILABLE.value
    )
    assert AdmissionReviewBlockerCode.MISSING_DURABLE_READ_PROJECTION.value in packet[
        "blocker_codes"
    ]
    assert packet["admission_review_candidate_ready"] is False


def test_verified_observation_with_failed_read_projection_is_blocked() -> None:
    verification, observation = _verified_observation()
    durable = as_admission_review_read_projection(observation)
    durable["read_posture"] = "read_unavailable"
    durable["read_status"] = "unreadable"

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=durable,
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.READ_OBSERVATION_UNREADABLE.value
    )
    assert AdmissionReviewBlockerCode.READ_OBSERVATION_UNREADABLE.value in packet[
        "blocker_codes"
    ]
    assert packet["recommended_next_step"] == (
        RecommendedNextStep.RERUN_FETCH_READ_VERIFICATION.value
    )


def test_verification_not_successful_is_blocked() -> None:
    verification, observation = _verified_observation()
    verification = deepcopy(verification)
    verification["verification_status"] = "fetch_read_failed"
    verification["unsupported_reason"] = "fetch_status_did_not_produce_readable_observation"

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=as_admission_review_read_projection(
            observation
        ),
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.VERIFICATION_NOT_SUCCESSFUL.value
    )
    assert AdmissionReviewBlockerCode.VERIFICATION_NOT_SUCCESSFUL.value in packet[
        "blocker_codes"
    ]


def test_candidate_url_mismatch_routes_to_reacquisition() -> None:
    verification, observation = _verified_observation()
    durable = as_admission_review_read_projection(observation)
    durable["url_domain_comparison_posture"] = "candidate_url_mismatch"
    durable["attempted_url"] = "https://www.irs.gov/unrelated"
    durable["resolved_url"] = "https://www.irs.gov/unrelated"

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=durable,
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.CANDIDATE_URL_MISMATCH.value
    )
    assert packet["recommended_next_step"] == (
        RecommendedNextStep.REACQUIRE_CANDIDATE.value
    )
    assert packet["evidence_ledger_admitted"] is False


def test_candidate_domain_mismatch_routes_to_reacquisition() -> None:
    verification, observation = _verified_observation()
    durable = as_admission_review_read_projection(observation)
    durable["url_domain_comparison_posture"] = "candidate_domain_mismatch"
    durable["attempted_domain"] = "mirror.example.com"
    durable["resolved_domain"] = "mirror.example.com"

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=durable,
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.CANDIDATE_DOMAIN_MISMATCH.value
    )
    assert AdmissionReviewBlockerCode.CANDIDATE_DOMAIN_MISMATCH.value in packet[
        "blocker_codes"
    ]
    assert packet["recommended_next_step"] == (
        RecommendedNextStep.REACQUIRE_CANDIDATE.value
    )


def test_candidate_identity_unverified_is_explicit_and_not_admitted() -> None:
    verification, observation = _verified_observation()
    verification = deepcopy(verification)
    durable = as_admission_review_read_projection(observation)
    verification["source_identity_status"] = "candidate_identity_unverified"
    durable["url_domain_comparison_posture"] = "candidate_identity_unverified"

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=durable,
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.CANDIDATE_IDENTITY_UNVERIFIED.value
    )
    assert AdmissionReviewBlockerCode.CANDIDATE_IDENTITY_UNVERIFIED.value in packet[
        "blocker_codes"
    ]
    assert packet["evidence_ledger_admitted"] is False
    assert packet["citation_eligible"] is False


def test_currentness_unclear_blocks_readiness() -> None:
    verification, observation = _verified_observation()
    verification = deepcopy(verification)
    verification["verification_status"] = "official_but_currentness_unclear"
    verification["unsupported_reason"] = (
        "currentness_or_required_year_not_supported_by_read_observation"
    )

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=as_admission_review_read_projection(
            observation
        ),
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.CURRENTNESS_UNCLEAR.value
    )
    assert AdmissionReviewBlockerCode.CURRENTNESS_UNCLEAR.value in packet[
        "blocker_codes"
    ]
    assert packet["recommended_next_step"] == (
        RecommendedNextStep.RERUN_FETCH_READ_VERIFICATION.value
    )


def test_relevance_unclear_blocks_readiness() -> None:
    verification, observation = _verified_observation()
    verification = deepcopy(verification)
    verification["verification_status"] = "official_but_required_terms_missing"
    verification["unsupported_reason"] = "required_terms_missing_from_read_observation"

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=as_admission_review_read_projection(
            observation
        ),
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.RELEVANCE_UNCLEAR.value
    )
    assert AdmissionReviewBlockerCode.RELEVANCE_UNCLEAR.value in packet[
        "blocker_codes"
    ]


def test_source_class_or_official_posture_missing_is_explicit() -> None:
    verification, observation = _verified_observation()
    verification = deepcopy(verification)
    verification.pop("official_source_status")

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=as_admission_review_read_projection(
            observation
        ),
    )

    assert packet["admission_review_status"] == (
        AdmissionReviewStatus.SOURCE_CLASS_UNCLEAR.value
    )
    assert AdmissionReviewBlockerCode.SOURCE_CLASS_UNCLEAR.value in packet[
        "blocker_codes"
    ]
    assert packet["verification_summary"]["source_class_posture"] == (
        "source_class_or_official_posture_unclear"
    )


def test_raw_verifier_text_is_not_copied_into_admission_review_candidate() -> None:
    verification, observation = _verified_observation(text_suffix=_RAW_SENTINEL)

    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        sanitized_read_observation=observation,
    )
    serialized = json.dumps(packet, sort_keys=True)

    assert _RAW_SENTINEL not in serialized
    assert "business use of a car" not in serialized
    assert packet["raw_private_payload_redaction_posture"]["verifier_input_text_retained"] is False
    assert packet["durable_projection"]["raw_page_text_retained"] is False


def test_all_outputs_remain_non_authoritative() -> None:
    verification, observation = _verified_observation()
    packet = build_evidence_ledger_admission_review_candidate(
        fetch_read_currentness_verification=verification,
        durable_read_observation_projection=as_admission_review_read_projection(
            observation
        ),
    )

    assert packet["final_evidence"] is False
    assert packet["citation_eligible"] is False
    assert packet["evidence_ledger_admitted"] is False
    assert packet["author_activation_allowed"] is False
    flags = packet["non_authoritative_boundary_flags"]
    assert flags["evidence_ledger_intake_performed"] is False
    assert flags["evidence_ledger_canonical_state_mutated"] is False
    assert flags["sufficiency_judgment_rechecked"] is False
    assert flags["final_answer_packet_updated"] is False
    boundary = packet["evidence_boundary"]
    assert boundary["evidence_ledger_admission_review_candidate_only"] is True
    assert boundary["actual_evidence_ledger_intake_deferred_to_later_phase"] is True


def test_static_guard_no_provider_ledger_intake_author_citation_or_orchestrator_imports() -> None:
    source = ADMISSION_REVIEW_MODULE.read_text(encoding="utf-8")
    imports = _imports(ADMISSION_REVIEW_MODULE)
    forbidden_imports = {
        "core.search_providers",
        "core.pipeline_orchestrator",
        "core.evidence_ledger",
        "core.evidence_ledger_runtime",
        "core.followup_evidence_intake_runtime",
        "core.author_execution_runtime",
        "core.citation_source_handoff_contract",
        "core.followup_final_answer_packet_runtime",
        "core.final_answer_packet",
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
        "execute_evidence_ledger_reduction_action",
        "build_followup_evidence_intake_record",
        "EvidenceLedgerObservation",
        "SufficiencyJudgment",
        "FinalAnswerPacket",
        "AuthorExecutor",
    ):
        assert forbidden not in source


def test_static_guard_no_pipeline_orchestrator_reference() -> None:
    source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")

    assert "evidence_ledger_admission_review_diagnostics" not in source
    assert "ag96i3l" not in source.casefold()


def _verified_observation(*, text_suffix: str = "") -> tuple[dict[str, Any], dict[str, Any]]:
    handoff = _handoff(
        url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
        domain="irs.gov",
    )
    observation = build_sanitized_read_observation(
        scout_to_acquisition_handoff_diagnostics=handoff,
        fetch_read_material={
            "attempted_url": "https://www.irs.gov/tax-professionals/standard-mileage-rates",
            "resolved_url": "https://www.irs.gov/tax-professionals/standard-mileage-rates",
            "domain": "irs.gov",
            "fetch_status": "fetched",
            "read_status": "readable",
            "http_status": 200,
            "content_type": "text/html",
            "title": "Standard mileage rates | Internal Revenue Service",
            "detected_updated_date": "2026-01-01",
            "text": (
                "Standard mileage rates from the Internal Revenue Service. "
                "The 2026 table includes business use of a car and current "
                f"standard mileage rate categories for taxpayers. {text_suffix}"
            ),
        },
    )
    verification = build_fetch_read_currentness_verification_diagnostics(
        scout_to_acquisition_handoff_diagnostics=handoff,
        read_observation=observation["verifier_input"],
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
            "source_class_required": "official_government",
        },
    )
    return verification, observation


def _handoff(*, url: str, domain: str) -> dict[str, Any]:
    query = "IRS 2026 standard mileage rates business use car notice announcement"
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
                "title": "Standard mileage rates | Internal Revenue Service",
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
        authorized_query_ref="ag96i3l:fixture",
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


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
