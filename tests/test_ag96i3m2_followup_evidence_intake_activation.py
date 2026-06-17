from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.evidence_ledger import SourceRequirementStatus
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_evidence_intake_runtime import (
    AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
    execute_followup_evidence_intake_action,
)
from core.run_kernel import (
    EVIDENCE_LEDGER_STAGE,
    FOLLOWUP_EVIDENCE_INTAKE_STAGE,
    RunKernel,
    RunKernelTransitionError,
)
from tests.helpers.followup_fixture_spine import run_followup_through_execution

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "ag96i3m2-followup-intake"


def test_valid_bound_admission_review_intake_mutates_canonical_evidence_ledger() -> None:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    before = _closed_surface_snapshot(kernel)

    action, _result = _execute_m2_intake(kernel)
    after = kernel.state.evidence_ledger.to_projection().to_dict()

    assert action.action_type.value == "followup_evidence_intake"
    assert action.inputs["evidence_ledger_intake_mode"] == (
        AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
    )
    assert after["candidate_count"] == 1
    assert after["requirement_count"] == 1
    assert after["custody_record_count"] == 1
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE] == after
    assert after["final_evidence_refs"] == []
    assert after["observation_refs"] == [
        {
            "observation_id": "ag96i3m2:obs:001",
            "source": "ag96i3m1_admission_review_intake_adapter",
        }
    ]
    candidate = after["candidate_records"][0]
    assert candidate["candidate_id"] == "irs_current_rules_2026"
    assert candidate["fact_disposition"] == "accepted"
    assert candidate["final_evidence_eligible"] is False
    requirement = _requirement(after, "source_requirement:requirement_official_current")
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value
    assert requirement["required_source_class"] == "official_current_rules"

    state = kernel.state.followup_evidence_intake_state
    projection = kernel.state.followup_evidence_intake_projection
    assert state["canonical_state"] is True
    assert state["runtime_evidence_intake_occurred"] is True
    assert state["ag96i3m1_adapter_projection"]["accepted"] is True
    assert state["citation_eligible"] is False
    assert state["final_evidence_satisfied"] is False
    assert state["author_activation_allowed"] is False
    assert state["sufficiency_judgment_rechecked"] is False
    assert state["final_answer_packet_updated"] is False
    assert projection["runtime_evidence_intake_occurred"] is True
    assert projection["citation_eligible"] is False
    assert projection["author_activation_allowed"] is False
    assert kernel.state.projections[FOLLOWUP_EVIDENCE_INTAKE_STAGE] == projection
    assert _closed_surface_snapshot(kernel) == before


@pytest.mark.parametrize(
    ("binding_overrides", "match"),
    [
        ({"candidate_id": "other_candidate"}, "EvidenceLedgerIntakeBinding"),
        ({"requirement_id": "source_requirement:other"}, "EvidenceLedgerIntakeBinding"),
        ({"source_obligation": "reputable_secondary"}, "EvidenceLedgerIntakeBinding"),
        ({"observation_id": "ag96i3m2:obs:other"}, "EvidenceLedgerIntakeBinding"),
        ({"observation_ref": "ag96i3l:admission-review:other"}, "EvidenceLedgerIntakeBinding"),
    ],
)
def test_m2_binding_mismatches_are_rejected_without_ledger_mutation(
    binding_overrides: dict[str, Any],
    match: str,
) -> None:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    before = kernel.state.evidence_ledger.to_projection().to_dict()
    action = _authorize_m2(kernel)

    with pytest.raises(PermissionError, match=match):
        execute_followup_evidence_intake_action(
            action,
            followup_execution_state=kernel.state.followup_execution_state,
            evidence_ledger_projection=before,
            admission_review_candidate=_ready_candidate(),
            evidence_ledger_intake_binding=_binding_dict(**binding_overrides),
        )

    assert kernel.state.evidence_ledger.to_projection().to_dict() == before


