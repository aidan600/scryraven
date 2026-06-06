from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from core.source_conflict_model import (
    SOURCE_CONFLICT_TRACE_KEY,
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
MODEL_PATH = ROOT / "core" / "source_conflict_model.py"


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
            value_kind="number" if isinstance(value, (int, float)) else "text",
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


def test_two_conflicting_official_current_sources_both_survive_representation() -> None:
    claim_a = _claim("claim-a", _source("official-a"), "March 1")
    claim_b = _claim("claim-b", _source("official-b"), "April 1")
    record = build_source_conflict_record(
        conflict_id="conflict-official-current",
        contradiction_shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=claim_a,
        claim_b=claim_b,
        centrality=SourceConflictCentrality.CENTRAL,
        unresolved_state=SourceConflictUnresolvedState.NEEDS_ARBITRATION,
        obligation_impact=SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT,
    )
    group = build_source_conflict_group(group_id="group-official-current", records=[record])
    state = group.to_controller_state()

    assert state["involved_source_ids"] == ["official-a", "official-b"]
    assert state["records"][0]["claim_a"]["claim_id"] == "claim-a"
    assert state["records"][0]["claim_b"]["claim_id"] == "claim-b"
    assert state["records"][0]["winner_chosen"] is False
    assert state["winner_chosen"] is False
    assert state["records"][0]["unresolved_state"] in {
        SourceConflictUnresolvedState.UNRESOLVED.value,
        SourceConflictUnresolvedState.NEEDS_ARBITRATION.value,
    }


def test_official_current_vs_secondary_conflict_preserves_hierarchy() -> None:
    official = _claim("claim-official", _source("official-a"), "May 1")
    secondary = _claim(
        "claim-secondary",
        _source("secondary-b", source_class="secondary", source_tier="tertiary"),
        "June 1",
    )
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
        claim_a=official,
        claim_b=secondary,
        obligation_impact=impact,
    )
    state = build_source_conflict_group(group_id="group-hierarchy", records=[record]).to_controller_state()
    represented = state["records"][0]

    assert represented["lower_tier_cannot_satisfy_stronger_obligation"] is True
    assert represented["obligation_impact"]["required_source_class"] == "official"
    assert represented["obligation_impact"]["required_source_tier"] == "primary"
    assert represented["claim_a"]["source_class"] == "official"
    assert represented["claim_b"]["source_class"] == "secondary"
    assert state["involved_source_ids"] == ["official-a", "secondary-b"]


def test_stale_vs_current_conflict_records_currentness_and_effective_date_tension() -> None:
    stale = _claim(
        "claim-stale",
        _source(
            "stale-a",
            currentness_label=SourceConflictCurrentness.STALE,
            effective_date="2024-01-01",
        ),
        "Old threshold",
        start="2024-01-01",
        end="2025-12-31",
    )
    current = _claim(
        "claim-current",
        _source(
            "current-b",
            currentness_label=SourceConflictCurrentness.CURRENT,
            effective_date="2026-01-01",
        ),
        "New threshold",
        start="2026-01-01",
    )
    record = build_source_conflict_record(
        conflict_id="conflict-stale-current",
        contradiction_shape=[
            SourceConflictContradictionShape.STALE_VS_CURRENT,
            SourceConflictContradictionShape.EFFECTIVE_DATE_TENSION,
        ],
        claim_a=stale,
        claim_b=current,
    )
    represented = record.to_dict()

    assert SourceConflictContradictionShape.STALE_VS_CURRENT.value in represented["contradiction_shape"]
    assert SourceConflictContradictionShape.EFFECTIVE_DATE_TENSION.value in represented["contradiction_shape"]
    assert represented["claim_a"]["currentness_label"] == "stale"
    assert represented["claim_b"]["currentness_label"] == "current"
    assert represented["claim_a"]["effective_period_start"] == "2024-01-01"
    assert represented["claim_a"]["effective_period_end"] == "2025-12-31"
    assert represented["claim_b"]["effective_period_start"] == "2026-01-01"


def test_jurisdiction_scope_mismatch_is_represented_without_choosing_winner() -> None:
    us_claim = _claim(
        "claim-us",
        _source("official-us", jurisdiction="US", scope="federal"),
        "18 months",
        key="retention_period",
    )
    eu_claim = _claim(
        "claim-eu",
        _source("official-eu", jurisdiction="EU", scope="member-state"),
        "24 months",
        key="retention_period",
    )
    record = build_source_conflict_record(
        conflict_id="conflict-scope",
        contradiction_shape=SourceConflictContradictionShape.JURISDICTION_SCOPE_MISMATCH,
        claim_a=us_claim,
        claim_b=eu_claim,
        unresolved_state=SourceConflictUnresolvedState.UNRESOLVED,
    )
    represented = record.to_dict()

    assert represented["contradiction_shape"] == ["jurisdiction_scope_mismatch"]
    assert represented["claim_a"]["jurisdiction"] == "US"
    assert represented["claim_b"]["jurisdiction"] == "EU"
    assert represented["claim_a"]["scope"] == "federal"
    assert represented["claim_b"]["scope"] == "member-state"
    assert represented["winner_chosen"] is False
    assert represented["unresolved_state"] == "unresolved"


