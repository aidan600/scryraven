from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from core.evidence_ledger import build_evidence_ledger_observation_from_run_contract
from core.evidence_ledger_lifecycle import (
    reduce_provider_job_evidence_into_evidence_ledger,
    reduce_run_contract_requirements_into_evidence_ledger,
)
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.final_answer_packet import FinalAnswerReadinessStatus
from core.final_answer_runtime_adapter import (
    build_final_answer_packet,
    derive_author_input_payload,
)
from core.ordinary_semantic_producer_runtime import (
    build_component_coverage_proposal,
    build_semantic_observation_and_content_refs,
    select_bindable_final_passage,
)
from core.quant_work_unit_runtime import build_quant_work_unit_packets
from core.query_plan import QUERY_PLAN_TRACE_KEY, QueryPlanRole
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    RunSufficiencyJudgmentInput,
    SufficiencyPosture,
)
from core.run_authority_sufficiency_validation import (
    build_deterministic_sufficiency_judgment,
)
from core.run_kernel import Observation, ObservationType, RunKernel, RunStageStatus
from core.search_work_provider_job_execution import (
    build_provider_job_execution_handoff,
)
from core.semantic_contract_foundation import (
    AnswerComponentContract,
    Materiality,
    QuestionMeaningRecord,
    RequirementPosture,
    ResolverKind,
    SemanticSlot,
    SemanticSlotKind,
    SemanticSlotStatus,
    SupportKind,
)
from core.sufficiency_semantic_state_consumption_runtime import (
    build_semantic_state_facts_for_sufficiency,
)

ROOT = Path(__file__).resolve().parents[1]


def _clean(value: str) -> str:
    return " ".join(str(value or "").split())[:300]


def _search_work_projection() -> dict[str, Any]:
    return {
        "trace_key": "query_plan_work_shadow_projection",
        "components": [
            {"component_id": "component-fee"},
            {"component_id": "component-legal"},
            {"component_id": "component-api"},
            {"component_id": "component-numeric"},
        ],
        "source_obligations_by_component": {
            "component-fee": [
                {
                    "obligation_id": "obligation-official-fee",
                    "kind": "official_current",
                    "strictness": "required",
                    "required_source_class": "official_current_rules",
                    "required_currentness": "current",
                }
            ],
            "component-legal": [
                {
                    "obligation_id": "obligation-legal-deadline",
                    "kind": "legal_current_primary",
                    "strictness": "required",
                    "required_source_class": "legal_or_regulatory_text",
                    "required_currentness": "current",
                }
            ],
            "component-api": [
                {
                    "obligation_id": "obligation-api-docs",
                    "kind": "canonical_documentation",
                    "strictness": "required",
                    "required_source_class": "primary_source_documents",
                }
            ],
            "component-numeric": [
                {
                    "obligation_id": "obligation-source-bound-numeric",
                    "kind": "source_bound_numeric",
                    "strictness": "required",
                    "required_source_class": "sourced_numeric_values",
                }
            ],
        },
        "provider_jobs_by_component": {
            "component-fee": [
                {
                    "work_id": "provider-official-fee",
                    "work_kind": "official_candidate_acquisition",
                    "source_obligation_ids": ["obligation-official-fee"],
                    "executes_runtime_work": False,
                }
            ],
            "component-legal": [
                {
                    "work_id": "provider-legal-currentness",
                    "work_kind": "conflict_currentness_check",
                    "source_obligation_ids": ["obligation-legal-deadline"],
                    "executes_runtime_work": False,
                }
            ],
            "component-api": [
                {
                    "work_id": "provider-api-canonical",
                    "work_kind": "canonical_extraction",
                    "source_obligation_ids": ["obligation-api-docs"],
                    "executes_runtime_work": False,
                }
            ],
            "component-numeric": [
                {
                    "work_id": "provider-numeric-extract",
                    "work_kind": "fetch_read_extract",
                    "source_obligation_ids": ["obligation-source-bound-numeric"],
                    "executes_runtime_work": False,
                }
            ],
        },
    }


def _search_work_for_components(*component_ids: str) -> dict[str, Any]:
    base = _search_work_projection()
    wanted = set(component_ids)
    return {
        **base,
        "components": [item for item in base["components"] if item.get("component_id") in wanted],
        "source_obligations_by_component": {
            key: value for key, value in base["source_obligations_by_component"].items() if key in wanted
        },
        "provider_jobs_by_component": {
            key: value for key, value in base["provider_jobs_by_component"].items() if key in wanted
        },
    }


