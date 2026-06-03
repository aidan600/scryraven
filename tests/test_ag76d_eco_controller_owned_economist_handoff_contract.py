from __future__ import annotations

import ast
from pathlib import Path

from core.analyst_author_handoff_contract import build_analyst_author_handoff_state
from core.citation_source_handoff_contract import build_citation_source_handoff_state
from core.economist_handoff_contract import (
    ECONOMIST_HANDOFF_SCHEMA_VERSION,
    ECONOMIST_HANDOFF_TRACE_KEY,
    build_economist_handoff_state,
    execute_economist_handoff,
)
from tests.static_import_guard_utils import assert_controller_contract_imports_closed

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "core" / "economist_handoff_contract.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
PIPELINE_CORE = ROOT / "core" / "pipeline.py"
PROMPTS = ROOT / "core" / "prompts.py"


def _packet() -> dict[str, object]:
    return {
        "schema_version": "quantitative_packet_v1",
        "query": "Compare two products",
        "economist_schema_version": "economist_v1",
        "source_ids_used": [1, 2],
        "source_bound_values": [
            {
                "name": "a_price",
                "entity": "A",
                "metric": "price",
                "period": "2026",
                "value": "$10",
                "unit": "USD",
                "source_id": 1,
            }
        ],
        "unsupported_values": ["B price is missing"],
        "calculation_results": [{"name": "difference", "value": "unavailable"}],
        "target_metric_names": ["price"],
        "target_metric_bound_value_refs": ["a_price"],
        "target_metric_calculation_refs": [],
        "unsupported_values_count": 1,
        "high_stakes_quant_detected": False,
        "requires_analyst": True,
        "direct_use_eligible": False,
        "validation_errors": ["missing:B price"],
    }


def _safety(**overrides: object) -> dict[str, object]:
    packet = _packet()
    data: dict[str, object] = {
        "economist_code_execution_requested": False,
        "economist_code_execution_blocked": False,
        "economist_safety_status": "code_execution_disabled",
        "economist_skip_reason": None,
        "economist_schema_version": "economist_v1",
        "economist_schema_valid": True,
        "source_binding_valid": True,
        "source_bound_value_count": 1,
        "source_ids_used": [1, 2],
        "target_metric_names": ["price"],
        "target_metric_missing": ["B price"],
        "quantitative_packet_present": True,
        "quantitative_packet_valid": False,
        "quantitative_packet_validation_errors": ["missing:B price"],
        "quantitative_packet_direct_use_eligible": False,
        "quantitative_packet_requires_analyst": True,
        "quantitative_packet_shadow_mode": True,
        "quantitative_packet_gate_reason": "packet_validation_failed",
        "quantitative_packet": packet,
    }
    data.update(overrides)
    return data


def _analyst_author_state():
    evidence = [
        {
            "source_id": 1,
            "title": "Official metric",
            "url": "https://example.com/a",
            "text": "A price is $10.",
        }
    ]
    return build_analyst_author_handoff_state(
        run_id="run-eco",
        analyst_skipped=False,
        analyst_skip_reason=None,
        post_retrieval_fast_path_used=False,
        pre_analyst_gate_signals=[],
        analyst_skipped_after_economist=False,
        analyst_after_economist_skip_reason="economist_shadow_mode_no_framework",
        economist_output_used_as_analysis=False,
        analyst_evidence=evidence,
        analyst_context_prefix="[Source 1] Official metric",
        corpus_weak=False,
        failure_card_payload={"show": False, "reason": ""},
        author_notes="",
        author_evidence=evidence,
        selected_evidence=evidence,
        final_evidence=evidence,
        ordered_sources=["- [1] Official metric"],
        unique_source_urls={"https://example.com/a": 1},
        author_evidence_block="[Source 1] Official metric",
        source_telemetry_ref={"source_ids": [1]},
        author_prompt="Today is 2026-05-31. Write.",
        complexity="medium",
        author_system_prompt_key="author",
        author_effort="medium",
        includes_analysis=True,
        includes_recency_notes=False,
        includes_author_notes=False,
        image_context_active=False,
        answer_contract_ref={"answer_contract": "runtime"},
        final_evidence_ref={"final_evidence_count": 1},
    )


def _citation_state(aa_state):
    evidence = [
        {
            "source_id": 1,
            "title": "Official metric",
            "url": "https://example.com/a",
            "text": "A price is $10.",
        }
    ]
    return build_citation_source_handoff_state(
        run_id="run-eco",
        final_evidence=evidence,
        selected_evidence=evidence,
        author_evidence=evidence,
        unique_source_urls={"https://example.com/a": 1},
        ordered_sources=["- [1] Official metric"],
        evidence_block="[Source 1] Official metric",
        cached_prefix="[Source 1] Official metric",
        author_evidence_block="[Source 1] Official metric",
        final_answer_source_telemetry={"final_answer_source_ids_used": ["1"]},
        final_citation_observation_refs=["1"],
        final_evidence_bundle_ref={"final_evidence_count": 1},
        ledger_ref={"final_evidence_snapshot_recorded": True},
        answer_contract_ref={"answer_contract": "runtime"},
        analyst_author_handoff_state=aa_state,
        source_telemetry_ref={"source_ids": [1]},
    )


