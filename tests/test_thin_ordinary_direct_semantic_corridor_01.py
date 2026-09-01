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
from copy import deepcopy
from typing import Any

import pytest

import core.component_work_graph_v1 as graph_runtime
import core.multicomponent_graph_scheduling as scheduler_runtime
import core.ordinary_multicomponent_synthesis_runtime as ordinary_runtime
from core.evidence_ledger import (
    CandidateCustodyKind,
    CandidateCustodyRecord,
    CandidateDisposition,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SYSTEM_PROMPTS,
)
from core.ordinary_direct_semantic_corridor import (
    execute_ordinary_direct_semantic_corridor,
)
from core.run_kernel import RunKernel
from core.strict_one_shot_model_transport import (
    wrap_text_callable_as_strict_one_shot_transport,
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
) -> Any:
    def ask_model(prompt: str, system_prompt: str, **_kwargs: Any) -> str:
        packet = json.loads(prompt)
        captured.append({"system_prompt": system_prompt, "packet": packet})
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            component_id = str(packet["component_ref"]["component_id"])
            aliases = [
                str(item["local_evidence_alias"])
                for item in packet["component_evidence_set"]["members"]
            ]
            return json.dumps(
                {
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
            )
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            return json.dumps(
                {
                    "synthesis_proposals": cross_proposals,
                    "self_audit": SELF_AUDIT,
                }
            )
        raise AssertionError(f"unexpected semantic role prompt: {system_prompt}")

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
    captured: list[dict[str, Any]] = []
    admissions, cross = execute_ordinary_direct_semantic_corridor(
        run_kernel=kernel,
        component_evidence_sets=evidence_sets,
        query="Relate the exact bounded offline components.",
        requested_synthesis_directive="Relate the exact components.",
        requested_mode="Balanced",
        strict_one_shot_transport=_transport(
            cross_proposals=cross_proposals,
            captured=captured,
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


def test_n2_mixed_cardinality_direct_admissions_then_one_bound_cross(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, admissions, cross, captured = _execute(
        monkeypatch,
        cross_proposals=_one_relationship_proposal(),
    )

    assert [item["component_id"] for item in admissions] == [
        "component-1",
        "component-2",
    ]
    assert [len(item["packet"]["component_evidence_set"]["members"]) for item in captured[:2]] == [
        1,
        2,
    ]
    assert cross is not None
    assert cross["semantic_output"]["self_audit"] == SELF_AUDIT
    assert cross["semantic_output"]["synthesis_proposals"][0][
        "component_inputs"
    ] == ["component-1", "component-2"]
    assert [item["system_prompt"] for item in captured].count(
        ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
    ) == 1
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
    assert not any(
        "synthesis" in key or "relationship" in key
        for key in kernel.state.projections
        if key != "multicomponent_component_admission"
    )
    _assert_old_path_absent(kernel)
