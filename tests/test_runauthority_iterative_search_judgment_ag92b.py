from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.authoritative_source_action import (
    AuthoritativeSourceActionFacts,
    build_authoritative_source_obligation_state_and_action,
)
from core.evidence_ledger import (
    CandidateDisposition,
    EvidenceLedger,
    build_evidence_ledger_observation_from_run_contract,
)
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.run_authority_contract_runtime import execute_run_contract_synthesis_action
from core.run_authority_contract_templates import build_deterministic_contract
from core.run_authority_search_judgment import (
    RunSearchJudgmentDecision,
    RunSearchJudgmentInput,
    SearchJudgmentClassification,
)
from core.run_authority_search_judgment_prompt import (
    RUN_AUTHORITY_SEARCH_JUDGMENT_SYSTEM_PROMPT,
)
from core.run_authority_search_judgment_runtime import (
    execute_run_authority_search_judgment_action,
)
from core.run_authority_search_judgment_validation import (
    build_deterministic_search_judgment,
)
from core.run_controller import RunController
from core.run_kernel import (
    SEARCH_JUDGMENT_STAGE,
    ActionType,
    ObservationType,
    RunKernel,
)

ROOT = Path(__file__).resolve().parents[1]


def _contract(query: str) -> dict[str, Any]:
    return build_deterministic_contract(query=query, mode="Balanced").to_projection()


def _ledger_projection(
    contract: dict[str, Any],
    *,
    candidates: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        build_evidence_ledger_observation_from_run_contract(
            observation_id="ledger:contract",
            contract_projection=contract,
        ).to_dict()
    )
    if candidates or links:
        ledger.reduce_observation(
            {
                "observation_id": "ledger:candidates",
                "observation_source": "ag92b_fixture",
                "candidates": candidates or [],
                "requirement_links": links or [],
            }
        )
    return ledger.to_projection().to_dict()


