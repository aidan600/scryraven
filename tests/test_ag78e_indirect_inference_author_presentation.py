import ast
import json
import subprocess
from pathlib import Path

from core.answer_contract_runtime_handoff import (
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)
from core.indirect_inference_answer_posture_activation import (
    build_indirect_inference_answer_posture_activation,
)
from core.indirect_inference_author_presentation_handoff import (
    INDIRECT_INFERENCE_AUTHOR_PRESENTATION_TRACE_KEY,
    INFERRED_FROM_SOURCED_PREMISES_LABEL,
    IndirectInferenceAuthorPresentationLabel,
    build_indirect_inference_author_presentation_handoff,
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


def _presentation(path):
    runtime_handoff = build_indirect_inference_runtime_handoff(path)
    activation = build_indirect_inference_answer_posture_activation(runtime_handoff)
    assert activation is not None
    handoff = build_indirect_inference_author_presentation_handoff(activation)
    assert handoff is not None
    return handoff.to_controller_state()["presentation_facts"]["claims"][0]


def test_directly_sourced_claim_remains_presented_as_directly_sourced():
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

    claim = _presentation(path)

    assert claim["presentation_label"] == IndirectInferenceAuthorPresentationLabel.DIRECTLY_SOURCED.value
    assert claim["human_label"] == "directly sourced"
    assert claim["directly_sourced"] is True
    assert claim["conclusion_direct_source_ids"] == ["src-target-1"]
    assert claim["source_attribution_mode"] == "direct_source_statement"


def test_inferred_from_sourced_premises_claim_is_labeled_as_inferred():
    path = InferencePath(
        path_id="inferred-path",
        target_claim=_target(),
        premises=(_premise("premise-a", "src-a"),),
        bridges=(_bridge("bridge-a", "src-rel-a"),),
        mode=InferenceModePolicy.BALANCED,
        depth=1,
    )

    claim = _presentation(path)

    assert claim["presentation_label"] == (
        IndirectInferenceAuthorPresentationLabel.INFERRED_FROM_SOURCED_PREMISES.value
    )
    assert INFERRED_FROM_SOURCED_PREMISES_LABEL in claim["human_label"]
    assert claim["inference_label_required"] is True
    assert claim["directly_sourced"] is False


def test_inferred_conclusion_is_not_presented_as_directly_source_stated():
    path = InferencePath(
        path_id="no-launder-path",
        target_claim=_target(),
        premises=(_premise("premise-a", "src-a"),),
        bridges=(_bridge("bridge-a", "src-rel-a"),),
    )

    claim = _presentation(path)

    assert claim["directly_sourced"] is False
    assert claim["conclusion_direct_source_ids"] == []
    assert claim["source_attribution_mode"] == "premise_or_bridge_support_only"
    assert claim["premise_bridge_sources_support_direct_conclusion"] is False
    assert "do not mean the inferred conclusion was directly source-stated" in claim[
        "premise_bridge_source_attribution_boundary"
    ]


def test_premise_and_bridge_source_ids_remain_visible_for_attribution():
    path = InferencePath(
        path_id="attribution-path",
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

    claim = _presentation(path)

    assert claim["premise_ids"] == ["premise-a"]
    assert claim["premise_source_ids"] == ["src-a"]
    assert claim["bridge_ids"] == ["bridge-a"]
    assert claim["bridge_types"] == [InferenceBridgeType.SOURCE_STATED_RELATIONSHIP.value]
    assert claim["bridge_relationship_source_ids"] == ["src-rel-a"]


def test_speculative_unsupported_path_is_not_presented_as_supported_inference():
    path = InferencePath(
        path_id="speculative-path",
        target_claim=_target(InferencePosture.SPECULATIVE),
        premises=(_premise(),),
        bridges=(
            _bridge(
                bridge_type=InferenceBridgeType.MODEL_ASSUMED_SPECULATIVE,
                strength=BridgeStrength.SPECULATIVE,
                valid=False,
            ),
        ),
        posture=InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
        recommendation=PathRecommendation.MAY_STATE,
    )

    claim = _presentation(path)

    assert claim["presentation_label"] == (
        IndirectInferenceAuthorPresentationLabel.SPECULATIVE_OR_UNSUPPORTED.value
    )
    assert claim["speculative_or_unsupported"] is True
    assert claim["inference_label_required"] is False
    assert claim["human_label"] != INFERRED_FROM_SOURCED_PREMISES_LABEL


def test_blocked_by_premise_conflict_is_not_presented_as_supported_inference():
    path = InferencePath(
        path_id="conflict-path",
        target_claim=_target(),
        premises=(_premise(conflict_impact=PremiseConflictImpact.BLOCKS),),
        bridges=(_bridge(),),
    )

    claim = _presentation(path)

    assert claim["presentation_label"] == (
        IndirectInferenceAuthorPresentationLabel.BLOCKED_BY_PREMISE_CONFLICT.value
    )
    assert claim["blocked_by_premise_conflict"] is True
    assert claim["inference_label_required"] is False
    assert claim["human_label"] == "blocked by premise conflict"


def test_range_bound_source_bound_numeric_is_unresolved_not_scalar():
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

    claim = _presentation(path)

    assert claim["presentation_label"] == (
        IndirectInferenceAuthorPresentationLabel.RANGE_BOUND_OR_SOURCE_BOUND.value
    )
    assert claim["range_bound_or_source_bound"] is True
    assert claim["resolved_scalar"] is False
    assert "range-bound" in claim["human_label"]


def test_lower_tier_non_satisfaction_does_not_satisfy_stronger_obligation():
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

    claim = _presentation(path)

    assert claim["lower_tier_non_satisfaction"] is True
    assert claim["stronger_obligation_satisfied"] is False
    assert claim["presentation_label"] == (
        IndirectInferenceAuthorPresentationLabel.SPECULATIVE_OR_UNSUPPORTED.value
    )


def test_answer_contract_runtime_handoff_attaches_author_presentation_only_with_ag78d_state():
    no_inference = build_runtime_answer_contract_handoff(RuntimeAnswerContractFacts(query="q"))
    assert no_inference.indirect_inference_author_presentation_handoff is None
    assert INDIRECT_INFERENCE_AUTHOR_PRESENTATION_TRACE_KEY not in no_inference.execution_trace_fragment()

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
    assert with_inference.indirect_inference_author_presentation_handoff is not None
    assert INDIRECT_INFERENCE_AUTHOR_PRESENTATION_TRACE_KEY in trace
    assert trace[INDIRECT_INFERENCE_AUTHOR_PRESENTATION_TRACE_KEY]["ag78d_state_key"] == (
        "indirect_inference_answer_posture_activation"
    )


def test_author_presentation_trace_is_json_safe_and_behavior_flags_closed():
    path = InferencePath(
        path_id="json-path",
        target_claim=_target(),
        premises=(_premise(),),
        bridges=(_bridge(),),
    )
    runtime_handoff = build_indirect_inference_runtime_handoff(path)
    activation = build_indirect_inference_answer_posture_activation(runtime_handoff)
    handoff = build_indirect_inference_author_presentation_handoff(activation)
    assert handoff is not None

    controller = json.loads(json.dumps(handoff.to_controller_state()))

    assert controller["provider_behavior_changed"] is False
    assert controller["search_behavior_changed"] is False
    assert controller["retrieval_behavior_changed"] is False
    assert controller["cache_behavior_changed"] is False
    assert controller["db_session_runoutcome_behavior_changed"] is False
    assert controller["scrutineer_behavior_changed"] is False
    assert controller["economist_followup_behavior_changed"] is False
    assert controller["pipeline_orchestrator_behavior_changed"] is False
    assert controller["runtime_inference_detection_changed"] is False
    assert controller["citation_laundering_guard_enabled"] is True


def test_static_protected_import_guard_for_author_presentation_helper():
    module = ast.parse(
        Path("core/indirect_inference_author_presentation_handoff.py").read_text()
    )
    imports = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    forbidden_fragments = (
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
    assert "core.indirect_inference_answer_posture_activation" in imports
    assert "core.indirect_inference_contract" in imports
    assert not any(
        fragment in imported.casefold()
        for imported in imports
        for fragment in forbidden_fragments
    )


def test_pipeline_orchestrator_only_has_unrelated_scrutineer_handoff_touch():
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        check=True,
        capture_output=True,
        text=True,
    )
    diff = subprocess.run(
        ["git", "diff", "--", "core/pipeline_orchestrator.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    if "core/pipeline_orchestrator.py" in result.stdout.splitlines():
        assert (
            "core.scrutineer_remediation_runtime_handoff" in diff
            or "synthesis_evaluator_supplemental_search_runtime_handoff" in diff
            or "final_answer_runtime_adapter" in diff
            or "FinalAnswerPacket" in diff
            or "pre_author_source_obligation_projection" in diff
            or "session_output_projection" in diff
                or "runtime_prompt_assembly" in diff
                or "retrieval_dispatch_runtime" in diff
                or "retrieval_stop_trace_projection" in diff
        )
    else:
        assert "core/pipeline_orchestrator.py" not in result.stdout.splitlines()
