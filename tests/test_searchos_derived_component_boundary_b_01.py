from __future__ import annotations

from copy import deepcopy

import pytest

from core.analyst_query_resolution_proposal import (
    AnalystQueryResolutionProposalError,
    arbitrate_analyst_query_resolution_proposals,
    bind_analyst_query_resolution_proposal,
    replay_before_currentness,
)
from core.contract_amendment_record import (
    build_contract_amendment_v2_from_analyst_proposal,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    MulticomponentRoleRuntimeError,
    _normalize_semantic_output,
)
from core.searchos_existing_gap_recovery_runtime import (
    SearchOSExistingGapRecoveryError,
    admit_searchos_recovery_cycle,
    ensure_searchos_whole_run_recovery_lease,
    settle_searchos_recovery_terminal_aggregate,
    terminalize_searchos_recovery_cycle,
)
from core.searchos_iterative_judgment_runtime import (
    build_searchos_initial_state,
    build_searchos_policy_snapshot,
)
from core.semantic_contract_foundation import (
    AnswerComponentContract,
    ComponentPurpose,
    SupportKind,
    validate_answer_component_contract_set,
)


def _direct(component_id: str, *, purpose: str = "supporting_premise") -> AnswerComponentContract:
    return AnswerComponentContract(
        component_id=component_id,
        component_purpose=purpose,
        user_facing_label=component_id,
        user_facing_question=f"What establishes {component_id}?",
        source_obligation_candidate_ids=(f"obligation:{component_id}",),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
    )


def _contract_and_graph() -> tuple[dict, dict, dict[str, AnswerComponentContract]]:
    premise_a = _direct("component:A")
    premise_d = _direct("component:D")
    target_e = AnswerComponentContract(
        component_id="component:E",
        component_purpose=(ComponentPurpose.USER_FACING_ANSWER_TARGET),
        user_facing_label="component:E",
        user_facing_question="What establishes component:E?",
        source_obligation_candidate_ids=("obligation:component:E",),
        allowed_support_kinds=(
            SupportKind.DIRECT,
            SupportKind.INFERRED,
        ),
        max_inference_depth=1,
    )
    contract = {
        "canonical_state": True,
        "accepted_contract_version": "1",
        "accepted_contract_digest": "contract-digest-1",
        "parent_question_meaning_record_id": "qmr:1",
        "parent_question_meaning_record_digest": "qmr-digest-1",
        "accepted_answer_component_refs": [
            premise_a.to_dict(),
            premise_d.to_dict(),
            target_e.to_dict(),
        ],
    }
    graph = {
        "graph_id": "graph:1",
        "graph_revision": "1",
        "graph_digest": "graph-digest-1",
    }
    return (
        contract,
        graph,
        {
            "A": premise_a,
            "D": premise_d,
            "E": target_e,
        },
    )


def _artifact(
    *,
    role: str = "cross_component_analyst",
    suffix: str = "1",
    contract: dict,
    graph: dict,
) -> dict:
    return {
        "schema_version": "multicomponent_semantic_role_artifact_v1",
        "role": role,
        "artifact_id": f"artifact:{suffix}",
        "artifact_digest": f"artifact-digest:{suffix}",
        "input_packet_digest": f"input-digest:{suffix}",
        "logical_evaluation_key": f"logical:{suffix}",
        "run_id": "run:1",
        "request_id": "request:1",
        "accepted_contract_ref": deepcopy(contract),
        "graph_ref": deepcopy(graph),
    }


