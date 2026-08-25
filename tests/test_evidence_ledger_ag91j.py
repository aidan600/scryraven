from __future__ import annotations

import json
from pathlib import Path

from core.allocation_result_candidate_custody import (
    build_allocation_result_candidate_custody_projection,
)
from core.answer_contract_runtime_handoff import (
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)
from core.controller_evidence_ledger import build_controller_evidence_ledger
from core.evidence_ledger import (
    EvidenceCustodyGapType,
    EvidenceLedger,
    SourceRequirementStatus,
)
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.run_kernel import EVIDENCE_LEDGER_STAGE, RunKernel

ROOT = Path(__file__).resolve().parents[1]


def _projection_from_observation(observation: dict) -> dict:
    ledger = EvidenceLedger()
    ledger.reduce_observation(observation)
    return ledger.to_projection().to_dict()


def _requirement(projection: dict, requirement_id: str) -> dict:
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement
    raise AssertionError(f"missing requirement {requirement_id}")


def _gap_types(projection: dict) -> set[str]:
    return {
        gap["gap_type"]
        for gap in projection["custody_gaps"]
        if isinstance(gap, dict)
    }


def _official_requirement() -> dict:
    return {
        "requirement_id": "official_current_source:official_current_rules",
        "requirement_kind": "official_current",
        "origin_ref": "answer_contract:current_official_rules",
        "required_source_class": "official_current_rules",
        "required_source_tier": "official",
        "required_currentness": "current",
    }


def _official_candidate(**overrides: object) -> dict:
    candidate = {
        "candidate_id": "irs-current-rules",
        "url": "https://www.irs.gov/current-rule",
        "title": "Current official rule",
        "domain": "irs.gov",
        "provider_name": "offline_fixture",
        "retrieval_pass_id": "retrieval-pass-1",
        "query_ref": "current official rule",
        "action_ref": "action-1",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
        "readable_status": "readable",
        "fetchable_status": "fetchable",
        "disposition": "accepted",
        "record_kind": "fact",
        "requirement_id": "official_current_source:official_current_rules",
        "eligible_for_stronger_obligation": True,
        "final_evidence_eligible": True,
    }
    candidate.update(overrides)
    return candidate


