from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.evidence_ledger import SourceRequirementStatus
from core.evidence_ledger_intake_adapter import (
    SCHEMA_VERSION,
    EvidenceLedgerIntakeBinding,
    EvidenceLedgerIntakeBlockerCode,
    build_evidence_ledger_intake_observation_from_admission_review,
)
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.official_current_source_custody import OfficialCurrentCustodyStatus
from core.run_kernel import EVIDENCE_LEDGER_STAGE, RunKernel

ROOT = Path(__file__).resolve().parents[1]
INTAKE_ADAPTER_MODULE = ROOT / "core" / "evidence_ledger_intake_adapter.py"


def test_ready_admission_review_candidate_and_binding_builds_reducer_observation() -> None:
    result = build_evidence_ledger_intake_observation_from_admission_review(
        admission_review_candidate=_ready_candidate(),
        binding=_binding(),
    )

    assert result.accepted is True
    assert result.blocker_codes == ()
    assert result.observation is not None
    payload = result.observation.to_dict()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["observation_id"] == "ag96i3m1:obs:001"
    assert payload["observation_source"] == "ag96i3m1_admission_review_intake_adapter"
    assert payload["requirements"] == [
        {
            "requirement_id": "official_current_source:official_current_rules",
            "requirement_kind": "official_current",
            "origin_ref": "ag96i3m1:ag96i3m1_intake_adapter_test",
            "required_source_class": "official_current_rules",
            "required_source_tier": "official",
            "required_currentness": "current",
            "linked_candidate_ids": ["irs_current_rules_2026"],
        }
    ]
    candidate = payload["candidates"][0]
    assert candidate["candidate_id"] == "irs_current_rules_2026"
    assert candidate["source_class"] == "official_current_rules"
    assert candidate["source_tier"] == "official"
    assert candidate["currentness_signal"] == "current"
    assert candidate["disposition"] == "accepted"
    assert candidate["eligible_for_stronger_obligation"] is True
    assert candidate["final_evidence_eligible"] is False
    assert "final_evidence" not in payload
    assert payload["requirement_links"] == [
        {
            "requirement_id": "official_current_source:official_current_rules",
            "candidate_id": "irs_current_rules_2026",
            "link_reason": "ag96i3m1_explicit_intake_binding",
            "link_status": "accepted",
        }
    ]
    assert result.projection["official_current_rules"] == {
        "source_obligation": "official_current",
        "requirement_kind": "official_current",
        "required_source_class": "official_current_rules",
        "required_source_tier": "official",
        "required_currentness": "current",
        "requirement_id": "official_current_source:official_current_rules",
    }
    assert result.projection["behavior_boundary_flags"]["runtime_activation"] is False
    assert result.projection["behavior_boundary_flags"]["citation_eligible"] is False


def test_runkernel_evidence_ledger_reduction_mutates_canonical_state_only() -> None:
    kernel = RunKernel.start(run_id="ag96i3m1", request_id="request-ag96i3m1")
    result = build_evidence_ledger_intake_observation_from_admission_review(
        admission_review_candidate=_ready_candidate(),
        binding=_binding(),
    )
    assert result.observation is not None
    before = _closed_surface_snapshot(kernel)

    _reduce_intake_observation(kernel, result.observation.to_dict())

    after = kernel.state.evidence_ledger.to_projection().to_dict()
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE] == after
    assert after["owner"] == "RunKernel.EvidenceLedger"
    assert after["canonical_state"] is True
    assert after["candidate_count"] == 1
    assert after["requirement_count"] == 1
    assert after["custody_record_count"] == 1
    assert after["final_evidence_refs"] == []
    candidate = after["candidate_records"][0]
    assert candidate["candidate_id"] == "irs_current_rules_2026"
    assert candidate["fact_disposition"] == "accepted"
    assert candidate["final_evidence_eligible"] is False
    requirement = _requirement(
        after,
        "official_current_source:official_current_rules",
    )
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value
    assert requirement["required_source_class"] == "official_current_rules"
    official = after["official_current_source_custody"]
    assert official["requirements"] == [
        {
            "requirement_id": "official_current_source:official_current_rules",
            "source_class": "official_current_rules",
            "status": OfficialCurrentCustodyStatus.REQUIREMENT_SATISFIED.value,
            "satisfied_candidate_ids": ["irs_current_rules_2026"],
        }
    ]
    assert _closed_surface_snapshot(kernel) == before


