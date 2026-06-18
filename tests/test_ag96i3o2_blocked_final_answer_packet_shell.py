from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.final_answer_packet import FinalAnswerPacket
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import (
    AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE,
    AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE,
    execute_followup_blocked_final_answer_packet_shell_action,
    execute_followup_final_answer_packet_prepare_action,
    execute_followup_final_answer_packet_readiness_action,
)
from core.followup_sufficiency_recheck_runtime import (
    evidence_ledger_projection_digest,
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import (
    FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
)
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_o2_boundary_snapshot_unchanged,
    assert_o2_closed_surfaces_unchanged,
    snapshot_o2_boundary_state,
    snapshot_o2_closed_surfaces,
)
from tests.helpers.followup_fixture_spine import run_followup_through_execution
from tests.test_ag96i3m2_followup_evidence_intake_activation import (
    _execute_m2_intake,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "ag96i3o2-blocked-final-answer-packet-shell"


def test_o2_happy_path_installs_canonical_blocked_packet_shell() -> None:
    kernel = _m2n_o1_kernel()
    readiness_before = deepcopy(kernel.state.followup_final_answer_packet_readiness_state)
    readiness_projection_before = deepcopy(
        kernel.state.followup_final_answer_packet_readiness_projection
    )
    ledger_before = kernel.state.evidence_ledger.to_projection().to_dict()
    sufficiency_before = deepcopy(kernel.state.sufficiency_judgment_projection)
    recheck_before = deepcopy(kernel.state.followup_sufficiency_recheck_state)
    before = snapshot_o2_closed_surfaces(kernel)

    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    readiness = kernel.state.followup_final_answer_packet_readiness_state
    recheck = kernel.state.followup_sufficiency_recheck_state

    assert action.stage == FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE
    assert action.inputs["blocked_final_answer_packet_mode"] == (
        AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
    )
    assert action.inputs["packet_preparation_readiness_mode"] == (
        AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
    )
    assert action.inputs["packet_preparation_readiness_id"] == (
        readiness["packet_preparation_readiness_id"]
    )
    assert action.inputs["readiness_observation_id"] == readiness["observation_id"]
    assert action.inputs["followup_final_answer_packet_readiness_digest"]
    assert action.inputs["followup_sufficiency_recheck_id"] == recheck["recheck_id"]
    assert action.inputs["followup_sufficiency_recheck_observation_id"] == (
        recheck["observation_id"]
    )

    result = _execute_o2(kernel, action=action)
    kernel.reduce(result.observation)

    shell = kernel.state.followup_blocked_final_answer_packet_shell_state
    projection = kernel.state.followup_blocked_final_answer_packet_shell_projection
    packet = kernel.state.final_answer_packet
    assert before["final_answer_packet"] == {}
    assert shell["owner"] == "RunKernel.FollowupBlockedFinalAnswerPacketShell"
    assert shell["canonical_state"] is True
    assert projection["owner"] == "RunKernel.FollowupBlockedFinalAnswerPacketShell"
    assert projection["canonical_state"] is True
    assert packet["owner"] == "RunKernel.FinalAnswerPacket"
    assert packet["canonical_state"] is True
    assert packet["blocked_final_answer_packet_mode"] == (
        AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
    )
    assert packet["packet_preparation_readiness_id"] == (
        readiness_before["packet_preparation_readiness_id"]
    )
    assert packet["readiness_status"] == "blocked"
    assert "insufficient_authorized" not in packet["readiness_status"]
    assert packet["final_answer_allowed"] is False
    assert packet["answer_ready"] is False
    assert packet["evidence_allowed"] == []
    assert packet["evidence_excluded"] == []
    assert packet["author_evidence"] == []
    assert packet["citation_eligible"] == []
    assert packet["citation_ineligible"] == []
    assert packet["author_input_refs"] == {}
    assert packet["final_evidence_selected"] is False
    assert packet["citation_eligible_flag"] is False
    assert packet["citations_rendered"] is False
    assert packet["citation_rendering_changed"] is False
    assert packet["citation_formatter_invoked"] is False
    assert packet["author_payload_created"] is False
    assert packet["author_activation_allowed"] is False
    assert packet["author_execution_deferred"] is True
    assert packet["analyst_activation_allowed"] is False
    assert packet["analyst_handoff_created"] is False
    assert packet["economist_activation_allowed"] is False
    assert packet["economist_handoff_created"] is False
    assert packet["economist_code_execution_allowed"] is False
    assert packet["prompt_behavior_changed"] is False
    assert packet["product_answer_behavior_changed"] is False
    assert packet["live_validation_not_run"] is True
    assert packet["not_role_consumption_payload"] is True
    assert packet["final_evidence_selection_deferred"] is True
    assert packet["citation_eligibility_deferred"] is True
    assert "ag96i3o2_blocked_packet_shell" in packet["readiness_reasons"]
    assert "final_evidence_selection_deferred" in packet["readiness_reasons"]
    assert "citation_eligibility_deferred" in packet["readiness_reasons"]
    assert "role_handoffs_closed" in packet["readiness_reasons"]
    assert "final_evidence_refs" not in packet
    assert "citation_eligible_source_ids" not in packet
    assert "citation_eligibility_refs" not in packet
    assert "author_payload_ref" not in packet
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.followup_final_answer_packet_readiness_state == (
        readiness_before
    )
    assert kernel.state.followup_final_answer_packet_readiness_projection == (
        readiness_projection_before
    )
    assert kernel.state.evidence_ledger.to_projection().to_dict() == ledger_before
    assert kernel.state.sufficiency_judgment_projection == sufficiency_before
    assert kernel.state.followup_sufficiency_recheck_state == recheck_before
    assert kernel.state.followup_final_answer_packet_state == {}
    assert kernel.state.followup_author_gate_state == {}
    assert kernel.state.followup_author_observation_state == {}
    assert projection["packet_projection"] == packet
    assert kernel.state.projections[FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE] == (
        projection
    )
    assert kernel.state.followup_blocked_final_answer_packet_shell_history == [
        projection
    ]
    assert_o2_closed_surfaces_unchanged(kernel, before)


def test_o2_shell_is_not_structurally_role_consumable() -> None:
    kernel = _m2n_o1_kernel()
    _consume_o2(kernel)
    packet = kernel.state.final_answer_packet

    blocked_packet = FinalAnswerPacket(
        packet_id=packet["packet_id"],
        final_answer_allowed=packet["final_answer_allowed"],
        readiness_status=packet["readiness_status"],
    )
    with pytest.raises(ValueError, match="blocked FinalAnswerPacket"):
        blocked_packet.to_author_input_payload(
            prompt="fixture prompt",
            author_system_prompt_key="fixture",
            author_effort="low",
        )
    with pytest.raises(RunKernelTransitionError, match="reduced follow-up FinalAnswerPacket"):
        kernel.authorize_followup_author_gate()

    assert kernel.state.followup_author_gate_state == {}
    assert kernel.state.followup_author_observation_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("readiness_status", "insufficient_authorized", "readiness_status"),
        ("readiness_status", "author_ready", "readiness_status"),
        ("final_answer_allowed", True, "final_answer_allowed"),
    ],
)
def test_o2_reducer_rejects_attempted_packet_posture_upgrade(
    field: str,
    value: Any,
    match: str,
) -> None:
    kernel = _m2n_o1_kernel()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    bad_state["packet_projection"][field] = value

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(_observation_from_state(action, bad_state))

    assert kernel.state.final_answer_packet == {}
    assert kernel.state.followup_blocked_final_answer_packet_shell_state == {}