def test_m2_candidate_id_mismatch_is_rejected_without_ledger_mutation() -> None:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    before = kernel.state.evidence_ledger.to_projection().to_dict()
    action = _authorize_m2(kernel)

    with pytest.raises(PermissionError, match="admission-review candidate"):
        execute_followup_evidence_intake_action(
            action,
            followup_execution_state=kernel.state.followup_execution_state,
            evidence_ledger_projection=before,
            admission_review_candidate=_ready_candidate(candidate_id="other_candidate"),
            evidence_ledger_intake_binding=_binding_dict(),
        )

    assert kernel.state.evidence_ledger.to_projection().to_dict() == before


def test_m2_reducer_rejects_mutated_payload_binding_before_ledger_mutation() -> None:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    before = kernel.state.evidence_ledger.to_projection().to_dict()
    action = _authorize_m2(kernel)
    result = execute_followup_evidence_intake_action(
        action,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=before,
        admission_review_candidate=_ready_candidate(),
        evidence_ledger_intake_binding=_binding_dict(),
    )
    payload = deepcopy(result.observation.payload["followup_evidence_intake_state"])
    payload["ag96i3m2_evidence_ledger_intake_binding_payload"][
        "candidate_id"
    ] = "other_candidate"
    bad_observation = result.observation.__class__(
        observation_id=result.observation.observation_id,
        run_id=result.observation.run_id,
        action_id=result.observation.action_id,
        stage=result.observation.stage,
        observation_type=result.observation.observation_type,
        status=result.observation.status,
        payload={"followup_evidence_intake_state": payload},
        sequence=result.observation.sequence,
    )

    with pytest.raises(RunKernelTransitionError, match="EvidenceLedgerIntakeBinding"):
        kernel.reduce(bad_observation)

    assert kernel.state.evidence_ledger.to_projection().to_dict() == before


@pytest.mark.parametrize(
    "candidate_overrides",
    [
        {
            "admission_review_candidate_ready": False,
            "admission_review_status": "currentness_unclear",
        },
        {"blocker_codes": ["currentness_unclear"]},
    ],
)
def test_non_ready_or_blocked_ag96i3l_candidates_are_rejected(
    candidate_overrides: dict[str, Any],
) -> None:
    candidate = _ready_candidate(**candidate_overrides)
    kernel = run_followup_through_execution(run_id=RUN_ID)
    action = _authorize_m2(kernel, candidate=candidate)
    before = kernel.state.evidence_ledger.to_projection().to_dict()

    with pytest.raises(PermissionError, match="adapter rejected"):
        execute_followup_evidence_intake_action(
            action,
            followup_execution_state=kernel.state.followup_execution_state,
            evidence_ledger_projection=before,
            admission_review_candidate=candidate,
            evidence_ledger_intake_binding=_binding_dict(),
        )

    assert kernel.state.evidence_ledger.to_projection().to_dict() == before


def test_missing_evidence_ledger_intake_binding_is_rejected() -> None:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    action = _authorize_m2(kernel)
    before = kernel.state.evidence_ledger.to_projection().to_dict()

    with pytest.raises(PermissionError, match="EvidenceLedgerIntakeBinding"):
        execute_followup_evidence_intake_action(
            action,
            followup_execution_state=kernel.state.followup_execution_state,
            evidence_ledger_projection=before,
            admission_review_candidate=_ready_candidate(),
            evidence_ledger_intake_binding=None,
        )

    assert kernel.state.evidence_ledger.to_projection().to_dict() == before


def test_invalid_official_current_rules_mapping_is_rejected() -> None:
    binding = _binding_dict(
        official_current_rules={
            "source_obligation": "official_current",
            "requirement_kind": "official_current",
            "required_source_class": "reputable_secondary",
            "required_source_tier": "secondary",
            "required_currentness": "current",
            "requirement_id": "source_requirement:requirement_official_current",
        }
    )
    kernel = run_followup_through_execution(run_id=RUN_ID)
    action = _authorize_m2(kernel, binding=binding)
    before = kernel.state.evidence_ledger.to_projection().to_dict()

    with pytest.raises(PermissionError, match="adapter rejected"):
        execute_followup_evidence_intake_action(
            action,
            followup_execution_state=kernel.state.followup_execution_state,
            evidence_ledger_projection=before,
            admission_review_candidate=_ready_candidate(),
            evidence_ledger_intake_binding=binding,
        )

    assert kernel.state.evidence_ledger.to_projection().to_dict() == before


