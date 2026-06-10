from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.offline_golden_harness import (
    GoldenEvaluationStatus,
    OfflineGoldenTaskEvaluator,
    load_observed_run_snapshots,
)
from core.offline_golden_tasks import load_golden_tasks

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "ag93b"
TASK_FIXTURE = FIXTURE_DIR / "golden_tasks.json"
SNAPSHOT_FIXTURE = FIXTURE_DIR / "observed_snapshots.json"


def _tasks() -> dict[str, Any]:
    return {task.task_id: task for task in load_golden_tasks(TASK_FIXTURE)}


def _raw_snapshots() -> dict[str, dict[str, Any]]:
    payload = json.loads(SNAPSHOT_FIXTURE.read_text(encoding="utf-8"))
    return {item["task_id"]: item for item in payload["snapshots"]}


def _evaluate(task_id: str, snapshot: dict[str, Any] | None = None):
    task = _tasks()[task_id]
    observed = deepcopy(snapshot if snapshot is not None else _raw_snapshots()[task_id])
    return OfflineGoldenTaskEvaluator().evaluate(task, observed)


def _finding_statuses(result) -> set[str]:
    return {item.status.value for item in result.findings}


def test_all_fixture_golden_tasks_pass_and_emit_machine_readable_results() -> None:
    tasks = _tasks()
    snapshots = load_observed_run_snapshots(SNAPSHOT_FIXTURE)

    assert len(tasks) == 8
    assert {
        "current_official_fact",
        "legal_regulatory_current_primary_fact",
        "canonical_technical_documentation",
        "source_bound_numeric_fact",
        "ordinary_explainer",
        "conflict_changed_over_time_fact",
        "indirect_inference_from_sourced_premises",
        "weak_corpus_insufficient_evidence",
    } <= {task.family for task in tasks.values()}

    for task_id, task in tasks.items():
        result = OfflineGoldenTaskEvaluator().evaluate(task, snapshots[task_id])
        assert result.passed, result.human_summary()
        payload = result.to_dict()
        assert payload["status"] == GoldenEvaluationStatus.PASS.value
        assert payload["passed"] is True
        assert payload["task_id"] == task_id
        assert result.human_summary().startswith("PASS")


def test_weak_corpus_insufficient_case_passes_when_posture_is_insufficient() -> None:
    result = _evaluate("ag93b_weak_corpus_insufficient")

    assert result.status is GoldenEvaluationStatus.PASS
    assert result.passed


def test_prose_wording_change_is_non_failing_when_structured_ingredients_survive() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["final_answer"]["text"] = (
        "Different wording: the structured answer still carries the same official-status ingredient."
    )
    snapshot["final_answer"]["style_notes"] = ["wording changed without evidence/posture change"]

    result = _evaluate("ag93b_current_official_fact", snapshot)

    assert result.passed, result.human_summary()
    assert GoldenEvaluationStatus.PROSE_STYLE_NOTE.value in _finding_statuses(result)
    assert all(
        finding.status is GoldenEvaluationStatus.PROSE_STYLE_NOTE
        for finding in result.findings
    )


def test_lower_tier_secondary_evidence_passes_only_for_allowed_explainer_obligation() -> None:
    allowed = _evaluate("ag93b_ordinary_explainer_secondary_allowed")
    assert allowed.passed, allowed.human_summary()

    stronger = deepcopy(_raw_snapshots()["ag93b_legal_regulatory_current_primary"])
    stronger["ledger"]["source_requirements"][0]["linked_candidate_ids"] = [
        "src_legal_secondary_summary"
    ]
    stronger["ledger"]["candidate_records"][1]["fact_disposition"] = "accepted"

    result = _evaluate("ag93b_legal_regulatory_current_primary", stronger)

    assert result.status is GoldenEvaluationStatus.SOURCE_POSTURE_FAILED
    assert GoldenEvaluationStatus.SOURCE_POSTURE_FAILED.value in _finding_statuses(result)


def test_missing_expected_ingredient_from_ledger_and_final_answer_fails() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["ledger"]["candidate_records"] = [
        item
        for item in snapshot["ledger"]["candidate_records"]
        if item["candidate_id"] != "src_alpha_official_current"
    ]
    snapshot["final_answer"]["ingredient_ids"] = []
    snapshot["final_answer"]["text"] = "The answer omits the Alpha current-status ingredient."

    result = _evaluate("ag93b_current_official_fact", snapshot)

    assert result.status is GoldenEvaluationStatus.ANSWER_INGREDIENT_FAILED
    assert GoldenEvaluationStatus.ANSWER_INGREDIENT_FAILED.value in _finding_statuses(result)
    assert GoldenEvaluationStatus.FINAL_ANSWER_OMISSION.value in _finding_statuses(result)


