from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from core.evidence_ledger import (
    CandidateDisposition,
    EvidenceLedger,
    build_evidence_ledger_observation_from_run_contract,
)
from core.evidence_ledger_lifecycle import (
    reduce_run_contract_requirements_into_evidence_ledger,
)
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.final_answer_packet import ClaimPosture, FinalAnswerReadinessStatus
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.run_authority_contract_runtime import execute_run_contract_synthesis_action
from core.run_authority_contract_templates import build_deterministic_contract
from core.run_authority_projection_refs import (
    canonical_search_judgment_projection,
    canonical_sufficiency_judgment_projection,
    compact_search_judgment_ref,
    compact_sufficiency_judgment_ref,
    is_canonical_search_judgment_projection,
    is_canonical_sufficiency_judgment_projection,
)
from core.run_authority_search_judgment_adapter import (
    build_search_judgment_input_from_runtime,
)
from core.run_authority_sufficiency import RunSufficiencyJudgmentInput
from core.run_authority_sufficiency_adapter import (
    build_sufficiency_judgment_input_from_runtime,
)
from core.run_authority_sufficiency_validation import (
    build_deterministic_sufficiency_judgment,
)
from core.run_kernel import EVIDENCE_LEDGER_STAGE, RunKernel

ROOT = Path(__file__).resolve().parents[1]


def _contract(query: str) -> dict[str, Any]:
    return build_deterministic_contract(query=query, mode="Balanced").to_projection()


def _candidate(
    *,
    candidate_id: str = "C1",
    source_class: str = "official_current_rules",
    source_tier: str = "official",
    currentness: str = "current",
    disposition: str = CandidateDisposition.ACCEPTED.value,
    eligible: bool = True,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "url": f"https://example.test/{candidate_id}",
        "title": candidate_id,
        "source_class": source_class,
        "source_tier": source_tier,
        "currentness_signal": currentness,
        "readable_status": "readable",
        "fetchable_status": "fetchable",
        "disposition": disposition,
        "eligible_for_stronger_obligation": eligible,
    }


def _links(contract: dict[str, Any], *, candidate_id: str = "C1") -> list[dict[str, str]]:
    return [
        {
            "requirement_id": requirement["requirement_id"],
            "candidate_id": candidate_id,
            "link_status": "fixture_link",
        }
        for requirement in contract["source_requirements"]
    ]


def _ledger_projection(
    contract: dict[str, Any],
    *,
    candidates: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        build_evidence_ledger_observation_from_run_contract(
            observation_id="ag92e:ledger:contract",
            contract_projection=contract,
        ).to_dict()
    )
    if candidates or links:
        ledger.reduce_observation(
            {
                "observation_id": "ag92e:ledger:candidates",
                "observation_source": "ag92e_fixture",
                "candidates": candidates or [],
                "requirement_links": links or [],
            }
        )
    return ledger.to_projection().to_dict()


def _sufficiency_projection(
    contract: dict[str, Any],
    ledger: dict[str, Any],
) -> dict[str, Any]:
    return build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection=contract,
            evidence_ledger_projection=ledger,
            search_judgment_projection={"decision": "stop_satisfied"},
            source_obligation_projection=ledger,
            final_evidence_facts={
                "final_evidence_count": 1,
                "author_evidence_count": 1,
            },
        )
    ).to_projection()


def _final_passage() -> dict[str, Any]:
    return {
        "source_id": "S1",
        "url": "https://example.gov/rule",
        "title": "Official rule",
        "text": "Official current rule excerpt.",
        "source_tier": "official",
        "source_class": "official_current_rules",
    }


def test_search_judgment_input_builder_preserves_payload_semantics() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract)

    judgment_input = build_search_judgment_input_from_runtime(
        contract_projection=contract,
        evidence_ledger_projection=ledger,
        query_authority_trace={"query_plan_ref": {"query_count": 2}},
        core_topic="filing fee",
        primary_entity="agency",
        result_count=3,
        iterations_run=1,
        source_tier_counts={"official": 1, "secondary": 2},
        source_domain_counts={"agency.gov": 1},
        top_source_domains=["agency.gov"],
        provider_diagnostic_count=4,
        source_class_recovery_recommendation={
            "source_class_recovery_recommended": True
        },
        source_class_observability={
            "missing_expected_source_classes": ["official_current_rules"]
        },
        retrieval_stop_shadow_telemetry={"decision": "continue"},
        retrieval_stop_active_telemetry={"decision": "continue_targeted"},
        answer_contract_projection={
            "unfulfilled_source_classes": ["official_current_rules"]
        },
        max_iterations=3,
        recovery_attempt_count=1,
    )

    payload = judgment_input.to_model_payload()
    assert payload["contract_ref"]["contract_id"] == contract["contract_id"]
    assert payload["evidence_ledger_ref"]["requirement_count"] == ledger[
        "requirement_count"
    ]
    assert payload["query_ref_facts"]["query_role"] == "post_retrieval_recovery"
    assert payload["query_ref_facts"]["core_topic"] == "filing fee"
    assert payload["retrieval_observation_facts"] == {
        "result_count": 3,
        "iterations_run": 1,
        "source_tier_counts": {"official": 1, "secondary": 2},
        "source_domain_counts": {"agency.gov": 1},
        "top_source_domains": ["agency.gov"],
        "provider_diagnostic_count": 4,
    }
    assert payload["helper_proposals"]["source_class_recovery"][
        "source_class_recovery_recommended"
    ] is True
    assert payload["helper_proposals"]["source_class_recovery"][
        "missing_expected_source_classes"
    ] == ["official_current_rules"]
    assert payload["helper_proposals"]["retrieval_stop"]["active"] == {
        "decision": "continue_targeted"
    }
    assert payload["helper_proposals"]["answer_contract"][
        "unfulfilled_source_classes"
    ] == ["official_current_rules"]
    assert payload["budget"] == {
        "iteration": 1,
        "max_iterations": 3,
        "remaining_budget": 2,
        "recovery_attempts": 1,
        "budget_exhausted": False,
        "source_class_recovery_slot_available": True,
    }


