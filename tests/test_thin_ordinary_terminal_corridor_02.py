"""Offline Phase-2 proof for the thin ordinary terminal corridor.

Test path/node id: this module's terminal owner-consumption proofs
Proof class: OFFLINE_COMPONENT_PROOF
Validation bucket: phase_focus
Surface guarded: direct Component Analyst/Cross -> Sufficiency -> FAP -> Author
High-custody or closed-this-phase surface: SearchOS acquisition, scheduler,
Graph V1, D-prime, Scrutineer, Specialist, and PRODUCT routing remain closed
Runtime/product path guarded: experimental branch-only terminal corridor
Expected cost: bounded in-memory fake transports, under 15s
Promotion posture: exploratory proof only; not a fast_pr sentinel
Demotion/retirement condition: replace only after separately authorized PRODUCT
comparison and convergence.
Why not fast_pr: this is a phase-local architecture experiment.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

import core.component_work_graph_v1 as graph_runtime
import core.multicomponent_graph_scheduling as scheduler_runtime
import core.ordinary_direct_semantic_corridor as direct_runtime
import core.ordinary_multicomponent_synthesis_runtime as ordinary_runtime
from core.component_analyst_evidence_set import (
    build_component_analyst_evidence_set,
)
from core.direct_semantic_sufficiency_consumption_runtime import (
    build_direct_semantic_sufficiency_consumption,
    direct_semantic_provenance_envelope_digest,
    direct_semantic_sufficiency_consumption_digest,
)
from core.evidence_ledger import (
    CandidateCustodyKind,
    CandidateCustodyRecord,
    CandidateDisposition,
    EvidenceCandidate,
    SourceRequirementRecord,
    SourceRequirementStatus,
)
from core.multicomponent_component_admission import (
    MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
    component_analyst_input_packet,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYSTEM_PROMPTS,
    SafeMulticomponentWorkerResult,
    safe_packet_digest,
)
from core.ordinary_direct_semantic_corridor import (
    OrdinaryDirectSemanticCorridorError,
    execute_ordinary_direct_semantic_corridor_with_context,
    execute_ordinary_direct_terminal_corridor_from_result,
)
from core.run_authority_sufficiency_runtime import (
    execute_sufficiency_judgment_handoff_from_scope,
)
from core.run_kernel import (
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
)
from core.specialist_graph_runtime import (
    SPECIALIST_NEED_SCHEMA_VERSION,
    validate_specialist_need_proposal_candidate,
)
from core.strict_one_shot_model_transport import (
    wrap_text_callable_as_strict_one_shot_transport,
)

QUERY = "Relate the exact bounded offline components."
DIRECTIVE = "Relate the exact components."
SELF_AUDIT = (
    "The relationship stays within the exact current component cases and "
    "retains their caveats, nonclaims, and blockers."
)


class _QueryAuthority:
    def to_trace_fragment(self) -> dict[str, Any]:
        return {"query_plan": {"plan_id": "offline-terminal-corridor"}}


def _forbid_old_path(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the thin terminal corridor invoked forbidden old-path work")

    for owner, name in (
        (RunKernel, "initialize_multicomponent_graph_scheduler"),
        (RunKernel, "grant_next_multicomponent_work_lease"),
        (RunKernel, "grant_next_multicomponent_work_batch"),
        (RunKernel, "commit_multicomponent_batch_dispatch"),
        (RunKernel, "prepare_multicomponent_role_dispatch"),
        (RunKernel, "authorize_multicomponent_graph_reduction"),
        (scheduler_runtime, "initialize_scheduler_v2_state"),
        (scheduler_runtime, "initialize_scheduler_v3_state"),
        (scheduler_runtime, "grant_next_lease"),
        (scheduler_runtime, "grant_next_batch"),
        (scheduler_runtime, "dispatch_lease"),
        (scheduler_runtime, "dispatch_batch"),
        (graph_runtime, "component_work_graph_v1_from_cross_component_artifact"),
        (graph_runtime, "component_work_graph_v1_from_single_component_admission"),
        (
            graph_runtime,
            "component_work_graph_v1_resynthesis_from_cross_component_artifact",
        ),
        (graph_runtime, "reduce_component_work_graph_v1"),
        (graph_runtime, "synthesis_dprime_input_packet"),
        (graph_runtime, "scrutineer_input_packet"),
        (ordinary_runtime, "_execute_multicomponent_role_transport"),
        (ordinary_runtime, "_execute_run_kernel_selected_batch"),
    ):
        monkeypatch.setattr(owner, name, forbidden)


def _component_ref(index: int) -> dict[str, Any]:
    return {
        "component_id": f"component-{index}",
        "component_revision": "1",
        "component_digest": f"component-{index}-digest",
        "user_facing_label": f"Component {chr(64 + index)}",
        "user_facing_question": f"What does material {chr(64 + index)} establish?",
        "component_purpose": "bounded offline terminal proof",
        "requirement_posture": "required",
        "allowed_support_kinds": ["direct"],
        "mandatory_caveats": [],
        "prohibited_upgrades": [],
    }


def _evidence_set(component_index: int, member_count: int = 1) -> dict[str, Any]:
    members = []
    for member_index in range(1, member_count + 1):
        candidate_id = f"evidence:{component_index}:{member_index}"
        source_id = f"source-{component_index}-{member_index}"
        url = f"https://offline.example/{component_index}/{member_index}"
        text = f"Bounded material {chr(64 + component_index)}{chr(96 + member_index)} supports its exact component."
        passage = {
            "candidate_id": candidate_id,
            "source_id": source_id,
            "title": f"Offline source {component_index}-{member_index}",
            "url": url,
            "text": text,
            "source_class": "official_docs",
            "source_tier": "primary",
            "currentness_signal": "current",
            "fact_disposition": "accepted",
            "readable_status": "readable",
        }
        members.append(
            {
                "evidence_ref_id": candidate_id,
                "passage": passage,
                "candidate_record": {key: deepcopy(value) for key, value in passage.items() if key != "text"},
            }
        )
    return build_component_analyst_evidence_set(members)


def _fixture(
    *,
    component_count: int,
) -> tuple[RunKernel, dict[str, dict[str, Any]], dict[str, Any]]:
    kernel = RunKernel.start(
        run_id=f"offline-terminal-run-{component_count}",
        request_id=f"offline-terminal-request-{component_count}",
    )
    components = [_component_ref(index) for index in range(1, component_count + 1)]
    contract = {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": kernel.state.run_id,
        "request_id": kernel.state.request_id,
        "accepted_contract_version": "v1",
        "accepted_contract_digest": f"offline-terminal-contract-{component_count}",
        "parent_question_meaning_record_id": "qmr:offline-terminal",
        "parent_question_meaning_record_digest": "qmr:offline-terminal-digest",
        "accepted_answer_component_count": component_count,
        "accepted_answer_component_refs": components,
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            **({"requested_synthesis_directive": DIRECTIVE} if component_count >= 2 else {}),
        },
    }
    kernel.state.initial_answer_contract = deepcopy(contract)
    kernel.state.initial_answer_contract_projection = {"accepted": True}
    kernel.state.run_contract_projection = {
        "contract_id": f"run-contract:offline-terminal-{component_count}",
        "schema_version": "test_run_contract_offline_terminal_v1",
        "selected_template_ids": [],
        "source_requirements": [],
        "source_requirement_summary": [],
        "inference_policy": {},
        "conflict_policy": {},
        "numeric_policy": {},
        "final_posture_policy": {"partial_allowed_if": []},
    }
    evidence_sets = {
        component["component_id"]: _evidence_set(
            index,
            member_count=2 if index == 2 else 1,
        )
        for index, component in enumerate(components, start=1)
    }
    for evidence_set in evidence_sets.values():
        for member in evidence_set["members"]:
            candidate = member["candidate_record"]
            candidate_id = member["code_binding"]["evidence_ref_id"]
            kernel.state.evidence_ledger.candidates[candidate_id] = EvidenceCandidate(
                candidate_id=candidate_id,
                url=candidate.get("url"),
                title=candidate.get("title"),
                source_class=candidate.get("source_class"),
                source_tier=candidate.get("source_tier"),
                currentness_signal=candidate.get("currentness_signal"),
                readable_status="readable",
                fact_disposition=CandidateDisposition.ACCEPTED,
                final_evidence_eligible=True,
            )
            kernel.state.evidence_ledger.custody_records.append(
                CandidateCustodyRecord(
                    candidate_id=candidate_id,
                    record_kind=CandidateCustodyKind.FACT,
                    disposition=CandidateDisposition.ACCEPTED,
                    reason="bounded offline terminal-corridor fixture custody",
                    source="offline_terminal_corridor_fixture",
                )
            )
    kernel.state.evidence_ledger.requirements["offline-terminal-requirement"] = SourceRequirementRecord(
        requirement_id="offline-terminal-requirement",
        requirement_kind="offline_terminal_fixture",
        status=SourceRequirementStatus.SATISFIED,
        reason="bounded offline terminal fixture",
    )
    return kernel, evidence_sets, contract


def _semantic_transport(
    *,
    cross_proposals: list[dict[str, Any]],
    captured: list[dict[str, Any]],
    component_postures: Mapping[str, str] | None = None,
    component_two_first_only: bool = False,
    specialist_need_target: tuple[str, str] | None = None,
) -> Any:
    postures = dict(component_postures or {})

    def ask_model(prompt: str, system_prompt: str, **_kwargs: Any) -> str:
        packet = json.loads(prompt)
        captured.append({"system_prompt": system_prompt, "packet": packet})
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            component_id = str(packet["component_ref"]["component_id"])
            posture = postures.get(component_id, "supported")
            if posture != "supported":
                return json.dumps(
                    {
                        "case_posture": posture,
                        "evidence_analysis": ("The supplied current material does not establish support."),
                        "self_audit": "No admitted component claim is asserted.",
                        "caveats": [],
                        "nonclaims": ["No supported component claim is asserted."],
                        "contradictions": [],
                        "blockers": [],
                    }
                )
            aliases = [str(item["local_evidence_alias"]) for item in packet["component_evidence_set"]["members"]]
            if component_id == "component-2" and component_two_first_only:
                aliases = aliases[:1]
            output = {
                "case_posture": "supported",
                "claim_text": "The exact supplied material supports its component.",
                "evidence_analysis": "The selected bounded material supports the claim.",
                "self_audit": "The component claim stays within selected evidence.",
                "supporting_evidence_aliases": aliases,
                "caveats": [],
                "nonclaims": [],
                "contradictions": [],
                "blockers": [],
            }
            if specialist_need_target == ("component", component_id):
                output["specialist_need_proposal"] = _lawful_specialist_need(
                    target_kind="component",
                    target_key=component_id,
                )
            return json.dumps(output)
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            output = {
                "synthesis_proposals": cross_proposals,
                "self_audit": SELF_AUDIT,
            }
            if specialist_need_target and specialist_need_target[0] == "synthesis":
                output["specialist_need_proposal"] = _lawful_specialist_need(
                    target_kind="synthesis",
                    target_key=specialist_need_target[1],
                )
            return json.dumps(output)
        raise AssertionError(f"unexpected semantic role prompt: {system_prompt}")

    return wrap_text_callable_as_strict_one_shot_transport(
        ask_model,
        canonical_provider="OpenAI",
        model="offline-terminal-corridor",
    )


def _runtime_scope(query: str = QUERY) -> dict[str, Any]:
    return {
        "query": query,
        "intent": "research",
        "report_type": "general",
        "query_type": "general",
        "core_topic": "bounded component relationship",
        "primary_entity": "offline components",
        "anchor_packet_telemetry": {},
        "query_authority": _QueryAuthority(),
        "scrutineer_flags": [],
        "corpus_weak": False,
        "weak_corpus_recovery_skip_reason": None,
        "corpus_state": "healthy",
        "synth_was_insufficient": False,
        "_pre_gate_failure_card_show": False,
        "_pre_gate_failure_card_reason": None,
        "iterations_run": 1,
        "max_iterations": 2,
        "_run_controller_mirror": SimpleNamespace(state=SimpleNamespace(active_source_class_recovery_attempt_count=0)),
        "author_notes": "",
        "author_prompt": "BASE OFFLINE AUTHOR PROMPT",
        "analyst_effort": "medium",
        "_efp_author": False,
        "_relevance_low": False,
        "strategy": "Balanced",
        "fast_provider": "offline",
        "fast_model": "offline-author",
        "smart_provider": "offline",
        "smart_model": "offline-author",
        "economist_safety_telemetry": {},
    }


def _direct_result(
    *,
    kernel: RunKernel,
    evidence_sets: Mapping[str, Mapping[str, Any]],
    cross_proposals: list[dict[str, Any]],
    captured: list[dict[str, Any]],
    component_postures: Mapping[str, str] | None = None,
    component_two_first_only: bool = False,
    specialist_need_target: tuple[str, str] | None = None,
) -> Any:
    return execute_ordinary_direct_semantic_corridor_with_context(
        run_kernel=kernel,
        component_evidence_sets=evidence_sets,
        query=QUERY,
        requested_synthesis_directive=(
            DIRECTIVE if len(kernel.state.initial_answer_contract["accepted_answer_component_refs"]) >= 2 else ""
        ),
        requested_mode="Balanced",
        strict_one_shot_transport=_semantic_transport(
            cross_proposals=cross_proposals,
            captured=captured,
            component_postures=component_postures,
            component_two_first_only=component_two_first_only,
            specialist_need_target=specialist_need_target,
        ),
        clean_json_response=lambda value: value,
        provider="OpenAI",
        model="offline-terminal-corridor",
        use_reasoning=False,
    )


def _terminal(
    *,
    kernel: RunKernel,
    direct_result: Any,
    author_calls: list[dict[str, Any]],
) -> Any:
    def author_model(prompt: str, system_prompt: str, **kwargs: Any) -> str:
        author_calls.append({"prompt": prompt, "system_prompt": system_prompt, "kwargs": kwargs})
        return "Offline final answer grounded in the packet-authorized evidence."

    return execute_ordinary_direct_terminal_corridor_from_result(
        run_kernel=kernel,
        direct_result=direct_result,
        runtime_scope=_runtime_scope(),
        default_system={"author": "OFFLINE AUTHOR SYSTEM"},
        author_ask_model=author_model,
        author_system_prompt_registry={"author": "OFFLINE AUTHOR SYSTEM"},
    )


def _one_relationship(component_ids: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "synthesis_key": "bounded_relation",
            "claim_text": "The exact component cases form the requested relation.",
            "relationship_type": "bounded_comparison",
            "component_inputs": component_ids,
            "synthesis_inputs": [],
            "caveats": ["Only the supplied current cases are related."],
            "nonclaims": ["This does not exceed the supplied component cases."],
            "blockers": [],
        }
    ]


def _lawful_specialist_need(
    *,
    target_kind: str,
    target_key: str,
) -> dict[str, Any]:
    proposal = {
        "schema_version": SPECIALIST_NEED_SCHEMA_VERSION,
        "local_need_id": "direct-signal-need",
        "capability_requirement": "bounded_test_capability",
        "candidate_capability_hint": "specialist.test_signal",
        "bounded_question": "Apply one bounded Specialist operation.",
        "target": {
            "target_kind": target_kind,
            "target_key": target_key,
        },
        "posture": "required",
        "input_schema_ref": "generic.specialist.input.v1",
        "expected_output_schema_ref": "generic.specialist.output.v1",
        "input_artifact_refs": [],
        "assumptions": [],
        "caveats": [],
        "nonclaims": ["The proposal is not Specialist authority."],
        "advisory_budget_posture": "one bounded unit",
        "recursion_depth": 0,
        "specialist_parent_ref": None,
    }
    assert validate_specialist_need_proposal_candidate(proposal) == proposal
    return proposal


def _capture_safe_worker_results(
    monkeypatch: pytest.MonkeyPatch,
) -> list[SafeMulticomponentWorkerResult]:
    observed: list[SafeMulticomponentWorkerResult] = []
    original = direct_runtime._stop_on_unserviceable_direct_specialist_need

    def capture(result: SafeMulticomponentWorkerResult) -> None:
        observed.append(result)
        original(result)

    monkeypatch.setattr(
        direct_runtime,
        "_stop_on_unserviceable_direct_specialist_need",
        capture,
    )
    return observed


def _assert_old_path_absent(kernel: RunKernel) -> None:
    assert "multicomponent_graph_scheduler" not in kernel.state.projections
    assert "multicomponent_component_work_graph_v1" not in kernel.state.projections
    assert not kernel.state.multicomponent_scheduler_context
    roles = [str(action.inputs.get("role") or "") for action in kernel.state.issued_actions.values()]
    assert "component_dprime" not in roles
    assert "synthesis_dprime" not in roles
    assert "scrutineer" not in roles
    assert "specialist" not in roles
    assert all("lease" not in action.action_type.value for action in kernel.state.issued_actions.values())
    assert all("batch" not in action.action_type.value for action in kernel.state.issued_actions.values())


def _assert_author_mechanical_finalization(
    kernel: RunKernel,
    terminal: Any,
) -> None:
    assert kernel.state.final_answer_outcome == kernel.state.projections["author_execution"]
    assert kernel.state.final_answer_outcome["owner"] == "RunKernel.AuthorObservation"
    assert kernel.state.final_answer_outcome["canonical_state"] is True
    assert kernel.state.final_answer_outcome["packet_id"] == (terminal.final_answer_packet_handoff.packet.packet_id)
    assert kernel.state.final_answer_outcome["report_hash"]
    assert kernel.state.final_answer_outcome["final_text_included"] is False


def test_n1_support_reaches_existing_sufficiency_fap_and_author(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, _contract = _fixture(component_count=1)
    captured: list[dict[str, Any]] = []
    author_calls: list[dict[str, Any]] = []
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=[],
        captured=captured,
    )

    terminal = _terminal(
        kernel=kernel,
        direct_result=direct,
        author_calls=author_calls,
    )

    assert terminal.direct_result.cross_artifact is None
    assert terminal.sufficiency_handoff.projection["final_answer_allowed"] is True
    assert terminal.final_answer_packet_handoff.author_input_blocked is False
    assert terminal.author_handoff is not None
    assert terminal.author_handoff.report.startswith("Offline final answer")
    assert len(author_calls) == 1
    assert len(terminal.final_answer_packet_handoff.packet.citation_eligible) == 1
    _assert_author_mechanical_finalization(kernel, terminal)
    _assert_old_path_absent(kernel)


def test_n2_multiple_cross_relationships_reach_existing_fap_and_author_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, _contract = _fixture(component_count=2)
    captured: list[dict[str, Any]] = []
    author_calls: list[dict[str, Any]] = []
    proposals = [
        *_one_relationship(["component-1", "component-2"]),
        {
            "synthesis_key": "bounded_consequence",
            "claim_text": "The first bounded relation retains 2 exact inputs.",
            "relationship_type": "bounded_dependency",
            "component_inputs": [],
            "synthesis_inputs": ["bounded_relation"],
            "caveats": [],
            "nonclaims": ["No further relationship is asserted."],
            "blockers": [],
        },
    ]
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=proposals,
        captured=captured,
        component_two_first_only=True,
    )

    terminal = _terminal(
        kernel=kernel,
        direct_result=direct,
        author_calls=author_calls,
    )

    assert [item["synthesis_key"] for item in terminal.direct_semantic_consumption["cross_relationship_entries"]] == [
        "bounded_relation",
        "bounded_consequence",
    ]
    packet = terminal.final_answer_packet_handoff.packet
    assert [item["synthesis_inputs"] for item in packet.cross_relationship_entries] == [
        [],
        ["bounded_relation"],
    ]
    assert terminal.sufficiency_handoff.projection["final_answer_allowed"] is True
    assert terminal.author_handoff is not None
    assert len(author_calls) == 1
    assert "The exact component cases form the requested relation." in author_calls[0]["prompt"]
    assert [item["candidate_id"] for item in terminal.selected_evidence_passages] == [
        "evidence:1:1",
        "evidence:2:1",
    ]
    assert {item.source_id for item in packet.citation_eligible} == {
        "source-1-1",
        "source-2-1",
    }
    quantitative = packet.quantitative_fap_authority_preflight()["diagnostic"]
    assert quantitative["status"] == "ready"
    assert quantitative["required_numeric_claim_count"] == 1
    assert quantitative["authorized_numeric_claim_count"] == 0
    assert [item["system_prompt"] for item in captured].count(ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]) == 1
    _assert_author_mechanical_finalization(kernel, terminal)
    _assert_old_path_absent(kernel)


def test_n3_one_cross_call_receives_all_components_and_terminal_path_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, _contract = _fixture(component_count=3)
    captured: list[dict[str, Any]] = []
    author_calls: list[dict[str, Any]] = []
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=_one_relationship(["component-1", "component-2", "component-3"]),
        captured=captured,
    )

    terminal = _terminal(
        kernel=kernel,
        direct_result=direct,
        author_calls=author_calls,
    )

    cross_packets = [
        item["packet"]
        for item in captured
        if item["system_prompt"] == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
    ]
    assert len(cross_packets) == 1
    assert [item["component_id"] for item in cross_packets[0]["component_nodes"]] == [
        "component-1",
        "component-2",
        "component-3",
    ]
    assert len(terminal.direct_result.component_admission_refs) == 3
    assert (
        list(terminal.direct_result.component_admission_refs)
        == kernel.state.projections[MULTICOMPONENT_COMPONENT_ADMISSION_STAGE]["component_admission_refs"]
    )
    assert [item["component_id"] for item in terminal.direct_result.component_admission_refs] == [
        "component-1",
        "component-2",
        "component-3",
    ]
    assert terminal.sufficiency_handoff.projection["final_answer_allowed"] is True
    assert terminal.author_handoff is not None
    assert len(author_calls) == 1
    _assert_author_mechanical_finalization(kernel, terminal)
    _assert_old_path_absent(kernel)


def test_component_specialist_need_stops_before_component_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    observed = _capture_safe_worker_results(monkeypatch)
    kernel, evidence_sets, _contract = _fixture(component_count=2)
    captured: list[dict[str, Any]] = []

    with pytest.raises(
        OrdinaryDirectSemanticCorridorError,
        match="direct corridor Specialist execution is not licensed/implemented",
    ):
        _direct_result(
            kernel=kernel,
            evidence_sets=evidence_sets,
            cross_proposals=_one_relationship(["component-1", "component-2"]),
            captured=captured,
            specialist_need_target=("component", "component-2"),
        )

    signaled = [
        result for result in observed if result.specialist_need_proposal_present
    ]
    assert len(signaled) == 1
    assert isinstance(signaled[0], SafeMulticomponentWorkerResult)
    assert signaled[0].role == ROLE_COMPONENT_ANALYST
    assert signaled[0].logical_evaluation_key == "component-2"
    assert signaled[0].specialist_need_proposal_candidate == (
        _lawful_specialist_need(
            target_kind="component",
            target_key="component-2",
        )
    )
    assert signaled[0].raw_prompt_retained is False
    assert signaled[0].raw_model_response_retained is False
    assert signaled[0].raw_provider_payload_retained is False

    admission_projection = kernel.state.projections[
        MULTICOMPONENT_COMPONENT_ADMISSION_STAGE
    ]
    assert [
        item["component_id"]
        for item in admission_projection["component_admission_refs"]
    ] == ["component-1"]
    failed_role_projection = kernel.state.projections[
        f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:component-2"
    ]
    assert failed_role_projection["schema_version"] == (
        "multicomponent_semantic_role_failure_v1"
    )
    assert failed_role_projection["semantic_artifact_admitted"] is False
    assert failed_role_projection["raw_model_response_retained"] is False
    assert failed_role_projection["raw_provider_payload_retained"] is False
    assert "semantic_output" not in failed_role_projection
    assert "specialist_need_proposal" not in failed_role_projection
    assert len(kernel.state.semantic_observation_admission_history) == 1
    assert kernel.state.semantic_observation_admission_history[0][
        "answer_component_id"
    ] == "component-1"
    assert len(kernel.state.component_coverage_history) == 1
    assert kernel.state.component_coverage_history[0]["answer_component_id"] == (
        "component-1"
    )
    assert [item["system_prompt"] for item in captured].count(
        ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
    ) == 0
    assert not kernel.state.sufficiency_judgment_projection
    assert not kernel.state.final_answer_packet
    assert not kernel.state.author_observation
    _assert_old_path_absent(kernel)


def test_cross_specialist_need_stops_before_direct_sufficiency_consumption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    observed = _capture_safe_worker_results(monkeypatch)
    kernel, evidence_sets, _contract = _fixture(component_count=2)
    captured: list[dict[str, Any]] = []

    with pytest.raises(
        OrdinaryDirectSemanticCorridorError,
        match="direct corridor Specialist execution is not licensed/implemented",
    ):
        _direct_result(
            kernel=kernel,
            evidence_sets=evidence_sets,
            cross_proposals=_one_relationship(["component-1", "component-2"]),
            captured=captured,
            specialist_need_target=("synthesis", "bounded_relation"),
        )

    signaled = [
        result for result in observed if result.specialist_need_proposal_present
    ]
    assert len(signaled) == 1
    assert isinstance(signaled[0], SafeMulticomponentWorkerResult)
    assert signaled[0].role == ROLE_CROSS_COMPONENT_ANALYST
    assert signaled[0].specialist_need_proposal_candidate == (
        _lawful_specialist_need(
            target_kind="synthesis",
            target_key="bounded_relation",
        )
    )
    assert signaled[0].normalized_semantic_output == {
        "synthesis_proposals": _one_relationship(
            ["component-1", "component-2"]
        ),
        "self_audit": SELF_AUDIT,
    }
    assert signaled[0].raw_prompt_retained is False
    assert signaled[0].raw_model_response_retained is False
    assert signaled[0].raw_provider_payload_retained is False

    admissions = kernel.state.projections[
        MULTICOMPONENT_COMPONENT_ADMISSION_STAGE
    ]["component_admission_refs"]
    assert [item["component_id"] for item in admissions] == [
        "component-1",
        "component-2",
    ]
    assert all(item["current"] is True for item in admissions)
    assert all(item["stale"] is False for item in admissions)
    failed_role_projection = kernel.state.projections[
        f"multicomponent_role:{ROLE_CROSS_COMPONENT_ANALYST}:"
        "thin-ordinary-direct-cross"
    ]
    assert failed_role_projection["schema_version"] == (
        "multicomponent_semantic_role_failure_v1"
    )
    assert failed_role_projection["semantic_artifact_admitted"] is False
    assert failed_role_projection["raw_model_response_retained"] is False
    assert failed_role_projection["raw_provider_payload_retained"] is False
    assert "semantic_output" not in failed_role_projection
    assert "specialist_need_proposal" not in failed_role_projection
    assert [item["system_prompt"] for item in captured].count(
        ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
    ) == 1
    assert not kernel.state.sufficiency_judgment_projection
    assert not kernel.state.final_answer_packet
    assert not kernel.state.author_observation
    _assert_old_path_absent(kernel)


def test_lawful_non_support_reaches_sufficiency_and_blocks_before_author(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, _contract = _fixture(component_count=2)
    captured: list[dict[str, Any]] = []
    author_calls: list[dict[str, Any]] = []
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=[],
        captured=captured,
        component_postures={"component-2": "unsupported"},
    )
    canonical_refs = deepcopy(
        kernel.state.projections[MULTICOMPONENT_COMPONENT_ADMISSION_STAGE]["component_admission_refs"]
    )
    canonical_aggregate = deepcopy(kernel.state.projections[MULTICOMPONENT_COMPONENT_ADMISSION_STAGE])
    assert canonical_aggregate["component_count"] == 2
    assert canonical_aggregate["admitted_component_count"] == 1
    assert canonical_aggregate["blocked_component_count"] == 1
    assert canonical_aggregate["projection_digest"] == safe_packet_digest(
        {key: deepcopy(value) for key, value in canonical_aggregate.items() if key != "projection_digest"}
    )

    terminal = _terminal(
        kernel=kernel,
        direct_result=direct,
        author_calls=author_calls,
    )

    assert list(terminal.direct_result.component_admission_refs) == canonical_refs
    unsupported = terminal.direct_result.component_admission_refs[1]
    assert unsupported["admission_status"] == "unsupported"
    assert unsupported["current"] is True and unsupported["stale"] is False
    assert unsupported["component_analyst_case_ref"]
    assert not unsupported["admitted_claim_ref"]
    assert not unsupported["semantic_observation_ref"]
    assert not unsupported["component_coverage_ref"]
    sufficiency = terminal.sufficiency_handoff.projection
    assert sufficiency["decision"] == "insufficient_evidence"
    assert sufficiency["final_answer_allowed"] is False
    assert sufficiency["direct_semantic_consumption"]["component_count"] == 2
    assert sufficiency["direct_semantic_consumption"]["component_admission_refs"] == canonical_refs
    assert terminal.final_answer_packet_handoff.author_input_blocked is True
    assert terminal.author_handoff is None
    assert not author_calls
    assert [item["system_prompt"] for item in captured].count(ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]) == 0
    _assert_old_path_absent(kernel)


def test_cross_blocker_is_preserved_in_blocked_fap_without_author(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, _contract = _fixture(component_count=2)
    captured: list[dict[str, Any]] = []
    proposals = _one_relationship(["component-1", "component-2"])
    proposals[0]["blockers"] = ["The supplied cases leave the relation blocked."]
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=proposals,
        captured=captured,
    )

    terminal = _terminal(kernel=kernel, direct_result=direct, author_calls=[])

    assert terminal.sufficiency_handoff.projection["decision"] == "block_finalization"
    assert terminal.final_answer_packet_handoff.author_input_blocked is True
    assert terminal.author_handoff is None
    assert terminal.final_answer_packet_handoff.packet.cross_relationship_entries[0]["blockers"] == [
        "The supplied cases leave the relation blocked."
    ]
    _assert_old_path_absent(kernel)


def test_zero_cross_proposals_remain_lawful_and_sufficiency_decides_no_author(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, _contract = _fixture(component_count=2)
    captured: list[dict[str, Any]] = []
    author_calls: list[dict[str, Any]] = []
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=[],
        captured=captured,
    )

    terminal = _terminal(
        kernel=kernel,
        direct_result=direct,
        author_calls=author_calls,
    )

    assert terminal.direct_result.cross_artifact is not None
    assert terminal.direct_semantic_consumption["cross_relationship_entries"] == []
    assert terminal.sufficiency_handoff.projection["decision"] == "insufficient_evidence"
    assert terminal.final_answer_packet_handoff.author_input_blocked is True
    assert terminal.author_handoff is None
    assert not author_calls
    assert "multicomponent_component_work_graph_v1" not in kernel.state.projections
    _assert_old_path_absent(kernel)


def test_terminal_reproof_rejects_corrupted_current_admission_before_sufficiency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, _contract = _fixture(component_count=2)
    captured: list[dict[str, Any]] = []
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=_one_relationship(["component-1", "component-2"]),
        captured=captured,
    )
    projection = kernel.state.projections[MULTICOMPONENT_COMPONENT_ADMISSION_STAGE]
    projection["component_admission_refs"][0]["current"] = False
    projection["projection_digest"] = safe_packet_digest(
        {key: deepcopy(value) for key, value in projection.items() if key != "projection_digest"}
    )

    with pytest.raises(
        OrdinaryDirectSemanticCorridorError,
        match="stale or incomplete",
    ):
        _terminal(kernel=kernel, direct_result=direct, author_calls=[])

    assert not kernel.state.sufficiency_judgment_projection
    assert not kernel.state.final_answer_packet
    _assert_old_path_absent(kernel)


def test_public_sufficiency_handoff_rejects_self_digested_forged_direct_packet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, contract = _fixture(component_count=2)
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=_one_relationship(["component-1", "component-2"]),
        captured=[],
    )
    consumption = build_direct_semantic_sufficiency_consumption(
        accepted_contract=contract,
        component_admission_refs=direct.component_admission_refs,
        cross_component_artifact=direct.cross_artifact,
        requested_synthesis_directive=DIRECTIVE,
    )
    forged = deepcopy(consumption)
    forged["direct_semantic_provenance"]["accepted_component_refs"][0]["user_facing_label"] = "Forged component label"
    forged["direct_component_entries"][0]["accepted_component_ref"]["user_facing_label"] = "Forged component label"
    forged["direct_component_entries"][0]["component_label"] = "Forged component label"
    forged["direct_semantic_provenance"]["provenance_digest"] = direct_semantic_provenance_envelope_digest(
        forged["direct_semantic_provenance"]
    )
    forged["consumption_digest"] = direct_semantic_sufficiency_consumption_digest(forged)
    scope = _runtime_scope()
    scope.update(
        {
            "evidence_ledger_projection": (kernel.state.evidence_ledger.to_projection().to_dict()),
            "run_contract_projection": deepcopy(kernel.state.run_contract_projection),
            "answer_contract_projection": deepcopy(contract),
            "final_top_evidence": [],
            "author_evidence": [],
            "unique_source_urls": {},
            "direct_semantic_consumption": forged,
        }
    )

    with pytest.raises(ValueError, match="exact current owner-derived packet"):
        execute_sufficiency_judgment_handoff_from_scope(
            kernel,
            scope,
            smart_model_enabled=False,
        )

    assert not kernel.state.sufficiency_judgment_projection
    _assert_old_path_absent(kernel)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("schema_version", "multicomponent_component_admission_projection_v0"),
        ("trace_only", True),
    ),
)
def test_public_sufficiency_handoff_rejects_forged_admission_projection_surface(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: Any,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, contract = _fixture(component_count=2)
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=_one_relationship(["component-1", "component-2"]),
        captured=[],
    )
    consumption = build_direct_semantic_sufficiency_consumption(
        accepted_contract=contract,
        component_admission_refs=direct.component_admission_refs,
        cross_component_artifact=direct.cross_artifact,
        requested_synthesis_directive=DIRECTIVE,
    )
    projection = deepcopy(kernel.state.projections[MULTICOMPONENT_COMPONENT_ADMISSION_STAGE])
    projection[field] = value
    projection["projection_digest"] = safe_packet_digest(
        {key: item for key, item in projection.items() if key != "projection_digest"}
    )
    kernel.state.projections[MULTICOMPONENT_COMPONENT_ADMISSION_STAGE] = projection
    scope = _runtime_scope()
    scope.update(
        {
            "evidence_ledger_projection": (kernel.state.evidence_ledger.to_projection().to_dict()),
            "run_contract_projection": deepcopy(kernel.state.run_contract_projection),
            "answer_contract_projection": deepcopy(contract),
            "final_top_evidence": [],
            "author_evidence": [],
            "unique_source_urls": {},
            "direct_semantic_consumption": consumption,
        }
    )

    with pytest.raises(ValueError, match="current component admission authority"):
        execute_sufficiency_judgment_handoff_from_scope(
            kernel,
            scope,
            smart_model_enabled=False,
        )

    assert not kernel.state.sufficiency_judgment_projection
    _assert_old_path_absent(kernel)


def test_terminal_reproof_rejects_self_consistent_mutated_analyst_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, contract = _fixture(component_count=2)
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=_one_relationship(["component-1", "component-2"]),
        captured=[],
    )
    mutated_evidence_sets = deepcopy(dict(direct.component_evidence_sets))
    current_member = deepcopy(mutated_evidence_sets["component-1"]["members"][0])
    current_member["passage"]["text"] = "Self-consistent but unauthorized text."
    mutated_members = [
        {
            "evidence_ref_id": current_member["code_binding"]["evidence_ref_id"],
            "passage": current_member["passage"],
            "candidate_record": current_member["candidate_record"],
        }
    ]
    mutated_evidence_sets["component-1"] = build_component_analyst_evidence_set(mutated_members)
    mutated_packets = deepcopy(dict(direct.component_analyst_input_packets))
    mutated_packets["component-1"] = component_analyst_input_packet(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        accepted_contract=contract,
        component_ref=contract["accepted_answer_component_refs"][0],
        component_evidence_set=mutated_evidence_sets["component-1"],
    )
    forged = replace(
        direct,
        component_evidence_sets=mutated_evidence_sets,
        component_analyst_input_packets=mutated_packets,
    )

    with pytest.raises(
        OrdinaryDirectSemanticCorridorError,
        match="Component Analyst input is not exact current input",
    ):
        _terminal(kernel=kernel, direct_result=forged, author_calls=[])

    assert not kernel.state.sufficiency_judgment_projection
    assert not kernel.state.final_answer_packet
    _assert_old_path_absent(kernel)


def test_sufficiency_reduction_cannot_drop_authorized_direct_consumption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_old_path(monkeypatch)
    kernel, evidence_sets, contract = _fixture(component_count=2)
    direct = _direct_result(
        kernel=kernel,
        evidence_sets=evidence_sets,
        cross_proposals=_one_relationship(["component-1", "component-2"]),
        captured=[],
    )
    consumption = build_direct_semantic_sufficiency_consumption(
        accepted_contract=contract,
        component_admission_refs=direct.component_admission_refs,
        cross_component_artifact=direct.cross_artifact,
        requested_synthesis_directive=DIRECTIVE,
    )
    original_reduce = kernel.reduce

    def reduce_without_direct_consumption(observation: Observation) -> Any:
        if observation.observation_type is ObservationType.SUFFICIENCY_JUDGMENT_DECIDED:
            payload = deepcopy(dict(observation.payload))
            judgment = deepcopy(dict(payload["judgment_projection"]))
            judgment.pop("direct_semantic_consumption", None)
            payload["judgment_projection"] = judgment
            action = kernel.state.issued_actions[observation.action_id]
            observation = Observation.from_action(
                action,
                observation_type=observation.observation_type,
                status=observation.status,
                payload=payload,
            )
        return original_reduce(observation)

    monkeypatch.setattr(kernel, "reduce", reduce_without_direct_consumption)
    scope = _runtime_scope()
    scope.update(
        {
            "evidence_ledger_projection": (kernel.state.evidence_ledger.to_projection().to_dict()),
            "run_contract_projection": deepcopy(kernel.state.run_contract_projection),
            "answer_contract_projection": deepcopy(contract),
            "final_top_evidence": [],
            "author_evidence": [],
            "unique_source_urls": {},
            "direct_semantic_consumption": consumption,
        }
    )

    with pytest.raises(
        RunKernelTransitionError,
        match="lost direct semantic authority",
    ):
        execute_sufficiency_judgment_handoff_from_scope(
            kernel,
            scope,
            smart_model_enabled=False,
        )

    assert not kernel.state.sufficiency_judgment_projection
    _assert_old_path_absent(kernel)
