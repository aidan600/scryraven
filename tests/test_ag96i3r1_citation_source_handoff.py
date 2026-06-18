from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.followup_citation_source_handoff_runtime import (
    AG96I3R1_CITATION_SOURCE_HANDOFF_MODE,
    execute_followup_citation_source_handoff_action,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import (
    execute_followup_final_answer_packet_prepare_action,
)
from core.run_kernel import (
    FOLLOWUP_CITATION_SOURCE_HANDOFF_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
)
from tests.test_ag96i3p1_final_evidence_selection import (
    OFFICIAL_CANDIDATE_ID,
    OFFICIAL_REQUIREMENT_ID,
    _add_secondary_candidate,
    _assert_no_sensitive_payload,
    _consume_p1,
    _execute_o2,
    _execute_p1,
    _kernel_through_o1,
    _kernel_through_o2,
    _resequence_action_and_observation,
    _stale_legacy_i2e_action,
)
from tests.test_ag96i3q1_citation_eligibility import (
    _consume_q1,
    _execute_q1,
    _inject_external_stale_action_and_observation,
    _kernel_through_q1,
)

ROOT = Path(__file__).resolve().parents[1]


def test_r1_happy_path_creates_q1_bound_source_handoff_only() -> None:
    kernel = _kernel_through_q1()
    q1_packet = deepcopy(kernel.state.final_answer_packet)

    action = kernel.authorize_followup_citation_source_handoff()
    assert action.stage == FOLLOWUP_CITATION_SOURCE_HANDOFF_STAGE
    assert action.inputs["citation_source_handoff_mode"] == (
        AG96I3R1_CITATION_SOURCE_HANDOFF_MODE
    )

    result = _execute_r1(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_citation_source_handoff_state
    projection = kernel.state.followup_citation_source_handoff_projection
    history = kernel.state.followup_citation_source_handoff_history
    eligible = q1_packet["citation_eligible"]
    assert state["owner"] == "RunKernel.FollowupCitationSourceHandoff"
    assert state["canonical_state"] is True
    assert state["trace_only"] is False
    assert state["storage_only"] is False
    assert projection["owner"] == "RunKernel.FollowupCitationSourceHandoff"
    assert projection["canonical_state"] is True
    assert history == [projection]
    assert kernel.state.projections[FOLLOWUP_CITATION_SOURCE_HANDOFF_STAGE] == (
        projection
    )

    assert state["packet_id"] == q1_packet["packet_id"]
    assert state["citation_eligibility_id"] == (
        kernel.state.followup_citation_eligibility_state["citation_eligibility_id"]
    )
    assert state["citation_eligible_source_ids"] == [
        item["source_id"] for item in eligible
    ]
    assert [item["citation_id"] for item in state["citation_eligibility_refs"]] == [
        item["citation_id"] for item in eligible
    ]
    assert len(state["source_identity_records"]) == len(eligible)
    identity = state["source_identity_records"][0]
    citation = eligible[0]
    assert identity["citation_id"] == citation["citation_id"]
    assert identity["evidence_id"] == citation["evidence_id"]
    assert identity["candidate_id"] == OFFICIAL_CANDIDATE_ID
    assert identity["source_id"] == OFFICIAL_CANDIDATE_ID
    assert identity["requirement_id"] == OFFICIAL_REQUIREMENT_ID
    assert identity["source_obligation_id"] == citation["source_obligation_id"]
    assert identity["url"] == citation["url"]
    assert identity["domain"] == citation["domain"]
    assert identity["title"] == citation["title"]
    assert identity["source_class"] == citation["source_class"]
    assert identity["source_tier"] == citation["source_tier"]
    assert identity["packet_local"] is True
    assert identity["derived_from_q1"] is True
    assert identity["source_identity_position"] == 1

    assert kernel.state.final_answer_packet == q1_packet
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.final_answer_packet["author_input_refs"] == {}
    assert "author_payload_ref" not in kernel.state.final_answer_packet
    assert kernel.state.final_answer_packet["readiness_status"] == "blocked"
    assert kernel.state.final_answer_packet["final_answer_allowed"] is False
    assert kernel.state.final_answer_packet["answer_ready"] is False
    assert state["canonical_final_answer_packet_mutated"] is False
    assert state["citations_rendered"] is False
    assert state["citation_formatter_invoked"] is False
    assert state["ordered_product_source_output_created"] is False
    assert state["author_input_refs"] == {}
    assert state["author_payload_created"] is False
    assert state["author_activation_allowed"] is False
    assert state["analyst_activation_allowed"] is False
    assert state["economist_activation_allowed"] is False
    assert state["not_role_consumption_payload"] is True

    with pytest.raises(RunKernelTransitionError, match="FinalAnswerPacket"):
        kernel.authorize_followup_author_gate()
    _assert_no_sensitive_payload(state)
    _assert_no_sensitive_payload(projection)


def test_r1_uses_only_q1_eligible_packet_records() -> None:
    kernel = _kernel_through_o2(mutator=_add_secondary_candidate)
    _consume_p1(kernel)
    _consume_q1(kernel)
    packet = deepcopy(kernel.state.final_answer_packet)

    _consume_r1(kernel)

    identities = kernel.state.followup_citation_source_handoff_state[
        "source_identity_records"
    ]
    assert [item["candidate_id"] for item in packet["evidence_allowed"]] == [
        OFFICIAL_CANDIDATE_ID
    ]
    assert [item["candidate_id"] for item in packet["evidence_excluded"]] == [
        "secondary_context_2026"
    ]
    assert [item["candidate_id"] for item in packet["citation_eligible"]] == [
        OFFICIAL_CANDIDATE_ID
    ]
    assert [item["candidate_id"] for item in identities] == [OFFICIAL_CANDIDATE_ID]
    assert "secondary_context_2026" not in {
        item["candidate_id"] for item in identities
    }
    assert kernel.state.followup_citation_source_handoff_state[
        "citation_eligible_source_ids"
    ] == [OFFICIAL_CANDIDATE_ID]
    _assert_no_sensitive_payload(identities)


def test_r1_keeps_rendering_output_and_role_surfaces_closed() -> None:
    kernel = _kernel_through_q1()

    _consume_r1(kernel)

    packet = kernel.state.final_answer_packet
    state = kernel.state.followup_citation_source_handoff_state
    projection = kernel.state.followup_citation_source_handoff_projection
    forbidden_fields = (
        "rendered_citation",
        "rendered_citations",
        "formatted_citation",
        "formatted_citations",
        "ordered_sources",
        "ordered_product_source_output",
        "final_answer_text",
        "prompt",
        "prompt_text",
        "author_payload_ref",
        "author_input_payload",
        "analyst_handoff_ref",
        "economist_handoff_ref",
    )
    for surface in (state, projection, packet):
        for field in forbidden_fields:
            assert field not in surface
    assert state["citations_rendered"] is False
    assert state["citation_formatter_invoked"] is False
    assert state["citation_rendering_deferred"] is True
    assert state["prompt_behavior_changed"] is False
    assert packet["citations_rendered"] is False
    assert packet["citation_formatter_invoked"] is False
    assert kernel.state.final_answer_authority_projection == {}
    assert kernel.state.followup_final_answer_packet_state == {}
    assert kernel.state.followup_author_gate_state == {}
    assert kernel.state.followup_author_observation_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert getattr(kernel.state, "analyst_author_handoff_state", {}) == {}
    assert getattr(kernel.state, "economist_handoff_state", {}) == {}


def test_r1_authorization_binds_required_ids_modes_and_digests() -> None:
    kernel = _kernel_through_q1()

    action = kernel.authorize_followup_citation_source_handoff()
    inputs = action.inputs

    for field in (
        "citation_source_handoff_id",
        "citation_eligibility_id",
        "citation_eligibility_observation_id",
        "followup_citation_eligibility_digest",
        "final_evidence_selection_id",
        "final_evidence_selection_observation_id",
        "followup_final_evidence_selection_digest",
        "blocked_final_answer_packet_shell_id",
        "blocked_final_answer_packet_shell_observation_id",
        "blocked_final_answer_packet_shell_digest",
        "blocked_final_answer_packet_digest",
        "packet_preparation_readiness_id",
        "readiness_observation_id",
        "followup_final_answer_packet_readiness_digest",
        "followup_sufficiency_recheck_id",
        "recheck_id",
        "followup_sufficiency_recheck_digest",
        "followup_evidence_intake_id",
        "intake_id",
        "execution_id",
        "followup_execution_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "evidence_ledger_projection_digest",
        "sufficiency_judgment_digest",
        "current_final_answer_packet_digest",
    ):
        assert inputs[field] not in (None, "", [], {})
    assert inputs["requirement_ids"] == ["requirement_official_current"]
    assert inputs["expected_source_classes"] == [
        "official_government",
        "official_current_rules",
    ]
    assert inputs["citation_source_handoff_mode"] == (
        AG96I3R1_CITATION_SOURCE_HANDOFF_MODE
    )


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("ledger", "EvidenceLedger digest mismatch"),
        ("sufficiency", "SufficiencyJudgment digest mismatch"),
        ("recheck", "recheck digest mismatch"),
        ("readiness", "O1 readiness digest mismatch"),
        ("shell", "O2 shell digest mismatch"),
        ("p1", "P1 digest mismatch"),
        ("q1", "Q1 digest mismatch"),
        ("packet", "FinalAnswerPacket digest mismatch"),
    ],
)
def test_r1_reducer_rejects_stale_digests(
    mutation: str,
    match: str,
) -> None:
    kernel = _kernel_through_q1()
    action = kernel.authorize_followup_citation_source_handoff()
    result = _execute_r1(kernel, action=action)
    if mutation == "ledger":
        kernel.state.evidence_ledger.observation_refs.append(
            {"observation_id": "ag96i3r1:stale-ledger", "source": "test"}
        )
    elif mutation == "sufficiency":
        kernel.state.sufficiency_judgment_projection["digest_mutation"] = "test"
    elif mutation == "recheck":
        kernel.state.followup_sufficiency_recheck_state["digest_mutation"] = "test"
    elif mutation == "readiness":
        kernel.state.followup_final_answer_packet_readiness_state[
            "digest_mutation"
        ] = "test"
    elif mutation == "shell":
        kernel.state.followup_blocked_final_answer_packet_shell_state[
            "digest_mutation"
        ] = "test"
    elif mutation == "p1":
        kernel.state.followup_final_evidence_selection_state[
            "digest_mutation"
        ] = "test"
    elif mutation == "q1":
        kernel.state.followup_citation_eligibility_state[
            "digest_mutation"
        ] = "test"
    else:
        kernel.state.final_answer_packet["digest_mutation"] = "test"
    snapshot = _r1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)

    _assert_r1_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("citation_source_handoff_id", "mutated-handoff"),
        ("citation_eligibility_id", "mutated-eligibility"),
        ("citation_eligibility_observation_id", "mutated-q1-observation"),
        ("final_evidence_selection_id", "mutated-selection"),
        ("blocked_final_answer_packet_shell_id", "mutated-shell"),
        ("packet_preparation_readiness_id", "mutated-readiness"),
        ("recheck_id", "mutated-recheck"),
        ("intake_id", "mutated-intake"),
        ("execution_id", "mutated-execution"),
        ("sealed_candidate_id", "mutated-candidate"),
        ("requirement_ids", ["mutated-requirement"]),
        ("expected_source_classes", ["mutated-class"]),
        ("provider_job_kind", "mutated-provider"),
        ("component_id", "mutated-component"),
        ("source_obligation_id", "mutated-obligation"),
    ],
)
def test_r1_reducer_rejects_mutated_binding_fields(
    field: str,
    value: Any,
) -> None:
    kernel = _kernel_through_q1()
    action = kernel.authorize_followup_citation_source_handoff()
    result = _execute_r1(kernel, action=action)
    bad_state = deepcopy(result.record.to_dict())
    bad_state[field] = value

    with pytest.raises(RunKernelTransitionError, match=field):
        kernel.reduce(_r1_observation_from_state(action, bad_state))

    assert kernel.state.followup_citation_source_handoff_state == {}


