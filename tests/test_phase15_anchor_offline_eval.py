from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tests.replay_jsonl_utils import load_jsonl_dict_rows

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "phase15_anchor_offline_eval.jsonl"

REQUIRED_CASE_CLASSES = {
    "recent_mutable_official_rule",
    "likely_non_public_evidence",
    "proxy_only_target_metric_risk",
    "latest_current_wording_over_trigger",
    "public_notice_change_over_trigger",
    "explicit_proxy_private_over_trigger",
    "bounded_comparison_under_trigger",
    "causal_hidden_evidence_under_trigger",
    "simple_evergreen_lookup_negative_control",
    "fully_specified_metric_negative_control",
    "fully_specified_current_retention_over_trigger",
    "fully_specified_margin_metric_over_trigger",
    "historical_official_current_rule_over_trigger",
}

OVER_TRIGGER_GAP_CONTROL_CASE_IDS = {
    "fully_specified_current_retention_possible_over_trigger",
    "fully_specified_margin_metric_possible_over_trigger",
    "historical_official_current_rule_possible_over_trigger",
}

REVIEWER_LABELS = {
    "reviewable_true_positive",
    "reviewable_likely_over_trigger",
    "reviewable_likely_under_trigger",
    "reviewable_negative_control",
    "unclear_needs_human_review",
}

ALLOWED_TOP_LEVEL_FIELDS = {
    "case_id",
    "case_class",
    "query_shape",
    "anchor_packet_present",
    "anchor_packet_next_action",
    "anchor_packet_ambiguity_types",
    "anchor_packet",
    "expected_reviewer_label",
    "expected_review_rationale",
    "is_negative_control",
    "must_not_imply_behavior_change",
}

ANCHOR_PACKET_FIELDS = {
    "confidence_bucket",
    "freshness_requirement",
    "source_class_expectation",
    "answerability_forecast",
    "decomposition_hints",
    "off_domain_traps",
}

FORBIDDEN_FIELD_NAMES = {
    "conversation",
    "database",
    "db_path",
    "event",
    "execution_trace",
    "final_answer",
    "final_output",
    "golden_answer",
    "messages",
    "model_output",
    "prompt",
    "provider_payload",
    "provider_response",
    "raw_log",
    "raw_model_output",
    "raw_prompt",
    "raw_transcript",
    "run_id",
    "secret",
    "session_id",
    "system_prompt",
    "transcript",
    "user_prompt",
}

FORBIDDEN_VALUE_PATTERNS = (
    r"://",
    r"\bwww\.",
    r"\.com\b",
    r"\.db\b",
    r"\bapi[_-]?key\b",
    r"\bsecret\b",
    r"\btoken\b",
    r"\bpassword\b",
    r"\bexecution_log\b",
    r"\boutput/",
    r"\boutput\\",
    r"\bproplex\b",
    r"\borigin/main\b",
    r"\bbranch\b",
    r"\bcommit\b",
    r"[a-z]:\\",
)

FORBIDDEN_BEHAVIOR_IMPLICATIONS = {
    "diagnostics do not become gates",
    "no active probe",
    "no prompt change",
    "no query-generation change",
    "no retrieval change",
    "no provider change",
    "no search-depth change",
    "no analyst change",
    "no economist change",
    "no author change",
    "no weak-corpus behavior change",
}


def _rows() -> list[dict[str, Any]]:
    return load_jsonl_dict_rows(FIXTURE_PATH)


