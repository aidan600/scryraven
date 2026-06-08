import json
from pathlib import Path

from core.indirect_inference_contract import (
    BridgeStrength,
    InferenceBridge,
    InferenceBridgeType,
    InferenceModePolicy,
    InferencePath,
    InferencePosture,
    InferenceSourceAttribution,
    PremiseConflictImpact,
    SourcedPremise,
    TargetClaim,
)


def _source(source_id: str, *, source_class: str = "official", source_tier: str = "primary") -> InferenceSourceAttribution:
    return InferenceSourceAttribution(
        source_id=source_id,
        source_class=source_class,
        source_tier=source_tier,
        title=f"Source {source_id}",
        url=f"https://example.test/{source_id}",
        retrieved_at="2026-05-30",
        effective_period_start="2026-01-01",
        effective_period_end="2026-12-31",
        jurisdiction="US",
        scope="fixture",
    )


def _target(claim_id: str = "target-a", posture: str = InferencePosture.INFERRED_FROM_SOURCED_PREMISES) -> TargetClaim:
    return TargetClaim(
        claim_id=claim_id,
        claim_text="Target claim A",
        posture=posture,
        directly_sourced=posture == InferencePosture.DIRECTLY_SOURCED,
        source_attributions=(_source("source-a"),) if posture == InferencePosture.DIRECTLY_SOURCED else (),
        value=20,
        unit="USD",
    )


def _premise(
    premise_id: str,
    source_id: str,
    *,
    value: str | int | float = "fact",
    unit: str | None = None,
    conflict_impact: str = PremiseConflictImpact.NONE,
    source_class: str = "official",
    source_tier: str = "primary",
    source_bound_numeric: bool = False,
    satisfies_required_source_obligation: bool = True,
) -> SourcedPremise:
    return SourcedPremise(
        premise_id=premise_id,
        claim_text=f"Premise {premise_id} states {value}",
        source_attribution=_source(source_id, source_class=source_class, source_tier=source_tier),
        value=value,
        unit=unit,
        date_or_period="2026",
        effective_period_start="2026-01-01",
        effective_period_end="2026-12-31",
        jurisdiction="US",
        scope="fixture",
        conflict_impact=conflict_impact,
        source_bound_numeric=source_bound_numeric,
        satisfies_required_source_obligation=satisfies_required_source_obligation,
    )


def _bridge(
    bridge_id: str = "bridge-1",
    bridge_type: str = InferenceBridgeType.MATHEMATICAL,
    *,
    strength: str = BridgeStrength.EXACT,
    source_ids: tuple[str, ...] = (),
    allowed_modes: tuple[str, ...] = (InferenceModePolicy.BALANCED, InferenceModePolicy.DEEP),
) -> InferenceBridge:
    return InferenceBridge(
        bridge_id=bridge_id,
        bridge_type=bridge_type,
        description="Bridge derives A from sourced premises.",
        strength=strength,
        allowed_modes=allowed_modes,
        source_attributions=tuple(_source(source_id) for source_id in source_ids),
    )


def _path(
    *,
    mode: str = InferenceModePolicy.BALANCED,
    depth: int = 1,
    premises: tuple[SourcedPremise, ...] | None = None,
    bridges: tuple[InferenceBridge, ...] | None = None,
    target: TargetClaim | None = None,
    posture: str | None = None,
    recommendation: str | None = None,
) -> InferencePath:
    return InferencePath(
        path_id="path-1",
        target_claim=target or _target(),
        premises=premises if premises is not None else (_premise("premise-b", "source-b"),),
        bridges=bridges if bridges is not None else (_bridge(),),
        mode=mode,
        depth=depth,
        posture=posture,
        recommendation=recommendation,
    )


