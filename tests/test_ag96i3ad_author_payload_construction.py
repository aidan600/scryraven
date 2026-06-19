from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pytest

from core.followup_author_input_authority_runtime import (
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_author_payload_construction_runtime import (
    AD_AUTHORITY_PROJECTION_MUTATION_FIELDS,
    AD_PACKET_MUTATION_FIELDS,
    AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE,
    FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE,
    FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS,
    execute_followup_author_payload_construction_action,
)
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.run_kernel import Observation, RunKernel, RunKernelTransitionError
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_ac_boundary_snapshot_unchanged,
    assert_ad_boundary_snapshot_unchanged,
    assert_no_sensitive_payload,
    snapshot_ac_boundary_state,
    snapshot_ad_boundary_state,
)
from tests.test_ag96i3ac_author_payload_authority import (
    _consume_ac,
    _execute_ac,
    _kernel_through_z,
    _stale_z_action_and_observation,
)
from tests.test_ag96i3q1_citation_eligibility import (
    _inject_external_stale_action_and_observation,
)
from tests.test_ag96i3u1_author_input_authority import (
    _stale_legacy_i2e_action_and_observation,
    _stale_o2_action_and_observation,
    _stale_p1_action_and_observation,
    _stale_q1_action_and_observation,
    _stale_r1_action_and_observation,
    _stale_t1_action_and_observation,
)
from tests.test_ag96i3v1_author_gate import _stale_u1_action_and_observation
from tests.test_ag96i3w_author_execution_readiness import (
    _stale_v1_action_and_observation,
)
from tests.test_ag96i3x_author_input_materialization import (
    _stale_w_action_and_observation,
)
from tests.test_ag96i3y_author_execution_activation import (
    _stale_x_action_and_observation,
)
from tests.test_ag96i3z_author_prompt_assembly_manifest import (
    _stale_y_action_and_observation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_ad_happy_path_constructs_ac_bound_author_payload_envelope() -> None:
    kernel = _kernel_through_ac()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    ac_state = deepcopy(kernel.state.followup_author_payload_authority_state)
    ac_projection = deepcopy(kernel.state.followup_author_payload_authority_projection)
    z_state = deepcopy(kernel.state.followup_author_prompt_assembly_manifest_state)
    y_state = deepcopy(kernel.state.followup_author_execution_activation_state)
    x_state = deepcopy(kernel.state.followup_author_input_materialization_state)
    w_state = deepcopy(kernel.state.followup_author_execution_readiness_state)
    v1_state = deepcopy(kernel.state.followup_author_gate_state)
    u1_state = deepcopy(kernel.state.followup_author_input_authority_state)

    action = kernel.authorize_followup_author_payload_construction()
    assert action.stage == FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE
    assert action.inputs["payload_envelope_mode"] == (
        AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE
    )
    assert action.inputs["ac_payload_authority_id"] == ac_state["payload_authority_id"]

    result = _execute_ad(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_payload_construction_state
    projection = kernel.state.followup_author_payload_construction_projection
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    envelope_ref = state["ag96i3_author_payload_envelope_ref"]
    for surface in (state, projection):
        assert surface["owner"] == "RunKernel.FollowupAuthorPayloadConstruction"
        assert surface["canonical_state"] is True
        assert surface["trace_only"] is False
        assert surface["storage_only"] is False
        assert surface["status"] == FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STATUS
        assert surface["payload_envelope_mode"] == (
            AG96I3AD_AC_CONSUMING_AUTHOR_PAYLOAD_MODE
        )
        assert surface["ac_payload_authority_consumed"] is True
        assert surface["ac_payload_authority_id"] == ac_state["payload_authority_id"]
        assert surface["ac_payload_authority_digest"] == (
            followup_projection_digest(ac_state)
        )
        assert surface["ac_payload_authority_projection_digest"] == (
            followup_projection_digest(ac_projection)
        )
        assert surface["z_author_prompt_assembly_manifest_id"] == (
            z_state["author_prompt_assembly_manifest_id"]
        )
        assert surface["z_author_prompt_assembly_manifest_digest"] == (
            followup_projection_digest(z_state)
        )
        assert surface["y_author_execution_activation_id"] == (
            y_state["author_execution_activation_id"]
        )
        assert surface["x_author_input_materialization_id"] == (
            x_state["author_input_materialization_id"]
        )
        assert surface["w_author_execution_readiness_id"] == (
            w_state["author_execution_readiness_id"]
        )
        assert surface["v1_author_gate_id"] == v1_state["author_gate_id"]
        assert surface["u1_authority_id"] == u1_state["author_input_authority_id"]
        assert surface["current_final_answer_packet_digest"] == (
            followup_projection_digest(packet_before)
        )
        assert surface["final_answer_authority_projection_digest"] == (
            followup_projection_digest(authority_before)
        )
        assert surface["author_input_refs_digest"] == (
            followup_projection_digest(packet_before["author_input_refs"])
        )
        assert surface["legacy_author_payload_ref_status"] == (
            FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
        )
        _assert_x_bill_of_materials(surface["x_bill_of_materials"], x_state)
        _assert_y_demotion(surface)
        _assert_closed_author_surface(surface)

    assert envelope_ref["status"] == FOLLOWUP_AUTHOR_PAYLOAD_ENVELOPE_REF_STATUS
    assert envelope_ref["future_author_execution_must_consume"] is True
    assert envelope_ref["legacy_author_payload_ref_subordinated"] is True
    assert envelope_ref["legacy_author_payload_ref_status"] == (
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    )
    assert set(envelope_ref["payload_section_ids"]) == set(state["payload_sections"])
    assert envelope_ref["payload_section_digests"] == state["payload_section_digests"]
    assert packet["ag96i3_author_payload_envelope_ref"] == envelope_ref
    assert authority["ag96i3_author_payload_envelope_ref"] == envelope_ref
    assert packet["author_payload_ref"] == packet_before["author_payload_ref"]
    assert authority["author_payload_ref"] == authority_before["author_payload_ref"]
    assert packet["author_payload_ref"]["status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert authority["author_payload_ref"]["status"] == (
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    )
    assert kernel.state.followup_author_payload_construction_history == [projection]
    assert kernel.state.projections[FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE] == (
        projection
    )
    for surface in (state, projection, envelope_ref, packet, authority):
        _assert_closed_author_surface(surface)
        _assert_no_closed_payload_text(surface)
        assert_no_sensitive_payload(surface)
    with pytest.raises(RunKernelTransitionError, match="consume AG-96I3AD"):
        kernel.authorize_author_execution()


def test_ad_payload_envelope_contains_consumable_sections_without_prompt_text() -> None:
    kernel = _kernel_through_ac()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    u1_state = deepcopy(kernel.state.followup_author_input_authority_state)
    x_state = deepcopy(kernel.state.followup_author_input_materialization_state)
    ac_state = deepcopy(kernel.state.followup_author_payload_authority_state)

    _consume_ad(kernel)

    state = kernel.state.followup_author_payload_construction_state
    projection = kernel.state.followup_author_payload_construction_projection
    sections = state["payload_sections"]
    expected_sections = {
        "ac_payload_authority",
        "x_bill_of_materials",
        "author_input_refs",
        "legacy_author_payload_ref",
        "final_answer_packet_snapshot",
        "allowed_evidence_refs",
        "citation_eligibility_refs",
        "rendered_source_entry_refs",
        "mandatory_caveat_refs",
        "prohibited_upgrade_refs",
        "source_bound_unknown_refs",
        "prompt_digest_manifest",
        "x_materialization_manifest",
    }
    assert set(state["payload_section_ids"]) == expected_sections
    assert set(state["payload_section_digests"]) == expected_sections
    for section_id, section in sections.items():
        assert state["payload_section_digests"][section_id] == (
            followup_projection_digest(section)
        )
    assert sections["ac_payload_authority"]["state_digest"] == (
        followup_projection_digest(ac_state)
    )
    assert sections["x_bill_of_materials"]["section_digests"] == (
        x_state["section_digests"]
    )
    assert sections["author_input_refs"]["refs"] == packet_before["author_input_refs"]
    assert sections["legacy_author_payload_ref"]["ref"] == (
        packet_before["author_payload_ref"]
    )
    assert sections["allowed_evidence_refs"]["refs"] == (
        u1_state["author_allowed_evidence_refs"]
    )
    assert sections["citation_eligibility_refs"]["refs"] == (
        u1_state["citation_eligibility_refs"]
    )
    assert sections["rendered_source_entry_refs"]["refs"] == (
        u1_state["author_rendered_source_entry_refs"]
    )
    assert sections["prompt_digest_manifest"]["prompt_text_digest"] == (
        ac_state["prompt_text_digest"]
    )
    assert sections["prompt_digest_manifest"]["prompt_text_length"] == (
        ac_state["prompt_text_length"]
    )
    assert sections["prompt_digest_manifest"]["authority_block_text_digest"] == (
        ac_state["authority_block_text_digest"]
    )
    assert state["prompt_text_digest"] == ac_state["prompt_text_digest"]
    assert state["prompt_text_length"] == ac_state["prompt_text_length"]
    assert state["authority_block_text_digest"] == (
        ac_state["authority_block_text_digest"]
    )
    assert state["allowed_evidence_refs"] == u1_state["author_allowed_evidence_refs"]
    assert state["rendered_source_entries_refs_or_digest"]["digest"] == (
        followup_projection_digest({"refs": u1_state["author_rendered_source_entry_refs"]})
    )
    assert projection["payload_sections"] == sections
    assert kernel.state.final_answer_packet["author_payload_ref"] == (
        packet_before["author_payload_ref"]
    )
    assert kernel.state.final_answer_authority_projection["author_payload_ref"] == (
        authority_before["author_payload_ref"]
    )
    for surface in (state, projection, sections):
        _assert_no_closed_payload_text(surface)
        assert_no_sensitive_payload(surface)


def test_ad_packet_and_authority_mutation_boundary_is_only_ad_fields() -> None:
    kernel = _kernel_through_ac()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)

    _consume_ad(kernel)

    state = kernel.state.followup_author_payload_construction_state
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    packet_changed = _changed_keys(packet_before, packet)
    authority_changed = _changed_keys(authority_before, authority)
    assert set(state["packet_mutation"]) == set(AD_PACKET_MUTATION_FIELDS)
    assert set(state["final_answer_authority_projection_mutation"]) == set(
        AD_AUTHORITY_PROJECTION_MUTATION_FIELDS
    )
    assert packet_changed <= set(AD_PACKET_MUTATION_FIELDS)
    assert authority_changed <= set(AD_AUTHORITY_PROJECTION_MUTATION_FIELDS)
    assert packet_changed >= {
        "ag96i3_author_payload_envelope_ref",
        "ag96i3_author_payload_digest",
        "ag96i3_author_payload_status",
    }
    assert authority_changed >= {
        "ag96i3_author_payload_envelope_ref",
        "ag96i3_author_payload_digest",
        "ag96i3_author_payload_status",
    }
    assert packet["author_payload_ref"] == packet_before["author_payload_ref"]
    assert authority["author_payload_ref"] == authority_before["author_payload_ref"]
    assert packet["ag96i3_author_payload_authority_ref"] == (
        packet_before["ag96i3_author_payload_authority_ref"]
    )
    assert authority["ag96i3_author_payload_authority_ref"] == (
        authority_before["ag96i3_author_payload_authority_ref"]
    )


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (
            lambda kernel: kernel.state.followup_author_payload_authority_state.update(
                {"stale_digest": True}
            ),
            "AC payload authority|AC inputs|stale packet",
        ),
        (
            lambda kernel: kernel.state.followup_author_payload_authority_projection.update(
                {"canonical_state": False}
            ),
            "canonical AC",
        ),
        (
            lambda kernel: kernel.state.followup_author_payload_authority_history.clear(),
            "current AC history",
        ),
        (
            lambda kernel: kernel.state.followup_author_prompt_assembly_manifest_state.update(
                {"stale_digest": True}
            ),
            "z_author_prompt_assembly_manifest_digest|AC inputs",
        ),
        (
            lambda kernel: kernel.state.followup_author_execution_activation_state.update(
                {"stale_digest": True}
            ),
            "y_author_execution_activation_digest|AC inputs",
        ),
        (
            lambda kernel: kernel.state.followup_author_input_materialization_state.update(
                {"stale_digest": True}
            ),
            "x_author_input_materialization_digest|AC inputs",
        ),
        (
            lambda kernel: kernel.state.followup_author_execution_readiness_state.update(
                {"stale_digest": True}
            ),
            "w_author_execution_readiness_digest|AC inputs",
        ),
        (
            lambda kernel: kernel.state.followup_author_gate_state.update(
                {"stale_digest": True}
            ),
            "v1_author_gate_digest|AC inputs",
        ),
        (
            lambda kernel: kernel.state.followup_author_input_authority_state.update(
                {"stale_digest": True}
            ),
            "u1_authority_digest|AC inputs",
        ),
        (
            lambda kernel: kernel.state.final_answer_packet.update(
                {"stale_digest": True}
            ),
            "stale packet|AC inputs",
        ),
        (
            lambda kernel: kernel.state.final_answer_authority_projection.update(
                {"stale_digest": True}
            ),
            "stale authority|AC inputs",
        ),
        (
            lambda kernel: kernel.state.final_answer_packet["author_payload_ref"].update(
                {"status": "author_input_ready"}
            ),
            "deferred|ready|AC inputs",
        ),
    ],
)
def test_ad_missing_stale_or_noncanonical_inputs_reject_atomically(
    mutator: Callable[[RunKernel], None],
    match: str,
) -> None:
    kernel = _kernel_through_ac()
    action = kernel.authorize_followup_author_payload_construction()
    result = _execute_ad(kernel, action=action)
    mutator(kernel)
    snapshot = snapshot_ac_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)
    assert_ac_boundary_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    "payload",
    [
        {"followup_author_payload_construction_state": {"status": "spoofed"}},
        {"ag96i3_author_payload_envelope_ref": {"status": "spoofed"}},
        {"payload_sections": {"spoofed": True}},
        {"prompt_text": "write the answer"},
        {"authority_block_text": "full authority block"},
        {"final_answer_text": "not allowed"},
        {"source_snippet": "raw source text"},
        {"product_output": "ready answer"},
        {"executable_author_input_payload": {"status": "author_input_ready"}},
        {"author_input_ready": True},
    ],
)
def test_ad_caller_supplied_closed_payload_fields_are_rejected(
    payload: dict[str, Any],
) -> None:
    kernel = _kernel_through_ac()
    with pytest.raises(
        RunKernelTransitionError,
        match="caller-supplied|retain|requires|ready",
    ):
        kernel.authorize_followup_author_payload_construction(inputs=payload)