def test_source_bound_numeric_conflict_records_values_units_and_effective_periods() -> None:
    claim_a = _claim(
        "claim-2025",
        _source("dataset-a"),
        7.2,
        key="inflation_rate",
        unit="percent",
        source_bound=True,
        start="2025-01-01",
        end="2025-12-31",
    )
    claim_b = _claim(
        "claim-2026",
        _source("dataset-b"),
        6.8,
        key="inflation_rate",
        unit="percent",
        source_bound=True,
        start="2026-01-01",
        end="2026-12-31",
    )
    record = build_source_conflict_record(
        conflict_id="conflict-numeric",
        contradiction_shape=SourceConflictContradictionShape.SOURCE_BOUND_NUMERIC_CONFLICT,
        claim_a=claim_a,
        claim_b=claim_b,
        obligation_impact=SourceConflictObligationImpact.AFFECTS_SOURCE_BOUND_QUANTITATIVE,
    )
    represented = record.to_dict()

    assert represented["claim_a"]["observed_value"]["value"] == 7.2
    assert represented["claim_b"]["observed_value"]["value"] == 6.8
    assert represented["claim_a"]["observed_value"]["unit"] == "percent"
    assert represented["claim_b"]["observed_value"]["unit"] == "percent"
    assert represented["claim_a"]["source_ref"]["source_id"] == "dataset-a"
    assert represented["claim_b"]["source_ref"]["source_id"] == "dataset-b"
    assert represented["claim_a"]["effective_period_start"] == "2025-01-01"
    assert represented["claim_b"]["effective_period_end"] == "2026-12-31"
    assert represented["obligation_impact"]["impact"] == "affects_source_bound_quantitative"


def test_unresolved_conflict_state_is_controller_visible_and_ledger_compatible() -> None:
    record = build_source_conflict_record(
        conflict_id="conflict-controller-state",
        contradiction_shape=SourceConflictContradictionShape.DIRECT_VALUE_CONFLICT,
        claim_a=_claim("claim-a", _source("official-a"), "A"),
        claim_b=_claim("claim-b", _source("official-b"), "B"),
        obligation_impact=SourceConflictObligationImpact.AFFECTS_OFFICIAL_CURRENT,
    )
    group = build_source_conflict_group(group_id="group-controller-state", records=[record])
    representation = build_source_conflict_representation([group])
    state = representation.to_controller_state()
    trace = representation.to_trace_fragment()

    assert state["controller_visible"] is True
    assert state["ledger_compatible"] is True
    assert state["groups"][0]["records"][0]["unresolved_state"] == "unresolved"
    assert state["groups"][0]["records"][0]["claim_a"]["source_ref"]["source_id"] == "official-a"
    assert state["groups"][0]["highest_obligation_impact"] == "affects_official_current"
    assert trace[SOURCE_CONFLICT_TRACE_KEY]["group_count"] == 1
    assert trace[SOURCE_CONFLICT_TRACE_KEY]["winner_chosen"] is False


def test_static_protected_surface_guard_for_model_imports() -> None:
    tree = ast.parse(MODEL_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_roots = {
        "core.answer_contract_runtime_handoff",
        "core.pipeline_orchestrator",
        "core.conflict_resolution_controller",
        "core.conflict_resolution_executor",
        "core.final_evidence_bundle_builder",
        "core.citation_source_handoff_contract",
        "core.economist_handoff_contract",
        "core.followup_initial_state_contract",
        "core.source_class_recovery_controller",
        "core.source_class_recovery_executor",
        "core.weak_corpus_recovery",
        "core.scrutineer",
        "core.remediation",
        "core.session",
        "core.run_outcome",
        "core.llm_cache",
        "requests",
        "httpx",
        "openai",
    }
    assert imported_modules.isdisjoint(forbidden_roots)
    assert imported_modules <= {"__future__", "dataclasses", "enum", "hashlib", "typing"}


def test_lane_distinction_static_guard_and_pipeline_orchestrator_unchanged() -> None:
    changed = set(
        subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD", "--"],
            cwd=ROOT,
            text=True,
        ).splitlines()
    )

    distinct_lane_modules = {
        "core/retrieval_loop_contract.py",  # ordinary continuation lane
        "core/router_query_preparation_contract.py",  # ordinary query prep lane
        "core/conflict_resolution_controller.py",  # conflict-resolution query lane
        "core/conflict_resolution_executor.py",  # conflict-resolution execution lane
        "core/source_class_recovery_controller.py",  # source-class recovery lane
        "core/source_class_recovery_executor.py",  # source-class recovery execution lane
        "core/weak_corpus_recovery.py",  # weak-corpus recovery lane
        "core/pipeline_orchestrator.py",  # Scrutineer/remediation and runtime spine
    }
    if "core/pipeline_orchestrator.py" in changed:
        pipeline_diff = subprocess.check_output(
            ["git", "diff", "HEAD", "--", "core/pipeline_orchestrator.py"],
            cwd=ROOT,
            text=True,
        )
        assert (
            "synthesis_evaluator_supplemental_search_runtime_handoff" in pipeline_diff
            or "final_answer_runtime_adapter" in pipeline_diff
            or "FinalAnswerPacket" in pipeline_diff
            or "pre_author_source_obligation_projection" in pipeline_diff
            or "session_output_projection" in pipeline_diff
        )
        distinct_lane_modules.remove("core/pipeline_orchestrator.py")
    assert changed.isdisjoint(distinct_lane_modules)


def test_no_winner_or_arbitration_helper_is_exposed() -> None:
    tree = ast.parse(MODEL_PATH.read_text(encoding="utf-8"))
    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    forbidden_terms = (
        "choose_winner",
        "resolve_conflict",
        "arbitrate",
        "rank_sources",
        "select_authority",
        "winner",
    )

    assert not any(
        forbidden in function_name
        for function_name in function_names
        for forbidden in forbidden_terms
    )
