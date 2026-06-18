from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import (
    AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE,
    execute_followup_final_answer_packet_readiness_action,
)
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    evidence_ledger_projection_digest,
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import (
    FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
)
from tests.helpers.followup_fixture_spine import run_followup_through_execution
from tests.test_ag96i3m2_followup_evidence_intake_activation import (
    _execute_m2_intake,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "ag96i3o1-final-answer-packet-readiness"


def test_valid_i3n_recheck_authorizes_executes_and_reduces_readiness() -> None:
    kernel = _m2n_kernel()
    before = _closed_surface_snapshot(kernel)

    action = kernel.authorize_followup_final_answer_packet_readiness()
    recheck = kernel.state.followup_sufficiency_recheck_state
    sufficiency = kernel.state.sufficiency_judgment_projection
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()

    assert action.stage == FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE
    assert action.inputs["recheck_id"] == recheck["recheck_id"]
    assert action.inputs["followup_sufficiency_recheck_id"] == recheck["recheck_id"]
    assert action.inputs["followup_sufficiency_recheck_observation_id"] == (
        recheck["observation_id"]
    )
    assert action.inputs["intake_id"] == recheck["intake_id"]
    assert action.inputs["followup_evidence_intake_id"] == (
        recheck["followup_evidence_intake_id"]
    )
    assert action.inputs["execution_id"] == recheck["execution_id"]
    assert action.inputs["followup_authorization_consumption_id"] == (
        recheck["followup_authorization_consumption_id"]
    )
    assert action.inputs["sealed_candidate_id"] == recheck["sealed_candidate_id"]
    assert action.inputs["provider_job_kind"] == recheck["provider_job_kind"]
    assert action.inputs["component_id"] == recheck["component_id"]
    assert action.inputs["source_obligation_id"] == recheck["source_obligation_id"]
    assert action.inputs["requirement_ids"] == recheck["requirement_ids"]
    assert action.inputs["expected_source_classes"] == [
        "official_government",
        "official_current_rules",
    ]
    assert action.inputs["evidence_ledger_intake_mode"] == (
        "ag96i3m2_admission_review_followup_intake"
    )
    assert action.inputs["sufficiency_recheck_mode"] == (
        FOLLOWUP_SUFFICIENCY_RECHECK_MODE
    )
    assert action.inputs["packet_preparation_readiness_mode"] == (
        AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
    )
    assert action.inputs["evidence_ledger_projection_digest"] == (
        evidence_ledger_projection_digest(ledger)
    )
    assert action.inputs["sufficiency_judgment_digest"]
    assert action.inputs["followup_sufficiency_recheck_digest"]

    result = _execute_readiness(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_final_answer_packet_readiness_state
    projection = kernel.state.followup_final_answer_packet_readiness_projection
    assert state["owner"] == "RunKernel.FollowupFinalAnswerPacketReadiness"
    assert state["canonical_state"] is True
    assert projection["canonical_state"] is True
    assert projection["diagnostic_only"] is True
    assert projection["not_final_answer_packet_authority"] is True
    assert projection["not_role_consumption_payload"] is True
    assert projection["preparation_readiness_status"] == (
        "prerequisites_present_activation_blocked"
    )
    assert projection["final_answer_activation_blocked"] is True
    assert projection["prerequisite_summary"]["custody_present"] is True
    assert projection["prerequisite_summary"]["sufficiency_rechecked"] is True
    assert projection["prerequisite_summary"]["obligations_satisfied"] is True
    assert projection["evidence_ledger_counts"]["candidate_count"] == 1
    assert projection["evidence_ledger_counts"]["custody_record_count"] == 1
    assert projection["source_requirement_status_summary"]["satisfied"] == 1
    assert projection["official_current_custody_status"][
        "official_current_satisfied"
    ] is True
    assert projection["sufficiency_decision"] == sufficiency["decision"]
    assert projection["final_answer_allowed"] is False
    assert projection["canonical_final_answer_packet_mutated"] is False
    assert projection["final_evidence_selected"] is False
    assert projection["citation_eligible"] is False
    assert projection["citations_rendered"] is False
    assert projection["citation_rendering_changed"] is False
    assert projection["citation_formatter_invoked"] is False
    assert projection["author_activation_allowed"] is False
    assert projection["author_payload_created"] is False
    assert projection["author_execution_deferred"] is True
    assert projection["analyst_activation_allowed"] is False
    assert projection["analyst_handoff_created"] is False
    assert projection["economist_activation_allowed"] is False
    assert projection["economist_handoff_created"] is False
    assert projection["economist_code_execution_allowed"] is False
    assert projection["answer_ready"] is False
    assert projection["prompt_behavior_changed"] is False
    assert projection["product_answer_behavior_changed"] is False
    assert projection["live_validation_not_run"] is True
    assert projection["ag96i3m2_candidate_summary"]
    assert projection["ag96i3m2_binding_summary"]
    assert projection["ag96i3n_recheck_summary"]["recheck_id"] == recheck["recheck_id"]
    assert "citation_eligible_source_ids" not in projection
    assert "citation_eligibility_refs" not in projection
    assert "final_evidence_refs" not in projection
    assert "author_payload_ref" not in projection
    assert kernel.state.projections[FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE] == (
        projection
    )
    assert kernel.state.followup_final_answer_packet_readiness_history == [
        projection
    ]
    assert _closed_surface_snapshot(kernel) == before


def test_missing_custody_blocks_readiness_without_selecting_final_evidence() -> None:
    kernel = _m2n_kernel()
    kernel.state.evidence_ledger.custody_records.clear()

    _authorize_execute_reduce_readiness(kernel)

    projection = kernel.state.followup_final_answer_packet_readiness_projection
    assert projection["prerequisite_summary"]["custody_present"] is False
    assert "missing_custody" in projection["block_reasons"]
    assert projection["final_evidence_selected"] is False
    assert projection["citation_eligible"] is False
    assert kernel.state.final_answer_packet == {}


def test_unsatisfied_obligation_blocks_readiness_with_explicit_reason() -> None:
    kernel = _m2n_kernel(source_obligation_satisfied=False)

    _authorize_execute_reduce_readiness(kernel)

    projection = kernel.state.followup_final_answer_packet_readiness_projection
    assert projection["source_requirement_status_summary"]["unsatisfied"] == 1
    assert projection["prerequisite_summary"]["obligations_missing"] is True
    assert "missing_or_unsatisfied_obligation" in projection["block_reasons"]
    assert projection["missing_obligations"][0]["status"] == "unsatisfied"
    assert projection["answer_ready"] is False


def test_caveats_and_prohibited_upgrades_are_machine_readable_posture_only() -> None:
    kernel = _m2n_kernel()

    _authorize_execute_reduce_readiness(kernel)

    projection = kernel.state.followup_final_answer_packet_readiness_projection
    assert "fixture_only_sufficiency_recheck_final_answer_deferred" in (
        projection["mandatory_caveats"]
    )
    assert "do_not_create_citation_eligibility_from_readiness" in (
        projection["prohibited_upgrades"]
    )
    assert projection["author_payload_created"] is False
    assert projection["not_role_consumption_payload"] is True


@pytest.mark.parametrize(
    "field",
    [
        "recheck_id",
        "intake_id",
        "execution_id",
        "sealed_candidate_id",
        "requirement_ids",
        "expected_source_classes",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
    ],
)
def test_readiness_reducer_rejects_mutated_binding_fields(field: str) -> None:
    kernel = _m2n_kernel()
    action = kernel.authorize_followup_final_answer_packet_readiness()
    result = _execute_readiness(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    if field in {"requirement_ids", "expected_source_classes"}:
        bad_state[field] = ["mutated"]
    else:
        bad_state[field] = f"mutated-{field}"

    with pytest.raises(RunKernelTransitionError, match=field):
        kernel.reduce(_observation_from_state(action, bad_state))


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("ledger", "EvidenceLedger digest mismatch"),
        ("sufficiency", "SufficiencyJudgment digest mismatch"),
        ("recheck", "recheck digest mismatch"),
    ],
)
def test_readiness_reducer_rejects_stale_digests(
    mutation: str,
    match: str,
) -> None:
    kernel = _m2n_kernel()
    action = kernel.authorize_followup_final_answer_packet_readiness()
    result = _execute_readiness(kernel, action=action)
    if mutation == "ledger":
        kernel.state.evidence_ledger.observation_refs.append(
            {"observation_id": "ag96i3o1:stale-ledger", "source": "test"}
        )
    elif mutation == "sufficiency":
        kernel.state.sufficiency_judgment_projection["digest_mutation"] = "test"
    else:
        kernel.state.followup_sufficiency_recheck_state["digest_mutation"] = "test"

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)


