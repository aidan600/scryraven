from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts import ag_local_dryrun_query_to_authorprose_01 as dryrun

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ag_local_dryrun_query_to_authorprose_01.py"
DOC = ROOT / "docs" / "architecture" / "AG_LOCAL_DRYRUN_QUERY_TO_AUTHORPROSE_01.md"
QUERY = "What is the official current permit threshold for the example program?"


def test_accepts_user_style_query_and_records_query_ref(tmp_path: Path) -> None:
    generated = dryrun.generate_query_dry_run_packets(
        query=QUERY,
        scenario="full_supported",
        output_dir=tmp_path,
    )

    assert len(generated) == 1
    packet = generated[0].packet
    loaded = json.loads(generated[0].json_path.read_text(encoding="utf-8"))

    assert loaded["original_user_query"] == QUERY
    assert packet["original_user_query"] == QUERY
    assert packet["query_digest_ref"]["ordinary_query_ref"]["digest"] == (
        dryrun._ordinary_query_digest(QUERY)
    )
    current_path_query_ref = packet["query_digest_ref"]["current_path_user_query_ref"]
    assert current_path_query_ref["preview"] == QUERY
    assert current_path_query_ref["digest"]

    query_driven = packet["query_driven_inputs_and_refs"]
    assert query_driven["component_search_requirements"][0][
        "requirement_summary"
    ] == QUERY
    assert query_driven["search_planner_user_query_ref"]["preview"] == QUERY
    assert generated[0].markdown_path.exists()
    assert (tmp_path / "index.json").exists()
    assert (tmp_path / "index.md").exists()


def test_required_scenarios_reach_authorprose_postures(tmp_path: Path) -> None:
    generated = dryrun.generate_query_dry_run_packets(
        query=QUERY,
        scenario="all",
        output_dir=tmp_path,
    )

    packets = {item.scenario_id: item.packet for item in generated}
    assert set(packets) == {
        "01_full_supported",
        "02_partial_unresolved",
        "03_contested_weak_evidence",
    }

    full = packets["01_full_supported"]
    assert full["sufficiency_readiness_status"]["final_readiness_status"] == (
        "full_answer_ready"
    )
    assert full["hardened_final_answer_packet_status"]["fap_status"] == (
        "full_answer_packet_ready"
    )
    assert full["author_prose_output"]["author_prose_status"] == (
        "full_answer_prose_created"
    )

    partial = packets["02_partial_unresolved"]
    assert partial["sufficiency_readiness_status"]["final_readiness_status"] == (
        "partial_answer_ready"
    )
    assert partial["author_prose_output"]["author_prose_status"] == (
        "partial_answer_prose_created"
    )
    assert partial["author_prose_output"]["unresolved_component_ids"] == [
        "component:optional-context"
    ]
    initial_ref = partial["query_driven_inputs_and_refs"][
        "initial_answer_contract_ref"
    ]
    current_ref = partial["query_driven_inputs_and_refs"][
        "current_answer_contract_ref"
    ]
    assert initial_ref["component_count"] == 2
    assert current_ref["component_count"] == 2
    assert "component:optional-context" in initial_ref["component_ids"]

    contested = packets["03_contested_weak_evidence"]
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