def _searched_candidate(target: AnswerComponentContract) -> dict:
    return {
        "classification": "searched_premise",
        "local_proposal_key": "recover_C",
        "local_target_key": "target_E",
        "normalized_premise_identity": "alder premise c",
        "answer_target_refs": [target.to_dict()],
        "parent_component_refs": [target.to_dict()],
        "current_dependency_component_refs": [],
        "premise_semantics": "Premise C required to evaluate target E.",
        "user_facing_label": "Distinctive recovered premise C label",
        "user_facing_question": ("Which distinctive filing condition establishes premise C?"),
        "acceptance_criteria": ["Distinctive criterion: verify the signed filing condition."],
        "requirement_posture": "required",
        "materiality": "material",
        "partial_answer_policy": "qualify_visible_gap",
        "mandatory_caveats": ["Distinctive mandatory caveat for premise C."],
        "source_obligation_specification": {
            "candidate_id": "obligation:component:C",
            "obligation_kind": "authoritative_direct_support",
            "strictness": "required",
            "distinctive_source_semantics": ("Signed filing-condition record only."),
        },
        "necessity_rationale": "The accepted target cannot be fulfilled without C.",
        "why_current_premises_insufficient": "A and D do not establish C.",
        "searchability_material_need_posture": "material_and_searchable",
        "recovery_generation": {
            "parent_ref": "generation:0",
            "depth": 1,
        },
        "assumptions": [],
        "caveats": ["C remains direct-source bounded."],
        "prohibited_upgrades": ["Do not infer C from search direction."],
    }


def _bind(candidate: dict, *, artifact_suffix: str = "1") -> tuple[dict, dict, dict]:
    contract, graph, components = _contract_and_graph()
    proposal = bind_analyst_query_resolution_proposal(
        role_artifact=_artifact(
            suffix=artifact_suffix,
            contract=contract,
            graph=graph,
        ),
        local_candidate=candidate,
        question_meaning_record_ref={
            "record_id": "qmr:1",
            "record_digest": "qmr-digest-1",
        },
        parent_contract_ref=contract,
        parent_graph_ref=graph,
    )
    return proposal, contract, components


def test_component_matrix_enforces_purpose_support_profile_and_cycles() -> None:
    premise = _direct("component:A")
    target = AnswerComponentContract(
        component_id="component:E",
        component_purpose=ComponentPurpose.USER_FACING_ANSWER_TARGET,
        user_facing_label="E",
        user_facing_question="What follows?",
        allowed_support_kinds=(SupportKind.INFERRED,),
        max_inference_depth=2,
        dependency_component_ids=("component:A",),
    )
    assert validate_answer_component_contract_set(
        (premise, target),
        requested_mode="Deep",
    ).ok
    fast = validate_answer_component_contract_set(
        (premise, target),
        requested_mode="Fast",
    )
    assert not fast.ok
    assert any("profile ceiling 1" in error for error in fast.errors)

    cyclic_a = AnswerComponentContract(
        component_id="component:A",
        component_purpose=ComponentPurpose.SUPPORTING_PREMISE,
        user_facing_label="A",
        user_facing_question="A?",
        allowed_support_kinds=(SupportKind.INFERRED,),
        max_inference_depth=1,
        dependency_component_ids=("component:E",),
    )
    cyclic = validate_answer_component_contract_set(
        (cyclic_a, target),
        requested_mode="Deep",
    )
    assert any("cycle" in error for error in cyclic.errors)


def test_component_digest_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="component_digest does not match"):
        AnswerComponentContract(
            component_id="component:A",
            user_facing_label="A",
            user_facing_question="A?",
            source_obligation_candidate_ids=("obligation:A",),
            component_digest="forged",
        )


