from __future__ import annotations

import ast
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.answer_contract_runtime_handoff import RuntimeAnswerContractFacts, build_runtime_answer_contract_handoff
from core.source_conflict_answer_posture_activation import (
    SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_TRACE_KEY,
    build_source_conflict_answer_posture_activation,
)
from core.source_conflict_arbitration import arbitrate_source_conflicts
from core.source_conflict_arbitration_runtime_handoff import (
    SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_TRACE_KEY,
    build_source_conflict_arbitration_runtime_handoff,
)
from core.source_conflict_model import (
    SourceConflictCentrality,
    SourceConflictClaim,
    SourceConflictContradictionShape,
    SourceConflictCurrentness,
    SourceConflictObligationImpact,
    SourceConflictObligationImpactDetail,
    SourceConflictSourceRef,
    SourceConflictUnresolvedState,
    SourceConflictValue,
    build_source_conflict_group,
    build_source_conflict_record,
    build_source_conflict_representation,
)

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "core" / "source_conflict_answer_posture_activation.py"
PIPELINE_PATH = "core/pipeline_orchestrator.py"


def _source(
    source_id: str,
    *,
    source_class: str = "official",
    source_tier: str = "official",
    currentness_label: SourceConflictCurrentness | str = SourceConflictCurrentness.CURRENT,
    jurisdiction: str = "US",
    scope: str = "national",
) -> SourceConflictSourceRef:
    return SourceConflictSourceRef(
        source_id=source_id,
        url=f"https://{source_id}.example.test/rule",
        title=f"{source_id} rule page",
        source_class=source_class,
        source_tier=source_tier,
        publisher=f"{source_id} publisher",
        retrieved_at="2026-06-01T00:00:00Z",
        currentness_label=currentness_label,
        jurisdiction=jurisdiction,
        scope=scope,
        evidence_position=1 if source_id.endswith("a") else 2,
        text_hash=f"hash-{source_id}",
    )


def _claim(
    claim_id: str,
    source: SourceConflictSourceRef,
    value: str | int | float,
    *,
    key: str = "official_current_deadline",
    unit: str | None = None,
    source_bound: bool = False,
) -> SourceConflictClaim:
    return SourceConflictClaim(
        claim_id=claim_id,
        claim_text=f"{key} is {value}",
        claim_summary=f"{key}: {value}",
        normalized_claim_key=key,
        observed_value=SourceConflictValue(
            value=value,
            unit=unit,
            value_kind="number" if isinstance(value, (int, float)) else "text",
        ),
        observed_unit=unit,
        date_or_period="2026",
        effective_period_start="2026-01-01",
        effective_period_end="2026-12-31",
        jurisdiction=source.jurisdiction,
        scope=source.scope,
        source_ref=source,
        source_class=source.source_class,
        source_tier=source.source_tier,
        currentness_label=source.currentness_label,
        source_bound=source_bound,
    )


def _representation(
    *,
    shape: SourceConflictContradictionShape | list[SourceConflictContradictionShape],
    claim_a: SourceConflictClaim,
    claim_b: SourceConflictClaim,
    centrality: SourceConflictCentrality = SourceConflictCentrality.CENTRAL,
    impact: SourceConflictObligationImpact | SourceConflictObligationImpactDetail = (
        SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT
    ),
) -> Any:
    record = build_source_conflict_record(
        conflict_id="conflict-1",
        contradiction_shape=shape,
        claim_a=claim_a,
        claim_b=claim_b,
        centrality=centrality,
        unresolved_state=SourceConflictUnresolvedState.NEEDS_ARBITRATION,
        obligation_impact=impact,
    )
    group = build_source_conflict_group(group_id="group-1", records=[record])
    return build_source_conflict_representation([group])


def _runtime_state(representation: Any) -> dict[str, Any]:
    arbitration = arbitrate_source_conflicts(representation)
    handoff = build_source_conflict_arbitration_runtime_handoff(
        representation=representation,
        arbitration_state=arbitration,
    )
    return handoff.to_controller_state()


def _activation_state(representation: Any) -> dict[str, Any]:
    return build_source_conflict_answer_posture_activation(
        _runtime_state(representation)
    ).to_controller_state()