def test_sufficiency_input_builder_preserves_payload_semantics() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract)
    search_projection = {
        "owner": "RunKernel.RunAuthoritySearchJudgment",
        "canonical_state": True,
        "trace_only": False,
        "decision": "stop_insufficient",
        "classifications": ["budget_exhausted"],
        "gaps": [{"required_source_class": "official_current_rules"}],
        "target_source_classes": ["official_current_rules"],
        "insufficient_posture": {"answerable": True},
    }

    judgment_input = build_sufficiency_judgment_input_from_runtime(
        contract_projection=contract,
        evidence_ledger_projection=ledger,
        search_judgment_projection=search_projection,
        search_judgment_history=[{"decision": "continue_targeted_search"}],
        answer_contract_projection={
            "unfulfilled_source_classes": ["official_current_rules"],
            "source_bound_numeric_obligations": ["fee_amount"],
        },
        final_evidence_count=2,
        author_evidence_count=1,
        citation_eligible_candidate_count=1,
        conflicts_present=True,
        scrutineer_flag_count=2,
        corpus_weak=True,
        weak_corpus_reason="off_topic",
        synth_was_insufficient=True,
        failure_card_show=True,
        failure_card_reason="no_useful_content",
        iterations_run=3,
        max_iterations=3,
        recovery_attempt_count=1,
    )

    payload = judgment_input.to_model_payload()
    assert payload["contract_ref"]["contract_id"] == contract["contract_id"]
    assert payload["evidence_ledger_ref"]["candidate_count"] == ledger[
        "candidate_count"
    ]
    assert payload["search_judgment_ref"]["decision"] == "stop_insufficient"
    assert payload["search_judgment_ref"]["history_decisions"] == [
        "continue_targeted_search"
    ]
    assert payload["answer_contract_ref"]["unfulfilled_source_classes"] == [
        "official_current_rules"
    ]
    assert payload["source_obligation_ref"] == ledger
    assert payload["final_evidence_facts"] == {
        "final_evidence_count": 2,
        "author_evidence_count": 1,
        "citation_eligible_candidate_count": 1,
    }
    assert payload["conflict_facts"] == {
        "conflicts_present": True,
        "scrutineer_flag_count": 2,
        "conflict_posture": "unresolved",
    }
    assert payload["indirect_inference_facts"] == {}
    assert payload["weak_failure_facts"] == {
        "corpus_weak": True,
        "weak_corpus_reason": "off_topic",
        "synth_was_insufficient": True,
        "failure_card": {"show": True, "reason": "no_useful_content"},
    }
    assert payload["budget"] == {
        "iteration": 3,
        "max_iterations": 3,
        "remaining_budget": 0,
        "recovery_attempts": 1,
        "budget_exhausted": True,
    }


def test_evidence_ledger_lifecycle_helper_matches_direct_reduction_shape() -> None:
    direct_kernel = _kernel_with_contract("ag92e-direct")
    helper_kernel = _kernel_with_contract("ag92e-helper")
    contract_projection = dict(direct_kernel.state.run_contract_projection)

    direct_action = direct_kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": "run_authority_contract",
            "contract_id": contract_projection.get("contract_id"),
            "source_requirement_count": len(
                contract_projection.get("source_requirements", [])
            ),
        }
    )
    direct_result = execute_evidence_ledger_reduction_action(
        direct_action,
        payload=build_evidence_ledger_observation_from_run_contract(
            observation_id="ag92e-direct:evidence-ledger:run-contract",
            contract_projection=contract_projection,
        ).to_dict(),
    )
    direct_kernel.reduce(direct_result.observation)
    direct_projection = direct_kernel.state.evidence_ledger.to_projection().to_dict()

    helper_projection = reduce_run_contract_requirements_into_evidence_ledger(
        run_kernel=helper_kernel,
        run_id="ag92e-direct",
        run_contract_projection=dict(helper_kernel.state.run_contract_projection),
        observation_id_suffix="run-contract",
        authorization_observation_source="run_authority_contract",
    )

    assert helper_projection == direct_projection
    assert helper_kernel.state.projections[EVIDENCE_LEDGER_STAGE] == helper_projection


