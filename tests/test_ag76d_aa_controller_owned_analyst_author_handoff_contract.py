from __future__ import annotations

from pathlib import Path

from core.analyst_author_handoff_contract import (
    ANALYST_AUTHOR_HANDOFF_SCHEMA_VERSION,
    ANALYST_AUTHOR_HANDOFF_TRACE_KEY,
    build_analyst_author_handoff_state,
    execute_analyst_author_handoff,
)
from core.retrieval_loop_contract import (
    build_retrieval_execution_envelope,
    build_retrieval_loop_state,
    build_retrieval_pass_descriptor,
)
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.weak_failure_gate_contract import (
    build_analyst_gate_descriptor,
    build_weak_failure_gate_state,
)
from tests.static_import_guard_utils import assert_controller_contract_imports_closed

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
SESSION_OUTPUT_PROJECTION = ROOT / "core" / "session_output_projection.py"
CONTRACT = ROOT / "core" / "analyst_author_handoff_contract.py"


def _evidence() -> list[dict[str, object]]:
    return [
        {
            "source_id": 1,
            "title": "Official result",
            "url": "https://example.com/official",
            "text": "official evidence text",
            "score": 0.99,
            "source_tier": "official",
            "source_class": "official_current_rules",
        },
        {
            "source_id": 2,
            "title": "Secondary result",
            "url": "https://example.com/secondary",
            "text": "secondary evidence text",
            "score": 0.77,
            "source_tier": "secondary",
            "source_class": "reputable_secondary",
        },
    ]


def _router_state():
    return build_router_query_preparation_state(
        query="What changed in Acme pricing?",
        router_text=(
            '{"intent":"research","report_type":"general_research",'
            '"query_type":"news","image_mode":"contextual",'
            '"core_topic":"Acme pricing","is_academic":false,'
            '"primary_entity":"Acme","entities":["Acme"]}'
        ),
    )


def _retrieval_loop_state():
    descriptor = build_retrieval_pass_descriptor(
        iteration=1,
        query_source="router_query_preparation",
        current_queries=["Acme pricing official"],
        provider_list=["tavily"],
        search_depth="basic",
        results_per_query=5,
        top_chunks=10,
        max_iterations=2,
        intent="research",
        complexity="medium",
    )
    return build_retrieval_loop_state(
        router_query_preparation_state=_router_state(),
        pass_descriptor=descriptor,
        execution_envelope=build_retrieval_execution_envelope(descriptor),
        retrieval_stop_decision={"decision": "continue", "controller_owned": True},
        run_id="run-aa",
    )


def _weak_state():
    return build_weak_failure_gate_state(
        corpus_state="HEALTHY",
        corpus_weak=False,
        corpus_state_forced=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason="not_weak_corpus",
        weak_corpus_recovery_queries=[],
        weak_corpus_recovery_decision="no_action",
        weak_corpus_recovery_reason="not_weak_corpus",
        weak_corpus_recovery_blockers=[],
        useful_content=True,
        useful_content_reason="word_count=50",
        response_displayable=True,
        evidence_sufficient=True,
        answer_class="supported_answer",
        failure_card_payload={"show": False, "reason": ""},
        analyst_gate=build_analyst_gate_descriptor(
            pre_analyst_gate={
                "analyst_skipped": False,
                "analyst_skip_reason": None,
                "post_retrieval_fast_path_used": False,
                "pre_analyst_gate_signals": [],
            }
        ),
    )


def _state(**overrides):
    evidence = _evidence()
    params = {
        "run_id": "run-aa",
        "analyst_skipped": False,
        "analyst_skip_reason": None,
        "post_retrieval_fast_path_used": False,
        "pre_analyst_gate_signals": [],
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": "disabled_shadow_only",
        "economist_output_used_as_analysis": False,
        "analyst_evidence": evidence,
        "analyst_context_prefix": "<evidence_block>stable</evidence_block>",
        "linkup_block_included": False,
        "quantitative_packet_injected": False,
        "missing_target_metric_directive_emitted": False,
        "corpus_weak": False,
        "failure_card_payload": {"show": False, "reason": ""},
        "author_notes": "",
        "author_evidence": evidence[:1],
        "selected_evidence": evidence,
        "final_evidence": evidence,
        "ordered_sources": ["- [1] [Official result](https://example.com/official)"],
        "unique_source_urls": {"https://example.com/official": 1},
        "author_evidence_block": "[Source 1] Official result",
        "source_telemetry_ref": {"source_ids": [1, 2], "final_evidence_count": 2},
        "author_prompt": "Today is 2026-05-31. Write the final markdown report.",
        "complexity": "medium",
        "author_system_prompt_key": "author",
        "author_effort": "medium",
        "includes_analysis": True,
        "includes_recency_notes": False,
        "includes_author_notes": False,
        "image_context_active": False,
        "pre_analyst_gate_ref": {"analyst_skipped": False},
        "weak_failure_gate_state": _weak_state(),
        "retrieval_loop_state": _retrieval_loop_state(),
        "router_query_preparation_state": _router_state(),
        "answer_contract_ref": {"answer_contract": "runtime"},
        "final_evidence_ref": {"final_evidence_count": 2},
    }
    params.update(overrides)
    return build_analyst_author_handoff_state(**params)


