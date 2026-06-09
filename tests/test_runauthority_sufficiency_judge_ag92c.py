from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.evidence_ledger import (
    CandidateDisposition,
    EvidenceLedger,
    build_evidence_ledger_observation_from_run_contract,
)
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.final_answer_packet import (
    ClaimPosture,
    FinalAnswerReadinessStatus,
    SourceObligationStatus,
)
from core.final_answer_runtime_adapter import (
    build_final_answer_packet,
    derive_author_input_payload,
)
from core.run_authority_contract_runtime import execute_run_contract_synthesis_action
from core.run_authority_contract_templates import build_deterministic_contract
from core.run_authority_search_judgment import RunSearchJudgmentInput
from core.run_authority_search_judgment_runtime import (
    execute_run_authority_search_judgment_action,
)
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgmentInput,
    SufficiencyPosture,
)
from core.run_authority_sufficiency_prompt import (
    RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT,
)
from core.run_authority_sufficiency_runtime import (
    execute_run_authority_sufficiency_judgment_action,
)
from core.run_authority_sufficiency_validation import (
    build_deterministic_sufficiency_judgment,
)
from core.run_kernel import (
    SUFFICIENCY_JUDGMENT_STAGE,
    ActionType,
    ObservationType,
    RunKernel,
)

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
            observation_id="ag92c:ledger:contract",
            contract_projection=contract,
        ).to_dict()
    )
    if candidates or links:
        ledger.reduce_observation(
            {
                "observation_id": "ag92c:ledger:candidates",
                "observation_source": "ag92c_fixture",
                "candidates": candidates or [],
                "requirement_links": links or [],
            }
        )
    return ledger.to_projection().to_dict()


def _input(
    contract: dict[str, Any],
    ledger: dict[str, Any],
    *,
    search: dict[str, Any] | None = None,
    search_history: list[dict[str, Any]] | None = None,
    answer_contract: dict[str, Any] | None = None,
    final_evidence_count: int = 1,
    conflict_facts: dict[str, Any] | None = None,
    inference_facts: dict[str, Any] | None = None,
    weak_failure_facts: dict[str, Any] | None = None,
    budget: dict[str, Any] | None = None,
) -> RunSufficiencyJudgmentInput:
    return RunSufficiencyJudgmentInput(
        contract_projection=contract,
        evidence_ledger_projection=ledger,
        search_judgment_projection=search or {"decision": "defer_to_legacy_compatibility"},
        search_judgment_history=search_history or [],
        answer_contract_projection=answer_contract or {},
        source_obligation_projection=ledger,
        final_evidence_facts={
            "final_evidence_count": final_evidence_count,
            "author_evidence_count": final_evidence_count,
        },
        conflict_facts=conflict_facts or {},
        indirect_inference_facts=inference_facts or {},
        weak_failure_facts=weak_failure_facts or {},
        budget=budget or {"iteration": 1, "max_iterations": 3},
    )


def _final_passage() -> dict[str, Any]:
    return {
        "source_id": "S1",
        "url": "https://example.gov/rule",
        "title": "Official rule",
        "text": "Official current rule excerpt.",
        "source_tier": "official",
        "source_class": "official_current_rules",
    }