def test_packets_distinguish_query_fixture_and_fake_provider_posture(
    tmp_path: Path,
) -> None:
    generated = dryrun.generate_query_dry_run_packets(
        query=QUERY,
        scenario="full_supported",
        output_dir=tmp_path,
    )
    packet = generated[0].packet

    inherited = packet["deterministic_fixture_inheritance_reuse"]
    assert inherited["reused_current_path_chain"] is True
    assert "SearchPlannerInput.user_query_text" in inherited[
        "newly_ordinary_query_driven_fields"
    ]
    assert "fake provider-result records" in inherited[
        "inherited_deterministic_fixture_fields"
    ]

    fake = packet["fake_captured_provider_result_posture"]
    assert fake["provider_result_kind"] == (
        "fake_offline_sanitized_provider_result_records"
    )
    assert fake["fake_provider_used"] is True
    assert fake["broker_invoked"] is False
    assert fake["live_provider_called"] is False
    assert fake["raw_provider_payload_retained"] is False
    assert fake["raw_search_response_retained"] is False
    assert fake["real_acquisition_quality_claimed"] is False
    assert fake["ranking_quality_claimed"] is False
    assert "do not imply real acquisition" in fake["disclosure"]

    assert packet["live_validation_status"].startswith("not run and not licensed")
    for non_proof in dryrun.EXPLICIT_NON_PROOFS:
        assert non_proof in packet["explicit_non_proofs"]


def test_packets_record_actual_current_path_outputs_not_manual_summary(
    tmp_path: Path,
) -> None:
    generated = dryrun.generate_query_dry_run_packets(
        query=QUERY,
        scenario="all",
        output_dir=tmp_path,
    )

    for item in generated:
        packet = item.packet
        outputs = packet["current_path_outputs"]
        assert outputs["search_planner_proposal_state"]["user_query_ref"][
            "preview"
        ] == QUERY
        assert outputs["search_executor_handoff_state"]["handoff_id"]
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
        assert packet["author_prose_output"]["answer_text"] == outputs[
            "author_prose_projection"
        ]["answer_text"]
        assert packet["review_packet_theater_guard"][
            "manual_final_summary_assembly"
        ] is False
        assert packet["review_packet_theater_guard"][
            "manual_author_prose_text"
        ] is False
        assert packet["review_packet_theater_guard"][
            "actual_current_path_outputs_recorded"
        ] is True


def test_old_paths_remain_quarantined_and_state_mutation_is_avoided(
    tmp_path: Path,
) -> None:
    generated = dryrun.generate_query_dry_run_packets(
        query=QUERY,
        scenario="full_supported",
        output_dir=tmp_path,
    )
    packet = generated[0].packet
    author = packet["current_path_outputs"]["author_prose_projection"]

    assert packet["direct_state_mutation_avoided"] is True
    assert packet["old_path_treatment"] == dryrun.OLD_PATH_TREATMENT
    assert author["old_author_runtime_called"] is False
    assert author["pipeline_orchestrator_called"] is False
    assert author["citations_rendered"] is False
    assert author["source_obligation_satisfied"] is False
    assert author["product_correctness_claimed"] is False


def test_static_script_guards_avoid_old_author_and_direct_contract_mutation() -> None:
    imports, calls = _imports_and_calls(SCRIPT)

    forbidden_imports = {
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
    assert forbidden_calls.isdisjoint(calls)

    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign):
            targets = list(getattr(node, "targets", ())) or [node.target]
            for target in targets:
                assert not _contains_attr_or_key(target, "current_answer_contract")
                assert not _contains_attr_or_key(
                    target,
                    "accepted_answer_component_refs",
                )
                assert not _contains_attr_or_key(
                    target,
                    "accepted_answer_component_count",
                )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert not (
                node.func.attr == "append"
                and _contains_attr_or_key(
                    node.func.value,
                    "accepted_answer_component_refs",
                )
            )


def test_docs_note_records_command_scenarios_and_non_proofs() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "py scripts/ag_local_dryrun_query_to_authorprose_01.py" in text
    assert "--query" in text
    assert "full_supported" in text
    assert "partial_unresolved" in text
    assert "contested_weak" in text
    assert "user-style query" in text
    assert dryrun.MANDATORY_NEXT_CHECKPOINT in text
    for non_proof in dryrun.EXPLICIT_NON_PROOFS:
        assert non_proof in text


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


def _contains_attr_or_key(node: ast.AST, name: str) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and child.attr == name:
            return True
        if isinstance(child, ast.Constant) and child.value == name:
            return True
    return False