def _candidate(
    *,
    candidate_id: str = "C1",
    source_class: str = "official_current_rules",
    source_tier: str = "official",
    currentness: str = "current",
    disposition: str = CandidateDisposition.ACCEPTED.value,
    eligible: bool = True,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "url": f"https://example.test/{candidate_id}",
        "title": candidate_id,
        "source_class": source_class,
        "source_tier": source_tier,
        "currentness_signal": currentness,
        "disposition": disposition,
        "eligible_for_stronger_obligation": eligible,
        "reason": reason,
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


def _input(
    contract: dict[str, Any],
    ledger: dict[str, Any],
    *,
    query_facts: dict[str, Any] | None = None,
    helper_proposals: dict[str, Any] | None = None,
    budget: dict[str, Any] | None = None,
) -> RunSearchJudgmentInput:
    return RunSearchJudgmentInput(
        contract_projection=contract,
        evidence_ledger_projection=ledger,
        query_facts=query_facts or {"query_preview": "research query"},
        retrieval_observations={"result_count": ledger.get("candidate_count", 0)},
        helper_proposals=helper_proposals or {},
        budget=budget or {"iteration": 1, "max_iterations": 3},
    )


def _source_bound_only(contract: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(contract)
    requirements = [
        item
        for item in out["source_requirements"]
        if item["requirement_kind"] == "source_bound_numeric"
    ]
    out["source_requirements"] = requirements
    out["source_requirement_summary"] = requirements
    out["source_requirement_count"] = len(requirements)
    out["required_source_requirement_count"] = len(requirements)
    return out


def _without_source_requirements(contract: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(contract)
    out["source_requirements"] = []
    out["source_requirement_summary"] = []
    out["source_requirement_count"] = 0
    out["required_source_requirement_count"] = 0
    return out


def _semantic_gap_helper(
    *,
    component_id: str = "component:fee",
    component_digest: str = "component-digest-fee",
    contract_version: str = "accepted-v1",
    contract_digest: str = "accepted-digest-v1",
    duplicate: bool = False,
    stale_component_digest: str | None = None,
    requirement_kind: str = "semantic_component_coverage",
) -> dict[str, Any]:
    assessment = {
        "requirement_id": f"semantic:missing_required_component_coverage:{component_id}",
        "requirement_kind": requirement_kind,
        "answer_component_id": component_id,
        "component_id": component_id,
        "accepted_contract_version": contract_version,
        "accepted_contract_digest": contract_digest,
        "component_digest": stale_component_digest or component_digest,
        "semantic_gap_code": "missing_required_component_coverage",
        "status": "missing",
    }
    assessments = [assessment, dict(assessment)] if duplicate else [assessment]
    return {
        "semantic_state_facts": {
            "accepted_contract_version": contract_version,
            "accepted_contract_digest": contract_digest,
            "accepted_required_component_refs": [
                {
                    "answer_component_id": component_id,
                    "component_digest": component_digest,
                    "accepted_contract_version": contract_version,
                    "accepted_contract_digest": contract_digest,
                }
            ],
            "component_summaries": [
                {
                    "component_id": component_id,
                    "component_digest": component_digest,
                    "coverage_present": False,
                    "coverage_suspect": False,
                }
            ],
        },
        "semantic_missing_assessments": assessments,
    }


def _kernel_with_official_contract() -> tuple[RunKernel, dict[str, Any]]:
    kernel = RunKernel.start(run_id="ag92b-run", request_id="request")
    contract_action = kernel.authorize_run_contract_synthesis(
        inputs={"query_length": 41}
    )
    contract_result = execute_run_contract_synthesis_action(
        contract_action,
        query="What is the current official filing fee?",
        mode="Balanced",
        current_date="June 9, 2026",
        route_projection={"intent": "general", "query_type": "rule"},
    )
    kernel.reduce(contract_result.observation)
    contract = dict(kernel.state.run_contract_projection)
    ledger_action = kernel.authorize_evidence_ledger_reduction(
        inputs={"observation_source": "run_authority_contract"}
    )
    ledger_result = execute_evidence_ledger_reduction_action(
        ledger_action,
        payload=build_evidence_ledger_observation_from_run_contract(
            observation_id="ag92b-run:ledger:contract",
            contract_projection=contract,
        ).to_dict(),
    )
    kernel.reduce(ledger_result.observation)
    return kernel, contract


def _execute_and_reduce(
    kernel: RunKernel,
    judgment_input: RunSearchJudgmentInput,
    **kwargs: Any,
) -> Any:
    action = kernel.authorize_search_judgment(inputs={"phase": "ag92b_test"})
    result = execute_run_authority_search_judgment_action(
        action,
        judgment_input=judgment_input,
        **kwargs,
    )
    kernel.reduce(result.observation)
    return result


def test_run_kernel_authorizes_executes_and_reduces_search_judgment() -> None:
    kernel, contract = _kernel_with_official_contract()
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    action = kernel.authorize_search_judgment(inputs={"candidate_count": 0})

    assert action.action_type is ActionType.SEARCH_JUDGMENT_DECIDE
    assert action.stage == SEARCH_JUDGMENT_STAGE
    assert action.expected_observation_type is ObservationType.SEARCH_JUDGMENT_DECIDED

    result = execute_run_authority_search_judgment_action(
        action,
        judgment_input=_input(contract, ledger),
    )
    kernel.reduce(result.observation)

    projection = kernel.state.search_judgment_projection
    assert projection["owner"] == "RunKernel.RunAuthoritySearchJudgment"
    assert projection["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["decision"] in {
        RunSearchJudgmentDecision.RECOVER_MISSING_OFFICIAL_CURRENT.value,
        RunSearchJudgmentDecision.RECOVER_MISSING_SOURCE_BOUND_NUMERIC.value,
    }
    assert kernel.state.search_judgment_history
    assert (
        kernel.to_trace_fragment()["run_kernel"]["search_judgment_projection"][
            "judgment_id"
        ]
        == projection["judgment_id"]
    )


def test_search_judgment_executor_validates_authorized_action() -> None:
    kernel, contract = _kernel_with_official_contract()
    wrong_action = kernel.authorize_route_request(inputs={"route": "wrong"})
    with pytest.raises(ValueError, match="authorized action type"):
        execute_run_authority_search_judgment_action(
            wrong_action,
            judgment_input=_input(
                contract,
                kernel.state.evidence_ledger.to_projection().to_dict(),
            ),
        )


def test_official_current_lower_tier_lead_is_not_satisfied() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(
        contract,
        candidates=[
            _candidate(
                source_class="reputable_secondary",
                source_tier="secondary",
                eligible=False,
            )
        ],
        links=_links(contract),
    )
    judgment = build_deterministic_search_judgment(_input(contract, ledger))

    assert judgment.decision in {
        RunSearchJudgmentDecision.RECOVER_MISSING_OFFICIAL_CURRENT,
        RunSearchJudgmentDecision.RECOVER_MISSING_SOURCE_BOUND_NUMERIC,
    }
    assert SearchJudgmentClassification.LOWER_TIER_LEAD_ONLY.value in (
        judgment.classifications
    )
    assert not judgment.satisfaction.contract_satisfied


def test_satisfied_evidence_ledger_custody_stops_satisfied() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(
        contract,
        candidates=[_candidate()],
        links=_links(contract),
    )
    judgment = build_deterministic_search_judgment(_input(contract, ledger))

    assert judgment.decision is RunSearchJudgmentDecision.STOP_SATISFIED
    assert SearchJudgmentClassification.CONTRACT_SATISFIED.value in (
        judgment.classifications
    )


def test_legal_current_primary_gap_recovers_legal_primary() -> None:
    contract = _contract("What is the current California legal deadline to appeal?")
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_search_judgment(_input(contract, ledger))

    assert judgment.decision is RunSearchJudgmentDecision.RECOVER_MISSING_LEGAL_PRIMARY
    assert "legal_or_regulatory_text" in judgment.target_source_classes


def test_canonical_docs_gap_recovers_canonical_docs() -> None:
    contract = _contract("What is the current OpenAI Responses API parameter?")
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_search_judgment(_input(contract, ledger))

    assert judgment.decision is RunSearchJudgmentDecision.RECOVER_MISSING_CANONICAL
    assert set(judgment.target_source_classes) & {
        "primary_source_documents",
        "archival_primary_text",
    }


def test_source_bound_numeric_gap_recovers_or_stops_insufficient_when_exhausted() -> None:
    contract = _source_bound_only(_contract("What is the current official filing fee?"))
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_search_judgment(_input(contract, ledger))
    exhausted = build_deterministic_search_judgment(
        _input(
            contract,
            ledger,
            budget={"iteration": 3, "max_iterations": 3, "budget_exhausted": True},
        )
    )

    assert (
        judgment.decision
        is RunSearchJudgmentDecision.RECOVER_MISSING_SOURCE_BOUND_NUMERIC
    )
    assert exhausted.decision is RunSearchJudgmentDecision.STOP_INSUFFICIENT
    assert exhausted.insufficient_posture["posture"] == "insufficient_partial"


def test_semantic_component_gap_preserves_version_bound_identity() -> None:
    contract = _without_source_requirements(_contract("What is the filing fee?"))
    ledger = _ledger_projection(contract)

    judgment = build_deterministic_search_judgment(
        _input(
            contract,
            ledger,
            helper_proposals=_semantic_gap_helper(),
        )
    )

    semantic_gap = judgment.gaps[0].to_dict()
    assert semantic_gap["requirement_kind"] == "semantic_component_coverage"
    assert semantic_gap["accepted_contract_version"] == "accepted-v1"
    assert semantic_gap["accepted_contract_digest"] == "accepted-digest-v1"
    assert semantic_gap["answer_component_id"] == "component:fee"
    assert semantic_gap["component_digest"] == "component-digest-fee"
    assert semantic_gap["semantic_gap_code"] == "missing_required_component_coverage"
    assert judgment.recommended_queries == ()
    assert judgment.helper_assessments["semantic_component_gap_authority_valid"] is True


def test_duplicate_semantic_component_gaps_fail_closed() -> None:
    contract = _without_source_requirements(_contract("What is the filing fee?"))
    ledger = _ledger_projection(contract)

    judgment = build_deterministic_search_judgment(
        _input(
            contract,
            ledger,
            helper_proposals=_semantic_gap_helper(duplicate=True),
        )
    )

    assert judgment.gaps == ()
    assert judgment.helper_assessments["semantic_component_gap_authority_valid"] is False
    assert "duplicate_semantic_component_gap" in judgment.helper_assessments[
        "semantic_component_gap_authority_reasons"
    ]


def test_stale_semantic_component_identity_fails_closed() -> None:
    contract = _without_source_requirements(_contract("What is the filing fee?"))
    ledger = _ledger_projection(contract)

    judgment = build_deterministic_search_judgment(
        _input(
            contract,
            ledger,
            helper_proposals=_semantic_gap_helper(
                stale_component_digest="stale-component-digest"
            ),
        )
    )

    assert judgment.gaps == ()
    assert "semantic_component_gap_stale_component_identity" in (
        judgment.helper_assessments["semantic_component_gap_authority_reasons"]
    )


def test_generic_semantic_recovery_kind_does_not_erase_component_identity() -> None:
    contract = _without_source_requirements(_contract("What is the filing fee?"))
    ledger = _ledger_projection(contract)

    judgment = build_deterministic_search_judgment(
        _input(
            contract,
            ledger,
            helper_proposals=_semantic_gap_helper(requirement_kind="source_class"),
        )
    )

    assert judgment.gaps == ()
    assert "semantic_component_gap_generic_kind_erases_identity" in (
        judgment.helper_assessments["semantic_component_gap_authority_reasons"]
    )
    assert judgment.recommended_queries == ()


def test_ordinary_explainer_does_not_over_require_official_recovery() -> None:
    contract = _contract("Explain why plants need sunlight")
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_search_judgment(_input(contract, ledger))

    assert judgment.decision is RunSearchJudgmentDecision.DEFER_TO_EXISTING_LEGACY_COMPATIBILITY
    assert "official_current_rules" not in judgment.target_source_classes


def test_helper_satisfied_with_stale_or_lower_tier_evidence_is_rejected() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(
        contract,
        candidates=[
            _candidate(
                source_class="official_current_rules",
                source_tier="official",
                currentness="stale",
                reason="off-topic stale result",
            )
        ],
        links=_links(contract),
    )
    judgment = build_deterministic_search_judgment(
        _input(
            contract,
            ledger,
            helper_proposals={"retrieval_stop": {"decision": "stop_satisfied"}},
        )
    )

    assert SearchJudgmentClassification.HELPER_ASSESSMENT_REJECTED.value in (
        judgment.classifications
    )
    assert SearchJudgmentClassification.STALE_OR_OFF_TOPIC_ONLY.value in (
        judgment.classifications
    )
    assert judgment.decision is not RunSearchJudgmentDecision.STOP_SATISFIED


def test_duplicate_query_without_new_gap_target_is_blocked() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_search_judgment(
        _input(
            contract,
            ledger,
            query_facts={
                "proposed_query_signature": "sig-1",
                "prior_query_signatures": ["sig-1"],
                "target_source_classes": [],
            },
        )
    )

    assert judgment.decision is RunSearchJudgmentDecision.BLOCK_REDUNDANT_QUERY
    assert judgment.redundancy.blocked is True


def test_similar_query_with_new_source_class_target_is_allowed() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_search_judgment(
        _input(
            contract,
            ledger,
            query_facts={
                "proposed_query_signature": "sig-1",
                "prior_query_signatures": ["sig-1"],
                "target_source_classes": ["official_current_rules"],
            },
        )
    )

    assert judgment.decision is not RunSearchJudgmentDecision.BLOCK_REDUNDANT_QUERY
    assert judgment.continuation.allowed is True
    assert SearchJudgmentClassification.NEW_SOURCE_CLASS_TARGET_ALLOWED.value in (
        judgment.classifications
    )


def test_runtime_consumer_promotes_reduced_judgment_into_recovery_action() -> None:
    kernel, contract = _kernel_with_official_contract()
    result = _execute_and_reduce(
        kernel,
        _input(contract, kernel.state.evidence_ledger.to_projection().to_dict()),
    )
    assert result.judgment.decision in {
        RunSearchJudgmentDecision.RECOVER_MISSING_OFFICIAL_CURRENT,
        RunSearchJudgmentDecision.RECOVER_MISSING_SOURCE_BOUND_NUMERIC,
    }

    controller = RunController()
    action_result = build_authoritative_source_obligation_state_and_action(
        controller,
        facts=AuthoritativeSourceActionFacts(
            query="What is the current official filing fee?",
            core_topic="filing fee",
            recommendation={
                "source_class_recovery_recommended": False,
                "source_class_underfire_shadow": True,
                "source_class_gap_candidates": ["official_current_rules"],
            },
            source_class_observability={},
            source_class_evidence_signals={},
            run_search_judgment_projection=kernel.state.search_judgment_projection,
            iteration_budget_available=True,
            answer_contract_source_class_slot_available=True,
            ordinary_iteration_budget_remaining=2,
        ),
    )

    assert action_result.recommendation["run_authority_search_judgment_consumed"] is True
    assert action_result.active_source_class_recovery_lifecycle[
        "active_source_class_recovery_eligible"
    ] is True
    assert controller.state.active_source_class_recovery_queries


def test_invalid_smart_model_json_falls_back_without_raw_output_storage() -> None:
    kernel, contract = _kernel_with_official_contract()
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_ask_model(*args: Any, **kwargs: Any) -> str:
        calls.append((args, kwargs))
        return "{not-json sentinel-raw-model-output}"

    result = _execute_and_reduce(
        kernel,
        _input(
            contract,
            ledger,
            helper_proposals={"raw_provider_payload": "SENTINEL_RAW_PAYLOAD"},
        ),
        ask_model=fake_ask_model,
        clean_json_response=lambda text: text,
        smart_model_enabled=True,
        provider="fake-provider",
        model="fake-model",
        effort="high",
        use_reasoning=True,
    )

    assert calls
    assert calls[0][0][1] == RUN_AUTHORITY_SEARCH_JUDGMENT_SYSTEM_PROMPT
    assert calls[0][1]["require_json"] is True
    assert calls[0][1]["effort"] == "high"
    assert result.validation.status.value == "fallback"
    trace = json.dumps(kernel.to_trace_fragment(), sort_keys=True)
    assert "sentinel-raw-model-output" not in trace
    assert "SENTINEL_RAW_PAYLOAD" not in trace


def test_smart_model_cannot_downgrade_lower_tier_to_satisfied() -> None:
    kernel, contract = _kernel_with_official_contract()
    ledger = _ledger_projection(
        contract,
        candidates=[
            _candidate(
                source_class="reputable_secondary",
                source_tier="secondary",
                eligible=False,
            )
        ],
        links=_links(contract),
    )
    kernel.state.evidence_ledger = EvidenceLedger()
    ledger_action = kernel.authorize_evidence_ledger_reduction(
        inputs={"observation_source": "lower_tier_fixture"}
    )
    ledger_result = execute_evidence_ledger_reduction_action(
        ledger_action,
        payload={
            "observation_id": "lower-tier-reset",
            "observation_source": "lower_tier_fixture",
            "source_requirements": ledger["source_requirements"],
            "candidates": ledger["candidate_records"],
            "requirement_links": ledger["requirement_links"],
        },
    )
    kernel.reduce(ledger_result.observation)

    def fake_ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(
            {
                "decision": "stop_satisfied",
                "classifications": ["contract_satisfied"],
                "satisfaction": {"contract_satisfied": True},
                "gaps": [],
                "rationale": "secondary source is enough",
            }
        )

    result = _execute_and_reduce(
        kernel,
        _input(contract, kernel.state.evidence_ledger.to_projection().to_dict()),
        ask_model=fake_ask_model,
        clean_json_response=lambda text: text,
        smart_model_enabled=True,
    )

    assert result.validation.status.value == "repaired"
    assert result.judgment.decision is not RunSearchJudgmentDecision.STOP_SATISFIED
    assert SearchJudgmentClassification.LOWER_TIER_LEAD_ONLY.value in (
        result.judgment.classifications
    )


def test_raw_prompt_model_payloads_and_private_artifacts_excluded_from_trace() -> None:
    kernel, contract = _kernel_with_official_contract()
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    _execute_and_reduce(
        kernel,
        _input(
            contract,
            ledger,
            query_facts={
                "query_preview": "fee",
                "raw_prompt": "SENTINEL_RAW_PROMPT",
                "db_row": "SENTINEL_DB_ROW",
                "cache": "SENTINEL_CACHE",
                "output_packet": "SENTINEL_PACKET",
                "raw_trace": "SENTINEL_PRIVATE_TRACE",
            },
            helper_proposals={"raw_provider_payload": "SENTINEL_PROVIDER_PAYLOAD"},
        ),
    )
    trace = json.dumps(kernel.to_trace_fragment(), sort_keys=True)

    for sentinel in (
        "SENTINEL_RAW_PROMPT",
        "SENTINEL_DB_ROW",
        "SENTINEL_CACHE",
        "SENTINEL_PACKET",
        "SENTINEL_PRIVATE_TRACE",
        "SENTINEL_PROVIDER_PAYLOAD",
    ):
        assert sentinel not in trace
    assert '"prompt_text_retained": false' in trace
    assert '"model_response_text_retained": false' in trace
    assert '"provider_payload_retained": false' in trace


def test_static_guards_keep_prompt_and_validators_out_of_pipeline_orchestrator() -> None:
    pipeline = (ROOT / "core" / "pipeline_orchestrator.py").read_text()

    assert "RUN_AUTHORITY_SEARCH_JUDGMENT_SYSTEM_PROMPT" not in pipeline
    assert "careful research director deciding the next retrieval action" not in pipeline
    assert "validate_or_repair_search_judgment" not in pipeline
    assert "build_deterministic_search_judgment" not in pipeline
    assert "execute_run_authority_search_judgment_action(" in pipeline
    assert "authorize_search_judgment(" in pipeline