@pytest.mark.parametrize(
    ("ledger_projection", "match"),
    [
        ({}, "EvidenceLedger owner"),
        (
            {"owner": "RunKernel.EvidenceLedger", "canonical_state": False},
            "canonical EvidenceLedger",
        ),
    ],
)
def test_readiness_runtime_rejects_missing_or_noncanonical_ledger_projection(
    ledger_projection: dict[str, Any],
    match: str,
) -> None:
    kernel = _m2n_kernel()
    action = kernel.authorize_followup_final_answer_packet_readiness()

    with pytest.raises(PermissionError, match=match):
        execute_followup_final_answer_packet_readiness_action(
            action,
            followup_sufficiency_recheck_state=(
                kernel.state.followup_sufficiency_recheck_state
            ),
            sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
            evidence_ledger_projection=ledger_projection,
            followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        )


def test_readiness_runtime_rejects_missing_canonical_sufficiency_projection() -> None:
    kernel = _m2n_kernel()
    action = kernel.authorize_followup_final_answer_packet_readiness()

    with pytest.raises(PermissionError, match="canonical sufficiency owner"):
        execute_followup_final_answer_packet_readiness_action(
            action,
            followup_sufficiency_recheck_state=(
                kernel.state.followup_sufficiency_recheck_state
            ),
            sufficiency_judgment_projection={},
            evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
            followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        )