def test_ad_spoofed_observation_is_rebuilt_or_rejected_atomically() -> None:
    kernel = _kernel_through_ac()
    action = kernel.authorize_followup_author_payload_construction()
    result = _execute_ad(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["ag96i3_author_payload_envelope_ref"][
        "payload_envelope_ref_id"
    ] = "spoofed-ref"
    spoofed["payload_sections"]["x_bill_of_materials"][
        "prompt_or_input_digest"
    ] = "spoofed-digest"
    kernel.reduce(_ad_observation_from_state(action, spoofed))
    state = kernel.state.followup_author_payload_construction_state
    assert state["ag96i3_author_payload_envelope_ref"][
        "payload_envelope_ref_id"
    ] != "spoofed-ref"
    assert state["payload_sections"]["x_bill_of_materials"][
        "prompt_or_input_digest"
    ] != "spoofed-digest"

    kernel = _kernel_through_ac()
    action = kernel.authorize_followup_author_payload_construction()
    result = _execute_ad(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["prompt_text"] = "retain this prompt"
    snapshot = snapshot_ac_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="retain"):
        kernel.reduce(_ad_observation_from_state(action, spoofed))
    assert_ac_boundary_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _stale_legacy_i2e_action_and_observation(),
        lambda: _stale_o2_action_and_observation(),
        lambda: _stale_p1_action_and_observation(),
        lambda: _stale_q1_action_and_observation(),
        lambda: _stale_r1_action_and_observation(),
        lambda: _stale_t1_action_and_observation(),
        lambda: _stale_u1_action_and_observation(),
        lambda: _stale_v1_action_and_observation(),
        lambda: _stale_w_action_and_observation(),
        lambda: _stale_x_action_and_observation(),
        lambda: _stale_y_action_and_observation(),
        lambda: _stale_z_action_and_observation(),
        lambda: _stale_ac_action_and_observation(),
    ],
)
def test_ad_rejects_stale_upstream_reductions_after_success(
    factory: Callable[[], tuple[RunKernel, Any, Observation]],
) -> None:
    source_kernel, stale_action, stale_observation = factory()
    kernel = _kernel_through_ac()
    _consume_ad(kernel)
    _, injected_observation = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_action,
        stale_observation,
    )
    snapshot = snapshot_ad_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="AG-96I3AD|stale"):
        kernel.reduce(injected_observation)
    assert_ad_boundary_snapshot_unchanged(kernel, snapshot)