@pytest.mark.parametrize(
    ("binding_overrides", "expected"),
    [
        (
            {"requirement_id": ""},
            EvidenceLedgerIntakeBlockerCode.MISSING_REQUIREMENT_ID,
        ),
        (
            {"candidate_id": ""},
            EvidenceLedgerIntakeBlockerCode.MISSING_CANDIDATE_ID,
        ),
        (
            {"observation_id": "", "observation_ref": ""},
            EvidenceLedgerIntakeBlockerCode.MISSING_OBSERVATION_ID_OR_REF,
        ),
        (
            {"idempotency_key": "", "deduplication_basis": ()},
            EvidenceLedgerIntakeBlockerCode.MISSING_IDEMPOTENCY_OR_DEDUP_BASIS,
        ),
        (
            {"source_obligation": ""},
            EvidenceLedgerIntakeBlockerCode.MISSING_SOURCE_OBLIGATION,
        ),
        (
            {"source_obligation": "reputable_secondary"},
            EvidenceLedgerIntakeBlockerCode.UNSUPPORTED_SOURCE_OBLIGATION,
        ),
        (
            {"required_source_class": ""},
            EvidenceLedgerIntakeBlockerCode.MISSING_REQUIRED_SOURCE_CLASS,
        ),
        (
            {"official_current_rules": {}},
            EvidenceLedgerIntakeBlockerCode.MISSING_OFFICIAL_CURRENT_RULES_MAPPING,
        ),
        (
            {"origin_action": ""},
            EvidenceLedgerIntakeBlockerCode.MISSING_ORIGIN_ACTION,
        ),
        (
            {"citation_eligible": True},
            EvidenceLedgerIntakeBlockerCode.DOWNSTREAM_ACTIVATION_REQUESTED,
        ),
    ],
)
def test_complete_explicit_binding_is_required_for_intake(
    binding_overrides: dict[str, Any],
    expected: EvidenceLedgerIntakeBlockerCode,
) -> None:
    result = build_evidence_ledger_intake_observation_from_admission_review(
        admission_review_candidate=_ready_candidate(),
        binding=_binding_dict(**binding_overrides),
    )

    assert result.accepted is False
    assert result.observation is None
    assert expected in result.blocker_codes


@pytest.mark.parametrize(
    ("candidate_overrides", "expected"),
    [
        (
            {
                "admission_review_candidate_ready": False,
                "admission_review_status": "currentness_unclear",
            },
            EvidenceLedgerIntakeBlockerCode.ADMISSION_REVIEW_CANDIDATE_NOT_READY,
        ),
        (
            {"blocker_codes": ["currentness_unclear"]},
            EvidenceLedgerIntakeBlockerCode.ADMISSION_REVIEW_BLOCKERS_PRESENT,
        ),
        (
            {
                "candidate_identity_summary": {
                    "source_identity_status": "candidate_identity_unverified",
                    "url_domain_comparison_posture": "candidate_identity_unverified",
                }
            },
            EvidenceLedgerIntakeBlockerCode.CANDIDATE_IDENTITY_UNVERIFIED,
        ),
        (
            {
                "candidate_identity_summary": {
                    "source_identity_status": "candidate_domain_mismatch",
                    "url_domain_comparison_posture": "candidate_domain_mismatch",
                }
            },
            EvidenceLedgerIntakeBlockerCode.CANDIDATE_IDENTITY_MISMATCH,
        ),
        (
            {
                "verification_summary": {
                    "verification_status": "official_but_currentness_unclear",
                    "official_source_status": "official_source_supported",
                    "currentness_posture": "currentness_unclear",
                    "relevance_posture": "relevance_supported",
                }
            },
            EvidenceLedgerIntakeBlockerCode.CANDIDATE_CURRENTNESS_OR_RELEVANCE_UNCLEAR,
        ),
        (
            {"read_observation_summary": {"read_posture": "read_unavailable"}},
            EvidenceLedgerIntakeBlockerCode.CANDIDATE_READ_OBSERVATION_INCOMPLETE,
        ),
        (
            {"custody_metadata_complete": False},
            EvidenceLedgerIntakeBlockerCode.CANDIDATE_CUSTODY_METADATA_INCOMPLETE,
        ),
    ],
)
def test_non_ready_or_blocked_admission_review_candidates_do_not_intake(
    candidate_overrides: dict[str, Any],
    expected: EvidenceLedgerIntakeBlockerCode,
) -> None:
    result = build_evidence_ledger_intake_observation_from_admission_review(
        admission_review_candidate=_ready_candidate(**candidate_overrides),
        binding=_binding(),
    )

    assert result.accepted is False
    assert result.observation is None
    assert expected in result.blocker_codes


def test_invalid_candidates_do_not_mutate_runkernel_evidence_ledger() -> None:
    kernel = RunKernel.start(run_id="ag96i3m1-invalid", request_id="request-invalid")
    before = kernel.state.evidence_ledger.to_projection().to_dict()

    result = build_evidence_ledger_intake_observation_from_admission_review(
        admission_review_candidate=_ready_candidate(
            admission_review_candidate_ready=False,
            admission_review_status="relevance_unclear",
            blocker_codes=["relevance_unclear"],
        ),
        binding=_binding(),
    )

    assert result.observation is None
    assert kernel.state.evidence_ledger.to_projection().to_dict() == before