@pytest.mark.parametrize(
    "binding_overrides",
    [
        {"citation_eligible": True},
        {"final_evidence": True},
        {"author_activation_allowed": True},
    ],
)
def test_downstream_activation_flags_are_rejected(
    binding_overrides: dict[str, Any],
) -> None:
    binding = _binding_dict(**binding_overrides)
    kernel = run_followup_through_execution(run_id=RUN_ID)
    action = _authorize_m2(kernel, binding=binding)
    before = kernel.state.evidence_ledger.to_projection().to_dict()

    with pytest.raises(PermissionError, match="requires .*False"):
        execute_followup_evidence_intake_action(
            action,
            followup_execution_state=kernel.state.followup_execution_state,
            evidence_ledger_projection=before,
            admission_review_candidate=_ready_candidate(),
            evidence_ledger_intake_binding=binding,
        )

    assert kernel.state.evidence_ledger.to_projection().to_dict() == before


def test_raw_text_verifier_excerpts_provider_payloads_are_rejected_before_reduction() -> None:
    sentinel = "ag96i3m2-private-sentinel"
    candidate = _ready_candidate(
        raw_text=sentinel,
        provider_payload={"payload": sentinel},
        verification_summary={
            "verification_status": "verified_official_current_relevance",
            "official_source_status": "official_source_supported",
            "source_obligation": "official_current",
            "currentness_posture": "currentness_supported",
            "relevance_posture": "relevance_supported",
            "supported_excerpt_fragments": [sentinel],
        },
    )
    kernel = run_followup_through_execution(run_id=RUN_ID)
    action = _authorize_m2(kernel)
    before = kernel.state.evidence_ledger.to_projection().to_dict()

    with pytest.raises(PermissionError, match="adapter rejected"):
        execute_followup_evidence_intake_action(
            action,
            followup_execution_state=kernel.state.followup_execution_state,
            evidence_ledger_projection=before,
            admission_review_candidate=candidate,
            evidence_ledger_intake_binding=_binding_dict(),
        )

    assert kernel.state.evidence_ledger.to_projection().to_dict() == before


def test_binding_raw_private_extras_are_stripped_before_runtime_state_and_adapter_use() -> None:
    sentinel = "ag96i3m2-binding-private-sentinel"
    binding = _binding_dict(
        raw_text=sentinel,
        verifier_text=sentinel,
        supported_excerpt_fragments=[sentinel],
        provider_payload={"payload": sentinel},
        raw_prompt=sentinel,
        full_trace={"trace": sentinel},
    )
    kernel = run_followup_through_execution(run_id=RUN_ID)
    action = _authorize_m2(kernel, binding=binding)
    result = execute_followup_evidence_intake_action(
        action,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        admission_review_candidate=_ready_candidate(),
        evidence_ledger_intake_binding=binding,
    )

    serialized_result = json.dumps(
        {
            "record": result.record.to_dict(),
            "observation": result.observation.to_dict(),
        },
        sort_keys=True,
    )
    assert sentinel not in serialized_result
    state_payload = result.record.to_dict()
    persisted_binding = state_payload["ag96i3m2_evidence_ledger_intake_binding_payload"]
    for forbidden_key in (
        "raw_text",
        "verifier_text",
        "supported_excerpt_fragments",
        "provider_payload",
        "raw_prompt",
        "full_trace",
    ):
        assert forbidden_key not in persisted_binding

    kernel.reduce(result.observation)

    serialized_state = json.dumps(
        {
            "state": kernel.state.followup_evidence_intake_state,
            "projection": kernel.state.followup_evidence_intake_projection,
            "ledger": kernel.state.evidence_ledger.to_projection().to_dict(),
        },
        sort_keys=True,
    )
    assert sentinel not in serialized_state
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    assert ledger["candidate_count"] == 1
    assert ledger["candidate_records"][0]["candidate_id"] == "irs_current_rules_2026"