def _requirement(
    requirement_id: str,
    *,
    kind: str,
    source_class: str,
    source_tier: str,
    component_id: str,
    source_obligation_id: str,
    provider_job_id: str,
    currentness: str | None = "current",
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "requirement_kind": kind,
        "strictness": "required",
        "required_source_class": source_class,
        "required_source_tier": source_tier,
        "required_currentness": currentness,
        "component_id": component_id,
        "source_obligation_id": source_obligation_id,
        "provider_job_id": provider_job_id,
    }


def _contract(*requirements: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "owner": "RunKernel.RunAuthorityContract",
        "contract_id": "ag96g3-g4-contract",
        "selected_template_ids": ["ag96g3-g4"],
        "source_requirements": [
            {key: value for key, value in item.items() if key != "provider_job_id"} for item in requirements
        ],
        "final_posture_policy": {
            "partial_allowed_if": "some required obligations remain missing",
            "mandatory_caveats": ["missing_source_custody_must_be_caveated"],
            "prohibited_upgrades": ["do_not_upgrade_missing_official_current_custody"],
        },
    }


REQS = {
    "official": _requirement(
        "run-contract:official-fee",
        kind="official_current",
        source_class="official_current_rules",
        source_tier="official",
        component_id="component-fee",
        source_obligation_id="obligation-official-fee",
        provider_job_id="provider-official-fee",
    ),
    "legal": _requirement(
        "run-contract:legal-deadline",
        kind="legal_primary",
        source_class="legal_or_regulatory_text",
        source_tier="primary",
        component_id="component-legal",
        source_obligation_id="obligation-legal-deadline",
        provider_job_id="provider-legal-currentness",
    ),
    "canonical": _requirement(
        "run-contract:api-docs",
        kind="canonical_docs",
        source_class="primary_source_documents",
        source_tier="canonical",
        component_id="component-api",
        source_obligation_id="obligation-api-docs",
        provider_job_id="provider-api-canonical",
        currentness=None,
    ),
    "numeric": _requirement(
        "run-contract:numeric-rate",
        kind="source_bound_numeric",
        source_class="sourced_numeric_values",
        source_tier="official",
        component_id="component-numeric",
        source_obligation_id="obligation-source-bound-numeric",
        provider_job_id="provider-numeric-extract",
        currentness=None,
    ),
}


QUERY_BY_COMPONENT = {
    "component-fee": "official current filing fee",
    "component-legal": "legal deadline appeal rule",
    "component-api": "API parameter documentation",
    "component-numeric": "numeric rate amount source",
}


def _adapter() -> Any:
    return build_query_plan_runtime_adapter(
        run_id="ag96g3-g4",
        primary_entity="Acme Filing System",
        entities_list=["Acme Filing System"],
        core_topic="Acme fee legal deadline API numeric rate",
        user_query="What are the current fee, legal deadline, API parameter, and numeric rate?",
        intent="general",
        clean=_clean,
    )


def _candidate(
    *,
    query: str,
    source_class: str,
    source_tier: str,
    url: str,
    title: str,
    source_id: int = 501,
    currentness: str | None = "current",
    eligible: bool = True,
    final_evidence_eligible: bool = True,
    disposition: str = "accepted",
) -> dict[str, Any]:
    return {
        "candidate_id": f"closure-candidate:{source_id}",
        "source_id": source_id,
        "url": url,
        "title": title,
        "text": "Fixture text is intentionally compact and not asserted.",
        "query_ref": query,
        "provider_name": "offline_fixture",
        "retrieval_pass_id": f"retrieval-{source_id}",
        "source_tier": source_tier,
        "source_class": source_class,
        "currentness_signal": currentness,
        "readable_status": "readable",
        "fetchable_status": "fetchable",
        "disposition": disposition,
        "eligible_for_stronger_obligation": eligible,
        "final_evidence_eligible": final_evidence_eligible,
    }


def _final_evidence(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": item.get("candidate_id"),
            "source_id": item.get("source_id"),
            "url": item.get("url"),
            "title": item.get("title"),
            "text": item.get("text", ""),
            "source_tier": item.get("source_tier"),
            "source_class": item.get("source_class"),
        }
        for item in records
        if item.get("url")
    ]


