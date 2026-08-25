"""EvidenceLedger containment for source-class observability telemetry.

Test path/node id:
    tests/test_evidence_ledger_telemetry_helper_containment_01.py
Proof class: owner-invariant / lifecycle regression
Validation bucket: phase_focus
Why this bucket: Stage-B telemetry-vs-canonical-authority repair for PR #600.
Why not fast_pr: phase-detail EvidenceLedger authority check, not a cheap broad sentinel.
Promotion/demotion: remain phase_focus unless later promoted as a durable ledger sentinel.
"""

from __future__ import annotations

from typing import Any

from core.evidence_ledger import (
    CandidateCustodyKind,
    CandidateDisposition,
    EvidenceCustodyGapType,
    EvidenceLedger,
    SourceRequirementStatus,
    build_evidence_ledger_observation_from_runtime,
)
from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
    reduce_final_evidence_bundle_into_evidence_ledger,
    reduce_pre_recovery_source_obligations_into_evidence_ledger,
    reduce_run_contract_requirements_into_evidence_ledger,
)
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.official_current_source_custody import (
    OfficialCurrentCustodyStatus,
    OfficialCurrentSourceCustodyState,
)
from core.run_authority_contract_templates import build_deterministic_contract
from core.run_kernel import RunKernel
from tests.test_ag_evidence_ledger_candidate_custody_01 import _packet

CANONICAL_OFFICIAL_REQUIREMENT_ID = "run-contract:official_current_rules"
TELEMETRY_REQUIREMENT_ID = "official_current_source:official_current_rules"


def _requirement(projection: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    cleaned = requirement_id.replace("-", "_")
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] in {requirement_id, cleaned}:
            return requirement
    raise AssertionError(f"missing requirement {requirement_id}")


