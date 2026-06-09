from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import core.post_author_output_projection as helper

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "core" / "post_author_output_projection.py"
ORCHESTRATOR = ROOT / "core" / "pipeline_orchestrator.py"


class _TraceObject:
    state = SimpleNamespace(
        evidence_state_summary=SimpleNamespace(
            scrutineer_requested=True,
            scrutineer_needed=False,
        ),
        active_contract=SimpleNamespace(scrutineer_relevance=SimpleNamespace(value="central")),
    )

    def execution_trace_fragment(self):
        return {"answer_contract_runtime_handoff": {"available": True}}


class _HandoffObject:
    def __init__(self, key):
        self.key = key

    def to_trace_fragment(self):
        return {self.key: {"available": True}}


def _runtime_values() -> dict:
    return {
        "query": "q",
        "core_topic": "topic",
        "primary_entity": "entity",
        "current_date": "2026-06-07",
        "final_top_evidence": [{"url": "https://example.test"}],
        "_source_tier_exec": {"source_tier_counts": {"official": 1}},
        "_source_domain_exec": {"source_domain_counts": {"example.test": 1}},
        "runtime_source_class_recovery_telemetry": {"class": "telemetry"},
        "runtime_active_source_class_recovery_lifecycle": {"life": "cycle"},
        "intent": "research",
        "report_type": "standard",
        "query_type": "general",
        "strategy": "deep",
        "evidence_sufficient": True,
        "corpus_weak": False,
        "weak_corpus_recovery_skip_reason": None,
        "corpus_state": "strong",
        "weak_corpus_recovery_considered": False,
        "weak_corpus_recovery_used": False,
        "retrieval_stop_shadow_telemetry": {"shadow": True},
        "retrieval_stop_active_telemetry": {"active": True},
        "queries_per_iter": {1: ["q"]},
        "evidence_integration_checkpoint_handoff": {"checkpoint": True},
        "evidence_ledger_projection": {},
        "iterations_run": 1,
        "max_iterations": 2,
        "_run_controller_mirror": object(),
        "weak_failure_gate_contract_state": None,
        "provider_diagnostics": [{"provider": "offline"}],
        "final_answer_packet": object(),
        "run_id": "run-1",
        "final_answer_source_telemetry": {"source_ids": ["s1"]},
        "final_source_telemetry_inputs": object(),
        "analyst_skipped": False,
        "analyst_skip_reason": None,
        "post_retrieval_fast_path_used": False,
        "pre_analyst_gate_signals": [],
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": None,
        "economist_output_used_as_analysis": False,
        "analyst_cached_prefix": "analysis",
        "linkup_block": "",
        "analyst_quant_packet_handoff_telemetry": {},
        "missing_target_metric_directive_emitted": False,
        "failure_card_payload": {"show": False},
        "author_notes": "",
        "author_evidence": [],
        "ordered_sources": ["https://example.test"],
        "unique_source_urls": {"https://example.test": True},
        "author_evidence_block": "",
        "author_prompt": "prompt",
        "complexity": "high",
        "author_system_prompt_key": "default",
        "_author_effort": "medium",
        "recency_notes": "",
        "image_context": "",
        "pre_analyst_gate_contract": object(),
        "retrieval_loop_contract_state": object(),
        "router_query_preparation_contract": object(),
        "_efp_author": False,
        "_relevance_low": False,
        "need_economist": False,
        "economist_ran": False,
        "economist_preflight_allowed": True,
        "economist_preflight_block_reason": None,
        "economist_preflight_missing_entities": [],
        "economist_safety_telemetry": {},
        "economist_pre_analyst_skip_candidate_telemetry": {},
        "author_quant_source_telemetry": {},
        "estimate_from_priors_requested": False,
        "estimate_from_priors_blocked_by_pre_analyst_gate": False,
        "synthesis_evaluator_supplemental_search_collector": SimpleNamespace(
            to_trace_fragment=lambda **kwargs: {"synthesis_evaluator_supplemental_search_handoff": kwargs}
        ),
        "synth_was_insufficient": False,
        "results_per_query": 5,
        "delta_urls_supplemental": 0,
        "supplemental_ran": False,
        "scrutineer_ran": True,
        "scrutineer_flags": ["flag"],
        "scrutineer_remediation_queries": ["rq"],
        "scrutineer_remediation_dispatch_authorized": False,
        "scrutineer_remediation_dispatch_posture": "skipped",
        "scrutineer_remediation_provider_role": None,
        "scrutineer_remediation_providers": [],
        "search_depth": "standard",
        "scrutineer_remediation_linkup_depth_override": None,
        "scrutineer_remediation_evidence": [],
        "scrutineer_remediation_resynthesis_triggered": False,
        "analysis": "analysis",
        "scrutineer_pass_flags_directly_to_author": False,
    }