def test_readiness_runtime_rejects_missing_canonical_recheck_state() -> None:
    kernel = _m2n_kernel()
    action = kernel.authorize_followup_final_answer_packet_readiness()

    with pytest.raises(PermissionError, match="canonical recheck state"):
        execute_followup_final_answer_packet_readiness_action(
            action,
            followup_sufficiency_recheck_state={},
            sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
            evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
            followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("author_activation_allowed", True),
        ("citation_behavior_changed", True),
        ("citation_eligible", True),
        ("answer_ready", True),
        ("analyst_activation_allowed", True),
        ("economist_code_execution_allowed", True),
    ],
)
def test_readiness_reducer_rejects_boundary_spoofing(
    field: str,
    value: bool,
) -> None:
    kernel = _m2n_kernel()
    action = kernel.authorize_followup_final_answer_packet_readiness()
    result = _execute_readiness(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    bad_state[field] = value

    with pytest.raises(RunKernelTransitionError, match=field):
        kernel.reduce(_observation_from_state(action, bad_state))


def test_invalid_recheck_mode_intake_mode_and_packet_deferred_posture_rejected() -> None:
    kernel = _m2n_kernel()
    kernel.state.followup_sufficiency_recheck_state[
        "sufficiency_recheck_mode"
    ] = "live_recheck"
    with pytest.raises(RunKernelTransitionError, match="sufficiency recheck mode"):
        kernel.authorize_followup_final_answer_packet_readiness()

    kernel = _m2n_kernel()
    kernel.state.followup_sufficiency_recheck_state[
        "evidence_ledger_intake_mode"
    ] = "fixture_only_followup_intake"
    with pytest.raises(RunKernelTransitionError, match="AG-96I3M2 intake mode"):
        kernel.authorize_followup_final_answer_packet_readiness()

    kernel = _m2n_kernel()
    kernel.state.followup_sufficiency_recheck_state[
        "final_answer_packet_deferred"
    ] = False
    with pytest.raises(RunKernelTransitionError, match="packet-deferred"):
        kernel.authorize_followup_final_answer_packet_readiness()


def test_readiness_rejects_raw_private_sentinel_before_state_serialization() -> None:
    sentinel = "ag96i3o1-private-sentinel"
    kernel = _m2n_kernel()
    kernel.state.followup_sufficiency_recheck_state[
        "ag96i3m2_admission_review_candidate"
    ]["title"] = sentinel
    action = kernel.authorize_followup_final_answer_packet_readiness()

    with pytest.raises(PermissionError, match="private payload"):
        _execute_readiness(kernel, action=action)

    serialized = json.dumps(
        {
            "state": kernel.state.followup_final_answer_packet_readiness_state,
            "projection": kernel.state.followup_final_answer_packet_readiness_projection,
        },
        sort_keys=True,
    )
    assert sentinel not in serialized


def test_static_guards_keep_o1_closed_to_live_roles_and_orchestrator() -> None:
    module_paths = [
        ROOT / "core" / "followup_final_answer_packet_runtime.py",
        ROOT / "core" / "followup_runkernel_reducers.py",
    ]
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.prompts",
        "core.author_execution_runtime",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
        "subprocess",
        "os",
    }
    for path in module_paths:
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()
        assert _imports(path).isdisjoint(forbidden_imports)
        for forbidden in (
            "AnalystExecutor",
            "EconomistExecutor",
            "AuthorExecutor(",
            "execute_analyst",
            "execute_economist",
            "execute_author_action",
            "select_author_system_prompt",
            "format_citation",
        ):
            assert forbidden not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3o1" not in pipeline_source.casefold()
    assert "followup_final_answer_packet_readiness" not in pipeline_source