def test_records_candidate_identity_custody_and_excludes_sensitive_payloads() -> None:
    projection = _projection_from_observation(
        {
            "observation_id": "obs-1",
            "observation_source": "retrieval_observation",
            "requirements": [_official_requirement()],
            "candidates": [
                _official_candidate(
                    raw_provider_payload={
                        "payload_marker": "fake-provider-sentinel-should-not-survive"
                    },
                    raw_prompt="raw prompt should not survive",
                    snippet="full snippet should not survive",
                    text="full source text should not survive",
                    db_row={"id": 1},
                    output_packet={"private": True},
                )
            ],
        }
    )

    assert projection["owner"] == "RunKernel.EvidenceLedger"
    assert projection["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["storage_only"] is False
    assert projection["candidate_count"] == 1
    candidate = projection["candidate_records"][0]
    assert candidate["candidate_id"] == "irs_current_rules"
    assert candidate["url"] == "https://www.irs.gov/current-rule"
    assert candidate["provider_name"] == "offline_fixture"
    assert candidate["eligible_for_stronger_obligation"] is True
    assert candidate["fact_disposition"] == "accepted"
    requirement = _requirement(
        projection,
        "official_current_source:official_current_rules",
    )
    assert requirement["linked_candidate_ids"] == ["irs_current_rules"]
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value

    serialized = json.dumps(projection, sort_keys=True).casefold()
    for forbidden in (
        "raw prompt",
        "raw_provider_payload",
        "full source text",
        "full snippet",
        "fake-provider-sentinel-should-not-survive",
        "db_row",
        "output_packet",
    ):
        assert forbidden not in serialized


def test_helper_assessments_and_proposals_do_not_promote_to_facts() -> None:
    projection = _projection_from_observation(
        {
            "observation_id": "obs-helper",
            "observation_source": "helper_controller_assessment",
            "requirements": [_official_requirement()],
            "candidates": [
                _official_candidate(
                    candidate_id="helper-accepted",
                    record_kind="helper_assessment",
                    disposition="accepted",
                ),
                _official_candidate(
                    candidate_id="proposal-accepted",
                    record_kind="proposal",
                    disposition="accepted",
                ),
            ],
        }
    )

    records = {
        record["candidate_id"]: record
        for record in projection["custody_records"]
    }
    assert records["helper_accepted"]["record_kind"] == "helper_assessment"
    assert records["proposal_accepted"]["record_kind"] == "proposal"
    helper = next(
        candidate
        for candidate in projection["candidate_records"]
        if candidate["candidate_id"] == "helper_accepted"
    )
    assert helper["fact_disposition"] == "unknown"
    assert helper["eligible_for_stronger_obligation"] is False
    assert helper.get("source_class") != "official_current_rules"
    assert helper.get("source_tier") != "official"
    requirement = _requirement(
        projection,
        "official_current_source:official_current_rules",
    )
    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert "helper_accepted" not in requirement["linked_candidate_ids"]
    assert (
        EvidenceCustodyGapType.HELPER_CONTROLLER_ASSESSMENT_NOT_PROMOTABLE.value
        in _gap_types(projection)
    )


def test_requirements_link_to_candidate_ids_and_aggregate_counts_do_not_satisfy() -> None:
    projection = _projection_from_observation(
        {
            "observation_id": "obs-aggregate",
            "observation_source": "source_tier_counts",
            "requirements": [_official_requirement()],
            "aggregate_counts": {
                "official_current_source:official_current_rules": 4,
            },
        }
    )

    requirement = _requirement(
        projection,
        "official_current_source:official_current_rules",
    )
    assert requirement["linked_candidate_ids"] == []
    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert requirement["reason"] == "aggregate_counts_cannot_satisfy_custody"
    assert requirement["aggregate_counts_insufficient"] is True
    assert projection["aggregate_counts_are_authoritative_for_custody"] is False
    assert EvidenceCustodyGapType.LEGACY_AGGREGATE_ONLY_PATH.value in _gap_types(
        projection
    )


def test_weak_secondary_stale_and_off_topic_sources_cannot_satisfy_strong_requirements() -> None:
    for candidate in (
        _official_candidate(
            candidate_id="secondary-explainer",
            source_tier="secondary",
            source_class="reputable_secondary",
            eligible_for_stronger_obligation=True,
        ),
        _official_candidate(
            candidate_id="stale-official",
            currentness_signal="stale",
            eligible_for_stronger_obligation=True,
        ),
        _official_candidate(
            candidate_id="forum-context",
            source_tier="social_or_forum",
            source_class="social_signal",
            currentness_signal="off_topic",
            eligible_for_stronger_obligation=True,
        ),
    ):
        projection = _projection_from_observation(
            {
                "observation_id": f"obs-{candidate['candidate_id']}",
                "observation_source": "retrieval_observation",
                "requirements": [_official_requirement()],
                "candidates": [candidate],
            }
        )
        requirement = _requirement(
            projection,
            "official_current_source:official_current_rules",
        )
        assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
        assert EvidenceCustodyGapType.MISSING_SOURCE_CLASS_FIT.value in _gap_types(
            projection
        )


def test_missing_official_current_candidate_creates_explicit_gap() -> None:
    projection = _projection_from_observation(
        {
            "observation_id": "obs-missing",
            "observation_source": "answer_contract_source_obligation",
            "requirements": [_official_requirement()],
        }
    )

    requirement = _requirement(
        projection,
        "official_current_source:official_current_rules",
    )
    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert requirement["reason"] == "missing_official_current_candidate"
    assert (
        EvidenceCustodyGapType.MISSING_OFFICIAL_CURRENT_CANDIDATE.value
        in _gap_types(projection)
    )


def test_final_evidence_without_ledger_custody_is_compatibility_gap() -> None:
    projection = _projection_from_observation(
        {
            "observation_id": "obs-final",
            "observation_source": "final_evidence_bundle",
            "final_evidence": [
                {
                    "source_id": 1,
                    "url": "https://example.com/selected",
                    "title": "Selected evidence",
                    "text": "raw full text does not become custody",
                }
            ],
        }
    )

    assert (
        EvidenceCustodyGapType.FINAL_EVIDENCE_SELECTED_WITHOUT_LEDGER_CUSTODY.value
        in _gap_types(projection)
    )
    assert projection["compatibility"]["final_evidence_compatibility_gap_count"] == 1
    assert "raw full text" not in json.dumps(projection).casefold()


def test_run_kernel_reduces_ledger_into_canonical_run_state_projection() -> None:
    kernel = RunKernel.start(run_id="ag91j", request_id="request-ag91j")
    action = kernel.authorize_evidence_ledger_reduction(
        inputs={"observation_source": "retrieval_observation"}
    )
    result = execute_evidence_ledger_reduction_action(
        action,
        payload={
            "observation_id": "obs-kernel",
            "observation_source": "retrieval_observation",
            "requirements": [_official_requirement()],
            "candidates": [_official_candidate()],
        },
    )

    kernel.reduce(result.observation)

    canonical = kernel.state.evidence_ledger.to_projection().to_dict()
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE] == canonical
    trace_projection = kernel.state.to_trace_projection().to_dict()
    assert trace_projection["evidence_ledger"] == canonical
    stage_projection = trace_projection["projections"][EVIDENCE_LEDGER_STAGE]
    assert stage_projection["owner"] == "RunKernel.EvidenceLedger"
    assert stage_projection["candidate_count"] == canonical["candidate_count"]
    assert stage_projection["requirement_count"] == canonical["requirement_count"]


