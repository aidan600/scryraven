from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core import post_analyst_handoff_packaging as stage


def _evidence(url: str, text: str, source_id: str) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "url": url,
        "title": f"Title {source_id}",
        "score": 0.9,
        "source_tier": "official",
        "source_class": "official",
        "text": text,
    }


def _base_kwargs(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "run_id": "run-ag90g",
        "analyst_skipped": False,
        "analyst_skip_reason": None,
        "post_retrieval_fast_path_used": False,
        "pre_analyst_gate_signals": ["official_evidence_found"],
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": None,
        "economist_output_used_as_analysis": False,
        "analyst_evidence": [_evidence("https://analyst.example/a", "analyst text", "a1")],
        "analyst_context_prefix": "ANALYST PREFIX",
        "linkup_block_included": True,
        "quantitative_packet_injected": True,
        "missing_target_metric_directive_emitted": True,
        "corpus_weak": False,
        "failure_card_payload": {"show": False, "reason": None},
        "author_notes": "Author note",
        "author_evidence": [_evidence("https://author.example/a", "author text", "au1")],
        "selected_evidence": [_evidence("https://selected.example/a", "selected text", "s1")],
        "final_evidence": [_evidence("https://final.example/a", "final text", "f1")],
        "ordered_sources": ["https://final.example/a"],
        "unique_source_urls": ["https://final.example/a"],
        "author_evidence_block": "AUTHOR EVIDENCE BLOCK",
        "author_prompt": "Prompt with sourced analyst-reviewed synthesis.",
        "complexity": "medium",
        "author_system_prompt_key": "author_standard",
        "author_effort": "medium",
        "includes_analysis": True,
        "includes_recency_notes": True,
        "includes_author_notes": True,
        "image_context_active": False,
        "pre_analyst_gate_ref": {"gate": "ref"},
        "retrieval_loop_state": {"loop": "state"},
        "router_query_preparation_state": {"router": "state"},
        "report_type": "quantitative_comparison",
        "mode": "Balanced",
        "economist_safety_telemetry": {
            "quantitative_packet_valid": True,
            "quantitative_packet_direct_use_eligible": True,
            "quantitative_packet_requires_analyst": False,
            "high_stakes_quant_detected": False,
            "economist_code_execution_requested": False,
        },
        "analyst_quant_packet_handoff_telemetry": {
            "analyst_quant_packet_reviewed_by_model": True,
            "analyst_model_called": True,
        },
        "author_quant_source_telemetry": {
            "author_quant_content_source": "analyst_reviewed",
            "author_received_raw_quant_packet": False,
            "author_received_economist_framework": False,
            "author_received_analyst_packet_marker": False,
            "author_quant_handoff_gate_reason": "author_received_analyst_reviewed_quantitative_synthesis",
        },
        "quant_retrieval_sufficiency_telemetry": {
            "quant_retrieval_target_detected": True,
            "quant_retrieval_sufficiency_valid": True,
        },
        "economist_pre_analyst_skip_candidate_telemetry": {
            "economist_pre_analyst_skip_candidate_shadow": True,
        },
        "pre_analyst_gate_skipped": False,
    }
    values.update(overrides)
    return values


def test_build_post_analyst_handoff_packaging_preserves_handoff_shape() -> None:
    outcome = stage.build_post_analyst_handoff_packaging(**_base_kwargs())

    state = outcome.analyst_author_handoff_state
    trace = state.to_controller_state()
    assert outcome.author_system_prompt_key == "author_standard"
    assert outcome.author_effort == "medium"
    assert outcome.analyst_author_handoff.author_system_prompt_key == "author_standard"
    assert trace["run_id"] == "run-ag90g"
    assert trace["analyst_admission"] == {
        "controller_owned": True,
        "analyst_should_run": True,
        "analyst_skipped": False,
        "analyst_skip_reason": None,
        "post_retrieval_fast_path_used": False,
        "pre_analyst_gate_signals": ["official_evidence_found"],
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": None,
        "economist_output_used_as_analysis": False,
        "legacy_runtime_branch": "pre_analyst_gate_contract",
        "mechanical_handoff_only": True,
    }
    assert trace["analyst_evidence_context"]["evidence_count"] == 1
    assert trace["analyst_evidence_context"]["linkup_block_included"] is True
    assert trace["analyst_evidence_context"]["quantitative_packet_injected"] is True
    assert trace["unsupported_directives"]["failure_card_directive_active"] is False
    assert trace["author_prompt_input"]["complexity"] == "medium"
    assert trace["author_prompt_input"]["includes_analysis"] is True
    assert outcome.economist_skip_eligibility_shadow_telemetry["economist_skip_eligible_shadow"] is True
    assert outcome.economist_skip_shadow_alignment == "candidate_and_posthoc_eligible"