def test_duplicate_m2_observation_id_remains_idempotent() -> None:
    kernel = run_followup_through_execution(run_id=RUN_ID)

    _execute_m2_intake(kernel)
    after_first = deepcopy(kernel.state.evidence_ledger.to_projection().to_dict())
    _execute_m2_intake(kernel)
    after_second = kernel.state.evidence_ledger.to_projection().to_dict()

    assert after_second == after_first
    assert after_second["candidate_count"] == 1
    assert after_second["custody_record_count"] == 1
    assert after_second["observation_refs"] == [
        {
            "observation_id": "ag96i3m2:obs:001",
            "source": "ag96i3m1_admission_review_intake_adapter",
        }
    ]


def test_static_guards_keep_m2_closed_to_live_and_pipeline_surfaces() -> None:
    module_paths = [
        ROOT / "core" / "followup_evidence_intake_runtime.py",
        ROOT / "core" / "followup_runkernel_reducers.py",
    ]
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.prompts",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
    }
    for path in module_paths:
        source = path.read_text(encoding="utf-8")
        if path.name == "followup_evidence_intake_runtime.py":
            assert passive_module_static_guard(source, module_name=path.name) == ()
        assert _imports(path).isdisjoint(forbidden_imports)
        for forbidden in (
            "requests.",
            "httpx.",
            "urlopen",
            "ask_model",
            "select_providers",
            "format_citation",
            "AuthorExecutor(",
        ):
            assert forbidden not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3m2" not in pipeline_source.casefold()
    assert "evidence_ledger_intake_adapter" not in pipeline_source


def _authorize_m2(
    kernel: RunKernel,
    *,
    candidate: dict[str, Any] | None = None,
    binding: dict[str, Any] | None = None,
) -> Any:
    return kernel.authorize_followup_evidence_intake(
        reason="ag96i3m2_followup_admission_review_evidence_intake",
        ag96i3l_admission_review_candidate=candidate or _ready_candidate(),
        evidence_ledger_intake_binding=binding or _binding_dict(),
    )


def _execute_m2_intake(
    kernel: RunKernel,
    *,
    candidate: dict[str, Any] | None = None,
    binding: dict[str, Any] | None = None,
) -> tuple[Any, Any]:
    candidate = candidate or _ready_candidate()
    binding = binding or _binding_dict()
    action = _authorize_m2(kernel, candidate=candidate, binding=binding)
    result = execute_followup_evidence_intake_action(
        action,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        admission_review_candidate=candidate,
        evidence_ledger_intake_binding=binding,
    )
    kernel.reduce(result.observation)
    return action, result


def _binding_dict(**overrides: Any) -> dict[str, Any]:
    payload = {
        "requirement_id": "source_requirement:requirement_official_current",
        "candidate_id": "irs_current_rules_2026",
        "observation_id": "ag96i3m2:obs:001",
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
            "requirement_id": "source_requirement:requirement_official_current",
        },
        "origin_phase": "ag96i3m2",
        "origin_action": "followup_evidence_intake",
        "origin_record_type": "evidence_ledger_admission_review_candidate_diagnostics",
        "origin_schema_version": "ag96i3l_evidence_ledger_admission_review_diagnostics_v1",
        "idempotency_key": "ag96i3m2:irs-current-rules-2026",
        "deduplication_basis": (
            "requirement_id",
            "candidate_id",
            "observation_ref",
        ),
        "final_evidence": False,
        "citation_eligible": False,
        "author_activation_allowed": False,
    }
    _deep_update(payload, overrides)
    return payload


def _ready_candidate(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "ag96i3l_evidence_ledger_admission_review_diagnostics_v1",
        "record_type": "evidence_ledger_admission_review_candidate_diagnostics",
        "candidate_id": "irs_current_rules_2026",
        "observation_ref": "ag96i3l:admission-review:001",
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


def _requirement(projection: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement
    raise AssertionError(f"missing requirement {requirement_id}")


def _closed_surface_snapshot(kernel: RunKernel) -> dict[str, Any]:
    return {
        "run_contract": deepcopy(kernel.state.run_contract),
        "run_contract_projection": deepcopy(kernel.state.run_contract_projection),
        "search_work_plan": deepcopy(kernel.state.search_work_plan),
        "search_work_plan_projection": deepcopy(kernel.state.search_work_plan_projection),
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
