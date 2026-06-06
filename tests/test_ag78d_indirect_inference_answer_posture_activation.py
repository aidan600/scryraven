import ast
import copy
import json
import subprocess
from pathlib import Path

from core.answer_contract_runtime_handoff import (
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)
from core.indirect_inference_answer_posture_activation import (
    INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY,
    build_indirect_inference_answer_posture_activation,
)
from core.indirect_inference_contract import (
    BridgeStrength,
    InferenceBridge,
    InferenceBridgeType,
    InferenceModePolicy,
    InferencePath,
    InferencePosture,
    InferenceSourceAttribution,
    PathRecommendation,
    PremiseConflictImpact,
    SourcedPremise,
    TargetClaim,
)
from core.indirect_inference_runtime_handoff import (
    INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY,
    build_indirect_inference_runtime_handoff,
)


def _source(source_id="src-1", *, source_tier="official"):
    return InferenceSourceAttribution(
        source_id=source_id,
        source_class="official_current_rules",
        source_tier=source_tier,
        title=f"Source {source_id}",
    )


def _target(
    posture=InferencePosture.UNSUPPORTED,
    *,
    directly_sourced=False,
    resolved_scalar=False,
):
    return TargetClaim(
        claim_id="target-1",
        claim_text="Target claim text",
        posture=posture,
        directly_sourced=directly_sourced,
        source_attributions=(_source("src-target-1"),) if directly_sourced else (),
        resolved_scalar=resolved_scalar,
        value=42 if resolved_scalar else None,
    )


def _premise(
    premise_id="premise-1",
    source_id="src-premise-1",
    *,
    conflict_impact=PremiseConflictImpact.NONE,
    source_bound_numeric=False,
    satisfies_required_source_obligation=True,
    source_tier="official",
):
    return SourcedPremise(
        premise_id=premise_id,
        claim_text=f"Premise {premise_id}",
        source_attribution=_source(source_id, source_tier=source_tier),
        conflict_impact=conflict_impact,
        source_bound_numeric=source_bound_numeric,
        satisfies_required_source_obligation=satisfies_required_source_obligation,
        value=10 if source_bound_numeric else None,
        unit="widgets" if source_bound_numeric else None,
    )


def _bridge(
    bridge_id="bridge-1",
    source_id="src-bridge-1",
    *,
    bridge_type=InferenceBridgeType.MATHEMATICAL,
    strength=BridgeStrength.EXACT,
    valid=True,
):
    return InferenceBridge(
        bridge_id=bridge_id,
        bridge_type=bridge_type,
        description="Source-stated relationship from premise to target.",
        strength=strength,
        allowed_modes=(InferenceModePolicy.BALANCED, InferenceModePolicy.DEEP),
        source_attributions=(_source(source_id),),
        valid=valid,
    )


def _activation(path):
    handoff = build_indirect_inference_runtime_handoff(path)
    activation = build_indirect_inference_answer_posture_activation(handoff)
    assert activation is not None
    return activation.to_controller_state()


def _effect(path):
    return _activation(path)["path_effects"][0]


def test_directly_sourced_ag78c_posture_activates_direct_controller_posture():
    path = InferencePath(
        path_id="direct-path",
        target_claim=_target(
            InferencePosture.DIRECTLY_SOURCED,
            directly_sourced=True,
            resolved_scalar=True,
        ),
        premises=(),
        bridges=(),
        mode=InferenceModePolicy.FAST,
    )

    state = _activation(path)
    effect = state["path_effects"][0]

    assert effect["answer_posture"] == InferencePosture.DIRECTLY_SOURCED.value
    assert effect["directly_sourced"] is True
    assert effect["direct_source_ids"] == ["src-target-1"]
    assert state["direct_claim_count"] == 1


def test_balanced_one_hop_inferred_activation_marks_not_directly_sourced():
    path = InferencePath(
        path_id="inferred-path",
        target_claim=_target(),
        premises=(_premise("premise-a", "src-a"),),
        bridges=(_bridge("bridge-a", "src-rel-a"),),
        mode=InferenceModePolicy.BALANCED,
        depth=1,
    )

    state = _activation(path)
    effect = state["path_effects"][0]

    assert effect["answer_posture"] == InferencePosture.INFERRED_FROM_SOURCED_PREMISES.value
    assert effect["directly_sourced"] is False
    assert effect["requires_inference_label"] is True
    assert state["final_answer_behavior_changed"] is False
    assert state["author_behavior_changed"] is False


