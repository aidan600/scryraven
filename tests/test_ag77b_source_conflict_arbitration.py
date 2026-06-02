from __future__ import annotations

import ast
import copy
import json
import subprocess
from pathlib import Path

from core.source_conflict_arbitration import (
    SOURCE_CONFLICT_ARBITRATION_TRACE_KEY,
    SourceConflictAnswerPosture,
    SourceConflictArbitrationDisposition,
    SourceConflictArbitrationInput,
    SourceConflictArbitrationReason,
    arbitrate_source_conflicts,
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
ARBITRATION_PATH = ROOT / "core" / "source_conflict_arbitration.py"


def _source(
    source_id: str,
    *,
    source_class: str = "official",
    source_tier: str = "primary",
    currentness_label: SourceConflictCurrentness | str = SourceConflictCurrentness.CURRENT,
    jurisdiction: str | None = "US",
    scope: str | None = "national",
    effective_date: str | None = "2026-01-01",
) -> SourceConflictSourceRef:
    return SourceConflictSourceRef(
        source_id=source_id,
        url=f"https://{source_id}.example.test/rule",
        title=f"{source_id} rule page",
        source_class=source_class,
        source_tier=source_tier,
        publisher=f"{source_id} publisher",
        retrieved_at="2026-06-01T00:00:00Z",
        effective_date=effective_date,
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
    start: str | None = "2026-01-01",
    end: str | None = None,
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
        date_or_period=start,
        effective_period_start=start,
        effective_period_end=end,
        jurisdiction=source.jurisdiction,
        scope=source.scope,
        source_ref=source,
        source_class=source.source_class,
        source_tier=source.source_tier,
        currentness_label=source.currentness_label,
        source_bound=source_bound,
    )


def _single_record_state(record):
    group = build_source_conflict_group(group_id="group-test", records=[record])
    representation = build_source_conflict_representation([group])
    state = arbitrate_source_conflicts(
        SourceConflictArbitrationInput(representation=representation),
    )
    return state, state.group_arbitrations[0].record_arbitrations[0]


def test_equal_official_current_conflict_is_unresolved_blocking() -> None:
    record = build_source_conflict_record(
        conflict_id="conflict-official-current",
        contradiction_shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "March 1"),
        claim_b=_claim("claim-b", _source("official-b"), "April 1"),
        centrality=SourceConflictCentrality.CENTRAL,
        obligation_impact=SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT,
    )

    state, arbitration = _single_record_state(record)

    assert arbitration.disposition == SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING
    assert arbitration.answer_posture == (
        SourceConflictAnswerPosture.INSUFFICIENT_FOR_AUTHORITATIVE_ANSWER
    )
    assert arbitration.reason == SourceConflictArbitrationReason.EQUAL_AUTHORITY_CONFLICT
    assert arbitration.preferred_claim_id is None
    assert arbitration.winner_chosen is False
    assert arbitration.source_ids_preserved == ("official-a", "official-b")
    assert arbitration.claim_ids_preserved == ("claim-a", "claim-b")
    assert state.unresolved_blocking_count == 1


def test_official_current_vs_secondary_prefers_official_but_preserves_secondary() -> None:
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

    _, arbitration = _single_record_state(record)

    assert arbitration.disposition == SourceConflictArbitrationDisposition.PREFER_CLAIM_A
    assert arbitration.preferred_claim_id == "claim-official"
    assert arbitration.non_satisfying_claim_ids == ("claim-secondary",)
    assert arbitration.background_only_claim_ids == ("claim-secondary",)
    assert arbitration.lower_tier_cannot_satisfy_stronger_obligation is True
    assert arbitration.claim_b_preserved is True
    assert arbitration.source_ids_preserved == ("official-a", "secondary-b")


def test_current_vs_stale_prefers_current_without_mutating_representation() -> None:
    record = build_source_conflict_record(
        conflict_id="conflict-stale-current",
        contradiction_shape=[
            SourceConflictContradictionShape.STALE_VS_CURRENT,
            SourceConflictContradictionShape.EFFECTIVE_DATE_TENSION,
        ],
        claim_a=_claim(
            "claim-stale",
            _source("stale-a", currentness_label=SourceConflictCurrentness.STALE),
            "Old threshold",
            start="2024-01-01",
            end="2025-12-31",
        ),
        claim_b=_claim(
            "claim-current",
            _source("current-b", currentness_label=SourceConflictCurrentness.CURRENT),
            "New threshold",
            start="2026-01-01",
        ),
        centrality=SourceConflictCentrality.CENTRAL,
    )
    group = build_source_conflict_group(group_id="group-stale-current", records=[record])
    representation = build_source_conflict_representation([group])
    before = copy.deepcopy(representation.to_controller_state())

    state = arbitrate_source_conflicts(representation)
    arbitration = state.group_arbitrations[0].record_arbitrations[0]

    assert arbitration.disposition == SourceConflictArbitrationDisposition.PREFER_CLAIM_B
    assert arbitration.preferred_claim_id == "claim-current"
    assert arbitration.background_only_claim_ids == ("claim-stale",)
    assert arbitration.claim_a["effective_period_end"] == "2025-12-31"
    assert representation.to_controller_state() == before