def test_direct_target_claim_represented_separately_from_inferred_target_claim() -> None:
    direct = _path(target=_target("target-direct", InferencePosture.DIRECTLY_SOURCED), premises=(), bridges=(), depth=0)
    inferred = _path(
        target=_target("target-inferred", InferencePosture.INFERRED_FROM_SOURCED_PREMISES),
        premises=(_premise("premise-b", "source-b"), _premise("premise-c", "source-c")),
        bridges=(_bridge(),),
    )

    assert direct.posture == "directly_sourced"
    assert inferred.posture == "inferred_from_sourced_premises"
    assert direct.to_controller_state()["directly_sourced_target"] is True
    assert inferred.to_controller_state()["directly_sourced_target"] is False
    assert inferred.to_controller_state()["target_claim"]["directly_sourced"] is False


def test_balanced_one_hop_mathematical_inference_preserves_premise_sources() -> None:
    path = _path(
        mode=InferenceModePolicy.BALANCED,
        depth=1,
        premises=(
            _premise("fee-per-unit", "source-fee", value=10, unit="USD/unit"),
            _premise("unit-count", "source-units", value=2, unit="unit"),
        ),
        bridges=(_bridge("multiply-fee-by-units", InferenceBridgeType.MATHEMATICAL),),
    )
    state = path.to_controller_state()

    assert state["mode"] == "balanced"
    assert state["depth"] == 1
    assert state["bridges"][0]["bridge_type"] == "mathematical"
    assert state["posture"] == "inferred_from_sourced_premises"
    assert state["premise_source_ids"] == ["source-fee", "source-units"]


def test_balanced_one_hop_definitional_inference_with_all_elements_sourced() -> None:
    path = _path(
        premises=(
            _premise("definition-elements", "source-definition", value="term requires elements x and y"),
            _premise("entity-elements", "source-entity", value="entity satisfies x and y"),
        ),
        bridges=(_bridge("definition-application", InferenceBridgeType.DEFINITIONAL),),
    )

    assert path.to_controller_state()["bridges"][0]["bridge_type"] == "definitional"
    assert path.posture == "inferred_from_sourced_premises"
    assert path.recommendation == "may_state"


def test_source_stated_relationship_bridge_preserves_relationship_source_separately() -> None:
    path = _path(
        premises=(_premise("input-premise", "source-input", value="input value"),),
        bridges=(
            _bridge(
                "relationship-rule",
                InferenceBridgeType.SOURCE_STATED_RELATIONSHIP,
                source_ids=("source-relationship",),
            ),
        ),
    )
    state = path.to_controller_state()

    assert state["premise_source_ids"] == ["source-input"]
    assert state["bridge_source_ids"] == ["source-relationship"]
    assert state["bridges"][0]["relationship_source_ids"] == ["source-relationship"]


def test_model_assumed_speculative_bridge_is_not_supported_inference() -> None:
    path = _path(
        bridges=(
            _bridge(
                "speculative-link",
                InferenceBridgeType.MODEL_ASSUMED_SPECULATIVE,
                strength=BridgeStrength.SPECULATIVE,
            ),
        ),
    )

    assert path.posture in {"speculative", "unsupported"}
    assert path.posture != "inferred_from_sourced_premises"
    assert path.recommendation == "unsupported"


def test_constructor_override_cannot_promote_speculative_bridge_to_supported_inference() -> None:
    path = _path(
        bridges=(
            _bridge(
                "speculative-link",
                InferenceBridgeType.MODEL_ASSUMED_SPECULATIVE,
                strength=BridgeStrength.SPECULATIVE,
            ),
        ),
        posture=InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
        recommendation="may_state",
    )

    assert path.posture == "speculative"
    assert path.recommendation == "unsupported"


def test_constructor_override_cannot_promote_blocked_premise_to_supported_inference() -> None:
    path = _path(
        premises=(_premise("blocked-premise", "source-b", conflict_impact=PremiseConflictImpact.BLOCKS),),
        posture=InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
        recommendation="may_state",
    )

    assert path.posture == "blocked_by_premise_conflict"
    assert path.recommendation == "decline"


