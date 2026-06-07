import ast
import copy
import json
import subprocess
from pathlib import Path

from core.answer_contract_runtime_handoff import (
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
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


def _source(source_id="src-1"):
    return InferenceSourceAttribution(
        source_id=source_id,
        source_class="official_current_rules",
        source_tier="official",
    )


def _premise(
    premise_id="premise-1",
    source_id="src-premise-1",
    *,
    conflict_impact=PremiseConflictImpact.NONE,
    source_bound_numeric=False,
    satisfies_required_source_obligation=True,
):
    return SourcedPremise(
        premise_id=premise_id,
        claim_text=f"Premise {premise_id}",
        source_attribution=_source(source_id),
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


def _visibility(path):
    state = build_indirect_inference_runtime_handoff(path).to_controller_state()
    return state["paths"][0]


def test_directly_sourced_target_posture_survives_runtime_visibility():
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

    visible = _visibility(path)

    assert visible["path_posture"] == InferencePosture.DIRECTLY_SOURCED.value
    assert visible["target_claim_posture"] == InferencePosture.DIRECTLY_SOURCED.value
    assert visible["support_marker"] == "direct"
    assert visible["directly_sourced_target"] is True


def test_balanced_one_hop_inferred_path_preserves_mode_recommendation_and_sources():
    path = InferencePath(
        path_id="inferred-path",
        target_claim=_target(),
        premises=(_premise("premise-a", "src-a"),),
        bridges=(_bridge("bridge-a", "src-rel-a"),),
        mode=InferenceModePolicy.BALANCED,
        depth=1,
    )

    visible = _visibility(path)

    assert visible["path_posture"] == InferencePosture.INFERRED_FROM_SOURCED_PREMISES.value
    assert visible["support_marker"] == "inferred"
    assert visible["inference_mode"] == InferenceModePolicy.BALANCED.value
    assert visible["path_recommendation"] == PathRecommendation.MAY_STATE.value
    assert visible["premise_ids"] == ["premise-a"]
    assert visible["premise_source_ids"] == ["src-a"]


def test_speculative_or_unsupported_posture_is_not_upgraded():
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

    visible = _visibility(path)

    assert visible["path_posture"] == InferencePosture.SPECULATIVE.value
    assert visible["path_recommendation"] == PathRecommendation.UNSUPPORTED.value
    assert visible["support_marker"] == "speculative"
    assert visible["inferred_target"] is False


def test_ag78b_evaluator_result_remains_authoritative_after_handoff():
    path = InferencePath(
        path_id="override-attempt",
        target_claim=_target(),
        premises=(),
        bridges=(),
        posture=InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
        recommendation=PathRecommendation.MAY_STATE,
    )

    visible = _visibility(path)

    assert path.posture == InferencePosture.UNSUPPORTED
    assert path.recommendation == PathRecommendation.UNSUPPORTED
    assert visible["path_posture"] == InferencePosture.UNSUPPORTED.value
    assert visible["path_recommendation"] == PathRecommendation.UNSUPPORTED.value
    assert visible["evaluator_authoritative_posture_recommendation"] is True


def test_constructor_override_promotion_remains_impossible_through_handoff():
    path = InferencePath(
        path_id="invalid-promotion",
        target_claim=_target(),
        premises=(_premise(satisfies_required_source_obligation=False),),
        bridges=(_bridge(),),
        posture=InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
        recommendation=PathRecommendation.MAY_STATE,
    )

    visible = _visibility(path)

    assert visible["path_posture"] == InferencePosture.UNSUPPORTED.value
    assert visible["path_recommendation"] == PathRecommendation.UNSUPPORTED.value
    assert visible["support_marker"] == "unsupported"
    assert visible["inferred_target"] is False


def test_premise_and_bridge_relationship_source_ids_survive_controller_and_trace():
    path = InferencePath(
        path_id="source-serialization",
        target_claim=_target(),
        premises=(_premise("premise-source", "src-premise"),),
        bridges=(_bridge("bridge-source", "src-relationship"),),
    )
    handoff = build_indirect_inference_runtime_handoff(path)

    controller = handoff.to_controller_state()
    trace = handoff.to_trace_fragment()[INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY]

    assert controller["paths"][0]["premise_source_ids"] == ["src-premise"]
    assert controller["paths"][0]["relationship_source_ids"] == ["src-relationship"]
    assert trace["paths"][0]["premise_source_ids"] == ["src-premise"]
    assert trace["paths"][0]["relationship_source_ids"] == ["src-relationship"]


def test_ag77_premise_conflict_impact_survives_serialization():
    path = InferencePath(
        path_id="conflict-impact",
        target_claim=_target(),
        premises=(
            _premise(conflict_impact=PremiseConflictImpact.BLOCKS),
        ),
        bridges=(_bridge(),),
    )

    visible = _visibility(path)

    assert visible["path_posture"] == InferencePosture.BLOCKED_BY_PREMISE_CONFLICT.value
    assert visible["ag77_premise_conflict_impact"] == [PremiseConflictImpact.BLOCKS.value]


def test_source_bound_numeric_range_bound_marker_and_resolved_scalar_survive():
    path = InferencePath(
        path_id="range-bound",
        target_claim=_target(resolved_scalar=True),
        premises=(
            _premise(
                conflict_impact=PremiseConflictImpact.RANGE_BOUNDS,
                source_bound_numeric=True,
            ),
        ),
        bridges=(_bridge(),),
    )

    visible = _visibility(path)

    assert visible["path_posture"] == InferencePosture.RANGE_BOUND_INFERENCE.value
    assert visible["source_bound_numeric_present"] is True
    assert visible["source_bound_numeric_marker"] == "range_bound"
    assert visible["resolved_scalar"] is False


def test_lower_tier_non_satisfaction_survives_and_does_not_become_inferred_support():
    path = InferencePath(
        path_id="non-satisfying",
        target_claim=_target(),
        premises=(
            _premise(
                conflict_impact=PremiseConflictImpact.NON_SATISFYING_FOR_OBLIGATION,
                satisfies_required_source_obligation=False,
            ),
        ),
        bridges=(_bridge(),),
    )

    visible = _visibility(path)

    assert visible["lower_tier_non_satisfaction"] is True
    assert visible["path_posture"] == InferencePosture.UNSUPPORTED.value
    assert visible["support_marker"] == "unsupported"
    assert visible["inferred_target"] is False


def test_empty_input_produces_no_inference_no_answer_impact_visibility():
    state = build_indirect_inference_runtime_handoff(()).to_controller_state()

    assert state["inference_available"] is False
    assert state["no_inference_input"] is True
    assert state["no_answer_impact"] is True
    assert state["answer_behavior_changed"] is False
    assert state["paths"] == []


def test_controller_and_trace_serialization_are_json_safe():
    path = InferencePath(
        path_id="json-safe",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(_bridge(),),
    )
    handoff = build_indirect_inference_runtime_handoff(path)

    assert json.loads(json.dumps(handoff.to_controller_state()))["paths"][0]["path_id"] == "json-safe"
    assert json.loads(json.dumps(handoff.to_trace_fragment()))[
        INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY
    ]["paths"][0]["path_id"] == "json-safe"


def test_ag78b_objects_are_immutable_inputs_for_handoff():
    path = InferencePath(
        path_id="immutable-input",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(_bridge(),),
    )
    before = copy.deepcopy(path.to_controller_state())

    build_indirect_inference_runtime_handoff(path).to_controller_state()

    assert path.to_controller_state() == before


def test_static_protected_import_guard_for_runtime_helper():
    module = ast.parse(Path("core/indirect_inference_runtime_handoff.py").read_text())
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
        "pipeline_orchestrator",
    )
    assert "core.indirect_inference_contract" in imports
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
            or "session_output_projection" in diff
                or "runtime_prompt_assembly" in diff
                or "retrieval_dispatch_runtime" in diff
                or "retrieval_stop_trace_projection" in diff
        )


def test_answer_contract_runtime_handoff_attaches_visibility_only_when_supplied():
    no_inference = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(query="q")
    )
    assert no_inference.indirect_inference_runtime_handoff is None
    assert INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY not in no_inference.execution_trace_fragment()

    path = InferencePath(
        path_id="runtime-attach",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(_bridge(),),
    )
    with_inference = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(query="q", indirect_inference_paths=(path,))
    )

    assert with_inference.indirect_inference_runtime_handoff is not None
    assert INDIRECT_INFERENCE_RUNTIME_HANDOFF_TRACE_KEY in with_inference.execution_trace_fragment()