def _accept_answer_contract(
    kernel: RunKernel,
    contract: Mapping[str, Any],
    *,
    required_component_ids: Sequence[str],
) -> dict[str, Any]:
    requirements = [dict(item) for item in contract.get("source_requirements", ()) if isinstance(item, Mapping)]
    slots = tuple(
        SemanticSlot(
            slot_id=f"slot:{requirement['component_id']}",
            slot_kind=SemanticSlotKind.SOURCE_BASIS,
            status=SemanticSlotStatus.EXPLICIT,
            selected_value=str(requirement["required_source_class"]),
            materiality=Materiality.MATERIAL,
        )
        for requirement in requirements
    )
    components = tuple(
        AnswerComponentContract(
            component_id=str(requirement["component_id"]),
            component_revision="1",
            user_facing_label=str(requirement["component_id"]),
            user_facing_question=QUERY_BY_COMPONENT[str(requirement["component_id"])],
            requirement_posture=(
                RequirementPosture.REQUIRED
                if requirement["component_id"] in required_component_ids
                else RequirementPosture.CONDITIONAL
            ),
            acceptance_criteria=("bind direct support to the exact owned source obligation",),
            semantic_slot_ids=(f"slot:{requirement['component_id']}",),
            source_obligation_candidate_ids=(str(requirement["source_obligation_id"]),),
            allowed_support_kinds=(SupportKind.DIRECT,),
            max_inference_depth=0,
            materiality=Materiality.MATERIAL,
        )
        for requirement in requirements
    )
    question_meaning_record = QuestionMeaningRecord(
        record_id="qmr:ag96g3-g4-final-answer-closure",
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        request_digest="request-digest-ag96g3-g4",
        requested_mode="balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version="ag96g3-g4-closure-test",
        intent="Answer every represented component from exact owned evidence.",
        requested_output="A concise, evidence-bound answer.",
        semantic_slots=slots,
        answer_components=components,
        metadata={"offline_fixture": True},
    ).require_valid()
    action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=question_meaning_record.record_id,
        parent_proposal_digest=question_meaning_record.record_digest,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
            status=RunStageStatus.COMPLETED,
            payload={"question_meaning_record": question_meaning_record.to_dict()},
        )
    )
    return dict(kernel.state.initial_answer_contract)


def _reduce_exact_run_contract_requirements(
    kernel: RunKernel,
    *,
    contract: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    exact_candidate_bindings: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]] = (),
) -> None:
    observation = build_evidence_ledger_observation_from_run_contract(
        observation_id="ag96g3-g4:evidence-ledger:contract",
        contract_projection=contract,
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        answer_contract_version=str(accepted_contract["accepted_contract_version"]),
        answer_contract_digest=str(accepted_contract["accepted_contract_digest"]),
    )
    payload = observation.to_dict()
    payload["candidates"] = [
        {
            **dict(candidate),
            "record_kind": "fact",
            "requirement_id": requirement["requirement_id"],
            "link_reason": "ag96g3_g4_explicit_exact_owned_requirement",
        }
        for candidate, requirement in exact_candidate_bindings
    ]
    action = kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": "ag96g3_g4_exact_contract",
            "contract_id": contract.get("contract_id"),
            "source_requirement_count": len(contract.get("source_requirements", ())),
            "exact_candidate_binding_count": len(exact_candidate_bindings),
        }
    )
    result = execute_evidence_ledger_reduction_action(
        action,
        payload=payload,
    )
    kernel.reduce(result.observation)


def _commit_component_coverage(
    kernel: RunKernel,
    *,
    accepted_contract: Mapping[str, Any],
    candidate: Mapping[str, Any],
    component_id: str,
) -> None:
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    bindable = select_bindable_final_passage([candidate], ledger)
    assert bindable is not None
    component_ref = next(
        item for item in accepted_contract["accepted_answer_component_refs"] if item["component_id"] == component_id
    )
    semantic_observation, content_refs = build_semantic_observation_and_content_refs(
        accepted_contract=accepted_contract,
        bindable=bindable,
        component_ref=component_ref,
    )
    admission = kernel.authorize_semantic_observation_admission(
        semantic_observation_id=semantic_observation.observation_id,
        semantic_observation_digest=semantic_observation.observation_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            admission,
            observation_type=ObservationType.SEMANTIC_OBSERVATION_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={
                "semantic_observation": semantic_observation.to_dict(),
                "sanitized_content_references": [item.to_dict() for item in content_refs],
            },
        )
    )
    coverage = build_component_coverage_proposal(
        accepted_contract=accepted_contract,
        observation=semantic_observation,
        content_ref=content_refs[0],
        evidence_ledger_projection=ledger,
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        query=QUERY_BY_COMPONENT[component_id],
    )
    assert coverage is not None
    coverage_payload = coverage.to_dict(include_validation=False)
    coverage_payload["record_digest"] = coverage.record_digest
    reduction = kernel.authorize_component_coverage_reduction(
        coverage_record_id=coverage.record_id,
        coverage_record_digest=coverage.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            reduction,
            observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
            status=RunStageStatus.COMPLETED,
            payload={"component_coverage_record": coverage_payload},
        )
    )