def test_source_bound_numeric_claim_without_eligible_source_support_fails() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_source_bound_numeric_fact"])
    snapshot["final_answer"]["citations"][0]["source_ids"] = [
        "src_numeric_secondary_article"
    ]
    snapshot["final_packet"]["citation_eligible"][0]["source_id"] = (
        "src_numeric_secondary_article"
    )

    result = _evaluate("ag93b_source_bound_numeric_fact", snapshot)

    assert result.status is GoldenEvaluationStatus.SOURCE_POSTURE_FAILED
    assert GoldenEvaluationStatus.SOURCE_POSTURE_FAILED.value in _finding_statuses(result)


def test_search_judgment_stopping_satisfied_with_missing_evidence_fails() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_weak_corpus_insufficient"])
    snapshot["search"]["decision"] = "stop_satisfied"

    result = _evaluate("ag93b_weak_corpus_insufficient", snapshot)

    assert result.status is GoldenEvaluationStatus.SEARCH_JUDGMENT_FAILED
    assert GoldenEvaluationStatus.SEARCH_JUDGMENT_FAILED.value in _finding_statuses(result)


def test_sufficiency_direct_posture_with_missing_required_evidence_fails() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_weak_corpus_insufficient"])
    snapshot["sufficiency"]["decision"] = "ready_direct"
    snapshot["sufficiency"]["final_answer_posture"] = "direct_answer"

    result = _evaluate("ag93b_weak_corpus_insufficient", snapshot)

    assert result.status is GoldenEvaluationStatus.SUFFICIENCY_POSTURE_FAILED
    assert GoldenEvaluationStatus.SUFFICIENCY_POSTURE_FAILED.value in _finding_statuses(result)


def test_final_answer_packet_missing_caveat_or_upgrade_guardrail_fails() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_weak_corpus_insufficient"])
    snapshot["final_packet"]["mandatory_caveats"] = []
    snapshot["final_packet"]["prohibited_upgrades"] = []

    result = _evaluate("ag93b_weak_corpus_insufficient", snapshot)

    assert result.status is GoldenEvaluationStatus.FINAL_PACKET_FAILED
    assert GoldenEvaluationStatus.FINAL_PACKET_FAILED.value in _finding_statuses(result)


def test_unsupported_extra_claim_in_final_answer_fails() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["final_answer"]["claim_ids"].append("alpha_closed_claim")
    snapshot["final_answer"]["text"] += " Alpha permit window is closed."

    result = _evaluate("ag93b_current_official_fact", snapshot)

    assert result.status is GoldenEvaluationStatus.UNSUPPORTED_CLAIM
    assert GoldenEvaluationStatus.UNSUPPORTED_CLAIM.value in _finding_statuses(result)


def test_wrong_source_cited_for_key_fact_fails_alignment() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["final_answer"]["citations"][0]["source_ids"] = [
        "src_alpha_secondary_context"
    ]

    result = _evaluate("ag93b_current_official_fact", snapshot)

    assert result.status is GoldenEvaluationStatus.CITATION_ALIGNMENT_FAILED
    assert GoldenEvaluationStatus.CITATION_ALIGNMENT_FAILED.value in _finding_statuses(result)


def test_search_and_recovery_count_out_of_bounds_fails_distinct_taxonomy() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["search"]["attempt_count"] = 5

    result = _evaluate("ag93b_current_official_fact", snapshot)

    assert result.status is GoldenEvaluationStatus.SEARCH_COUNT_OUT_OF_BOUNDS
    assert GoldenEvaluationStatus.SEARCH_COUNT_OUT_OF_BOUNDS.value in _finding_statuses(result)


def test_harness_modules_do_not_import_runtime_or_live_surfaces() -> None:
    for path in (
        ROOT / "core" / "offline_golden_tasks.py",
        ROOT / "core" / "offline_golden_harness.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "from core.pipeline_orchestrator" not in text
        assert "import core.pipeline_orchestrator" not in text
        assert "from core.provider" not in text
        assert "ask_model(" not in text
        assert "raw_provider_payload" not in text