def test_inferred_activation_preserves_premise_bridge_and_source_identity():
    path = InferencePath(
        path_id="identity-path",
        target_claim=_target(),
        premises=(_premise("premise-a", "src-a"),),
        bridges=(
            _bridge(
                "bridge-a",
                "src-rel-a",
                bridge_type=InferenceBridgeType.SOURCE_STATED_RELATIONSHIP,
            ),
        ),
    )

    effect = _effect(path)

    assert effect["premise_ids"] == ["premise-a"]
    assert effect["premise_source_ids"] == ["src-a"]
    assert effect["bridge_ids"] == ["bridge-a"]
    assert effect["bridge_types"] == [InferenceBridgeType.SOURCE_STATED_RELATIONSHIP.value]
    assert effect["relationship_source_ids"] == ["src-rel-a"]


def test_inferred_label_does_not_change_author_or_final_answer_flags():
    path = InferencePath(
        path_id="label-path",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(_bridge(),),
    )

    state = _activation(path)
    effect = state["path_effects"][0]

    assert effect["requires_inference_label"] is True
    assert state["final_answer_behavior_changed"] is False
    assert state["author_behavior_changed"] is False
    assert state["citation_behavior_changed"] is False


def test_speculative_model_assumed_path_remains_unsupported_speculative():
    path = InferencePath(
        path_id="speculative-path",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(
            _bridge(
                bridge_type=InferenceBridgeType.MODEL_ASSUMED_SPECULATIVE,
                strength=BridgeStrength.SPECULATIVE,
            ),
        ),
    )

    effect = _effect(path)

    assert effect["path_posture"] == InferencePosture.SPECULATIVE.value
    assert effect["answer_posture"] == InferencePosture.SPECULATIVE.value
    assert effect["speculative_or_unsupported"] is True
    assert effect["requires_inference_label"] is False


def test_constructor_override_promotion_remains_impossible_through_activation():
    path = InferencePath(
        path_id="override-path",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(_bridge(valid=False),),
        posture=InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
        recommendation=PathRecommendation.MAY_STATE,
    )

    effect = _effect(path)

    assert path.posture == InferencePosture.UNSUPPORTED
    assert path.recommendation == PathRecommendation.UNSUPPORTED
    assert effect["answer_posture"] == InferencePosture.UNSUPPORTED.value
    assert effect["speculative_or_unsupported"] is True


def test_premise_conflict_blocks_activation_posture():
    path = InferencePath(
        path_id="conflict-path",
        target_claim=_target(),
        premises=(_premise(conflict_impact=PremiseConflictImpact.BLOCKS),),
        bridges=(_bridge(),),
    )

    state = _activation(path)
    effect = state["path_effects"][0]

    assert effect["answer_posture"] == InferencePosture.BLOCKED_BY_PREMISE_CONFLICT.value
    assert effect["blocked_by_premise_conflict"] is True
    assert state["blocked_by_premise_conflict_count"] == 1


def test_range_bound_source_bound_numeric_preserves_unresolved_scalar():
    path = InferencePath(
        path_id="range-path",
        target_claim=_target(resolved_scalar=True),
        premises=(
            _premise(
                conflict_impact=PremiseConflictImpact.RANGE_BOUNDS,
                source_bound_numeric=True,
            ),
        ),
        bridges=(_bridge(),),
    )

    effect = _effect(path)

    assert effect["answer_posture"] == InferencePosture.RANGE_BOUND_INFERENCE.value
    assert effect["range_bound_or_source_bound"] is True
    assert effect["resolved_scalar"] is False


