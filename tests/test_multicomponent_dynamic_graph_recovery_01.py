"""PRODUCT-PATH-REGRESSION: bounded ordinary dynamic graph recovery."""

from __future__ import annotations

import json
from types import SimpleNamespace

from core.component_work_graph_v1 import (
    graph_with_scrutineer,
    reduce_component_work_graph_v1,
    scrutineer_input_packet,
)
from core.multicomponent_component_admission import (
    component_analyst_input_packet,
    component_dprime_input_packet,
    execute_multicomponent_component_admission,
)
from core.multicomponent_dynamic_recovery_runtime import (
    apply_recovered_component_amendment,
    execute_recovery_acquisition,
)
from core.multicomponent_role_runtime import (
    ROLE_SCRUTINEER,
    execute_multicomponent_role_call,
)
from core.ordinary_multicomponent_synthesis_runtime import (
    _evidence_input,
    _semantic_material,
)
from core.run_kernel import Observation, RunStageStatus
from tests.test_multicomponent_component_work_graph_v1 import (
    _flat_graph,
    _validate_synthesis,
)


def _challenged_graph_with_missing_component_proposal():
    kernel, graph = _flat_graph(caveats=("A filing-route rule remains material.",))
    graph = _validate_synthesis(kernel, graph, "E")
    scrutiny_input = scrutineer_input_packet(graph)
    target = next(
        item
        for item in scrutiny_input["challenge_target_catalog"]
        if item["target_kind"] == "synthesis"
    )
    response = {
        "challenge_status": "challenged",
        "reasons": ["The filing-route synthesis omits a necessary rule."],
        "challenge_targets": [
            {
                "target_kind": target["target_kind"],
                "target_key": target["target_key"],
            }
        ],
        "missing_component_proposals": [
            {
                "proposal_key": "bonus_paper_rule",
                "component_label": "Bonus filing route",
                "component_question": (
                    "Must an applicant claiming the income bonus file on paper?"
                ),
                "necessity_reason": (
                    "The accepted filing-route explanation is incomplete without it."
                ),
                "target_kind": target["target_kind"],
                "target_key": target["target_key"],
                "relationship_to_accepted_synthesis_directive": (
                    "It supplies the missing branch of the accepted combined result."
                ),
                "scope_posture": (
                    "required_to_fulfill_existing_accepted_user_obligation"
                ),
                "bounded_search_hints": ["bonus paper application rule"],
                "source_requirement_hints": ["official program rule"],
                "caveats": ["Fictional offline scenario only."],
                "nonclaims": ["No general filing rule is claimed."],
            }
        ],
        "caveats": [],
        "nonclaims": [],
    }
    artifact = execute_multicomponent_role_call(
        run_kernel=kernel,
        role=ROLE_SCRUTINEER,
        input_packet=scrutiny_input,
        ask_model=lambda *_args, **_kwargs: json.dumps(response),
        clean_json_response=lambda value: value,
        provider="offline",
        model="fixture",
        base_url="http://offline.invalid/v1",
        api_key="",
        use_reasoning=False,
        logical_evaluation_key="full-case",
    )
    graph = reduce_component_work_graph_v1(
        run_kernel=kernel,
        operation="scrutiny",
        graph_candidate=graph_with_scrutineer(
            graph,
            scrutineer_artifact=artifact,
        ),
    )
    return kernel, graph


def test_scrutineer_proposal_reduces_to_one_exact_recovery_authorization() -> None:
    kernel, graph = _challenged_graph_with_missing_component_proposal()

    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )

    authorization = kernel.state.projections[action.stage]
    assert authorization["canonical_state"] is True
    assert authorization["proposal_key"] == "bonus_paper_rule"
    assert authorization["target_kind"] == "synthesis"
    assert authorization["target_key"] == "synthesis_01"
    assert authorization["graph_digest"] == graph["graph_digest"]
    assert authorization["recovery_authorization_action_count"] == 1
    assert authorization["recovery_authorization_observation_count"] == 1
    assert authorization["automatic_amendment_authority_class"] == (
        "required_to_fulfill_existing_accepted_user_obligation"
    )


def test_recovery_authority_applies_one_versioned_add_component_amendment() -> None:
    kernel, _graph = _challenged_graph_with_missing_component_proposal()
    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }

    result = apply_recovered_component_amendment(run_kernel=kernel)

    initial = kernel.state.initial_answer_contract
    current = kernel.state.current_answer_contract
    assert current["accepted_contract_version"] != initial["accepted_contract_version"]
    assert current["accepted_contract_digest"] != initial["accepted_contract_digest"]
    assert current["previous_contract_digest"] == initial["accepted_contract_digest"]
    assert len(current["accepted_answer_component_refs"]) == 3
    assert result.component_ref["component_id"].startswith("component:recovered:")
    assert result.component_ref["lifecycle_status"] == "pending"
    assert len(kernel.state.contract_amendment_admission_history) == 1
    assert len(kernel.state.contract_amendment_application_history) == 1
    assert result.amendment_admission["user_confirmation_posture"] == (
        "required_to_fulfill_existing_accepted_user_obligation"
    )
    assert kernel.state.initial_answer_contract == initial