def test_proposal_arbitration_collapses_equivalent_and_blocks_alternatives() -> None:
    _, _, components = _contract_and_graph()
    candidate = _searched_candidate(components["E"])
    first, _, _ = _bind(candidate, artifact_suffix="one")
    second, _, _ = _bind(candidate, artifact_suffix="two")
    collapsed = arbitrate_analyst_query_resolution_proposals([first, second])
    reversed_collapsed = arbitrate_analyst_query_resolution_proposals([second, first])
    assert collapsed["status"] == "byte_equivalent_resolution_proposals_collapsed"
    assert collapsed["mutation_permitted"] is True
    assert reversed_collapsed == collapsed
    assert collapsed["proposal_refs"] == sorted(
        collapsed["proposal_refs"],
        key=lambda item: (
            item["proposal_digest"],
            item["proposal_id"],
            item["stable_replay_key"],
        ),
    )

    first_record = build_contract_amendment_v2_from_analyst_proposal(
        proposal=collapsed["selected_proposal"],
        current_contract=first["parent_contract_ref"],
        new_component_spec={"component_id": "component:C"},
        request_digest="request-digest-order",
        requested_mode="Balanced",
    )
    reversed_record = build_contract_amendment_v2_from_analyst_proposal(
        proposal=reversed_collapsed["selected_proposal"],
        current_contract=first["parent_contract_ref"],
        new_component_spec={"component_id": "component:C"},
        request_digest="request-digest-order",
        requested_mode="Balanced",
    )
    assert reversed_record.to_dict() == first_record.to_dict()

    alternative = deepcopy(candidate)
    alternative["premise_semantics"] = "A materially different premise C."
    third, _, _ = _bind(alternative, artifact_suffix="three")
    ambiguous = arbitrate_analyst_query_resolution_proposals([first, third])
    assert ambiguous["status"] == "ambiguous_resolution_proposals"
    assert ambiguous["selected_proposal"] is None
    assert ambiguous["contract_amendment_permitted"] is False
    assert ambiguous["searchos_permitted"] is False


def test_replay_is_resolved_before_parent_currentness_and_conflicts_fail() -> None:
    _, _, components = _contract_and_graph()
    candidate = _searched_candidate(components["E"])
    proposal, contract, _ = _bind(candidate)
    downstream = {
        "amendment_record_ref": {"amendment_record_id": "amendment:1"},
        "application_ref": {"application_id": "application:1"},
    }
    replay = replay_before_currentness(
        proposal=proposal,
        replay_history=[{"proposal": proposal, "downstream_refs": downstream}],
        current_contract_ref={"accepted_contract_digest": "later"},
        current_graph_ref={"graph_digest": "later"},
    )
    assert replay["status"] == "exact_replay"
    assert replay["downstream_refs"] == downstream
    assert replay["mutation_permitted"] is False

    changed = deepcopy(candidate)
    changed["premise_semantics"] = "Changed content under the same local identity."
    changed_proposal, _, _ = _bind(changed)
    with pytest.raises(
        AnalystQueryResolutionProposalError,
        match="stable replay identity conflict",
    ):
        replay_before_currentness(
            proposal=changed_proposal,
            replay_history=[{"proposal": proposal, "downstream_refs": downstream}],
            current_contract_ref=contract,
            current_graph_ref=proposal["parent_graph_ref"],
        )


def test_searched_premise_amendment_is_atomic_and_preserves_matrix() -> None:
    _, _, components = _contract_and_graph()
    proposal, contract, _ = _bind(_searched_candidate(components["E"]))
    record = build_contract_amendment_v2_from_analyst_proposal(
        proposal=proposal,
        current_contract=contract,
        new_component_spec={
            "component_id": "component:C",
        },
        request_digest="request-digest-1",
        requested_mode="Balanced",
    )
    payload = record.to_dict()
    assert payload["validation"]["ok"] is True
    assert payload["schema_version"] == "contract_amendment_record_v2"
    assert [item["operation_kind"] for item in payload["operations"]] == [
        "add_component",
        "revise_component",
    ]
    added = payload["operations"][0]["operation_payload"]["component"]
    assert added["component_purpose"] == "supporting_premise"
    assert added["allowed_support_kinds"] == ["direct"]
    assert added["max_inference_depth"] == 0
    assert added["source_obligation_candidate_ids"] == ["obligation:component:C"]
    assert added["user_facing_label"] == ("Distinctive recovered premise C label")
    assert added["user_facing_question"] == ("Which distinctive filing condition establishes premise C?")
    assert added["acceptance_criteria"] == ["Distinctive criterion: verify the signed filing condition."]
    assert added["mandatory_caveats"] == ["Distinctive mandatory caveat for premise C."]
    assert (
        added["metadata"]["source_obligation_specification"]["distinctive_source_semantics"]
        == "Signed filing-condition record only."
    )
    revised = payload["operations"][1]["after_payload"]["component"]
    assert revised["dependency_component_ids"] == ["component:C"]
    assert revised["allowed_support_kinds"] == ["direct", "inferred"]
    assert revised["max_inference_depth"] == 1