def test_r1_missing_noncanonical_prerequisites_reject() -> None:
    kernel = _kernel_through_q1()
    kernel.state.followup_citation_eligibility_state["canonical_state"] = False

    with pytest.raises(RunKernelTransitionError, match="canonical Q1 state"):
        kernel.authorize_followup_citation_source_handoff()

    kernel = _kernel_through_q1()
    kernel.state.followup_citation_eligibility_projection = {}
    with pytest.raises(RunKernelTransitionError, match="Q1 projection"):
        kernel.authorize_followup_citation_source_handoff()

    kernel = _kernel_through_q1()
    kernel.state.followup_citation_eligibility_history = []
    with pytest.raises(RunKernelTransitionError, match="Q1 history"):
        kernel.authorize_followup_citation_source_handoff()

    kernel = _kernel_through_q1()
    kernel.state.final_answer_packet["canonical_state"] = False
    with pytest.raises(RunKernelTransitionError, match="canonical FinalAnswerPacket"):
        kernel.authorize_followup_citation_source_handoff()


def test_r1_reducer_rebuilds_handoff_and_ignores_caller_records() -> None:
    kernel = _kernel_through_q1()
    action = kernel.authorize_followup_citation_source_handoff()
    result = _execute_r1(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["source_identity_records"] = [
        {**spoofed["source_identity_records"][0], "source_id": "spoofed"}
    ]
    spoofed["citation_eligible_source_ids"] = ["spoofed"]

    kernel.reduce(_r1_observation_from_state(action, spoofed))

    state = kernel.state.followup_citation_source_handoff_state
    assert state["source_identity_records"][0]["source_id"] == (
        OFFICIAL_CANDIDATE_ID
    )
    assert state["citation_eligible_source_ids"] == [OFFICIAL_CANDIDATE_ID]


def test_r1_malformed_observation_rejects_before_bookkeeping_or_mutation() -> None:
    kernel = _kernel_through_q1()
    action = kernel.authorize_followup_citation_source_handoff()
    snapshot = _r1_state_snapshot(kernel)
    bad_observation = Observation.from_action(
        action,
        observation_type="followup_citation_source_handoff_prepared",
        status="completed",
        payload={},
    )

    with pytest.raises(RunKernelTransitionError, match="requires followup"):
        kernel.reduce(bad_observation)

    _assert_r1_snapshot_unchanged(kernel, snapshot)


def test_duplicate_r1_activation_for_same_q1_packet_rejects() -> None:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)

    with pytest.raises(RunKernelTransitionError, match="already activated"):
        kernel.authorize_followup_citation_source_handoff()


