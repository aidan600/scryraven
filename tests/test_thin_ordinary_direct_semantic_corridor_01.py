"""Offline Phase-1 proof for the thin ordinary direct semantic corridor.

Test path/node id: this module's focused positive and absence proofs
Proof class: OFFLINE_COMPONENT_PROOF
Validation bucket: phase_focus
Surface guarded: direct Component Analyst/admission/Cross composition
High-custody or closed-this-phase surface: SearchPlanner, D-prime, Scrutineer,
Sufficiency, FAP, Author, and the ordinary scheduler/Graph path remain closed
Runtime/product path guarded: experimental branch-only direct corridor
Expected cost: bounded in-memory fake transports, under 10s
Promotion posture: exploratory proof only; not a fast_pr sentinel
Demotion/retirement condition: replace after separately authorized ordinary
product-path convergence and held-out PRODUCT evidence.
Why not fast_pr: this is a phase-local architecture experiment.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any

import pytest

import core.component_work_graph_v1 as graph_runtime
import core.multicomponent_graph_scheduling as scheduler_runtime
import core.ordinary_direct_semantic_corridor as direct_runtime
import core.ordinary_multicomponent_synthesis_runtime as ordinary_runtime
from core.component_analyst_evidence_set import build_component_analyst_evidence_set
from core.evidence_ledger import (
    CandidateCustodyKind,
    CandidateCustodyRecord,
    CandidateDisposition,
)
from core.multicomponent_component_admission import (
    MulticomponentComponentAdmissionError,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYSTEM_PROMPTS,
    MulticomponentRoleRuntimeError,
    safe_packet_digest,
)
from core.ordinary_direct_semantic_corridor import (
    OrdinaryDirectSemanticCorridorError,
    _validate_direct_cross_result_binding,
    execute_ordinary_direct_semantic_corridor,
)
from core.ordinary_multicomponent_synthesis_runtime import (
    OrdinaryMulticomponentRuntimeError,
)
from core.run_kernel import RunKernel
from core.strict_one_shot_model_transport import (
    wrap_text_callable_as_strict_one_shot_transport,
)
from tests.fixtures.component_analyst_evidence_sets import (
    component_analyst_evidence_set_fixture,
)
from tests.test_searchos_component_analyst_multimaterial_direct_handoff_01 import (
    _scheduler_inputs_with_exact_sets,
)

SELF_AUDIT = (
    "The relationship stays within the exact admitted component cases and "
    "retains their caveats, nonclaims, and blockers."
)


def _forbid_old_path(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the thin direct corridor invoked forbidden old-path work")

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
        (graph_runtime, "component_work_graph_v1_resynthesis_from_cross_component_artifact"),
        (graph_runtime, "reduce_component_work_graph_v1"),
        (graph_runtime, "synthesis_dprime_input_packet"),
        (graph_runtime, "scrutineer_input_packet"),
        (ordinary_runtime, "_execute_multicomponent_role_transport"),
        (ordinary_runtime, "_execute_run_kernel_selected_batch"),
    ):
        monkeypatch.setattr(owner, name, forbidden)


def _transport(
    *,
    cross_proposals: list[dict[str, Any]],
    captured: list[dict[str, Any]],
    component_two_support: str = "all",
    response_mutator: (
        Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]] | None
    ) = None,
) -> Any:
    def ask_model(prompt: str, system_prompt: str, **_kwargs: Any) -> str:
        packet = json.loads(prompt)
        captured.append({"system_prompt": system_prompt, "packet": packet})
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            role = ROLE_COMPONENT_ANALYST
            component_id = str(packet["component_ref"]["component_id"])
            aliases = [
                str(item["local_evidence_alias"])
                for item in packet["component_evidence_set"]["members"]
            ]
            if component_id == "component-2" and component_two_support == "first":
                aliases = aliases[:1]
            response = {
                "case_posture": "supported",
                "claim_text": f"The exact supplied materials support {component_id}.",
                "evidence_analysis": (
                    f"All {len(aliases)} nominated bounded materials support the claim."
                ),
                "self_audit": "The component claim does not exceed its exact evidence set.",
                "supporting_evidence_aliases": aliases,
                "caveats": [],
                "nonclaims": [],
                "contradictions": [],
                "blockers": [],
            }
        elif system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            role = ROLE_CROSS_COMPONENT_ANALYST
            response = {
                "synthesis_proposals": cross_proposals,
                "self_audit": SELF_AUDIT,
            }
        else:
            raise AssertionError(f"unexpected semantic role prompt: {system_prompt}")
        if response_mutator is not None:
            response = response_mutator(role, packet, response)
        return json.dumps(response)

    return wrap_text_callable_as_strict_one_shot_transport(
        ask_model,
        canonical_provider="OpenAI",
        model="offline-direct-corridor",
    )


def _execute(
    monkeypatch: pytest.MonkeyPatch,
    *,
    cross_proposals: list[dict[str, Any]],
    n1: bool = False,
    component_two_support: str = "all",
    fixture_mutator: (
        Callable[[Any, dict[str, dict[str, Any]], dict[str, Any]], None] | None
    ) = None,
    response_mutator: (
        Callable[[str, dict[str, Any], dict[str, Any]], dict[str, Any]] | None
    ) = None,
    capture_sink: list[dict[str, Any]] | None = None,
) -> tuple[Any, tuple[dict[str, Any], ...], dict[str, Any] | None, list[dict[str, Any]]]:
    _forbid_old_path(monkeypatch)
    kernel, _packets, evidence_sets, contract = _scheduler_inputs_with_exact_sets()
    for candidate in kernel.state.evidence_ledger.candidates.values():
        candidate.fact_disposition = CandidateDisposition.ACCEPTED
        candidate.final_evidence_eligible = True
        kernel.state.evidence_ledger.custody_records.append(
            CandidateCustodyRecord(
                candidate_id=candidate.candidate_id,
                record_kind=CandidateCustodyKind.FACT,
                disposition=CandidateDisposition.ACCEPTED,
                reason="bounded offline direct-corridor fixture custody",
                source="offline_direct_corridor_fixture",
            )
        )
    if n1:
        contract = deepcopy(contract)
        contract["accepted_answer_component_refs"] = contract[
            "accepted_answer_component_refs"
        ][:1]
        contract["accepted_answer_component_count"] = 1
        contract["accepted_contract_digest"] = "multimaterial-n1-contract-digest"
        kernel.state.initial_answer_contract = deepcopy(contract)
        evidence_sets = {"component-1": evidence_sets["component-1"]}
    if fixture_mutator is not None:
        fixture_mutator(kernel, evidence_sets, contract)
    captured = capture_sink if capture_sink is not None else []
    admissions, cross = execute_ordinary_direct_semantic_corridor(
        run_kernel=kernel,
        component_evidence_sets=evidence_sets,
        query="Relate the exact bounded offline components.",
        requested_synthesis_directive="Relate the exact components.",
        requested_mode="Balanced",
        strict_one_shot_transport=_transport(
            cross_proposals=cross_proposals,
            captured=captured,
            component_two_support=component_two_support,
            response_mutator=response_mutator,
        ),
        clean_json_response=lambda value: value,
        provider="OpenAI",
        model="offline-direct-corridor",
        use_reasoning=False,
    )
    return kernel, admissions, cross, captured


def _one_relationship_proposal() -> list[dict[str, Any]]:
    return [
        {
            "synthesis_key": "bounded_relation",
            "claim_text": "The exact admitted component cases form the requested relation.",
            "relationship_type": "bounded_comparison",
            "component_inputs": ["component_01", "component_02"],
            "synthesis_inputs": [],
            "caveats": ["Only the supplied current cases are related."],
            "nonclaims": ["This does not establish whole-answer sufficiency."],
            "blockers": [],
        }
    ]


def _assert_old_path_absent(kernel: Any) -> None:
    assert "multicomponent_graph_scheduler" not in kernel.state.projections
    assert "multicomponent_component_work_graph_v1" not in kernel.state.projections
    assert not kernel.state.multicomponent_scheduler_context
    roles = [str(action.inputs.get("role") or "") for action in kernel.state.issued_actions.values()]
    assert "synthesis_dprime" not in roles
    assert "scrutineer" not in roles
    assert all("lease" not in action.action_type.value for action in kernel.state.issued_actions.values())
    assert all("batch" not in action.action_type.value for action in kernel.state.issued_actions.values())


def test_n1_direct_component_analyst_and_admission_without_cross(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, admissions, cross, captured = _execute(
        monkeypatch,
        cross_proposals=[],
        n1=True,
    )

    assert [item["component_id"] for item in admissions] == ["component-1"]
    assert admissions[0]["admission_status"] == "admitted"
    assert cross is None
    assert [item["system_prompt"] for item in captured] == [
        ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]
    ]
    _assert_old_path_absent(kernel)


@pytest.mark.parametrize(
    ("component_two_support", "expected_component_two_evidence_count"),
    (("first", 1), ("all", 2)),
)
def test_n2_mixed_cardinality_direct_admissions_then_one_bound_cross(
    monkeypatch: pytest.MonkeyPatch,
    component_two_support: str,
    expected_component_two_evidence_count: int,
) -> None:
    build_calls = 0
    original_build = direct_runtime._build_direct_cross_input_packet

    def counted_build(**kwargs: Any) -> dict[str, Any]:
        nonlocal build_calls
        build_calls += 1
        return original_build(**kwargs)

    monkeypatch.setattr(
        direct_runtime,
        "_build_direct_cross_input_packet",
        counted_build,
    )
    kernel, admissions, cross, captured = _execute(
        monkeypatch,
        cross_proposals=_one_relationship_proposal(),
        component_two_support=component_two_support,
    )

    assert [item["component_id"] for item in admissions] == [
        "component-1",
        "component-2",
    ]
    assert [len(item["packet"]["component_evidence_set"]["members"]) for item in captured[:2]] == [
        1,
        2,
    ]
    assert len(admissions[1]["evidence_refs"]) == expected_component_two_evidence_count
    assert cross is not None
    assert cross["semantic_output"]["self_audit"] == SELF_AUDIT
    assert cross["semantic_output"]["synthesis_proposals"][0][
        "component_inputs"
    ] == ["component-1", "component-2"]
    assert [item["system_prompt"] for item in captured].count(
        ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
    ) == 1
    assert build_calls == 1
    assert cross["input_packet_digest"] == safe_packet_digest(captured[-1]["packet"])
    assert [
        item["component_id"] for item in captured[-1]["packet"]["component_nodes"]
    ] == ["component-1", "component-2"]
    _assert_old_path_absent(kernel)


def test_zero_proposals_retains_cross_artifact_without_downstream_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, admissions, cross, captured = _execute(
        monkeypatch,
        cross_proposals=[],
    )

    assert len(admissions) == 2
    assert cross is not None
    assert cross["semantic_output"] == {
        "synthesis_proposals": [],
        "self_audit": SELF_AUDIT,
    }
    assert [item["system_prompt"] for item in captured].count(
        ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
    ) == 1
    assert len(kernel.state.issued_actions) == 5
    assert not cross["semantic_output"].get("query_resolution_proposals")
    assert not cross["semantic_output"].get("specialist_need_proposal")
    assert not any(
        "synthesis" in key or "relationship" in key
        for key in kernel.state.projections
        if key != "multicomponent_component_admission"
    )
    _assert_old_path_absent(kernel)


def _with_component_binding(
    evidence_set: Mapping[str, Any],
    *,
    component_id: str,
) -> dict[str, Any]:
    return build_component_analyst_evidence_set(
        [
            {
                "evidence_ref_id": member["code_binding"]["evidence_ref_id"],
                "passage": {
                    **deepcopy(member["passage"]),
                    "searchos_slot_ref": {"component_id": component_id},
                },
                "candidate_record": deepcopy(member["candidate_record"]),
            }
            for member in evidence_set["members"]
        ]
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("foreign", "not current ledger authority"),
        ("stale", "content or custody binding is altered"),
        ("cross_component", "cross-component binding"),
        ("missing_component", "one exact evidence set per accepted component"),
    ),
)
def test_direct_input_evidence_and_component_integrity_fail_before_model_call(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    message: str,
) -> None:
    captured: list[dict[str, Any]] = []

    def mutate_fixture(
        _kernel: Any,
        evidence_sets: dict[str, dict[str, Any]],
        _contract: dict[str, Any],
    ) -> None:
        if mutation == "foreign":
            evidence_sets["component-1"] = component_analyst_evidence_set_fixture(
                {
                    "evidence_ref_id": "evidence:foreign",
                    "bounded_text": "Foreign material must not enter this component.",
                }
            )
        elif mutation == "stale":
            evidence_sets["component-1"]["members"][0]["passage"][
                "text"
            ] = "A stale mutation after canonicalization."
        elif mutation == "cross_component":
            bound = {
                component_id: _with_component_binding(
                    evidence_set,
                    component_id=component_id,
                )
                for component_id, evidence_set in evidence_sets.items()
            }
            evidence_sets["component-1"] = bound["component-2"]
            evidence_sets["component-2"] = bound["component-1"]
        elif mutation == "missing_component":
            evidence_sets.pop("component-2")
        else:  # pragma: no cover - parametrization closes this branch
            raise AssertionError(mutation)

    with pytest.raises(OrdinaryDirectSemanticCorridorError, match=message):
        _execute(
            monkeypatch,
            cross_proposals=_one_relationship_proposal(),
            fixture_mutator=mutate_fixture,
            capture_sink=captured,
        )

    assert captured == []


@pytest.mark.parametrize(
    ("alias_mutation", "message"),
    (
        ("unknown", "unknown supplied member"),
        ("duplicate", "repeat a supplied member"),
    ),
)
def test_direct_component_analyst_alias_substitution_fails_before_admission(
    monkeypatch: pytest.MonkeyPatch,
    alias_mutation: str,
    message: str,
) -> None:
    captured: list[dict[str, Any]] = []

    def mutate_response(
        role: str,
        _packet: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, Any]:
        if role != ROLE_COMPONENT_ANALYST:
            return response
        aliases = list(response["supporting_evidence_aliases"])
        response["supporting_evidence_aliases"] = (
            ["component_evidence_foreign"]
            if alias_mutation == "unknown"
            else [aliases[0], aliases[0]]
        )
        return response

    with pytest.raises(
        (OrdinaryMulticomponentRuntimeError, MulticomponentRoleRuntimeError),
        match=message,
    ):
        _execute(
            monkeypatch,
            cross_proposals=_one_relationship_proposal(),
            response_mutator=mutate_response,
            capture_sink=captured,
        )

    assert captured
    assert all(
        item["system_prompt"]
        != ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
        for item in captured
    )


def test_stale_current_ledger_evidence_fails_before_cross(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, Any]] = []

    def stale_ledger_candidate(
        kernel: Any,
        _evidence_sets: dict[str, dict[str, Any]],
        _contract: dict[str, Any],
    ) -> None:
        candidate = kernel.state.evidence_ledger.candidates["evidence:a"]
        candidate.fact_disposition = CandidateDisposition.REJECTED
        candidate.final_evidence_eligible = False
        candidate.currentness_signal = "stale"

    with pytest.raises(OrdinaryMulticomponentRuntimeError, match="could not satisfy"):
        _execute(
            monkeypatch,
            cross_proposals=_one_relationship_proposal(),
            fixture_mutator=stale_ledger_candidate,
            capture_sink=captured,
        )

    assert captured
    assert all(
        item["system_prompt"]
        != ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
        for item in captured
    )


def test_wrong_component_analyst_result_fails_existing_admission_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_admission = direct_runtime.execute_multicomponent_component_admission
    first_artifact: dict[str, Any] = {}
    captured: list[dict[str, Any]] = []

    def substitute_component_result(**kwargs: Any) -> dict[str, Any]:
        if kwargs["component_id"] == "component-1":
            first_artifact.update(deepcopy(kwargs["analyst_artifact"]))
        elif kwargs["component_id"] == "component-2":
            kwargs = {**kwargs, "analyst_artifact": deepcopy(first_artifact)}
        return original_admission(**kwargs)

    monkeypatch.setattr(
        direct_runtime,
        "execute_multicomponent_component_admission",
        substitute_component_result,
    )
    with pytest.raises(
        MulticomponentComponentAdmissionError,
        match="exact input binding mismatch|exact completed RunKernel Analyst case",
    ):
        _execute(
            monkeypatch,
            cross_proposals=_one_relationship_proposal(),
            capture_sink=captured,
        )

    assert first_artifact
    assert all(
        item["system_prompt"]
        != ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
        for item in captured
    )


def test_wrong_component_analyst_exact_input_fails_existing_admission_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_admission = direct_runtime.execute_multicomponent_component_admission

    def substitute_analyst_input(**kwargs: Any) -> dict[str, Any]:
        if kwargs["component_id"] == "component-2":
            packet = deepcopy(kwargs["analyst_input_packet"])
            packet["component_ref"]["component_digest"] = "foreign-component-digest"
            kwargs = {**kwargs, "analyst_input_packet": packet}
        return original_admission(**kwargs)

    monkeypatch.setattr(
        direct_runtime,
        "execute_multicomponent_component_admission",
        substitute_analyst_input,
    )
    with pytest.raises(
        MulticomponentComponentAdmissionError,
        match="exact input binding mismatch",
    ):
        _execute(
            monkeypatch,
            cross_proposals=_one_relationship_proposal(),
        )


def test_cross_foreign_component_alias_fails_exact_current_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _one_relationship_proposal()[0]
    proposal["component_inputs"] = ["component_01", "component_foreign"]

    with pytest.raises(
        OrdinaryDirectSemanticCorridorError,
        match="unknown or duplicate component binding",
    ):
        _execute(monkeypatch, cross_proposals=[proposal])


def _projection_with_refreshed_digest(projection: Mapping[str, Any]) -> dict[str, Any]:
    updated = deepcopy(dict(projection))
    updated["projection_digest"] = safe_packet_digest(
        {key: value for key, value in updated.items() if key != "projection_digest"}
    )
    return updated


def test_stale_component_result_is_rejected_before_cross_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_build = direct_runtime._build_direct_cross_input_packet
    captured: list[dict[str, Any]] = []

    def stale_before_build(**kwargs: Any) -> dict[str, Any]:
        kernel = kwargs["run_kernel"]
        projection = deepcopy(
            kernel.state.projections["multicomponent_component_admission"]
        )
        projection["component_admission_refs"][1]["current"] = False
        projection["component_admission_refs"][1]["stale"] = True
        kernel.state.projections["multicomponent_component_admission"] = (
            _projection_with_refreshed_digest(projection)
        )
        return original_build(**kwargs)

    monkeypatch.setattr(
        direct_runtime,
        "_build_direct_cross_input_packet",
        stale_before_build,
    )
    with pytest.raises(
        OrdinaryDirectSemanticCorridorError,
        match="stale or incomplete",
    ):
        _execute(
            monkeypatch,
            cross_proposals=_one_relationship_proposal(),
            capture_sink=captured,
        )

    assert len(captured) == 2
    assert all(
        item["system_prompt"] == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]
        for item in captured
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("stale_component", "stale or incomplete"),
        ("mutated_projection", "lost canonical integrity"),
        ("component_substitution", "input is stale"),
        ("wrong_cross_digest", "exact-input binding mismatch"),
    ),
)
def test_direct_cross_exact_current_binding_rejects_stale_substituted_and_forged_inputs(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    message: str,
) -> None:
    kernel, _admissions, cross, captured = _execute(
        monkeypatch,
        cross_proposals=_one_relationship_proposal(),
    )
    assert cross is not None
    packet = deepcopy(captured[-1]["packet"])
    artifact = deepcopy(cross)
    if mutation == "stale_component":
        projection = deepcopy(
            kernel.state.projections["multicomponent_component_admission"]
        )
        projection["component_admission_refs"][1]["current"] = False
        projection["component_admission_refs"][1]["stale"] = True
        kernel.state.projections["multicomponent_component_admission"] = (
            _projection_with_refreshed_digest(projection)
        )
    elif mutation == "mutated_projection":
        kernel.state.projections["multicomponent_component_admission"][
            "component_admission_refs"
        ][0]["required_caveats"] = ["Post-reduction mutation must fail."]
    elif mutation == "component_substitution":
        packet["component_nodes"][1] = deepcopy(packet["component_nodes"][0])
    elif mutation == "wrong_cross_digest":
        artifact["input_packet_digest"] = "0" * 64
        artifact["artifact_digest"] = safe_packet_digest(
            {key: value for key, value in artifact.items() if key != "artifact_digest"}
        )
    else:  # pragma: no cover - parametrization closes this branch
        raise AssertionError(mutation)

    with pytest.raises(OrdinaryDirectSemanticCorridorError, match=message):
        _validate_direct_cross_result_binding(
            run_kernel=kernel,
            cross_input_packet=packet,
            cross_artifact=artifact,
        )


def test_cross_run_result_reuse_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _kernel, _admissions, original_cross, original_captured = _execute(
        monkeypatch,
        cross_proposals=_one_relationship_proposal(),
    )
    assert original_cross is not None

    def rebind_run(
        kernel: Any,
        _evidence_sets: dict[str, dict[str, Any]],
        _contract: dict[str, Any],
    ) -> None:
        kernel.state.run_id = "foreign-direct-corridor-run"
        kernel.state.request_id = "foreign-direct-corridor-request"
        kernel.state.initial_answer_contract["run_id"] = kernel.state.run_id
        kernel.state.initial_answer_contract["request_id"] = kernel.state.request_id

    foreign_kernel, _foreign_admissions, _foreign_cross, foreign_captured = _execute(
        monkeypatch,
        cross_proposals=_one_relationship_proposal(),
        fixture_mutator=rebind_run,
    )
    with pytest.raises(OrdinaryDirectSemanticCorridorError):
        _validate_direct_cross_result_binding(
            run_kernel=foreign_kernel,
            cross_input_packet=foreign_captured[-1]["packet"],
            cross_artifact=original_cross,
        )


def test_direct_cross_dependency_depth_uses_installed_mechanical_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposals = [
        _one_relationship_proposal()[0],
        {
            **_one_relationship_proposal()[0],
            "synthesis_key": "second_relation",
            "component_inputs": ["component_02"],
            "synthesis_inputs": ["bounded_relation"],
        },
        {
            **_one_relationship_proposal()[0],
            "synthesis_key": "third_relation",
            "component_inputs": ["component_01"],
            "synthesis_inputs": ["second_relation"],
        },
    ]

    with pytest.raises(
        OrdinaryDirectSemanticCorridorError,
        match="dependency depth exceeds",
    ):
        _execute(monkeypatch, cross_proposals=proposals)