def test_ad_duplicate_and_future_execution_guards() -> None:
    kernel = _kernel_through_ac()
    first_action = kernel.authorize_followup_author_payload_construction()
    first_result = _execute_ad(kernel, action=first_action)
    duplicate_action = kernel.authorize_followup_author_payload_construction()
    duplicate_result = _execute_ad(kernel, action=duplicate_action)

    kernel.reduce(first_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already constructed"):
        kernel.authorize_followup_author_payload_construction()
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3AD"):
        kernel.reduce(duplicate_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(first_result.observation)

    kernel.state.final_answer_packet["author_payload_ref"][
        "status"
    ] = "author_input_ready"
    kernel.state.final_answer_authority_projection["author_payload_ref"][
        "status"
    ] = "author_input_ready"
    with pytest.raises(RunKernelTransitionError, match="consume AG-96I3AD"):
        kernel.authorize_author_execution()


def test_ad_requires_ac_before_authorization() -> None:
    kernel = _kernel_through_z()
    with pytest.raises(RunKernelTransitionError, match="requires reduced AC"):
        kernel.authorize_followup_author_payload_construction()


def test_ad_static_guards_keep_legacy_execution_product_and_pipeline_closed() -> None:
    runtime_path = ROOT / "core" / "followup_author_payload_construction_runtime.py"
    run_kernel_path = ROOT / "core" / "run_kernel.py"
    forbidden_imports = {
        "core.runtime_prompt_assembly",
        "core.author_execution_runtime",
        "core.final_answer_runtime_assembly",
        "core.final_answer_runtime_adapter",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
        "subprocess",
        "os",
    }
    assert imported_modules(runtime_path).isdisjoint(forbidden_imports)

    runtime_source = runtime_path.read_text(encoding="utf-8")
    run_kernel_source = run_kernel_path.read_text(encoding="utf-8")
    ad_sections = [
        run_kernel_source.split(
            "def authorize_followup_author_payload_construction",
            1,
        )[1].split("def authorize_followup_author_observation", 1)[0],
        run_kernel_source.split(
            "if action.action_type is ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION:\n"
            "            ad_observed_payload_construction_state",
            1,
        )[1].split(
            "self.state.reduced_action_ids.add(action.action_id)",
            1,
        )[0],
        run_kernel_source.split(
            "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION:",
            1,
        )[1].split(
            "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_OBSERVATION",
            1,
        )[0],
    ]
    forbidden_names = (
        "FinalAnswerAuthorInputPayload",
        "derive_author_input_payload",
        "to_author_input_payload",
        "runtime_prompt_assembly",
        "final_answer_runtime_assembly",
        "pipeline_orchestrator",
        "build_ordered_sources",
    )
    for forbidden in forbidden_names:
        assert forbidden not in runtime_source
        for section in ad_sections:
            assert forbidden not in section
    for forbidden_call in (
        "execute_author_action(",
        "ask_model(",
        "author_payload.status",
        "AUTHOR_EXECUTE",
        "AUTHOR_OUTPUT_OBSERVED",
    ):
        assert forbidden_call not in runtime_source
        for section in ad_sections:
            assert forbidden_call not in section

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3ad" not in pipeline_source.casefold()
    assert "followup_author_payload_construction" not in pipeline_source


def _kernel_through_ac() -> RunKernel:
    kernel = _kernel_through_z()
    _consume_ac(kernel)
    return kernel


def _execute_ad(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_author_payload_construction_action(
        action,
        followup_author_payload_authority_state=(
            kernel.state.followup_author_payload_authority_state
        ),
        followup_author_payload_authority_projection=(
            kernel.state.followup_author_payload_authority_projection
        ),
        followup_author_payload_authority_history=(
            kernel.state.followup_author_payload_authority_history
        ),
        followup_author_prompt_assembly_manifest_state=(
            kernel.state.followup_author_prompt_assembly_manifest_state
        ),
        followup_author_execution_activation_state=(
            kernel.state.followup_author_execution_activation_state
        ),
        followup_author_input_materialization_state=(
            kernel.state.followup_author_input_materialization_state
        ),
        followup_author_execution_readiness_state=(
            kernel.state.followup_author_execution_readiness_state
        ),
        followup_author_gate_state=kernel.state.followup_author_gate_state,
        followup_author_input_authority_state=(
            kernel.state.followup_author_input_authority_state
        ),
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
    )


def _consume_ad(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_author_payload_construction()
    result = _execute_ad(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _stale_ac_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_z()
    action = kernel.authorize_followup_author_payload_authority()
    result = _execute_ac(kernel, action=action)
    return kernel, action, result.observation


def _ad_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_author_payload_constructed",
        status="completed",
        payload={"followup_author_payload_construction_state": state},
    )


def _changed_keys(before: dict[str, Any], after: dict[str, Any]) -> set[str]:
    return {key for key in set(before) | set(after) if before.get(key) != after.get(key)}


def _assert_x_bill_of_materials(bom: dict[str, Any], x_state: dict[str, Any]) -> None:
    for key in (
        "section_ids",
        "section_digests",
        "prompt_or_input_digest",
        "prompt_or_input_length",
        "authority_block_digest",
        "author_payload_ref_digest",
        "rendered_source_entry_digest",
        "source_identity_digest",
    ):
        assert bom[key] == x_state[key]


def _assert_y_demotion(surface: dict[str, Any]) -> None:
    assert surface["y_old_ready_status_demoted"] is True
    assert surface["y_author_input_ready"] is False
    assert surface["activation_consumable_by_future_author_execution"] is True
    assert surface["legacy_author_payload_ref_status"] == (
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    )


def _assert_closed_author_surface(surface: dict[str, Any]) -> None:
    for key in (
        "author_input_ready",
        "author_execution_allowed",
        "author_activation_allowed",
        "prompt_text_retained",
        "authority_block_text_retained",
        "final_answer_author_input_payload_created",
        "final_text_included",
        "product_answer_ready",
        "model_called",
        "author_model_called",
        "execute_author_action_called",
        "ask_model_called",
        "author_observation_created",
        "final_answer_outcome_created",
    ):
        if key in surface:
            assert surface[key] is False
    assert surface.get("author_execution_deferred") is True


def _assert_no_closed_payload_text(value: Any) -> None:
    forbidden_keys = {
        "prompt_text",
        "authority_block_text",
        "final_answer_text",
        "answer_text",
        "ordered_sources",
        "ordered_product_source_output",
        "source_snippet",
        "snippet",
        "author_input_payload",
        "executable_author_input_payload",
        "product_output",
        "raw_text",
        "private_payload",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden_keys
            _assert_no_closed_payload_text(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_no_closed_payload_text(child)
    elif isinstance(value, str):
        serialized = json.dumps(value).casefold()
        for token in (
            "author_input_ready",
            "z_prompt_manifest",
            "z_authority_block_manifest",
            "write the final markdown report",
            "precision evidence",
            "ordered product source",
        ):
            assert token not in serialized
