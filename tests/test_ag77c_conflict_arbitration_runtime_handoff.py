from __future__ import annotations

import ast
import copy
import json
import subprocess
from pathlib import Path

from core.answer_contract_runtime_handoff import (
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)
from core.source_conflict_arbitration import (
    SourceConflictAnswerPosture,
    SourceConflictArbitrationDisposition,
    arbitrate_source_conflicts,
)
from core.source_conflict_arbitration_runtime_handoff import (
    SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_SCHEMA_VERSION,
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
    SourceConflictValue,
    build_source_conflict_group,
    build_source_conflict_record,
    build_source_conflict_representation,
)

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "core" / "source_conflict_arbitration_runtime_handoff.py"
PIPELINE_PATH = ROOT / "core" / "pipeline_orchestrator.py"


def _source(
    source_id: str,
    *,
    source_class: str = "official",
    source_tier: str = "primary",
    currentness_label: SourceConflictCurrentness | str = SourceConflictCurrentness.CURRENT,
    jurisdiction: str | None = "US",
    scope: str | None = "national",
) -> SourceConflictSourceRef:
    return SourceConflictSourceRef(
        source_id=source_id,
        url=f"https://{source_id}.example.test/rule",
        title=f"{source_id} rule page",
        source_class=source_class,
        source_tier=source_tier,
        publisher=f"{source_id} publisher",
        retrieved_at="2026-06-01T00:00:00Z",
        effective_date="2026-01-01",
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
    key: str = "filing_deadline",
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
            value_kind="number" if isinstance(value, int | float) else "text",
        ),
        date_or_period="2026-01-01",
        effective_period_start="2026-01-01",
        effective_period_end="2026-12-31" if source_bound else None,
        jurisdiction=source.jurisdiction,
        scope=source.scope,
        source_ref=source,
        source_class=source.source_class,
        source_tier=source.source_tier,
        currentness_label=source.currentness_label,
        source_bound=source_bound,
    )


def _representation(record):
    group = build_source_conflict_group(group_id="group-test", records=[record])
    return build_source_conflict_representation([group])


def _runtime_state(representation, arbitration_state=None):
    handoff = build_source_conflict_arbitration_runtime_handoff(
        representation=representation,
        arbitration_state=arbitration_state,
    )
    return handoff.to_controller_state()


def _official_current_record():
    return build_source_conflict_record(
        conflict_id="conflict-official-current",
        contradiction_shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "March 1"),
        claim_b=_claim("claim-b", _source("official-b"), "April 1"),
        centrality=SourceConflictCentrality.CENTRAL,
        obligation_impact=SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT,
    )


def test_runtime_answercontract_visible_state_carries_arbitration_posture() -> None:
    representation = _representation(_official_current_record())
    arbitration_state = arbitrate_source_conflicts(representation)

    state = _runtime_state(representation, arbitration_state)

    assert state["schema_version"] == SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_SCHEMA_VERSION
    assert state["top_level_disposition"] == SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING.value
    assert state["top_level_answer_posture"] == (
        SourceConflictAnswerPosture.INSUFFICIENT_FOR_AUTHORITATIVE_ANSWER.value
    )
    assert state["unresolved_blocking_count"] == 1
    assert state["preserved_source_ids"] == ["official-a", "official-b"]
    assert state["ledger_compatible"] is True
    assert state["no_prose_change"] is True
    assert state["final_answer_behavior_changed"] is False
    assert state["runtime_behavior_changed"] is False
    assert state["author_exposed"] is False


def test_runtime_handoff_attaches_to_answer_contract_trace_when_supplied() -> None:
    representation = _representation(_official_current_record())

    result = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(
            query="What is the current official deadline?",
            evidence_available=True,
            source_conflict_representation=representation,
        )
    )
    trace = result.execution_trace_fragment()

    assert SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_TRACE_KEY in trace
    assert trace[SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_TRACE_KEY][
        "consumer"
    ] == "Controller / AnswerContract runtime visibility"
    assert trace[SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_TRACE_KEY][
        "author_exposed"
    ] is False


def test_empty_and_absent_runtime_state_are_no_conflict_no_answer_impact() -> None:
    absent_state = build_source_conflict_arbitration_runtime_handoff().to_controller_state()
    empty_state = _runtime_state(build_source_conflict_representation([]))

    for state in (absent_state, empty_state):
        assert state["top_level_disposition"] == SourceConflictArbitrationDisposition.NO_CONFLICT.value
        assert state["top_level_answer_posture"] == SourceConflictAnswerPosture.NO_ANSWER_IMPACT.value
        assert state["unresolved_blocking_count"] == 0
        assert state["preserved_source_ids"] == []
        assert state["no_answer_impact"] is True
        assert state["final_answer_behavior_changed"] is False
        assert state["author_behavior_changed"] is False
        assert state["citation_behavior_changed"] is False
        assert state["retrieval_behavior_changed"] is False


def test_central_unresolved_official_current_conflict_is_visibility_only() -> None:
    state = _runtime_state(_representation(_official_current_record()))
    record = state["arbitration"]["groups"][0]["record_arbitrations"][0]

    assert state["top_level_disposition"] == SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING.value
    assert state["top_level_answer_posture"] == (
        SourceConflictAnswerPosture.INSUFFICIENT_FOR_AUTHORITATIVE_ANSWER.value
    )
    assert record["blocks_authoritative_posture"] is True
    assert state["visibility_only"] is True
    assert state["final_answer_behavior_changed"] is False
    assert state["author_exposure_changed"] is False