def _spine(
    contract: Mapping[str, Any],
    *,
    candidate_queries: Sequence[str],
    retrieval_records: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None,
    final_evidence_records: Sequence[Mapping[str, Any]] | None = None,
    search_work_projection: Mapping[str, Any] | None = None,
    quant_work_units: Sequence[Mapping[str, Any]] | None = None,
    required_component_ids: Sequence[str] = (),
    covered_component_ids: Sequence[str] = (),
) -> dict[str, Any]:
    projection = search_work_projection if search_work_projection is not None else _search_work_projection()
    adapter = _adapter()
    admitted = adapter.consume_search_work_for_existing_queries(
        candidate_queries,
        search_work_projection=projection,
        max_len=len(candidate_queries),
        origin="ag96g3_g4_tripwire",
        role=QueryPlanRole.INITIAL,
    )
    query_plan_trace = adapter.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    handoff = build_provider_job_execution_handoff(
        search_work_projection=projection,
        query_plan_trace=query_plan_trace,
        current_queries=admitted,
    )
    kernel = RunKernel.start(run_id="ag96g3-g4", request_id="request")
    kernel.state.run_contract_projection = dict(contract)
    candidate_records = list(retrieval_records) if isinstance(retrieval_records, Sequence) else []
    requirements_by_component = {
        str(item["component_id"]): dict(item)
        for item in contract.get("source_requirements", ())
        if isinstance(item, Mapping)
    }
    candidates_by_component = {
        component_id: next(
            (
                candidate
                for candidate in candidate_records
                if candidate.get("query_ref") == QUERY_BY_COMPONENT[component_id]
            ),
            None,
        )
        for component_id in covered_component_ids
    }
    assert all(candidate is not None for candidate in candidates_by_component.values())
    if required_component_ids or covered_component_ids:
        accepted_contract = _accept_answer_contract(
            kernel,
            contract,
            required_component_ids=required_component_ids,
        )
        _reduce_exact_run_contract_requirements(
            kernel,
            contract=contract,
            accepted_contract=accepted_contract,
            exact_candidate_bindings=tuple(
                (candidate, requirements_by_component[component_id])
                for component_id, candidate in candidates_by_component.items()
                if candidate is not None
            ),
        )
    else:
        accepted_contract = {}
        reduce_run_contract_requirements_into_evidence_ledger(
            run_kernel=kernel,
            run_id="ag96g3-g4",
            run_contract_projection=contract,
            observation_id_suffix="contract",
            authorization_observation_source="ag96g3_g4_contract",
        )
    reduced = reduce_provider_job_evidence_into_evidence_ledger(
        run_kernel=kernel,
        run_id="ag96g3-g4",
        provider_job_execution_handoff=handoff,
        query_plan_trace=query_plan_trace,
        current_authorized_queries=admitted,
        retrieval_records=retrieval_records,
        search_work_projection=projection,
    )
    ledger = reduced["evidence_ledger_projection"]
    for component_id, candidate in candidates_by_component.items():
        assert candidate is not None
        _commit_component_coverage(
            kernel,
            accepted_contract=accepted_contract,
            candidate=candidate,
            component_id=component_id,
        )
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    semantic_state_facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=kernel.state.initial_answer_contract,
        component_coverage_history=kernel.state.component_coverage_history,
        contract_amendment_admission_history=(kernel.state.contract_amendment_admission_history),
        evidence_ledger_projection=ledger,
    )
    evidence = (
        list(final_evidence_records) if final_evidence_records is not None else _final_evidence(candidate_records)
    )
    quant_packets = build_quant_work_unit_packets(
        quant_work_units=quant_work_units or (),
        evidence_ledger_projection=ledger,
        candidate_records=retrieval_records,
    )
    judgment = build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection=contract,
            evidence_ledger_projection=ledger,
            search_judgment_projection={"decision": "stop_satisfied"},
            answer_contract_projection={},
            source_obligation_projection=ledger,
            semantic_state_facts=semantic_state_facts,
            final_evidence_facts={
                "final_evidence_count": len(evidence),
                "author_evidence_count": len(evidence),
                "citation_eligible_candidate_count": len(evidence),
                "quant_extraction_executed": bool(quant_packets),
                "calculation_executed": any(
                    packet.get("calculation_status") == "succeeded" for packet in quant_packets
                ),
                "quant_work_unit_packets": list(quant_packets),
            },
        )
    )
    packet = build_final_answer_packet(
        run_id="ag96g3-g4",
        final_evidence=evidence,
        author_evidence=evidence,
        ordered_sources=[],
        unique_source_urls={},
        run_contract_projection=contract,
        source_obligation_projection=ledger,
        sufficiency_judgment_projection=judgment.to_projection(),
    )
    payload = None
    if packet.final_answer_allowed:
        packet, payload = derive_author_input_payload(
            packet,
            prompt="BASE AUTHOR PROMPT",
            author_system_prompt_key="author",
            author_effort="low",
        )
    return {
        "admitted": admitted,
        "query_plan_trace": query_plan_trace,
        "provider_job_handoff": handoff,
        "provider_job_bridge_projection": reduced["provider_job_evidence_ledger_bridge_projection"],
        "ledger": ledger,
        "accepted_contract": accepted_contract,
        "semantic_admission_history": list(kernel.state.semantic_observation_admission_history),
        "component_coverage_history": list(kernel.state.component_coverage_history),
        "semantic_state_facts": semantic_state_facts,
        "quant_packets": quant_packets,
        "judgment": judgment,
        "packet": packet,
        "payload": payload,
    }