def _sufficiency_projection(
    contract: dict[str, Any],
    ledger: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    return build_deterministic_sufficiency_judgment(
        _input(contract, ledger, **kwargs)
    ).to_projection()


def _kernel_with_contract_ledger_search(
    *,
    satisfied: bool,
) -> tuple[RunKernel, dict[str, Any], dict[str, Any]]:
    kernel = RunKernel.start(run_id="ag92c-run", request_id="request")
    contract_action = kernel.authorize_run_contract_synthesis(inputs={})
    contract_result = execute_run_contract_synthesis_action(
        contract_action,
        query="What is the current official filing fee?",
        mode="Balanced",
        current_date="June 9, 2026",
        route_projection={"intent": "general", "query_type": "rule"},
    )
    kernel.reduce(contract_result.observation)
    contract = dict(kernel.state.run_contract_projection)

    ledger_action = kernel.authorize_evidence_ledger_reduction(inputs={})
    ledger_observation = build_evidence_ledger_observation_from_run_contract(
        observation_id="ag92c-run:ledger:contract",
        contract_projection=contract,
    ).to_dict()
    ledger_result = execute_evidence_ledger_reduction_action(
        ledger_action,
        payload=ledger_observation,
    )
    kernel.reduce(ledger_result.observation)
    if satisfied:
        candidate_action = kernel.authorize_evidence_ledger_reduction(inputs={})
        candidate_result = execute_evidence_ledger_reduction_action(
            candidate_action,
            payload={
                "observation_id": "ag92c-run:ledger:candidate",
                "observation_source": "ag92c_fixture",
                "candidates": [_candidate()],
                "requirement_links": _links(contract),
            },
        )
        kernel.reduce(candidate_result.observation)
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()

    search_action = kernel.authorize_search_judgment(inputs={})
    search_result = execute_run_authority_search_judgment_action(
        search_action,
        judgment_input=RunSearchJudgmentInput(
            contract_projection=contract,
            evidence_ledger_projection=ledger,
            retrieval_observations={"result_count": ledger.get("candidate_count", 0)},
            budget={"iteration": 1, "max_iterations": 3},
        ),
    )
    kernel.reduce(search_result.observation)
    return kernel, contract, kernel.state.evidence_ledger.to_projection().to_dict()


def test_run_kernel_authorizes_executes_and_reduces_sufficiency_judgment() -> None:
    kernel, contract, ledger = _kernel_with_contract_ledger_search(satisfied=True)
    action = kernel.authorize_sufficiency_judgment(inputs={"phase": "ag92c"})

    assert action.action_type is ActionType.SUFFICIENCY_JUDGMENT_DECIDE
    assert action.stage == SUFFICIENCY_JUDGMENT_STAGE
    assert action.expected_observation_type is (
        ObservationType.SUFFICIENCY_JUDGMENT_DECIDED
    )

    result = execute_run_authority_sufficiency_judgment_action(
        action,
        judgment_input=_input(
            contract,
            ledger,
            search=kernel.state.search_judgment_projection,
            search_history=kernel.state.search_judgment_history,
        ),
    )
    kernel.reduce(result.observation)

    projection = kernel.state.sufficiency_judgment_projection
    assert projection["owner"] == "RunKernel.RunAuthoritySufficiencyJudgment"
    assert projection["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["decision"] == RunSufficiencyDecision.READY_DIRECT.value
    assert projection["final_packet_inputs"]["readiness_status"] == "author_ready"
    assert kernel.state.sufficiency_judgment_history
    assert (
        kernel.to_trace_fragment()["run_kernel"]["sufficiency_judgment_projection"][
            "judgment_id"
        ]
        == projection["judgment_id"]
    )


def test_sufficiency_executor_validates_authorized_action() -> None:
    kernel, contract, ledger = _kernel_with_contract_ledger_search(satisfied=True)
    wrong_action = kernel.authorize_route_request(inputs={"route": "wrong"})
    with pytest.raises(ValueError, match="authorized action type"):
        execute_run_authority_sufficiency_judgment_action(
            wrong_action,
            judgment_input=_input(contract, ledger),
        )


def test_all_required_ledger_obligations_satisfied_ready_direct() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(
        contract,
        candidates=[_candidate()],
        links=_links(contract),
    )
    judgment = build_deterministic_sufficiency_judgment(
        _input(contract, ledger, search={"decision": "stop_satisfied"})
    )

    assert judgment.decision is RunSufficiencyDecision.READY_DIRECT
    assert judgment.final_answer_posture is SufficiencyPosture.DIRECT_ANSWER
    assert judgment.required_obligations_satisfied is True
    assert not judgment.missing_required_obligations


@pytest.mark.parametrize(
    ("query", "expected_kind", "expected_caveat"),
    [
        (
            "What is the current official filing fee?",
            "official_current",
            "official_current_unsatisfied:official_current_rules",
        ),
        (
            "What is the current California legal deadline to appeal?",
            "legal_primary",
            "missing_legal_primary_source_must_be_caveated",
        ),
        (
            "What is the current OpenAI Responses API parameter?",
            "canonical_docs",
            "missing_canonical_docs_must_be_caveated",
        ),
    ],
)
def test_missing_required_primary_obligations_are_not_ready_direct(
    query: str,
    expected_kind: str,
    expected_caveat: str,
) -> None:
    contract = _contract(query)
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_sufficiency_judgment(_input(contract, ledger))

    assert judgment.decision is not RunSufficiencyDecision.READY_DIRECT
    assert any(
        item.requirement_kind == expected_kind
        for item in judgment.missing_required_obligations
    )
    assert expected_caveat in judgment.mandatory_caveats
    assert judgment.final_answer_posture in {
        SufficiencyPosture.PARTIAL_ANSWER,
        SufficiencyPosture.INSUFFICIENT_ANSWER,
    }


def test_source_bound_numeric_missing_remains_unknown() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_sufficiency_judgment(_input(contract, ledger))

    assert judgment.decision is RunSufficiencyDecision.SOURCE_BOUND_NUMERIC_UNKNOWN
    assert judgment.source_bound_numeric_unknowns
    assert "do_not_present_source_bound_numeric_unknown_as_known" in (
        judgment.prohibited_upgrades
    )


@pytest.mark.parametrize(
    "candidate",
    [
        _candidate(source_class="reputable_secondary", source_tier="secondary", eligible=False),
        _candidate(currentness="stale"),
        _candidate(source_class="social_signal", source_tier="social_or_forum", eligible=False),
    ],
)
def test_lower_tier_stale_or_off_topic_evidence_cannot_satisfy_strong_obligation(
    candidate: dict[str, Any],
) -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract, candidates=[candidate], links=_links(contract))
    judgment = build_deterministic_sufficiency_judgment(_input(contract, ledger))

    assert judgment.decision is not RunSufficiencyDecision.READY_DIRECT
    assert judgment.missing_required_obligations
    assert "do_not_treat_lower_tier_stale_or_off_topic_evidence_as_required_custody" in (
        judgment.prohibited_upgrades
    )


def test_search_stop_insufficient_forces_insufficient_or_partial_posture() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_sufficiency_judgment(
        _input(
            contract,
            ledger,
            search={"decision": "stop_insufficient"},
            budget={"iteration": 3, "max_iterations": 3, "budget_exhausted": True},
        )
    )

    assert judgment.decision is RunSufficiencyDecision.SOURCE_BOUND_NUMERIC_UNKNOWN
    assert "search_judgment_stop_insufficient" in judgment.readiness_reasons
    assert judgment.final_answer_posture in {
        SufficiencyPosture.PARTIAL_ANSWER,
        SufficiencyPosture.INSUFFICIENT_ANSWER,
    }


def test_search_stop_satisfied_plus_satisfied_ledger_ready() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract, candidates=[_candidate()], links=_links(contract))
    judgment = build_deterministic_sufficiency_judgment(
        _input(contract, ledger, search={"decision": "stop_satisfied"})
    )

    assert judgment.decision is RunSufficiencyDecision.READY_DIRECT
    assert judgment.contract_fulfilled is True


