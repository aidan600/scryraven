from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import pytest

from core.evidence_ledger import SourceRequirementStatus
from core.followup_author_gate_runtime import AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
from core.followup_author_input_authority_runtime import (
    AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
    execute_followup_author_input_authority_action,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import (
    execute_followup_final_answer_packet_prepare_action,
    followup_projection_digest,
)
from core.run_kernel import (
    FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
)
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_no_sensitive_payload,
    assert_u1_boundary_snapshot_unchanged,
    snapshot_u1_boundary_state,
)
from tests.test_ag96i3p1_final_evidence_selection import (
    OFFICIAL_REQUIREMENT_ID,
    _consume_p1,
    _execute_o2,
    _execute_p1,
    _kernel_through_o1,
    _kernel_through_o2,
)
from tests.test_ag96i3q1_citation_eligibility import (
    _execute_q1,
    _inject_external_stale_action_and_observation,
    _kernel_through_q1,
)
from tests.test_ag96i3r1_citation_source_handoff import (
    _consume_r1,
    _execute_r1,
)
from tests.test_ag96i3t1_citation_rendering import (
    _consume_t1,
    _execute_t1,
)

ROOT = Path(__file__).resolve().parents[1]


def test_u1_happy_path_creates_author_input_authority_refs_only() -> None:
    kernel = _kernel_through_t1()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    p1_state = deepcopy(kernel.state.followup_final_evidence_selection_state)
    q1_state = deepcopy(kernel.state.followup_citation_eligibility_state)
    r1_state = deepcopy(kernel.state.followup_citation_source_handoff_state)
    t1_state = deepcopy(kernel.state.followup_citation_rendering_state)

    action = kernel.authorize_followup_author_input_authority()
    assert action.stage == FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE
    assert action.inputs["author_input_authority_mode"] == (
        AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE
    )

    result = _execute_u1(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_input_authority_state
    projection = kernel.state.followup_author_input_authority_projection
    history = kernel.state.followup_author_input_authority_history
    packet = kernel.state.final_answer_packet
    refs = packet["author_input_refs"]
    payload_ref = packet["author_payload_ref"]

    assert state["owner"] == "RunKernel.FollowupAuthorInputAuthority"
    assert state["canonical_state"] is True
    assert projection["owner"] == "RunKernel.FollowupAuthorInputAuthority"
    assert projection == kernel.state.final_answer_authority_projection
    assert history == [projection]
    assert kernel.state.projections[FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE] == projection
    assert kernel.state.projections["final_answer_packet"] == projection

    assert packet["owner"] == "RunKernel.FinalAnswerPacket"
    assert packet["canonical_state"] is True
    assert packet["readiness_status"] == "blocked"
    assert packet["final_answer_allowed"] is False
    assert packet["answer_ready"] is False
    assert packet["evidence_allowed"] == packet_before["evidence_allowed"]
    assert packet["evidence_excluded"] == packet_before["evidence_excluded"]
    assert packet["citation_eligible"] == packet_before["citation_eligible"]
    assert packet["citation_ineligible"] == packet_before["citation_ineligible"]
    assert refs["packet_id"] == packet["packet_id"]
    assert refs["final_evidence_selection_id"] == p1_state["final_evidence_selection_id"]
    assert refs["citation_eligibility_id"] == q1_state["citation_eligibility_id"]
    assert refs["citation_source_handoff_id"] == r1_state["citation_source_handoff_id"]
    assert refs["citation_rendering_id"] == t1_state["citation_rendering_id"]
    assert refs["author_input_authority_id"] == state["author_input_authority_id"]
    assert refs["final_answer_authority_projection_digest"] == (
        followup_projection_digest(projection)
    )
    assert refs["rendered_source_entry_digest"] == t1_state[
        "rendered_source_entry_digest"
    ]
    assert payload_ref["payload_ref_id"] == refs["author_payload_ref_id"]
    assert payload_ref["status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert payload_ref["prompt_text_included"] is False
    assert payload_ref["final_text_included"] is False
    assert payload_ref["author_activation_allowed"] is False
    assert payload_ref["author_execution_deferred"] is True
    assert payload_ref["not_for_product_answer_activation"] is True

    assert kernel.state.followup_author_gate_state == {}
    assert kernel.state.followup_author_observation_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert getattr(kernel.state, "analyst_author_handoff_state", {}) == {}
    assert getattr(kernel.state, "economist_handoff_state", {}) == {}
    gate_action = kernel.authorize_followup_author_gate()
    assert gate_action.inputs["author_gate_mode"] == AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
    with pytest.raises(RunKernelTransitionError, match="packet-ready author input"):
        kernel.authorize_author_execution()

    assert_no_sensitive_payload(state)
    assert_no_sensitive_payload(projection)
    assert_no_sensitive_payload(packet)


def test_u1_authority_projection_content_and_packet_mutation_boundary() -> None:
    kernel = _kernel_through_t1()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    r1_state = deepcopy(kernel.state.followup_citation_source_handoff_state)
    t1_state = deepcopy(kernel.state.followup_citation_rendering_state)

    _consume_u1(kernel)

    packet = kernel.state.final_answer_packet
    projection = kernel.state.final_answer_authority_projection
    changed_keys = {
        key
        for key in set(packet_before) | set(packet)
        if packet_before.get(key) != packet.get(key)
    }
    assert changed_keys == {
        "author_input_refs",
        "author_payload_ref",
        "author_input_authority_prepared",
        "author_payload_ref_created",
        "prompt_text_included",
        "final_text_included",
        "author_gate_deferred",
        "product_answer_ready",
    }
    assert projection["final_evidence_refs"] == packet_before["evidence_allowed"]
    assert projection["author_allowed_evidence_refs"] == packet_before[
        "evidence_allowed"
    ]
    assert projection["citation_eligible_refs"] == packet_before["citation_eligible"]
    assert projection["author_allowed_citation_refs"] == packet_before[
        "citation_eligible"
    ]
    assert [item["source_id"] for item in projection["source_handoff_refs"]] == [
        item["source_id"] for item in r1_state["source_identity_records"]
    ]
    assert [item["source_id"] for item in projection["rendered_source_entry_refs"]] == [
        item["source_id"] for item in t1_state["rendered_source_entries"]
    ]
    assert projection["rendered_source_entry_digest"] == t1_state[
        "rendered_source_entry_digest"
    ]
    assert projection["mandatory_caveat_refs"] == packet_before["mandatory_caveats"]
    assert projection["prohibited_upgrade_refs"] == packet_before[
        "prohibited_upgrades"
    ]
    assert projection["author_missing_obligation_refs"] == packet_before.get(
        "missing_obligations",
        [],
    )
    assert projection["prompt_text_included"] is False
    assert projection["final_text_included"] is False
    assert projection["author_activation_allowed"] is False
    assert projection["author_execution_deferred"] is True
    assert projection["author_gate_deferred"] is True
    assert projection["product_answer_ready"] is False
    assert projection["live_validation_not_run"] is True
    _assert_forbidden_product_fields_absent(projection)
    _assert_forbidden_product_fields_absent(packet)


@pytest.mark.parametrize(
    ("label", "mutator"),
    [
        (
            "stale EvidenceLedger digest",
            lambda kernel: setattr(
                kernel.state.evidence_ledger.requirements[OFFICIAL_REQUIREMENT_ID],
                "status",
                SourceRequirementStatus.UNSATISFIED,
            ),
        ),
        (
            "stale SufficiencyJudgment digest",
            lambda kernel: kernel.state.sufficiency_judgment_projection.update(
                {"stale_digest": True}
            ),
        ),
        (
            "stale N recheck digest",
            lambda kernel: kernel.state.followup_sufficiency_recheck_state.update(
                {"stale_digest": True}
            ),
        ),
        (
            "stale O1 digest",
            lambda kernel: kernel.state.followup_final_answer_packet_readiness_state.update(
                {"stale_digest": True}
            ),
        ),
        (
            "stale O2 digest",
            lambda kernel: kernel.state.followup_blocked_final_answer_packet_shell_state.update(
                {"stale_digest": True}
            ),
        ),
        (
            "stale P1 digest",
            lambda kernel: kernel.state.followup_final_evidence_selection_state.update(
                {"stale_digest": True}
            ),
        ),
        (
            "stale Q1 digest",
            lambda kernel: kernel.state.followup_citation_eligibility_state.update(
                {"stale_digest": True}
            ),
        ),
        (
            "stale R1 digest",
            lambda kernel: kernel.state.followup_citation_source_handoff_state.update(
                {"stale_digest": True}
            ),
        ),
        (
            "stale T1 digest",
            lambda kernel: kernel.state.followup_citation_rendering_state.update(
                {"stale_digest": True}
            ),
        ),
        (
            "stale FinalAnswerPacket digest",
            lambda kernel: kernel.state.final_answer_packet.update(
                {"packet_id": "stale-packet"}
            ),
        ),
        (
            "mutated rendered source refs",
            lambda kernel: kernel.state.followup_citation_rendering_state[
                "rendered_source_entries"
            ][0].update({"source_id": "spoofed-source"}),
        ),
        (
            "missing T1 history",
            lambda kernel: kernel.state.followup_citation_rendering_history.clear(),
        ),
        (
            "noncanonical FinalAnswerPacket",
            lambda kernel: kernel.state.final_answer_packet.update(
                {"canonical_state": False}
            ),
        ),
    ],
)
def test_u1_binding_and_digest_failures_leave_state_unchanged(
    label: str,
    mutator: Callable[[RunKernel], None],
) -> None:
    kernel = _kernel_through_t1()
    action = kernel.authorize_followup_author_input_authority()
    result = _execute_u1(kernel, action=action)

    mutator(kernel)
    snapshot = snapshot_u1_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="U1|requires|mismatch"):
        kernel.reduce(result.observation)
    assert_u1_boundary_snapshot_unchanged(kernel, snapshot), label


def test_u1_spoofed_observation_payload_cannot_override_canonical_rebuild() -> None:
    kernel = _kernel_through_t1()
    action = kernel.authorize_followup_author_input_authority()
    result = _execute_u1(kernel, action=action)
    spoofed_state = deepcopy(result.record.to_dict())
    spoofed_state["final_answer_authority_projection"]["packet_id"] = "spoofed-packet"
    spoofed_state["author_payload_ref"]["payload_ref_id"] = "spoofed-ref"
    spoofed_state["author_input_refs"]["packet_id"] = "spoofed-packet"
    spoofed_observation = replace(
        result.observation,
        payload={"followup_author_input_authority_state": spoofed_state},
    )

    kernel.reduce(spoofed_observation)

    packet = kernel.state.final_answer_packet
    projection = kernel.state.final_answer_authority_projection
    assert packet["packet_id"] != "spoofed-packet"
    assert projection["packet_id"] == packet["packet_id"]
    assert packet["author_payload_ref"]["payload_ref_id"] != "spoofed-ref"
    assert packet["author_input_refs"]["packet_id"] == packet["packet_id"]


def test_u1_malformed_observation_rejects_before_mutation_or_bookkeeping() -> None:
    kernel = _kernel_through_t1()
    action = kernel.authorize_followup_author_input_authority()
    malformed = Observation.from_action(
        action,
        observation_type="followup_author_input_authority_prepared",
        status="completed",
        payload={},
    )
    snapshot = snapshot_u1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="requires"):
        kernel.reduce(malformed)
    assert_u1_boundary_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _stale_legacy_i2e_action_and_observation(),
        lambda: _stale_o2_action_and_observation(),
        lambda: _stale_p1_action_and_observation(),
        lambda: _stale_q1_action_and_observation(),
        lambda: _stale_r1_action_and_observation(),
        lambda: _stale_t1_action_and_observation(),
    ],
)
def test_u1_rejects_stale_upstream_reductions_after_success(
    factory: Callable[[], tuple[RunKernel, Any, Observation]],
) -> None:
    source_kernel, stale_action, stale_observation = factory()
    kernel = _kernel_through_t1()
    _consume_u1(kernel)
    _, injected_observation = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_action,
        stale_observation,
    )
    snapshot = snapshot_u1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3U1|stale"):
        kernel.reduce(injected_observation)
    assert_u1_boundary_snapshot_unchanged(kernel, snapshot)