def test_legacy_i2e_prepare_rejects_after_o2_shell_activation() -> None:
    kernel = _m2n_o1_kernel()
    _consume_o2(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3O2 blocked packet shell"):
        kernel.authorize_followup_final_answer_packet_prepare()

    assert kernel.state.final_answer_authority_projection == {}


def test_pre_authorized_legacy_i2e_reduce_rejects_after_o2_shell_activation() -> None:
    kernel = _m2n_o1_kernel()
    o2_action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    legacy_action = kernel.authorize_followup_final_answer_packet_prepare()
    o2_result = _execute_o2(kernel, action=o2_action)
    legacy_result = execute_followup_final_answer_packet_prepare_action(
        legacy_action,
        followup_sufficiency_recheck_state=(
            kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )

    kernel.reduce(o2_result.observation)
    snapshot = snapshot_o2_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="cannot reduce after AG-96I3O2"):
        kernel.reduce(legacy_result.observation)

    assert_o2_boundary_snapshot_unchanged(kernel, snapshot)

    packet = kernel.state.final_answer_packet
    assert packet["owner"] == "RunKernel.FinalAnswerPacket"
    assert packet["canonical_state"] is True
    assert packet["readiness_status"] == "blocked"
    assert packet["final_answer_allowed"] is False
    assert packet["answer_ready"] is False


@pytest.mark.parametrize(
    "field",
    [
        "blocked_final_answer_packet_shell_id",
        "packet_preparation_readiness_id",
        "readiness_observation_id",
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
def test_o2_reducer_rejects_mutated_observation_bindings(field: str) -> None:
    kernel = _m2n_o1_kernel()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
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
        ("readiness", "readiness digest mismatch"),
    ],
)
def test_o2_reducer_rejects_stale_digests(mutation: str, match: str) -> None:
    kernel = _m2n_o1_kernel()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    if mutation == "ledger":
        kernel.state.evidence_ledger.observation_refs.append(
            {"observation_id": "ag96i3o2:stale-ledger", "source": "test"}
        )
    elif mutation == "sufficiency":
        kernel.state.sufficiency_judgment_projection["digest_mutation"] = "test"
    elif mutation == "recheck":
        kernel.state.followup_sufficiency_recheck_state["digest_mutation"] = "test"
    else:
        kernel.state.followup_final_answer_packet_readiness_state[
            "digest_mutation"
        ] = "test"

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)