def _iter_keys_and_values(value: Any) -> list[tuple[str | None, Any]]:
    found: list[tuple[str | None, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.append((key, item))
            found.extend(_iter_keys_and_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_iter_keys_and_values(item))
    else:
        found.append((None, value))
    return found


def _has_reviewable_retrieve_reason(row: dict[str, Any]) -> bool:
    packet = row["anchor_packet"]
    hints = set(packet["decomposition_hints"])
    ambiguity = set(row["anchor_packet_ambiguity_types"])
    return any(
        (
            packet["freshness_requirement"] in {"high", "official-current"},
            packet["source_class_expectation"] == "official"
            and "include-official-source" in hints,
            packet["answerability_forecast"] in {"likely non-public", "proxy-only risk"},
            bool({"evidence-access", "temporal", "metric"} & ambiguity),
        )
    )


def test_phase15_anchor_offline_eval_fixture_is_scrubbed_data_only() -> None:
    raw = FIXTURE_PATH.read_bytes()
    rows = _rows()

    assert FIXTURE_PATH.suffix == ".jsonl"
    assert raw[:1] != b"["
    assert len(raw) < 20 * 1024
    assert len(rows) == 13

    for row in rows:
        assert set(row) == ALLOWED_TOP_LEVEL_FIELDS
        assert set(row["anchor_packet"]) == ANCHOR_PACKET_FIELDS
        for key, value in _iter_keys_and_values(row):
            assert key not in FORBIDDEN_FIELD_NAMES
            if isinstance(value, str):
                assert value == value.lower()
                assert not any(
                    re.search(pattern, value, flags=re.IGNORECASE)
                    for pattern in FORBIDDEN_VALUE_PATTERNS
                )


def test_phase15_anchor_offline_eval_required_case_classes_are_present() -> None:
    rows = _rows()
    case_classes = [row["case_class"] for row in rows]

    assert set(case_classes) == REQUIRED_CASE_CLASSES
    assert len(case_classes) == len(set(case_classes))


def test_phase15_anchor_offline_eval_rows_have_reviewer_labels_and_rationales() -> None:
    for row in _rows():
        assert row["expected_reviewer_label"] in REVIEWER_LABELS
        assert row["expected_review_rationale"]
        assert row["anchor_packet_present"] is True
        assert row["anchor_packet_next_action"] in {
            "proceed_single_frame",
            "preserve_multiple_frames",
            "retrieve_to_anchor",
            "ask_clarification",
        }


def test_retrieve_to_anchor_rows_are_reviewable_without_probe_reason_field() -> None:
    retrieve_rows = [
        row for row in _rows() if row["anchor_packet_next_action"] == "retrieve_to_anchor"
    ]

    assert retrieve_rows
    for row in retrieve_rows:
        assert "recommended_probe_reason" not in row
        assert "retrieve_to_anchor_recommended" not in row
        assert "recommended_probe_reason" not in row["anchor_packet"]
        assert _has_reviewable_retrieve_reason(row)


def test_over_and_under_trigger_rows_are_review_cases_not_behavior_gates() -> None:
    rows = _rows()
    over_trigger_rows = [
        row
        for row in rows
        if row["expected_reviewer_label"] == "reviewable_likely_over_trigger"
    ]
    under_trigger_rows = [
        row
        for row in rows
        if row["expected_reviewer_label"] == "reviewable_likely_under_trigger"
    ]

    assert len(over_trigger_rows) == 6
    assert len(under_trigger_rows) == 2
    for row in over_trigger_rows + under_trigger_rows:
        invariants = set(row["must_not_imply_behavior_change"])
        assert "diagnostics do not become gates" in invariants
        assert "no active probe" in invariants


def test_over_trigger_gap_controls_are_present_and_review_only() -> None:
    rows_by_id = {row["case_id"]: row for row in _rows()}

    assert OVER_TRIGGER_GAP_CONTROL_CASE_IDS <= set(rows_by_id)
    for case_id in OVER_TRIGGER_GAP_CONTROL_CASE_IDS:
        row = rows_by_id[case_id]

        assert row["expected_reviewer_label"] in {
            "reviewable_likely_over_trigger",
            "reviewable_negative_control",
        }
        assert row["expected_review_rationale"]
        assert FORBIDDEN_BEHAVIOR_IMPLICATIONS <= set(
            row["must_not_imply_behavior_change"]
        )


def test_negative_controls_do_not_recommend_active_probes() -> None:
    negative_controls = [row for row in _rows() if row["is_negative_control"] is True]

    assert len(negative_controls) == 2
    for row in negative_controls:
        assert row["expected_reviewer_label"] == "reviewable_negative_control"
        assert row["anchor_packet_next_action"] != "retrieve_to_anchor"
        assert "no active probe" in row["must_not_imply_behavior_change"]


def test_no_row_implies_behavior_surface_changes() -> None:
    for row in _rows():
        invariants = set(row["must_not_imply_behavior_change"])
        assert FORBIDDEN_BEHAVIOR_IMPLICATIONS <= invariants


def test_fixture_rows_are_data_only_and_not_pipeline_replay_events() -> None:
    for row in _rows():
        assert "event" not in row
        assert "run_id" not in row
        assert "session_id" not in row
        assert "execution_trace" not in row