def test_post_author_trace_packaging_projects_expected_fragments(monkeypatch):
    monkeypatch.setattr(
        helper,
        "_build_runtime_conflict_state_projection",
        lambda **kwargs: (object(), {"conflicts_present": False, "conflict_notes": [], "resolving_queries": []}),
    )
    monkeypatch.setattr(helper, "build_runtime_answer_contract_handoff", lambda *args, **kwargs: _TraceObject())
    monkeypatch.setattr(helper, "provider_diagnostics_payload", lambda diagnostics: {"provider_diagnostics": diagnostics})
    monkeypatch.setattr(
        helper,
        "assemble_final_answer_citation_runtime_from_scope",
        lambda scope, analyst_evidence: SimpleNamespace(
            packet="packet",
            analyst_author_handoff_state="analyst-state",
            analyst_author_handoff_trace_fragment={"analyst_author_handoff_contract": {"available": True}},
            citation_source_handoff_state="citation-state",
            citation_source_handoff_trace_fragment={"citation_source_handoff_contract": {"available": True}},
            unique_source_urls={"u": True},
            ordered_sources=["u"],
            final_answer_source_telemetry={"source": "telemetry"},
            packet_trace_fragment={"final_answer_packet": {"available": True}},
        ),
    )
    monkeypatch.setattr(helper, "build_economist_handoff_state", lambda **kwargs: _HandoffObject("economist_handoff_contract"))
    monkeypatch.setattr(helper, "runtime_scrutineer_remediation_trace_fragment", lambda facts: {"scrutineer_remediation_handoff": {"run_id": facts.run_id}})

    packaging = helper.build_post_author_trace_packaging_from_scope(
        _runtime_values(),
        analyst_evidence=[{"id": "a1"}],
        logger=SimpleNamespace(warning=lambda *args, **kwargs: None),
        answer_contract_handoff_builder=lambda *args, **kwargs: _TraceObject(),
    )

    assert packaging.answer_contract_runtime_trace_fragment == {"answer_contract_runtime_handoff": {"available": True}}
    assert packaging.provider_diagnostics_payload == {"provider_diagnostics": [{"provider": "offline"}]}
    assert packaging.weak_failure_gate_trace_fragment == {
        "weak_failure_gate_contract": {"controller_owned": False, "available": False}
    }
    assert packaging.final_answer_packet == "packet"
    assert packaging.ordered_sources == ["u"]
    assert packaging.trace_field_fragments == (
        {"final_answer_packet": {"available": True}},
        {"citation_source_handoff_contract": {"available": True}},
        {"economist_handoff_contract": {"available": True}},
    )


