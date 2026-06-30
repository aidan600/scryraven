from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.fetch_read_content_reference import (
    FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS,
    select_bounded_answer_bearing_text,
)
from scripts import ag_live_answer_bearing_bounding_repair_01 as repair
from scripts import ag_live_semantic_support_coverage_01 as semantic_harness
from scripts import ag_live_source_survival_fetch_read_custody_01 as source_harness
from tests.test_ag_live_source_survival_fetch_read_custody_01 import (
    FakeFetcher,
    _fake_fetch_result,
    _output_dir,
    _prior_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
REPAIR_SCRIPT = ROOT / "scripts" / "ag_live_answer_bearing_bounding_repair_01.py"
DOC = ROOT / "docs" / "architecture" / "AG_LIVE_ANSWER_BEARING_BOUNDING_REPAIR_01.md"

ANCHORS = source_harness.TARGET_COMPONENT_ANCHOR_GROUPS


def _late_answer_text() -> str:
    prefix = " ".join(["general travel instructions"] * 180)
    answer_window = (
        "Passport Fees Travel.gov. Adult applicants age 16 and older who use "
        "DS-82 renewal for a U.S. passport book pay the passport book fee $130. "
        "This local source region is bounded sanitized readable content."
    )
    suffix = " ".join(["routine processing notes"] * 80)
    return f"{prefix} {answer_window} {suffix}"


def _semantic_output_dir(name: str) -> Path:
    return ROOT / "output" / "ag_live_semantic_support_coverage_01" / (
        f"answer-bearing-bounding-{name}"
    )


def _reduce_359_from_source(source_dir: Path, name: str) -> dict[str, Any]:
    return semantic_harness.reduce_semantic_coverage(
        source_survival_packet_path=source_dir / source_harness.SOURCE_PACKET_NAME,
        fetch_read_content_packet_path=source_dir / source_harness.FETCH_READ_PACKET_NAME,
        sanitized_content_reference_path=source_dir / source_harness.CONTENT_REFERENCE_NAME,
        evidence_ledger_projection_path=source_dir / source_harness.LEDGER_PROJECTION_NAME,
        output_dir=_semantic_output_dir(name),
        confirm_semantic_coverage=True,
        run_kernel=None,
    )


def _source_packet_from_text(name: str, text: str) -> tuple[dict[str, Any], Path]:
    candidate_path, validation_path = _prior_outputs(f"answer-bearing-{name}")
    source_dir = _output_dir(f"answer-bearing-{name}")
    packet = source_harness.fetch_read_custody(
        candidate_packet_path=candidate_path,
        validation_packet_path=validation_path,
        output_dir=source_dir,
        confirm_fetch_read=True,
        fetcher=FakeFetcher(_fake_fetch_result(text=text)),
    )
    return packet, source_dir


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    return imported, called


def test_old_prefix_bounding_misses_late_answer_bearing_content() -> None:
    text = _late_answer_text()
    old_prefix = " ".join(text.split())[:FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS]

    assert "$130" not in old_prefix
    assert "Adult applicants" not in old_prefix

    selection = select_bounded_answer_bearing_text(
        text,
        max_chars=FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS,
        required_or_preferred_anchors=ANCHORS,
    )

    assert len(selection.bounded_text) <= FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS
    assert "$130" in selection.bounded_text
    assert "Adult applicants" in selection.bounded_text
    assert "passport book" in selection.bounded_text
    assert selection.selection_strategy == "answer_anchor_single_contiguous_window"
    assert selection.missing_anchors == ()
    assert selection.local_context_posture == "single_contiguous_window"
    assert selection.anti_anchor_laundering_passed is True


def test_selector_records_safe_metadata_and_no_unbounded_text() -> None:
    selection = select_bounded_answer_bearing_text(
        _late_answer_text(),
        required_or_preferred_anchors=ANCHORS,
    )
    metadata = selection.to_metadata()

    assert metadata["bounded_text_char_count"] == len(selection.bounded_text)
    assert metadata["bounded_text_digest"] == selection.bounded_text_digest
    assert metadata["not_semantic_support"] is True
    assert metadata["not_citation_eligible"] is True
    assert metadata["not_source_obligation_satisfied"] is True
    assert "bounded_text" not in metadata
    assert "unbounded_text" not in _all_keys(metadata)


def test_missing_anchors_fail_honestly_without_false_support() -> None:
    selection = select_bounded_answer_bearing_text(
        "Passport renewal page for a book without the adult amount.",
        required_or_preferred_anchors=ANCHORS,
    )

    assert selection.matched_anchor_count < selection.required_anchor_count
    assert selection.missing_anchors
    assert "$130/130" in selection.missing_anchors


def test_selector_does_not_concatenate_distant_anchor_fragments() -> None:
    distant = (
        "adult "
        + " ".join(["spacing"] * 500)
        + " passport book "
        + " ".join(["spacing"] * 500)
        + " renewal "
        + " ".join(["spacing"] * 500)
        + " $130"
    )

    selection = select_bounded_answer_bearing_text(
        distant,
        required_or_preferred_anchors=ANCHORS,
    )

    assert len(selection.bounded_text) <= FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS
    assert selection.local_context_posture == "single_contiguous_window"
    assert selection.anti_anchor_laundering_passed is True
    assert selection.missing_anchors
    assert not all(anchor in selection.bounded_text.casefold() for anchor in ("adult", "passport", "renew"))


def test_358_harness_uses_repaired_selector_for_late_answer_window() -> None:
    packet, _source_dir = _source_packet_from_text("358-selector", _late_answer_text())
    ref = packet["sanitized_content_reference_ref"]
    selection = ref["bounded_text_selection"]

    assert packet["selected_source_survived"] == "source_survival_pass"
    assert ref["bounded_text_char_count"] <= FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS
    assert selection["selection_strategy"] == "answer_anchor_single_contiguous_window"
    assert selection["missing_anchors"] == []
    assert selection["matched_anchor_count"] == len(ANCHORS)
    assert packet["bounded_text_selection"]["bounded_text_digest"] == ref["bounded_text_digest"]


def test_359_advances_past_source_content_insufficient_for_late_answer_window() -> None:
    _source_packet, source_dir = _source_packet_from_text("359-advances", _late_answer_text())

    packet = _reduce_359_from_source(source_dir, "359-advances")

    assert packet["semantic_support_result"] == (
        "semantic_support_fail_semantic_observation_admission"
    )
    assert packet["first_failed_gate"] == "gate_6_semantic_observation_admission"
    assert packet["semantic_observation_attempted_count"] == 1
    assert packet["component_coverage_reduced_count"] == 0


def test_359_still_fails_source_content_insufficient_when_support_is_absent() -> None:
    _source_packet, source_dir = _source_packet_from_text(
        "359-still-insufficient",
        "Passport renewal page for a book without the adult renewal amount.",
    )

    packet = _reduce_359_from_source(source_dir, "359-still-insufficient")

    assert packet["semantic_support_result"] == (
        "semantic_support_fail_source_content_insufficient"
    )
    assert packet["first_failed_gate"] == "gate_5_evidence_relative_analysis_proposal"


def test_repair_packet_records_post_repair_gate_and_closed_surfaces() -> None:
    source_packet, source_dir = _source_packet_from_text("repair-packet", _late_answer_text())
    semantic_packet = _reduce_359_from_source(source_dir, "repair-packet")

    packet = repair.build_repair_packet(
        source_packet=source_packet,
        semantic_packet=semantic_packet,
        old_source_packet={},
        old_semantic_packet={
            "semantic_support_result": "semantic_support_fail_source_content_insufficient",
            "first_failed_gate": "gate_5_evidence_relative_analysis_proposal",
        },
    )

    assert packet["mode"] == "REPAIR"
    assert packet["repair_verdict_target"] == "YES"
    assert packet["selector_strategy"] == "answer_anchor_single_contiguous_window"
    assert packet["missing_anchors"] == []
    assert packet["repaired_bounded_content_answer_bearing_enough_for_359_gate_5"] is True
    assert packet["post_repair_359_semantic_support_result"] == (
        "semantic_support_fail_semantic_observation_admission"
    )
    assert packet["first_failed_gate_after_repair"] == "gate_6_semantic_observation_admission"
    assert packet["provider_search_calls"] == 0
    assert packet["broker_calls"] == 0
    assert packet["model_calls"] == 0


def test_closed_surfaces_stay_closed_and_pytest_does_not_run_live_fetch() -> None:
    imported, called = _imports_and_calls(REPAIR_SCRIPT)
    forbidden_imports = {
        "core.search_providers",
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "scripts.run_provider_proxy_broker_once",
    }
    forbidden_calls = {
        "call_broker",
        "invoke_broker",
        "search_web",
        "ask_model",
        "execute_author",
        "create_final_answer_packet",
    }

    assert imported.isdisjoint(forbidden_imports)
    assert called.isdisjoint(forbidden_calls)
    with pytest.raises(repair.AnswerBearingBoundingRepairError) as exc_info:
        repair.verify_live_repair(confirm_fetch_read_repair=False)
    assert exc_info.value.code == "confirm_fetch_read_repair_required"


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "raw_html",
        "headers",
        "unbounded_text",
        "answer_text",
        "citations",
        "final_answer_packet",
        "author_material",
        "prompt",
        "model_response",
        "provider_payload",
        "secret",
    ],
)
def test_repair_output_rejects_raw_unbounded_answer_citation_fap_author_and_secret_fields(
    forbidden_key: str,
) -> None:
    source_packet, source_dir = _source_packet_from_text(
        f"reject-{forbidden_key}",
        _late_answer_text(),
    )
    semantic_packet = _reduce_359_from_source(source_dir, f"reject-{forbidden_key}")
    packet = repair.build_repair_packet(
        source_packet=source_packet,
        semantic_packet=semantic_packet,
    )
    spoofed = deepcopy(packet)
    spoofed[forbidden_key] = "forbidden"

    with pytest.raises(repair.AnswerBearingBoundingRepairError):
        repair.validate_repair_packet(spoofed)


def test_doc_records_repair_mode_boundaries_and_next_checkpoint() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "Mode: REPAIR",
        "semantic_support_fail_source_content_insufficient",
        "coherent answer-bearing window",
        "one contiguous source-derived window",
        "provider/search/broker calls: 0",
        "model calls: 0",
        "AG-LIVE-SEMANTIC-SUPPORT-COVERAGE-REPLAY-01",
    )
    for needle in required:
        assert needle in text