def test_contract_ownership_schema_and_trace_visibility():
    state = _state()
    trace = state.to_trace_fragment()[ANALYST_AUTHOR_HANDOFF_TRACE_KEY]

    assert state.schema_version == ANALYST_AUTHOR_HANDOFF_SCHEMA_VERSION
    assert trace["controller_owned"] is True
    assert trace["trace_visibility"]["owned_by"] == "Controller"
    assert trace["trace_visibility"]["additive_only"] is True
    assert trace["mechanical_executor_boundary"] is True


def test_analyst_run_skip_parity_and_skip_reason_are_mechanical():
    skipped = _state(
        analyst_skipped=True,
        analyst_skip_reason="corpus_weak",
        post_retrieval_fast_path_used=True,
        pre_analyst_gate_signals=["mostly_unknown_sources"],
        corpus_weak=True,
        failure_card_payload={"show": True, "reason": "corpus_weak"},
    )
    handoff = execute_analyst_author_handoff(skipped)
    trace = skipped.to_controller_state()["analyst_admission"]

    assert handoff.analyst_should_run is False
    assert handoff.analyst_skipped is True
    assert handoff.analyst_skip_reason == "corpus_weak"
    assert handoff.post_retrieval_fast_path_used is True
    assert handoff.pre_analyst_gate_signals == ("mostly_unknown_sources",)
    assert trace["analyst_should_run"] is False
    assert trace["legacy_runtime_branch"] == "pre_analyst_gate_contract"


def test_analyst_evidence_context_package_identity_order_and_metadata_are_preserved():
    state = _state(quantitative_packet_injected=True)
    trace = state.to_controller_state()["analyst_evidence_context"]

    assert trace["evidence_count"] == 2
    assert [item["source_id"] for item in trace["evidence_identity"]] == [1, 2]
    assert [item["url"] for item in trace["evidence_identity"]] == [
        "https://example.com/official",
        "https://example.com/secondary",
    ]
    assert trace["context_prefix_hash"]
    assert trace["context_prefix_length"] == len("<evidence_block>stable</evidence_block>")
    assert trace["quantitative_packet_injected"] is True
    assert trace["prompt_text_included"] is False


def test_unsupported_weak_and_failure_card_directive_state_is_preserved():
    notes = "NOTE FOR AUTHOR - UNSUPPORTED RETRIEVAL FAST PATH"
    state = _state(
        analyst_skipped=True,
        analyst_skip_reason="unsupported_off_domain_retrieval",
        corpus_weak=True,
        failure_card_payload={"show": True, "reason": "off_topic"},
        author_notes=notes,
    )
    trace = state.to_controller_state()["unsupported_directives"]

    assert trace["unsupported_retrieval_directive_active"] is True
    assert trace["weak_evidence_directive_active"] is True
    assert trace["failure_card_directive_active"] is True
    assert trace["analyst_skip_reason"] == "unsupported_off_domain_retrieval"
    assert trace["failure_card_reason"] == "off_topic"
    assert trace["author_notes_length"] == len(notes)
    assert trace["directive_text_included"] is False


def test_author_evidence_handoff_selected_final_and_source_telemetry_identity():
    state = _state()
    trace = state.to_controller_state()["author_evidence_handoff"]

    assert trace["author_evidence_count"] == 1
    assert trace["selected_evidence_count"] == 2
    assert trace["final_evidence_count"] == 2
    assert trace["author_evidence_identity"][0]["source_id"] == 1
    assert [item["source_id"] for item in trace["final_evidence_identity"]] == [1, 2]
    assert trace["ordered_source_count"] == 1
    assert trace["unique_source_url_count"] == 1
    assert trace["source_telemetry_ref"] == {"source_ids": [1, 2], "final_evidence_count": 2}
    assert trace["citation_behavior_included"] is False