def test_pre_authorized_duplicate_r1_reduce_rejects_after_r1() -> None:
    kernel = _kernel_through_q1()
    first_action = kernel.authorize_followup_citation_source_handoff()
    first_result = _execute_r1(kernel, action=first_action)
    duplicate_action = kernel.authorize_followup_citation_source_handoff()
    duplicate_result = _execute_r1(kernel, action=duplicate_action)

    kernel.reduce(first_result.observation)
    snapshot = _r1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match="duplicate|AG-96I3R1"):
        kernel.reduce(duplicate_result.observation)

    _assert_r1_snapshot_unchanged(kernel, snapshot)


def test_stale_legacy_i2e_reduce_rejects_after_r1_without_state_change() -> None:
    kernel = _kernel_through_q1()
    legacy_kernel = _kernel_through_o2()
    legacy_action = _stale_legacy_i2e_action(legacy_kernel)
    legacy_result = execute_followup_final_answer_packet_prepare_action(
        legacy_action,
        followup_sufficiency_recheck_state=(
            legacy_kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=(
            legacy_kernel.state.sufficiency_judgment_projection
        ),
        evidence_ledger_projection=(
            legacy_kernel.state.evidence_ledger.to_projection().to_dict()
        ),
        followup_evidence_intake_state=(
            legacy_kernel.state.followup_evidence_intake_state
        ),
    )
    _consume_r1(kernel)
    _stale_action, stale_observation = _inject_external_stale_action_and_observation(
        kernel,
        legacy_kernel,
        legacy_action,
        legacy_result.observation,
    )
    snapshot = _r1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3R1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    _assert_r1_snapshot_unchanged(kernel, snapshot)


def test_stale_o2_reduce_rejects_after_r1_without_state_change() -> None:
    kernel = _kernel_through_o1()
    stale_o2_action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    stale_o2_result = _execute_o2(kernel, action=stale_o2_action)
    kernel.reduce(stale_o2_result.observation)
    _consume_p1(kernel)
    _consume_q1(kernel)
    _consume_r1(kernel)
    _stale_action, stale_observation = _resequence_action_and_observation(
        kernel,
        stale_o2_action,
        stale_o2_result.observation,
    )
    snapshot = _r1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3R1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    _assert_r1_snapshot_unchanged(kernel, snapshot)


def test_stale_p1_reduce_rejects_after_r1_without_state_change() -> None:
    kernel = _kernel_through_o2()
    stale_p1_action = kernel.authorize_followup_final_evidence_selection()
    stale_p1_result = _execute_p1(kernel, action=stale_p1_action)
    kernel.reduce(stale_p1_result.observation)
    _consume_q1(kernel)
    _consume_r1(kernel)
    _stale_action, stale_observation = _resequence_action_and_observation(
        kernel,
        stale_p1_action,
        stale_p1_result.observation,
    )
    snapshot = _r1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3R1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    _assert_r1_snapshot_unchanged(kernel, snapshot)


def test_stale_q1_reduce_rejects_after_r1_without_state_change() -> None:
    kernel = _kernel_through_q1()
    source_kernel = _kernel_through_p1_for_stale_q1()
    stale_q1_action = source_kernel.authorize_followup_citation_eligibility()
    stale_q1_result = _execute_q1(source_kernel, action=stale_q1_action)

    _consume_r1(kernel)
    _stale_action, stale_observation = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_q1_action,
        stale_q1_result.observation,
    )
    snapshot = _r1_state_snapshot(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3R1"):
        kernel.reduce(stale_observation)

    assert _stale_action
    _assert_r1_snapshot_unchanged(kernel, snapshot)


def test_static_guards_keep_r1_closed_to_rendering_roles_provider_and_pipeline() -> None:
    runtime_path = ROOT / "core" / "followup_citation_source_handoff_runtime.py"
    reducer_path = ROOT / "core" / "followup_runkernel_reducers.py"
    run_kernel_path = ROOT / "core" / "run_kernel.py"
    for path in (runtime_path, reducer_path, run_kernel_path):
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()

    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.prompts",
        "core.author_execution_runtime",
        "core.final_answer_runtime_assembly",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
        "subprocess",
        "os",
    }
    assert _imports(runtime_path).isdisjoint(forbidden_imports)
    runtime_source = runtime_path.read_text(encoding="utf-8")
    assert "format_citation(" not in runtime_source
    assert "render_citation(" not in runtime_source
    assert "derive_author_input_payload(" not in runtime_source
    assert "build_final_answer_authority_projection(" not in runtime_source

    reducer_source = reducer_path.read_text(encoding="utf-8")
    r1_reducer_section = reducer_source.split(
        "def validate_followup_citation_source_handoff_observation_binding",
        1,
    )[1].split("def validate_followup_author_gate_observation_binding", 1)[0]
    for forbidden in (
        "format_citation(",
        "render_citation(",
        "derive_author_input_payload(",
        "build_final_answer_authority_projection(",
        "AuthorExecutor(",
        "AnalystExecutor",
        "EconomistExecutor",
    ):
        assert forbidden not in r1_reducer_section

    run_kernel_source = run_kernel_path.read_text(encoding="utf-8")
    r1_authorize_section = run_kernel_source.split(
        "def authorize_followup_citation_source_handoff",
        1,
    )[1].split("def authorize_followup_final_answer_packet_prepare", 1)[0]
    r1_reduce_section = run_kernel_source.split(
        "elif action.action_type is ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF:",
        1,
    )[1].split(
        "elif (",
        1,
    )[0]
    for forbidden in (
        "format_citation(",
        "render_citation(",
        "derive_author_input_payload(",
        "build_final_answer_authority_projection(",
        "AuthorExecutor(",
        "AnalystExecutor",
        "EconomistExecutor",
    ):
        assert forbidden not in r1_authorize_section
        assert forbidden not in r1_reduce_section

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3r1" not in pipeline_source.casefold()
    assert "followup_citation_source_handoff" not in pipeline_source