@pytest.mark.parametrize(
    ("surface", "mutator", "match"),
    [
        (
            "ledger",
            lambda kernel: kernel.state.evidence_ledger.candidates.clear(),
            "EvidenceLedger digest mismatch",
        ),
        (
            "sufficiency",
            lambda kernel: kernel.state.sufficiency_judgment_projection.update(
                {"canonical_state": False}
            ),
            "canonical sufficiency",
        ),
        (
            "recheck",
            lambda kernel: kernel.state.followup_sufficiency_recheck_state.update(
                {"canonical_state": False}
            ),
            "canonical recheck state",
        ),
        (
            "readiness",
            lambda kernel: kernel.state.followup_final_answer_packet_readiness_state.update(
                {"canonical_state": False}
            ),
            "canonical readiness state",
        ),
    ],
)
def test_o2_rejects_missing_or_noncanonical_inputs(
    surface: str,
    mutator: Any,
    match: str,
) -> None:
    kernel = _m2n_o1_kernel()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    mutator(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)

    assert surface


def test_o2_reducer_rejects_forbidden_refs_and_raw_private_payloads() -> None:
    kernel = _m2n_o1_kernel()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    bad_state["final_evidence_refs"] = [{"source_id": "forbidden"}]

    with pytest.raises(RunKernelTransitionError, match="final_evidence_refs"):
        kernel.reduce(_observation_from_state(action, bad_state))

    kernel = _m2n_o1_kernel()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    bad_state["packet_projection"]["author_payload_ref"] = {}
    with pytest.raises(RunKernelTransitionError, match="author_payload_ref"):
        kernel.reduce(_observation_from_state(action, bad_state))

    kernel = _m2n_o1_kernel()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    bad_state["private_note"] = "ag96i3o2-private-sentinel"
    with pytest.raises(RunKernelTransitionError, match="raw/private"):
        kernel.reduce(_observation_from_state(action, bad_state))


def test_o2_caller_packet_projection_cannot_override_canonical_rebuild() -> None:
    kernel = _m2n_o1_kernel()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["packet_projection"]["mandatory_caveats"] = []
    spoofed["packet_projection"]["prohibited_upgrades"] = []

    kernel.reduce(_observation_from_state(action, spoofed))

    packet = kernel.state.final_answer_packet
    assert packet["mandatory_caveats"]
    assert "do_not_treat_blocked_shell_as_author_input" in (
        packet["prohibited_upgrades"]
    )