def _kernel_with_contract(run_id: str) -> RunKernel:
    kernel = RunKernel.start(run_id=run_id, request_id=f"{run_id}:request")
    action = kernel.authorize_run_contract_synthesis(inputs={})
    result = execute_run_contract_synthesis_action(
        action,
        query="What is the current official filing fee?",
        mode="Balanced",
        current_date="June 10, 2026",
        route_projection={"report_type": "brief", "query_type": "fact"},
    )
    kernel.reduce(result.observation)
    return kernel


def test_projection_ref_helpers_accept_only_canonical_run_authority_refs() -> None:
    search_projection = {
        "owner": "RunKernel.RunAuthoritySearchJudgment",
        "canonical_state": True,
        "trace_only": False,
        "judgment_id": "search-1",
        "decision": "stop_satisfied",
        "classifications": ["contract_satisfied"],
        "target_source_classes": [],
    }
    sufficiency_projection = {
        "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "canonical_state": True,
        "trace_only": False,
        "judgment_id": "sufficiency-1",
        "decision": "ready_direct",
        "final_answer_posture": "direct_answer",
        "final_answer_allowed": True,
    }

    assert is_canonical_search_judgment_projection(search_projection) is True
    assert canonical_search_judgment_projection(search_projection) == search_projection
    assert compact_search_judgment_ref(search_projection)["decision"] == (
        "stop_satisfied"
    )
    assert (
        is_canonical_sufficiency_judgment_projection(sufficiency_projection)
        is True
    )
    assert canonical_sufficiency_judgment_projection(sufficiency_projection) == (
        sufficiency_projection
    )
    assert compact_sufficiency_judgment_ref(sufficiency_projection)[
        "final_answer_posture"
    ] == "direct_answer"

    trace_only = deepcopy(search_projection)
    trace_only["trace_only"] = True
    wrong_owner = deepcopy(sufficiency_projection)
    wrong_owner["owner"] = "RunKernel.LegacyCompatibility"
    not_canonical = deepcopy(sufficiency_projection)
    not_canonical["canonical_state"] = False

    assert canonical_search_judgment_projection(trace_only) == {}
    assert canonical_sufficiency_judgment_projection(wrong_owner) == {}
    assert canonical_sufficiency_judgment_projection(not_canonical) == {}


def test_final_adapter_uses_canonical_sufficiency_over_legacy_readiness_fields() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(
        contract,
        candidates=[_candidate()],
        links=_links(contract),
    )
    sufficiency_projection = _sufficiency_projection(contract, ledger)

    packet = build_final_answer_packet(
        run_id="ag92e-final-adapter",
        final_evidence=[_final_passage()],
        run_contract_projection=contract,
        sufficiency_judgment_projection=sufficiency_projection,
        evidence_sufficient=False,
        corpus_weak=True,
        failure_card_payload={"show": True, "reason": "legacy_failure"},
        conflicts_present=True,
        synth_was_insufficient=True,
    )

    assert packet.readiness_status is FinalAnswerReadinessStatus.AUTHOR_READY
    assert packet.readiness_reasons == ()
    assert ClaimPosture.DIRECTLY_SOURCED in packet.claim_postures
    assert ClaimPosture.WEAK_CORPUS_AUTHORIZED not in packet.claim_postures
    assert ClaimPosture.FAILURE_CARD_AUTHORIZED not in packet.claim_postures
    assert ClaimPosture.CONFLICT_PRESERVED not in packet.claim_postures
    assert packet.author_input_refs["sufficiency_judgment_ref"]["decision"] == (
        "ready_direct"
    )


def test_pipeline_orchestrator_static_guards_for_ag92e_extraction() -> None:
    pipeline = (ROOT / "core" / "pipeline_orchestrator.py").read_text()

    assert "build_search_judgment_input_from_runtime(" in pipeline
    assert "build_sufficiency_judgment_input_from_runtime(" in pipeline
    assert "reduce_run_contract_requirements_into_evidence_ledger(" in pipeline
    assert "reduce_final_evidence_bundle_into_evidence_ledger(" in pipeline
    assert "RunSearchJudgmentInput(" not in pipeline
    assert "RunSufficiencyJudgmentInput(" not in pipeline
    assert "build_evidence_ledger_observation_from_runtime" not in pipeline
    assert "execute_evidence_ledger_reduction_action(" not in pipeline
    assert "RUN_AUTHORITY_SEARCH_JUDGMENT_SYSTEM_PROMPT" not in pipeline
    assert "RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT" not in pipeline
    assert "careful research director deciding the next retrieval action" not in pipeline
    assert "Decide final answer sufficiency" not in pipeline
    assert "build_deterministic_search_judgment" not in pipeline
    assert "validate_or_repair_search_judgment" not in pipeline
    assert "build_deterministic_sufficiency_judgment" not in pipeline
    assert "validate_or_repair_sufficiency_judgment" not in pipeline