def _execute_r1(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_citation_source_handoff_action(
        action,
        followup_citation_eligibility_state=(
            kernel.state.followup_citation_eligibility_state
        ),
        followup_citation_eligibility_projection=(
            kernel.state.followup_citation_eligibility_projection
        ),
        followup_citation_eligibility_history=(
            kernel.state.followup_citation_eligibility_history
        ),
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=(
            kernel.state.final_answer_authority_projection
        ),
        followup_final_evidence_selection_state=(
            kernel.state.followup_final_evidence_selection_state
        ),
        followup_final_evidence_selection_projection=(
            kernel.state.followup_final_evidence_selection_projection
        ),
        followup_final_evidence_selection_history=(
            kernel.state.followup_final_evidence_selection_history
        ),
        followup_blocked_final_answer_packet_shell_state=(
            kernel.state.followup_blocked_final_answer_packet_shell_state
        ),
        followup_blocked_final_answer_packet_shell_projection=(
            kernel.state.followup_blocked_final_answer_packet_shell_projection
        ),
        followup_blocked_final_answer_packet_shell_history=(
            kernel.state.followup_blocked_final_answer_packet_shell_history
        ),
        followup_final_answer_packet_readiness_state=(
            kernel.state.followup_final_answer_packet_readiness_state
        ),
        followup_final_answer_packet_readiness_projection=(
            kernel.state.followup_final_answer_packet_readiness_projection
        ),
        followup_final_answer_packet_readiness_history=(
            kernel.state.followup_final_answer_packet_readiness_history
        ),
        followup_sufficiency_recheck_state=(
            kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=(
            kernel.state.sufficiency_judgment_projection
        ),
        evidence_ledger_projection=(
            kernel.state.evidence_ledger.to_projection().to_dict()
        ),
        followup_evidence_intake_state=(
            kernel.state.followup_evidence_intake_state
        ),
    )


def _consume_r1(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_citation_source_handoff()
    result = _execute_r1(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _r1_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_citation_source_handoff_prepared",
        status="completed",
        payload={"followup_citation_source_handoff_state": state},
    )


def _kernel_through_p1_for_stale_q1() -> RunKernel:
    kernel = _kernel_through_o2()
    _consume_p1(kernel)
    return kernel


def _r1_state_snapshot(kernel: RunKernel) -> dict[str, Any]:
    return {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "followup_citation_source_handoff_state": deepcopy(
            kernel.state.followup_citation_source_handoff_state
        ),
        "followup_citation_source_handoff_projection": deepcopy(
            kernel.state.followup_citation_source_handoff_projection
        ),
        "followup_citation_source_handoff_history": deepcopy(
            kernel.state.followup_citation_source_handoff_history
        ),
        "followup_citation_eligibility_state": deepcopy(
            kernel.state.followup_citation_eligibility_state
        ),
        "followup_citation_eligibility_projection": deepcopy(
            kernel.state.followup_citation_eligibility_projection
        ),
        "followup_citation_eligibility_history": deepcopy(
            kernel.state.followup_citation_eligibility_history
        ),
        "projections": deepcopy(kernel.state.projections),
        "action_statuses": deepcopy(kernel.state.action_statuses),
        "stage_statuses": deepcopy(kernel.state.stage_statuses),
        "reduced_action_ids": deepcopy(kernel.state.reduced_action_ids),
        "observations": deepcopy(kernel.state.observations),
        "next_observation_sequence": kernel.state.next_observation_sequence,
    }


def _assert_r1_snapshot_unchanged(
    kernel: RunKernel,
    snapshot: dict[str, Any],
) -> None:
    assert kernel.state.final_answer_packet == snapshot["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == snapshot[
        "final_answer_authority_projection"
    ]
    assert kernel.state.followup_citation_source_handoff_state == snapshot[
        "followup_citation_source_handoff_state"
    ]
    assert kernel.state.followup_citation_source_handoff_projection == snapshot[
        "followup_citation_source_handoff_projection"
    ]
    assert kernel.state.followup_citation_source_handoff_history == snapshot[
        "followup_citation_source_handoff_history"
    ]
    assert kernel.state.followup_citation_eligibility_state == snapshot[
        "followup_citation_eligibility_state"
    ]
    assert kernel.state.followup_citation_eligibility_projection == snapshot[
        "followup_citation_eligibility_projection"
    ]
    assert kernel.state.followup_citation_eligibility_history == snapshot[
        "followup_citation_eligibility_history"
    ]
    assert kernel.state.projections == snapshot["projections"]
    assert kernel.state.action_statuses == snapshot["action_statuses"]
    assert kernel.state.stage_statuses == snapshot["stage_statuses"]
    assert kernel.state.reduced_action_ids == snapshot["reduced_action_ids"]
    assert kernel.state.observations == snapshot["observations"]
    assert kernel.state.next_observation_sequence == snapshot[
        "next_observation_sequence"
    ]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