def test_answer_contract_handoff_consumes_ledger_source_requirements_over_aggregates() -> None:
    projection = _projection_from_observation(
        {
            "observation_id": "obs-contract",
            "observation_source": "source_obligation",
            "requirements": [_official_requirement()],
            "aggregate_counts": {
                "official_current_source:official_current_rules": 2,
            },
        }
    )

    result = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(
            query="What is the current official rule?",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"official": 99},
            evidence_ledger_projection=projection,
        )
    )

    assert (
        "official_current_rules"
        in result.state.evidence_state_summary.source_classes_missing
    )
    assert (
        "official_current_rules"
        in result.fulfillment_handoff.unfulfilled_source_classes
    )

    satisfied_projection = _projection_from_observation(
        {
            "observation_id": "obs-contract-satisfied",
            "observation_source": "source_obligation",
            "requirements": [_official_requirement()],
            "candidates": [_official_candidate()],
        }
    )
    satisfied = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(
            query="What is the current official rule?",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={},
            evidence_ledger_projection=satisfied_projection,
        )
    )
    assert (
        "official_current_rules"
        not in satisfied.state.evidence_state_summary.source_classes_missing
    )


def test_final_answer_packet_consumes_ledger_custody_and_preserves_uncustodied_gap() -> None:
    projection = _projection_from_observation(
        {
            "observation_id": "obs-final-packet",
            "observation_source": "final_evidence_bundle",
            "requirements": [_official_requirement()],
            "final_evidence": [
                {
                    "source_id": "selected-1",
                    "url": "https://example.com/uncustodied",
                    "title": "Uncustodied evidence",
                }
            ],
        }
    )

    packet = build_final_answer_packet(
        run_id="ag91j",
        final_evidence=[
            {
                "source_id": "selected-1",
                "url": "https://example.com/uncustodied",
                "title": "Uncustodied evidence",
            }
        ],
        source_obligation_projection=projection,
        evidence_sufficient=True,
    )

    assert (
        packet.official_current_custody_summary["custody_authority"]
        == "RunKernel.EvidenceLedger"
    )
    assert (
        packet.official_current_custody_summary[
            "final_evidence_compatibility_gap_count"
        ]
        == 1
    )
    assert (
        "do_not_treat_uncustodied_final_evidence_as_ledger_proof"
        in packet.prohibited_upgrades
    )


def test_static_guards_preserve_runkernel_custody_authority() -> None:
    pipeline = (ROOT / "core" / "pipeline_orchestrator.py").read_text()
    ledger = (ROOT / "core" / "evidence_ledger.py").read_text()
    lifecycle = (ROOT / "core" / "evidence_ledger_lifecycle.py").read_text()
    answer_contract = (
        ROOT / "core" / "answer_contract_runtime_handoff.py"
    ).read_text()

    assert "reduce_run_contract_requirements_into_evidence_ledger(" in pipeline
    assert "reduce_pre_recovery_source_obligations_into_evidence_ledger(" in pipeline
    assert "run_kernel.authorize_evidence_ledger_reduction(" in lifecycle
    assert "execute_evidence_ledger_reduction_action(" in lifecycle
    assert "evidence_ledger_projection=evidence_ledger_projection" in pipeline
    assert "EvidenceCandidate(" not in pipeline
    assert "SourceRequirementRecord(" not in pipeline
    assert "source_class_facts_from_evidence_ledger_projection" in answer_contract

    forbidden_runtime_calls = (
        "ask_model(",
        "process_search_queries(",
        "select_providers(",
        "ProviderPlan(",
        "requests.",
        "openai.",
        "DATABASE_URL",
    )
    for forbidden in forbidden_runtime_calls:
        assert forbidden not in ledger
        assert forbidden not in lifecycle

    assert (
        build_controller_evidence_ledger()[
            "run_kernel_compatibility_status"
        ]
        == "compatibility_only_subordinate_to_run_kernel_evidence_ledger_ag91j"
    )
    assert (
        build_allocation_result_candidate_custody_projection({})[
            "run_kernel_compatibility_status"
        ]
        == "sanitized_observation_input_for_run_kernel_evidence_ledger_ag91j"
    )
