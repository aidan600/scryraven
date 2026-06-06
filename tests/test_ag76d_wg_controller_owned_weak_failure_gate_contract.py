from __future__ import annotations

import ast
from pathlib import Path

from core.answer_outcome import classify_answer_outcome
from core.corpus_state import CorpusState, classify_corpus_state, is_weak_corpus_state
from core.failure_card import failure_card_reason, failure_card_should_show
from core.retrieval_loop_contract import (
    RETRIEVAL_LOOP_TRACE_KEY,
    build_retrieval_execution_envelope,
    build_retrieval_loop_state,
    build_retrieval_pass_descriptor,
)
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.useful_content import evaluate_useful_content
from core.weak_failure_gate_contract import (
    WEAK_FAILURE_GATE_SCHEMA_VERSION,
    WEAK_FAILURE_GATE_TRACE_KEY,
    build_analyst_gate_descriptor,
    build_weak_failure_gate_state,
    execute_weak_failure_gate_handoff,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
SESSION_OUTPUT_PROJECTION = ROOT / "core" / "session_output_projection.py"
CONTRACT = ROOT / "core" / "weak_failure_gate_contract.py"


def _analyst_gate():
    return build_analyst_gate_descriptor(
        pre_analyst_gate={
            "analyst_skipped": True,
            "analyst_skip_reason": "corpus_off_topic",
            "post_retrieval_fast_path_used": True,
            "pre_analyst_gate_signals": ["no_domain_relevant_source"],
        },
        post_economist_gate={
            "analyst_skipped_after_economist": False,
            "analyst_after_economist_skip_reason": "corpus_off_topic",
            "economist_output_used_as_analysis": False,
        },
    )


def _failure_payload(*, corpus_state: str, useful_content: bool = True):
    show = failure_card_should_show(
        corpus_state=corpus_state,
        retrieval_retry_used=False,
        empty_entity=False,
        scrutineer_high_count=0,
        useful_content=useful_content,
    )
    reason = failure_card_reason(
        corpus_state=corpus_state,
        retrieval_retry_used=False,
        empty_entity=False,
        scrutineer_high_count=0,
        useful_content=useful_content,
        chunks_with_entity=0,
        total_chunks_embedded=12,
    )
    return {
        "show": show,
        "reason": reason,
        "corpus_state": corpus_state,
        "empty_entity": False,
        "first_pass_providers": ["tavily"],
        "retrieval_retry_used": False,
        "scrutineer_high_count": 0,
        "useful_content": useful_content,
    }


def _contract(*, corpus_state: str = CorpusState.OFF_TOPIC.value):
    report = "No reliable retrieved evidence supports the requested claim."
    useful_content, useful_reason = evaluate_useful_content(report)
    response_displayable, evidence_sufficient, answer_class = classify_answer_outcome(
        report,
        corpus_state=corpus_state,
        corpus_weak=is_weak_corpus_state(corpus_state),
        useful_content=useful_content,
        synth_was_insufficient=True,
        empty_entity=False,
    )
    return build_weak_failure_gate_state(
        corpus_state=corpus_state,
        corpus_weak=is_weak_corpus_state(corpus_state),
        corpus_state_forced=False,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason="checkpoint_action_not_approved",
        weak_corpus_recovery_queries=["Acme official source"],
        weak_corpus_recovery_decision="run_weak_corpus_recovery",
        weak_corpus_recovery_reason="weak_corpus_first_pass",
        weak_corpus_recovery_blockers=[],
        useful_content=useful_content,
        useful_content_reason=useful_reason,
        response_displayable=response_displayable,
        evidence_sufficient=evidence_sufficient,
        answer_class=answer_class,
        failure_card_payload=_failure_payload(corpus_state=corpus_state, useful_content=useful_content),
        analyst_gate=_analyst_gate(),
        run_id="run-wg",
        iteration=1,
        answer_outcome_ref={
            "response_displayable": response_displayable,
            "evidence_sufficient": evidence_sufficient,
            "answer_class": answer_class,
        },
    )


def test_contract_ownership_descriptor_and_controller_visibility():
    state = _contract()
    trace = state.to_trace_fragment()[WEAK_FAILURE_GATE_TRACE_KEY]

    assert state.schema_version == WEAK_FAILURE_GATE_SCHEMA_VERSION
    assert trace["controller_owned"] is True
    assert trace["failure_card"]["controller_owned"] is True
    assert trace["analyst_gate"]["controller_owned"] is True
    assert trace["trace_visibility"]["owned_by"] == "Controller"
    assert trace["mechanical_executor_boundary"] is True


def test_weak_corpus_parity_fields_are_copied_unchanged():
    forced = classify_corpus_state(
        empty_entity=False,
        utilization_rate=0.05,
        utilization_threshold=0.25,
        estimate_from_priors=True,
    ).value
    state = build_weak_failure_gate_state(
        corpus_state=forced,
        corpus_weak=is_weak_corpus_state(forced),
        corpus_state_forced=True,
        weak_corpus_recovery_considered=True,
        weak_corpus_recovery_used=True,
        weak_corpus_recovery_skip_reason=None,
        weak_corpus_recovery_queries=["q1", "q2"],
        weak_corpus_recovery_decision="run_weak_corpus_recovery",
        weak_corpus_recovery_reason="weak_corpus_first_pass",
        weak_corpus_recovery_blockers=["none"],
        useful_content=True,
        useful_content_reason="word_count=130",
        response_displayable=True,
        evidence_sufficient=False,
        answer_class="partial_answer",
        failure_card_payload=_failure_payload(corpus_state=forced),
        analyst_gate=_analyst_gate(),
    )
    trace = state.to_controller_state()

    assert trace["corpus_state"] == forced
    assert trace["corpus_weak"] is True
    assert trace["corpus_state_forced"] is True
    assert trace["weak_corpus_recovery_considered"] is True
    assert trace["weak_corpus_recovery_used"] is True
    assert trace["weak_corpus_recovery_skip_reason"] is None
    assert trace["weak_corpus_recovery_queries"] == ["q1", "q2"]
    assert trace["weak_corpus_recovery_decision"] == "run_weak_corpus_recovery"
    assert trace["weak_corpus_recovery_reason"] == "weak_corpus_first_pass"
    assert trace["weak_corpus_recovery_blockers"] == ["none"]


def test_off_topic_no_good_evidence_displayability_parity():
    state = _contract(corpus_state=CorpusState.OFF_TOPIC.value)
    trace = state.to_controller_state()

    assert trace["corpus_state"] == CorpusState.OFF_TOPIC.value
    assert trace["off_topic"] is True
    assert trace["no_good_evidence"] is True
    assert trace["response_displayable"] is True
    assert trace["evidence_sufficient"] is False
    assert trace["answer_class"] == "off_topic_retrieval"


def test_failure_card_parity_payload_shape_reason_and_show():
    state = _contract(corpus_state=CorpusState.OFF_TOPIC.value)
    trace = state.to_controller_state()["failure_card"]
    payload = state.failure_card.payload

    assert trace["should_show"] == payload["show"]
    assert trace["reason"] == payload["reason"]
    assert trace["payload"] == payload
    assert sorted(trace["payload_summary"]["keys"]) == sorted(payload)


def test_useful_content_answer_outcome_parity():
    report = (
        "### Finding\nRetrieved source [1](https://example.com) supports a partial "
        "answer with 42% directional evidence and explicit limitations. " * 5
    )
    useful_content, useful_reason = evaluate_useful_content(report)
    outcome = classify_answer_outcome(
        report,
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        useful_content=useful_content,
        synth_was_insufficient=False,
        empty_entity=False,
    )
    state = build_weak_failure_gate_state(
        corpus_state=CorpusState.HEALTHY.value,
        corpus_weak=False,
        corpus_state_forced=False,
        weak_corpus_recovery_considered=False,
        weak_corpus_recovery_used=False,
        weak_corpus_recovery_skip_reason="not_weak_corpus",
        weak_corpus_recovery_queries=[],
        weak_corpus_recovery_decision="no_action",
        weak_corpus_recovery_reason="not_weak_corpus",
        weak_corpus_recovery_blockers=[],
        useful_content=useful_content,
        useful_content_reason=useful_reason,
        response_displayable=outcome[0],
        evidence_sufficient=outcome[1],
        answer_class=outcome[2],
        failure_card_payload=_failure_payload(corpus_state=CorpusState.HEALTHY.value),
        analyst_gate=build_analyst_gate_descriptor(
            pre_analyst_gate={
                "analyst_skipped": False,
                "analyst_skip_reason": None,
                "post_retrieval_fast_path_used": False,
                "pre_analyst_gate_signals": [],
            }
        ),
    )
    trace = state.to_controller_state()

    assert trace["useful_content"] == useful_content
    assert trace["useful_content_reason"] == useful_reason
    assert (trace["response_displayable"], trace["evidence_sufficient"], trace["answer_class"]) == outcome


def test_mechanical_executor_handoff_returns_legacy_outputs_without_deciding():
    state = _contract()
    handoff = execute_weak_failure_gate_handoff(state)

    assert handoff.mechanical_handoff_only is True
    assert handoff.failure_card_payload == state.failure_card.payload
    assert handoff.answer_class == state.answer_class
    assert handoff.analyst_skipped == state.analyst_gate.analyst_skipped
    assert handoff.pre_analyst_gate_signals == state.analyst_gate.pre_analyst_gate_signals


def test_orchestrator_consumes_contract_and_static_guard_blocks_silent_gate_decision():
    source = PIPELINE.read_text(encoding="utf-8") + SESSION_OUTPUT_PROJECTION.read_text(encoding="utf-8")

    assert "build_weak_failure_gate_state(" in source
    assert "execute_weak_failure_gate_handoff(" in source
    assert "weak_failure_gate_handoff.failure_card_payload" in source
    assert "pre_analyst_gate_contract = build_analyst_gate_descriptor" in source
    assert "analyst_skipped = bool(pre_analyst_gate_handoff" in source
    assert "weak_failure_gate_trace_fragment" in source

    final_handoff_idx = source.index("weak_failure_gate_handoff = execute_weak_failure_gate_handoff")
    final_trace_idx = source.index("execution_trace = build_execution_trace_projection")
    final_region = source[final_handoff_idx:final_trace_idx]
    forbidden_redecision_fragments = (
        "failure_card_should_show(",
        "failure_card_reason(",
        "classify_answer_outcome(",
        "evaluate_useful_content(",
    )
    for fragment in forbidden_redecision_fragments:
        assert fragment not in final_region


def test_retrieval_loop_state_can_be_referenced_without_changing_it():
    router = build_router_query_preparation_state(
        router_text='{"intent":"general","report_type":"general_research","query_type":"general","core_topic":"Acme","entities":["Acme"],"primary_entity":"Acme"}',
        query="Acme query",
    )
    descriptor = build_retrieval_pass_descriptor(
        iteration=1,
        query_source="researcher",
        current_queries=["Acme query"],
        provider_list=["tavily"],
        search_depth="basic",
        results_per_query=5,
        top_chunks=10,
        max_iterations=2,
        intent="general",
        complexity="low",
    )
    loop = build_retrieval_loop_state(
        router_query_preparation_state=router,
        pass_descriptor=descriptor,
        execution_envelope=build_retrieval_execution_envelope(descriptor),
        retrieval_budget_facts={"iteration": 1},
    )
    before = loop.to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY]
    base = _contract()
    state = build_weak_failure_gate_state(
        corpus_state=base.corpus_state,
        corpus_weak=base.corpus_weak,
        corpus_state_forced=base.corpus_state_forced,
        weak_corpus_recovery_considered=base.weak_corpus_recovery_considered,
        weak_corpus_recovery_used=base.weak_corpus_recovery_used,
        weak_corpus_recovery_skip_reason=base.weak_corpus_recovery_skip_reason,
        weak_corpus_recovery_queries=base.weak_corpus_recovery_queries,
        weak_corpus_recovery_decision=base.weak_corpus_recovery_decision,
        weak_corpus_recovery_reason=base.weak_corpus_recovery_reason,
        weak_corpus_recovery_blockers=base.weak_corpus_recovery_blockers,
        useful_content=base.useful_content,
        useful_content_reason=base.useful_content_reason,
        response_displayable=base.response_displayable,
        evidence_sufficient=base.evidence_sufficient,
        answer_class=base.answer_class,
        failure_card_payload=base.failure_card.payload,
        analyst_gate=base.analyst_gate,
        retrieval_loop_state=loop,
    )

    assert state.to_controller_state()["retrieval_loop_ref"] == before
    assert loop.to_trace_fragment()[RETRIEVAL_LOOP_TRACE_KEY] == before


