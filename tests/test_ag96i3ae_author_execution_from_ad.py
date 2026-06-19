from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pytest

from core.followup_author_execution_from_ad_runtime import (
    AE_AUTHORITY_PROJECTION_MUTATION_FIELDS,
    AE_PACKET_MUTATION_FIELDS,
    AG96I3AE_AD_CONSUMING_AUTHOR_EXECUTION_FAKE_MODEL_MODE,
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE,
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STATUS,
    execute_followup_author_execution_from_ad_action,
)
from core.followup_author_input_authority_runtime import (
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.run_kernel import (
    ActionType,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
)
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_ae_boundary_snapshot_unchanged,
    assert_no_sensitive_payload,
    snapshot_ae_boundary_state,
)
from tests.test_ag96i3ac_author_payload_authority import _stale_z_action_and_observation
from tests.test_ag96i3ad_author_payload_construction import (
    _consume_ad,
    _execute_ad,
    _kernel_through_ac,
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
_AE_RUNTIME_PREFIXES = (
    "followup_author_payload_construction",
    "followup_author_payload_authority",
    "followup_author_prompt_assembly_manifest",
    "followup_author_execution_activation",
    "followup_author_input_materialization",
    "followup_author_execution_readiness",
    "followup_author_gate",
    "followup_author_input_authority",
)


def test_ae_happy_path_executes_ad_payload_with_fake_model_hash_only() -> None:
    kernel = _kernel_through_ad()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    ad_state = deepcopy(kernel.state.followup_author_payload_construction_state)

    action = kernel.authorize_followup_author_execution_from_ad()
    assert action.stage == FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE
    assert action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD
    assert action.expected_observation_type is (
        ObservationType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_OBSERVED
    )
    assert action.inputs["author_execution_from_ad_mode"] == (
        AG96I3AE_AD_CONSUMING_AUTHOR_EXECUTION_FAKE_MODEL_MODE
    )
    assert action.inputs["payload_envelope_id"] == ad_state["payload_envelope_id"]
    assert action.inputs["payload_envelope_digest"] == (
        ad_state["ag96i3_author_payload_digest"]
    )

    result = _execute_ae(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_execution_from_ad_state
    projection = kernel.state.followup_author_execution_from_ad_projection
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    author_observation = kernel.state.author_observation
    final_answer_outcome = kernel.state.final_answer_outcome
    execution_ref = state["ag96i3_author_execution_from_ad_ref"]

    assert state["owner"] == "RunKernel.FollowupAuthorExecutionFromAD"
    for surface in (state, projection):
        assert surface["canonical_state"] is True
        assert surface["status"] == FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STATUS
        assert surface["author_execution_from_ad_mode"] == (
            AG96I3AE_AD_CONSUMING_AUTHOR_EXECUTION_FAKE_MODEL_MODE
        )
        _assert_ae_closed_surface(surface)
    for field in (
        "payload_envelope_id",
        "payload_envelope_digest",
        "ad_payload_construction_digest",
        "current_final_answer_packet_digest",
        "final_answer_authority_projection_digest",
        "author_report_text_digest",
        "author_report_text_length",
    ):
        assert projection[field] == state[field]

    assert state["ad_author_payload_envelope_consumed"] is True
    assert state["payload_envelope_id"] == ad_state["payload_envelope_id"]
    assert state["payload_envelope_digest"] == ad_state["ag96i3_author_payload_digest"]
    assert state["ad_payload_construction_digest"] == followup_projection_digest(
        ad_state
    )
    for field in (
        "ad_payload_construction_projection_digest",
        "ac_payload_authority_id",
        "ac_payload_authority_digest",
        "z_author_prompt_assembly_manifest_id",
        "z_author_prompt_assembly_manifest_digest",
        "y_author_execution_activation_id",
        "y_author_execution_activation_digest",
        "x_author_input_materialization_id",
        "x_author_input_materialization_digest",
        "w_author_execution_readiness_id",
        "w_author_execution_readiness_digest",
        "v1_author_gate_id",
        "v1_author_gate_digest",
        "u1_authority_id",
        "u1_authority_digest",
        "current_final_answer_packet_digest",
        "final_answer_authority_projection_digest",
        "author_input_refs_digest",
    ):
        assert state[field] == action.inputs[field]
    assert state["legacy_author_payload_ref_status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert state["payload_section_digests"] == ad_state["payload_section_digests"]
    assert state["x_bill_of_materials_digest"] == followup_projection_digest(
        ad_state["x_bill_of_materials"]
    )
    assert state["prompt_text_digest"] == ad_state["prompt_text_digest"]
    assert state["prompt_text_length"] == ad_state["prompt_text_length"]
    assert state["author_report_text_digest"]
    assert state["author_report_text_length"] > 0

    assert packet["ag96i3_author_execution_from_ad_ref"] == execution_ref
    assert authority["ag96i3_author_execution_from_ad_ref"] == execution_ref
    assert packet["author_payload_ref"] == packet_before["author_payload_ref"]
    assert authority["author_payload_ref"] == authority_before["author_payload_ref"]
    assert packet["author_payload_ref"]["status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert authority["author_payload_ref"]["status"] == (
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    )
    assert kernel.state.followup_author_execution_from_ad_history == [projection]
    assert kernel.state.projections[FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE] == (
        projection
    )

    _assert_author_observation(author_observation, state)
    _assert_final_answer_outcome(final_answer_outcome, state, author_observation)
    assert state["author_observation"] == author_observation
    assert state["final_answer_outcome"] == final_answer_outcome
    for surface in (
        state,
        projection,
        packet,
        authority,
        author_observation,
        final_answer_outcome,
        kernel.state.to_trace_projection().to_dict(),
    ):
        _assert_no_closed_payload_text(surface)
        assert_no_sensitive_payload(surface)


def test_ae_packet_and_authority_mutation_boundary_is_only_ae_fields() -> None:
    kernel = _kernel_through_ad()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)

    _consume_ae(kernel)

    state = kernel.state.followup_author_execution_from_ad_state
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    packet_changed = _changed_keys(packet_before, packet)
    authority_changed = _changed_keys(authority_before, authority)
    assert set(state["packet_mutation"]) == set(AE_PACKET_MUTATION_FIELDS)
    assert set(state["final_answer_authority_projection_mutation"]) == set(
        AE_AUTHORITY_PROJECTION_MUTATION_FIELDS
    )
    assert packet_changed <= set(AE_PACKET_MUTATION_FIELDS)
    assert authority_changed <= set(AE_AUTHORITY_PROJECTION_MUTATION_FIELDS)
    assert packet_changed >= {
        "ag96i3_author_execution_from_ad_ref",
        "ag96i3_author_execution_from_ad_digest",
        "ag96i3_author_execution_from_ad_status",
        "author_observation_created",
        "final_answer_outcome_created",
    }
    assert authority_changed >= {
        "ag96i3_author_execution_from_ad_ref",
        "ag96i3_author_execution_from_ad_digest",
        "ag96i3_author_execution_from_ad_status",
        "author_observation_created",
        "final_answer_outcome_created",
    }
    assert packet["author_payload_ref"] == packet_before["author_payload_ref"]
    assert authority["author_payload_ref"] == authority_before["author_payload_ref"]


def _update_state_attr(attr: str, values: dict[str, Any]) -> Callable[[RunKernel], None]:
    def mutate(kernel: RunKernel) -> None:
        getattr(kernel.state, attr).update(values)

    return mutate


def _clear_state_attr(attr: str) -> Callable[[RunKernel], None]:
    def mutate(kernel: RunKernel) -> None:
        getattr(kernel.state, attr).clear()

    return mutate


def _set_old_ready_status(kernel: RunKernel) -> None:
    kernel.state.final_answer_packet["author_payload_ref"].update(
        {"status": "author_input_ready"}
    )


_STALE_DIGEST_CASES = (
    ("followup_author_payload_authority_state", "ac_payload_authority_digest"),
    (
        "followup_author_prompt_assembly_manifest_state",
        "z_author_prompt_assembly_manifest_digest",
    ),
    ("followup_author_execution_activation_state", "y_author_execution_activation_digest"),
    ("followup_author_input_materialization_state", "x_author_input_materialization_digest"),
    ("followup_author_execution_readiness_state", "w_author_execution_readiness_digest"),
    ("followup_author_gate_state", "v1_author_gate_digest"),
    ("followup_author_input_authority_state", "u1_authority_digest"),
    ("final_answer_packet", "stale packet"),
    ("final_answer_authority_projection", "stale authority"),
)


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (
            _update_state_attr(
                "followup_author_payload_construction_state",
                {"stale_digest": True},
            ),
            "AD|canonical AD inputs|stale packet|action",
        ),
        (
            _update_state_attr(
                "followup_author_payload_construction_projection",
                {"canonical_state": False},
            ),
            "canonical AD",
        ),
        (
            _clear_state_attr("followup_author_payload_construction_history"),
            "current AD history",
        ),
        *[
            (
                _update_state_attr(attr, {"stale_digest": True}),
                f"{match}|canonical AD inputs",
            )
            for attr, match in _STALE_DIGEST_CASES
        ],
        (_set_old_ready_status, "deferred|ready|canonical AD inputs"),
    ],
)
def test_ae_missing_stale_or_noncanonical_inputs_reject_atomically(
    mutator: Callable[[RunKernel], None],
    match: str,
) -> None:
    kernel = _kernel_through_ad()
    action = kernel.authorize_followup_author_execution_from_ad()
    result = _execute_ae(kernel, action=action)
    mutator(kernel)
    snapshot = snapshot_ae_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)
    assert_ae_boundary_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    "payload",
    [
        {"followup_author_execution_from_ad_state": {"status": "spoofed"}},
        {"author_observation": {"report_hash": "spoofed"}},
        {"final_answer_outcome": {"report_hash": "spoofed"}},
        {"prompt_text": "write the answer"},
        {"authority_block_text": "full authority block"},
        {"report_text": "not retained"},
        {"final_answer_text": "not allowed"},
        {"source_snippet": "raw source text"},
        {"model_response": "not allowed"},
        {"product_output": "ready answer"},
        {"executable_author_input_payload": {"status": "author_input_ready"}},
        {"fake_model_used": False},
    ],
)
def test_ae_caller_supplied_prompt_payload_model_response_and_output_rejected(
    payload: dict[str, Any],
) -> None:
    kernel = _kernel_through_ad()
    with pytest.raises(
        RunKernelTransitionError,
        match="caller-supplied|retain|closed text|requires|ready",
    ):
        kernel.authorize_followup_author_execution_from_ad(inputs=payload)