def test_searched_premise_rejects_direct_only_target_without_widening() -> None:
    contract, graph, components = _contract_and_graph()
    direct_target = _direct(
        "component:E",
        purpose=ComponentPurpose.USER_FACING_ANSWER_TARGET.value,
    )
    contract["accepted_answer_component_refs"][-1] = direct_target.to_dict()
    proposal = bind_analyst_query_resolution_proposal(
        role_artifact=_artifact(
            contract=contract,
            graph=graph,
        ),
        local_candidate=_searched_candidate(direct_target),
        question_meaning_record_ref={
            "record_id": "qmr:1",
            "record_digest": "qmr-digest-1",
        },
        parent_contract_ref=contract,
        parent_graph_ref=graph,
    )
    before = deepcopy(contract)
    with pytest.raises(
        ValueError,
        match="must already permit inferred support",
    ):
        build_contract_amendment_v2_from_analyst_proposal(
            proposal=proposal,
            current_contract=contract,
            new_component_spec={"component_id": "component:C"},
            request_digest="request-digest-direct-only",
            requested_mode="Balanced",
        )
    assert contract == before
    assert components["E"].allowed_support_kinds == (
        SupportKind.DIRECT,
        SupportKind.INFERRED,
    )


def test_analyst_owns_resolution_candidates_and_scrutineer_authorship_is_retired() -> None:
    _, _, components = _contract_and_graph()
    normalized = _normalize_semantic_output(
        ROLE_COMPONENT_ANALYST,
        {
            "claim_text": "The current evidence does not establish premise C.",
            "support_status": "blocked",
            "caveats": [],
            "nonclaims": [],
            "blockers": ["Missing direct premise support."],
            "query_resolution_proposals": [_searched_candidate(components["E"])],
        },
    )
    assert normalized["query_resolution_proposals"][0]["classification"] == ("searched_premise")

    with pytest.raises(
        MulticomponentRoleRuntimeError,
        match="Scrutineer cannot author",
    ):
        _normalize_semantic_output(
            ROLE_SCRUTINEER,
            {
                "challenge_status": "challenged",
                "reasons": ["Missing premise."],
                "challenge_targets": [{"target_kind": "synthesis", "target_key": "target_E"}],
                "query_resolution_proposals": [{"proposal_key": "legacy"}],
                "caveats": [],
                "nonclaims": [],
            },
        )


def _searchos_state(profile: str = "deep") -> dict:
    policy = build_searchos_policy_snapshot(
        run_id="run:1",
        request_id="request:1",
        profile_name=profile.capitalize(),
        existing_gap_recovery_runtime_open=True,
    )
    return build_searchos_initial_state(
        run_id="run:1",
        request_id="request:1",
        answer_contract_ref={
            "answer_contract_id": "contract:1",
            "answer_contract_digest": "a" * 64,
        },
        policy_snapshot=policy,
        active_slots=[
            {
                "slot_id": "slot:A",
                "component_ref": {
                    "component_id": "component:A",
                    "component_digest": "b" * 64,
                },
                "source_obligation_ref": {
                    "source_obligation_id": "obligation:A",
                    "source_obligation_digest": "c" * 64,
                },
                "requirement_posture": "required",
            }
        ],
    )