def test_duplicate_o2_activation_for_same_readiness_rejects() -> None:
    kernel = _m2n_o1_kernel()
    _consume_o2(kernel)

    with pytest.raises(RunKernelTransitionError, match="already activated"):
        kernel.authorize_followup_blocked_final_answer_packet_shell()


def test_o2_authorization_binds_every_required_identity_and_digest() -> None:
    kernel = _m2n_o1_kernel()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    readiness = kernel.state.followup_final_answer_packet_readiness_state
    recheck = kernel.state.followup_sufficiency_recheck_state
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()

    for field in (
        "blocked_final_answer_packet_shell_id",
        "packet_preparation_readiness_id",
        "readiness_observation_id",
        "recheck_id",
        "followup_sufficiency_recheck_id",
        "followup_sufficiency_recheck_observation_id",
        "intake_id",
        "followup_evidence_intake_id",
        "followup_evidence_intake_observation_id",
        "execution_id",
        "followup_execution_id",
        "followup_execution_observation_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "requirement_ids",
        "expected_source_classes",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
        "packet_preparation_readiness_mode",
        "blocked_final_answer_packet_mode",
        "evidence_ledger_projection_digest",
        "sufficiency_judgment_digest",
        "followup_sufficiency_recheck_digest",
        "followup_final_answer_packet_readiness_digest",
    ):
        assert action.inputs[field] not in (None, "", [], {})
    assert action.inputs["packet_preparation_readiness_id"] == (
        readiness["packet_preparation_readiness_id"]
    )
    assert action.inputs["readiness_observation_id"] == readiness["observation_id"]
    assert action.inputs["recheck_id"] == recheck["recheck_id"]
    assert action.inputs["evidence_ledger_projection_digest"] == (
        evidence_ledger_projection_digest(ledger)
    )


def test_static_guards_keep_o2_closed_to_live_roles_citations_and_orchestrator() -> None:
    runtime_path = ROOT / "core" / "followup_final_answer_packet_runtime.py"
    reducer_path = ROOT / "core" / "followup_runkernel_reducers.py"
    module_paths = [runtime_path, reducer_path]
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
        assert imported_modules(path).isdisjoint(forbidden_imports)
        for forbidden in (
            "AuthorExecutor(",
            "AnalystExecutor",
            "EconomistExecutor",
            "execute_author_action",
            "execute_analyst",
            "execute_economist",
            "select_author_system_prompt",
            "format_citation",
            "subprocess.",
        ):
            assert forbidden not in source

    runtime_source = runtime_path.read_text(encoding="utf-8")
    o2_builder = runtime_source.split(
        "def build_followup_blocked_final_answer_packet_shell_record",
        1,
    )[1].split("def followup_projection_digest", 1)[0]
    assert "_eligible_final_evidence_refs" not in o2_builder
    assert "build_followup_final_answer_packet_record" not in o2_builder

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3o2" not in pipeline_source.casefold()
    assert "followup_blocked_final_answer_packet_shell" not in pipeline_source


def _m2n_o1_kernel() -> RunKernel:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    _execute_m2_intake(kernel)
    recheck_action = kernel.authorize_followup_sufficiency_recheck()
    recheck_result = execute_followup_sufficiency_recheck_action(
        recheck_action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        prior_sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        sufficiency_handoff=kernel.state.followup_authorization_state.get(
            "sufficiency_handoff",
            {},
        ),
    )
    kernel.reduce(recheck_result.observation)
    readiness_action = kernel.authorize_followup_final_answer_packet_readiness()
    readiness_result = execute_followup_final_answer_packet_readiness_action(
        readiness_action,
        followup_sufficiency_recheck_state=(
            kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    kernel.reduce(readiness_result.observation)
    return kernel


def _execute_o2(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_blocked_final_answer_packet_shell_action(
        action,
        followup_final_answer_packet_readiness_state=(
            kernel.state.followup_final_answer_packet_readiness_state
        ),
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )


def _consume_o2(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_blocked_final_answer_packet_shell_prepared",
        status="completed",
        payload={"followup_blocked_final_answer_packet_shell_state": state},
    )