def test_ordinary_explainer_without_required_official_current_does_not_overblock() -> None:
    contract = _contract("Explain why plants need sunlight")
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_sufficiency_judgment(
        _input(contract, ledger, final_evidence_count=1)
    )

    assert not judgment.missing_required_obligations
    assert judgment.final_answer_allowed is True
    assert judgment.final_answer_posture is not SufficiencyPosture.BLOCKED


def test_unresolved_central_conflict_blocks_overconfident_posture() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract, candidates=[_candidate()], links=_links(contract))
    judgment = build_deterministic_sufficiency_judgment(
        _input(
            contract,
            ledger,
            conflict_facts={
                "conflicts_present": True,
                "unresolved_central_conflict": True,
            },
        )
    )

    assert judgment.decision is RunSufficiencyDecision.CONFLICT_BLOCKED
    assert judgment.final_answer_posture is SufficiencyPosture.ANSWER_WITH_CAVEATS
    assert "do_not_flatten_unresolved_conflicts_into_direct_claims" in (
        judgment.prohibited_upgrades
    )


def test_indirect_inference_forces_labeling_not_direct_source_laundering() -> None:
    contract = _contract("Can we infer market share from sourced revenue numbers?")
    ledger = _ledger_projection(contract)
    judgment = build_deterministic_sufficiency_judgment(
        _input(
            contract,
            ledger,
            inference_facts={"inferred_claim_count": 1, "claim_id": "claim-1"},
        )
    )

    assert judgment.decision is RunSufficiencyDecision.INFERENCE_ONLY_WITH_LABELING
    assert judgment.indirect_inference_claims[0]["requires_inference_label"] is True
    assert "do_not_launder_inference_as_direct_source_claim" in (
        judgment.prohibited_upgrades
    )