def test_raw_text_verifier_excerpts_provider_payloads_and_private_fields_are_blocked() -> None:
    sentinel = "ag96i3m1-private-raw-text-sentinel"
    result = build_evidence_ledger_intake_observation_from_admission_review(
        admission_review_candidate=_ready_candidate(
            raw_text=sentinel,
            provider_payload={"payload": sentinel},
            verification_summary={
                "verification_status": "verified_official_current_relevance",
                "official_source_status": "official_source_supported",
                "currentness_posture": "currentness_supported",
                "relevance_posture": "relevance_supported",
                "supported_excerpt_fragments": [sentinel],
            },
        ),
        binding=_binding(),
    )

    assert result.accepted is False
    assert EvidenceLedgerIntakeBlockerCode.RAW_PRIVATE_PAYLOAD_RETENTION_BLOCKED in (
        result.blocker_codes
    )
    serialized = json.dumps(result.to_dict(), sort_keys=True)
    assert sentinel not in serialized
    assert "supported_excerpt_fragments" not in serialized
    assert '"provider_payload":' not in serialized


def test_reducing_same_binding_observation_id_is_idempotent_in_ledger_projection() -> None:
    kernel = RunKernel.start(run_id="ag96i3m1-repeat", request_id="request-repeat")
    result = build_evidence_ledger_intake_observation_from_admission_review(
        admission_review_candidate=_ready_candidate(),
        binding=_binding(),
    )
    assert result.observation is not None
    payload = result.observation.to_dict()

    _reduce_intake_observation(kernel, payload)
    after_first = deepcopy(kernel.state.evidence_ledger.to_projection().to_dict())
    _reduce_intake_observation(kernel, payload)
    after_second = kernel.state.evidence_ledger.to_projection().to_dict()

    assert after_second == after_first
    assert after_second["candidate_count"] == 1
    assert after_second["custody_record_count"] == 1
    assert after_second["observation_refs"] == [
        {
            "observation_id": "ag96i3m1:obs:001",
            "source": "ag96i3m1_admission_review_intake_adapter",
        }
    ]


def test_static_guards_keep_adapter_closed_to_runtime_live_and_answer_surfaces() -> None:
    source = INTAKE_ADAPTER_MODULE.read_text(encoding="utf-8")
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.followup_evidence_intake_runtime",
        "core.followup_fetch_read_currentness_verification",
        "core.followup_final_answer_packet_runtime",
        "core.followup_sufficiency_recheck_runtime",
        "core.final_answer_packet",
        "core.prompts",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
    }

    assert _imports(INTAKE_ADAPTER_MODULE).isdisjoint(forbidden_imports)
    for forbidden in (
        "requests.",
        "httpx.",
        "urlopen",
        "ask_model",
        "execute_evidence_ledger_reduction_action",
        "SufficiencyJudgment(",
        "FinalAnswerPacket(",
        "AuthorExecutor(",
        "build_followup_evidence_intake_record",
    ):
        assert forbidden not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "evidence_ledger_intake_adapter" not in pipeline_source
    assert "ag96i3m1" not in pipeline_source.casefold()


def _reduce_intake_observation(kernel: RunKernel, payload: dict[str, Any]) -> None:
    action = kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": payload["observation_source"],
            "schema_version": payload["schema_version"],
            "origin_phase": "ag96i3m1",
        }
    )
    result = execute_evidence_ledger_reduction_action(action, payload=payload)
    kernel.reduce(result.observation)