def _amendment_ref(kind: str, digest_character: str) -> dict:
    return {
        f"{kind}_id": f"{kind}:1",
        f"{kind}_digest": digest_character * 64,
    }


def _admit_searched_cycle(
    state: dict,
    lease: dict,
    *,
    depth: int,
    replay_key: str,
    generation_parent_ref: dict,
) -> tuple[dict, dict]:
    return admit_searchos_recovery_cycle(
        state=state,
        lease=lease,
        stable_replay_key=replay_key,
        recovery_classification="searched_premise",
        proposal_ref={
            "proposal_id": f"proposal:{depth}",
            "proposal_digest": "d" * 64,
        },
        current_contract_ref={
            "answer_contract_id": f"contract:{depth + 1}",
            "answer_contract_digest": str(depth + 1) * 64,
        },
        current_graph_ref={
            "graph_id": f"graph:{depth}",
            "graph_digest": "e" * 64,
        },
        component_ref={
            "component_id": f"component:C{depth}",
            "component_digest": "f" * 64,
        },
        source_obligation_ref={
            "source_obligation_id": f"obligation:C{depth}",
            "source_obligation_digest": "9" * 64,
        },
        answer_target_refs=[
            {
                "component_id": "component:E",
                "component_digest": "8" * 64,
            }
        ],
        dependency_component_refs=[],
        generation_parent_ref=generation_parent_ref,
        generation_depth=depth,
        contract_amendment_record_ref=_amendment_ref(
            "amendment_record",
            "1",
        ),
        contract_amendment_admission_ref=_amendment_ref(
            "amendment_admission",
            "2",
        ),
        contract_amendment_application_ref=_amendment_ref(
            "amendment_application",
            "3",
        ),
        expected_parent_state_ref={
            "state_id": state["state_id"],
            "state_digest": state["state_digest"],
        },
    )


def _expenditure() -> dict:
    return {
        "logical_judgment_calls": 1,
        "search_queries": 1,
        "read_operations": 1,
        "navigation_operations": 0,
        "acquisition_operations": 1,
    }