def test_central_equal_official_current_conflict_blocks_authoritative_posture_only() -> None:
    representation = _representation(
        shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "March 1"),
        claim_b=_claim("claim-b", _source("official-b"), "April 1"),
    )

    state = _activation_state(representation)

    assert state["authoritative_posture_blocked"] is True
    assert state["authoritative_posture_insufficient"] is True
    assert state["effects"][0]["effect_type"] == "authoritative_posture_blocked_insufficient"
    assert state["effects"][0]["obligation_impact"] == "affects_official_current"
    assert state["no_final_answer_prose_change"] is True
    assert state["final_answer_behavior_changed"] is False
    assert state["author_behavior_changed"] is False
    assert state["author_exposure_changed"] is False
    assert state["citation_behavior_changed"] is False
    assert state["provider_search_query_behavior_changed"] is False
    assert state["retrieval_behavior_changed"] is False


def test_source_bound_numeric_conflict_marks_value_unresolved_not_resolved_scalar() -> None:
    representation = _representation(
        shape=SourceConflictContradictionShape.SOURCE_BOUND_NUMERIC_CONFLICT,
        claim_a=_claim(
            "claim-a",
            _source("official-a"),
            10,
            key="source_bound_fee",
            unit="USD",
            source_bound=True,
        ),
        claim_b=_claim(
            "claim-b",
            _source("official-b"),
            15,
            key="source_bound_fee",
            unit="USD",
            source_bound=True,
        ),
        impact=SourceConflictObligationImpact.AFFECTS_SOURCE_BOUND_QUANTITATIVE,
    )

    state = _activation_state(representation)
    effect = state["effects"][0]

    assert effect["effect_type"] == "source_bound_value_unresolved"
    assert effect["source_bound_value_unresolved"] is True
    assert effect["resolved_source_bound_scalar"] is False
    assert state["source_bound_unresolved_value_count"] == 1
    assert state["resolved_source_bound_scalar_count"] == 0
    assert state["numeric_output_behavior_changed"] is False
    assert state["final_answer_behavior_changed"] is False


def test_official_current_vs_secondary_preserves_lower_tier_non_satisfaction() -> None:
    impact = SourceConflictObligationImpactDetail(
        impact=SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT,
        obligation_key="official_current_deadline",
        required_source_class="official",
        required_source_tier="official",
        lower_tier_cannot_satisfy_stronger_obligation=True,
    )
    representation = _representation(
        shape=[
            SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
            SourceConflictContradictionShape.SOURCE_CLASS_AUTHORITY_MISMATCH,
        ],
        claim_a=_claim("claim-official", _source("official-a"), "May 1"),
        claim_b=_claim(
            "claim-secondary",
            _source("secondary-b", source_class="secondary", source_tier="secondary"),
            "June 1",
        ),
        impact=impact,
    )

    state = _activation_state(representation)
    effect = state["effects"][0]

    assert effect["effect_type"] == "lower_tier_non_satisfaction_background_context"
    assert effect["lower_tier_non_satisfying_for_stronger_obligation"] is True
    assert effect["secondary_background_context_only"] is True
    assert effect["non_satisfying_claim_ids"] == ["claim-secondary"]
    assert effect["background_only_claim_ids"] == ["claim-secondary"]
    assert state["lower_tier_non_satisfaction_preserved"] is True
    assert state["author_exposure_changed"] is False


def test_peripheral_background_conflict_is_preserved_nonblocking_no_answer_impact() -> None:
    representation = _representation(
        shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "A"),
        claim_b=_claim("claim-b", _source("official-b"), "B"),
        centrality=SourceConflictCentrality.PERIPHERAL,
        impact=SourceConflictObligationImpact.NO_OBLIGATION_IMPACT,
    )

    state = _activation_state(representation)
    effect = state["effects"][0]

    assert effect["effect_type"] == "peripheral_background_nonblocking"
    assert effect["nonblocking"] is True
    assert effect["no_answer_impact"] is True
    assert state["nonblocking_background_conflict_count"] == 1
    assert state["authoritative_posture_blocked"] is False
    assert state["no_answer_impact"] is True