def _state(**overrides):
    aa_state = overrides.pop("analyst_author_handoff_state", _analyst_author_state())
    citation_state = overrides.pop("citation_source_handoff_state", _citation_state(aa_state))
    params = {
        "run_id": "run-eco",
        "need_economist": True,
        "economist_ran": True,
        "economist_preflight_allowed": True,
        "economist_preflight_block_reason": None,
        "economist_preflight_missing_entities": [],
        "economist_safety_telemetry": _safety(),
        "economist_pre_analyst_skip_candidate_telemetry": {
            "economist_pre_analyst_skip_candidate_shadow": False
        },
        "analyst_quant_packet_handoff_telemetry": {
            "analyst_quant_packet_injected": True,
            "analyst_quant_packet_reviewed_by_model": True,
            "analyst_model_called": True,
        },
        "author_quant_source_telemetry": {
            "author_quant_content_source": "analyst_reviewed",
            "author_received_raw_quant_packet": False,
            "author_received_economist_framework": False,
            "author_received_analyst_packet_marker": False,
        },
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": "economist_shadow_mode_no_framework",
        "economist_output_used_as_analysis": False,
        "estimate_from_priors_requested": False,
        "estimate_from_priors_blocked_by_pre_analyst_gate": False,
        "answer_contract_ref": {"answer_contract": "runtime"},
        "analyst_author_handoff_state": aa_state,
        "citation_source_handoff_state": citation_state,
    }
    params.update(overrides)
    return build_economist_handoff_state(**params)


def test_economist_run_block_unavailable_parity_and_skip_reason_are_mechanical():
    blocked = _state(
        economist_ran=False,
        economist_preflight_allowed=False,
        economist_preflight_block_reason="missing_numerical_anchor_for_entities",
        economist_preflight_missing_entities=["A", "B"],
        economist_safety_telemetry=_safety(quantitative_packet_present=False),
    )
    unavailable = _state(
        need_economist=True,
        economist_ran=False,
        economist_preflight_allowed=None,
        economist_preflight_block_reason=None,
    )
    handoff = execute_economist_handoff(blocked)

    assert handoff.economist_should_run is True
    assert handoff.economist_ran is False
    assert handoff.economist_blocked is True
    assert handoff.economist_preflight_missing_entities == ("A", "B")
    assert blocked.to_controller_state()["admission"]["economist_blocked"] is True
    assert unavailable.to_controller_state()["admission"]["economist_unavailable"] is True


def test_preflight_posture_parity_and_trace_visibility_are_preserved():
    state = _state(
        economist_preflight_allowed=False,
        economist_preflight_block_reason="missing_numerical_anchor_for_entities",
        economist_preflight_missing_entities=["A"],
    )
    trace = state.to_controller_state()["preflight"]

    assert state.schema_version == ECONOMIST_HANDOFF_SCHEMA_VERSION
    assert trace["controller_owned"] is True
    assert trace["evaluated"] is True
    assert trace["allowed"] is False
    assert trace["block_reason"] == "missing_numerical_anchor_for_entities"
    assert trace["missing_entities"] == ["A"]


def test_source_bound_packet_identity_and_unsupported_model_derived_posture_are_explicit():
    state = _state()
    trace = state.to_controller_state()
    packet = trace["source_bound_packet"]["packet_identity"]
    unsupported = trace["unsupported_values"]

    assert packet["present"] is True
    assert packet["schema_version"] == "quantitative_packet_v1"
    assert packet["source_ids_used"] == [1, 2]
    assert packet["source_bound_value_count"] == 1
    assert packet["unsupported_values_count"] == 1
    assert packet["raw_packet_included"] is False
    assert unsupported["missing_target_metrics"] == ["B price"]
    assert unsupported["model_derived_value_flags"]["quantitative_packet_requires_analyst"] is True
    assert unsupported["estimate_from_priors_requested"] is False


def test_economist_output_does_not_bypass_analyst_or_author_contracts():
    state = _state()
    trace = state.to_controller_state()

    assert trace["analyst_exposure"]["economist_output_used_as_analysis"] is False
    assert trace["analyst_exposure"]["analyst_skipped_after_economist"] is False
    assert trace["analyst_exposure"]["does_not_bypass_analyst_author_contract"] is True
    assert trace["analyst_exposure"]["analyst_author_handoff_ref"]["schema_version"]
    assert trace["author_exposure"]["author_quant_content_source"] == "analyst_reviewed"
    assert trace["author_exposure"]["author_received_raw_quant_packet"] is False
    assert trace["author_exposure"]["author_received_economist_framework"] is False
    assert trace["author_exposure"]["does_not_bypass_author_contract"] is True
    assert trace["citation_source_handoff_ref"]["schema_version"]