def test_from_scope_scans_author_quant_source_and_preserves_failure_card() -> None:
    scope = _base_kwargs(
        analyst_skipped=True,
        analyst_skip_reason="pre_analyst_gate_weak_retrieval",
        pre_analyst_gate_signals=["missing_official_evidence"],
        analyst_context_prefix="SCOPED PREFIX",
        linkup_block="LINKUP",
        _pre_gate_failure_card_show=True,
        _pre_gate_failure_card_reason="weak_retrieval",
        author_prompt="Final prompt that includes quantitative_packet_v1 by mistake.",
        author_quant_source_telemetry={},
        _author_effort="low",
        strategy="Balanced",
        pre_analyst_gate={"analyst_skipped": True},
        _efp_author=False,
        _relevance_low=False,
    )
    # Scope adapter names differ from direct kwargs for a few orchestrator locals.
    scope.update(
        {
            "linkup_block": scope.pop("linkup_block"),
            "analyst_cached_prefix": scope.pop("analyst_context_prefix"),
            "_pre_gate_failure_card_show": scope.pop("_pre_gate_failure_card_show"),
            "_pre_gate_failure_card_reason": scope.pop("_pre_gate_failure_card_reason"),
            "strategy": scope.pop("strategy"),
            "_author_effort": scope.pop("_author_effort"),
            "pre_analyst_gate": scope.pop("pre_analyst_gate"),
            "_efp_author": scope.pop("_efp_author"),
            "_relevance_low": scope.pop("_relevance_low"),
            "analysis": "Analyst reviewed the quantitative packet.",
            "recency_notes": "recent",
            "image_context": None,
            "pre_analyst_gate_contract": {"gate": "contract"},
            "retrieval_loop_contract_state": {"retrieval": "state"},
            "router_query_preparation_contract": {"router": "contract"},
            "final_top_evidence": scope["selected_evidence"],
        }
    )
    for direct_only_key in (
        "analyst_evidence", "linkup_block_included", "quantitative_packet_injected",
        "failure_card_payload", "selected_evidence", "final_evidence", "mode",
        "pre_analyst_gate_skipped",
    ):
        scope.pop(direct_only_key, None)

    outcome = stage.build_post_analyst_handoff_packaging_from_scope(
        scope,
        evidence_slice_for_analyst=lambda: [_evidence("https://scope.example", "scope text", "sc")],
    )

    trace = outcome.analyst_author_handoff_state.to_controller_state()
    assert outcome.author_quant_source_telemetry["author_quant_content_source"] == "raw_quant_packet_detected"
    assert trace["analyst_admission"]["analyst_skipped"] is True
    assert trace["unsupported_directives"]["failure_card_directive_active"] is True
    assert trace["unsupported_directives"]["failure_card_reason"] == "weak_retrieval"
    assert trace["analyst_evidence_context"]["context_prefix_length"] == len("SCOPED PREFIX")
    assert trace["analyst_evidence_context"]["evidence_count"] == 1
    assert outcome.economist_skip_eligibility_shadow_telemetry[
        "economist_skip_eligibility_gate_reason"
    ] == "blocked_by_author_marker_leak"


def test_static_post_analyst_packaging_seam_guard() -> None:
    helper_path = Path("core/post_analyst_handoff_packaging.py")
    orchestrator_path = Path("core/pipeline_orchestrator.py")
    helper_source = helper_path.read_text()
    orchestrator_source = orchestrator_path.read_text()
    assert "{**globals(), **locals()}" not in helper_source + orchestrator_source
    assert "globals()" not in helper_source

    tree = ast.parse(helper_source)
    forbidden_import_fragments = ("provider", "search", "prompt", "model", "citation")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(
                fragment in alias.name for alias in node.names for fragment in forbidden_import_fragments
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not any(fragment in module for fragment in forbidden_import_fragments)
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            assert name not in {
                "ask_model",
                "process_search_queries",
                "select_providers",
                "choose_supplemental_search_depth",
                "format_citations",
                "build_final_evidence_bundle",
            }