def _candidate(projection: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    cleaned = candidate_id.replace("-", "_")
    for candidate in projection["candidate_records"]:
        if candidate["candidate_id"] in {candidate_id, cleaned}:
            return candidate
    raise AssertionError(f"missing candidate {candidate_id}")


def _accepted_telemetry(*, candidate_id: str) -> dict[str, Any]:
    state = OfficialCurrentSourceCustodyState.for_required_source_classes(
        ["official_current_rules"]
    )
    state = state.record_candidate_returned(
        TELEMETRY_REQUIREMENT_ID,
        candidate_id=candidate_id,
        attempt_id="telemetry",
    ).record_candidate_disposition(
        TELEMETRY_REQUIREMENT_ID,
        status=OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED,
        candidate_id=candidate_id,
        reason="telemetry_claimed_candidate_accepted",
        attempt_id="telemetry",
    )
    return {"official_current_source_custody": state.to_dict()}


def _reduce_identity(
    kernel: RunKernel,
    *,
    candidate_id: str,
    url: str,
    title: str,
) -> dict[str, Any]:
    action = kernel.authorize_evidence_ledger_reduction(
        inputs={"observation_source": "retrieval_observation"}
    )
    result = execute_evidence_ledger_reduction_action(
        action,
        payload={
            "observation_id": f"{kernel.state.run_id}:candidate-identity",
            "observation_source": "retrieval_observation",
            "candidates": [
                {
                    "candidate_id": candidate_id,
                    "url": url,
                    "title": title,
                    "record_kind": CandidateCustodyKind.FACT.value,
                    "disposition": CandidateDisposition.OBSERVED.value,
                    "eligible_for_stronger_obligation": False,
                }
            ],
        },
    )
    kernel.reduce(result.observation)
    return kernel.state.evidence_ledger.to_projection().to_dict()


def test_source_class_telemetry_cannot_promote_canonical_ledger_authority() -> None:
    kernel = RunKernel.start(
        run_id="telemetry-helper-containment",
        request_id="telemetry-helper-containment:request",
    )
    contract = build_deterministic_contract(
        query="What is the current official filing fee?",
        mode="Balanced",
    ).to_projection()
    reduce_run_contract_requirements_into_evidence_ledger(
        run_kernel=kernel,
        run_id=kernel.state.run_id,
        run_contract_projection=contract,
        observation_id_suffix="run-contract",
        authorization_observation_source="run_authority_contract",
    )

    _throwaway_kernel, _candidate_packet, fetch_read_packet = _packet()
    reference = fetch_read_packet["reference_records"][0]
    candidate_id = str(reference["candidate_id"])
    identity = _reduce_identity(
        kernel,
        candidate_id=candidate_id,
        url=str(reference["candidate_url"]),
        title=str(reference.get("candidate_title") or "identity-only candidate"),
    )
    identity_candidate = _candidate(identity, candidate_id)
    assert identity_candidate["fact_disposition"] == CandidateDisposition.OBSERVED.value
    assert identity_candidate["eligible_for_stronger_obligation"] is False
    assert _requirement(identity, CANONICAL_OFFICIAL_REQUIREMENT_ID)[
        "status"
    ] != SourceRequirementStatus.SATISFIED.value

    telemetry = _accepted_telemetry(candidate_id=candidate_id)
    builder_payload = build_evidence_ledger_observation_from_runtime(
        observation_id=f"{kernel.state.run_id}:builder-inspect",
        observation_source="pre_recovery_source_obligation",
        source_class_recovery_telemetry=telemetry,
        final_top_evidence=[],
    ).to_dict()
    assert builder_payload["requirements"] == []
    assert builder_payload["requirement_links"] == []
    assert builder_payload["aggregate_counts"] == {}
    assert builder_payload["candidates"]
    assert all(
        record["record_kind"] == CandidateCustodyKind.HELPER_ASSESSMENT.value
        for record in builder_payload["candidates"]
    )
    assert all(
        record.get("eligible_for_stronger_obligation") in (None, False)
        for record in builder_payload["candidates"]
    )

    after_telemetry = reduce_pre_recovery_source_obligations_into_evidence_ledger(
        run_kernel=kernel,
        run_id=kernel.state.run_id,
        source_class_recovery_telemetry=telemetry,
        final_top_evidence=[],
    )
    telemetry_candidate = _candidate(after_telemetry, candidate_id)
    official_requirement = _requirement(
        after_telemetry,
        CANONICAL_OFFICIAL_REQUIREMENT_ID,
    )
    requirement_ids = {
        requirement["requirement_id"]
        for requirement in after_telemetry["source_requirements"]
    }
    telemetry_links = [
        link
        for link in after_telemetry["requirement_links"]
        if link.get("link_reason") == "official_current_source_custody_record"
    ]
    helper_records = [
        record
        for record in after_telemetry["custody_records"]
        if record["candidate_id"] == telemetry_candidate["candidate_id"]
        and record["observation_id"].endswith("pre_recovery")
    ]

    assert telemetry_candidate["fact_disposition"] not in {
        CandidateDisposition.ACCEPTED.value,
        CandidateDisposition.PARTIALLY_ACCEPTED.value,
    }
    assert telemetry_candidate["eligible_for_stronger_obligation"] is False
    assert telemetry_candidate.get("source_class") != "official_current_rules"
    assert telemetry_candidate.get("source_tier") != "official"
    assert official_requirement["status"] != SourceRequirementStatus.SATISFIED.value
    assert official_requirement["status"] != (
        SourceRequirementStatus.PARTIALLY_SATISFIED.value
    )
    assert telemetry_candidate["candidate_id"] not in official_requirement[
        "linked_candidate_ids"
    ]
    assert TELEMETRY_REQUIREMENT_ID.replace("-", "_") not in requirement_ids
    assert telemetry_links == []
    assert helper_records
    assert all(
        record["record_kind"] == CandidateCustodyKind.HELPER_ASSESSMENT.value
        for record in helper_records
    )
    assert EvidenceCustodyGapType.HELPER_CONTROLLER_ASSESSMENT_NOT_PROMOTABLE.value in {
        gap["gap_type"] for gap in after_telemetry["custody_gaps"] if isinstance(gap, dict)
    }

    after_fetch_read = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=kernel,
        fetch_read_content_packet=fetch_read_packet,
        observation_id=f"{kernel.state.run_id}:fetch-read",
        linked_requirement_ids=[CANONICAL_OFFICIAL_REQUIREMENT_ID],
    )
    fetch_read_candidate = _candidate(after_fetch_read, candidate_id)
    fetch_read_requirement = _requirement(
        after_fetch_read,
        CANONICAL_OFFICIAL_REQUIREMENT_ID,
    )
    fetch_read_fact_records = [
        record
        for record in after_fetch_read["custody_records"]
        if record["candidate_id"] == fetch_read_candidate["candidate_id"]
        and record["record_kind"] == CandidateCustodyKind.FACT.value
    ]
    assert fetch_read_fact_records
    assert fetch_read_candidate["fact_disposition"] == (
        CandidateDisposition.OBSERVED.value
    )
    assert fetch_read_candidate["eligible_for_stronger_obligation"] is False
    assert fetch_read_requirement["status"] != SourceRequirementStatus.SATISFIED.value

    after_final = reduce_final_evidence_bundle_into_evidence_ledger(
        run_kernel=kernel,
        run_id=kernel.state.run_id,
        final_top_evidence=[
            {
                "candidate_id": fetch_read_candidate["candidate_id"],
                "url": reference["candidate_url"],
                "title": reference.get("candidate_title") or "official current rule",
                "source_class": "official_current_rules",
                "source_tier": "official",
                "currentness_signal": "current",
                "readable_status": "readable",
                "fetchable_status": "fetchable",
                "eligible_for_stronger_obligation": True,
            }
        ],
    )
    final_candidate = _candidate(after_final, candidate_id)
    final_requirement = _requirement(after_final, CANONICAL_OFFICIAL_REQUIREMENT_ID)
    assert final_candidate["fact_disposition"] == CandidateDisposition.ACCEPTED.value
    assert final_candidate["eligible_for_stronger_obligation"] is True
    assert final_candidate["source_class"] == "official_current_rules"
    assert final_requirement["status"] == SourceRequirementStatus.SATISFIED.value
    assert final_candidate["candidate_id"] in final_requirement["linked_candidate_ids"]

    packet = build_final_answer_packet(
        run_id=kernel.state.run_id,
        final_evidence=[
            {
                "candidate_id": final_candidate["candidate_id"],
                "url": reference["candidate_url"],
                "title": reference.get("candidate_title") or "official current rule",
            }
        ],
        source_obligation_projection=after_final,
        evidence_sufficient=True,
    )
    assert (
        packet.official_current_custody_summary["custody_authority"]
        == "RunKernel.EvidenceLedger"
    )