def _m2n_kernel(*, source_obligation_satisfied: bool = True) -> RunKernel:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    _execute_m2_intake(kernel)
    if not source_obligation_satisfied:
        kernel.state.followup_evidence_intake_state[
            "source_obligation_satisfied"
        ] = False
    action = kernel.authorize_followup_sufficiency_recheck()
    result = execute_followup_sufficiency_recheck_action(
        action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        prior_sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        sufficiency_handoff=kernel.state.followup_authorization_state.get(
            "sufficiency_handoff",
            {},
        ),
    )
    kernel.reduce(result.observation)
    return kernel


def _execute_readiness(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_final_answer_packet_readiness_action(
        action,
        followup_sufficiency_recheck_state=(
            kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )


def _authorize_execute_reduce_readiness(kernel: RunKernel) -> None:
    action = kernel.authorize_followup_final_answer_packet_readiness()
    result = _execute_readiness(kernel, action=action)
    kernel.reduce(result.observation)


def _observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_final_answer_packet_readiness_prepared",
        status="completed",
        payload={"followup_final_answer_packet_readiness_state": state},
    )


def _closed_surface_snapshot(kernel: RunKernel) -> dict[str, Any]:
    return {
        "search_judgment": deepcopy(kernel.state.search_judgment),
        "search_judgment_projection": deepcopy(kernel.state.search_judgment_projection),
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
        "followup_final_answer_packet_state": deepcopy(
            kernel.state.followup_final_answer_packet_state
        ),
        "followup_author_gate_state": deepcopy(kernel.state.followup_author_gate_state),
        "followup_author_observation_state": deepcopy(
            kernel.state.followup_author_observation_state
        ),
    }


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
