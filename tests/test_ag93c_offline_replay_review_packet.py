from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.offline_golden_harness import GoldenEvaluationStatus, OfflineGoldenTaskEvaluator
from core.offline_golden_tasks import load_golden_tasks
from core.offline_replay_review_packet import (
    OFFLINE_REPLAY_REVIEW_PACKET_SCHEMA_VERSION,
    build_offline_replay_review_packet,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "ag93b"
TASK_FIXTURE = FIXTURE_DIR / "golden_tasks.json"
SNAPSHOT_FIXTURE = FIXTURE_DIR / "observed_snapshots.json"
PACKET_MODULE = ROOT / "core" / "offline_replay_review_packet.py"


def _tasks() -> dict[str, Any]:
    return {task.task_id: task for task in load_golden_tasks(TASK_FIXTURE)}


def _raw_snapshots() -> dict[str, dict[str, Any]]:
    payload = json.loads(SNAPSHOT_FIXTURE.read_text(encoding="utf-8"))
    return {item["task_id"]: item for item in payload["snapshots"]}


def _packet(task_id: str, snapshot: dict[str, Any] | None = None):
    task = _tasks()[task_id]
    observed = deepcopy(snapshot if snapshot is not None else _raw_snapshots()[task_id])
    result = OfflineGoldenTaskEvaluator().evaluate(task, observed)
    return build_offline_replay_review_packet(task, observed, result), result


def test_passing_ag93b_fixture_packet_contains_end_to_end_sections() -> None:
    packet, result = _packet("ag93b_current_official_fact")

    assert result.passed
    payload = packet.to_dict()
    markdown = packet.to_markdown()

    assert payload["schema_version"] == OFFLINE_REPLAY_REVIEW_PACKET_SCHEMA_VERSION
    assert payload["phase"] == "AG-93C"
    assert payload["metadata"]["query"] == ("Fixture: what is the current Alpha permit window status?")
    assert payload["metadata"]["task_family"] == "current_official_fact"
    assert payload["metadata"]["evaluation_status"] == "PASS"
    assert payload["metadata"]["passed"] is True
    assert payload["golden_expectations"]["expected_answer_ingredients"]
    assert payload["observed_contract"]["source_requirements"]
    assert payload["observed_evidence_ledger"]["candidate_records"]
    assert payload["observed_search_judgment"]["decision"] == "stop_satisfied"
    assert payload["observed_sufficiency_judgment"]["decision"] == "ready_direct"
    assert payload["observed_final_answer_packet"]["allowed_evidence_source_ids"] == ["src_alpha_official_current"]
    assert payload["final_answer"]["observed_ingredient_ids"] == ["alpha_current_status"]
    assert payload["final_answer"]["citations"]
    assert "AG-93C Offline Replay Review Packet" in markdown
    assert "Contract / Ledger" in markdown
    assert "Final Answer" in markdown
    assert "PASS" in markdown


def test_failing_mutated_packet_surfaces_missing_ingredient() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["ledger"]["candidate_records"] = [
        item for item in snapshot["ledger"]["candidate_records"] if item["candidate_id"] != "src_alpha_official_current"
    ]
    snapshot["final_answer"]["ingredient_ids"] = []
    snapshot["final_answer"]["text"] = "The answer omits the Alpha current-status ingredient."

    packet, result = _packet("ag93b_current_official_fact", snapshot)

    assert result.status is GoldenEvaluationStatus.ANSWER_INGREDIENT_FAILED
    payload = packet.to_dict()
    markdown = packet.to_markdown()
    assert "alpha_current_status" in payload["final_answer"]["missing_expected_ingredient_ids"]
    assert "alpha_current_status" in markdown
    assert "FINAL_ANSWER_OMISSION" in markdown


def test_source_posture_failure_packet_highlights_lower_tier_custody() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_legal_regulatory_current_primary"])
    snapshot["ledger"]["source_requirements"][0]["linked_candidate_ids"] = ["src_legal_secondary_summary"]
    snapshot["ledger"]["candidate_records"][1]["fact_disposition"] = "accepted"

    packet, result = _packet("ag93b_legal_regulatory_current_primary", snapshot)

    assert result.status is GoldenEvaluationStatus.SOURCE_POSTURE_FAILED
    warnings = packet.to_dict()["observed_evidence_ledger"]["warnings"]
    codes = {item["code"] for item in warnings}
    assert "FORBIDDEN_SOURCE_SATISFIED_OBLIGATION" in codes
    assert "LOWER_TIER_WEAK_STALE_OR_OFF_TOPIC_SOURCE_SATISFIED_STRONGER_OBLIGATION" in codes
    assert "Source posture/custody warnings" in packet.to_markdown()


def test_search_recovery_bounds_packet_reports_out_of_bounds() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["search"]["attempt_count"] = 5

    packet, result = _packet("ag93b_current_official_fact", snapshot)

    assert result.status is GoldenEvaluationStatus.SEARCH_COUNT_OUT_OF_BOUNDS
    search = packet.to_dict()["observed_search_judgment"]
    assert search["search_attempt_count"] == 5
    assert search["expected_bounds"]["max_attempts"] == 2
    assert search["search_count_status"] == "over_maximum"
    assert {item["code"] for item in search["warnings"]} == {"SEARCH_COUNT_OUT_OF_BOUNDS"}
    assert "SEARCH_COUNT_OUT_OF_BOUNDS" in packet.to_markdown()


def test_sufficiency_final_posture_packet_warns_on_direct_with_missing_obligations() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_weak_corpus_insufficient"])
    snapshot["sufficiency"]["decision"] = "ready_direct"
    snapshot["sufficiency"]["final_answer_posture"] = "direct_answer"

    packet, result = _packet("ag93b_weak_corpus_insufficient", snapshot)

    assert result.status is GoldenEvaluationStatus.SUFFICIENCY_POSTURE_FAILED
    sufficiency = packet.to_dict()["observed_sufficiency_judgment"]
    assert sufficiency["posture_status"] == "posture_out_of_bounds"
    assert sufficiency["missing_or_partial_requirement_ids"] == ["req_gamma_official_current"]
    assert {item["code"] for item in sufficiency["warnings"]} == {"DIRECT_POSTURE_WITH_MISSING_OBLIGATIONS"}
    assert "DIRECT_POSTURE_WITH_MISSING_OBLIGATIONS" in packet.to_markdown()


def test_final_answer_packet_guardrail_packet_highlights_missing_caveat_and_upgrade() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_weak_corpus_insufficient"])
    snapshot["final_packet"]["mandatory_caveats"] = []
    snapshot["final_packet"]["prohibited_upgrades"] = []

    packet, result = _packet("ag93b_weak_corpus_insufficient", snapshot)

    assert result.status is GoldenEvaluationStatus.FINAL_PACKET_FAILED
    final_packet = packet.to_dict()["observed_final_answer_packet"]
    assert final_packet["missing_caveats"] == ["official_current_fixture_source_unavailable"]
    assert final_packet["missing_prohibited_upgrades"] == ["do_not_claim_fixture_threshold_without_official_source"]
    assert {item["code"] for item in final_packet["warnings"]} == {
        "MANDATORY_CAVEAT_MISSING",
        "PROHIBITED_UPGRADE_GUARDRAIL_MISSING",
    }
    assert "MANDATORY_CAVEAT_MISSING" in packet.to_markdown()


def test_citation_alignment_packet_reports_expected_vs_observed_source_ids() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["final_answer"]["citations"][0]["source_ids"] = ["src_alpha_secondary_context"]

    packet, result = _packet("ag93b_current_official_fact", snapshot)

    assert result.status is GoldenEvaluationStatus.CITATION_ALIGNMENT_FAILED
    findings = packet.to_dict()["final_answer"]["citation_alignment_findings"]
    assert findings == [
        {
            "ingredient_id": "alpha_current_status",
            "expected_source_ids": ["src_alpha_official_current"],
            "observed_source_ids": ["src_alpha_secondary_context"],
        }
    ]
    markdown = packet.to_markdown()
    assert "alpha_current_status" in markdown
    assert "CITATION_ALIGNMENT_FAILED" in markdown


def test_prose_note_remains_non_failing_and_separate_from_evidence_failures() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["final_answer"]["text"] = "Different wording, same structured official-status ingredient."
    snapshot["final_answer"]["style_notes"] = ["wording changed only"]

    packet, result = _packet("ag93b_current_official_fact", snapshot)

    assert result.passed
    payload = packet.to_dict()
    assert payload["metadata"]["passed"] is True
    assert payload["ag93b_evaluation"]["failing_findings"] == []
    assert payload["ag93b_evaluation"]["prose_style_notes"][0]["status"] == ("PROSE_STYLE_NOTE")
    markdown = packet.to_markdown()
    assert "Prose style notes (non-failing)" in markdown
    assert "Evidence/posture failures: none" in markdown


def test_weak_corpus_insufficient_packet_makes_unavailable_official_source_visible() -> None:
    packet, result = _packet("ag93b_weak_corpus_insufficient")

    assert result.passed
    payload = packet.to_dict()
    assert payload["metadata"]["passed"] is True
    assert payload["observed_search_judgment"]["decision"] == "stop_insufficient"
    assert payload["observed_sufficiency_judgment"]["final_answer_posture"] == ("insufficient_answer")
    assert payload["observed_evidence_ledger"]["unsatisfied_or_partial_requirement_ids"] == [
        "req_gamma_official_current"
    ]
    assert payload["observed_evidence_ledger"]["custody_gaps"][0]["gap_type"] == ("missing_official_current_candidate")
    assert "official Gamma threshold is unavailable" in payload["final_answer"]["text"]
    assert "src_gamma_weak_forum" in packet.to_markdown()


def test_privacy_output_hygiene_blocks_forbidden_fields_from_dict_and_markdown() -> None:
    snapshot = deepcopy(_raw_snapshots()["ag93b_current_official_fact"])
    snapshot["raw_provider_payload"] = "provider payload should not render"
    snapshot["final_answer"]["raw_prompt"] = "prompt should not render"
    snapshot["ledger"]["candidate_records"][0]["api_key"] = "fake-api-key"
    snapshot["ledger"]["private_log"] = "private log should not render"
    snapshot["final_packet"]["cache_blob"] = {"nested": "cache should not render"}
    snapshot["search"]["db_row"] = {"id": 1}
    snapshot["sufficiency"]["full_raw_trace"] = ["trace should not render"]
    snapshot["contract"]["secret"] = "secret should not render"

    packet, result = _packet("ag93b_current_official_fact", snapshot)

    assert result.passed
    rendered_dict = json.dumps(packet.to_dict(), sort_keys=True)
    markdown = packet.to_markdown()
    forbidden_fragments = [
        "raw_provider_payload",
        "raw_prompt",
        "api_key",
        "secret should not render",
        "provider payload should not render",
        "prompt should not render",
        "private log should not render",
        "cache should not render",
        "trace should not render",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in rendered_dict
        assert fragment not in markdown
    assert packet.to_dict()["privacy"]["blocked_or_redacted"] is True
    assert "forbidden/private field or value" in markdown


def test_offline_boundary_static_guard_for_ag93c_module() -> None:
    text = PACKET_MODULE.read_text(encoding="utf-8")
    forbidden_imports = [
        "from core.pipeline_orchestrator",
        "import core.pipeline_orchestrator",
        "from core.provider",
        "import core.provider",
        "from core.providers",
        "import core.providers",
        "from core.runtime_prompt",
        "import core.runtime_prompt",
        "from core.runtime_model",
        "import core.runtime_model",
        "from core.author_execution_runtime",
        "import core.author_execution_runtime",
    ]
    for forbidden in forbidden_imports:
        assert forbidden not in text
    assert "ask_model(" not in text
    assert "python -m proplex" not in text