def test_ae_spoofed_observation_is_rebuilt_or_rejected_atomically() -> None:
    kernel = _kernel_through_ad()
    action = kernel.authorize_followup_author_execution_from_ad()
    result = _execute_ae(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["ag96i3_author_execution_from_ad_ref"][
        "author_execution_from_ad_ref_id"
    ] = "spoofed-ref"
    spoofed["author_observation"]["report_hash"] = "spoofed-report"
    kernel.reduce(_ae_observation_from_state(action, spoofed))
    state = kernel.state.followup_author_execution_from_ad_state
    assert state["ag96i3_author_execution_from_ad_ref"][
        "author_execution_from_ad_ref_id"
    ] != "spoofed-ref"
    assert state["author_observation"]["report_hash"] != "spoofed-report"
    assert kernel.state.author_observation["report_hash"] != "spoofed-report"

    kernel = _kernel_through_ad()
    action = kernel.authorize_followup_author_execution_from_ad()
    result = _execute_ae(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["report_text"] = "retain this report"
    snapshot = snapshot_ae_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="retain"):
        kernel.reduce(_ae_observation_from_state(action, spoofed))
    assert_ae_boundary_snapshot_unchanged(kernel, snapshot)


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
        lambda: _stale_ad_action_and_observation(),
    ],
)
def test_ae_rejects_stale_upstream_reductions_after_success(
    factory: Callable[[], tuple[RunKernel, Any, Observation]],
) -> None:
    source_kernel, stale_action, stale_observation = factory()
    kernel = _kernel_through_ad()
    _consume_ae(kernel)
    _, injected_observation = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_action,
        stale_observation,
    )
    snapshot = snapshot_ae_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="AG-96I3AE|stale"):
        kernel.reduce(injected_observation)
    assert_ae_boundary_snapshot_unchanged(kernel, snapshot)


