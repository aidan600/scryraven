from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

from scripts import ag_fixture_dogfood_integration_01 as dogfood

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ag_fixture_dogfood_integration_01.py"
DOC = ROOT / "docs" / "architecture" / "AG_FIXTURE_DOGFOOD_INTEGRATION_01.md"


def test_generates_three_reviewable_author_prose_packets(tmp_path: Path) -> None:
    generated = dogfood.generate_review_packets(output_dir=tmp_path)

    assert len(generated) == 3
    assert (tmp_path / "index.json").exists()
    assert (tmp_path / "index.md").exists()

    packets = {item.scenario_id: item.packet for item in generated}
    assert set(packets) == {
        "01_full_supported",
        "02_partial_unresolved",
        "03_contested_weak_evidence",
    }

    full = packets["01_full_supported"]
    partial = packets["02_partial_unresolved"]
    contested = packets["03_contested_weak_evidence"]

    assert full["sufficiency_readiness_status"]["final_readiness_status"] == (
        "full_answer_ready"
    )
    assert full["hardened_final_answer_packet_status"]["fap_status"] == (
        "full_answer_packet_ready"
    )
    assert full["author_prose_output"]["author_prose_status"] == (
        "full_answer_prose_created"
    )

    assert partial["sufficiency_readiness_status"]["final_readiness_status"] == (
        "partial_answer_ready"
    )
    assert partial["author_prose_output"]["author_prose_status"] == (
        "partial_answer_prose_created"
    )
    assert partial["author_prose_output"]["supported_component_ids"]
    assert partial["author_prose_output"]["unresolved_component_ids"] == [
        "component:optional-context"
    ]

    assert contested["sufficiency_readiness_status"]["final_readiness_status"] == (
        "contested"
    )
    assert contested["hardened_final_answer_packet_status"]["fap_status"] == (
        "contested_answer_packet"
    )
    assert contested["author_prose_output"]["author_prose_status"] == (
        "contested_answer_prose_created"
    )
    assert contested["caveats_blockers_contested_posture"][
        "contested_posture_preserved"
    ] is True

    for item in generated:
        assert item.json_path.exists()
        assert item.markdown_path.exists()
        loaded = json.loads(item.json_path.read_text(encoding="utf-8"))
        _assert_required_packet_shape(loaded)


def test_review_packets_record_actual_current_path_outputs(tmp_path: Path) -> None:
    generated = dogfood.generate_review_packets(output_dir=tmp_path)

    for item in generated:
        packet = item.packet
        surfaces = {
            surface["surface"]: surface
            for surface in packet["current_path_surfaces_consumed"]
        }
        for required in (
            "SearchResultCandidatePacket",
            "FetchReadContentPacket / SanitizedContentReference",
            "EvidenceLedger candidate/content custody",
            "EvidenceRelativeAnalysisPacket / AnalystReport",
            "SemanticObservation admission",
            "ComponentCoverage",
            "SufficiencyReadiness",
            "hardened FinalAnswerPacket",
            "AuthorProseFinalization",
        ):
            assert surfaces[required]["status"] == "consumed"
            assert surfaces[required]["ref"]

        outputs = packet["current_path_outputs"]
        assert outputs["search_result_candidate_packet"]["packet_id"]
        assert outputs["fetch_read_content_packet"]["packet_id"]
        assert outputs["evidence_relative_analysis_packet"]["packet_id"]
        assert outputs["semantic_observation_admission_projection"][
            "observation_id"
        ]
        assert outputs["component_coverage_projection"]["answer_component_id"]
        assert outputs["sufficiency_readiness_projection"][
            "final_readiness_status"
        ]
        assert outputs["final_answer_packet_projection"]["fap_status"]
        assert outputs["author_prose_projection"]["answer_text"]
        assert packet["generated_by_invoking_current_path_surfaces"] is True
        assert packet["review_packet_theater_guard"]["manual_final_summary_assembly"] is (
            False
        )


def test_review_packets_preserve_non_proofs_and_closed_old_paths(
    tmp_path: Path,
) -> None:
    generated = dogfood.generate_review_packets(output_dir=tmp_path)

    for item in generated:
        packet = item.packet
        assert packet["proof_class"] == dogfood.PROOF_CLASS
        assert packet["product_facing_progress_type"] == (
            dogfood.PRODUCT_PROGRESS_TYPE
        )
        assert packet["old_path_treatment"] == dogfood.OLD_PATH_TREATMENT
        assert packet["mandatory_next_checkpoint"] == (
            dogfood.MANDATORY_NEXT_CHECKPOINT
        )
        for non_proof in dogfood.EXPLICIT_NON_PROOFS:
            assert non_proof in packet["explicit_non_proofs"]
        author = packet["current_path_outputs"]["author_prose_projection"]
        assert author["old_author_runtime_called"] is False
        assert author["pipeline_orchestrator_called"] is False
        assert author["citations_rendered"] is False
        assert author["source_obligation_satisfied"] is False
        assert author["product_correctness_claimed"] is False


def test_static_script_guards_avoid_old_author_and_old_fap_imports() -> None:
    imports, calls = _imports_and_calls(SCRIPT)

    forbidden_imports = {
        "tests",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "core.followup_final_answer_packet_runtime",
        "core.pipeline_orchestrator",
    }
    forbidden_calls = {
        "run_pipeline",
        "execute_author",
        "build_final_answer_packet",
    }
    assert forbidden_imports.isdisjoint(imports)
    assert all(not name.startswith("tests.") for name in imports)
    assert forbidden_calls.isdisjoint(calls)


def test_docs_note_records_command_scenarios_and_non_proofs() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "py scripts/ag_fixture_dogfood_integration_01.py" in text
    assert "01_full_supported" in text
    assert "02_partial_unresolved" in text
    assert "03_contested_weak_evidence" in text
    assert dogfood.MANDATORY_NEXT_CHECKPOINT in text
    for non_proof in dogfood.EXPLICIT_NON_PROOFS:
        assert non_proof in text


def _assert_required_packet_shape(packet: Mapping[str, Any]) -> None:
    for key in (
        "scenario",
        "proof_class",
        "current_path_surfaces_consumed",
        "input_candidate_content_custody_refs",
        "component_coverage_summary",
        "followup_scrutineer_specialist_posture",
        "sufficiency_readiness_status",
        "hardened_final_answer_packet_status",
        "author_prose_output",
        "caveats_blockers_contested_posture",
        "explicit_non_proofs",
    ):
        assert key in packet
    assert packet["author_prose_output"]["answer_text"]
    assert packet["input_candidate_content_custody_refs"]["candidate_refs"]
    assert packet["input_candidate_content_custody_refs"]["content_refs"]
    assert packet["input_candidate_content_custody_refs"]["custody_refs"]


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
    return imported_names, called_names