def test_searchos_uses_one_shared_lease_and_append_only_linear_generations() -> None:
    initial = _searchos_state("deep")
    leased, lease, replayed = ensure_searchos_whole_run_recovery_lease(state=initial)
    assert replayed is False
    leased_again, same_lease, replayed = ensure_searchos_whole_run_recovery_lease(state=leased)
    assert replayed is True
    assert leased_again == leased
    assert same_lease == lease
    assert len(leased["recovery_lease_history"]) == 1

    first_state, first = _admit_searched_cycle(
        leased,
        lease,
        depth=1,
        replay_key="replay:searched:1",
        generation_parent_ref={
            "state_id": leased["state_id"],
            "state_digest": leased["state_digest"],
        },
    )
    first_admission = deepcopy(first["cycle_admission"])
    assert first["work_authorized"] is True
    assert first_admission["prior_slot_absent"] is True
    first_slot = first_state["slots_by_id"][first["recovery_slot_ref"]["slot_id"]]
    assert first_slot["current_candidate_state_ref"] == {}
    assert first_slot["current_window_ref"] == {}
    assert first_slot["candidate_wave_count"] == 0
    active_snapshot = deepcopy(first_state)
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="one linear active recovery cycle",
    ):
        _admit_searched_cycle(
            first_state,
            lease,
            depth=2,
            replay_key="replay:searched:active-sibling",
            generation_parent_ref={},
        )
    assert first_state == active_snapshot

    terminal_state, first_terminal = terminalize_searchos_recovery_cycle(
        state=first_state,
        cycle_admission_ref=first["cycle_admission_ref"],
        terminal_status="recovered",
        terminal_reason=None,
        terminal_interpretation=None,
        lawful_selected_recovery_work_remains=True,
        expenditure=_expenditure(),
        component_admission_ref={"admission_id": "component:C1"},
        component_coverage_ref={"coverage_id": "coverage:C1"},
    )
    assert terminal_state["recovery_cycle_admission_history"] == [first_admission]
    assert len(terminal_state["recovery_cycle_terminal_history"]) == 1
    first_expenditure_record = deepcopy(terminal_state["recovery_expenditure_history"][0])
    assert terminal_state["active_recovery_cycle_ref"] == {}
    assert terminal_state["recovery_terminal_aggregate"]["posture"] == ("open")
    assert terminal_state["recovery_terminal_aggregate"]["lawful_selected_recovery_work_remains"] is True

    replay_state, replay = _admit_searched_cycle(
        terminal_state,
        lease,
        depth=1,
        replay_key="replay:searched:1",
        generation_parent_ref={
            "state_id": leased["state_id"],
            "state_digest": leased["state_digest"],
        },
    )
    assert replay_state == terminal_state
    assert replay["status"] == "exact_replay"
    assert replay["work_authorized"] is False

    second_state, second = _admit_searched_cycle(
        terminal_state,
        lease,
        depth=2,
        replay_key="replay:searched:2",
        generation_parent_ref={
            "schema_version": "searchos_recovery_cycle_terminal_v2",
            "cycle_id": first_terminal["cycle_id"],
            "cycle_terminal_id": first_terminal["cycle_terminal_id"],
            "cycle_terminal_digest": first_terminal["cycle_terminal_digest"],
            "terminal_status": first_terminal["terminal_status"],
        },
    )
    assert second["cycle_admission"]["generation_depth"] == 2
    second_terminal_state, second_terminal = terminalize_searchos_recovery_cycle(
        state=second_state,
        cycle_admission_ref=second["cycle_admission_ref"],
        terminal_status="exhausted_insufficient",
        terminal_reason="No adequate direct source was acquired.",
        terminal_interpretation="lawful_recovery_exhaustion",
        lawful_selected_recovery_work_remains=False,
        expenditure=_expenditure(),
    )
    normalized_replay_state, normalized_replay_terminal = terminalize_searchos_recovery_cycle(
        state=second_terminal_state,
        cycle_admission_ref=second["cycle_admission_ref"],
        terminal_status="exhausted_insufficient",
        terminal_reason=("  No   adequate direct source was acquired.  "),
        terminal_interpretation="lawful_recovery_exhaustion",
        lawful_selected_recovery_work_remains=False,
        expenditure=_expenditure(),
    )
    assert normalized_replay_state == second_terminal_state
    assert normalized_replay_terminal == second_terminal
    assert len(second_terminal_state["recovery_cycle_admission_history"]) == 2
    assert len(second_terminal_state["recovery_cycle_terminal_history"]) == 2
    assert second_terminal_state["recovery_terminal_aggregate"]["terminal_count"] == 2
    assert second_terminal_state["recovery_terminal_aggregate"]["posture"] == "settled"
    assert (
        second_terminal_state["recovery_terminal_aggregate"]["settled_interpretation"] == "lawful_recovery_exhaustion"
    )
    assert second_terminal_state["recovery_terminal_aggregate"]["cumulative_expenditure"] == {
        key: value * 2 for key, value in _expenditure().items()
    }
    assert second_terminal_state["recovery_lease"] == leased["recovery_lease"]
    assert len(second_terminal_state["recovery_lease_history"]) == 1
    assert second_terminal_state["recovery_expenditure_history"][0] == (first_expenditure_record)
    assert len(second_terminal_state["recovery_expenditure_history"]) == 2
    before_generation_three = deepcopy(second_terminal_state)

    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="generation 3|budget",
    ):
        _admit_searched_cycle(
            second_terminal_state,
            lease,
            depth=3,
            replay_key="replay:searched:3",
            generation_parent_ref={},
        )
    assert second_terminal_state == before_generation_three