def test_author_prompt_input_metadata_parity_without_prompt_text():
    prompt = "Today is 2026-05-31. Analysis: stable. Precision Evidence: stable."
    state = _state(
        author_prompt=prompt,
        author_system_prompt_key="author_corpus_weak",
        author_effort="low",
        includes_analysis=False,
        includes_recency_notes=True,
        includes_author_notes=True,
        image_context_active=True,
    )
    trace = state.to_controller_state()["author_prompt_input"]
    handoff = execute_analyst_author_handoff(state)

    assert trace["prompt_length"] == len(prompt)
    assert trace["prompt_hash"]
    assert trace["author_system_prompt_key"] == "author_corpus_weak"
    assert trace["author_effort"] == "low"
    assert trace["includes_analysis"] is False
    assert trace["includes_recency_notes"] is True
    assert trace["includes_author_notes"] is True
    assert trace["image_context_active"] is True
    assert trace["prompt_text_included"] is False
    assert handoff.author_system_prompt_key == "author_corpus_weak"
    assert handoff.author_effort == "low"


def test_trace_compatibility_flags_are_additive_and_legacy_fields_remain_in_orchestrator():
    pipeline = PIPELINE.read_text() + SESSION_OUTPUT_PROJECTION.read_text()
    trace = _state().to_controller_state()

    for legacy_field in (
        '"analyst_skipped"',
        '"analyst_skip_reason"',
        '"author_system_prompt_key"',
        '"failure_card"',
    ):
        assert legacy_field in pipeline
    assert trace["did_change_analyst_behavior"] is False
    assert trace["did_change_author_behavior"] is False
    assert trace["did_change_final_answer_behavior"] is False
    assert trace["did_change_citation_behavior"] is False
    assert trace["did_change_prompt_text"] is False


def test_static_protected_import_guard_for_contract_module():
    assert_controller_contract_imports_closed(
        CONTRACT,
        allowed_import_roots={"copy", "dataclasses", "hashlib", "typing"},
        forbidden_module_fragments=(
            "ask_model",
            "provider",
            "search",
            "prompts",
            "citation",
            "final_answer",
            "economist",
            "scrutineer",
            "follow_up",
            "session",
            "run_outcome",
            "cache",
            "pipeline_orchestrator",
        ),
    )


def test_orchestrator_authority_guard_wires_contract_and_keeps_prompt_strings_local():
    pipeline = PIPELINE.read_text() + SESSION_OUTPUT_PROJECTION.read_text()
    prompt_helper = (ROOT / "core" / "runtime_prompt_assembly.py").read_text(encoding="utf-8")
    contract = CONTRACT.read_text()

    assert "build_analyst_author_handoff_state" in pipeline
    assert "execute_analyst_author_handoff" in pipeline
    assert "analyst_author_handoff_trace_fragment" in pipeline
    assert "build_author_prompt_from_scope" in pipeline
    assert "Write the final markdown report" in prompt_helper
    assert "UNSUPPORTED_RETRIEVAL_DIRECTIVE" in prompt_helper
    assert "Write the final markdown report" not in contract
    assert "DEFAULT_SYSTEM" not in contract
    assert "ask_model(" not in prompt_helper


def test_protected_surface_guard_keeps_live_and_behavior_modules_out_of_contract():
    text = CONTRACT.read_text()
    forbidden_calls = (
        "ask_model(",
        "process_search_queries(",
        "build_final_source_citation",
        "RunOutcome",
        "sqlite",
        "DEFAULT_SYSTEM",
    )
    assert [call for call in forbidden_calls if call in text] == []


def test_upstream_contract_integration_references_without_behavior_changes():
    state = _state()
    trace = state.to_controller_state()

    assert trace["weak_failure_gate_ref"]["schema_version"]
    assert trace["weak_failure_gate_ref"]["mechanical_executor_boundary"] is True
    assert trace["retrieval_loop_ref"]["controller_owned"] is True
    assert trace["router_query_preparation_ref"]["controller_owned"] is True
    assert trace["answer_contract_ref"] == {"answer_contract": "runtime"}


def test_no_live_product_path_guard_uses_only_pure_contract_builders():
    pipeline = PIPELINE.read_text() + SESSION_OUTPUT_PROJECTION.read_text()
    contract = CONTRACT.read_text()

    assert "SCRYRAVEN_" not in contract
    assert "PROPLEX_" not in contract
    assert ".env" not in contract
    assert "provider=" not in contract
    assert "stream=True" not in contract
    assert "execute_analyst_author_handoff" in pipeline