def test_u1_duplicate_and_pre_authorized_duplicate_reductions_reject() -> None:
    kernel = _kernel_through_t1()
    first_action = kernel.authorize_followup_author_input_authority()
    first_result = _execute_u1(kernel, action=first_action)
    duplicate_action = kernel.authorize_followup_author_input_authority()
    duplicate_result = _execute_u1(kernel, action=duplicate_action)

    kernel.reduce(first_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already prepared"):
        kernel.authorize_followup_author_input_authority()

    snapshot = snapshot_u1_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3U1"):
        kernel.reduce(duplicate_result.observation)
    assert_u1_boundary_snapshot_unchanged(kernel, snapshot)


def test_u1_static_guards_keep_prompt_provider_role_and_pipeline_surfaces_closed() -> None:
    runtime_path = ROOT / "core" / "followup_author_input_authority_runtime.py"
    runtime_source = runtime_path.read_text(encoding="utf-8")
    assert passive_module_static_guard(
        runtime_source,
        module_name="followup_author_input_authority_runtime",
    ) == ()
    assert imported_modules(runtime_path).isdisjoint(
        {
            "core.runtime_prompt_assembly",
            "core.final_answer_runtime_assembly",
            "core.final_answer_runtime_adapter",
            "core.final_evidence_bundle_builder",
            "core.pipeline_orchestrator",
            "core.search_web",
            "core.search_providers",
            "core.retrieval_dispatch_runtime",
        }
    )
    for forbidden in (
        "runtime_prompt_assembly",
        "derive_author_input_payload",
        "build_final_answer_packet",
        "build_ordered",
        "post_author_output_projection",
        "AuthorExecutor",
        "AnalystExecutor",
        "EconomistExecutor",
    ):
        assert forbidden not in runtime_source

    run_kernel_source = (ROOT / "core" / "run_kernel.py").read_text(
        encoding="utf-8"
    )
    u1_authorize_section = run_kernel_source.split(
        "def authorize_followup_author_input_authority",
        1,
    )[1].split("def authorize_followup_final_answer_packet_prepare", 1)[0]
    u1_reduce_section = run_kernel_source.split(
        "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY:",
        1,
    )[1].split(
        "elif (\n            action.action_type\n            is ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE",
        1,
    )[0]
    for forbidden in (
        "runtime_prompt_assembly",
        "derive_author_input_payload",
        "build_ordered",
        "post_author_output_projection",
        "AuthorExecutor",
        "AnalystExecutor",
        "EconomistExecutor",
    ):
        assert forbidden not in u1_authorize_section
        assert forbidden not in u1_reduce_section

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3u1" not in pipeline_source.casefold()
    assert "followup_author_input_authority" not in pipeline_source


def _kernel_through_t1() -> RunKernel:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    _consume_t1(kernel)
    return kernel


def _execute_u1(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_author_input_authority_action(
        action,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        followup_final_answer_packet_readiness_state=(
            kernel.state.followup_final_answer_packet_readiness_state
        ),
        followup_final_answer_packet_readiness_projection=(
            kernel.state.followup_final_answer_packet_readiness_projection
        ),
        followup_final_answer_packet_readiness_history=(
            kernel.state.followup_final_answer_packet_readiness_history
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
        followup_final_evidence_selection_state=(
            kernel.state.followup_final_evidence_selection_state
        ),
        followup_final_evidence_selection_projection=(
            kernel.state.followup_final_evidence_selection_projection
        ),
        followup_final_evidence_selection_history=(
            kernel.state.followup_final_evidence_selection_history
        ),
        followup_citation_eligibility_state=(
            kernel.state.followup_citation_eligibility_state
        ),
        followup_citation_eligibility_projection=(
            kernel.state.followup_citation_eligibility_projection
        ),
        followup_citation_eligibility_history=(
            kernel.state.followup_citation_eligibility_history
        ),
        followup_citation_source_handoff_state=(
            kernel.state.followup_citation_source_handoff_state
        ),
        followup_citation_source_handoff_projection=(
            kernel.state.followup_citation_source_handoff_projection
        ),
        followup_citation_source_handoff_history=(
            kernel.state.followup_citation_source_handoff_history
        ),
        followup_citation_rendering_state=(
            kernel.state.followup_citation_rendering_state
        ),
        followup_citation_rendering_projection=(
            kernel.state.followup_citation_rendering_projection
        ),
        followup_citation_rendering_history=(
            kernel.state.followup_citation_rendering_history
        ),
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
    )


def _consume_u1(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_author_input_authority()
    result = _execute_u1(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _stale_legacy_i2e_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_o1()
    action = kernel.authorize_followup_final_answer_packet_prepare()
    result = execute_followup_final_answer_packet_prepare_action(
        action,
        followup_sufficiency_recheck_state=(
            kernel.state.followup_sufficiency_recheck_state
        ),
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    return kernel, action, result.observation


def _stale_o2_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_o1()
    action = kernel.authorize_followup_blocked_final_answer_packet_shell()
    result = _execute_o2(kernel, action=action)
    return kernel, action, result.observation


def _stale_p1_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_o2()
    action = kernel.authorize_followup_final_evidence_selection()
    result = _execute_p1(kernel, action=action)
    return kernel, action, result.observation


def _stale_q1_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_o2()
    _consume_p1(kernel)
    action = kernel.authorize_followup_citation_eligibility()
    result = _execute_q1(kernel, action=action)
    return kernel, action, result.observation


def _stale_r1_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_q1()
    action = kernel.authorize_followup_citation_source_handoff()
    result = _execute_r1(kernel, action=action)
    return kernel, action, result.observation


def _stale_t1_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_q1()
    _consume_r1(kernel)
    action = kernel.authorize_followup_citation_rendering()
    result = _execute_t1(kernel, action=action)
    return kernel, action, result.observation


def _assert_forbidden_product_fields_absent(value: Any) -> None:
    forbidden = {
        "prompt",
        "prompt_text",
        "final_answer_text",
        "ordered_sources",
        "ordered_product_source_output",
        "markdown_source_list",
        "source_list_prose",
        "inline_citation",
        "inline_citation_string",
        "final_answer_citation",
        "final_answer_citation_string",
        "rendered_citation",
        "rendered_citations",
        "formatted_citation",
        "formatted_citations",
        "author_input_payload",
        "analyst_handoff_ref",
        "economist_handoff_ref",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden
            _assert_forbidden_product_fields_absent(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_forbidden_product_fields_absent(child)