def test_no_model_generated_code_execution_boundary_is_controller_visible():
    state = _state(
        economist_safety_telemetry=_safety(
            economist_code_execution_requested=True,
            economist_code_execution_blocked=True,
            economist_skip_reason="model_generated_code_execution_disabled",
        )
    )
    safety = state.to_controller_state()["safety"]

    assert safety["economist_code_execution_requested"] is True
    assert safety["economist_code_execution_blocked"] is True
    assert safety["no_model_generated_code_execution"] is True
    assert safety["subprocess_eval_exec_shell_enabled"] is False
    assert state.to_controller_state()["admission"]["economist_blocked"] is True


def test_trace_is_additive_and_behavior_change_flags_remain_false():
    trace = _state().to_trace_fragment()[ECONOMIST_HANDOFF_TRACE_KEY]

    assert trace["controller_owned"] is True
    assert trace["trace_visibility"]["additive_only"] is True
    assert trace["trace_visibility"]["legacy_trace_fields_preserved"] is True
    assert trace["did_change_economist_behavior"] is False
    assert trace["did_change_quantitative_policy"] is False
    assert trace["did_change_code_execution_behavior"] is False
    assert trace["did_change_analyst_behavior"] is False
    assert trace["did_change_author_behavior"] is False
    assert trace["did_change_final_answer_behavior"] is False
    assert trace["did_change_citation_behavior"] is False
    assert trace["did_change_provider_search_query_behavior"] is False
    assert trace["did_change_db_session_run_outcome_shape"] is False


def test_static_protected_import_guard_for_contract():
    assert_controller_contract_imports_closed(
        CONTRACT,
        allowed_import_roots={"copy", "dataclasses", "hashlib", "typing"},
        forbidden_modules={
            "core.pipeline",
            "core.scrutineer",
            "core.followup",
            "core.outcome_persistence_packaging",
            "core.persistence_side_effects",
            "subprocess",
        },
    )


def test_static_no_code_execution_affordance_added_to_contract_or_orchestrator():
    contract_text = CONTRACT.read_text()
    added_orchestrator_text = "\n".join(
        line for line in PIPELINE.read_text().splitlines() if "economist_handoff" in line
    )

    contract_tree = ast.parse(contract_text)
    dangerous_calls = {"eval", "exec", "compile", "open"}
    contract_calls = {
        node.func.id
        for node in ast.walk(contract_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not (contract_calls & dangerous_calls)
    for token in ("shell=True", "TemporaryDirectory", "mkstemp"):
        assert token not in contract_text
        assert token not in added_orchestrator_text

    pipeline_tree = ast.parse(PIPELINE_CORE.read_text())
    run_code = next(
        node
        for node in ast.walk(pipeline_tree)
        if isinstance(node, ast.FunctionDef) and node.name == "run_economist_code"
    )
    calls = [node.func.id for node in ast.walk(run_code) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    assert "eval" not in calls
    assert "exec" not in calls


def test_orchestrator_authority_guard_builds_and_consumes_contract_at_handoff_seam():
    text = PIPELINE.read_text()

    assert "build_economist_handoff_state" in text
    assert "execute_economist_handoff" in text
    assert "economist_handoff_trace_fragment" in text
    assert "**economist_handoff_trace_fragment" in text
    assert text.index("post_economist_gate = _post_economist_analyst_gate") < text.index(
        "economist_handoff_state = build_economist_handoff_state"
    )
    assert text.index("economist_handoff = execute_economist_handoff") < text.index(
        "pre_analyst_gate_contract = build_analyst_gate_descriptor"
    )


def test_upstream_contract_integration_refs_are_sanitized_without_behavior_changes():
    state = _state(answer_contract_ref={"answer_contract": "runtime", "quant": "source_bound"})
    trace = state.to_controller_state()

    assert trace["answer_contract_ref"]["quant"] == "source_bound"
    assert trace["analyst_author_handoff_ref"]["schema_version"]
    assert trace["citation_source_handoff_ref"]["schema_version"]
    assert trace["output"]["raw_economist_output_included"] is False
    assert trace["source_bound_packet"]["raw_packet_included"] is False


def test_protected_surfaces_prompt_and_live_product_paths_are_unopened():
    contract_text = CONTRACT.read_text()
    prompt_text = PROMPTS.read_text()

    assert "economist" in prompt_text
    assert "default_system" not in contract_text
    assert "ask_model" not in contract_text
    assert "OPENAI_API_KEY" not in contract_text
    imports = {
        node.module
        for node in ast.walk(ast.parse(contract_text))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any("provider" in name for name in imports)
    assert not any("sqlite" in name.casefold() for name in imports)
    assert "RunOutcome" not in contract_text