def test_trace_compatibility_existing_fields_and_additive_contract():
    state = _contract()
    legacy_trace = {
        "corpus_state": state.corpus_state,
        "corpus_weak": state.corpus_weak,
        "useful_content": state.useful_content,
        "response_displayable": state.response_displayable,
        "evidence_sufficient": state.evidence_sufficient,
        "answer_class": state.answer_class,
        "failure_card": state.failure_card.payload,
        **state.to_trace_fragment(),
    }

    assert legacy_trace["corpus_state"] == state.corpus_state
    assert legacy_trace["failure_card"] == state.failure_card.payload
    assert WEAK_FAILURE_GATE_TRACE_KEY in legacy_trace
    assert legacy_trace[WEAK_FAILURE_GATE_TRACE_KEY]["trace_visibility"]["additive_only"] is True


def test_analyst_author_final_answer_citation_non_change_static_guard():
    diff = PIPELINE.read_text(encoding="utf-8")
    prompt_helper = (ROOT / "core" / "runtime_prompt_assembly.py").read_text(encoding="utf-8")
    assert "UNSUPPORTED_RETRIEVAL_DIRECTIVE" in prompt_helper
    assert "NOTE FOR AUTHOR - UNSUPPORTED RETRIEVAL FAST PATH" in prompt_helper
    assert "build_unsupported_retrieval_prompt_fragments" in diff
    assert "author_system_prompt_key" in diff
    assert "final_answer_source_telemetry" in diff
    assert "ask_model(" not in prompt_helper

    contract_source = CONTRACT.read_text(encoding="utf-8")
    assert "did_change_analyst_behavior\": False" in contract_source
    assert "did_change_author_behavior\": False" in contract_source
    assert "did_change_citation_behavior\": False" in contract_source
    assert "did_change_final_answer_behavior\": False" in contract_source


def test_protected_surface_guard_no_live_or_closed_surface_imports_or_calls():
    tree = ast.parse(CONTRACT.read_text(encoding="utf-8"))
    forbidden_modules = (
        "core.prompts",
        "core.pipeline",
        "core.db",
        "core.run_config",
        "core.citations",
        "core.citation",
        "core.follow_up",
        "core.llm_cache",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module not in forbidden_modules
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_modules
        if isinstance(node, ast.Call):
            func_name = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
            assert func_name not in {
                "ask_model",
                "process_search_queries",
                "author_agent",
                "analyst_agent",
                "kb_review_agent",
                "execute_persistence_side_effects",
            }

    source = CONTRACT.read_text(encoding="utf-8")
    for forbidden in ("os.getenv", "requests.", "sqlite3", "RunOutcome", ".env"):
        assert forbidden not in source