def test_recovery_reenters_ordinary_offline_acquisition_and_evidence_ledger() -> None:
    kernel, _graph = _challenged_graph_with_missing_component_proposal()
    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }
    amendment = apply_recovered_component_amendment(run_kernel=kernel)
    calls: list[list[str]] = []

    def execute_search(queries, *_args, **_kwargs):
        calls.append(list(queries))
        return [
            {
                "title": "Northstar bonus paper rule",
                "url": "https://northstar.example/paper-rule",
                "text": (
                    "Applicants claiming the income-based bonus must submit "
                    "the paper application."
                ),
                "readable_status": "readable",
                "currentness_signal": "current",
                "source_class": "primary_source_documents",
                "source_tier": "official",
            }
        ]

    acquisition = execute_recovery_acquisition(
        run_kernel=kernel,
        runtime_scope={
            "deps": SimpleNamespace(process_search_queries=execute_search),
            "intent": "general",
            "complexity": "medium",
            "search_depth": "basic",
        },
        component_ref=amendment.component_ref,
    )

    assert acquisition.acquired is True, json.dumps(
        {
            "projection": acquisition.projection,
            "ledger": kernel.state.evidence_ledger.to_projection().to_dict(),
        },
        sort_keys=True,
    )
    assert len(calls) == 1
    assert acquisition.bindable is not None
    assert "paper application" in acquisition.bindable.passage["text"]
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    source_id = amendment.component_ref["source_obligation_candidate_ids"][0]
    requirement = next(
        item
        for item in ledger["source_requirements"]
        if item["requirement_id"] == source_id.replace("-", "_")
    )
    assert requirement["status"] == "satisfied"
    assert acquisition.projection["ordinary_acquisition_attempt_count"] == 1
    assert acquisition.projection["direct_semantic_producer_used"] is False


def test_recovered_component_uses_typed_analyst_dprime_and_runkernel_admission() -> None:
    kernel, _graph = _challenged_graph_with_missing_component_proposal()
    kernel.state.initial_answer_contract.update(
        {
            "parent_question_meaning_record_id": "qmr:northstar-recovery",
            "parent_question_meaning_record_digest": "qmr-digest-northstar-recovery",
        }
    )
    action = kernel.authorize_multicomponent_missing_component_recovery(
        proposal_key="bonus_paper_rule"
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )
    kernel.state.initial_answer_contract_projection = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
    }
    amendment = apply_recovered_component_amendment(run_kernel=kernel)

    def execute_search(*_args, **_kwargs):
        return [
            {
                "title": "Northstar bonus paper rule",
                "url": "https://northstar.example/paper-rule",
                "text": (
                    "Applicants claiming the income-based bonus must submit "
                    "the paper application."
                ),
                "readable_status": "readable",
                "currentness_signal": "current",
                "source_class": "primary_source_documents",
                "source_tier": "official",
            }
        ]

    acquisition = execute_recovery_acquisition(
        run_kernel=kernel,
        runtime_scope={
            "deps": SimpleNamespace(process_search_queries=execute_search),
            "intent": "general",
            "complexity": "medium",
            "search_depth": "basic",
        },
        component_ref=amendment.component_ref,
    )
    assert acquisition.bindable is not None
    component_id = str(amendment.component_ref["component_id"])
    analyst_input = component_analyst_input_packet(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        accepted_contract=kernel.state.current_answer_contract,
        component_ref=amendment.component_ref,
        evidence_input=_evidence_input(acquisition.bindable),
    )
    analyst = execute_multicomponent_role_call(
        run_kernel=kernel,
        role="component_analyst",
        input_packet=analyst_input,
        ask_model=lambda *_args, **_kwargs: json.dumps(
            {
                "claim_text": (
                    "Applicants claiming the income-based bonus must submit "
                    "the paper application."
                ),
                "support_status": "supported",
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            }
        ),
        clean_json_response=lambda value: value,
        provider="offline",
        model="fixture",
        base_url="http://offline.invalid/v1",
        api_key="",
        use_reasoning=False,
        logical_evaluation_key=component_id,
    )
    dprime_input = component_dprime_input_packet(
        analyst_artifact=analyst,
        analyst_input_packet=analyst_input,
    )
    dprime = execute_multicomponent_role_call(
        run_kernel=kernel,
        role="component_dprime",
        input_packet=dprime_input,
        ask_model=lambda *_args, **_kwargs: json.dumps(
            {
                "validation_status": "supported",
                "reasons": ["The exact bounded evidence supports the claim."],
                "caveats": [],
                "nonclaims": [],
                "blockers": [],
            }
        ),
        clean_json_response=lambda value: value,
        provider="offline",
        model="fixture",
        base_url="http://offline.invalid/v1",
        api_key="",
        use_reasoning=False,
        logical_evaluation_key=component_id,
    )
    observation, content_refs, coverage = _semantic_material(
        run_kernel=kernel,
        component_ref=amendment.component_ref,
        bindable=acquisition.bindable,
        analyst_artifact=analyst,
        dprime_artifact=dprime,
        query="Northstar filing route",
    )
    admitted = execute_multicomponent_component_admission(
        run_kernel=kernel,
        component_id=component_id,
        analyst_artifact=analyst,
        dprime_artifact=dprime,
        analyst_input_packet=analyst_input,
        semantic_observation=observation,
        sanitized_content_references=content_refs,
        component_coverage_record=coverage,
    )

    assert admitted["admission_status"] == "admitted"
    assert admitted["accepted_contract_version"] == (
        kernel.state.current_answer_contract["accepted_contract_version"]
    )
    assert admitted["accepted_contract_digest"] == (
        kernel.state.current_answer_contract["accepted_contract_digest"]
    )
    assert admitted["analyst_finding_ref"]["role"] == "component_analyst"
    assert admitted["dprime_validation_ref"]["role"] == "component_dprime"
    assert len(kernel.state.semantic_observation_admission_history) == 1
    assert len(kernel.state.component_coverage_history) == 1