def _requirement(projection: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement
    raise AssertionError(f"missing requirement {requirement_id}")


def _closed_surface_snapshot(kernel: RunKernel) -> dict[str, Any]:
    return {
        "search_judgment": deepcopy(kernel.state.search_judgment),
        "search_judgment_projection": deepcopy(kernel.state.search_judgment_projection),
        "sufficiency_judgment": deepcopy(kernel.state.sufficiency_judgment),
        "sufficiency_judgment_projection": deepcopy(
            kernel.state.sufficiency_judgment_projection
        ),
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
    }


def _binding() -> EvidenceLedgerIntakeBinding:
    return EvidenceLedgerIntakeBinding(**_binding_dict())


def _binding_dict(**overrides: Any) -> dict[str, Any]:
    payload = {
        "requirement_id": "official_current_source:official_current_rules",
        "candidate_id": "irs_current_rules_2026",
        "observation_id": "ag96i3m1:obs:001",
        "observation_ref": "ag96i3l:admission-review:001",
        "source_obligation": "official_current",
        "required_source_class": "official_current_rules",
        "required_source_tier": "official",
        "required_currentness": "current",
        "official_current_rules": {
            "source_obligation": "official_current",
            "requirement_kind": "official_current",
            "required_source_class": "official_current_rules",
            "required_source_tier": "official",
            "required_currentness": "current",
            "requirement_id": "official_current_source:official_current_rules",
        },
        "origin_phase": "ag96i3m1",
        "origin_action": "ag96i3m1_intake_adapter_test",
        "origin_record_type": "evidence_ledger_admission_review_candidate_diagnostics",
        "origin_schema_version": "ag96i3l_evidence_ledger_admission_review_diagnostics_v1",
        "idempotency_key": "ag96i3m1:irs-current-rules-2026",
        "deduplication_basis": (
            "requirement_id",
            "candidate_id",
            "observation_ref",
        ),
        "final_evidence": False,
        "citation_eligible": False,
        "author_activation_allowed": False,
    }
    payload.update(overrides)
    return payload


def _ready_candidate(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "ag96i3l_evidence_ledger_admission_review_diagnostics_v1",
        "record_type": "evidence_ledger_admission_review_candidate_diagnostics",
        "owner": "EvidenceLedgerAdmissionReviewDiagnostics",
        "canonical_state": False,
        "trace_only": False,
        "storage_only": False,
        "diagnostic_only": True,
        "admission_review_status": "admission_review_candidate_ready",
        "admission_review_candidate_ready": True,
        "blocker_codes": [],
        "reason_codes": [],
        "recommended_next_step": "evidence_ledger_intake_review_later",
        "candidate_identity_summary": {
            "candidate_url": "https://www.irs.gov/tax-professionals/standard-mileage-rates",
            "candidate_domain": "irs.gov",
            "attempted_url": "https://www.irs.gov/tax-professionals/standard-mileage-rates",
            "resolved_url": "https://www.irs.gov/tax-professionals/standard-mileage-rates",
            "attempted_domain": "irs.gov",
            "resolved_domain": "irs.gov",
            "observation_domain": "irs.gov",
            "source_identity_status": "candidate_url_match",
            "url_domain_comparison_posture": "candidate_url_match",
        },
        "verification_summary": {
            "verification_status": "verified_official_current_relevance",
            "candidate_accounting_status": "used_for_verification",
            "source_identity_status": "candidate_url_match",
            "official_source_status": "official_source_supported",
            "source_obligation": "official_current",
            "source_class_required": "official_government",
            "source_class_posture": "official_source_supported",
            "currentness_posture": "currentness_supported",
            "relevance_posture": "relevance_supported",
            "candidate_fit_posture": "candidate_fit_supported",
            "recommended_next_step_from_verification": "evidence_ledger_admission_review",
        },
        "read_observation_summary": {
            "schema_version": "ag96i3k_read_observation_adapter_v1",
            "record_type": "sanitized_read_observation_adapter",
            "read_posture": "read_observation_ready",
            "fetch_status": "fetched",
            "read_status": "readable",
            "http_status": 200,
            "content_type": "text/html",
            "media_type": "html",
            "title": "Standard mileage rates | Internal Revenue Service",
            "detected_updated_date": "2026-01-01",
            "extracted_text_present": True,
            "extracted_text_char_count": 1000,
            "sanitized_text_char_count": 1000,
            "extracted_text_truncated": False,
            "raw_page_text_retained": False,
        },
        "custody_metadata_summary": {
            "candidate_url_present": True,
            "candidate_domain_present": True,
            "observation_url_present": True,
            "observation_domain_present": True,
            "source_identity_present": True,
            "source_class_or_official_posture_present": True,
            "read_status_present": True,
            "extracted_text_presence_recorded": True,
            "durable_projection_omits_raw_text": True,
            "non_authoritative_flags_present": True,
        },
        "custody_metadata_complete": True,
        "non_authoritative_boundary_flags": {
            "final_evidence": False,
            "citation_eligible": False,
            "evidence_ledger_admitted": False,
            "author_activation_allowed": False,
            "evidence_ledger_intake_performed": False,
            "evidence_ledger_canonical_state_mutated": False,
            "sufficiency_judgment_rechecked": False,
            "final_answer_packet_updated": False,
        },
        "evidence_boundary": {
            "evidence_ledger_admission_review_candidate_only": True,
            "evidence_ledger_admission_performed": False,
            "evidence_ledger_intake_performed": False,
            "candidate_is_final_evidence": False,
            "candidate_is_citation_eligible": False,
            "author_or_final_answer_activation_allowed": False,
        },
        "final_evidence": False,
        "citation_eligible": False,
        "evidence_ledger_admitted": False,
        "author_activation_allowed": False,
    }
    _deep_update(payload, overrides)
    return payload


def _deep_update(target: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