def test_post_author_output_packaging_merges_trace_runtime_values(monkeypatch):
    trace_packaging = helper.PostAuthorTracePackaging(
        answer_contract_runtime_result="contract",
        answer_contract_runtime_trace_fragment={"answer_contract_runtime_handoff": {"available": True}},
        provider_diagnostics_payload={"provider_diagnostics": []},
        weak_failure_gate_trace_fragment={"weak_failure_gate_contract": {"available": False}},
        final_answer_packet="packet",
        analyst_author_handoff_state="analyst-state",
        analyst_author_handoff_trace_fragment={"analyst_author_handoff_contract": {"available": True}},
        citation_source_handoff_state="citation-state",
        unique_source_urls={"u": True},
        ordered_sources=["u"],
        final_answer_source_telemetry={"source": "telemetry"},
        citation_source_handoff_trace_fragment={"citation_source_handoff_contract": {"available": True}},
        economist_handoff_state="economist-state",
        economist_handoff_trace_fragment={"economist_handoff_contract": {"available": True}},
        synthesis_evaluator_supplemental_search_handoff_trace_fragment={"synthesis": {}},
        scrutineer_remediation_handoff_trace_fragment={"scrutineer": {}},
        trace_field_fragments=(),
    )

    def fake_trace(values):
        assert values["final_answer_packet"] == "packet"
        assert values["output_word_count"] == 7
        assert values["_provider_diagnostics_payload"] == {"provider_diagnostics": []}
        return {"trace": True}

    def fake_log(values, *, execution_trace, source_class_recovery_validation_packet, code_version_metadata):
        assert values["ordered_sources"] == ["u"]
        assert execution_trace == {"trace": True}
        assert source_class_recovery_validation_packet == {"validation": True}
        assert code_version_metadata == {"code": "version"}
        return {"log": True}

    monkeypatch.setattr(helper, "build_final_output_metadata", lambda **kwargs: {"output_word_count": 7})
    monkeypatch.setattr(helper, "build_execution_trace_projection", fake_trace)
    monkeypatch.setattr(
        helper,
        "attach_runtime_trace_export_compatibility_payloads",
        lambda *args, **kwargs: SimpleNamespace(source_class_recovery_validation_packet={"validation": True}),
    )
    monkeypatch.setattr(helper, "build_execution_log_entry_projection", fake_log)
    monkeypatch.setattr(helper, "current_code_version_metadata", lambda: {"code": "version"})
    monkeypatch.setattr(
        helper,
        "_POST_AUTHOR_OUTPUT_SCOPE_KEYS",
        (
            "report", "latency_seconds", "cost_snapshot", "source_class_projection_handoff",
            "final_top_evidence", "max_iterations", "source_class_evidence_bundle_observability_telemetry",
            "new_session", "run_log",
        ),
    )

    output = helper.build_post_author_output_packaging_from_scope(
        {
            "report": "one two",
            "latency_seconds": 1.25,
            "cost_snapshot": {"usd": 0},
            "source_class_projection_handoff": SimpleNamespace(recovered_source_class_passages=[]),
            "final_top_evidence": [],
            "max_iterations": 2,
            "source_class_evidence_bundle_observability_telemetry": {},
            "new_session": {"session": True},
            "run_log": SimpleNamespace(info=lambda *args, **kwargs: None),
        },
        trace_packaging=trace_packaging,
        code_version_metadata_builder=lambda: {"code": "version"},
    )

    assert output.execution_trace == {"trace": True}
    assert output.output_word_count == 7
    assert output.execution_log_entry == {"log": True}


def test_ag90h_static_seam_guard_for_post_author_helper():
    source = HELPER.read_text()
    forbidden_snippets = (
        "{**globals(), **locals()}",
        "globals()",
        "ask_model(",
        "process_search_queries(",
        "select_providers(",
        "choose_retrieval_search_depth(",
        "format_citation",
        "select_final_evidence",
        "execute_persistence_side_effects(",
        "cache.",
    )
    for snippet in forbidden_snippets:
        assert snippet not in source
    assert "**runtime_values" not in source
    assert "for key in _POST_AUTHOR_TRACE_SCOPE_KEYS" in source
    assert "for key in _POST_AUTHOR_OUTPUT_SCOPE_KEYS" in source
    forbidden_imports = (
        "core.search_providers",
        "core.prompts",
        "core.retrieval_dispatch_runtime",
        "core.final_evidence_bundle_builder",
        "core.persistence_side_effects",
    )
    for import_name in forbidden_imports:
        assert import_name not in source


def test_ag90h_orchestrator_uses_bounded_post_author_projection_seam():
    source = ORCHESTRATOR.read_text()
    assert "build_post_author_trace_packaging_from_scope" in source
    assert "build_post_author_output_packaging_from_scope" in source
    assert "return build_run_outcome_from_scope(locals())" in source
    assert "{**globals(), **locals()}" not in source