def test_constructor_override_cannot_promote_fast_multi_premise_inference() -> None:
    path = _path(
        mode=InferenceModePolicy.FAST,
        premises=(_premise("premise-b", "source-b"), _premise("premise-c", "source-c")),
        bridges=(_bridge(allowed_modes=(InferenceModePolicy.FAST, InferenceModePolicy.BALANCED)),),
        posture=InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
        recommendation="may_state",
    )

    assert path.posture == "declined"
    assert path.recommendation == "decline"


def test_constructor_override_cannot_promote_balanced_multi_hop_inference() -> None:
    path = _path(
        mode=InferenceModePolicy.BALANCED,
        depth=2,
        bridges=(
            _bridge("bridge-1", InferenceBridgeType.MATHEMATICAL),
            _bridge("bridge-2", InferenceBridgeType.DEFINITIONAL),
        ),
        posture=InferencePosture.INFERRED_FROM_SOURCED_PREMISES,
        recommendation="may_state",
    )

    assert path.posture == "declined"
    assert path.recommendation == "decline"


def test_fast_mode_rejects_non_trivial_multi_premise_inference() -> None:
    path = _path(
        mode=InferenceModePolicy.FAST,
        premises=(_premise("premise-b", "source-b"), _premise("premise-c", "source-c")),
        bridges=(_bridge(allowed_modes=(InferenceModePolicy.FAST, InferenceModePolicy.BALANCED)),),
    )

    assert path.allowed_by_mode_policy is False
    assert path.posture in {"unsupported", "declined"}


def test_balanced_mode_rejects_multi_hop_inference() -> None:
    path = _path(
        mode=InferenceModePolicy.BALANCED,
        depth=2,
        bridges=(
            _bridge("bridge-1", InferenceBridgeType.MATHEMATICAL),
            _bridge("bridge-2", InferenceBridgeType.DEFINITIONAL),
        ),
    )

    assert path.allowed_by_mode_policy is False
    assert path.posture in {"unsupported", "declined"}


def test_deep_mode_can_represent_multi_hop_posture_without_final_answer_behavior() -> None:
    path = _path(
        mode=InferenceModePolicy.DEEP,
        depth=2,
        bridges=(
            _bridge("bridge-1", InferenceBridgeType.MATHEMATICAL),
            _bridge("bridge-2", InferenceBridgeType.DEFINITIONAL),
        ),
    )
    state = path.to_controller_state()

    assert state["mode"] == "deep"
    assert state["depth"] == 2
    assert state["allowed_by_mode_policy"] is True
    assert state["final_answer_behavior_changed"] is False
    assert state["author_behavior_changed"] is False


def test_premise_conflict_blocks_inference_when_ag77_marks_required_premise_blocking() -> None:
    path = _path(premises=(_premise("blocked-premise", "source-b", conflict_impact=PremiseConflictImpact.BLOCKS),))

    assert path.posture == "blocked_by_premise_conflict"
    assert path.recommendation == "decline"


def test_premise_conflict_weakens_or_backgrounds_without_authoritative_upgrade() -> None:
    weakened = _path(premises=(_premise("weakened-premise", "source-b", conflict_impact=PremiseConflictImpact.WEAKENS),))
    background = _path(
        premises=(_premise("background-premise", "source-c", conflict_impact=PremiseConflictImpact.BACKGROUND_ONLY),)
    )

    assert weakened.posture == "caveated_inference"
    assert background.posture == "caveated_inference"
    assert weakened.recommendation == "state_with_caveat"
    assert weakened.posture != "inferred_from_sourced_premises"