def test_telemetry_helper_cannot_launder_authority_into_later_weak_fact() -> None:
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        {
            "observation_id": "launder-contract",
            "observation_source": "run_authority_contract",
            "requirements": [
                {
                    "requirement_id": CANONICAL_OFFICIAL_REQUIREMENT_ID,
                    "requirement_kind": "official_current",
                    "origin_ref": "RunKernel.RunAuthorityContract:launder",
                    "required_source_class": "official_current_rules",
                    "required_source_tier": "official",
                    "required_currentness": "current",
                }
            ],
        }
    )
    ledger.reduce_observation(
        {
            "observation_id": "launder-helper",
            "observation_source": "pre_recovery_source_obligation",
            "candidates": [
                {
                    "candidate_id": "weak-explainer",
                    "url": "https://blog.example.com/weak-explainer",
                    "title": "Secondary explainer",
                    "record_kind": CandidateCustodyKind.HELPER_ASSESSMENT.value,
                    "disposition": CandidateDisposition.ACCEPTED.value,
                    "source_class": "official_current_rules",
                    "source_tier": "official",
                    "currentness_signal": "current",
                    "eligible_for_stronger_obligation": True,
                    "requirement_id": CANONICAL_OFFICIAL_REQUIREMENT_ID,
                    "readable_status": "readable",
                }
            ],
            "requirement_links": [
                {
                    "requirement_id": CANONICAL_OFFICIAL_REQUIREMENT_ID,
                    "candidate_id": "weak-explainer",
                    "link_reason": "official_current_source_custody_record",
                    "link_status": OfficialCurrentCustodyStatus.CANDIDATE_ACCEPTED.value,
                }
            ],
        }
    )
    ledger.reduce_observation(
        {
            "observation_id": "launder-weak-fact",
            "observation_source": "retrieval_observation",
            "candidates": [
                {
                    "candidate_id": "weak-explainer",
                    "url": "https://blog.example.com/weak-explainer",
                    "title": "Secondary explainer",
                    "record_kind": CandidateCustodyKind.FACT.value,
                    "disposition": CandidateDisposition.ACCEPTED.value,
                    "readable_status": "readable",
                }
            ],
        }
    )

    projection = ledger.to_projection().to_dict()
    candidate = _candidate(projection, "weak-explainer")
    requirement = _requirement(projection, CANONICAL_OFFICIAL_REQUIREMENT_ID)
    assert candidate["fact_disposition"] == CandidateDisposition.ACCEPTED.value
    assert candidate["eligible_for_stronger_obligation"] is False
    assert candidate.get("source_class") != "official_current_rules"
    assert candidate.get("source_tier") != "official"
    assert candidate.get("currentness_signal") != "current"
    assert requirement["status"] != SourceRequirementStatus.SATISFIED.value
    assert requirement["status"] != SourceRequirementStatus.PARTIALLY_SATISFIED.value
    assert candidate["candidate_id"] not in requirement["linked_candidate_ids"]
    assert all(
        link.get("link_reason") != "official_current_source_custody_record"
        for link in projection["requirement_links"]
    )