def _payload_authority(result: Mapping[str, Any]) -> Mapping[str, Any]:
    return result["payload"].authority_payload


def _ledger_token(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _assert_canonical_component_closure(
    result: Mapping[str, Any],
    *,
    requirement: Mapping[str, Any],
    candidate: Mapping[str, Any],
    expect_full_coverage: bool = True,
) -> None:
    component_id = str(requirement["component_id"])
    requirement_id = _ledger_token(requirement["requirement_id"])
    source_obligation_id = _ledger_token(requirement["source_obligation_id"])
    candidate_id = _ledger_token(candidate["candidate_id"])
    accepted_contract = result["accepted_contract"]

    assert len(result["semantic_admission_history"]) == 1
    coverage = next(
        item for item in result["component_coverage_history"] if item["answer_component_id"] == component_id
    )
    assert coverage["coverage_state"] == "satisfied"
    assert coverage["semantic_support_status"] == "supported"
    assert coverage["source_obligation_status"] == "satisfied"
    assert coverage["candidate_ids"] == [candidate_id]
    assert coverage["source_obligation_ids"] == [source_obligation_id]
    assert coverage["evidence_ledger_binding"]["source_requirement_ids"] == [requirement_id]
    assert coverage["owned_requirement_candidate_refs"] == [
        {
            "candidate_id": candidate_id,
            "link_status": "accepted",
            "requirement_id": requirement_id,
            "source_obligation_id": source_obligation_id,
        }
    ]

    ledger_requirements = [
        item for item in result["ledger"]["source_requirements"] if item["requirement_id"] == requirement_id
    ]
    assert len(ledger_requirements) == 1
    ledger_requirement = ledger_requirements[0]
    assert ledger_requirement["status"] == "satisfied"
    assert ledger_requirement["component_id"] == _ledger_token(component_id)
    assert ledger_requirement["source_obligation_id"] == source_obligation_id
    assert ledger_requirement["run_id"] == "ag96g3-g4"
    assert ledger_requirement["request_id"] == "request"
    assert ledger_requirement["answer_contract_version"] == (accepted_contract["accepted_contract_version"])
    assert ledger_requirement["answer_contract_digest"] == (accepted_contract["accepted_contract_digest"])
    exact_links = [
        item
        for item in result["ledger"]["requirement_links"]
        if item["requirement_id"] == requirement_id and item["candidate_id"] == candidate_id
    ]
    assert exact_links == [
        {
            "candidate_id": candidate_id,
            "link_reason": "ag96g3_g4_explicit_exact_owned_requirement",
            "link_status": "accepted",
            "requirement_id": requirement_id,
        }
    ]

    if expect_full_coverage:
        facts = result["semantic_state_facts"]
        assert facts["covered_component_count"] == facts["required_component_count"]
        assert facts["missing_component_count"] == 0
        semantic_consumption = result["judgment"].to_projection()["semantic_consumption"]
        assert semantic_consumption["covered_component_count"] == (semantic_consumption["required_component_count"])
        assert semantic_consumption["direct_answer_blocked"] is False


def test_direct_official_current_sufficiency_constrains_packet_and_author_payload() -> None:
    record = _candidate(
        query=QUERY_BY_COMPONENT["component-fee"],
        source_class="official_current_rules",
        source_tier="official",
        url="https://agency.example.gov/fee",
        title="Current fee",
        source_id=601,
    )

    result = _spine(
        _contract(REQS["official"]),
        candidate_queries=[QUERY_BY_COMPONENT["component-fee"]],
        retrieval_records=[record],
        search_work_projection=_search_work_for_components("component-fee"),
        required_component_ids=("component-fee",),
        covered_component_ids=("component-fee",),
    )
    packet = result["packet"]
    authority = _payload_authority(result)
    _assert_canonical_component_closure(
        result,
        requirement=REQS["official"],
        candidate=record,
    )
    assert result["judgment"].decision is RunSufficiencyDecision.READY_DIRECT
    assert packet.readiness_status is FinalAnswerReadinessStatus.AUTHOR_READY
    assert packet.required_obligations_satisfied is True
    assert authority["readiness_status"] == "author_ready"
    assert authority["claim_postures"] == ["directly_sourced"]
    assert authority["citation_eligible_source_ids"] == [601]
    assert authority["satisfied_source_obligations"][0]["requirement_kind"] == ("official_current")
    assert "Final-answer readiness: author_ready" in result["payload"].prompt


def test_aggregate_only_official_current_forces_partial_authority_payload() -> None:
    result = _spine(
        _contract(REQS["official"]),
        candidate_queries=[QUERY_BY_COMPONENT["component-fee"]],
        retrieval_records={"source_tier_counts": {"official": 1}},
        search_work_projection=_search_work_for_components("component-fee"),
    )
    authority = _payload_authority(result)

    assert result["semantic_admission_history"] == []
    assert result["component_coverage_history"] == []
    assert result["judgment"].decision is not RunSufficiencyDecision.READY_DIRECT
    assert result["packet"].readiness_status is (FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED)
    assert authority["citation_eligible_source_ids"] == []
    assert authority["missing_source_obligations"]
    assert authority["mandatory_caveats"]
    assert "missing_source_custody_must_be_caveated" in (authority["mandatory_caveats"])
    assert authority["prohibited_upgrades"]
    assert "do_not_treat_missing_official_current_custody_as_satisfied" in (authority["prohibited_upgrades"])


def test_lower_tier_context_source_is_citation_ineligible_for_strict_current_need() -> None:
    record = _candidate(
        query=QUERY_BY_COMPONENT["component-fee"],
        source_class="reputable_secondary",
        source_tier="secondary",
        url="https://example.com/context",
        title="Context article",
        source_id=602,
        eligible=False,
    )

    result = _spine(
        _contract(REQS["official"]),
        candidate_queries=[QUERY_BY_COMPONENT["component-fee"]],
        retrieval_records=[record],
        search_work_projection=_search_work_for_components("component-fee"),
    )
    authority = _payload_authority(result)

    assert result["semantic_admission_history"] == []
    assert result["component_coverage_history"] == []
    assert result["packet"].readiness_status is (FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED)
    assert authority["citation_eligible_source_ids"] == []
    assert authority["citation_ineligible_refs"][0]["source_id"] == 602
    assert authority["citation_ineligible_refs"][0]["reason"] == ("sufficiency_has_no_satisfied_source_obligation")
    assert authority["missing_source_obligations"]


def test_legal_current_primary_and_canonical_docs_satisfy_their_obligations() -> None:
    legal = _candidate(
        query=QUERY_BY_COMPONENT["component-legal"],
        source_class="legal_or_regulatory_text",
        source_tier="primary",
        url="https://law.example.gov/rule",
        title="Current legal rule",
        source_id=603,
    )
    canonical = _candidate(
        query=QUERY_BY_COMPONENT["component-api"],
        source_class="primary_source_documents",
        source_tier="canonical",
        url="https://docs.example.com/api",
        title="Canonical API docs",
        source_id=604,
        currentness=None,
    )

    legal_result = _spine(
        _contract(REQS["legal"]),
        candidate_queries=[QUERY_BY_COMPONENT["component-legal"]],
        retrieval_records=[legal],
        search_work_projection=_search_work_for_components("component-legal"),
        required_component_ids=("component-legal",),
        covered_component_ids=("component-legal",),
    )
    canonical_result = _spine(
        _contract(REQS["canonical"]),
        candidate_queries=[QUERY_BY_COMPONENT["component-api"]],
        retrieval_records=[canonical],
        search_work_projection=_search_work_for_components("component-api"),
        required_component_ids=("component-api",),
        covered_component_ids=("component-api",),
    )

    _assert_canonical_component_closure(
        legal_result,
        requirement=REQS["legal"],
        candidate=legal,
    )
    _assert_canonical_component_closure(
        canonical_result,
        requirement=REQS["canonical"],
        candidate=canonical,
    )
    assert _payload_authority(legal_result)["satisfied_source_obligations"][0]["requirement_kind"] == "legal_primary"
    assert (
        _payload_authority(canonical_result)["satisfied_source_obligations"][0]["requirement_kind"] == "canonical_docs"
    )
    assert _payload_authority(legal_result)["citation_eligible_source_ids"] == [603]
    assert _payload_authority(canonical_result)["citation_eligible_source_ids"] == [604]


def test_source_bound_numeric_candidate_without_extraction_reaches_author_unknown_posture() -> None:
    record = _candidate(
        query=QUERY_BY_COMPONENT["component-numeric"],
        source_class="sourced_numeric_values",
        source_tier="official",
        url="https://stats.example.gov/rate",
        title="Numeric rate source",
        source_id=605,
    )

    result = _spine(
        _contract(REQS["numeric"]),
        candidate_queries=[QUERY_BY_COMPONENT["component-numeric"]],
        retrieval_records=[record],
        search_work_projection=_search_work_for_components("component-numeric"),
    )
    authority = _payload_authority(result)

    assert result["semantic_admission_history"] == []
    assert result["component_coverage_history"] == []
    assert result["judgment"].decision is (RunSufficiencyDecision.SOURCE_BOUND_NUMERIC_UNKNOWN)
    assert result["packet"].readiness_status is (FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED)
    assert authority["source_bound_numeric_unknowns"]
    assert "do_not_present_source_bound_numeric_unknown_as_known" in (authority["prohibited_upgrades"])
    assert "Source-bound numeric unknowns:" in result["payload"].prompt


def test_mixed_multipart_preserves_separate_satisfied_and_missing_obligations() -> None:
    record = _candidate(
        query=QUERY_BY_COMPONENT["component-fee"],
        source_class="official_current_rules",
        source_tier="official",
        url="https://agency.example.gov/fee",
        title="Current fee",
        source_id=606,
    )

    result = _spine(
        _contract(REQS["official"], REQS["legal"]),
        candidate_queries=[
            QUERY_BY_COMPONENT["component-fee"],
            QUERY_BY_COMPONENT["component-legal"],
        ],
        retrieval_records=[record],
        search_work_projection=_search_work_for_components(
            "component-fee",
            "component-legal",
        ),
        required_component_ids=("component-fee", "component-legal"),
        covered_component_ids=("component-fee",),
    )
    _assert_canonical_component_closure(
        result,
        requirement=REQS["official"],
        candidate=record,
        expect_full_coverage=False,
    )
    assert len(result["accepted_contract"]["accepted_answer_component_refs"]) == 2
    assert all(
        item["requirement_posture"] == "required"
        for item in result["accepted_contract"]["accepted_answer_component_refs"]
    )
    assert len(result["component_coverage_history"]) == 1
    assert len(result["judgment"].satisfied_obligations) == 1
    assert {_ledger_token(item.component_id) for item in result["judgment"].missing_required_obligations} == {
        "component_legal"
    }
    assert result["semantic_state_facts"]["required_component_count"] == 2
    assert result["semantic_state_facts"]["covered_component_count"] == 1
    assert result["semantic_state_facts"]["missing_component_count"] == 1
    assert result["judgment"].decision is (RunSufficiencyDecision.PARTIAL_ANSWER_AUTHORIZED)
    assert result["packet"].readiness_status is FinalAnswerReadinessStatus.BLOCKED
    assert [item.source_id for item in result["packet"].citation_eligible] == [606]
    assert result["packet"].final_answer_allowed is False
    assert result["payload"] is None


def test_no_provider_job_handoff_or_g1_bridge_payload_invents_no_satisfaction() -> None:
    search_work_without_jobs = {
        **_search_work_for_components("component-fee"),
        "provider_jobs_by_component": {},
    }

    result = _spine(
        _contract(REQS["official"]),
        candidate_queries=[QUERY_BY_COMPONENT["component-fee"]],
        retrieval_records=[],
        search_work_projection=search_work_without_jobs,
    )
    authority = _payload_authority(result)

    assert result["semantic_admission_history"] == []
    assert result["component_coverage_history"] == []
    assert result["provider_job_handoff"]["provider_job_execution_record_count"] == 0
    assert result["provider_job_bridge_projection"]["evidence_ledger_observation_created"] is False
    assert result["judgment"].required_obligations_satisfied is False
    assert authority["missing_source_obligations"]
    assert authority["citation_eligible_source_ids"] == []


def test_blocked_sufficiency_packet_cannot_produce_author_input() -> None:
    blocked = RunSufficiencyJudgment(
        judgment_id="blocked-ag96g3-g4",
        decision=RunSufficiencyDecision.BLOCK_FINALIZATION,
        final_answer_posture=SufficiencyPosture.BLOCKED,
        required_obligations_satisfied=False,
        final_answer_allowed=False,
        readiness_reasons=("blocked_by_sufficiency",),
        final_packet_inputs={
            "decision": "block_finalization",
            "final_answer_posture": "blocked",
            "final_answer_allowed": False,
            "required_obligations_satisfied": False,
            "readiness_status": "blocked",
            "readiness_reasons": ["blocked_by_sufficiency"],
            "claim_postures": ["unsupported"],
            "missing_required_obligations": [],
            "partial_obligations": [],
            "satisfied_obligations": [],
            "source_bound_numeric_unknowns": [],
            "mandatory_caveats": ["finalization_blocked"],
            "prohibited_upgrades": ["do_not_call_author"],
            "behavior_boundary_flags": {
                "provider_search_behavior_changed": False,
                "retrieval_behavior_changed": False,
                "prompt_behavior_changed": False,
                "citation_behavior_changed": False,
                "author_prose_behavior_changed": False,
            },
        },
    )
    packet = build_final_answer_packet(
        run_id="blocked-ag96g3-g4",
        final_evidence=[],
        sufficiency_judgment_projection=blocked.to_projection(),
    )

    assert packet.readiness_status is FinalAnswerReadinessStatus.BLOCKED
    with pytest.raises(ValueError, match="blocked FinalAnswerPacket"):
        derive_author_input_payload(
            packet,
            prompt="BASE AUTHOR PROMPT",
            author_system_prompt_key="author",
            author_effort="low",
        )


def test_author_payload_authority_is_redacted_and_machine_readable() -> None:
    record = _candidate(
        query=QUERY_BY_COMPONENT["component-fee"],
        source_class="official_current_rules",
        source_tier="official",
        url="https://agency.example.gov/fee",
        title="Current fee",
        source_id=607,
    )
    dirty_record = {
        **record,
        "raw_prompt": "RAW_PROMPT_SENTINEL",
        "raw_provider_payload": "RAW_PROVIDER_SENTINEL",
        "raw_model_response": "RAW_MODEL_SENTINEL",
        "raw_text": "RAW_TEXT_SENTINEL",
        "full_text": "FULL_TEXT_SENTINEL",
        "snippets": ["SNIPPET_SENTINEL"],
        "secret": "SECRET_SENTINEL",  # pragma: allowlist secret
        "token": "TOKEN_SENTINEL",
        "db_row": "DB_ROW_SENTINEL",
        "full_trace": "FULL_TRACE_SENTINEL",
    }

    result = _spine(
        _contract(REQS["official"]),
        candidate_queries=[QUERY_BY_COMPONENT["component-fee"]],
        retrieval_records=[dirty_record],
        search_work_projection=_search_work_for_components("component-fee"),
        required_component_ids=("component-fee",),
        covered_component_ids=("component-fee",),
    )
    payload = result["payload"]
    encoded = json.dumps(
        {
            "packet": result["packet"].to_dict(),
            "payload_ref": payload.to_trace_ref(),
            "authority_payload": payload.authority_payload,
        },
        sort_keys=True,
    )

    _assert_canonical_component_closure(
        result,
        requirement=REQS["official"],
        candidate=dirty_record,
    )
    assert payload.authority_payload["readiness_status"] == "author_ready"
    assert payload.authority_payload["claim_postures"] == ["directly_sourced"]
    assert payload.authority_payload["citation_eligible_source_ids"] == [607]
    for sentinel in (
        "RAW_PROMPT_SENTINEL",
        "RAW_PROVIDER_SENTINEL",
        "RAW_MODEL_SENTINEL",
        "RAW_TEXT_SENTINEL",
        "FULL_TEXT_SENTINEL",
        "SNIPPET_SENTINEL",
        "SECRET_SENTINEL",
        "TOKEN_SENTINEL",
        "DB_ROW_SENTINEL",
        "FULL_TRACE_SENTINEL",
    ):
        assert sentinel not in encoded


def test_static_guards_keep_g3_g4_offline_and_out_of_closed_surfaces() -> None:
    final_packet_imports = _imports(ROOT / "core" / "final_answer_packet.py")
    author_runtime_imports = _imports(ROOT / "core" / "author_execution_runtime.py")
    forbidden_runtime_imports = {
        "core.search_providers",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.search_web",
        "core.pipeline_orchestrator",
    }

    assert final_packet_imports.isdisjoint(forbidden_runtime_imports)
    assert author_runtime_imports.isdisjoint(forbidden_runtime_imports - {"core.pipeline_orchestrator"})

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")
    for token in (
        "source_bound_numeric_unknowns",
        "satisfied_source_obligations",
        "not_supported_by_sufficiency_satisfied_obligation",
        "FinalAnswerReadinessStatus.BLOCKED",
    ):
        assert token not in pipeline_source

    adapter_source = (ROOT / "core" / "final_answer_runtime_adapter.py").read_text(encoding="utf-8")
    assert "format_citation" not in adapter_source
    assert "ask_model" not in adapter_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