def test_source_bound_numeric_unresolved_posture_is_visibility_only() -> None:
    record = build_source_conflict_record(
        conflict_id="conflict-numeric",
        contradiction_shape=SourceConflictContradictionShape.SOURCE_BOUND_NUMERIC_CONFLICT,
        claim_a=_claim(
            "claim-dataset-a",
            _source("dataset-a"),
            7.2,
            key="inflation_rate",
            unit="percent",
            source_bound=True,
        ),
        claim_b=_claim(
            "claim-dataset-b",
            _source("dataset-b"),
            6.8,
            key="inflation_rate",
            unit="percent",
            source_bound=True,
        ),
        centrality=SourceConflictCentrality.CENTRAL,
        obligation_impact=SourceConflictObligationImpact.AFFECTS_SOURCE_BOUND_QUANTITATIVE,
    )

    state = _runtime_state(_representation(record))

    assert state["top_level_answer_posture"] == (
        SourceConflictAnswerPosture.SOURCE_BOUND_VALUE_UNRESOLVED.value
    )
    assert state["top_level_disposition"] == SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING.value
    assert state["numeric_output_behavior_changed"] is False
    assert state["final_answer_behavior_changed"] is False


def test_official_current_vs_secondary_preserves_lower_tier_non_satisfaction() -> None:
    impact = SourceConflictObligationImpactDetail(
        impact=SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT,
        obligation_key="official_current_deadline",
        required_source_class="official",
        required_source_tier="primary",
        lower_tier_cannot_satisfy_stronger_obligation=True,
    )
    record = build_source_conflict_record(
        conflict_id="conflict-hierarchy",
        contradiction_shape=[
            SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
            SourceConflictContradictionShape.SOURCE_CLASS_AUTHORITY_MISMATCH,
        ],
        claim_a=_claim("claim-official", _source("official-a"), "May 1"),
        claim_b=_claim(
            "claim-secondary",
            _source("secondary-b", source_class="secondary", source_tier="secondary"),
            "June 1",
        ),
        centrality=SourceConflictCentrality.CENTRAL,
        obligation_impact=impact,
    )

    state = _runtime_state(_representation(record))
    arbitration = state["arbitration"]["groups"][0]["record_arbitrations"][0]

    assert arbitration["preferred_claim_id"] == "claim-official"
    assert arbitration["non_satisfying_claim_ids"] == ["claim-secondary"]
    assert arbitration["background_only_claim_ids"] == ["claim-secondary"]
    assert arbitration["lower_tier_cannot_satisfy_stronger_obligation"] is True
    assert state["top_level_answer_posture"] == SourceConflictAnswerPosture.QUALIFIED_ANSWER.value
    assert state["final_answer_behavior_changed"] is False


def test_trace_and_controller_serialization_are_json_safe() -> None:
    handoff = build_source_conflict_arbitration_runtime_handoff(
        representation=_representation(_official_current_record())
    )
    controller_state = handoff.to_controller_state()
    trace = handoff.execution_trace_fragment()

    json.dumps(controller_state, sort_keys=True)
    json.dumps(trace, sort_keys=True)
    assert SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_TRACE_KEY in trace
    assert controller_state["schema_version"] == SOURCE_CONFLICT_ARBITRATION_RUNTIME_HANDOFF_SCHEMA_VERSION
    assert controller_state["trace_key"] == "source_conflict_arbitration"


def test_ag77a_representation_remains_immutable_after_handoff() -> None:
    representation = _representation(_official_current_record())
    before = copy.deepcopy(representation.to_controller_state())

    build_source_conflict_arbitration_runtime_handoff(representation=representation)

    assert representation.to_controller_state() == before


def test_ag77b_arbitration_state_remains_immutable_after_handoff() -> None:
    representation = _representation(_official_current_record())
    arbitration_state = arbitrate_source_conflicts(representation)
    before = copy.deepcopy(arbitration_state.to_controller_state())

    build_source_conflict_arbitration_runtime_handoff(
        representation=representation,
        arbitration_state=arbitration_state,
    )

    assert arbitration_state.to_controller_state() == before


def test_static_protected_import_guard() -> None:
    tree = ast.parse(HELPER_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert imported_modules <= {
        "__future__",
        "copy",
        "dataclasses",
        "typing",
        "core.source_conflict_arbitration",
        "core.source_conflict_model",
    }
    banned_fragments = {
        "author",
        "citation",
        "prompt",
        "provider",
        "search",
        "retrieval",
        "scrutineer",
        "remediation",
        "economist",
        "followup",
        "follow_up",
        "session",
        "run_outcome",
        "cache",
        "pipeline_orchestrator",
        "conflict_resolution_controller",
        "conflict_resolution_executor",
    }
    for module in imported_modules:
        assert not any(fragment in module for fragment in banned_fragments)


def test_pipeline_orchestrator_adapter_guard_untouched() -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    pipeline_path = str(PIPELINE_PATH.relative_to(ROOT))
    if pipeline_path in changed:
        diff = subprocess.run(
            ["git", "diff", "--", pipeline_path],
            cwd=ROOT,
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
                or "provider_plan" in diff
        )
    else:
        assert pipeline_path not in changed