def test_weak_corpus_and_failure_card_reach_packet_and_author_payload() -> None:
    contract = _contract("Explain why plants need sunlight")
    ledger = _ledger_projection(contract)
    projection = _sufficiency_projection(
        contract,
        ledger,
        weak_failure_facts={
            "corpus_weak": True,
            "weak_corpus_reason": "off_topic",
            "failure_card": {"show": True, "reason": "no_useful_content"},
        },
    )
    packet = build_final_answer_packet(
        run_id="ag92c-weak",
        final_evidence=[_final_passage()],
        run_contract_projection=contract,
        sufficiency_judgment_projection=projection,
    )
    packet, payload = derive_author_input_payload(
        packet,
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert packet.readiness_status is FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED
    assert ClaimPosture.FAILURE_CARD_AUTHORIZED in packet.claim_postures
    assert ClaimPosture.WEAK_CORPUS_AUTHORIZED in packet.claim_postures
    assert "failure_card_authorized:no_useful_content" in payload.prompt
    assert "do_not_upgrade_weak_or_failure_card_posture_to_direct" in payload.prompt


def test_final_answer_packet_consumes_sufficiency_to_demote_legacy_missing_inference() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract, candidates=[_candidate()], links=_links(contract))
    direct_projection = _sufficiency_projection(
        contract,
        ledger,
        search={"decision": "stop_satisfied"},
    )

    legacy_packet = build_final_answer_packet(
        run_id="ag92c-legacy",
        final_evidence=[_final_passage()],
        run_contract_projection=contract,
    )
    packet = build_final_answer_packet(
        run_id="ag92c-consumed",
        final_evidence=[_final_passage()],
        run_contract_projection=contract,
        sufficiency_judgment_projection=direct_projection,
    )

    assert legacy_packet.readiness_status is (
        FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED
    )
    assert packet.readiness_status is FinalAnswerReadinessStatus.AUTHOR_READY
    assert not any(
        obligation.status is not SourceObligationStatus.SATISFIED
        for obligation in packet.source_obligations
    )
    assert packet.author_input_refs["sufficiency_judgment_ref"]["decision"] == (
        RunSufficiencyDecision.READY_DIRECT.value
    )


