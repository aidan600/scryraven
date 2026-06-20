from __future__ import annotations

from pathlib import Path
from typing import Any

from core.followup_author_evidence_content_bridge_runtime import (
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS,
)
from core.followup_author_execution_from_af4d_runtime import (
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STATUS,
)
from core.followup_author_invocation_construction_runtime import (
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS,
)
from core.followup_author_model_request_assembly_runtime import (
    FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS,
)
from core.followup_author_response_finalization_runtime import (
    FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STATUS,
)
from scripts.ag96i3af5c_offline_author_lane_smoke import (
    DEFAULT_ANSWER_TEXT,
    FALSE_BOUNDARY_FLAGS,
    run_offline_author_lane_smoke,
)
from tests.ag96_static_guards import imported_modules

ROOT = Path(__file__).resolve().parents[1]


def test_af5c_offline_author_lane_e2e_smoke_exposes_final_answer_output() -> None:
    result = run_offline_author_lane_smoke()
    kernel = result.kernel
    summary = result.summary
    af4b2 = kernel.state.followup_author_evidence_content_bridge_state
    af4c = kernel.state.followup_author_invocation_construction_state
    af4d = kernel.state.followup_author_model_request_assembly_state
    af5a = kernel.state.followup_author_execution_from_af4d_state
    af5b = kernel.state.followup_author_response_finalization_state
    outcome = kernel.state.final_answer_outcome
    output = outcome["final_answer_output"]
    candidate = af5a["bounded_sanitized_author_response_candidate"]

    assert af4b2["status"] == FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS
    assert af4c["status"] == FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS
    assert af4d["status"] == FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS
    assert af5a["status"] == FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STATUS
    assert af5b["status"] == FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STATUS

    assert output["answer_text"]
    assert output["answer_text"] == DEFAULT_ANSWER_TEXT
    assert outcome["final_answer_text"] == DEFAULT_ANSWER_TEXT
    assert candidate["bounded_sanitized_author_response_candidate_text"] == DEFAULT_ANSWER_TEXT
    assert outcome["af5a_author_response_candidate_ref_id"] == (
        candidate["author_response_candidate_ref_id"]
    )
    assert af5b["af5a_author_response_candidate_digest"] == (
        candidate["author_response_candidate_digest"]
    )

    _assert_packet_source_citation_caveat_refs(outcome)
    assert summary["answer_text"] == DEFAULT_ANSWER_TEXT
    assert summary["final_answer_outcome_id"] == outcome["final_answer_outcome_id"]
    assert summary["final_answer_outcome_digest"] == af5b["final_answer_outcome_digest"]
    assert summary["packet_id"] == kernel.state.final_answer_packet["packet_id"]
    assert summary["source_ref_count"] > 0
    assert summary["citation_ref_count"] > 0
    assert summary["caveat_ref_count"] > 0
    assert all(value is False for value in summary["boundary_flags"].values())

    for surface in (af5a, af5b, outcome):
        _assert_live_provider_search_fetch_ranking_citation_flags_false(surface)


def test_af5c_smoke_harness_stays_off_pipeline_and_live_provider_surfaces() -> None:
    script_path = ROOT / "scripts" / "ag96i3af5c_offline_author_lane_smoke.py"
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.llm",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "dotenv",
    }
    assert imported_modules(script_path).isdisjoint(forbidden_imports)
    source = script_path.read_text(encoding="utf-8")
    for token in (
        "pipeline_orchestrator",
        "ask_model(",
        "execute_author_action(",
        "search_web",
        "render_citation",
        "format_citation",
    ):
        assert token not in source


def _assert_packet_source_citation_caveat_refs(outcome: dict[str, Any]) -> None:
    packet_ref = outcome["final_answer_packet_ref"]
    source_refs = outcome["source_refs"]
    citation_refs = outcome["citation_refs"]
    caveat_refs = outcome["caveat_refs"]

    assert packet_ref["packet_id"]
    assert packet_ref["author_payload_status"]
    assert _has_present_ref(source_refs)
    assert _has_present_ref(citation_refs)
    assert _has_present_ref(caveat_refs)


def _has_present_ref(refs: dict[str, Any]) -> bool:
    for value in refs.values():
        if isinstance(value, list) and value:
            return True
        if value not in (None, "", [], {}):
            return True
    return False


def _assert_live_provider_search_fetch_ranking_citation_flags_false(
    surface: dict[str, Any],
) -> None:
    for flag in FALSE_BOUNDARY_FLAGS:
        if flag in surface:
            assert surface[flag] is False