def test_terminal_policy_uses_typed_interpretation_not_reason_prose() -> None:
    initial = _searchos_state("balanced")
    leased, lease, _ = ensure_searchos_whole_run_recovery_lease(state=initial)
    admitted, cycle = _admit_searched_cycle(
        leased,
        lease,
        depth=1,
        replay_key="replay:typed:structural",
        generation_parent_ref={
            "state_id": leased["state_id"],
            "state_digest": leased["state_digest"],
        },
    )
    structural_state, structural = terminalize_searchos_recovery_cycle(
        state=admitted,
        cycle_admission_ref=cycle["cycle_admission_ref"],
        terminal_status="failed",
        terminal_reason="Identical diagnostic prose.",
        terminal_interpretation="structural_or_validation_blocker",
        lawful_selected_recovery_work_remains=False,
        expenditure=_expenditure(),
    )
    assert structural["terminal_blocker"] == {
        "blocker_class": "structural_or_validation",
        "interpretation": "structural_or_validation_blocker",
        "reason_code": "Identical diagnostic prose.",
    }
    assert (
        structural_state["recovery_terminal_aggregate"]["settled_interpretation"] == "structural_or_validation_blocker"
    )
    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="typed interpretation",
    ):
        settle_searchos_recovery_terminal_aggregate(
            state=admitted,
            settled_interpretation="invented_from_reason_prose",
        )

    admitted_2, cycle_2 = _admit_searched_cycle(
        leased,
        lease,
        depth=1,
        replay_key="replay:typed:exhaustion",
        generation_parent_ref={
            "state_id": leased["state_id"],
            "state_digest": leased["state_digest"],
        },
    )
    exhausted_state, exhausted = terminalize_searchos_recovery_cycle(
        state=admitted_2,
        cycle_admission_ref=cycle_2["cycle_admission_ref"],
        terminal_status="exhausted_insufficient",
        terminal_reason="Identical diagnostic prose.",
        terminal_interpretation="lawful_recovery_exhaustion",
        lawful_selected_recovery_work_remains=False,
        expenditure=_expenditure(),
    )
    assert exhausted["terminal_blocker"]["interpretation"] == "lawful_recovery_exhaustion"
    assert exhausted_state["recovery_terminal_aggregate"]["settled_interpretation"] == "lawful_recovery_exhaustion"

    with pytest.raises(
        SearchOSExistingGapRecoveryError,
        match="status and typed interpretation conflict",
    ):
        terminalize_searchos_recovery_cycle(
            state=admitted_2,
            cycle_admission_ref=cycle_2["cycle_admission_ref"],
            terminal_status="failed",
            terminal_reason="Identical diagnostic prose.",
            terminal_interpretation="lawful_recovery_exhaustion",
            lawful_selected_recovery_work_remains=False,
            expenditure=_expenditure(),
        )


@pytest.mark.parametrize(
    ("profile", "searched_allowed"),
    [("fast", False), ("balanced", True), ("deep", True)],
)
def test_searchos_profile_recovery_cycle_caps(
    profile: str,
    searched_allowed: bool,
) -> None:
    state = _searchos_state(profile)
    state, lease, _ = ensure_searchos_whole_run_recovery_lease(state=state)
    if searched_allowed:
        _, result = _admit_searched_cycle(
            state,
            lease,
            depth=1,
            replay_key=f"replay:{profile}:1",
            generation_parent_ref={
                "state_id": state["state_id"],
                "state_digest": state["state_digest"],
            },
        )
        assert result["work_authorized"] is True
    else:
        with pytest.raises(
            SearchOSExistingGapRecoveryError,
            match="searched-premise recovery cycle budget",
        ):
            _admit_searched_cycle(
                state,
                lease,
                depth=1,
                replay_key="replay:fast:1",
                generation_parent_ref={
                    "state_id": state["state_id"],
                    "state_digest": state["state_digest"],
                },
            )