def test_source_bound_numeric_conflict_is_range_bound_not_resolved_scalar() -> None:
    target = TargetClaim(
        claim_id="target-total",
        claim_text="Target total is source-bound",
        posture=InferencePosture.RANGE_BOUND_INFERENCE,
        value=None,
        unit="USD",
        resolved_scalar=True,
    )
    path = _path(
        target=target,
        premises=(
            _premise(
                "fee-a",
                "source-fee-a",
                value=10,
                unit="USD",
                conflict_impact=PremiseConflictImpact.RANGE_BOUNDS,
                source_bound_numeric=True,
            ),
            _premise(
                "fee-b",
                "source-fee-b",
                value=15,
                unit="USD",
                conflict_impact=PremiseConflictImpact.RANGE_BOUNDS,
                source_bound_numeric=True,
            ),
        ),
    )
    state = path.to_controller_state()

    assert state["posture"] == "range_bound_inference"
    assert state["recommendation"] == "range_bound"
    assert state["resolved_scalar"] is False


def test_lower_tier_source_cannot_satisfy_official_current_legal_canonical_obligation() -> None:
    path = _path(
        premises=(
            _premise(
                "secondary-premise",
                "source-secondary",
                conflict_impact=PremiseConflictImpact.NON_SATISFYING_FOR_OBLIGATION,
                source_class="secondary",
                source_tier="lower",
                satisfies_required_source_obligation=False,
            ),
        ),
        bridges=(_bridge("legal-bridge", InferenceBridgeType.LEGAL_STATUTORY, strength=BridgeStrength.DOMAIN_CONDITIONED),),
    )

    assert path.to_controller_state()["premises"][0]["conflict_impact"] == "non_satisfying_for_obligation"
    assert path.posture in {"unsupported", "caveated_inference"}
    assert path.posture != "inferred_from_sourced_premises"


def test_controller_state_and_trace_fragment_are_json_safe_and_preserve_identities() -> None:
    path = _path(
        target=_target("target-json"),
        premises=(_premise("premise-json", "source-json"),),
        bridges=(_bridge("bridge-json", InferenceBridgeType.SOURCE_STATED_RELATIONSHIP, source_ids=("source-rule",)),),
    )

    state = json.loads(json.dumps(path.to_controller_state()))
    trace = json.loads(json.dumps(path.to_trace_fragment()))

    assert state["target_claim"]["claim_id"] == "target-json"
    assert state["premise_ids"] == ["premise-json"]
    assert state["premise_source_ids"] == ["source-json"]
    assert state["bridge_ids"] == ["bridge-json"]
    assert trace["indirect_inference_contract"]["bridge_source_ids"] == ["source-rule"]


def test_protected_surface_flags_remain_false() -> None:
    state = _path().to_controller_state()

    assert state["protected_surface_flags"]["final_answer_behavior_changed"] is False
    assert state["protected_surface_flags"]["author_behavior_changed"] is False
    assert state["protected_surface_flags"]["citation_behavior_changed"] is False
    assert state["protected_surface_flags"]["provider_behavior_changed"] is False
    assert state["protected_surface_flags"]["search_behavior_changed"] is False
    assert state["protected_surface_flags"]["query_behavior_changed"] is False
    assert state["protected_surface_flags"]["retrieval_behavior_changed"] is False
    assert state["protected_surface_flags"]["db_session_runoutcome_behavior_changed"] is False
    assert state["protected_surface_flags"]["cache_behavior_changed"] is False
    assert state["protected_surface_flags"]["scrutineer_behavior_changed"] is False
    assert state["protected_surface_flags"]["economist_followup_behavior_changed"] is False
    assert state["protected_surface_flags"]["orchestrator_behavior_changed"] is False


def test_static_guard_contract_does_not_import_or_rewrite_pipeline_orchestrator() -> None:
    module_text = Path("core/indirect_inference_contract.py").read_text(encoding="utf-8")
    assert "pipeline_orchestrator" not in module_text
    diff_name_only = Path(".git").exists()
    if diff_name_only:
        import subprocess

        result = subprocess.run(["git", "diff", "--name-only"], check=True, capture_output=True, text=True)
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
                or "query_authority.admit_execution_queries" in diff
        )