def test_empty_state_has_no_answer_impact_and_no_behavior_change_flags() -> None:
    state = build_source_conflict_answer_posture_activation(None).to_controller_state()

    assert state["source_conflict_arbitration_available"] is False
    assert state["effect_count"] == 0
    assert state["no_answer_impact"] is True
    assert state["final_answer_behavior_changed"] is False
    assert state["author_behavior_changed"] is False
    assert state["citation_behavior_changed"] is False
    assert state["provider_search_query_behavior_changed"] is False
    assert state["retrieval_behavior_changed"] is False
    assert state["ag78_indirect_inference_changed"] is False


def test_ag77a_representation_is_immutable_across_activation() -> None:
    representation = _representation(
        shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "March 1"),
        claim_b=_claim("claim-b", _source("official-b"), "April 1"),
    )
    before = deepcopy(representation.to_controller_state())

    build_source_conflict_answer_posture_activation(_runtime_state(representation))

    assert representation.to_controller_state() == before


def test_ag77b_arbitration_state_is_immutable_across_activation() -> None:
    representation = _representation(
        shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "March 1"),
        claim_b=_claim("claim-b", _source("official-b"), "April 1"),
    )
    arbitration = arbitrate_source_conflicts(representation)
    before = deepcopy(arbitration.to_controller_state())

    build_source_conflict_answer_posture_activation(arbitration)

    assert arbitration.to_controller_state() == before


def test_ag77c_runtime_handoff_serialization_stays_json_safe_and_stable() -> None:
    representation = _representation(
        shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "March 1"),
        claim_b=_claim("claim-b", _source("official-b"), "April 1"),
    )
    handoff = build_source_conflict_arbitration_runtime_handoff(
        representation=representation,
        arbitration_state=arbitrate_source_conflicts(representation),
    )
    before_state = handoff.to_controller_state()
    before_trace = handoff.execution_trace_fragment()

    activation = build_source_conflict_answer_posture_activation(handoff)

    json.dumps(activation.to_controller_state(), sort_keys=True)
    json.dumps(handoff.to_controller_state(), sort_keys=True)
    json.dumps(handoff.execution_trace_fragment(), sort_keys=True)
    assert handoff.to_controller_state() == before_state
    assert handoff.execution_trace_fragment() == before_trace


def test_answer_contract_runtime_handoff_consumes_ag77c_state_without_author_handoff_change() -> None:
    representation = _representation(
        shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "March 1"),
        claim_b=_claim("claim-b", _source("official-b"), "April 1"),
    )
    baseline = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(query="What are the current official rules?")
    )
    result = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(
            query="What are the current official rules?",
            source_conflict_representation=representation,
            source_conflict_arbitration_state=arbitrate_source_conflicts(representation),
        )
    )

    trace = result.execution_trace_fragment()

    assert SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_TRACE_KEY in trace
    assert SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_TRACE_KEY in trace
    assert result.source_conflict_answer_posture_activation is not None
    assert (
        trace[SOURCE_CONFLICT_ANSWER_POSTURE_ACTIVATION_TRACE_KEY][
            "authoritative_posture_blocked"
        ]
        is True
    )
    assert result.fulfillment_handoff.to_dict() == baseline.fulfillment_handoff.to_dict()


def test_static_protected_import_guard_for_ag77d_helper() -> None:
    tree = ast.parse(HELPER_PATH.read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    allowed = {
        "__future__",
        "copy",
        "dataclasses",
        "typing",
        "core.source_conflict_arbitration",
        "core.source_conflict_arbitration_runtime_handoff",
    }
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
        "db",
        "session",
        "runoutcome",
        "cache",
        "pipeline_orchestrator",
    )

    assert imported <= allowed
    assert not any(
        fragment in module.casefold()
        for module in imported
        for fragment in forbidden_fragments
    )


def test_pipeline_orchestrator_boundary_untouched_in_diff() -> None:
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD", "--"],
        cwd=ROOT,
        text=True,
    ).splitlines()

    assert PIPELINE_PATH not in changed