def test_jurisdiction_scope_mismatch_reports_both_by_scope() -> None:
    record = build_source_conflict_record(
        conflict_id="conflict-scope",
        contradiction_shape=SourceConflictContradictionShape.JURISDICTION_SCOPE_MISMATCH,
        claim_a=_claim(
            "claim-us",
            _source("official-us", jurisdiction="US", scope="federal"),
            "18 months",
            key="retention_period",
        ),
        claim_b=_claim(
            "claim-eu",
            _source("official-eu", jurisdiction="EU", scope="member-state"),
            "24 months",
            key="retention_period",
        ),
        centrality=SourceConflictCentrality.CENTRAL,
        obligation_impact=SourceConflictObligationImpact.AFFECTS_LEGAL_CURRENT_PRIMARY,
    )

    _, arbitration = _single_record_state(record)

    assert arbitration.disposition == SourceConflictArbitrationDisposition.REPORT_BOTH_BY_SCOPE
    assert arbitration.preferred_claim_id is None
    assert arbitration.winner_chosen is False
    assert arbitration.claim_a["jurisdiction"] == "US"
    assert arbitration.claim_b["jurisdiction"] == "EU"
    assert arbitration.claim_a["scope"] == "federal"
    assert arbitration.claim_b["scope"] == "member-state"


def test_source_bound_numeric_conflict_preserves_values_and_marks_unresolved() -> None:
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
            start="2026-01-01",
            end="2026-12-31",
        ),
        claim_b=_claim(
            "claim-dataset-b",
            _source("dataset-b"),
            6.8,
            key="inflation_rate",
            unit="percent",
            source_bound=True,
            start="2026-01-01",
            end="2026-12-31",
        ),
        centrality=SourceConflictCentrality.CENTRAL,
        obligation_impact=SourceConflictObligationImpact.AFFECTS_SOURCE_BOUND_QUANTITATIVE,
    )

    _, arbitration = _single_record_state(record)

    assert arbitration.answer_posture == SourceConflictAnswerPosture.SOURCE_BOUND_VALUE_UNRESOLVED
    assert arbitration.disposition == SourceConflictArbitrationDisposition.UNRESOLVED_BLOCKING
    assert arbitration.claim_a["observed_value"] == {
        "value": 7.2,
        "unit": "percent",
        "value_kind": "number",
        "normalized": None,
    }
    assert arbitration.claim_b["observed_value"]["value"] == 6.8
    assert arbitration.claim_a["source_ref"]["source_id"] == "dataset-a"
    assert arbitration.claim_b["source_ref"]["source_id"] == "dataset-b"
    assert arbitration.claim_a["effective_period_start"] == "2026-01-01"
    assert arbitration.claim_b["effective_period_end"] == "2026-12-31"


def test_peripheral_background_conflict_does_not_block_or_force_exposure() -> None:
    record = build_source_conflict_record(
        conflict_id="conflict-background",
        contradiction_shape=SourceConflictContradictionShape.AMBIGUOUS_OR_PARTIAL_CONFLICT,
        claim_a=_claim("claim-background-a", _source("source-a"), "blue"),
        claim_b=_claim("claim-background-b", _source("source-b"), "green"),
        centrality=SourceConflictCentrality.PERIPHERAL,
        obligation_impact=SourceConflictObligationImpact.NO_OBLIGATION_IMPACT,
    )

    _, arbitration = _single_record_state(record)

    assert arbitration.disposition == SourceConflictArbitrationDisposition.BACKGROUND_ONLY
    assert arbitration.answer_posture == SourceConflictAnswerPosture.NO_ANSWER_IMPACT
    assert arbitration.blocks_authoritative_posture is False
    assert arbitration.reportable_claim_ids == ()
    assert arbitration.background_only_claim_ids == (
        "claim-background-a",
        "claim-background-b",
    )
    assert arbitration.claim_a_preserved is True
    assert arbitration.claim_b_preserved is True