def test_final_answer_packet_consumes_missing_sufficiency_projection() -> None:
    contract = _contract("What is the current official filing fee?")
    ledger = _ledger_projection(contract)
    projection = _sufficiency_projection(contract, ledger)
    packet = build_final_answer_packet(
        run_id="ag92c-missing",
        final_evidence=[_final_passage()],
        run_contract_projection=contract,
        sufficiency_judgment_projection=projection,
    )
    _packet, payload = derive_author_input_payload(
        packet,
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert packet.readiness_status is FinalAnswerReadinessStatus.INSUFFICIENT_AUTHORIZED
    assert "source_bound_numeric_unknown" in packet.readiness_reasons
    assert "Final answer posture: partial_answer" in payload.prompt
    assert "do_not_present_source_bound_numeric_unknown_as_known" in payload.prompt


def test_smart_model_valid_json_may_adapt_posture_when_safe() -> None:
    kernel, contract, ledger = _kernel_with_contract_ledger_search(satisfied=True)
    action = kernel.authorize_sufficiency_judgment(inputs={})
    deterministic = build_deterministic_sufficiency_judgment(
        _input(contract, ledger, search=kernel.state.search_judgment_projection)
    ).to_projection()
    model_projection = deepcopy(deterministic)
    model_projection["decision"] = RunSufficiencyDecision.READY_WITH_CAVEATS.value
    model_projection["final_answer_posture"] = (
        SufficiencyPosture.ANSWER_WITH_CAVEATS.value
    )
    model_projection["mandatory_caveats"] = ["minor_context_gap"]
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_ask_model(*args: Any, **kwargs: Any) -> str:
        calls.append((args, kwargs))
        return json.dumps(model_projection)

    result = execute_run_authority_sufficiency_judgment_action(
        action,
        judgment_input=_input(
            contract,
            ledger,
            search=kernel.state.search_judgment_projection,
        ),
        ask_model=fake_ask_model,
        clean_json_response=lambda text: text,
        smart_model_enabled=True,
        provider="smart-provider",
        model="smart-model",
        effort="xhigh",
        use_reasoning=True,
    )

    assert calls
    assert calls[0][0][1] == RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT
    assert calls[0][1]["require_json"] is True
    assert calls[0][1]["effort"] == "xhigh"
    assert result.judgment.decision is RunSufficiencyDecision.READY_WITH_CAVEATS
    assert "minor_context_gap" in result.judgment.mandatory_caveats
    assert result.validation.status.value == "valid"


def test_invalid_smart_model_json_falls_back_to_deterministic_without_raw_storage() -> None:
    kernel, contract, ledger = _kernel_with_contract_ledger_search(satisfied=True)
    action = kernel.authorize_sufficiency_judgment(inputs={})

    result = execute_run_authority_sufficiency_judgment_action(
        action,
        judgment_input=_input(contract, ledger),
        ask_model=lambda *_args, **_kwargs: "not-json raw prompt sentinel",
        clean_json_response=lambda text: text,
        smart_model_enabled=True,
    )
    kernel.reduce(result.observation)
    serialized = json.dumps(kernel.to_trace_fragment(), sort_keys=True)

    assert result.validation.status.value == "fallback"
    assert result.judgment.decision is RunSufficiencyDecision.READY_DIRECT
    assert "not-json raw prompt sentinel" not in serialized
    assert "Decide final answer sufficiency" not in serialized
    assert "raw_provider_payload" not in serialized


def test_smart_model_ready_direct_with_required_gaps_is_repaired() -> None:
    kernel, contract, ledger = _kernel_with_contract_ledger_search(satisfied=False)
    action = kernel.authorize_sufficiency_judgment(inputs={})
    unsafe = {
        "decision": RunSufficiencyDecision.READY_DIRECT.value,
        "final_answer_posture": SufficiencyPosture.DIRECT_ANSWER.value,
        "contract_fulfilled": True,
        "required_obligations_satisfied": True,
        "final_answer_allowed": True,
        "rationale": "unsafe direct",
    }

    result = execute_run_authority_sufficiency_judgment_action(
        action,
        judgment_input=_input(contract, ledger),
        ask_model=lambda *_args, **_kwargs: json.dumps(unsafe),
        clean_json_response=lambda text: text,
        smart_model_enabled=True,
    )

    assert result.validation.status.value == "repaired"
    assert result.judgment.decision is not RunSufficiencyDecision.READY_DIRECT
    assert result.judgment.missing_required_obligations


def test_sufficiency_state_excludes_sensitive_raw_material() -> None:
    kernel, contract, ledger = _kernel_with_contract_ledger_search(satisfied=True)
    action = kernel.authorize_sufficiency_judgment(
        inputs={"raw_prompt": "should redact", "api_key": "secret"}
    )
    result = execute_run_authority_sufficiency_judgment_action(
        action,
        judgment_input=_input(
            contract,
            ledger,
            search=kernel.state.search_judgment_projection,
        ),
    )
    kernel.reduce(result.observation)
    serialized = json.dumps(kernel.to_trace_fragment(), sort_keys=True).casefold()

    for forbidden in (
        "should redact",
        "raw prompt",
        "raw_model_response",
        "raw_provider_payload",
        "db_row",
        "output_packet",
        "full_trace",
    ):
        assert forbidden not in serialized
    assert "prompt_text_retained\": false" in serialized
    assert "model_response_text_retained\": false" in serialized


def test_static_guards_keep_sufficiency_brain_out_of_pipeline_orchestrator() -> None:
    pipeline = (ROOT / "core" / "pipeline_orchestrator.py").read_text()
    run_kernel = (ROOT / "core" / "run_kernel.py").read_text()
    runtime = (ROOT / "core" / "run_authority_sufficiency_runtime.py").read_text()
    validation = (
        ROOT / "core" / "run_authority_sufficiency_validation.py"
    ).read_text()
    prompt = (ROOT / "core" / "run_authority_sufficiency_prompt.py").read_text()

    assert "SUFFICIENCY_JUDGMENT_STAGE" in run_kernel
    assert "SUFFICIENCY_JUDGMENT_DECIDE" in run_kernel
    assert "SUFFICIENCY_JUDGMENT_DECIDED" in run_kernel
    assert "sufficiency_judgment_projection" in run_kernel
    assert "run_kernel.authorize_sufficiency_judgment(" in pipeline
    assert "execute_run_authority_sufficiency_judgment_action(" in pipeline
    assert "run_kernel.reduce(sufficiency_result.observation)" in pipeline
    assert "build_run_authority_sufficiency_prompt" not in pipeline
    assert "build_deterministic_sufficiency_judgment" not in pipeline
    assert "validate_or_repair_sufficiency_judgment" not in pipeline
    assert "RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT" not in pipeline
    assert "ask_model(" in runtime
    assert "RUN_AUTHORITY_SUFFICIENCY_SYSTEM_PROMPT" in prompt
    assert "READY_DIRECT" not in pipeline
    assert "lower_tier" in validation