def test_lower_tier_non_satisfaction_prevents_stronger_obligation_satisfaction():
    path = InferencePath(
        path_id="lower-tier-path",
        target_claim=_target(),
        premises=(
            _premise(
                conflict_impact=PremiseConflictImpact.NON_SATISFYING_FOR_OBLIGATION,
                satisfies_required_source_obligation=False,
                source_tier="lower",
            ),
        ),
        bridges=(_bridge(),),
    )

    state = _activation(path)
    effect = state["path_effects"][0]

    assert effect["lower_tier_non_satisfaction"] is True
    assert effect["stronger_obligation_satisfied"] is False
    assert effect["answer_posture"] == InferencePosture.UNSUPPORTED.value
    assert state["lower_tier_non_satisfaction_count"] == 1


def test_empty_no_inference_state_remains_no_answer_impact():
    handoff = build_indirect_inference_runtime_handoff(())
    activation = build_indirect_inference_answer_posture_activation(handoff)
    assert activation is not None
    state = activation.to_controller_state()

    assert state["path_effects"] == []
    assert state["top_level_posture_summary"]["no_answer_impact"] is True
    assert state["final_answer_behavior_changed"] is False
    assert state["author_behavior_changed"] is False


def test_ag78b_and_ag78c_inputs_are_immutable_for_activation():
    path = InferencePath(
        path_id="immutable-path",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(_bridge(),),
    )
    handoff = build_indirect_inference_runtime_handoff(path)
    before_path = copy.deepcopy(path.to_controller_state())
    before_handoff = copy.deepcopy(handoff.to_controller_state())

    build_indirect_inference_answer_posture_activation(handoff)

    assert path.to_controller_state() == before_path
    assert handoff.to_controller_state() == before_handoff


def test_json_safe_trace_and_controller_serialization():
    path = InferencePath(
        path_id="json-path",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(_bridge(),),
    )
    handoff = build_indirect_inference_runtime_handoff(path)
    activation = build_indirect_inference_answer_posture_activation(handoff)
    assert activation is not None

    controller = json.loads(json.dumps(activation.to_controller_state()))
    trace = json.loads(json.dumps(activation.to_trace_fragment()))

    assert controller["path_effects"][0]["path_id"] == "json-path"
    assert trace[INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY]["path_effects"][0][
        "path_id"
    ] == "json-path"


def test_static_protected_import_guard_for_activation_helper():
    module = ast.parse(
        Path("core/indirect_inference_answer_posture_activation.py").read_text()
    )
    imports = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    forbidden_fragments = (
        "author",
        "prompt",
        "citation",
        "provider",
        "search",
        "retrieval",
        "scrutineer",
        "remediation",
        "economist",
        "followup",
        "follow_up",
        "db",
        "session",
        "run_outcome",
        "cache",
        "live_validation",
        "pipeline_orchestrator",
    )
    assert "core.indirect_inference_contract" in imports
    assert "core.indirect_inference_runtime_handoff" in imports
    assert not any(
        fragment in imported.casefold()
        for imported in imports
        for fragment in forbidden_fragments
    )


def test_pipeline_orchestrator_remains_untouched_in_diff():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        check=True,
        capture_output=True,
        text=True,
    )

    if "core/pipeline_orchestrator.py" in result.stdout.splitlines():
        diff = subprocess.run(
            ["git", "diff", "--", "core/pipeline_orchestrator.py"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert (
            "synthesis_evaluator_supplemental_search_runtime_handoff" in diff
            or "final_answer_runtime_adapter" in diff
            or "FinalAnswerPacket" in diff
            or "pre_author_source_obligation_projection" in diff
        )


def test_answer_contract_runtime_handoff_attaches_activation_only_with_ag78c_state():
    no_inference = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(query="q")
    )
    assert no_inference.indirect_inference_answer_posture_activation is None
    assert (
        INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY
        not in no_inference.execution_trace_fragment()
    )

    path = InferencePath(
        path_id="runtime-attach",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(_bridge(),),
    )
    with_inference = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(query="q", indirect_inference_paths=(path,))
    )

    trace = with_inference.execution_trace_fragment()
    assert with_inference.indirect_inference_answer_posture_activation is not None
    assert INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY in trace
    assert INDIRECT_INFERENCE_ANSWER_POSTURE_ACTIVATION_TRACE_KEY in trace