def test_controller_state_and_trace_fragment_are_json_safe_and_ledger_compatible() -> None:
    record = build_source_conflict_record(
        conflict_id="conflict-official-current",
        contradiction_shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "March 1"),
        claim_b=_claim("claim-b", _source("official-b"), "April 1"),
        centrality=SourceConflictCentrality.CENTRAL,
        obligation_impact=SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT,
    )
    state, _ = _single_record_state(record)

    controller_state = state.to_controller_state()
    trace = state.to_trace_fragment()

    json.dumps(controller_state, sort_keys=True)
    json.dumps(trace, sort_keys=True)
    assert SOURCE_CONFLICT_ARBITRATION_TRACE_KEY in trace
    assert controller_state["ledger_compatible"] is True
    assert controller_state["controller_visible"] is True
    assert controller_state["final_answer_behavior_changed"] is False
    assert controller_state["citation_behavior_changed"] is False
    assert controller_state["prompt_behavior_changed"] is False
    assert controller_state["provider_search_query_behavior_changed"] is False
    assert controller_state["runtime_behavior_changed"] is False
    first_record = controller_state["groups"][0]["record_arbitrations"][0]
    assert first_record["source_ids_preserved"] == ["official-a", "official-b"]
    assert first_record["obligation_impact"] == "affects_official_current"


def test_ag77a_representation_is_consumed_immutably() -> None:
    record = build_source_conflict_record(
        conflict_id="conflict-immutable",
        contradiction_shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "A"),
        claim_b=_claim("claim-b", _source("official-b"), "B"),
        centrality=SourceConflictCentrality.CENTRAL,
    )
    group = build_source_conflict_group(group_id="group-immutable", records=[record])
    representation = build_source_conflict_representation([group])
    before = copy.deepcopy(representation.to_controller_state())

    arbitrate_source_conflicts(representation)

    assert representation.to_controller_state() == before
    assert group.to_controller_state() == before["groups"][0]
    assert record.to_dict() == before["groups"][0]["records"][0]


def test_empty_representation_returns_no_conflict_no_answer_impact() -> None:
    representation = build_source_conflict_representation([])

    state = arbitrate_source_conflicts(representation)

    assert state.group_arbitrations == ()
    assert state.top_level_answer_posture == SourceConflictAnswerPosture.NO_ANSWER_IMPACT
    assert state.to_controller_state()["group_count"] == 0
    assert state.unresolved_blocking_count == 0
    assert state.needs_more_evidence_count == 0


def test_static_protected_import_guard() -> None:
    tree = ast.parse(ARBITRATION_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert "core.source_conflict_model" in imported_modules
    banned_fragments = {
        "author",
        "citation",
        "prompt",
        "provider",
        "search",
        "query",
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
        if module == "core.source_conflict_model":
            continue
        assert not any(fragment in module for fragment in banned_fragments)


def test_existing_retrieval_and_recovery_lanes_remain_distinct_static_guard() -> None:
    source = ARBITRATION_PATH.read_text(encoding="utf-8")
    banned_runtime_terms = {
        "conflict_resolution_controller",
        "conflict_resolution_executor",
        "source_class_recovery",
        "weak_corpus",
        "scrutineer",
        "remediation",
        "generate_query",
        "run_search",
        "search_provider",
        "next_query",
    }
    assert all(term not in source for term in banned_runtime_terms)

    expected_distinct_lane_files = [
        "core/conflict_resolution_controller.py",
        "core/conflict_resolution_executor.py",
        "core/source_class_recovery.py",
        "core/weak_corpus_controller.py",
        "tests/test_conflict_resolution_controller.py",
        "tests/test_conflict_resolution_executor.py",
        "tests/test_source_class_recovery.py",
        "tests/test_weak_corpus_controller.py",
        "tests/test_ag76d_rq_router_query_preparation_contract.py",
        "tests/test_ag76d_wg_controller_owned_weak_failure_gate_contract.py",
    ]
    assert all((ROOT / file_name).exists() for file_name in expected_distinct_lane_files)


def test_no_ag78_indirect_inference_api_is_defined() -> None:
    source = ARBITRATION_PATH.read_text(encoding="utf-8")
    banned_terms = {
        "infer_from_premises",
        "inference_bridge",
        "premise_chain",
        "premise_bridge",
        "indirect_inference",
        "premise_reasoning",
    }
    assert all(term not in source for term in banned_terms)


def test_pipeline_orchestrator_is_not_rewritten() -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert "pipeline_orchestrator.py" not in changed
    if "core/pipeline_orchestrator.py" in changed:
        diff = subprocess.run(
            ["git", "diff", "--", "core/pipeline_orchestrator.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert "synthesis_evaluator_supplemental_search_runtime_handoff" in diff