def test_ae_duplicate_and_old_ready_status_guards() -> None:
    kernel = _kernel_through_ad()
    first_action = kernel.authorize_followup_author_execution_from_ad()
    first_result = _execute_ae(kernel, action=first_action)
    duplicate_action = kernel.authorize_followup_author_execution_from_ad()
    duplicate_result = _execute_ae(kernel, action=duplicate_action)

    kernel.reduce(first_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already observed"):
        kernel.authorize_followup_author_execution_from_ad()
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3AE"):
        kernel.reduce(duplicate_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(first_result.observation)
    with pytest.raises(RunKernelTransitionError, match="consume AG-96I3AD"):
        kernel.authorize_author_execution()

    kernel = _kernel_through_ad()
    kernel.state.final_answer_packet["author_payload_ref"][
        "status"
    ] = "author_input_ready"
    kernel.state.final_answer_authority_projection["author_payload_ref"][
        "status"
    ] = "author_input_ready"
    with pytest.raises(RunKernelTransitionError, match="rejects executable"):
        kernel.authorize_followup_author_execution_from_ad()


def test_ae_requires_ad_before_authorization() -> None:
    kernel = _kernel_through_ac()
    with pytest.raises(RunKernelTransitionError, match="requires reduced AD"):
        kernel.authorize_followup_author_execution_from_ad()


def test_ae_static_guards_keep_legacy_model_product_pipeline_and_live_closed() -> None:
    runtime_path = ROOT / "core" / "followup_author_execution_from_ad_runtime.py"
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
    ae_sections = [
        run_kernel_source.split(
            "def authorize_followup_author_execution_from_ad",
            1,
        )[1].split("def authorize_followup_author_observation", 1)[0],
        run_kernel_source.split(
            "if action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD:",
            1,
        )[1].split(
            "self.state.reduced_action_ids.add(action.action_id)",
            1,
        )[0],
        run_kernel_source.split(
            "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD:",
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
        for section in ae_sections:
            assert forbidden not in section
    for forbidden_call in (
        "execute_author_action(",
        "ask_model(",
        "ActionType.AUTHOR_EXECUTE",
        "ObservationType.AUTHOR_OUTPUT_OBSERVED",
        "authorize_author_execution(",
    ):
        assert forbidden_call not in runtime_source
        for section in ae_sections:
            assert forbidden_call not in section

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3ae" not in pipeline_source.casefold()
    assert "followup_author_execution_from_ad" not in pipeline_source


def _kernel_through_ad() -> RunKernel:
    kernel = _kernel_through_ac()
    _consume_ad(kernel)
    return kernel


def _execute_ae(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_author_execution_from_ad_action(
        action,
        **_ae_runtime_kwargs(kernel),
    )


def _ae_runtime_kwargs(kernel: RunKernel) -> dict[str, Any]:
    state = kernel.state
    kwargs = {
        f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
        for prefix in _AE_RUNTIME_PREFIXES
        for suffix in ("state", "projection", "history")
    }
    kwargs["final_answer_packet"] = state.final_answer_packet
    kwargs["final_answer_authority_projection"] = (
        state.final_answer_authority_projection
    )
    return kwargs


def _consume_ae(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_author_execution_from_ad()
    result = _execute_ae(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _stale_ad_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_ac()
    action = kernel.authorize_followup_author_payload_construction()
    result = _execute_ad(kernel, action=action)
    return kernel, action, result.observation


def _ae_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_author_execution_from_ad_observed",
        status="completed",
        payload={"followup_author_execution_from_ad_state": state},
    )


def _changed_keys(before: dict[str, Any], after: dict[str, Any]) -> set[str]:
    return {key for key in set(before) | set(after) if before.get(key) != after.get(key)}


def _assert_author_observation(
    author_observation: dict[str, Any],
    state: dict[str, Any],
) -> None:
    assert author_observation["owner"] == "RunKernel.FollowupAuthorExecutionFromAD"
    assert author_observation["canonical_state"] is True
    assert author_observation["packet_id"] == state["packet_id"]
    assert author_observation["payload_envelope_id"] == state["payload_envelope_id"]
    assert author_observation["payload_envelope_digest"] == (
        state["payload_envelope_digest"]
    )
    assert author_observation["prompt_text_digest"] == state["prompt_text_digest"]
    assert author_observation["prompt_text_length"] == state["prompt_text_length"]
    assert author_observation["author_report_text_digest"] == (
        state["author_report_text_digest"]
    )
    assert author_observation["author_report_text_length"] == (
        state["author_report_text_length"]
    )
    _assert_ae_closed_surface(author_observation)


def _assert_final_answer_outcome(
    final_answer_outcome: dict[str, Any],
    state: dict[str, Any],
    author_observation: dict[str, Any],
) -> None:
    assert final_answer_outcome["owner"] == (
        "RunKernel.FollowupAuthorExecutionFromADOutcome"
    )
    assert final_answer_outcome["canonical_state"] is True
    assert final_answer_outcome["packet_id"] == state["packet_id"]
    assert final_answer_outcome["payload_envelope_id"] == state["payload_envelope_id"]
    assert final_answer_outcome["author_observation_id"] == (
        author_observation["author_observation_id"]
    )
    assert final_answer_outcome["author_observation_digest"] == (
        followup_projection_digest(author_observation)
    )
    assert final_answer_outcome["author_report_text_digest"] == (
        state["author_report_text_digest"]
    )
    assert final_answer_outcome["author_report_text_length"] == (
        state["author_report_text_length"]
    )
    _assert_ae_closed_surface(final_answer_outcome)


def _assert_ae_closed_surface(surface: dict[str, Any]) -> None:
    false_keys = """
        author_input_ready author_execution_allowed author_activation_allowed
        real_model_called ask_model_called execute_author_action_called
        prompt_text_retained report_text_retained final_text_retained
        final_text_included product_answer_ready citation_strings_included
        ordered_product_source_output_created
    """.split()
    for key in false_keys:
        if key in surface:
            assert surface[key] is False
    for key in """
        fake_model_used author_observation_created final_answer_outcome_created
        live_validation_not_run not_for_product_answer_activation
    """.split():
        if key in surface:
            assert surface[key] is True
    if "author_execution_deferred" in surface:
        assert surface["author_execution_deferred"] is True


def _assert_no_closed_payload_text(value: Any) -> None:
    forbidden_keys = """
        prompt_text authority_block_text report_text fake_report_text
        final_answer_text answer_text ordered_sources ordered_product_source_output
        source_snippet snippet author_input_payload executable_author_input_payload
        product_output model_response raw_text private_payload
    """.split()
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden_keys
            _assert_no_closed_payload_text(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_no_closed_payload_text(child)
